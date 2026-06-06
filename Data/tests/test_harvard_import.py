from veduta_data.harvard_import import import_harvard_records, score_harvard_record


def harvard_record(
    *,
    objectid=1111,
    title="Water Lilies",
    people=None,
    classification="Paintings",
    medium="oil on canvas",
    iiifbaseuri="https://ids.lib.harvard.edu/ids/iiif/monet-image-id",
    width=4200,
    height=3000,
    imagepermissionlevel=0,
    displayorder=1,
    url="https://harvardartmuseums.org/collections/object/1111",
    verificationlevel=4,
    publicationcount=3,
    exhibitioncount=2,
    totalpageviews=250,
):
    if people is None:
        people = [{"role": "Artist", "displayname": "Claude Monet"}]
    return {
        "objectid": objectid,
        "title": title,
        "people": people,
        "classification": classification,
        "medium": medium,
        "imagepermissionlevel": imagepermissionlevel,
        "images": [{
            "iiifbaseuri": iiifbaseuri,
            "width": width,
            "height": height,
            "displayorder": displayorder,
        }],
        "url": url,
        "verificationlevel": verificationlevel,
        "publicationcount": publicationcount,
        "exhibitioncount": exhibitioncount,
        "totalpageviews": totalpageviews,
    }


def test_import_harvard_records_keeps_public_high_resolution_landscape_paintings_and_sorts_famous_first():
    monet = harvard_record()
    ordinary = harvard_record(
        objectid=2222,
        title="Quiet Landscape",
        people=[{"role": "Artist", "displayname": "Unknown Painter"}],
        iiifbaseuri="https://ids.lib.harvard.edu/ids/iiif/ordinary-image-id",
        width=4100,
        height=2900,
        url="https://harvardartmuseums.org/collections/object/2222",
        verificationlevel=1,
        publicationcount=0,
        exhibitioncount=0,
        totalpageviews=0,
    )
    portrait = harvard_record(title="Portrait", width=2500, height=3600)
    panorama = harvard_record(title="Panorama", width=9000, height=2000)
    low_res = harvard_record(title="Tiny", width=1200, height=900)
    restricted = harvard_record(title="Restricted", imagepermissionlevel=1)
    unknown_permission = harvard_record(title="Unknown Permission", imagepermissionlevel=None)
    no_image = harvard_record(title="No Image", iiifbaseuri="")

    library = import_harvard_records(
        [portrait, panorama, low_res, restricted, unknown_permission, no_image, ordinary, monet],
        limit=10,
        min_long_edge=3000,
    )

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "harvard"
    assert collection.title == "Harvard Art Museums"
    assert [artwork.title for artwork in collection.artworks] == [
        "Water Lilies",
        "Quiet Landscape",
    ]

    artwork = collection.artworks[0]
    assert artwork.id == "claude-monet-water-lilies"
    assert artwork.creator == "Claude Monet"
    assert artwork.attribution == "Harvard Art Museums"
    assert artwork.canonical_page == "https://harvardartmuseums.org/collections/object/1111"
    assert artwork.upstream_image_base == "https://ids.lib.harvard.edu/ids/iiif/monet-image-id/full/3400,/0/default.jpg"
    assert artwork.source_pack_id == 1005
    assert artwork.source_index == 0


def test_import_harvard_records_deduplicates_repeated_creator_title_records():
    first = harvard_record(objectid=1, title="Landscape", iiifbaseuri="https://ids.lib.harvard.edu/ids/iiif/first")
    second = harvard_record(objectid=2, title="Landscape", iiifbaseuri="https://ids.lib.harvard.edu/ids/iiif/second")

    library = import_harvard_records([first, second], limit=10, min_long_edge=3000)

    assert [artwork.id for artwork in library.collections[0].artworks] == ["claude-monet-landscape"]


def test_score_harvard_record_prefers_famous_landscape_paintings():
    ordinary = harvard_record(
        title="Untitled",
        people=[{"role": "Artist", "displayname": "Unknown"}],
        medium="tempera",
        verificationlevel=0,
        publicationcount=0,
        exhibitioncount=0,
        totalpageviews=0,
    )
    famous = harvard_record(title="Water Lilies", people=[{"role": "Artist", "displayname": "Claude Monet"}])

    assert score_harvard_record(famous) > score_harvard_record(ordinary)
