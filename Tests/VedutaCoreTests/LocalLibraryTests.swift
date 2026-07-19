import XCTest
@testable import VedutaCore

final class LocalLibraryTests: XCTestCase {
    func testDecodesCatalogAndCollectionManifest() throws {
        let root = try makeTemporaryLibraryRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        try writeCatalog(to: root, artworkCount: 1)
        try writeCollection(
            to: root,
            artworks: [
                artworkJSON(
                    id: "met-dp-1",
                    localPath: "images/met-dp-1.jpg",
                    importedFromArtPaperPack: "/Library/Application Support/ArtPaper/Packs/essentials"
                )
            ]
        )

        let library = LocalLibrary(root: root)
        let catalog = try library.loadCatalog()
        XCTAssertEqual(catalog.collections.count, 1)

        let summary = try XCTUnwrap(catalog.collections.first)
        XCTAssertEqual(summary.id, "essentials-5k")
        XCTAssertEqual(summary.title, "Essentials 5K")
        XCTAssertEqual(summary.shortName, "Essentials")
        XCTAssertEqual(summary.artworkCount, 1)
        XCTAssertEqual(summary.manifest, "collections/essentials.json")

        let manifest = try library.loadCollection(summary)
        XCTAssertEqual(manifest.artworks.count, 1)

        let artwork = try XCTUnwrap(manifest.artworks.first)
        XCTAssertEqual(artwork.id, "met-dp-1")
        XCTAssertEqual(artwork.title, "A Sunday on La Grande Jatte")
        XCTAssertEqual(artwork.creator, "Georges Seurat")
        XCTAssertEqual(artwork.sources.canonicalPage, "https://example.com/artworks/met-dp-1")
        XCTAssertEqual(artwork.images.wallpaper.localPath, "images/met-dp-1.jpg")
        XCTAssertEqual(artwork.images.wallpaper.fallbackUrls, ["https://example.com/fallback.jpg"])
        XCTAssertEqual(artwork.images.wallpaper.width, 5120)
        XCTAssertEqual(artwork.images.wallpaper.height, 2880)
        XCTAssertEqual(artwork.images.wallpaper.bytes, 123456)
        XCTAssertEqual(artwork.images.wallpaper.sha256, "abc123")
        XCTAssertEqual(artwork.classification?.kind, .flatArt)
        XCTAssertEqual(library.wallpaperURL(for: artwork), root.appendingPathComponent("images/met-dp-1.jpg"))
    }

