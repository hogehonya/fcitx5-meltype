# ビルド準備と工程

このrepoにはまだビルドscript・Gradle task・APKがありません。以下は実在する依存を取得し、既存coreのAndroid NativeAOTを検証するための未実行手順です。dotnetは調査環境へ未導入で、Android build成功は確認していません。

## 固定する依存

参照したrevisionと役割を固定します。Fcitx forkはmainの存在を仮定せず、remoteで確認したbranchを使います。

|依存|固定revision|用途|
|---|---|---|
|[Meltype fork](https://gitea.honya.dev/honya-dev-forks/meltype/src/commit/2b61c003965d5cbe6eafcaa890d6c496d91623e3)|`2b61c003965d5cbe6eafcaa890d6c496d91623e3` (`main`)|net10.0 core、C ABI、helper|
|[Fcitx Android fork](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/commit/6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4)|`6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4` (`honya/mozc-trial`)|host、plugin convention、Mozc静的build|
|[dotnet/runtime資料](https://github.com/dotnet/runtime/blob/v10.0.0/src/coreclr/nativeaot/docs/android-bionic.md)|`v10.0.0`|Bionic NativeAOT仕様|

Fcitxのsubmoduleはこのsuperprojectのgitlinkへ固定します。ローカル既存cloneにはdirtyなMozc submoduleがあるので、そこでreset/update/buildしません。依存コード導入時はGPL・第三者ライセンス原本を保持します。

Fcitx固定revisionの`Versions.kt`はcompile/target SDK 36、min SDK 23、Build Tools 36.1.0、NDK 28.0.13004108、CMake 3.31.6、Javaソース互換11です。wrapperはGradle 9.6.1です。Java 11はGradle実行JDKではありません。hostの固定revisionの[HONYA.md](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/commit/6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4/HONYA.md)に従い実行JDKは21を用意し、`./gradlew --version`で確認・記録します。[Gradle互換表](https://docs.gradle.org/current/userguide/compatibility.html)は更新されるため採用時に再確認してください。

## 安全な依存取得

Bashで実行します。毎回新しい作業場所を作り、既存cloneへ変更を加えません。認証情報をURLやログへ埋め込まないでください。

```bash
set -euo pipefail
meltype_build_root=$(mktemp -d "${TMPDIR:-/tmp}/meltype-android-build.XXXXXXXX")
git clone https://gitea.honya.dev/honya-dev-forks/meltype.git "$meltype_build_root/core"
git -C "$meltype_build_root/core" checkout --detach 2b61c003965d5cbe6eafcaa890d6c496d91623e3
git clone --branch honya/mozc-trial https://gitea.honya.dev/honya-dev-forks/fcitx5-android.git "$meltype_build_root/host"
git -C "$meltype_build_root/host" checkout --detach 6b0fa06ce08f8a0b32dd8df6a0817ee4d31420f4
git -C "$meltype_build_root/host" submodule update --init --recursive
```

## Mozcの生成・クロスビルド前提

固定hostのHONYA.mdには、host protocの構築、Python 3で生成scriptを動かす準備、`patches/0001-android-util.patch`、BazelによるOSSデータheader生成、Mozc plugin buildの試行手順があります。これらはNativeAOTとは別工程です。host protocは対象Android ABIではなく開発hostで実行できるものを使い、protobuf revisionを一致させます。生成した辞書headerと静的ライブラリが後段addon buildの入力になります。

既存ローカルcloneのdirty patchや生成済み48MB headerをclean cloneの成果物と見なしません。初回実装ではHONYAの手順を新cloneで再現し、patch適用状態・生成入力・出力を確認してから、このrepoの再現可能なbuild定義へ取り込みます。現時点のcloneコマンドだけでMozc buildが成功するという保証はありません。

## 既存coreのpublish検証

.NET 10 SDK、上記NDK、host側の必要build toolsを別途準備してから、同じBash sessionで実行します。SDKのexact patch・runtime pack解決結果は初回成功時に記録し、その後固定します。このrepoへのSDK導入は今回行っていません。

```bash
set -euo pipefail
: "${meltype_build_root:?先に依存取得を実行}"
meltype_ndk="$HOME/Android/Sdk/ndk/28.0.13004108"
test -d "$meltype_ndk/toolchains/llvm/prebuilt/linux-x86_64/bin"
export PATH="$meltype_ndk/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH"
dotnet --version
clang --version
dotnet publish "$meltype_build_root/core/src/Meltype.Mac.Native/Meltype.Mac.Native.csproj"   -c Release -r linux-bionic-arm64   -p:PublishAot=true -p:NativeLib=Shared   -p:DisableUnsupportedError=true -p:PublishAotUsingRuntimePack=true
```

`linux-bionic-arm64`と2つのBionic用flagはv10資料の手順です。`android-arm64`ではpublishしません。これはC ABI共有ライブラリの検証で、Android addonやAPKを完成させるコマンドではありません。成果物候補はcoreの`bin/Release/net10.0/linux-bionic-arm64/publish/`です。実際の`.so`名・exports・NEEDED依存を確認してからAPK向け`libMeltypeNative.so`の収録を実装します。

## 今後追加するAPK工程

1. このrepoへaddon・bridge・ABI headerを実装し、coreへ保存先等の必要変更を加える。
2. host forkへ固定revision参照の`plugin/meltype`を登録する。既存Mozc pluginのPrefab依存・addon/assets収録方法を参考にする。
3. CMake imported shared targetでNativeAOTライブラリへリンクし、Mozc静的engine・辞書生成を組み込む。hostと一致するSTLを使用し、Fcitx/libc++を重複収録しない。
4. arm64を初期MVPとする提案を採用する場合、hostの`buildABI`をarm64-v8aへ制限する。module追加後に`tasks`で実在taskを確認してからAPKコマンドを文書へ追加する。現在`plugin:meltype`taskは存在しない。
5. APK内にaddon、NativeAOT `.so`、inputmethod/addon設定、辞書、必要な依存とライセンスを収録し、[TESTING](TESTING.md)で端末検証する。

NativeAOT側のICU/globalization、libsslの必要性、minimum API、16KB page alignmentは未確認です。既存projectはInvariantGlobalization=falseなのでAndroidでICU解決を検証します。無条件にinvariantへ切り替えたり、OpenSSLを不要と決めたりしません。v10資料はminimum API 21と記載していますが、採用runtime packの実値とhost minSDK 23の両方を確認します。[16KB公式手順](https://developer.android.com/guide/practices/page-sizes)

[構成](ARCHITECTURE.md) / [検証](TESTING.md) / [文書一覧](README.md)
