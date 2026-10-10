# ビルド準備と工程

このrepoのビルド入口は `scripts/build-core.py` です。固定coreから `arm64-v8a` の NativeAOT 共有
ライブラリを作り、`manifest.json` と検証結果を残します。Linux Fcitx5 addon は [addon/README.md](../addon/README.md) の独立 CMake 入口で build できます。
Android factory/bridge と Gradle module は実装済みです。[Android APK手順](../android/README.md)でhost forkへ登録してビルドします。

controller環境で共有ライブラリの生成、必須export、16KB LOAD alignmentを検証しています。
worker sandboxのAF_UNIX制限による失敗は[実行記録](#実行記録)で分離しています。

## 固定する依存

固定値の正本は [`scripts/deps.lock.json`](../scripts/deps.lock.json) です。script はこの値と実物が
一致しなければ build を始めません。値を変えるときは lock を更新し、理由と検証を Issue へ記録します。

|依存|固定revision|用途|
|---|---|---|
|[Meltype fork](https://gitea.honya.dev/honya-dev-forks/meltype/src/commit/9c84625e894f50f06cafba1c6aada5eaa65208f4)|`9c84625e894f50f06cafba1c6aada5eaa65208f4`|net10.0 core、C ABI。NativeAOT build の入力|
|.NET SDK|`10.0.100`|NativeAOT の publish|
|Android NDK|`28.0.13004108`|Bionic arm64 のリンクと `llvm-readelf` による検証|
|RID / ABI|`linux-bionic-arm64` / `arm64-v8a`|build と成果物の対象|
|[Fcitx Android fork](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/commit/6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4)|`6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4` (`honya/mozc-trial`)|host、plugin convention、Mozc 静的 build|
|[dotnet/runtime 資料](https://github.com/dotnet/runtime/blob/v10.0.0/src/coreclr/nativeaot/docs/android-bionic.md)|`v10.0.0`|Bionic NativeAOT 仕様|

Fcitx の submodule はこの superproject の gitlink へ固定します。ローカル既存 clone には dirty な
Mozc submodule があるので、そこで reset/update/build しません。依存コード導入時は GPL・第三者
ライセンス原本を保持します。

Fcitx 固定revisionの`Versions.kt`は compile/target SDK 36、min SDK 23、Build Tools 36.1.0、
NDK 28.0.13004108、CMake 3.31.6、Java ソース互換11です。wrapperは Gradle 9.6.1 です。Java 11 は
Gradle 実行 JDK ではありません。hostの固定revisionの
[HONYA.md](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/commit/6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4/HONYA.md)
に従い実行 JDK は 21 を用意し、`./gradlew --version` で確認・記録します。
[Gradle 互換表](https://docs.gradle.org/current/userguide/compatibility.html) は更新されるため
採用時に再確認してください。

## 依存の取得 (手動)

`scripts/build-core.py` は clone・SDK/NDK の導入・端末操作をしません。必要なものは利用者が用意し、
`--core-dir` / `--dotnet` / `--ndk-dir` で明示します。core は固定 SHA を detach checkout した
clean な作業ツリーを渡します。毎回新しい場所へ clone し、既存 clone へ変更を加えないでください。
認証情報を URL やログへ埋め込まないでください。

```bash
set -euo pipefail
core_root=$(mktemp -d "${TMPDIR:-/tmp}/meltype-core.XXXXXXXX")
git clone https://gitea.honya.dev/honya-dev-forks/meltype.git "$core_root/core"
git -C "$core_root/core" checkout --detach 9c84625e894f50f06cafba1c6aada5eaa65208f4
```

この調査環境では次のものを使いました。版は script が `--dotnet` / `--ndk-dir` の実物から確認します。

|ツール|パス|版|
|---|---|---|
|dotnet|`/home/honya/.local/share/meltype-android/toolchains/dotnet-10.0.100/dotnet`|`10.0.100`|
|NDK|`/home/honya/Android/Sdk/ndk/28.0.13004108`|`28.0.13004108` (`clang` 19.0.0 (r530567c) / `llvm-readelf` 19.0.0)|

## 固定coreのNativeAOT build

```bash
python3 scripts/build-core.py \
    --core-dir /home/honya/repos/meltype \
    --dotnet /home/honya/.local/share/meltype-android/toolchains/dotnet-10.0.100/dotnet \
    --ndk-dir /home/honya/Android/Sdk/ndk/28.0.13004108 \
    --output-dir /tmp/meltype-native-arm64
```

script の手順は次のとおりです。引数の一覧は [scripts/README.md](../scripts/README.md) を参照してください。

1. `--output-dir` が存在しないこと、core の SHA が lock と一致し作業ツリーが clean であること、
   `dotnet --version` と NDK の `Pkg.Revision` が lock と一致すること、core の
   `InvariantGlobalization=false` が維持されていることを確認する。output-dir は core の中に置かない。
2. `--output-dir/staging` へ core の追跡ファイルだけを `git archive` で取り出す (元 core へは書かない)。
3. NDK の LLVM bin を `PATH` の先頭に置き、`DOTNET_CLI_TELEMETRY_OPTOUT=1` で publish する。

```bash
dotnet publish src/Meltype.Mac.Native/Meltype.Mac.Native.csproj -c Release -r linux-bionic-arm64 \
    -p:PublishAot=true -p:NativeLib=Shared -p:DisableUnsupportedError=true \
    -p:PublishAotUsingRuntimePack=true --source https://api.nuget.org/v3/index.json
```

固定coreの`nuget.config`は packageSources を clear するため、NativeAOT コンパイラと runtime pack を
restore するには取得先が必要です。既存`linux/build.sh`と同様に、この publish だけ取得先を明示します
(既定は上記。オフライン検証などでは `--nuget-source` で差し替え、実際に使った取得先を manifest へ
記録します)。

4. `llvm-readelf` で `ELF64` / `AArch64` / `DYN` と little endian、必須 export 9 個
   (`meltype_init` / `meltype_create` / `meltype_destroy` / `meltype_handle_key` / `meltype_commit` /
   `meltype_select_candidate` / `meltype_set_direct` / `meltype_free` / `meltype_set_data_directory`)、
   全 `LOAD` の `p_align >= 16384` を検証する。`SONAME` と `NEEDED` は記録する。
5. `lib/arm64-v8a/libMeltypeNative.so`、`manifest.json`、`LICENSE` と `THIRD-PARTY-NOTICES.md` の原本、
   `logs/publish.log` (IL2026/IL3050 の JSON AOT 警告を含む)、`README.md` を残す。

`manifest.json` は最後に書きます。途中で失敗したら `--output-dir` ごと削除し、非 0 で終わります
(成功 manifest を残さない)。終了コードは 0=成功、1=失敗、2=引数の誤りです。この成果物は APK では
なく、addon への収録と端末検証は[今後追加するAPK工程](#今後追加するapk工程)です。

## 実行記録

2026-10-07 に worker sandbox で `scripts/build-core.py` を実行しました。この sandbox は外部ネットワーク
(`api.nuget.org`) も拒否するため、同じ版 (10.0.0) の package を持つローカルディレクトリを
`--nuget-source` で指定しました。成功時の `manifest.json` は実際に使った取得先を
`environment.nuget_sources` へ記録します。結果は次のとおりです。

- 入力検証: 通過。core SHA `9c84625e894f50f06cafba1c6aada5eaa65208f4` (clean)、`dotnet` `10.0.100`、
  NDK `28.0.13004108`、`clang` 19.0.0 (r530567c)、`llvm-readelf` 19.0.0、`InvariantGlobalization=false`。
- publish: 失敗。restore と C# の compile (`Meltype.Core.dll` / `MeltypeNative.dll`) までは進み、
  `Microsoft.NET.ILLink.targets(325,5): error MSB4216` で MSBuild がタスクホスト (`runtime "NET" /
  architecture "x64"`) を作れませんでした (続けて MSB4027)。この sandbox では AF_UNIX の socket 作成が
  `Operation not permitted` で拒否され (確認済み)、MSBuild のタスクホストが使う named pipe は Linux では
  Unix domain socket で実装されるためです。
- 成果物: 生成されず。script は output-dir を削除し、成功 manifest も残していません。
- 単体テスト: `python3 -m unittest discover -s tests -t .` で 28 件すべて成功 (fake ツールによる
  入力検証・失敗時の後始末・`llvm-readelf` 出力の解釈、本物の clang/`llvm-readelf` を使う AArch64
  共有ライブラリの検証を含む)。

controllerで同じ固定coreと公開NuGet sourceを使って再実行し、NativeAOT publishとELF検証が成功しました。
必須exportは9個、すべてのLOAD alignmentは16384、NEEDEDは`libdl.so`、`libm.so`、`libc.so`、
SONAMEは未設定です。成果物のSHA256は
`28233d2c4d03452e3060c0c06f00e4fd59172b901b74508dae034c7daaaf8011`です。
IL2026/IL3050警告は保存されており、端末実行・JSON保存の成功を示すものではありません。
相対パスの回帰テストを追加後、単体テスト29件が成功しています。

## ICU/globalization と page size

NativeAOT 側の ICU/globalization、libssl の必要性、minimum API は実機で未確認です。core は
`InvariantGlobalization=false` なので Android で ICU が解決できるかを実機で検証します。無条件に
invariant へ切り替えたり、OpenSSL を不要と決めたりしません。v10 資料は minimum API 21 と記載して
いますが、採用 runtime pack の実値と host minSDK 23 の両方を確認します。16KB page は ILCompiler が
bionic + `NativeLib=Shared` の arm64/x64 へ `-Wl,-z,max-page-size=16384` を付けるため
(`Microsoft.NETCore.Native.Unix.targets`)、script は全 `LOAD` の `p_align >= 16384` を検証します。
APK packaging 側の alignment は別途確認します。[16KB公式手順](https://developer.android.com/guide/practices/page-sizes)

## Mozcの生成・クロスビルド前提

固定hostのHONYA.mdには、host protocの構築、Python 3で生成scriptを動かす準備、
`patches/0001-android-util.patch`、BazelによるOSSデータheader生成、Mozc plugin buildの試行手順が
あります。これらはNativeAOTとは別工程です。host protocは対象Android ABIではなく開発hostで
実行できるものを使い、protobuf revisionを一致させます。生成した辞書headerと静的ライブラリが
後段addon buildの入力になります。

既存ローカルcloneのdirty patchや生成済み48MB headerをclean cloneの成果物と見なしません。初回実装
ではHONYAの手順を新cloneで再現し、patch適用状態・生成入力・出力を確認してから、このrepoの
再現可能なbuild定義へ取り込みます。現時点のcloneコマンドだけでMozc buildが成功するという保証は
ありません。

## Android APK工程

現在のビルド入口、必要な固定入力、host登録、SDK/ABI、成果物検査は[Android手順](../android/README.md)を正本とします。root CMake は in-process Mozc bridge、`android/plugin` は Android addon/APK、`addon/CMakeLists.txt` は Linux addonです。

[構成](ARCHITECTURE.md) / [検証](TESTING.md) / [文書一覧](README.md)
