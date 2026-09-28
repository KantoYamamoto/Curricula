// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Curricula",
    products: [
        .library(name: "Curricula", targets: ["Curricula"]),
        .executable(name: "curricula", targets: ["CurriculaCLI"])
    ],
    targets: [
        .target(name: "Curricula"),
        .target(name: "CurriculaPilot", dependencies: ["Curricula"], resources: [.process("Resources")]),
        .executableTarget(name: "CurriculaCLI", dependencies: ["Curricula", "CurriculaPilot"]),
        .testTarget(name: "CurriculaTests", dependencies: ["Curricula", "CurriculaPilot"])
    ]
)
