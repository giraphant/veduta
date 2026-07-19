import XCTest
@testable import VedutaCore

final class WallpaperCacheJanitorTests: XCTestCase {
    private var cacheDir: URL!

    override func setUpWithError() throws {
        try super.setUpWithError()
        // The janitor only operates on a path that looks like the wallpaper
        // agent's cache, so the temp fixture must mirror that shape.
        cacheDir = FileManager.default.temporaryDirectory
            .appendingPathComponent("VedutaTests.\(UUID().uuidString)")
            .appendingPathComponent("com.apple.wallpaper.agent/Data/Library/Caches/com.apple.wallpaper.caches")
        try FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws {
        if let cacheDir { try? FileManager.default.removeItem(at: cacheDir) }
        cacheDir = nil
        try super.tearDownWithError()
    }

    private func writeRender(_ name: String, bytes: Int, ageDays: Int) throws -> URL {
        let url = cacheDir.appendingPathComponent(name)
        try Data(count: bytes).write(to: url)
        let modified = Date(timeIntervalSinceNow: TimeInterval(-ageDays * 86_400))
        try FileManager.default.setAttributes([.modificationDate: modified], ofItemAtPath: url.path)
        return url
    }

    func testCurrentSizeSumsOnlyBMPFiles() throws {
        _ = try writeRender("a-2560-1600-0-x.bmp", bytes: 1000, ageDays: 1)
        _ = try writeRender("b-3000-2400-0-y.bmp", bytes: 2000, ageDays: 1)
        // A non-render file in the same dir must be ignored entirely.
        try Data(count: 9999).write(to: cacheDir.appendingPathComponent(".DS_Store"))

        let janitor = WallpaperCacheJanitor(cacheDirectory: cacheDir)
        XCTAssertEqual(janitor.currentSizeBytes(), 3000)
    }

    func testPruneRemovesOldestUntilUnderCap() throws {
        let oldest = try writeRender("old-2560-1600-0-a.bmp", bytes: 1000, ageDays: 10)
        let middle = try writeRender("mid-2560-1600-0-b.bmp", bytes: 1000, ageDays: 5)
        let newest = try writeRender("new-2560-1600-0-c.bmp", bytes: 1000, ageDays: 1)

        let janitor = WallpaperCacheJanitor(cacheDirectory: cacheDir)
        XCTAssertEqual(janitor.currentSizeBytes(), 3000)
        janitor.prune(toMaxBytes: 1500)

        XCTAssertEqual(janitor.currentSizeBytes(), 1000)
        // The two oldest go; the newest render is preserved.
        XCTAssertFalse(FileManager.default.fileExists(atPath: oldest.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: middle.path))
        XCTAssertTrue(FileManager.default.fileExists(atPath: newest.path))
    }

    func testPruneIsNoOpWhenUnderCap() throws {
        let render = try writeRender("a-2560-1600-0-a.bmp", bytes: 1000, ageDays: 1)
        let janitor = WallpaperCacheJanitor(cacheDirectory: cacheDir)

        janitor.prune(toMaxBytes: 5000)
        XCTAssertTrue(FileManager.default.fileExists(atPath: render.path))
        XCTAssertEqual(janitor.currentSizeBytes(), 1000)
    }

    func testRefusesPathsOutsideTheWallpaperCache() throws {
        let stray = FileManager.default.temporaryDirectory
            .appendingPathComponent("VedutaStray.\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: stray, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: stray) }
        let victim = stray.appendingPathComponent("important-2560-1600-0.bmp")
        try Data(count: 4000).write(to: victim)

        let janitor = WallpaperCacheJanitor(cacheDirectory: stray)
        janitor.prune(toMaxBytes: 0)

        XCTAssertEqual(janitor.currentSizeBytes(), 0, "Unsafe paths report no renders")
        XCTAssertTrue(FileManager.default.fileExists(atPath: victim.path), "Files outside the cache are never touched")
    }
}
