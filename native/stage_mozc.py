# SPDX-License-Identifier: GPL-3.0-or-later
"""Copy upstream sources into build directory; never patch the original."""
import hashlib, json, pathlib, shutil, subprocess, sys
source, target, header = map(pathlib.Path, sys.argv[1:])
identity = {"source": str(source.resolve()), "sha": subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip(), "header_sha256": hashlib.sha256(header.read_bytes()).hexdigest()}
if identity["sha"] != "91534fe508673f496c2e35e48e09260b75398671":
    raise SystemExit("Unexpected Mozc revision; update reviewed dependency pin first")
if subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True).strip():
    raise SystemExit("Mozc source must be clean")
marker = target.parent / "mozc-stage-inputs.json"
if target.exists() and (not marker.exists() or json.loads(marker.read_text()) != identity):
    raise SystemExit("Staged input changed or is unverified; use a fresh build directory")
if not target.exists():
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git', 'bazel-*', 'build', '__pycache__'))
marker.write_text(json.dumps(identity, sort_keys=True) + '\n')
destination = target / 'mozc/src/data_manager/oss/mozc_data.inc'
if not destination.exists() or hashlib.sha256(destination.read_bytes()).hexdigest() != identity['header_sha256']:
    if destination.exists(): destination.chmod(0o644)
    shutil.copyfile(header, destination)
p = target / 'cmake/base.cmake'
text = p.read_text()
if 'base/android_util.cc' not in text:
    p.write_text(text + '\nif(ANDROID)\n  list(APPEND MOZC_BASE_SRCS "${MOZC_SRC_DIR}/base/android_util.cc")\nendif()\n')
