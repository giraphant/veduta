import urllib.error

from veduta_data import met_import
from veduta_data.met_import import import_met_records, score_met_record


def met_record(
    *,
    object_id=437980,
    title="Cypresses",
    artist="Vincent van Gogh",
    primary_image="https://images.metmuseum.org/CRDImages/ep/original/DP130999.jpg",
    is_public_domain=True,
    department="European Paintings",
    classification="Paintings",
    medium="Oil on canvas",
    object_date="1889",
    tags=None,
):
    return {
        "objectID": object_id,
        "isPublicDomain": is_public_domain,
        "primaryImage": primary_image,
        "primaryImageSmall": "https://images.metmuseum.org/CRDImages/ep/web-large/DP130999.jpg" if primary_image else "",
        "title": title,
        "artistDisplayName": artist,
        "artistDisplayBio": "Dutch, 1853–1890",
        "objectDate": object_date,
        "medium": medium,
        "department": department,
        "classification": classification,
        "objectURL": f"https://www.metmuseum.org/art/collection/search/{object_id}",
        "tags": tags if tags is not None else [{"term": "Trees"}, {"term": "Landscapes"}],
    }


def test_get_json_retries_transient_forbidden_response(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", hdrs=None, fp=None)
        return FakeResponse()

    monkeypatch.setattr(met_import.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(met_import.time, "sleep", lambda seconds: None)

    assert met_import._get_json("https://example.test/met") == {"ok": True}
    assert calls == ["https://example.test/met", "https://example.test/met"]


def test_fetch_met_records_skips_object_records_that_fail(monkeypatch):
    calls = []

    def fake_get_json(url):
        calls.append(url)
        if "/search?" in url:
            return {"objectIDs": [101, 102, 103]}
        if url.endswith("/102"):
            raise urllib.error.HTTPError(url, 403, "Forbidden", hdrs=None, fp=None)
        return {"objectID": int(url.rsplit("/", 1)[1]), "title": "ok"}

    monkeypatch.setattr(met_import, "_get_json", fake_get_json)
    monkeypatch.setattr(met_import.time, "sleep", lambda seconds: None)

    records = met_import.fetch_met_records(queries=["landscape"], fetch_limit=3, delay_seconds=0)

    assert [record["objectID"] for record in records] == [101, 103]


def test_import_met_records_keeps_public_domain_image_records_and_sorts_famous_first():
    van_gogh = met_record()
    turner = met_record(
        object_id=437853,
        title="Venice, from the Porch of Madonna della Salute",
        artist="Joseph Mallord William Turner",
        primary_image="https://images.metmuseum.org/CRDImages/ep/original/DP169568.jpg",
        tags=[{"term": "Venice"}, {"term": "Boats"}],
    )
    sculpture = met_record(
        object_id=1,
        title="Small Sculpture",
        artist="Unknown artist",
        classification="Sculpture",
        medium="Bronze",
        primary_image="https://images.metmuseum.org/CRDImages/es/original/example.jpg",
    )
    restricted = met_record(object_id=2, title="Restricted", is_public_domain=False)
    no_image = met_record(object_id=3, title="No Image", primary_image="")

    library = import_met_records([sculpture, restricted, no_image, turner, van_gogh], limit=10)

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "met"
    assert collection.title == "The Metropolitan Museum of Art"
    assert [artwork.title for artwork in collection.artworks] == [
        "Cypresses",
        "Venice, from the Porch of Madonna della Salute",
    ]

    artwork = collection.artworks[0]
    assert artwork.id == "vincent-van-gogh-cypresses"
    assert artwork.creator == "Vincent van Gogh"
    assert artwork.attribution == "The Metropolitan Museum of Art"
    assert artwork.canonical_page == "https://www.metmuseum.org/art/collection/search/437980"
    assert artwork.upstream_image_base == (
        "https://images.metmuseum.org/CRDImages/ep/original/DP130999.jpg|"
        "https://images.metmuseum.org/CRDImages/ep/web-large/DP130999.jpg"
    )
    assert artwork.source_pack_id == 1003
    assert artwork.source_index == 0


def test_import_met_records_adds_primary_small_as_fallback_when_available():
    record = met_record(primary_image="https://images.metmuseum.org/CRDImages/ep/original/missing.jpg")
    record["primaryImageSmall"] = "https://images.metmuseum.org/CRDImages/ep/web-large/missing.jpg"

    library = import_met_records([record], limit=10)

    assert library.collections[0].artworks[0].upstream_image_base == (
        "https://images.metmuseum.org/CRDImages/ep/original/missing.jpg|"
        "https://images.metmuseum.org/CRDImages/ep/web-large/missing.jpg"
    )


def test_import_met_records_truncates_long_artwork_ids():
    record = met_record(
        title="Niche in the Form of a Cartouche from the Series Veelderleij Niewe Inuentien van Antijcksche Sepultueren Diemen Nou Zeere Ghebruijkende Is Met Noch Zeer Fraeije Grotissen",
        artist="Johannes van Doetecum I",
    )

    library = import_met_records([record], limit=10)

    assert len(library.collections[0].artworks[0].id) <= 96


def test_import_met_records_deduplicates_repeated_creator_title_records():
    first = met_record(object_id=10, title="Cypresses", artist="Vincent van Gogh")
    second = met_record(object_id=11, title="Cypresses", artist="Vincent van Gogh")

    library = import_met_records([first, second], limit=10)

    assert [artwork.id for artwork in library.collections[0].artworks] == ["vincent-van-gogh-cypresses"]


def test_score_met_record_prefers_famous_landscape_paintings():
    ordinary = met_record(
        title="Study",
        artist="Unknown artist",
        department="Drawings and Prints",
        classification="Prints",
        medium="Etching",
        tags=[{"term": "Figures"}],
    )
    famous_landscape = met_record(
        title="Wheat Field with Cypresses",
        artist="Vincent van Gogh",
        tags=[{"term": "Landscapes"}, {"term": "Trees"}],
    )

    assert score_met_record(famous_landscape) > score_met_record(ordinary)
