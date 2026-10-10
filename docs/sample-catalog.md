# 構造を確かめる標本カタログ

確認日：2026-10-11。実原典の教科横断標本に加え、改訂や機関別経路を意図的に作った補助例を使います。データ版名とスキーマ版は別です。`examples-0.2.0` は旧スキーマ0.1.0のデータ版で、現契約0.2.0の標本ではありません。

## データと再現

| データ版 | スキーマ | 用途 |
|---|---|---|
| `pilot-0.1.0` | 0.1.0 | 初回の比例の標本。公開時の内容を保持 |
| `examples-0.1.0` / `examples-0.2.0` | 0.1.0 | 実原典4項目と機関・定義・科学・歴史・語学の合成例、改訂候補 |
| `cross-subject-0.1.0` | 0.1.0 | 8教科11例の旧契約版。69原典・9対象・11能力 |
| `cross-subject-0.2.0` | 0.2.0 | 同じ原典を現契約で表現。69原典・9対象・12目標・13注釈・128根拠 |
| `editing-0.2.0`〜`editing-0.2.3` | 0.2.0 | 編集、分割・統合、後継追跡、AND/OR、資料種別 |

```sh
make check
make serve
```

[旧契約の構造標本](http://127.0.0.1:8000/read?release=examples-0.1.0)、[現契約の教科横断標本](http://127.0.0.1:8000/read?release=cross-subject-0.2.0)、[編集・経路の標本](http://127.0.0.1:8000/read?release=editing-0.2.0)を確認できます。通常の初期表示は全原文に国語の整理結果を加えた `reading-0.3.1` です。

補助例の実装は [StructureSamples.swift](../Sources/CurriculaPilot/StructureSamples.swift)。大学・架空課程は合成例と表示します。概念の出典は[根拠の扱い](cross-subject-validation.md#根拠の扱い)を参照してください。

## 現契約で追加した確認

| 旧契約で不足したもの | 0.2.0での表現と確認 |
|---|---|
| A06 資料種別・非告示資料のメタデータ | `sources.kind` と書誌・告示・取得情報を分離。合成シラバス・参照基準・書籍を保持 |
| A12/A14 正式な編集・分割・統合 | `changes` と `retired`・`successorIDs`。旧新版のIDと改訂、理由を追跡 |
| A13 AND/ORと別経路 | `goal` / `allOf` / `anyOf`。文脈ごとの到達可能性を検証 |
| 学年帯の検索 | 専用 `education`。未指定・非該当と明示学年を区別 |
| 条件・観点ごとの根拠 | 対象フィールドと原典項目の改訂を結ぶ `evidence` |
| 判定の観点 | 独立した `annotations`。ソフトウェア判定を登録条件にしない |

仕様は[交換契約0.2.0](exchange-contract-0.2.md)、操作例は[IDと編集操作](identity-editing.md)。テストは [Tests/CurriculaTests](../Tests/CurriculaTests) と [scripts/test_api.py](../scripts/test_api.py) にあります。具体的な歴史資料・批判関係の整備、大学のコース・単位管理、汎用採点・証明は追加していません。

## 旧契約0.1.0での観点と結果

「確認」はその小標本に限った構造確認。「部分」は一部の意味を保持できるが必要な表現が残る。「未対応」は不十分な入力を捨てたりダミー値で埋めたりせず、実行可能な検証で不足を示す。

| 例 | 入力・参照ID | 確かめる振る舞い | 結果 |
|---|---|---|---|
| A01 | sm.proportionを小6と中1へ対応 | 知識を複製せず枠組みと対応を分ける | 確認 |
| A02 | cp.link-positive / cp.link-signed | 同じ対象でも条件と達成観点を同一視しない | 確認 |
| A03 | sm.proportion / sm.affine / sm.linear-map | 比例・b≠0の一次関数・線形写像を区別し、関連で結ぶ | 確認。一般化・制限の推論はしない |
| A04 | fw.university-a / fw.university-b、2026/2027 | 同じ線形写像を異なる機関・年度へ対応。文科省コード・学年のダミーは不要 | 確認 |
| A05 | dep.a-definition-example / dep.b-example-definition / enroll.a-example-definition | 逆向きでも文脈が違えば許可。履修規則を学習前提へ変換しない | 確認。コース単位の履修管理は範囲外 |
| A06 | unsupported.jsonの参照基準・シラバス | 発行主体・資料種別・適用範囲を区別。架空資料に告示日・取得日・実在URLを要求しない | 未対応を確認。SourceDocumentの必須フィールドとkind/scope/origin不足を検出 |
| A07 | sm.naturals-zero / sm.naturals-positive | 「自然数」の同名を統合せず、0を含む/含まない約束を保持 | 確認 |
| A08 | sm.gas-model / sm.right-triangle | 理想気体の近似条件と直角三角形の定理の成立条件を別の分類・条件で保持 | 確認。条件文の数学的証明はしない |
| A09 | sm.interpretation-a / sm.interpretation-b / cp.discuss | 異なる架空解釈・観点を併記。片方を真と判定しない | 部分。立場・編集理由は保持、具体的な史料出典・批判関係の収録は残る |
| A10 | cp.language-peer / cp.language-visitor | 同じ対象でも相手で能力・達成観点を分ける。単一の正解文は不要 | 確認 |
| A11 | fi.inquiry-attitude → cp.discuss | 広い態度目標は保持し、討論能力の部分対応と未収録部分を明示 | 確認 |
| A12 | fi.high-school-functions → fi.high-school-formula / properties | 旧版・新版で項目と対応を再現。分割の理由を候補表で追跡 | 部分。スナップショットと候補参照を検証。移行関係の正式な契約/APIは未対応 |
| A13 | 文脈別必須・相互推奨・anyOf [[A],[B,C]] | 必須循環は同文脈のみ。Aまたは(BかつC)を三本の必須辺へつぶさない | 部分。必須/推奨は確認、AND/ORの原入力は候補として保持しalternative辺は拒否 |
| A14 | fi.university-b-mapの外部コード、sm.affine-expanded | コードだけの変更は知識IDを維持。定義条件の変更は新IDと旧定義を保持 | 部分。2版で確認し理由を候補表に記録。自動移行は未対応 |
| 補助 | cp.multiply / cp.boundary | 前提一覧が空でも未調査と探索の停止点は違う | 確認 |
| 補助 | 同じ対象を参照する目次を並べ替え | 対象ID・意味・関係を変更しない | 確認 |

## 不正例と不足を検出する例

[StructureSamplesTests.swift](../Tests/CurriculaTests/StructureSamplesTests.swift)でA01〜A14を個別テストとして対応付ける。全ての正常例をJSONに書き戻し、参照と条件・分類・対応範囲が残るか検証する。既存の[検証テスト](../Tests/CurriculaTests/CurriculaTests.swift)も維持する。

- A大学とB大学の逆方向の必須前提を同じ文脈へ移すと、循環として拒否される。
- 履修規則を誤って学習前提へ変えると、今回の例では循環が顕在化する。
- 態度目標の対象外範囲を残したまま完全対応に変えると、矛盾として拒否される。
- A06の合成資料は、契約0.1.0のSourceDocumentへ直接デコードできないことを期待結果にする。このテストの成功は「資料を取り込めた」ことを意味しない。
- A13の代替経路は未対応として拒否し、AND/ORの元のまとまりを検証資源へ残す。
- A12/A14の改訂対応候補は実在する旧新版のIDと理由を持つが、契約0.1.0に含まれていないことも確認する。

[unsupported.json](../Tests/CurriculaTests/Fixtures/unsupported.json)は不足を検討するための**契約外の候補入力**であり、公開APIが対応済みの仕様ではない。A06の資料を実在の出典としてDBへ投入したり、A12/A14の候補を証明済みの同値対応と扱ったりしない。旧契約の期待された失敗は互換性の確認として維持する。現契約の対応は別の成功例・不正例で確認する。


## 結果を読むときの注意

上のA01〜A14の表は旧契約に対する結果です。旧契約で未対応だったものを、現在も全体で未実装と解釈しません。`unsupported.json` は旧契約の候補入力を保持する資源で、投入用の正式データではありません。DB化だけでは概念不足を解決できないため、契約・検証・保存・APIを揃えて変更します。
