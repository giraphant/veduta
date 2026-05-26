import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from openartpaper_data.models import SourceLibrary

IMAGE_SUFFIXES = ["s0", "s8192", "s6000", "s5120", "s4096"]


def candidate_image_urls(image_base: str) -> list[str]:
    clean_base = image_base.split("=")[0]
    return [f"{clean_base}={suffix}" for suffix in IMAGE_SUFFIXES]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(json_text)

        temp_path.replace(path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_metadata_library(library: SourceLibrary, library_root: Path) -> None:
    generated_at = now_iso()
    collection_summaries: list[dict[str, object]] = []

    for collection in library.collections:
        manifest_path = f"collections/{collection.id}.json"
        collection_summaries.append({
            "id": collection.id,
            "title": collection.title,
            "shortName": collection.short_name,
            "sourcePackId": collection.source_pack_id,
            "artworkCount": len(collection.artworks),
            "expectedArtworkCount": collection.expected_artwork_count,
            "manifest": manifest_path,
        })

        artworks = []
        for artwork in collection.artworks:
            local_path = f"images/{collection.id}/{artwork.id}.jpg"
            artworks.append({
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
            })

        write_json(library_root / manifest_path, {
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
        })

    write_json(library_root / "catalog.json", {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "collections": collection_summaries,
    })
