import functools
import json
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from veduta_data.artwork_kinds import classify_artwork_kind
from veduta_data.models import SourceCollection, SourceLibrary

IMAGE_SUFFIXES = ["s0", "s8192", "s6000", "s5120", "s4096"]

# IIIF hosts get a ladder of size fallbacks; the rest are direct-download URLs.
IIIF_SIZE_FALLBACKS = {
    "https://www.artic.edu/iiif/2/": ["4096,", "3400,", "3000,", "2500,", "1600,", "1200,", "843,"],
    "https://api.nga.gov/iiif/": ["4096,", "3400,", "3000,", "2500,", "1600,", "1200,"],
    "https://ids.lib.harvard.edu/ids/iiif/": ["3400,", "3000,", "2500,", "1600,", "1200,"],
    "https://framemark.vam.ac.uk/collections/": ["4096,", "3400,", "3000,", "2500,", "1600,", "1200,"],
    "https://images.collections.yale.edu/iiif/2/": ["!4096,4096", "3400,", "3000,", "2500,", "1600,", "1200,"],
    "https://media.getty.edu/iiif/image/": ["4096,", "3400,", "3000,", "2500,", "1600,", "1200,"],
}
PASSTHROUGH_PREFIXES = (
    "https://ids.si.edu/ids/download",
    "https://images.metmuseum.org/",
    "https://openaccess-cdn.clevelandart.org/",
)

# Curated per-collection cover images (the museum's signature work), kept in
# the repo so regenerating the catalog re-applies them. Maps collection id ->
# library-relative image path.
COVERS_PATH = Path(__file__).resolve().parents[2] / "covers.json"


@functools.lru_cache(maxsize=1)
def collection_covers() -> dict[str, str]:
    try:
        return json.loads(COVERS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def candidate_image_urls(image_base: str) -> list[str]:
    if "|" in image_base:
        return [url for url in image_base.split("|") if url]
    for prefix, sizes in IIIF_SIZE_FALLBACKS.items():
        if image_base.startswith(prefix):
            return [
                re.sub(r"/full/[^/]+/0/default\.jpg$", f"/full/{size}/0/default.jpg", image_base)
                for size in sizes
            ]
    if image_base.startswith(PASSTHROUGH_PREFIXES):
        return [image_base]
    clean_base = image_base.split("=")[0]
    return [f"{clean_base}={suffix}" for suffix in IMAGE_SUFFIXES]


def atomic_write(path: Path, write) -> None:
    """Write via a sibling tempfile + rename; `write` receives the open binary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            write(temp_file)

        temp_path.replace(path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def write_json(path: Path, value: object) -> None:
    json_text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    atomic_write(path, lambda temp_file: temp_file.write(json_text.encode("utf-8")))


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


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collection_summary(collection: SourceCollection) -> dict[str, object]:
    summary: dict[str, object] = {
        "id": collection.id,
        "title": collection.title,
        "shortName": collection.short_name,
        "sourcePackId": collection.source_pack_id,
        "artworkCount": len(collection.artworks),
        "expectedArtworkCount": collection.expected_artwork_count,
        "manifest": f"collections/{collection.id}.json",
    }
    cover = collection_covers().get(collection.id)
    if cover:
        summary["cover"] = cover
    return summary


def collection_manifest(collection: SourceCollection, generated_at: str) -> dict[str, object]:
    artworks = []
    for artwork in collection.artworks:
        local_path = f"images/{collection.id}/{artwork.id}.jpg"
        artwork_manifest = {
            "id": artwork.id,
            "title": artwork.title,
            "creator": artwork.creator,
            "attribution": artwork.attribution,
            "sources": {
                "canonicalPage": artwork.canonical_page,
                "artistPage": artwork.artist_page,
                "upstreamImageBase": artwork.upstream_image_base,
            },
            "rights": {
                "work": "public-domain",
                "reproduction": "faithful-reproduction",
                "creditLine": f"{artwork.attribution} via Google Arts & Culture",
            },
            "classification": {
                "kind": classify_artwork_kind(collection.id, artwork.title, artwork.creator, artwork.metadata, artwork.id),
            },
            "images": {
                "wallpaper": {
                    "localPath": local_path,
                    "fallbackUrls": candidate_image_urls(artwork.upstream_image_base),
                }
            },
            "source": {
                "artpaperPackId": artwork.source_pack_id,
                "artpaperIndex": artwork.source_index,
            },
        }
        if artwork.metadata:
            artwork_manifest["details"] = artwork.metadata
        artworks.append(artwork_manifest)

    return {
        "schemaVersion": 1,
        "id": collection.id,
        "title": collection.title,
        "shortName": collection.short_name,
        "generatedAt": generated_at,
        "source": {
            "type": "artpaper-bundle",
            "packId": collection.source_pack_id,
            "reportedSizesMb": collection.source_sizes_mb,
        },
        "artworks": artworks,
    }


def write_metadata_library(library: SourceLibrary, library_root: Path) -> None:
    generated_at = now_iso()
    collection_summaries: list[dict[str, object]] = []

    for collection in library.collections:
        manifest_path = f"collections/{collection.id}.json"
        collection_summaries.append(collection_summary(collection))
        write_json(library_root / manifest_path, collection_manifest(collection, generated_at))

    write_json(library_root / "catalog.json", {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "collections": collection_summaries,
    })


def upsert_metadata_collections(library: SourceLibrary, library_root: Path) -> None:
    generated_at = now_iso()
    catalog_path = library_root / "catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        collection_summaries = list(catalog.get("collections") or [])
    else:
        catalog = {"schemaVersion": 1}
        collection_summaries = []

    by_id = {str(summary["id"]): index for index, summary in enumerate(collection_summaries)}
    for collection in library.collections:
        summary = collection_summary(collection)
        existing_index = by_id.get(collection.id)
        if existing_index is None:
            by_id[collection.id] = len(collection_summaries)
            collection_summaries.append(summary)
        else:
            collection_summaries[existing_index] = summary
        write_json(library_root / str(summary["manifest"]), collection_manifest(collection, generated_at))

    catalog["schemaVersion"] = int(catalog.get("schemaVersion") or 1)
    catalog["generatedAt"] = generated_at
    catalog["collections"] = collection_summaries
    write_json(catalog_path, catalog)


def update_wallpaper_metadata(collection_manifest_path: Path, artwork_id: str, metadata: dict[str, object]) -> None:
    collection = json.loads(collection_manifest_path.read_text(encoding="utf-8"))
    updated = False
    for artwork in collection["artworks"]:
        if artwork["id"] == artwork_id:
            wallpaper = artwork["images"]["wallpaper"]
            for key, value in metadata.items():
                if value is None:
                    wallpaper.pop(key, None)
                else:
                    wallpaper[key] = value
            updated = True
            break
    if not updated:
        raise KeyError(f"Artwork {artwork_id} not found in {collection_manifest_path}")
    write_json(collection_manifest_path, collection)
