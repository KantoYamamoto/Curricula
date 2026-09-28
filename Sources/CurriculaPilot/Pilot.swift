import Foundation
import Curricula

public enum Pilot {
    struct PinnedInput: Decodable {
        var sources: [SourceDocument]
        var items: [Item]
        struct Item: Decodable { var code: String; var text: String; var sourceID: String; var locator: String; var frameworkID: String }
    }
    public static func make() throws -> Dataset {
        guard let url = Bundle.module.url(forResource: "mext-sample", withExtension: "json") else { throw CocoaError(.fileNoSuchFile) }
        let pinned = try JSONDecoder().decode(PinnedInput.self, from: Data(contentsOf: url))
        let authored = Provenance(.editorial, rationale: "v0.3の小標本を検証するためのAI下書き。教育上の妥当性は未レビュー。")
        let synthetic = Provenance(.synthetic, rationale: "構造検証専用の架空例。実在する機関の到達目標ではない。")
        var entities = pinned.items.map { item in
            Entity(id: "fi." + item.code, kind: .frameworkItem, label: item.text, text: item.text,
                   provenance: .init(.original, sources: [item.sourceID], rationale: "公式コード表の当該行を改変せず抽出。"),
                   frameworkID: item.frameworkID, externalIDs: ["mext:course-of-study": item.code], sourceLocator: item.locator)
        }
        entities += [
            Entity(id: "sm.proportion", kind: .subjectMatter, label: "比例関係", text: "二つの数量x、yの関係が、一定の係数aを用いて y = ax と表される。",
                   conditions: "この小標本では a ≠ 0。扱う数の範囲と単位は各能力で指定する。x = 0 では y/x を計算しない。", provenance: authored, category: "curricula-v1:concept"),
            Entity(id: "sm.table", kind: .subjectMatter, label: "対応表", text: "同じ組に属する二つの量を行または列で対応付けて示す表。", provenance: authored, category: "curricula-v1:representation"),
            Entity(id: "sm.multiplication", kind: .subjectMatter, label: "乗法と倍", text: "一定の単価と個数から代金を求める場面で用いる乗法。", conditions: "今回は正の整数。小数・分数は未収録。", provenance: authored, category: "curricula-v1:procedure"),
            Entity(id: "sm.linear-map", kind: .subjectMatter, label: "線形写像", text: "加法とスカラー倍を保つ写像。", conditions: "実ベクトル空間。R→Rの f(x)=ax は一例。b≠0 の ax+b と同一視しない。", provenance: synthetic, category: "curricula-v1:concept"),
            Entity(id: "sm.interpretation-a", kind: .subjectMatter, label: "歴史事象の解釈", text: "経済条件を重視する架空の解釈。", conditions: "構造検証用の立場A。史実の主張ではない。", provenance: synthetic, category: "curricula-v1:interpretation"),
            Entity(id: "sm.interpretation-b", kind: .subjectMatter, label: "歴史事象の解釈", text: "制度の変化を重視する架空の解釈。", conditions: "構造検証用の立場B。Aと同名でも別対象。", provenance: synthetic, category: "curricula-v1:interpretation")
        ]
        func competency(_ id: String, _ label: String, _ conditions: String, _ criteria: [String], targets: [String] = ["sm.proportion"], status: Investigation = .uninvestigated) -> Entity {
            Entity(id: id, kind: .competency, label: label, text: label, conditions: conditions, provenance: authored,
                   targetIDs: targets, criteria: criteria, prerequisiteStatus: status)
        }
        entities += [
            competency("cp.multiply", "一定の単価と個数から代金を求める", "単価120円、正の整数の個数。割引はない。", ["3個の代金を360円と求め、単位を示す。"], targets: ["sm.multiplication"]),
            competency("cp.read-table", "比例する二量の表から対応する値を読む", "比例関係が与えられた正の数量。個数と代金の単位を明示。", ["3個に対応する360円を読み、量を取り違えない。"], targets: ["sm.proportion", "sm.table"]),
            competency("cp.explain", "比例の関係を数量の変化で説明する", "一定の単価120円。正の整数の個数。", ["個数を2倍にすると代金も2倍になる理由を説明する。"]),
            competency("cp.make-table", "比例の式から表を作る", "y=120x、xは1,2,3。xは個数、yは円。", ["対応するyを120,240,360と表に記す。"]),
            competency("cp.link-positive", "正の数量の比例を表・式・グラフで関連付ける", "y=120x、xは正の整数。個数の間を連続量とみなさない。", ["式・表・点の座標で同じ対応を示す。"]),
            competency("cp.link-signed", "負の値も含む比例を表・式・座標で関連付ける", "y=-2x、実数の定義域。標本x=-1,0,1。", ["(-1,2),(0,0),(1,-2)を対応付け、全体のグラフが原点を通る直線であると説明する。"]),
            competency("cp.nonexample", "比例しない関係を反例で説明する", "実数上で規則y=2x+1が与えられている。", ["x=0でy=1となるためy=axでは表せないと説明する。", "有限個の観測だけで全定義域の比例を証明したとしない。"]),
            competency("cp.apply", "比例とみなす条件を確認し数量を求める", "単価120円で追加料金・割引がない場合と、固定送料がある場合を比べる。", ["固定送料がある代金全体には、そのまま比例を適用しない。"])
        ]
        entities += [
            Entity(id: "fi.university-a", kind: .frameworkItem, label: "写像の性質を説明する（合成例）", text: "架空の到達目標。", provenance: synthetic, frameworkID: "fw.university-a"),
            Entity(id: "cp.discuss", kind: .competency, label: "根拠を挙げて二つの解釈を比較する", text: "目的と相手に応じて比較を説明する。", conditions: "架空の史料を複数提示する討論場面。", provenance: synthetic,
                   targetIDs: ["sm.interpretation-a", "sm.interpretation-b"], criteria: ["各立場の根拠と限界を示す。単一の正解文は要求しない。"], prerequisiteStatus: .uninvestigated)
        ]
        var relations = [Relation]()
        func align(_ id: String, _ code: String, _ target: String, _ excluded: [String]) {
            relations.append(Relation(id: id, kind: .alignment, from: "fi." + code, to: target, predicate: "covers",
                                      coverage: .partial, excluded: excluded, provenance: authored))
        }
        align("al.elementary", "8250263311100000", "sm.proportion", ["性質の体系的な説明と理解の評価は未収録"])
        align("al.secondary", "8350213311200000", "sm.proportion", ["反比例"])
        align("al.represent", "8350213311400000", "cp.link-positive", ["反比例", "負の数を含む範囲"])
        align("al.signed", "8350213311400000", "cp.link-signed", ["反比例"])
        align("al.explain", "8350213312100000", "cp.explain", ["反比例", "一般的な変化や対応の考察"])
        relations += [
            Relation(id: "dep.multiply-table", kind: .dependency, from: "cp.multiply", to: "cp.make-table", contextID: "ctx.positive", predicate: "prerequisite", strength: .required,
                     provenance: .init(.editorial, rationale: "単価×個数で各値を計算する今回の経路に限定。学習順一般の主張ではない。")),
            Relation(id: "dep.table-link", kind: .dependency, from: "cp.read-table", to: "cp.link-positive", contextID: "ctx.positive", predicate: "prerequisite", strength: .recommended, provenance: authored),
            Relation(id: "kr.proportion-linear", kind: .knowledge, from: "sm.proportion", to: "sm.linear-map", predicate: "related", provenance: synthetic),
            Relation(id: "kr.interpretations", kind: .knowledge, from: "sm.interpretation-a", to: "sm.interpretation-b", predicate: "contrasts", provenance: synthetic),
            Relation(id: "al.university", kind: .alignment, from: "fi.university-a", to: "sm.linear-map", predicate: "covers", coverage: .partial, excluded: ["証明の能力"], provenance: synthetic)
        ]
        return Dataset(release: "pilot-0.1.0", sources: pinned.sources, frameworks: [
            Framework(id: "fw.elementary-2017", label: "小学校算数・第6学年（抜粋）", issuer: "文部科学省", version: "2017", sourceIDs: ["src.mext-82v12"]),
            Framework(id: "fw.secondary-2017", label: "中学校数学・第1学年（抜粋）", issuer: "文部科学省", version: "2017", sourceIDs: ["src.mext-83v11"]),
            Framework(id: "fw.university-a", label: "架空大学A・教養課程", issuer: "架空大学A", version: "2026", origin: .synthetic)
        ], contexts: [
            Context(id: "ctx.positive", label: "正の数量・単価による経路", conditions: "単価120円、正の整数の個数。", frameworkID: "fw.elementary-2017"),
            Context(id: "ctx.signed", label: "符号を含む比例", conditions: "実数上の y=-2x。", frameworkID: "fw.secondary-2017")
        ], entities: entities, relations: relations, readingOutlines: [
            ReadingOutline(id: "reading.proportion", label: "比例をたどる", sections: [
                ReadingSection(id: "section.meaning", label: "数量の対応と比例", entityIDs: ["sm.proportion", "cp.read-table", "cp.explain"]),
                ReadingSection(id: "section.table", label: "表と式", entityIDs: ["sm.table", "cp.make-table", "cp.multiply"]),
                ReadingSection(id: "section.graph", label: "座標とグラフ", entityIDs: ["cp.link-positive", "cp.link-signed"]),
                ReadingSection(id: "section.conditions", label: "つながりと適用条件", entityIDs: ["cp.nonexample", "cp.apply"])
            ])
        ], limitations: ["AI下書き・内容レビュー前。機械検証は教育上の妥当性を保証しない。", "原典階層の全件取り込み、本文PDF・訂正票・LOD照合は未完了。", "小学校までの前提経路は未調査。空の前提一覧は基礎到達を意味しない。", "AND/OR代替経路、旧版からの分割・統合移行は未実装。", "高校・大学・異分野の全構造検証例は未完了。合成例を実在の要件と扱わない。"])
    }
}
