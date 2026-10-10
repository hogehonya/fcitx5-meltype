# 文書

Linux addon・共通ABI adapterとAndroid NativeAOT build入口は実装済みです。Android bridge・factory・host登録・APK・端末検証は今後の計画です。存在する上流コード、このrepoのビルド入口
([scripts/build-core.py](../scripts/build-core.py))、今後作るAndroidコードを区別しています。

- [BUILD.md](BUILD.md): 固定依存、環境準備、固定coreのNativeAOT build、実行記録、今後のAPK工程
- [ARCHITECTURE.md](ARCHITECTURE.md): Linux/Android経路、ABI、session寿命、キーボード要求の正本
- [TESTING.md](TESTING.md): 実行済み検証とAndroid実装後の合格条件
- [scripts/README.md](../scripts/README.md): ビルドscriptの引数・出力・検証内容
- [tests/README.md](../tests/README.md): ビルド入口の単体テスト
- [入口](../README.md) / [全ファイル](../SITEMAP.md)
