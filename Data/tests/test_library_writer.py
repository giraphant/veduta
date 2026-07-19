import json
from pathlib import Path

import pytest

from veduta_data.library_writer import update_wallpaper_metadata, wallpaper_local_path, write_json, write_metadata_library
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary


def sample_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="essentials",
            source_pack_id=0,
            short_name="Essentials",
            title="Essentials Set",
            expected_artwork_count=1,
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
    # Curated cover from covers.json is re-applied when the catalog is written.
    assert catalog["collections"][0]["cover"].startswith("images/essentials/")

    collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    assert collection["schemaVersion"] == 1
    assert collection["id"] == "essentials"
    assert collection["artworks"][0]["classification"] == {"kind": "flat-art"}
    assert collection["artworks"][0]["images"]["wallpaper"]["localPath"] == "images/essentials/artist-title.jpg"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://lh6.ggpht.com/example=s0",
        "https://lh6.ggpht.com/example=s8192",
        "https://lh6.ggpht.com/example=s6000",
        "https://lh6.ggpht.com/example=s5120",
        "https://lh6.ggpht.com/example=s4096",
    ]


def test_candidate_image_urls_adds_nga_iiif_size_fallbacks():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://api.nga.gov/iiif/image-id/full/3400,/0/default.jpg") == [
        "https://api.nga.gov/iiif/image-id/full/4096,/0/default.jpg",
        "https://api.nga.gov/iiif/image-id/full/3400,/0/default.jpg",
        "https://api.nga.gov/iiif/image-id/full/3000,/0/default.jpg",
        "https://api.nga.gov/iiif/image-id/full/2500,/0/default.jpg",
        "https://api.nga.gov/iiif/image-id/full/1600,/0/default.jpg",
        "https://api.nga.gov/iiif/image-id/full/1200,/0/default.jpg",
    ]


def test_candidate_image_urls_adds_harvard_iiif_size_fallbacks():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://ids.lib.harvard.edu/ids/iiif/image-id/full/3400,/0/default.jpg") == [
        "https://ids.lib.harvard.edu/ids/iiif/image-id/full/3400,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/image-id/full/3000,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/image-id/full/2500,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/image-id/full/1600,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/image-id/full/1200,/0/default.jpg",
    ]


def test_candidate_image_urls_adds_vam_iiif_size_fallbacks():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://framemark.vam.ac.uk/collections/image-id/full/3400,/0/default.jpg") == [
        "https://framemark.vam.ac.uk/collections/image-id/full/4096,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/image-id/full/3400,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/image-id/full/3000,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/image-id/full/2500,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/image-id/full/1600,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/image-id/full/1200,/0/default.jpg",
    ]


def test_candidate_image_urls_adds_ycba_iiif_size_fallbacks():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://images.collections.yale.edu/iiif/2/ycba:image-id/full/3400,/0/default.jpg") == [
        "https://images.collections.yale.edu/iiif/2/ycba:image-id/full/!4096,4096/0/default.jpg",
        "https://images.collections.yale.edu/iiif/2/ycba:image-id/full/3400,/0/default.jpg",
        "https://images.collections.yale.edu/iiif/2/ycba:image-id/full/3000,/0/default.jpg",
        "https://images.collections.yale.edu/iiif/2/ycba:image-id/full/2500,/0/default.jpg",
        "https://images.collections.yale.edu/iiif/2/ycba:image-id/full/1600,/0/default.jpg",
        "https://images.collections.yale.edu/iiif/2/ycba:image-id/full/1200,/0/default.jpg",
    ]


def test_candidate_image_urls_keeps_smithsonian_download_url():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://ids.si.edu/ids/download?id=SAAM-1984.50_2.jpg") == [
        "https://ids.si.edu/ids/download?id=SAAM-1984.50_2.jpg",
    ]


def test_candidate_image_urls_splits_explicit_url_fallbacks():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://example.test/original.jpg|https://example.test/fallback.jpg") == [
        "https://example.test/original.jpg",
        "https://example.test/fallback.jpg",
    ]


def test_candidate_image_urls_keeps_met_original_image_url():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://images.metmuseum.org/CRDImages/ep/original/DP130999.jpg") == [
        "https://images.metmuseum.org/CRDImages/ep/original/DP130999.jpg",
    ]


def test_candidate_image_urls_adds_artic_iiif_size_fallbacks():
    from veduta_data.library_writer import candidate_image_urls

    assert candidate_image_urls("https://www.artic.edu/iiif/2/image-id/full/3400,/0/default.jpg") == [
        "https://www.artic.edu/iiif/2/image-id/full/4096,/0/default.jpg",
        "https://www.artic.edu/iiif/2/image-id/full/3400,/0/default.jpg",
        "https://www.artic.edu/iiif/2/image-id/full/3000,/0/default.jpg",
        "https://www.artic.edu/iiif/2/image-id/full/2500,/0/default.jpg",
        "https://www.artic.edu/iiif/2/image-id/full/1600,/0/default.jpg",
        "https://www.artic.edu/iiif/2/image-id/full/1200,/0/default.jpg",
        "https://www.artic.edu/iiif/2/image-id/full/843,/0/default.jpg",
    ]


def test_wallpaper_local_path_uses_jpg_for_wallpaper_assets():
    assert wallpaper_local_path(
        "cleveland",
        "artwork",
        "https://openaccess-cdn.clevelandart.org/1964.420/1964.420_full.tif",
    ) == "images/cleveland/artwork.jpg"
    assert wallpaper_local_path(
        "sample",
        "artwork",
        "https://example.test/image.png",
    ) == "images/sample/artwork.jpg"
    assert wallpaper_local_path(
        "chicago",
        "artwork",
        "https://www.artic.edu/iiif/2/image-id/full/4096,/0/default.jpg",
    ) == "images/chicago/artwork.jpg"


def test_write_json_leaves_existing_file_intact_if_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "nested" / "value.json"
    path.parent.mkdir()
    original = '{"original": true}\n'
    path.write_text(original, encoding="utf-8")

    def fail_replace(self, target):
        raise RuntimeError("replace interrupted")

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(RuntimeError, match="replace interrupted"):
        write_json(path, {"updated": True})

    assert path.read_text(encoding="utf-8") == original


def test_update_wallpaper_metadata_updates_matching_artwork(tmp_path):
    write_metadata_library(sample_library(), tmp_path)
    manifest = tmp_path / "collections" / "essentials.json"

    update_wallpaper_metadata(manifest, "artist-title", {
        "width": 6000,
        "height": 4000,
        "bytes": 123,
        "sha256": "abc",
        "downloadedFrom": "https://lh6.ggpht.com/example=s0",
    })

    collection = json.loads(manifest.read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    assert wallpaper["width"] == 6000
    assert wallpaper["height"] == 4000
    assert wallpaper["bytes"] == 123
    assert wallpaper["sha256"] == "abc"
    assert wallpaper["downloadedFrom"] == "https://lh6.ggpht.com/example=s0"


def test_update_wallpaper_metadata_removes_none_values(tmp_path):
    write_metadata_library(sample_library(), tmp_path)
    manifest = tmp_path / "collections" / "essentials.json"
    update_wallpaper_metadata(manifest, "artist-title", {
        "excluded": True,
        "exclusionReason": "old-reason",
    })

    update_wallpaper_metadata(manifest, "artist-title", {
        "width": 6000,
        "height": 4000,
        "excluded": None,
        "exclusionReason": None,
    })

    collection = json.loads(manifest.read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    assert wallpaper["width"] == 6000
    assert wallpaper["height"] == 4000
    assert "excluded" not in wallpaper
    assert "exclusionReason" not in wallpaper
