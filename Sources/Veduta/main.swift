import AppKit
import Foundation
import VedutaCore

final class AppDelegate: NSObject, NSApplicationDelegate, SettingsWindowControllerDelegate {
    private var statusItem: NSStatusItem?
    private var currentSelections: [(artwork: Artwork, imageURL: URL)] = []
    private var collectionSummaries: [CollectionSummary] = []
    private var statusMessage = "Ready"
    private var enabledCollectionIDs = Set<String>()
    private var enabledArtworkKinds = Set(ArtworkKind.allCases)
    private var rotationIntervalSeconds: TimeInterval? = AppPreferences.defaultRotationIntervalSeconds
    private let preferences = AppPreferences()
    private let picker = RandomArtworkPicker()
    private let wallpaperService = WallpaperService()
    private lazy var settingsWindowController: SettingsWindowController = {
        let controller = SettingsWindowController()
        controller.delegate = self
        return controller
    }()
    private var timer: Timer?

    private var isRotating = false

    private lazy var library: LocalLibrary = {
        let environmentPath = ProcessInfo.processInfo.environment["VEDUTA_LIBRARY_DIR"]
        let root: URL
        if let environmentPath, !environmentPath.isEmpty {
            root = URL(fileURLWithPath: environmentPath).standardizedFileURL
        } else {
            root = FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Pictures")
                .appendingPathComponent("VedutaLibrary")
        }
        return LocalLibrary(root: root, mirror: Self.makeMirror())
    }()

    /// The published mirror images and manifests stream from when they aren't
    /// present locally. Defaults to the public origin; override the base URL
    /// with `VEDUTA_MIRROR_BASE_URL`, or disable streaming with
    /// `VEDUTA_MIRROR=off` (then the app is purely local, as before).
    private static func makeMirror() -> MirrorClient? {
        let environment = ProcessInfo.processInfo.environment
        if environment["VEDUTA_MIRROR"] == "off" { return nil }
        let base = environment["VEDUTA_MIRROR_BASE_URL"]
            .flatMap(URL.init(string:))
            ?? URL(string: "https://garage.ramu.us/")!
        return MirrorClient(baseURL: base)
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        loadPreferences()
        applyDockActivationPolicy()
        updateStatusItemVisibility()
        showSettingsWindow()
        rotateWallpaper()
        rescheduleTimer()
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showSettingsWindow()
        return false
    }

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

        let artworkKindsItem = NSMenuItem(title: "Artwork Types", action: nil, keyEquivalent: "")
        artworkKindsItem.submenu = artworkKindsMenu()
        menu.addItem(artworkKindsItem)

        let rotationItem = NSMenuItem(title: "Rotation Interval", action: nil, keyEquivalent: "")
        rotationItem.submenu = rotationIntervalMenu()
        menu.addItem(rotationItem)

        menu.addItem(.separator())

        let quitItem = NSMenuItem(title: "Quit Veduta", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)

