import Curricula

/// Deliberately small, synthetic probes. They are not institutional curricula.
/// Keep Pilot.make() and its published bytes unchanged.
public enum StructureSamples {
    public static func make(revised: Bool = false) throws -> Dataset {
        var data = try Pilot.make()
        data.release = revised ? "examples-0.2.0" : "examples-0.1.0"
        func evidence(_ reason: String) -> Provenance {
            .init(.synthetic, rationale: "構造検証用の合成例。" + reason)
        }
        func subject(_ id: String, _ label: String, _ text: String, _ conditions: String, _ category: String) -> Entity {
            Entity(id: id, kind: .subjectMatter, label: label, text: text, conditions: conditions,
                   provenance: evidence("名称ではなく定義・条件・IDで区別する。"), category: "curricula-v1:" + category)
        }
        func skill(_ id: String, _ label: String, _ targets: [String], _ conditions: String, _ criteria: [String], status: Investigation = .uninvestigated) -> Entity {
            Entity(id: id, kind: .competency, label: label, text: label, conditions: conditions,
                   provenance: evidence("相手・目的・条件・達成観点を保存する。自動採点を前提にしない。"),
                   targetIDs: targets, criteria: criteria, prerequisiteStatus: status)
        }
        func item(_ id: String, _ label: String, _ framework: String, parent: String? = nil) -> Entity {
            Entity(id: id, kind: .frameworkItem, label: label, text: label,
                   provenance: evidence("実在機関の要求の引用ではない。"), frameworkID: framework, parentID: parent)
        }
        func align(_ id: String, _ from: String, _ to: String, _ context: String, excluded: [String] = []) -> Relation {
            Relation(id: id, kind: .alignment, from: from, to: to, contextID: context, predicate: "covers",
                     coverage: excluded.isEmpty ? .full : .partial, excluded: excluded,
                     provenance: evidence("この架空項目の明示した範囲だけに対応する。"))
        }
        func edge(_ id: String, _ from: String, _ to: String, _ context: String, _ kind: RelationKind = .dependency, _ strength: Strength = .required) -> Relation {
            Relation(id: id, kind: kind, from: from, to: to, contextID: context, predicate: kind == .enrollment ? "enrollmentRule" : "prerequisite", strength: strength,
                     provenance: evidence(kind == .enrollment ? "A機関の順序指定。学習上の必須前提とは主張しない。" : "明示した学習経路だけの前提。別経路には一般化しない。"))
        }
        data.frameworks += [
            Framework(id: "fw.high-school-sample", label: "高校・関数（合成例）", issuer: "架空高校", version: "2026", origin: .synthetic),
            Framework(id: "fw.university-b", label: "架空大学B・言語と数理", issuer: "架空大学B", version: "2027", origin: .synthetic),
            Framework(id: "fw.inquiry", label: "科学・歴史・語学の探究（合成例）", issuer: "架空の教材編集者", version: "1", origin: .synthetic)
        ]
        data.contexts += [
            Context(id: "ctx.school-functions", label: "高校・関数を比較する経路", conditions: "実数上の関数。全国の必修要求を示す例ではない。", frameworkID: "fw.high-school-sample"),
            Context(id: "ctx.university-a", label: "A大学・2026年度・定義から計算へ", conditions: "架空の履修規則と学習経路。", frameworkID: "fw.university-a"),
            Context(id: "ctx.university-b", label: "B大学・2027年度・計算例から定義へ", conditions: "A大学とは別経路。", frameworkID: "fw.university-b"),
            Context(id: "ctx.inquiry", label: "史料比較・説明活動", conditions: "相手・目的を指定した架空の探究活動。", frameworkID: "fw.inquiry")
        ]
        data.entities += [
            subject("sm.affine", "一次関数", "f(x)=ax+b で表される関数。", "a≠0、x∈R。この例は b≠0 に限定し、線形写像と同一視しない。", "concept"),
            subject("sm.naturals-zero", "自然数", "この立場では {0,1,2,…} と定める。", "0を含むという定義上の約束。", "definition"),
            subject("sm.naturals-positive", "自然数", "この立場では {1,2,3,…} と定める。", "0を含まないという定義上の約束。", "definition"),
            subject("sm.gas-model", "理想気体モデル", "気体の状態を pV=nRT で記述するモデル。", "理想化された粒子像を仮定する。実在気体への近似の適否は条件の検討が必要。", "model"),
            subject("sm.right-triangle", "三平方の定理", "直角を挟む辺をa,b、斜辺をcとすると a²+b²=c²。", "ユークリッド平面の直角三角形、a,b,c>0。", "theorem"),
            subject("sm.audience-explanation", "相手に応じた説明", "語彙・具体例・説明順を相手の知識と目的に応じて選ぶ。", "一つの正解文に固定しない。", "communication"),
            item("fi.high-school-functions", "関数の式と性質を比較する", "fw.high-school-sample"),
            item("fi.university-b-root", "数理と言語の教養", "fw.university-b"),
            item("fi.university-b-map", "線形写像の具体例を説明する", "fw.university-b", parent: "fi.university-b-root"),
            item("fi.inquiry-root", "探究と表現", "fw.inquiry"),
            item("fi.inquiry-attitude", "異なる立場に関心を持ち、根拠を吟味しながら学び続ける", "fw.inquiry", parent: "fi.inquiry-root"),
            item("fi.language", "目的と相手に応じて外国語で説明する", "fw.inquiry", parent: "fi.inquiry-root"),
            skill("cp.compare-functions", "比例と一次関数を比較する", ["sm.proportion", "sm.affine"], "実数上の f(x)=2x と g(x)=2x+1。", ["原点の像と一定の差に注目し、同じ関数ではないと説明する。"]),
            skill("cp.map-definition", "線形写像の定義を説明する", ["sm.linear-map"], "実ベクトル空間、加法とスカラー倍の保存。", ["二つの保存条件を述べる。"]),
            skill("cp.map-example", "具体的な写像を調べる", ["sm.linear-map"], "R→Rの f(x)=3x。", ["加法とスカラー倍を保存することを式で確かめる。"]),
            skill("cp.model-limits", "モデルの適用条件を説明する", ["sm.gas-model"], "理想気体を仮定した計算と実測のずれについて話し合う。", ["近似モデルと無条件の法則を区別する。"]),
            skill("cp.language-peer", "外国語で同級生に道順を説明する", ["sm.audience-explanation"], "学校を知る同級生、校門から図書室への道順、英語。", ["既知の目印を使い、必要な順序を説明する。"]),
            skill("cp.language-visitor", "外国語で初訪問者に道順を説明する", ["sm.audience-explanation"], "学校を初めて訪れる人、校門から図書室への道順、英語。", ["校内の略称を説明し、理解を確かめる。", "複数の適切な表現を認める。"]),
            skill("cp.boundary", "正の整数の積を求める（調査境界の例）", ["sm.multiplication"], "構造検証のため一桁の正の整数に範囲を限定する。", ["指定した積を求める。"], status: .scopedBoundary)
        ]
        // Bibliographic references for the non-elementary concepts used by these probes.
        for (id, reference) in [
            ("sm.gas-model", "モデルと近似条件の根拠: OpenStax, University Physics Volume 2, §2.1 https://openstax.org/books/university-physics-volume-2/pages/2-1-molecular-model-of-an-ideal-gas"),
            ("cp.model-limits", "近似条件の根拠: OpenStax, University Physics Volume 2, §2.1 https://openstax.org/books/university-physics-volume-2/pages/2-1-molecular-model-of-an-ideal-gas"),
            ("sm.linear-map", "定義の根拠: W. Keith Nicholson, Linear Algebra with Applications, §2.6 https://math.libretexts.org/Bookshelves/Linear_Algebra/Linear_Algebra_with_Applications_(Nicholson)/02%3A_Matrix_Algebra/2.06%3A_Linear_Transformations")
        ] {
            if let index = data.entities.firstIndex(where: { $0.id == id }) {
                data.entities[index].provenance.rationale += " " + reference
            }
        }
        data.relations += [
            align("al.high-school", "fi.high-school-functions", "cp.compare-functions", "ctx.school-functions"),
            align("al.university-b", "fi.university-b-map", "sm.linear-map", "ctx.university-b", excluded: ["具体例の説明能力そのもの"]),
            align("al.attitude", "fi.inquiry-attitude", "cp.discuss", "ctx.inquiry", excluded: ["関心や態度の全体", "継続して学ぶ姿勢の長期的な観察"]),
            align("al.language-peer", "fi.language", "cp.language-peer", "ctx.inquiry", excluded: ["初訪問者への説明", "道順以外の目的"]),
            align("al.language-visitor", "fi.language", "cp.language-visitor", "ctx.inquiry", excluded: ["同級生への説明", "道順以外の目的"]),
            edge("dep.a-definition-example", "cp.map-definition", "cp.map-example", "ctx.university-a"),
            edge("dep.b-example-definition", "cp.map-example", "cp.map-definition", "ctx.university-b"),
            edge("enroll.a-example-definition", "cp.map-example", "cp.map-definition", "ctx.university-a", .enrollment),
            edge("dep.inquiry-peer-visitor", "cp.language-peer", "cp.language-visitor", "ctx.inquiry", .dependency, .recommended),
            edge("dep.inquiry-visitor-peer", "cp.language-visitor", "cp.language-peer", "ctx.inquiry", .dependency, .recommended),
            Relation(id: "kr.affine-linear", kind: .knowledge, from: "sm.affine", to: "sm.linear-map", predicate: "contrasts", provenance: evidence("定数項b≠0の条件を消して統合しない。")),
            Relation(id: "kr.natural-conventions", kind: .knowledge, from: "sm.naturals-zero", to: "sm.naturals-positive", predicate: "contrasts", provenance: evidence("用語が同じでも定義域の約束が異なる。"))
        ]
        data.readingOutlines = [ReadingOutline(id: "reading.structure", label: "データ構造の小標本", sections: [
            ReadingSection(id: "sample.school", label: "学校段階と対象の共有", entityIDs: ["sm.proportion", "cp.link-positive", "cp.link-signed", "cp.compare-functions"]),
            ReadingSection(id: "sample.institution", label: "機関・年度・学習経路", entityIDs: ["fi.university-a", "fi.university-b-map", "cp.map-definition", "cp.map-example"]),
            ReadingSection(id: "sample.definitions", label: "同名の定義と異なる条件", entityIDs: ["sm.naturals-zero", "sm.naturals-positive", "sm.affine", "sm.linear-map"]),
            ReadingSection(id: "sample.science", label: "近似モデルと定理", entityIDs: ["sm.gas-model", "cp.model-limits", "sm.right-triangle"]),
            ReadingSection(id: "sample.humanities", label: "立場・語学・広い目標", entityIDs: ["sm.interpretation-a", "sm.interpretation-b", "cp.discuss", "cp.language-peer", "cp.language-visitor", "fi.inquiry-attitude"]),
            ReadingSection(id: "sample.boundary", label: "未調査と調査境界", entityIDs: ["cp.multiply", "cp.boundary"])
        ])]
        data.limitations = [
            "構造検証用。追加した学校・大学・科学・歴史・語学の例はすべて合成例。比例の公式4項目だけは出典付き原文。",
            "資料種別と出典なしの合成資料、AND/OR、分割・定義変更の移行関係には中核モデルの不足がある。docs/sample-catalog.mdの期待結果を参照。",
            "scopedBoundaryは今回の探索の停止点であり、前提が数学的に存在しないという意味ではない。",
            "enrollmentの端点は能力であり、コース・単位・履修管理は未対応。"
        ]
        if revised {
            // A12/A14: retain the old snapshot; candidate mapping is a separate fixture, not a supported core field.
            data.entities.removeAll { $0.id == "fi.high-school-functions" }
            data.entities += [
                item("fi.high-school-formula", "関数の式を比較する", "fw.high-school-sample"),
                item("fi.high-school-properties", "関数の性質を比較する", "fw.high-school-sample"),
                subject("sm.affine-expanded", "アフィン関数", "f(x)=ax+b で表される関数。", "x∈R、a,b∈R。a=0とb=0も含める。旧例と定義条件が異なるため別ID。", "concept")
            ]
            data.relations.removeAll { $0.id == "al.high-school" }
            data.relations += [
                align("al.high-school-formula", "fi.high-school-formula", "cp.compare-functions", "ctx.school-functions", excluded: ["比較対象の関数全般"]),
                align("al.high-school-properties", "fi.high-school-properties", "cp.compare-functions", "ctx.school-functions", excluded: ["比較対象の関数全般"])
            ]
            // Only synthetic framework/code versions change. Official source snapshots remain untouched.
            let frameworkIndex = data.frameworks.firstIndex { $0.id == "fw.high-school-sample" }!
            data.frameworks[frameworkIndex].version = "2027-synthetic"
            let itemIndex = data.entities.firstIndex { $0.id == "fi.university-b-map" }!
            data.entities[itemIndex].externalIDs = ["synthetic:university-b:2027": "MAP-NEW"]
            data.readingOutlines[0].sections.append(ReadingSection(id: "sample.revision", label: "項目分割と定義の変更", entityIDs: ["fi.high-school-formula", "fi.high-school-properties", "sm.affine", "sm.affine-expanded"]))
        } else {
            let itemIndex = data.entities.firstIndex { $0.id == "fi.university-b-map" }!
            data.entities[itemIndex].externalIDs = ["synthetic:university-b:2027": "MAP-OLD"]
        }
        return data
    }
}
