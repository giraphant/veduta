from veduta_data.nga_import import import_nga_records, score_nga_record


def nga_record(
    *,
    objectid="1111",
    title="The Japanese Footbridge",
    attribution="Claude Monet",
    medium="oil on canvas",
    classification="painting",
    iiifurl="https://api.nga.gov/iiif/monet-image-id",
    width="4200",
    height="3000",
    openaccess="1",
):
    return {
        "objectid": objectid,
        "title": title,
        "displaydate": "1899",
        "medium": medium,
        "classification": classification,
        "attribution": attribution,
        "openaccess": openaccess,
        "iiifurl": iiifurl,
        "width": width,
        "height": height,
    }


def test_import_nga_records_keeps_open_high_resolution_landscape_paintings_and_sorts_famous_first():
    monet = nga_record()
    homer = nga_record(
        objectid="2222",
        title="Breezing Up (A Fair Wind)",
        attribution="Winslow Homer",
        iiifurl="https://api.nga.gov/iiif/homer-image-id",
        width="4000",
        height="2900",
    )
    portrait = nga_record(title="Portrait", width="2500", height="3600", iiifurl="https://api.nga.gov/iiif/portrait-id")
    low_res = nga_record(title="Tiny", width="1200", height="900", iiifurl="https://api.nga.gov/iiif/tiny-id")
    closed = nga_record(title="Closed", openaccess="0", iiifurl="https://api.nga.gov/iiif/closed-id")
    no_image = nga_record(title="No Image", iiifurl="")

    library = import_nga_records([portrait, low_res, closed, no_image, homer, monet], limit=10, min_long_edge=3000)

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "nga"
    assert collection.title == "National Gallery of Art"
    assert [artwork.title for artwork in collection.artworks] == [
        "The Japanese Footbridge",
        "Breezing Up (A Fair Wind)",
    ]

    artwork = collection.artworks[0]
    assert artwork.id == "claude-monet-the-japanese-footbridge"
    assert artwork.creator == "Claude Monet"
    assert artwork.attribution == "National Gallery of Art"
    assert artwork.canonical_page == "https://www.nga.gov/collection/art-object-page.1111.html"
    assert artwork.upstream_image_base == "https://api.nga.gov/iiif/monet-image-id/full/3400,/0/default.jpg"
    assert artwork.source_pack_id == 1004
    assert artwork.source_index == 0


def test_import_nga_records_deduplicates_repeated_creator_title_records():
    first = nga_record(objectid="1", title="Landscape", attribution="Claude Monet", iiifurl="https://api.nga.gov/iiif/first")
    second = nga_record(objectid="2", title="Landscape", attribution="Claude Monet", iiifurl="https://api.nga.gov/iiif/second")

    library = import_nga_records([first, second], limit=10, min_long_edge=3000)

    assert [artwork.id for artwork in library.collections[0].artworks] == ["claude-monet-landscape"]


def test_score_nga_record_prefers_famous_landscape_paintings():
    ordinary = nga_record(title="Untitled", attribution="Unknown", medium="etching", classification="print")
    famous = nga_record(title="The Japanese Footbridge", attribution="Claude Monet", medium="oil on canvas")

    assert score_nga_record(famous) > score_nga_record(ordinary)
