from veduta_data.vam_import import import_vam_records, score_vam_record


def vam_record(
    *,
    system_number="O16861",
    accession_number="123-1900",
    title="A River Landscape",
    maker="J. M. W. Turner",
    image_id="2011EV9123",
    width=2500,
    height=1875,
    image_resolution="high",
    warning_types=None,
    on_display=False,
    detail=None,
):
    detail_record = detail if detail is not None else {
        "titles": [{"title": title}],
        "briefDescription": f"{title}, oil on canvas, London, 1850",
        "materialsAndTechniques": "oil on canvas",
        "productionDates": [{"date": {"text": "1850"}}],
        "placesOfOrigin": [{"place": {"text": "London"}}],
        "categories": [{"text": "Paintings"}],
    }
    return {
        "systemNumber": system_number,
        "accessionNumber": accession_number,
        "objectType": "Painting",
        "_primaryTitle": title,
        "_primaryMaker": {"name": maker, "association": "artist"},
        "_primaryImageId": image_id,
        "_imageWidth": width,
        "_imageHeight": height,
        "_warningTypes": warning_types or [],
        "_currentLocation": {"onDisplay": on_display},
        "_images": {"imageResolution": image_resolution},
        "_detailRecord": detail_record,
    }


def test_import_vam_records_keeps_high_resolution_landscape_paintings_and_sorts_famous_first():
    turner = vam_record()
    ordinary = vam_record(
        system_number="O200",
        title="Study of Trees",
        maker="Known Artist",
        image_id="ordinary-image",
        width=2600,
        height=1800,
        on_display=True,
    )
    portrait = vam_record(title="Portrait", image_id="portrait-image", width=1800, height=2500)
    low_res = vam_record(title="Tiny", image_id="tiny-image", width=1200, height=900)
    low_resolution_flag = vam_record(title="Low", image_id="low-image", image_resolution="low")
    warning = vam_record(title="Warning", image_id="warning-image", warning_types=["content"])
    no_image = vam_record(title="No Image", image_id="")
    unknown_artist = vam_record(title="Known Title", maker="Unknown", image_id="unknown-artist-image")
    untitled = vam_record(
        title="Untitled painting (123)",
        maker="Known Artist",
        image_id="untitled-image",
        detail={},
    )

    library = import_vam_records(
        [portrait, low_res, low_resolution_flag, warning, no_image, unknown_artist, untitled, ordinary, turner],
        limit=10,
        min_long_edge=2500,
    )

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "vam"
    assert collection.title == "Victoria and Albert Museum"
    assert [artwork.title for artwork in collection.artworks] == [
        "A River Landscape",
        "Study of Trees",
        "Known Title",
    ]

    artwork = collection.artworks[0]
    assert artwork.id == "j-m-w-turner-a-river-landscape"
    assert artwork.creator == "J. M. W. Turner"
    assert artwork.attribution == "Victoria and Albert Museum"
    assert artwork.canonical_page == "https://collections.vam.ac.uk/item/O16861/"
    assert artwork.upstream_image_base == "https://framemark.vam.ac.uk/collections/2011EV9123/full/3400,/0/default.jpg"
    assert artwork.source_pack_id == 1007
    assert artwork.source_index == 0


def test_import_vam_records_deduplicates_repeated_creator_title_records():
    first = vam_record(system_number="O1", image_id="first")
    second = vam_record(system_number="O2", image_id="second")

    library = import_vam_records([first, second], limit=10, min_long_edge=2500)

    assert [artwork.id for artwork in library.collections[0].artworks] == [
        "j-m-w-turner-a-river-landscape",
        "j-m-w-turner-a-river-landscape-2",
    ]


def test_import_vam_records_uses_detail_description_to_replace_untitled_summary():
    record = vam_record(
        system_number="O1305003",
        title="",
        maker="Unknown",
        image_id="detail-image",
        detail={
            "titles": [],
            "briefDescription": "Interior view of the Teatro del Cocomero showing Harlequin and Columbine dancing on stage in a comic opera, ca.1760. Oil on canvas by Thomas Patch (1725-1782)",
            "materialsAndTechniques": "Oil on canvas",
            "productionDates": [{"date": {"text": "ca. 1760"}}],
            "categories": [{"text": "Paintings"}],
        },
    )

    library = import_vam_records([record], limit=10, min_long_edge=2500)

    artwork = library.collections[0].artworks[0]
    assert artwork.title == "Interior view of the Teatro del Cocomero showing Harlequin and Columbine dancing on stage in a comic opera"
    assert artwork.creator == "Thomas Patch"
    assert artwork.metadata["date"] == "ca. 1760"
    assert artwork.metadata["medium"] == "Oil on canvas"


def test_score_vam_record_prefers_famous_landscape_paintings():
    ordinary = vam_record(title="City View", maker="Known Artist")
    famous = vam_record(title="A River Landscape", maker="J. M. W. Turner")

    assert score_vam_record(famous) > score_vam_record(ordinary)
