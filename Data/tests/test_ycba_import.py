from veduta_data.ycba_import import import_ycba_records, score_ycba_record


def ycba_record(
    *,
    object_id=53,
    title="Old Walton Bridge",
    creator="Canaletto, 1697-1768",
    medium="Oil on canvas",
    copyright="Public Domain",
    width=7548,
    height=2785,
    service="https://images.collections.yale.edu/iiif/2/ycba:image-id",
    description="A view of the bridge over the river.",
    include_date_metadata=True,
):
    metadata = [
        ("Copyright Statement", copyright),
        ("Creator", creator),
        ("Title", title),
        ("Medium", medium),
        ("Physical Description", "18 x 48 inches"),
        ("Credit Line", "Yale Center for British Art, Paul Mellon Collection"),
        ("Collection", "Paintings and Sculpture"),
        ("Call Number", "B1981.25.86"),
    ]
    if include_date_metadata:
        metadata.insert(3, ("Date", "1755"))
    return {
        "id": f"https://manifests.collections.yale.edu/ycba/obj/{object_id}",
        "type": "Manifest",
        "label": {"en": [f"{creator}, {title}, 1755"]},
        "summary": {"en": [description]} if description else {},
        "metadata": [
            {"label": {"en": [label]}, "value": {"en": [value]}}
            for label, value in metadata
        ],
        "homepage": [{
            "id": f"https://collections.britishart.yale.edu/catalog/tms:{object_id}",
            "type": "Text",
        }],
        "items": [{
            "id": "canvas",
            "type": "Canvas",
            "width": width,
            "height": height,
            "items": [{
                "items": [{
                    "body": {
                        "service": [{"@id": service, "@type": "ImageService2"}],
                    }
                }]
            }],
        }],
    }


def test_import_ycba_records_keeps_public_domain_high_resolution_landscape_artworks():
    canaletto = ycba_record()
    turner = ycba_record(
        object_id=34,
        title="Dort, or Dordrecht: The Dort Packet-Boat from Rotterdam Becalmed",
        creator="Joseph Mallord William Turner, 1775-1851",
        width=14484,
        height=9741,
        service="https://images.collections.yale.edu/iiif/2/ycba:turner",
    )
    portrait = ycba_record(object_id=1, title="Portrait", width=2000, height=3200)
    low_res = ycba_record(object_id=2, title="Low", width=1200, height=900)
    closed = ycba_record(object_id=3, title="Closed", copyright="Copyright Undetermined")
    no_medium = ycba_record(object_id=4, title="No Medium", medium="")
    no_image = ycba_record(object_id=5, title="No Image", service="")

    library = import_ycba_records(
        [portrait, low_res, closed, no_medium, no_image, canaletto, turner],
        limit=10,
        min_long_edge=2500,
    )

    collection = library.collections[0]
    assert collection.id == "ycba"
    assert collection.title == "Yale Center for British Art"
    assert [artwork.title for artwork in collection.artworks] == [
        "Dort, or Dordrecht: The Dort Packet-Boat from Rotterdam Becalmed",
        "Old Walton Bridge",
    ]

    artwork = collection.artworks[0]
    assert artwork.id == "joseph-mallord-william-turner-1775-1851-dort-or-dordrecht-the-dort-packet-boat-from-rotterdam-be"
    assert artwork.creator == "Joseph Mallord William Turner, 1775-1851"
    assert artwork.canonical_page == "https://collections.britishart.yale.edu/catalog/tms:34"
    assert artwork.upstream_image_base == "https://images.collections.yale.edu/iiif/2/ycba:turner/full/3400,/0/default.jpg"
    assert artwork.metadata["medium"] == "Oil on canvas"
    assert artwork.metadata["description"] == "A view of the bridge over the river."


def test_import_ycba_records_deduplicates_repeated_creator_title_records():
    first = ycba_record(object_id=1)
    second = ycba_record(object_id=2, service="https://images.collections.yale.edu/iiif/2/ycba:second")

    library = import_ycba_records([first, second], limit=10, min_long_edge=2500)

    assert [artwork.id for artwork in library.collections[0].artworks] == [
        "canaletto-1697-1768-old-walton-bridge",
        "canaletto-1697-1768-old-walton-bridge-2",
    ]


def test_import_ycba_records_prefers_recto_canvas_over_x_radiograph():
    record = ycba_record(
        width=8000,
        height=5000,
        service="https://images.collections.yale.edu/iiif/2/ycba:recto",
    )
    record["items"].append({
        "id": "xray-canvas",
        "type": "Canvas",
        "label": {"en": ["x-radiograph"]},
        "width": 50000,
        "height": 30000,
        "items": [{
            "items": [{
                "body": {
                    "service": [{"@id": "https://images.collections.yale.edu/iiif/2/ycba:xray", "@type": "ImageService2"}],
                }
            }]
        }],
    })
    record["items"][0]["label"] = {"en": ["recto, cropped to image"]}

    library = import_ycba_records([record], limit=10, min_long_edge=2500)

    assert library.collections[0].artworks[0].upstream_image_base == (
        "https://images.collections.yale.edu/iiif/2/ycba:recto/full/3400,/0/default.jpg"
    )


def test_score_ycba_record_prefers_famous_landscape_artworks():
    ordinary = ycba_record(title="Figure Study", creator="Known Artist")
    famous = ycba_record(title="Old Walton Bridge", creator="Canaletto")

    assert score_ycba_record(famous) > score_ycba_record(ordinary)


def test_import_ycba_records_falls_back_to_label_date():
    record = ycba_record(include_date_metadata=False)

    library = import_ycba_records([record], limit=10, min_long_edge=2500)

    assert library.collections[0].artworks[0].metadata["date"] == "1755"
