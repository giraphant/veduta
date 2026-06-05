from veduta_data.cleveland_import import import_cleveland_records, score_cleveland_record


def cleveland_record(
    *,
    title="The Biglin Brothers Turning the Stake",
    creator="Thomas Eakins (American, 1844–1916)",
    width="3400",
    height="2247",
    is_highlight=False,
    share_license_status="CC0",
    image_url="https://openaccess-cdn.clevelandart.org/1927.1984/1927.1984_print.jpg",
    full_width=None,
    full_height=None,
    full_filesize="101799424",
):
    images = {
        "print": {
            "url": image_url,
            "width": width,
            "height": height,
            "filesize": "5271592",
        },
        "web": {
            "url": "https://openaccess-cdn.clevelandart.org/1927.1984/1927.1984_web.jpg",
            "width": "1263",
            "height": "835",
        },
    }
    if full_width is not None and full_height is not None:
        images["full"] = {
            "url": "https://openaccess-cdn.clevelandart.org/1927.1984/1927.1984_full.tif",
            "width": str(full_width),
            "height": str(full_height),
            "filesize": str(full_filesize),
        }
    return {
        "id": 151904,
        "accession_number": "1927.1984",
        "title": title,
        "url": "https://clevelandart.org/art/1927.1984",
        "creators": [{"description": creator}],
        "share_license_status": share_license_status,
        "collection": "American - Painting",
        "department": "American Painting and Sculpture",
        "type": "Painting",
        "creation_date": "1873",
        "is_highlight": is_highlight,
        "description": "A celebrated rowing race painting by Eakins.",
        "citations": [
            {"citation": "Treasures of the Cleveland Museum of Art", "page_number": "Reproduced, p. 267."},
            {"citation": "A Companion to American Art", "page_number": "Reproduced, p. 149."},
        ],
        "exhibitions": {
            "current": [
                {"title": "The Twentieth Anniversary Exhibition"},
                {"title": "The Silver Jubilee Exhibition"},
            ]
        },
        "images": images,
    }


def test_import_cleveland_records_keeps_open_high_resolution_records_and_sorts_landscape_famous_first():
    another_landscape_highlight = cleveland_record(
        title="Stag at Sharkey's",
        creator="George Bellows (American, 1882–1925)",
        width="3400",
        height="2542",
        is_highlight=True,
        image_url="https://openaccess-cdn.clevelandart.org/1922.1133/1922.1133_print.jpg",
    )
    landscape_famous = cleveland_record()
    low_resolution = cleveland_record(
        title="Small Study",
        width="1800",
        height="1200",
        image_url="https://openaccess-cdn.clevelandart.org/small.jpg",
    )
    restricted = cleveland_record(
        title="Restricted Work",
        share_license_status="Copyrighted",
        image_url="https://openaccess-cdn.clevelandart.org/restricted.jpg",
    )

    library = import_cleveland_records([
        another_landscape_highlight,
        low_resolution,
        restricted,
        landscape_famous,
    ], limit=10, min_long_edge=3000)

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "cleveland"
    assert collection.title == "Cleveland Museum of Art"
    assert [artwork.title for artwork in collection.artworks] == [
        "Stag at Sharkey's",
        "The Biglin Brothers Turning the Stake",
    ]

    artwork = collection.artworks[1]
    assert artwork.id == "thomas-eakins-the-biglin-brothers-turning-the-stake"
    assert artwork.creator == "Thomas Eakins"
    assert artwork.attribution == "Cleveland Museum of Art"
    assert artwork.canonical_page == "https://clevelandart.org/art/1927.1984"
    assert artwork.upstream_image_base == "https://openaccess-cdn.clevelandart.org/1927.1984/1927.1984_print.jpg"
    assert artwork.source_pack_id == 1001
    assert artwork.source_index == 1


def test_import_cleveland_records_rejects_portraits_and_extreme_panoramas_by_default():
    portrait = cleveland_record(title="Portrait", width="2700", height="3400", is_highlight=True)
    extreme_strip = cleveland_record(title="Illustrated Scroll", width="3400", height="114", is_highlight=True)
    landscape = cleveland_record(title="Landscape", width="3400", height="2247", is_highlight=True)

    library = import_cleveland_records([portrait, extreme_strip, landscape], limit=10, min_long_edge=3000)

    assert [artwork.title for artwork in library.collections[0].artworks] == ["Landscape"]


def test_import_cleveland_records_prefers_reasonable_full_tiff_image():
    record = cleveland_record(width="3400", height="2247", full_width=7164, full_height=4735)

    library = import_cleveland_records([record], limit=10, min_long_edge=3840)

    artwork = library.collections[0].artworks[0]
    assert artwork.upstream_image_base == "https://openaccess-cdn.clevelandart.org/1927.1984/1927.1984_full.tif"
    assert artwork.metadata["accessionNumber"] == "1927.1984"
    assert artwork.metadata["selectedImageFileSize"] == 101799424


def test_import_cleveland_records_rejects_oversized_full_tiff_when_print_is_below_threshold():
    record = cleveland_record(
        width="3400",
        height="2247",
        full_width=14395,
        full_height=11486,
        full_filesize="496057452",
    )

    library = import_cleveland_records([record], limit=10, min_long_edge=3840)

    assert library.collections[0].artworks == []


def test_score_cleveland_record_prefers_landscape_resolution_highlights_and_citations():
    ordinary_portrait = cleveland_record(
        title="Ordinary Portrait",
        width="3200",
        height="4200",
        is_highlight=False,
    )
    strong_landscape = cleveland_record(
        title="Famous Landscape",
        width="5000",
        height="3000",
        is_highlight=True,
    )

    assert score_cleveland_record(strong_landscape) > score_cleveland_record(ordinary_portrait)
