import XCTest
@testable import VedutaCore

private final class FakeTransport: MirrorTransport {
    var responses: [URL: Data] = [:]
    private(set) var requested: [URL] = []

    func get(_ url: URL) throws -> Data {
        requested.append(url)
        if let data = responses[url] { return data }
        throw MirrorError.http(404)
    }
}

final class MirrorClientTests: XCTestCase {
    private let base = URL(string: "https://mirror.test/")!

    func testCatalogDecodesOptionalMirrorBaseUrl() throws {
        let withField = """
        { "collections": [], "mirrorBaseUrl": "https://example.org/" }
        """
        let withoutField = """
        { "collections": [] }
        """
        let decoder = JSONDecoder()
        XCTAssertEqual(
            try decoder.decode(Catalog.self, from: Data(withField.utf8)).mirrorBaseUrl,
            "https://example.org/"
        )
        XCTAssertNil(try decoder.decode(Catalog.self, from: Data(withoutField.utf8)).mirrorBaseUrl)
    }

    func testDownloadImagePrefersMirrorAndVerifiesChecksum() throws {
        let transport = FakeTransport()
        let imageData = Data("the-real-image".utf8)
        let mirrorURL = base.appendingPathComponent("images/met/x.jpg")
        transport.responses[mirrorURL] = imageData

        let client = MirrorClient(baseURL: base, transport: transport)
        let data = try client.downloadImage(
            localPath: "images/met/x.jpg",
            expectedSHA256: MirrorClient.sha256Hex(imageData),
            fallbackUrls: ["https://upstream.test/x.jpg"]
        )

        XCTAssertEqual(data, imageData)
        XCTAssertEqual(transport.requested.first, mirrorURL)
    }

    func testDownloadImageFallsBackWhenMirrorChecksumMismatches() throws {
        let transport = FakeTransport()
        let good = Data("expected-bytes".utf8)
        let corrupt = Data("corrupt".utf8)
        transport.responses[base.appendingPathComponent("images/x.jpg")] = corrupt
        let fallback = URL(string: "https://upstream.test/x.jpg")!
        transport.responses[fallback] = good

        let client = MirrorClient(baseURL: base, transport: transport)
        let data = try client.downloadImage(
            localPath: "images/x.jpg",
            expectedSHA256: MirrorClient.sha256Hex(good),  // mirror's bytes won't match this
            fallbackUrls: [fallback.absoluteString]
        )

        XCTAssertEqual(data, good)
        XCTAssertEqual(transport.requested, [base.appendingPathComponent("images/x.jpg"), fallback])
    }

    func testDownloadImageThrowsWhenEverythingFails() {
        let client = MirrorClient(baseURL: base, transport: FakeTransport())
        XCTAssertThrowsError(
            try client.downloadImage(localPath: "images/x.jpg", expectedSHA256: nil, fallbackUrls: [])
        ) { error in
            XCTAssertEqual(error as? MirrorError, .allCandidatesFailed)
        }
    }

    // MARK: - LocalLibrary mirror behaviour

    func testStreamsMissingImageFromMirrorIntoLibraryRoot() throws {
        let root = try makeRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        let imageData = Data("downloaded-wallpaper".utf8)
        try writeLibrary(at: root, localPath: "images/met/x.jpg", sha256: MirrorClient.sha256Hex(imageData), bytes: imageData.count)

        let transport = FakeTransport()
        transport.responses[base.appendingPathComponent("images/met/x.jpg")] = imageData
        let library = LocalLibrary(root: root, mirror: MirrorClient(baseURL: base, transport: transport))

        // Available even though no local image is on disk yet.
        let available = try library.availableArtworks()
        XCTAssertEqual(available.map { $0.0.id }, ["mirror-artwork"])

        let artwork = try XCTUnwrap(try library.loadCollection(library.loadCatalog().collections[0]).artworks.first)
        let destination = root.appendingPathComponent("images/met/x.jpg")
        XCTAssertFalse(FileManager.default.fileExists(atPath: destination.path))

        let resolved = try library.ensureLocalImage(for: artwork)
        XCTAssertEqual(resolved, destination)
        XCTAssertEqual(try Data(contentsOf: destination), imageData)

        // Second call is a no-op (already local).
        let again = try library.ensureLocalImage(for: artwork)
        XCTAssertEqual(again, destination)
    }

