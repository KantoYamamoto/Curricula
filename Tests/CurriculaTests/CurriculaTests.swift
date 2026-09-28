import Foundation
import Testing
@testable import Curricula
import CurriculaPilot

@Test func pilotIsValidAndRoundTrips() throws {
    let data = try Pilot.make()
    #expect(Validator.validate(data).isEmpty)
    let decoded = try JSONDecoder().decode(Dataset.self, from: data.canonicalJSON())
    #expect(try decoded.canonicalJSON() == data.canonicalJSON())
    #expect(decoded.entities.first { $0.id == "fi.university-a" }?.externalIDs.isEmpty == true)
    #expect(decoded.relations.filter { $0.kind == .alignment }.allSatisfy { $0.coverage == .partial && !$0.excluded.isEmpty })
}
@Test func canonicalExportDoesNotDependOnDeclarationOrder() throws {
    let data = try Pilot.make()
    var reordered = data
    reordered.entities.reverse(); reordered.relations.reverse(); reordered.frameworks.reverse(); reordered.sources.reverse()
    #expect(try data.canonicalJSON() == reordered.canonicalJSON())
    reordered.entities[0].label = "変更した表示名"
    #expect(Set(data.entities.map(\.id)) == Set(reordered.entities.map(\.id)))
    reordered.readingOutlines[0].sections.reverse()
    #expect(reordered.relations == data.relations.reversed())
}
@Test func duplicateAndMissingReferencesAreReportedWithoutCrashing() throws {
    var data = try Pilot.make()
    data.entities.append(data.entities[0])
    data.relations[0].to = "missing.entity"
    let issues = Validator.validate(data)
    #expect(issues.contains { $0.code == "duplicateID" })
    #expect(issues.contains { $0.code == "missingReference" && $0.path == data.relations[0].id })
}
@Test func relationEndpointTypesAreChecked() throws {
    var data = try Pilot.make()
    data.relations[0].from = "sm.proportion"
    #expect(Validator.validate(data).contains { $0.code == "invalidEndpoints" })
}
@Test func requiredCyclesAreScopedToContext() throws {
    var data = try Pilot.make()
    let p = Provenance(.editorial, rationale: "テスト用の経路")
    data.relations.append(Relation(id: "dep.reverse", kind: .dependency, from: "cp.make-table", to: "cp.multiply", contextID: "ctx.signed", predicate: "prerequisite", strength: .required, provenance: p))
    #expect(!Validator.validate(data).contains { $0.code == "cycle" })
    data.relations[data.relations.count-1].contextID = "ctx.positive"
    #expect(Validator.validate(data).contains { $0.code == "cycle" && $0.message.contains("cp.multiply") && $0.message.contains("cp.make-table") })
    data.relations[data.relations.count-1].strength = .recommended
    #expect(!Validator.validate(data).contains { $0.code == "cycle" })
    data.relations[data.relations.count-1].kind = .enrollment
    data.relations[data.relations.count-1].strength = .required
    #expect(!Validator.validate(data).contains { $0.code == "cycle" })
}
@Test func knowledgeCyclesAndConflictingInterpretationsAreAllowed() throws {
    var data = try Pilot.make()
    var edge = try #require(data.relations.first { $0.id == "kr.interpretations" })
    edge.id = "kr.reverse"; swap(&edge.from, &edge.to)
    data.relations.append(edge)
    #expect(Validator.validate(data).isEmpty)
    #expect(data.entities.filter { $0.label == "歴史事象の解釈" }.count == 2)
}
@Test func alternativePathsAreExplicitlyUnsupported() throws {
    var data = try Pilot.make()
    let i = try #require(data.relations.firstIndex { $0.kind == .dependency })
    data.relations[i].strength = .alternative
    #expect(Validator.validate(data).contains { $0.code == "unsupportedAlternative" })
}
@Test func fullCoverageCannotHideExclusions() throws {
    var data = try Pilot.make()
    data.relations[0].coverage = .full
    #expect(Validator.validate(data).contains { $0.code == "invalidCoverage" })
}
@Test func hierarchyCyclesAndCrossFrameworkParentsAreRejected() throws {
    var data = try Pilot.make()
    let i = try #require(data.entities.firstIndex { $0.id == "fi.8350213311200000" })
    let j = try #require(data.entities.firstIndex { $0.id == "fi.8350213311400000" })
    data.entities[i].parentID = data.entities[j].id
    data.entities[j].parentID = data.entities[i].id
    #expect(Validator.validate(data).contains { $0.code == "cycle" && $0.path == "frameworkHierarchy" })
    data.entities[i].parentID = "fi.8250263311100000"
    #expect(Validator.validate(data).contains { $0.code == "invalidParent" })
}
@Test func originalTextRequiresSourceAndCompetencyRequiresConditions() throws {
    var data = try Pilot.make()
    data.entities[0].provenance.sourceIDs = []
    let i = try #require(data.entities.firstIndex { $0.kind == .competency })
    data.entities[i].conditions = ""
    let issues = Validator.validate(data)
    #expect(issues.contains { $0.code == "missingSource" })
    #expect(issues.contains { $0.code == "incompleteCompetency" })
}
