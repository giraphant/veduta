import Foundation

// These models declare only the manifest fields the app reads; Decodable
// ignores the rest of the pipeline's JSON (provenance, rights, source info).

public struct Catalog: Decodable, Sendable, Equatable {
    public let collections: [CollectionSummary]
}

public struct CollectionSummary: Decodable, Sendable, Equatable {
    public let id: String
    public let title: String
    public let shortName: String
    public let artworkCount: Int
    public let manifest: String
    /// Relative path of the curated cover artwork's image (the collection's
    /// signature piece). Optional; the app falls back to a heuristic pick.
    public let cover: String?
}

public struct CollectionManifest: Decodable, Sendable, Equatable {
    public let artworks: [Artwork]
}

public struct Artwork: Decodable, Sendable, Equatable {
    public let id: String
    public let title: String
    public let creator: String
    public let sources: ArtworkSources
    public let images: ArtworkImages
    public let classification: ArtworkClassification?
}

public struct ArtworkSources: Decodable, Sendable, Equatable {
    public let canonicalPage: String
}

public struct ArtworkImages: Decodable, Sendable, Equatable {
    public let wallpaper: WallpaperImage
}

public struct WallpaperImage: Decodable, Sendable, Equatable {
    public let localPath: String
    public let fallbackUrls: [String]
    public let width: Int?
    public let height: Int?
    public let bytes: Int?
    public let sha256: String?
    public let lowRes: Bool?
    public let excluded: Bool?
    public let removedLocalImage: Bool?
}
