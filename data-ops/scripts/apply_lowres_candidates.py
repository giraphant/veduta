#!/usr/bin/env python3
"""Apply audited high-res replacements for low-res OpenArtPaper artworks.

Reads JSON arrays from ~/Pictures/OpenArtPaperLibrary/lowres_audit_candidates/*.json.
Each candidate must include id and candidate_url.

This only applies verified candidates: it downloads the candidate image, verifies
it is larger than the current manifest dimensions, atomically replaces the local
image, updates metadata, and removes the lowRes flag.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openartpaper_data.downloader import image_dimensions, sha256_file
from openartpaper_data.library_writer import write_json

LIBRARY_ROOT = Path(os.environ.get("OPENARTPAPER_LIBRARY", os.path.expanduser("~/Pictures/OpenArtPaperLibrary")))
CANDIDATE_DIR = LIBRARY_ROOT / "lowres_audit_candidates"
USER_AGENT = "OpenArtPaper/0.1 high-res audit applicator"


def load_manifests() -> dict[str, tuple[Path, dict]]:
    manifests: dict[str, tuple[Path, dict]] = {}
    for path in (LIBRARY_ROOT / "collections").glob("*.json"):
        data = json.loads(path.read_text())
        manifests[data["id"]] = (path, data)
    return manifests


def find_artwork(manifests: dict[str, tuple[Path, dict]], artwork_id: str) -> tuple[str, Path, dict, dict] | None:
    for cid, (path, manifest) in manifests.items():
        for artwork in manifest["artworks"]:
            if artwork["id"] == artwork_id:
                return cid, path, manifest, artwork
    return None


def download(url: str, dest: Path, timeout: float = 180.0) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = resp.headers.get("content-type", "")
        if not ctype.startswith("image/"):
            raise ValueError(f"Expected image content, got {ctype}")
        with dest.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)


def load_candidates() -> list[dict]:
    all_candidates: list[dict] = []
    if not CANDIDATE_DIR.exists():
        raise FileNotFoundError(f"Candidate dir not found: {CANDIDATE_DIR}")
    for path in sorted(CANDIDATE_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise ValueError(f"Expected list in {path}")
        for item in data:
            item["_candidate_file"] = path.name
        all_candidates.extend(data)
    return all_candidates


def apply_candidate(candidate: dict, manifests: dict[str, tuple[Path, dict]]) -> str:
    aid = candidate["id"]
    found = find_artwork(manifests, aid)
    if not found:
        return f"MISS manifest: {aid}"

    cid, manifest_path, manifest, artwork = found
    wallpaper = artwork["images"]["wallpaper"]
    if not wallpaper.get("lowRes"):
        return f"SKIP already-hires: {cid}/{aid}"

    current_w = int(wallpaper.get("width") or 0)
    current_h = int(wallpaper.get("height") or 0)
    local_path = LIBRARY_ROOT / wallpaper["localPath"]
    tmp_path = local_path.with_suffix(".candidate.jpg")
    backup_path = local_path.with_suffix(".before-candidate.jpg")

    url = candidate["candidate_url"]
    try:
        download(url, tmp_path)
        new_w, new_h = image_dimensions(tmp_path)
        if new_w <= current_w and new_h <= current_h:
            tmp_path.unlink(missing_ok=True)
            return f"SKIP not-better: {cid}/{aid} {current_w}x{current_h} -> {new_w}x{new_h}"

        # Backup then replace.
        if local_path.exists():
            if backup_path.exists():
                backup_path.unlink()
            local_path.replace(backup_path)
        tmp_path.replace(local_path)

        wallpaper.update({
            "width": new_w,
            "height": new_h,
            "bytes": local_path.stat().st_size,
            "sha256": sha256_file(local_path),
            "downloadedFrom": url,
        })
        wallpaper.pop("lowRes", None)
        artwork["sources"]["canonicalPage"] = candidate.get("candidate_page") or candidate.get("source_page") or url
        write_json(manifest_path, manifest)

        backup_path.unlink(missing_ok=True)
        return f"OK {cid}/{aid}: {current_w}x{current_h} -> {new_w}x{new_h}"
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        # Restore if replacement somehow happened before failure.
        if backup_path.exists() and not local_path.exists():
            backup_path.replace(local_path)
        return f"FAIL {cid}/{aid}: {exc}"


def main() -> None:
    candidates = load_candidates()
    manifests = load_manifests()
    print(f"Loaded {len(candidates)} candidates from {CANDIDATE_DIR}", flush=True)

    ok = fail = skip = 0
    for i, candidate in enumerate(candidates, start=1):
        result = apply_candidate(candidate, manifests)
        print(f"[{i}/{len(candidates)}] {result}", flush=True)
        if result.startswith("OK "):
            ok += 1
        elif result.startswith("FAIL") or result.startswith("MISS"):
            fail += 1
        else:
            skip += 1
        time.sleep(0.2)

    print(f"\nDone: {ok} applied, {skip} skipped, {fail} failed", flush=True)


if __name__ == "__main__":
    main()
