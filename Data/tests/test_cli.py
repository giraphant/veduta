import json
from pathlib import Path

from veduta_data import cli
from veduta_data.models import SourceArtwork, SourceCollection, SourceLibrary


def write_library(
    root: Path,
    artwork_ids: list[str],
    fallback_url_template: str = "https://example.com/{artwork_id}=s0",
) -> None:
    (root / "collections").mkdir(parents=True)
    (root / "catalog.json").write_text(json.dumps({
        "collections": [{
            "id": "essentials",
            "manifest": "collections/essentials.json",
        }],
    }), encoding="utf-8")
    (root / "collections" / "essentials.json").write_text(json.dumps({
        "id": "essentials",
        "artworks": [
            {
                "id": artwork_id,
                "images": {
                    "wallpaper": {
                        "localPath": f"images/essentials/{artwork_id}.jpg",
                        "fallbackUrls": [fallback_url_template.format(artwork_id=artwork_id)],
                    },
                },
                "sources": {
                    "canonicalPage": f"https://artsandculture.google.com/asset/{artwork_id}/google-id",
                },
            }
            for artwork_id in artwork_ids
        ],
    }), encoding="utf-8")


def test_classify_artwork_kinds_updates_selected_collection(tmp_path):
    write_library(tmp_path, ["flat"])
    catalog_path = tmp_path / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["collections"].append({"id": "graffitimundo", "manifest": "collections/graffitimundo.json"})
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    (tmp_path / "collections" / "graffitimundo.json").write_text(json.dumps({
        "id": "graffitimundo",
        "artworks": [{
            "id": "mural",
            "title": "Mural",
            "creator": "Blu",
            "images": {"wallpaper": {"localPath": "images/graffitimundo/mural.jpg", "fallbackUrls": []}},
            "sources": {"canonicalPage": "https://example.com/mural"},
        }],
    }), encoding="utf-8")

    result = cli.main(["classify-artwork-kinds", "--library-root", str(tmp_path), "--collection", "graffitimundo"])

    assert result == 0
    flat_collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    street_collection = json.loads((tmp_path / "collections" / "graffitimundo.json").read_text(encoding="utf-8"))
    assert "classification" not in flat_collection["artworks"][0]
    assert street_collection["artworks"][0]["classification"] == {"kind": "street-art"}


def test_classify_artwork_kinds_updates_all_collections(tmp_path):
    write_library(tmp_path, ["flat"])
    catalog_path = tmp_path / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["collections"].append({"id": "photo", "manifest": "collections/photo.json"})
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    (tmp_path / "collections" / "photo.json").write_text(json.dumps({
        "id": "photo",
        "artworks": [{
            "id": "print",
            "title": "Gelatin silver photograph",
            "creator": "Unknown",
            "classification": {"kind": "flat-art"},
            "images": {"wallpaper": {"localPath": "images/photo/print.jpg", "fallbackUrls": []}},
            "sources": {"canonicalPage": "https://example.com/print"},
        }],
    }), encoding="utf-8")

    result = cli.main(["classify-artwork-kinds", "--library-root", str(tmp_path), "--all"])

    assert result == 0
    flat_collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    photo_collection = json.loads((tmp_path / "collections" / "photo.json").read_text(encoding="utf-8"))
    assert flat_collection["artworks"][0]["classification"] == {"kind": "flat-art"}
    assert photo_collection["artworks"][0]["classification"] == {"kind": "photography"}


def cleveland_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="cleveland",
            source_pack_id=1001,
            short_name="Cleveland",
            title="Cleveland Museum of Art",
            expected_artwork_count=1,
            source_sizes_mb={},
            artworks=[
                SourceArtwork(
                    id="thomas-eakins-the-biglin-brothers-turning-the-stake",
                    title="The Biglin Brothers Turning the Stake",
                    creator="Thomas Eakins",
                    attribution="Cleveland Museum of Art",
                    canonical_page="https://clevelandart.org/art/1927.1984",
                    artist_page=None,
                    upstream_image_base="https://openaccess-cdn.clevelandart.org/1927.1984/1927.1984_print.jpg",
                    source_pack_id=1001,
                    source_index=0,
                )
            ],
        )
    ])


