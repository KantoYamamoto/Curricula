# 交換契約 0.2.0：属性・根拠・目標・編集履歴

確認日：2026-10-11。新規の内容整理・ローカル編集が使う交換契約。学年・教科、フィールド別の根拠、目標と判定注釈、UUIDと改訂、AND/OR前提、資料種別を定義する。[旧契約0.1.0](exchange-contract.md)の公開済み4版もそのまま読み取れる。

定義は [SchemaV2.swift](../Sources/Curricula/SchemaV2.swift)、整合性検証は [ValidationV2.swift](../Sources/Curricula/ValidationV2.swift)。教科横断版は `cross-subject-0.2.0`、編集操作例は `editing-0.2.0`〜`editing-0.2.3`。

## 学年・教科・科目

原典項目・目標・学ぶ対象・枠組み・文脈に `education` を持たせる。一つの対象を複数学年・教科で共有できるよう配列にする。

| フィールド | 意味 |
|---|---|
| stage | elementary / lowerSecondary / upperSecondary / higherEducation / other |
| gradeStatus | specified（指定あり）/ notSpecified（未指定）/ notApplicable（該当なし） |
| grades | 学校段階内の学年番号の集合。小3〜4は `[3,4]`。指定なしの場合は空配列 |
| subjectID | `taxons` の教科を参照するUUID |
| courseID | 科目・分野のUUID。親教科との整合性を検証。任意 |

教科と科目の名称は別の `taxons` に置く。教科横断標本では8教科に加え、英語・歴史的分野・情報Ⅰの3科目・分野を収録。小学校の算数と高校の情報を同一の固定学年体系へ押し込まない。一般の教科見出しに、下位科目の指定を逆流させない。

小1〜2、小3〜4、小5〜6を原典の学年帯として登録する。中学歴史・高校情報Ⅰの履修年は未指定。大学等では学年が必要ない枠組みに `notApplicable` を選べる。教科横断標本は[編集用選定表](../Sources/CurriculaPilot/Resources/v2-authoring.json)で指定する。全範囲の原文取り込みでは固定したLODメタデータを使用し、学年未指定を全学年に補わない。[収録仕様](curriculum-coverage.md)を参照。

## 目標と自然言語の注釈

旧 `competency` を新契約では `goal` とする。目標本文、条件、学ぶ対象への参照、学年・教科を保持する。観点・自動採点器・点数の存在は登録の要件にしない。

旧 `criteria` は `annotations` へ移す。各注釈には独立したUUIDと編集版、目標のID＋編集版、自然言語の `text`、表示順 `position`、`evaluationMode` がある。配列の位置を注釈のIDとして使わない。

判定方法は `unspecified`（未指定）または `humanObservation`（人による観察）。将来のソフトウェア判定用に `software` / `evaluatorID` の境界を設けたが、この版に採点器はないため、その指定は `unavailableEvaluator` として拒否する。文章があるだけで実行可能とは扱わない。前提の論理式を計算することと、学習者の目標達成を判定することも別である。

道徳の「誰に対しても思いやりをもち…」は独立した目標として原文の要求を保持し、観点のない状態で登録した。初回標本にあった13の観点は、内容を変えず13注釈へ移した。

## 根拠を編集対象のフィールドへ結ぶ

`evidence` は独立したレコード。編集理由の文章からコードを解析する必要はない。

```text
根拠レコード
  target: { id, revisionID }  ← 記述や注釈の、どの編集版か
  field: text | conditions | education | coverage | expression
  role: quotation | supports | contextualizes
  citations:
    source: { id, revisionID } ← 原典・書籍等の、どの版か
    locator: 引用位置           ← CSV行、節、ページ等
    item?: { id, revisionID }  ← 取り込み済み原典項目があれば参照
  rationale: この箇所を根拠とする理由
```

注釈の根拠は注釈自身の `text` へ結ぶ。理科の条件制御のように親項目の条件を参照する場合、目標の `conditions` にその親項目を結ぶ。情報Ⅰの一部だけを対応させる判断は関係レコードの `coverage` に結ぶ。注釈1件に複数の根拠、同じ原典に複数の編集対象を結べる。

原典引用は文書の版と箇所を必須にする。取り込み済み原典項目も指定した場合、その原典項目の引用元と文書・位置が一致することを検証する。存在しないフィールドや古い編集版を指す根拠を拒否する。明白な定義・計算例や合成した操作例に一律の出典必須制約は設けない。

## 出典の種類と版

`sources` は `curriculum / commentary / book / article / syllabus / referenceStandard / webPage` を区別し、`origin` と `scope` を持つ。対象文書のUUIDと編集版UUIDを持ち、引用は両方へ固定する。

書誌情報は `title, creators, publisher, identifiers, edition, issuedOn`。告示がある資料だけに `promulgatedOn`。URLは任意で、書籍はISBN等の書誌情報でも表現できる。取得したファイルの記録には `retrievedOn, sha256, verification` を使う。ハッシュを付ける場合は取得日も必要。日付は原資料の精度に合わせる。

