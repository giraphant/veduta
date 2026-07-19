import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from veduta_data.artwork_kinds import classify_artwork_kind
from veduta_data.artpaper_import import import_artpaper_bundle
from veduta_data.chicago_api_import import import_chicago_api
from veduta_data.cleveland_import import import_cleveland_api
from veduta_data.downloader import download_first_working
from veduta_data.google_arts_dezoom import dezoomify_google_arts
from veduta_data.getty_import import import_getty_api
from veduta_data.harvard_import import import_harvard_api
from veduta_data.installed_packs import default_artpaper_image_root, import_installed_pack_images
from veduta_data.library_writer import (
    load_catalog,
    load_collection,
    selected_collections,
    update_wallpaper_metadata,
    upsert_metadata_collections,
    write_json,
    write_metadata_library,
)
from veduta_data.met_import import import_met_api
from veduta_data.nga_import import import_nga_api
from veduta_data.smithsonian_import import import_smithsonian_api
from veduta_data.vam_import import import_vam_api
from veduta_data.ycba_import import import_ycba_api


def default_library_root() -> Path:
    return Path.home() / "Pictures" / "VedutaLibrary"


def import_metadata(args: argparse.Namespace) -> int:
    library = import_artpaper_bundle(Path(args.artpaper_app))
    write_metadata_library(library, Path(args.library_root).expanduser())
    total = sum(len(collection.artworks) for collection in library.collections)
    print(f"Imported {len(library.collections)} collections and {total} artworks into {args.library_root}")
    return 0


def _harvard_kwargs(args: argparse.Namespace) -> dict[str, object] | None:
    api_key = str(args.api_key or "").strip()
    if not api_key:
        print(
            "Provide --api-key or set HARVARD_ART_MUSEUMS_API_KEY. "
            "Register at https://harvardartmuseums.org/collections/api",
            file=sys.stderr,
        )
        return None
    return {"api_key": api_key}


def _vam_kwargs(args: argparse.Namespace) -> dict[str, object]:
    max_per_creator = int(args.max_per_creator)
    return {"max_per_creator": max_per_creator if max_per_creator > 0 else None}


# One entry per museum API import command; all share run_api_import.
# import_fn is a module-global *name*, resolved at call time so tests can
# monkeypatch e.g. cli.import_cleveland_api.
API_IMPORTS = [
    {
        "command": "import-cleveland",
        "label": "Cleveland Museum of Art",
        "import_fn": "import_cleveland_api",
        "options": {
            "--fetch-limit": dict(type=int, default=250),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=3840),
            "--include-all-open-access": dict(action="store_true"),
        },
        "extra_kwargs": lambda args: {"highlights_only": not bool(args.include_all_open_access)},
    },
    {
        "command": "import-chicago-api",
        "label": "Art Institute of Chicago",
        "import_fn": "import_chicago_api",
        "legacy_collection_id": "chicago-api",
        "options": {
            "--fetch-limit": dict(type=int, default=250),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=3000),
        },
    },
    {
        "command": "import-met",
        "label": "Metropolitan Museum of Art",
        "import_fn": "import_met_api",
        "options": {
            "--fetch-limit": dict(type=int, default=250),
            "--limit": dict(type=int, default=100),
        },
    },
    {
        "command": "import-nga",
        "label": "National Gallery of Art",
        "import_fn": "import_nga_api",
        "options": {
            "--fetch-limit": dict(type=int, default=250),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=3000),
        },
    },
    {
        "command": "import-harvard",
        "label": "Harvard Art Museums",
        "import_fn": "import_harvard_api",
        "options": {
            "--api-key": dict(default=os.environ.get("HARVARD_ART_MUSEUMS_API_KEY", "")),
            "--fetch-limit": dict(type=int, default=250),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=3000),
        },
        "extra_kwargs": _harvard_kwargs,
    },
    {
        "command": "import-smithsonian",
        "label": "Smithsonian American Art Museum",
        "import_fn": "import_smithsonian_api",
        "options": {
            "--fetch-limit": dict(type=int, default=500),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=3840),
            "--max-files": dict(type=int, default=256),
        },
        "extra_kwargs": lambda args: {"max_files": int(args.max_files)},
    },
    {
        "command": "import-vam",
        "label": "Victoria and Albert Museum",
        "import_fn": "import_vam_api",
        "options": {
            "--fetch-limit": dict(type=int, default=300),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=3840),
            "--max-per-creator": dict(type=int, default=3, help="0 disables the per-artist cap"),
        },
        "extra_kwargs": _vam_kwargs,
    },
    {
        "command": "import-ycba",
        "label": "Yale Center for British Art",
        "import_fn": "import_ycba_api",
        "options": {
            "--fetch-limit": dict(type=int, default=1000),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=2500),
        },
    },
    {
        "command": "import-getty",
        "label": "J. Paul Getty Museum",
        "import_fn": "import_getty_api",
        "options": {
            "--fetch-limit": dict(type=int, default=250),
            "--limit": dict(type=int, default=100),
            "--min-long-edge": dict(type=int, default=3840),
            "--start-page": dict(type=int, default=1000),
        },
        "extra_kwargs": lambda args: {"start_page": int(args.start_page)},
    },
]


