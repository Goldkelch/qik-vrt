#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

set -eu

VERSION=2.96.0
MODE=check
ACCEPT_THIRD_PARTY=0
PRINT_PATH=0
ARCHIVE_FILE=
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
CACHE_DIR=${QIKVRT_TOOLCHAIN_CACHE:-"$ROOT/.qikvrt/toolchains"}
CHECKSUMS="$ROOT/runtime/toolchains/gh-2.96.0-checksums.txt"
EXTRACTED_CHECKSUMS="$ROOT/runtime/toolchains/gh-2.96.0-extracted.sha256"
TMP_DIR=
ROLLBACK_CACHE_ROOT=0

usage() {
    cat <<'EOF'
Usage: tools/bootstrap-gh.sh [--check-only] [--install]
       [--accept-third-party] [--cache-dir PATH] [--archive-file PATH]
       [--print-path]

The default is an offline, non-mutating exact-version check. --install also
requires --accept-third-party. Authentication is intentionally not performed.

Exit status: 0 PASS, 20 CONTINUE (runtime absent), 1 BLOCK, 2 usage error.
EOF
}

fail() {
    printf '%s\n' "BLOCK: $*" >&2
    exit 1
}

continue_status() {
    printf '%s\n' "CONTINUE: $*" >&2
    exit 20
}

cleanup() {
    if [ "$ROLLBACK_CACHE_ROOT" -eq 1 ] && [ -n "${CACHE_ROOT:-}" ]; then
        if [ -e "$CACHE_ROOT" ] || [ -L "$CACHE_ROOT" ]; then
            rm -rf -- "$CACHE_ROOT"
        fi
        ROLLBACK_CACHE_ROOT=0
    fi
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf -- "$TMP_DIR"
    fi
}
trap cleanup EXIT HUP INT TERM

while [ "$#" -gt 0 ]; do
    case "$1" in
        --check-only) MODE=check ;;
        --install) MODE=install ;;
        --accept-third-party) ACCEPT_THIRD_PARTY=1 ;;
        --cache-dir)
            shift
            [ "$#" -gt 0 ] || { usage >&2; exit 2; }
            CACHE_DIR=$1
            ;;
        --archive-file)
            shift
            [ "$#" -gt 0 ] || { usage >&2; exit 2; }
            ARCHIVE_FILE=$1
            ;;
        --print-path) PRINT_PATH=1 ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
    shift
done

[ -f "$CHECKSUMS" ] || fail "missing checksum authority: $CHECKSUMS"
[ -f "$EXTRACTED_CHECKSUMS" ] || fail "missing extracted checksum authority: $EXTRACTED_CHECKSUMS"

case "$(uname -s 2>/dev/null || printf unknown)" in
    Linux) OS=linux; EXT=tar.gz ;;
    Darwin) OS=macOS; EXT=zip ;;
    *) continue_status "GitHub CLI bootstrap has no POSIX adapter for this operating system" ;;
esac

case "$(uname -m 2>/dev/null || printf unknown)" in
    x86_64|amd64) ARCH=amd64 ;;
    arm64|aarch64) ARCH=arm64 ;;
    *) continue_status "GitHub CLI bootstrap has no locked asset for this architecture" ;;
esac

TARGET="$OS-$ARCH"
ARCHIVE="gh_${VERSION}_${OS}_${ARCH}.${EXT}"
EXPECTED_ARCHIVE_SHA=$(awk -v archive="$ARCHIVE" '$2 == archive { print $1 }' "$CHECKSUMS")
[ -n "$EXPECTED_ARCHIVE_SHA" ] || fail "no checksum is locked for $ARCHIVE"

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        fail "sha256sum or shasum is required"
    fi
}

exact_version() {
    candidate=$1
    [ -f "$candidate" ] && [ -x "$candidate" ] || return 1
    first_line=$("$candidate" --version 2>/dev/null | sed -n '1p') || return 1
    [ "$first_line" = "gh version $VERSION (2026-07-02)" ]
}

reject_symlink_chain() {
    check_path=$1
    while [ "$check_path" != "/" ] && [ "$check_path" != "." ] && [ -n "$check_path" ]; do
        [ ! -L "$check_path" ] || fail "cache path contains a symlink: $check_path"
        parent_path=$(dirname -- "$check_path")
        [ "$parent_path" != "$check_path" ] || break
        check_path=$parent_path
    done
}

