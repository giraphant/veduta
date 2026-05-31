# Main Window Menu Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current small settings-style UI and menu-bar dropdown with a standard macOS main window layout: left sidebar, native grouped detail pages, and a concise companion status menu.

**Architecture:** Keep the current AppKit lifecycle in `Sources/Veduta/main.swift` and continue hosting SwiftUI from `SettingsWindowController`; this avoids converting the package executable to a SwiftUI `@main` app. Repurpose the existing settings window into the app's main window, add a native `NavigationSplitView`/`Form` detail layout, and update the AppDelegate menu builder to open/focus that window.

**Tech Stack:** Swift 5.9, SwiftUI, AppKit `NSStatusItem`, Swift Package Manager, XCTest for existing core tests, manual macOS UI verification.

---

## File Structure

- Modify `Sources/Veduta/SettingsWindowController.swift`
  - Keep this file as the hosted SwiftUI window controller to minimize churn.
  - Change the window title/size to a main-window shape.
  - Change `SettingsPane` to the final sidebar pages: `wallpaper`, `settings`, `collections`, `library`, `about`.
  - Replace custom cards/gradient icons with native `List` sidebar and grouped `Form` detail pages.
  - Add `libraryPath` and `downloadedCollectionCount` to `SettingsSnapshot` so the Library page can render without reading app state directly.

- Modify `Sources/Veduta/main.swift`
  - Rename the menu action from settings-oriented wording to `Open Veduta`.
  - Reorder the status menu to match the design spec.
  - Add a `collectionsMenu()` helper so collections live under a submenu instead of inline menu rows.
  - Populate the new snapshot fields from `library.root` and `collectionSummaries.count`.

- Modify `.gitignore`
  - Keep `.superpowers/` ignored because visual companion artifacts are local scratch files.

- Test with existing commands:
  - `swift test`
  - `swift build`
  - `make run-app` for manual UI verification.

## Task 1: Extend the settings snapshot for main-window content

**Files:**
- Modify: `Sources/Veduta/SettingsWindowController.swift:24-43`
- Modify: `Sources/Veduta/main.swift:264-282`

- [ ] **Step 1: Update `SettingsSnapshot` fields**

In `Sources/Veduta/SettingsWindowController.swift`, change the struct and `.empty` value to include library information:

```swift
struct SettingsSnapshot: Equatable {
    let showMenuBarIcon: Bool
    let showDockIcon: Bool
    let rotationIntervalSeconds: TimeInterval?
    let rotationOptions: [SettingsRotationOption]
    let collections: [SettingsCollectionOption]
    let currentArtworkTitle: String?
    let currentArtworkCreator: String?
    let statusMessage: String
    let libraryPath: String
    let downloadedCollectionCount: Int

    static let empty = SettingsSnapshot(
        showMenuBarIcon: true,
        showDockIcon: false,
        rotationIntervalSeconds: 30 * 60,
        rotationOptions: [],
        collections: [],
        currentArtworkTitle: nil,
        currentArtworkCreator: nil,
        statusMessage: "Ready",
        libraryPath: "",
        downloadedCollectionCount: 0
    )
}
```

- [ ] **Step 2: Run build to see the missing initializer arguments**

Run: `swift build`

Expected: FAIL with an error pointing at `SettingsSnapshot(` in `Sources/Veduta/main.swift` because `libraryPath` and `downloadedCollectionCount` are missing.

- [ ] **Step 3: Populate snapshot fields from `AppDelegate.settingsSnapshot()`**

In `Sources/Veduta/main.swift`, update `settingsSnapshot()` to pass the new fields at the end:

```swift
private func settingsSnapshot() -> SettingsSnapshot {
    SettingsSnapshot(
        showMenuBarIcon: preferences.showMenuBarIcon,
        showDockIcon: preferences.showDockIcon,
        rotationIntervalSeconds: rotationIntervalSeconds,
        rotationOptions: rotationIntervalOptions.map { SettingsRotationOption(title: $0.title, seconds: $0.seconds) },
        collections: collectionSummaries.map { summary in
            let isEnabled = enabledCollectionIDs.contains(summary.id)
            return SettingsCollectionOption(
                id: summary.id,
                title: summary.shortName,
                isEnabled: isEnabled,
                isToggleEnabled: collectionSummaries.count > 1 && (!isEnabled || enabledCollectionIDs.count > 1)
            )
        },
        currentArtworkTitle: currentSelections.first?.artwork.title,
        currentArtworkCreator: currentSelections.first?.artwork.creator,
        statusMessage: statusMessage,
        libraryPath: library.root.path,
        downloadedCollectionCount: collectionSummaries.count
    )
}
```

- [ ] **Step 4: Run build to verify this data-shape change compiles**

Run: `swift build`

