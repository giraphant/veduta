import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import short_slug
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary

MET_COLLECTION_ID = "met"
MET_PACK_ID = 1003
MET_TITLE = "The Metropolitan Museum of Art"
MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
USER_AGENT = "Veduta/0.1 (met-import; local user)"

DEFAULT_QUERIES = [
    "Van Gogh cypresses",
    "Van Gogh landscape",
    "Turner Venice",
    "Hokusai wave",
    "Washington Crossing Delaware",
    "landscape paintings",
    "Hudson River School",
    "Winslow Homer landscape",
    "John Singer Sargent landscape",
]

FAMOUS_CREATORS = {
    "bierstadt",
    "cassatt",
    "cezanne",
    "church",
    "cole",
    "degas",
    "delacroix",
    "goya",
    "hassam",
    "homer",
    "hokusai",
    "leutze",
    "manet",
    "monet",
    "rembrandt",
    "renoir",
    "sargent",
    "tiepolo",
    "turner",
    "van gogh",
    "vermeer",
    "whistler",
}
FAMOUS_TITLE_WORDS = {
    "cypresses",
    "delaware",
    "garden",
    "great wave",
    "haystacks",
    "landscape",
    "lilies",
    "mountain",
    "river",
    "seascape",
    "venice",
    "view",
    "washington",
    "wave",
    "wheat field",
}
LANDSCAPE_TAGS = {
    "boats",
    "bridges",
    "clouds",
    "gardens",
    "landscapes",
    "mountains",
    "rivers",
    "seascapes",
    "trees",
    "venice",
    "water",
}


def fetch_met_records(
    *,
    queries: Iterable[str] = DEFAULT_QUERIES,
    fetch_limit: int,
    delay_seconds: float = 0.1,
) -> list[dict[str, Any]]:
    object_ids: list[int] = []
    seen_ids: set[int] = set()
    for query in queries:
        if len(object_ids) >= fetch_limit:
            break
        search_url = (
            f"{MET_API_BASE}/search?"
            + urllib.parse.urlencode({"hasImages": "true", "isPublicDomain": "true", "q": query})
        )
        payload = _get_json(search_url)
        for object_id in payload.get("objectIDs") or []:
            object_id = int(object_id)
            if object_id in seen_ids:
                continue
            seen_ids.add(object_id)
            object_ids.append(object_id)
            if len(object_ids) >= fetch_limit:
                break
        time.sleep(delay_seconds)

    records: list[dict[str, Any]] = []
    for object_id in object_ids[:fetch_limit]:
        try:
            records.append(_get_json(f"{MET_API_BASE}/objects/{object_id}"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            pass
        time.sleep(delay_seconds)
    return records


def import_met_api(*, fetch_limit: int, keep_limit: int) -> SourceLibrary:
    return import_met_records(fetch_met_records(fetch_limit=fetch_limit), limit=keep_limit)


def import_met_records(records: Iterable[dict[str, Any]], *, limit: int) -> SourceLibrary:
    candidates = [record for record in records if _is_usable_record(record)]
    candidates.sort(key=score_met_record, reverse=True)

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
        used_ids.add(artwork_id)
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=MET_TITLE,
            canonical_page=str(record.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{record.get('objectID')}"),
            artist_page=None,
            upstream_image_base=_image_candidates(record),
            source_pack_id=MET_PACK_ID,
            source_index=len(artworks),
        ))

    return SourceLibrary(collections=[
        SourceCollection(
            id=MET_COLLECTION_ID,
            source_pack_id=MET_PACK_ID,
            short_name="Met",
            title=MET_TITLE,
            expected_artwork_count=len(artworks),
            source_sizes_mb={},
            artworks=artworks,
        )
    ])


def score_met_record(record: dict[str, Any]) -> float:
    score = 0.0
    creator = _creator_name(record).lower()
    title = str(record.get("title") or "").lower()
    department = str(record.get("department") or "").lower()
    classification = str(record.get("classification") or "").lower()
    medium = str(record.get("medium") or "").lower()
    tag_terms = {str(tag.get("term") or "").lower() for tag in (record.get("tags") or []) if isinstance(tag, dict)}

    if any(name in creator for name in FAMOUS_CREATORS):
        score += 10
    if "van gogh" in creator:
        score += 2
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 5
    if tag_terms & LANDSCAPE_TAGS:
        score += 5
    if "paint" in classification or "painting" in department or "oil" in medium:
        score += 4
    if "european paintings" in department:
        score += 2
    if str(record.get("primaryImage") or "").startswith("https://images.metmuseum.org/"):
        score += 2
    return score


def _is_usable_record(record: dict[str, Any]) -> bool:
    if record.get("isPublicDomain") is not True:
        return False
    if not record.get("primaryImage"):
        return False
    classification = str(record.get("classification") or "").lower()
    medium = str(record.get("medium") or "").lower()
    department = str(record.get("department") or "").lower()
    if not ("paint" in classification or "oil" in medium or "print" in classification):
        return False
    return True


def _creator_name(record: dict[str, Any]) -> str:
    return str(record.get("artistDisplayName") or "Unknown artist").strip() or "Unknown artist"


def _image_candidates(record: dict[str, Any]) -> str:
    urls = [str(record.get("primaryImage") or "")]
    small = str(record.get("primaryImageSmall") or "")
    if small and small not in urls:
        urls.append(small)
    return "|".join(url for url in urls if url)


def _get_json(url: str, *, retries: int = 3) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            last_error = error
            if error.code not in {403, 429, 500, 502, 503, 504} or attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    assert last_error is not None
    raise last_error
