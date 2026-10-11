#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Yukishiro
"""固定 core から Android arm64 の NativeAOT 共有ライブラリを作るビルド入口。

scripts/deps.lock.json の固定値 (core SHA / .NET SDK / NDK / RID / ABI / export 一覧) を正本とし、
--core-dir, --dotnet, --ndk-dir, --output-dir の明示入力だけを使う。依存の clone・SDK の導入・
端末操作はしない。

    python3 scripts/build-core.py \
        --core-dir /path/to/meltype \
        --dotnet /path/to/dotnet \
        --ndk-dir /path/to/Android/Sdk/ndk/28.0.13004108 \
        --output-dir /path/to/out/meltype-native-arm64

成功すると --output-dir に lib/arm64-v8a/libMeltypeNative.so, manifest.json, LICENSE,
THIRD-PARTY-NOTICES.md, README.md, logs/ を残す。失敗したら --output-dir を残さず非 0 で終わる
(成功 manifest を残さない)。APK と Fcitx5 addon の収録はこの script の範囲外。
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Iterable, Sequence

EXIT_OK = 0
EXIT_FAILED = 1

DEFAULT_LOCK_FILE = Path(__file__).resolve().with_name("deps.lock.json")

PUBLISH_LOG = Path("logs") / "publish.log"
BUILD_LOG = Path("logs") / "build.log"
STAGING_DIR = "staging"
CORE_TAR_NAME = "core.tar"

OUTPUT_README = "README.md"
MANIFEST_NAME = "manifest.json"

# 実機・後続工程で確認する項目。この script の出力だけでは保証しない。
LIMITATIONS = (
    "実機 Android 上での ICU/globalization の解決は未確認",
    "設定・学習の JSON 保存は未確認",
    "APK/addon への収録と端末での動作は未確認",
)

# MSBuild のタスクホストは Unix domain socket (named pipe) を使う。AF_UNIX を拒否する sandbox では
# ILLink の task host を作れず、NativeAOT の publish がここで失敗する。
TASK_HOST_MARKERS = ("MSB4216", "could not create or connect to a task host")

TRANSCRIPT: list[str] = []


class BuildError(Exception):
    """この script が想定した失敗。利用者へそのまま見せる。"""


def trace(message: str) -> None:
    """build ログへ残すだけ (標準出力へは出さない)。"""
    TRANSCRIPT.append(message)


def log(message: str = "") -> None:
    """標準出力と build ログの両方へ出す。"""
    trace(message)
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def run_capture(command: Sequence[object], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """外部コマンドを実行し、標準出力と標準エラーをまとめて受け取る。"""
    text_command = [str(part) for part in command]
    log(f"  $ {shlex.join(text_command)}")
    try:
        result = subprocess.run(
            text_command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
    except OSError as error:
        raise BuildError(f"コマンドを実行できません: {text_command[0]}: {error}") from error
    output = (result.stdout or "").rstrip()
    if output:
        trace(output)
    return result


def resolve_executable(value: str, what: str) -> Path:
    """実行ファイルのパスを決める。bare name は PATH から探す。"""
    if os.sep in value or (os.altsep is not None and os.altsep in value):
        path = Path(value).expanduser()
        if not path.is_file():
            raise BuildError(f"{what} が見つかりません: {value}")
        if not os.access(path, os.X_OK):
            raise BuildError(f"{what} を実行できません (実行権限がありません): {value}")
        return path.resolve()
    found = shutil.which(value)
    if found is None:
        raise BuildError(f"{what} が PATH にありません: {value}")
    return Path(found).resolve()


def read_properties(path: Path) -> dict[str, str]:
    """`key = value` 形式 (Android SDK/NDK の source.properties) を読む。"""
    properties: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        properties[key.strip()] = value.strip()
    return properties


def load_lock(lock_file: Path) -> dict:
    if not lock_file.is_file():
        raise BuildError(f"lock file がありません: {lock_file}")
    try:
        lock = json.loads(lock_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BuildError(f"lock file を JSON として読めません: {lock_file}: {error}") from error
    if lock.get("lock_version") != 1:
        raise BuildError(f"lock file の lock_version が 1 ではありません: {lock_file}")
    for key in ("core", "toolchain", "target", "publish", "required_exports", "license_files"):
        if key not in lock:
            raise BuildError(f"lock file に {key} がありません: {lock_file}")
    return lock


def check_core_tree(core_dir: Path, lock: dict, env: dict[str, str]) -> str:
    """core の SHA が固定値で、作業ツリーが clean であることを確認する。"""
    if not core_dir.is_dir():
        raise BuildError(f"--core-dir がディレクトリではありません: {core_dir}")
    expected_sha = str(lock["core"]["sha"])
    revision = run_capture(["git", "-C", core_dir, "rev-parse", "HEAD"], env=env)
    if revision.returncode != 0:
        raise BuildError(f"core の git revision を読めません: {core_dir}\n{revision.stdout.strip()}")
    actual_sha = revision.stdout.strip().splitlines()[-1].strip()
    if actual_sha != expected_sha:
        raise BuildError(f"core SHA が固定値と違います: 期待 {expected_sha} / 実際 {actual_sha}")
    log(f"  core SHA: {actual_sha} (固定値と一致)")
    if lock["core"].get("clean_tree_required", True) is False:
        return actual_sha
    status = run_capture(["git", "-C", core_dir, "status", "--porcelain"], env=env)
    if status.returncode != 0:
        raise BuildError(f"core の git status を読めません: {core_dir}\n{status.stdout.strip()}")
    if status.stdout.strip():
        raise BuildError("core の作業ツリーが clean ではありません:\n" + status.stdout.strip())
    log("  作業ツリー: clean")
    return actual_sha


def check_dotnet(dotnet_arg: str, lock: dict, env: dict[str, str]) -> tuple[Path, str]:
    dotnet = resolve_executable(dotnet_arg, "--dotnet")
    result = run_capture([dotnet, "--version"], env=env)
    if result.returncode != 0:
        raise BuildError(
            f"dotnet --version が失敗しました (exit {result.returncode}):\n{result.stdout.strip()}"
        )
    versions = [
        line.strip()
        for line in result.stdout.splitlines()
        if re.fullmatch(r"\d+\.\d+\.\d+[A-Za-z0-9.+-]*", line.strip())
    ]
    version = versions[-1] if versions else ""
    expected = str(lock["toolchain"]["dotnet_sdk"])
    if version != expected:
        raise BuildError(f".NET SDK 版が固定値と違います: 期待 {expected} / 実際 {version or '不明'}")
    return dotnet, version


def check_ndk(ndk_dir: Path, lock: dict, env: dict[str, str]) -> dict:
    """NDK の版と LLVM ツールの実在を確認し、PATH へ足す bin と各ツールの版を返す。"""
    if not ndk_dir.is_dir():
        raise BuildError(f"--ndk-dir がディレクトリではありません: {ndk_dir}")
    expected = str(lock["toolchain"]["ndk"])
    properties_file = ndk_dir / "source.properties"
    if not properties_file.is_file():
        raise BuildError(f"NDK の source.properties がありません: {properties_file}")
    revision = read_properties(properties_file).get("Pkg.Revision", "")
    if revision != expected:
        raise BuildError(f"NDK 版が固定値と違います: 期待 {expected} / 実際 {revision or '不明'}")
    llvm_bin = ndk_dir / str(lock["toolchain"]["ndk_llvm_bin"])
    if not llvm_bin.is_dir():
        raise BuildError(f"NDK の LLVM bin がありません: {llvm_bin}")
    tools: dict[str, Path] = {}
    for name in ("clang", "llvm-readelf"):
        path = llvm_bin / name
        if not path.is_file() or not os.access(path, os.X_OK):
            raise BuildError(f"NDK の {name} がありません: {path}")
        tools[name] = path
    clang_version = first_version_line(run_capture([tools["clang"], "--version"], env=env).stdout)
    readelf_version = first_version_line(run_capture([tools["llvm-readelf"], "--version"], env=env).stdout)
    return {
        "revision": revision,
        "llvm_bin": llvm_bin,
        "clang": tools["clang"],
        "llvm_readelf": tools["llvm-readelf"],
        "clang_version": clang_version,
        "llvm_readelf_version": readelf_version,
    }


def first_version_line(output: str) -> str:
    for line in output.splitlines():
        if line.strip():
            return line.strip()
    return ""


def check_output_dir(output_dir: Path) -> None:
    if output_dir.exists() or output_dir.is_symlink():
        raise BuildError(f"--output-dir が既にあります (上書きしません): {output_dir}")


def check_output_location(output_dir: Path, core_dir: Path) -> None:
    """core の中へ build 出力を置かない (元 core に出力を残さない)。"""
    core_root = core_dir.resolve()
    output_root = output_dir.resolve()
    if output_root == core_root or core_root in output_root.parents:
        raise BuildError(f"--output-dir を core の中に置けません: {output_dir}")
    if output_root in core_root.parents:
        raise BuildError(f"--core-dir を --output-dir の中に置けません: {core_dir}")


def check_invariant_globalization(staged_core: Path, lock: dict) -> str:
    """InvariantGlobalization=false (ICU/globalization を使う) が維持されていることを確認する。"""
    project = staged_core / str(lock["publish"]["project"])
    if not project.is_file():
        raise BuildError(f"core に publish 対象の project がありません: {project}")
    try:
        root = ElementTree.parse(project).getroot()
    except ElementTree.ParseError as error:
        raise BuildError(f"project を XML として読めません: {project}: {error}") from error
    value: str | None = None
    for group in root.iter("PropertyGroup"):
        node = group.find("InvariantGlobalization")
        if node is not None:
            value = (node.text or "").strip()
    if (value or "").lower() != "false":
        raise BuildError(
            "InvariantGlobalization=false が維持されていません "
            f"(実際: {value if value is not None else '未設定'}): {project}"
        )
    return value


def configure_android_soname(staged_core: Path, lock: dict) -> None:
    """Give the staged provider the SONAME required by Bionic symbol version lookup."""
    project = staged_core / str(lock["publish"]["project"])
    tree = ElementTree.parse(project)
    group = ElementTree.SubElement(tree.getroot(), "ItemGroup")
    ElementTree.SubElement(group, "LinkerArg", {"Include": "-Wl,-soname," + str(lock["publish"]["installed_name"])})
    tree.write(project, encoding="utf-8", xml_declaration=True)


def extract_core(staged_core: Path, staging: Path, core_dir: Path, lock: dict, env: dict[str, str]) -> None:
    """固定 tree の追跡ファイルだけを staging へ取り出す (元 core へは何も書かない)。"""
    staging.mkdir(parents=True, exist_ok=True)
    archive = staging / CORE_TAR_NAME
    result = run_capture(
        ["git", "-C", core_dir, "archive", "--format=tar", "-o", archive, str(lock["core"]["sha"])],
        env=env,
    )
    if result.returncode != 0 or not archive.is_file():
        raise BuildError(f"core の archive を作れません (exit {result.returncode}):\n{result.stdout.strip()}")
    staged_core.mkdir(parents=True)
    try:
        with tarfile.open(archive, mode="r") as tar:
            try:
                tar.extractall(staged_core, filter="data")
            except TypeError:
                # Python 3.11.4 より前は filter 引数がない。入力は固定 SHA の git archive のみ。
                tar.extractall(staged_core)
    except tarfile.TarError as error:
        raise BuildError(f"core の archive を展開できません: {error}") from error
    finally:
        archive.unlink(missing_ok=True)
    if not any(staged_core.iterdir()):
        raise BuildError(f"core の archive が空です: {core_dir}")


def publish_environment(ndk: dict, base_env: dict[str, str]) -> dict[str, str]:
    """NDK LLVM bin を PATH の先頭に置き、telemetry を切った環境を作る。"""
    env = dict(base_env)
    env["PATH"] = str(ndk["llvm_bin"]) + os.pathsep + env.get("PATH", "")
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    return env


def publish_command(dotnet: Path, lock: dict, sources: Iterable[str]) -> list[str]:
    publish = lock["publish"]
    command = [
        str(dotnet),
        "publish",
        str(publish["project"]),
        "-c",
        str(publish["configuration"]),
        "-r",
        str(lock["target"]["rid"]),
    ]
    command.extend(f"-p:{property_value}" for property_value in publish["properties"])
    for source in sources:
        command.extend(["--source", str(source)])
    return command


def run_publish(command: Sequence[str], cwd: Path, env: dict[str, str], log_path: Path) -> None:
    log(f"dotnet publish を実行します (生ログ: {log_path.parent.name}/{log_path.name})")
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"$ {shlex.join(command)}\n\n")
        handle.flush()
        try:
            process = subprocess.Popen(
                list(command),
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except OSError as error:
            raise BuildError(f"dotnet を実行できません: {command[0]}: {error}") from error
        assert process.stdout is not None
        for line in process.stdout:
            handle.write(line)
            print(line, end="", flush=True)
        process.stdout.close()
        returncode = process.wait()
    if returncode != 0:
        hint = ""
        if any(marker in log_path.read_text(encoding="utf-8", errors="replace") for marker in TASK_HOST_MARKERS):
            hint = (
                "\nAF_UNIX (Unix domain socket) を拒否する環境では MSBuild のタスクホストを作れず、"
                "NativeAOT の publish は失敗します。socket を許可する環境 (controller) で再実行してください。"
            )
        raise BuildError(f"dotnet publish が失敗しました (exit {returncode}){hint}")


def count_warnings(log_path: Path) -> dict[str, int]:
    """publish ログの警告コードを数える (JSON AOT 警告の記録)。"""
    counts: dict[str, int] = {}
    text = log_path.read_text(encoding="utf-8", errors="replace")
    for code in re.findall(r"\bwarning ([A-Z]{2}\d{4})\b", text):
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def find_published_library(staged_core: Path, lock: dict) -> Path:
    """publish された共有ライブラリを探す。名前と個数を固定値どおりに要求する。"""
    name = str(lock["publish"]["artifact_name"])
    found = sorted(path for path in staged_core.glob("**/publish/*.so") if path.is_file())
    if not found:
        raise BuildError(f"publish 出力に .so がありません: {staged_core} 配下の **/publish/*.so")
    unexpected = [path for path in found if path.name != name]
    if unexpected:
        raise BuildError(
            f"publish 出力の .so が想定と違います (期待 {name}): "
            + ", ".join(str(path) for path in unexpected)
        )
    if len(found) != 1:
        raise BuildError(f"publish 出力の .so が 1 個ではありません: " + ", ".join(str(p) for p in found))
    return found[0]


def readelf_sections(readelf: Path, library: Path, env: dict[str, str]) -> dict[str, str]:
    """llvm-readelf の出力を種類ごとに集める。"""
    sections: dict[str, str] = {}
    for key, option in (
        ("header", "-h"),
        ("program_headers", "-l"),
        ("dynamic", "-d"),
        ("dyn_symbols", "--dyn-syms"),
    ):
        result = run_capture([readelf, option, library], env=env)
        if result.returncode != 0:
            raise BuildError(
                f"llvm-readelf {option} が失敗しました (exit {result.returncode}):\n{result.stdout.strip()}"
            )
        sections[key] = result.stdout
    return sections


def parse_elf_header(text: str) -> dict[str, str]:
    wanted = {"Class": "class", "Data": "data", "Type": "type", "Machine": "machine", "OS/ABI": "os_abi"}
    header: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s+([A-Za-z0-9'/. _-]+):\s+(.*?)\s*$", line)
        if match is None:
            continue
        key = match.group(1).strip()
        if key in wanted:
            header[wanted[key]] = match.group(2).strip()
    return header


def parse_load_alignments(text: str) -> list[int]:
    """LOAD セグメントの p_align を並び順に返す。"""
    alignments: list[int] = []
    for line in text.splitlines():
        match = re.match(r"^\s*LOAD\s+(\S.*?)\s*$", line)
        if match is None:
            continue
        columns = match.group(1).split()
        if len(columns) < 4:
            raise BuildError(f"LOAD 行を読めません: {line.strip()}")
        raw_align = columns[-1]
        try:
            alignments.append(int(raw_align, 16))
        except ValueError as error:
            raise BuildError(f"LOAD の p_align を数値として読めません: {line.strip()}") from error
    return alignments


def parse_dynamic(text: str) -> dict[str, object]:
    needed = re.findall(r"\(NEEDED\)\s+Shared library: \[(.*?)\]", text)
    soname = re.findall(r"\(SONAME\)\s+Library soname: \[(.*?)\]", text)
    return {"needed": needed, "soname": soname[-1] if soname else None}


def parse_dyn_symbols(text: str) -> dict[str, dict[str, str]]:
    """dynsym のシンボルを、版 (meltype_init@@V1.0 の @ 以降) を除いた名前で引けるようにする。"""
    symbols: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(.*?)\s*$"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if match is None:
            continue
        value, size, symbol_type, bind, visibility, section_index, raw_name = match.groups()
        if not raw_name or not section_index:
            continue
        base_name = raw_name.split("@", 1)[0]
        if not base_name:
            continue
        entry = {
            "name": raw_name,
            "value": value,
            "size": size,
            "type": symbol_type,
            "bind": bind,
            "visibility": visibility,
            "section_index": section_index,
        }
        previous = symbols.get(base_name)
        if previous is None or symbol_priority(entry) > symbol_priority(previous):
            symbols[base_name] = entry
    return symbols


def symbol_priority(symbol: dict[str, str]) -> tuple[int, int]:
    """定義済みで既定版 (@@) のシンボルを優先する。"""
    return (0 if symbol["section_index"] == "UND" else 1, 1 if "@@" in symbol["name"] else 0)


def verify_elf(library: Path, lock: dict, ndk: dict, env: dict[str, str]) -> dict:
    """ABI・必須 export・16KB page alignment を llvm-readelf で検証する。"""
    readelf = ndk["llvm_readelf"]
    sections = readelf_sections(readelf, library, env)
    header = parse_elf_header(sections["header"])
    symbols = parse_dyn_symbols(sections["dyn_symbols"])
    dynamic = parse_dynamic(sections["dynamic"])
    alignments = parse_load_alignments(sections["program_headers"])
    target = lock["target"]

    failures: list[str] = []
    checks: list[dict[str, object]] = []

    def check(name: str, expected: object, actual: object, ok: bool) -> None:
        checks.append({"name": name, "expected": expected, "actual": actual, "ok": ok})
        if not ok:
            failures.append(f"{name}: 期待 {expected!r} / 実際 {actual!r}")

    check("elf_class", target["elf_class"], header.get("class"), header.get("class") == target["elf_class"])
    check("elf_machine", target["elf_machine"], header.get("machine"), header.get("machine") == target["elf_machine"])
    soname = str(lock["publish"]["installed_name"])
    check("elf_soname", soname, dynamic["soname"], dynamic["soname"] == soname)
    actual_type = (header.get("type") or "").split()[0] if header.get("type") else ""
    check("elf_type", target["elf_type"], header.get("type"), actual_type == target["elf_type"])
    check(
        "elf_data",
        "little endian",
        header.get("data"),
        "little endian" in (header.get("data") or ""),
    )

    minimum_align = int(target["min_page_align"])
    check("load_segments", "1 個以上", len(alignments), len(alignments) >= 1)
    check(
        "load_page_align",
        f">= {minimum_align}",
        alignments,
        bool(alignments) and all(align >= minimum_align for align in alignments),
    )

    exports: dict[str, dict[str, str]] = {}
    for name in lock["required_exports"]:
        symbol = symbols.get(name)
        defined = symbol is not None and symbol["section_index"] != "UND" and symbol["bind"] in ("GLOBAL", "WEAK")
        check(
            f"export:{name}",
            "定義済み GLOBAL シンボル",
            "なし" if symbol is None else f"{symbol['bind']}/{symbol['section_index']}",
            defined,
        )
        if defined:
            exports[name] = symbol

    if failures:
        raise BuildError("ELF 検証に失敗しました:\n  - " + "\n  - ".join(failures))

    return {
        "class": header.get("class"),
        "data": header.get("data"),
        "type": header.get("type"),
        "machine": header.get("machine"),
        "os_abi": header.get("os_abi"),
        "soname": dynamic["soname"],
        "needed": dynamic["needed"],
        "load_alignments": alignments,
        "min_load_alignment": min(alignments),
        "exports": exports,
        "checks": checks,
    }


def render_output_readme(lock: dict, core_sha: str) -> str:
    abi = lock["target"]["android_abi"]
    limitations = "\n".join(f"- {item}" for item in LIMITATIONS)
    return f"""# Meltype Android NativeAOT 成果物 ({abi})

