import csv
import io
import json
import urllib.request
from collections.abc import Iterable
from typing import Any

from veduta_data.artpaper_import import int_value, short_slug
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary, orientation_score, usable_dimensions

NGA_COLLECTION_ID = "nga"
NGA_PACK_ID = 1004
NGA_TITLE = "National Gallery of Art"
USER_AGENT = "Veduta/0.1 (nga-import; local user)"
OPEN_DATA_BASE = "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data"

FAMOUS_CREATORS = {
    "bellows",
    "bierstadt",
    "cassatt",
    "cezanne",
    "church",
    "cole",
    "constable",
    "degas",
    "delacroix",
    "goya",
    "homer",
    "hopper",
    "manet",
    "monet",
    "pissarro",
    "rembrandt",
    "renoir",
    "sargent",
    "turner",
    "van gogh",
    "vermeer",
    "whistler",
}
FAMOUS_TITLE_WORDS = {
    "bridge",
    "breezing up",
    "garden",
    "harbor",
    "landscape",
    "mountain",
    "river",
    "seascape",
    "view",
    "water lilies",
}


def fetch_nga_records(fetch_limit: int) -> list[dict[str, str]]:
    objects = _fetch_csv("objects.csv")
    images = _fetch_csv("published_images.csv")

    image_by_object: dict[str, dict[str, str]] = {}
    for image in images:
        if image.get("openaccess") != "1" or image.get("viewtype") != "primary" or not image.get("iiifurl"):
            continue
        object_id = str(image.get("depictstmsobjectid") or "")
        if object_id and object_id not in image_by_object:
            image_by_object[object_id] = image

    records: list[dict[str, str]] = []
    for obj in objects:
        image = image_by_object.get(str(obj.get("objectid") or ""))
        if image is None:
            continue
        record = dict(obj)
        record.update({
            "openaccess": image.get("openaccess", ""),
            "iiifurl": image.get("iiifurl", ""),
            "width": image.get("width", ""),
            "height": image.get("height", ""),
        })
        records.append(record)
        if len(records) >= fetch_limit:
            break
    return records


def import_nga_api(*, fetch_limit: int, keep_limit: int, min_long_edge: int = 3000) -> SourceLibrary:
    return import_nga_records(fetch_nga_records(fetch_limit), limit=keep_limit, min_long_edge=min_long_edge)


def import_nga_records(
    records: Iterable[dict[str, Any]],
    *,
    limit: int,
    min_long_edge: int = 3000,
) -> SourceLibrary:
    candidates = [record for record in records if _is_usable_record(record, min_long_edge=min_long_edge)]
    candidates.sort(key=score_nga_record, reverse=True)

    used_ids: set[str] = set()
    artworks: list[SourceArtwork] = []
    for record in candidates:
        if len(artworks) >= limit:
            break
        title = str(record.get("title") or "Untitled")
        creator = str(record.get("attribution") or "Unknown artist").strip() or "Unknown artist"
        artwork_id = short_slug(f"{creator} {title}")
        if artwork_id in used_ids:
            continue
        used_ids.add(artwork_id)
        object_id = str(record.get("objectid") or "")
        artworks.append(SourceArtwork(
            id=artwork_id,
            title=title,
            creator=creator,
            attribution=NGA_TITLE,
            canonical_page=f"https://www.nga.gov/collection/art-object-page.{object_id}.html",
            artist_page=None,
            upstream_image_base=f"{str(record.get('iiifurl')).rstrip('/')}/full/3400,/0/default.jpg",
            source_pack_id=NGA_PACK_ID,
            source_index=len(artworks),
        ))

    return SourceLibrary(collections=[
        SourceCollection(
            id=NGA_COLLECTION_ID,
            source_pack_id=NGA_PACK_ID,
            short_name="NGA",
            title=NGA_TITLE,
            expected_artwork_count=len(artworks),
            source_sizes_mb={},
            artworks=artworks,
        )
    ])


def score_nga_record(record: dict[str, Any]) -> float:
    width = int_value(record.get("width"))
    height = int_value(record.get("height"))
    creator = str(record.get("attribution") or "").lower()
    title = str(record.get("title") or "").lower()
    medium = str(record.get("medium") or "").lower()
    classification = str(record.get("classification") or "").lower()
    score = max(width, height) / 1000

    score += orientation_score(width, height, 1.15, 2.4)

    if any(name in creator for name in FAMOUS_CREATORS):
        score += 8
    if any(word in title for word in FAMOUS_TITLE_WORDS):
        score += 4
    if "oil" in medium or "paint" in classification:
        score += 3
    return score


def _is_usable_record(record: dict[str, Any], *, min_long_edge: int) -> bool:
    if str(record.get("openaccess") or "") != "1":
        return False
    if not record.get("iiifurl"):
        return False
    if not usable_dimensions(int_value(record.get("width")), int_value(record.get("height")), min_long_edge):
        return False
    classification = str(record.get("classification") or "").lower()
    medium = str(record.get("medium") or "").lower()
    return "paint" in classification or "oil" in medium or "print" in classification


def _fetch_csv(name: str) -> list[dict[str, str]]:
    url = f"{OPEN_DATA_BASE}/{name}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))
