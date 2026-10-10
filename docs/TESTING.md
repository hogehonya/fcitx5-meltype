# 検証と受入条件

以下に2026-10-10の実機結果と継続する受入条件を示します。Androidコードは検証済み未mergeブランチにあり、このmainのコードだけで同じAPKを作れるとは扱いません。Linuxの動作をAndroidの証拠に流用しません。

## 2026-10-10のAndroid受入結果

[要件・VR対応](SPECIFICATIONS.md)のVR-02〜07を検証しました。詳しい実行記録・成果物SHA256は[plugin14cbeaaの検証正本](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/14cbeaa/docs/TESTING.md)を参照します。

|端末・接続|通常phase / 別process reload|GUI確認|
|---|---|---|
|moto g31 Android12 arm64、USB|2.829s / 最終host25で2.305s PASS|dark、日本語キー入力・Space候補・tap/Enter確定済み|
|F-52E Android16 arm64、USB|1.549s / 0.968s PASS|light、日本語候補表示・確定済み|
|Pixel7 Android17 arm64、USB|1.490s / 0.985s PASS|Fcitx有効/default確認、GUIは画面ロック解除待ち|

通常phaseはnihongo→日本語、kyouhagithubnipushshita→今日はgithubにpushしたの完全一致と非既定hashi候補のJSON保存を確認します。reloadは別processでSpace変換後の先頭候補とcommitへ学習が戻ることを確認します。ICU初期化・addonロード成功、.broken無しを確認。変換履歴のAOT読込はsource-generated serializerで修正済みです。

APK build/checker、Python30件、bridge engine、core186件が成功。16KB ELF LOAD alignmentは確認済みですが、16KB page端末、API24下限、変換履歴以外のJSON用途、全focus/回転/記号/矢印は実機未確認。Mozc固有学習callbackは未対応。host lintは既存269件で失敗、変更ファイル0件と分離記録しています。2026-10-10 15:55 JST確認時点でcore head CI17件中Ubuntu push core1件は成功（15:55:14）、残16件はWaiting/Blocked・aggregate pending。Windows/macOS適合runnerはなく、実装3PRは依存順にmerge保留。

この実機検証記録の時点ではAPKを `/home/honya/Downloads/Meltype-Android-20261010/` に保管し、GitHub Release未公開でした。後続の試用版公開状況は[導入案内](ANDROID-TRIAL.md)を参照してください。既存IMEを保持してhost25/plugin28を追加導入しました。

以下の項目は過去のmainビルド検証と、残る受入条件です。各項目を全て実機合格したという意味ではありません。

## ビルド成果物の検証 (自動)

