# 工程と進捗

確認日：2026-10-11。実装済みの増分、継続中の内容整備、これから決める設計を分けて追跡します。原文・目標の作業量は[収録台帳](curriculum-coverage.md)が基準です。

## 実装済みの増分

| 増分 | 成果 | 確認記録 |
|---|---|---|
| 初回の一連の実装 | Swiftモデル→JSON→ローカルAPI→読む／構造画面。比例の小標本 | [初回](reviews/pilot-0.1.0.md) |
| 教科横断・境界の検証 | 8教科11例と、機関・条件・改訂などの補助ケース | [構造標本](reviews/structure-samples.md) |
| 契約0.2.0 | UUID、学年・教科、版付き根拠、目標注釈、AND/OR、資料種別 | [契約](reviews/schema-0.2.0.md) |
| SQLite編集 | 下書き・競合・確認・不変版作成・バックアップ復元 | [編集](reviews/local-editing.md) |
| 小中の原文収録 | 5,939項目、138区切りの原文段階が完了 | [原文](reviews/curriculum-0.3.0.md) |
| 目標整理の最初のまとまり | 国語1・2年「読むこと」の6対象・6目標・6注釈、原文12項目を確認 | [目標整理](reviews/reading-authoring.md) |
| 教科書・問題集の試作 | 4単元・14問、目標と原文の改訂参照、答え合わせと記述観点 | [教材試作](learning-preview.md) |

記録のテスト件数と未対応事項は各確認日時点のものです。古い記録にある「DB未導入」「AND/OR未対応」は現在の状態ではありません。

## 継続する内容整備

1. 小学校国語1・2年の「話すこと・聞くこと」を整理する。
2. 同学年の残り、3・4年、5・6年を順に整理する。
3. 小学校の掲載順で他教科へ進み、その後に中学校へ進む。

各まとまりで、原文を選ぶ→対象と目標を作る→条件と判定注釈を付ける→根拠を確認する→新しい版を作る→原文単位の確認記録を残す、まで行います。学年帯の一部を終えただけで区切り全体を完了にしません。現在は目標整理0区切り完了、1区切り整理中です。

## 設計の議論と依存

全体の入口は[Issue #1](https://github.com/KantoYamamoto/Curricula/issues/1)です。以下は設計・文書のタスクで、資料を更新しただけでは決定・完了になりません。

| Issue | 決めること・作るもの | 主な前提 |
|---|---|---|
| [#2](https://github.com/KantoYamamoto/Curricula/issues/2) | 利用者、初回の外部公開範囲、優先順位、完了条件 | 推奨案を比較し、所有者が最終決定 |
| [#3](https://github.com/KantoYamamoto/Curricula/issues/3) | 全体構成図と責務・データの流れ | #2の公開範囲 |
| [#4](https://github.com/KantoYamamoto/Curricula/issues/4) | 教材・問題・解答・図表のモデルと版管理 | #2、既存の試作と共通契約 |
| [#5](https://github.com/KantoYamamoto/Curricula/issues/5) | 保存構造と移行 | #3・#4、現在のSQLite |
| [#6](https://github.com/KantoYamamoto/Curricula/issues/6) | REST APIの資源・パス・応答 | #2・#4、現在の読み取りAPI |
| [#7](https://github.com/KantoYamamoto/Curricula/issues/7) | OpenAPIとSwagger UI | #6の契約 |
| [#8](https://github.com/KantoYamamoto/Curricula/issues/8) | 公開ページと利用導線 | #2・#4・#6 |
| [#9](https://github.com/KantoYamamoto/Curricula/issues/9) | 編集・確認・版作成の流れ | #4・#5、現在のローカル編集 |
| [#10](https://github.com/KantoYamamoto/Curricula/issues/10) | 原文・目標・教材の進捗の表し方 | #2、既存の138区切りと部分進捗 |
| [#11](https://github.com/KantoYamamoto/Curricula/issues/11) | 執筆・解答・判定観点・根拠の方針 | #4・#9 |
| [#12](https://github.com/KantoYamamoto/Curricula/issues/12) | コード・原典・独自データ・教材の利用条件 | #2・#4、既存の利用条件記録 |
| [#13](https://github.com/KantoYamamoto/Curricula/issues/13) | 外部配信、保守、バックアップ等の運用 | #3・#5・#6・#12 |
| [#14](https://github.com/KantoYamamoto/Curricula/issues/14) | 検証と文書保守 | 上記の決定と実装 |

#2では、原文・整理済み目標と代表教材を提供する案のほか、データ再利用先行、一教科・学年の教材先行を比較しています。期限と初回公開の対象量は未決定です。高等教育の本格収録、公開wiki編集、学習履歴・推薦を、自動的に初回公開の必須条件には加えません。

初期のM0〜M5の比例中心の工程は[保存版](history/design-2026-09-28/milestones.md)にあります。
