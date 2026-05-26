import json
from pathlib import Path

from openartpaper_data import cli
from openartpaper_data import installed_packs


def write_library(root: Path, artworks: list[dict[str, object]]) -> None:
    (root / "collections").mkdir(parents=True)
    (root / "catalog.json").write_text(json.dumps({
        "collections": [{
            "id": "essentials",
            "manifest": "collections/essentials.json",
        }],
    }), encoding="utf-8")
    (root / "collections" / "essentials.json").write_text(json.dumps({
        "id": "essentials",
        "artworks": artworks,
    }), encoding="utf-8")


def artwork(artwork_id: str, source_index: int) -> dict[str, object]:
    return {
        "id": artwork_id,
        "images": {
            "wallpaper": {
                "localPath": f"images/essentials/{artwork_id}.jpg",
            },
        },
        "source": {
            "artpaperPackId": 0,
            "artpaperIndex": source_index,
        },
    }


def test_installed_pack_image_path_uses_5k_pack_layout(tmp_path):
    assert installed_packs.installed_pack_image_path(tmp_path, 0, 63, "5k") == tmp_path / "5k_pack_0" / "0" / "63.jpg"


def test_import_installed_pack_images_copies_by_artpaper_index_and_updates_metadata(tmp_path, monkeypatch):
    library_root = tmp_path / "library"
    artpaper_root = tmp_path / "artpaper"
    write_library(library_root, [artwork("monet", 63)])
    source = artpaper_root / "5k_pack_0" / "0" / "63.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"installed-image-bytes")
    stale_destination = library_root / "images" / "essentials" / "monet.jpg"
    stale_destination.parent.mkdir(parents=True)
    stale_destination.write_bytes(b"stale")

    monkeypatch.setattr(installed_packs, "image_dimensions", lambda path: (4800, 2700))

    summary = installed_packs.import_installed_pack_images(
        library_root=library_root,
        artpaper_image_root=artpaper_root,
        quality="5k",
        collection_id="essentials",
    )

    assert summary.copied_count == 1
    assert summary.missing_count == 0
    assert stale_destination.read_bytes() == b"installed-image-bytes"
    collection = json.loads((library_root / "collections" / "essentials.json").read_text(encoding="utf-8"))
    wallpaper = collection["artworks"][0]["images"]["wallpaper"]
    assert wallpaper["width"] == 4800
    assert wallpaper["height"] == 2700
    assert wallpaper["bytes"] == len(b"installed-image-bytes")
    assert wallpaper["sha256"] == "d658cf6bf1ac268e23ab11d8614521931308ccc1f13932a8ee15b6a7d6a46d33"
    assert wallpaper["importedFromArtPaperPack"] == str(source)


def test_cli_import_installed_packs_returns_nonzero_for_missing_selected_collection(tmp_path, monkeypatch):
    library_root = tmp_path / "library"
    artpaper_root = tmp_path / "artpaper"
    write_library(library_root, [artwork("missing", 63)])
    monkeypatch.setattr(installed_packs, "image_dimensions", lambda path: (4800, 2700))

    result = cli.main([
        "import-installed-packs",
        "--library-root", str(library_root),
        "--artpaper-image-root", str(artpaper_root),
        "--collection", "essentials",
    ])

    assert result == 1


def test_cli_import_installed_packs_returns_zero_when_selected_collection_copied(tmp_path, monkeypatch):
    library_root = tmp_path / "library"
    artpaper_root = tmp_path / "artpaper"
    write_library(library_root, [artwork("copied", 63)])
    source = artpaper_root / "5k_pack_0" / "0" / "63.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"installed-image-bytes")
    monkeypatch.setattr(installed_packs, "image_dimensions", lambda path: (4800, 2700))

    result = cli.main([
        "import-installed-packs",
        "--library-root", str(library_root),
        "--artpaper-image-root", str(artpaper_root),
        "--collection", "essentials",
    ])

    assert result == 0
