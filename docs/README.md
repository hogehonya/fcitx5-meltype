# 文書

要求→要件→基本設計→ビルド→検証の順に参照します。mainにはLinux addonとNativeAOT build入口があり、Android完成版は検証済み未mergeブランチです。実装済み・公開済み・未確認の区別は[入口](../README.md)に示します。

- [REQUIREMENTS.md](REQUIREMENTS.md): R-ID、要求者・日時・出所、目的と採用経緯
- [SPECIFICATIONS.md](SPECIFICATIONS.md): S/NF-ID、VR受入対応、確認済み・未確認範囲
- [ARCHITECTURE.md](ARCHITECTURE.md): 基本設計、3repo構成、ABI、初期化・変換・学習の図
- [BUILD.md](BUILD.md): このブランチの固定依存とNativeAOT手順、検証済みAndroidビルドへの入口
- [TESTING.md](TESTING.md): 受入結果、既存試験条件、制限と残作業
- [ビルドscript](../scripts/README.md) / [単体テスト](../tests/README.md)
- [入口](../README.md) / [全ファイル](../SITEMAP.md)

- [in-process Mozc bridge](../native/README.md): native APIとビルド契約
