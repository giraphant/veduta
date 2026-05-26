ARTPAPER_APP ?= /Applications/Artpaper.app
ARTPAPER_IMAGE_ROOT ?= $(HOME)/Library/Containers/andriiliakh.Artpaper/Data/Documents/Artpaperimg
LIBRARY_ROOT ?= $(HOME)/Pictures/OpenArtPaperLibrary
PYTHONPATH := data-ops/src

.PHONY: test-data test-swift test import-metadata download-essentials import-installed-essentials download-all run-app

test-data:
	cd data-ops && python3 -m pytest -q

test-swift:
	swift test

test: test-data test-swift

import-metadata:
	cd data-ops && PYTHONPATH=src python3 -m openartpaper_data.cli import-metadata --artpaper-app "$(ARTPAPER_APP)" --library-root "$(LIBRARY_ROOT)"

download-essentials:
	cd data-ops && PYTHONPATH=src python3 -m openartpaper_data.cli download --library-root "$(LIBRARY_ROOT)" --collection essentials --delay 1.0

import-installed-essentials:
	cd data-ops && PYTHONPATH=src python3 -m openartpaper_data.cli import-installed-packs --library-root "$(LIBRARY_ROOT)" --artpaper-image-root "$(ARTPAPER_IMAGE_ROOT)" --quality 5k --collection essentials

download-all:
	cd data-ops && PYTHONPATH=src python3 -m openartpaper_data.cli download --library-root "$(LIBRARY_ROOT)" --all --delay 1.0

run-app:
	OPENARTPAPER_LIBRARY_DIR="$(LIBRARY_ROOT)" swift run OpenArtPaper
