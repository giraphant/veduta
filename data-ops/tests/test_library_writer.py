import json
from pathlib import Path

from openartpaper_data.library_writer import write_metadata_library
from openartpaper_data.models import SourceArtwork, SourceCollection, SourceLibrary


def sample_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="essentials",
            source_pack_id=0,
            short_name="Essentials",
            title="Essentials Set",
            expected_artwork_count=1,
            expected_author_count=1,
            source_sizes_mb={"regular": 0, "hd": 332, "ultrahd": 945},
            artworks=[
                SourceArtwork(
                    id="artist-title",
                    title="Title",
                    creator="Artist",
                    attribution="Museum",
                    canonical_page="https://artsandculture.google.com/asset/example",
                    artist_page="https://example.com/artist",
                    upstream_image_base="https://lh6.ggpht.com/example",
                    source_pack_id=0,
                    source_index=0,
                )
            ],
        )
    ])


def test_write_metadata_library_creates_catalog_and_collection_manifest(tmp_path):
    write_metadata_library(sample_library(), tmp_path)

    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["schemaVersion"] == 1
    assert catalog["collections"][0]["id"] == "essentials"
    assert catalog["collections"][0]["manifest"] == "collections/essentials.json"

    collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    assert collection["schemaVersion"] == 1
    assert collection["id"] == "essentials"
    assert collection["artworks"][0]["images"]["wallpaper"]["localPath"] == "images/essentials/artist-title.jpg"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://lh6.ggpht.com/example=s0",
        "https://lh6.ggpht.com/example=s8192",
        "https://lh6.ggpht.com/example=s6000",
        "https://lh6.ggpht.com/example=s5120",
        "https://lh6.ggpht.com/example=s4096",
    ]
