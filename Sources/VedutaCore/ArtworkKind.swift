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
