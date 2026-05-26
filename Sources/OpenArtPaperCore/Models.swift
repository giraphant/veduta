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
    public let sourcePackId: String
    public let artworkCount: Int
    public let expectedArtworkCount: Int
    public let manifest: String

    public init(
        id: String,
        title: String,
        shortName: String,
        sourcePackId: String,
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
    public let id: String
    public let title: String
    public let shortName: String
    public let sourcePackId: String
    public let artworks: [Artwork]

    public init(
        id: String,
        title: String,
        shortName: String,
        sourcePackId: String,
        artworks: [Artwork]
    ) {
        self.id = id
        self.title = title
        self.shortName = shortName
        self.sourcePackId = sourcePackId
        self.artworks = artworks
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
    public let primary: String
    public let metObjectId: String?
    public let chicagoArtworkId: String?
    public let rijksmuseumObjectNumber: String?
    public let wikidataId: String?

    public init(
        primary: String,
        metObjectId: String? = nil,
        chicagoArtworkId: String? = nil,
        rijksmuseumObjectNumber: String? = nil,
        wikidataId: String? = nil
    ) {
        self.primary = primary
        self.metObjectId = metObjectId
        self.chicagoArtworkId = chicagoArtworkId
        self.rijksmuseumObjectNumber = rijksmuseumObjectNumber
        self.wikidataId = wikidataId
    }
}

public struct ArtworkRights: Decodable, Sendable, Equatable {
    public let license: String
    public let creditLine: String?
    public let isPublicDomain: Bool?

    public init(license: String, creditLine: String? = nil, isPublicDomain: Bool? = nil) {
        self.license = license
        self.creditLine = creditLine
        self.isPublicDomain = isPublicDomain
    }
}

public struct ArtworkImages: Decodable, Sendable, Equatable {
    public let wallpaper: WallpaperImage
    public let fallbackUrls: [String]

    public init(wallpaper: WallpaperImage, fallbackUrls: [String]) {
        self.wallpaper = wallpaper
        self.fallbackUrls = fallbackUrls
    }
}

public struct WallpaperImage: Decodable, Sendable, Equatable {
    public let localPath: String
    public let width: Int?
    public let height: Int?
    public let bytes: Int?
    public let sha256: String?
    public let downloadedFrom: String?
    public let importedFromArtPaperPack: Bool?

    public init(
        localPath: String,
        width: Int? = nil,
        height: Int? = nil,
        bytes: Int? = nil,
        sha256: String? = nil,
        downloadedFrom: String? = nil,
        importedFromArtPaperPack: Bool? = nil
    ) {
        self.localPath = localPath
        self.width = width
        self.height = height
        self.bytes = bytes
        self.sha256 = sha256
        self.downloadedFrom = downloadedFrom
        self.importedFromArtPaperPack = importedFromArtPaperPack
    }
}
