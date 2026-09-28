# 交換契約 0.1.0

2026-09-28。設計資料v0.3を使った初回実装の契約。現物例は [pilot-0.1.0.json](../data/releases/pilot-0.1.0.json)。JSONの正式なキーは [Model.swift](../Sources/Curricula/Model.swift) の公開値型に対応し、互換性を意図せず変更しない。JSON Schemaによる網羅的な構文検証は未導入。

## 版と正規形

- `schemaVersion` は交換契約、`release` はデータ版。URLの `v1`、原典告示年、配布版とは別。
- UTF-8 JSON、末尾改行。最上位は `schemaVersion, release, sources, frameworks, contexts, entities, relations, readingOutlines, limitations`。
- レコード集合はID順、オブジェクトキーは辞書順。対象参照・出典参照・対象外範囲は集合として整列する。目次の節・節内の対象・達成観点の順序は保持する。
- 内部IDは `[a-z][a-z0-9.-]*`、リリース全体で一意。ラベルや並び順から生成しない。外部コードは `externalIDs` に名前空間付きのキーで保存する。
- 任意フィールドは省略。空配列は「登録なし」。調査完了の意味を与えない。能力の `prerequisiteStatus` で `uninvestigated / scopedBoundary / investigated` を明示する。
- 同一入力の再出力を `make check` で照合。既存リリース公開後の意味変更は新しいファイルと版にする。分割・統合の移行表は未実装。

## レコードと関係

| 集合 | 主なフィールド・意味 |
|---|---|
| sources | id, title, publisher, url, promulgated, distributionVersion, retrievedOn, sha256, verification。ハッシュは元CSV全体 |
| frameworks | id, label, issuer, version, sourceIDs, origin |
| contexts | id, label, conditions, frameworkID（任意）。履修規則と学習経路を共通化しない |
| entities | id, kind, label, text, conditions, provenance, externalIDs, targetIDs, criteria。frameworkID, parentID, sourceLocator, prerequisiteStatus, categoryは任意 |
| relations | id, kind, from, to, predicate, provenance, excluded。contextID, coverage, strengthは関係種別による |
| readingOutlines | id, label, sections。各節はid, label, entityIDs。原典階層と別 |

`Entity.kind` は frameworkItem / subjectMatter / competency。分類語彙 `category` は版付きの文字列で拡張可能。能力だけが対象ID、条件、達成観点、調査状態を必須とする。原文は `provenance.origin=original`、独自編集は editorial、合成例は synthetic。`reviewStatus=draft` は機械検証後も変えない。

| 関係種別 | 向きと制約 |
|---|---|
| alignment | 枠組み項目 → 知識または能力。coverage必須。partialはexcluded必須、fullはexcludedを空にする |
| knowledge | 知識 → 知識。predicateを保持。現在のrelated/contrastsから対称性・推移性を自動推論しない。循環可 |
| dependency | 前提能力 → 対象能力。contextID・strength必須。同じ文脈内のrequiredのみ循環検出 |
| enrollment | 能力 → 能力の履修規則用の初期スロット。dependencyとは別。コース履修管理には未対応 |

`strength=alternative` は情報落ちを避けるため検証エラー `unsupportedAlternative` にする。AND/OR構造の支持を主張しない。原典項目の親は同一枠組みの項目に限定し、循環を検出する。

## HTTP API

`python3 scripts/serve.py` は127.0.0.1にのみbind。外部公開用サーバーではない。起動時に出力済みJSONを読み、更新時は再起動する。APIレスポンスは `/releases` 一覧と未知版エラーを除き `release, schemaVersion` を持つ。

| GET（先頭は `/api/v1`） | 内容 |
|---|---|
| /releases | 利用可能版一覧 |
| /releases/{release}/overview | 枠組み、文脈、目次、既知の限界 |
| /releases/{release}/entities/{id} | dataに対象・能力・原典項目 |
| /releases/{release}/frameworks/{id} | dataに枠組み、itemsに所属項目（parentIDによる階層） |
| /releases/{release}/relations?entityId=…&contextId=… | 関係一覧。パラメータはそれぞれ任意 |
| /releases/{release}/reading-outlines/{id} | dataに目次 |
| /releases/{release}/sources/{id} | dataに出典 |
| /releases/{release}/contexts/{id} | dataに文脈 |

contextId指定時は完全一致。省略時は文脈を保持して全件を返す。指定時に文脈なしのalignmentを混ぜない。空一覧は200、未知の版・ID・文脈は404と区別する。重複/空/未知の絞り込みは400。POST/PUT/PATCH/DELETEは405。

画面は選択版をリンクへ引き継ぎ、各API応答の版を照合する。取得中・再試行可能な取得失敗・空結果を区別する。目次の編成はAPIから取得する。未調査は能力の状態、部分対応は関係、合成例は由来から表示する。
