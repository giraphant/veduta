import json
import urllib.request
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from veduta_data.artpaper_import import int_value, short_slug, unique_artwork_id
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary, orientation_score, usable_dimensions

YCBA_COLLECTION_ID = "ycba"
YCBA_PACK_ID = 1008
YCBA_TITLE = "Yale Center for British Art"
YCBA_MANIFEST_BASE = "https://manifests.collections.yale.edu/ycba/obj"
USER_AGENT = "Veduta/0.1 (ycba-import; local user)"

FAMOUS_CREATORS = {
    "bonington",
    "canaletto",
    "constable",
    "gainsborough",
    "homer",
    "lear",
    "romney",
    "sandby",
    "stubbs",
    "turner",
    "wilson",
}
FAMOUS_TITLE_WORDS = {
    "bridge",
    "castle",
    "coast",
    "dordrecht",
    "forest",
    "landscape",
    "river",
    "sea",
    "shore",
    "thames",
    "view",
    "westminster",
}


def fetch_ycba_records(fetch_limit: int, *, workers: int = 16) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for record in executor.map(fetch_ycba_manifest, range(1, fetch_limit + 1)):
            if record is not None:
                records.append(record)
    return records


def fetch_ycba_manifest(object_id: int) -> dict[str, Any] | None:
    url = f"{YCBA_MANIFEST_BASE}/{object_id}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            return json.loads(response.read())
    except Exception:
        return None


def import_ycba_api(*, fetch_limit: int, keep_limit: int, min_long_edge: int = 2500) -> SourceLibrary:
    return import_ycba_records(fetch_ycba_records(fetch_limit), limit=keep_limit, min_long_edge=min_long_edge)


def import_ycba_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 2500,
) -> SourceLibrary:
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_ycba_record, reverse=True)

    used_ids: set[str] = set()
    artworks: list[SourceArtwork] = []
    for record in candidates:
        if len(artworks) >= limit:
            break
        metadata = _metadata(record)
        title = str(metadata.get("title") or _label(record) or "Untitled")
        creator = str(metadata.get("creator") or "Unknown artist")
        artwork_id = unique_artwork_id(short_slug(f"{creator} {title}"), used_ids)
        object_id = _object_id(record)
        image_base = _image_service(_best_canvas(record))
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=YCBA_TITLE,
            canonical_page=str(metadata.get("canonicalPage") or f"https://collections.britishart.yale.edu/catalog/tms:{object_id}"),
            artist_page=None,
            upstream_image_base=f"{image_base}/full/3400,/0/default.jpg",
            source_pack_id=YCBA_PACK_ID,
            source_index=len(artworks),
            metadata=metadata,
        ))

    return SourceLibrary(collections=[
        SourceCollection(
            id=YCBA_COLLECTION_ID,
            source_pack_id=YCBA_PACK_ID,
            short_name="YCBA",
            title=YCBA_TITLE,
            expected_artwork_count=len(artworks),
            source_sizes_mb={},
            artworks=artworks,
        )
    ])


def score_ycba_record(record: dict[str, Any]) -> float:
    canvas = _best_canvas(record)
    width = int_value(canvas.get("width"))
    height = int_value(canvas.get("height"))
    short_edge = min(width, height)
    metadata = _metadata(record)
    creator = str(metadata.get("creator") or "").lower()
    title = str(metadata.get("title") or "").lower()
    medium = str(metadata.get("medium") or "").lower()
    score = max(width, height) / 1000
    score += orientation_score(width, height, 1.2, 2.2)

    if any(name in creator for name in FAMOUS_CREATORS):
        score += 8
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 4
    if "oil" in medium or "watercolor" in medium or "watercolour" in medium:
        score += 2
    if metadata.get("description"):
        score += 2
    if short_edge >= 2500:
        score += 2
    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    metadata = _metadata(record)
    if str(metadata.get("copyright") or "").lower() != "public domain":
        return False
    if not metadata.get("title") or not metadata.get("creator") or not metadata.get("medium"):
        return False
    canvas = _best_canvas(record)
    image_base = _image_service(canvas)
    if not image_base:
        return False
    return usable_dimensions(int_value(canvas.get("width")), int_value(canvas.get("height")), min_long_edge)


def _metadata(record: dict[str, Any]) -> dict[str, object]:
    values = _metadata_values(record)
    homepage = record.get("homepage") or []
    canonical_page = ""
    if isinstance(homepage, list) and homepage and isinstance(homepage[0], dict):
        canonical_page = str(homepage[0].get("id") or "")
    description = _description(record)
    metadata: dict[str, object] = {
        "manifest": record.get("id"),
        "canonicalPage": canonical_page,
        "copyright": values.get("Copyright Statement"),
        "creator": values.get("Creator"),
        "title": values.get("Title"),
        "date": values.get("Date") or _date_from_label(record, values.get("Title") or ""),
        "medium": values.get("Medium"),
        "dimensions": values.get("Physical Description"),
        "creditLine": values.get("Credit Line"),
        "collection": values.get("Collection"),
        "callNumber": values.get("Call Number"),
    }
    if description:
        metadata["description"] = description
    return {key: value for key, value in metadata.items() if value}


def _metadata_values(record: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in record.get("metadata") or []:
        if not isinstance(item, dict):
            continue
        label = _language_value(item.get("label"))
        value = _language_value(item.get("value"))
        if label and value:
            values[label] = value
    return values


def _description(record: dict[str, Any]) -> str:
    for key in ("summary", "description"):
        value = _language_value(record.get(key))
        if value:
            return value
    return ""


def _date_from_label(record: dict[str, str], title: str) -> str:
    label = _label(record)
    if not label or not title or title not in label:
        return ""
    tail = label.rsplit(title, 1)[-1].strip(" ,")
    if tail and len(tail) <= 40:
        return tail
    return ""


def _best_canvas(record: dict[str, Any]) -> dict[str, Any]:
    best: dict[str, Any] = {}
    for canvas in record.get("items") or []:
        if not isinstance(canvas, dict):
            continue
        if _is_non_display_canvas(canvas):
            continue
        if (
            _canvas_priority(canvas),
            int_value(canvas.get("width")),
        ) > (
            _canvas_priority(best),
            int_value(best.get("width")),
        ):
            best = canvas
    return best


def _is_non_display_canvas(canvas: dict[str, Any]) -> bool:
    label = _language_value(canvas.get("label")).lower()
    return "x-radiograph" in label or "xray" in label or "x-ray" in label or label.startswith("verso")


def _canvas_priority(canvas: dict[str, Any]) -> int:
    label = _language_value(canvas.get("label")).lower()
    if "recto" in label and "cropped to image" in label:
        return 4
    if "recto" in label and "unframed" in label:
        return 3
    if "recto" in label and "framed" in label:
        return 2
    if "recto" in label:
        return 1
    return 0


def _image_service(canvas: dict[str, Any]) -> str:
    for page in canvas.get("items") or []:
        for annotation in page.get("items") or []:
            body = annotation.get("body") or {}
            services = body.get("service") or []
            for service in services:
                if isinstance(service, dict):
                    value = str(service.get("@id") or service.get("id") or "").rstrip("/")
                    if value:
                        return value
    return ""


def _label(record: dict[str, Any]) -> str:
    return _language_value(record.get("label"))


def _language_value(value: object) -> str:
    if isinstance(value, dict):
        values = value.get("en")
        if isinstance(values, list):
            return " ".join(str(item).strip() for item in values if str(item).strip())
    if isinstance(value, list):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def _object_id(record: dict[str, Any]) -> str:
    return str(record.get("id") or "").rstrip("/").rsplit("/", 1)[-1]
