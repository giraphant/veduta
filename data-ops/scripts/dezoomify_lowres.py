#!/usr/bin/env python3
"""Find Google Arts asset URLs for low-res artworks and dezoomify them.

For each lowRes-flagged artwork sourced from ggpht.com:
1. Search Google Arts & Culture for the artwork
2. Pick the best matching asset URL
3. Run dezoomify-rs to download the hi-res version
4. Replace the low-res image and update manifest
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Add data-ops src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openartpaper_data.downloader import sha256_file, image_dimensions
from openartpaper_data.library_writer import update_wallpaper_metadata, write_json

LIBRARY_ROOT = Path(os.environ.get(
    "OPENARTPAPER_LIBRARY",
    os.path.expanduser("~/Pictures/OpenArtPaperLibrary"),
))

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DEZOOMIFY = "dezoomify-rs"
SEARCH_DELAY = 300.0  # 5 min between searches to avoid 429
DEZOOMIFY_DELAY = 1.0
SEARCH_RETRIES = 3


# ── Google Arts search ───────────────────────────────────────────────

def search_google_arts(query: str) -> list[str]:
    """Search Google Arts & Culture, return matching asset paths."""
    url = f"https://artsandculture.google.com/search?q={urllib.parse.quote(query)}"
    for attempt in range(SEARCH_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                return list(set(re.findall(r'/asset/([^"\s]+)', html)))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < SEARCH_RETRIES - 1:
                wait = 30 * (2 ** attempt)
                print(f"    ⏳ Google 429, backing off {wait}s…", flush=True)
                time.sleep(wait)
                continue
            print(f"    search error: {e}", flush=True)
            return []
        except Exception as e:
            print(f"    search error: {e}", flush=True)
            return []
    return []


def pick_best_asset(assets: list[str], creator: str, title: str) -> str | None:
    """Pick the asset URL that best matches the artwork."""
    if not assets:
        return None

    title_lower = title.lower()
    creator_lower = creator.lower()
    creator_last = creator.split()[-1].lower() if creator else ""

    best = None
    best_score = 0

    for asset in assets:
        slug = asset.split("/")[0].lower()  # the descriptive part before the ID
        score = 0

        # Match creator last name
        if creator_last and creator_last in slug:
            score += 5

        # Match significant title words
        title_words = {w.lower() for w in title.split() if len(w) > 3}
        matches = sum(1 for w in title_words if w in slug)
        score += matches * 2

        if score > best_score:
            best_score = score
            best = asset

    if best and best_score >= 3:
        return f"https://artsandculture.google.com/asset/{best}"
    return None


# ── Dezoomify ────────────────────────────────────────────────────────

def dezoomify(url: str, output_path: Path, timeout: int = 300) -> bool:
    """Run dezoomify-rs to download a hi-res image."""
    tmp = output_path.with_suffix(".dezoomifying.jpg")
    try:
        result = subprocess.run(
            [DEZOOMIFY, "--largest", url, str(tmp)],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            print(f"    dezoomify error: {result.stderr[-200:]}", flush=True)
            if tmp.exists():
                tmp.unlink()
            return False

        if not tmp.exists() or tmp.stat().st_size < 10000:
            if tmp.exists():
                tmp.unlink()
            return False

        tmp.replace(output_path)
        return True
    except subprocess.TimeoutExpired:
        print(f"    dezoomify timeout ({timeout}s)", flush=True)
        if tmp.exists():
            tmp.unlink()
        return False
    except Exception as e:
        print(f"    dezoomify failed: {e}", flush=True)
        if tmp.exists():
            tmp.unlink()
        return False


# ── Main pipeline ────────────────────────────────────────────────────

def load_lowres_ggpht() -> list[dict]:
    """Load all lowRes artworks sourced from ggpht.com."""
    cat = json.loads((LIBRARY_ROOT / "catalog.json").read_text())
    results = []
    for c in cat["collections"]:
        cid = c["id"]
        manifest = json.loads((LIBRARY_ROOT / "collections" / f"{cid}.json").read_text())
        for a in manifest["artworks"]:
            w = a["images"]["wallpaper"]
            if w.get("lowRes") and "ggpht" in w.get("downloadedFrom", ""):
                results.append({
                    "collection": cid,
                    "id": a["id"],
                    "creator": a["creator"],
                    "title": a["title"],
                    "width": w.get("width", 0),
                    "height": w.get("height", 0),
                    "localPath": w.get("localPath", ""),
                })
    return results


def main():
    # Optional: limit for testing
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    artworks = load_lowres_ggpht()
    print(f"Found {len(artworks)} low-res ggpht artworks to upgrade", flush=True)

    if limit:
        artworks = artworks[:limit]
        print(f"Limited to {limit}", flush=True)

    # Resume support: track which ones we've tried
    progress_path = LIBRARY_ROOT / "dezoomify_progress.json"
    if progress_path.exists():
        progress = json.loads(progress_path.read_text())
        print(f"Resuming: {len(progress)} already processed", flush=True)
    else:
        progress = {}

    upgraded = 0
    failed = 0
    skipped = 0

    for i, art in enumerate(artworks):
        aid = art["id"]
        cid = art["collection"]

        if aid in progress:
            skipped += 1
            continue

        query = f"{art['creator']} {art['title']}"
        print(f"\n  [{i+1}/{len(artworks)}] {art['creator'][:25]} – {art['title'][:35]}", flush=True)

        # Step 1: Search Google Arts
        assets = search_google_arts(query)
        asset_url = pick_best_asset(assets, art["creator"], art["title"])

        if not asset_url:
            print(f"    ✗ no asset found ({len(assets)} candidates)", flush=True)
            progress[aid] = {"status": "no_asset", "url": None}
            failed += 1
            _save_progress(progress_path, progress)
            time.sleep(SEARCH_DELAY)
            continue

        print(f"    → {asset_url[:70]}", flush=True)

        # Step 2: Dezoomify
        img_path = LIBRARY_ROOT / art["localPath"]
        backup_path = img_path.with_suffix(".lowres.jpg")

        # Backup the existing low-res
        if img_path.exists() and not backup_path.exists():
            import shutil
            shutil.copy2(img_path, backup_path)

        if dezoomify(asset_url, img_path):
            # Step 3: Verify the new image is actually better
            try:
                new_w, new_h = image_dimensions(img_path)
                old_w, old_h = art["width"], art["height"]

                if new_w > old_w:
                    # Update manifest
                    manifest_path = LIBRARY_ROOT / "collections" / f"{cid}.json"
                    update_wallpaper_metadata(manifest_path, aid, {
                        "width": new_w,
                        "height": new_h,
                        "bytes": img_path.stat().st_size,
                        "sha256": sha256_file(img_path),
                        "downloadedFrom": asset_url,
                    })
                    # Remove lowRes flag
                    manifest = json.loads(manifest_path.read_text())
                    for a in manifest["artworks"]:
                        if a["id"] == aid:
                            a["images"]["wallpaper"].pop("lowRes", None)
                            break
                    write_json(manifest_path, manifest)

                    # Remove backup
                    if backup_path.exists():
                        backup_path.unlink()

                    progress[aid] = {"status": "upgraded", "url": asset_url,
                                     "old": f"{old_w}x{old_h}", "new": f"{new_w}x{new_h}"}
                    upgraded += 1
                    print(f"    ✓ upgraded {old_w}x{old_h} → {new_w}x{new_h}", flush=True)
                else:
                    # New image isn't better, restore backup
                    if backup_path.exists():
                        backup_path.replace(img_path)
                    progress[aid] = {"status": "not_better", "url": asset_url,
                                     "old": f"{old_w}x{old_h}", "new": f"{new_w}x{new_h}"}
                    failed += 1
                    print(f"    ✗ not better ({old_w}x{old_h} vs {new_w}x{new_h})", flush=True)
            except Exception as e:
                # Restore backup on error
                if backup_path.exists():
                    backup_path.replace(img_path)
                progress[aid] = {"status": "verify_error", "url": asset_url, "error": str(e)}
                failed += 1
                print(f"    ✗ verify error: {e}", flush=True)
        else:
            # Restore backup
            if backup_path.exists():
                backup_path.replace(img_path)
            progress[aid] = {"status": "dezoomify_failed", "url": asset_url}
            failed += 1

        _save_progress(progress_path, progress)
        time.sleep(DEZOOMIFY_DELAY)

    print(f"\n═══ Upgraded {upgraded}, Failed {failed}, Skipped {skipped} ═══", flush=True)


def _save_progress(path: Path, progress: dict):
    path.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
