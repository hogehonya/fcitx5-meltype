# Meltype Fcitx5 plugin (Linux / Android)

原作はYukishiro（@yksr_melt / GitHub: [yksr-melt](https://github.com/yksr-melt)）による [Meltype](https://github.com/yksr-melt/Meltype) です。このリポジトリは日本語・英語混在入力をFcitx5へ接続するLinux / Android向け移植・連携版で、上流公式配布ではありません。ソースの開発正本は [Gitea fcitx5-meltype](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype)、GitHub公開先は [hogehonya/fcitx5-meltype](https://github.com/hogehonya/fcitx5-meltype) です。

## 3リポジトリの役割

|リポジトリ|担当|ビルド・設計の入口|
|---|---|---|
|[meltype](https://gitea.honya.dev/honya-dev-forks/meltype)|共通C#変換・英日判定・学習、NativeAOT C ABI|[core開発手順](https://gitea.honya.dev/honya-dev-forks/meltype/src/branch/main/docs/DEVELOPMENT.md)|
|[fcitx5-meltype](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype)|Fcitx addon、共通adapter、Android factory、in-process Mozc bridge、plugin APK|[文書一覧](docs/README.md)|
|[fcitx5-android](https://gitea.honya.dev/honya-dev-forks/fcitx5-android)|Android IMEサービス、キーボード・候補UI、plugin module登録、host APK|[hostフォーク手順](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/src/branch/honya/mozc-trial/HONYA.md)|

3リポジトリを維持します。Linux addonは [addon/README.md](addon/README.md)、Androidは以下の検証済みブランチの手順を参照してください。Linux IBusランチャーはAndroidの起動方法に使いません。

## AndroidのビルドとAPK入手

2026-10-10時点でAndroid arm64-v8aのhost・plugin・instrumentation APKをビルドし、moto g31（Android 12）、F-52E（Android 16）、Pixel 7（Android 17）へ導入しました。3端末とも日本語・英日混在入力、学習保存と別process再読込のinstrumentationが成功しています。GUI入力・候補確定はmoto g31のdarkとF-52Eのlightで確認済みです。Pixel 7のGUI確認は画面ロック解除待ちです。

この節は2026-10-10に確認した可変の公開状況です。要求・要件・基本設計は文書PR #14でmainへ公開済みですが、Android実装はまだ既定ブランチへマージしていません。検証済みAPKを生成したコード入力はcore `87b1ae13` → plugin `14cbeaa` → host `a0cf7ed8`です。その後のplugin `41a79d4` / host `e264cffa`は文書・remote URL・gitlinkのみの更新で、APK実装は変わりません。2026-10-10 15:55 JST確認時点でcore head CI17件のうちUbuntu push core1件は成功（15:55:14）、残16件はWaiting/Blocked、aggregateはpendingです。Windows/macOSに適合するrunnerはありません。このため、[core PR #8](https://gitea.honya.dev/honya-dev-forks/meltype/pulls/8)、[plugin PR #11](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/pulls/11)、[host PR #11](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/pulls/11)は依存順にマージ保留です。

- [検証済みAndroid APKビルド手順](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/14cbeaa/android/README.md): JDK 21、SDK 36、NDK 28.0.13004108、NativeAOT/Mozc入力とGradle引数。
- [検証済み固定依存とNativeAOT生成](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/14cbeaa/docs/BUILD.md)。既存dirty cloneを使わず独立checkoutでビルドします。
- [実機結果・SHA256・制限](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/14cbeaa/docs/TESTING.md)。16KB page端末と他のJSON保存用途は実機未確認です。

試用版の入手先・公開状態は[android-v0.1.0-alpha.1 のPre-releaseページ](https://github.com/hogehonya/fcitx5-meltype/releases/tag/android-v0.1.0-alpha.1)を参照してください。[導入・制限・対応ソースの案内](docs/ANDROID-TRIAL.md)に沿って、ライセンス付き導入ZIPのhost・pluginを組で導入します。stable版ではなくdebug署名です。上流Fcitx5 AndroidのRelease APKにこの統合が含まれるとは扱いません。元の検証済みAPKは作業ホストの `/home/honya/Downloads/Meltype-Android-20261010/` に保管しています。

## 設計・検証

- [要求定義](docs/REQUIREMENTS.md) / [要件定義と受入対応](docs/SPECIFICATIONS.md)
- [基本設計・構成図・フロー](docs/ARCHITECTURE.md)
- [このブランチのビルド入口](docs/BUILD.md) / [検証記録](docs/TESTING.md)
- [ビルドscript](scripts/README.md) / [単体テスト](tests/README.md)

上流MeltypeのGPL-3.0-or-laterとMozc/Fcitx等の第三者ライセンス・copyright・[NOTICE](NOTICE)を保持します。
