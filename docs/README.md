# 文書

現在の文書は実装前の設計です。存在する上流コード、このrepoのビルド入口
([scripts/build-core.py](../scripts/build-core.py))、今後作るAndroidコードを区別しています。

- [BUILD.md](BUILD.md): 固定依存、環境準備、固定coreのNativeAOT build、実行記録、今後のAPK工程
- [ARCHITECTURE.md](ARCHITECTURE.md): リポジトリ境界、callback ABI、必要変更
- [TESTING.md](TESTING.md): Android実装後の合格条件
- [scripts/README.md](../scripts/README.md): ビルドscriptの引数・出力・検証内容
- [tests/README.md](../tests/README.md): ビルド入口の単体テスト
- [入口](../README.md) / [全ファイル](../SITEMAP.md)