    func testOversizedAndRemovedImagesAreNotMirrorAvailable() throws {
        let root = try makeRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        try writeLibrary(at: root, localPath: "images/big.jpg", sha256: "x", bytes: 500_000_000)
        let library = LocalLibrary(
            root: root,
            mirror: MirrorClient(baseURL: base, transport: FakeTransport()),
            maxImageBytes: 64 * 1024 * 1024
        )
        XCTAssertTrue(try library.availableArtworks().isEmpty, "gigapixel image should not be offered for streaming")
    }

    func testWithoutMirrorMissingImageIsNotAvailable() throws {
        let root = try makeRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        try writeLibrary(at: root, localPath: "images/met/x.jpg", sha256: "x", bytes: 1000)
        let library = LocalLibrary(root: root) // no mirror
        XCTAssertTrue(try library.availableArtworks().isEmpty)
    }

    func testCollectionAvailabilitySeparatesDownloadedFromStreamable() throws {
        let root = try makeRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        // catalog with two collections
        let catalog = """
        {
          "collections": [
            { "id": "essentials", "title": "Essentials", "shortName": "Essentials", "sourcePackId": 0, "artworkCount": 1, "expectedArtworkCount": 1, "manifest": "collections/essentials.json" },
            { "id": "berlin", "title": "Berlin", "shortName": "Berlin", "sourcePackId": 1, "artworkCount": 1, "expectedArtworkCount": 1, "manifest": "collections/berlin.json" }
          ]
        }
        """
        try Data(catalog.utf8).write(to: root.appendingPathComponent("catalog.json"))
        try Data(manifestJSON(id: "essentials", artworkID: "ess-1", localPath: "images/essentials/ess-1.jpg").utf8)
            .write(to: root.appendingPathComponent("collections/essentials.json"))
        try Data(manifestJSON(id: "berlin", artworkID: "ber-1", localPath: "images/berlin/ber-1.jpg").utf8)
            .write(to: root.appendingPathComponent("collections/berlin.json"))

        // only the essentials image exists on disk
        let essImage = root.appendingPathComponent("images/essentials/ess-1.jpg")
        try FileManager.default.createDirectory(at: essImage.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data("img".utf8).write(to: essImage)

        let library = LocalLibrary(root: root, mirror: MirrorClient(baseURL: base, transport: FakeTransport()))
        let availability = try library.collectionAvailability()

        let essentials = try XCTUnwrap(availability.first { $0.summary.id == "essentials" })
        let berlin = try XCTUnwrap(availability.first { $0.summary.id == "berlin" })
        XCTAssertTrue(essentials.hasLocal)
        XCTAssertFalse(essentials.hasStreamable)  // its only image is already local
        XCTAssertFalse(berlin.hasLocal)
        XCTAssertTrue(berlin.hasStreamable)       // only reachable via mirror
    }

    func testPendingDownloadsListsOnlyMissingStreamableArtworks() throws {
        let root = try makeRoot()
        defer { try? FileManager.default.removeItem(at: root) }

        let catalog = """
        { "collections": [ { "id": "c", "title": "C", "shortName": "C", "sourcePackId": 0, "artworkCount": 2, "expectedArtworkCount": 2, "manifest": "collections/c.json" } ] }
        """
        try Data(catalog.utf8).write(to: root.appendingPathComponent("catalog.json"))
        let manifest = """
        {
          "schemaVersion": 1, "id": "c", "title": "C", "shortName": "C", "generatedAt": "2026-06-06T00:00:00Z",
          "source": { "type": "mirror", "packId": 0, "reportedSizesMb": {} },
          "artworks": [
            { "id": "a-1", "title": "A1", "creator": "x", "attribution": "y", "sources": { "canonicalPage": "https://e.com/1" }, "rights": { "work": "public-domain", "reproduction": "f" }, "images": { "wallpaper": { "localPath": "images/c/a-1.jpg", "fallbackUrls": [], "bytes": 1000 } } },
            { "id": "a-2", "title": "A2", "creator": "x", "attribution": "y", "sources": { "canonicalPage": "https://e.com/2" }, "rights": { "work": "public-domain", "reproduction": "f" }, "images": { "wallpaper": { "localPath": "images/c/a-2.jpg", "fallbackUrls": [], "bytes": 1000 } } }
          ]
        }
        """
        try Data(manifest.utf8).write(to: root.appendingPathComponent("collections/c.json"))

        let local = root.appendingPathComponent("images/c/a-1.jpg")
        try FileManager.default.createDirectory(at: local.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data("img".utf8).write(to: local)

        let library = LocalLibrary(root: root, mirror: MirrorClient(baseURL: base, transport: FakeTransport()))
        let pending = try library.pendingDownloads(inCollection: "c")
        XCTAssertEqual(pending.map { $0.id }, ["a-2"], "only the not-yet-local artwork is pending")
    }

    func testLoadCatalogFetchesFromMirrorWhenMissingLocally() throws {
        let root = try makeRoot(createCollectionsDir: false)
        defer { try? FileManager.default.removeItem(at: root) }

        let transport = FakeTransport()
        transport.responses[base.appendingPathComponent("catalog.json")] = Data(catalogJSON.utf8)
        let library = LocalLibrary(root: root, mirror: MirrorClient(baseURL: base, transport: transport))

        let catalog = try library.loadCatalog()
        XCTAssertEqual(catalog.collections.map(\.id), ["mirror-collection"])
        XCTAssertTrue(
            FileManager.default.fileExists(atPath: root.appendingPathComponent("catalog.json").path),
            "fetched catalog should be cached into the library root"
        )
    }

    // MARK: - Fixtures

    private func makeRoot(createCollectionsDir: Bool = true) throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("MirrorClientTests")
            .appendingPathComponent(UUID().uuidString)
        if createCollectionsDir {
            try FileManager.default.createDirectory(
                at: root.appendingPathComponent("collections", isDirectory: true),
                withIntermediateDirectories: true
            )
        } else {
            try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        }
        return root
    }

    private let catalogJSON = """
    {
      "collections": [
        {
          "id": "mirror-collection",
          "title": "Mirror Collection",
          "shortName": "Mirror",
          "sourcePackId": 0,
          "artworkCount": 1,
          "expectedArtworkCount": 1,
          "manifest": "collections/mirror.json"
        }
      ]
    }
    """

    private func manifestJSON(id: String, artworkID: String, localPath: String) -> String {
        """
        {
          "schemaVersion": 1,
          "id": "\(id)",
          "title": "\(id)",
          "shortName": "\(id)",
          "generatedAt": "2026-06-06T00:00:00Z",
          "source": { "type": "mirror", "packId": 0, "reportedSizesMb": {} },
          "artworks": [
            {
              "id": "\(artworkID)",
              "title": "Artwork",
              "creator": "Anon",
              "attribution": "public domain",
              "sources": { "canonicalPage": "https://example.com/a" },
              "rights": { "work": "public-domain", "reproduction": "faithful" },
              "images": {
                "wallpaper": {
                  "localPath": "\(localPath)",
                  "fallbackUrls": [],
                  "sha256": "x",
                  "bytes": 1000
                }
              }
            }
          ]
        }
        """
    }

    private func writeLibrary(at root: URL, localPath: String, sha256: String, bytes: Int) throws {
        try Data(catalogJSON.utf8).write(to: root.appendingPathComponent("catalog.json"))
        let manifest = """
        {
          "schemaVersion": 1,
          "id": "mirror-collection",
          "title": "Mirror Collection",
          "shortName": "Mirror",
          "generatedAt": "2026-06-06T00:00:00Z",
          "source": { "type": "mirror", "packId": 0, "reportedSizesMb": {} },
          "artworks": [
            {
              "id": "mirror-artwork",
              "title": "Streamed Artwork",
              "creator": "Anon",
              "attribution": "public domain",
              "sources": { "canonicalPage": "https://example.com/a" },
              "rights": { "work": "public-domain", "reproduction": "faithful" },
              "images": {
                "wallpaper": {
                  "localPath": "\(localPath)",
                  "fallbackUrls": ["https://upstream.test/a.jpg"],
                  "sha256": "\(sha256)",
                  "bytes": \(bytes)
                }
              }
            }
          ]
        }
        """
        try Data(manifest.utf8).write(to: root.appendingPathComponent("collections/mirror.json"))
    }
}