def run_api_import(args: argparse.Namespace) -> int:
    spec = args.import_spec
    kwargs: dict[str, object] = {"fetch_limit": int(args.fetch_limit), "keep_limit": int(args.limit)}
    if hasattr(args, "min_long_edge"):
        kwargs["min_long_edge"] = int(args.min_long_edge)
    extra_kwargs = spec.get("extra_kwargs")
    if extra_kwargs is not None:
        extra = extra_kwargs(args)
        if extra is None:
            return 1
        kwargs.update(extra)
    library_root = Path(args.library_root).expanduser()
    library = globals()[spec["import_fn"]](**kwargs)
    legacy_id = spec.get("legacy_collection_id")
    if legacy_id:
        remove_legacy_collection(library_root, legacy_id)
    upsert_metadata_collections(library, library_root)
    total = sum(len(collection.artworks) for collection in library.collections)
    print(f"Imported {spec['label']} collection with {total} artworks into {args.library_root}")
    return 0


def remove_legacy_collection(library_root: Path, collection_id: str) -> None:
    catalog_path = library_root / "catalog.json"
    if not catalog_path.exists():
        return
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    collections = list(catalog.get("collections") or [])
    removed_manifests = [
        str(collection.get("manifest"))
        for collection in collections
        if collection.get("id") == collection_id and collection.get("manifest")
    ]
    catalog["collections"] = [collection for collection in collections if collection.get("id") != collection_id]
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for manifest in removed_manifests:
        (library_root / manifest).unlink(missing_ok=True)


def is_http_url(value: object) -> bool:
    return isinstance(value, str) and urlparse(value).scheme in {"http", "https"}


def is_low_resolution(width: int, height: int, min_long_edge: int = 3840) -> bool:
    return max(width, height) < min_long_edge


def unsupported_download_artworks(collection: dict[str, object]) -> list[str]:
    unsupported = []
    for artwork in collection["artworks"]:
        wallpaper = artwork["images"]["wallpaper"]
        fallback_urls = wallpaper["fallbackUrls"]
        if not fallback_urls or any(not is_http_url(url) for url in fallback_urls):
            unsupported.append(str(artwork["id"]))
    return unsupported


def classify_artwork_kinds(args: argparse.Namespace) -> int:
    library_root = Path(args.library_root).expanduser()
    catalog = load_catalog(library_root)
    total_updated = 0
    processed = 0

    for collection_summary in selected_collections(catalog, args.collection, args.all):
        processed += 1
        manifest_path = library_root / str(collection_summary["manifest"])
        collection = load_collection(library_root, str(collection_summary["manifest"]))
        updated = 0
        for artwork in collection["artworks"]:
            classification = artwork.setdefault("classification", {})
            kind = classify_artwork_kind(
                str(collection["id"]),
                str(artwork.get("title", "")),
                str(artwork.get("creator", "")),
                artwork.get("details") if isinstance(artwork.get("details"), dict) else None,
                str(artwork.get("id", "")),
            )
            if classification.get("kind") != kind:
                classification["kind"] = kind
                updated += 1
        if updated:
            write_json(manifest_path, collection)
        total_updated += updated
        print(f"{collection['id']}: {updated} artwork classification(s) updated")

    print(f"Updated {total_updated} artwork classification(s) in {processed} collection(s)")
    return 0


