#!/usr/bin/env python3
"""Scan Wikimedia Commons for undownloaded OpenArtPaper artworks.

For each artwork missing a local image, searches Commons using the
Wikimedia API and picks the best match (preferring "Google Art Project"
uploads for maximum resolution).

Outputs a JSON mapping: {artwork_id: {commons_page, direct_url, file_title}}
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LIBRARY_ROOT = Path(os.environ.get(
    "OPENARTPAPER_LIBRARY",
    os.path.expanduser("~/Pictures/OpenArtPaperLibrary"),
))

API_URL = "https://commons.wikimedia.org/w/api.php"
UA = "OpenArtPaper/1.0 (gallery-expansion; courtesy bot)"
RATE_LIMIT = 1.5  # seconds between API calls (be kind to Wikimedia)
MAX_RETRIES = 5


# ── Commons API helpers ──────────────────────────────────────────────

def _api(params: dict) -> dict:
    """Call the Wikimedia Commons API with exponential backoff on 429."""
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES - 1:
                wait = 10 * (2 ** attempt)  # 10s, 20s, 40s, 80s
                print(f"    ⏳ 429 rate-limited, backing off {wait}s (attempt {attempt+1})…")
                time.sleep(wait)
                continue
            raise
        except (TimeoutError, OSError) as e:
            if attempt < MAX_RETRIES - 1:
                wait = 5 * (attempt + 1)
                print(f"    ⏳ network error ({e}), retrying in {wait}s…")
                time.sleep(wait)
                continue
            raise


def search_commons_with_url(query: str, limit: int = 10) -> list[tuple[dict, str | None]]:
    """Search Commons AND resolve direct URLs in a single pass.

    Returns list of (search_hit_dict, direct_url_or_None).
    """
    data = _api({
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size",
        "format": "json",
    })

    # Build a map of pageid -> direct_url from the imageinfo results
    url_map: dict[int, str | None] = {}
    size_map: dict[int, tuple[int, int]] = {}
    pages = data.get("query", {}).get("pages", {})
    if pages:
        for pid, page in pages.items():
            ii = page.get("imageinfo", [])
            if ii:
                url_map[int(pid)] = ii[0].get("url")
                w = ii[0].get("width", 0)
                h = ii[0].get("height", 0)
                size_map[int(pid)] = (w, h)
            else:
                url_map[int(pid)] = None

    # Also get search result ordering (generator doesn't always preserve it)
    results = []
    for pid, page in (pages or {}).items():
        results.append((page, url_map.get(int(pid)), size_map.get(int(pid), (0, 0))))

    return results


# ── Match scoring ────────────────────────────────────────────────────

def score_result(file_title: str, creator: str, title: str, width: int, height: int) -> float:
    """Score a Commons file; higher is better."""
    t = file_title.lower()
    score = 0.0

    # Strong preference for Google Art Project uploads (highest res)
    if "google art project" in t:
        score += 10.0

    # Penalise cropped / thumbnail variants
    for bad in ("cropped", "thumbnail", "detail", "crop"):
        if bad in t:
            score -= 5.0

    # Bonus if creator surname appears in filename
    creator_last = creator.split()[-1].lower() if creator else ""
    if creator_last and creator_last in t:
        score += 3.0

    # Bonus for significant words from title appearing
    title_words = {w.lower() for w in title.split() if len(w) > 3}
    matches = sum(1 for w in title_words if w in t)
    score += matches * 0.5

    # Bonus for higher resolution
    megapixels = (width * height) / 1_000_000
    if megapixels > 10:
        score += 2.0
    elif megapixels > 5:
        score += 1.0

    return score


def pick_best(hits: list[tuple[dict, str | None, tuple[int, int]]],
              creator: str, title: str) -> tuple[dict, str | None] | None:
    """Return (page_dict, direct_url) for the best-scoring hit."""
    scored = []
    for page, url, (w, h) in hits:
        ft = page.get("title", "")
        s = score_result(ft, creator, title, w, h)
        scored.append((s, page, url))
    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1], scored[0][2]
    return None


# ── Main scan logic ──────────────────────────────────────────────────

def load_undownloaded(collection_id: str) -> list[dict]:
    manifest_path = LIBRARY_ROOT / "collections" / f"{collection_id}.json"
    data = json.loads(manifest_path.read_text())
    return [
        a for a in data["artworks"]
        if not a["images"]["wallpaper"].get("sha256")
    ]


def build_query(creator: str, title: str) -> str:
    """Build a Commons search query from artwork metadata."""
    parts = [creator]
    for w in title.split():
        if len(w) > 2 and w.lower() not in (
            "the", "der", "die", "das", "und", "von", "with", "near", "from", "and",
        ):
            parts.append(w)
    return " ".join(parts)


def scan_collection(collection_id: str, output: dict) -> tuple[int, int]:
    """Scan one collection. Returns (matched, total)."""
    artworks = load_undownloaded(collection_id)
    matched = 0
    total = len(artworks)

    print(f"\n[{collection_id}] Scanning {total} artworks…", flush=True)

    for i, art in enumerate(artworks):
        aid = art["id"]

        # Skip if already scanned (resume support)
        if aid in output:
            matched += 1
            continue

        creator = art["creator"]
        title = art["title"]
        query = build_query(creator, title)

        hits = search_commons_with_url(query, limit=10)
        result = pick_best(hits, creator, title)

        if result:
            page, direct_url = result
            file_title = page.get("title", "")
            if direct_url:
                commons_page = (
                    "https://commons.wikimedia.org/wiki/"
                    + urllib.parse.quote(file_title.replace(" ", "_"))
                )
                output[aid] = {
                    "collection": collection_id,
                    "commons_page": commons_page,
                    "direct_url": direct_url,
                    "file_title": file_title,
                    "creator": creator,
                    "title": title,
                }
                matched += 1
                status = "✓"
            else:
                status = "✗ (no direct URL)"
        else:
            status = "✗"

        pct = (i + 1) / total * 100
        print(f"  {pct:5.1f}%  {status}  {creator} – {title}", flush=True)

        # Save progress every 10 artworks
        if (i + 1) % 10 == 0:
            _save_results(output)

        time.sleep(RATE_LIMIT)

    print(f"[{collection_id}] Matched {matched}/{total}", flush=True)
    return matched, total


def _save_results(results: dict):
    results_path = LIBRARY_ROOT / "commons_scan_results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))


def main():
    collections = sys.argv[1:] if len(sys.argv) > 1 else ["berlin", "wales"]
    results_path = LIBRARY_ROOT / "commons_scan_results.json"

    # Load existing results (resume support)
    if results_path.exists():
        results = json.loads(results_path.read_text())
        print(f"Resuming with {len(results)} existing results", flush=True)
    else:
        results = {}

    total_matched = 0
    total_artworks = 0
    for cid in collections:
        m, t = scan_collection(cid, results)
        total_matched += m
        total_artworks += t
        _save_results(results)

    print(f"\n═══ Final: {total_matched}/{total_artworks} artworks matched on Commons ═══", flush=True)
    print(f"Results saved to {results_path}", flush=True)


if __name__ == "__main__":
    main()
