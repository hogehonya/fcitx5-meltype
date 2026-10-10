# 基本設計

Fcitx5の入力・候補UI、Meltypeの混在入力判定・ローマ字・学習、Mozcの日本語変換を組み合わせる。[要求定義](REQUIREMENTS.md)のR-01〜05と[要件定義](SPECIFICATIONS.md)のS-01〜09・NF-01〜04に対応する。依存revisionと再現手順は[BUILD](BUILD.md)、合否と実行記録は[TESTING](TESTING.md)を正本とする。

## 実装と公開の状態

2026-10-10時点の実装根拠はplugin `14cbeaa`、host `a0cf7ed8`、core `87b1ae1` の各実装ブランチである。この設計文書のmain反映とAndroid実装のmain反映・公開は別工程であり、Android実装はまだmainへ統合されていない。以下は実装ブランチの動作を記述する。

moto g31とF-52EでGUI入力の成功を確認した。PixelのGUI入力は未確認。2026-10-10 15:55 JST確認時点でcore head CI17件中Ubuntu push core1件は成功（15:55:14）、残16件はWaiting/Blocked・aggregate pending。Windows/macOSには適合runnerがなく、CI全体の成功は未確認。ビルド、instrumentation、GUI、CI、公開の合否を相互に代用しない。端末・試験別の証拠と未確認範囲は[TESTING](TESTING.md)に集約する。

## ソース所属と3リポジトリの責務（S-01・S-08・S-09）

