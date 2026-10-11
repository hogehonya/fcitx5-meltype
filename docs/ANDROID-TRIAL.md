# Android試用版の導入

原作はYukishiro（@yksr_melt / GitHub: [yksr-melt](https://github.com/yksr-melt)）による [Meltype](https://github.com/yksr-melt/Meltype) です。この試用版はFcitx5向けの移植・連携版で、原作の公式配布ではありません。ライセンスと既存NOTICEを保持しています。

## 入手と導入

[android-v0.1.0-alpha.1 のPre-release](https://github.com/hogehonya/fcitx5-meltype/releases/tag/android-v0.1.0-alpha.1)から、導入用ZIP `meltype-android-v0.1.0-alpha.1-install.zip` を取得して展開してください。ZIPには本体とMeltypeプラグインの2 APK、導入案内、ライセンス文書が入っています。通常の利用にテストAPKは不要です。

1. Android API24以上（Android7.0以上）のarm64端末で、ZIPを展開して本体APK、続いてMeltypeプラグインAPKをインストールする。必要なら使用中のファイル管理アプリに「不明なアプリのインストール」を許可する。
2. Androidのキーボード設定で「Fcitx5 Debug」を有効にして、入力中のキーボード切替から選ぶ。
3. Fcitx5の入力メソッド一覧へMeltypeを追加し、Meltypeを選ぶ。
4. `nihongo`を入力しSpaceで日本語候補を表示、候補を選んでEnterで確定する。混在入力例は`kyouhagithubnipushshita` → `今日はgithubにpushした`。

既存のATOK/Gboard等を削除する必要はありません。本体はdebug packageのため公式Fcitx5とは共存できます。別のFcitx5 Debugが既にあり署名が違う場合は更新できません。データを消して解決せず、元の環境を保持して導入を止めてください。試用をやめるときはAndroidのキーボード切替で元のIMEへ戻せます。

## 更新版の機能と確認範囲

2026-10-11、host62 / plugin68への差し替えを公開しました。導入ZIP・対応ソース・manifest・SHA256SUMSの4ファイルを再取得し、配布前原本と完全一致を確認しました。取得時にRelease本文・manifest・SHA256SUMSを確認してください。

- 入力中の予測候補と、確定後に辞書が候補を返す文脈での次語予測を表示します。候補がない文脈では表示しません。
- 「あ/ア」は未確定文字をかな/カナへ切り替え、「英数」は半角英数へ変換します。恒久的な入力モードや12キーかな配列ではありません。空入力で変換キーはアプリへ送られません。
- 未確定時の画面Enterは確定だけを行い、空入力時はeditorの送信・完了・改行設定に従います。focus-outでクライアント消去済みの文字を独自に再確定しません。
- 半透明aux凡例を除去し、予測/変換候補行を保持します。
- 機能追加段階のF-52E Android16/arm64でEnter、次語、予測、あア/英数、直接英字、学習再読込のinstrumentationを確認。plugin68ではeditorclear試験のみを追加確認し、他のnative回帰は再実行待ちです。通常phase全体はUSB切断により未実施です。GUIは許諾下の合成文でEnter確定と送信後消去・20秒間再投入なしを確認しました。
- Pixel7 Android17は無線更新の許諾後にhost62/plugin68/test71を導入し、editorclear（1.599秒）、Enter3件（0.218秒）、次語（1.74秒）が成功。プロフィール原状復帰とMeltype選択の維持を確認しました。GUIは画面ロック中で未確認、他のnative回帰は未実行。以下の3台の実績は初版の記録であり最新版へ引き継いだ検証とは扱いません。

## 初版の実測と共通制限

stable版ではありません。両APKは同じdebug署名で、正式版と署名互換を保証しません。APKそのものは実機検証したファイルから変更していません。

- arm64-v8aのみ。plugin利用の下限はAPI24で、本体のminSDK23とは区別します。
- moto g31 Android12、F-52E Android16、Pixel7 Android17で日本語・英日混在入力、学習保存と別process再読込のinstrumentationが成功。
- GUIキー入力・Space候補・選択/Enter確定はmoto g31 darkとF-52E lightで確認。Pixel7 GUI、API24下限端末、16KB page端末は未確認。
- 変換履歴以外のNativeAOT JSON保存、全focus/password/回転等の網羅試験は未完。Mozc固有学習callbackは未対応です。
- 2026-10-11時点でも必要なCIは未完、Android実装は既定mainへ未merge。[core PR8](https://gitea.honya.dev/honya-dev-forks/meltype/pulls/8) / [plugin PR11](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/pulls/11) / [host PR11](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/pulls/11)。試用版公開はCI完了・stable化を意味しません。

確認範囲と過去の実測は[TESTING](TESTING.md)、要求・要件・設計は[文書一覧](README.md)を参照してください。問題は端末/Android版・操作・期待結果を添えて[Issue](https://github.com/hogehonya/fcitx5-meltype/issues)へ報告できます。個人の入力文や学習ファイルを公開する必要はありません。

## ソース・SHA256・ライセンス

同じPre-releaseに `meltype-android-v0.1.0-alpha.1-corresponding-source.tar.xz`、`release-manifest.json`、`SHA256SUMS` を添付します。初版の対応ソースはcore `87b1ae13`、plugin `14cbeaa`、host `a0cf7ed8`でした。差し替え版はcore `444ce0d6532aa727987e6409b010e91a3889786e`、plugin `f5974122208e47a4c8f85b26f29acb200ba6aae5`（APK製品ソース `3134d2f91096a10f62b2e571f827f7ebd47230c3` との差は文書のみ）、host `52e506a9775eba9d9c936afd4eb257c8b4662f23` をmanifestへ記録し、必要な公開依存の固定参照・取得手順、ライセンス全文、ビルド入力も含みます。展開後の `SOURCE-README.md` と `bootstrap-sources.py` が入口です。

**GitHubが自動生成する「Source code (zip/tar.gz)」はタグ位置の文書mainで、未mergeのAndroid実装は含みません。APK対応ソースは上記の添付CorrespondingSourceを使ってください。** 署名秘密鍵は配布しません。ソースから生成したAPKの署名とversion metadataは配布APKと異なることがあります。

SHA256は `SHA256SUMS` またはmanifestと照合できます。ライセンス文書は導入ZIPと対応ソースに同伴し、原作・Fcitx5/Mozc・第三者の著作権を保持します。
