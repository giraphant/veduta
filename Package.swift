// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "Veduta",
    platforms: [.macOS(.v13)],
    products: [
        .library(name: "VedutaCore", targets: ["VedutaCore"]),
        .executable(name: "Veduta", targets: ["Veduta"]),
    ],
    targets: [
        .target(name: "VedutaCore"),
        .executableTarget(name: "Veduta", dependencies: ["VedutaCore"]),
        .testTarget(name: "VedutaCoreTests", dependencies: ["VedutaCore"]),
    ]
)
