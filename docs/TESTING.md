# 実装後の検証

以下はAndroid実装の受入条件と実行記録です。過去の検証結果と未実施項目は区別し、Linux結果をAndroidの合格証拠に流用しません。


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
 / `meltype_set_prediction_callback`
  が定義済みシンボルとして export されている (`meltype_init@@V1.0` のような版付きも可)
- すべての `LOAD` セグメントの `p_align` が 16384 以上
- 成果物の SHA256 が manifest の記録と一致し、元 core に build 出力が残っていない

Android 12でaddonロード、ICU初期化、日本語変換、変換学習JSONの保存・再読込を確認しました。他の設定・学習JSON用途と他APIの実機確認は未実施です。

単体テスト (`tests/`) の内容と実行方法は [tests/README.md](../tests/README.md) を参照してください。

## build・ロード

- 固定core/host/submodule SHA、.NET SDK/runtime pack、JDK、NDK、SDK、ABIを記録し、新しいcloneから再現する。
- NativeAOT `.so`のarm64 ABI、C exports、SONAME/NEEDED、16KB ELF alignmentを確認する。APK packagingのalignmentも調べ、4KB/16KB環境で起動する。[Android 16KB検証](https://developer.android.com/guide/practices/page-sizes)
- host minSDK 23、plugin minSDK 24と採用NativeAOTのminimum APIを照合し、対応下限の端末でもdlopen・初期化が成功する。
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

[In-process Mozc bridge・native buildと契約](../native/README.md)（Issue #5）。APK/端末統合は別工程です。

S-09/VR-09のLinux受入は、実provider/Fcitx InputContext integrationと異常回復の既存2tests（2/2成功）に加え、隔離D-Bus/XvfbのGTK入力欄で`kyouhagithubnipushshita` + Enter → `今日はgithubにpushした`の完全一致です。Linux配布v1.0.0 provider/helperを使用し、Android NativeAOT成果物の試験結果で代替しません。再実行のbuild/ctest手順は[addon手順](../addon/README.md#実-core--fcitx-inputcontext-test)を参照します。

共通`engine.cpp`、`session.h`、`meltype_abi.h`、providerのABI/JSON/キー処理を変更した場合は、Android試験だけで完了せず、このLinux2testsと隔離GTK混在入力を再実行します。使用provider・helper・Fcitx版、変更revision、コマンド、期待/実結果を本書または関連Issueへ記録し、実行不能なら理由とLinux受入未完を明記します。文書のみの今回変更は実装差分がなく、過去成功を今回再実行成功とは扱いません。

## hostキーボードの設計受入

既存host UIを基準にした[要求](ARCHITECTURE.md)の今後の試験です。Gboard/ATOKを参考にする新設計と、Meltypeを統合したAndroid host・APKを生成済みです。下記に実機で確認した結果を記録します。buildと実行手順は[Android手順](../android/README.md)を参照してください。

- QWERTY・数字行を維持しローマ字・英語・混在入力のラベルと入力結果を照合する。
- 主画面`@`・句読点、記号面への到達と復帰、左右矢印を確認する。
- 候補表示とtap対象が一致しaddonへeventが届き正しい候補を確定する。
- IME切替と配列/記号面切替のラベル・操作・結果を区別し既存入力を維持する。
- light/dark双方でキー境界・文字・候補・選択状態が読める。日本語デザイン成果物の実装はIBM Plex Sans JPを使用する。
- 実機画面と操作で採否を記録する。12キー/フリックは別途採用決定が必要。

## Android実機の実行記録（2026-10-10、Issues #5/#8）

依頼: ユーザーのAndroid plugin完成・接続端末追加、およびGboard/ATOK参考キーボード要求（plugin Issue #8、host Issues #9/#10）。端末はmoto g31 `ZY22FBW7BR`、Android 12、arm64-v8a。既存ATOKを保持しdebug hostとpluginを追加しました。

検証した成果物:

|用途|APK version|SHA256|
|---|---|---|
|host|`0.1.3-25-gab2f5117` arm64 debug|`09dae1550ebfad2c7fc12206df7777d7c1d72dccc0eb739e8a7ea79d262cf9ab`|
|instrumentation|`0.1.3-25-gab2f5117` debug AndroidTest|`b22e0aebdc8936f23a380e2bdfa7253d5a1e3a6c5f4f7050f3662976f19d6eae`|
|plugin|`0.1.3-28-g65922d39` arm64 debug|`be496fe31cfc059209e05abe8950359204a9c7ad4d3cd46a00ba8379a8314995`|

配布APKは `/home/honya/Downloads/Meltype-Android-20261010` に保管し、実機の最終導入はhost 25 / plugin 28です。

plugin source `3353260`、固定core `87b1ae13e95144266f9e69d8b20d42f00aa0e26e`。APK内NativeAOT provider SHA256は `200b5150bc97afa7c01f5d28825fa430bda18d19539de9c66990a13101725339` でbuild manifestと一致。テストAPKはbuild metadataのcommit後に追加したreload仕様修正（host `9821b319`）を含みます。host product codeは同じで、その後のgitlink・文書更新による再buildは不要です。

- `Loaded addon meltype`を実機logcatで確認。初回のSONAME欠落は正式publishのLinkerArgで修正済み。
- `MeltypeTest`通常実行 PASS（2.829秒）: `nihongo`→候補選択→`日本語`、`kyouhagithubnipushshita`→`今日はgithubにpushした`の完全一致、非既定漢字候補のJSON保存。
- 別processの `-e phase reload` PASS（2.215秒）、最終host APK更新後の再確認もPASS（2.305秒）: 保存した読みをSpaceで変換した際の先頭候補と、候補を選び直さずReturnで確定した文字列が保存した学習結果と一致。
- 保存先はnative正本 `DataManager.dataDir/files/meltype`（この端末ではdevice-protected storage）。ConversionHistoryのNativeAOT reflection読込失敗はsource-generated metadataで修正。既存JSON形式、不正JSON、保存後の別instance読込、Forgetをcoreテストで確認し全186/186 PASS。
- GUIでMeltypeを選択し、ソフトキー7tapで `nihongo`→`日本語` preedit、Spaceで `日本語/ニホンゴ/にほんご/Japanese`候補表示、先頭候補tap＋Enterで`日本語`確定。dark Pixelのキー境界、数字行、左右矢印、IBM Plex Sans JP表示を確認。
- GUI証拠は実施環境の `/tmp/meltype-touch-nihongo.png`、`/tmp/meltype-candidates-ready.png`、`/tmp/meltype-touch-commit.png`。リポジトリへの画像収録はしていません。
- 正規NativeAOT/Gradle build成功、Python30/30 tests成功、APK checkerでarm64・SONAME・symbol version provider・DT_NEEDED・RUNPATH・ELF 16KB alignment・assetsを検証。plugin lintDebug成功（警告5件）。

未実施・制限:

- Android 12/16/17以外、plugin最低API 24、16KB page size端末は実機未確認。ELF 16KB alignmentの静的検査成功を16KB実機起動成功とは扱いません。
- Settings、UserModel、LanguageMemory、TranslationHistory等、変換履歴以外のJSON用途の実機保存・再読込は未確認。既存IL2026/IL3050警告を抑制していません。
- Mozc固有learning callbackは未公開で未対応。確認した保存・復元はMeltype側の変換学習です。
- hardware keyboard、端末rotation、password欄、容量不足等の全受入条件は今回の実機検証に含みません。light表示は下記F-52Eで確認しました。
- host lintDebugは既存269件（UseAppTint 1、StringFormatMatches 2、MissingTranslation 266）で失敗。今回変更したファイルにあるerrorは0件で、baselineやgate無効化はしていません。
- Linux-x64 NativeAOT smokeはruntime pack未取得・repository NuGet sources設定によるNU1100で未完了。Android NativeAOTビルドと上記実機reloadで修正を検証しました。

### 追加端末の要求・実機記録（2026-10-10 15:07 JST）

要求者はこの会話のユーザー。親agentから伝達された追加要望は「Pixel 7とF-52Eにも同じ導入」「USB指定」です。既存の配布APKを使い、他IMEを保持したまま追加します。新機能・CI変更・runner新設への範囲拡張ではありません。

- F-52E `ZH2AA2PQFB`、Android 16、arm64-v8a: USBで上記配布host/plugin/test APKを `install -r`、すべて成功。通常instrumentation PASS（1.549秒）、別process reload PASS（0.968秒）。light GUIでMeltypeを選択し、`nihongo`→`日本語`候補表示と確定を確認。証拠は `/tmp/meltype-f52e-nihongo.png` と `/tmp/meltype-f52e-commit.png`。
- Pixel 7 `29081FDH200DGG`、Android 17、arm64-v8a（2026-10-10 15:20 JST追記）: 同じhost/plugin APKはUSB指定前に無線ADBで導入済み。USB指定後は無線操作を停止し、USB接続に切り替えてtest APKを導入。通常instrumentation PASS（1.490秒）、別process reload PASS（0.985秒）。USBでFcitxのIME enable/set成功、有効かつ既定IMEであることを確認。本体/pluginは先の導入を継続使用しています。GUIはユーザーへの解除依頼中で、確認時点ではkeyguard showing=true・画面OFFのためタップ操作を未確認です。解除後のGUI結果はこの正本へ追記予定です。

2026-10-10 15:55 JST確認時点でcore PR #8のhead CI17件中Ubuntu push core1件は成功（15:55:14）、残16件はWaiting/Blocked・aggregate pending。Windows/macOS適合runnerはありません。このため、core→plugin→hostの依存順mergeは保留です。今回の端末追加でソースをmerge済みとは扱いません。未mergeのbranches/worktreesと配布APKを保持します。

## 要件との対応

[要求](REQUIREMENTS.md)・[要件のS/NF/VR対応](SPECIFICATIONS.md)・[基本設計](ARCHITECTURE.md)から本書の実測を参照します。VR-02〜07は上記Androidビルド・通常/reload・GUI試験に対応します。main公開用の要約は[公開main TESTING](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/branch/main/docs/TESTING.md#2026-10-10のandroid受入結果)にあります。

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

## 入力途中の予測（Issue #27）

core予測3件と全189件、Native ABI managed build、plugin Python30件が成功。純日本語入力途中候補、tap即確定、未完ローマ字抑制、Backspace再表示、通常Space変換、provider失敗/英数を検証。新bridge sourceを隔離/tmp objectへcompileし、既存の固定Mozc archivesとlinkした実engine試験で「にほ」→「日本」包含、NULL/空入力、反復20回の予測freeと通常変換回帰が成功。上流deprecated警告、空の隔離profileに対する未作成辞書/historyログを記録。新artifact・APK GUIは統合担当が別途検証し、core/bridge成功を代用しない。上行削除は意図確認まで保留。

## かな・カナの一回変換（Issue #24）

要求出所は2026-10-10のユーザー発言「漢字かな混じりではなくカナだけ、かなだけに変換できるようにしたい」。画面の直接英字切替キーを「かな」「カナ」に置き換え、core既存F6/F7による未確定文字列全体の読み変換を使用する。物理無変換の直接英字機能は維持する。永続かな入力モード・12key配列・英単語の日本語発音への翻訳は対象外。

実core integrationは`nihongo`のlive入力/候補表示中それぞれからF6→`にほんご`、F7→`ニホンゴ`、候補消去、Enter完全一致、次入力の通常`日本語`復帰を確認する。Android instrumentation `MeltypeTest -e phase script`は画面と同じaction helperを使用し、上記に加えて直接英字から通常復帰・空のF6/F7非転送を確認する。実機結果はIssue #24へ記録する。engine/core変更なしでplugin39 APKを再利用、host/testのみ生成する。

## F10の一回変換と次composition（Issue #26）

2026-10-10の画面「英数」要求は未確定文字列の一回変換として採用。Pixelのlive/候補中F10確定は成功したが、続くnihongoが英字になり受入失敗。coreは表示モードをAutoへ戻しても直前英語文脈を保持するため、pluginはIC単位にF10変換を追跡し、確定後にcore sessionを破棄、次compositionで再作成する。保存データは変更・削除しない。F6/F7/F9へ変更した場合はF10追跡を解除する。物理無変換の直接英字は従来どおり。

Linux実NativeAOT配布v1.0.0/helperによる2回F10確定→次nihongoのintegrationは旧engineでFAILを再現（Red）。修正後integrationと異常回復2/2 PASS（1.04秒）。初回F10一回だけではRedを再現しなかったため、実機の二回確定と一致させた。Android core87/providerは変更せずpluginのみ再生成する。Pixel修正版受入は未実行でIssue #26へ追記する。
