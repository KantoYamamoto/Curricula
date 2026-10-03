# Curricula

学習指導要領、学ぶ対象、できることを結ぶデータ基盤。Swiftの共通モデルから版付きJSONを出力し、ローカルAPIを通じて「読む」「構造を見る」の二つの画面で確認できます。長期的には小中高校から大学教養までを対象にします。

## 起動する

Swift 6.0以上、Python 3.10以上。外部パッケージは不要です。

```sh
make check   # モデル・HTTP API・交換契約・出力の再現性を検証
make serve   # 同梱JSONでローカルAPIと画面を起動
```

[読む](http://127.0.0.1:8000/read) / [構造を見る](http://127.0.0.1:8000/structure)。終了はCtrl+C。別ポートは `python3 scripts/serve.py --port 8001`。

Swift小標本のデータを編集したら `make export` でJSONを生成し、サーバーを再起動します。通常の生成・テスト・起動時に原典サイトへアクセスしません。公開済みデータの更新は新しいデータ版として追加します。

## 今回の検証範囲

**国語・理科・社会・外国語・音楽・道徳・算数・情報の8教科、11例**を実際の学習指導要領から選びました。比例に限定せず、学年帯、実験の条件制御、資料に基づく考察、合奏、態度目標、プログラミングの評価・改善を扱います。

- `cross-subject-0.2.0`：初期表示。原典69項目、学ぶ対象9件、目標12件、判定注釈13件、構造化した根拠128件。学年・教科・科目の検索に対応。
- `editing-0.2.0`〜`editing-0.2.3`：UUIDを維持した編集、分割・統合と後継追跡、AND/OR前提、複数種類の出典。
- `examples-0.1.0` / `examples-0.2.0`：機関別経路、同名の定義、項目分割、改訂、未対応入力の補助標本。
- `pilot-0.1.0`：最初の比例の小標本。公開時の内容を保存。

[教科横断の選定理由・原典コード・確認結果](docs/cross-subject-validation.md)、[補助小標本カタログ](docs/sample-catalog.md)、[検証記録](docs/reviews/structure-samples.md)に詳細があります。前回見つかった学年帯の属性化、根拠の構造化、資料種別、改訂対応、AND/OR経路は[契約0.2.0](docs/exchange-contract-0.2.md)で実装しました。目標を残し、判定の観点を任意の自然言語注釈として分離しています。旧契約と公開済みデータは引き続き利用できます。

説明の根拠は学習指導要領を優先し、必要に応じて文科省解説や信頼できる学術資料を参照します。初等教育の自明な概念に一律の引用は要求しません。

## wiki編集とDB移行

**SQLiteに下書きを保存するローカル編集**を実装しました。独自の本文・条件・判定観点の編集と追加、根拠の引き継ぎ、差分・履歴確認、新しいデータ版の作成ができます。

```sh
make serve-edit
```

[編集する](http://127.0.0.1:8000/edit)。下書きは `.local/curricula.sqlite3` に保存され、再起動後も残ります。元の公開版は保持し、確認済みの下書きから不変の新しい版を作ります。編集競合や未確認の根拠を検出します。

[操作・保存・バックアップ](docs/local-editing.md)、[検証記録](docs/reviews/local-editing.md)、[DB移行方針](docs/database-editing-plan.md)。編集起動時はDBが保存元となり、Swift小標本と同梱JSONは初期投入・回帰確認用です。通常の `make serve` は閲覧専用で起動します。

## 構成と開発

| 場所 | 役割 |
|---|---|
| `Sources/Curricula` | 共通モデル、検証、正規化したJSON出力 |
| `Sources/CurriculaPilot` | 小標本の編集記述と版固定した原典入力 |
| `Sources/CurriculaCLI` | 検証・書き出しコマンド |
| `data/releases` | 版付きの交換データ |
| `scripts/serve.py` / `web` | 読み取りAPIと閲覧画面 |
| `scripts/editing_db.py` / `editing_api.py` / `web/edit.js` | SQLite、ローカル編集APIと画面 |
| `Tests` / `scripts/test_api.py` | モデル・APIの受入テスト |

[交換契約とAPI 0.2.0](docs/exchange-contract-0.2.md)、[IDと編集操作](docs/identity-editing.md)。原典の再取得は既存ファイルを上書きせず、候補のハッシュ・差分を確認して採用します。

```sh
python3 scripts/import_cross_subjects.py --retrieved-on YYYY-MM-DD --output /tmp/cross-candidate.json
curl http://127.0.0.1:8000/api/v1/releases/cross-subject-0.2.0/entities/cp.cross-language-write
```

## 資料とライセンス

[0.2.0の検証記録](docs/reviews/schema-0.2.0.md)。現在の方針は[変更記録](docs/decisions.md)、構造は[ドメイン設計](docs/domain-model.md)を参照してください。[実装引き継ぎ](docs/implementation-brief.md)、[初期の単元選定](docs/pilot-scope.md)、[初回レビュー](docs/reviews/pilot-0.1.0.md)には過去の計画・検証を残しています。

独自コードは[MIT](LICENSE)。原典由来の文章と独自データの扱いは[外部資料の利用条件](THIRD_PARTY_NOTICES.md)に記載しています。
