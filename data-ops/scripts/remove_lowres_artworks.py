#!/usr/bin/env python3
"""Remove confirmed low-resolution artworks from the active local gallery.

This script deletes local image files for artworks still marked lowRes and updates
collection manifests so the artwork remains documented but is excluded from the
active downloaded wallpaper set.

It is intentionally conservative: only artworks with images.wallpaper.lowRes ==
true are affected.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

LIBRARY_ROOT = Path(os.environ.get("OPENARTPAPER_LIBRARY", os.path.expanduser("~/Pictures/OpenArtPaperLibrary")))
EXCLUSION_REASON = "low-resolution-no-high-res-source"


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    removed_at = now_iso()
    report: list[dict[str, object]] = []

    for manifest_path in sorted((LIBRARY_ROOT / "collections").glob("*.json")):
        manifest = json.loads(manifest_path.read_text())
        changed = False

        for artwork in manifest["artworks"]:
            wallpaper = artwork["images"]["wallpaper"]
            if not wallpaper.get("lowRes"):
                continue

            local_path = wallpaper.get("localPath")
            image_path = LIBRARY_ROOT / local_path if local_path else None
            existed = bool(image_path and image_path.exists())
            previous = {
                key: wallpaper.get(key)
                for key in ("width", "height", "bytes", "sha256", "downloadedFrom")
                if wallpaper.get(key) is not None
            }

            if image_path and image_path.exists():
                image_path.unlink()

            # Keep lowRes true as requested, but remove active downloaded-image
            # metadata so this artwork is not treated as a usable wallpaper.
            wallpaper["lowRes"] = True
            wallpaper["excluded"] = True
            wallpaper["exclusionReason"] = EXCLUSION_REASON
            wallpaper["removedLocalImage"] = True
            wallpaper["removedAt"] = removed_at
            wallpaper["rejectedLowRes"] = previous
            for key in ("width", "height", "bytes", "sha256", "downloadedFrom"):
                wallpaper.pop(key, None)

            report.append({
                "collection": manifest["id"],
                "id": artwork["id"],
                "title": artwork["title"],
                "creator": artwork["creator"],
                "localPath": local_path,
                "fileExisted": existed,
                "previous": previous,
                "exclusionReason": EXCLUSION_REASON,
            })
            changed = True

        if changed:
            write_json(manifest_path, manifest)

    report_path = LIBRARY_ROOT / "lowres_removed_report.json"
    write_json(report_path, {
        "removedAt": removed_at,
        "reason": EXCLUSION_REASON,
        "count": len(report),
        "items": report,
    })

    print(f"Removed/marked {len(report)} low-res artworks")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