|正本|所有する実装|他repoとの境界|
|---|---|---|
|[fcitx5-meltype](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype)|C++ addon、ABI/JSON adapter、Android factory、Mozc bridge、plugin APK定義、依存lock・検証script|coreの公開C ABIを呼ぶ。hostへ入力方式と候補eventを提供する|
|[fcitx5-android](https://gitea.honya.dev/honya-dev-forks/fcitx5-android)|IMEサービス、キーボード・候補UI、plugin発見・ロード、保存先供給、Gradle module登録|pluginは固定gitlinkで参照する。レイアウトやthemeをaddonへ持ち込まない|
|[Meltype](https://gitea.honya.dev/honya-dev-forks/meltype)|共通C# core、混在入力、ローマ字、session、学習・設定、NativeAOT exports|FcitxのUIやAndroid APK packagingを共通coreへ持ち込まない|

```mermaid
%%{init: {"themeVariables": {"fontFamily": "IBM Plex Sans JP"}}}%%
flowchart LR
    subgraph Host[fcitx5-android / hostソース]
        UI[キーボード・候補UI]
        F[Fcitx InputContext]
        UI <--> F
    end
    subgraph Plugin[fcitx5-meltype / addon・bridgeソース]
        A[C++ addon / ABI adapter]
        B[in-process Mozc bridge]
        M[Mozc Engine / OSS辞書]
        A --> B
        B --> M
    end
    subgraph Core[meltype / 共通coreソース]
        C[C# core / NativeAOT exports]
    end
    F <--> A
    A <--> C
    C -->|変換callback| B
    C --> D[host私有領域 / 設定・学習JSON]
    F -->|保存先を供給| D
```

この図の枠はソースの所属を示し、APK収録先を示さない。pluginのaddon、Mozc bridge、NativeAOTはhost IME processにロードされ、別serviceや外部helper processを起動しない。Linux providerは既存の外部Mozc helper経路を使う。

## Android APK収録と実行先（S-07）

```mermaid
%%{init: {"themeVariables": {"fontFamily": "IBM Plex Sans JP"}}}%%
flowchart LR
    subgraph HostAPK[host APK]
        UIH[IMEサービス・キーボードUI]
        FH[Fcitx共有ライブラリ・STL]
    end
    subgraph PluginAPK[plugin APK]
        ADD[libmeltype.so / addon・Mozc bridge・静的engineと辞書]
        NAT[libMeltypeNative.so / NativeAOT provider]
        AS[addon・inputmethod設定・ライセンス]
    end
    subgraph Process[host IME process]
        LOAD[Fcitx addon loader]
        RUN[addon・provider・Mozc実行]
    end
    UIH --> LOAD
    FH --> LOAD
    ADD --> LOAD
    NAT --> RUN
    AS --> LOAD
    LOAD --> RUN
```

`libMeltypeNative.so`のソースはmeltype repoに所属するが、生成したproviderはplugin APKへ収録する。Mozc OSS辞書は生成headerから静的engineへ組み込まれ、独立した辞書assetとして配置する設計ではない。addon/bridge/辞書と同じplugin APKに配置し、host APKへproviderを重複収録しない。pluginはhostのFcitx共有ライブラリ/STLを利用し、実行時は両APKのライブラリがhost IME processで動く。LinuxではAPKを使わず、addonと指定provider/helperを[Linux手順](../addon/README.md)で配置する。

## 起動・保存先（S-02・S-05）

hostはAPI 24以上でdevice-protected storageの私有領域の絶対パスを`MELTYPE_DATA_DIR`へ供給する。Android factoryは保存先を検査し、`meltype_set_data_directory`、`meltype_mozc_bridge_init`、`meltype_init`の順に初期化してEngineを作成する。Mozc profileはその保存先の`mozc/`に置く。設定・学習はplugin APK自身の領域ではなくhostが書ける領域へ保存する。

`meltype_init`は文節変換・候補callbackを登録する。isWord callbackは`nullptr`であり、専用のAndroid英語辞書providerを実装したことにはならない。bridgeはprocess内で同じprofileへの再初期化を許容し、異なるprofileへの再初期化は失敗する。初期化失敗時はfactoryがエラーを返し、入力内容や保存先をログへ出さない。

Meltype側の学習JSONと再読込を実装した。Mozc固有のlearn/save callbackは現行ABIにないため未対応であり、両者を区別する。再起動後の学習確認手順は[Android受入](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/14cbeaabef946c160ecc67004a9b49b4a0a39218/android/README.md#実機受入)と[TESTING](TESTING.md)を参照する。

実装根拠: pluginの`addon/android_factory.cpp`・`native/mozc_bridge.cc`、coreの`src/Meltype.Mac.Native/Exports.cs`。これらのAndroidファイルは実装ブランチに存在し、文書mainだけでは参照できない場合がある。

## 入力・変換・候補・確定（S-03・S-04）

addonはFcitx keyをWindows VK・UTF-16文字・modifier bitへ変換する。最初の対応keyでInputContextごとのsessionを遅延作成し、coreへ渡す。未確定文字がないときだけ取得可能なsurrounding textをbefore/afterへ渡す。password/sensitive欄はcoreへ渡さず、通常の入力経路へ返す。

coreのJSON結果から`commits`の削除と文字列確定、`view`のpreedit・hint・候補を反映する。候補リストは`converting=true`かつ候補が複数のときに表示し、候補indexをcoreへ戻す。JSONの`consumed`がtrueの場合だけkey eventを受理する。

```mermaid
%%{init: {"themeVariables": {"fontFamily": "IBM Plex Sans JP"}}}%%
sequenceDiagram
    participant U as 利用者
    participant H as host UI / Fcitx
    participant A as addon / Session
    participant C as NativeAOT core
    participant B as Mozc bridge
    U->>H: 英字入力 / Space
    H->>A: keyEvent・取得可能な周辺文字
    A->>C: meltype_handle_key
    opt 日本語変換が必要
        C->>B: 文節・候補callback
        B-->>C: UTF-8変換結果
    end
    C-->>A: JSON commits / view / consumed
    A->>H: preedit・候補表示 / 必要ならcommit
    U->>H: 候補tap
    H->>A: Candidate.select(index)
    A->>C: meltype_select_candidate
    C-->>A: 更新JSON
    A->>H: 選択結果・確定を反映
    U->>H: Enter等で確定
    H->>A: keyEvent
    A->>C: meltype_handle_key
    C-->>A: commit結果
    A->>H: commitString・preedit更新
```

候補tapが確定するか選択状態を更新するかはcoreの返すJSONに従う。図は代表操作の連携を示し、すべてのkeyを固定した状態遷移仕様に置き換えない。

```mermaid
%%{init: {"themeVariables": {"fontFamily": "IBM Plex Sans JP"}}}%%
stateDiagram-v2
    [*] --> NoSession
    NoSession --> Editing: 最初の対応keyでsession作成
    Editing --> Editing: 文字入力・Backspace / preedit更新
    Editing --> Converting: Space等 / convertingなview
    Converting --> Converting: 候補移動・選択 / view更新
    Converting --> Editing: coreが編集viewを返す
    Editing --> Idle: commit / preeditなし
    Converting --> Idle: commit / preeditなし
    Idle --> Editing: 次の文字入力
    Editing --> Idle: reset・deactivate / commit
    Converting --> Idle: reset・deactivate / commit
    Idle --> NoSession: context破棄
    Editing --> NoSession: context破棄・処理エラー
    Converting --> NoSession: context破棄・処理エラー
```

ここでEditing/Converting/Idleは表示上の状態で、addonが保持する独立enumではない。reset/deactivateはcommitしてsessionを保持し、context property破棄はsessionをdestroyする。エラー時はsessionを破棄してUIをクリアし、次の対応keyで再作成する。

実装根拠: pluginの`addon/engine.cpp`・`addon/session.h`。非BMPや未対応keyは入力順序を保つため既存preeditをcommitしてから通常経路へ返す。削除位置はUTF-16単位からUnicode文字数へ変換し、surrogate pair分割や範囲超過を拒否する。

## ABIと安全境界（NF-01・NF-02）

文字列はUTF-8 NUL終端。coreが返すJSONはadapterが`meltype_free`で解放する。callbackの文字列はC++側がmallocし、C#側がfreeする。変換失敗はNULL、候補は改行区切り、文節は`読み\t結果`の改行区切りで渡す。Linux helperのUS/RS protocolをAndroid callbackへそのまま流さない。

core exportは排他を提供しないため、呼出しはFcitx event threadで直列化する。callback・bridgeはsessionより長いprocess寿命を持つ。C++/managed例外は各ABI境界で失敗値へ変換し、hostへ漏らさない。addonは結果の削除範囲をすべて検証してからアプリの文字列を編集する。

開発・ビルドは分離checkout/worktreeを使う。Mozc sourceはstagingへコピーしてAndroid用変更を適用し、元repo・dirty submodule・既存成果物を上書きしない。

## ビルドと配布（S-07・NF-03・NF-04）

Android pluginの対象はarm64-v8a / API 24以上。hostの全ABIへ自動展開しない。NativeAOTとaddonを同じplugin APKへ収録し、addonは`RUNPATH=$ORIGIN`からproviderを解決する。Fcitx共有ライブラリとSTLはhostが所有し、pluginへ重複収録しない。SDK/NDK等の値やコマンドは[BUILD](BUILD.md)・[Androidビルド](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/14cbeaabef946c160ecc67004a9b49b4a0a39218/android/README.md#ビルド)を正本とする。

```mermaid
%%{init: {"themeVariables": {"fontFamily": "IBM Plex Sans JP"}}}%%
flowchart TD
    L[固定revision / 依存lock] --> C[core NativeAOT生成]
    L --> M[Mozc clean source・OSS辞書・host protoc準備]
    C --> E[ELF exports・SONAME・ABI・alignment検査]
    M --> P[host Gradleでplugin addon・APK生成]
    E --> P
    L --> H[固定host / UI・IME APK生成]
    P --> V[plugin APK構成・依存・alignment検査]
    H --> T[host・plugin・test APKを実機導入]
    V --> T
    T --> I[instrumentation / 入力・学習再読込]
    I --> G[GUI / 候補tap・配列・明暗・切替]
    G --> R[PR・CIと受入証拠の確認]
    R --> S[main統合・固定参照更新]
    S --> D[公開用成果物・配布記録]
```

後半は完了までの工程で、すべての段階が現在成功済みという図ではない。ELFの16KB LOAD alignmentやAPK構成検査の成功は、16KBページサイズ端末での起動成功を意味しない。min API実機・未確認端末・CIの状況は[TESTING](TESTING.md)を参照する。

pluginはGPL-3.0-or-laterとしてMeltype由来のCopyright 2026 Yukishiroと[NOTICE](../NOTICE)、第三者ライセンス原本を保持する。依存更新・公開境界は[BUILD](BUILD.md#依存更新と公開)を参照する。

## キーボードの設計（S-06）

ユーザー要求の出所は[plugin #10](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/10)、実装範囲は[host #9](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/issues/9)。ATOK参考のQWERTY・数字行・主画面`@`と句読点・記号面・左右カーソルを維持し、Gboard参考のキー背景分離・余白・角丸を採用した。キー文字にはIBM Plex Sans JPを同梱する。候補欄はFcitxの既存UIとPixel配色を使う。

寸法・設定・既存設定保持はhostの`HONYA.md`、`ThemePrefs.kt`、`KeyView.kt`が正本。キーボードのタッチ領域は維持し、外観のinsetだけを調整する。12キー/フリックの採用は未決定であり、今回のQWERTY実装に含めない。[受入](TESTING.md#hostキーボードの設計受入)で入力結果・候補tap・明暗を確認する。

[ビルド](BUILD.md) / [検証](TESTING.md) / [文書一覧](README.md)
