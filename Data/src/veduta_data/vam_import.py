import json
import re
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import int_value, short_slug, unique_artwork_id
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary, orientation_score, usable_dimensions

VAM_COLLECTION_ID = "vam"
VAM_PACK_ID = 1007
VAM_TITLE = "Victoria and Albert Museum"
VAM_API_URL = "https://api.vam.ac.uk/v2/objects/search"
VAM_IIIF_BASE = "https://framemark.vam.ac.uk/collections"
USER_AGENT = "Veduta/0.1 (vam-import; local user)"

# Kept in sync with the downstream sparse-metadata audit: a work whose resolved
# creator or title lands here is placeholder-only and would be culled after
# import (the V&A "painting" set is ~85% anonymous catalogue entries), leaving an
# empty collection. Rejecting them at the source keeps import and audit aligned.
PLACEHOLDER_CREATORS = {"", "unknown", "unknown artist", "unidentified artist", "anonymous"}

FAMOUS_CREATORS = {
    "beardsley",
    "blake",
    "burne-jones",
    "constable",
    "morris",
    "pugin",
    "rossetti",
    "sargent",
    "turner",
    "whistler",
}
FAMOUS_TITLE_WORDS = {
    "coast",
    "garden",
    "harbor",
    "landscape",
    "mountain",
    "river",
    "sea",
    "seascape",
    "view",
    "water",
}


def fetch_vam_records(
    fetch_limit: int,
    *,
    page_size: int = 100,
    object_type: str = "painting",
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page = 1
    while len(records) < fetch_limit:
        # Always page a full window: we filter most rows out below, so sizing the
        # request to the remaining count would stall once anonymous works dominate.
        params = {
            "q_object_type": object_type,
            "images_exist": "1",
            "page_size": str(page_size),
            "page": str(page),
        }
        url = VAM_API_URL + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        batch = list(payload.get("records") or [])
        if not batch:
            break
        for raw_record in batch:
            if len(records) >= fetch_limit:
                break
            # Cheap gate on the search row before spending two API round-trips
            # (image info + detail) resolving metadata the audit would reject.
            if not _search_record_promising(raw_record):
                continue
            record = dict(raw_record)
            image_id = _image_id(record)
            if image_id:
                record.update(fetch_vam_image_info(image_id))
            system_number = str(record.get("systemNumber") or "")
            if system_number:
                record["_detailRecord"] = fetch_vam_object_record(system_number)
            records.append(record)
        page += 1
    return records


def _search_record_promising(record: dict[str, Any]) -> bool:
    """Pre-filter on the fields a search row already carries, so anonymous or
    untitled works are dropped before the per-record detail/image fetches."""
    maker = record.get("_primaryMaker")
    name = str(maker.get("name") or "").strip() if isinstance(maker, dict) else ""
    if _is_placeholder_creator(name):
        return False
    return not _is_placeholder_title(str(record.get("_primaryTitle") or ""))


def _is_placeholder_creator(creator: str) -> bool:
    return creator.strip().lower() in PLACEHOLDER_CREATORS


def _is_placeholder_title(title: str) -> bool:
    normalized = title.strip().lower()
    return not normalized or normalized.startswith("untitled")


def fetch_vam_image_info(image_id: str) -> dict[str, int]:
    url = f"{VAM_IIIF_BASE}/{urllib.parse.quote(image_id)}/info.json"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())
    return {
        "_imageWidth": int_value(payload.get("width")),
        "_imageHeight": int_value(payload.get("height")),
    }


def fetch_vam_object_record(system_number: str) -> dict[str, Any]:
    url = f"https://api.vam.ac.uk/v2/object/{urllib.parse.quote(system_number)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())
    record = payload.get("record") or {}
    if not isinstance(record, dict):
        return {}
    return record


def import_vam_api(
    *,
    fetch_limit: int,
    keep_limit: int,
    min_long_edge: int = 3840,
    max_per_creator: int | None = None,
) -> SourceLibrary:
    return import_vam_records(
        fetch_vam_records(fetch_limit),
        limit=keep_limit,
        min_long_edge=min_long_edge,
        max_per_creator=max_per_creator,
    )


