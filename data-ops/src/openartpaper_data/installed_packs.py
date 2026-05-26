import json
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from openartpaper_data.downloader import image_dimensions, sha256_file
from openartpaper_data.library_writer import update_wallpaper_metadata

QUALITY_DIR_PREFIXES = {
    "5k": "5k_pack",
    "hd": "hd_pack",
    "regular": "pack",
}


def default_artpaper_image_root() -> Path:
    return Path.home() / "Library" / "Containers" / "andriiliakh.Artpaper" / "Data" / "Documents" / "Artpaperimg"


def installed_pack_image_path(artpaper_image_root: Path, pack_id: int, source_index: int, quality: str) -> Path:
    try:
        prefix = QUALITY_DIR_PREFIXES[quality]
    except KeyError as error:
        raise ValueError(f"Unsupported quality: {quality}") from error
    return artpaper_image_root / f"{prefix}_{pack_id}" / str(pack_id) / f"{source_index}.jpg"


@dataclass
class MissingInstalledImage:
    collection_id: str
    artwork_id: str
    source_path: Path


@dataclass
class InstalledPackImportSummary:
    copied_count: int = 0
    missing: list[MissingInstalledImage] = field(default_factory=list)

    @property
    def missing_count(self) -> int:
        return len(self.missing)


def _load_catalog(library_root: Path) -> dict[str, object]:
    return json.loads((library_root / "catalog.json").read_text(encoding="utf-8"))


def _load_collection(library_root: Path, manifest: str) -> dict[str, object]:
    return json.loads((library_root / manifest).read_text(encoding="utf-8"))


def _selected_collections(catalog: dict[str, object], collection_id: str | None) -> list[dict[str, object]]:
    collections = list(catalog["collections"])
    if collection_id is None:
        return collections
    matches = [collection for collection in collections if collection["id"] == collection_id]
    if not matches:
        available = ", ".join(str(collection["id"]) for collection in collections)
        raise ValueError(f"Unknown collection {collection_id}. Available: {available}")
    return matches


def _copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            with source.open("rb") as source_file:
                shutil.copyfileobj(source_file, temp_file, length=1024 * 1024)
        temp_path.replace(destination)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def import_installed_pack_images(
    *,
    library_root: Path,
    artpaper_image_root: Path,
    quality: str = "5k",
    collection_id: str | None = None,
) -> InstalledPackImportSummary:
    library_root = library_root.expanduser()
    artpaper_image_root = artpaper_image_root.expanduser()
    catalog = _load_catalog(library_root)
    summary = InstalledPackImportSummary()

    for collection_summary in _selected_collections(catalog, collection_id):
        manifest = str(collection_summary["manifest"])
        manifest_path = library_root / manifest
        collection = _load_collection(library_root, manifest)
        current_collection_id = str(collection["id"])
        for artwork in collection["artworks"]:
            source_info = artwork["source"]
            pack_id = int(source_info["artpaperPackId"])
            source_index = int(source_info["artpaperIndex"])
            source_path = installed_pack_image_path(artpaper_image_root, pack_id, source_index, quality)
            artwork_id = str(artwork["id"])
            if not source_path.exists():
                summary.missing.append(MissingInstalledImage(current_collection_id, artwork_id, source_path))
                continue

            destination = library_root / str(artwork["images"]["wallpaper"]["localPath"])
            _copy_atomic(source_path, destination)
            width, height = image_dimensions(destination)
            update_wallpaper_metadata(manifest_path, artwork_id, {
                "width": width,
                "height": height,
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "importedFromArtPaperPack": str(source_path),
            })
            summary.copied_count += 1

    return summary
