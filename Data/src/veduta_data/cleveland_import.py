import json
import re
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import int_value, slugify, unique_artwork_id
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary, orientation_score, usable_dimensions

CLEVELAND_COLLECTION_ID = "cleveland"
CLEVELAND_PACK_ID = 1001
CLEVELAND_TITLE = "Cleveland Museum of Art"
CLEVELAND_API_URL = "https://openaccess-api.clevelandart.org/api/artworks/"
CLEVELAND_MAX_FULL_FILESIZE = 180_000_000
USER_AGENT = "Veduta/0.1 (museum-import; local user)"

FAMOUS_TITLE_WORDS = {
    "adoration",
    "annunciation",
    "bathers",
    "garden",
    "harbor",
    "landscape",
    "madonna",
    "mountain",
    "portrait",
    "river",
    "saint",
    "seascape",
    "self-portrait",
    "still life",
    "venice",
    "view",
}
FAMOUS_CREATORS = {
    "bellows",
    "botticelli",
    "canaletto",
    "cassatt",
    "cezanne",
    "church",
    "cole",
    "copley",
    "courbet",
    "degas",
    "eakins",
    "el greco",
    "gauguin",
    "goya",
    "hassam",
    "hopper",
    "kandinsky",
    "monet",
    "munch",
    "picasso",
    "pissarro",
    "rembrandt",
    "renoir",
    "rodin",
    "sargent",
    "tiepolo",
    "turner",
    "van gogh",
    "velazquez",
    "veronese",
    "whistler",
    "winslow homer",
}


def fetch_cleveland_records(
    limit: int,
    *,
    page_size: int = 100,
    query: str | None = None,
    highlights_only: bool = True,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    skip = 0
    while len(records) < limit:
        current_limit = min(page_size, limit - len(records))
        params: dict[str, str] = {
            "has_image": "1",
            "cc0": "1",
            "limit": str(current_limit),
            "skip": str(skip),
        }
        if query:
            params["q"] = query
        if highlights_only:
            params["highlight"] = "1"
        url = CLEVELAND_API_URL + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        batch = list(payload.get("data") or [])
        if not batch:
            break
        records.extend(batch)
        skip += len(batch)
    return records


def import_cleveland_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 3840,
) -> SourceLibrary:
    used_ids: set[str] = set()
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_cleveland_record, reverse=True)

    artworks: list[SourceArtwork] = []
    for index, record in enumerate(candidates[:limit]):
        title = _clean_text(str(record.get("title") or "Untitled"))
        creator = _creator_name(record)
        artwork_id = unique_artwork_id(slugify(f"{creator} {title}"), used_ids)
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=CLEVELAND_TITLE,
            canonical_page=str(record.get("url") or f"https://clevelandart.org/art/{record.get('accession_number') or record.get('id')}"),
            artist_page=None,
            upstream_image_base=_best_image(record)["url"],
            source_pack_id=CLEVELAND_PACK_ID,
            source_index=index,
            metadata=_metadata(record),
        ))

    collection = SourceCollection(
        id=CLEVELAND_COLLECTION_ID,
        source_pack_id=CLEVELAND_PACK_ID,
        short_name="Cleveland",
        title=CLEVELAND_TITLE,
        expected_artwork_count=len(artworks),
        source_sizes_mb={},
        artworks=artworks,
    )
    return SourceLibrary(collections=[collection])


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def import_cleveland_api(
    *,
    fetch_limit: int,
    keep_limit: int,
    min_long_edge: int = 3840,
    highlights_only: bool = True,
) -> SourceLibrary:
    records = fetch_cleveland_records(fetch_limit, highlights_only=highlights_only)
    return import_cleveland_records(records, limit=keep_limit, min_long_edge=min_long_edge)


def score_cleveland_record(record: dict[str, Any]) -> float:
    image = _best_image(record)
    width = int_value(image.get("width"))
    height = int_value(image.get("height"))
    long_edge = max(width, height)
    short_edge = min(width, height)
    score = long_edge / 1000

    score += orientation_score(width, height, 1.25, 2.1)

    if record.get("is_highlight") is True:
        score += 10

    citations = record.get("citations") or []
    score += min(len(citations), 8) * 1.2

    exhibitions = record.get("exhibitions") or {}
    exhibition_count = 0
    if isinstance(exhibitions, dict):
        for value in exhibitions.values():
            if isinstance(value, list):
                exhibition_count += len(value)
    score += min(exhibition_count, 8) * 0.8

    description = str(record.get("description") or "")
    if len(description) > 250:
        score += 2

    title = str(record.get("title") or "").lower()
    creator = _creator_name(record).lower()
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 3
    if any(name in creator for name in FAMOUS_CREATORS):
        score += 5

    if short_edge >= 2500:
        score += 2

    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    if str(record.get("share_license_status") or "").upper() != "CC0":
        return False
    image = _best_image(record)
    if not image.get("url"):
        return False
    return usable_dimensions(int_value(image.get("width")), int_value(image.get("height")), min_long_edge)


def _creator_name(record: dict[str, Any]) -> str:
    creators = record.get("creators") or []
    if creators:
        creator = creators[0]
        if isinstance(creator, dict):
            description = str(creator.get("description") or creator.get("name") or "").strip()
            if description:
                return description.split("(", 1)[0].strip() or description
    return "Unknown artist"


def _best_image(record: dict[str, Any]) -> dict[str, Any]:
    images = record.get("images") or {}
    full = images.get("full")
    if (
        isinstance(full, dict)
        and full.get("url")
        and int_value(full.get("filesize")) <= CLEVELAND_MAX_FULL_FILESIZE
    ):
        return full
    for key in ("print", "web"):
        image = images.get(key)
        if isinstance(image, dict) and image.get("url"):
            return image
    return {}


def _metadata(record: dict[str, Any]) -> dict[str, object]:
    images = record.get("images") or {}
    best = _best_image(record)
    return {
        "accessionNumber": record.get("accession_number"),
        "type": record.get("type"),
        "collection": record.get("collection"),
        "department": record.get("department"),
        "date": record.get("creation_date"),
        "medium": record.get("technique") or record.get("medium"),
        "description": record.get("description"),
        "fullImageFileSize": int_value((images.get("full") or {}).get("filesize")) if isinstance(images.get("full"), dict) else None,
        "selectedImageFileSize": int_value(best.get("filesize")),
    }
