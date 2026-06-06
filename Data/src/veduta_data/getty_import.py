import json
import re
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import slugify, unique_artwork_id
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary

GETTY_COLLECTION_ID = "getty"
GETTY_PACK_ID = 1004
GETTY_TITLE = "J. Paul Getty Museum"
GETTY_ACTIVITY_PAGE_URL = "https://data.getty.edu/museum/collection/activity-stream/page/{page}"
USER_AGENT = "Veduta/0.1 (museum-import; local user)"

FAMOUS_TITLE_WORDS = {
    "architecture",
    "cloud",
    "garden",
    "harbor",
    "landscape",
    "mountain",
    "portrait",
    "river",
    "sea",
    "seascape",
    "still life",
    "view",
}

FAMOUS_CREATORS = {
    "canaletto",
    "cezanne",
    "degas",
    "gauguin",
    "manet",
    "monet",
    "pissarro",
    "rembrandt",
    "renoir",
    "rubens",
    "turner",
    "van gogh",
}


def fetch_getty_records(
    limit: int,
    *,
    start_page: int = 1000,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page = start_page
    while len(records) < limit:
        payload = _fetch_json(GETTY_ACTIVITY_PAGE_URL.format(page=page))
        object_urls = [
            str((item.get("object") or {}).get("id"))
            for item in list(payload.get("orderedItems") or [])
            if (item.get("object") or {}).get("type") == "HumanMadeObject"
        ]
        if not object_urls and not payload.get("next"):
            break
        for url in object_urls:
            if len(records) >= limit:
                break
            records.append(_fetch_json(url))
        page += 1
        if page_size <= 0:
            break
    return records


def import_getty_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 3840,
) -> SourceLibrary:
    used_ids: set[str] = set()
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_getty_record, reverse=True)

    artworks: list[SourceArtwork] = []
    for index, record in enumerate(candidates[:limit]):
        title = _title(record)
        creator = _creator_name(record)
        artwork_id = unique_artwork_id(slugify(f"{creator} {title}"), used_ids)
        image_base = _image_base(record)
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=GETTY_TITLE,
            canonical_page=_canonical_page(record),
            artist_page=None,
            upstream_image_base=f"{image_base}/full/4096,/0/default.jpg",
            source_pack_id=GETTY_PACK_ID,
            source_index=index,
            metadata=_metadata(record),
        ))

    collection = SourceCollection(
        id=GETTY_COLLECTION_ID,
        source_pack_id=GETTY_PACK_ID,
        short_name="Getty",
        title=GETTY_TITLE,
        expected_artwork_count=len(artworks),
        expected_author_count=len({artwork.creator for artwork in artworks}),
        source_sizes_mb={},
        artworks=artworks,
    )
    return SourceLibrary(collections=[collection])


def import_getty_api(
    *,
    fetch_limit: int,
    keep_limit: int,
    min_long_edge: int = 3840,
    start_page: int = 1000,
) -> SourceLibrary:
    records = fetch_getty_records(fetch_limit, start_page=start_page)
    return import_getty_records(records, limit=keep_limit, min_long_edge=min_long_edge)


def score_getty_record(record: dict[str, Any]) -> float:
    width, height = _image_dimensions(record)
    long_edge = max(width, height)
    short_edge = min(width, height)
    score = long_edge / 1000

    if width > height:
        ratio = width / max(height, 1)
        score += 8
        if 1.25 <= ratio <= 2.1:
            score += 4
    else:
        score -= 4

    title = _title(record).lower()
    creator = _creator_name(record).lower()
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 3
    if any(name in creator for name in FAMOUS_CREATORS):
        score += 5
    if short_edge >= 2500:
        score += 2
    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    try:
        width, height = _image_dimensions(record)
    except ValueError:
        return False
    if max(width, height) < min_long_edge:
        return False
    if width <= height:
        return False
    ratio = width / max(height, 1)
    return 1.15 <= ratio <= 3.0


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _title(record: dict[str, Any]) -> str:
    preferred = _identified_content(record, "Preferred Title")
    if preferred:
        return _clean_title(preferred)
    return _clean_title(str(record.get("_label") or "Untitled").split(" (", 1)[0])


def _clean_title(value: str) -> str:
    title = value.strip()
    if title.startswith("[") and title.endswith("]"):
        return title[1:-1].strip()
    return title


def _creator_name(record: dict[str, Any]) -> str:
    production = record.get("produced_by") if isinstance(record.get("produced_by"), dict) else {}
    producer = _referred_content(production, "Artist/Maker (Producer) Name")
    if producer:
        return producer
    label = str(production.get("_label") or "")
    match = re.search(r"by (.+)$", label)
    return match.group(1).strip() if match else "Unknown artist"


def _canonical_page(record: dict[str, Any]) -> str:
    for subject in list(record.get("subject_of") or []):
        if str(subject.get("format") or "") == "text/html":
            return str(subject.get("id"))
    return str(record.get("id"))


def _image_base(record: dict[str, Any]) -> str:
    representations = list(record.get("representation") or [])
    for representation in representations:
        image_url = str(representation.get("id") or "")
        match = re.match(r"^(https://media\.getty\.edu/iiif/image/[^/]+)", image_url)
        if match:
            return match.group(1)
    raise ValueError("Getty record has no IIIF image representation")


def _image_dimensions(record: dict[str, Any]) -> tuple[int, int]:
    dimensions = record.get("_vedutaImageDimensions")
    if isinstance(dimensions, list) and len(dimensions) == 2:
        return int(dimensions[0]), int(dimensions[1])

    image_base = _image_base(record)
    info = _fetch_json(f"{image_base}/info.json")
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    if width <= 0 or height <= 0:
        raise ValueError("Getty image info has no dimensions")
    record["_vedutaImageDimensions"] = [width, height]
    return width, height


def _metadata(record: dict[str, Any]) -> dict[str, object]:
    width, height = _image_dimensions(record)
    accession = _identified_content(record, "Accession Number")
    object_type = _classification_label(record)
    date = _production_date(record)
    metadata: dict[str, object] = {
        "imageWidth": width,
        "imageHeight": height,
    }
    if accession:
        metadata["accessionNumber"] = accession
    if object_type:
        metadata["type"] = object_type
    if date:
        metadata["date"] = date
    return metadata


def _classification_label(record: dict[str, Any]) -> str | None:
    for classification in list(record.get("classified_as") or []):
        if str(classification.get("_label") or "").lower() not in {"artwork", "object record structure: whole"}:
            return str(classification.get("_label"))
    return None


def _production_date(record: dict[str, Any]) -> str | None:
    production = record.get("produced_by") if isinstance(record.get("produced_by"), dict) else {}
    timespan = production.get("timespan") if isinstance(production.get("timespan"), dict) else {}
    for name in list(timespan.get("identified_by") or []):
        content = str(name.get("content") or "").strip()
        if content:
            return content
    return None


def _identified_content(record: dict[str, Any], label: str) -> str | None:
    for value in list(record.get("identified_by") or []):
        if value.get("_label") == label:
            content = str(value.get("content") or "").strip()
            if content:
                return content
    return None


def _referred_content(record: dict[str, Any], label: str) -> str | None:
    for value in list(record.get("referred_to_by") or []):
        if value.get("_label") == label:
            content = str(value.get("content") or "").strip()
            if content:
                return content
    return None
