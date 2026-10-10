# 要求定義

## 目的と資料

Meltypeの英日混在入力をFcitx5で使用し、Android端末でも入力・候補確定・学習を利用できるようにする。正本としてREADME、既存ARCHITECTURE/BUILD/TESTING、検証済みplugin `14cbeaa`、host `a0cf7ed8`、core `87b1ae13`を参照した。対象はLinux addonとAndroid pluginであり、Windows/Mac/IBus全体の再設計は含めない。

## ユーザー要求

要求と実装手段を区別する。下表の出所はユーザー発言を記録したIssueまたは本会話であり、記録にない原発言日時は推測しない。

|ID|要求|要求者・日時・出所|目的・採用経緯|
|---|---|---|---|
|R-01|Fcitx5プラグイン形式を使いcore/plugin/hostの3repoを維持する|ユーザー。[初期 #1](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/1)、3repo維持は2026-10-10本会話/[#13](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/13)|共通coreを再利用しIMEサービス・画面とaddonの責務を分ける|
|R-02|Android実装を完成し実機へ導入する。追加端末もUSBで導入する|ユーザー。2026-10-10本会話/[#8](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/8)|moto g31、F-52E、Pixel 7で入力を使う。既存IMEとデータを保持する|
|R-03|Gboard/ATOKを参考にキーボードを作る|ユーザー。2026-10-10/[plugin #10](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/10)、[host #9](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/issues/9)|QWERTY・数字段・記号ページ・左右矢印の操作とキーの視認性を整える|
|R-04|Gitea plugin名称をfcitx5-meltypeへ統一し公開先・ビルド・APK入手先を整理する|ユーザー。2026-10-10本会話/[#13](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/13)|3repoの入口を明確にし、未公開APKや未mergeを正確に案内する|
|R-05|要求定義・要件定義・基本設計・フローその他の図をrepoへ置く|ユーザー。2026-10-10本会話/[#13](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/13)追記|要求から実装と検証を追跡できるようにする。既存設計文書を更新し重複しない|

## 実装判断・提案・未決

NativeAOT、arm64-v8a先行、Androidのin-process MozcはAgentによる実装判断として採用・検証した。ユーザーの初期要求そのものと混同しない。Gboard/ATOKの完全な複製、12キー/フリックの採用、他ABI対応、GitHub APK Release公開は確定要求に含めない。

Android実装は検証済みブランチにあり、mainへ未merge。core head CI17件未開始（Windows/macOS適合runner無し、Linux待機原因未特定）による待機は残作業で、実機成功をCI成功へ置き換えない。Pixel 7のGUI確認は端末解除待ち。[現状と検証](TESTING.md)を参照する。

[要件と受入対応](SPECIFICATIONS.md) / [基本設計](ARCHITECTURE.md) / [文書一覧](README.md)
