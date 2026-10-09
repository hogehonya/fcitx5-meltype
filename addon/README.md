# Meltype Fcitx5 addon

[Issue #6](https://gitea.honya.dev/honya-dev-forks/meltype-android/issues/6) の Linux 最小プラグインです。`engine.cpp`、`session.h`、`meltype_abi.h` は Android でも共有する入力・ABI 部分、`factory.cpp` は Linux の Mozc helper 初期化です。
Android の in-process Mozc bridge は [Issue #5](https://gitea.honya.dev/honya-dev-forks/meltype-android/issues/5) で別に実装します。Android factory・host 登録・APK はまだありません。この CMake 入口は Android を受け付けず、未完成の APK 成功を装いません。

## Linux build

C++17 compiler、CMake、Fcitx5 Core/Config/Utils development headers、nlohmann-json が必要です。Debian 系では `libfcitx5core-dev libfcitx5config-dev libfcitx5utils-dev nlohmann-json3-dev` を用意します。
既存の Linux NativeAOT `libMeltypeNative.so` と Mozc helper を指定します。バイナリはこの repo に収録しません。

```bash
native_dir="$HOME/.local/opt/meltype-1.0.0" # 配布版を展開した場所
cmake -S addon -B build/addon \
  -DMELTYPE_NATIVE_LIBRARY="$native_dir/libMeltypeNative.so" \
  -DCMAKE_INSTALL_PREFIX="$HOME/.local"
cmake --build build/addon
```

初期検証に使用したものは Linux x86_64 配布 v1.0.0 と Fcitx5 5.1.12、nlohmann-json 3.11.3、CMake 3.31.6、G++ 14.2.0 です。Linux fork core の自前 build はこの addon 検証の入力ではありません。既存の Android NativeAOT build の依存固定値は [deps.lock.json](../scripts/deps.lock.json) を維持しています。

## 実 core / Fcitx InputContext test

ユーザーの設定・学習データを触らない新しい HOME と Mozc profile で実行します。隔離先にはテスト成果物が残ります。

```bash
test_home=$(mktemp -d "${TMPDIR:-/tmp}/meltype-fcitx-test.XXXXXXXX")
HOME="$test_home" XDG_DATA_HOME="$test_home/data" XDG_CONFIG_HOME="$test_home/config" \
MELTYPE_MOZC_HELPER="$native_dir/mozc/meltype_mozc_helper" \
MELTYPE_MOZC_PROFILE="$test_home/mozc" \
ctest --test-dir build/addon --output-on-failure
```

実共有ライブラリと helper、実 Fcitx InputContext を使い、混在文、英単語、入力欄間の独立、候補クリック、release、password、reset、非 BMP キー、UTF-16 → UCS4 削除境界、NULL 結果を確認します。必須 helper/profile がない場合はテストが失敗します。モック成功へ置き換えません。別の異常回復 test は ABI スタブで初期化失敗・壊れた JSON・危険な削除を注入し、例外を host へ漏らさず session を破棄することを確認します。

## 導入と起動

`cmake --install build/addon` は `lib/fcitx5/libmeltype.so` と `share/fcitx5/{addon,inputmethod}/meltype.conf` を install prefix に配置します。NativeAOT ライブラリの install RPATH は指定したライブラリのディレクトリです。移動した場合は再 configure/build が必要です。
Fcitx の起動環境に次を設定し、Fcitx 設定から入力メソッド Meltype を追加します。既存の入力環境を停止・変更する操作はこの build では行いません。
起動環境を永続化する場合は、下の export の絶対パスを確定したうえで `~/.xsessionrc` に追加してください。既存の内容を保持し、同じ設定は重複させず更新します。文書を保存して再起動すると、Fcitx の開始時から継承されます。`native_dir` 変数自体はログイン環境には存在しないため、永続設定では helper の絶対パスを直接指定します。

```bash
export FCITX_ADDON_DIRS="$HOME/.local/lib/fcitx5:${FCITX_ADDON_DIRS:-/usr/lib/$(gcc -dumpmachine)/fcitx5}"
export FCITX_DATA_DIRS="$HOME/.local/share/fcitx5:${FCITX_DATA_DIRS:-/usr/share/fcitx5}"
export MELTYPE_MOZC_HELPER="$native_dir/mozc/meltype_mozc_helper"
export MELTYPE_MOZC_PROFILE="${XDG_DATA_HOME:-$HOME/.local/share}/Meltype/mozc"
```

helper は絶対パス必須、profile を指定する場合も絶対パスです。未指定 profile は core 既定保存先を使用します。初期化失敗は addon load を拒否します。
配布 v1.0.0 の Linux ABI には `meltype_set_data_directory` がないため、この Linux factory は呼びません。Android factory は既存の固定 core にあるその API を session 作成前に呼び、host の私有領域を設定する必要があります。

## 共通 ABI と状態

文字列は UTF-8 NUL 終端、handle は入力欄ごとに一つです。結果 JSON は RAII で必ず `meltype_free` へ戻します。共有 API は Fcitx event thread 上で直列に呼びます。C++ 例外を host へ漏らさず、入力文字列をエラーログへ出しません。Native core 自体の不正 handle 保護を仮定せず、handle の作成・破棄は adapter が管理します。

`commits[]` の編集、preedit、候補、候補選択、surrounding text を Fcitx UI へ反映します。Fcitx の Unicode cursor は UTF-8 の文字境界で切り、core の `deleteBefore` (UTF-16 単位) を UCS4 文字数へ変換します。サロゲート途中や取得済み文脈を超える削除は拒否します。選択範囲のある入力欄・password/sensitive 欄の文脈は渡しません。password/sensitive キーと非 BMP キーは host へそのまま通します。reset / deactivate は未確定入力を確定します。非 BMP / 未対応キーを通す前にも未確定文字を確定し、入力順序を維持します。例外時は session を破棄して UI を消し、次の入力で新規作成します。
入力メソッドの直接英数切り替えは Fcitx の Ctrl+Space で行います。隔離 GUI で `meltype` → `keyboard-us` → `meltype` の切り替えを確認しました。

Linux では上流 `meltype_init_mozc` と既存 helper が変換・Mozc 学習を担当します。Android では共通 engine/session に [ARCHITECTURE](../docs/ARCHITECTURE.md) の callback bridge を接続し、process 実行は使いません。Android bridge の学習 callback、ABI/header 合流、packaging は未実装です。

## 実行結果

2026-10-10 に上記 Linux build、実 core integration test と異常回復 test (2/2) が成功しました。別 D-Bus / Xvfb の GTK 入力欄で addon をロードし、`kyouhagithubnipushshita` + Enter が `今日はgithubにpushした` になる実 GUI 確認も成功しました。通常デスクトップの入力設定はその検証では変更していません。Android クロス build・APK・端末試験は未実施です。

キー変換と JSON 表示契約は GPL-3.0-or-later の上流 Meltype `linux/ibus-engine-meltype` (Copyright 2026 Yukishiro) と core ABI に基づきます。NativeAOT / Mozc / Fcitx の既存ライセンスと NOTICE は配布元のものを保持してください。
