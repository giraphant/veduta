#!/usr/bin/env python3
"""Download artworks matched on Wikimedia Commons and update manifests.

Reads commons_scan_results.json produced by commons_scan.py, downloads
each image, computes metadata, and updates the collection manifests.
Fully resumable — skips artworks that already have sha256 in the manifest.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add data src to path so we can import the existing modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veduta_data.downloader import (
    download_url,
    image_dimensions,
    sha256_file,
)
from veduta_data.library_writer import update_wallpaper_metadata

LIBRARY_ROOT = Path(os.environ.get(
    "VEDUTA_LIBRARY",
    os.path.expanduser("~/Pictures/VedutaLibrary"),
))

RATE_LIMIT = 1.0  # seconds between downloads (be kind to Wikimedia)


def load_manifest(collection_id: str) -> dict:
    path = LIBRARY_ROOT / "collections" / f"{collection_id}.json"
    return json.loads(path.read_text())


def is_downloaded(manifest: dict, artwork_id: str) -> bool:
    for a in manifest["artworks"]:
        if a["id"] == artwork_id:
            return bool(a["images"]["wallpaper"].get("sha256"))
    return False


def download_one(match: dict, delay: float) -> bool:
    """Download a single artwork. Returns True on success."""
    aid = match["artwork_id"] if "artwork_id" in match else None
    cid = match["collection"]
    direct_url = match["direct_url"]

    # Reload manifest to check current state
    manifest_path = LIBRARY_ROOT / "collections" / f"{cid}.json"
    manifest = json.loads(manifest_path.read_text())

    # Find artwork id from commons_page or scan results
    if not aid:
        for a in manifest["artworks"]:
            if a["creator"] == match["creator"] and a["title"] == match["title"]:
                aid = a["id"]
                break

    if not aid:
        print(f"    ✗ could not find artwork id for {match['creator']} – {match['title']}", flush=True)
        return False

    if is_downloaded(manifest, aid):
        return True  # already done

    dest = LIBRARY_ROOT / "images" / cid / f"{aid}.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        download_url(direct_url, dest, timeout=120)
        width, height = image_dimensions(dest)
        file_size = dest.stat().st_size
        sha = sha256_file(dest)

        # Update manifest: metadata + commons canonical page
        update_wallpaper_metadata(manifest_path, aid, {
            "width": width,
            "height": height,
            "bytes": file_size,
            "sha256": sha,
            "downloadedFrom": direct_url,
        })

        # Also update the canonical page to point to Commons
        manifest2 = json.loads(manifest_path.read_text())
        for a in manifest2["artworks"]:
            if a["id"] == aid:
                a["sources"]["canonicalPage"] = match["commons_page"]
                break
        from veduta_data.library_writer import write_json
        write_json(manifest_path, manifest2)

        print(f"    ✓ {aid} ({width}×{height}, {file_size/1024/1024:.1f} MB)", flush=True)
        return True

    except Exception as e:
        print(f"    ✗ {aid}: {e}", flush=True)
        # Clean up partial/failed files
        if dest.exists():
            dest.unlink()
        partial = dest.with_suffix(dest.suffix + ".partial")
        if partial.exists():
            partial.unlink()
        return False


def main():
    results_path = LIBRARY_ROOT / "commons_scan_results.json"
    if not results_path.exists():
        print("No scan results found. Run commons_scan.py first.", file=sys.stderr)
        sys.exit(1)

    results = json.loads(results_path.read_text())
    print(f"Loaded {len(results)} scan results", flush=True)

    # Group by collection
    by_collection: dict[str, list[dict]] = {}
    for aid, match in results.items():
        cid = match["collection"]
        match["artwork_id"] = aid
        by_collection.setdefault(cid, []).append(match)

    total_ok = 0
    total_fail = 0

    for cid, matches in sorted(by_collection.items()):
        print(f"\n[{cid}] Downloading {len(matches)} matched artworks…", flush=True)
        ok = 0
        fail = 0

        for i, match in enumerate(matches):
            success = download_one(match, RATE_LIMIT)
            if success:
                ok += 1
            else:
                fail += 1

            if (i + 1) % 10 == 0:
                print(f"  progress: {i+1}/{len(matches)} ({ok} ok, {fail} fail)", flush=True)

            time.sleep(RATE_LIMIT)

        print(f"[{cid}] Done: {ok} downloaded, {fail} failed", flush=True)
        total_ok += ok
        total_fail += fail

    print(f"\n═══ Final: {total_ok} downloaded, {total_fail} failed ═══", flush=True)


if __name__ == "__main__":
    main()
