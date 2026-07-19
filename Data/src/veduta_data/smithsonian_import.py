import json
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import short_slug
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary, orientation_score, usable_dimensions

SMITHSONIAN_COLLECTION_ID = "smithsonian"
SMITHSONIAN_PACK_ID = 1006
SMITHSONIAN_TITLE = "Smithsonian American Art Museum"
USER_AGENT = "Veduta/0.1 (smithsonian-import; local user)"
S3_BASE = "https://smithsonian-open-access.s3.amazonaws.com/metadata/edan/saam"
S3_FILE_COUNT = 256  # files 00.txt through ff.txt

FAMOUS_CREATORS = {
    "benton",
    "bierstadt",
    "cassatt",
    "church",
    "cole",
    "coles",
    "demuth",
    "eakins",
    "hassam",
    "heade",
    "homer",
    "hopper",
    "inness",
    "lawrence",
    "marin",
    "moran",
    "o'keeffe",
    "okeeffe",
    "remington",
    "ritman",
    "sargent",
    "twachtman",
    "whistler",
}
FAMOUS_TITLE_WORDS = {
    "bay",
    "bridge",
    "coast",
    "garden",
    "harbor",
    "landscape",
    "mountain",
    "river",
    "seascape",
    "shore",
    "sunlight",
    "sunset",
    "trees",
    "view",
    "water",
    "winter",
}


def fetch_smithsonian_records(
    *,
    fetch_limit: int,
    max_files: int = S3_FILE_COUNT,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for file_index in range(min(max_files, S3_FILE_COUNT)):
        if len(records) >= fetch_limit:
            break
        hex_prefix = f"{file_index:02x}"
        url = f"{S3_BASE}/{hex_prefix}.txt"
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                for line in response:
                    if len(records) >= fetch_limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    content = record.get("content", {})
                    idx = content.get("indexedStructured", {})
                    obj_types = idx.get("object_type", [])
                    if any("painting" in str(ot).lower() for ot in obj_types):
                        records.append(record)
        except Exception:
            continue
    return records[:fetch_limit]


def import_smithsonian_api(
    *,
    fetch_limit: int,
    keep_limit: int,
    min_long_edge: int = 3000,
    max_files: int = S3_FILE_COUNT,
) -> SourceLibrary:
    records = fetch_smithsonian_records(fetch_limit=fetch_limit, max_files=max_files)
    return import_smithsonian_records(records, limit=keep_limit, min_long_edge=min_long_edge)


def import_smithsonian_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 3000,
) -> SourceLibrary:
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_smithsonian_record, reverse=True)

    used_ids: set[str] = set()
    artworks: list[SourceArtwork] = []
    for record in candidates:
        if len(artworks) >= limit:
            break
        title = _title(record)
        creator = _creator_name(record)
        artwork_id = short_slug(f"{creator} {title}")
        if artwork_id in used_ids:
            continue
        used_ids.add(artwork_id)
        image_resource = _best_image_resource(record)
        dnr = record.get("content", {}).get("descriptiveNonRepeating", {})
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=SMITHSONIAN_TITLE,
            canonical_page=str(dnr.get("record_link") or f"https://americanart.si.edu/collections/search/artwork/?id={dnr.get('record_ID', '')}"),
            artist_page=None,
            upstream_image_base=image_resource["url"],
            source_pack_id=SMITHSONIAN_PACK_ID,
            source_index=len(artworks),
        ))

    return SourceLibrary(collections=[
        SourceCollection(
            id=SMITHSONIAN_COLLECTION_ID,
            source_pack_id=SMITHSONIAN_PACK_ID,
            short_name="Smithsonian",
            title=SMITHSONIAN_TITLE,
            expected_artwork_count=len(artworks),
            source_sizes_mb={},
            artworks=artworks,
        )
    ])


