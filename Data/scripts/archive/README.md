# Archived one-off tools

These are **one-off tools** used while curating the *initial* artwork library
— pruning low-resolution images, rescanning Wikimedia Commons, retrying
dezoomify on Google Arts assets, and marking sparse metadata.

They are **not part of the build**: none are invoked by `make` or by
`veduta_data.cli`, and you do **not** need them to build, rebuild, or run
Veduta. The reproducible pipeline lives in `data/src/veduta_data/` and is
driven by the `make import-*` targets.

They are kept here for **provenance** — a record of how the library was
cleaned — not as supported, maintained scripts.

| Script | What it did once |
|---|---|
| `commons_scan.py` | Scan Wikimedia Commons for higher-res replacements |
| `commons_download.py` | Download the replacements that scan found |
| `dezoomify_lowres.py` | Retry dezoomify on low-res Google Arts assets |
| `mark_lowres_artworks.py` | Flag artworks whose image is below the resolution bar |
| `apply_lowres_candidates.py` | Apply reviewed low-res replacement candidates |
| `remove_lowres_artworks.py` | Drop artworks that stayed below the bar |
| `mark_sparse_metadata_artworks.py` | Flag artworks with thin metadata |

> For the live mirror-publishing tool, see `../publish_mirror.py` — that one
> *is* meant to be run repeatedly (`make publish-mirror`).
