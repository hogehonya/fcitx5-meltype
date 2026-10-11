# Android package notices

Meltype is GPL-3.0-or-later; its copyright and upstream attribution are in LICENSE and NOTICE. Original upstream platform notices are preserved in licenses/Meltype-THIRD-PARTY-NOTICES.md.

The Android addon statically links the Mozc OSS conversion engine and dictionary, Protocol Buffers and Abseil from the fixed source revisions documented in native/README.md. Full Mozc BSD, protobuf BSD and Abseil Apache-2.0 license texts and Mozc dictionary/third-party credits are installed under usr/share/fcitx5/meltype/licenses in the APK assets.

libMeltypeNative.so includes .NET NativeAOT 10.0.0 runtime code. The runtime package's original MIT license and complete third-party notices are preserved in licenses/NativeAOT-LICENSE.txt and licenses/NativeAOT-THIRD-PARTY-NOTICES.txt and installed with the APK. These files come from Microsoft.NETCore.App.Runtime.NativeAOT.linux-bionic-arm64 10.0.0.

Fcitx5 and libc++ providers are supplied by the host APK; this plugin does not duplicate their shared libraries. Preserve host licenses when distributing the matching host application.

nlohmann-json 3.11.3 headers are compiled into the adapter. The original distribution copyright file and complete MIT (Expat) license are preserved in licenses/nlohmann-json-copyright and installed with the APK.