[scripts/build-core.py](../scripts/build-core.py) は build の入力と成果物を自動で検証します。次が
合格条件で、1つでも外れたら成果物を残さず非 0 で終わります。実 build の実行記録は
[BUILD.md の実行記録](BUILD.md#実行記録)にあります。

- core の SHA が lock の固定値で、作業ツリーが clean
- `dotnet --version` と NDK の `Pkg.Revision` が lock の固定値
- core の `InvariantGlobalization=false` が維持されている
- publish ログと発生した警告が保存されている (警告の存在を成功条件にはしない)
- `llvm-readelf` で `ELF64` / `AArch64` / `DYN` (little endian) である
- `meltype_init` / `meltype_create` / `meltype_destroy` / `meltype_handle_key` / `meltype_commit` /
  `meltype_select_candidate` / `meltype_set_direct` / `meltype_free` / `meltype_set_data_directory`
  が定義済みシンボルとして export されている (`meltype_init@@V1.0` のような版付きも可)
- すべての `LOAD` セグメントの `p_align` が 16384 以上
- 成果物の SHA256 が manifest の記録と一致し、元 core に build 出力が残っていない

mainの旧NativeAOT単体成果物では未確認だった項目（Android完成ブランチの結果は上記）:

- 実機 Android での ICU/globalization の解決
- 設定・学習の JSON 保存（変換履歴のみ上記で確認）
- APK への収録と端末での動作

単体テスト (`tests/`) の内容と実行方法は [tests/README.md](../tests/README.md) を参照してください。

## build・ロード

- 固定core/host/submodule SHA、.NET SDK/runtime pack、JDK、NDK、SDK、ABIを記録し、新しいcloneから再現する。
- NativeAOT `.so`のarm64 ABI、C exports、SONAME/NEEDED、16KB ELF alignmentを確認する。APK packagingのalignmentも調べ、4KB/16KB環境で起動する。[Android 16KB検証](https://developer.android.com/guide/practices/page-sizes)
- host minSDK 23と採用NativeAOTのminimum APIを照合し、対応下限の端末でもdlopen・初期化が成功する。
- ICU/globalizationと必要ならcrypto/libsslを含め、依存不足・辞書不足時はエラーを示し、IMEサービスを落とさない。
- plugin APK導入後にMeltypeがFcitx入力方式一覧へ現れ、既存Mozc等と切り替えられる。

## ABI・寿命・保存

- callbackのUTF-8/NUL、NULL失敗、文節形式、malloc/free所有権を検証し、反復入力・focus切替・context破棄で漏れや二重解放を起こさない。
- key処理を同threadに直列化し、C++例外・managed例外をABIの外へ漏らさない。未対応keyは通常入力へ渡す。
- host IMEの私有filesDirに設定・学習が保存され、再起動後に再読込できる。readonly・容量不足・不正JSONでIME全体を落とさない。ログに入力内容やsecretを不用意に残さない。
- Mozc Learn callbackを実装した場合、候補確定とsave/restartで学習が反映される。未実装ならMozc学習未対応を明示し、Meltype側の学習と混同しない。
- wordProvider/isWordの辞書あり・なし両方で英語判定を確認する。NULL経路を完成した辞書実装として扱わない。

## 入力とUI

- soft keyboardとhardware keyboardで英語、日本語、混在入力を試す。例として`kyouhagithubnipushshita`の期待結果「今日はgithubにpushした」を確認し、端末・設定・実入力操作を記録する。
- Space変換・複数候補表示・候補tap・確定・Backspace・Enter・direct切替がcommit/preeditへ正しく反映される。
- surrounding textが取得できる場合とできない場合を確認する。focus移動、reset、アプリ切替、password入力欄で未確定文字・学習の扱いを確認する。
- 日本語候補、英語保持、文節境界、空文字、非BMP文字についてcursor/UTF-16とFcitx側の位置単位を照合する。

[ビルド](BUILD.md) / [構成](ARCHITECTURE.md) / [文書一覧](README.md)

## Linux addon の実行済み検証

[addon/README.md](../addon/README.md) の実 NativeAOT / Fcitx InputContext integration test と、隔離 D-Bus / Xvfb の GTK 混在文入力が成功しました。Android APK と端末試験の成功を意味しません。

S-09/VR-09のLinux受入は、実provider/Fcitx InputContext integrationと異常回復の既存2tests（2/2成功）に加え、隔離D-Bus/XvfbのGTK入力欄で`kyouhagithubnipushshita` + Enter → `今日はgithubにpushした`の完全一致です。Linux配布v1.0.0 provider/helperを使用し、Android NativeAOT成果物の試験結果で代替しません。再実行のbuild/ctest手順は[addon手順](../addon/README.md#実-core--fcitx-inputcontext-test)を参照します。

共通`engine.cpp`、`session.h`、`meltype_abi.h`、providerのABI/JSON/キー処理を変更した場合は、Android試験だけで完了せず、このLinux2testsと隔離GTK混在入力を再実行します。使用provider・helper・Fcitx版、変更revision、コマンド、期待/実結果を本書または関連Issueへ記録し、実行不能なら理由とLinux受入未完を明記します。文書のみの今回変更は実装差分がなく、過去成功を今回再実行成功とは扱いません。

## hostキーボードの設計受入

[R-03要求](REQUIREMENTS.md)と[基本設計](ARCHITECTURE.md)の受入項目です。moto dark/F-52E lightの日本語操作は上記で確認済み。次の全操作の網羅検証とPixel GUIは未完です。

- QWERTY・数字行を維持しローマ字・英語・混在入力のラベルと入力結果を照合する。
- 主画面`@`・句読点、記号面への到達と復帰、左右矢印を確認する。
- 候補表示とtap対象が一致しaddonへeventが届き正しい候補を確定する。
- IME切替と配列/記号面切替のラベル・操作・結果を区別し既存入力を維持する。
- light/dark双方でキー境界・文字・候補・選択状態が読める。日本語デザイン成果物の実装はIBM Plex Sans JPを使用する。
- 実機画面と操作で採否を記録する。12キー/フリックは別途採用決定が必要。

## 2026-10-10 文献基準による状態点検

対象は文書main `e73ed756`とIssue #15の文書修正、実装core `87b1ae13` / plugin `41a79d4` / host `e264cffa`です。今回の変更は文書のみで実装コードは変えていません。

文献の整理正本は[Gitea調査文書](https://gitea.honya.dev/honya-records/investigations/src/branch/main/2026-10-10-requirements-engineering-literature.md)です。[NASA System Design Processes 4.0](https://www.nasa.gov/reference/4-0-system-design-processes/)の4.1目的・利用場面、4.2検証可能性と追跡、4.3機能分解、4.4設計判断、および[Appendix C](https://www.nasa.gov/reference/appendix-c-how-to-write-a-good-requirement/) C.4を点検の観点に使います。[IPA要件定義ガイド](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/youkenteigi20190912.html)は公式概要・章構成まで確認しています。[IPA公式目次](https://www.ipa.go.jp/archive/publish/tn20191220.html)の第7章7.12非機能要求・7.13運用/移行/総合テストを確認しましたが、498ページの全文は未読です。NASA Appendix C C.4は曖昧さ、一要件一内容、双方向追跡、性能、異常復旧、検証可能性の本文を確認しました。書籍・ISO本文は精読しておらず、正式な規格適合審査ではありません。

|観点|確認した事実|未確認・不足|
|---|---|---|
|目的・要求出所|R-01〜05とIssueにユーザー要求・日時・出所を記録|日常利用の成功条件は部分的|
|追跡|R→S/NF→VR→試験参照あり。今回Linux S-09/VR-09を追加|全受入項目を実測済みという意味ではない|
|検証可能性|代表文字列の完全一致と学習復元は判定可能|遅延・メモリ等の目標は未決。Agentが数値を追加しない|
|構成・設計|3repo、入力・状態・ビルド工程、ソース所属とAPK収録の図を記述|主要方式の比較・不採用理由は不足|
|異常時・運用|ABI異常回復の記述と受入計画あり|容量不足・辞書欠損・password/focus/回転の実機証拠は不足|
|受入|Android3台instrumentation、Linux2testsと隔離GTKの成功記録あり|Pixel GUI、下限API、16KB page端末等は未確認|
|変更・公開|Issue/PR/SHAとソース・APK公開状態を区別|点検時点では実装PRはCI未完・未merge、APKはGitHub Release未公開。後続の試用版は[導入案内](ANDROID-TRIAL.md)を参照|

実機試用に進める実装と設計の骨格はありますが、要求全体の完了判定、異常系・非機能の証拠、実装の統合公開は未完です。上表の不足は提案・未決事項として記録し、この状態点検を根拠に追加機能や数値目標を確定しません。最新のCI・公開状態は[公開状況](../README.md#androidのビルドとapk入手)と実装PRを参照します。

## Linux 英字直接入力の検証（Issue #20）

2026-10-10、Linux配布v1.0.0 provider/helper、Fcitx5 5.1.12、G++14.2.0を同じ固定入力として使用。新受入testを旧engineへ適用すると `Muhenkan consumed` でintegration失敗（Red）、実装後はctest 2/2成功。直接キーpass-through、通常Meltype復帰、context独立、pending/候補の一回commit、release/修飾キー保持、mode表示/解除後保持を検証した。`addon/README.md`のcmake/ctest手順を利用し、HOME/Mozc profileは `/home/honya/tmp/fcitx5-english-mode/green-home` に隔離した。GUI検証は別途Issue #20へ記録し、ここで実行済みとは扱わない。既存Android APK・対応ソースassetは変更しない。
