import Foundation
import Curricula

/// Real curriculum excerpts selected for structural variety, independent of the proportionality pilot.
public enum CrossSubjectSamples {
    public struct Input: Decodable {
        public var sources: [SourceDocument]
        public var frameworks: [Framework]
        public var items: [Item]
        public var cases: [Case]
        public struct Item: Decodable {
            public var code: String
            public var text: String
            public var sourceID: String
            public var locator: String
            public var frameworkID: String
            public var parentCode: String?
        }
        public struct Case: Decodable {
            public var id: String
            public var label: String
            public var context: String
            public var version: String
            public var frameworkID: String
            public var leafCodes: [String]
            public var paths: [[String]]
        }
    }
    public static func input() throws -> Input {
        guard let url = Bundle.module.url(forResource: "cross-subjects", withExtension: "json") else { throw CocoaError(.fileNoSuchFile) }
        return try JSONDecoder().decode(Input.self, from: Data(contentsOf: url))
    }
    public static func itemID(_ code: String) -> String { "fi." + code.lowercased() }
    public static func make() throws -> Dataset {
        let pinned = try input()
        let byCode = Dictionary(uniqueKeysWithValues: pinned.items.map { ($0.code, $0) })
        var entities = pinned.items.map { item in
            Entity(id: itemID(item.code), kind: .frameworkItem, label: item.text, text: item.text,
                   provenance: .init(.original, sources: [item.sourceID], rationale: "文部科学省のコード表から当該行をそのまま抽出。"),
                   frameworkID: item.frameworkID, parentID: item.parentCode.map(itemID),
                   externalIDs: ["mext:course-of-study": item.code], sourceLocator: item.locator)
        }
        var relations = [Relation]()
        var sections = [ReadingSection]()
        func evidence(_ codes: [String], _ reason: String) -> Provenance {
            .init(.editorial, sources: Array(Set(codes.compactMap { byCode[$0]?.sourceID })).sorted(),
                  rationale: "根拠項目: " + codes.joined(separator: ", ") + "。" + reason)
        }
        func matter(_ id: String, _ label: String, _ text: String, _ codes: [String], category: String = "concept") {
            entities.append(Entity(id: id, kind: .subjectMatter, label: label, text: text,
                                   provenance: evidence(codes, "原典で扱う対象を、能力と分けて整理。"), category: "curricula-v1:" + category))
        }
        matter("sm.character-reading", "登場人物の行動と気持ち", "物語の場面、登場人物の行動や気持ちを読む対象として扱う。", ["82102A3231200000", "82102C3231200000"])
        matter("sm.pendulum", "振り子の運動", "振り子が1往復する時間と、おもりの重さや振り子の長さなどの条件との関係。", ["8260253120000000", "8260253121100000"])
        matter("sm.control-conditions", "条件を制御して調べる方法", "予想や仮説を基に、調べる条件とそろえる条件を考えて方法を組み立てる。", ["8260253120000000", "8260253122000000"], category: "procedure")
        matter("sm.local-history", "地域の歴史と資料", "地域に残る文化財や諸資料と、地域の歴史的な特徴。", ["8322203122100000"])
        matter("sm.familiar-language", "身近な事柄を表す英語", "自分のことや身近で簡単な事柄を表す、簡単な語句や基本的な表現。", ["82H12D2110000000", "82H12D2520000000"])
        matter("sm.ensemble", "各声部と全体の響き", "各声部の楽器の音、全体の響き、伴奏と、自分の演奏との関わり。", ["82802D3123300000"], category: "musicalExpression")
        matter("sm.consideration", "親切・思いやり", "相手の立場に立って親切にすること。", ["82K04D0213000000"], category: "value")
        matter("sm.data-organization", "データの分類と表現", "日時や場所などの観点で整理したデータと、その表やグラフによる表現。", ["8250233411100000", "8250233412100000"], category: "representation")
        matter("sm.algorithm-process", "アルゴリズムと改善過程", "目的に応じたアルゴリズムの表現、プログラミング、その過程の評価と改善。", ["84I1503322000000"], category: "procedure")

        func skill(_ caseID: String, _ suffix: String = "", _ label: String, targets: [String], conditions: String,
                   criteria: [String], excluded: [String] = []) {
            let sample = pinned.cases.first { $0.id == caseID }!
            let id = "cp.cross-" + caseID + suffix
            let p = evidence(sample.paths.flatMap { $0 }.filter { code in
                sample.leafCodes.contains(code) || code == "8260253120000000" || code == "82802D3123000000"
            }, "原典の行為・条件を能力の記述へ分けた。達成観点は原典の要求に対応する確認事項。")
            entities.append(Entity(id: id, kind: .competency, label: label, text: label, conditions: conditions,
                                   provenance: p, targetIDs: targets, criteria: criteria, prerequisiteStatus: .uninvestigated))
            for (index, code) in sample.leafCodes.enumerated() {
                relations.append(Relation(id: "al.cross-" + caseID + suffix + "-" + String(index), kind: .alignment,
                                          from: itemID(code), to: id, contextID: "ctx.cross-" + caseID, predicate: "covers",
                                          coverage: excluded.isEmpty ? .full : .partial, excluded: excluded,
                                          provenance: evidence([code], excluded.isEmpty ? "この細目の要求を能力の行為・条件・観点に対応付ける。" : "細目の一部を扱い、対象外を明示。")))
            }
        }
        skill("japanese-early", "", "物語の場面や登場人物の行動から内容の大体を捉える", targets: ["sm.character-reading"],
              conditions: "小1〜2の読むこと。場面の様子や登場人物の行動に着目する。", criteria: ["場面や行動を手掛かりに、内容の大体を述べる。"])
        skill("japanese-middle", "", "叙述を基に登場人物の行動や気持ちを捉える", targets: ["sm.character-reading"],
              conditions: "小3〜4の読むこと。文章中の叙述を基に捉える。", criteria: ["登場人物の行動や気持ちを、対応する叙述と結び付けて述べる。"])
        skill("science-knowledge", "", "振り子の1往復の時間と条件の関係を説明する", targets: ["sm.pendulum"],
              conditions: "小5の振り子の観察・実験。親項目に従い、おもりの重さや長さなどの条件を制御して調べる。",
              criteria: ["1往復の時間がおもりの重さなどによって変わらず、長さによって変わることを説明する。"])
        skill("science-inquiry", "", "予想や仮説に基づき振り子の調べ方を考える", targets: ["sm.pendulum", "sm.control-conditions"],
              conditions: "小5。振り子が1往復する時間に関係する条件について予想や仮説を立てる。親項目の条件制御を保持。",
              criteria: ["調べる条件とそろえる条件を示し、予想や仮説を確かめる方法を表現する。"])
        skill("history", "", "文化財や諸資料から地域の歴史的な特徴を考察する", targets: ["sm.local-history"],
              conditions: "中学校歴史的分野。比較や関連、時代的背景、地域的環境、現在とのつながりに着目する。",
              criteria: ["地域の文化財や諸資料を活用する。", "歴史的な特徴を多面的・多角的に考察し、表現する。"])
        skill("language-listen", "", "身近な英語の語句や基本的表現を聞き取る", targets: ["sm.familiar-language"],
              conditions: "小5〜6。ゆっくりはっきりと話される、自分のことや身近で簡単な事柄。",
              criteria: ["提示された簡単な語句や基本的な表現を聞き取る。"])
        skill("language-write", "", "例文を参考に身近な事柄を英語で書く", targets: ["sm.familiar-language"],
              conditions: "小5〜6。自分のことや身近で簡単な事柄。例文を参考にし、音声で十分に慣れ親しんだ語句や基本的表現を用いる。",
              criteria: ["指定された条件で、自分のことや身近な事柄を書く。"])
        skill("music", "", "各声部や伴奏を聴き、音を合わせて演奏する", targets: ["sm.ensemble"],
              conditions: "小5〜6の器楽活動。親項目の『思いや意図に合った表現』を目的とする。",
              criteria: ["各声部の楽器の音、全体の響き、伴奏を聴きながら、音を合わせて演奏する。"])
        // Do not reduce the moral goal to a scored ability. Preserve the original item and its target.
        relations.append(Relation(id: "al.cross-ethics-target", kind: .alignment, from: itemID("82K04D0213000000"),
                                  to: "sm.consideration", contextID: "ctx.cross-ethics", predicate: "covers", coverage: .partial,
                                  excluded: ["思いやりの心をもち、実際に親切にする態度・行動全体"],
                                  provenance: evidence(["82K04D0213000000"], "学ぶ対象の意味だけを対応させ、態度・行動の要求は原文で保持する。")))
        skill("data", "", "データを分類して表に表し、考察を伝える", targets: ["sm.data-organization"],
              conditions: "小3。身の回りの事象について、日時や場所など、整理する観点に着目する。",
              criteria: ["観点に沿って分類整理し、表に表したり読んだりする。", "表を用いて考察し、見いだしたことを表現する。"], excluded: ["グラフを用いた考察"])
        if let index = relations.firstIndex(where: { $0.id == "al.cross-data-0" }) {
            relations[index].coverage = .full
            relations[index].excluded = []
            relations[index].provenance = evidence(["8250233411100000"], "分類整理と表の読み書きは全て含む。別細目の考察も同じ能力へ対応付ける。")
        }
        skill("information", "-build", "目的に応じたアルゴリズムを表現して実装する", targets: ["sm.algorithm-process"],
              conditions: "高校情報Ⅰ。目的に応じた適切な表現方法を選び、コンピュータや情報通信ネットワークを活用する。",
              criteria: ["アルゴリズムを考え、適切な方法で表現し、プログラミングで活用する。"], excluded: ["過程の評価と改善"])
        skill("information", "-improve", "実装した過程を評価し改善する", targets: ["sm.algorithm-process"],
              conditions: "高校情報Ⅰ。目的に応じたアルゴリズムの表現・プログラミングの過程を対象とする。",
              criteria: ["取り組んだ過程を評価し、改善する。"], excluded: ["アルゴリズムの設計・表現・実装そのもの"])

        let caseTargets: [String: [String]] = [
            "japanese-early": ["sm.character-reading"], "japanese-middle": ["sm.character-reading"],
            "science-knowledge": ["sm.pendulum"], "science-inquiry": ["sm.control-conditions"],
            "history": ["sm.local-history"], "language-listen": ["sm.familiar-language"], "language-write": ["sm.familiar-language"],
            "music": ["sm.ensemble"], "ethics": ["sm.consideration"], "data": ["sm.data-organization"], "information": ["sm.algorithm-process"]
        ]
        for sample in pinned.cases {
            let skills = entities.filter { $0.kind == .competency && ($0.id == "cp.cross-" + sample.id || $0.id.hasPrefix("cp.cross-" + sample.id + "-")) }.map(\.id)
            let originalIDs = sample.leafCodes.map(itemID)
            sections.append(ReadingSection(id: "section.cross-" + sample.id, label: sample.label,
                                           entityIDs: originalIDs + (caseTargets[sample.id] ?? []) + skills))
        }
        return Dataset(release: "cross-subject-0.1.0", sources: pinned.sources, frameworks: pinned.frameworks,
                       contexts: pinned.cases.map { .init(id: "ctx.cross-" + $0.id, label: $0.context, conditions: "根拠は選定した原典項目とその上位見出し。", frameworkID: $0.frameworkID) },
                       entities: entities, relations: relations,
                       readingOutlines: [.init(id: "reading.cross-subject", label: "教科をまたいで学びを読む", sections: sections)],
                       limitations: ["選定した8教科・11例を収録。親子階層は教科見出しから選定細目まで。", "前提関係は今回の収録対象外。原典の掲載順から必須前提を生成しない。", "学年帯や活動の条件は原文・文脈で保持。専用フィールドによる学年検索・活動実行・採点は未実装。"])
    }
}