def download(args: argparse.Namespace) -> int:
    library_root = Path(args.library_root).expanduser()
    catalog = load_catalog(library_root)
    failures_path = library_root / "failures.jsonl"
    failures_path.unlink(missing_ok=True)
    successes = 0
    failures = 0

    selected = []
    for collection_summary in selected_collections(catalog, args.collection, args.all):
        manifest_path = library_root / str(collection_summary["manifest"])
        collection = load_collection(library_root, str(collection_summary["manifest"]))
        unsupported = unsupported_download_artworks(collection)
        if unsupported:
            sample = unsupported[:5]
            print(
                f"Cannot download collection {collection['id']}: {len(unsupported)} artwork(s) have non-HTTP fallback URLs "
                f"(e.g. {', '.join(sample)}). Use import-installed-packs or revise the acquisition strategy.",
                file=sys.stderr,
            )
            failures += len(unsupported)
        else:
            selected.append((collection, manifest_path))

    if failures:
        print(f"Download pass complete: 0 successes, {failures} failures")
        return 1

    for collection, manifest_path in selected:
        for artwork in collection["artworks"]:
            if args.limit is not None and successes >= int(args.limit):
                break
            wallpaper = artwork["images"]["wallpaper"]
            if wallpaper.get("excluded") and wallpaper.get("exclusionReason") != "pending-slow-download":
                continue
            destination = library_root / str(wallpaper["localPath"])
            existing_width = int(wallpaper.get("width") or 0)
            existing_height = int(wallpaper.get("height") or 0)
            if (
                args.limit is not None
                and destination.exists()
                and not wallpaper.get("excluded")
                and existing_width > 0
                and existing_height > 0
                and not is_low_resolution(existing_width, existing_height)
            ):
                continue
            try:
                result = download_first_working(list(wallpaper["fallbackUrls"]), destination, float(args.delay))
                metadata = {
                    "width": result["width"],
                    "height": result["height"],
                    "bytes": result["bytes"],
                    "sha256": result["sha256"],
                }
                if result["url"] is not None:
                    metadata["downloadedFrom"] = result["url"]
                elif wallpaper.get("downloadedFrom"):
                    metadata["downloadedFrom"] = wallpaper["downloadedFrom"]
                elif wallpaper["fallbackUrls"]:
                    metadata["downloadedFrom"] = wallpaper["fallbackUrls"][0]
                if is_low_resolution(int(metadata["width"]), int(metadata["height"])):
                    metadata["lowRes"] = True
                    metadata["excluded"] = True
                    metadata["exclusionReason"] = "downloaded-image-below-wallpaper-threshold"
                    if destination.exists():
                        destination.unlink()
                else:
                    metadata["lowRes"] = None
                    metadata["excluded"] = None
                    metadata["exclusionReason"] = None
                    metadata["rejectedLowRes"] = None
                update_wallpaper_metadata(manifest_path, str(artwork["id"]), metadata)
                successes += 1
                print(f"{result['status']}: {collection['id']}/{artwork['id']} {metadata['width']}x{metadata['height']}")
            except Exception as error:
                failures += 1
                failures_path.parent.mkdir(parents=True, exist_ok=True)
                with failures_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({
                        "collection": collection["id"],
                        "artwork": artwork["id"],
                        "error": str(error),
                    }, ensure_ascii=False) + "\n")
                print(f"failed: {collection['id']}/{artwork['id']}: {error}", file=sys.stderr)
            if args.limit is None or successes < int(args.limit):
                time.sleep(float(args.delay))
        if args.limit is not None and successes >= int(args.limit):
            break

    print(f"Download pass complete: {successes} successes, {failures} failures")
    return 1 if failures > 0 else 0


def import_installed_packs(args: argparse.Namespace) -> int:
    summary = import_installed_pack_images(
        library_root=Path(args.library_root),
        artpaper_image_root=Path(args.artpaper_image_root),
        quality=str(args.quality),
        collection_id=args.collection,
    )
    print(f"Installed pack import complete: {summary.copied_count} copied, {summary.missing_count} missing")
    for missing in summary.missing[:20]:
        print(f"missing: {missing.collection_id}/{missing.artwork_id}: {missing.source_path}", file=sys.stderr)
    if summary.missing_count > 20:
        print(f"missing: ... {summary.missing_count - 20} more", file=sys.stderr)
    return 1 if summary.copied_count == 0 or summary.missing_count > 0 else 0


