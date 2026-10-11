# 要求定義

## 目的と資料

Meltypeの英日混在入力をFcitx5で使用し、Android端末でも入力・候補確定・学習を利用できるようにする。正本としてREADME、既存ARCHITECTURE/BUILD/TESTING、初期実装と、予測対応plugin `64009ff`、製品host `047277e6`、core `353995a`（試験修正host `1e0295f9`）を参照した。対象はLinux addonとAndroid pluginであり、Windows/Mac/IBus全体の再設計は含めない。

## ユーザー要求

要求と実装手段を区別する。下表の出所はユーザー発言を記録したIssueまたは本会話であり、記録にない原発言日時は推測しない。

|ID|要求|要求者・日時・出所|目的・採用経緯|
|---|---|---|---|
|R-01|Fcitx5プラグイン形式を使いcore/plugin/hostの3repoを維持する|ユーザー。[初期 #1](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/1)、3repo維持は2026-10-10本会話/[#13](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/13)|共通coreを再利用しIMEサービス・画面とaddonの責務を分ける|
|R-02|Android実装を完成し実機へ導入する。追加端末もUSBで導入する|ユーザー。2026-10-10本会話/[#8](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/8)|moto g31、F-52E、Pixel 7で入力を使う。既存IMEとデータを保持する|
|R-03|Gboard/ATOKを参考にキーボードを作る|ユーザー。2026-10-10/[plugin #10](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/10)、[host #9](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/issues/9)|QWERTY・数字段・記号ページ・左右矢印の操作とキーの視認性を整える|
|R-04|Gitea plugin名称をfcitx5-meltypeへ統一し公開先・ビルド・APK入手先を整理する|ユーザー。2026-10-10本会話/[#13](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/13)|3repoの入口を明確にし、未公開APKや未mergeを正確に案内する|
|R-05|要求定義・要件定義・基本設計・フローその他の図をrepoへ置く|ユーザー。2026-10-10本会話/[#13](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/13)追記|要求から実装と検証を追跡できるようにする。既存設計文書を更新し重複しない|

|R-06|入力途中の予測変換を追加する|ユーザー。2026-10-10「予測変換も追加してほしいな、予測変換がでたら上一行はいらないかも」、[core #9](https://gitea.honya.dev/honya-dev-forks/meltype/issues/9) / [plugin #27](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/27)|候補tap即確定はAgent採用案。2026-10-11に「半透明の凡例」「space 確定＋空白」と特定され、Android操作説明hintだけを非表示とする。2026-10-11「pixel7も修正を」「ドキュメント更新も」で追加端末・正本更新を継続。「POBOXみたいな予測変換」は入力途中の横候補/tap確定へ対応。2026-10-11「確定後も出せるなら出してみよう」で次語予測も採用（[変更記録](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/27#issuecomment-59533)）|
|R-07|未確定全文をかな・カナ・英数へ一回変換する|ユーザー。2026-10-10 [かな/カナ #24](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/24) / [英数 #26](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/26)|F6/F7/F10を使用する。永続直接英字モードとは区別し、次compositionへ英数変換を持ち越さない|

## 実装判断・提案・未決

NativeAOT、arm64-v8a先行、Androidのin-process MozcはAgentによる実装判断として採用・検証した。ユーザーの初期要求そのものと混同しない。Gboard/ATOKの完全な複製、12キー/フリックの採用、他ABI対応、GitHub APK Release公開は確定要求に含めない。

以下は2026-10-11の各試験時点の履歴です。当時Android実装は実装ブランチを対象とし、既存main公開PR core #8 / plugin #11は未mergeでした。2026-10-11のF-52E USB native受入は予測・通常変換・学習再読込・英字・かな英数切替が成功。次語統合版host62/plugin62/test63はF-52E次語・予測・切替・英字・reload・Enter native受入成功。normalはUSB切断で未実施、core CI17pending/plugin noCIのため統合保留。Pixel 7の今回版更新・予測受入は継続中。F-52E GUIは後続の明示送信許可により合成文で候補行・凡例非表示・1回目Enter確定/送信なし・2回目Enter改行をcurrent確認。private画面・会話は保存しない。最新のPixel 7受入・公開状況は[現状と検証](TESTING.md#2026-10-11-alpha1差し替え公開の確認範囲)を参照してください。CI修復と統合は[Issue #36](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/36)で追跡し、この履歴を現時点のCI成功の証拠とは扱いません。

[要件と受入対応](SPECIFICATIONS.md) / [基本設計](ARCHITECTURE.md) / [文書一覧](README.md)

## 2026-10-10のレビュー修正

ユーザーが本会話で「いいですね、修正しよう」と承認した3指摘は[#15](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/15)で追跡します。R-01/R-04/R-05の範囲内で、恒久要件と公開進捗の分離、Linux受入と共通変更時の回帰、ソース所属とAPK収録先の図の区別を明確にします。新機能要求の追加ではありません。

## 英字モードの追加要求（Issue #20）

2026-10-10本会話でユーザーが「meltype自体に無変換もできるといいな英字モード」と要求。Meltype選択中の直接英字入力を追加する。無変換で開始し変換/ひらがなで通常へ復帰する操作は親Agentの採用案であり、キー割当までユーザー指定とは扱わない。[Issue #20](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/20)で実装・受入を追跡する。

## Android英字モード反映（Issue #22）

2026-10-10本会話でユーザーがLinux英字mode完成後「反映させて」とAndroidへの反映・実機更新を要求。Linux PR21の共有engineを取り込み、画面用のMeltype専用ABC/かな操作と物理無変換/変換mappingを接続する（画面操作はAgent採用案）。既存LanguageKey/数字記号面ABC layout切替は維持。公開試用版assetは変更せず、今回buildしたAPKをUSB指定端末へ更新して別に検証する。

## 送信後のFocusOut（R-08、Issue #30）

2026-10-11 ユーザー「それで試して実装してテストしよう」。F-52E Signal 8.30.3で未確定合成文をSpace変換後にアプリ送信すると同文が欄へ戻る。ATOK同手順は欄が空（root観測）。FocusOutの独自再commitを止める案を採用し、[Issue #30](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/issues/30)で追跡する。通常reset・IME切替・明示確定を保持し、端末再受入で効果を確認する。
