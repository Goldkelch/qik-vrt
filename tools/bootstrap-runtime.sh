#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

set -eu

MODE=check
ACCEPT_THIRD_PARTY=0
PROFILE=ietf
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CACHE_DIR=${QIKVRT_TOOLCHAIN_CACHE:-"$ROOT/.qikvrt/toolchains"}
XML2RFC_VERSION=3.34.0
PYTHON_RENDERER_VERSION=3.12.13
XML2RFC_LOCK="$ROOT/runtime/toolchains/requirements-xml2rfc-3.34.0.txt"
TMP_DIR=
VENV_PATH=
VENV_BACKUP=
INSTALL_IN_PROGRESS=0
OVERALL=0

usage() {
    cat <<'EOF'
Usage: tools/bootstrap-runtime.sh [--check-only] [--install]
       [--accept-third-party]
       [--profile core|ietf|formal|audio|publication|all]
       [--cache-dir PATH]

Every profile checks GitHub CLI first. Only the verified GitHub CLI and
xml2rfc environments have an automatic install path. Other profile tools are
operator-managed and produce a precise CONTINUE when absent. Default: check.

Exit status: 0 PASS, 20 CONTINUE (runtime absent), 1 BLOCK, 2 usage error.
EOF
}

fail() {
    printf '%s\n' "BLOCK: $*" >&2
    exit 1
}

mark_continue() {
    printf '%s\n' "CONTINUE: $*" >&2
    OVERALL=20
}

cleanup() {
    if [ "$INSTALL_IN_PROGRESS" -eq 1 ] && [ -n "$VENV_PATH" ]; then
        if [ -e "$VENV_PATH" ] || [ -L "$VENV_PATH" ]; then
            rm -rf -- "$VENV_PATH"
        fi
        if [ -n "$VENV_BACKUP" ] && [ -d "$VENV_BACKUP" ]; then
            mv -- "$VENV_BACKUP" "$VENV_PATH"
        fi
    fi
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf -- "$TMP_DIR"
    fi
}
trap cleanup EXIT HUP INT TERM

reject_symlink_chain() {
    check_path=$1
    while [ "$check_path" != "/" ] && [ "$check_path" != "." ] && [ -n "$check_path" ]; do
        [ ! -L "$check_path" ] || fail "cache path contains a symlink: $check_path"
        parent_path=$(dirname -- "$check_path")
        [ "$parent_path" != "$check_path" ] || break
        check_path=$parent_path
    done
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --check-only) MODE=check ;;
        --install) MODE=install ;;
        --accept-third-party) ACCEPT_THIRD_PARTY=1 ;;
        --profile)
            shift
            [ "$#" -gt 0 ] || { usage >&2; exit 2; }
            PROFILE=$1
            ;;
        --cache-dir)
            shift
            [ "$#" -gt 0 ] || { usage >&2; exit 2; }
            CACHE_DIR=$1
            ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
    shift
done

case "$PROFILE" in
    core|ietf|formal|audio|publication|all) ;;
    *) usage >&2; exit 2 ;;
esac
if [ "$MODE" = install ] && [ "$ACCEPT_THIRD_PARTY" -ne 1 ]; then
    fail "--install requires --accept-third-party"
fi

reject_symlink_chain "$CACHE_DIR"
set +e
if [ "$MODE" = install ]; then
    sh "$SCRIPT_DIR/bootstrap-gh.sh" --install --accept-third-party --cache-dir "$CACHE_DIR"
else
    sh "$SCRIPT_DIR/bootstrap-gh.sh" --check-only --cache-dir "$CACHE_DIR"
fi
GH_RC=$?
set -e
case "$GH_RC" in
    0) ;;
    20) OVERALL=20 ;;
    *) exit "$GH_RC" ;;
esac

python_is_compatible() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

python_is_renderer_exact() {
    "$1" -I -c 'import platform, sys; raise SystemExit(0 if platform.python_version() == sys.argv[1] else 1)' \
        "$PYTHON_RENDERER_VERSION" >/dev/null 2>&1
}

python_is_312() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)' >/dev/null 2>&1
}

python_package_is_exact() {
    "$1" -c 'import importlib.metadata as m, sys; raise SystemExit(0 if m.version(sys.argv[1]) == sys.argv[2] else 1)' "$2" "$3" >/dev/null 2>&1
}

