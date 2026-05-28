import AppKit
import Foundation
import SwiftUI

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

struct SettingsCollectionOption: Identifiable, Equatable {
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

protocol SettingsWindowControllerDelegate: AnyObject {
    func settingsWindowController(_ controller: SettingsWindowController, didChangeMenuBarIconVisibility isVisible: Bool)
    func settingsWindowController(_ controller: SettingsWindowController, didChangeDockIconVisibility isVisible: Bool)
    func settingsWindowController(_ controller: SettingsWindowController, didChangeRotationInterval seconds: TimeInterval?)
    func settingsWindowController(_ controller: SettingsWindowController, didSetCollection collectionID: String, isEnabled: Bool)
    func settingsWindowControllerDidRequestNextWallpaper(_ controller: SettingsWindowController)
    func settingsWindowControllerDidRequestOpenLibraryFolder(_ controller: SettingsWindowController)
    func settingsWindowControllerDidRequestQuit(_ controller: SettingsWindowController)
}

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
        window.title = "OpenArtPaper"
        window.isReleasedWhenClosed = false
        window.minSize = NSSize(width: 820, height: 540)
        super.init(window: window)
        window.contentViewController = hostingController
        window.titlebarAppearsTransparent = true
        window.toolbarStyle = .unified
        window.setFrameAutosaveName("OpenArtPaperMainWindow")
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
                Text("If both icons are hidden, open OpenArtPaper again from Finder or Spotlight to show this window.")
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

    private var aboutPane: some View {
        Form {
            Section("OpenArtPaper") {
                LabeledContent("App") {
                    Text("OpenArtPaper")
                }

                Text("A local-first open-source wallpaper rotator for macOS.")
                    .foregroundStyle(.secondary)
            }

            Section("Actions") {
                Button("Open Library Folder", action: onOpenLibraryFolder)
                Button("Quit OpenArtPaper", action: onQuit)
            }
        }
        .formStyle(.grouped)
    }
}
