#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate Meltype APK entries, ELF architecture/alignment and loader paths.
Does not install, alter a device, or treat a source tree as a built APK.
"""
import argparse
import json
import re
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path


def check(apk, readelf):
    required = {
        "lib/arm64-v8a/libmeltype.so",
        "lib/arm64-v8a/libMeltypeNative.so",
        "assets/descriptor.json",
        "assets/usr/share/fcitx5/addon/meltype.conf",
        "assets/usr/share/fcitx5/inputmethod/meltype.conf",
        "assets/usr/share/fcitx5/meltype/LICENSE",
        "assets/usr/share/fcitx5/meltype/NOTICE",
        "assets/usr/share/fcitx5/meltype/THIRD-PARTY-NOTICES.md",
        "AndroidManifest.xml",
    }
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix="meltype-apk-check-") as temp:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError("Duplicate APK entries")
        missing = required - set(names)
        if missing:
            raise ValueError(f"Missing APK entries: {sorted(missing)}")
        native = [n for n in names if n.startswith("lib/") and n.endswith(".so")]
        if any(not n.startswith("lib/arm64-v8a/") for n in native):
            raise ValueError("Unexpected ABI; only arm64-v8a was validated")
        if any(Path(n).name.startswith("libFcitx5") or Path(n).name == "libc++_shared.so" for n in native):
            raise ValueError("Duplicate host Fcitx/STL provider in plugin APK")
        descriptor = json.loads(archive.read("assets/descriptor.json"))
        for path in ("usr/share/fcitx5/addon/meltype.conf", "usr/share/fcitx5/inputmethod/meltype.conf"):
            if path not in descriptor["files"]:
                raise ValueError(f"Configuration absent from data descriptor: {path}")
        for name in native:
            raw = archive.read(name)
            if len(raw) < 64 or raw[:6] != b"\x7fELF\x02\x01":
                raise ValueError(f"Not little-endian ELF64: {name}")
            if struct.unpack_from("<HH", raw, 16) != (3, 183):
                raise ValueError(f"Not AArch64 DYN: {name}")
            phoff = struct.unpack_from("<Q", raw, 32)[0]
            phsize, count = struct.unpack_from("<HH", raw, 54)
            if phsize < 56:
                raise ValueError(f"Invalid ELF program header size: {name}")
            loads = 0
            for i in range(count):
                header = phoff + phsize * i
                kind = struct.unpack_from("<I", raw, header)[0]
                if kind == 1:
                    loads += 1
                    align = struct.unpack_from("<Q", raw, header + 48)[0]
                    if align < 16384:
                        raise ValueError(f"LOAD alignment below 16KB: {name}")
            if not loads:
                raise ValueError(f"No LOAD segments: {name}")
            output = Path(temp) / Path(name).name
            output.write_bytes(raw)
            dynamic = subprocess.check_output([str(readelf), "-d", str(output)], text=True)
            needed = re.findall(r"NEEDED.*\[([^]]+)\]", dynamic)
            versions = subprocess.check_output([str(readelf), "--version-info", str(output)], text=True)
            version_providers = re.findall(r"\bFile:\s*(\S+)", versions)
            if set(version_providers) - set(needed):
                raise ValueError(f"Symbol version providers are absent from DT_NEEDED in {name}: {version_providers}")
            if output.name == "libMeltypeNative.so":
                sonames = re.findall(r"SONAME.*\[([^]]+)\]", dynamic)
                if sonames != ["libMeltypeNative.so"]:
                    raise ValueError(f"Bionic requires the NativeAOT provider SONAME: {sonames}")
            if any("/" in library for library in needed):
                raise ValueError(f"Build-path dependency in {name}: {needed}")
            if output.name == "libmeltype.so":
                if "libMeltypeNative.so" not in needed:
                    raise ValueError("Addon does not reference NativeAOT provider by basename")
                paths = re.findall(r"RUNPATH.*\[([^]]+)\]", dynamic)
                if paths != ["$ORIGIN"]:
                    raise ValueError(f"Addon must resolve same-APK provider through $ORIGIN: {paths}")
    return {"apk": str(apk), "abi": "arm64-v8a", "native_libraries": native, "result": "pass"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--readelf", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.apk, args.readelf), ensure_ascii=False))
    except (OSError, ValueError, KeyError, struct.error, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"APK validation failed: {exc}\n")


if __name__ == "__main__":
    main()
