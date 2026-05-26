import XCTest
@testable import OpenArtPaperCore

final class LocalLibraryTests: XCTestCase {
    func testDecodesCatalogAndCollectionManifest() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("OpenArtPaperCoreTests")
            .appendingPathComponent(UUID().uuidString)
        let collectionsDirectory = root.appendingPathComponent("collections", isDirectory: true)
        try FileManager.default.createDirectory(at: collectionsDirectory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let catalogJSON = """
        {
          "collections": [
            {
              "id": "essentials-5k",
              "title": "Essentials 5K",
              "shortName": "Essentials",
              "sourcePackId": "artpaper-essentials",
              "artworkCount": 1,
              "expectedArtworkCount": 5000,
              "manifest": "collections/essentials.json"
            }
          ]
        }
        """

        let collectionJSON = """
        {
          "id": "essentials-5k",
          "title": "Essentials 5K",
          "shortName": "Essentials",
          "sourcePackId": "artpaper-essentials",
          "artworks": [
            {
              "id": "met-dp-1",
              "title": "A Sunday on La Grande Jatte",
              "creator": "Georges Seurat",
              "attribution": "Georges Seurat, public domain",
              "sources": {
                "primary": "met",
                "metObjectId": "123",
                "extraSourceMetadata": "ignored"
              },
              "rights": {
                "license": "Public Domain",
                "creditLine": "The Metropolitan Museum of Art",
                "isPublicDomain": true
              },
              "images": {
                "wallpaper": {
                  "localPath": "images/met-dp-1.jpg",
                  "width": 5120,
                  "height": 2880,
                  "bytes": 123456,
                  "sha256": "abc123",
                  "downloadedFrom": "https://example.com/image.jpg",
                  "importedFromArtPaperPack": true
                },
                "fallbackUrls": ["https://example.com/fallback.jpg"]
              }
            }
          ]
        }
        """

        try catalogJSON.data(using: .utf8)!.write(to: root.appendingPathComponent("catalog.json"))
        try collectionJSON.data(using: .utf8)!.write(to: collectionsDirectory.appendingPathComponent("essentials.json"))

        let library = LocalLibrary(root: root)
        let catalog = try library.loadCatalog()
        XCTAssertEqual(catalog.collections.count, 1)

        let summary = try XCTUnwrap(catalog.collections.first)
        XCTAssertEqual(summary.id, "essentials-5k")
        XCTAssertEqual(summary.title, "Essentials 5K")
        XCTAssertEqual(summary.shortName, "Essentials")
        XCTAssertEqual(summary.sourcePackId, "artpaper-essentials")
        XCTAssertEqual(summary.artworkCount, 1)
        XCTAssertEqual(summary.expectedArtworkCount, 5000)
        XCTAssertEqual(summary.manifest, "collections/essentials.json")

        let manifest = try library.loadCollection(summary)
        XCTAssertEqual(manifest.id, "essentials-5k")
        XCTAssertEqual(manifest.artworks.count, 1)

        let artwork = try XCTUnwrap(manifest.artworks.first)
        XCTAssertEqual(artwork.id, "met-dp-1")
        XCTAssertEqual(artwork.title, "A Sunday on La Grande Jatte")
        XCTAssertEqual(artwork.creator, "Georges Seurat")
        XCTAssertEqual(artwork.attribution, "Georges Seurat, public domain")
        XCTAssertEqual(artwork.sources.primary, "met")
        XCTAssertEqual(artwork.sources.metObjectId, "123")
        XCTAssertEqual(artwork.rights.license, "Public Domain")
        XCTAssertEqual(artwork.rights.creditLine, "The Metropolitan Museum of Art")
        XCTAssertEqual(artwork.rights.isPublicDomain, true)
        XCTAssertEqual(artwork.images.wallpaper.localPath, "images/met-dp-1.jpg")
        XCTAssertEqual(artwork.images.wallpaper.width, 5120)
        XCTAssertEqual(artwork.images.wallpaper.height, 2880)
        XCTAssertEqual(artwork.images.wallpaper.bytes, 123456)
        XCTAssertEqual(artwork.images.wallpaper.sha256, "abc123")
        XCTAssertEqual(artwork.images.wallpaper.downloadedFrom, "https://example.com/image.jpg")
        XCTAssertEqual(artwork.images.wallpaper.importedFromArtPaperPack, true)
        XCTAssertEqual(artwork.images.fallbackUrls, ["https://example.com/fallback.jpg"])
        XCTAssertEqual(library.wallpaperURL(for: artwork), root.appendingPathComponent("images/met-dp-1.jpg"))
    }
}
