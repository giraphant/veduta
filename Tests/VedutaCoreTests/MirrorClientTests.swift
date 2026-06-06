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
