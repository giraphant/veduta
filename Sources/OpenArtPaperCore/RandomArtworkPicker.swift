import Foundation

public enum RandomArtworkPickerError: Error, Equatable {
    case emptyLibrary
}

public final class RandomArtworkPicker {
    private var lastArtworkIDs: Set<String> = []

    public init() {}

    public func pick(from artworks: [(Artwork, URL)]) throws -> (Artwork, URL) {
        try pick(count: 1, from: artworks)[0]
    }

    public func pick(count: Int, from artworks: [(Artwork, URL)]) throws -> [(Artwork, URL)] {
        guard !artworks.isEmpty else { throw RandomArtworkPickerError.emptyLibrary }
        guard count > 0 else { return [] }

        let uniqueCount = min(count, artworks.count)
        let freshCandidates = artworks.filter { !lastArtworkIDs.contains($0.0.id) }
        var remaining = freshCandidates.count >= uniqueCount ? freshCandidates : artworks
        var selected: [(Artwork, URL)] = []

        while selected.count < uniqueCount {
            let index = Int.random(in: 0..<remaining.count)
            selected.append(remaining.remove(at: index))
        }

        var expanded = selected
        while expanded.count < count {
            expanded.append(selected[expanded.count % selected.count])
        }

        lastArtworkIDs = Set(selected.map { $0.0.id })
        return expanded
    }
}
