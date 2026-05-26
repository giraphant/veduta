import argparse
import json
import sys
import time
from pathlib import Path

from openartpaper_data.artpaper_import import import_artpaper_bundle
from openartpaper_data.downloader import download_first_working
from openartpaper_data.library_writer import update_wallpaper_metadata, write_metadata_library


def default_library_root() -> Path:
    return Path.home() / "Pictures" / "OpenArtPaperLibrary"


def import_metadata(args: argparse.Namespace) -> int:
    library = import_artpaper_bundle(Path(args.artpaper_app))
    write_metadata_library(library, Path(args.library_root).expanduser())
    total = sum(len(collection.artworks) for collection in library.collections)
    print(f"Imported {len(library.collections)} collections and {total} artworks into {args.library_root}")
    return 0


def load_catalog(library_root: Path) -> dict[str, object]:
    return json.loads((library_root / "catalog.json").read_text(encoding="utf-8"))


def load_collection(library_root: Path, manifest: str) -> dict[str, object]:
    return json.loads((library_root / manifest).read_text(encoding="utf-8"))


def selected_collections(catalog: dict[str, object], collection_id: str | None, all_collections: bool) -> list[dict[str, object]]:
    collections = list(catalog["collections"])
    if all_collections:
        return collections
    if collection_id is None:
        raise SystemExit("Provide --collection <id> or --all")
    matches = [collection for collection in collections if collection["id"] == collection_id]
    if not matches:
        available = ", ".join(str(collection["id"]) for collection in collections)
        raise SystemExit(f"Unknown collection {collection_id}. Available: {available}")
    return matches


def download(args: argparse.Namespace) -> int:
    library_root = Path(args.library_root).expanduser()
    catalog = load_catalog(library_root)
    failures_path = library_root / "failures.jsonl"
    failures_path.unlink(missing_ok=True)
    successes = 0
    failures = 0

    for collection_summary in selected_collections(catalog, args.collection, args.all):
        collection = load_collection(library_root, str(collection_summary["manifest"]))
        manifest_path = library_root / str(collection_summary["manifest"])
        for artwork in collection["artworks"]:
            wallpaper = artwork["images"]["wallpaper"]
            destination = library_root / str(wallpaper["localPath"])
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
            time.sleep(float(args.delay))

    print(f"Download pass complete: {successes} successes, {failures} failures")
    return 1 if failures > 0 else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openartpaper-data")
    subcommands = parser.add_subparsers(dest="command", required=True)

    import_parser = subcommands.add_parser("import-metadata")
    import_parser.add_argument("--artpaper-app", default="/Applications/Artpaper.app")
    import_parser.add_argument("--library-root", default=str(default_library_root()))
    import_parser.set_defaults(func=import_metadata)

    download_parser = subcommands.add_parser("download")
    download_parser.add_argument("--library-root", default=str(default_library_root()))
    download_parser.add_argument("--collection")
    download_parser.add_argument("--all", action="store_true")
    download_parser.add_argument("--delay", type=float, default=1.0)
    download_parser.set_defaults(func=download)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
