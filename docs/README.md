# ドキュメント一覧

現行文書の確認日：2026-10-11。利用・開発の説明は現在の実装に基づきます。将来案はIssueで検討し、決定後に仕様へ反映します。過去の計画・検証結果は対象版を示して保存しています。

## 使う・編集する

| 目的 | 資料 |
|---|---|
| 起動し、使える機能を知る | [README](../README.md) |
| どこまで収録・整理したか、次に何を整理するか | [原文収録と作業台帳](curriculum-coverage.md) |
| 下書き、根拠、レビュー、新しい版、バックアップを扱う | [ローカル編集](local-editing.md) |
| 教科書・問題集の試作を使う | [教材試作](learning-preview.md) |
| 原典と独自データの利用条件を調べる | [外部資料の利用条件](../THIRD_PARTY_NOTICES.md) |

## 開発・データを利用する

| 目的 | 資料 |
|---|---|
| 実装の構成と変更手順を知る | [開発の引き継ぎ](implementation-brief.md) |
| 原文・目標・根拠・前提の区別を理解する | [ドメイン設計](domain-model.md) |
| 画面とHTTP APIを使う | [閲覧・API](viewer-api.md) |
| UUID・フィールド・検証規則を確認する | [交換契約0.2.0](exchange-contract-0.2.md) |
| 旧データを読む | [旧交換契約0.1.0](exchange-contract.md) |
| 修正・分割・統合のIDを扱う | [IDと編集操作](identity-editing.md) |
| SQLiteの役割と今後の移行条件を理解する | [DBと編集基盤](database-editing-plan.md) |

## 計画・根拠を確認する

| 目的 | 資料 |
|---|---|
| 長期目標と現在の要件を知る | [要件](requirements.md) |
| 実装済みの増分と今後の設計課題を知る | [工程と進捗](milestones.md) |
| 方針の変更理由をたどる | [方針台帳](decisions.md) |
| 標本の選定目的を知る | [小標本の範囲](pilot-scope.md) |
| 教科別の原典・構造確認を調べる | [教科横断の検証](cross-subject-validation.md) |
| 境界例と契約ごとの対応状態を調べる | [構造検証例](architecture-cases.md)、[標本カタログ](sample-catalog.md) |
| 参照資料と取り込みでの役割を知る | [資料一覧](research.md) |

設計の議論と未決事項は[親Issue #1](https://github.com/KantoYamamoto/Curricula/issues/1)から参照できます。[Issue #2](https://github.com/KantoYamamoto/Curricula/issues/2)の公開範囲・優先順位は提案段階で、最終決定待ちです。

## 過去の記録

検証記録は当時の版に対する結果です。現在の全機能の検証済み一覧としては扱いません。

- [初回の比例標本](reviews/pilot-0.1.0.md)
- [構造標本と教科横断標本](reviews/structure-samples.md)
- [契約0.2.0](reviews/schema-0.2.0.md)
- [ローカル編集](reviews/local-editing.md)
- [小中の原文収録](reviews/curriculum-0.3.0.md)
- [国語「読むこと」の目標整理](reviews/reading-authoring.md)
- [初期設計の保存版](history/design-2026-09-28/README.md)
- [一次方程式を対象にした最初の案](history/linear-equation-pilot-v0.1.md)
