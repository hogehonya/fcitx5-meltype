# tests

[../scripts/build-core.py](../scripts/build-core.py) の単体テストです。NativeAOT の実 build は回さず、
fake の `dotnet` / NDK ツールと、NDK r28 の `llvm-readelf` で実際に取った出力 (`fixtures/`) で
入力検証・ELF 検証・失敗時の後始末を確かめます。

```bash
# リポジトリのrootで実行
python3 -m unittest discover -s tests -t .
```

`tests` は `__init__.py` を持つ package です (`-t .` を付けた discovery のため)。
`python3 -m unittest tests.test_build_core` でも同じテストが走ります。

## 何を確かめるか

|テスト|内容|
|---|---|
|`SuccessTest`|成功時の成果物 (`lib/arm64-v8a/libMeltypeNative.so`, `manifest.json`, `LICENSE`, `THIRD-PARTY-NOTICES.md`, `README.md`, `logs/`)、manifest の内容、`--keep-staging`、`--nuget-source` の上書き|
|`InputValidationTest`|core SHA・clean tree・dotnet 版・NDK 版・LLVM ツール・`InvariantGlobalization=false`・既存 output-dir・core 内の output-dir を拒否すること|
|`FailureArtifactsTest`|publish 失敗、MSBuild タスクホスト失敗、`.so` なし、export 不足、page alignment 不足のときに、非 0 で終わり output-dir (成功 manifest) を残さないこと|
|`ElfParsingTest`|`llvm-readelf` の `-h` / `-l` / `-d` / `--dyn-syms` 出力の読み取り (版付きシンボル `meltype_init@@V1.0` を含む)|
|`RealReadelfIntegrationTest`|本物の clang で作った AArch64 共有ライブラリを本物の `llvm-readelf` で検証できること (NDK がない環境では skip)|

`RealReadelfIntegrationTest` は NDK の `aarch64-linux-android23-clang` と `llvm-readelf` を使います。
場所は `MELTYPE_ANDROID_NDK` で上書きできます (既定: `/home/honya/Android/Sdk/ndk/28.0.13004108`)。

fake ツールは環境変数で挙動を切り替えます (`MELTYPE_TEST_DOTNET_MODE` = `ok` / `fail` / `taskhost` /
`noso` / `real`、`MELTYPE_TEST_ELF_ALIGN` = `ok` / `align-4k`、`MELTYPE_TEST_ELF_SYMBOLS` =
`ok` / `missing-export` / `versioned`)。実 build の代わりにこの切り替えで失敗経路を作ります。

テスト用の fixture は [fixtures/README.md](fixtures/README.md) を参照してください。

Native bridgeの実engine検証は[native/README.md](../native/README.md)を参照してください。host ctestは実Mozc変換・候補・寿命を検証します。
