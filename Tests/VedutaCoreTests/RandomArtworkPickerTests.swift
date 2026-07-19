import XCTest
@testable import VedutaCore

final class RandomArtworkPickerTests: XCTestCase {
    func testPickerReturnsOnlyArtworkFromInput() throws {
        let artwork = makeArtwork(id: "artwork-1")
        let imageURL = URL(fileURLWithPath: "/tmp/artwork-1.jpg")

        let picked = try RandomArtworkPicker().pick(count: 1, from: [(artwork, imageURL)])[0]

        XCTAssertEqual(picked.0.id, artwork.id)
        XCTAssertEqual(picked.1, imageURL)
    }

    func testPickerThrowsForEmptyInput() {
        XCTAssertThrowsError(try RandomArtworkPicker().pick(count: 1, from: [])) { error in
            XCTAssertEqual(error as? RandomArtworkPickerError, .emptyLibrary)
        }
    }

    func testPickerAvoidsReturningSameLastArtworkWhenAvoidable() throws {
        let firstArtwork = makeArtwork(id: "artwork-1")
        let secondArtwork = makeArtwork(id: "artwork-2")
        let artworks = [
            (firstArtwork, URL(fileURLWithPath: "/tmp/artwork-1.jpg")),
            (secondArtwork, URL(fileURLWithPath: "/tmp/artwork-2.jpg"))
        ]
        let picker = RandomArtworkPicker()

        let firstPick = try picker.pick(count: 1, from: artworks)[0]
        let secondPick = try picker.pick(count: 1, from: artworks)[0]

        XCTAssertNotEqual(secondPick.0.id, firstPick.0.id)
    }

    func testPickerReturnsDifferentArtworksForMultipleDisplaysWhenAvailable() throws {
        let artworks = [
            (makeArtwork(id: "artwork-1"), URL(fileURLWithPath: "/tmp/artwork-1.jpg")),
            (makeArtwork(id: "artwork-2"), URL(fileURLWithPath: "/tmp/artwork-2.jpg")),
            (makeArtwork(id: "artwork-3"), URL(fileURLWithPath: "/tmp/artwork-3.jpg"))
        ]

        let picked = try RandomArtworkPicker().pick(count: 3, from: artworks)

        XCTAssertEqual(picked.count, 3)
        XCTAssertEqual(Set(picked.map { $0.0.id }).count, 3)
    }

    func testPickerRepeatsArtworksWhenDisplaysOutnumberLibrary() throws {
        let artworks = [
            (makeArtwork(id: "artwork-1"), URL(fileURLWithPath: "/tmp/artwork-1.jpg")),
            (makeArtwork(id: "artwork-2"), URL(fileURLWithPath: "/tmp/artwork-2.jpg"))
        ]

        let picked = try RandomArtworkPicker().pick(count: 3, from: artworks)

        XCTAssertEqual(picked.count, 3)
        XCTAssertEqual(Set(picked.map { $0.0.id }).count, 2)
    }

    private func makeArtwork(id: String) -> Artwork {
        Artwork(
            id: id,
            title: "A Sunday on La Grande Jatte",
            creator: "Georges Seurat",
            sources: ArtworkSources(canonicalPage: "https://example.com/artworks/\(id)"),
            images: ArtworkImages(
                wallpaper: WallpaperImage(
                    localPath: "images/\(id).jpg",
                    fallbackUrls: ["https://example.com/fallback.jpg"],
                    width: 5120,
                    height: 2880,
                    bytes: 123456,
                    sha256: "abc123",
                    lowRes: nil,
                    excluded: nil,
                    removedLocalImage: nil
                )
            ),
            classification: nil
        )
    }
}
