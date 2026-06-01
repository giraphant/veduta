import Foundation

public final class LocalLibrary {
    public let root: URL

    private let decoder: JSONDecoder

    public init(root: URL) {
        self.root = root
        self.decoder = JSONDecoder()
    }

    public func loadCatalog() throws -> Catalog {
        try decode(Catalog.self, from: root.appendingPathComponent("catalog.json"))
    }

    public func loadCollection(_ summary: CollectionSummary) throws -> CollectionManifest {
        try decode(CollectionManifest.self, from: root.appendingPathComponent(summary.manifest))
    }

    public func wallpaperURL(for artwork: Artwork) -> URL {
        root.appendingPathComponent(artwork.images.wallpaper.localPath)
    }

    public func loadDownloadedCollections(enabledArtworkKinds: Set<ArtworkKind>? = nil) throws -> [CollectionSummary] {
        let catalog = try loadCatalog()
        var downloadedCollections: [CollectionSummary] = []

        for summary in catalog.collections {
            let collection = try loadCollection(summary)
            if collection.artworks.contains(where: { artwork in
                isDownloaded(artwork, in: summary.id, enabledArtworkKinds: enabledArtworkKinds)
            }) {
                downloadedCollections.append(summary)
            }
        }

        return downloadedCollections
    }

    public func loadDownloadedArtworks(
        collectionIDs: Set<String>? = nil,
        enabledArtworkKinds: Set<ArtworkKind>? = nil
    ) throws -> [(Artwork, URL)] {
        let catalog = try loadCatalog()
        var downloadedArtworks: [(Artwork, URL)] = []

        for summary in catalog.collections {
            if let collectionIDs, !collectionIDs.contains(summary.id) {
                continue
            }

            let collection = try loadCollection(summary)
            for artwork in collection.artworks {
                let url = wallpaperURL(for: artwork)
                if isDownloaded(artwork, in: summary.id, enabledArtworkKinds: enabledArtworkKinds) {
                    downloadedArtworks.append((artwork, url))
                }
            }
        }

        return downloadedArtworks
    }

    public func loadAllDownloadedArtworks() throws -> [(Artwork, URL)] {
        try loadDownloadedArtworks()
    }

    private func isDownloaded(
        _ artwork: Artwork,
        in collectionID: String,
        enabledArtworkKinds: Set<ArtworkKind>?
    ) -> Bool {
        guard artwork.images.wallpaper.excluded != true else { return false }
        guard FileManager.default.fileExists(atPath: wallpaperURL(for: artwork).path) else { return false }
        guard let enabledArtworkKinds else { return true }
        let kind = ArtworkKindClassifier.kind(for: artwork, collectionID: collectionID)
        return enabledArtworkKinds.contains(kind)
    }

    private func decode<T: Decodable>(_ type: T.Type, from url: URL) throws -> T {
        let data = try Data(contentsOf: url)
        return try decoder.decode(type, from: data)
    }
}
