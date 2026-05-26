import AppKit
import Foundation
import OpenArtPaperCore

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var currentArtwork: Artwork?
    private let picker = RandomArtworkPicker()
    private let wallpaperService = WallpaperService()
    private var timer: Timer?

    private lazy var library: LocalLibrary = {
        let environmentPath = ProcessInfo.processInfo.environment["OPENARTPAPER_LIBRARY_DIR"]
        let root: URL
        if let environmentPath, !environmentPath.isEmpty {
            root = URL(fileURLWithPath: environmentPath).standardizedFileURL
        } else {
            root = FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Pictures")
                .appendingPathComponent("OpenArtPaperLibrary")
        }
        return LocalLibrary(root: root)
    }()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "Art"
        rebuildMenu(message: "Ready")
        rotateWallpaper()
        timer = Timer.scheduledTimer(withTimeInterval: 30 * 60, repeats: true) { [weak self] _ in
            self?.rotateWallpaper()
        }
    }

    private func rebuildMenu(message: String) {
        let menu = NSMenu()
        let title = currentArtwork.map { "\($0.title) — \($0.creator)" } ?? message
        let currentItem = NSMenuItem(title: title, action: nil, keyEquivalent: "")
        currentItem.isEnabled = false
        menu.addItem(currentItem)
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Next Wallpaper", action: #selector(nextWallpaper), keyEquivalent: "n"))
        menu.addItem(NSMenuItem(title: "Open Library Folder", action: #selector(openLibraryFolder), keyEquivalent: "o"))
        menu.addItem(.separator())
        menu.addItem(NSMenuItem(title: "Quit OpenArtPaper", action: #selector(quit), keyEquivalent: "q"))
        statusItem.menu = menu
    }

    @objc private func nextWallpaper() { rotateWallpaper() }

    private func rotateWallpaper() {
        do {
            let artworks = try library.loadAllDownloadedArtworks()
            let selected = try picker.pick(from: artworks)
            try wallpaperService.setWallpaperOnAllScreens(imageURL: selected.1)
            currentArtwork = selected.0
            rebuildMenu(message: "Ready")
        } catch {
            rebuildMenu(message: "OpenArtPaper error: \(error.localizedDescription)")
        }
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
