import json
from pathlib import Path

from openartpaper_data import cli


def write_library(root: Path, artwork_ids: list[str]) -> None:
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
                        "fallbackUrls": [f"https://example.com/{artwork_id}=s0"],
                    },
                },
            }
            for artwork_id in artwork_ids
        ],
    }), encoding="utf-8")


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