        statusItem.menu = menu
    }

    private func updateStatusItemVisibility() {
        if preferences.showMenuBarIcon {
            if statusItem == nil {
                statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
                if let button = statusItem?.button {
                    let image = menuBarIcon()
                    image?.isTemplate = true
                    button.image = image
                }
            }
            rebuildMenu(message: statusMessage)
        } else if let statusItem {
            NSStatusBar.system.removeStatusItem(statusItem)
            self.statusItem = nil
        }
    }

    /// Phosphor "mountains" glyph bundled as a vector PDF; falls back to an SF Symbol.
    private func menuBarIcon() -> NSImage? {
        if let url = Bundle.main.url(forResource: "menubar-icon", withExtension: "pdf"),
           let image = NSImage(contentsOf: url) {
            image.size = NSSize(width: 18, height: 18)
            return image
        }
        let config = NSImage.SymbolConfiguration(pointSize: 14, weight: .regular)
        return NSImage(systemSymbolName: "mountain.2", accessibilityDescription: "Veduta")?
            .withSymbolConfiguration(config)
    }

    private func applyDockActivationPolicy() {
        NSApp.setActivationPolicy(preferences.showDockIcon ? .regular : .accessory)
    }

    private var rotationIntervalOptions: [(title: String, seconds: TimeInterval?)] {
        [
            ("Manual Only", nil),
            ("15 Minutes", 15 * 60),
            ("30 Minutes", 30 * 60),
            ("1 Hour", 60 * 60),
            ("4 Hours", 4 * 60 * 60),
            ("12 Hours", 12 * 60 * 60),
            ("1 Day", 24 * 60 * 60)
        ]
    }

    private func currentWallpapersMenu() -> NSMenu {
        let menu = NSMenu()
        for (index, selection) in currentSelections.enumerated() {
            let displayItem = NSMenuItem(
                title: "Display \(index + 1): \(selection.artwork.title)",
                action: nil,
                keyEquivalent: ""
            )
            let displayMenu = NSMenu()

            let creatorItem = NSMenuItem(title: selection.artwork.creator, action: nil, keyEquivalent: "")
            creatorItem.isEnabled = false
            displayMenu.addItem(creatorItem)

            let openImageItem = NSMenuItem(title: "Reveal Image File", action: #selector(revealImageFile(_:)), keyEquivalent: "")
            openImageItem.target = self
            openImageItem.representedObject = selection.imageURL
            displayMenu.addItem(openImageItem)

            if let sourceURL = URL(string: selection.artwork.sources.canonicalPage) {
                let sourceItem = NSMenuItem(title: "Open Source Page", action: #selector(openSourcePage(_:)), keyEquivalent: "")
                sourceItem.target = self
                sourceItem.representedObject = sourceURL
                displayMenu.addItem(sourceItem)
            }

            displayItem.submenu = displayMenu
            menu.addItem(displayItem)
        }
        return menu
    }

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

    private func artworkKindsMenu() -> NSMenu {
        let menu = NSMenu()
        for kind in ArtworkKind.allCases {
            let item = NSMenuItem(title: kind.displayName, action: #selector(toggleArtworkKind(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = kind.rawValue
            item.state = enabledArtworkKinds.contains(kind) ? .on : .off
            item.isEnabled = !enabledArtworkKinds.contains(kind) || enabledArtworkKinds.count > 1
            menu.addItem(item)
        }
        return menu
    }

    private func rotationIntervalMenu() -> NSMenu {
        let menu = NSMenu()
        for option in rotationIntervalOptions {
            let item = NSMenuItem(title: option.title, action: #selector(setRotationInterval(_:)), keyEquivalent: "")
            item.target = self
            item.representedObject = NSNumber(value: option.seconds ?? 0)
            item.state = rotationIntervalMatches(rotationIntervalSeconds, option.seconds) ? .on : .off
            menu.addItem(item)
        }
        return menu
    }

    private func rotationIntervalMatches(_ lhs: TimeInterval?, _ rhs: TimeInterval?) -> Bool {
        switch (lhs, rhs) {
        case (.none, .none):
            return true
        case let (.some(lhs), .some(rhs)):
            return abs(lhs - rhs) < 0.5
        default:
            return false
        }
    }

    @objc private func openMainWindow() { showSettingsWindow() }

    @objc private func nextWallpaper() { rotateWallpaper() }

    @objc private func setRotationInterval(_ sender: NSMenuItem) {
        guard let value = sender.representedObject as? NSNumber else { return }
        let seconds = value.doubleValue
        rotationIntervalSeconds = seconds > 0 ? seconds : nil
        saveRotationInterval()
        rescheduleTimer()
        rebuildMenu(message: "Ready")
        updateSettingsWindow()
    }

    @objc private func revealImageFile(_ sender: NSMenuItem) {
        guard let imageURL = sender.representedObject as? URL else { return }
        NSWorkspace.shared.activateFileViewerSelecting([imageURL])
    }

    @objc private func openSourcePage(_ sender: NSMenuItem) {
        guard let sourceURL = sender.representedObject as? URL else { return }
        NSWorkspace.shared.open(sourceURL)
    }

    @objc private func toggleCollection(_ sender: NSMenuItem) {
        guard let collectionID = sender.representedObject as? String else { return }
        if enabledCollectionIDs.contains(collectionID) {
            guard enabledCollectionIDs.count > 1 else { return }
            enabledCollectionIDs.remove(collectionID)
        } else {
            enabledCollectionIDs.insert(collectionID)
        }
        saveEnabledCollectionIDs()
        rebuildMenu(message: "Ready")
        updateSettingsWindow()
    }

    @objc private func toggleArtworkKind(_ sender: NSMenuItem) {
        guard let rawValue = sender.representedObject as? String,
              let kind = ArtworkKind(rawValue: rawValue)
        else { return }
        if enabledArtworkKinds.contains(kind) {
            guard enabledArtworkKinds.count > 1 else { return }
            enabledArtworkKinds.remove(kind)
        } else {
            enabledArtworkKinds.insert(kind)
        }
        saveEnabledArtworkKinds()
        rebuildMenu(message: "Ready")
        updateSettingsWindow()
    }

    private func rotateWallpaper() {
        guard !isRotating else { return }
        isRotating = true
        rebuildMenu(message: "Fetching wallpaper…")
        updateSettingsWindow()

        let kinds = enabledArtworkKinds
        let requestedCollections = enabledCollectionIDs
        let screenCount = max(NSScreen.screens.count, 1)

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            let outcome: Result<RotationResult, Error>
            do {
                let summaries = try self.library.availableCollections()
                let availableIDs = Set(summaries.map { $0.id })
                var enabled = requestedCollections.isEmpty
                    ? availableIDs
                    : requestedCollections.intersection(availableIDs)
                if enabled.isEmpty, let first = summaries.first { enabled = [first.id] }

                let artworks = try self.library.availableArtworks(
                    collectionIDs: enabled,
                    enabledArtworkKinds: kinds
                )
                let picked = try self.picker.pick(count: screenCount, from: artworks)
                let materialized = try self.materialize(picked, from: artworks)
                outcome = .success(RotationResult(summaries: summaries, enabled: enabled, selections: materialized))
            } catch {
                outcome = .failure(error)
            }

            DispatchQueue.main.async {
                self.isRotating = false
                self.applyRotationOutcome(outcome)
            }
        }
    }

    private struct RotationResult {
        let summaries: [CollectionSummary]
        let enabled: Set<String>
        let selections: [(artwork: Artwork, imageURL: URL)]
    }

    private func applyRotationOutcome(_ outcome: Result<RotationResult, Error>) {
        switch outcome {
        case let .success(result):
            collectionSummaries = result.summaries
            if result.enabled != enabledCollectionIDs {
                enabledCollectionIDs = result.enabled
                saveEnabledCollectionIDs()
            }
            do {
                try wallpaperService.setWallpapers(imageURLs: result.selections.map { $0.imageURL })
                currentSelections = result.selections
                rebuildMenu(message: "Ready")
            } catch {
                rebuildMenu(message: "Veduta error: \(error.localizedDescription)")
            }
        case let .failure(error):
            rebuildMenu(message: "Veduta error: \(error.localizedDescription)")
        }
        updateSettingsWindow()
    }

    /// Ensure each picked artwork has a local image, downloading from the
    /// mirror when needed. If one fails to materialize, fill from a spare so a
    /// transient fetch error doesn't abort the whole rotation. Runs on a
    /// background queue. `setWallpapers` cycles across screens, so one
    /// resolved image is enough.
    private func materialize(
        _ picked: [(Artwork, URL)],
        from pool: [(Artwork, URL)]
    ) throws -> [(artwork: Artwork, imageURL: URL)] {
        var resolved: [(artwork: Artwork, imageURL: URL)] = []
        var usedIDs = Set(picked.map { $0.0.id })
        var spares = pool.filter { !usedIDs.contains($0.0.id) }.shuffled()

        for item in picked {
            if let url = try? library.ensureLocalImage(for: item.0) {
                resolved.append((item.0, url))
                continue
            }
            while let spare = spares.popLast() {
                guard !usedIDs.contains(spare.0.id) else { continue }
                if let url = try? library.ensureLocalImage(for: spare.0) {
                    usedIDs.insert(spare.0.id)
                    resolved.append((spare.0, url))
                    break
                }
            }
        }

        guard !resolved.isEmpty else { throw LibraryError.imageUnavailable("rotation") }
        return resolved
    }

    private func refreshCollectionsAsync() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            let summaries = (try? self.library.availableCollections()) ?? []
            DispatchQueue.main.async {
                guard !summaries.isEmpty else { return }
                self.collectionSummaries = summaries
                self.reconcileEnabledCollections(available: Set(summaries.map { $0.id }))
                self.rebuildMenu(message: self.statusMessage)
                self.updateSettingsWindow()
            }
        }
    }

    private func reconcileEnabledCollections(available: Set<String>) {
        let previousIDs = enabledCollectionIDs
        if enabledCollectionIDs.isEmpty {
            enabledCollectionIDs = available
        } else {
            enabledCollectionIDs.formIntersection(available)
            if enabledCollectionIDs.isEmpty, let firstCollection = collectionSummaries.first {
                enabledCollectionIDs.insert(firstCollection.id)
            }
        }
        if enabledCollectionIDs != previousIDs {
            saveEnabledCollectionIDs()
        }
    }

    private func showSettingsWindow() {
        updateSettingsWindow()
        settingsWindowController.showWindow(nil)
        NSApp.activate(ignoringOtherApps: true)
        refreshCollectionsAsync()
    }

    private func updateSettingsWindow() {
        settingsWindowController.update(snapshot: settingsSnapshot())
    }

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
            artworkKinds: ArtworkKind.allCases.map { kind in
                let isEnabled = enabledArtworkKinds.contains(kind)
                return SettingsArtworkKindOption(
                    id: kind.rawValue,
                    title: kind.displayName,
                    isEnabled: isEnabled,
                    isToggleEnabled: !isEnabled || enabledArtworkKinds.count > 1
                )
            },
            currentArtworkTitle: currentSelections.first?.artwork.title,
            currentArtworkCreator: currentSelections.first?.artwork.creator,
            statusMessage: statusMessage,
            libraryPath: library.root.path,
            downloadedCollectionCount: collectionSummaries.count
        )
    }

    private func loadPreferences() {
        enabledCollectionIDs = preferences.enabledCollectionIDs
        enabledArtworkKinds = preferences.enabledArtworkKinds
        rotationIntervalSeconds = preferences.rotationIntervalSeconds
    }

    private func saveEnabledCollectionIDs() {
        preferences.enabledCollectionIDs = enabledCollectionIDs
    }

    private func saveEnabledArtworkKinds() {
        preferences.enabledArtworkKinds = enabledArtworkKinds
    }

    private func saveRotationInterval() {
        preferences.rotationIntervalSeconds = rotationIntervalSeconds
    }

    private func rescheduleTimer() {
        timer?.invalidate()
        guard let rotationIntervalSeconds else {
            timer = nil
            return
        }
        timer = Timer.scheduledTimer(withTimeInterval: rotationIntervalSeconds, repeats: true) { [weak self] _ in
            self?.rotateWallpaper()
        }
    }

    func settingsWindowController(_ controller: SettingsWindowController, didChangeMenuBarIconVisibility isVisible: Bool) {
        preferences.showMenuBarIcon = isVisible
        updateStatusItemVisibility()
        updateSettingsWindow()
    }

    func settingsWindowController(_ controller: SettingsWindowController, didChangeDockIconVisibility isVisible: Bool) {
        preferences.showDockIcon = isVisible
        updateSettingsWindow()
    }

    func settingsWindowController(_ controller: SettingsWindowController, didChangeRotationInterval seconds: TimeInterval?) {
        rotationIntervalSeconds = seconds
        saveRotationInterval()
        rescheduleTimer()
        rebuildMenu(message: "Ready")
        updateSettingsWindow()
    }

    func settingsWindowController(_ controller: SettingsWindowController, didSetCollection collectionID: String, isEnabled: Bool) {
        if isEnabled {
            enabledCollectionIDs.insert(collectionID)
        } else {
            guard enabledCollectionIDs.count > 1 else {
                updateSettingsWindow()
                return
            }
            enabledCollectionIDs.remove(collectionID)
        }
        saveEnabledCollectionIDs()
        rebuildMenu(message: "Ready")
        updateSettingsWindow()
    }

    func settingsWindowController(_ controller: SettingsWindowController, didSetArtworkKind kind: ArtworkKind, isEnabled: Bool) {
        if isEnabled {
            enabledArtworkKinds.insert(kind)
        } else {
            guard enabledArtworkKinds.count > 1 else {
                updateSettingsWindow()
                return
            }
            enabledArtworkKinds.remove(kind)
        }
        saveEnabledArtworkKinds()
        rebuildMenu(message: "Ready")
        updateSettingsWindow()
    }

    func settingsWindowControllerDidRequestNextWallpaper(_ controller: SettingsWindowController) {
        rotateWallpaper()
    }

    func settingsWindowControllerDidRequestOpenLibraryFolder(_ controller: SettingsWindowController) {
        openLibraryFolder()
    }

    func settingsWindowControllerDidRequestQuit(_ controller: SettingsWindowController) {
        quit()
    }

    @objc private func openLibraryFolder() { NSWorkspace.shared.open(library.root) }

    @objc private func quit() {
        timer?.invalidate()
        NSApp.terminate(nil)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