find_python() {
    for command_name in python3 python; do
        if command -v "$command_name" >/dev/null 2>&1; then
            candidate=$(command -v "$command_name")
            if python_is_compatible "$candidate"; then
                printf '%s\n' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

find_renderer_python() {
    if [ -n "${QIKVRT_PYTHON:-}" ]; then
        [ -f "$QIKVRT_PYTHON" ] && [ -x "$QIKVRT_PYTHON" ] || fail "QIKVRT_PYTHON is not an executable file"
        python_is_renderer_exact "$QIKVRT_PYTHON" || fail "QIKVRT_PYTHON is not exactly Python $PYTHON_RENDERER_VERSION"
        printf '%s\n' "$QIKVRT_PYTHON"
        return 0
    fi
    for command_name in python3.12 python3 python; do
        if command -v "$command_name" >/dev/null 2>&1; then
            candidate=$(command -v "$command_name")
            if python_is_renderer_exact "$candidate"; then
                printf '%s\n' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

find_python_312() {
    for command_name in python3.12 python3 python; do
        if command -v "$command_name" >/dev/null 2>&1; then
            candidate=$(command -v "$command_name")
            if python_is_312 "$candidate"; then
                printf '%s\n' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

check_core_profile() {
    compiler=${CC:-cc}
    if ! command -v "$compiler" >/dev/null 2>&1; then
        mark_continue "core: ANSI-C90 compiler is absent; automatic compiler installation is not supported"
        return
    fi
    if ! printf '%s\n' 'int main(void) { return 0; }' | \
        "$compiler" -std=c90 -pedantic -Wall -Wextra -Werror -x c -fsyntax-only - >/dev/null 2>&1; then
        mark_continue "core: $compiler does not satisfy the strict ANSI-C90 compile contract"
        return
    fi
    printf '%s\n' "PASS: core ANSI-C90 compiler contract: $(command -v "$compiler")"
}

xml2rfc_metadata_is_exact() {
    python_package_is_exact "$1" xml2rfc "$XML2RFC_VERSION"
}

xml2rfc_cli_is_exact() {
    first_line=$("$1" --version 2>/dev/null | sed -n '1p') || return 1
    [ "$first_line" = "xml2rfc $XML2RFC_VERSION" ]
}

xml2rfc_module_cli_is_exact() {
    first_line=$("$1" -m xml2rfc.run --version 2>/dev/null | sed -n '1p') || return 1
    [ "$first_line" = "xml2rfc $XML2RFC_VERSION" ]
}

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        fail "sha256sum or shasum is required"
    fi
}

pip_isolated() {
    pip_python=$1
    shift
    PIP_CONFIG_FILE=/dev/null PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1 \
        PYTHONNOUSERSITE=1 "$pip_python" -I -m pip --isolated \
        --disable-pip-version-check "$@"
}

locked_environment_is_exact() {
    "$1" -I -c '
import importlib.metadata as metadata
import pathlib
import re
import sys

canonical = lambda value: re.sub(r"[-_.]+", "-", value).lower()
expected = {}
for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    match = re.match(r"^([A-Za-z0-9_.-]+)==([^ \\]+)", line)
    if match:
        expected[canonical(match.group(1))] = match.group(2)
actual = {canonical(dist.metadata["Name"]): dist.version for dist in metadata.distributions()}
allowed_bootstrap = {"pip", "setuptools"}
raise SystemExit(0 if all(actual.get(name) == version for name, version in expected.items())
                 and not (set(actual) - set(expected) - allowed_bootstrap) else 1)
' "$XML2RFC_LOCK" >/dev/null 2>&1
}

check_ietf_profile() {
    [ -f "$XML2RFC_LOCK" ] || fail "missing xml2rfc lock: $XML2RFC_LOCK"
    pin_count=$(awk '/^[A-Za-z0-9_.-]+==/ {count++} END {print count+0}' "$XML2RFC_LOCK")
    [ "$pin_count" -eq 19 ] || fail "xml2rfc lock must contain exactly 19 pinned packages"
    [ "$(awk -F '[=[:space:]]+' '$1 == "xml2rfc" {print $2}' "$XML2RFC_LOCK")" = "$XML2RFC_VERSION" ] || fail "xml2rfc lock does not pin version $XML2RFC_VERSION"

    case "$(uname -s 2>/dev/null || printf unknown)" in
        Linux) XML_PLATFORM=linux-amd64 ;;
        Darwin) XML_PLATFORM=macOS-amd64 ;;
        *) mark_continue "ietf: POSIX xml2rfc adapter is unavailable on this operating system"; return ;;
    esac
    case "$(uname -m 2>/dev/null || printf unknown)" in
        x86_64|amd64) ;;
        *) mark_continue "ietf: the locked xml2rfc wheel set targets x64 runners"; return ;;
    esac

    XML_ROOT="$CACHE_DIR/xml2rfc/$XML2RFC_VERSION/python-$PYTHON_RENDERER_VERSION/$XML_PLATFORM"
    XML_CACHE="$XML_ROOT/venv"
    WHEELHOUSE="$XML_ROOT/wheelhouse"
    CACHED_PYTHON="$XML_CACHE/bin/python"
    CACHED_XML2RFC="$XML_CACHE/bin/xml2rfc"
    COMPLETE_MARKER="$XML_ROOT/COMPLETE"
    reject_symlink_chain "$XML_ROOT"

    if [ "$MODE" != install ]; then
        # A restored venv is untrusted executable state. Check-only deliberately
        # does not execute it; explicit install must rebuild it from hashed
        # wheels before any renderer code runs.
        mark_continue "ietf: fresh hash-locked derivation of xml2rfc $XML2RFC_VERSION / Python $PYTHON_RENDERER_VERSION is required"
        return
    fi
    SYSTEM_PYTHON=$(find_renderer_python || true)
    [ -n "$SYSTEM_PYTHON" ] || fail "exactly Python $PYTHON_RENDERER_VERSION is required to install the IETF renderer"
    reject_symlink_chain "$CACHE_DIR/xml2rfc"
    mkdir -p -- "$XML_ROOT"
    reject_symlink_chain "$XML_ROOT"
    TMP_DIR=$(mktemp -d "$XML_ROOT/.install.XXXXXX") || fail "could not create renderer staging directory"
    VERIFIED_WHEELHOUSE="$TMP_DIR/verified-wheelhouse"
    mkdir -- "$VERIFIED_WHEELHOUSE"

    if [ -d "$WHEELHOUSE" ]; then
        reject_symlink_chain "$WHEELHOUSE"
        pip_isolated "$SYSTEM_PYTHON" download --no-index --find-links "$WHEELHOUSE" \
            --dest "$VERIFIED_WHEELHOUSE" --only-binary=:all: --require-hashes --no-deps \
            -r "$XML2RFC_LOCK" || fail "cached wheelhouse failed hash-locked offline verification"
    else
        [ ! -e "$WHEELHOUSE" ] && [ ! -L "$WHEELHOUSE" ] || fail "renderer wheelhouse is not a regular directory"
        pip_isolated "$SYSTEM_PYTHON" download --index-url https://pypi.org/simple \
            --dest "$VERIFIED_WHEELHOUSE" --only-binary=:all: --require-hashes --no-deps \
            -r "$XML2RFC_LOCK" || fail "hash-locked renderer wheel download failed"
        mv -- "$VERIFIED_WHEELHOUSE" "$WHEELHOUSE"
        VERIFIED_WHEELHOUSE=$WHEELHOUSE
    fi

    # A virtual environment is deliberately not trusted after an Actions cache
    # restore. Every explicit install derives it again from the hash-verified
    # wheelhouse at its final path (console launchers embed this path).
    VENV_PATH=$XML_CACHE
    INSTALL_IN_PROGRESS=1
    if [ -e "$XML_CACHE" ] || [ -L "$XML_CACHE" ]; then
        [ -d "$XML_CACHE" ] && [ ! -L "$XML_CACHE" ] || fail "renderer venv is not a regular directory"
        VENV_BACKUP="$TMP_DIR/previous-venv"
        mv -- "$XML_CACHE" "$VENV_BACKUP"
    fi
    "$SYSTEM_PYTHON" -I -m venv --copies "$XML_CACHE" || fail "could not create xml2rfc virtual environment"
    CACHED_PYTHON="$XML_CACHE/bin/python"
    CACHED_XML2RFC="$XML_CACHE/bin/xml2rfc"
    pip_isolated "$CACHED_PYTHON" install --no-index --find-links "$VERIFIED_WHEELHOUSE" \
        --only-binary=:all: --require-hashes --no-deps --require-virtualenv \
        -r "$XML2RFC_LOCK" || fail "hash-locked offline xml2rfc installation failed"
    python_is_renderer_exact "$CACHED_PYTHON" || fail "installed renderer is not bound to Python $PYTHON_RENDERER_VERSION"
    locked_environment_is_exact "$CACHED_PYTHON" || fail "installed renderer does not contain exactly the locked package set"
    xml2rfc_metadata_is_exact "$CACHED_PYTHON" || fail "installed xml2rfc metadata is not exactly $XML2RFC_VERSION"
    python_package_is_exact "$CACHED_PYTHON" pypdf 6.14.2 || fail "installed pypdf metadata is not exactly 6.14.2"
    xml2rfc_cli_is_exact "$CACHED_XML2RFC" || fail "installed xml2rfc command failed its exact-version execution check"
    lock_sha=$(hash_file "$XML2RFC_LOCK")
    {
        printf '%s\n' "xml2rfc=$XML2RFC_VERSION"
        printf '%s\n' "python=$PYTHON_RENDERER_VERSION"
        printf '%s\n' "platform=$XML_PLATFORM"
        printf '%s\n' "lock_sha256=$lock_sha"
        printf '%s\n' "derivation=verified-wheelhouse"
    } > "$XML_ROOT/.COMPLETE.tmp"
    mv "$XML_ROOT/.COMPLETE.tmp" "$COMPLETE_MARKER"
    VENV_BACKUP=
    INSTALL_IN_PROGRESS=0
    rm -rf -- "$TMP_DIR"
    TMP_DIR=
    printf '%s\n' "PASS: xml2rfc $XML2RFC_VERSION on Python $PYTHON_RENDERER_VERSION (fresh hash-locked derivation): $CACHED_XML2RFC"
}