def import_vam_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 3840,
    max_per_creator: int | None = None,
) -> SourceLibrary:
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_vam_record, reverse=True)

    used_ids: set[str] = set()
    per_creator: dict[str, int] = {}
    artworks: list[SourceArtwork] = []
    for record in candidates:
        if len(artworks) >= limit:
            break
        title = _title(record)
        creator = _creator_name(record)
        # Cap each artist so a single deep series (e.g. one painter's altar-vessel
        # set) can't crowd out the collection's variety.
        if max_per_creator is not None:
            creator_key = creator.strip().lower()
            if per_creator.get(creator_key, 0) >= max_per_creator:
                continue
            per_creator[creator_key] = per_creator.get(creator_key, 0) + 1
        artwork_id = unique_artwork_id(short_slug(f"{creator} {title}"), used_ids)
        system_number = str(record.get("systemNumber") or "")
        image_id = _image_id(record)
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=VAM_TITLE,
            canonical_page=f"https://collections.vam.ac.uk/item/{system_number}/",
            artist_page=None,
            upstream_image_base=_iiif_image_url(image_id),
            source_pack_id=VAM_PACK_ID,
            source_index=len(artworks),
            metadata=_metadata(record),
        ))

    return SourceLibrary(collections=[
        SourceCollection(
            id=VAM_COLLECTION_ID,
            source_pack_id=VAM_PACK_ID,
            short_name="V&A",
            title=VAM_TITLE,
            expected_artwork_count=len(artworks),
            source_sizes_mb={},
            artworks=artworks,
        )
    ])


def score_vam_record(record: dict[str, Any]) -> float:
    width = int_value(record.get("_imageWidth"))
    height = int_value(record.get("_imageHeight"))
    long_edge = max(width, height)
    short_edge = min(width, height)
    score = long_edge / 1000
    score += orientation_score(width, height)

    current_location = record.get("_currentLocation") or {}
    if isinstance(current_location, dict) and current_location.get("onDisplay") is True:
        score += 4

    images = record.get("_images") or {}
    if isinstance(images, dict) and images.get("imageResolution") == "high":
        score += 2

    title = _title(record).lower()
    creator = _creator_name(record).lower()
    if any(name in creator for name in FAMOUS_CREATORS):
        score += 6
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 4

    if short_edge >= 2000:
        score += 2
    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    if not _has_informative_metadata(record):
        return False
    # Backstop after detail/description recovery has run: a work that still
    # resolves to a placeholder creator or title would be culled by the audit.
    if _is_placeholder_creator(_creator_name(record)) or _is_placeholder_title(_title(record)):
        return False
    image_id = _image_id(record)
    if not image_id:
        return False
    images = record.get("_images") or {}
    if isinstance(images, dict) and images.get("imageResolution") not in {"high", None}:
        return False
    if record.get("_warningTypes"):
        return False
    return usable_dimensions(int_value(record.get("_imageWidth")), int_value(record.get("_imageHeight")), min_long_edge)


def _has_informative_metadata(record: dict[str, Any]) -> bool:
    title = _title(record).strip().lower()
    metadata = _metadata(record)
    if not title:
        return False
    return bool(metadata.get("description") or metadata.get("date") or metadata.get("place") or metadata.get("medium"))


def _title(record: dict[str, Any]) -> str:
    title = _detail_title(record) or str(record.get("_primaryTitle") or "").strip()
    if title and not title.lower().startswith("untitled"):
        return title
    description_title = _title_from_description(record)
    if description_title:
        return description_title
    object_type = str(record.get("objectType") or "").strip().lower()
    accession = str(record.get("accessionNumber") or "").strip()
    if object_type and accession:
        return f"Untitled {object_type} ({accession})"
    if object_type:
        return f"Untitled {object_type}"
    return "Untitled"


