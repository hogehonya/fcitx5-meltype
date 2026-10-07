# Meltype Android

MeltypeをFcitx5 for Androidのプラグインとして開発するリポジトリです。Android実装、Gradleプロジェクト、APKはまだありません。固定coreからarm64 (arm64-v8a) のNativeAOT共有ライブラリを作るビルド入口と単体テストがあり、controller環境で実buildとELF検証を確認しています。端末検証は未実施です。

ユーザー確定事項は「Fcitx5プラグイン形式」と「リポジトリ・ビルド文書の作成」です。[Issue #1](https://gitea.honya.dev/honya-dev-forks/meltype-android/issues/1)を要求の入口とし、固定coreからのNativeAOT成果物生成を[Issue #3](https://gitea.honya.dev/honya-dev-forks/meltype-android/issues/3)で扱います。NativeAOTとarm64を最初のMVPに使う構成は調査に基づくAgent提案です。

- [ビルド入口と工程 (実行記録つき)](docs/BUILD.md)
- [構成・ABI・必要な実装](docs/ARCHITECTURE.md)
- [実装後の受入検証](docs/TESTING.md)
- [ビルドscriptの使い方](scripts/README.md) / [単体テスト](tests/README.md)
- [文書一覧](docs/README.md) / [サイトマップ](SITEMAP.md)

Android addonとbridgeの実装正本はこのリポジトリとします。共通C# coreは[Meltype fork](https://gitea.honya.dev/honya-dev-forks/meltype)、IMEサービスとキーボードUIは[Fcitx5 Android fork](https://gitea.honya.dev/honya-dev-forks/fcitx5-android)の担当です。host側の`plugin/meltype`登録・APK統合は今後の計画です。Linux IBusランチャーはAndroidの起動方法として使いません。

上流MeltypeのGPL-3.0-or-laterと、Mozc/Fcitx等の第三者ライセンス・copyright・NOTICEを保持します。依存コードの導入時に原本を同梱し、独自の互換性判断やライセンス変更を行いません。
