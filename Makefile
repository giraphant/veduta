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