`scripts/build-core.py` が固定 core (SHA `{core_sha}`) から生成した NativeAOT 共有ライブラリです。
APK と Fcitx5 addon は含みません。

- `lib/{abi}/libMeltypeNative.so`: C ABI (`meltype_*`) を export する {abi} 共有ライブラリ
- `manifest.json`: core SHA、実使用ツール版、実行コマンド、SHA256、ELF/依存情報、検証結果
- `LICENSE` / `THIRD-PARTY-NOTICES.md`: core の原本
- `logs/publish.log`: `dotnet publish` の生ログ (JSON の AOT 警告 IL2026/IL3050 を含む)
- `logs/build.log`: 入力検証と ELF 検証の記録

この成果物だけでは次を保証しません。

{limitations}
"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def assemble(
    output_dir: Path, staged_core: Path, published: Path, lock: dict, core_sha: str
) -> dict:
    """成果物を output-dir へ集め、manifest 用の情報を返す。"""
    abi = str(lock["target"]["android_abi"])
    library_dir = output_dir / "lib" / abi
    library_dir.mkdir(parents=True)
    installed = library_dir / str(lock["publish"]["installed_name"])
    shutil.copy2(published, installed)

    source_sha256 = sha256_file(published)
    copied_sha256 = sha256_file(installed)
    if source_sha256 != copied_sha256:
        raise BuildError(f"成果物の SHA256 が一致しません: {published} / {installed}")

    licenses: list[dict[str, str]] = []
    for name in lock["license_files"]:
        source = staged_core / str(name)
        if not source.is_file():
            raise BuildError(f"core に {name} がありません: {source}")
        destination = output_dir / str(name)
        shutil.copy2(source, destination)
        licenses.append({"path": str(name), "sha256": sha256_file(destination)})

    write_text(output_dir / OUTPUT_README, render_output_readme(lock, core_sha))

    return {
        "artifact": {
            "path": f"lib/{abi}/{installed.name}",
            "name": installed.name,
            "source_name": published.name,
            "size_bytes": installed.stat().st_size,
            "sha256": copied_sha256,
        },
        "licenses": licenses,
    }


