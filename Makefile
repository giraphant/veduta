ARTPAPER_APP ?= /Applications/Artpaper.app
ARTPAPER_IMAGE_ROOT ?= $(HOME)/Library/Containers/andriiliakh.Artpaper/Data/Documents/Artpaperimg
LIBRARY_ROOT ?= $(HOME)/Pictures/VedutaLibrary
PYTHONPATH := data/src

.PHONY: test-data test-swift test import-metadata import-cleveland import-chicago import-met import-nga import-harvard import-smithsonian import-vam import-ycba download-essentials import-installed-essentials download-all run-app

test-data:
	cd data && python3 -m pytest -q

test-swift:
	swift test

test: test-data test-swift

import-metadata:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-metadata --artpaper-app "$(ARTPAPER_APP)" --library-root "$(LIBRARY_ROOT)"

import-cleveland:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-cleveland --library-root "$(LIBRARY_ROOT)" --fetch-limit 250 --limit 100 --min-long-edge 3000

import-chicago:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-chicago-api --library-root "$(LIBRARY_ROOT)" --fetch-limit 250 --limit 100 --min-long-edge 3000

import-met:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-met --library-root "$(LIBRARY_ROOT)" --fetch-limit 250 --limit 100

import-nga:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-nga --library-root "$(LIBRARY_ROOT)" --fetch-limit 250 --limit 100 --min-long-edge 3000

import-harvard:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-harvard --library-root "$(LIBRARY_ROOT)" --fetch-limit 250 --limit 100 --min-long-edge 3000

import-smithsonian:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-smithsonian --library-root "$(LIBRARY_ROOT)" --fetch-limit 500 --limit 100 --min-long-edge 3000

import-vam:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-vam --library-root "$(LIBRARY_ROOT)" --fetch-limit 1000 --limit 100 --min-long-edge 2500

import-ycba:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-ycba --library-root "$(LIBRARY_ROOT)" --fetch-limit 1000 --limit 100 --min-long-edge 2500

download-essentials:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli download --library-root "$(LIBRARY_ROOT)" --collection essentials --delay 1.0

import-installed-essentials:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli import-installed-packs --library-root "$(LIBRARY_ROOT)" --artpaper-image-root "$(ARTPAPER_IMAGE_ROOT)" --quality 5k --collection essentials

download-all:
	cd data && PYTHONPATH=src python3 -m veduta_data.cli download --library-root "$(LIBRARY_ROOT)" --all --delay 1.0

run-app:
	VEDUTA_LIBRARY_DIR="$(LIBRARY_ROOT)" swift run Veduta