node_24_is_available() {
    command -v node >/dev/null 2>&1 || return 1
    node_version=$(node --version 2>/dev/null) || return 1
    case "$node_version" in v24.*) return 0 ;; *) return 1 ;; esac
}

check_formal_profile() {
    formal_root="$ROOT/formalization/QIKVRT_Formalization_v1.0"
    formal_python=$(find_python_312 || true)
    if [ -z "$formal_python" ]; then
        mark_continue "formal: Python 3.12.x is absent; automatic installation is not supported"
    elif ! python_package_is_exact "$formal_python" pytest 9.1.1; then
        mark_continue "formal: pytest 9.1.1 is absent from Python 3.12; automatic installation is not supported"
    else
        printf '%s\n' "PASS: formal Python 3.12 + pytest 9.1.1: $formal_python"
    fi

    if ! node_24_is_available; then
        mark_continue "formal: Node 24.x is absent; automatic installation is not supported"
    elif ! (cd "$formal_root" && node -e 'const p=require("./node_modules/zod/package.json"); process.exit(p.version === "4.4.3" ? 0 : 1)' >/dev/null 2>&1); then
        mark_continue "formal: installed Zod 4.4.3 is absent; run the reviewed npm lock installation"
    else
        printf '%s\n' "PASS: formal Node 24 + Zod 4.4.3"
    fi

    if ! command -v lean >/dev/null 2>&1 || ! command -v lake >/dev/null 2>&1; then
        mark_continue "formal: Lean 4.19.0 and Lake are absent; automatic installation is not supported"
    elif ! lean --version 2>/dev/null | sed -n '1p' | grep 'version 4\.19\.0' >/dev/null 2>&1; then
        mark_continue "formal: Lean is present but not version 4.19.0"
    else
        printf '%s\n' "PASS: formal Lean 4.19.0 + Lake"
    fi
}

