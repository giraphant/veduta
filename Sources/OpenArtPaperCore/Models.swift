import Foundation

public struct Catalog: Decodable, Sendable, Equatable {
    public let collections: [CollectionSummary]

    public init(collections: [CollectionSummary]) {
        self.collections = collections
    }
}

public struct CollectionSummary: Decodable, Sendable, Equatable {
    public let id: String
    public let title: String
    public let shortName: String
    public let sourcePackId: Int
    public let artworkCount: Int
    public let expectedArtworkCount: Int
    public let manifest: String

    public init(
        id: String,
        title: String,
        shortName: String,
        sourcePackId: Int,
        artworkCount: Int,
        expectedArtworkCount: Int,
        manifest: String
    ) {
        self.id = id
        self.title = title
        self.shortName = shortName
        self.sourcePackId = sourcePackId
        self.artworkCount = artworkCount
        self.expectedArtworkCount = expectedArtworkCount
        self.manifest = manifest
    }
}

public struct CollectionManifest: Decodable, Sendable, Equatable {
    public let schemaVersion: Int
    public let id: String
    public let title: String
    public let shortName: String
    public let generatedAt: String
    public let source: CollectionSource
    public let artworks: [Artwork]

    public init(
        schemaVersion: Int,
        id: String,
        title: String,
        shortName: String,
        generatedAt: String,
        source: CollectionSource,
        artworks: [Artwork]
    ) {
        self.schemaVersion = schemaVersion
        self.id = id
        self.title = title
        self.shortName = shortName
        self.generatedAt = generatedAt
        self.source = source
        self.artworks = artworks
    }
}

public struct CollectionSource: Decodable, Sendable, Equatable {
    public let type: String
    public let packId: Int
    public let reportedSizesMb: [String: Int]

    public init(type: String, packId: Int, reportedSizesMb: [String: Int]) {
        self.type = type
        self.packId = packId
        self.reportedSizesMb = reportedSizesMb
    }
}

public struct Artwork: Decodable, Sendable, Equatable {
    public let id: String
    public let title: String
    public let creator: String
    public let attribution: String
    public let sources: ArtworkSources
    public let rights: ArtworkRights
    public let images: ArtworkImages

    public init(
        id: String,
        title: String,
        creator: String,
        attribution: String,
        sources: ArtworkSources,
        rights: ArtworkRights,
        images: ArtworkImages
    ) {
        self.id = id
        self.title = title
        self.creator = creator
        self.attribution = attribution
        self.sources = sources
        self.rights = rights
        self.images = images
    }
}

public struct ArtworkSources: Decodable, Sendable, Equatable {
    public let canonicalPage: String
    public let artistPage: String?
    public let upstreamImageBase: String?

    public init(
        canonicalPage: String,
        artistPage: String? = nil,
        upstreamImageBase: String? = nil
    ) {
        self.canonicalPage = canonicalPage
        self.artistPage = artistPage
        self.upstreamImageBase = upstreamImageBase
    }
}

public struct ArtworkRights: Decodable, Sendable, Equatable {
    public let work: String
    public let reproduction: String
    public let creditLine: String?

    public init(work: String, reproduction: String, creditLine: String? = nil) {
        self.work = work
        self.reproduction = reproduction
        self.creditLine = creditLine
    }
}

public struct ArtworkImages: Decodable, Sendable, Equatable {
    public let wallpaper: WallpaperImage

    public init(wallpaper: WallpaperImage) {
        self.wallpaper = wallpaper
    }
}

public struct WallpaperImage: Decodable, Sendable, Equatable {
    public let localPath: String
    public let fallbackUrls: [String]
    public let width: Int?
    public let height: Int?
    public let bytes: Int?
    public let sha256: String?
    public let downloadedFrom: String?
    public let importedFromArtPaperPack: String?

    public init(
        localPath: String,
        fallbackUrls: [String],
        width: Int? = nil,
        height: Int? = nil,
        bytes: Int? = nil,
        sha256: String? = nil,
        downloadedFrom: String? = nil,
        importedFromArtPaperPack: String? = nil
    ) {
        self.localPath = localPath
        self.fallbackUrls = fallbackUrls
        self.width = width
        self.height = height
        self.bytes = bytes
        self.sha256 = sha256
        self.downloadedFrom = downloadedFrom
        self.importedFromArtPaperPack = importedFromArtPaperPack
    }
}
