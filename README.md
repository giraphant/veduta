# OpenArtPaper

OpenArtPaper is a local-first, open-source macOS wallpaper app for public-domain and museum artwork.

The current goal is a reliable local data pipeline plus a minimal menu-bar app. Hosting, sync, gallery features, and release packaging come later.

## Current local-first workflow

Generated artwork data lives outside the repo at:

```text
~/Pictures/OpenArtPaperLibrary/
├── catalog.json
├── collections/*.json
└── images/<collection-id>/*.jpg
```

The repository does not commit downloaded artwork or generated local library files.

## Requirements

- macOS 13+
- Swift 5.9+
- Python 3.11+
- Local ArtPaper app at `/Applications/Artpaper.app` for the initial metadata import
- Optional installed ArtPaper sandbox 5K pack for Essentials import

## Commands

```sh
make import-metadata
```

Imports metadata from the local ArtPaper app into the OpenArtPaper local library.

```sh
make import-installed-essentials
```

Preferred path for the Essentials collection when the installed ArtPaper sandbox contains `5k_pack_0`; this imports the actual 5K Essentials images locally.

```sh
make download-essentials
```

Fallback only. The current Google preview URLs for Essentials cap images around 1200px, so use the installed-pack import when available.

```sh
make download-all
```

Do not use this yet. Collections 7-15 currently reference local package filenames such as `0.jpg`, not HTTP URLs, and high-resolution acquisition for those collections still needs to be revised.

```sh
make run-app
```

Runs the Swift app once the minimal macOS app tasks are implemented.

## Current data-source notes

The root-cause finding so far: Google manifest URLs are preview URLs capped around 1200px. ArtPaper's actual 5K Essentials images came from the installed `5k_pack_0` package, not from those Google preview URLs.

## Roadmap

### 1. Local data pipeline

Status: metadata import and Essentials installed-pack import are done.

Remaining work: define and implement a high-resolution acquisition strategy for the other collections.

### 2. Minimal macOS app

Build the first menu-bar app that:

- Reads local manifests from `~/Pictures/OpenArtPaperLibrary/`
- Chooses a random downloaded artwork
- Sets the selected image as the macOS wallpaper
- Provides basic menu controls

### 3. Better local product

Improve the local app experience with:

- Interval settings
- Collection filtering
- Favorites
- Artwork detail views
- Launch-at-login support

### 4. Self-hosted mirror

Prepare a hosted distribution path without making the app depend on it first:

- Export CDN-ready manifests and images
- Serve from a static origin
- Put Cloudflare in front
- Preserve upstream fallback and provenance metadata

### 5. Public release

Package the app for public use:

- App bundle
- Icon
- Code signing
- Notarization
- GitHub Releases
