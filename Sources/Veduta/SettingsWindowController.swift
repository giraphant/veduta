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
    /// Longer descriptive line (currently the catalog's full title; a curated
    /// blurb can replace it once the pipeline ships one).
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

protocol SettingsWindowControllerDelegate: AnyObject {
    func settingsWindowController(_ controller: SettingsWindowController, didChangeMenuBarIconVisibility isVisible: Bool)
    func settingsWindowController(_ controller: SettingsWindowController, didChangeDockIconVisibility isVisible: Bool)
    func settingsWindowController(_ controller: SettingsWindowController, didChangeRotationInterval seconds: TimeInterval?)
    func settingsWindowController(_ controller: SettingsWindowController, didSetCollection collectionID: String, isEnabled: Bool)
    func settingsWindowController(_ controller: SettingsWindowController, didRequestDownloadCollection collectionID: String)
    func settingsWindowController(_ controller: SettingsWindowController, didRequestCancelDownloadCollection collectionID: String)
    func settingsWindowController(_ controller: SettingsWindowController, didSetArtworkKind kind: ArtworkKind, isEnabled: Bool)
    func settingsWindowControllerDidRequestNextWallpaper(_ controller: SettingsWindowController)
    func settingsWindowControllerDidRequestOpenLibraryFolder(_ controller: SettingsWindowController)
    func settingsWindowControllerDidRequestQuit(_ controller: SettingsWindowController)
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
    weak var delegate: SettingsWindowControllerDelegate?

    private var snapshot = SettingsSnapshot.empty
    private var selectedPane = SettingsPane.wallpaper
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
        SettingsView(
            selectedPane: selectedPane,
            snapshot: snapshot,
            onPaneChanged: { [weak self] pane in
                self?.selectedPane = pane
            },
            onMenuBarChanged: { [weak self] isVisible in
                guard let self else { return }
                self.delegate?.settingsWindowController(self, didChangeMenuBarIconVisibility: isVisible)
            },
            onDockChanged: { [weak self] isVisible in
                guard let self else { return }
                self.delegate?.settingsWindowController(self, didChangeDockIconVisibility: isVisible)
            },
            onRotationChanged: { [weak self] seconds in
                guard let self else { return }
                self.delegate?.settingsWindowController(self, didChangeRotationInterval: seconds)
            },
            onCollectionChanged: { [weak self] collectionID, isEnabled in
                guard let self else { return }
                self.delegate?.settingsWindowController(self, didSetCollection: collectionID, isEnabled: isEnabled)
            },
            onDownloadCollection: { [weak self] collectionID in
                guard let self else { return }
                self.delegate?.settingsWindowController(self, didRequestDownloadCollection: collectionID)
            },
            onCancelDownloadCollection: { [weak self] collectionID in
                guard let self else { return }
                self.delegate?.settingsWindowController(self, didRequestCancelDownloadCollection: collectionID)
            },
            onArtworkKindChanged: { [weak self] kind, isEnabled in
                guard let self else { return }
                self.delegate?.settingsWindowController(self, didSetArtworkKind: kind, isEnabled: isEnabled)
            },
            onNextWallpaper: { [weak self] in
                guard let self else { return }
                self.delegate?.settingsWindowControllerDidRequestNextWallpaper(self)
            },
            onOpenLibraryFolder: { [weak self] in
                guard let self else { return }
                self.delegate?.settingsWindowControllerDidRequestOpenLibraryFolder(self)
            },
            onQuit: { [weak self] in
                guard let self else { return }
                self.delegate?.settingsWindowControllerDidRequestQuit(self)
            }
        )
    }
}

private struct SettingsView: View {
    let snapshot: SettingsSnapshot
    let onPaneChanged: (SettingsPane) -> Void
    let onMenuBarChanged: (Bool) -> Void
    let onDockChanged: (Bool) -> Void
    let onRotationChanged: (TimeInterval?) -> Void
    let onCollectionChanged: (String, Bool) -> Void
    let onDownloadCollection: (String) -> Void
    let onCancelDownloadCollection: (String) -> Void
    let onArtworkKindChanged: (ArtworkKind, Bool) -> Void
    let onNextWallpaper: () -> Void
    let onOpenLibraryFolder: () -> Void
    let onQuit: () -> Void

    @State private var selectedPane: SettingsPane?

    init(
        selectedPane: SettingsPane,
        snapshot: SettingsSnapshot,
        onPaneChanged: @escaping (SettingsPane) -> Void,
        onMenuBarChanged: @escaping (Bool) -> Void,
        onDockChanged: @escaping (Bool) -> Void,
        onRotationChanged: @escaping (TimeInterval?) -> Void,
        onCollectionChanged: @escaping (String, Bool) -> Void,
        onDownloadCollection: @escaping (String) -> Void,
        onCancelDownloadCollection: @escaping (String) -> Void,
        onArtworkKindChanged: @escaping (ArtworkKind, Bool) -> Void,
        onNextWallpaper: @escaping () -> Void,
        onOpenLibraryFolder: @escaping () -> Void,
        onQuit: @escaping () -> Void
    ) {
        self.snapshot = snapshot
        self.onPaneChanged = onPaneChanged
        self.onMenuBarChanged = onMenuBarChanged
        self.onDockChanged = onDockChanged
        self.onRotationChanged = onRotationChanged
        self.onCollectionChanged = onCollectionChanged
        self.onDownloadCollection = onDownloadCollection
        self.onCancelDownloadCollection = onCancelDownloadCollection
        self.onArtworkKindChanged = onArtworkKindChanged
        self.onNextWallpaper = onNextWallpaper
        self.onOpenLibraryFolder = onOpenLibraryFolder
        self.onQuit = onQuit
        _selectedPane = State(initialValue: selectedPane)
    }

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
        .onChange(of: selectedPane) { pane in
            if let pane {
                onPaneChanged(pane)
            }
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
            set: { value in onCollectionChanged(collection.id, value) }
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
                onDownloadCollection(collection.id)
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
                    onCancelDownloadCollection(collection.id)
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
                            onArtworkKindChanged(artworkKind, value)
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
                Button("Open Library Folder", action: onOpenLibraryFolder)
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
                Button("Open Library Folder", action: onOpenLibraryFolder)
                Button("Quit Veduta", action: onQuit)
            }
        }
        .formStyle(.grouped)
    }
}
