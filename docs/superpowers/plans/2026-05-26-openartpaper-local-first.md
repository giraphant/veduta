# OpenArtPaper Local-First Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first OpenArtPaper prototype that imports ArtPaper's 16 bundled collection manifests, downloads the highest practical artwork images to a local library, and runs a minimal macOS menu-bar app that rotates wallpapers from that local library.

**Architecture:** A Python `data-ops` CLI owns ingestion: it reads the local ArtPaper.app bundle, normalizes metadata, downloads images, and writes a self-contained library under `~/Pictures/OpenArtPaperLibrary`. A Swift package owns the client: `OpenArtPaperCore` loads local manifests and chooses wallpapers, while the `OpenArtPaper` executable is a lightweight AppKit menu-bar app. CDN/mirror publishing is intentionally deferred until the local library and client are stable; the schema already separates upstream source URLs from local/mirror image paths.

**Tech Stack:** Python 3.11+ stdlib + pytest for data operations; Swift 5.9+ / macOS 13+ / AppKit / Foundation / XCTest for the client; `sips` for local image dimension inspection; GitHub-flavored Markdown for project roadmap docs.

---

## Scope

### In scope for this plan

- Import all 16 ArtPaper collection JSON files from `/Applications/Artpaper.app/Contents/Resources`.
- Preserve source attribution and Google Arts image base URLs.
- Download high-resolution local images using Google image size suffixes, preferring `=s0` and falling back to `=s8192`, `=s6000`, `=s5120`, and `=s4096`.
- Resume interrupted downloads without redownloading completed images.
- Write normalized local manifests to `~/Pictures/OpenArtPaperLibrary`.
- Build a minimal local-only macOS menu-bar app:
  - status-bar item
  - manual “Next Wallpaper”
  - automatic interval rotation, default 30 minutes
  - set wallpaper on all visible screens
  - show current artwork title and creator in the menu
- Add `README.md` with the multi-day roadmap so future sessions know the next milestones.

### Out of scope for this plan

- Cloudflare/CDN upload automation.
- Public release `.dmg` packaging, signing, notarization.
- Full ArtPaper-style gallery UI.
- Favorites.
- Multi-collection UI picker.
- App Store distribution.

---

## File Structure

```text
openartpaper/
├── .gitignore
├── Makefile
├── README.md
├── Package.swift
├── data-ops/
│   ├── pyproject.toml
│   ├── src/openartpaper_data/
│   │   ├── __init__.py
│   │   ├── artpaper_import.py
│   │   ├── cli.py
│   │   ├── downloader.py
│   │   ├── library_writer.py
│   │   └── models.py
│   └── tests/
│       ├── test_artpaper_import.py
│       ├── test_downloader.py
│       └── test_library_writer.py
├── Sources/
│   ├── OpenArtPaper/
│   │   └── main.swift
│   └── OpenArtPaperCore/
│       ├── LocalLibrary.swift
│       ├── Models.swift
│       ├── RandomArtworkPicker.swift
│       └── WallpaperService.swift
└── Tests/
    └── OpenArtPaperCoreTests/
        ├── LocalLibraryTests.swift
        └── RandomArtworkPickerTests.swift
```

Generated local data lives outside the repo by default:

```text
~/Pictures/OpenArtPaperLibrary/
├── catalog.json
├── collections/
│   ├── essentials.json
│   ├── albany.json
│   └── ...
├── images/
│   ├── essentials/
│   │   ├── master-of-the-dresden-prayer-book-the-temperate-and-the-intemperate.jpg
│   │   └── ...
│   └── ...
└── failures.jsonl
```

The repo may use `OPENARTPAPER_LIBRARY_DIR` for tests and development, but production defaults to `~/Pictures/OpenArtPaperLibrary`.

---

## Task 1: Repository scaffolding

**Files:**
- Create: `.gitignore`
- Create: `Makefile`
- Create: `data-ops/pyproject.toml`
- Create: `data-ops/src/openartpaper_data/__init__.py`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
.DS_Store
.swiftpm/
.build/
DerivedData/
__pycache__/
.pytest_cache/
*.pyc
.venv/
.env
coverage.xml
htmlcov/
OpenArtPaperLibrary/
data/library/
*.partial
```

- [ ] **Step 2: Create `data-ops/pyproject.toml`**

```toml
[project]
name = "openartpaper-data"
version = "0.1.0"
description = "Local data pipeline for OpenArtPaper"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
openartpaper-data = "openartpaper_data.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Create `data-ops/src/openartpaper_data/__init__.py`**

```python
__all__ = []
```

- [ ] **Step 4: Create `Makefile`**

```makefile
ARTPAPER_APP ?= /Applications/Artpaper.app
LIBRARY_ROOT ?= $(HOME)/Pictures/OpenArtPaperLibrary
PYTHONPATH := data-ops/src

.PHONY: test-data test-swift test import-metadata download-essentials download-all run-app

test-data:
	cd data-ops && python3 -m pytest -q

test-swift:
	swift test

test: test-data test-swift

import-metadata:
	cd data-ops && PYTHONPATH=src python3 -m openartpaper_data.cli import-metadata --artpaper-app "$(ARTPAPER_APP)" --library-root "$(LIBRARY_ROOT)"

download-essentials:
	cd data-ops && PYTHONPATH=src python3 -m openartpaper_data.cli download --library-root "$(LIBRARY_ROOT)" --collection essentials --delay 1.0

download-all:
	cd data-ops && PYTHONPATH=src python3 -m openartpaper_data.cli download --library-root "$(LIBRARY_ROOT)" --all --delay 1.0

run-app:
	OPENARTPAPER_LIBRARY_DIR="$(LIBRARY_ROOT)" swift run OpenArtPaper
```

- [ ] **Step 5: Run scaffold checks**

Run:

```bash
make test-data
```

Expected:

```text
no tests ran
```

Run:

```bash
make test-swift
```

Expected before `Package.swift` exists:

```text
error: Could not find Package.swift in this directory or any of its parent directories.
```

