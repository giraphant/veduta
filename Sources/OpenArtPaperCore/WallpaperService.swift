import AppKit
import Foundation

public final class WallpaperService {
    public init() {}

    public func setWallpaperOnAllScreens(imageURL: URL) throws {
        try setWallpapers(imageURLs: [imageURL])
    }

    public func setWallpapers(imageURLs: [URL]) throws {
        guard !imageURLs.isEmpty else { return }
        let workspace = NSWorkspace.shared
        for (index, screen) in NSScreen.screens.enumerated() {
            try workspace.setDesktopImageURL(imageURLs[index % imageURLs.count], for: screen, options: [:])
        }
    }
}
