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

2026-10-11、[android-v0.1.0-alpha.1 のPre-release](https://github.com/hogehonya/fcitx5-meltype/releases/tag/android-v0.1.0-alpha.1)を最新のhost62 / plugin68へ差し替える準備をしています。公開済みファイルのrevisionはRelease本文と添付 `release-manifest.json` / `SHA256SUMS` を正本として確認してください。[導入・制限・対応ソース](docs/ANDROID-TRIAL.md)を案内しています。debug署名の試用版で、stable版ではありません。

最新版は入力中・確定後の予測候補、画面の「あ/ア」「英数」変換、未確定時Enterの確定専用処理、focus-out時の文字再投入防止を含みます。候補行を残し、半透明のaux凡例は表示しません。F-52E（Android16/arm64）で隔離instrumentationと許諾済みGUI送信後の欄消去を確認しました。Pixel7・moto g31の旧版での実績を最新版の確認とは扱いません。Pixel7更新は未実施です。

共通core `444ce0d` と未mergeのAndroid実装が対応ソースの対象です。必要なCIは未完のため実装PRはmerge保留です（[core PR10](https://gitea.honya.dev/honya-dev-forks/meltype/pulls/10)、[plugin PR29](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/pulls/29)、[focus-out PR31](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/pulls/31)、[host PR17](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/pulls/17)、[境界テストPR19](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/pulls/19)）。公開はCI完了を意味しません。

- 最新版のソース再現はRelease添付CorrespondingSourceの `SOURCE-README.md` と固定revision・ビルド入力を使います。GitHubの自動Source codeはAndroid実装を含みません。
- 開発中の[Androidビルド手順](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/f5974122208e47a4c8f85b26f29acb200ba6aae5/android/README.md)と[検証記録](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/f5974122208e47a4c8f85b26f29acb200ba6aae5/docs/TESTING.md)は実装ブランチにあります。配布ファイルはmanifestの固定revisionを優先します。
- [初版と最新版の実測・制限](docs/TESTING.md)。API24下限、16KB page端末、他のJSON保存用途、全focus/password/回転等は未確認です。

## 設計・検証

- [要求定義](docs/REQUIREMENTS.md) / [要件定義と受入対応](docs/SPECIFICATIONS.md)
- [基本設計・構成図・フロー](docs/ARCHITECTURE.md)
- [このブランチのビルド入口](docs/BUILD.md) / [検証記録](docs/TESTING.md)
- [ビルドscript](scripts/README.md) / [単体テスト](tests/README.md)

上流MeltypeのGPL-3.0-or-laterとMozc/Fcitx等の第三者ライセンス・copyright・[NOTICE](NOTICE)を保持します。