Expected: PASS, or only errors from later tasks if this task is being applied together with them.

- [ ] **Step 5: Commit if commits are authorized**

Only run this if the user explicitly authorized commits for this implementation session:

```bash
git add Sources/Veduta/SettingsWindowController.swift Sources/Veduta/main.swift
git commit -m "refactor: extend app window snapshot"
```

## Task 2: Change the window shell and sidebar pages

**Files:**
- Modify: `Sources/Veduta/SettingsWindowController.swift:56-115`

- [ ] **Step 1: Replace `SettingsPane` with the main-window page list**

Replace the current `SettingsPane` enum with:

```swift
private enum SettingsPane: String, CaseIterable, Identifiable, Hashable {
    case wallpaper
    case settings
    case collections
    case library
    case about

    var id: Self { self }

    var title: String {
        switch self {
        case .wallpaper: "Wallpaper"
        case .settings: "Settings"
        case .collections: "Collections"
        case .library: "Library"
        case .about: "About"
        }
    }

    var symbolName: String {
        switch self {
        case .wallpaper: "photo.on.rectangle"
        case .settings: "gearshape"
        case .collections: "square.grid.2x2"
        case .library: "folder"
        case .about: "info.circle"
        }
    }
}
```

- [ ] **Step 2: Update the controller default pane and window sizing**

In `SettingsWindowController`, change the selected pane and window setup to:

```swift
private var selectedPane = SettingsPane.wallpaper
private lazy var hostingController = NSHostingController(rootView: makeView())

init() {
    let window = NSWindow(
        contentRect: NSRect(x: 0, y: 0, width: 980, height: 680),
        styleMask: [.titled, .closable, .miniaturizable, .resizable],
        backing: .buffered,
        defer: false
    )
    window.title = "Veduta"
    window.isReleasedWhenClosed = false
    window.minSize = NSSize(width: 820, height: 540)
    super.init(window: window)
    window.contentViewController = hostingController
    window.titlebarAppearsTransparent = true
    window.toolbarStyle = .unified
    window.setFrameAutosaveName("VedutaMainWindow")
    window.center()
}
```

- [ ] **Step 3: Run build to catch remaining enum switch errors**

Run: `swift build`

Expected: FAIL until the detail `switch` and sidebar loops are updated in Task 3, because old cases such as `.general` still exist in view code.

- [ ] **Step 4: Commit if commits are authorized**

Only run this if the user explicitly authorized commits for this implementation session:

```bash
git add Sources/Veduta/SettingsWindowController.swift
git commit -m "refactor: define main window sidebar pages"
```

## Task 3: Replace custom settings cards with native grouped forms

**Files:**
- Modify: `Sources/Veduta/SettingsWindowController.swift:171-593`

- [ ] **Step 1: Replace `SettingsView.body`, sidebar, and detail switch**

In `SettingsView`, replace the existing `body`, `sidebar`, `sidebarItem(for:)`, and `detailView` implementations with:

```swift
var body: some View {
    NavigationSplitView {
        sidebar
    } detail: {
        detailView
            .navigationTitle((selectedPane ?? .wallpaper).title)
    }
    .navigationSplitViewStyle(.balanced)
    .onChange(of: selectedPane) { pane in
        if let pane {
            onPaneChanged(pane)
        }
    }
}

private var sidebar: some View {
    List(selection: $selectedPane) {
        ForEach(SettingsPane.allCases) { pane in
            Label(pane.title, systemImage: pane.symbolName)
                .foregroundStyle(.primary)
                .tag(pane)
        }
    }
    .listStyle(.sidebar)
    .navigationSplitViewColumnWidth(min: 170, ideal: 190, max: 230)
}

@ViewBuilder
private var detailView: some View {
    switch selectedPane ?? .wallpaper {
    case .wallpaper:
        wallpaperPane
    case .settings:
        settingsPane
    case .collections:
        collectionsPane
    case .library:
        libraryPane
    case .about:
        aboutPane
    }
}
```

- [ ] **Step 2: Replace the old `generalPane` with `settingsPane`**

Delete `generalPane` and add:

```swift
private var settingsPane: some View {
    Form {
        Section("App Visibility") {
            Toggle("Show menu bar icon", isOn: Binding(
                get: { snapshot.showMenuBarIcon },
                set: { value in onMenuBarChanged(value) }
            ))

            Toggle("Show Dock icon on next launch", isOn: Binding(
                get: { snapshot.showDockIcon },
                set: { value in onDockChanged(value) }
            ))
        }

        Section("Recovery") {
            Text("If both icons are hidden, open Veduta again from Finder or Spotlight to show this window.")
                .foregroundStyle(.secondary)
        }
    }
    .formStyle(.grouped)
}
```