- [ ] **Step 6: Commit scaffolding**

```bash
git add .gitignore Makefile data-ops/pyproject.toml data-ops/src/openartpaper_data/__init__.py
git commit -m "chore: scaffold local-first project"
```

---

## Task 2: Data models and ArtPaper bundle importer

**Files:**
- Create: `data-ops/src/openartpaper_data/models.py`
- Create: `data-ops/src/openartpaper_data/artpaper_import.py`
- Test: `data-ops/tests/test_artpaper_import.py`

- [ ] **Step 1: Write failing importer tests**

Create `data-ops/tests/test_artpaper_import.py`:

```python
import json
from pathlib import Path

from openartpaper_data.artpaper_import import import_artpaper_bundle, slugify


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
    assert artwork.canonical_page == "https://artsandculture.google.com/asset/example"
    assert artwork.upstream_image_base == "https://lh6.ggpht.com/example-image"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd data-ops && python3 -m pytest tests/test_artpaper_import.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'openartpaper_data.artpaper_import'
```

- [ ] **Step 3: Implement models**

Create `data-ops/src/openartpaper_data/models.py`:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceArtwork:
    id: str
    title: str
    creator: str
    attribution: str
    canonical_page: str
    artist_page: str | None
    upstream_image_base: str
    source_pack_id: int
    source_index: int


@dataclass(frozen=True)
class SourceCollection:
    id: str
    source_pack_id: int
    short_name: str
    title: str
    expected_artwork_count: int
    expected_author_count: int
    source_sizes_mb: dict[str, int]
    artworks: list[SourceArtwork] = field(default_factory=list)


@dataclass(frozen=True)
class SourceLibrary:
    collections: list[SourceCollection]
```

- [ ] **Step 4: Implement ArtPaper importer**

Create `data-ops/src/openartpaper_data/artpaper_import.py`:

```python
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from openartpaper_data.models import SourceArtwork, SourceCollection, SourceLibrary


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_value.lower()
    replaced = re.sub(r"[^a-z0-9]+", "-", lowered)
    return replaced.strip("-") or "untitled"


def https_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
    return urlunparse(parsed)


def google_arts_page(link: str) -> str:
    cleaned = link.strip().lstrip("/")
    return f"https://artsandculture.google.com/{cleaned}"


def unique_artwork_id(base: str, used: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def import_artpaper_bundle(app_path: Path) -> SourceLibrary:
    resources = app_path / "Contents" / "Resources"
    packages_path = resources / "packages.json"
    packages = json.loads(packages_path.read_text(encoding="utf-8"))

    collections: list[SourceCollection] = []
    for package in packages:
        pack_id = int(package["id"])
        short_name = str(package.get("short_name") or package["name"])
        collection_id = slugify(short_name)
        artwork_path = resources / f"{pack_id}.json"
        raw_artworks = json.loads(artwork_path.read_text(encoding="utf-8"))

        used_ids: set[str] = set()
        artworks: list[SourceArtwork] = []
        for index, raw in enumerate(raw_artworks):
            title = str(raw.get("title") or "Untitled")
            creator = str(raw.get("creator") or "Unknown artist")
            artwork_id = unique_artwork_id(slugify(f"{creator} {title}"), used_ids)
            image_base = https_url(str(raw["image"]).split("=")[0])
            artworks.append(SourceArtwork(
                id=artwork_id,
                title=title,
                creator=creator,
                attribution=str(raw.get("attribution") or "Unknown collection"),
                canonical_page=google_arts_page(str(raw.get("link") or "")),
                artist_page=str(raw.get("artist_link") or "") or None,
                upstream_image_base=image_base,
                source_pack_id=pack_id,
                source_index=index,
            ))

        collections.append(SourceCollection(
            id=collection_id,
            source_pack_id=pack_id,
            short_name=short_name,
            title=str(package["name"]),
            expected_artwork_count=int(package.get("objects") or len(artworks)),
            expected_author_count=int(package.get("authors") or 0),
            source_sizes_mb={key: int(value) for key, value in dict(package.get("sizes") or {}).items()},
            artworks=artworks,
        ))

    return SourceLibrary(collections=collections)
```

- [ ] **Step 5: Run importer tests**

Run:

```bash
cd data-ops && python3 -m pytest tests/test_artpaper_import.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 6: Commit importer**

```bash
git add data-ops/src/openartpaper_data/models.py data-ops/src/openartpaper_data/artpaper_import.py data-ops/tests/test_artpaper_import.py
git commit -m "feat: import ArtPaper bundle metadata"
```

---

## Task 3: Normalized local library writer

**Files:**
- Create: `data-ops/src/openartpaper_data/library_writer.py`
- Test: `data-ops/tests/test_library_writer.py`

- [ ] **Step 1: Write failing library writer tests**

Create `data-ops/tests/test_library_writer.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd data-ops && python3 -m pytest tests/test_library_writer.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'openartpaper_data.library_writer'
```

- [ ] **Step 3: Implement library writer**

Create `data-ops/src/openartpaper_data/library_writer.py`:

```python
import json
from datetime import UTC, datetime
from pathlib import Path

from openartpaper_data.models import SourceLibrary

IMAGE_SUFFIXES = ["s0", "s8192", "s6000", "s5120", "s4096"]


def candidate_image_urls(image_base: str) -> list[str]:
    clean_base = image_base.split("=")[0]
    return [f"{clean_base}={suffix}" for suffix in IMAGE_SUFFIXES]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_metadata_library(library: SourceLibrary, library_root: Path) -> None:
    generated_at = now_iso()
    collection_summaries: list[dict[str, object]] = []

    for collection in library.collections:
        manifest_path = f"collections/{collection.id}.json"
        collection_summaries.append({
            "id": collection.id,
            "title": collection.title,
            "shortName": collection.short_name,
            "sourcePackId": collection.source_pack_id,
            "artworkCount": len(collection.artworks),
            "expectedArtworkCount": collection.expected_artwork_count,
            "manifest": manifest_path,
        })

        artworks = []
        for artwork in collection.artworks:
            local_path = f"images/{collection.id}/{artwork.id}.jpg"
            artworks.append({
                "id": artwork.id,
                "title": artwork.title,
                "creator": artwork.creator,
                "attribution": artwork.attribution,
                "sources": {
                    "canonicalPage": artwork.canonical_page,
                    "artistPage": artwork.artist_page,
                    "upstreamImageBase": artwork.upstream_image_base,
                },
                "rights": {
                    "work": "public-domain",
                    "reproduction": "faithful-reproduction",
                    "creditLine": f"{artwork.attribution} via Google Arts & Culture",
                },
                "images": {
                    "wallpaper": {
                        "localPath": local_path,
                        "fallbackUrls": candidate_image_urls(artwork.upstream_image_base),
                    }
                },
                "source": {
                    "artpaperPackId": artwork.source_pack_id,
                    "artpaperIndex": artwork.source_index,
                },
            })

        write_json(library_root / manifest_path, {
            "schemaVersion": 1,
            "id": collection.id,
            "title": collection.title,
            "shortName": collection.short_name,
            "generatedAt": generated_at,
            "source": {
                "type": "artpaper-bundle",
                "packId": collection.source_pack_id,
                "reportedSizesMb": collection.source_sizes_mb,
            },
            "artworks": artworks,
        })

    write_json(library_root / "catalog.json", {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "collections": collection_summaries,
    })
```

- [ ] **Step 4: Run library writer tests**

Run:

```bash
cd data-ops && python3 -m pytest tests/test_library_writer.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Commit library writer**

```bash
git add data-ops/src/openartpaper_data/library_writer.py data-ops/tests/test_library_writer.py
git commit -m "feat: write local library manifests"
```

---

## Task 4: High-resolution image downloader

**Files:**
- Create: `data-ops/src/openartpaper_data/downloader.py`
- Test: `data-ops/tests/test_downloader.py`

- [ ] **Step 1: Write failing downloader tests**

Create `data-ops/tests/test_downloader.py`:

```python
import hashlib

from openartpaper_data.downloader import choose_download_state, sha256_file


def test_choose_download_state_skips_complete_file(tmp_path):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"abc")
    assert choose_download_state(image_path) == "skip"


