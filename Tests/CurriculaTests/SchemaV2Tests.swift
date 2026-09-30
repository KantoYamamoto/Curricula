import Foundation
import Testing
import Curricula
import CurriculaPilot

private func record(_ d: V2.Dataset, _ alias: String) throws -> V2.Entity {
    let id = try #require(d.aliases[alias]); return try #require(d.entities.first { $0.id == id })
}
private func randomRef() -> V2.Ref { .init(UUID().uuidString.lowercased(), UUID().uuidString.lowercased()) }

@Test func v2RoundTripStableUUIDsAndOriginalText() throws {
    let d = try StructuredSamples.make(), again = try StructuredSamples.make()
    #expect(ValidatorV2.validate(d).isEmpty)
    #expect(try d.canonicalJSON() == again.canonicalJSON())
    #expect(try JSONDecoder().decode(V2.Dataset.self, from: d.canonicalJSON()).canonicalJSON() == d.canonicalJSON())
    for ref in d.recordRefs { #expect(UUID(uuidString: ref.id) != nil && UUID(uuidString: ref.revisionID) != nil && ref.id != ref.revisionID) }
    for e in try CrossSubjectSamples.make().entities {
        let new = try record(d, e.id)
        #expect(new.text == e.text && new.externalIDs == e.externalIDs)
        #expect(new.id != e.id)
    }
    var reordered = d; reordered.entities.reverse(); reordered.evidence.reverse(); reordered.annotations.reverse()
    #expect(try reordered.canonicalJSON() == d.canonicalJSON())
}

@Test func v2GradeBandsAndCoursesAreDedicatedAttributes() throws {
    let d = try StructuredSamples.make()
    #expect(try record(d, "cp.cross-japanese-early").education[0].grades == [1, 2])
    #expect(try record(d, "cp.cross-japanese-middle").education[0].grades == [3, 4])
    #expect(try record(d, "sm.character-reading").education.count == 2)
    let info = try record(d, "cp.cross-information-build").education[0]
    #expect(info.stage == .upperSecondary && info.gradeStatus == .notSpecified && info.grades.isEmpty)
    #expect(info.courseID == d.aliases["course.information"])
    #expect(try record(d, "fi.84i0000000000000").education[0].courseID == nil)
    #expect(try record(d, "cp.cross-language-write").education[0].courseID == d.aliases["course.language"])
    #expect(try record(d, "fi.8210000000000000").education[0].gradeStatus == .notSpecified)
    var bad = d
    let index = try #require(bad.entities.firstIndex { $0.kind == .goal })
    bad.entities[index].education[0].grades = [99]; bad.entities[index].education[0].gradeStatus = .specified
    #expect(ValidatorV2.validate(bad).contains { $0.code == "invalidGrades" })
    bad = d; bad.entities[index].education[0].courseID = d.aliases["course.information"]
    if bad.entities[index].education[0].subjectID != d.aliases["subject.information"] {
        #expect(ValidatorV2.validate(bad).contains { $0.code == "invalidCourse" })
    }
}

@Test func v2EvidencePinsFieldsAnnotationsAndSourceLocations() throws {
    let d = try StructuredSamples.make()
    let science = try record(d, "cp.cross-science-inquiry")
    let condition = try #require(d.evidence.first { $0.target == science.ref && $0.field == .conditions })
    #expect(condition.citations.contains { $0.item?.id == d.aliases["fi.8260253120000000"] })
    let note = try #require(d.annotations.first { $0.goal == science.ref })
    #expect(d.evidence.contains { $0.target.id == note.id && $0.field == .text })
    var bad = d
    bad.evidence[0].target.revisionID = UUID().uuidString.lowercased()
    #expect(ValidatorV2.validate(bad).contains { $0.code == "staleRevision" })
    bad = d
    let index = try #require(bad.evidence.firstIndex { $0.citations.contains { $0.item != nil } })
    bad.evidence[index].citations[0].locator = "unrelated location"
    #expect(ValidatorV2.validate(bad).contains { $0.code == "citationSourceMismatch" })
    bad = d; bad.evidence[index].field = .expression
    #expect(ValidatorV2.validate(bad).contains { $0.code == "invalidEvidenceField" })
}

@Test func v2GoalsSurviveWithoutScoringOrAnnotations() throws {
    let d = try StructuredSamples.make()
    let moral = try record(d, "goal.cross-ethics")
    #expect(moral.kind == .goal && moral.text.contains("誰に対しても"))
    #expect(!d.annotations.contains { $0.goal.id == moral.id })
    #expect(d.relations.contains { $0.to == moral.id && $0.coverage == .full })
    #expect(d.annotations.allSatisfy { $0.evaluationMode == .unspecified && $0.evaluatorID == nil })
    var bad = d; bad.annotations[0].evaluationMode = .software
    #expect(ValidatorV2.validate(bad).contains { $0.code == "unavailableEvaluator" })
    bad = d; bad.annotations[0].evaluationMode = .humanObservation
    #expect(ValidatorV2.validate(bad).isEmpty)
}

@Test func v2SourceKindsDoNotRequireInventedPromulgationOrRetrieval() throws {
    let d = try EditingSamples.make()
    #expect(ValidatorV2.validate(d).isEmpty)
    #expect(Set(d.sources.map(\.kind)) == [.book, .syllabus, .referenceStandard])
    #expect(d.sources.allSatisfy { $0.promulgatedOn == nil && $0.sha256 == nil && $0.retrievedOn == nil })
    var offlineBook = d.sources.first { $0.kind == .book }!
    offlineBook.url = nil; offlineBook.identifiers = ["ISBN": "bibliographic-fixture"]
    var copy = d; copy.sources[copy.sources.firstIndex { $0.kind == .book }!] = offlineBook
    #expect(ValidatorV2.validate(copy).isEmpty)
    let index = copy.sources.firstIndex { $0.origin == .synthetic }!
    copy.sources[index].promulgatedOn = "2027"
    #expect(ValidatorV2.validate(copy).contains { $0.code == "syntheticAcquisition" })
}

@Test func v2PrerequisiteAlternativesPreserveBooleanMeaning() throws {
    let d = try EditingSamples.make(); let expression = d.prerequisites[0].expression
    let a = try record(d, "goal.editing.a").id, b = try record(d, "goal.editing.b").id, c = try record(d, "goal.editing.c").id
    #expect(expression.isSatisfied(by: [a]))
    #expect(expression.isSatisfied(by: [b, c]))
    #expect(!expression.isSatisfied(by: [b]) && !expression.isSatisfied(by: [c]) && !expression.isSatisfied(by: []))
    #expect(try JSONDecoder().decode(V2.Dataset.self, from: d.canonicalJSON()).prerequisites == d.prerequisites)
}

@Test func v2CyclesWithAnAlternativeEscapeAreNotFlattenedIntoInvalidDAGs() throws {
    var d = try EditingSamples.make()
    let a = try record(d, "goal.editing.a").id, target = try record(d, "goal.editing.target").id
    let cycle = V2.Prerequisite(randomRef(), targetGoalID: a, contextID: d.contexts[0].id, strength: .required,
                                expression: .init(goalID: target), provenance: .init(.synthetic, "Cycle with a B-and-C escape"))
    d.prerequisites.append(cycle)
    #expect(ValidatorV2.validate(d).isEmpty)
    d.prerequisites[0].expression = .init(goalID: a)
    #expect(ValidatorV2.validate(d).contains { $0.code == "unreachablePrerequisite" })
    d.prerequisites[1].strength = .recommended
    #expect(ValidatorV2.validate(d).isEmpty)
    d.prerequisites[1].strength = .required
    let other = V2.Context(randomRef(), label: "Other route", conditions: "Separate context")
    d.contexts.append(other); d.prerequisites[1].contextID = other.id
    #expect(ValidatorV2.validate(d).isEmpty)
}

@Test func v2MalformedRequirementsFailWithoutSilentlyDroppingLogic() throws {
    var d = try EditingSamples.make()
    d.prerequisites[0].expression = .init(.anyOf, [])
    #expect(ValidatorV2.validate(d).contains { $0.code == "invalidExpression" })
    d = try EditingSamples.make(); d.prerequisites[0].expression = .init(goalID: randomRef().id)
    #expect(ValidatorV2.validate(d).contains { $0.code == "missingReference" })
}

@Test func v2EditSplitMergeKeepIdentityHistoryAndOldSnapshots() throws {
    let snapshots = try EditingSamples.revisions()
    for d in snapshots { #expect(ValidatorV2.validate(d, history: snapshots.filter { $0.release != d.release }).isEmpty) }
    let original = try record(snapshots[0], "goal.editing.a"), edited = try record(snapshots[1], "goal.editing.a")
    #expect(original.id == edited.id && original.revisionID != edited.revisionID && original.text != edited.text)
    let splitOld = try record(snapshots[2], "goal.editing.combined")
    #expect(splitOld.lifecycle == .retired && splitOld.successorIDs.count == 2)
    let left = try record(snapshots[3], "goal.editing.left"), right = try record(snapshots[3], "goal.editing.right")
    #expect(left.lifecycle == .retired && right.lifecycle == .retired && left.successorIDs == right.successorIDs)
    #expect(snapshots[3].changes.map(\.kind) == [.edit, .split, .merge])
    #expect(try record(snapshots[0], "goal.editing.combined").lifecycle == .active)
}

@Test func v2OptimisticEditingRejectsStaleInputAndReusedRevision() throws {
    let snapshots = try EditingSamples.revisions(), base = snapshots[0], newer = snapshots[1]
    let old = try record(base, "goal.editing.a")
    var replacement = old; replacement.revisionID = randomRef().revisionID
    do {
        _ = try EditorV2.apply(to: newer, nextRelease: "test-stale", kind: .edit, expected: [old.ref], replacements: [replacement], change: randomRef(), rationale: "Stale input", history: [base])
        Issue.record("Stale edit was accepted")
    } catch EditorV2.EditError.conflict(let id) { #expect(id == old.id) }
    var bad = base; bad.entities[0].text += "mutated"
    #expect(ValidatorV2.validate(bad, history: [base]).contains { $0.code == "mutatedRevision" })
}

@Test func v2EditingWithPinnedAnnotationsRequiresExplicitUpdates() throws {
    let base = try StructuredSamples.make(), goal = try record(base, "cp.cross-language-write")
    var changed = goal; changed.revisionID = randomRef().revisionID; changed.label += "（文言編集）"
    do {
        _ = try EditorV2.apply(to: base, nextRelease: "test-edit", kind: .edit, expected: [goal.ref], replacements: [changed], change: randomRef(), rationale: "Text edit")
        Issue.record("Stale evidence was accepted")
    } catch EditorV2.EditError.invalidDataset(let issues) { #expect(issues.contains { $0.code == "staleRevision" }) }
    let notes = base.annotations.filter { $0.goal == goal.ref }.map { old in
        var n = old; n.revisionID = randomRef().revisionID; n.goal = changed.ref; return n
    }
    let evidence = base.evidence.filter { evidence in evidence.target == goal.ref || notes.contains { $0.id == evidence.target.id } }.map { old in
        var e = old; e.revisionID = randomRef().revisionID
        e.target = e.target.id == goal.id ? changed.ref : V2.Ref(e.target.id, notes.first { $0.id == e.target.id }!.revisionID)
        return e
    }
    let result = try EditorV2.apply(to: base, nextRelease: "test-edit", kind: .edit, expected: [goal.ref], replacements: [changed], change: randomRef(), rationale: "Explicit pin update", annotationUpdates: notes, evidenceUpdates: evidence)
    #expect(ValidatorV2.validate(result, history: [base]).isEmpty)
}
