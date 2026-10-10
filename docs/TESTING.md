# 実装後の検証

以下はAndroid実装の受入条件と実行記録です。Android 12 arm64実機で下記の項目が成功しました。他環境と未実施項目は区別し、Linuxの結果をAndroidの合格証拠に流用しません。

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

## hostキーボードの設計受入

既存host UIを基準にした[要求](ARCHITECTURE.md#キーボードの要求と参照)の今後の試験です。Gboard/ATOKを参考にする新設計と、Meltypeを統合したAndroid host・APKを生成済みです。下記に実機で確認した結果を記録します。buildと実行手順は[Android手順](../android/README.md)を参照してください。

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
|host|`0.1.3-22-g137c919b` arm64 debug|`622b7f7f74d5a353ef53aaa4a10d05d2c9b640c3086a79299e5e7077f4a55bb9`|
|instrumentation|`0.1.3-25-gab2f5117` debug AndroidTest|`b22e0aebdc8936f23a380e2bdfa7253d5a1e3a6c5f4f7050f3662976f19d6eae`|
|plugin|`0.1.3-28-g65922d39` arm64 debug|`be496fe31cfc059209e05abe8950359204a9c7ad4d3cd46a00ba8379a8314995`|

plugin source `3353260`、固定core `87b1ae13e95144266f9e69d8b20d42f00aa0e26e`。APK内NativeAOT provider SHA256は `200b5150bc97afa7c01f5d28825fa430bda18d19539de9c66990a13101725339` でbuild manifestと一致。テストAPKはbuild metadataのcommit後に追加したreload仕様修正（host `9821b319`）を含みます。host product codeは同じで、その後のgitlink・文書更新による再buildは不要です。

- `Loaded addon meltype`を実機logcatで確認。初回のSONAME欠落は正式publishのLinkerArgで修正済み。
- `MeltypeTest`通常実行 PASS（2.829秒）: `nihongo`→候補選択→`日本語`、`kyouhagithubnipushshita`→`今日はgithubにpushした`の完全一致、非既定漢字候補のJSON保存。
- 別processの `-e phase reload` PASS（2.215秒）: 保存した読みをSpaceで変換した際の先頭候補と、候補を選び直さずReturnで確定した文字列が保存した学習結果と一致。
- 保存先はnative正本 `DataManager.dataDir/files/meltype`（この端末ではdevice-protected storage）。ConversionHistoryのNativeAOT reflection読込失敗はsource-generated metadataで修正。既存JSON形式、不正JSON、保存後の別instance読込、Forgetをcoreテストで確認し全186/186 PASS。
- GUIでMeltypeを選択し、ソフトキー7tapで `nihongo`→`日本語` preedit、Spaceで `日本語/ニホンゴ/にほんご/Japanese`候補表示、先頭候補tap＋Enterで`日本語`確定。dark Pixelのキー境界、数字行、左右矢印、IBM Plex Sans JP表示を確認。
- GUI証拠は実施環境の `/tmp/meltype-touch-nihongo.png`、`/tmp/meltype-candidates-ready.png`、`/tmp/meltype-touch-commit.png`。リポジトリへの画像収録はしていません。
- 正規NativeAOT/Gradle build成功、Python30/30 tests成功、APK checkerでarm64・SONAME・symbol version provider・DT_NEEDED・RUNPATH・ELF 16KB alignment・assetsを検証。plugin lintDebug成功（警告5件）。

未実施・制限:

- Android 12以外、plugin最低API 24、16KB page size端末は実機未確認。ELF 16KB alignmentの静的検査成功を16KB実機起動成功とは扱いません。
- Settings、UserModel、LanguageMemory、TranslationHistory等、変換履歴以外のJSON用途の実機保存・再読込は未確認。既存IL2026/IL3050警告を抑制していません。
- Mozc固有learning callbackは未公開で未対応。確認した保存・復元はMeltype側の変換学習です。
- hardware keyboard、lightテーマの実機視認性、端末rotation、password欄、容量不足等の全受入条件は今回の実機検証に含みません。
- host lintDebugは既存269件（UseAppTint 1、StringFormatMatches 2、MissingTranslation 266）で失敗。今回変更したファイルにあるerrorは0件で、baselineやgate無効化はしていません。
- Linux-x64 NativeAOT smokeはruntime pack未取得・repository NuGet sources設定によるNU1100で未完了。Android NativeAOTビルドと上記実機reloadで修正を検証しました。