def write_manifest(output_dir: Path, manifest: dict) -> Path:
    """成功 manifest を最後に書く (途中で失敗したら manifest は存在しない)。"""
    path = output_dir / MANIFEST_NAME
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return path


def build(args: argparse.Namespace) -> None:
    lock = load_lock(args.lock_file)
    core_dir = Path(args.core_dir).expanduser().absolute()
    ndk_dir = Path(args.ndk_dir).expanduser().absolute()
    output_dir = Path(args.output_dir).expanduser().absolute()
    sources = list(args.nuget_source) if args.nuget_source else list(lock["publish"]["nuget_sources"])

    env = dict(os.environ)

    log("== 1/5 入力の検証")
    check_output_dir(output_dir)
    check_output_location(output_dir, core_dir)
    core_sha = check_core_tree(core_dir, lock, env)
    dotnet, dotnet_version = check_dotnet(args.dotnet, lock, env)
    log(f"  dotnet: {dotnet} ({dotnet_version})")
    ndk = check_ndk(ndk_dir, lock, env)
    log(f"  NDK: {ndk_dir} ({ndk['revision']})")
    log(f"  clang: {ndk['clang_version']}")
    log(f"  llvm-readelf: {ndk['llvm_readelf_version']}")
    log(f"  出力先: {output_dir} (既存ではない)")

    output_dir.mkdir(parents=True)
    log_path = output_dir / PUBLISH_LOG
    log_path.parent.mkdir(parents=True)
    try:
        log("== 2/5 隔離 staging へ core をコピー")
        staging = output_dir / STAGING_DIR
        staged_core = staging / "core"
        extract_core(staged_core, staging, core_dir, lock, env)
        log(f"  {staged_core} へ追跡ファイルだけを展開 (元 core へは書かない)")
        invariant = check_invariant_globalization(staged_core, lock)
        configure_android_soname(staged_core, lock)
        log(f"  InvariantGlobalization={invariant} を確認")

        log("== 3/5 NativeAOT publish")
        command = publish_command(dotnet, lock, sources)
        run_publish(command, staged_core, publish_environment(ndk, env), log_path)
        warnings = count_warnings(log_path)
        log(f"  警告: {warnings if warnings else 'なし'} (詳細は logs/publish.log)")

        log("== 4/5 ABI・export・page alignment の検証")
        published = find_published_library(staged_core, lock)
        log(f"  publish 出力: {published.relative_to(staged_core)}")
        elf = verify_elf(published, lock, ndk, env)
        log(f"  {elf['class']} / {elf['machine']} / {elf['type']}、LOAD p_align: {elf['load_alignments']}")
        log(f"  必須 export {len(elf['exports'])} 個を確認")
        log(f"  SONAME: {elf['soname']}、NEEDED: {elf['needed']}")

        log("== 5/5 成果物の配置")
        assembled = assemble(output_dir, staged_core, published, lock, core_sha)
        log(f"  {assembled['artifact']['path']} (sha256 {assembled['artifact']['sha256']})")
        for license_entry in assembled["licenses"]:
            log(f"  {license_entry['path']}")

        after = run_capture(["git", "-C", core_dir, "status", "--porcelain"], env=env)
        if after.returncode != 0 or after.stdout.strip():
            raise BuildError("core の作業ツリーが build 後に clean ではありません:\n" + after.stdout.strip())

        write_text(output_dir / BUILD_LOG, "\n".join(TRANSCRIPT) + "\n")
        manifest = {
            "manifest_version": 1,
            "scope": "Android NativeAOT 共有ライブラリ (APK/addon は対象外)",
            "generated_at": now_iso(),
            "core": {
                "repository": lock["core"]["repository"],
                "sha": core_sha,
                "tree_clean": True,
            },
            "target": {
                "rid": lock["target"]["rid"],
                "android_abi": lock["target"]["android_abi"],
                "page_size_requirement": int(lock["target"]["min_page_align"]),
            },
            "toolchain": {
                "dotnet": {"path": str(dotnet), "version": dotnet_version},
                "ndk": {
                    "path": str(ndk_dir),
                    "revision": ndk["revision"],
                    "llvm_bin": str(ndk["llvm_bin"]),
                },
                "clang": {"path": str(ndk["clang"]), "version": ndk["clang_version"]},
                "llvm_readelf": {
                    "path": str(ndk["llvm_readelf"]),
                    "version": ndk["llvm_readelf_version"],
                },
            },
            "command": command,
            "environment": {
                "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                "PATH_prepended": str(ndk["llvm_bin"]),
                "InvariantGlobalization": "false",
                "SONAME": str(lock["publish"]["installed_name"]),
                "nuget_sources": sources,
                "nuget_packages": env.get("NUGET_PACKAGES", str(Path.home() / ".nuget" / "packages")),
            },
            "artifact": assembled["artifact"],
            "elf": {
                "class": elf["class"],
                "data": elf["data"],
                "type": elf["type"],
                "machine": elf["machine"],
                "os_abi": elf["os_abi"],
                "soname": elf["soname"],
                "needed": elf["needed"],
                "load_alignments": elf["load_alignments"],
                "min_load_alignment": elf["min_load_alignment"],
                "exports": elf["exports"],
            },
            "verification": {
                "checks": elf["checks"],
                "result": "ok",
            },
            "warnings": warnings,
            "licenses": assembled["licenses"],
            "logs": {"build": str(BUILD_LOG), "publish": str(PUBLISH_LOG)},
            "not_verified": list(LIMITATIONS),
        }
        manifest_path = write_manifest(output_dir, manifest)

        if not args.keep_staging:
            shutil.rmtree(staging, ignore_errors=True)

        log("")
        log(f"成功: {manifest_path}")
        log(f"  成果物: {output_dir / assembled['artifact']['path']}")
        log("  APK/addon は含みません。実機 ICU/globalization・JSON 保存・端末動作は未確認です。")
    except BaseException:
        report = output_dir / PUBLISH_LOG
        if report.is_file():
            lines = report.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                print(f"--- {PUBLISH_LOG} の末尾 ---", file=sys.stderr)
                print("\n".join(lines[-200:]), file=sys.stderr)
        # 失敗した出力は残さない (成功 manifest を残さない)。
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="build-core.py",
        description="固定 core から Android arm64 の NativeAOT 共有ライブラリを作る。",
        epilog="終了コード: 0=成功 / 1=失敗 (output-dir を残さない) / 2=引数の誤り",
    )
    parser.add_argument("--core-dir", required=True, help="固定 core の作業ツリー (clean であること)")
    parser.add_argument("--dotnet", required=True, help=".NET SDK の dotnet 実行ファイル")
    parser.add_argument("--ndk-dir", required=True, help="Android NDK (28.0.13004108) のディレクトリ")
    parser.add_argument("--output-dir", required=True, help="成果物の出力先 (既存なら拒否)")
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=DEFAULT_LOCK_FILE,
        help="固定値の JSON (既定: scripts/deps.lock.json)",
    )
    parser.add_argument(
        "--nuget-source",
        action="append",
        metavar="URL_OR_DIR",
        help="NuGet の取得先 (既定: lock file の値。複数指定できる)",
    )
    parser.add_argument("--keep-staging", action="store_true", help="成功後も output-dir/staging を残す")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        build(args)
    except BuildError as error:
        print(f"失敗: {error}", file=sys.stderr)
        return EXIT_FAILED
    except KeyboardInterrupt:
        print("中断しました", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