- [ ] **Step 3: Replace `wallpaperPane` with native sections**

Replace the current `wallpaperPane` with:

```swift
private var wallpaperPane: some View {
    Form {
        Section("Current Wallpaper") {
            LabeledContent("Artwork") {
                Text(snapshot.currentArtworkTitle ?? "No wallpaper selected yet")
                    .multilineTextAlignment(.trailing)
            }

            if let creator = snapshot.currentArtworkCreator {
                LabeledContent("Creator") {
                    Text(creator)
                        .multilineTextAlignment(.trailing)
                }
            }

            if snapshot.statusMessage != "Ready" {
                LabeledContent("Status") {
                    Text(snapshot.statusMessage)
                        .multilineTextAlignment(.trailing)
                }
            }
        }

        Section("Rotation") {
            Picker("Interval", selection: Binding(
                get: { SettingsRotationOption(title: "", seconds: snapshot.rotationIntervalSeconds).id },
                set: { value in
                    guard let option = snapshot.rotationOptions.first(where: { $0.id == value }) else { return }
                    onRotationChanged(option.seconds)
                }
            )) {
                ForEach(snapshot.rotationOptions) { option in
                    Text(option.title).tag(option.id)
                }
            }
            .pickerStyle(.menu)
        }

        Section("Actions") {
            Button("Next Wallpaper", action: onNextWallpaper)
                .keyboardShortcut("n")
        }
    }
    .formStyle(.grouped)
}
```

- [ ] **Step 4: Replace `collectionsPane` with a grouped form list**

Replace the current `collectionsPane` with:

```swift
private var collectionsPane: some View {
    Form {
        Section("Downloaded Collections") {
            if snapshot.collections.isEmpty {
                Text("No downloaded collections found yet.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(snapshot.collections) { collection in
                    Toggle(collection.title, isOn: Binding(
                        get: { collection.isEnabled },
                        set: { value in onCollectionChanged(collection.id, value) }
                    ))
                    .disabled(!collection.isToggleEnabled)

                    if !collection.isToggleEnabled {
                        Text("At least one collection must stay enabled.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }
    .formStyle(.grouped)
}
```

- [ ] **Step 5: Add `libraryPane`**

Add this new pane before `aboutPane`:

```swift
private var libraryPane: some View {
    Form {
        Section("Local Library") {
            LabeledContent("Path") {
                Text(snapshot.libraryPath.isEmpty ? "Not configured" : snapshot.libraryPath)
                    .multilineTextAlignment(.trailing)
                    .textSelection(.enabled)
            }

            LabeledContent("Downloaded Collections") {
                Text("\(snapshot.downloadedCollectionCount)")
            }
        }

        Section("Actions") {
            Button("Open Library Folder", action: onOpenLibraryFolder)
        }
    }
    .formStyle(.grouped)
}
```

- [ ] **Step 6: Replace `aboutPane` with native sections**

Replace the current `aboutPane` with:

```swift
private var aboutPane: some View {
    Form {
        Section("Veduta") {
            LabeledContent("App") {
                Text("Veduta")
            }

            Text("A local-first open-source wallpaper rotator for macOS.")
                .foregroundStyle(.secondary)
        }

        Section("Actions") {
            Button("Open Library Folder", action: onOpenLibraryFolder)
            Button("Quit Veduta", action: onQuit)
        }
    }
    .formStyle(.grouped)
}
```

- [ ] **Step 7: Delete unused custom view helpers**

Remove these now-unused types from the bottom of `SettingsWindowController.swift`:

```swift
private struct SettingsDetail<Content: View>: View { ... }
private struct SettingsHeader: View { ... }
private struct SettingsSection<Content: View>: View { ... }
private struct SettingsCard<Content: View>: View { ... }
private struct SettingsToggleRow: View { ... }
private struct SettingsControlRow<Content: View>: View { ... }
private struct SettingsValueRow: View { ... }
private struct SettingsDivider: View { ... }
```

Do not leave placeholder comments for removed helpers.

- [ ] **Step 8: Run build to verify the main window view compiles**

Run: `swift build`

Expected: PASS.

- [ ] **Step 9: Commit if commits are authorized**

Only run this if the user explicitly authorized commits for this implementation session:

```bash
git add Sources/Veduta/SettingsWindowController.swift
git commit -m "refactor: use native main window forms"
```

## Task 4: Reorder the menu-bar dropdown around the main window

**Files:**
- Modify: `Sources/Veduta/main.swift:49-99`
- Modify: `Sources/Veduta/main.swift:185-219`

- [ ] **Step 1: Replace `rebuildMenu(message:)` ordering**

Replace the body of `rebuildMenu(message:)` with this ordering:

```swift
private func rebuildMenu(message: String) {
    statusMessage = message
    guard let statusItem else { return }
    let menu = NSMenu()

    let openItem = NSMenuItem(title: "Open Veduta", action: #selector(openMainWindow), keyEquivalent: "")
    openItem.target = self
    menu.addItem(openItem)

    menu.addItem(.separator())

    let nextItem = NSMenuItem(title: "Next Wallpaper", action: #selector(nextWallpaper), keyEquivalent: "n")
    nextItem.target = self
    menu.addItem(nextItem)

    if !currentSelections.isEmpty {
        let currentWallpapersItem = NSMenuItem(title: "Current Wallpapers", action: nil, keyEquivalent: "")
        currentWallpapersItem.submenu = currentWallpapersMenu()
        menu.addItem(currentWallpapersItem)
    }

    if !collectionSummaries.isEmpty {
        let collectionsItem = NSMenuItem(title: "Collections", action: nil, keyEquivalent: "")
        collectionsItem.submenu = collectionsMenu()
        menu.addItem(collectionsItem)
    }

    let rotationItem = NSMenuItem(title: "Rotation Interval", action: nil, keyEquivalent: "")
    rotationItem.submenu = rotationIntervalMenu()
    menu.addItem(rotationItem)

    menu.addItem(.separator())

    let quitItem = NSMenuItem(title: "Quit Veduta", action: #selector(quit), keyEquivalent: "q")
    quitItem.target = self
    menu.addItem(quitItem)

    statusItem.menu = menu
}
```

- [ ] **Step 2: Add `collectionsMenu()` helper**

Add this helper near `currentWallpapersMenu()`:

```swift
private func collectionsMenu() -> NSMenu {
    let menu = NSMenu()
    for summary in collectionSummaries {
        let item = NSMenuItem(title: summary.shortName, action: #selector(toggleCollection(_:)), keyEquivalent: "")
        item.target = self
        item.representedObject = summary.id
        item.state = enabledCollectionIDs.contains(summary.id) ? .on : .off
        item.isEnabled = collectionSummaries.count > 1 && (!enabledCollectionIDs.contains(summary.id) || enabledCollectionIDs.count > 1)
        menu.addItem(item)
    }
    return menu
}
```

- [ ] **Step 3: Rename `openSettings` selector to `openMainWindow`**

Replace:

```swift
@objc private func openSettings() { showSettingsWindow() }
```

with:

```swift
@objc private func openMainWindow() { showSettingsWindow() }
```

Keep `showSettingsWindow()` as the internal method name for this pass to avoid unnecessary delegate renames.

- [ ] **Step 4: Run build to catch selector/name errors**

Run: `swift build`

Expected: PASS.

- [ ] **Step 5: Commit if commits are authorized**

Only run this if the user explicitly authorized commits for this implementation session:

```bash
git add Sources/Veduta/main.swift
git commit -m "refactor: simplify menu bar dropdown"
```

## Task 5: Run automated verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Run Swift unit tests**

Run: `swift test`

Expected: PASS for existing VedutaCore tests.

- [ ] **Step 2: Run a full Swift build**

Run: `swift build`

Expected: PASS for `VedutaCore` and `Veduta` targets.

- [ ] **Step 3: Commit verification-only changes if commits are authorized and there are staged docs/gitignore changes**

Only run this if the user explicitly authorized commits for this implementation session:

```bash
git status --short
git add .gitignore docs/superpowers/specs/2026-05-28-main-window-menu-layout-design.md docs/superpowers/plans/2026-05-28-main-window-menu-layout.md
git commit -m "docs: plan main window menu layout"
```

## Task 6: Manual UI verification

**Files:**
- No source edits expected unless verification finds a concrete defect.

- [ ] **Step 1: Start the app**

Run: `make run-app`

Expected: The app launches and opens an `Veduta` window.

- [ ] **Step 2: Verify the main window**

Expected UI checks:

```text
- Left sidebar shows Wallpaper, Settings, Collections, Library, About.
- Detail page title follows the selected sidebar item.
- Right side uses native grouped form sections, not custom gradient cards.
- System dark/light mode controls colors; no copied green reference palette appears.
- Wallpaper page shows current artwork information and Next Wallpaper.
- Settings page toggles menu-bar and Dock preferences.
- Collections page disables the final enabled collection toggle.
- Library page shows the local library path and opens the folder.
```

- [ ] **Step 3: Verify the menu-bar dropdown**

Expected menu order:

```text
Open Veduta
---
Next Wallpaper
Current Wallpapers      (submenu, when current selections exist)
Collections             (submenu, when collections exist)
Rotation Interval       (submenu)
---
Quit Veduta
```

- [ ] **Step 4: Stop the app from the menu**

Use `Quit Veduta` from the status menu.

Expected: App exits cleanly.
