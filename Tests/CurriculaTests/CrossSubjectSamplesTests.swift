import Foundation
import Testing
import Curricula
import CurriculaPilot

private func crossEntity(_ data: Dataset, _ id: String) throws -> Entity {
    try #require(data.entities.first { $0.id == id })
}

@Test func crossSubjectOriginalRowsAndExplicitPathsSurviveExchange() throws {
    let input = try CrossSubjectSamples.input()
    let original = try CrossSubjectSamples.make()
    let d = try JSONDecoder().decode(Dataset.self, from: original.canonicalJSON())
    #expect(Validator.validate(d).isEmpty)
    #expect(d.frameworks.count == 8 && input.cases.count == 11 && input.items.count == 69)
    #expect(d.entities.count == 89 && d.relations.count == 13)
    #expect(d.sources == original.sources)
    for item in input.items {
        let e = try crossEntity(d, CrossSubjectSamples.itemID(item.code))
        #expect(e.text == item.text && e.sourceLocator == item.locator)
        #expect(e.externalIDs["mext:course-of-study"] == item.code)
        #expect(e.parentID == item.parentCode.map(CrossSubjectSamples.itemID))
        #expect(e.provenance.origin == .original && e.provenance.sourceIDs == [item.sourceID])
    }
    for sample in input.cases {
        for path in sample.paths {
            for (parent, child) in zip(path, path.dropFirst()) {
                #expect(try crossEntity(d, CrossSubjectSamples.itemID(child)).parentID == CrossSubjectSamples.itemID(parent))
            }
        }
    }
    #expect(try crossEntity(d, "fi.82k04d0213000000").parentID == "fi.82k0400210000000")
    #expect(try crossEntity(d, "fi.82h12d0000000000").parentID == "fi.82h02d0000000000")
    #expect(try crossEntity(d, "fi.8260250000000000").parentID == "fi.82602l0000000000")
    #expect(d.relations.allSatisfy { $0.kind == .alignment })
    #expect(try d.canonicalJSON() == original.canonicalJSON())
}

@Test func crossSubjectGradeConditionsDoNotCollapseSharedKnowledge() throws {
    let d = try CrossSubjectSamples.make()
    let early = try crossEntity(d, "cp.cross-japanese-early")
    let middle = try crossEntity(d, "cp.cross-japanese-middle")
    #expect(early.targetIDs == middle.targetIDs)
    #expect(early.conditions != middle.conditions && early.criteria != middle.criteria)
    #expect(middle.conditions.contains("叙述"))
    let listen = try crossEntity(d, "cp.cross-language-listen")
    let write = try crossEntity(d, "cp.cross-language-write")
    #expect(listen.targetIDs == write.targetIDs)
    #expect(listen.conditions.contains("ゆっくりはっきり"))
    #expect(write.conditions.contains("例文") && write.conditions.contains("音声で十分に慣れ親しんだ"))
}

@Test func crossSubjectInquiryAndPerformanceKeepEvidenceAndMultipleCriteria() throws {
    let d = try CrossSubjectSamples.make()
    let inquiry = try crossEntity(d, "cp.cross-science-inquiry")
    #expect(inquiry.targetIDs.count == 2)
    #expect(inquiry.conditions.contains("条件制御"))
    #expect(inquiry.provenance.rationale.contains("8260253120000000"))
    let music = try crossEntity(d, "cp.cross-music")
    #expect(music.provenance.rationale.contains("82802D3123000000"))
    #expect(music.criteria.joined().contains("聴きながら"))
    let history = try crossEntity(d, "cp.cross-history")
    #expect(history.criteria.count == 2 && history.criteria.joined().contains("多面的・多角的"))
    #expect(d.entities.filter { $0.provenance.origin == .editorial }.allSatisfy { !$0.provenance.sourceIDs.isEmpty })
}

@Test func crossSubjectBroadMoralGoalIsPreservedWithoutInventedScoring() throws {
    let d = try CrossSubjectSamples.make()
    let e = try crossEntity(d, "fi.82k04d0213000000")
    #expect(e.text.contains("誰に対しても") && e.text.contains("\n"))
    let section = try #require(d.readingOutlines[0].sections.first { $0.id == "section.cross-ethics" })
    #expect(section.entityIDs.count == 2)
    #expect(!d.entities.contains { section.entityIDs.contains($0.id) && $0.kind == .competency })
    let alignment = try #require(d.relations.first { $0.id == "al.cross-ethics-target" })
    #expect(alignment.coverage == .partial && !alignment.excluded.isEmpty)
}

@Test func crossSubjectManyToManyMappingsKeepTheirActualCoverage() throws {
    var d = try CrossSubjectSamples.make()
    let data = d.relations.filter { $0.to == "cp.cross-data" }
    #expect(data.count == 2 && Set(data.map(\.from)).count == 2)
    #expect(data.first { $0.from == "fi.8250233411100000" }?.coverage == .full)
    #expect(data.first { $0.from == "fi.8250233412100000" }?.excluded == ["グラフを用いた考察"])
    let info = d.relations.filter { $0.from == "fi.84i1503322000000" }
    #expect(info.count == 2 && Set(info.map(\.to)).count == 2)
    #expect(info.allSatisfy { $0.coverage == .partial && !$0.excluded.isEmpty })
    let index = try #require(d.relations.firstIndex { $0.id == "al.cross-information-build-0" })
    d.relations[index].coverage = .full
    #expect(Validator.validate(d).contains { $0.code == "invalidCoverage" })
}

@Test func crossSubjectInvalidHierarchyAndMissingTargetsAreRejected() throws {
    var d = try CrossSubjectSamples.make()
    let index = try #require(d.entities.firstIndex { $0.id == "fi.82k04d0213000000" })
    d.entities[index].parentID = "fi.82102a3231200000"
    #expect(Validator.validate(d).contains { $0.code == "invalidParent" })
    d = try CrossSubjectSamples.make()
    d.entities[index].parentID = d.entities[index].id
    #expect(Validator.validate(d).contains { $0.code == "cycle" })
    d = try CrossSubjectSamples.make()
    d.entities.removeAll { $0.id == "sm.familiar-language" }
    #expect(Validator.validate(d).contains { $0.code == "missingReference" })
}
