import AppKit
import Foundation
import SwiftUI
import VedutaCore

struct SettingsRotationOption: Identifiable, Equatable {
    let id: String
    let title: String
    let seconds: TimeInterval?

    init(title: String, seconds: TimeInterval?) {
        self.id = seconds.map { String(Int($0)) } ?? "manual"
        self.title = title
        self.seconds = seconds
    }
}

enum SettingsCollectionDownloadState: Equatable {
    /// Every image is on disk (pipeline-built or fully downloaded).
    case fullyDownloaded
    /// `remaining` images are streamable from the mirror but not local yet.
    case downloadable(remaining: Int)
    /// A "Download all" task is running.
    case downloading(completed: Int, total: Int)
}

struct SettingsCollectionOption: Identifiable, Equatable {
    let id: String
    let title: String
    /// Longer descriptive line (the catalog's full title).
    let subtitle: String
    let artworkCount: Int
    let coverURL: URL?
    let isEnabled: Bool
    let isToggleEnabled: Bool
    let downloadState: SettingsCollectionDownloadState
}

struct SettingsArtworkKindOption: Identifiable, Equatable {
    let id: String
    let title: String
    let isEnabled: Bool
    let isToggleEnabled: Bool
}

struct SettingsSnapshot: Equatable {
    let showMenuBarIcon: Bool
    let showDockIcon: Bool
    let launchAtLogin: Bool
    let launchAtLoginSupported: Bool
    let automaticCacheCleanupEnabled: Bool
    let wallpaperCacheSizeBytes: Int64
    let rotationIntervalSeconds: TimeInterval?
    let rotationOptions: [SettingsRotationOption]
    let collections: [SettingsCollectionOption]
    let artworkKinds: [SettingsArtworkKindOption]
    let currentArtworkTitle: String?
    let currentArtworkCreator: String?
    let statusMessage: String
    let libraryPath: String
    let downloadedCollectionCount: Int
    let mirrorCollectionCount: Int

    static let empty = SettingsSnapshot(
        showMenuBarIcon: true,
        showDockIcon: false,
        launchAtLogin: false,
        launchAtLoginSupported: true,
        automaticCacheCleanupEnabled: false,
        wallpaperCacheSizeBytes: 0,
        rotationIntervalSeconds: 30 * 60,
        rotationOptions: [],
        collections: [],
        artworkKinds: [],
        currentArtworkTitle: nil,
        currentArtworkCreator: nil,
        statusMessage: "Ready",
        libraryPath: "",
        downloadedCollectionCount: 0,
        mirrorCollectionCount: 0
    )
}

/// The app-side handlers behind the Settings UI, wired up once by AppDelegate.
/// Default no-ops let the controller exist before wiring.
struct SettingsActions {
    var setMenuBarIconVisible: (Bool) -> Void = { _ in }
    var setDockIconVisible: (Bool) -> Void = { _ in }
    var setLaunchAtLogin: (Bool) -> Void = { _ in }
    var setAutomaticCacheCleanup: (Bool) -> Void = { _ in }
    var cleanWallpaperCache: () -> Void = {}
    var setRotationInterval: (TimeInterval?) -> Void = { _ in }
    var setCollectionEnabled: (String, Bool) -> Void = { _, _ in }
    var downloadCollection: (String) -> Void = { _ in }
    var cancelCollectionDownload: (String) -> Void = { _ in }
    var setArtworkKindEnabled: (ArtworkKind, Bool) -> Void = { _, _ in }
    var nextWallpaper: () -> Void = {}
    var openLibraryFolder: () -> Void = {}
    var quit: () -> Void = {}
}

private enum SettingsPane: String, CaseIterable, Identifiable, Hashable {
    case wallpaper
    case settings
    case collections
    case artworkTypes
    case library
    case about

    var id: Self { self }

    var title: String {
        switch self {
        case .wallpaper: "Wallpaper"
        case .settings: "Settings"
        case .collections: "Collections"
        case .artworkTypes: "Artwork Types"
        case .library: "Library"
        case .about: "About"
        }
    }

    var symbolName: String {
        switch self {
        case .wallpaper: "photo.on.rectangle"
        case .settings: "gearshape"
        case .collections: "square.grid.2x2"
        case .artworkTypes: "paintpalette"
        case .library: "folder"
        case .about: "info.circle"
        }
    }
}

final class SettingsWindowController: NSWindowController {
    var actions = SettingsActions()

    private var snapshot = SettingsSnapshot.empty
    private lazy var hostingController = NSHostingController(rootView: makeView())

