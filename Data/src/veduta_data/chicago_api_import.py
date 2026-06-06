import json
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import slugify, unique_artwork_id
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary

CHICAGO_COLLECTION_ID = "chicago"
CHICAGO_PACK_ID = 1002
CHICAGO_TITLE = "The Art Institute of Chicago"
CHICAGO_ATTRIBUTION = "The Art Institute of Chicago"
CHICAGO_API_URL = "https://api.artic.edu/api/v1/artworks/search"
CHICAGO_IIIF_URL = "https://www.artic.edu/iiif/2"
CHICAGO_IMAGE_WIDTH = 4096
USER_AGENT = "Veduta/0.1 (chicago-api-import; local user)"

FAMOUS_CREATORS = {
    "bellows",
    "bonnard",
    "botticelli",
    "cassatt",
    "cezanne",
    "degas",
    "el greco",
    "gauguin",
    "homer",
    "kandinsky",
    "manet",
    "matisse",
    "monet",
    "picasso",
    "pissarro",
    "renoir",
    "seurat",
    "toulouse-lautrec",
    "turner",
    "van gogh",
    "whistler",
}
FAMOUS_TITLE_WORDS = {
    "bathers",
    "bay",
    "bedroom",
    "garden",
    "harbor",
    "landscape",
    "marseille",
    "mountain",
    "normandy train",
    "paris",
    "river",
    "saint-lazare",
    "seascape",
    "sunday",
    "view",
}


def fetch_chicago_api_records(limit: int, *, page_size: int = 100) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page = 1
    while len(records) < limit:
        current_limit = min(page_size, limit - len(records))
        params = {
            "query[bool][must][0][term][is_public_domain]": "true",
            "query[bool][must][1][exists][field]": "image_id",
            "limit": str(current_limit),
            "page": str(page),
            "fields": ",".join([
                "id",
                "title",
                "artist_title",
                "artist_display",
                "image_id",
                "is_public_domain",
                "artwork_type_title",
                "classification_title",
                "date_display",
                "place_of_origin",
                "department_title",
                "api_link",
                "thumbnail",
                "publication_history",
                "exhibition_history",
            ]),
            "sort[0][is_boosted]": "desc",
        }
        url = CHICAGO_API_URL + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        batch = list(payload.get("data") or [])
        if not batch:
            break
        records.extend(batch)
        page += 1
    return records


def import_chicago_api_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 3000,
) -> SourceLibrary:
    used_ids: set[str] = set()
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_chicago_api_record, reverse=True)

    artworks: list[SourceArtwork] = []
    for record in candidates:
        if len(artworks) >= limit:
            break
        title = str(record.get("title") or "Untitled")
        creator = _creator_name(record)
        artwork_id = slugify(f"{creator} {title}")
        if artwork_id in used_ids:
            continue
        used_ids.add(artwork_id)
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=CHICAGO_ATTRIBUTION,
            canonical_page=f"https://www.artic.edu/artworks/{record.get('id')}",
            artist_page=None,
            upstream_image_base=_iiif_image_url(str(record.get("image_id"))),
            source_pack_id=CHICAGO_PACK_ID,
            source_index=len(artworks),
        ))

    collection = SourceCollection(
        id=CHICAGO_COLLECTION_ID,
        source_pack_id=CHICAGO_PACK_ID,
        short_name="Chicago",
        title=CHICAGO_TITLE,
        expected_artwork_count=len(artworks),
        expected_author_count=len({artwork.creator for artwork in artworks}),
        source_sizes_mb={},
        artworks=artworks,
    )
    return SourceLibrary(collections=[collection])


def import_chicago_api(*, fetch_limit: int, keep_limit: int, min_long_edge: int = 3000) -> SourceLibrary:
    records = fetch_chicago_api_records(fetch_limit)
    return import_chicago_api_records(records, limit=keep_limit, min_long_edge=min_long_edge)


def score_chicago_api_record(record: dict[str, Any]) -> float:
    width, height = _dimensions(record)
    long_edge = max(width, height)
    short_edge = min(width, height)
    ratio = width / max(height, 1)
    score = long_edge / 1000

    if width > height:
        score += 8
        if 1.2 <= ratio <= 2.0:
            score += 4
    else:
        score -= 4

    creator = _creator_name(record).lower()
    title = str(record.get("title") or "").lower()
    if any(name in creator for name in FAMOUS_CREATORS):
        score += 8
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 4

    publication_history = str(record.get("publication_history") or "")
    exhibition_history = str(record.get("exhibition_history") or "")
    score += min(publication_history.lower().count("reproduced") + publication_history.lower().count("catalogue"), 6) * 1.5
    score += min(len([line for line in exhibition_history.splitlines() if line.strip()]), 8) * 0.6
    if len(publication_history) > 500:
        score += 3
    if len(exhibition_history) > 300:
        score += 2

    if short_edge >= 2500:
        score += 2

    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    if record.get("is_public_domain") is not True:
        return False
    if not record.get("image_id"):
        return False
    width, height = _dimensions(record)
    if max(width, height) < min_long_edge:
        return False
    if width <= height:
        return False
    ratio = width / max(height, 1)
    return 1.15 <= ratio <= 3.0


def _dimensions(record: dict[str, Any]) -> tuple[int, int]:
    thumbnail = record.get("thumbnail") or {}
    if not isinstance(thumbnail, dict):
        return 0, 0
    return _int_value(thumbnail.get("width")), _int_value(thumbnail.get("height"))


def _creator_name(record: dict[str, Any]) -> str:
    value = str(record.get("artist_title") or "").strip()
    if value:
        return value
    display = str(record.get("artist_display") or "").strip()
    if display:
        return display.split("\n", 1)[0].split("(", 1)[0].strip() or display
    return "Unknown artist"


def _iiif_image_url(image_id: str) -> str:
    return f"{CHICAGO_IIIF_URL}/{image_id}/full/{CHICAGO_IMAGE_WIDTH},/0/default.jpg"


def _int_value(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0