check_audio_profile() {
    audio_root="$ROOT/tools/offline-audio-transcription"
    if ! node_24_is_available; then
        mark_continue "audio: Node 24.x is absent; automatic installation is not supported"
    elif ! (cd "$audio_root" && node -e 'const p=require("./node_modules/sherpa-onnx-node/package.json"); process.exit(p.version === "1.13.4" ? 0 : 1)' >/dev/null 2>&1); then
        mark_continue "audio: installed sherpa-onnx-node 1.13.4 is absent; run the reviewed npm lock installation"
    else
        printf '%s\n' "PASS: audio Node 24 + sherpa-onnx-node 1.13.4"
    fi

    if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
        mark_continue "audio: FFmpeg and FFprobe are required; automatic installation is not supported"
        return
    fi
    ffmpeg_version=$(ffmpeg -version 2>/dev/null | awk 'NR == 1 && $1 == "ffmpeg" && $2 == "version" {print $3}')
    ffprobe_version=$(ffprobe -version 2>/dev/null | awk 'NR == 1 && $1 == "ffprobe" && $2 == "version" {print $3}')
    if [ -z "$ffmpeg_version" ] || [ "$ffmpeg_version" != "$ffprobe_version" ]; then
        mark_continue "audio: FFmpeg and FFprobe must report the same non-empty version"
    else
        printf '%s\n' "PASS: audio FFmpeg/FFprobe $ffmpeg_version"
    fi
}

check_publication_profile() {
    missing=
    for tool in xelatex pdftotext pdftoppm; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            missing="$missing $tool"
        fi
    done
    if [ -n "$missing" ]; then
        mark_continue "publication: missing operator-managed tools:$missing"
        return
    fi
    xelatex --version 2>/dev/null | sed -n '1p' | grep . >/dev/null || fail "XeLaTeX did not report a version"
    pdftotext -v 2>&1 | sed -n '1p' | grep . >/dev/null || fail "pdftotext did not report a version"
    pdftoppm -v 2>&1 | sed -n '1p' | grep . >/dev/null || fail "pdftoppm did not report a version"
    printf '%s\n' "PASS: publication XeLaTeX + Poppler command contract"
}

case "$PROFILE" in
    core) check_core_profile ;;
    ietf) check_ietf_profile ;;
    formal) check_formal_profile ;;
    audio) check_audio_profile ;;
    publication) check_publication_profile ;;
    all)
        check_core_profile
        check_ietf_profile
        check_formal_profile
        check_audio_profile
        check_publication_profile
        ;;
esac

exit "$OVERALL"