def test_choose_download_state_retries_partial_file(tmp_path):
    image_path = tmp_path / "image.jpg"
    partial_path = tmp_path / "image.jpg.partial"
    partial_path.write_bytes(b"abc")
    assert choose_download_state(image_path) == "download"


def test_sha256_file_hashes_file_contents(tmp_path):
    path = tmp_path / "payload.bin"
    path.write_bytes(b"openartpaper")
    assert sha256_file(path) == hashlib.sha256(b"openartpaper").hexdigest()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd data-ops && python3 -m pytest tests/test_downloader.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'openartpaper_data.downloader'
```

- [ ] **Step 3: Implement downloader utilities**

Create `data-ops/src/openartpaper_data/downloader.py`:

```python
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "OpenArtPaper/0.1 (+https://github.com/openartpaper/openartpaper)"


def choose_download_state(final_path: Path) -> str:
    if final_path.exists() and final_path.stat().st_size > 0:
        return "skip"
    return "download"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int, int]:
    result = subprocess.run(
        ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
        text=True,
        capture_output=True,
        check=True,
    )
    width = 0
    height = 0
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("pixelWidth:"):
            width = int(stripped.split(":", 1)[1].strip())
        if stripped.startswith("pixelHeight:"):
            height = int(stripped.split(":", 1)[1].strip())
    if width <= 0 or height <= 0:
        raise ValueError(f"Could not read image dimensions from {path}")
    return width, height


def download_url(url: str, destination: Path, timeout: float = 60.0) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise ValueError(f"Expected image content from {url}, got {content_type}")
        with partial.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    partial.replace(destination)