def chicago_api_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="chicago",
            source_pack_id=1002,
            short_name="Chicago",
            title="The Art Institute of Chicago",
            expected_artwork_count=1,
            source_sizes_mb={},
            artworks=[
                SourceArtwork(
                    id="claude-monet-arrival-of-the-normandy-train-gare-saint-lazare",
                    title="Arrival of the Normandy Train, Gare Saint-Lazare",
                    creator="Claude Monet",
                    attribution="The Art Institute of Chicago",
                    canonical_page="https://www.artic.edu/artworks/16571",
                    artist_page=None,
                    upstream_image_base="https://www.artic.edu/iiif/2/monet-image-id/full/3400,/0/default.jpg",
                    source_pack_id=1002,
                    source_index=0,
                )
            ],
        )
    ])


def nga_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="nga",
            source_pack_id=1004,
            short_name="NGA",
            title="National Gallery of Art",
            expected_artwork_count=1,
            source_sizes_mb={},
            artworks=[
                SourceArtwork(
                    id="claude-monet-the-japanese-footbridge",
                    title="The Japanese Footbridge",
                    creator="Claude Monet",
                    attribution="National Gallery of Art",
                    canonical_page="https://www.nga.gov/collection/art-object-page.1111.html",
                    artist_page=None,
                    upstream_image_base="https://api.nga.gov/iiif/monet-image-id/full/3400,/0/default.jpg",
                    source_pack_id=1004,
                    source_index=0,
                )
            ],
        )
    ])


def harvard_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="harvard",
            source_pack_id=1005,
            short_name="Harvard",
            title="Harvard Art Museums",
            expected_artwork_count=1,
            source_sizes_mb={},
            artworks=[
                SourceArtwork(
                    id="claude-monet-water-lilies",
                    title="Water Lilies",
                    creator="Claude Monet",
                    attribution="Harvard Art Museums",
                    canonical_page="https://harvardartmuseums.org/collections/object/1111",
                    artist_page=None,
                    upstream_image_base="https://ids.lib.harvard.edu/ids/iiif/monet-image-id/full/3400,/0/default.jpg",
                    source_pack_id=1005,
                    source_index=0,
                )
            ],
        )
    ])


def test_import_nga_writes_collection_manifest(tmp_path, monkeypatch):
    calls = []

    def fake_import_nga_api(*, fetch_limit, keep_limit, min_long_edge):
        calls.append((fetch_limit, keep_limit, min_long_edge))
        return nga_library()

    monkeypatch.setattr(cli, "import_nga_api", fake_import_nga_api)

    result = cli.main([
        "import-nga",
        "--library-root", str(tmp_path),
        "--fetch-limit", "25",
        "--limit", "5",
        "--min-long-edge", "3200",
    ])

    assert result == 0
    assert calls == [(25, 5, 3200)]
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["collections"][0]["id"] == "nga"
    collection = json.loads((tmp_path / "collections" / "nga.json").read_text(encoding="utf-8"))
    assert collection["title"] == "National Gallery of Art"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://api.nga.gov/iiif/monet-image-id/full/4096,/0/default.jpg",
        "https://api.nga.gov/iiif/monet-image-id/full/3400,/0/default.jpg",
        "https://api.nga.gov/iiif/monet-image-id/full/3000,/0/default.jpg",
        "https://api.nga.gov/iiif/monet-image-id/full/2500,/0/default.jpg",
        "https://api.nga.gov/iiif/monet-image-id/full/1600,/0/default.jpg",
        "https://api.nga.gov/iiif/monet-image-id/full/1200,/0/default.jpg",
    ]


def test_import_harvard_writes_collection_manifest(tmp_path, monkeypatch):
    calls = []

    def fake_import_harvard_api(*, api_key, fetch_limit, keep_limit, min_long_edge):
        calls.append((api_key, fetch_limit, keep_limit, min_long_edge))
        return harvard_library()

    monkeypatch.setattr(cli, "import_harvard_api", fake_import_harvard_api)

    result = cli.main([
        "import-harvard",
        "--library-root", str(tmp_path),
        "--api-key", "test-key",
        "--fetch-limit", "25",
        "--limit", "5",
        "--min-long-edge", "3200",
    ])

    assert result == 0
    assert calls == [("test-key", 25, 5, 3200)]
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["collections"][0]["id"] == "harvard"
    collection = json.loads((tmp_path / "collections" / "harvard.json").read_text(encoding="utf-8"))
    assert collection["title"] == "Harvard Art Museums"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://ids.lib.harvard.edu/ids/iiif/monet-image-id/full/3400,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/monet-image-id/full/3000,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/monet-image-id/full/2500,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/monet-image-id/full/1600,/0/default.jpg",
        "https://ids.lib.harvard.edu/ids/iiif/monet-image-id/full/1200,/0/default.jpg",
    ]


