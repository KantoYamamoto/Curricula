# Curricula

更新日: 2026-09-28 / 設計資料 v0.3 / 実装 pilot-0.1.0

**長期的には、小中高校の学習指導要領から大学教養までの学びを扱うデータ基盤を目指す。** 大学教養はまだ分野を絞らず、理数と人文・社会・語学の両方に広げられるか検討する。 最初の利用者は教材・学習アプリを作る開発者やAI、その先の用途は個人の自学を想定している。

これまでのユーザー回答も、今後変更できる「現時点の方針」として扱う。回答の履歴と理由を残し、調査・試作で得た根拠に応じて見直す。「ユーザーが選んだ」ことを、教育上・技術上の正しさの証明にしない。


## 起動する

Swift 6.0以上、Python 3.10以上。外部パッケージは不要です。macOSのSwift 6.4 / Python 3.14で確認。Linux Swift 6.0.3はGitHub Actionsで検証します。

```sh
make check   # Swift・HTTP API・交換契約・出力の再現性を検証
make serve   # 同梱JSONでローカルAPIと画面を起動
```

[読む](http://127.0.0.1:8000/read) / [構造を見る](http://127.0.0.1:8000/structure)。終了はCtrl+C。別ポートは `python3 scripts/serve.py --port 8001`。

データを編集したら `make export` でJSONを生成し、サーバーを再起動します。生成・テスト・起動時に原典サイトへアクセスしません。

```sh
swift run curricula validate
curl http://127.0.0.1:8000/api/v1/releases/pilot-0.1.0/entities/sm.proportion
```

## 初回実装の範囲

- 比例の7能力、補助能力1件、公式コード表4項目、少数の合成例。計20要素、10関係、4節。
- 安定ID、原典と独自編集の分離、出典版、条件、部分対応、文脈別の前提検証。
- 同じ版付きAPIを使う「読む」「構造を見る」。取得失敗・未調査・空結果を区別。
- 大学の合成項目は学年・文科省コードなしで記述可能。

前提調査は未完了です。データはAI下書きで、テスト成功は教育内容の妥当性の確認を意味しません。[初回レビューと残作業](docs/reviews/pilot-0.1.0.md)を参照してください。

## 構成と開発

| 場所 | 役割 |
|---|---|
| `Sources/Curricula` | 共通モデル、検証、正規化したJSON出力 |
| `Sources/CurriculaPilot` | Swiftによる小標本と版固定した原典入力 |
| `Sources/CurriculaCLI` | 検証・書き出しコマンド |
| `data/releases` | 同梱する版付きの交換データ |
| `scripts/serve.py` / `web` | ローカル読み取りAPIと閲覧画面 |
| `Tests` / `scripts/test_api.py` | モデル・APIの受入テスト |

[交換契約とAPI](docs/exchange-contract.md)。原典を再取得する場合は、次のように別ファイルへ候補を出し、ハッシュ・差分を確認してから採用します。独自の能力や対応付けは上書きしません。

```sh
python3 scripts/import_sources.py --retrieved-on YYYY-MM-DD --output /tmp/mext-candidate.json
```

## ライセンス

独自コードは [MIT](LICENSE)。原典由来の文章と独自データの扱いは [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) に記載しています。

## 現在の進め方

- Swiftで宣言的にデータを書き、JSON・読み取りAPIを介して、構造表示と教科書風の閲覧ページへ届けるローカルMVPを作る。
- OSSを目指す。AIで下書きし、小標本・構造・画面・内容を段階的にレビューする。専門家の確保は当面の要件にしない。
- 原典はMVP開始時点の最新の告示済み学習指導要領を確認し、取り込み時に版を固定する。
- MVPは**小6〜中1の「比例の意味と表・式・グラフの対応」**を初期選定とする。ユーザーから単元選定を委ねられた上での設計判断であり、検証結果に応じて変える。
- 関連する前提を小学校算数までたどる。小学校全教科・算数全領域の網羅はMVPの条件にしない。
- 高校・大学の少数の例を最初から構造の検証に使う。教材や前提をその段階まで全件整備することとは区別する。

## 資料

1. [要件と変更の扱い](docs/requirements.md)
2. [調査結果](docs/research.md) — v0.3の追加調査は末尾
3. [ドメイン設計](docs/domain-model.md) — 原典・教育上の枠組み・知識・能力の分離
4. [MVPの単元選定と小標本](docs/pilot-scope.md)
5. [高校・大学までの構造検証例](docs/architecture-cases.md)
6. [マイルストーン](docs/milestones.md)
7. [実装引き継ぎ](docs/implementation-brief.md)
8. [方針・変更・質問の記録](docs/decisions.md)
9. [閲覧ページ・APIと段階的な設計](docs/viewer-api.md)

原資料は[事前の壁打ち](docs/source/initial-concept.txt)。旧MVP候補は[一次方程式の検討履歴](docs/history/linear-equation-pilot-v0.1.md)に保存している。現行方針の参照先は上の資料とする。

初回の動作する小標本を実装済み。Swift宣言・機械検証・JSON・ローカルAPI・二つの閲覧画面を含む。全MVPの完了ではなく、原典全文照合・前提整備・移行例・内容レビューは継続課題。「将来矛盾が生じない」ことは事前に保証できないため、異なる教育段階・分野の例で構造を検証し、変更可能な境界を設ける。
