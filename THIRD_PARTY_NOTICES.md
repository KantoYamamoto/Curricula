# 外部資料とライセンスの境界

独自コードは [MIT License](LICENSE)。原典由来の文章をMITへ変更するものではありません。独自の教育データ・設計資料のデータライセンスは未決定です。

## 文部科学省のコード表

出典：文部科学省「学習指導要領コード表」

- [小学校・平成29年告示・82V12](https://www.mext.go.jp/content/20230901-mxt_syoto01-000013115_73.csv)
- [中学校・平成29年告示・83V11](https://www.mext.go.jp/content/20230901-mxt_syoto01-000013115_37.csv)
- [高等学校・平成30年告示及び一部改正・84V10](https://www.mext.go.jp/content/20230901-mxt_syoto01-000010374_01.csv)
- 取得日：2026-09-28
- [文部科学省ウェブサイト利用規約](https://www.mext.go.jp/b_menu/1351168.htm)（確認時の最終改正：令和8年8月17日）。出典表示と加工の明示を行い、この規約に従って利用します。

初回は4項目、教科横断標本は親見出しを含む69項目を上記CSVから抽出し、JSONへの変換、独自IDの付与、知識・能力との対応付けを行っています。原典テキスト自体は抽出元の文字列を保持しています。これらの編集・対応付けはCurriculaによるもので、文部科学省が作成・承認したものではありません。

抽出結果は `Sources/CurriculaPilot/Resources/mext-sample.json` と `cross-subjects.json`、配布用データは `data/releases` に含みます。各出典のURL、配布版、取得日、元CSV全体のSHA-256、引用位置を保持しています。

2026-10-05の全範囲収録では、現行一覧に記載された[小学校82V12](https://www.mext.go.jp/content/20230901-mxt_syoto01-000010374_27.csv)・[中学校83V11](https://www.mext.go.jp/content/20230901-mxt_syoto01-000010374_09.csv)を配布時のバイトで `data/sources/mext` に保存しています。以前の取得URLと内容のハッシュは一致しています。CSV全5,937項目と、[小学校本文PDF](https://www.mext.go.jp/content/20230120-mxt_kyoiku02-100002604_01.pdf)・[中学校本文PDF](https://www.mext.go.jp/content/20230120-mxt_kyoiku02-100002604_02.pdf)の前文を交換データへ変換しました。前文は柱・ページ番号・ルビを除き段落内の改行を接続しました。本文、原典の位置、取得日、元ファイルのSHA-256を保持しています。

## 学習指導要領LODの補助メタデータ

出典：教育データプラス研究会「[学習指導要領LOD](https://jp-cos.github.io/)」。データの利用条件は [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。取得日：2026-10-05。

- [学習指導要領細目 20220830](https://jp-cos.github.io/cs-items-20220830.ttl.gz)
- [階層 20240704](https://jp-cos.github.io/section-hierarchy-20240704.ttl)

小学校・中学校の全コードに対応する学年・分野・親子関係を抽出し、`data/sources/mext/metadata.json` に同梱しています。章をまたぐ親関係9件を公式PDF目次に基づき変更しました。変更箇所、取得した元データのURL・SHA-256を同ファイルに記録しています。本文は文科省CSVから取得しており、LOD由来の本文は同梱しません。

出版社の教科書本文は取り込んでいません。大学・歴史の合成例は独自に作成した構造検証用の例であり、実在する機関の到達目標ではありません。

OpenStaxとNicholsonの教科書は概念の根拠として参照し、本文の転載・データセットの取り込みは行っていません。対応する概念とURLは[教科横断の検証記録](docs/cross-subject-validation.md#根拠の扱い)に記載しています。
