from veduta_data.getty_import import import_getty_records, score_getty_record


def getty_record(
    *,
    title="Irises",
    creator="Vincent van Gogh",
    width=9021,
    height=7122,
    accession="90.PA.20",
    object_type="Paintings",
    date="1889",
    image_id="8c255d80-7382-46db-9fa8-892c0d37247e",
    canonical_page="https://www.getty.edu/art/collection/object/103JNH",
):
    return {
        "id": "https://data.getty.edu/museum/collection/object/c88b3df0-de91-4f5b-a9ef-7b2b9a6d8abb",
        "_label": f"{title} ({accession})",
        "_vedutaImageDimensions": [width, height],
        "classified_as": [
            {"_label": "Artwork"},
            {"_label": object_type},
            {"_label": "Object Record Structure: Whole"},
        ],
        "identified_by": [
            {"_label": "Accession Number", "content": accession},
            {"_label": "Preferred Title", "content": title},
        ],
        "produced_by": {
            "_label": f"Production of Artwork by {creator}",
            "referred_to_by": [
                {"_label": "Artist/Maker (Producer) Name", "content": creator},
            ],
            "timespan": {
                "identified_by": [{"content": date}],
            },
        },
        "subject_of": [
            {"id": canonical_page, "format": "text/html"},
        ],
        "representation": [
            {
                "id": f"https://media.getty.edu/iiif/image/{image_id}/full/full/0/default.jpg",
                "format": "image/jpeg",
            },
        ],
    }


def test_import_getty_records_keeps_open_high_resolution_landscape_records():
    strong = getty_record(title="Landscape with a River", creator="Claude Monet", width=8000, height=4500)
    low_resolution = getty_record(title="Small View", width=2500, height=1600)
    portrait = getty_record(title="Portrait", width=4200, height=5200)

    library = import_getty_records([low_resolution, portrait, strong], limit=10, min_long_edge=3840)

    collection = library.collections[0]
    assert collection.id == "getty"
    assert collection.title == "J. Paul Getty Museum"
    assert [artwork.title for artwork in collection.artworks] == ["Landscape with a River"]

    artwork = collection.artworks[0]
    assert artwork.id == "claude-monet-landscape-with-a-river"
    assert artwork.creator == "Claude Monet"
    assert artwork.attribution == "J. Paul Getty Museum"
    assert artwork.canonical_page == "https://www.getty.edu/art/collection/object/103JNH"
    assert artwork.upstream_image_base == (
        "https://media.getty.edu/iiif/image/8c255d80-7382-46db-9fa8-892c0d37247e/full/4096,/0/default.jpg"
    )
    assert artwork.source_pack_id == 1004
    assert artwork.metadata["accessionNumber"] == "90.PA.20"
    assert artwork.metadata["type"] == "Paintings"
    assert artwork.metadata["date"] == "1889"
    assert artwork.metadata["imageWidth"] == 8000


def test_score_getty_record_prefers_famous_landscape_with_large_short_edge():
    ordinary = getty_record(title="Untitled Study", creator="Unknown", width=4200, height=2600)
    famous = getty_record(title="River Landscape", creator="Vincent van Gogh", width=8000, height=5000)

    assert score_getty_record(famous) > score_getty_record(ordinary)
