import Foundation
import Curricula
import CurriculaPilot

func run() throws {
    let args = Array(CommandLine.arguments.dropFirst())
    guard args == ["validate"] || (args.count == 2 && args[0] == "export") else {
        throw CLIError.message("Usage: curricula validate | curricula export <output.json>")
    }
    let dataset = try Pilot.make()
    let issues = Validator.validate(dataset)
    guard issues.isEmpty else { throw CLIError.message(issues.map(\.description).joined(separator: "\n")) }
    if args[0] == "export" {
        try dataset.canonicalJSON().write(to: URL(fileURLWithPath: args[1]), options: .atomic)
    } else {
        print("Valid: \(dataset.release), \(dataset.entities.count) entities, \(dataset.relations.count) relations. Content remains draft.")
    }
}
enum CLIError: Error { case message(String) }
do { try run() } catch {
    FileHandle.standardError.write(Data("\(error)\n".utf8)); exit(1)
}
