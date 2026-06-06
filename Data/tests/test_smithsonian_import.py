from veduta_data.smithsonian_import import import_smithsonian_records, score_smithsonian_record


def smithsonian_record(
    *,
    record_id="saam_1984.50",
    title="The Departure of the Crusaders",
    artist="Victor Nehlig, born Paris, France 1830-died New York City 1909",
    medium="oil on canvas",
    object_types=None,
    ids_id="SAAM-1984.50_2",
    image_url="https://ids.si.edu/ids/download?id=SAAM-1984.50_2.jpg",
    width=3000,
    height=1904,
    usage_access="CC0",
    metadata_access="CC0",
    record_link="https://americanart.si.edu/collections/search/artwork/?id=18220",
    topics=None,
    department="Painting and Sculpture",
):
    if object_types is None:
        object_types = ["Paintings"]
    if topics is None:
        topics = ["Landscapes", "Mountains"]
    return {
        "id": "ld1-test",
        "unitCode": "SAAM",
        "type": "edanmdm",
        "title": title,
        "content": {
            "freetext": {
                "name": [
                    {"label": "Artist", "content": artist},
                ],
                "physicalDescription": [
                    {"label": "Medium", "content": medium},
                ],
                "objectType": [
                    {"label": "Type", "content": "Painting"},
                ],
                "objectRights": [
                    {"label": "Restrictions & Rights", "content": usage_access},
                ],
                "setName": [
                    {"label": "Department", "content": department},
                ],
            },
            "indexedStructured": {
                "object_type": object_types,
                "topic": topics,
            },
            "descriptiveNonRepeating": {
                "title": {
                    "label": "Title",
                    "content": title,
                },
                "record_ID": record_id,
                "unit_code": "SAAM",
                "record_link": record_link,
                "metadata_usage": {
                    "access": metadata_access,
                },
                "online_media": {
                    "media": [
                        {
                            "id": f"media:{ids_id}",
                            "type": "Images",
                            "idsId": ids_id,
                            "usage": {
                                "access": usage_access,
                            },
                            "resources": [
                                {
                                    "label": "High-resolution JPEG",
                                    "url": image_url,
                                    "width": width,
                                    "height": height,
                                    "dimensions": f"{width}x{height}",
                                },
                            ],
                        },
                    ],
                    "mediaCount": 1,
                },
            },
        },
    }


def test_import_smithsonian_records_keeps_cc0_high_resolution_landscape_paintings_and_sorts_famous_first():
    twachtman = smithsonian_record(
        record_id="saam_1929.6.144",
        title="The Brook, Greenwich, Connecticut",
        artist="John Henry Twachtman, born Cincinnati, OH 1853-died Gloucester, MA 1902",
        ids_id="SAAM-1929.6.144_1",
        image_url="https://ids.si.edu/ids/download?id=SAAM-1929.6.144_1.jpg",
        width=3000,
        height=2166,
        record_link="https://americanart.si.edu/collections/search/artwork/?id=24336",
        topics=["Landscapes", "Rivers"],
    )
    homer = smithsonian_record(
        record_id="saam_1893.3",
        title="Breezing Up",
        artist="Winslow Homer, born Boston, MA 1836-died Prouts Neck, ME 1910",
        ids_id="SAAM-1893.3_1",
        image_url="https://ids.si.edu/ids/download?id=SAAM-1893.3_1.jpg",
        width=4000,
        height=2600,
        record_link="https://americanart.si.edu/collections/search/artwork/?id=99999",
        topics=["Seascapes"],
    )
    portrait = smithsonian_record(title="Portrait", width=2500, height=3600)
    low_res = smithsonian_record(title="Tiny", width=1200, height=900)
    restricted = smithsonian_record(title="Restricted", metadata_access="CC-BY")
    no_image = smithsonian_record(title="No Image", image_url="", width=0, height=0)

    library = import_smithsonian_records(
        [portrait, low_res, restricted, no_image, homer, twachtman],
        limit=10,
        min_long_edge=3000,
    )

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "smithsonian"
    assert collection.title == "Smithsonian American Art Museum"
    assert len(collection.artworks) == 2

    artwork = collection.artworks[0]
    assert artwork.creator == "Winslow Homer, born Boston, MA 1836-died Prouts Neck, ME 1910"
    assert artwork.attribution == "Smithsonian American Art Museum"
    assert artwork.canonical_page == "https://americanart.si.edu/collections/search/artwork/?id=99999"
    assert artwork.upstream_image_base == "https://ids.si.edu/ids/download?id=SAAM-1893.3_1.jpg"
    assert artwork.source_pack_id == 1006
    assert artwork.source_index == 0


def test_import_smithsonian_records_deduplicates_repeated_creator_title_records():
    first = smithsonian_record(title="Landscape", ids_id="SAAM-1", image_url="https://ids.si.edu/ids/download?id=SAAM-1.jpg")
    second = smithsonian_record(title="Landscape", ids_id="SAAM-2", image_url="https://ids.si.edu/ids/download?id=SAAM-2.jpg")

    library = import_smithsonian_records([first, second], limit=10, min_long_edge=3000)

    assert len(library.collections[0].artworks) == 1


def test_import_smithsonian_records_rejects_portraits_and_extreme_panoramas():
    portrait = smithsonian_record(title="Portrait", width=3000, height=4000)
    panorama = smithsonian_record(title="Panorama", width=9000, height=2000)

    library = import_smithsonian_records([portrait, panorama], limit=10, min_long_edge=3000)

    assert len(library.collections[0].artworks) == 0


def test_import_smithsonian_records_rejects_non_paintings():
    sculpture = smithsonian_record(
        title="Sculpture",
        object_types=["Sculpture"],
        width=3000,
        height=2000,
    )

    library = import_smithsonian_records([sculpture], limit=10, min_long_edge=3000)

    assert len(library.collections[0].artworks) == 0


def test_score_smithsonian_record_prefers_famous_landscape_paintings():
    ordinary = smithsonian_record(
        title="Untitled",
        artist="Unknown Painter",
        medium="watercolor on paper",
        topics=["Animals"],
        department="Graphic Arts",
    )
    famous = smithsonian_record(
        title="Hudson River View",
        artist="Albert Bierstadt",
        medium="oil on canvas",
        topics=["Landscapes", "Rivers"],
        department="Painting and Sculpture",
    )

    assert score_smithsonian_record(famous) > score_smithsonian_record(ordinary)
