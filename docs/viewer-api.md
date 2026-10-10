# 閲覧画面とHTTP API

確認日：2026-10-11。ローカル実装の仕様です。公開向けの資源設計は[Issue #6](https://github.com/KantoYamamoto/Curricula/issues/6)、OpenAPI・Swagger UIは[Issue #7](https://github.com/KantoYamamoto/Curricula/issues/7)で検討します。`/openapi.json` と `/api-docs` は未実装です。

## 画面と取得元

`make serve` で127.0.0.1:8000に起動します。HTML/CSS/JavaScriptとAPIは同じPythonサーバーから配信します。

| ルート | 目的 | 主な取得元 |
|---|---|---|
| `/read` | 目次に沿って原文・対象・目標を読む | 版付き読み取りAPI |
| `/structure` | 原典階層、属性、根拠、前提、変更を確認する | 同じ版付き読み取りAPI |
| `/coverage` | 原文収録と目標整理の進捗を見る | `/api/v1/coverage` |
| `/learn` | 教科書／問題集の4単元を試す | `/api/preview/lessons` |
| `/edit` | 下書き・確認・新しい版・進捗を編集する | `/api/edit/*`。編集起動時のみ |

原文・目標の初期表示は `reading-0.3.1` です。`release` でデータ版、`outline` と `section` で目次・節、構造画面の `entity` で項目を指定できます。教材画面は `unit` と `mode=textbook|workbook` を使います。教材モードは一つの画面で切り替えます。外部公開時のURLをこの構成に固定する決定はしていません。

## 読み取りAPI

以下はGETです。版付きパスの基点を `/api/v1/releases/{release}` とします。UUIDを正本とし、契約0.2.0では登録された別名も参照に使用できます。

| パス | 応答の主要フィールド・用途 |
|---|---|
| `/api/v1/releases` | `releases`：利用できるデータ版とスキーマ版 |
| `/api/v1/capabilities` | `localEditing`：編集起動の有無 |
| `/api/v1/coverage` | 収録台帳に版付きの整理進捗を重ねた結果。データ版固定ではない |
| 基点 + `/overview` | 枠組み・文脈・目次・制約。0.2.0では分類も含む |
| 基点 + `/entities/{id}` | `data`。0.2.0では注釈・根拠・逆引き・前提・変更も付属 |
| 基点 + `/entities` | 0.2.0の一覧検索。`entities` と `gradePolicy` |
| 基点 + `/frameworks/{id}` | `data` と所属する `items` |
| 基点 + `/reading-outlines/{id}` | `data`：節・表示順・対象ID参照 |
| 基点 + `/reading-sections/{id}` | 0.2.0の節と、その項目詳細を一括取得する `data`・`entities` |
| 基点 + `/sources/{id}`、`/contexts/{id}` | 出典・文脈の `data` |
| 基点 + `/taxons/{id}`、`/annotations/{id}` | 0.2.0の分類・注釈の `data` |
| 基点 + `/resolve/{alias}` | 0.2.0のUUID・改訂UUID・コレクションを含む `data` |
| 基点 + `/relations?entityId=...&contextId=...` | `relations` と文脈の扱いを示す `contextPolicy` |
| 基点 + `/evidence?targetId=...` | 0.2.0の対象へ直接結び付いた `evidence` |
| 基点 + `/prerequisites?entityId=...&contextId=...` | 0.2.0の前提式 `prerequisites` |
| 基点 + `/changes?entityId=...` | 0.2.0の変更前後に対象を含む `changes` |

`entities` の検索条件は `stage`、`grade`、`subjectId`、`courseId`、`kind` です。`kind` は `frameworkItem` / `subjectMatter` / `goal`。`grade` には `stage` が必要です。一つの `education` 範囲内で全条件が一致するものを返し、学年未指定を全学年として扱いません。一覧は `active` のみ、直接取得は `retired` も返します。ページネーションは未実装です。

例：サーバーを起動した別のターミナルで実行します。`&` を含むURLは引用符で囲みます。

```sh
curl 'http://127.0.0.1:8000/api/v1/releases'
curl 'http://127.0.0.1:8000/api/v1/releases/reading-0.3.1/entities?kind=goal&stage=elementary&grade=1'
curl 'http://127.0.0.1:8000/api/v1/releases/cross-subject-0.2.0/entities/cp.cross-language-write'
curl 'http://127.0.0.1:8000/api/v1/releases/cross-subject-0.2.0/resolve/cp.cross-language-write'
```

版付き応答は `release` と `schemaVersion` を含みます。例として `resolve` の `data` は `{ "id": "…", "revisionID": "…", "collection": "entities" }` の形です。未発見の版とグローバルAPIの応答には、特定版の包絡情報はありません。旧0.1.0版は[旧契約](exchange-contract.md)の応答を維持します。

## 結果の読み方

| 状態 | HTTP応答 |
|---|---|
| 正常取得、条件に合う項目がない一覧 | 200。一覧は空配列 |
| 未対応・不正な検索条件 | 400。`error.code` で理由を識別 |
| 存在しない版・ID・ルート | 404 |
| 読み取りAPIへの書き込み | 405 |
| 編集下書きの期待版が一致しない | 409。編集APIのみ |

版が見つかった後のエラーにも版・スキーマ情報を含みます。`error.code` は `release_not_found`、`id_not_found`、`invalid_grade` などです。空一覧から未収録・未調査・学習不要を推論せず、収録範囲と確認記録を参照します。

文脈なしの関係取得では各関係の文脈を保持し、世界共通の必須前提へ統合しません。原文詳細の `derivedEntities` は本文または条件の根拠としてその原文を使う対象・目標です。学年設定だけの根拠は含みません。

## 編集・教材と公開の境界

`make serve-edit` はSQLiteの公開済み0.2.0版を読み、下書きは別の編集APIで扱います。確認後に作成した新しい版だけを読み取りAPIへ追加します。[ローカル編集API](local-editing.md)に操作・競合・セッションの仕様があります。

`/api/preview/lessons` は教材試作の専用形式で、`/api/v1` の交換契約には含めません。教材・問題の安定APIや独立した版管理は未実装です。[試作の仕様](learning-preview.md)と[Issue #4](https://github.com/KantoYamamoto/Curricula/issues/4)を参照してください。

現在のサーバーはローカル利用用です。外部配信、認証、権限、更新・保守は[Issue #13](https://github.com/KantoYamamoto/Curricula/issues/13)で設計します。パブリックリポジトリの存在と、稼働中のAPIのインターネット公開は別の状態です。

[初期のAPI案](history/design-2026-09-28/viewer-api.md)は履歴として保存しています。
