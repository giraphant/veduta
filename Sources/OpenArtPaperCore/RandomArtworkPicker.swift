import Foundation

public enum RandomArtworkPickerError: Error, Equatable {
    case emptyLibrary
}

public final class RandomArtworkPicker {
    private var lastArtworkID: String?

    public init() {}

    public func pick(from artworks: [(Artwork, URL)]) throws -> (Artwork, URL) {
        guard !artworks.isEmpty else { throw RandomArtworkPickerError.emptyLibrary }
        if artworks.count == 1 {
            lastArtworkID = artworks[0].0.id
            return artworks[0]
        }
        let candidates = artworks.filter { $0.0.id != lastArtworkID }
        let selected = candidates.randomElement() ?? artworks[0]
        lastArtworkID = selected.0.id
        return selected
    }
}
