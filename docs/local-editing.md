# ローカルwiki編集とSQLite

2026-10-05更新（初回実装2026-10-04）。ユーザー指定のローカル編集を実装。交換契約は0.2.0を維持する。

## 起動と操作

```sh
make serve-edit
```

[編集画面](http://127.0.0.1:8000/edit)で元のデータ版を選び、名前を付けて下書きを作る。独自の学ぶ対象・目標について、見出し、本文、条件を変更できる。目標の判定観点は自然言語で編集・追加でき、採点器の登録を要求しない。

1. 「学ぶ対象・目標を追加する」で種類・文言を記入し、学年・教科の設定元となる原文を選ぶ。目標には学ぶ対象と任意の注釈を選択・記入する。原文はコードや語句で絞り込める。
2. 本文と条件の根拠を、それぞれ原文の項目から選ぶ。引用位置・原文と資料の改訂UUIDを保持する。すでにある項目にも根拠を追加できる。
3. 既存項目を編集する場合は、文言と観点を記入する。
4. 引き継ぐ注釈と根拠を個別に選択し、変更理由とともに下書きへ保存する。
5. 元の版との差分・注釈・根拠を確認し、確認内容を記録する。
6. 新しいデータ版名を付けて保存する。閲覧画面から読め、正規化JSONも書き出せる。

根拠をまだ確認できない段階でも下書きを保存できる。注釈と根拠の旧版参照を残し、画面に確認項目を表示する。この状態では確認記録と新しい版の保存は拒否する。目標の変更だけで既存の根拠や注釈を無条件に付け替えない。注釈の本文を明示的に編集した場合は、その注釈を現在の目標へ結び付けるが、注釈自体の根拠は別途確認する。

原典項目、原文由来の対象、廃止された対象はこの画面の編集対象にしない。学年・教科は選択した原文の専用属性をコピーし、その原文を設定根拠として記録する。属性を任意に変更する画面、外部資料の新規登録、関係・前提経路・分割統合の編集画面は後続の工程。現在の保存処理は文言修正を扱い、分割・統合は[既存のSwift編集操作](identity-editing.md)に残す。

`make serve` は従来の閲覧専用起動。編集起動ではSQLiteがスキーマ0.2.0の編集・閲覧の保存元となる。Swift小標本・同梱JSONは初期投入と回帰確認用。`make export` は小標本の再生成であり、DB内の編集内容を取り出すコマンドではない。

## 保存構造

既定のDBは `.local/curricula.sqlite3`。Gitの対象外とし、ローカルの下書きや確認記録をリポジトリへ送らない。

| テーブル | 保存するもの |
|---|---|
| identities | 安定UUIDとレコードの種類 |
| revisions | 編集版UUID、対象UUID、不変のレコード本文 |
| snapshots / snapshot_records | データ版のヘッダー、ハッシュ、採用したレコード版と順序 |
| aliases | 版ごとの読みやすい別名と対象UUID |
| education_scopes / scope_grades | 編集版に結び付いた学校段階・学年・教科・科目の検索索引 |
| drafts | 初期版、現在の下書き版、保存済みの公開版へのポインタ |
| events | 変更前後の下書き版、時刻、編集者、理由、明示した引き継ぎ対象 |
| reviews | 確認した下書き版、時刻、確認者、確認内容 |
| work_reviews | 確認した作業区切り・原文・目標・注釈、公開版、次の範囲 |

本文は各レコードのJSONとして保持し、索引・対象・版・版集合をリレーショナルに管理する。目次内の節もUUID・編集版を登録する。AND/ORや引用位置は自由文へ潰さず、元の交換契約の構造で保存する。外部キーと一意制約を有効にし、編集版と版集合の上書き・削除はDBトリガーで拒否する。

DBの保存スキーマは `user_version=2`。既存の版1からは進捗記録テーブルを追加し、公開版と下書きは保持する。初期投入は小標本5版、全範囲原文版、整理済みの版を共通Swift検証へ通し、DBから再構成したJSONが元ファイルとバイト単位で一致することを確認する。再起動の再投入は同じ入力なら何もしない。元の公開版を別の内容で上書きしようとすると停止する。0.1.0版は同梱JSONから従来どおり読む。

## 競合、確認記録、版作成

保存・確認・版作成は、要求時の `expectedHead` と現在の下書き版を `BEGIN IMMEDIATE` 内で照合する。別のタブが先に保存した場合はHTTP 409を返す。画面は入力を残して競合を表示し、黙って上書きしない。複数のレコードと版集合、編集履歴、現在版ポインタは同じトランザクションで保存する。[SQLiteのトランザクション仕様](https://www.sqlite.org/lang_transaction.html)を参照。

確認記録は下書き版UUIDへ固定する。確認後に編集すれば、新しい版では確認記録が必要になる。これはローカルで差分を確認した記録であり、教育内容をソフトウェアが採点・審査した結果ではない。今回の編集者・確認者は `local-user` として記録する。

新しい版の作成時は、確認済みの下書き版を再検証し、その版のレコード集合を固定する。文言修正した対象の交換用 `changes` は、元の公開版と新しい公開版へ結ぶ。中間の下書き履歴はDBのeventsに残す。公開用のJSONが未公開の下書き名へ依存しないようにする。注釈だけの変更はDBの編集履歴で追跡する。以前の編集・分割・統合イベントは保持する。

「新しい版を保存」はローカル閲覧APIへの登録。インターネットへの公開操作ではない。下書きは `/api/v1/releases` に載せず、版作成後のデータだけを閲覧APIへ追加する。

## APIと実行境界

編集用APIは `--edit-db` 指定時だけ有効。サーバーは127.0.0.1に束縛し、Hostを確認する。書き込みは同一Origin、JSON Content-Type、起動セッションのトークンを必須にする。ユーザー認証や役割権限はまだ導入していないため、複数人による公開編集を始める段階で別途実装する。

| API | 操作 |
|---|---|
| GET /api/v1/capabilities | 編集機能の起動有無 |
| GET /api/edit/session | ローカル編集セッション |
| GET /api/edit/drafts | 下書き一覧 |
| POST /api/edit/drafts | baseRelease、titleから作成 |
| GET /api/edit/drafts/{id} | 下書き、元の版、検証項目、確認記録、履歴 |
| POST /api/edit/drafts/{id}/entities | expectedHead、kind、label、text、educationFrom、targetIDs、sourceItemIDs、conditionItemIDs、annotations、reasonで作成 |
| POST /api/edit/drafts/{id}/evidence | expectedHead、entityID、field、sourceItemIDs、reasonで根拠を追加 |
| GET /api/edit/work | 進捗の確認記録一覧 |
| POST /api/edit/work | expectedWorkID、chunkID、release、確認済み原文・目標・注釈UUID、label、note、nextを保存 |
| POST /api/edit/drafts/{id}/save | expectedHead、entityID、文言、注釈、引き継ぎ対象、reason |
| POST /api/edit/drafts/{id}/review | expectedHead、noteを記録 |
| POST /api/edit/drafts/{id}/publish | expectedHead、releaseで新しい版を保存 |
| GET /api/edit/drafts/{id}/history/{snapshotID} | その下書きの履歴に属する時点の内容 |
| GET /api/edit/releases/{release}/export | 公開版の正規化JSON |

読み取り用 `/api/v1/releases` への書き込みは引き続き拒否する。編集セッションのトークンはJavaScriptが取得し、利用者に入力を要求しない。Swiftの `check-json` は内部連携用で、標準入力のdataset/historyに対して共通検証結果と正規化JSONを返す。Python側でも変換前後を照合し、未対応フィールドの黙殺を拒否する。

## バックアップと書き出し

```sh
swift build
python3 scripts/manage_db.py init
python3 scripts/manage_db.py verify
python3 scripts/manage_db.py export reading-0.3.1 /tmp/reading-0.3.1.json
python3 scripts/manage_db.py export-work 8aaee542-ba06-43e2-9a37-4ebd21779947 /tmp/reading-work.json
python3 scripts/manage_db.py backup /tmp/curricula-backup.sqlite3
```

`--db PATH` で保存先を指定できる。書き出し先・バックアップ先の既存ファイルは上書きしない。バックアップには[Python sqlite3のbackup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup)を使い、稼働中のDBでも一貫したコピーを作る。

復元はサーバーを停止してバックアップを別の保存先へコピーし、`python3 scripts/manage_db.py --db PATH verify` の後、`python3 scripts/serve.py --edit-db PATH` で起動する。現在のDBを残したまま復元先を検証できる。verifyは進捗の参照・公開版対応、DB整合性、外部キー、全公開版の検証とハッシュ、下書き履歴の復元を確認する。旧版を指すchangesを持つJSONを別環境へ渡す場合は、参照先の旧公開版も一緒に渡す。

[DB移行方針](database-editing-plan.md)、[検証記録](reviews/local-editing.md)に続く。

## 整理した範囲の記録

新しい版を保存すると、同じ編集画面に「整理した範囲を進捗に記録する」が現れる。原文の枝を選んで確認済みにするか、個別に原文を選び、整理した目標・確認内容・次の範囲を記録する。作業区切り全体の原文を選ぶまでは整理中として表示する。機械検証の成功だけで進捗を完了にしない。

新規作成の対象・版・根拠・注釈はUUID v4を発行し、不変の下書き版とeventsに保存する。新しい目次「整理した学ぶ対象と目標」に追加し、原文から対応する対象・目標への逆引きも表示する。学年設定だけの参照は内容の対応として数えない。

共有する確認記録は `export-work` で書き出し、対応する公開版とともに `data/work-reviews`・`data/authoring` に追加する。起動時は同じUUID・内容なら再投入せず、同じUUIDの内容変更を拒否する。ローカルの未公開下書きと編集履歴はDBに残る。
