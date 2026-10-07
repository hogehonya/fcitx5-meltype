# tests/fixtures

[../test_build_core.py](../test_build_core.py) が使う `llvm-readelf` の出力です。すべて NDK r28
(`28.0.13004108`) の `toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf` (LLVM 19.0.0) で
取得した実物の出力をそのまま置いています。

取得元はテスト用の stub 共有ライブラリ (`meltype_*` と同じ名前の関数を持つ C ソースを
`aarch64-linux-android21-clang -shared` で build したもの) で、NativeAOT の成果物ではありません。
そのため、これらのファイルは「build が成功した証拠」ではなく、検証コードの入力形式の記録です。

|ファイル|取得元|
|---|---|
|`readelf-ok-header.txt`|`llvm-readelf -h ok.so`|
|`readelf-ok-program-headers.txt`|`llvm-readelf -l ok.so` (`-Wl,-z,max-page-size=16384`)|
|`readelf-align-4k-program-headers.txt`|`llvm-readelf -l align4k.so` (`-Wl,-z,max-page-size=4096`)|
|`readelf-ok-dynamic.txt`|`llvm-readelf -d ok.so`|
|`readelf-ok-dyn-syms.txt`|`llvm-readelf --dyn-syms ok.so` (9 export、版なし)|
|`readelf-missing-export-dyn-syms.txt`|`llvm-readelf --dyn-syms noexport.so` (`meltype_free` なし)|
|`readelf-versioned-dyn-syms.txt`|`llvm-readelf --dyn-syms versioned.so` (`--version-script` で `meltype_init@@V1.0` 形式)|

版付きシンボルの fixture は、実際の NativeAOT 共有ライブラリ (`V1.0` の version script を使う) で
`meltype_init@@V1.0` のように export されることを受けて追加しました。
