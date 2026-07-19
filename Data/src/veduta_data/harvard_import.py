import json
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import int_value, short_slug
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary, orientation_score, usable_dimensions

HARVARD_COLLECTION_ID = "harvard"
HARVARD_PACK_ID = 1005
HARVARD_TITLE = "Harvard Art Museums"
HARVARD_API_URL = "https://api.harvardartmuseums.org/object"
HARVARD_IMAGE_WIDTH = 3400
USER_AGENT = "Veduta/0.1 (harvard-import; local user)"

FAMOUS_CREATORS = {
    "bellows",
    "bonnard",
    "botticelli",
    "cassatt",
    "cezanne",
    "degas",
    "gauguin",
    "homer",
    "kandinsky",
    "klee",
    "manet",
    "matisse",
    "monet",
    "picasso",
    "pissarro",
    "rembrandt",
    "renoir",
    "rothko",
    "sargent",
    "seurat",
    "turner",
    "van gogh",
    "vermeer",
    "whistler",
}
FAMOUS_TITLE_WORDS = {
    "bay",
    "bridge",
    "garden",
    "harbor",
    "landscape",
    "mountain",
    "river",
    "seascape",
    "trees",
    "venice",
    "view",
    "water",
    "water lilies",
}


def fetch_harvard_records(
    *,
    api_key: str,
    fetch_limit: int,
    page_size: int = 100,
    delay_seconds: float = 0.1,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page = 1
    while len(records) < fetch_limit:
        current_size = min(page_size, fetch_limit - len(records))
        params = {
            "apikey": api_key,
            "classification": "Paintings",
            "hasimage": "1",
            "q": "imagepermissionlevel:0",
            "size": str(current_size),
            "page": str(page),
            "fields": ",".join([
                "objectid",
                "title",
                "people",
                "primaryimageurl",
                "imagepermissionlevel",
                "images",
                "url",
                "classification",
                "medium",
                "dated",
                "creditline",
                "century",
                "period",
                "culture",
                "department",
                "verificationlevel",
                "publicationcount",
                "exhibitioncount",
                "totalpageviews",
                "groupings",
            ]),
        }
        url = HARVARD_API_URL + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
        batch = list(payload.get("records") or [])
        if not batch:
            break
        records.extend(batch)
        info = payload.get("info") or {}
        if not info.get("next"):
            break
        page += 1
        time.sleep(delay_seconds)
    return records[:fetch_limit]


def import_harvard_api(
    *,
    api_key: str,
    fetch_limit: int,
    keep_limit: int,
    min_long_edge: int = 3000,
) -> SourceLibrary:
    records = fetch_harvard_records(api_key=api_key, fetch_limit=fetch_limit)
    return import_harvard_records(records, limit=keep_limit, min_long_edge=min_long_edge)


def import_harvard_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 3000,
) -> SourceLibrary:
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_harvard_record, reverse=True)

    used_ids: set[str] = set()
    artworks: list[SourceArtwork] = []
    for record in candidates:
        if len(artworks) >= limit:
            break
        title = str(record.get("title") or "Untitled")
        creator = _creator_name(record)
        artwork_id = short_slug(f"{creator} {title}")
        if artwork_id in used_ids:
            continue
        image = _best_image(record)
        used_ids.add(artwork_id)
        object_id = str(record.get("objectid") or "")
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=HARVARD_TITLE,
            canonical_page=str(record.get("url") or f"https://harvardartmuseums.org/collections/object/{object_id}"),
            artist_page=None,
            upstream_image_base=_iiif_image_url(str(image.get("iiifbaseuri") or "")),
            source_pack_id=HARVARD_PACK_ID,
            source_index=len(artworks),
        ))

    return SourceLibrary(collections=[
        SourceCollection(
            id=HARVARD_COLLECTION_ID,
            source_pack_id=HARVARD_PACK_ID,
            short_name="Harvard",
            title=HARVARD_TITLE,
            expected_artwork_count=len(artworks),
            source_sizes_mb={},
            artworks=artworks,
        )
    ])


def score_harvard_record(record: dict[str, Any]) -> float:
    image = _best_image(record)
    width = int_value(image.get("width"))
    height = int_value(image.get("height"))
    long_edge = max(width, height)
    short_edge = min(width, height)
    creator = _creator_name(record).lower()
    title = str(record.get("title") or "").lower()
    medium = str(record.get("medium") or "").lower()
    score = long_edge / 1000
    score += orientation_score(width, height)

    if any(name in creator for name in FAMOUS_CREATORS):
        score += 8
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 4
    if "oil" in medium or "paint" in medium:
        score += 3

    score += min(int_value(record.get("verificationlevel")), 4)
    score += min(int_value(record.get("publicationcount")), 6)
    score += min(int_value(record.get("exhibitioncount")), 6) * 0.5
    score += min(int_value(record.get("totalpageviews")) / 100, 5)
    if short_edge >= 2500:
        score += 2
    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    image_permission = record.get("imagepermissionlevel")
    if image_permission is None or str(image_permission).strip() == "" or int_value(image_permission) != 0:
        return False
    image = _best_image(record)
    if not image.get("iiifbaseuri"):
        return False
    if not usable_dimensions(int_value(image.get("width")), int_value(image.get("height")), min_long_edge):
        return False
    classification = str(record.get("classification") or "").lower()
    medium = str(record.get("medium") or "").lower()
    return "paint" in classification or "oil" in medium


def _creator_name(record: dict[str, Any]) -> str:
    people = record.get("people") or []
    if isinstance(people, list):
        for person in people:
            if not isinstance(person, dict):
                continue
            role = str(person.get("role") or "").lower()
            if role and "artist" not in role:
                continue
            name = str(person.get("displayname") or person.get("name") or "").strip()
            if name:
                return name
        for person in people:
            if isinstance(person, dict):
                name = str(person.get("displayname") or person.get("name") or "").strip()
                if name:
                    return name
    return "Unknown artist"


def _best_image(record: dict[str, Any]) -> dict[str, Any]:
    images = record.get("images") or []
    if not isinstance(images, list):
        return {}
    usable = [image for image in images if isinstance(image, dict) and image.get("iiifbaseuri")]
    if not usable:
        return {}
    primary = [image for image in usable if int_value(image.get("displayorder")) == 1]
    if primary:
        return primary[0]
    return max(usable, key=lambda image: int_value(image.get("width")) * int_value(image.get("height")))


def _iiif_image_url(iiifbaseuri: str) -> str:
    return f"{iiifbaseuri.rstrip('/')}/full/{HARVARD_IMAGE_WIDTH},/0/default.jpg"
