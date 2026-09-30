import Foundation
import Curricula

public struct IdentityRegistry {
    public struct Entry: Decodable { public var id: String; public var revisions: [String: String] }
    public let entries: [String: Entry]
    public init() throws {
        let url = Bundle.module.url(forResource: "identity-registry", withExtension: "json")!
        entries = try JSONDecoder().decode([String: Entry].self, from: Data(contentsOf: url))
    }
    public func ref(_ key: String, _ version: String = "1") throws -> V2.Ref {
        guard let record = entries[key], let revision = record.revisions[version] else {
            throw NSError(domain: "IdentityRegistry", code: 1, userInfo: [NSLocalizedDescriptionKey: "Allocate and persist UUIDs for \(key) revision \(version) before export"])
        }
        return .init(record.id, revision)
    }
}

public enum StructuredSamples {
    struct Plan: Decodable {
        struct Taxon: Decodable { var key: String; var kind: V2.TaxonKind; var label: String; var parent: String? }
        struct Evidence: Decodable { var key: String; var target: String; var field: V2.EvidenceField; var codes: [String]; var quotation: Bool }
        var taxons: [Taxon]
        var frameworkEducation: [String: [V2.Education]]
        var contextEducation: [String: [V2.Education]]
        var entityEducation: [String: [V2.Education]]
        var evidence: [Evidence]
    }
    public static func make() throws -> V2.Dataset {
        let old = try CrossSubjectSamples.make(), registry = try IdentityRegistry()
        let planURL = Bundle.module.url(forResource: "v2-authoring", withExtension: "json")!
        let plan = try JSONDecoder().decode(Plan.self, from: Data(contentsOf: planURL))
        let input = try CrossSubjectSamples.input()
        let originals = Dictionary(uniqueKeysWithValues: input.items.map { ($0.code, $0) })
        var d = V2.Dataset(release: "cross-subject-0.2.0")
        func ref(_ key: String) throws -> V2.Ref { try registry.ref(key) }
        func id(_ key: String) throws -> String { try ref(key).id }
        func scopes(_ values: [V2.Education]) throws -> [V2.Education] {
            try values.map { scope in
                var copy = scope; copy.subjectID = try id(scope.subjectID); copy.courseID = try scope.courseID.map(id); return copy
            }
        }
        d.taxons = try plan.taxons.map { .init(try ref($0.key), kind: $0.kind, label: $0.label, parentID: try $0.parent.map(id)) }
        d.sources = try old.sources.map { old in
            var source = V2.Source(try ref(old.id), kind: .curriculum, origin: .original, title: old.title, scope: "選定した教科の学習指導要領。原文の版は配布CSVで固定。")
            source.publisher = old.publisher; source.url = old.url; source.promulgatedOn = old.promulgated; source.edition = old.distributionVersion
            source.retrievedOn = old.retrievedOn; source.sha256 = old.sha256; source.verification = old.verification; return source
        }
        d.frameworks = try old.frameworks.map { f in
            .init(try ref(f.id), label: f.label, issuer: f.issuer, version: f.version, sourceIDs: try f.sourceIDs.map(id), origin: f.origin, education: try scopes(plan.frameworkEducation[f.id] ?? []))
        }
        d.contexts = try old.contexts.map { c in
            .init(try ref(c.id), label: c.label, conditions: c.conditions, frameworkID: try c.frameworkID.map(id), education: try scopes(plan.contextEducation[c.id] ?? []))
        }
        d.entities = try old.entities.map { old in
            var e = V2.Entity(try ref(old.id), kind: old.kind == .competency ? .goal : old.kind == .frameworkItem ? .frameworkItem : .subjectMatter,
                              label: old.label, text: old.text, provenance: .init(old.provenance.origin, old.provenance.rationale))
            e.conditions = old.conditions; e.education = try scopes(plan.entityEducation[old.id] ?? [])
            e.frameworkID = try old.frameworkID.map(id); e.parentID = try old.parentID.map(id); e.externalIDs = old.externalIDs
            e.sourceLocator = old.sourceLocator; e.targetIDs = try old.targetIDs.map(id); e.category = old.category; e.prerequisiteStatus = old.prerequisiteStatus
            for (index, text) in old.criteria.enumerated() {
                d.annotations.append(.init(try ref("note.\(old.id).\(index + 1)"), goal: e.ref, text: text, position: index,
                                           provenance: .init(.editorial, "原典の要求から切り出した判定の観点。判定方法の選定は目標と独立に扱う。")))
            }
            return e
        }
        var ethics = V2.Entity(try ref("goal.cross-ethics"), kind: .goal, label: "誰に対しても思いやりをもち、相手の立場に立って親切にする",
                               text: "誰に対しても思いやりの心をもち，相手の立場に立って親切にすること。", provenance: .init(.editorial, "原典の態度目標を目標として保持。判定の観点が未設定でも登録できる。"))
        ethics.education = try scopes(plan.entityEducation["goal.cross-ethics"] ?? [])
        ethics.targetIDs = [try id("sm.consideration")]; ethics.prerequisiteStatus = .uninvestigated; d.entities.append(ethics)
        d.relations = try old.relations.map { old in
            var r = V2.Relation(try ref(old.id), kind: .alignment, from: try id(old.from), to: try id(old.to), predicate: old.predicate,
                                provenance: .init(old.provenance.origin, old.provenance.rationale))
            r.contextID = try old.contextID.map(id); r.coverage = old.coverage; r.excluded = old.excluded; return r
        }
        var moral = V2.Relation(try ref("al.cross-ethics-goal"), kind: .alignment, from: try id("fi.82k04d0213000000"), to: ethics.id,
                                predicate: "covers", provenance: .init(.editorial, "原文の目標全体を保持。自動判定の可否と対応範囲を分ける。"))
        moral.coverage = .full; moral.contextID = try id("ctx.cross-ethics"); d.relations.append(moral)
        d.evidence = try plan.evidence.map { spec in
            let citations = try spec.codes.map { code -> V2.Citation in
                guard let original = originals[code] else { throw NSError(domain: "UnknownSourceCode", code: 1) }
                return .init(source: try ref(original.sourceID), locator: original.locator,
                             item: spec.quotation ? nil : try ref(CrossSubjectSamples.itemID(code)))
            }
            return .init(try ref(spec.key), target: try ref(spec.target), field: spec.field, role: spec.quotation ? .quotation : .supports,
                         citations: citations, rationale: spec.quotation ? "配布原文と一致する抽出箇所。" : "指定した記述・条件・注釈・対応範囲を根拠項目の版に結び付ける。")
        }
        d.readingOutlines = try old.readingOutlines.map { outline in
            .init(try ref(outline.id), label: outline.label, sections: try outline.sections.map { section in
                var ids = try section.entityIDs.map(id)
                if section.id == "section.cross-ethics" { ids.append(ethics.id) }
                return .init(try ref(section.id), label: section.label, entityIDs: ids)
            })
        }
        let used = Set(d.recordRefs.map(\.id))
        d.aliases = registry.entries.filter { used.contains($0.value.id) }.mapValues(\.id)
        d.limitations = ["選定した8教科・11例を収録。", "前提の学習経路はこの原典標本では追加していない。AND/ORと編集操作は別の操作例に収録。", "目標と判定の観点を分離。自動採点器は未登録。"]
        return d
    }
}
