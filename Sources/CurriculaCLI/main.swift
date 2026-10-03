import Foundation
import Curricula
import CurriculaPilot

func run() throws {
    let args = Array(CommandLine.arguments.dropFirst())
    if args == ["check-json"] {
        struct Request: Decodable { let dataset: V2.Dataset; let history: [V2.Dataset] }
        let request = try JSONDecoder().decode(Request.self, from: FileHandle.standardInput.readDataToEndOfFile())
        let issues = ValidatorV2.validate(request.dataset, history: request.history)
        let output: [String: Any] = [
            "canonical": String(decoding: try request.dataset.canonicalJSON(), as: UTF8.self),
            "issues": issues.map { ["code": $0.code, "path": $0.path, "message": $0.message] }
        ]
        FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys]))
        return
    }
    guard args == ["validate"] || (args.count == 2 && ["export", "export-examples", "export-cross-subjects", "export-v2"].contains(args[0])) else {
        throw CLIError.message("Usage: curricula validate | curricula export <output.json> | curricula export-examples <directory> | curricula export-cross-subjects <output.json> | curricula export-v2 <directory>")
    }
    if args.first == "export-v2" || args == ["validate"] {
        let datasets = [try StructuredSamples.make()] + (try EditingSamples.revisions())
        for dataset in datasets {
            let issues = ValidatorV2.validate(dataset, history: datasets.filter { $0.release != dataset.release })
            guard issues.isEmpty else { throw CLIError.message(issues.map(\.description).joined(separator: "\n")) }
        }
        if args.first == "export-v2" {
            for dataset in datasets {
                try dataset.canonicalJSON().write(to: URL(fileURLWithPath: args[1]).appendingPathComponent(dataset.release + ".json"), options: .atomic)
            }
            return
        }
        for dataset in datasets { print("Valid: \(dataset.release), schema \(dataset.schemaVersion), \(dataset.entities.count) entities.") }
    }
    if args == ["validate"] {
        for dataset in [try Pilot.make(), try StructureSamples.make(), try StructureSamples.make(revised: true), try CrossSubjectSamples.make()] {
            let issues = Validator.validate(dataset)
            guard issues.isEmpty else { throw CLIError.message(issues.map(\.description).joined(separator: "\n")) }
            print("Valid: \(dataset.release), \(dataset.entities.count) entities, \(dataset.relations.count) relations.")
        }
        return
    }
    if args.first == "export-cross-subjects" {
        let dataset = try CrossSubjectSamples.make()
        let issues = Validator.validate(dataset)
        guard issues.isEmpty else { throw CLIError.message(issues.map(\.description).joined(separator: "\n")) }
        try dataset.canonicalJSON().write(to: URL(fileURLWithPath: args[1]), options: .atomic)
        return
    }
    if args.first == "export-examples" {
        let datasets = [try StructureSamples.make(), try StructureSamples.make(revised: true)]
        for dataset in datasets {
            let issues = Validator.validate(dataset)
            guard issues.isEmpty else { throw CLIError.message(issues.map(\.description).joined(separator: "\n")) }
        }
        for dataset in datasets {
            let url = URL(fileURLWithPath: args[1]).appendingPathComponent(dataset.release + ".json")
            try dataset.canonicalJSON().write(to: url, options: .atomic)
        }
        return
    }
    let dataset = try Pilot.make()
    let issues = Validator.validate(dataset)
    guard issues.isEmpty else { throw CLIError.message(issues.map(\.description).joined(separator: "\n")) }
    try dataset.canonicalJSON().write(to: URL(fileURLWithPath: args[1]), options: .atomic)
}
enum CLIError: Error { case message(String) }
do { try run() } catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8)); exit(1)
}
