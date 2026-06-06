import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "archive" / "mark_lowres_artworks.py"
SPEC = importlib.util.spec_from_file_location("mark_lowres_artworks", SCRIPT_PATH)
mark_lowres_artworks = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mark_lowres_artworks)


def write_manifest(root: Path) -> None:
    (root / "collections").mkdir()
    (root / "images" / "sample").mkdir(parents=True)
    (root / "images" / "sample" / "low.jpg").write_bytes(b"low")
    (root / "images" / "sample" / "high.jpg").write_bytes(b"high")
    (root / "images" / "sample" / "already.jpg").write_bytes(b"already")
    (root / "collections" / "sample.json").write_text(json.dumps({
        "id": "sample",
        "artworks": [
            {
                "id": "low",
                "title": "Low",
                "creator": "Artist",
                "images": {
                    "wallpaper": {
                        "localPath": "images/sample/low.jpg",
                        "width": 1200,
                        "height": 800,
                        "downloadedFrom": "https://example.test/low.jpg",
                    }
                },
            },
            {
                "id": "high",
                "title": "High",
                "creator": "Artist",
                "images": {
                    "wallpaper": {
                        "localPath": "images/sample/high.jpg",
                        "width": 3000,
                        "height": 2000,
                    }
                },
            },
            {
                "id": "already",
                "title": "Already",
                "creator": "Artist",
                "images": {
                    "wallpaper": {
                        "localPath": "images/sample/already.jpg",
                        "width": 1000,
                        "height": 900,
                        "excluded": True,
                    }
                },
            },
            {
                "id": "missing",
                "title": "Missing",
                "creator": "Artist",
                "images": {
                    "wallpaper": {
                        "localPath": "images/sample/missing.jpg",
                        "width": 900,
                        "height": 700,
                    }
                },
            },
        ],
    }), encoding="utf-8")


def test_mark_lowres_artworks_excludes_only_downloaded_images_below_threshold(tmp_path):
    write_manifest(tmp_path)

    report = mark_lowres_artworks.mark_lowres_artworks(
        tmp_path,
        min_long_edge=2500,
        marked_at="2026-05-31T00:00:00Z",
    )

    assert report["count"] == 1
    assert report["items"][0]["id"] == "low"
    collection = json.loads((tmp_path / "collections" / "sample.json").read_text(encoding="utf-8"))
    by_id = {artwork["id"]: artwork for artwork in collection["artworks"]}
    low = by_id["low"]["images"]["wallpaper"]
    assert low["lowRes"] is True
    assert low["excluded"] is True
    assert low["exclusionReason"] == "existing-downloaded-image-below-wallpaper-threshold"
    assert low["markedLowResAt"] == "2026-05-31T00:00:00Z"
    assert low["rejectedLowRes"]["downloadedFrom"] == "https://example.test/low.jpg"
    assert (tmp_path / "images" / "sample" / "low.jpg").exists()
    assert "excluded" not in by_id["high"]["images"]["wallpaper"]
    assert by_id["already"]["images"]["wallpaper"]["excluded"] is True
    assert "excluded" not in by_id["missing"]["images"]["wallpaper"]


def test_mark_lowres_artworks_dry_run_does_not_write(tmp_path):
    write_manifest(tmp_path)

    report = mark_lowres_artworks.mark_lowres_artworks(tmp_path, dry_run=True)

    assert report["count"] == 1
    collection = json.loads((tmp_path / "collections" / "sample.json").read_text(encoding="utf-8"))
    low = collection["artworks"][0]["images"]["wallpaper"]
    assert "excluded" not in low
    assert not (tmp_path / "lowres_marked_report.json").exists()