def test_import_harvard_requires_api_key(tmp_path, monkeypatch, capsys):
    def fake_import_harvard_api(**kwargs):
        raise AssertionError("import should not be attempted")

    monkeypatch.setattr(cli, "import_harvard_api", fake_import_harvard_api)

    result = cli.main(["import-harvard", "--library-root", str(tmp_path), "--api-key", ""])

    captured = capsys.readouterr()
    assert result == 1
    assert "HARVARD_ART_MUSEUMS_API_KEY" in captured.err
    assert not (tmp_path / "catalog.json").exists()


def smithsonian_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="smithsonian",
            source_pack_id=1006,
            short_name="Smithsonian",
            title="Smithsonian American Art Museum",
            expected_artwork_count=1,
            source_sizes_mb={},
            artworks=[
                SourceArtwork(
                    id="winslow-homer-breezing-up",
                    title="Breezing Up",
                    creator="Winslow Homer",
                    attribution="Smithsonian American Art Museum",
                    canonical_page="https://americanart.si.edu/collections/search/artwork/?id=99999",
                    artist_page=None,
                    upstream_image_base="https://ids.si.edu/ids/download?id=SAAM-1893.3_1.jpg",
                    source_pack_id=1006,
                    source_index=0,
                )
            ],
        )
    ])


def test_import_smithsonian_writes_collection_manifest(tmp_path, monkeypatch):
    calls = []

    def fake_import_smithsonian_api(*, fetch_limit, keep_limit, min_long_edge, max_files):
        calls.append((fetch_limit, keep_limit, min_long_edge, max_files))
        return smithsonian_library()

    monkeypatch.setattr(cli, "import_smithsonian_api", fake_import_smithsonian_api)

    result = cli.main([
        "import-smithsonian",
        "--library-root", str(tmp_path),
        "--fetch-limit", "50",
        "--limit", "5",
        "--min-long-edge", "3200",
        "--max-files", "128",
    ])

    assert result == 0
    assert calls == [(50, 5, 3200, 128)]
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["collections"][0]["id"] == "smithsonian"
    collection = json.loads((tmp_path / "collections" / "smithsonian.json").read_text(encoding="utf-8"))
    assert collection["title"] == "Smithsonian American Art Museum"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://ids.si.edu/ids/download?id=SAAM-1893.3_1.jpg",
    ]


def vam_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="vam",
            source_pack_id=1007,
            short_name="V&A",
            title="Victoria and Albert Museum",
            expected_artwork_count=1,
            source_sizes_mb={},
            artworks=[
                SourceArtwork(
                    id="j-m-w-turner-a-river-landscape",
                    title="A River Landscape",
                    creator="J. M. W. Turner",
                    attribution="Victoria and Albert Museum",
                    canonical_page="https://collections.vam.ac.uk/item/O16861/",
                    artist_page=None,
                    upstream_image_base="https://framemark.vam.ac.uk/collections/2011EV9123/full/3400,/0/default.jpg",
                    source_pack_id=1007,
                    source_index=0,
                )
            ],
        )
    ])


def test_import_vam_writes_collection_manifest(tmp_path, monkeypatch):
    calls = []

    def fake_import_vam_api(*, fetch_limit, keep_limit, min_long_edge, max_per_creator):
        calls.append((fetch_limit, keep_limit, min_long_edge, max_per_creator))
        return vam_library()

    monkeypatch.setattr(cli, "import_vam_api", fake_import_vam_api)

    result = cli.main([
        "import-vam",
        "--library-root", str(tmp_path),
        "--fetch-limit", "50",
        "--limit", "5",
        "--min-long-edge", "2500",
    ])

    assert result == 0
    assert calls == [(50, 5, 2500, 3)]
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["collections"][0]["id"] == "vam"
    collection = json.loads((tmp_path / "collections" / "vam.json").read_text(encoding="utf-8"))
    assert collection["title"] == "Victoria and Albert Museum"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://framemark.vam.ac.uk/collections/2011EV9123/full/4096,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/2011EV9123/full/3400,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/2011EV9123/full/3000,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/2011EV9123/full/2500,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/2011EV9123/full/1600,/0/default.jpg",
        "https://framemark.vam.ac.uk/collections/2011EV9123/full/1200,/0/default.jpg",
    ]


