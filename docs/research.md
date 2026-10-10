# 参照資料と調査の扱い

文書整理日：2026-10-11。原典・設計・標本の確認に用いた資料の入口です。外部資料の調査日は各取得記録または保存版の記載に従います。この更新日に外部の全資料・最新規格・利用条件を再調査したという意味ではありません。

## 取り込みに使う資料

| 資料 | 現在の使い方 | 記録 |
|---|---|---|
| 文科省[学習指導要領コード表](https://www.mext.go.jp/a_menu/other/data_00001.htm) | 公式CSVの本文・外部コード。小学校82V12、中学校83V11を固定入力として全範囲収録 | [収録仕様](curriculum-coverage.md)、[固定入力](../data/sources/mext) |
| 文科省[本文・解説の掲載一覧](https://www.mext.go.jp/a_menu/shotou/new-cs/1384661.htm) | 小中の前文を本文PDFから補足し、目次と階層を照合 | [収録仕様](curriculum-coverage.md) |
| 教育データプラス研究会[学習指導要領LOD](https://jp-cos.github.io/) | 階層・学年・分野の補助メタデータ。本文の取得元は公式CSV | [取得版と補正](../data/sources/mext/metadata.json)、[利用条件](../THIRD_PARTY_NOTICES.md) |
| 文科省[中学校指導要領解説](https://www.mext.go.jp/a_menu/shotou/new-cs/1387016.htm) | 本文だけでは条件や説明が不足する場合の参照候補。解説全体の構造化取り込みは未実施 | 本文・解説・独自説明を別出典として扱う |

原典の告示年、CSV配布版、LODの配布版、独自データ版は別々に識別します。「最新版」という可変の名称だけを保存せず、採用したURL・版・取得日・ハッシュ・引用位置を残します。更新候補は既存入力とは別に取得して差分を確認し、通常の生成・テストで外部サービスに依存しません。

## 概念の根拠

教科横断の目標・条件・観点は、選定した学習指導要領と必要な親項目へ結び付けています。指導要領にない主張には、公式解説や著者・編集体制が明らかな資料を用い、どの記述を支えるか示します。初等教育の自明な概念に一律の引用を求めません。

補助標本の理想気体の近似条件と線形写像の定義にはOpenStaxとNicholsonの教科書を参照しています。具体的な章・URL・根拠の対象は[教科横断の検証](cross-subject-validation.md#根拠の扱い)を参照してください。教材試作の人数や実験数値は練習用の架空資料と明示します。

## 設計上の参考

以下は設計の参考で、すべてを導入する計画や規格への準拠宣言ではありません。

| 資料 | 参考にする境界 |
|---|---|
| [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html) | UUID v4による手動・編集用ID、v5による再現可能な原典取り込みID |
| [W3C SKOS](https://www.w3.org/TR/skos-reference/) | 名称・別名と概念の識別。分類の上下関係と学習前提の区別 |
| [W3C PROV-O](https://www.w3.org/TR/prov-o/) | 出典、生成、改訂、派生の区別 |
| [1EdTech CASE](https://standards.1edtech.org/case/) | 教育上の枠組み・項目・対応の交換 |
| [1EdTech QTI](https://www.1edtech.org/standards/qti/index) | 教材・問題・評価の交換モデルを検討する際の比較対象 |
| [SQLiteトランザクション](https://www.sqlite.org/lang_transaction.html) | 現在の下書き保存・期待版の照合・版作成 |
| [Python sqlite3 backup](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup) | 稼働中DBの一貫したバックアップ |

Swiftの型とパッケージ構成は[現行のコード](../Package.swift)、入出力の規則は[交換契約](exchange-contract-0.2.md)が基準です。外部規格の改訂を採用する場合は、必要な箇所を改めて調査します。

## 初期調査を参照する場合

2026-09-28の調査は[保存版](history/design-2026-09-28/research.md)にあります。参照IDはそのまま保持しています。

| ID | 調査対象 | 現在の位置付け |
|---|---|---|
| S01〜S03・S17〜S18 | 指導要領、LOD、解説、審議資料 | 採用した原典・取得版は上記の固定入力が基準。審議資料を告示済み原典と混同しない |
| S04〜S09 | CASE、SKOS、PROV-O、SHACL、QTI、xAPI | 外部交換・由来・評価・学習記録の参考。最新規格選定は未実施 |
| S10〜S12 | OLI Torus、Kolibri、Perseus | 教材制作・配布・表示・採点を検討する際の比較候補。採用は未決定 |
| S13〜S16 | Swift Package Manager、Result Builder、Codable、Swift Testing | 初期構成の検討資料。現在は共通モデル・CLI・テストを実装済み |
| S19〜S21 | 学術会議の参照基準、大学の科目一覧 | 高等教育へ広げる際の境界例。実在大学の到達目標の本格収録は未実施 |
| S22〜S24 | 小中の比例、出版社の指導計画・趣意書 | 初回の単元・粒度・閲覧順の選定資料。現在の収録を比例に限定しない |
| R01〜R03 | BKT、予測評価、pyKT | 将来の学習履歴・習熟度の検討材料。現在は推定モデルも履歴保存も未実装 |

外部公開の利用条件は[Issue #12](https://github.com/KantoYamamoto/Curricula/issues/12)、教材の執筆・根拠の方針は[Issue #11](https://github.com/KantoYamamoto/Curricula/issues/11)で整理します。
