from veduta_data.chicago_api_import import import_chicago_api_records, score_chicago_api_record


def chicago_record(
    *,
    title="The Bay of Marseille, Seen from L'Estaque",
    artist_title="Paul Cezanne",
    width=12821,
    height=10275,
    image_id="95be6a6f-7b9c-df3d-cb0a-21b0152a73f5",
    is_public_domain=True,
    artwork_type_title="Painting",
    publication_history="The Essential Guide, rev. ed. Reproduced p. 42. Catalogue raisonné entry.",
    exhibition_history="Art Institute of Chicago, Cezanne retrospective. Museum of Modern Art exhibition.",
):
    return {
        "id": 14572,
        "api_link": "https://api.artic.edu/api/v1/artworks/14572",
        "title": title,
        "artist_title": artist_title,
        "artist_display": f"{artist_title} (French, 1839–1906)",
        "date_display": "c. 1885",
        "place_of_origin": "France",
        "department_title": "Painting and Sculpture of Europe",
        "artwork_type_title": artwork_type_title,
        "classification_title": "painting",
        "is_public_domain": is_public_domain,
        "image_id": image_id,
        "thumbnail": {
            "width": width,
            "height": height,
            "alt_text": "Landscape painting.",
        },
        "publication_history": publication_history,
        "exhibition_history": exhibition_history,
    }


def test_import_chicago_api_records_keeps_public_high_resolution_landscapes_and_sorts_famous_first():
    monet_train = chicago_record(
        title="Arrival of the Normandy Train, Gare Saint-Lazare",
        artist_title="Claude Monet",
        width=6786,
        height=5092,
        image_id="monet-image-id",
    )
    cezanne = chicago_record()
    portrait = chicago_record(title="Portrait Study", width=3200, height=5200, image_id="portrait-image-id")
    low_resolution = chicago_record(title="Small Sketch", width=1800, height=1400, image_id="small-image-id")
    restricted = chicago_record(title="Restricted Work", image_id="restricted-image-id", is_public_domain=False)
    no_image = chicago_record(title="No Image", image_id=None)

    library = import_chicago_api_records(
        [portrait, low_resolution, restricted, no_image, monet_train, cezanne],
        limit=10,
        min_long_edge=3000,
    )

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "chicago"
    assert collection.title == "The Art Institute of Chicago"
    assert [artwork.title for artwork in collection.artworks] == [
        "The Bay of Marseille, Seen from L'Estaque",
        "Arrival of the Normandy Train, Gare Saint-Lazare",
    ]

    artwork = collection.artworks[1]
    assert artwork.id == "claude-monet-arrival-of-the-normandy-train-gare-saint-lazare"
    assert artwork.creator == "Claude Monet"
    assert artwork.attribution == "The Art Institute of Chicago"
    assert artwork.canonical_page == "https://www.artic.edu/artworks/14572"
    assert artwork.upstream_image_base == "https://www.artic.edu/iiif/2/monet-image-id/full/4096,/0/default.jpg"
    assert artwork.source_pack_id == 1002
    assert artwork.source_index == 1


def test_import_chicago_api_records_deduplicates_repeated_creator_title_records():
    first = chicago_record(title="Stacks of Wheat", artist_title="Claude Monet", image_id="first-image")
    second = chicago_record(title="Stacks of Wheat", artist_title="Claude Monet", image_id="second-image")

    library = import_chicago_api_records([first, second], limit=10, min_long_edge=3000)

    assert [artwork.id for artwork in library.collections[0].artworks] == ["claude-monet-stacks-of-wheat"]


def test_import_chicago_api_records_rejects_extreme_panoramas_by_default():
    scroll = chicago_record(title="Extreme Scroll", width=6000, height=500, image_id="scroll-id")
    landscape = chicago_record(title="Good Landscape", width=5000, height=3200, image_id="landscape-id")

    library = import_chicago_api_records([scroll, landscape], limit=10, min_long_edge=3000)

    assert [artwork.title for artwork in library.collections[0].artworks] == ["Good Landscape"]


def test_score_chicago_api_record_prefers_famous_landscape_with_publication_history():
    ordinary = chicago_record(
        title="Untitled Landscape",
        artist_title="Unknown Artist",
        width=3400,
        height=2600,
        publication_history="",
        exhibition_history="",
    )
    famous = chicago_record(
        title="Arrival of the Normandy Train, Gare Saint-Lazare",
        artist_title="Claude Monet",
        width=6786,
        height=5092,
        publication_history="Reproduced in catalogue. Essential Guide. Catalogue raisonné.",
        exhibition_history="Major Impressionism exhibition. Art Institute exhibition.",
    )

    assert score_chicago_api_record(famous) > score_chicago_api_record(ordinary)
