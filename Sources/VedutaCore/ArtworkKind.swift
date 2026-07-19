import Foundation

public enum ArtworkKind: String, Sendable, Equatable, CaseIterable {
    case flatArt = "flat-art"
    case photography = "photography"
    case streetArt = "street-art"
    case objectOrDocument = "object-or-document"
    case other = "other"

    public var displayName: String {
        switch self {
        case .flatArt: "Flat Art"
        case .photography: "Photography"
        case .streetArt: "Street Art / Murals"
        case .objectOrDocument: "Objects / Documents"
        case .other: "Other"
        }
    }
}

public struct ArtworkClassification: Decodable, Sendable, Equatable {
    public let kind: ArtworkKind

    private enum CodingKeys: String, CodingKey {
        case kind
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let rawKind = try container.decodeIfPresent(String.self, forKey: .kind)
        self.kind = rawKind.flatMap(ArtworkKind.init(rawValue:)) ?? .other
    }
}

public enum ArtworkKindClassifier {
    private static let streetArtCollectionIDs: Set<String> = ["east-side", "graffitimundo"]

    private static let photographyCreators = [
        "alexander gardner",
        "alfred stieglitz",
        "ansel adams",
        "berenice abbott",
        "carleton watkins",
        "dorothea lange",
        "eadweard muybridge",
        "edward s curtis",
        "gustave le gray",
        "laura gilpin",
        "lewis hine",
        "lewis wickes hine",
        "man ray",
        "mathew brady",
        "paul strand",
        "timothy o sullivan",
        "walker evans",
        "william henry jackson"
    ]

    private static let photographyTitleTerms = [
        "albumen print",
        "daguerreotype",
        "gelatin silver",
        "photograph"
    ]

    private static let objectOrDocumentTitleTerms = [
        "bowl",
        "carpet",
        "chart",
        "cup with",
        "dish",
        "document",
        "ewer",
        "fragment",
        "jar",
        "letter",
        "manuscript",
        "map of",
        "page from",
        "perspective map",
        "plate",
        "rug",
        "textile",
        "vase",
        "wall fragment",
        "wine cistern"
    ]

    public static func kind(for artwork: Artwork, collectionID: String) -> ArtworkKind {
        if let kind = artwork.classification?.kind {
            return kind
        }

        if streetArtCollectionIDs.contains(collectionID) {
            return .streetArt
        }

        let normalizedCreator = normalized(artwork.creator)
        if containsAny(photographyCreators, in: normalizedCreator) {
            return .photography
        }

        let normalizedTitle = normalized(artwork.title)
        if containsAny(photographyTitleTerms, in: normalizedTitle) {
            return .photography
        }

        if containsAny(objectOrDocumentTitleTerms, in: normalizedTitle) {
            return .objectOrDocument
        }

        return .flatArt
    }

    private static func containsAny(_ terms: [String], in value: String) -> Bool {
        terms.contains { value.contains($0) }
    }

    private static func normalized(_ value: String) -> String {
        value
            .folding(options: [.diacriticInsensitive, .caseInsensitive], locale: Locale(identifier: "en_US_POSIX"))
            .lowercased()
            .replacingOccurrences(of: ".", with: " ")
            .replacingOccurrences(of: "’", with: "'")
    }
}
