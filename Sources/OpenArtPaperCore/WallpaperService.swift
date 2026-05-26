import AppKit
import Foundation

public final class WallpaperService {
    public init() {}

    public func setWallpaperOnAllScreens(imageURL: URL) throws {
        let workspace = NSWorkspace.shared
        for screen in NSScreen.screens {
            try workspace.setDesktopImageURL(imageURL, for: screen, options: [:])
        }
    }
}