    func testLoadDownloadedArtworksReturnsOnlyExistingLocalFiles() throws {
        let root = try makeTemporaryLibraryRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        try writeCatalog(to: root, artworkCount: 2)
        try writeCollection(
            to: root,
            artworks: [
                artworkJSON(id: "existing-artwork", localPath: "images/existing.jpg"),
                artworkJSON(id: "missing-artwork", localPath: "images/missing.jpg")
            ]
        )

        let existingFile = root.appendingPathComponent("images/existing.jpg")
        try FileManager.default.createDirectory(
            at: existingFile.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("image".utf8).write(to: existingFile)

        let downloaded = try LocalLibrary(root: root).loadDownloadedArtworks()

        XCTAssertEqual(downloaded.count, 1)
        XCTAssertEqual(downloaded.first?.0.id, "existing-artwork")
        XCTAssertEqual(downloaded.first?.1, existingFile)
    }

    func testLoadDownloadedArtworksFiltersByArtworkKinds() throws {
        let root = try makeTemporaryLibraryRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        try writeCatalog(to: root, artworkCount: 3)
        try writeCollection(
            to: root,
            artworks: [
                artworkJSON(id: "flat-artwork", localPath: "images/flat.jpg", kind: .flatArt),
                artworkJSON(id: "photo-artwork", localPath: "images/photo.jpg", kind: .photography),
                artworkJSON(id: "other-artwork", localPath: "images/other.jpg")
            ]
        )

        for path in ["images/flat.jpg", "images/photo.jpg", "images/other.jpg"] {
            let file = root.appendingPathComponent(path)
            try FileManager.default.createDirectory(
                at: file.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            try Data("image".utf8).write(to: file)
        }

        let library = LocalLibrary(root: root)
        let flatOnly = try library.loadDownloadedArtworks(enabledArtworkKinds: [.flatArt])
        let photographyOnly = try library.loadDownloadedArtworks(enabledArtworkKinds: [.photography])
        let defaultKinds = try library.loadDownloadedArtworks()

        XCTAssertEqual(flatOnly.map { $0.0.id }, ["flat-artwork", "other-artwork"])
        XCTAssertEqual(photographyOnly.map { $0.0.id }, ["photo-artwork"])
        XCTAssertEqual(defaultKinds.map { $0.0.id }, ["flat-artwork", "photo-artwork", "other-artwork"])
    }

    func testLoadDownloadedArtworksFiltersByCollectionIDs() throws {
        let root = try makeTemporaryLibraryRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        let catalogJSON = """
        {
          "schemaVersion": 1,
          "generatedAt": "2026-05-26T12:00:00Z",
          "collections": [
            {
              "id": "essentials-5k",
              "title": "Essentials 5K",
              "shortName": "Essentials",
              "sourcePackId": 0,
              "artworkCount": 1,
              "expectedArtworkCount": 5000,
              "manifest": "collections/essentials.json"
            },
            {
              "id": "other-collection",
              "title": "Other Collection",
              "shortName": "Other",
              "sourcePackId": 1,
              "artworkCount": 1,
              "expectedArtworkCount": 1,
              "manifest": "collections/other.json"
            }
          ]
        }
        """
        try catalogJSON.data(using: .utf8)!.write(to: root.appendingPathComponent("catalog.json"))
        try writeCollection(
            to: root,
            artworks: [artworkJSON(id: "missing-artwork", localPath: "images/missing.jpg")]
        )
        try writeCollection(
            to: root,
            manifestName: "other",
            id: "other-collection",
            title: "Other Collection",
            shortName: "Other",
            packId: 1,
            artworks: [artworkJSON(id: "existing-artwork", localPath: "images/other/existing.jpg")]
        )

        let existingFile = root.appendingPathComponent("images/other/existing.jpg")
        try FileManager.default.createDirectory(
            at: existingFile.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try Data("image".utf8).write(to: existingFile)

        let library = LocalLibrary(root: root)
        let downloaded = try library.loadDownloadedArtworks(collectionIDs: ["other-collection"])
        let filteredOut = try library.loadDownloadedArtworks(collectionIDs: ["essentials-5k"])

        XCTAssertEqual(downloaded.count, 1)
        XCTAssertEqual(downloaded.first?.0.id, "existing-artwork")
        XCTAssertEqual(downloaded.first?.1, existingFile)
        XCTAssertEqual(filteredOut.count, 0)
    }

    private func makeTemporaryLibraryRoot() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("VedutaCoreTests")
            .appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(
            at: root.appendingPathComponent("collections", isDirectory: true),
            withIntermediateDirectories: true
        )
        return root
    }

    private func writeCatalog(to root: URL, artworkCount: Int) throws {
        let catalogJSON = """
        {
          "schemaVersion": 1,
          "generatedAt": "2026-05-26T12:00:00Z",
          "collections": [
            {
              "id": "essentials-5k",
              "title": "Essentials 5K",
              "shortName": "Essentials",
              "sourcePackId": 0,
              "artworkCount": \(artworkCount),
              "expectedArtworkCount": 5000,
              "manifest": "collections/essentials.json"
            }
          ]
        }
        """

        try catalogJSON.data(using: .utf8)!.write(to: root.appendingPathComponent("catalog.json"))
    }

    private func writeCollection(
        to root: URL,
        manifestName: String = "essentials",
        id: String = "essentials-5k",
        title: String = "Essentials 5K",
        shortName: String = "Essentials",
        packId: Int = 0,
        artworks: [String]
    ) throws {
        let collectionJSON = """
        {
          "schemaVersion": 1,
          "id": "\(id)",
          "title": "\(title)",
          "shortName": "\(shortName)",
          "generatedAt": "2026-05-26T12:00:00Z",
          "source": {
            "type": "artpaper-bundle",
            "packId": \(packId),
            "reportedSizesMb": {
              "regular": 0,
              "hd": 332,
              "ultrahd": 945
            }
          },
          "artworks": [
            \(artworks.joined(separator: ",\n"))
          ]
        }
        """

        try collectionJSON.data(using: .utf8)!.write(
            to: root.appendingPathComponent("collections/\(manifestName).json")
        )
    }

    private func artworkJSON(
        id: String,
        localPath: String,
        importedFromArtPaperPack: String? = nil,
        kind: ArtworkKind? = .flatArt
    ) -> String {
        let importedField = importedFromArtPaperPack.map {
            #", "importedFromArtPaperPack": "\\#($0)""#
        } ?? ""
        let classificationField = kind.map {
            ",\n              \"classification\": {\n                \"kind\": \"\($0.rawValue)\"\n              }"
        } ?? ""

        return """
            {
              "id": "\(id)",
              "title": "A Sunday on La Grande Jatte",
              "creator": "Georges Seurat",
              "attribution": "Georges Seurat, public domain",
              "sources": {
                "canonicalPage": "https://example.com/artworks/\(id)",
                "artistPage": "https://example.com/artists/georges-seurat",
                "upstreamImageBase": "https://images.example.com/\(id)",
                "extraSourceMetadata": "ignored"
              },
              "rights": {
                "work": "Public Domain",
                "reproduction": "CC0",
                "creditLine": "The Metropolitan Museum of Art"
              }\(classificationField),
              "images": {
                "wallpaper": {
                  "localPath": "\(localPath)",
                  "fallbackUrls": ["https://example.com/fallback.jpg"],
                  "width": 5120,
                  "height": 2880,
                  "bytes": 123456,
                  "sha256": "abc123",
                  "downloadedFrom": "https://example.com/image.jpg"\(importedField)
                }
              }
            }
        """
    }
}
