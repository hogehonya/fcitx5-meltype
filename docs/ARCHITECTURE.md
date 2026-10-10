# 構成と実装計画

Fcitx5の入力・候補UIを使い、Meltypeの判定・ローマ字・混在入力・学習設定を共通C# coreから再利用する提案です。依存revisionは[BUILD](BUILD.md)を正本とします。

## 実装の配置

既存C++ addon・ABI adapterにAndroid Mozc bridge・factory・パッケージ統合用定義を追加する計画です。共通coreの必要変更はMeltype forkへ還元し、Fcitx5 Android forkにはこのrepoの固定revisionを参照する`plugin/meltype`とmodule登録を追加します。Linux addon と共通 ABI adapter は [addon](../addon/README.md) に実装しました。Android bridge、host module 登録、APK 統合はまだ存在しません。

実装済みLinuxは `Fcitx context → factory.cpp の meltype_init_mozc → NativeAOT → 外部Mozc helper process` です。計画中Androidは `Fcitx context → Android factory の meltype_init(callback) → NativeAOT → in-process C++ Mozc bridge` です。AndroidではAPKに収録した共有ライブラリを使います。Android 10以降の対象アプリは書込み可能なapp home内のファイルをexecveできません。[Android公式制限](https://developer.android.com/about/versions/10/behavior-changes-10#execute-permission)

## 再利用するコード

Meltypeの`src/Meltype.Mac.Native/Exports.cs`にはcallback登録`meltype_init`、session作成/破棄、キー処理、確定、候補選択、direct切替、JSON結果解放が既存です。共通coreのexportですが、Linux providerは別の初期化経路を使います。

`native/mozc/meltype_mozc_helper.cc`のHelperの変換・候補・学習処理をC++ bridgeへ抽出します。mainと標準入出力protocol、C#のProcess.Start経路は使いません。Fcitx AndroidのMozcには`mozc_direct_client.cc`によるin-process Engine/SessionHandlerと`mozc-static`リンクの実例があります。ただし既存Mozc addonの内部classは公開APIではなく、その共有状態を直接呼ぶ前提にしません。独立bridgeのengine初期化・辞書生成を固定ソースから組み込みます。現時点でP/Invoke追加は不要で、既存callbackを優先します。

## ABI契約と追加作業

既存ABIはUTF-8 NUL終端です。Meltypeが返すJSON文字列は`meltype_free`で解放します。callbackが返す文字列はC++側でmallocし、C#側がfreeします。NULLは変換失敗、候補は改行区切り、文節は`読み\t結果`の改行区切りです。helperのUS/RS形式とは異なるためbridgeが整形します。

adapterはcontextの最初の対応keyでsessionを遅延作成します。reset/deactivateはcommitしhandleを保持します。context property破棄でdestroyし、エラー時はdestroyして次の対応keyで再作成します。一般のfocus動作は検証済みとは扱いません。Fcitxキーを既存Windows VKとmodifier bitへ変換し、surrounding textをbefore/afterへ渡します。候補tapは`meltype_select_candidate`へ戻し、JSONのcommit/preedit/candidatesをFcitx UIへ反映します。core exportは排他しない設計なのでFcitx event threadへ直列化します。C++/managed例外をC ABIやhostへ漏らさない契約です。

必要変更は次のとおりです。

- 保存先は固定coreに既存の`meltype_set_data_directory` (UTF-8の絶対パス、最初のSessionや設定・学習の読み込みより前に1回) をhostから呼ぶ。coreへのAPI追加は不要。SpecialFolder.LocalApplicationDataがAndroidで期待するパスになると仮定しない。plugin APK自身ではなくhost IME processが書ける領域を使う。
- 既存callbackにはMozc Learnがない。学習をMVPへ含めるならlearn/save callbackを追加し、確定した文節と文脈を伝える。省く場合はMozc学習未対応と明記し、Meltype自身の学習との違いを示す。
- isWord callback/wordProviderのAndroid実装と辞書供給を決める。NULLならその経路を使わない既存挙動を検証し、英語判定が完成済みとは扱わない。
- C++ callbackの例外を内部で捕捉しNULL等で失敗を返す。handle不正・二重破棄・初期化失敗でIME全体を落とさない。

最初のarm64対応はAgent提案です。armeabi-v7a/x86はBionic NativeAOTの対応RIDに含まれないため、hostの全ABIを自動で継承しません。[NativeAOT v10.0.0](https://github.com/dotnet/runtime/blob/v10.0.0/src/coreclr/nativeaot/docs/android-bionic.md)

[ビルド](BUILD.md) / [検証](TESTING.md) / [文書一覧](README.md)

## ABI profileと初期化

|profile|入力|初期化と状態|
|---|---|---|
|Linux|配布v1.0.0 ([addon](../addon/README.md))|`meltype_init_mozc`使用。保存先APIは配布版にないため呼ばない。addon/GUI検証済み|
|Android|[BUILD](BUILD.md)の固定core|既存export `meltype_set_data_directory` と `meltype_init` callbackをhostから呼ぶ計画。build/export検証済み、factory/bridge未実装|

[header](../addon/meltype_abi.h)は共有adapter/Linux factory向けで、`meltype_set_direct`等を含む完全なAndroid APIではありません。宣言だけでproviderのexportを保証せず固定coreのシグネチャと実ELF exportを照合します。保存先・callback登録はprocess全体で最初のsessionより前に行いcallback関数・bridge状態を全sessionより長く保持します。Android factoryのprocess寿命管理は未実装です。JSONはUTF-8です。

## リポジトリと公開の境界

独立plugin repoはMeltype由来のkey mapping・ABI/JSON adapterを含みGPL-3.0-or-later、Copyright 2026 Yukishiroと[NOTICE](../NOTICE)を保持します。依存ライセンス原本も保持しrepo全体を上流GitHub forkへ変える必要はありません。共通C#はMeltype fork、addon/bridgeはこのrepo、レイアウト・theme・IME切替はhost forkが正本です。addonはkey変換とcommit/preedit/candidate eventを担当します。公開は[BUILD](BUILD.md#依存更新と公開)を参照してください。

## キーボードの要求と参照

2026-10-10のユーザー要求「キーボード配列はGboard/ATOKを参考にする」は[plugin #10](https://gitea.honya.dev/honya-dev-forks/meltype-android/issues/10)で追跡します。[host #9](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/issues/9)の既存配列・入力維持、キー分離・隙間・角丸・コントラスト・候補表示要求と紐づけます。本作業にUI実装はありません。

基準はhost `honya/mozc-trial`固定SHAの[TextKeyboard.kt](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/commit/6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4/app/src/main/java/org/fcitx/fcitx5/android/input/keyboard/TextKeyboard.kt)です。[HONYA.md](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/commit/6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4/HONYA.md)の古い「@は記号面のみ」より実装を優先します。

|参照・目的|実装済み基準|提案・受入の境界|
|---|---|---|
|ATOK: 配列・記号|ATOK着想QWERTY、数字行、主画面`@`・`.`、記号面、左右矢印|[公式マニュアル](https://www.atok.com/other/support/howtouse/android_pro/manual.html)のパネル切替・候補操作を参考にラベルと入力結果を検証する|
|Gboard: 配列選択・視認性|QWERTYを初期基準としてhost #9の表示要求を適用する計画|[Android公式解説](https://www.android.com/intl/ja_jp/articles/466/)のQWERTY/12キー・切替・数字行を比較。12キー/フリック採用は未決定|
|切替・候補|hostは画面とIME、addonは候補eventを管理|IME切替と配列/記号面切替を区別する|

未確認画面から寸法・位置・色を決めません。採否はhost Issueへ記録し[受入](TESTING.md#hostキーボードの設計受入)で確認します。統合は[plugin #8](https://gitea.honya.dev/honya-dev-forks/meltype-android/issues/8)と[host #10](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/issues/10)で未完了です。