    init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 980, height: 680),
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
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

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    func update(snapshot: SettingsSnapshot) {
        self.snapshot = snapshot
        hostingController.rootView = makeView()
    }

    override func showWindow(_ sender: Any?) {
        super.showWindow(sender)
        window?.makeKeyAndOrderFront(sender)
        window?.orderFrontRegardless()
    }

    private func makeView() -> SettingsView {
        SettingsView(snapshot: snapshot, actions: actions)
    }
}

private struct SettingsView: View {
    let snapshot: SettingsSnapshot
    let actions: SettingsActions

    // Survives rootView replacement on snapshot updates, so the selected pane
    // sticks without round-tripping through the window controller.
    @State private var selectedPane: SettingsPane? = .wallpaper

    var body: some View {
        NavigationSplitView {
            List(SettingsPane.allCases, selection: $selectedPane) { pane in
                Label(pane.title, systemImage: pane.symbolName)
                    .tag(pane)
            }
            .listStyle(.sidebar)
            .navigationSplitViewColumnWidth(min: 170, ideal: 190, max: 230)
        } detail: {
            detailView
                .navigationTitle((selectedPane ?? .wallpaper).title)
        }
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
        case .artworkTypes:
            artworkTypesPane
        case .library:
            libraryPane
        case .about:
            aboutPane
        }
    }

    private var settingsPane: some View {
        Form {
            if snapshot.launchAtLoginSupported {
                Section("Startup") {
                    Toggle("Open Veduta at login", isOn: Binding(
                        get: { snapshot.launchAtLogin },
                        set: { value in actions.setLaunchAtLogin(value) }
                    ))
                }
            }

            Section("App Visibility") {
                Toggle("Show menu bar icon", isOn: Binding(
                    get: { snapshot.showMenuBarIcon },
                    set: { value in actions.setMenuBarIconVisible(value) }
                ))

                Toggle("Show Dock icon on next launch", isOn: Binding(
                    get: { snapshot.showDockIcon },
                    set: { value in actions.setDockIconVisible(value) }
                ))
            }

            Section("Storage") {
                LabeledContent("Wallpaper render cache") {
                    Text(Self.formatBytes(snapshot.wallpaperCacheSizeBytes))
                        .monospacedDigit()
                }

                Toggle("Automatically trim the cache", isOn: Binding(
                    get: { snapshot.automaticCacheCleanupEnabled },
                    set: { value in actions.setAutomaticCacheCleanup(value) }
                ))

                Text("macOS keeps a large, ever-growing cache of decoded wallpapers and never clears it on its own. When this is on, Veduta keeps the most recent renders and removes older ones once the cache passes 5 GB. Deleted files are rebuilt by macOS as needed.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)

                Button("Clean Up Now", action: actions.cleanWallpaperCache)
            }

            Section("Recovery") {
                Text("If both icons are hidden, open Veduta again from Finder or Spotlight to show this window.")
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
    }

    private static func formatBytes(_ bytes: Int64) -> String {
        ByteCountFormatter.string(fromByteCount: bytes, countStyle: .file)
    }

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
                        actions.setRotationInterval(option.seconds)
                    }
                )) {
                    ForEach(snapshot.rotationOptions) { option in
                        Text(option.title).tag(option.id)
                    }
                }
                .pickerStyle(.menu)
            }

            Section("Actions") {
                Button("Next Wallpaper", action: actions.nextWallpaper)
                    .keyboardShortcut("n")
            }
        }
        .formStyle(.grouped)
    }

    private var collectionsPane: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                if snapshot.collections.isEmpty {
                    Text("No collections found yet.")
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.top, 8)
                } else {
                    ForEach(snapshot.collections, content: collectionCard)
                }
            }
            .padding(20)
        }
    }

    /// A wide banner card per collection: cover art on the left, title +
    /// description + a count line in the middle, and the two actions stacked on
    /// the right — activation as a pill (the primary choice) over a quiet
    /// download control.
    private func collectionCard(_ collection: SettingsCollectionOption) -> some View {
        HStack(alignment: .top, spacing: 14) {
            collectionCover(collection)

            VStack(alignment: .leading, spacing: 3) {
                Text(collection.title)
                    .font(.headline)
                Text(collection.subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                Text("\(collection.artworkCount) works")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .padding(.top, 1)
                downloadControl(collection)
                    .padding(.top, 4)
            }

            Spacer(minLength: 12)

            activationToggle(collection)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 0.5)
        )
    }

    private func collectionCover(_ collection: SettingsCollectionOption) -> some View {
        ZStack {
            coverPlaceholder(collection)
            if let url = collection.coverURL, let image = NSImage(contentsOf: url) {
                Image(nsImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fill)
                    .transition(.opacity)
            }
        }
        .frame(width: 128, height: 72)
        .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(Color(nsColor: .separatorColor), lineWidth: 0.5)
        )
    }

    /// Gradient + serif initial shown until the cover image loads (or if none).
    private func coverPlaceholder(_ collection: SettingsCollectionOption) -> some View {
        let hue = Self.stableHue(collection.id)
        return LinearGradient(
            colors: [
                Color(hue: hue, saturation: 0.42, brightness: 0.62),
                Color(hue: (hue + 0.07).truncatingRemainder(dividingBy: 1), saturation: 0.5, brightness: 0.4)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .overlay(
            Text(String(collection.title.prefix(1)).uppercased())
                .font(.system(size: 28, weight: .semibold, design: .serif))
                .foregroundStyle(.white.opacity(0.92))
        )
    }

    /// Activation lives top-right as a single native switch: in rotation or not.
    @ViewBuilder
    private func activationToggle(_ collection: SettingsCollectionOption) -> some View {
        let isLastEnabled = collection.isEnabled && !collection.isToggleEnabled
        Toggle("", isOn: Binding(
            get: { collection.isEnabled },
            set: { value in actions.setCollectionEnabled(collection.id, value) }
        ))
        .toggleStyle(.switch)
        .labelsHidden()
        .disabled(isLastEnabled)
        .help(isLastEnabled
              ? "At least one collection must stay in rotation"
              : (collection.isEnabled ? "In rotation" : "Add to rotation. Images stream on demand."))
    }

    /// A quiet secondary line under the work count: download, progress, or saved.
    @ViewBuilder
    private func downloadControl(_ collection: SettingsCollectionOption) -> some View {
        switch collection.downloadState {
        case .fullyDownloaded:
            Label("Saved offline", systemImage: "checkmark.icloud")
                .font(.caption)
                .foregroundStyle(.secondary)
                .help("Every image in this collection is on disk")
        case let .downloadable(remaining):
            Button {
                actions.downloadCollection(collection.id)
            } label: {
                Label("Download \(remaining)", systemImage: "arrow.down.circle")
                    .font(.caption)
            }
            .buttonStyle(.borderless)
            .foregroundStyle(.secondary)
            .help("Download all \(remaining) images for offline use")
        case let .downloading(completed, total):
            HStack(spacing: 6) {
                ProgressView(value: Double(completed), total: Double(max(total, 1)))
                    .frame(width: 90)
                Text("\(completed)/\(total)")
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.secondary)
                Button {
                    actions.cancelCollectionDownload(collection.id)
                } label: {
                    Image(systemName: "stop.circle")
                }
                .buttonStyle(.borderless)
                .foregroundStyle(.secondary)
                .help("Stop downloading")
            }
        }
    }

    /// Deterministic 0..<1 hue from the collection id (String.hashValue is
    /// randomized per launch, so roll a stable FNV-1a instead).
    private static func stableHue(_ string: String) -> Double {
        var hash: UInt64 = 0xcbf29ce484222325
        for byte in string.utf8 {
            hash = (hash ^ UInt64(byte)) &* 0x100000001b3
        }
        return Double(hash % 360) / 360.0
    }

    private var artworkTypesPane: some View {
        Form {
            Section("Artwork Types") {
                ForEach(snapshot.artworkKinds) { kind in
                    Toggle(kind.title, isOn: Binding(
                        get: { kind.isEnabled },
                        set: { value in
                            guard let artworkKind = ArtworkKind(rawValue: kind.id) else { return }
                            actions.setArtworkKindEnabled(artworkKind, value)
                        }
                    ))
                    .disabled(!kind.isToggleEnabled)

                    if !kind.isToggleEnabled {
                        Text("At least one artwork type must stay enabled.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .formStyle(.grouped)
    }

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

                LabeledContent("Available from Mirror") {
                    Text("\(snapshot.mirrorCollectionCount)")
                }
            }

            Section("Actions") {
                Button("Open Library Folder", action: actions.openLibraryFolder)
            }
        }
        .formStyle(.grouped)
    }

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
                Button("Open Library Folder", action: actions.openLibraryFolder)
                Button("Quit Veduta", action: actions.quit)
            }
        }
        .formStyle(.grouped)
    }
}