def met_library() -> SourceLibrary:
    return SourceLibrary(collections=[
        SourceCollection(
            id="met",
            source_pack_id=1003,
            short_name="Met",
            title="The Metropolitan Museum of Art",
            expected_artwork_count=1,
            source_sizes_mb={},
            artworks=[
                SourceArtwork(
                    id="vincent-van-gogh-cypresses",
                    title="Cypresses",
                    creator="Vincent van Gogh",
                    attribution="The Metropolitan Museum of Art",
                    canonical_page="https://www.metmuseum.org/art/collection/search/437980",
                    artist_page=None,
                    upstream_image_base="https://images.metmuseum.org/CRDImages/ep/original/DP130999.jpg|https://images.metmuseum.org/CRDImages/ep/web-large/DP130999.jpg",
                    source_pack_id=1003,
                    source_index=0,
                )
            ],
        )
    ])


def test_import_met_writes_collection_manifest(tmp_path, monkeypatch):
    calls = []

    def fake_import_met_api(*, fetch_limit, keep_limit):
        calls.append((fetch_limit, keep_limit))
        return met_library()

    monkeypatch.setattr(cli, "import_met_api", fake_import_met_api)

    result = cli.main([
        "import-met",
        "--library-root", str(tmp_path),
        "--fetch-limit", "25",
        "--limit", "5",
    ])

    assert result == 0
    assert calls == [(25, 5)]
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["collections"][0]["id"] == "met"
    collection = json.loads((tmp_path / "collections" / "met.json").read_text(encoding="utf-8"))
    assert collection["title"] == "The Metropolitan Museum of Art"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://images.metmuseum.org/CRDImages/ep/original/DP130999.jpg",
        "https://images.metmuseum.org/CRDImages/ep/web-large/DP130999.jpg",
    ]


def test_import_chicago_api_writes_collection_manifest(tmp_path, monkeypatch):
    calls = []

    def fake_import_chicago_api(*, fetch_limit, keep_limit, min_long_edge):
        calls.append((fetch_limit, keep_limit, min_long_edge))
        return chicago_api_library()

    monkeypatch.setattr(cli, "import_chicago_api", fake_import_chicago_api)

    result = cli.main([
        "import-chicago-api",
        "--library-root", str(tmp_path),
        "--fetch-limit", "25",
        "--limit", "5",
        "--min-long-edge", "3200",
    ])

    assert result == 0
    assert calls == [(25, 5, 3200)]
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["collections"][0]["id"] == "chicago"
    collection = json.loads((tmp_path / "collections" / "chicago.json").read_text(encoding="utf-8"))
    assert collection["title"] == "The Art Institute of Chicago"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://www.artic.edu/iiif/2/monet-image-id/full/4096,/0/default.jpg",
        "https://www.artic.edu/iiif/2/monet-image-id/full/3400,/0/default.jpg",
        "https://www.artic.edu/iiif/2/monet-image-id/full/3000,/0/default.jpg",
        "https://www.artic.edu/iiif/2/monet-image-id/full/2500,/0/default.jpg",
        "https://www.artic.edu/iiif/2/monet-image-id/full/1600,/0/default.jpg",
        "https://www.artic.edu/iiif/2/monet-image-id/full/1200,/0/default.jpg",
        "https://www.artic.edu/iiif/2/monet-image-id/full/843,/0/default.jpg",
    ]