def _creator_name(record: dict[str, Any]) -> str:
    detail = _detail_record(record)
    for key in ("artistMakerPerson", "artistMakerPeople"):
        creators = detail.get(key) or []
        if isinstance(creators, list):
            for creator in creators:
                if not isinstance(creator, dict):
                    continue
                name = creator.get("name")
                if isinstance(name, dict):
                    value = str(name.get("text") or "").strip()
                else:
                    value = str(name or "").strip()
                if value and value.lower() != "unknown":
                    return value
    creator_from_description = _creator_from_description(record)
    if creator_from_description:
        return creator_from_description
    maker = record.get("_primaryMaker") or {}
    if isinstance(maker, dict):
        name = str(maker.get("name") or "").strip()
        if name and name.lower() != "unknown":
            return name
    return "Unknown artist"


def _image_id(record: dict[str, Any]) -> str:
    return str(record.get("_primaryImageId") or "").strip()


def _iiif_image_url(image_id: str) -> str:
    return f"{VAM_IIIF_BASE}/{image_id}/full/3400,/0/default.jpg"


def _detail_record(record: dict[str, Any]) -> dict[str, Any]:
    detail = record.get("_detailRecord") or {}
    return detail if isinstance(detail, dict) else {}


def _detail_title(record: dict[str, Any]) -> str:
    detail = _detail_record(record)
    titles = detail.get("titles") or []
    if isinstance(titles, list):
        for title in titles:
            if isinstance(title, dict):
                value = str(title.get("title") or "").strip()
                if value:
                    return value
    return ""


def _title_from_description(record: dict[str, Any]) -> str:
    description = str(_detail_record(record).get("briefDescription") or "").strip()
    if not description:
        description = str(_detail_record(record).get("physicalDescription") or "").strip()
    if not description:
        return ""
    value = re.split(r",\s*(?:ca\.|c\.|\d{4})|\.\s+", description, maxsplit=1)[0].strip()
    value = re.sub(r"^(painting|watercolour|drawing|print)\s*[;,:-]\s*", "", value, flags=re.IGNORECASE).strip()
    return value[:140].rstrip(" ,;:-")


def _creator_from_description(record: dict[str, Any]) -> str:
    description = str(_detail_record(record).get("briefDescription") or "").strip()
    match = re.search(r"\bby\s+([^().,]+(?:\s+[^().,]+){0,4})\s*(?:\(|$|[.,])", description)
    if not match:
        return ""
    creator = match.group(1).strip()
    if creator.lower() in {"unknown", "unknown artist"}:
        return ""
    return creator


def _metadata(record: dict[str, Any]) -> dict[str, object]:
    detail = _detail_record(record)
    metadata: dict[str, object] = {}
    mappings = {
        "accessionNumber": detail.get("accessionNumber") or record.get("accessionNumber"),
        "objectType": detail.get("objectType") or record.get("objectType"),
        "date": _first_nested_text(detail.get("productionDates"), "date"),
        "place": _first_nested_text(detail.get("placesOfOrigin"), "place"),
        "medium": detail.get("materialsAndTechniques"),
        "description": detail.get("summaryDescription") or detail.get("physicalDescription") or detail.get("briefDescription"),
        "briefDescription": detail.get("briefDescription"),
        "history": detail.get("objectHistory"),
        "categories": _list_text(detail.get("categories")),
        "materials": _list_text(detail.get("materials")),
        "techniques": _list_text(detail.get("techniques")),
    }
    for key, value in mappings.items():
        if value:
            metadata[key] = value
    return metadata


def _first_nested_text(values: object, key: str) -> str:
    if not isinstance(values, list):
        return ""
    for value in values:
        if not isinstance(value, dict):
            continue
        nested = value.get(key)
        if isinstance(nested, dict):
            text = str(nested.get("text") or "").strip()
            if text:
                return text
    return ""


def _list_text(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    texts: list[str] = []
    for value in values:
        if isinstance(value, dict):
            text = str(value.get("text") or "").strip()
            if text:
                texts.append(text)
    return texts
