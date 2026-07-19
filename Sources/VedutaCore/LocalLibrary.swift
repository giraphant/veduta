import Foundation

public enum LibraryError: Error, Equatable {
    case imageUnavailable(String)
}

public final class LocalLibrary {
    public let root: URL

    private let decoder: JSONDecoder
    private let mirror: MirrorClient?

    /// Artworks whose mirrored image exceeds this are not offered for
    /// streaming (avoids pulling gigapixel originals just to set a
    /// wallpaper); locally present ones are always usable.
    private static let maxImageBytes = 64 * 1024 * 1024

    /// - Parameter mirror: when set, missing catalog/manifests/images are
    ///   fetched from the mirror and written into `root`, so the local-first
    ///   reads below transparently work for a fresh install with no library
    ///   built.
    public init(root: URL, mirror: MirrorClient? = nil) {
        self.root = root
        self.decoder = JSONDecoder()
        self.mirror = mirror
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

    /// A collection's two independent dimensions: how many artworks are on
    /// disk (`localCount`) vs still only streamable from the mirror
    /// (`streamableCount`, i.e. pending downloads). A fully-downloaded
    /// collection has `streamableCount == 0`.
    public struct CollectionAvailability: Equatable {
        public let summary: CollectionSummary
        public let localCount: Int
        public let streamableCount: Int
        /// Relative path of the collection's cover image. Shown only once it's
        /// been prefetched to a local file (resolve with `localImageURL`), so
        /// the card never depends on a flaky network image load.
        public let coverPath: String?

        public var hasLocal: Bool { localCount > 0 }
    }

    /// Upper bound on an artwork's bytes for it to be a cover candidate, so a
    /// thumbnail never pulls a multi-hundred-MB gigapixel original.
    private static let coverMaxBytes = 20 * 1024 * 1024

    /// One pass over the catalog counting, per collection, how much is local
    /// vs still only on the mirror — so the UI can show an "Enable" toggle and
    /// a "Download all (N)" action independently.
    public func collectionAvailability() throws -> [CollectionAvailability] {
        let catalog = try loadCatalog()
        var result: [CollectionAvailability] = []
        for summary in catalog.collections {
            let collection = try loadCollection(summary)
            var localCount = 0
            var streamableCount = 0
            var cover: Artwork?
            var coverScore = (Int.max, Int.max)  // (landscapeRank, bytes); lower wins
            for artwork in collection.artworks where artwork.images.wallpaper.excluded != true {
                let wallpaper = artwork.images.wallpaper
                if FileManager.default.fileExists(atPath: wallpaperURL(for: artwork).path) {
                    localCount += 1
                } else if mirrorEligible(artwork) {
                    streamableCount += 1
                }
                // Prefer the smallest landscape image within the cover size cap.
                if wallpaper.removedLocalImage != true, wallpaper.lowRes != true,
                   let bytes = wallpaper.bytes, bytes <= Self.coverMaxBytes {
                    let landscapeRank = (wallpaper.width ?? 0) > (wallpaper.height ?? 0) ? 0 : 1
                    let score = (landscapeRank, bytes)
                    if score < coverScore {
                        coverScore = score
                        cover = artwork
                    }
                }
            }
            if localCount > 0 || streamableCount > 0 {
                // Curated signature cover from the catalog wins; otherwise the
                // heuristic pick (smallest landscape) is the fallback.
                let coverPath = summary.cover ?? cover.map { $0.images.wallpaper.localPath }
                result.append(CollectionAvailability(
                    summary: summary,
                    localCount: localCount,
                    streamableCount: streamableCount,
                    coverPath: coverPath
                ))
            }
        }
        return result
    }

    /// File URL for a library-relative image path when it's on disk, else nil.
    public func localImageURL(forRelativePath path: String) -> URL? {
        let local = root.appendingPathComponent(path)
        return FileManager.default.fileExists(atPath: local.path) ? local : nil
    }

    /// Download a collection's cover image into the library (at its normal
    /// `images/...` path) if it isn't already there. Returns the local URL.
    @discardableResult
    public func ensureLocalCover(relativePath: String) throws -> URL {
        let destination = root.appendingPathComponent(relativePath)
        if FileManager.default.fileExists(atPath: destination.path) { return destination }
        guard let mirror else { throw LibraryError.imageUnavailable(relativePath) }
        let data = try mirror.fetch(relativePath: relativePath)
        try FileManager.default.createDirectory(
            at: destination.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try data.write(to: destination, options: .atomic)
        return destination
    }

    /// Artworks in a collection that can be pulled from the mirror but aren't
    /// on disk yet — the work list for a "Download all" action.
    public func pendingDownloads(inCollection collectionID: String) throws -> [Artwork] {
        let catalog = try loadCatalog()
        guard let summary = catalog.collections.first(where: { $0.id == collectionID }) else { return [] }
        let collection = try loadCollection(summary)
        return collection.artworks.filter { artwork in
            artwork.images.wallpaper.excluded != true
                && mirrorEligible(artwork)
                && !FileManager.default.fileExists(atPath: wallpaperURL(for: artwork).path)
        }
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
        if let bytes = wallpaper.bytes, bytes > Self.maxImageBytes { return false }
        return true
    }

    private func ensureLocalMetadata(at url: URL, relativePath: String) throws {
        if FileManager.default.fileExists(atPath: url.path) { return }
        // No mirror: leave the file missing and let `decode` throw.
        guard let mirror else { return }
        let data = try mirror.fetch(relativePath: relativePath)
        try FileManager.default.createDirectory(
            at: url.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try data.write(to: url, options: .atomic)
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
