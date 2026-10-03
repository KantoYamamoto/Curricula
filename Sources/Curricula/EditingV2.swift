import Foundation

/// A local editing primitive. Persistence and authorization belong to the editing API.
public enum EditorV2 {
    public enum EditError: Error, Equatable { case conflict(String), invalidChange(String), invalidDataset([ValidationIssue]) }
    public static func apply(to original: V2.Dataset, nextRelease: String, kind: V2.ChangeKind, expected: [V2.Ref],
                             replacements: [V2.Entity], retiredRevisions: [String: String] = [:], change: V2.Ref,
                             rationale: String, history: [V2.Dataset] = [], annotationUpdates: [V2.Annotation] = [], evidenceUpdates: [V2.Evidence] = []) throws -> V2.Dataset {
        guard !nextRelease.isEmpty, nextRelease != original.release, !history.contains(where: { $0.release == nextRelease }), !rationale.isEmpty else { throw EditError.invalidChange("New release and reason required") }
        for ref in expected {
            guard original.entities.contains(where: { $0.ref == ref && $0.lifecycle == .active }) else { throw EditError.conflict(ref.id) }
        }
        let oldIDs = expected.map(\.id), newIDs = replacements.map(\.id)
        guard !oldIDs.isEmpty, !newIDs.isEmpty, Set(oldIDs).count == oldIDs.count, Set(newIDs).count == newIDs.count,
              replacements.allSatisfy({ $0.lifecycle == .active && $0.successorIDs.isEmpty }) else { throw EditError.invalidChange("Unique active endpoints required") }
        switch kind {
        case .edit:
            guard oldIDs.count == 1, oldIDs == newIDs, expected[0].revisionID != replacements[0].revisionID else { throw EditError.invalidChange("Edit preserves ID with a fresh revision") }
        case .split:
            guard oldIDs.count == 1, newIDs.count >= 2, Set(oldIDs).isDisjoint(with: newIDs) else { throw EditError.invalidChange("Split needs new identities") }
        case .merge:
            guard oldIDs.count >= 2, newIDs.count == 1, Set(oldIDs).isDisjoint(with: newIDs) else { throw EditError.invalidChange("Merge needs a new identity") }
        }
        if kind != .edit && replacements.contains(where: { replacement in original.entities.contains { $0.id == replacement.id } }) { throw EditError.invalidChange("Replacement identity already exists") }
        var d = original; d.release = nextRelease
        if kind == .edit {
            d.entities.removeAll { oldIDs.contains($0.id) }
        } else {
            for index in d.entities.indices where oldIDs.contains(d.entities[index].id) {
                guard let revision = retiredRevisions[d.entities[index].id], revision != d.entities[index].revisionID else { throw EditError.invalidChange("Retirement requires a fresh revision") }
                d.entities[index].revisionID = revision; d.entities[index].lifecycle = .retired; d.entities[index].successorIDs = newIDs
            }
        }
        d.entities += replacements
        // Updates are explicit and validated as one publication transaction. Stale pins fail below.
        for annotation in annotationUpdates {
            d.annotations.removeAll { $0.id == annotation.id }; d.annotations.append(annotation)
        }
        for evidence in evidenceUpdates {
            d.evidence.removeAll { $0.id == evidence.id }; d.evidence.append(evidence)
        }
        d.changes.append(.init(change, kind: kind, before: expected.map { .init(release: original.release, record: $0) },
                               after: replacements.map { .init(release: nextRelease, record: $0.ref) }, rationale: rationale))
        let issues = ValidatorV2.validate(d, history: history + [original])
        guard issues.isEmpty else { throw EditError.invalidDataset(issues) }
        return d
    }
}
