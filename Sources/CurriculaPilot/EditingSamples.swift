import Foundation
import Curricula

public enum EditingSamples {
    public static func make() throws -> V2.Dataset {
        let registry = try IdentityRegistry()
        func ref(_ key: String) throws -> V2.Ref { try registry.ref(key) }
        var d = V2.Dataset(release: "editing-0.2.0")
        d.taxons = [try .init(ref("subject.editing"), kind: .subject, label: "編集操作の例")]
        d.contexts = [try .init(ref("ctx.editing"), label: "AND/ORの操作例", conditions: "論理式と参照の検証に用いる合成経路。")]
        for (key, label) in [("a", "経路A"), ("b", "経路Bの前半"), ("c", "経路Bの後半"), ("target", "二つの経路で到達する目標"),
                             ("combined", "説明と図示を行う"), ("left", "資料を読む"), ("right", "資料を比較する")] {
            let e = V2.Entity(try ref("goal.editing." + key), kind: .goal, label: label, text: label,
                              provenance: .init(.synthetic, "目標の編集、分割、統合、前提の論理式を確認するための入力。"))
            d.entities.append(e)
        }
        func goal(_ key: String) throws -> V2.Requirement { .init(goalID: try ref("goal.editing." + key).id) }
        d.prerequisites = [try .init(ref("requirement.alternatives"), targetGoalID: ref("goal.editing.target").id,
                                    contextID: ref("ctx.editing").id, strength: .required,
                                    expression: .init(.anyOf, [goal("a"), .init(.allOf, [goal("b"), goal("c")])]),
                                    provenance: .init(.synthetic, "A、またはBとCの両方。辺を三本に分解せず選択肢のまとまりを保つ。"))]
        for (key, kind, title, scope) in [
            ("src.synthetic-reference", V2.SourceKind.referenceStandard, "架空学会の参照基準", "教養教育の検討に使う助言。"),
            ("src.synthetic-syllabus", V2.SourceKind.syllabus, "架空大学の授業シラバス", "2027年度の特定授業。")
        ] {
            var source = V2.Source(try ref(key), kind: kind, origin: .synthetic, title: title, scope: scope)
            source.publisher = "架空の発行者"; d.sources.append(source)
        }
        var book = V2.Source(try ref("src.book-openstax"), kind: .book, origin: .original,
                             title: "University Physics Volume 2", scope: "§2.1 Molecular Model of an Ideal Gas。書誌参照の例。")
        book.publisher = "OpenStax / Rice University"
        book.url = "https://openstax.org/books/university-physics-volume-2/pages/2-1-molecular-model-of-an-ideal-gas"
        d.sources.append(book)
        d.readingOutlines = [try .init(ref("reading.editing"), label: "編集と前提経路の操作例", sections: [
            .init(ref("section.editing"), label: "目標とAND/OR経路", entityIDs: d.entities.map(\.id))
        ])]
        let used = Set(d.recordRefs.map(\.id)); d.aliases = registry.entries.filter { used.contains($0.value.id) }.mapValues(\.id)
        d.limitations = ["合成した操作例。A06の資料種別とA13のAND/ORを正式なスキーマで扱う。"]
        return d
    }
    public static func revisions() throws -> [V2.Dataset] {
        let registry = try IdentityRegistry(); let base = try make()
        func original(_ key: String, in d: V2.Dataset) throws -> V2.Entity {
            let id = try registry.ref(key).id
            guard let entity = d.entities.first(where: { $0.id == id }) else { throw NSError(domain: "MissingEditEntity", code: 1) }; return entity
        }
        var edited = try original("goal.editing.a", in: base)
        edited.revisionID = try registry.ref("goal.editing.a", "2").revisionID
        edited.label = "経路A（説明を補足）"; edited.text = "経路Aを満たす。注記の文言を編集した例。"
        let edit = try EditorV2.apply(to: base, nextRelease: "editing-0.2.1", kind: .edit, expected: [original("goal.editing.a", in: base).ref],
                                      replacements: [edited], change: registry.ref("change.edit"), rationale: "同じ目標の文言修正。IDを維持し編集版を更新。")
        let combined = try original("goal.editing.combined", in: edit)
        let pieces = try [("goal.editing.edited", "説明を行う"), ("goal.editing.merged", "図示を行う")].map { key, label in
            V2.Entity(try registry.ref(key), kind: .goal, label: label, text: label, provenance: .init(.synthetic, "説明と図示を分けて編集する。"))
        }
        let split = try EditorV2.apply(to: edit, nextRelease: "editing-0.2.2", kind: .split, expected: [combined.ref], replacements: pieces,
                                       retiredRevisions: [combined.id: registry.ref("goal.editing.combined", "2").revisionID],
                                       change: registry.ref("change.split"), rationale: "説明と図示の目標を分割。旧IDは廃止状態と後継を保持。", history: [base])
        let left = try original("goal.editing.left", in: split), right = try original("goal.editing.right", in: split)
        let merged = V2.Entity(try registry.ref("goal.editing.split-merged"), kind: .goal, label: "資料を読んで比較する", text: "資料を読み、比較する。", provenance: .init(.synthetic, "関連する二つの目標を統合した操作例。"))
        let merge = try EditorV2.apply(to: split, nextRelease: "editing-0.2.3", kind: .merge, expected: [left.ref, right.ref], replacements: [merged],
                                       retiredRevisions: [left.id: registry.ref("goal.editing.left", "2").revisionID, right.id: registry.ref("goal.editing.right", "2").revisionID],
                                       change: registry.ref("change.merge"), rationale: "二つの目標を一つへ統合し、両方の旧IDから追跡する。", history: [base, edit])
        return [base, edit, split, merge].map { original in
            var d = original
            let used = Set(d.recordRefs.map(\.id))
            d.aliases = registry.entries.filter { used.contains($0.value.id) }.mapValues(\.id)
            return d
        }
    }
}
