# Veduta

A local-first, open-source macOS wallpaper app for public-domain and museum artwork.

The name comes from *veduta* — the 18th-century genre of highly detailed view paintings. The idea is the same: a faithful, full-resolution picture on your desktop, refreshed whenever you like.

Right now Veduta is two things: a local data pipeline that builds an artwork library on your machine, and a minimal menu-bar app that rotates wallpapers from it. Hosting, sync, and a packaged release come later.

## How it works

The pipeline writes a library outside the repo, under `~/Pictures/VedutaLibrary/`:

```text
~/Pictures/VedutaLibrary/
├── catalog.json
├── collections/*.json
└── images/<collection-id>/*.jpg
```

Downloaded artwork and generated library files are never committed.

## Requirements

- macOS 13+
- Swift 5.9+
- Python 3.11+
- ArtPaper installed at `/Applications/Artpaper.app` (used only for the initial metadata import)
- Optional: the installed ArtPaper 5K pack, for high-resolution Essentials

## Commands

```sh
make import-metadata             # import metadata from the local ArtPaper app
make import-installed-essentials # import the real 5K Essentials images (preferred)
make download-essentials         # fallback; Google previews cap around 1200px
make run-app                     # run the menu-bar app
```

`make download-all` isn't ready yet — collections 7–15 still need a high-resolution source.

## Roadmap

1. **Data pipeline** — metadata and Essentials import work; other collections still need a high-res source.
2. **Menu-bar app** — read the local library, pick a random artwork, set it as wallpaper, basic controls. *(done)*
3. **Better local app** — intervals, collection filters, favorites, artwork details, launch at login.
4. **Self-hosted mirror** — export CDN-ready manifests and images, serve from a static origin, keep upstream fallback and provenance.
5. **Public release** — app bundle, icon, signing, notarization, GitHub Releases.

## License

Open source. Artwork is public-domain or museum-provided; see each collection's metadata for provenance.
