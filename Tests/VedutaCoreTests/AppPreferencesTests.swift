import XCTest
@testable import VedutaCore

final class AppPreferencesTests: XCTestCase {
    private var defaults: UserDefaults!
    private var suiteName: String!

    override func setUp() {
        super.setUp()
        suiteName = "VedutaTests.\(UUID().uuidString)"
        defaults = UserDefaults(suiteName: suiteName)
        defaults.removePersistentDomain(forName: suiteName)
    }

    override func tearDown() {
        defaults.removePersistentDomain(forName: suiteName)
        defaults = nil
        suiteName = nil
        super.tearDown()
    }

    func testDefaultsKeepExistingMenuBarBehaviorAndAccessoryDockBehavior() {
        let preferences = AppPreferences(defaults: defaults)

        XCTAssertTrue(preferences.showMenuBarIcon)
        XCTAssertFalse(preferences.showDockIcon)
        XCTAssertEqual(preferences.rotationIntervalSeconds, 30 * 60)
        XCTAssertTrue(preferences.enabledCollectionIDs.isEmpty)
        XCTAssertEqual(preferences.enabledArtworkKinds, Set(ArtworkKind.allCases))
    }

    func testPersistsVisibilityAndWallpaperPreferences() {
        var preferences = AppPreferences(defaults: defaults)
        preferences.showMenuBarIcon = false
        preferences.showDockIcon = true
        preferences.rotationIntervalSeconds = nil
        preferences.enabledCollectionIDs = ["rijksmuseum", "essentials"]
        preferences.enabledArtworkKinds = [.flatArt, .streetArt]

        preferences = AppPreferences(defaults: defaults)
        XCTAssertFalse(preferences.showMenuBarIcon)
        XCTAssertTrue(preferences.showDockIcon)
        XCTAssertNil(preferences.rotationIntervalSeconds)
        XCTAssertEqual(preferences.enabledCollectionIDs, ["essentials", "rijksmuseum"])
        XCTAssertEqual(preferences.enabledArtworkKinds, [.flatArt, .streetArt])
    }
}
