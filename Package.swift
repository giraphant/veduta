// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "OpenArtPaper",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "OpenArtPaperCore", targets: ["OpenArtPaperCore"]),
        .executable(name: "OpenArtPaper", targets: ["OpenArtPaper"]),
    ],
    targets: [
        .target(name: "OpenArtPaperCore"),
        .executableTarget(name: "OpenArtPaper", dependencies: ["OpenArtPaperCore"]),
        .testTarget(name: "OpenArtPaperCoreTests", dependencies: ["OpenArtPaperCore"]),
    ]
)