def test_import_chicago_api_removes_legacy_chicago_api_collection(tmp_path, monkeypatch):
    write_library(tmp_path, ["existing-artwork"])
    catalog_path = tmp_path / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["collections"].append({"id": "chicago-api", "manifest": "collections/chicago-api.json"})
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    (tmp_path / "collections" / "chicago-api.json").write_text(json.dumps({"id": "chicago-api", "artworks": []}), encoding="utf-8")

    def fake_import_chicago_api(*, fetch_limit, keep_limit, min_long_edge):
        return chicago_api_library()

    monkeypatch.setattr(cli, "import_chicago_api", fake_import_chicago_api)

    result = cli.main(["import-chicago-api", "--library-root", str(tmp_path), "--fetch-limit", "1", "--limit", "1"])

    assert result == 0
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert [collection["id"] for collection in catalog["collections"]] == ["essentials", "chicago"]
    assert not (tmp_path / "collections" / "chicago-api.json").exists()


def test_import_cleveland_writes_collection_manifest(tmp_path, monkeypatch):
    calls = []

    def fake_import_cleveland_api(*, fetch_limit, keep_limit, min_long_edge, highlights_only):
        calls.append((fetch_limit, keep_limit, min_long_edge, highlights_only))
        return cleveland_library()

    monkeypatch.setattr(cli, "import_cleveland_api", fake_import_cleveland_api)

    result = cli.main([
        "import-cleveland",
        "--library-root", str(tmp_path),
        "--fetch-limit", "25",
        "--limit", "5",
        "--min-long-edge", "3200",
    ])

    assert result == 0
    assert calls == [(25, 5, 3200, True)]
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["collections"][0]["id"] == "cleveland"
    collection = json.loads((tmp_path / "collections" / "cleveland.json").read_text(encoding="utf-8"))
    assert collection["title"] == "Cleveland Museum of Art"
    assert collection["artworks"][0]["images"]["wallpaper"]["fallbackUrls"] == [
        "https://openaccess-cdn.clevelandart.org/1927.1984/1927.1984_print.jpg",
    ]


def test_import_cleveland_preserves_existing_collections(tmp_path, monkeypatch):
    write_library(tmp_path, ["existing-artwork"])

    def fake_import_cleveland_api(*, fetch_limit, keep_limit, min_long_edge, highlights_only):
        return cleveland_library()

    monkeypatch.setattr(cli, "import_cleveland_api", fake_import_cleveland_api)

    result = cli.main(["import-cleveland", "--library-root", str(tmp_path), "--fetch-limit", "1", "--limit", "1"])

    assert result == 0
    catalog = json.loads((tmp_path / "catalog.json").read_text(encoding="utf-8"))
    assert [collection["id"] for collection in catalog["collections"]] == ["essentials", "cleveland"]
    assert (tmp_path / "collections" / "essentials.json").exists()
    assert (tmp_path / "collections" / "cleveland.json").exists()


def test_download_returns_failure_when_any_artwork_fails_and_writes_current_failure(tmp_path, monkeypatch):
    write_library(tmp_path, ["success", "failure"])
    calls = []

    def fake_download(urls, destination, delay):
        calls.append(destination)
        if destination.name == "failure.jpg":
            raise RuntimeError("download failed")
        return {
            "status": "downloaded",
            "width": 6000,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": urls[0],
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)
    monkeypatch.setattr(cli.time, "sleep", lambda delay: None)

    result = cli.main(["download", "--library-root", str(tmp_path), "--collection", "essentials", "--delay", "0"])

    assert result == 1
    assert len(calls) == 2
    failure_lines = (tmp_path / "failures.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(failure_lines) == 1
    failure = json.loads(failure_lines[0])
    assert failure == {
        "collection": "essentials",
        "artwork": "failure",
        "error": "download failed",
    }

    collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    assert wallpaper["width"] == 6000
    assert wallpaper["height"] == 4000
    assert wallpaper["bytes"] == 123
    assert wallpaper["sha256"] == "abc"
    assert wallpaper["downloadedFrom"] == "https://example.com/success=s0"


def test_download_marks_low_resolution_success_as_excluded(tmp_path, monkeypatch):
    write_library(tmp_path, ["tiny"])

    def fake_download(urls, destination, delay):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"tiny")
        return {
            "status": "downloaded",
            "width": 466,
            "height": 624,
            "bytes": 4,
            "sha256": "tiny-sha",
            "url": urls[0],
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)
    monkeypatch.setattr(cli.time, "sleep", lambda delay: None)

    result = cli.main(["download", "--library-root", str(tmp_path), "--collection", "essentials", "--delay", "0"])

    assert result == 0
    collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    assert wallpaper["lowRes"] is True
    assert wallpaper["excluded"] is True
    assert wallpaper["exclusionReason"] == "downloaded-image-below-wallpaper-threshold"
    assert not (tmp_path / "images" / "essentials" / "tiny.jpg").exists()