def download_first_working(candidates: list[str], destination: Path, delay_seconds: float) -> dict[str, object]:
    if choose_download_state(destination) == "skip":
        width, height = image_dimensions(destination)
        return {
            "status": "skipped",
            "url": None,
            "width": width,
            "height": height,
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
        }

    errors: list[str] = []
    for url in candidates:
        try:
            download_url(url, destination)
            width, height = image_dimensions(destination)
            return {
                "status": "downloaded",
                "url": url,
                "width": width,
                "height": height,
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        except (urllib.error.URLError, TimeoutError, ValueError, subprocess.CalledProcessError) as error:
            errors.append(f"{url}: {error}")
            if destination.exists():
                destination.unlink()
            partial = destination.with_suffix(destination.suffix + ".partial")
            if partial.exists():
                partial.unlink()
            time.sleep(delay_seconds)

    raise RuntimeError(json.dumps({"destination": str(destination), "errors": errors}, ensure_ascii=False))
```

- [ ] **Step 4: Run downloader tests**

Run:

```bash
cd data-ops && python3 -m pytest tests/test_downloader.py -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit downloader utilities**

```bash
git add data-ops/src/openartpaper_data/downloader.py data-ops/tests/test_downloader.py
git commit -m "feat: add resumable image downloader"
```

---

## Task 5: Data-ops CLI

**Files:**
- Create: `data-ops/src/openartpaper_data/cli.py`
- Modify: `data-ops/src/openartpaper_data/library_writer.py`
- Test: `data-ops/tests/test_library_writer.py`

- [ ] **Step 1: Extend library writer to persist image metadata**

Modify `data-ops/src/openartpaper_data/library_writer.py` by adding this function below `write_metadata_library`:

```python

def update_wallpaper_metadata(collection_manifest_path: Path, artwork_id: str, metadata: dict[str, object]) -> None:
    collection = json.loads(collection_manifest_path.read_text(encoding="utf-8"))
    updated = False
    for artwork in collection["artworks"]:
        if artwork["id"] == artwork_id:
            artwork["images"]["wallpaper"].update(metadata)
            updated = True
            break
    if not updated:
        raise KeyError(f"Artwork {artwork_id} not found in {collection_manifest_path}")
    write_json(collection_manifest_path, collection)
```

- [ ] **Step 2: Add a failing test for image metadata updates**

Append to `data-ops/tests/test_library_writer.py`:

```python
from openartpaper_data.library_writer import update_wallpaper_metadata


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
```

- [ ] **Step 3: Run the new test**

Run:

```bash
cd data-ops && python3 -m pytest tests/test_library_writer.py::test_update_wallpaper_metadata_updates_matching_artwork -q
```

Expected:

```text
1 passed
```

- [ ] **Step 4: Implement CLI**

Create `data-ops/src/openartpaper_data/cli.py`:

```python
import argparse
import json
import sys
import time
from pathlib import Path

from openartpaper_data.artpaper_import import import_artpaper_bundle
from openartpaper_data.downloader import download_first_working
from openartpaper_data.library_writer import update_wallpaper_metadata, write_metadata_library


def default_library_root() -> Path:
    return Path.home() / "Pictures" / "OpenArtPaperLibrary"


def import_metadata(args: argparse.Namespace) -> int:
    library = import_artpaper_bundle(Path(args.artpaper_app))
    write_metadata_library(library, Path(args.library_root).expanduser())
    total = sum(len(collection.artworks) for collection in library.collections)
    print(f"Imported {len(library.collections)} collections and {total} artworks into {args.library_root}")
    return 0


def load_catalog(library_root: Path) -> dict[str, object]:
    return json.loads((library_root / "catalog.json").read_text(encoding="utf-8"))


def load_collection(library_root: Path, manifest: str) -> dict[str, object]:
    return json.loads((library_root / manifest).read_text(encoding="utf-8"))


def selected_collections(catalog: dict[str, object], collection_id: str | None, all_collections: bool) -> list[dict[str, object]]:
    collections = list(catalog["collections"])
    if all_collections:
        return collections
    if collection_id is None:
        raise SystemExit("Provide --collection <id> or --all")
    matches = [collection for collection in collections if collection["id"] == collection_id]
    if not matches:
        available = ", ".join(str(collection["id"]) for collection in collections)
        raise SystemExit(f"Unknown collection {collection_id}. Available: {available}")
    return matches


def download(args: argparse.Namespace) -> int:
    library_root = Path(args.library_root).expanduser()
    catalog = load_catalog(library_root)
    failures_path = library_root / "failures.jsonl"
    successes = 0
    failures = 0

    for collection_summary in selected_collections(catalog, args.collection, args.all):
        collection = load_collection(library_root, str(collection_summary["manifest"]))
        manifest_path = library_root / str(collection_summary["manifest"])
        for artwork in collection["artworks"]:
            wallpaper = artwork["images"]["wallpaper"]
            destination = library_root / str(wallpaper["localPath"])
            try:
                result = download_first_working(list(wallpaper["fallbackUrls"]), destination, float(args.delay))
                metadata = {
                    "width": result["width"],
                    "height": result["height"],
                    "bytes": result["bytes"],
                    "sha256": result["sha256"],
                }
                if result["url"] is not None:
                    metadata["downloadedFrom"] = result["url"]
                update_wallpaper_metadata(manifest_path, str(artwork["id"]), metadata)
                successes += 1
                print(f"{result['status']}: {collection['id']}/{artwork['id']} {metadata['width']}x{metadata['height']}")
            except Exception as error:
                failures += 1
                failures_path.parent.mkdir(parents=True, exist_ok=True)
                with failures_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({
                        "collection": collection["id"],
                        "artwork": artwork["id"],
                        "error": str(error),
                    }, ensure_ascii=False) + "\n")
                print(f"failed: {collection['id']}/{artwork['id']}: {error}", file=sys.stderr)
            time.sleep(float(args.delay))

    print(f"Download pass complete: {successes} successes, {failures} failures")
    return 1 if failures and successes == 0 else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openartpaper-data")
    subcommands = parser.add_subparsers(dest="command", required=True)

    import_parser = subcommands.add_parser("import-metadata")
    import_parser.add_argument("--artpaper-app", default="/Applications/Artpaper.app")
    import_parser.add_argument("--library-root", default=str(default_library_root()))
    import_parser.set_defaults(func=import_metadata)

    download_parser = subcommands.add_parser("download")
    download_parser.add_argument("--library-root", default=str(default_library_root()))
    download_parser.add_argument("--collection")
    download_parser.add_argument("--all", action="store_true")
    download_parser.add_argument("--delay", type=float, default=1.0)
    download_parser.set_defaults(func=download)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run all data tests**

Run:

```bash
make test-data
```

Expected:

```text
7 passed
```

- [ ] **Step 6: Import real ArtPaper metadata**

Run:

```bash
make import-metadata
```

Expected:

```text
Imported 16 collections and 1558 artworks into /Users/ramudai/Pictures/OpenArtPaperLibrary
```

- [ ] **Step 7: Inspect generated collection IDs**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
catalog = json.loads((Path.home() / 'Pictures' / 'OpenArtPaperLibrary' / 'catalog.json').read_text())
print('\n'.join(collection['id'] for collection in catalog['collections']))
PY
```

Expected:

```text
essentials
albany
berlin
carter
wales
americas
spisa
chicago
carmen
east-side
graffitimundo
greece
rijksmuseum
shizuoka
tokyo
uffizi
```

- [ ] **Step 8: Commit CLI**

```bash
git add data-ops/src/openartpaper_data/cli.py data-ops/src/openartpaper_data/library_writer.py data-ops/tests/test_library_writer.py
git commit -m "feat: add local data pipeline CLI"
```

---

## Task 6: Download Essentials at highest practical resolution

**Files:**
- Generated: `~/Pictures/OpenArtPaperLibrary/images/essentials/*.jpg`
- Generated/modified: `~/Pictures/OpenArtPaperLibrary/collections/essentials.json`
- Generated/modified: `~/Pictures/OpenArtPaperLibrary/failures.jsonl`

- [ ] **Step 1: Run Essentials download pass**

Run:

```bash
make download-essentials
```

Expected shape:

```text
downloaded: essentials/master-of-the-dresden-prayer-book-the-temperate-and-the-intemperate 6000x5440
...
Download pass complete: 161 successes, 0 failures
```

If Google returns fewer than 161 successful images, the expected final line is:

```text
Download pass complete: <successes> successes, <failures> failures
```

and `~/Pictures/OpenArtPaperLibrary/failures.jsonl` contains one JSON object per failed artwork.

- [ ] **Step 2: Retry failed Essentials downloads once**

Run:

```bash
make download-essentials
```

Expected: completed files are printed as `skipped`, failed files are retried, and no completed image is redownloaded.

- [ ] **Step 3: Verify local Essentials image count**

Run:

```bash
find "$HOME/Pictures/OpenArtPaperLibrary/images/essentials" -type f -name '*.jpg' | wc -l
```

Expected:

```text
     161
```

- [ ] **Step 4: Verify manifest has dimensions and hashes**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
manifest = json.loads((Path.home() / 'Pictures' / 'OpenArtPaperLibrary' / 'collections' / 'essentials.json').read_text())
missing = []
for artwork in manifest['artworks']:
    wallpaper = artwork['images']['wallpaper']
    for key in ['width', 'height', 'bytes', 'sha256']:
        if key not in wallpaper:
            missing.append((artwork['id'], key))
print('missing', len(missing))
PY
```

Expected:

```text
missing 0
```

- [ ] **Step 5: Commit code only**

Do not commit the downloaded images. Commit only code changes from prior tasks if any remain unstaged:

```bash
git status --short
git add data-ops/src/openartpaper_data data-ops/tests Makefile .gitignore
git commit -m "chore: verify essentials data pipeline"
```

If `git status --short` shows no code changes, skip this commit.

---

## Task 7: Download all 16 collections locally

**Files:**
- Generated: `~/Pictures/OpenArtPaperLibrary/images/<collection-id>/*.jpg`
- Generated/modified: `~/Pictures/OpenArtPaperLibrary/collections/*.json`
- Generated/modified: `~/Pictures/OpenArtPaperLibrary/failures.jsonl`

- [ ] **Step 1: Run the full collection download pass**

Run:

```bash
make download-all
```

Expected shape:

```text
skipped: essentials/master-of-the-dresden-prayer-book-the-temperate-and-the-intemperate 6000x5440
...
downloaded: albany/thomas-cole-the-course-of-empire 8192x5278
...
Download pass complete: <successes> successes, <failures> failures
```

This may take hours. Let it run in the terminal or a background shell. The command is resumable.

- [ ] **Step 2: Retry the full collection download pass**

Run:

```bash
make download-all
```

Expected: previously completed files are skipped; transient failures are retried.

- [ ] **Step 3: Verify total local image count**

Run:

```bash
find "$HOME/Pictures/OpenArtPaperLibrary/images" -type f -name '*.jpg' | wc -l
```

Expected if all upstream URLs still work:

```text
    1558
```

If the count is lower, inspect failures:

```bash
wc -l "$HOME/Pictures/OpenArtPaperLibrary/failures.jsonl"
```

Expected: number of failed attempts across all runs.

- [ ] **Step 4: Verify no collection manifest has missing completed image paths**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
root = Path.home() / 'Pictures' / 'OpenArtPaperLibrary'
missing_files = []
for manifest_path in sorted((root / 'collections').glob('*.json')):
    manifest = json.loads(manifest_path.read_text())
    for artwork in manifest['artworks']:
        local_path = root / artwork['images']['wallpaper']['localPath']
        if 'sha256' in artwork['images']['wallpaper'] and not local_path.exists():
            missing_files.append(str(local_path))
print('missing completed files', len(missing_files))
PY
```

Expected:

```text
missing completed files 0
```

- [ ] **Step 5: Record local data status in README later**

Do not commit local images. The README task below records the expected local library path, resumable download commands, and the intended future CDN workflow.

---

## Task 8: Swift package and core models

**Files:**
- Create: `Package.swift`
- Create: `Sources/OpenArtPaperCore/Models.swift`
- Test: `Tests/OpenArtPaperCoreTests/LocalLibraryTests.swift`

- [ ] **Step 1: Create `Package.swift`**

```swift
// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "OpenArtPaper",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "OpenArtPaperCore", targets: ["OpenArtPaperCore"]),
        .executable(name: "OpenArtPaper", targets: ["OpenArtPaper"]),
    ],
    targets: [
        .target(name: "OpenArtPaperCore"),
        .executableTarget(name: "OpenArtPaper", dependencies: ["OpenArtPaperCore"]),
        .testTarget(name: "OpenArtPaperCoreTests", dependencies: ["OpenArtPaperCore"]),
    ]
)
```

- [ ] **Step 2: Write failing model decode test**

Create `Tests/OpenArtPaperCoreTests/LocalLibraryTests.swift`:

```swift
import XCTest
@testable import OpenArtPaperCore

final class LocalLibraryTests: XCTestCase {
    func testDecodesCatalogAndCollectionManifest() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root.appendingPathComponent("collections"), withIntermediateDirectories: true)

        try """
        {
          "schemaVersion": 1,
          "generatedAt": "2026-05-26T00:00:00Z",
          "collections": [
            {
              "id": "essentials",
              "title": "Essentials Set",
              "shortName": "Essentials",
              "sourcePackId": 0,
              "artworkCount": 1,
              "expectedArtworkCount": 1,
              "manifest": "collections/essentials.json"
            }
          ]
        }
        """.write(to: root.appendingPathComponent("catalog.json"), atomically: true, encoding: .utf8)

        try """
        {
          "schemaVersion": 1,
          "id": "essentials",
          "title": "Essentials Set",
          "shortName": "Essentials",
          "generatedAt": "2026-05-26T00:00:00Z",
          "source": { "type": "artpaper-bundle", "packId": 0, "reportedSizesMb": { "ultrahd": 945 } },
          "artworks": [
            {
              "id": "artist-title",
              "title": "Title",
              "creator": "Artist",
              "attribution": "Museum",
              "sources": {
                "canonicalPage": "https://artsandculture.google.com/asset/example",
                "artistPage": "https://example.com/artist",
                "upstreamImageBase": "https://lh6.ggpht.com/example"
              },
              "rights": { "work": "public-domain", "reproduction": "faithful-reproduction", "creditLine": "Museum via Google Arts & Culture" },
              "images": { "wallpaper": { "localPath": "images/essentials/artist-title.jpg", "fallbackUrls": ["https://lh6.ggpht.com/example=s0"] } },
              "source": { "artpaperPackId": 0, "artpaperIndex": 0 }
            }
          ]
        }
        """.write(to: root.appendingPathComponent("collections/essentials.json"), atomically: true, encoding: .utf8)

        let library = try LocalLibrary(root: root)
        let catalog = try library.loadCatalog()
        XCTAssertEqual(catalog.collections.count, 1)
        let collection = try library.loadCollection(catalog.collections[0])
        XCTAssertEqual(collection.artworks[0].id, "artist-title")
        XCTAssertEqual(collection.artworks[0].creator, "Artist")
    }
}
```

- [ ] **Step 3: Run Swift test to verify it fails**

Run:

```bash
swift test --filter LocalLibraryTests/testDecodesCatalogAndCollectionManifest
```

Expected:

```text
error: no such module 'OpenArtPaperCore'
```

- [ ] **Step 4: Implement Swift models**

Create `Sources/OpenArtPaperCore/Models.swift`:

```swift
import Foundation

public struct Catalog: Decodable, Sendable {
    public let schemaVersion: Int
    public let generatedAt: String
    public let collections: [CollectionSummary]
}

public struct CollectionSummary: Decodable, Sendable {
    public let id: String
    public let title: String
    public let shortName: String
    public let sourcePackId: Int
    public let artworkCount: Int
    public let expectedArtworkCount: Int
    public let manifest: String
}

public struct CollectionManifest: Decodable, Sendable {
    public let schemaVersion: Int
    public let id: String
    public let title: String
    public let shortName: String
    public let generatedAt: String
    public let artworks: [Artwork]
}

public struct Artwork: Decodable, Sendable, Equatable {
    public let id: String
    public let title: String
    public let creator: String
    public let attribution: String
    public let sources: ArtworkSources
    public let rights: ArtworkRights
    public let images: ArtworkImages
}

public struct ArtworkSources: Decodable, Sendable, Equatable {
    public let canonicalPage: String
    public let artistPage: String?
    public let upstreamImageBase: String
}

public struct ArtworkRights: Decodable, Sendable, Equatable {
    public let work: String
    public let reproduction: String
    public let creditLine: String
}

public struct ArtworkImages: Decodable, Sendable, Equatable {
    public let wallpaper: WallpaperImage
}

public struct WallpaperImage: Decodable, Sendable, Equatable {
    public let localPath: String
    public let fallbackUrls: [String]
    public let width: Int?
    public let height: Int?
    public let bytes: Int?
    public let sha256: String?
    public let downloadedFrom: String?
}
```

- [ ] **Step 5: Implement local library loader**

Create `Sources/OpenArtPaperCore/LocalLibrary.swift`:

```swift
import Foundation

public final class LocalLibrary {
    public let root: URL
    private let decoder = JSONDecoder()

    public init(root: URL) {
        self.root = root
    }

    public func loadCatalog() throws -> Catalog {
        let data = try Data(contentsOf: root.appendingPathComponent("catalog.json"))
        return try decoder.decode(Catalog.self, from: data)
    }

    public func loadCollection(_ summary: CollectionSummary) throws -> CollectionManifest {
        let data = try Data(contentsOf: root.appendingPathComponent(summary.manifest))
        return try decoder.decode(CollectionManifest.self, from: data)
    }

    public func wallpaperURL(for artwork: Artwork) -> URL {
        root.appendingPathComponent(artwork.images.wallpaper.localPath)
    }

    public func loadAllDownloadedArtworks() throws -> [(Artwork, URL)] {
        let catalog = try loadCatalog()
        var result: [(Artwork, URL)] = []
        for summary in catalog.collections {
            let collection = try loadCollection(summary)
            for artwork in collection.artworks {
                let url = wallpaperURL(for: artwork)
                if FileManager.default.fileExists(atPath: url.path) {
                    result.append((artwork, url))
                }
            }
        }
        return result
    }
}
```

- [ ] **Step 6: Run Swift model tests**

Run:

```bash
swift test --filter LocalLibraryTests/testDecodesCatalogAndCollectionManifest
```

Expected:

```text
Test Suite 'Selected tests' passed
```

- [ ] **Step 7: Commit Swift models**

```bash
git add Package.swift Sources/OpenArtPaperCore/Models.swift Sources/OpenArtPaperCore/LocalLibrary.swift Tests/OpenArtPaperCoreTests/LocalLibraryTests.swift
git commit -m "feat: load local OpenArtPaper library"
```

---

## Task 9: Random artwork picker and wallpaper service

**Files:**
- Create: `Sources/OpenArtPaperCore/RandomArtworkPicker.swift`
- Create: `Sources/OpenArtPaperCore/WallpaperService.swift`
- Test: `Tests/OpenArtPaperCoreTests/RandomArtworkPickerTests.swift`

- [ ] **Step 1: Write failing picker test**

Create `Tests/OpenArtPaperCoreTests/RandomArtworkPickerTests.swift`:

```swift
import Foundation
import XCTest
@testable import OpenArtPaperCore

final class RandomArtworkPickerTests: XCTestCase {
    func testPickerReturnsOnlyArtworkFromInput() throws {
        let artwork = Artwork(
            id: "one",
            title: "Title",
            creator: "Artist",
            attribution: "Museum",
            sources: ArtworkSources(canonicalPage: "https://example.com", artistPage: nil, upstreamImageBase: "https://example.com/image"),
            rights: ArtworkRights(work: "public-domain", reproduction: "faithful-reproduction", creditLine: "Museum"),
            images: ArtworkImages(wallpaper: WallpaperImage(localPath: "images/one.jpg", fallbackUrls: [], width: nil, height: nil, bytes: nil, sha256: nil, downloadedFrom: nil))
        )
        let picker = RandomArtworkPicker()
        let picked = try picker.pick(from: [(artwork, URL(fileURLWithPath: "/tmp/one.jpg"))])
        XCTAssertEqual(picked.0.id, "one")
    }

    func testPickerThrowsForEmptyInput() {
        let picker = RandomArtworkPicker()
        XCTAssertThrowsError(try picker.pick(from: []))
    }
}
```

- [ ] **Step 2: Run picker tests to verify failure**

Run:

```bash
swift test --filter RandomArtworkPickerTests
```

Expected:

```text
error: cannot find 'RandomArtworkPicker' in scope
```

- [ ] **Step 3: Implement picker**

Create `Sources/OpenArtPaperCore/RandomArtworkPicker.swift`:

```swift
import Foundation

public enum RandomArtworkPickerError: Error, Equatable {
    case emptyLibrary
}

public final class RandomArtworkPicker {
    private var lastArtworkID: String?

    public init() {}

    public func pick(from artworks: [(Artwork, URL)]) throws -> (Artwork, URL) {
        guard !artworks.isEmpty else { throw RandomArtworkPickerError.emptyLibrary }
        if artworks.count == 1 {
            lastArtworkID = artworks[0].0.id
            return artworks[0]
        }
        let candidates = artworks.filter { $0.0.id != lastArtworkID }
        let selected = candidates.randomElement() ?? artworks[0]
        lastArtworkID = selected.0.id
        return selected
    }
}
```

- [ ] **Step 4: Implement wallpaper service**

Create `Sources/OpenArtPaperCore/WallpaperService.swift`:

```swift
import AppKit
import Foundation

public final class WallpaperService {
    public init() {}

    public func setWallpaperOnAllScreens(imageURL: URL) throws {
        let workspace = NSWorkspace.shared
        for screen in NSScreen.screens {
            try workspace.setDesktopImageURL(imageURL, for: screen, options: [:])
        }
    }
}
```

- [ ] **Step 5: Run Swift core tests**

Run:

```bash
swift test
```

Expected:

```text
Test Suite 'All tests' passed
```

- [ ] **Step 6: Commit picker and wallpaper service**

```bash
git add Sources/OpenArtPaperCore/RandomArtworkPicker.swift Sources/OpenArtPaperCore/WallpaperService.swift Tests/OpenArtPaperCoreTests/RandomArtworkPickerTests.swift
git commit -m "feat: pick and apply local wallpapers"
```

---

## Task 10: Minimal menu-bar app

**Files:**
- Create: `Sources/OpenArtPaper/main.swift`

- [ ] **Step 1: Create menu-bar executable**

Create `Sources/OpenArtPaper/main.swift`:

```swift
import AppKit
import Foundation
import OpenArtPaperCore

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var currentArtwork: Artwork?
    private let picker = RandomArtworkPicker()
    private let wallpaperService = WallpaperService()
    private var timer: Timer?

    private lazy var library: LocalLibrary = {
        let environmentPath = ProcessInfo.processInfo.environment["OPENARTPAPER_LIBRARY_DIR"]
        let root: URL
        if let environmentPath, !environmentPath.isEmpty {
            root = URL(fileURLWithPath: environmentPath).standardizedFileURL
        } else {
            root = FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Pictures")
                .appendingPathComponent("OpenArtPaperLibrary")
        }
        return LocalLibrary(root: root)
    }()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "Art"
        rebuildMenu(message: "Ready")
        rotateWallpaper()
        timer = Timer.scheduledTimer(withTimeInterval: 30 * 60, repeats: true) { [weak self] _ in
            self?.rotateWallpaper()
        }
    }

    private func rebuildMenu(message: String) {
        let menu = NSMenu()
        let title = currentArtwork.map { "\($0.title) — \($0.creator)" } ?? message
        let currentItem = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        currentItem.isEnabled = false
        menu.addItem(currentItem)
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Next Wallpaper", action: #selector(nextWallpaper), keyEquivalent: "n"))
        menu.addItem(NSMenuItem(title: "Open Library Folder", action: #selector(openLibraryFolder), keyEquivalent: "o"))
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Quit OpenArtPaper", action: #selector(quit), keyEquivalent: "q"))
        statusItem.menu = menu
    }

    @objc private func nextWallpaper() {
        rotateWallpaper()
    }

    private func rotateWallpaper() {
        do {
            let artworks = try library.loadAllDownloadedArtworks()
            let selected = try picker.pick(from: artworks)
            try wallpaperService.setWallpaperOnAllScreens(imageURL: selected.1)
            currentArtwork = selected.0
            rebuildMenu(message: "Ready")
        } catch {
            rebuildMenu(message: "OpenArtPaper error: \(error.localizedDescription)")
        }
    }

    @objc private func openLibraryFolder() {
        NSWorkspace.shared.open(library.root)
    }

    @objc private func quit() {
        timer?.invalidate()
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
```

- [ ] **Step 2: Run Swift tests**

Run:

```bash
swift test
```

Expected:

```text
Test Suite 'All tests' passed
```

- [ ] **Step 3: Run the app against local library**

Run:

```bash
make run-app
```

Expected:

- A menu-bar item titled `Art` appears.
- The current desktop wallpaper changes to a downloaded OpenArtPaper image.
- The menu shows the current artwork title and creator.
- Selecting `Next Wallpaper` changes the wallpaper again.
- Selecting `Open Library Folder` opens `~/Pictures/OpenArtPaperLibrary`.
- Selecting `Quit OpenArtPaper` exits the process.

- [ ] **Step 4: Commit menu-bar app**

```bash
git add Sources/OpenArtPaper/main.swift
git commit -m "feat: add minimal menu bar wallpaper app"
```

---

## Task 11: README and multi-day roadmap

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README with current local-first workflow**

Create `README.md`:

```markdown
# OpenArtPaper

OpenArtPaper is a local-first, open-source macOS wallpaper app for public-domain and museum artwork.

The first milestone is deliberately boring: make the local data pipeline and a minimal menu-bar wallpaper app work before adding hosting, syncing, gallery UI, or release packaging.

## Current milestone: local library first

The current workflow uses a locally installed copy of ArtPaper only as a seed for metadata. The generated OpenArtPaper library lives outside the repository by default:

```text
~/Pictures/OpenArtPaperLibrary/
├── catalog.json
├── collections/*.json
└── images/<collection-id>/*.jpg
```

The repository does not commit downloaded artwork files.

## Requirements

- macOS 13 or newer
- Swift 5.9 or newer
- Python 3.11 or newer
- A local ArtPaper.app bundle at `/Applications/Artpaper.app` for the initial import

## Import metadata

```bash
make import-metadata
```

Expected result:

```text
Imported 16 collections and 1558 artworks into ~/Pictures/OpenArtPaperLibrary
```

## Download artwork

Start with Essentials:

```bash
make download-essentials
```

Then download all collections:

```bash
make download-all
```

Downloads are resumable. Completed files are skipped. Failures are recorded in:

```text
~/Pictures/OpenArtPaperLibrary/failures.jsonl
```

## Run the local app

```bash
make run-app
```

The app runs as a menu-bar process and rotates wallpapers from the local library.

## Roadmap

### Phase 1: Local data pipeline

- Import all 16 ArtPaper collection manifests.
- Normalize metadata into OpenArtPaper schema.
- Download highest practical local image files.
- Resume failed downloads safely.
- Verify dimensions, file sizes, and SHA-256 hashes.

### Phase 2: Minimal macOS app

- Read local library manifests.
- Choose random downloaded artworks.
- Set wallpaper on all visible displays.
- Provide menu-bar controls for Next Wallpaper, Open Library Folder, and Quit.
- Keep interval rotation simple and local-only.

### Phase 3: Better local product

- Add interval settings.
- Add collection filtering.
- Add favorites.
- Add a small current-artwork panel with title, creator, attribution, and source link.
- Add launch-at-login support.

### Phase 4: Self-hosted mirror

- Generate CDN-ready relative paths from the local library.
- Upload `catalog.json`, `collections/*.json`, and `images/**` to a static origin.
- Put Cloudflare in front of the origin.
- Keep upstream Google/Museum URLs in manifest as fallback and provenance, not as the default runtime path.

### Phase 5: Public release

- Build a signed `.app` bundle.
- Add notarization.
- Publish GitHub Releases.
- Document mirror configuration for people who want to self-host.
```

- [ ] **Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: document local-first roadmap"
```

---

## Task 12: End-to-end verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Run data tests**

Run:

```bash
make test-data
```

Expected:

```text
7 passed
```

- [ ] **Step 2: Run Swift tests**

Run:

```bash
make test-swift
```

Expected:

```text
Test Suite 'All tests' passed
```

- [ ] **Step 3: Verify metadata import still works**

Run:

```bash
make import-metadata
```

Expected:

```text
Imported 16 collections and 1558 artworks into /Users/ramudai/Pictures/OpenArtPaperLibrary
```

- [ ] **Step 4: Verify Essentials image library exists**

Run:

```bash
find "$HOME/Pictures/OpenArtPaperLibrary/images/essentials" -type f -name '*.jpg' | wc -l
```

Expected after Task 6:

```text
     161
```

- [ ] **Step 5: Run app manually**

Run:

```bash
make run-app
```

Expected:

- Menu-bar item appears.
- Wallpaper changes once at launch.
- `Next Wallpaper` changes wallpaper again.
- `Open Library Folder` opens the local library.
- `Quit OpenArtPaper` exits the app.

- [ ] **Step 6: Commit verification note only if source changed**

Run:

```bash
git status --short
```

If no source files changed, do not commit. If README or scripts were adjusted during verification, commit those exact files:

```bash
git add README.md Makefile data-ops/src/openartpaper_data Sources Tests
git commit -m "chore: complete local-first verification"
```

---

## Continuation Plan After This File

Once Task 12 passes, create the next plan file instead of expanding this one. Use these exact follow-up plan names:

1. `docs/superpowers/plans/2026-05-27-openartpaper-local-product.md`
   - interval setting UI
   - collection filtering
   - favorites
   - current-artwork detail panel
   - launch at login

2. `docs/superpowers/plans/2026-05-28-openartpaper-static-mirror.md`
   - export CDN-ready manifest
   - upload script for static origin
   - Cloudflare cache headers
   - mirror verification
   - upstream fallback policy

3. `docs/superpowers/plans/2026-05-29-openartpaper-release-packaging.md`
   - app bundle generation
   - icon
   - signing
   - notarization
   - GitHub Releases

---

## Self-Review

### Spec coverage

- Local-first data pipeline: covered by Tasks 2–7.
- All 16 collections: covered by Tasks 5 and 7.
- Highest practical image download: covered by Tasks 3–7 through `s0`, `s8192`, `s6000`, `s5120`, and `s4096` fallback URLs.
- Minimal wallpaper app: covered by Tasks 8–10.
- README and future multi-day roadmap: covered by Task 11 and the Continuation Plan section.
- CDN later: excluded from implementation scope here, but represented in schema and README roadmap.

### Placeholder scan

The plan contains no `TBD`, no unresolved placeholders, and no steps that require inventing unspecified APIs.

### Type consistency

Python names are consistent across tasks: `SourceLibrary`, `SourceCollection`, `SourceArtwork`, `write_metadata_library`, `update_wallpaper_metadata`, `download_first_working`. Swift names are consistent across tasks: `Catalog`, `CollectionSummary`, `CollectionManifest`, `Artwork`, `LocalLibrary`, `RandomArtworkPicker`, `WallpaperService`.