emit_pass() {
    candidate=$1
    source_name=$2
    if [ "$PRINT_PATH" -eq 1 ]; then
        printf '%s\n' "$candidate"
    else
        printf '%s\n' "PASS: GitHub CLI $VERSION ($source_name): $candidate"
    fi
    exit 0
}

verify_cached() {
    candidate=$1
    cache_root=$2
    cached_archive="$cache_root/archive/$ARCHIVE"
    [ -f "$cached_archive" ] || fail "cached GitHub CLI archive is missing: $cached_archive"
    actual_archive_sha=$(hash_file "$cached_archive")
    [ "$actual_archive_sha" = "$EXPECTED_ARCHIVE_SHA" ] || fail "cached GitHub CLI archive checksum mismatch"

    # A cache-service receipt and `gh --version` are not byte authorities.
    # Re-extract the repo-hash-anchored archive and compare executable bytes on
    # every platform, including targets without a separately committed binary
    # digest.
    verify_dir=$(mktemp -d "${TMPDIR:-/tmp}/qikvrt-gh-verify.XXXXXX") || fail "could not create GitHub CLI verification directory"
    case "$EXT" in
        tar.gz)
            command -v tar >/dev/null 2>&1 || { rm -rf -- "$verify_dir"; fail "tar is required to verify $ARCHIVE"; }
            tar --no-same-owner -xzf "$cached_archive" -C "$verify_dir" || { rm -rf -- "$verify_dir"; fail "cached GitHub CLI archive extraction failed"; }
            ;;
        zip)
            command -v unzip >/dev/null 2>&1 || { rm -rf -- "$verify_dir"; fail "unzip is required to verify $ARCHIVE"; }
            unzip -q "$cached_archive" -d "$verify_dir" || { rm -rf -- "$verify_dir"; fail "cached GitHub CLI archive extraction failed"; }
            ;;
    esac
    derived_candidate="$verify_dir/gh_${VERSION}_${OS}_${ARCH}/bin/gh"
    [ -f "$derived_candidate" ] || { rm -rf -- "$verify_dir"; fail "repo-anchored archive does not contain the expected GitHub CLI executable"; }
    derived_binary_sha=$(hash_file "$derived_candidate")
    actual_binary_sha=$(hash_file "$candidate")
    rm -rf -- "$verify_dir"
    [ "$actual_binary_sha" = "$derived_binary_sha" ] || fail "cached GitHub CLI executable is not derived from the repo-anchored archive"

    expected_binary_sha=$(awk -v path="$TARGET/bin/gh" '$2 == path { print $1 }' "$EXTRACTED_CHECKSUMS")
    if [ -n "$expected_binary_sha" ]; then
        [ "$actual_binary_sha" = "$expected_binary_sha" ] || fail "cached GitHub CLI executable checksum mismatch"
    fi
    exact_version "$candidate" || fail "cached GitHub CLI failed the exact-version execution check"
}

if [ -n "${QIKVRT_GH:-}" ] && [ "$MODE" != install ]; then
    [ -f "$QIKVRT_GH" ] || fail "QIKVRT_GH does not name a regular file"
    exact_version "$QIKVRT_GH" || fail "QIKVRT_GH is not executable GitHub CLI $VERSION"
    emit_pass "$QIKVRT_GH" explicit
fi

CACHE_ROOT="$CACHE_DIR/gh/$VERSION/$TARGET"
CACHED_GH="$CACHE_ROOT/bin/gh"
reject_symlink_chain "$CACHE_DIR"
reject_symlink_chain "$CACHE_ROOT"
if [ -e "$CACHED_GH" ] || [ -L "$CACHED_GH" ]; then
    reject_symlink_chain "$CACHED_GH"
    verify_cached "$CACHED_GH" "$CACHE_ROOT"
    emit_pass "$CACHED_GH" verified-cache
fi

if [ "$MODE" != install ] && command -v gh >/dev/null 2>&1; then
    SYSTEM_GH=$(command -v gh)
    if exact_version "$SYSTEM_GH"; then
        emit_pass "$SYSTEM_GH" system
    fi
fi

[ "$MODE" = install ] || continue_status "GitHub CLI $VERSION is not available; rerun with explicit installation consent"
[ "$ACCEPT_THIRD_PARTY" -eq 1 ] || fail "--install requires --accept-third-party"