def test_download_clears_stale_failures_when_run_has_no_failures(tmp_path, monkeypatch):
    write_library(tmp_path, ["success"])
    failures_path = tmp_path / "failures.jsonl"
    failures_path.write_text('{"stale": true}\n', encoding="utf-8")

    def fake_download(urls, destination, delay):
        return {
            "status": "downloaded",
            "width": 6000,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": urls[0],
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)
    monkeypatch.setattr(cli.time, "sleep", lambda delay: None)

    result = cli.main(["download", "--library-root", str(tmp_path), "--collection", "essentials", "--delay", "0"])

    assert result == 0
    assert not failures_path.exists()


def test_download_limit_stops_after_success_count(tmp_path, monkeypatch):
    write_library(tmp_path, ["first", "second", "third"])
    calls = []

    def fake_download(urls, destination, delay):
        calls.append(destination.name)
        return {
            "status": "downloaded",
            "width": 6000,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": urls[0],
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)
    monkeypatch.setattr(cli.time, "sleep", lambda delay: None)

    result = cli.main([
        "download",
        "--library-root", str(tmp_path),
        "--collection", "essentials",
        "--delay", "0",
        "--limit", "2",
    ])

    assert result == 0
    assert calls == ["first.jpg", "second.jpg"]
    collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    assert "width" in collection["artworks"][0]["images"]["wallpaper"]
    assert "width" in collection["artworks"][1]["images"]["wallpaper"]
    assert "width" not in collection["artworks"][2]["images"]["wallpaper"]


def test_download_limit_skips_completed_high_resolution_artworks(tmp_path, monkeypatch):
    write_library(tmp_path, ["first", "second"])
    collection_path = tmp_path / "collections" / "essentials.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    first_wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    first_wallpaper["width"] = 6000
    first_wallpaper["height"] = 4000
    first_path = tmp_path / first_wallpaper["localPath"]
    first_path.parent.mkdir(parents=True)
    first_path.write_bytes(b"done")
    collection_path.write_text(json.dumps(collection), encoding="utf-8")
    calls = []

    def fake_download(urls, destination, delay):
        calls.append(destination.name)
        return {
            "status": "downloaded",
            "width": 6000,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": urls[0],
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)
    monkeypatch.setattr(cli.time, "sleep", lambda delay: None)

    result = cli.main([
        "download",
        "--library-root", str(tmp_path),
        "--collection", "essentials",
        "--delay", "0",
        "--limit", "1",
    ])

    assert result == 0
    assert calls == ["second.jpg"]


def test_download_skips_excluded_non_pending_artworks(tmp_path, monkeypatch):
    write_library(tmp_path, ["invalid", "pending"])
    collection_path = tmp_path / "collections" / "essentials.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    invalid_wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    invalid_wallpaper["excluded"] = True
    invalid_wallpaper["exclusionReason"] = "invalid-downloaded-image"
    pending_wallpaper = collection["artworks"][1]["images"]["wallpaper"]
    pending_wallpaper["excluded"] = True
    pending_wallpaper["exclusionReason"] = "pending-slow-download"
    collection_path.write_text(json.dumps(collection), encoding="utf-8")
    calls = []

    def fake_download(urls, destination, delay):
        calls.append(destination.name)
        return {
            "status": "downloaded",
            "width": 6000,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": urls[0],
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)
    monkeypatch.setattr(cli.time, "sleep", lambda delay: None)

    result = cli.main([
        "download",
        "--library-root", str(tmp_path),
        "--collection", "essentials",
        "--delay", "0",
        "--limit", "1",
    ])

    assert result == 0
    assert calls == ["pending.jpg"]


