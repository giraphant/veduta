import json
from pathlib import Path

from veduta_data import cli


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
            "title": "Untitled",
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
