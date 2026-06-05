ARTPAPER_APP ?= /Applications/Artpaper.app
ARTPAPER_IMAGE_ROOT ?= $(HOME)/Library/Containers/andriiliakh.Artpaper/Data/Documents/Artpaperimg
LIBRARY_ROOT ?= $(HOME)/Pictures/VedutaLibrary
PYTHONPATH := data/src

# ---------------------------------------------------------------------------
# App bundle / release
# ---------------------------------------------------------------------------
APP_NAME    := Veduta
BUILD_DIR   := .build
RELEASE_DIR := $(BUILD_DIR)/release
APP_BUNDLE  := $(BUILD_DIR)/$(APP_NAME).app
INSTALL_DIR := /Applications
DIST_DIR    := $(BUILD_DIR)/dist
DIST_APP    := $(DIST_DIR)/$(APP_NAME).app
DIST_DMG    := $(DIST_DIR)/$(APP_NAME).dmg
DMG_STAGING := $(BUILD_DIR)/dmg-staging

# Homebrew tap that ships the cask. `make release` bumps the cask here so
# users can `brew upgrade --cask veduta`.
TAP_REPO  ?= giraphant/homebrew-tap
CASK_PATH := Casks/veduta.rb

# Per-developer signing config lives in Makefile.local (gitignored). It
# defines DEVELOPER_ID_IDENTITY and NOTARY_PROFILE for your Apple account.
# If absent, the public defaults below act as placeholders and the codesign
# step falls back to ad-hoc.
-include Makefile.local

DEVELOPER_ID_IDENTITY ?= Developer ID Application: <Your Name> (<TEAMID>)
NOTARY_PROFILE        ?= <YourNotaryProfile>

CODESIGN_IDENTITY     ?= $(DEVELOPER_ID_IDENTITY)
CODESIGN_OPTIONS      ?= --options runtime
CODESIGN_ENTITLEMENTS ?= --entitlements Resources/Veduta.entitlements

.PHONY: all build run install dist notarize release update-cask clean \
        test-data test-swift test import-metadata import-cleveland import-chicago \
        import-met import-nga import-harvard import-smithsonian import-vam import-ycba \
        download-essentials import-installed-essentials download-all run-app

all: build

build:
	swift build -c release
	@rm -rf $(APP_BUNDLE)
	@mkdir -p $(APP_BUNDLE)/Contents/MacOS
	@mkdir -p $(APP_BUNDLE)/Contents/Resources
	@cp $(RELEASE_DIR)/$(APP_NAME) $(APP_BUNDLE)/Contents/MacOS/$(APP_NAME)
	@cp Resources/Info.plist $(APP_BUNDLE)/Contents/Info.plist
	@cp Assets/AppIcon.icns $(APP_BUNDLE)/Contents/Resources/AppIcon.icns
	@cp Assets/menubar-icon.pdf $(APP_BUNDLE)/Contents/Resources/menubar-icon.pdf
	@cp -R Resources/en.lproj $(APP_BUNDLE)/Contents/Resources/en.lproj
	@cp -R Resources/zh-Hans.lproj $(APP_BUNDLE)/Contents/Resources/zh-Hans.lproj
	@if security find-identity -v -p codesigning | grep -F "$(CODESIGN_IDENTITY)" >/dev/null 2>&1; then \
		codesign --force --deep $(CODESIGN_OPTIONS) $(CODESIGN_ENTITLEMENTS) --sign "$(CODESIGN_IDENTITY)" $(APP_BUNDLE); \
		echo "Built $(APP_BUNDLE) (signed with: $(CODESIGN_IDENTITY))"; \
	else \
		codesign --force --deep --sign - $(APP_BUNDLE); \
		echo "Built $(APP_BUNDLE) (ad-hoc signed — Developer ID cert missing from keychain)"; \
	fi

run: build
	open $(APP_BUNDLE)

install: build
	@rm -rf "$(INSTALL_DIR)/$(APP_NAME).app"
	@cp -R $(APP_BUNDLE) "$(INSTALL_DIR)/"
	@echo "Installed to $(INSTALL_DIR)/$(APP_NAME).app"

dist:
	@$(MAKE) build CODESIGN_OPTIONS="--options runtime --timestamp"
	@rm -rf "$(DIST_DIR)" "$(DMG_STAGING)"
	@mkdir -p "$(DIST_DIR)" "$(DMG_STAGING)"
	@cp -R "$(APP_BUNDLE)" "$(DIST_APP)"
	@cp -R "$(APP_BUNDLE)" "$(DMG_STAGING)/$(APP_NAME).app"
	@ln -s /Applications "$(DMG_STAGING)/Applications"
	@hdiutil create -volname "$(APP_NAME)" -srcfolder "$(DMG_STAGING)" -ov -format UDZO "$(DIST_DMG)" >/dev/null
	@codesign --force --sign "$(DEVELOPER_ID_IDENTITY)" --timestamp "$(DIST_DMG)"
	@echo "Packaged $(DIST_DMG)"

notarize: dist
	xcrun notarytool submit "$(DIST_DMG)" --keychain-profile "$(NOTARY_PROFILE)" --wait
	xcrun stapler staple "$(DIST_DMG)"
	@echo "Notarized and stapled $(DIST_DMG)"

# One-shot release: assumes Info.plist already bumped to $(VERSION) and committed.
release:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=0.1.0"; exit 1; fi
	@plist_v=$$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" Resources/Info.plist); \
	if [ "$$plist_v" != "$(VERSION)" ]; then \
		echo "ERROR: Info.plist version $$plist_v != VERSION=$(VERSION). Bump Info.plist first."; exit 1; \
	fi
	@if ! git diff-index --quiet HEAD --; then \
		echo "ERROR: working tree has uncommitted changes. Commit the version bump first."; exit 1; \
	fi
	@$(MAKE) notarize
	gh release create "v$(VERSION)" "$(DIST_DMG)" --title "v$(VERSION)" --generate-notes
	@echo "Release v$(VERSION) published. Tag pushed by gh."
	@$(MAKE) update-cask VERSION=$(VERSION)

# Bump the Homebrew cask in $(TAP_REPO) to $(VERSION) with the DMG's sha256.
update-cask:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make update-cask VERSION=0.1.0"; exit 1; fi
	@if [ ! -f "$(DIST_DMG)" ]; then echo "ERROR: $(DIST_DMG) not found. Run 'make dist' first."; exit 1; fi
	@sha=$$(shasum -a 256 "$(DIST_DMG)" | awk '{print $$1}'); \
	tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	echo "Cloning $(TAP_REPO)..."; \
	gh repo clone "$(TAP_REPO)" "$$tmp" -- -q || exit 1; \
	sed -i '' -E "s/^  version \".*\"/  version \"$(VERSION)\"/" "$$tmp/$(CASK_PATH)"; \
	sed -i '' -E "s/^  sha256 \".*\"/  sha256 \"$$sha\"/" "$$tmp/$(CASK_PATH)"; \
	git -C "$$tmp" add "$(CASK_PATH)"; \
	if git -C "$$tmp" diff --cached --quiet; then \
		echo "Cask already at $(VERSION) / $$sha — nothing to push."; \
	else \
		git -C "$$tmp" commit -q -m "veduta $(VERSION)"; \
		git -C "$$tmp" push -q origin HEAD; \
		echo "Cask bumped to $(VERSION) ($$sha) and pushed to $(TAP_REPO)."; \
	fi

clean:
	rm -rf $(BUILD_DIR)

# ---------------------------------------------------------------------------
# Data pipeline / tests
# ---------------------------------------------------------------------------
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