全種類へ告示日・URL・ハッシュを強制しない。合成資料に実在の告示・取得・ハッシュを捏造しない制約を置く。操作例にはURLなしの合成シラバス・参照基準と、告示日・ファイルハッシュなしのOpenStax書籍参照を収録した。

## ID・別名・改訂

全レコードにUUIDの `id` と `revisionID` を持つ。名称・学年・教科・並び順・外部コードはIDから独立。`aliases` は読みやすい別名からUUIDへの索引であり、参照の正本はUUID。外部コードは `externalIDs` に名前空間付きで保持する。Swiftの手動標本はUUID v4を[登録簿](../Sources/CurriculaPilot/Resources/identity-registry.json)へ割り当てて保存し、ビルドごとに再発行しない。SQLiteの新規作成は発行したUUID v4をDBへ保存する。新規の原典自動取り込みは固定名前空間と原典コードからUUID v5を生成し、既存標本と重なる原典には登録済みIDを使う。

編集では対象IDを維持し編集版を更新、分割・統合では新しい対象IDを発行する。旧IDは `retired` と後継 `successorIDs` を持ち、旧版も再現できる。変更レコードは、種類・理由・変更前後のリリース＋ID＋編集版を保持する。別名を一対多の転送先に書き換えず、旧対象から後継一覧へたどる。手順は [IDと編集操作](identity-editing.md)を参照。

## 前提経路

`prerequisites` は `targetGoalID`、`contextID`、`strength: required / recommended`、`expression` を持つ。式は次の三つだけで構成する。

```json
{
  "op": "anyOf",
  "operands": [
    {"op": "goal", "goalID": "AのUUID", "operands": []},
    {"op": "allOf", "operands": [
      {"op": "goal", "goalID": "BのUUID", "operands": []},
      {"op": "goal", "goalID": "CのUUID", "operands": []}
    ]}
  ]
}
```

A、またはBとCの両方。グループは2要素以上、葉は目標IDだけを持つ。ネスト上限は64。同じ文脈・対象への複数の必須ルールはすべて満たす必要がある。履修上の指定は別の `enrollment` 関係のまま残す。

構造検証では、必須ルールを持たない目標から始め、満たせる目標を反復して求める。循環する選択肢があっても別の経路で到達できれば許可し、全経路が循環して到達不能なら拒否する。文脈は混ぜず、推奨は必須判定へ混ぜない。これは登録した式の整合性確認で、学習者が出発点の目標を達成済みだという判定ではない。

## 読み取りAPI

URLの `/api/v1` は維持し、応答の `schemaVersion` で契約を識別する。版を省略して内容が変わるURLにはしない。旧版の応答形は変更しない。

| 取得 | 追加した動作 |
|---|---|
| `/entities/{UUIDまたは別名}` | 原レコードと `annotations, evidence, prerequisites, changes, derivedEntities` を返す |
| `/entities?stage=elementary&grade=3&subjectId=subject.japanese&kind=goal` | 属性の組合せで検索。gradeにはstageを要する。指定学年を明示した範囲だけ一致させる |
| `/entities?courseId=course.information` | 科目・分野で検索 |
| `/resolve/{別名}` | UUID・編集版・コレクションを返す |
| `/evidence?targetId={ID}` | 編集対象に直接結び付いた根拠 |
| `/prerequisites?entityId={ID}` | 目標の前提式 |
| `/changes?entityId={ID}` | 変更前後に対象を含む変更履歴 |
| `/annotations/{ID}`, `/taxons/{ID}`, `/sources/{ID}` | 独立レコードとして取得 |

属性検索は一つのeducation範囲内で全条件が一致する必要がある。別々の教科・学年範囲の値を組み合わせて誤一致させない。`notSpecified` を任意学年に一致させない。一覧検索はactiveのみ、直接取得ではretiredも返す。この `/api/v1` は読み取り専用。編集起動時だけ有効な `/api/edit` と、教材試作の `/api/preview` は別の境界とする。[現行のHTTP API](viewer-api.md)を参照。

## 設計の参照資料

UUIDは [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html) のv4とv5を使う。手動編集の同一性と、固定原典からの再生成を用途に応じて分ける。名称や表記と識別子の分離は [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/) を、版・改訂・派生の区別は [W3C PROV-O](https://www.w3.org/TR/prov-o/) を設計の参考にした。今回のJSONをそれらの規格への完全準拠形式とはしていない。

## 閲覧APIの原文逆引き

`derivedEntities` は、その原文を本文または条件の根拠として参照する学ぶ対象・目標を返す派生情報。学年・教科の設定元だけの参照は含めない。項目取得と `/reading-sections/{ID}` の各項目詳細に同じ逆引きを返す。公開JSONには新しいレコードを加えず、既存の版固定されたevidenceから索引を作る。新規作成・根拠追加・部分進捗は[ローカル編集API](local-editing.md)で扱う。
