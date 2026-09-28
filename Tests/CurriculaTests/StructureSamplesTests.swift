import Foundation
import Testing
import Curricula
import CurriculaPilot

private func entity(_ data: Dataset, _ id: String) throws -> Entity {
    try #require(data.entities.first { $0.id == id })
}
private func relation(_ data: Dataset, _ id: String) throws -> Relation {
    try #require(data.relations.first { $0.id == id })
}
private func probes() throws -> [String: Any] {
    let url = try #require(Bundle.module.url(forResource: "unsupported", withExtension: "json"))
    return try #require(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
}

@Test func a01SharedTargetAcrossSchoolStages() throws {
    let d = try StructureSamples.make()
    let elementary = try relation(d, "al.elementary"), secondary = try relation(d, "al.secondary")
    #expect(elementary.to == secondary.to)
    #expect(try entity(d, elementary.from).frameworkID != entity(d, secondary.from).frameworkID)
    #expect(d.entities.filter { $0.id == elementary.to }.count == 1)
}
@Test func a02SameTargetDifferentConditions() throws {
    let d = try StructureSamples.make()
    let positive = try entity(d, "cp.link-positive"), signed = try entity(d, "cp.link-signed")
    #expect(positive.targetIDs == signed.targetIDs)
    #expect(positive.id != signed.id && positive.conditions != signed.conditions)
    #expect(positive.criteria != signed.criteria)
}
@Test func a03FunctionsRemainDistinctThroughJSON() throws {
    let d = try JSONDecoder().decode(Dataset.self, from: StructureSamples.make().canonicalJSON())
    let affine = try entity(d, "sm.affine"), linear = try entity(d, "sm.linear-map")
    #expect(affine.conditions.contains("b≠0"))
    #expect(linear.conditions.contains("実ベクトル空間") && linear.text.contains("加法とスカラー倍"))
    #expect(try relation(d, "kr.affine-linear").predicate == "contrasts")
    #expect(try entity(d, "cp.compare-functions").targetIDs.contains(affine.id))
    #expect(affine.provenance.origin == .synthetic)
}
@Test func a04InstitutionsShareKnowledgeWithoutDummyGrades() throws {
    let d = try StructureSamples.make()
    let a = try #require(d.frameworks.first { $0.id == "fw.university-a" })
    let b = try #require(d.frameworks.first { $0.id == "fw.university-b" })
    #expect(a.issuer != b.issuer && a.version != b.version)
    #expect(try relation(d, "al.university").to == relation(d, "al.university-b").to)
    let university = try entity(d, "fi.university-a")
    #expect(university.externalIDs.isEmpty)
    let json = try JSONSerialization.jsonObject(with: d.canonicalJSON()) as! [String: Any]
    let items = json["entities"] as! [[String: Any]]
    #expect(items.filter { ($0["id"] as? String)?.hasPrefix("fi.university") == true }.allSatisfy { $0["grade"] == nil })
    #expect(try entity(d, "fi.university-b-map").parentID == "fi.university-b-root")
}
@Test func a05PathsAndEnrollmentAreNotOneGlobalDAG() throws {
    var d = try StructureSamples.make()
    #expect(Validator.validate(d).isEmpty)
    let a = try relation(d, "dep.a-definition-example"), b = try relation(d, "dep.b-example-definition")
    #expect(a.from == b.to && a.to == b.from && a.contextID != b.contextID)
    let index = try #require(d.relations.firstIndex { $0.id == b.id })
    d.relations[index].contextID = a.contextID
    #expect(Validator.validate(d).contains { $0.code == "cycle" && $0.path == "dependencies[ctx.university-a]" })
    d = try StructureSamples.make()
    let enrollment = try #require(d.relations.firstIndex { $0.kind == .enrollment })
    d.relations[enrollment].kind = .dependency
    #expect(Validator.validate(d).contains { $0.code == "cycle" })
}
@Test func a06SyntheticSourcesExposeRequiredOfficialMetadataGap() throws {
    let sources = try #require(probes()["sourceDocuments"] as? [[String: Any]])
    #expect(Set(sources.compactMap { $0["kind"] as? String }) == ["referenceStandard", "syllabus"])
    #expect(Set(sources.compactMap { $0["publisher"] as? String }).count == 2)
    for source in sources {
        #expect(source["promulgated"] == nil && source["url"] == nil && source["sha256"] == nil)
        // Expected limitation, not a valid production import. No invented announcement date or URL.
        do {
            _ = try JSONDecoder().decode(SourceDocument.self, from: JSONSerialization.data(withJSONObject: source))
            Issue.record("A06 is now representable: update the catalog and replace this expected-gap probe")
        } catch DecodingError.keyNotFound(let key, _) {
            #expect(["url", "promulgated", "retrievedOn", "sha256"].contains(key.stringValue))
        }
    }
}
@Test func a07HomonymsDoNotMergeDefinitions() throws {
    let d = try StructureSamples.make()
    let a = try entity(d, "sm.naturals-zero"), b = try entity(d, "sm.naturals-positive")
    #expect(a.label == b.label && a.id != b.id)
    #expect(a.text != b.text && a.conditions != b.conditions)
    #expect(try relation(d, "kr.natural-conventions").predicate == "contrasts")
}
@Test func a08ModelApproximationAndTheoremConditionsSurvive() throws {
    let d = try JSONDecoder().decode(Dataset.self, from: StructureSamples.make().canonicalJSON())
    let model = try entity(d, "sm.gas-model"), theorem = try entity(d, "sm.right-triangle")
    #expect(model.category == "curricula-v1:model")
    #expect(theorem.category == "curricula-v1:theorem")
    #expect(model.conditions.contains("近似") && theorem.conditions.contains("直角三角形"))
    #expect(model.provenance.origin == .synthetic && theorem.provenance.origin == .synthetic)
}
@Test func a09ContrastingInterpretationsCanCoexist() throws {
    let d = try StructureSamples.make()
    let a = try entity(d, "sm.interpretation-a"), b = try entity(d, "sm.interpretation-b")
    #expect(a.label == b.label && a.id != b.id && a.conditions != b.conditions)
    #expect(try entity(d, "cp.discuss").targetIDs.sorted() == [a.id,b.id].sorted())
    #expect(Validator.validate(d).isEmpty)
}
@Test func a10LanguageAudienceAndRubricNeedNoSingleAnswer() throws {
    let d = try StructureSamples.make()
    let peer = try entity(d, "cp.language-peer"), visitor = try entity(d, "cp.language-visitor")
    #expect(peer.targetIDs == visitor.targetIDs && peer.conditions != visitor.conditions)
    #expect(peer.criteria != visitor.criteria)
    #expect(visitor.criteria.contains { $0.contains("複数") })
    #expect(peer.prerequisiteStatus == .uninvestigated)
}
@Test func a11BroadAttitudeGoalRemainsPartiallyCovered() throws {
    var d = try StructureSamples.make()
    let r = try relation(d, "al.attitude")
    #expect(try entity(d, r.from).criteria.isEmpty)
    #expect(r.coverage == .partial && r.excluded.contains { $0.contains("長期") })
    let index = try #require(d.relations.firstIndex { $0.id == r.id })
    d.relations[index].coverage = .full
    #expect(Validator.validate(d).contains { $0.code == "invalidCoverage" && $0.path == r.id })
}
@Test func a12SplitSnapshotsAndCandidateMappingRemainTraceable() throws {
    let old = try StructureSamples.make(), new = try StructureSamples.make(revised: true)
    #expect(old.release != new.release)
    #expect(old.entities.contains { $0.id == "fi.high-school-functions" })
    #expect(!new.entities.contains { $0.id == "fi.high-school-functions" })
    #expect(new.entities.contains { $0.id == "fi.high-school-formula" })
    #expect(new.entities.contains { $0.id == "fi.high-school-properties" })
    let mappings = try #require(probes()["revisionMappings"] as? [[String: Any]])
    for mapping in mappings {
        #expect(mapping["fromRelease"] as? String == old.release)
        #expect(mapping["toRelease"] as? String == new.release)
        let before = try #require(mapping["fromIDs"] as? [String]), after = try #require(mapping["toIDs"] as? [String])
        #expect(before.allSatisfy { id in old.entities.contains { $0.id == id } })
        #expect(after.allSatisfy { id in new.entities.contains { $0.id == id } })
        #expect(!(mapping["rationale"] as? String ?? "").isEmpty)
    }
    #expect(Validator.validate(old).isEmpty && Validator.validate(new).isEmpty)
    // Candidate mappings are a test resource, intentionally not claimed as the current exchange contract.
    let exported = try JSONSerialization.jsonObject(with: new.canonicalJSON()) as! [String: Any]
    #expect(exported["revisionMappings"] == nil)
}
@Test func a13AlternativeGroupsRemainAnExplicitGap() throws {
    var d = try StructureSamples.make()
    let probe = try #require(probes()["alternativeDependency"] as? [String: Any])
    let groups = try #require(probe["anyOf"] as? [[String]])
    #expect(groups.count == 2 && groups[0].count == 1 && groups[1].count == 2)
    #expect(groups.flatMap { $0 }.allSatisfy { id in d.entities.contains { $0.id == id && $0.kind == .competency } })
    let target = try #require(probe["to"] as? String)
    #expect(d.entities.contains { $0.id == target && $0.kind == .competency })
    d.relations.append(Relation(id: "dep.alternative-probe", kind: .dependency, from: groups[0][0], to: target,
                               contextID: "ctx.university-a", predicate: "prerequisite", strength: .alternative,
                               provenance: .init(.synthetic, rationale: probe["rationale"] as! String)))
    #expect(Validator.validate(d).contains { $0.code == "unsupportedAlternative" })
}
@Test func a14CodeChangeIsDifferentFromDefinitionChange() throws {
    let old = try StructureSamples.make(), new = try StructureSamples.make(revised: true)
    #expect(try entity(old, "fi.university-b-map").externalIDs != entity(new, "fi.university-b-map").externalIDs)
    #expect(try entity(old, "sm.linear-map") == entity(new, "sm.linear-map"))
    #expect(old.sources == new.sources) // No fabricated official source update.
    let prior = try entity(old, "sm.affine"), expanded = try entity(new, "sm.affine-expanded")
    #expect(prior.id != expanded.id && prior.conditions != expanded.conditions)
    #expect(try entity(new, prior.id) == prior)
}
@Test func outlinesAndInvestigationStatesDoNotChangeCoreMeaning() throws {
    let original = try StructureSamples.make()
    var edited = original
    edited.readingOutlines[0].sections.reverse()
    #expect(edited.entities == original.entities && edited.relations == original.relations)
    #expect(try entity(original, "cp.boundary").prerequisiteStatus == .scopedBoundary)
    #expect(try entity(original, "cp.multiply").prerequisiteStatus == .uninvestigated)
    #expect(!original.relations.contains { $0.kind == .dependency && $0.to == "cp.boundary" })
}
@Test func repertoireIsDeterministicAndEverySectionIsResolvable() throws {
    for revised in [false, true] {
        let d = try StructureSamples.make(revised: revised)
        #expect(Validator.validate(d).isEmpty)
        let decoded = try JSONDecoder().decode(Dataset.self, from: d.canonicalJSON())
        #expect(try decoded.canonicalJSON() == d.canonicalJSON())
        var shuffled = d
        shuffled.entities.reverse(); shuffled.relations.reverse(); shuffled.contexts.reverse()
        #expect(try shuffled.canonicalJSON() == d.canonicalJSON())
        #expect(d.readingOutlines[0].sections.count >= 6)
        let baselineIDs = Set(try Pilot.make().entities.map(\.id))
        #expect(d.entities.filter { !baselineIDs.contains($0.id) }.allSatisfy { $0.provenance.origin == .synthetic })
    }
}
