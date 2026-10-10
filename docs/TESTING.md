# 検証と受入条件

以下に2026-10-10の実機結果と継続する受入条件を示します。Androidコードは検証済み未mergeブランチにあり、このmainのコードだけで同じAPKを作れるとは扱いません。Linuxの動作をAndroidの証拠に流用しません。

## 2026-10-10のAndroid受入結果

[要件・VR対応](SPECIFICATIONS.md)のVR-02〜07を検証しました。詳しい実行記録・成果物SHA256は[plugin14cbeaaの検証正本](https://gitea.honya.dev/honya-dev-forks/fcitx5-meltype/src/commit/14cbeaa/docs/TESTING.md)を参照します。

|端末・接続|通常phase / 別process reload|GUI確認|
|---|---|---|
|moto g31 Android12 arm64、USB|2.829s / 最終host25で2.305s PASS|dark、日本語キー入力・Space候補・tap/Enter確定済み|
|F-52E Android16 arm64、USB|1.549s / 0.968s PASS|light、日本語候補表示・確定済み|
|Pixel7 Android17 arm64、USB|1.490s / 0.985s PASS|Fcitx有効/default確認、GUIは画面ロック解除待ち|

通常phaseはnihongo→日本語、kyouhagithubnipushshita→今日はgithubにpushしたの完全一致と非既定hashi候補のJSON保存を確認します。reloadは別processでSpace変換後の先頭候補とcommitへ学習が戻ることを確認します。ICU初期化・addonロード成功、.broken無しを確認。変換履歴のAOT読込はsource-generated serializerで修正済みです。

APK build/checker、Python30件、bridge engine、core186件が成功。16KB ELF LOAD alignmentは確認済みですが、16KB page端末、API24下限、変換履歴以外のJSON用途、全focus/回転/記号/矢印は実機未確認。Mozc固有学習callbackは未対応。host lintは既存269件で失敗、変更ファイル0件と分離記録しています。coreのhead CI17件は未開始。Windows/macOS適合runnerはなく、Linux待機原因は未特定、実装3PRは依存順にmerge保留。

APKは `/home/honya/Downloads/Meltype-Android-20261010/` に保管し、GitHub Release未公開。既存IMEを保持してhost25/plugin28を追加導入しました。

以下の項目は過去のmainビルド検証と、残る受入条件です。各項目を全て実機合格したという意味ではありません。

## ビルド成果物の検証 (自動)

[scripts/build-core.py](../scripts/build-core.py) は build の入力と成果物を自動で検証します。次が
合格条件で、1つでも外れたら成果物を残さず非 0 で終わります。実 build の実行記録は
[BUILD.md の実行記録](BUILD.md#実行記録)にあります。

- core の SHA が lock の固定値で、作業ツリーが clean
- `dotnet --version` と NDK の `Pkg.Revision` が lock の固定値
- core の `InvariantGlobalization=false` が維持されている
- publish ログと発生した警告が保存されている (警告の存在を成功条件にはしない)
- `llvm-readelf` で `ELF64` / `AArch64` / `DYN` (little endian) である
- `meltype_init` / `meltype_create` / `meltype_destroy` / `meltype_handle_key` / `meltype_commit` /
  `meltype_select_candidate` / `meltype_set_direct` / `meltype_free` / `meltype_set_data_directory`
  が定義済みシンボルとして export されている (`meltype_init@@V1.0` のような版付きも可)
- すべての `LOAD` セグメントの `p_align` が 16384 以上
- 成果物の SHA256 が manifest の記録と一致し、元 core に build 出力が残っていない

mainの旧NativeAOT単体成果物では未確認だった項目（Android完成ブランチの結果は上記）:

- 実機 Android での ICU/globalization の解決
- 設定・学習の JSON 保存（変換履歴のみ上記で確認）
- APK への収録と端末での動作

単体テスト (`tests/`) の内容と実行方法は [tests/README.md](../tests/README.md) を参照してください。

## build・ロード

- 固定core/host/submodule SHA、.NET SDK/runtime pack、JDK、NDK、SDK、ABIを記録し、新しいcloneから再現する。
- NativeAOT `.so`のarm64 ABI、C exports、SONAME/NEEDED、16KB ELF alignmentを確認する。APK packagingのalignmentも調べ、4KB/16KB環境で起動する。[Android 16KB検証](https://developer.android.com/guide/practices/page-sizes)
- host minSDK 23と採用NativeAOTのminimum APIを照合し、対応下限の端末でもdlopen・初期化が成功する。
- ICU/globalizationと必要ならcrypto/libsslを含め、依存不足・辞書不足時はエラーを示し、IMEサービスを落とさない。
- plugin APK導入後にMeltypeがFcitx入力方式一覧へ現れ、既存Mozc等と切り替えられる。

## ABI・寿命・保存

- callbackのUTF-8/NUL、NULL失敗、文節形式、malloc/free所有権を検証し、反復入力・focus切替・context破棄で漏れや二重解放を起こさない。
- key処理を同threadに直列化し、C++例外・managed例外をABIの外へ漏らさない。未対応keyは通常入力へ渡す。
- host IMEの私有filesDirに設定・学習が保存され、再起動後に再読込できる。readonly・容量不足・不正JSONでIME全体を落とさない。ログに入力内容やsecretを不用意に残さない。
- Mozc Learn callbackを実装した場合、候補確定とsave/restartで学習が反映される。未実装ならMozc学習未対応を明示し、Meltype側の学習と混同しない。
- wordProvider/isWordの辞書あり・なし両方で英語判定を確認する。NULL経路を完成した辞書実装として扱わない。

## 入力とUI

- soft keyboardとhardware keyboardで英語、日本語、混在入力を試す。例として`kyouhagithubnipushshita`の期待結果「今日はgithubにpushした」を確認し、端末・設定・実入力操作を記録する。
- Space変換・複数候補表示・候補tap・確定・Backspace・Enter・direct切替がcommit/preeditへ正しく反映される。
- surrounding textが取得できる場合とできない場合を確認する。focus移動、reset、アプリ切替、password入力欄で未確定文字・学習の扱いを確認する。
- 日本語候補、英語保持、文節境界、空文字、非BMP文字についてcursor/UTF-16とFcitx側の位置単位を照合する。

[ビルド](BUILD.md) / [構成](ARCHITECTURE.md) / [文書一覧](README.md)

## Linux addon の実行済み検証

[addon/README.md](../addon/README.md) の実 NativeAOT / Fcitx InputContext integration test と、隔離 D-Bus / Xvfb の GTK 混在文入力が成功しました。Android APK と端末試験の成功を意味しません。

## hostキーボードの設計受入

[R-03要求](REQUIREMENTS.md)と[基本設計](ARCHITECTURE.md)の受入項目です。moto dark/F-52E lightの日本語操作は上記で確認済み。次の全操作の網羅検証とPixel GUIは未完です。

- QWERTY・数字行を維持しローマ字・英語・混在入力のラベルと入力結果を照合する。
- 主画面`@`・句読点、記号面への到達と復帰、左右矢印を確認する。
- 候補表示とtap対象が一致しaddonへeventが届き正しい候補を確定する。
- IME切替と配列/記号面切替のラベル・操作・結果を区別し既存入力を維持する。
- light/dark双方でキー境界・文字・候補・選択状態が読める。日本語デザイン成果物の実装はIBM Plex Sans JPを使用する。
- 実機画面と操作で採否を記録する。12キー/フリックは別途採用決定が必要。
