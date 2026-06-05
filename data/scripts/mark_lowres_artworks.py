#!/usr/bin/env python3
"""Mark already-downloaded low-resolution artworks as excluded.

This is for legacy manifests that have width/height metadata but were created
before the downloader started excluding low-resolution images automatically.
The local image file is kept for audit/replacement work; the app skips artworks
with images.wallpaper.excluded == true.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from veduta_data.downloader import image_dimensions
from veduta_data.library_writer import write_json

DEFAULT_LIBRARY_ROOT = Path(os.environ.get("VEDUTA_LIBRARY", os.path.expanduser("~/Pictures/VedutaLibrary")))
EXCLUSION_REASON = "existing-downloaded-image-below-wallpaper-threshold"


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def int_value(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def local_image_path(library_root: Path, wallpaper: dict[str, Any]) -> Path | None:
    local_path = wallpaper.get("localPath")
    if not isinstance(local_path, str) or not local_path:
        return None
    return library_root / local_path


def wallpaper_dimensions(library_root: Path, wallpaper: dict[str, Any]) -> tuple[int, int]:
    width = int_value(wallpaper.get("width"))
    height = int_value(wallpaper.get("height"))
    if width > 0 and height > 0:
        return width, height

    image_path = local_image_path(library_root, wallpaper)
    if image_path is None or not image_path.exists():
        return 0, 0

    return image_dimensions(image_path)


def mark_lowres_artworks(
    library_root: Path,
    *,
    min_long_edge: int = 2500,
    dry_run: bool = False,
    marked_at: str | None = None,
) -> dict[str, Any]:
    marked_at = marked_at or now_iso()
    report_items: list[dict[str, Any]] = []

    for manifest_path in sorted((library_root / "collections").glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        changed = False

        for artwork in manifest.get("artworks", []):
            wallpaper = artwork.get("images", {}).get("wallpaper", {})
            if wallpaper.get("excluded") is True:
                continue

            image_path = local_image_path(library_root, wallpaper)
            if image_path is None or not image_path.exists():
                continue

            width, height = wallpaper_dimensions(library_root, wallpaper)
            if max(width, height) == 0 or max(width, height) >= min_long_edge:
                continue

            previous = {
                key: wallpaper.get(key)
                for key in ("width", "height", "bytes", "sha256", "downloadedFrom")
                if wallpaper.get(key) is not None
            }
            item = {
                "collection": manifest["id"],
                "id": artwork["id"],
                "title": artwork.get("title"),
                "creator": artwork.get("creator"),
                "localPath": wallpaper.get("localPath"),
                "width": width,
                "height": height,
                "exclusionReason": EXCLUSION_REASON,
            }
            report_items.append(item)

            if dry_run:
                continue

            wallpaper["width"] = width
            wallpaper["height"] = height
            wallpaper["lowRes"] = True
            wallpaper["excluded"] = True
            wallpaper["exclusionReason"] = EXCLUSION_REASON
            wallpaper["markedLowResAt"] = marked_at
            wallpaper["rejectedLowRes"] = previous
            changed = True

        if changed:
            write_json(manifest_path, manifest)

    report = {
        "markedAt": marked_at,
        "dryRun": dry_run,
        "minLongEdge": min_long_edge,
        "reason": EXCLUSION_REASON,
        "count": len(report_items),
        "items": report_items,
    }

    if not dry_run:
        write_json(library_root / "lowres_marked_report.json", report)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", type=Path, default=DEFAULT_LIBRARY_ROOT)
    parser.add_argument("--min-long-edge", type=int, default=2500)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = mark_lowres_artworks(
        Path(args.library_root).expanduser(),
        min_long_edge=int(args.min_long_edge),
        dry_run=bool(args.dry_run),
    )
    action = "Would mark" if args.dry_run else "Marked"
    print(f"{action} {report['count']} low-resolution artworks below {report['minLongEdge']}px")
    if not args.dry_run:
        print(f"Report: {Path(args.library_root).expanduser() / 'lowres_marked_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
