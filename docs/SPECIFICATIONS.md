# 要件定義

[要求定義](REQUIREMENTS.md)を、実装で判定できる条件へ分解する。S-01/S-08とNFは共通の責務・文書・制約、S-02〜07/S-10〜12はAndroid、S-09はLinux addonの仕様です。Androidは検証済み実装ブランチを対象とし、mainへ全コードが反映済みという意味ではありません。実測と未確認範囲の正本は[TESTING](TESTING.md)、固定ビルド入力の正本は[BUILD](BUILD.md)。

## 機能要件と受入

|ID|要求|仕様|受入ID・確認方法・現状|
|---|---|---|---|
|S-01|R-01/R-04|coreは判定・変換・学習/C ABI、pluginはaddon/bridge/APK、hostはIME/UI/module登録を担当する|VR-01: [README](../README.md)役割表、gitlink、基本設計を照合。3repo維持、名称統一済み|
|S-02|R-02|hostの内部保存領域で初期化し、変換・学習が同じ保存先を使用する|VR-02: APK addonロード、ICU初期化、内部保存先を実機確認。3端末ロード成功。API24以上ではロック有無にかかわらずDataManager.dataDirのdevice-protected領域を使用|
|S-03|R-02|キーからpreedit/candidates/commitを反映する。nihongo→日本語、kyouhagithubnipushshita→今日はgithubにpushしたが完全一致する|VR-03: MeltypeTest通常phase。3端末PASS。GUIはmoto/F-52E確認済み|
|S-04|R-02|Spaceで候補を表示し、tapで候補を選択し、Enterで確定する|VR-04: 日本語候補選択・Enter確定。moto/F-52E GUI確認済み、Pixel GUI未確認|
|S-05|R-02|Meltype変換学習をconversions.jsonへ保存し、別processでSpace変換した際の先頭候補・commitへ再適用する|VR-05: 非既定hashi候補保存→通常phase終了→reload phase。3端末PASS。2文字読みはlive変換下限未満なのでSpaceで判定。Mozc固有学習callbackは未対応|
|S-06|R-03|既存QWERTY/数字行/記号面/左右矢印を保ち、新規設定の既定値としてPixel light/darkのキー背景・隙間・角丸とIBM Plex Sans JPを使う。保存済みの明示設定は維持する|VR-06: hostコード確認、moto dark/F-52E lightの日本語入力。全記号・矢印・回転・全IME切替は未確認|
|S-07|R-01/R-02|固定core/NDK/ABIでNativeAOTを生成し、host/plugin/test APKを生成する。共有ライブラリ依存を解決し端末でaddonをロードできる|VR-07: build、APK checker、Python30件、bridge engine、core186件成功。16KB ELF alignment確認、16KB端末未確認|
|S-08|R-04/R-05|READMEから要求・要件・設計・ビルド・検証へ辿れる。公開先・APK配布・merge/CIの現状を証拠と確認日付きで案内し、未公開・未確認を成功扱いしない|VR-08: 文書diff・リンク・独立reviewで確認。可変の進捗は[公開状況](../README.md#androidのビルドとapk入手)を参照|
|S-09|R-01|LinuxでFcitx addonから既存NativeAOT providerと外部Mozc helperへ接続し、混在入力・候補選択・commitを提供する。Android保存先APIをLinux配布ABIへ無条件要求しない|VR-09: Linux実provider/InputContext integrationと異常回復の既存2tests、隔離GTKでkyouhagithubnipushshita→今日はgithubにpushしたを完全一致確認。[Linux記録と回帰条件](TESTING.md#linux-addon-の実行済み検証)|

|S-11|R-06|任意予測providerを登録した日本語Auto編集中と通常日本語確定後に最大20候補を表示する。入力途中の予測tapで全文即確定し、次語tapは選択文字列を追加確定する。次語候補は更新文脈で継続し、新打鍵・空状態Backspace・フォーカス変更で消す。F6/F7/F10の明示変換確定や英数確定後は次語を表示しない。通常Space変換は文節選択後Enterで全文確定する。英語・混在・未完ローマ字・明示かな表示は予測を出さず、provider失敗は通常入力を続ける。Android操作説明auxUp hintを出さず、候補とキーを維持する。Linux hintは維持する|VR-11: prefix版F-52E USB test52成功。次語版はcore予測4件/全190件・実Mozc zero-query試験成功、F-52E host62/plugin62/test63次語/予測受入成功。normal最新版未実施、CI成功待ち。F-52E GUIはcurrent確認成功、Pixelの今回版受入は未確認|
|S-12|R-07|F6/F7で未確定全文をかな/カナへ、F10で英数へ一回変換する。F10確定後は次compositionを新sessionで通常へ戻し、取消では追跡だけを解除して入力文脈を保持する|VR-12: F-52E toggle test49成功（2.257秒）、F6/F7予測抑制はprediction test52成功。Linux F10/取消試験も成功。Pixel最新受入は継続中|

## 非機能要件

|ID|要求|条件|検証境界|
|---|---|---|---|
|NF-01|R-01/R-02|UTF-8/NUL、malloc/free・meltype_freeの所有権、session寿命、Fcitx event threadへの直列化を守り例外をC ABIへ漏らさない|[基本設計](ARCHITECTURE.md)とadapter/bridge試験。全focus/context lifecycleの実機網羅は未完|
|NF-02|R-02/R-04|dirty clone/他session変更を保護し独立checkoutでビルドする。既存IMEとデータを削除せずdebug host/pluginを追加する|出所snapshot、独立worktree、導入実績で確認。cleanupは未merge worktreeを保持|
|NF-03|R-01|GPLと第三者ライセンス・copyright・NOTICEを保持する|source/APK asset検査。独自のライセンス再判定はしない|
|NF-04|R-02|Android対象はarm64-v8a/API24以上。host minSDK23とplugin対象下限を区別する。page size検証を省略しない|Android12/16/17 arm64実機成功。API24下限、他ABI、16KB page端末は未実機検証|

## 未確認・範囲外

Settings/UserModel/LanguageMemory/TranslationDictionary等、変換履歴以外のNativeAOT JSON読書きは未実機検証。readonly/容量不足、password欄、非BMP cursor、hardware入力、回転・focus網羅試験も未確認。host lintの既存失敗は別記し、本変更の検証成功へ混ぜない。Release公開やCI runner新設はこの文書整理に含めない。

[基本設計と図](ARCHITECTURE.md) / [受入実績](TESTING.md) / [文書一覧](README.md)

### S-09の英字直接入力（Issue #20）

未修飾の無変換で入力context単位の直接英字モードへ移る。入力順を維持するため未確定文字・選択中候補を一回確定する。通常キーはアプリへ渡し、Meltype IM選択は維持する。変換/ひらがなで既存の英日自動判定へ戻る。状態表示は直接 `A`、通常 `あ`。モードはreset/deactivate後も同じcontextで保持し、新contextは通常モード。修飾付きモードキー・release・password/sensitive入力は取得しない。VR-09は上記の独立context、pass-through、復帰、二重確定防止を実providerテストで検証する。Android APKへの反映・実機確認は今回の受入範囲外。

### S-10 / VR-10: Android英字直接入力（Issue #22）

[Android反映要求](REQUIREMENTS.md#android英字モード反映issue-22)に対応する。S-09英字状態のshared engineをAndroidにも適用し、hostはMeltype選択時だけABC/かなキーを表示して無変換/変換symを送る。物理Androidキーcodeも対応symへ変換する。既存LanguageKey/数字記号ABCを維持。VR-10は `MeltypeTest -e phase english` のpendingcommit・Virtual文字とSpace完全一致・Meltype/A保持・復帰日本語/あ・物理mapping、および画面キー表示/タップ確認。通常/reloadを回帰し、実行結果はTESTING/Issue #22へ記録する。