def score_smithsonian_record(record: dict[str, Any]) -> float:
    image_resource = _best_image_resource(record)
    width = image_resource.get("width", 0)
    height = image_resource.get("height", 0)
    long_edge = max(width, height)
    short_edge = min(width, height)
    creator = _creator_name(record).lower()
    title = _title(record).lower()
    medium = _medium(record).lower()
    score = long_edge / 1000
    score += orientation_score(width, height)

    if any(name in creator for name in FAMOUS_CREATORS):
        score += 8
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 4
    if "oil" in medium or "paint" in medium:
        score += 3

    # Bonus for landscape topics
    idx = record.get("content", {}).get("indexedStructured", {})
    topics = {str(t).lower() for t in idx.get("topic", [])}
    landscape_topics = {"landscapes", "rivers", "mountains", "seascapes", "water", "trees", "beaches"}
    if topics & landscape_topics:
        score += 3

    # Bonus for "Painting and Sculpture" department
    freetext = record.get("content", {}).get("freetext", {})
    set_names = [str(s.get("content", "")).lower() for s in freetext.get("setName", []) if isinstance(s, dict)]
    if any("painting and sculpture" in s for s in set_names):
        score += 2

    if short_edge >= 2500:
        score += 2
    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    # Must be CC0
    dnr = record.get("content", {}).get("descriptiveNonRepeating", {})
    metadata_usage = dnr.get("metadata_usage", {})
    if not isinstance(metadata_usage, dict) or metadata_usage.get("access") != "CC0":
        return False

    # Must have media with CC0 usage
    image_resource = _best_image_resource(record)
    if not image_resource.get("url"):
        return False

    width = image_resource.get("width", 0)
    height = image_resource.get("height", 0)
    if not isinstance(width, int) or not isinstance(height, int):
        return False
    if not usable_dimensions(width, height, min_long_edge):
        return False

    # Must be a painting
    idx = record.get("content", {}).get("indexedStructured", {})
    obj_types = idx.get("object_type", [])
    if not any("painting" in str(ot).lower() for ot in obj_types):
        return False
    return True


def _creator_name(record: dict[str, Any]) -> str:
    freetext = record.get("content", {}).get("freetext", {})
    names = freetext.get("name", [])
    if isinstance(names, list):
        for name_entry in names:
            if not isinstance(name_entry, dict):
                continue
            label = str(name_entry.get("label", "")).lower()
            if "artist" not in label:
                continue
            content = str(name_entry.get("content") or "").strip()
            if content:
                return content
    return "Unknown artist"


def _title(record: dict[str, Any]) -> str:
    dnr = record.get("content", {}).get("descriptiveNonRepeating", {})
    title_obj = dnr.get("title")
    if isinstance(title_obj, dict):
        return str(title_obj.get("content") or record.get("title") or "Untitled")
    return str(record.get("title") or "Untitled")


def _medium(record: dict[str, Any]) -> str:
    freetext = record.get("content", {}).get("freetext", {})
    for desc in freetext.get("physicalDescription", []):
        if isinstance(desc, dict) and desc.get("label") == "Medium":
            return str(desc.get("content") or "")
    return ""


def _best_image_resource(record: dict[str, Any]) -> dict[str, Any]:
    dnr = record.get("content", {}).get("descriptiveNonRepeating", {})
    online_media = dnr.get("online_media", {})
    media_list = online_media.get("media", [])
    if not isinstance(media_list, list):
        return {}

    for media in media_list:
        if not isinstance(media, dict):
            continue
        usage = media.get("usage", {})
        if not isinstance(usage, dict) or usage.get("access") != "CC0":
            continue
        resources = media.get("resources", [])
        if not isinstance(resources, list):
            continue
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            label = str(resource.get("label", "")).lower()
            if "high-resolution jpeg" in label or "high resolution jpeg" in label:
                url = str(resource.get("url") or "")
                if url:
                    return {
                        "url": url,
                        "width": resource.get("width", 0),
                        "height": resource.get("height", 0),
                    }
    return {}
