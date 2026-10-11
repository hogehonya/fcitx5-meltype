# In-process Mozc bridge

`meltype-mozc-bridge`はPICのstatic C++ libraryです。最終addonへリンクし、外部helper processは起動しません。`mozc_bridge.h`（factory用入口`meltype_mozc_bridge.h`）のinit/shutdown/clauses/candidatesを使います。core ABIは[include/meltype_native.h](include/meltype_native.h)です。

initにはhostが書ける絶対private profileを渡します。同profileの再初期化は成功、稼働中の別profileは失敗です。shutdownは繰返し可能です。全呼出しを同じFcitx event threadで直列化してください。callback結果はmallocしたUTF-8 NUL文字列で、coreが解放します。単独テストではfreeします。未初期化・文脈もない空入力・失敗はNULL、例外はABI境界内で捕捉し、入力文字列をログへ出しません。

候補は1文節なら全候補、複数文節なら先頭候補をつないだ全文候補です。Mozc学習は既存core callbackで公開されないため未対応です。Meltype側の学習と混同しません。isWord callbackはNULLでcoreのBuiltInWordCheckerを使えます。

## Build

root CMakeに`MOZC_SOURCE_DIR`、`PROTOC_EXECUTABLE`、`MOZC_DATA_HEADER`を絶対パスで渡します。原本はcleanなfcitx5-mozc revision `91534fe508673f496c2e35e48e09260b75398671`（host `6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4`のgitlink）です。submoduleもgitlinkへ固定します。network取得は行いません。

[source](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/commit/6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4/HONYA.md)のhost protoc 34.1.0とBazel OSS辞書headerを別工程で生成します。CMakeがbuild directoryへsourceをコピーし、辞書を配置してAndroid base/android_util.ccをそこだけ追加します。staging markerで原本path/SHA/header hashを検証し、変更時はfresh build directoryを要求します。元source・既存成果は変更しません。

host検証は`-DMELTYPE_BRIDGE_TESTS=ON`を指定し、`cmake --build <build-dir> --target test-meltype-bridge -j2`、`ctest --test-dir <build-dir> --output-on-failure`で実行します。Androidは同入力とNDK toolchain/arm64-v8aを指定し、target `meltype-mozc-bridge`を-j2でbuildします。Androidではhost testを生成しません。最終addonで`-Wl,--exclude-libs,ALL`を指定し、Mozc等static依存のsymbolsが別addonへ干渉しないようにします。

host LinuxのRelease buildとctest 1/1は成功しています。Android cross buildの結果は統合担当が確定後に記録します。検証hostでは同じ確認済みstagingを`MELTYPE_MOZC_STAGE_DIR`で再利用し、重複sourceコピーを避けています。

## 検証範囲

bridge_testは未初期化、相対path拒否、繰返し初期化/終了、異なるprofile拒否、日本語文節、複数候補、空/NULL入力、反復malloc/freeを実測します。APK load・既存Mozcとの同process共存・UI操作はhost統合後の端末検証です。

[構成](../docs/ARCHITECTURE.md) / [ビルド](../docs/BUILD.md) / [検証](../docs/TESTING.md)

## 入力途中・確定後の予測（Issue #27）

`meltype_mozc_predictions`はMozc `StartPrediction` / PREDICTIONを使い、日本語の入力途中に最大20件の全文候補を返す。部分候補は無効、複数segment結果は返さない。既存StartConversion callbackを置換しない。Android factoryはcoreの任意export `meltype_set_prediction_callback`へ登録するため、予測対応core revisionのartifactが必須。保存値やユーザー辞書は変更しない。非変換viewの非空候補もFcitxへ渡す。hostのtoolbarは既存の同一行で候補へ自動置換され、Androidの操作説明auxUp hintは非表示、Linux表示は維持する。core日本語候補tapは即確定し、通常Space変換の候補選択は既存どおり。

bridge_testに「にほ」入力の「日本」予測と反復free、続く通常変換回帰を追加。core・bridge・APK/GUIは別の証拠として検証する。

次語は `meltype_mozc_predictions("", context)` で取得する。ReconstructHistoryとpreceding_textへ確定文脈を渡し、空query時のみzero_query_suggestion/mixed_conversionを有効にする。通常prefixとStartConversionは従来requestを維持する。返却は最大20件の追加文字列。Mozc Learn/saveを新たに呼ばず、既存ユーザーデータは初期化しない。
