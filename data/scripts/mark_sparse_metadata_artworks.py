#!/usr/bin/env python3
"""Mark downloaded artworks with placeholder metadata as excluded.

This keeps local image files in place, but removes sparse records from the app's
active wallpaper pool by setting images.wallpaper.excluded == true.
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

from veduta_data.library_writer import write_json

DEFAULT_LIBRARY_ROOT = Path(os.environ.get("VEDUTA_LIBRARY", os.path.expanduser("~/Pictures/VedutaLibrary")))
EXCLUSION_REASON = "sparse-or-placeholder-metadata"
PLACEHOLDER_CREATORS = {"", "unknown", "unknown artist", "unidentified artist", "anonymous"}


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def metadata_issues(artwork: dict[str, Any]) -> list[str]:
    title = str(artwork.get("title") or "").strip().lower()
    creator = str(artwork.get("creator") or "").strip().lower()
    sources = artwork.get("sources") or {}
    canonical = str(sources.get("canonicalPage") or "").strip()
    details = artwork.get("details") or {}
    has_details = isinstance(details, dict) and any(
        details.get(key)
        for key in ("description", "briefDescription", "date", "place", "medium", "categories", "materials")
    )

    issues: list[str] = []
    if (not title or title.startswith("untitled")) and not has_details:
        issues.append("placeholder-title")
    if creator in PLACEHOLDER_CREATORS and not has_details:
        issues.append("placeholder-creator")
    if not canonical:
        issues.append("missing-canonical-page")
    return issues


def mark_sparse_metadata_artworks(
    library_root: Path,
    *,
    collection_id: str | None = None,
    dry_run: bool = False,
    marked_at: str | None = None,
) -> dict[str, Any]:
    marked_at = marked_at or now_iso()
    report_items: list[dict[str, Any]] = []

    for manifest_path in sorted((library_root / "collections").glob("*.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if collection_id is not None and manifest.get("id") != collection_id:
            continue

        changed = False
        for artwork in manifest.get("artworks", []):
            wallpaper = artwork.get("images", {}).get("wallpaper", {})
            local_path = wallpaper.get("localPath")
            if not isinstance(local_path, str) or not (library_root / local_path).exists():
                continue
            if wallpaper.get("excluded") is True:
                continue

            issues = metadata_issues(artwork)
            if not issues:
                continue

            report_items.append({
                "collection": manifest["id"],
                "id": artwork["id"],
                "title": artwork.get("title"),
                "creator": artwork.get("creator"),
                "localPath": local_path,
                "issues": issues,
                "exclusionReason": EXCLUSION_REASON,
            })

            if dry_run:
                continue

            wallpaper["excluded"] = True
            wallpaper["exclusionReason"] = EXCLUSION_REASON
            wallpaper["metadataIssues"] = issues
            wallpaper["markedSparseMetadataAt"] = marked_at
            changed = True

        if changed:
            write_json(manifest_path, manifest)

    suffix = f"_{collection_id}" if collection_id else ""
    report = {
        "markedAt": marked_at,
        "dryRun": dry_run,
        "collection": collection_id,
        "reason": EXCLUSION_REASON,
        "count": len(report_items),
        "items": report_items,
    }
    if not dry_run:
        write_json(library_root / f"sparse_metadata_marked_report{suffix}.json", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-root", type=Path, default=DEFAULT_LIBRARY_ROOT)
    parser.add_argument("--collection")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = mark_sparse_metadata_artworks(
        Path(args.library_root).expanduser(),
        collection_id=args.collection,
        dry_run=bool(args.dry_run),
    )
    action = "Would mark" if args.dry_run else "Marked"
    scope = f" in {args.collection}" if args.collection else ""
    print(f"{action} {report['count']} sparse-metadata artworks{scope}")
    if not args.dry_run:
        suffix = f"_{args.collection}" if args.collection else ""
        print(f"Report: {Path(args.library_root).expanduser() / f'sparse_metadata_marked_report{suffix}.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
