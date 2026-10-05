import Foundation

public enum ValidatorV2 {
    public static func validate(_ d: V2.Dataset, history: [V2.Dataset] = []) -> [ValidationIssue] {
        var issues: [ValidationIssue] = []
        func fail(_ code: String, _ path: String, _ message: String) { issues.append(.init(code: code, path: path, message: message)) }
        func uuid(_ value: String) -> Bool { UUID(uuidString: value)?.uuidString.lowercased() == value }
        let all = d.recordRefs
        let refs = Dictionary(all.map { ($0.id, $0.revisionID) }, uniquingKeysWith: { a, _ in a })
        let entities = Dictionary(d.entities.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        let entityIDs = Set(entities.keys)
        let quotations = d.evidence.filter { $0.field == .text && $0.role == .quotation }
        let quotedRefs = Set(quotations.filter { !$0.citations.isEmpty }.map(\.target))
        let quotationByTarget = Dictionary(quotations.map { ($0.target, $0) }, uniquingKeysWith: { a, _ in a })
        let sources = Dictionary(d.sources.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        let taxons = Dictionary(d.taxons.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        let contexts = Set(d.contexts.map(\.id)), frameworks = Set(d.frameworks.map(\.id))
        var ids = Set<String>(), revisions = Set<String>()
        for ref in all {
            if !uuid(ref.id) || !uuid(ref.revisionID) { fail("invalidUUID", ref.id, "Record and revision identifiers must be canonical UUIDs") }
            if !ids.insert(ref.id).inserted { fail("duplicateID", ref.id, "Duplicate record") }
            if !revisions.insert(ref.revisionID).inserted { fail("duplicateRevision", ref.id, "A revision belongs to one record") }
        }
        if !ids.isDisjoint(with: revisions) { fail("identityCollision", "records", "Record and revision UUIDs must be distinct") }
        if d.schemaVersion != "0.2.0" || d.release.isEmpty { fail("schemaVersion", "release", "Expected schema 0.2.0 and a release") }
        func reference(_ id: String, _ allowed: Set<String>, _ path: String) {
            if !allowed.contains(id) { fail("missingReference", path, id) }
        }
        func pinned(_ ref: V2.Ref, _ path: String) {
            if refs[ref.id] == nil { fail("missingReference", path, ref.id) }
            else if refs[ref.id] != ref.revisionID { fail("staleRevision", path, ref.id) }
        }
        func education(_ scopes: [V2.Education], _ path: String) {
            if Set(scopes).count != scopes.count { fail("duplicateScope", path, "Duplicate education scope") }
            for scope in scopes {
                if taxons[scope.subjectID]?.kind != .subject { fail("invalidSubject", path, scope.subjectID) }
                if let course = scope.courseID, taxons[course]?.kind != .course || taxons[course]?.parentID != scope.subjectID { fail("invalidCourse", path, course) }
                let maximum: Int? = scope.stage == .elementary ? 6 : [.lowerSecondary, .upperSecondary].contains(scope.stage) ? 3 : nil
                if scope.gradeStatus == .specified {
                    if scope.grades.isEmpty || Set(scope.grades).count != scope.grades.count || scope.grades.contains(where: { $0 < 1 || (maximum != nil && $0 > maximum!) }) {
                        fail("invalidGrades", path, "Specified grades must be a nonempty set within the school stage")
                    }
                } else if !scope.grades.isEmpty { fail("invalidGrades", path, "Unspecified/nonapplicable grades cannot contain values") }
            }
        }
        for (alias, id) in d.aliases {
            if alias.isEmpty || uuid(alias) { fail("invalidAlias", "aliases", alias) }
            reference(id, ids, "aliases." + alias)
        }
        for taxon in d.taxons {
            if taxon.label.isEmpty { fail("emptyLabel", taxon.id, "Taxon label required") }
            if taxon.kind == .course && taxon.parentID.flatMap({ taxons[$0]?.kind }) != .subject { fail("invalidCourse", taxon.id, "Course requires a subject") }
            if taxon.kind == .subject && taxon.parentID != nil { fail("invalidSubject", taxon.id, "Subject cannot be a course") }
        }
        for source in d.sources {
            if source.title.isEmpty || source.scope.isEmpty { fail("incompleteSource", source.id, "Title and scope required") }
            if let url = source.url, !["https", "http"].contains(URL(string: url)?.scheme ?? "") { fail("invalidURL", source.id, url) }
            if let hash = source.sha256, hash.range(of: "^[0-9a-f]{64}$", options: .regularExpression) == nil { fail("invalidHash", source.id, "Expected SHA-256") }
            if source.sha256 != nil && source.retrievedOn == nil { fail("missingAcquisition", source.id, "A captured artifact requires a retrieval date") }
            if source.origin == .synthetic && (source.promulgatedOn != nil || source.retrievedOn != nil || source.sha256 != nil) { fail("syntheticAcquisition", source.id, "Do not invent real acquisition or promulgation metadata") }
            if source.origin == .original && source.url == nil && source.identifiers.isEmpty && source.creators.isEmpty && source.publisher == nil { fail("incompleteSource", source.id, "Record a retrievable or bibliographic identity") }
        }
        for f in d.frameworks { education(f.education, f.id); for id in f.sourceIDs { reference(id, Set(sources.keys), f.id) } }
        for c in d.contexts { education(c.education, c.id); if let id = c.frameworkID { reference(id, frameworks, c.id) } }
        for e in d.entities {
            education(e.education, e.id)
            if e.label.isEmpty || e.text.isEmpty { fail("emptyEntity", e.id, "Keep a label and the goal/content text") }
            if let f = e.frameworkID { reference(f, frameworks, e.id) }
            if e.kind == .frameworkItem && e.frameworkID == nil { fail("missingFramework", e.id, "Framework required") }
            if let parentID = e.parentID {
                if let parent = entities[parentID] {
                    if e.kind != .frameworkItem || parent.kind != .frameworkItem || parent.frameworkID != e.frameworkID { fail("invalidParent", e.id, parentID) }
                } else { fail("missingReference", e.id, parentID) }
            }
            for target in e.targetIDs { if entities[target]?.kind != .subjectMatter { fail("invalidTarget", e.id, target) } }
            for successor in e.successorIDs { if entities[successor] == nil || successor == e.id { fail("invalidSuccessor", e.id, successor) } }
            if e.lifecycle == .active && !e.successorIDs.isEmpty { fail("invalidSuccessor", e.id, "Active record cannot have successors") }
            if e.kind == .frameworkItem && e.provenance.origin == .original && !quotedRefs.contains(e.ref) {
                fail("missingEvidence", e.id, "Original framework text requires a pinned quotation citation")
            }
        }
        for e in d.entities {
            for mode in ["parent", "successor"] {
                var active = Set<String>(), done = Set<String>()
                func visit(_ id: String) {
                    if active.contains(id) { fail("cycle", e.id, mode); return }
                    if done.contains(id) { return }; active.insert(id)
                    let next = mode == "parent" ? entities[id]?.parentID.map { [$0] } ?? [] : entities[id]?.successorIDs ?? []
                    for n in next { visit(n) }; active.remove(id); done.insert(id)
                }
                visit(e.id)
            }
        }
        var annotationPositions = Set<String>()
        for a in d.annotations {
            pinned(a.goal, a.id)
            if entities[a.goal.id]?.kind != .goal { fail("invalidAnnotationTarget", a.id, "Annotations attach to goals") }
            if a.text.isEmpty || a.position < 0 || !annotationPositions.insert(a.goal.id + ":" + String(a.position)).inserted { fail("invalidAnnotation", a.id, "Text and unique nonnegative position required") }
            // This release ships no automatic assessors. A label must never imply executable scoring.
            if a.evaluationMode == .software || a.evaluatorID != nil { fail("unavailableEvaluator", a.id, "No software assessor registered in 0.2.0; retain a natural-language annotation") }
        }
        for e in d.evidence {
            pinned(e.target, e.id)
            let entity = entities[e.target.id]
            let valid: Bool
            if entity != nil { valid = [.text, .conditions, .education].contains(e.field) }
            else if d.annotations.contains(where: { $0.id == e.target.id }) { valid = e.field == .text }
            else if d.relations.contains(where: { $0.id == e.target.id }) { valid = e.field == .coverage }
            else if d.prerequisites.contains(where: { $0.id == e.target.id }) { valid = e.field == .expression }
            else { valid = false }
            if !valid { fail("invalidEvidenceField", e.id, e.field.rawValue) }
            if e.citations.isEmpty || e.rationale.isEmpty { fail("incompleteEvidence", e.id, "Citations and reason required") }
            for c in e.citations {
                pinned(c.source, e.id)
                if sources[c.source.id] == nil || c.locator.isEmpty { fail("invalidCitation", e.id, "Source record and locator required") }
                if e.role == .quotation && entity?.provenance.origin == .original && sources[c.source.id]?.origin == .synthetic {
                    fail("syntheticSourceForOriginal", e.id, "Original text cannot claim an invented external source")
                }
                if let item = c.item {
                    pinned(item, e.id)
                    if entities[item.id]?.kind != .frameworkItem { fail("invalidCitationItem", e.id, item.id) }
                    let original = quotationByTarget[item]
                    if !((original?.citations ?? []).contains { $0.source == c.source && $0.locator == c.locator }) {
                        fail("citationSourceMismatch", e.id, "Cited item and captured source location disagree")
                    }
                }
            }
        }
        for r in d.relations {
            guard let from = entities[r.from], let to = entities[r.to] else { fail("missingReference", r.id, "Relation endpoint"); continue }
            if let c = r.contextID { reference(c, contexts, r.id) }
            switch r.kind {
            case .alignment:
                if from.kind != .frameworkItem || to.kind == .frameworkItem { fail("invalidEndpoints", r.id, "Alignment") }
                if r.coverage == nil || (r.coverage == .full && !r.excluded.isEmpty) || (r.coverage == .partial && r.excluded.isEmpty) { fail("invalidCoverage", r.id, "Partial coverage requires exclusions") }
            case .knowledge:
                if from.kind != .subjectMatter || to.kind != .subjectMatter { fail("invalidEndpoints", r.id, "Knowledge") }
            case .enrollment:
                if r.contextID == nil || from.kind != .goal || to.kind != .goal { fail("invalidEndpoints", r.id, "Enrollment requires goals and context") }
            }
        }
        let goals = Set(d.entities.filter { $0.kind == .goal }.map(\.id))
        for p in d.prerequisites {
            reference(p.targetGoalID, goals, p.id); reference(p.contextID, contexts, p.id)
            func check(_ expression: V2.Requirement, depth: Int = 0) {
                if depth > 64 { fail("expressionDepth", p.id, "Expression exceeds 64 levels"); return }
                if expression.op == .goal {
                    if let id = expression.goalID { reference(id, goals, p.id) } else { fail("invalidExpression", p.id, "Missing goal") }
                    if !expression.operands.isEmpty { fail("invalidExpression", p.id, "Leaf cannot have operands") }
                } else {
                    if expression.goalID != nil || expression.operands.count < 2 { fail("invalidExpression", p.id, "Groups need at least two operands and no leaf ID") }
                    for child in expression.operands { check(child, depth: depth + 1) }
                }
            }
            check(p.expression)
        }
        // Least fixed point preserves OR alternatives: a cyclic option with another reachable option is valid.
        for context in contexts {
            let rules = d.prerequisites.filter { $0.contextID == context && $0.strength == .required }
            let targets = Set(rules.map(\.targetGoalID))
            var reachable = goals.subtracting(targets)
            var changed = true
            while changed {
                changed = false
                for target in targets.subtracting(reachable) {
                    if rules.filter({ $0.targetGoalID == target }).allSatisfy({ $0.expression.isSatisfied(by: reachable) }) {
                        reachable.insert(target); changed = true
                    }
                }
            }
            if !targets.isSubset(of: reachable) { fail("unreachablePrerequisite", context, "No finite route for: " + targets.subtracting(reachable).sorted().joined(separator: ", ")) }
        }
        for outline in d.readingOutlines {
            if outline.label.isEmpty { fail("emptyOutline", outline.id, "Outline label required") }
            for section in outline.sections {
                for id in section.entityIDs { reference(id, entityIDs, section.id) }
            }
        }
        let snapshots = Dictionary((history + [d]).map { ($0.release, $0) }, uniquingKeysWith: { _, b in b })
        for c in d.changes {
            if c.rationale.isEmpty || c.before.isEmpty || c.after.isEmpty { fail("incompleteChange", c.id, "Keep endpoints and rationale") }
            for endpoint in c.before + c.after {
                if snapshots[endpoint.release]?.entities.contains(where: { $0.ref == endpoint.record }) != true { fail("missingChangeRevision", c.id, endpoint.release + ":" + endpoint.record.id) }
            }
            if Set(c.before.map(\.release)).count != 1 || Set(c.after.map(\.release)).count != 1 || c.before.first?.release == c.after.first?.release {
                fail("invalidChangeRelease", c.id, "One source and one distinct destination release required")
            }
            if c.kind != .edit, let destination = c.after.first?.release, let snapshot = snapshots[destination] {
                let successors = Set(c.after.map { $0.record.id })
                for endpoint in c.before {
                    if !snapshot.entities.contains(where: { $0.id == endpoint.record.id && $0.lifecycle == .retired && Set($0.successorIDs) == successors && $0.revisionID != endpoint.record.revisionID }) {
                        fail("missingRetirement", c.id, "Retain the old identity and explicit successors")
                    }
                }
            }
            let before = c.before.map { $0.record.id }, after = c.after.map { $0.record.id }
            if Set(before).count != before.count || Set(after).count != after.count { fail("duplicateChangeEndpoint", c.id, "Duplicate endpoints") }
            switch c.kind {
            case .edit:
                if before.count != 1 || before != after || c.before.first?.record.revisionID == c.after.first?.record.revisionID { fail("invalidEdit", c.id, "Edit keeps identity, changes revision") }
            case .split:
                if before.count != 1 || after.count < 2 || !Set(before).isDisjoint(with: after) { fail("invalidSplit", c.id, "Split requires one old and several new identities") }
            case .merge:
                if before.count < 2 || after.count != 1 || !Set(before).isDisjoint(with: after) { fail("invalidMerge", c.id, "Merge requires several old and one new identity") }
            }
        }
        // Reusing a revision for changed bytes would make citations and history untrustworthy.
        func encodedRecords(_ data: V2.Dataset) -> [String: Data] {
            guard let raw = try? data.canonicalJSON(), let object = try? JSONSerialization.jsonObject(with: raw) as? [String: Any] else { return [:] }
            var result: [String: Data] = [:]
            func add(_ record: [String: Any]) {
                if let id = record["revisionID"] as? String { result[id] = try? JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]) }
                if let sections = record["sections"] as? [[String: Any]] { for section in sections { add(section) } }
            }
            for value in object.values { if let records = value as? [[String: Any]] { for record in records { add(record) } } }
            return result
        }
        let current = encodedRecords(d)
        for old in history {
            for (revision, bytes) in encodedRecords(old) where current[revision] != nil && current[revision] != bytes {
                fail("mutatedRevision", revision, "Changed content needs a fresh revision UUID")
            }
        }
        return issues.sorted { ($0.path, $0.code, $0.message) < ($1.path, $1.code, $1.message) }
    }
}
