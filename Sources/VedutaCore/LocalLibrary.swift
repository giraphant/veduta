import Foundation

public enum LibraryError: Error, Equatable {
    case imageUnavailable(String)
}

public final class LocalLibrary {
    public let root: URL

    private let decoder: JSONDecoder
    private let mirror: MirrorClient?
    private let maxImageBytes: Int

    /// - Parameters:
    ///   - mirror: when set, missing catalog/manifests/images are fetched from
    ///     the mirror and written into `root`, so the local-first reads below
    ///     transparently work for a fresh install with no library built.
    ///   - maxImageBytes: artworks whose mirrored image exceeds this are not
    ///     offered for streaming (avoids pulling gigapixel originals just to
    ///     set a wallpaper); locally present ones are always usable.
    public init(root: URL, mirror: MirrorClient? = nil, maxImageBytes: Int = 64 * 1024 * 1024) {
        self.root = root
        self.decoder = JSONDecoder()
        self.mirror = mirror
        self.maxImageBytes = maxImageBytes
    }

    public func loadCatalog() throws -> Catalog {
        let url = root.appendingPathComponent("catalog.json")
        try ensureLocalMetadata(at: url, relativePath: "catalog.json")
        return try decode(Catalog.self, from: url)
    }

    public func loadCollection(_ summary: CollectionSummary) throws -> CollectionManifest {
        let url = root.appendingPathComponent(summary.manifest)
        try ensureLocalMetadata(at: url, relativePath: summary.manifest)
        return try decode(CollectionManifest.self, from: url)
    }

    public func wallpaperURL(for artwork: Artwork) -> URL {
        root.appendingPathComponent(artwork.images.wallpaper.localPath)
    }

    // MARK: - Mirror-backed availability

    /// Collections with at least one *available* artwork — local on disk, or
    /// streamable from the mirror. With no mirror configured this is identical
    /// to `loadDownloadedCollections`.
    public func availableCollections(enabledArtworkKinds: Set<ArtworkKind>? = nil) throws -> [CollectionSummary] {
        let catalog = try loadCatalog()
        var result: [CollectionSummary] = []
        for summary in catalog.collections {
            let collection = try loadCollection(summary)
            if collection.artworks.contains(where: {
                isAvailable($0, in: summary.id, enabledArtworkKinds: enabledArtworkKinds)
            }) {
                result.append(summary)
            }
        }
        return result
    }

    /// Available artworks paired with the local path where their image lives
    /// (or will live once materialized via `ensureLocalImage`).
    public func availableArtworks(
        collectionIDs: Set<String>? = nil,
        enabledArtworkKinds: Set<ArtworkKind>? = nil
    ) throws -> [(Artwork, URL)] {
        let catalog = try loadCatalog()
        var result: [(Artwork, URL)] = []
        for summary in catalog.collections {
            if let collectionIDs, !collectionIDs.contains(summary.id) { continue }
            let collection = try loadCollection(summary)
            for artwork in collection.artworks
            where isAvailable(artwork, in: summary.id, enabledArtworkKinds: enabledArtworkKinds) {
                result.append((artwork, wallpaperURL(for: artwork)))
            }
        }
        return result
    }

    /// Return the local file URL for an artwork's image, downloading it from
    /// the mirror (then upstream fallbacks) into `root` if it isn't present.
    @discardableResult
    public func ensureLocalImage(for artwork: Artwork) throws -> URL {
        let destination = wallpaperURL(for: artwork)
        if FileManager.default.fileExists(atPath: destination.path) { return destination }
        guard let mirror else { throw LibraryError.imageUnavailable(artwork.id) }

        let wallpaper = artwork.images.wallpaper
        let data = try mirror.downloadImage(
            localPath: wallpaper.localPath,
            expectedSHA256: wallpaper.sha256,
            fallbackUrls: wallpaper.fallbackUrls
        )
        try FileManager.default.createDirectory(
            at: destination.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try data.write(to: destination, options: .atomic)
        return destination
    }

    private func isAvailable(
        _ artwork: Artwork,
        in collectionID: String,
        enabledArtworkKinds: Set<ArtworkKind>?
    ) -> Bool {
        guard artwork.images.wallpaper.excluded != true else { return false }
        let localExists = FileManager.default.fileExists(atPath: wallpaperURL(for: artwork).path)
        guard localExists || mirrorEligible(artwork) else { return false }
        guard let enabledArtworkKinds else { return true }
        let kind = ArtworkKindClassifier.kind(for: artwork, collectionID: collectionID)
        return enabledArtworkKinds.contains(kind)
    }

    private func mirrorEligible(_ artwork: Artwork) -> Bool {
        guard mirror != nil else { return false }
        let wallpaper = artwork.images.wallpaper
        guard wallpaper.removedLocalImage != true else { return false }
        if let bytes = wallpaper.bytes, bytes > maxImageBytes { return false }
        return true
    }

    private func ensureLocalMetadata(at url: URL, relativePath: String) throws {
        if FileManager.default.fileExists(atPath: url.path) { return }
        // No mirror: leave the file missing so `decode` throws exactly as it
        // did before mirror support existed.
        guard let mirror else { return }
        let data = try mirror.fetch(relativePath: relativePath)
        try FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try data.write(to: url, options: .atomic)
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
