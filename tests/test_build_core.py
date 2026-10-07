# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Yukishiro
"""scripts/build-core.py の単体テスト。

本物の .NET SDK と NDK を使う NativeAOT build はここでは回さない (build 入口の検証だけを行う)。
fake の dotnet / NDK ツールを置いた一時ツリーで script を子 process として実行し、入力検証と
失敗時に成果物・成功 manifest を残さないことを確かめる。ELF 検証は NDK r28 の llvm-readelf で
実際に取った出力 (tests/fixtures) を使う。実ツールを使う統合テストは NDK がある環境だけで走る。
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY_ROOT / "scripts" / "build-core.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

REAL_NDK = Path(os.environ.get("MELTYPE_ANDROID_NDK", "/home/honya/Android/Sdk/ndk/28.0.13004108"))
REAL_NDK_LLVM_BIN = REAL_NDK / "toolchains" / "llvm" / "prebuilt" / "linux-x86_64" / "bin"
# 共有ライブラリを arm64 向けに作る clang wrapper (host 用の clang は x86-64 を作る)。
REAL_TARGET_CLANG = REAL_NDK_LLVM_BIN / "aarch64-linux-android23-clang"

REQUIRED_EXPORTS = [
    "meltype_init",
    "meltype_create",
    "meltype_destroy",
    "meltype_handle_key",
    "meltype_commit",
    "meltype_select_candidate",
    "meltype_set_direct",
    "meltype_free",
    "meltype_set_data_directory",
]

NDK_REVISION = "28.0.13004108"
DOTNET_VERSION = "10.0.100"
NDK_LLVM_BIN = "toolchains/llvm/prebuilt/linux-x86_64/bin"

STUB_SOURCE = """
void *meltype_init(void) { return 0; }
void *meltype_create(void) { return 0; }
void meltype_destroy(void *handle) { (void)handle; }
void *meltype_handle_key(void *handle) { return handle; }
void *meltype_commit(void *handle) { return handle; }
void *meltype_select_candidate(void *handle) { return handle; }
void meltype_set_direct(void *handle) { (void)handle; }
void meltype_free(void *text) { (void)text; }
int meltype_set_data_directory(const char *path) { return path != 0; }
"""


def load_build_core():
    """scripts/build-core.py を module として読む (ファイル名に - があるため直接 import できない)。"""
    spec = importlib.util.spec_from_file_location("meltype_build_core", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BUILD_CORE = load_build_core()


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class BuildCoreTestCase(unittest.TestCase):
    """fake ツールで script を実行する共通の準備。"""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="meltype-build-core-test."))
        self.addCleanup(shutil.rmtree, self.tmp, True)

        self.git_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        }

        self.core = self.tmp / "core"
        self.make_core()
        self.core_sha = self.git("rev-parse", "HEAD").stdout.strip()

        self.ndk = self.tmp / "ndk"
        self.make_fake_ndk()

        self.dotnet = self.tmp / "dotnet"
        self.make_fake_dotnet()

        self.lock = self.tmp / "deps.lock.json"
        self.write_lock()

        self.output = self.tmp / "out"

    # --- 準備 -----------------------------------------------------------------

    def git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(cwd or self.core), *args],
            capture_output=True,
            text=True,
            env=self.git_env,
        )

    def make_core(self, invariant_globalization: str = "false") -> None:
        (self.core / "src" / "Meltype.Core").mkdir(parents=True, exist_ok=True)
        (self.core / "src" / "Meltype.Mac.Native").mkdir(parents=True, exist_ok=True)
        (self.core / "dictionaries").mkdir(exist_ok=True)
        (self.core / "LICENSE").write_text("GPL-3.0-or-later (test fixture)\n", encoding="utf-8")
        (self.core / "THIRD-PARTY-NOTICES.md").write_text(
            "third party notices (test fixture)\n", encoding="utf-8"
        )
        (self.core / "nuget.config").write_text(
            "<configuration><packageSources><clear /></packageSources></configuration>\n",
            encoding="utf-8",
        )
        (self.core / "dictionaries" / "words.txt").write_text("meltype\n", encoding="utf-8")
        (self.core / "src" / "Meltype.Core" / "Meltype.Core.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n'
            "    <TargetFramework>net10.0</TargetFramework>\n  </PropertyGroup>\n</Project>\n",
            encoding="utf-8",
        )
        (self.core / "src" / "Meltype.Mac.Native" / "Meltype.Mac.Native.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n'
            "    <TargetFramework>net10.0</TargetFramework>\n"
            f"    <InvariantGlobalization>{invariant_globalization}</InvariantGlobalization>\n"
            "  </PropertyGroup>\n</Project>\n",
            encoding="utf-8",
        )
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "test fixture")

    def make_fake_ndk(self) -> None:
        llvm_bin = self.ndk / NDK_LLVM_BIN
        llvm_bin.mkdir(parents=True)
        (self.ndk / "source.properties").write_text(
            f"Pkg.Desc = Android NDK\nPkg.Revision = {NDK_REVISION}\n", encoding="utf-8"
        )
        write_executable(
            llvm_bin / "clang",
            "#!/bin/sh\n"
            'if [ "$1" = "--version" ]; then\n'
            "  echo 'Android (000000, fake) clang version 19.0.0 (test stub)'\n"
            "  exit 0\n"
            "fi\n"
            "echo 'stub clang: unsupported: $*' >&2\n"
            "exit 64\n",
        )
        write_executable(
            llvm_bin / "llvm-readelf",
            textwrap.dedent(
                f"""\
                #!/bin/sh
                data="{FIXTURES}"
                case "$1" in
                  --version) echo 'LLVM version 19.0.0 (test stub)'; exit 0 ;;
                  -h) file="$data/readelf-ok-header.txt" ;;
                  -l) file="$data/readelf-${{MELTYPE_TEST_ELF_ALIGN:-ok}}-program-headers.txt" ;;
                  -d) file="$data/readelf-ok-dynamic.txt" ;;
                  --dyn-syms) file="$data/readelf-${{MELTYPE_TEST_ELF_SYMBOLS:-ok}}-dyn-syms.txt" ;;
                  *) echo "stub llvm-readelf: unsupported: $*" >&2; exit 64 ;;
                esac
                cat "$file"
                """
            ),
        )

    def use_real_ndk_tools(self) -> None:
        """ELF 検証を本物の llvm-readelf にする (fake dotnet は本物の clang で stub を作る)。"""
        llvm_bin = self.ndk / NDK_LLVM_BIN
        for name in ("clang", "llvm-readelf"):
            (llvm_bin / name).unlink()
            (llvm_bin / name).symlink_to(REAL_NDK_LLVM_BIN / name)
        (llvm_bin / "aarch64-linux-android23-clang").symlink_to(REAL_TARGET_CLANG)

    def make_fake_dotnet(self) -> None:
        write_executable(
            self.dotnet,
            textwrap.dedent(
                f"""\
                #!/bin/sh
                case "$1" in
                  --version) echo "{DOTNET_VERSION}"; exit 0 ;;
                  publish) ;;
                  *) echo "stub dotnet: unsupported: $*" >&2; exit 64 ;;
                esac
                publish_dir="$PWD/src/Meltype.Mac.Native/bin/Release/net10.0/linux-bionic-arm64/publish"
                mode="${{MELTYPE_TEST_DOTNET_MODE:-ok}}"
                echo "  Determining projects to restore..."
                case "$mode" in
                  fail)
                    echo "error NETSDK1045: fake failure for tests" >&2
                    exit 1
                    ;;
                  taskhost)
                    echo 'error MSB4216: Could not run the "ComputeManagedAssemblies" task because MSBuild could not create or connect to a task host with runtime "NET" and architecture "x64".' >&2
                    exit 1
                    ;;
                  noso)
                    mkdir -p "$publish_dir"
                    echo "  Meltype.Mac.Native -> $publish_dir"
                    exit 0
                    ;;
                  real)
                    mkdir -p "$publish_dir"
                    "$MELTYPE_TEST_REAL_CLANG" -shared -fPIC -Wl,-z,max-page-size=16384 \\
                        -Wl,-soname,libMeltypeNative.so -o "$publish_dir/MeltypeNative.so" \\
                        "$MELTYPE_TEST_STUB_SOURCE" || exit 1
                    echo "  Meltype.Mac.Native -> $publish_dir/MeltypeNative.so"
                    exit 0
                    ;;
                esac
                mkdir -p "$publish_dir"
                printf 'fake shared library for tests\\n' > "$publish_dir/MeltypeNative.so"
                echo "src/Meltype.Core/Config/Settings.cs(551,28): warning IL2026: Using JsonSerializer.Deserialize can break functionality when trimming."
                echo "src/Meltype.Core/Config/Settings.cs(551,28): warning IL3050: Using JsonSerializer.Deserialize can break functionality when AOT compiling."
                echo "  Meltype.Mac.Native -> $publish_dir/MeltypeNative.so"
                """
            ),
        )

    def write_lock(self, **overrides: object) -> Path:
        lock: dict = {
            "lock_version": 1,
            "core": {
                "repository": "https://example.invalid/meltype.git",
                "sha": self.core_sha,
                "clean_tree_required": True,
            },
            "toolchain": {
                "dotnet_sdk": DOTNET_VERSION,
                "ndk": NDK_REVISION,
                "ndk_llvm_bin": NDK_LLVM_BIN,
            },
            "target": {
                "rid": "linux-bionic-arm64",
                "android_abi": "arm64-v8a",
                "elf_class": "ELF64",
                "elf_machine": "AArch64",
                "elf_type": "DYN",
                "min_page_align": 16384,
            },
            "publish": {
                "project": "src/Meltype.Mac.Native/Meltype.Mac.Native.csproj",
                "configuration": "Release",
                "properties": [
                    "PublishAot=true",
                    "NativeLib=Shared",
                    "DisableUnsupportedError=true",
                    "PublishAotUsingRuntimePack=true",
                ],
                "nuget_sources": ["https://example.invalid/v3/index.json"],
                "artifact_name": "MeltypeNative.so",
                "installed_name": "libMeltypeNative.so",
            },
            "required_exports": list(REQUIRED_EXPORTS),
            "license_files": ["LICENSE", "THIRD-PARTY-NOTICES.md"],
        }
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(lock.get(key), dict):
                lock[key].update(value)
            else:
                lock[key] = value
        self.lock.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return self.lock

    # --- 実行 -----------------------------------------------------------------

    def run_script(
        self,
        *extra: str,
        core_dir: Path | None = None,
        dotnet: Path | None = None,
        ndk_dir: Path | None = None,
        output_dir: Path | None = None,
        lock_file: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        command = [
            sys.executable,
            str(SCRIPT),
            "--core-dir",
            str(core_dir or self.core),
            "--dotnet",
            str(dotnet or self.dotnet),
            "--ndk-dir",
            str(ndk_dir or self.ndk),
            "--output-dir",
            str(output_dir or self.output),
            "--lock-file",
            str(lock_file or self.lock),
            *extra,
        ]
        return subprocess.run(command, capture_output=True, text=True, env={**os.environ, **(env or {})})

    def read_manifest(self, output_dir: Path | None = None) -> dict:
        path = (output_dir or self.output) / "manifest.json"
        self.assertTrue(path.is_file(), f"manifest.json がありません: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def output_files(self, output_dir: Path | None = None) -> set[str]:
        root = output_dir or self.output
        return {str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()}


class SuccessTest(BuildCoreTestCase):
    """成功時に成果物と manifest を残すこと。"""

    def test_relative_paths_are_resolved_before_changing_directory(self) -> None:
        result = self.run_script(core_dir=Path(os.path.relpath(self.core)),
                                 ndk_dir=Path(os.path.relpath(self.ndk)),
                                 output_dir=Path(os.path.relpath(self.output)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_manifest()["verification"]["result"], "ok")

    def test_success_writes_artifacts_and_manifest(self) -> None:
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertEqual(
            self.output_files(),
            {
                "LICENSE",
                "THIRD-PARTY-NOTICES.md",
                "README.md",
                "lib/arm64-v8a/libMeltypeNative.so",
                "logs/build.log",
                "logs/publish.log",
                "manifest.json",
            },
        )
        manifest = self.read_manifest()
        self.assertEqual(manifest["core"]["sha"], self.core_sha)
        self.assertEqual(manifest["core"]["repository"], "https://example.invalid/meltype.git")
        self.assertEqual(manifest["target"]["rid"], "linux-bionic-arm64")
        self.assertEqual(manifest["target"]["android_abi"], "arm64-v8a")
        self.assertEqual(manifest["toolchain"]["dotnet"]["version"], DOTNET_VERSION)
        self.assertEqual(manifest["toolchain"]["ndk"]["revision"], NDK_REVISION)
        self.assertEqual(manifest["environment"]["DOTNET_CLI_TELEMETRY_OPTOUT"], "1")
        self.assertEqual(manifest["environment"]["InvariantGlobalization"], "false")
        self.assertEqual(manifest["verification"]["result"], "ok")
        self.assertEqual(manifest["warnings"], {"IL2026": 1, "IL3050": 1})
        self.assertTrue(manifest["not_verified"])

        # 実行したコマンドが固定した publish コマンドと一致する。
        command = manifest["command"]
        self.assertEqual(command[1:3], ["publish", "src/Meltype.Mac.Native/Meltype.Mac.Native.csproj"])
        self.assertEqual(command[command.index("-r") + 1], "linux-bionic-arm64")
        for property_value in (
            "PublishAot=true",
            "NativeLib=Shared",
            "DisableUnsupportedError=true",
            "PublishAotUsingRuntimePack=true",
        ):
            self.assertIn(f"-p:{property_value}", command)
        self.assertEqual(command[command.index("--source") + 1], "https://example.invalid/v3/index.json")

        artifact = self.output / manifest["artifact"]["path"]
        self.assertEqual(manifest["artifact"]["name"], "libMeltypeNative.so")
        self.assertEqual(manifest["artifact"]["sha256"], BUILD_CORE.sha256_file(artifact))
        self.assertEqual(manifest["artifact"]["size_bytes"], artifact.stat().st_size)
        self.assertEqual(sorted(manifest["elf"]["exports"]), sorted(REQUIRED_EXPORTS))
        self.assertGreaterEqual(manifest["elf"]["min_load_alignment"], 16384)
        self.assertEqual(manifest["elf"]["soname"], "libMeltypeNative.so")
        self.assertEqual(manifest["elf"]["needed"], ["libdl.so", "libc.so"])

        self.assertEqual(
            (self.output / "LICENSE").read_text(encoding="utf-8"),
            (self.core / "LICENSE").read_text(encoding="utf-8"),
        )
        self.assertIn("未確認", (self.output / "README.md").read_text(encoding="utf-8"))
        self.assertIn("IL2026", (self.output / "logs" / "publish.log").read_text(encoding="utf-8"))
        self.assertIn("readelf", (self.output / "logs" / "build.log").read_text(encoding="utf-8"))
        self.assertFalse((self.output / "staging").exists(), "成功後は staging を残さない")

        # 元 core へ build 出力を残さない。
        self.assertEqual(self.git("status", "--porcelain").stdout.strip(), "")
        self.assertFalse((self.core / "src" / "Meltype.Mac.Native" / "bin").exists())

    def test_keep_staging_keeps_core_copy(self) -> None:
        result = self.run_script("--keep-staging")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.output / "staging" / "core" / "src" / "Meltype.Mac.Native").is_dir())

    def test_versioned_exports_are_accepted(self) -> None:
        """共有ライブラリの export に版 (meltype_init@@V1.0) が付いていても成功する。"""
        result = self.run_script(env={"MELTYPE_TEST_ELF_SYMBOLS": "versioned"})
        self.assertEqual(result.returncode, 0, result.stderr)
        exports = self.read_manifest()["elf"]["exports"]
        self.assertEqual(exports["meltype_init"]["name"], "meltype_init@@V1.0")
        self.assertEqual(sorted(exports), sorted(REQUIRED_EXPORTS))

    def test_nuget_source_override_is_used_and_recorded(self) -> None:
        result = self.run_script("--nuget-source", "/tmp/local-feed")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = self.read_manifest()
        self.assertEqual(manifest["environment"]["nuget_sources"], ["/tmp/local-feed"])
        self.assertEqual(manifest["command"][manifest["command"].index("--source") + 1], "/tmp/local-feed")


class InputValidationTest(BuildCoreTestCase):
    """入力検証で止まること (build へ進まない)。"""

    def test_refuses_existing_output_dir(self) -> None:
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("既にあります", result.stderr)
        self.assertEqual(self.output_files(), {"keep.txt"})

    def test_refuses_output_dir_inside_core(self) -> None:
        result = self.run_script(output_dir=self.core / "out")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("core の中", result.stderr)
        self.assertFalse((self.core / "out").exists())

    def test_refuses_core_sha_mismatch(self) -> None:
        self.write_lock(core={"sha": "0" * 40})
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("core SHA が固定値と違います", result.stderr)
        self.assertFalse(self.output.exists())

    def test_refuses_dirty_core_tree(self) -> None:
        (self.core / "dictionaries" / "words.txt").write_text("dirty\n", encoding="utf-8")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clean ではありません", result.stderr)
        self.assertFalse(self.output.exists())

    def test_refuses_missing_core_dir(self) -> None:
        result = self.run_script(core_dir=self.tmp / "no-such-core")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ディレクトリではありません", result.stderr)
        self.assertFalse(self.output.exists())

    def test_refuses_core_dir_without_git(self) -> None:
        plain = self.tmp / "plain"
        plain.mkdir()
        result = self.run_script(core_dir=plain)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("git revision を読めません", result.stderr)

    def test_refuses_dotnet_version_mismatch(self) -> None:
        self.write_lock(toolchain={"dotnet_sdk": "9.9.999"})
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SDK 版が固定値と違います", result.stderr)
        self.assertFalse(self.output.exists())

    def test_refuses_missing_dotnet(self) -> None:
        result = self.run_script(dotnet=self.tmp / "no-dotnet")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("見つかりません", result.stderr)

    def test_refuses_ndk_revision_mismatch(self) -> None:
        self.write_lock(toolchain={"ndk": "27.0.00000000"})
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NDK 版が固定値と違います", result.stderr)
        self.assertFalse(self.output.exists())

    def test_refuses_missing_ndk_llvm_tools(self) -> None:
        (self.ndk / NDK_LLVM_BIN / "llvm-readelf").unlink()
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("llvm-readelf がありません", result.stderr)
        self.assertFalse(self.output.exists())

    def test_refuses_invariant_globalization_true(self) -> None:
        self.make_core(invariant_globalization="true")
        self.core_sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.write_lock()
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("InvariantGlobalization=false が維持されていません", result.stderr)
        self.assertFalse(self.output.exists())


class FailureArtifactsTest(BuildCoreTestCase):
    """失敗した実行が成果物・成功 manifest を残さないこと。"""

    def assert_failed_without_artifacts(self, result: subprocess.CompletedProcess) -> None:
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists(), "失敗時は output-dir を残さない")

    def test_publish_failure_leaves_no_artifacts(self) -> None:
        result = self.run_script(env={"MELTYPE_TEST_DOTNET_MODE": "fail"})
        self.assert_failed_without_artifacts(result)
        self.assertIn("dotnet publish が失敗しました", result.stderr)
        self.assertIn("NETSDK1045", result.stderr)

    def test_task_host_failure_mentions_sandbox_handoff(self) -> None:
        result = self.run_script(env={"MELTYPE_TEST_DOTNET_MODE": "taskhost"})
        self.assert_failed_without_artifacts(result)
        self.assertIn("AF_UNIX", result.stderr)
        self.assertIn("controller", result.stderr)

    def test_missing_shared_library_leaves_no_artifacts(self) -> None:
        result = self.run_script(env={"MELTYPE_TEST_DOTNET_MODE": "noso"})
        self.assert_failed_without_artifacts(result)
        self.assertIn("publish 出力に .so がありません", result.stderr)

    def test_missing_export_leaves_no_artifacts(self) -> None:
        result = self.run_script(env={"MELTYPE_TEST_ELF_SYMBOLS": "missing-export"})
        self.assert_failed_without_artifacts(result)
        self.assertIn("export:meltype_free", result.stderr)
        self.assertIn("ELF 検証に失敗しました", result.stderr)

    def test_small_page_alignment_leaves_no_artifacts(self) -> None:
        result = self.run_script(env={"MELTYPE_TEST_ELF_ALIGN": "align-4k"})
        self.assert_failed_without_artifacts(result)
        self.assertIn("load_page_align", result.stderr)


class ElfParsingTest(unittest.TestCase):
    """NDK r28 の llvm-readelf 出力 (tests/fixtures) を読めること。"""

    def test_parse_elf_header(self) -> None:
        header = BUILD_CORE.parse_elf_header(read_fixture("readelf-ok-header.txt"))
        self.assertEqual(header["class"], "ELF64")
        self.assertEqual(header["machine"], "AArch64")
        self.assertTrue(header["type"].startswith("DYN"))
        self.assertIn("little endian", header["data"])

    def test_parse_load_alignments(self) -> None:
        self.assertEqual(
            BUILD_CORE.parse_load_alignments(read_fixture("readelf-ok-program-headers.txt")),
            [16384, 16384, 16384],
        )
        self.assertEqual(
            BUILD_CORE.parse_load_alignments(read_fixture("readelf-align-4k-program-headers.txt")),
            [4096, 4096, 4096],
        )

    def test_parse_load_alignments_rejects_broken_line(self) -> None:
        with self.assertRaises(BUILD_CORE.BuildError):
            BUILD_CORE.parse_load_alignments("  LOAD 0x0 0x0\n")

    def test_parse_dynamic(self) -> None:
        dynamic = BUILD_CORE.parse_dynamic(read_fixture("readelf-ok-dynamic.txt"))
        self.assertEqual(dynamic["soname"], "libMeltypeNative.so")
        self.assertEqual(dynamic["needed"], ["libdl.so", "libc.so"])

    def test_parse_dyn_symbols(self) -> None:
        symbols = BUILD_CORE.parse_dyn_symbols(read_fixture("readelf-ok-dyn-syms.txt"))
        for name in REQUIRED_EXPORTS:
            self.assertIn(name, symbols)
            self.assertEqual(symbols[name]["bind"], "GLOBAL")
            self.assertNotEqual(symbols[name]["section_index"], "UND")
        # 版 (name@@V1.0) を除いた名前で引ける。
        self.assertEqual(symbols["__cxa_finalize"]["section_index"], "UND")

    def test_parse_dyn_symbols_finds_missing_export(self) -> None:
        symbols = BUILD_CORE.parse_dyn_symbols(read_fixture("readelf-missing-export-dyn-syms.txt"))
        self.assertIn("meltype_init", symbols)
        self.assertNotIn("meltype_free", symbols)

    def test_parse_dyn_symbols_strips_version_suffix(self) -> None:
        symbols = BUILD_CORE.parse_dyn_symbols(read_fixture("readelf-versioned-dyn-syms.txt"))
        for name in REQUIRED_EXPORTS:
            self.assertIn(name, symbols)
            self.assertEqual(symbols[name]["bind"], "GLOBAL")
            self.assertNotEqual(symbols[name]["section_index"], "UND")
        self.assertEqual(symbols["meltype_init"]["name"], "meltype_init@@V1.0")


@unittest.skipUnless(
    REAL_TARGET_CLANG.is_file() and (REAL_NDK_LLVM_BIN / "llvm-readelf").is_file(),
    f"NDK {NDK_REVISION} の LLVM ツールがないため skip",
)
class RealReadelfIntegrationTest(BuildCoreTestCase):
    """本物の clang で作った AArch64 共有ライブラリを本物の llvm-readelf で検証できること。"""

    def setUp(self) -> None:
        super().setUp()
        self.use_real_ndk_tools()
        self.stub_source = self.tmp / "stub.c"
        self.stub_source.write_text(STUB_SOURCE, encoding="utf-8")

    def test_verifies_real_aarch64_library(self) -> None:
        result = self.run_script(
            env={
                "MELTYPE_TEST_DOTNET_MODE": "real",
                "MELTYPE_TEST_REAL_CLANG": str(REAL_TARGET_CLANG),
                "MELTYPE_TEST_STUB_SOURCE": str(self.stub_source),
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = self.read_manifest()
        self.assertEqual(manifest["elf"]["class"], "ELF64")
        self.assertEqual(manifest["elf"]["machine"], "AArch64")
        self.assertTrue(manifest["elf"]["type"].startswith("DYN"))
        self.assertGreaterEqual(manifest["elf"]["min_load_alignment"], 16384)
        self.assertEqual(sorted(manifest["elf"]["exports"]), sorted(REQUIRED_EXPORTS))
        self.assertEqual(manifest["verification"]["result"], "ok")


if __name__ == "__main__":
    unittest.main()
