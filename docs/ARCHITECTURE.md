# 構成と実装計画

Fcitx5の入力・候補UIを使い、Meltypeの判定・ローマ字・混在入力・学習設定を共通C# coreから再利用する提案です。依存revisionは[BUILD](BUILD.md)を正本とします。

## 実装の配置

このrepoにC++ addon、Mozc bridge、ABI header、Androidパッケージ統合用定義を作ります。共通coreの必要変更はMeltype forkへ還元し、Fcitx5 Android forkにはこのrepoの固定revisionを参照する`plugin/meltype`とmodule登録を追加します。Linux addon と共通 ABI adapter は [addon](../addon/README.md) に実装しました。Android bridge、host module 登録、APK 統合はまだ存在しません。

呼出しは`Fcitx input context → C++ addon → NativeAOT MeltypeNative → C++ Mozc callback`です。別processのLinux helperを起動せず、APKに収録した共有ライブラリを使います。Android 10以降の対象アプリは書込み可能なapp home内のファイルをexecveできません。[Android公式制限](https://developer.android.com/about/versions/10/behavior-changes-10#execute-permission)

## 再利用するコード

Meltypeの`src/Meltype.Mac.Native/Exports.cs`にはcallback登録`meltype_init`、session作成/破棄、キー処理、確定、候補選択、direct切替、JSON結果解放が既存です。名前にMacを含みますがLinuxも同じABIを使っています。

`native/mozc/meltype_mozc_helper.cc`のHelperの変換・候補・学習処理をC++ bridgeへ抽出します。mainと標準入出力protocol、C#のProcess.Start経路は使いません。Fcitx AndroidのMozcには`mozc_direct_client.cc`によるin-process Engine/SessionHandlerと`mozc-static`リンクの実例があります。ただし既存Mozc addonの内部classは公開APIではなく、その共有状態を直接呼ぶ前提にしません。独立bridgeのengine初期化・辞書生成を固定ソースから組み込みます。現時点でP/Invoke追加は不要で、既存callbackを優先します。

## ABI契約と追加作業

既存ABIはUTF-8 NUL終端です。Meltypeが返すJSON文字列は`meltype_free`で解放します。callbackが返す文字列はC++側でmallocし、C#側がfreeします。NULLは変換失敗、候補は改行区切り、文節は`読み\t結果`の改行区切りです。helperのUS/RS形式とは異なるためbridgeが整形します。

contextごとにsession handleを持ち、破棄・focus離脱・resetで未確定文字の扱いを定義します。Fcitxキーを既存Windows VKとmodifier bitへ変換し、surrounding textをbefore/afterへ渡します。候補tapは`meltype_select_candidate`へ戻し、JSONのcommit/preedit/candidatesをFcitx UIへ反映します。core exportは排他しない設計なのでFcitx threadへ直列化します。

必要変更は次のとおりです。

- 保存先は固定coreに既存の`meltype_set_data_directory` (UTF-8の絶対パス、最初のSessionや設定・学習の読み込みより前に1回) をhostから呼ぶ。coreへのAPI追加は不要。SpecialFolder.LocalApplicationDataがAndroidで期待するパスになると仮定しない。plugin APK自身ではなくhost IME processが書ける領域を使う。
- 既存callbackにはMozc Learnがない。学習をMVPへ含めるならlearn/save callbackを追加し、確定した文節と文脈を伝える。省く場合はMozc学習未対応と明記し、Meltype自身の学習との違いを示す。
- isWord callback/wordProviderのAndroid実装と辞書供給を決める。NULLならその経路を使わない既存挙動を検証し、英語判定が完成済みとは扱わない。
- C++ callbackの例外を内部で捕捉しNULL等で失敗を返す。handle不正・二重破棄・初期化失敗でIME全体を落とさない。

最初のarm64対応はAgent提案です。armeabi-v7a/x86はBionic NativeAOTの対応RIDに含まれないため、hostの全ABIを自動で継承しません。[NativeAOT v10.0.0](https://github.com/dotnet/runtime/blob/v10.0.0/src/coreclr/nativeaot/docs/android-bionic.md)

[ビルド](BUILD.md) / [検証](TESTING.md) / [文書一覧](README.md)
