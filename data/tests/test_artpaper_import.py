import json
from pathlib import Path

from veduta_data.artpaper_import import import_artpaper_bundle, slugify


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_slugify_keeps_ascii_words_and_removes_punctuation():
    assert slugify("Alte Nationalgalerie, National Museums in Berlin") == "alte-nationalgalerie-national-museums-in-berlin"
    assert slugify("Galéria umelcov Spiša") == "galeria-umelcov-spisa"
    assert slugify("  Still Life: Lemons & Oranges!  ") == "still-life-lemons-oranges"


def test_import_artpaper_bundle_reads_packages_and_collection_json(tmp_path):
    resources = tmp_path / "Artpaper.app" / "Contents" / "Resources"
    resources.mkdir(parents=True)

    write_json(resources / "packages.json", [
        {
            "id": 0,
            "short_name": "Essentials",
            "name": "Essentials Set",
            "tier": 3,
            "objects": 1,
            "authors": 1,
            "sizes": {"regular": 0, "hd": 332, "ultrahd": 945},
        }
    ])
    write_json(resources / "0.json", [
        {
            "title": "Still Life with Lemons, Oranges and a Pomegranate",
            "link": "asset-viewer/example",
            "gap": "https://artsandculture.google.com/asset/specific-artwork/specific-id",
            "artist_link": "https://www.google.com/search?q=Jacob+van+Hulsdonck",
            "source": "CI_TAB",
            "creator": "Jacob van Hulsdonck",
            "image": "http://lh6.ggpht.com/example-image",
            "attribution_link": "collection/the-j-paul-getty-museum",
            "attribution": "The J. Paul Getty Museum",
        }
    ])

    library = import_artpaper_bundle(tmp_path / "Artpaper.app")

    assert len(library.collections) == 1
    collection = library.collections[0]
    assert collection.id == "essentials"
    assert collection.source_pack_id == 0
    assert collection.title == "Essentials Set"
    assert collection.expected_artwork_count == 1
    assert len(collection.artworks) == 1

    artwork = collection.artworks[0]
    assert artwork.id == "jacob-van-hulsdonck-still-life-with-lemons-oranges-and-a-pomegranate"
    assert artwork.title == "Still Life with Lemons, Oranges and a Pomegranate"
    assert artwork.creator == "Jacob van Hulsdonck"
    assert artwork.attribution == "The J. Paul Getty Museum"
    assert artwork.canonical_page == "https://artsandculture.google.com/asset/specific-artwork/specific-id"
    assert artwork.upstream_image_base == "https://lh6.ggpht.com/example-image"