def dezoomify_collection(args: argparse.Namespace) -> int:
    library_root = Path(args.library_root).expanduser()
    catalog = load_catalog(library_root)
    collection_summary = selected_collections(catalog, args.collection, False)[0]
    manifest_path = library_root / str(collection_summary["manifest"])
    collection = load_collection(library_root, str(collection_summary["manifest"]))
    failures_path = library_root / "dezoomify-failures.jsonl"
    failures_path.unlink(missing_ok=True)
    successes = 0
    failures = 0
    processed = 0

    for artwork in collection["artworks"]:
        if args.limit is not None and processed >= args.limit:
            break
        processed += 1
        wallpaper = artwork["images"]["wallpaper"]
        destination = library_root / str(wallpaper["localPath"])
        if destination.exists() and not args.force:
            successes += 1
            print(f"skipped: {collection['id']}/{artwork['id']} already exists")
            continue
        try:
            result = dezoomify_google_arts(
                str(artwork["sources"]["canonicalPage"]),
                destination,
                command=str(args.command),
                parallelism=int(args.parallelism),
                min_interval=str(args.min_interval),
                retries=int(args.retries),
                min_width=args.min_width,
                timeout=float(args.timeout),
            )
            metadata = {
                "width": result["width"],
                "height": result["height"],
                "bytes": result["bytes"],
                "sha256": result["sha256"],
                "downloadedFrom": result["url"],
            }
            update_wallpaper_metadata(manifest_path, str(artwork["id"]), metadata)
            successes += 1
            print(f"dezoomified: {collection['id']}/{artwork['id']} {metadata['width']}x{metadata['height']}")
        except Exception as error:
            failures += 1
            failures_path.parent.mkdir(parents=True, exist_ok=True)
            with failures_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "collection": collection["id"],
                    "artwork": artwork["id"],
                    "error": str(error),
                }, ensure_ascii=False) + "\n")
            print(f"failed: {collection['id']}/{artwork['id']}: {error}", file=sys.stderr)

        if args.artwork_delay > 0 and (args.limit is None or processed < args.limit):
            time.sleep(float(args.artwork_delay))

    print(f"Dezoomify pass complete: {successes} successes, {failures} failures")
    return 1 if failures > 0 else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="veduta-data")
    subcommands = parser.add_subparsers(dest="command", required=True)

    import_parser = subcommands.add_parser("import-metadata")
    import_parser.add_argument("--artpaper-app", default="/Applications/Artpaper.app")
    import_parser.add_argument("--library-root", default=str(default_library_root()))
    import_parser.set_defaults(func=import_metadata)

    for spec in API_IMPORTS:
        api_parser = subcommands.add_parser(str(spec["command"]))
        api_parser.add_argument("--library-root", default=str(default_library_root()))
        for flag, options in spec["options"].items():
            api_parser.add_argument(flag, **options)
        api_parser.set_defaults(func=run_api_import, import_spec=spec)

    classify_parser = subcommands.add_parser("classify-artwork-kinds")
    classify_parser.add_argument("--library-root", default=str(default_library_root()))
    classify_parser.add_argument("--collection")
    classify_parser.add_argument("--all", action="store_true")
    classify_parser.set_defaults(func=classify_artwork_kinds)

    download_parser = subcommands.add_parser("download")
    download_parser.add_argument("--library-root", default=str(default_library_root()))
    download_parser.add_argument("--collection")
    download_parser.add_argument("--all", action="store_true")
    download_parser.add_argument("--delay", type=float, default=1.0)
    download_parser.add_argument("--limit", type=int)
    download_parser.set_defaults(func=download)

    import_installed_parser = subcommands.add_parser("import-installed-packs")
    import_installed_parser.add_argument("--library-root", default=str(default_library_root()))
    import_installed_parser.add_argument("--artpaper-image-root", default=str(default_artpaper_image_root()))
    import_installed_parser.add_argument("--quality", choices=["5k", "hd", "regular"], default="5k")
    import_installed_parser.add_argument("--collection")
    import_installed_parser.set_defaults(func=import_installed_packs)

    dezoomify_parser = subcommands.add_parser("dezoomify-google-arts")
    dezoomify_parser.add_argument("--library-root", default=str(default_library_root()))
    dezoomify_parser.add_argument("--collection", required=True)
    dezoomify_parser.add_argument("--limit", type=int)
    dezoomify_parser.add_argument("--force", action="store_true")
    dezoomify_parser.add_argument("--command", default="dezoomify-rs")
    dezoomify_parser.add_argument("--parallelism", type=int, default=4)
    dezoomify_parser.add_argument("--min-interval", default="100ms")
    dezoomify_parser.add_argument("--retries", type=int, default=2)
    dezoomify_parser.add_argument("--min-width", type=int, default=2500)
    dezoomify_parser.add_argument("--timeout", type=float, default=600)
    dezoomify_parser.add_argument("--artwork-delay", type=float, default=0)
    dezoomify_parser.set_defaults(func=dezoomify_collection)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
