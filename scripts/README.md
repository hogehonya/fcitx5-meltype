# scripts

固定した core revision から Android arm64 (arm64-v8a) の NativeAOT 共有ライブラリを作るビルド入口です。
APK と Fcitx5 addon の収録はここでは行いません。

- [build-core.py](build-core.py): 入力検証 → 隔離 staging への core コピー → `dotnet publish` (NativeAOT) → ELF 検証 → 成果物配置
- [deps.lock.json](deps.lock.json): 固定値の正本 (core SHA / .NET SDK / NDK / RID / ABI / export 一覧 / ライセンス原本)

## 実行

Python 3.11 以降と、`git`、固定版の .NET SDK、固定版の Android NDK が必要です。依存の clone、
SDK/NDK の導入、端末操作はしません。必要なものはすべて `--` 引数で明示します。

```bash
python3 scripts/build-core.py \
    --core-dir /home/honya/repos/meltype \
    --dotnet /home/honya/.local/share/meltype-android/toolchains/dotnet-10.0.100/dotnet \
    --ndk-dir /home/honya/Android/Sdk/ndk/28.0.13004108 \
    --output-dir /tmp/meltype-native-arm64
```

|引数|意味|
|---|---|
|`--core-dir`|固定 core の作業ツリー。SHA が lock と一致し、作業ツリーが clean であることを要求する|
|`--dotnet`|.NET SDK の `dotnet`。`dotnet --version` が lock の版と一致することを要求する|
|`--ndk-dir`|Android NDK。`source.properties` の `Pkg.Revision` が lock の版と一致することを要求する|
|`--output-dir`|成果物の出力先。既存なら拒否する (上書きしない)|
|`--lock-file`|固定値の JSON (既定: `scripts/deps.lock.json`)|
|`--nuget-source`|NuGet の取得先。既定は lock の `https://api.nuget.org/v3/index.json`。オフライン検証などで差し替えるときに使う|
|`--keep-staging`|成功後も `output-dir/staging` (core のコピーと中間ファイル) を残す|

ビルドは `output-dir/staging/core` へ core の追跡ファイルだけを展開して行い、元の core へは
書き込みません。`dotnet publish` は NDK の LLVM bin を `PATH` の先頭に置き、
`DOTNET_CLI_TELEMETRY_OPTOUT=1` で実行します。core の `InvariantGlobalization=false` は変更しません。

## 出力

```
output-dir/
  lib/arm64-v8a/libMeltypeNative.so   publish された MeltypeNative.so
  manifest.json                       core SHA、ツール版、コマンド、SHA256、ELF/依存情報、検証結果
  LICENSE                             原本
  THIRD-PARTY-NOTICES.md              原本
  README.md                           成果物の説明と未確認事項
  logs/publish.log                    dotnet publish の生ログ (JSON の AOT 警告 IL2026/IL3050 を含む)
  logs/build.log                      入力検証と ELF 検証の記録
```

`manifest.json` は最後に書きます。検証に失敗した実行では manifest を残さず、`output-dir` 自体を
削除して非 0 で終わります。終了コードは 0=成功、1=失敗 (`build-error`)、2=引数の誤りです。

## 検証

`llvm-readelf` で次を確認し、1 つでも外れたら失敗します。

- `ELF64` / `AArch64` / `DYN` (共有ライブラリ)、little endian
- `meltype_init` / `meltype_create` / `meltype_destroy` / `meltype_handle_key` / `meltype_commit` /
  `meltype_select_candidate` / `meltype_set_direct` / `meltype_free` / `meltype_set_data_directory`
  が定義済み `GLOBAL` シンボルとして export されている
- すべての `LOAD` セグメントの `p_align` が 16384 以上 (16KB page)

`NEEDED` と `SONAME` は検証せず `manifest.json` へ記録します。

単体テストは [tests/README.md](../tests/README.md) を参照してください。

## 制約

- MSBuild のタスクホストは Unix domain socket (AF_UNIX) を使います。AF_UNIX を拒否する sandbox では
  NativeAOT の publish が `MSB4216` で失敗します。その場合は socket を許可する環境 (controller) で
  同じ入力・同じコマンドを実行し、worker では成功と報告しません。
- 実機での ICU/globalization、設定・学習の JSON 保存、APK への収録と端末動作は未確認です。
- 固定値を変えるときは `deps.lock.json` を更新し、理由と検証を Issue へ記録します。
