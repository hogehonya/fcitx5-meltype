# Android Meltype plugin

Issue #8 のプラグインは arm64-v8a / Android API 24 以上を対象にします。host は Issue #10 の module 登録と内部保存先 `MELTYPE_DATA_DIR` の供給が必要です。debug host と debug plugin を組み合わせます。元のIMEやデータを削除する必要はありません。

## ビルド

依存 revision と NativeAOT 生成は [BUILD](../docs/BUILD.md)、Mozc の clean source・辞書・host protoc は [native](../native/README.md)を参照してください。host は固定 `6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4` に Issue #10 の差分を適用し、plugin の固定 gitlink を取得します。独立 checkout を使用する場合は `-PmeltypePluginDir` で絶対パスを指定します。

JDK 21、SDK 36、Build Tools 36.1.0、NDK 28.0.13004108、CMake 3.31.6、ECM を用意してください。`/absolute/...` はそれぞれ実際の入力へ置換します。NDK/SDK の自動導入は使いません。

```bash
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
ANDROID_HOME=/absolute/Android/Sdk \
ECM_DIR=/absolute/ecm/usr/share/ECM/cmake \
CMAKE_BUILD_PARALLEL_LEVEL=2 \
./gradlew :plugin:meltype:assembleDebug :app:assembleDebug :app:assembleDebugAndroidTest \
  --max-workers=2 -Pandroid.builder.sdkDownload=false -PbuildABI=arm64-v8a \
  -PmeltypePluginDir=/absolute/fcitx5-meltype/android/plugin \
  -PmeltypeCoreLibrary=/absolute/core-artifact/lib/arm64-v8a/libMeltypeNative.so \
  -PmeltypeMozcSourceDir=/absolute/clean-fcitx5-mozc \
  -PmeltypeMozcDataHeader=/absolute/generated/mozc_data.inc \
  -PmeltypeHostProtoc=/absolute/host/protoc-34.1.0 \
  -PmeltypeJsonIncludeDir=/absolute/include
```

`meltypeJsonIncludeDir` は nlohmann-json 3.11.3 の `nlohmann/json.hpp` を含むヘッダーdirectoryです。必要なheaderだけbuild directoryへコピーし、hostの標準C headerをAndroid compilerへ混ぜません。plugin と host は同じ Fcitx5/STL を使い、plugin に host の `libFcitx5*` / `libc++_shared.so` を重複収録しません。NativeAOT と addon は同じAPKに収録し、addon は `$ORIGIN` から provider を解決します。Mozc sourceをbuild stagingへコピーし、原本へpatchしません。

成果物は plugin checkout の `android/plugin/build/outputs/apk/debug/`、host の `app/build/outputs/apk/debug/`、テスト APK は `app/build/outputs/apk/androidTest/debug/` に生成されます。

```bash
python3 scripts/check-plugin-apk.py /absolute/meltype-debug.apk \
  --readelf /absolute/Android/Sdk/ndk/28.0.13004108/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf
```

## 実機受入

host APK、plugin APK、テスト APK を同じ端末へ導入した後、次の instrumentation を実行します。既存IMEを保持し、debug appを追加します。

```bash
adb -s SERIAL install -r /absolute/host-debug.apk
adb -s SERIAL install -r /absolute/meltype-debug.apk
adb -s SERIAL install -r /absolute/host-debug-androidTest.apk
adb -s SERIAL shell am instrument -w \
  -e class org.fcitx.fcitx5.android.MeltypeTest \
  org.fcitx.fcitx5.android.debug.test/androidx.test.runner.AndroidJUnitRunner
adb -s SERIAL shell am instrument -w -e phase reload \
  -e class org.fcitx.fcitx5.android.MeltypeTest \
  org.fcitx.fcitx5.android.debug.test/androidx.test.runner.AndroidJUnitRunner
```

テストは Fcitx の同じnative経路で `nihongo` →候補選択→ `日本語` commit と、`kyouhagithubnipushshita` → Return → `今日はgithubにpushした` の完全一致を確認します。また、`hashi` の非既定漢字候補を選び、JSONに保存した値を確認します。`phase reload` は別process起動で同じ読みをSpaceで変換した際の先頭候補とcommitが学習した候補へ戻ることを確認します。実機でbackspace、端末rotation、ICU初期化を別途確認します。端末未実施の検証をAPKビルド成功だけで成功扱いしません。Mozc固有学習はcallback ABIに公開されていないため未対応です。

2026-10-10 の統合ビルドで host、plugin、instrumentation APK の生成が成功しました。plugin checker は arm64-only、NativeAOT/addon収録、Fcitx/STL重複無し、ELF 16KB LOAD alignment、正規asset/config descriptor、DT_NEEDED basename、`RUNPATH=$ORIGIN` が成功しています。Python単体30件と既存bridge実engine試験も成功しています。端末の検証結果は実行後に追記します。

## 成果の出所

今回統合した source snapshot は `snapshot-provenance.json` に元worktreeとSHA256を記録しています。元worktreeには書き込みません。生成されたビルドfileをsource snapshotには含めません。

実機ロードでproviderのSONAME欠落によりBionicのsymbol version lookupが失敗することを確認したため、NativeAOTの隔離publish入力にSONAME linker argを追加しました。APK checkerにもprovider SONAMEとVERNEED/DT_NEEDED整合検査を追加しています。既存provider成果物は変更せず、正式build scriptで再生成します。

## 英字モード（Issue #22）

共有engineはLinux PR21と同じ入力context単位の直接英字状態を使用します。物理無変換で直接英字、変換/ひらがなで通常の英日自動判定へ復帰。対応hostはMeltype選択時だけ画面にABC/かなキーを表示し、同じnative key経路へ送ります。既存のLanguageKeyと数字/記号面ABCはそれぞれIME切替・layout復帰を維持します。英字表示はA、通常はあ。

追加instrumentationは上記am instrumentに `-e phase english` を付けます。Virtual key経路でnihongo+Spaceを直接アプリ向けkeyとして返し、Meltype選択を維持、復帰後日本語commitを完全一致確認します。通常/reload phaseも回帰として再実行します。物理mappingと専用画面キー表示/タップは別に確認し、実行前に成功とは記録しません。core固定87b1、既存debug署名を維持し、Release alpha.1の既公開APKは変更しません。