if [ -e "$CACHE_ROOT" ]; then
    fail "refusing to replace an incomplete GitHub CLI cache: $CACHE_ROOT"
fi
[ ! -L "$CACHE_DIR" ] || fail "toolchain cache directory must not be a symlink"
mkdir -p -- "$CACHE_DIR/gh/$VERSION"
reject_symlink_chain "$CACHE_DIR/gh/$VERSION"
TMP_DIR=$(mktemp -d "$CACHE_DIR/gh/$VERSION/.install-${TARGET}.XXXXXX") || fail "could not create installation staging directory"
DOWNLOADED="$TMP_DIR/$ARCHIVE"
URL="https://github.com/cli/cli/releases/download/v$VERSION/$ARCHIVE"

if [ -n "$ARCHIVE_FILE" ]; then
    [ -f "$ARCHIVE_FILE" ] && [ ! -L "$ARCHIVE_FILE" ] || fail "--archive-file must name a regular non-symlink file"
    cp "$ARCHIVE_FILE" "$DOWNLOADED" || fail "could not stage the supplied GitHub CLI archive"
elif command -v curl >/dev/null 2>&1; then
    curl --fail --location --proto '=https' --tlsv1.2 --output "$DOWNLOADED" "$URL" || fail "GitHub CLI download failed"
else
    fail "curl is required for an explicitly authorized installation"
fi

ACTUAL_ARCHIVE_SHA=$(hash_file "$DOWNLOADED")
[ "$ACTUAL_ARCHIVE_SHA" = "$EXPECTED_ARCHIVE_SHA" ] || fail "downloaded GitHub CLI archive checksum mismatch"

EXTRACT_DIR="$TMP_DIR/extracted"
mkdir -p -- "$EXTRACT_DIR"
case "$EXT" in
    tar.gz)
        command -v tar >/dev/null 2>&1 || fail "tar is required to extract $ARCHIVE"
        # Never request archive-owner restoration. Restricted containers and
        # ordinary non-root users cannot chown to the upstream build UID, and
        # ownership is not part of the verified executable-byte contract.
        tar --no-same-owner -xzf "$DOWNLOADED" -C "$EXTRACT_DIR" || fail "GitHub CLI archive extraction failed"
        ;;
    zip)
        command -v unzip >/dev/null 2>&1 || fail "unzip is required to extract $ARCHIVE"
        unzip -q "$DOWNLOADED" -d "$EXTRACT_DIR" || fail "GitHub CLI archive extraction failed"
        ;;
esac

EXTRACTED_GH="$EXTRACT_DIR/gh_${VERSION}_${OS}_${ARCH}/bin/gh"
[ -f "$EXTRACTED_GH" ] || fail "extracted GitHub CLI executable is missing"
chmod 0755 "$EXTRACTED_GH"
exact_version "$EXTRACTED_GH" || fail "extracted GitHub CLI failed the exact-version execution check"

EXPECTED_BINARY_SHA=$(awk -v path="$TARGET/bin/gh" '$2 == path { print $1 }' "$EXTRACTED_CHECKSUMS")
if [ -n "$EXPECTED_BINARY_SHA" ]; then
    ACTUAL_BINARY_SHA=$(hash_file "$EXTRACTED_GH")
    [ "$ACTUAL_BINARY_SHA" = "$EXPECTED_BINARY_SHA" ] || fail "extracted GitHub CLI executable checksum mismatch"
fi

STAGE="$TMP_DIR/stage"
mkdir -p -- "$STAGE/bin" "$STAGE/archive"
cp "$EXTRACTED_GH" "$STAGE/bin/gh"
cp "$DOWNLOADED" "$STAGE/archive/$ARCHIVE"
hash_file "$STAGE/bin/gh" > "$STAGE/bin/gh.sha256"
ROLLBACK_CACHE_ROOT=1
mv "$STAGE" "$CACHE_ROOT" || fail "could not atomically install GitHub CLI cache"
# Failure-only regression hook: it can turn a valid install into BLOCK but can
# never bypass a check or authorize an effect.
if [ "${QIKVRT_TEST_FAIL_GH_FINAL_VERIFY:-0}" = 1 ]; then
    fail "test-requested failure before final GitHub CLI cache verification"
fi
verify_cached "$CACHED_GH" "$CACHE_ROOT"
ROLLBACK_CACHE_ROOT=0
cleanup
TMP_DIR=
emit_pass "$CACHED_GH" installed-verified-cache
