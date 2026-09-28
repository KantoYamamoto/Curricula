import Foundation
import Curricula
import CurriculaPilot

func run() throws {
    let args = Array(CommandLine.arguments.dropFirst())
    guard args == ["validate"] || (args.count == 2 && ["export", "export-examples", "export-cross-subjects"].contains(args[0])) else {
        throw CLIError.message("Usage: curricula validate | curricula export <output.json> | curricula export-examples <directory> | curricula export-cross-subjects <output.json>")
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
