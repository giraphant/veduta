import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_value.lower()
    replaced = re.sub(r"[^a-z0-9]+", "-", lowered)
    return replaced.strip("-") or "untitled"


def https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
    return urlunparse(parsed)


def google_arts_page(link: str) -> str:
    cleaned = link.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return https_url(cleaned)
    cleaned = cleaned.lstrip("/")
    if cleaned.startswith("asset-viewer/"):
        cleaned = f"asset/{cleaned.removeprefix('asset-viewer/')}"
    return f"https://artsandculture.google.com/{cleaned}"


def unique_artwork_id(base: str, used: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def import_artpaper_bundle(app_path: Path) -> SourceLibrary:
    resources = app_path / "Contents" / "Resources"
    packages_path = resources / "packages.json"
    packages = json.loads(packages_path.read_text(encoding="utf-8"))

    collections: list[SourceCollection] = []
    for package in packages:
        pack_id = int(package["id"])
        short_name = str(package.get("short_name") or package["name"])
        collection_id = slugify(short_name)
        artwork_path = resources / f"{pack_id}.json"
        raw_artworks = json.loads(artwork_path.read_text(encoding="utf-8"))

        used_ids: set[str] = set()
        artworks: list[SourceArtwork] = []
        for index, raw in enumerate(raw_artworks):
            title = str(raw.get("title") or "Untitled")
            creator = str(raw.get("creator") or "Unknown artist")
            artwork_id = unique_artwork_id(slugify(f"{creator} {title}"), used_ids)
            image_base = https_url(str(raw["image"]).split("=")[0])
            artworks.append(SourceArtwork(
                id=artwork_id,
                title=title,
                creator=creator,
                attribution=str(raw.get("attribution") or "Unknown collection"),
                canonical_page=google_arts_page(str(raw.get("gap") or raw.get("link") or "")),
                artist_page=str(raw.get("artist_link") or "") or None,
                upstream_image_base=image_base,
                source_pack_id=pack_id,
                source_index=index,
            ))

        collections.append(SourceCollection(
            id=collection_id,
            source_pack_id=pack_id,
            short_name=short_name,
            title=str(package["name"]),
            expected_artwork_count=int(package.get("objects") or len(artworks)),
            expected_author_count=int(package.get("authors") or 0),
            source_sizes_mb={key: int(value) for key, value in dict(package.get("sizes") or {}).items()},
            artworks=artworks,
        ))

    return SourceLibrary(collections=collections)
