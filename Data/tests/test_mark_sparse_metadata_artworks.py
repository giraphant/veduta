import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "archive" / "mark_sparse_metadata_artworks.py"
SPEC = importlib.util.spec_from_file_location("mark_sparse_metadata_artworks", SCRIPT_PATH)
mark_sparse_metadata_artworks = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mark_sparse_metadata_artworks)


def artwork(artwork_id: str, title: str, creator: str, *, local: bool = True) -> dict:
    local_path = f"images/sample/{artwork_id}.jpg"
    return {
        "id": artwork_id,
        "title": title,
        "creator": creator,
        "sources": {"canonicalPage": f"https://example.test/{artwork_id}"},
        "images": {"wallpaper": {"localPath": local_path if local else f"images/sample/missing-{artwork_id}.jpg"}},
    }


def write_manifest(root: Path) -> None:
    (root / "collections").mkdir()
    (root / "images" / "sample").mkdir(parents=True)
    for name in ["good", "untitled", "unknown", "missing-canonical"]:
        (root / "images" / "sample" / f"{name}.jpg").write_bytes(b"image")
    sample = {
        "id": "sample",
        "artworks": [
            artwork("good", "River View", "Known Artist"),
            artwork("untitled", "Untitled painting (123)", "Known Artist"),
            artwork("unknown", "River View", "Unknown artist"),
            artwork("missing", "Untitled", "Unknown artist", local=False),
            {
                **artwork("missing-canonical", "River View", "Known Artist"),
                "sources": {"canonicalPage": ""},
            },
        ],
    }
    other = {
        "id": "other",
        "artworks": [artwork("other-low", "Untitled", "Unknown artist")],
    }
    (root / "collections" / "sample.json").write_text(json.dumps(sample), encoding="utf-8")
    (root / "collections" / "other.json").write_text(json.dumps(other), encoding="utf-8")


def test_mark_sparse_metadata_artworks_marks_only_downloaded_sparse_records_in_collection(tmp_path):
    write_manifest(tmp_path)

    report = mark_sparse_metadata_artworks.mark_sparse_metadata_artworks(
        tmp_path,
        collection_id="sample",
        marked_at="2026-06-01T00:00:00Z",
    )

    assert report["count"] == 3
    assert [item["id"] for item in report["items"]] == ["untitled", "unknown", "missing-canonical"]

    collection = json.loads((tmp_path / "collections" / "sample.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in collection["artworks"]}
    assert "excluded" not in by_id["good"]["images"]["wallpaper"]
    assert by_id["untitled"]["images"]["wallpaper"]["metadataIssues"] == ["placeholder-title"]
    assert by_id["unknown"]["images"]["wallpaper"]["metadataIssues"] == ["placeholder-creator"]
    assert by_id["missing-canonical"]["images"]["wallpaper"]["metadataIssues"] == ["missing-canonical-page"]
    assert "excluded" not in by_id["missing"]["images"]["wallpaper"]

    other = json.loads((tmp_path / "collections" / "other.json").read_text(encoding="utf-8"))
    assert "excluded" not in other["artworks"][0]["images"]["wallpaper"]


def test_mark_sparse_metadata_artworks_dry_run_does_not_write(tmp_path):
    write_manifest(tmp_path)

    report = mark_sparse_metadata_artworks.mark_sparse_metadata_artworks(tmp_path, collection_id="sample", dry_run=True)

    assert report["count"] == 3
    collection = json.loads((tmp_path / "collections" / "sample.json").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in collection["artworks"]}
    assert "excluded" not in by_id["untitled"]["images"]["wallpaper"]
    assert not (tmp_path / "sparse_metadata_marked_report_sample.json").exists()
