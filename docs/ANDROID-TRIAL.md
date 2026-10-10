# Android試用版の導入

原作はYukishiro（@yksr_melt / GitHub: [yksr-melt](https://github.com/yksr-melt)）による [Meltype](https://github.com/yksr-melt/Meltype) です。この試用版はFcitx5向けの移植・連携版で、原作の公式配布ではありません。ライセンスと既存NOTICEを保持しています。

## 入手と導入

[android-v0.1.0-alpha.1 のPre-release](https://github.com/hogehonya/fcitx5-meltype/releases/tag/android-v0.1.0-alpha.1)から、導入用ZIP `meltype-android-v0.1.0-alpha.1-install.zip` を取得して展開してください。ZIPには本体とMeltypeプラグインの2 APK、導入案内、ライセンス文書が入っています。通常の利用にテストAPKは不要です。

1. Android API24以上（Android7.0以上）のarm64端末で、ZIPを展開して本体APK、続いてMeltypeプラグインAPKをインストールする。必要なら使用中のファイル管理アプリに「不明なアプリのインストール」を許可する。
2. Androidのキーボード設定で「Fcitx5 Debug」を有効にして、入力中のキーボード切替から選ぶ。
3. Fcitx5の入力メソッド一覧へMeltypeを追加し、Meltypeを選ぶ。
4. `nihongo`を入力しSpaceで日本語候補を表示、候補を選んでEnterで確定する。混在入力例は`kyouhagithubnipushshita` → `今日はgithubにpushした`。

既存のATOK/Gboard等を削除する必要はありません。本体はdebug packageのため公式Fcitx5とは共存できます。別のFcitx5 Debugが既にあり署名が違う場合は更新できません。データを消して解決せず、元の環境を保持して導入を止めてください。試用をやめるときはAndroidのキーボード切替で元のIMEへ戻せます。

## 試用版の範囲

stable版ではありません。両APKは同じdebug署名で、正式版と署名互換を保証しません。APKそのものは実機検証したファイルから変更していません。

- arm64-v8aのみ。plugin利用の下限はAPI24で、本体のminSDK23とは区別します。
- moto g31 Android12、F-52E Android16、Pixel7 Android17で日本語・英日混在入力、学習保存と別process再読込のinstrumentationが成功。
- GUIキー入力・Space候補・選択/Enter確定はmoto g31 darkとF-52E lightで確認。Pixel7 GUI、API24下限端末、16KB page端末は未確認。
- 変換履歴以外のNativeAOT JSON保存、全focus/password/回転等の網羅試験は未完。Mozc固有学習callbackは未対応です。
- 2026-10-10時点でCIは未完、Android実装3PRは未merge。[core PR8](https://gitea.honya.dev/honya-dev-forks/meltype/pulls/8) / [plugin PR11](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/pulls/11) / [host PR11](https://gitea.honya.dev/honya-dev-forks/fcitx5-android/pulls/11)。試用版公開はCI完了・stable化を意味しません。

確認範囲と過去の実測は[TESTING](TESTING.md)、要求・要件・設計は[文書一覧](README.md)を参照してください。問題は端末/Android版・操作・期待結果を添えて[Issue](https://github.com/hogehonya/fcitx5-meltype/issues)へ報告できます。個人の入力文や学習ファイルを公開する必要はありません。

## ソース・SHA256・ライセンス

同じPre-releaseに `meltype-android-v0.1.0-alpha.1-corresponding-source.tar.xz`、`release-manifest.json`、`SHA256SUMS` を添付します。対応ソースはcore `87b1ae13`、plugin `14cbeaa`、host `a0cf7ed8`で、必要な公開依存の固定参照・取得手順、ライセンス全文、ビルド入力も含みます。展開後の `SOURCE-README.md` と `bootstrap-sources.py` が入口です。

**GitHubが自動生成する「Source code (zip/tar.gz)」はタグ位置の文書mainで、未mergeのAndroid実装は含みません。APK対応ソースは上記の添付CorrespondingSourceを使ってください。** 署名秘密鍵は配布しません。ソースから生成したAPKの署名とversion metadataは配布APKと異なることがあります。

SHA256は `SHA256SUMS` またはmanifestと照合できます。ライセンス文書は導入ZIPと対応ソースに同伴し、原作・Fcitx5/Mozc・第三者の著作権を保持します。