def test_download_records_fallback_url_when_existing_pending_file_is_skipped(tmp_path, monkeypatch):
    write_library(tmp_path, ["pending"])
    collection_path = tmp_path / "collections" / "essentials.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    wallpaper["excluded"] = True
    wallpaper["exclusionReason"] = "pending-slow-download"
    collection_path.write_text(json.dumps(collection), encoding="utf-8")

    def fake_download(urls, destination, delay):
        return {
            "status": "skipped",
            "width": 6000,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": None,
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)
    monkeypatch.setattr(cli.time, "sleep", lambda delay: None)

    result = cli.main([
        "download",
        "--library-root", str(tmp_path),
        "--collection", "essentials",
        "--delay", "0",
    ])

    assert result == 0
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    assert wallpaper["downloadedFrom"] == "https://example.com/pending=s0"
    assert "excluded" not in wallpaper


def test_download_rejects_non_http_fallbacks_before_attempting_download(tmp_path, monkeypatch, capsys):
    write_library(tmp_path, ["local-filename"], fallback_url_template="0.jpg=s0")

    def fake_download(urls, destination, delay):
        raise AssertionError("download should not be attempted")

    monkeypatch.setattr(cli, "download_first_working", fake_download)

    result = cli.main(["download", "--library-root", str(tmp_path), "--collection", "essentials", "--delay", "0"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Cannot download collection essentials" in captured.err
    assert "local-filename" in captured.err
    assert not (tmp_path / "failures.jsonl").exists()


def test_download_all_preflights_every_collection_before_downloading(tmp_path, monkeypatch):
    write_library(tmp_path, ["success"])
    catalog_path = tmp_path / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["collections"].append({"id": "local-pack", "manifest": "collections/local-pack.json"})
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    (tmp_path / "collections" / "local-pack.json").write_text(json.dumps({
        "id": "local-pack",
        "artworks": [{
            "id": "local-filename",
            "images": {
                "wallpaper": {
                    "localPath": "images/local-pack/local-filename.jpg",
                    "fallbackUrls": ["0.jpg=s0"],
                },
            },
        }],
    }), encoding="utf-8")
    calls = []

    def fake_download(urls, destination, delay):
        calls.append(destination)
        return {
            "status": "downloaded",
            "width": 6000,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": urls[0],
        }

    monkeypatch.setattr(cli, "download_first_working", fake_download)

    result = cli.main(["download", "--library-root", str(tmp_path), "--all", "--delay", "0"])

    assert result == 1
    assert calls == []


def test_dezoomify_google_arts_updates_wallpaper_metadata(tmp_path, monkeypatch):
    write_library(tmp_path, ["success"])
    calls = []

    def fake_dezoomify(canonical_page, destination, **kwargs):
        calls.append((canonical_page, destination, kwargs))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"image")
        return {
            "width": 5547,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": canonical_page,
        }

    monkeypatch.setattr(cli, "dezoomify_google_arts", fake_dezoomify)

    result = cli.main([
        "dezoomify-google-arts",
        "--library-root", str(tmp_path),
        "--collection", "essentials",
        "--limit", "1",
        "--min-width", "2500",
    ])

    assert result == 0
    assert calls[0][0] == "https://artsandculture.google.com/asset/success/google-id"
    assert calls[0][1] == tmp_path / "images/essentials/success.jpg"
    collection = json.loads((tmp_path / "collections" / "essentials.json").read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    assert wallpaper["width"] == 5547
    assert wallpaper["height"] == 4000
    assert wallpaper["bytes"] == 123
    assert wallpaper["sha256"] == "abc"
    assert wallpaper["downloadedFrom"] == "https://artsandculture.google.com/asset/success/google-id"


def test_dezoomify_google_arts_limit_bounds_processed_artworks(tmp_path, monkeypatch):
    write_library(tmp_path, ["first", "second"])
    calls = []

    def fake_dezoomify(canonical_page, destination, **kwargs):
        calls.append(canonical_page)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"image")
        return {
            "width": 5547,
            "height": 4000,
            "bytes": 123,
            "sha256": "abc",
            "url": canonical_page,
        }

    monkeypatch.setattr(cli, "dezoomify_google_arts", fake_dezoomify)

    result = cli.main([
        "dezoomify-google-arts",
        "--library-root", str(tmp_path),
        "--collection", "essentials",
        "--limit", "1",
    ])

    assert result == 0
    assert calls == ["https://artsandculture.google.com/asset/first/google-id"]
