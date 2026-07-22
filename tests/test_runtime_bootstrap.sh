#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# Durable offline lifecycle checks for the POSIX GitHub CLI bootstrap.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
BOOTSTRAP="$ROOT/tools/bootstrap-gh.sh"
SOURCE_CACHE=${QIKVRT_TEST_SOURCE_CACHE:-"$ROOT/.qikvrt/toolchains"}

case "$(uname -s 2>/dev/null || printf unknown)" in
    Linux) OS=linux; EXT=tar.gz ;;
    Darwin) OS=macOS; EXT=zip ;;
    *) printf '%s\n' "SKIP: no POSIX GitHub CLI fixture mapping for this OS"; exit 0 ;;
esac
case "$(uname -m 2>/dev/null || printf unknown)" in
    x86_64|amd64) ARCH=amd64 ;;
    arm64|aarch64) ARCH=arm64 ;;
    *) printf '%s\n' "SKIP: no GitHub CLI fixture mapping for this architecture"; exit 0 ;;
esac

VERSION=2.96.0
TARGET="$OS-$ARCH"
ARCHIVE="gh_${VERSION}_${OS}_${ARCH}.${EXT}"
SOURCE_ARCHIVE="$SOURCE_CACHE/gh/$VERSION/$TARGET/archive/$ARCHIVE"
if [ ! -f "$SOURCE_ARCHIVE" ]; then
    printf '%s\n' "SKIP: verified source archive is absent; CI creates it with the full install contract"
    exit 0
fi

SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/qikvrt-runtime-bootstrap-test.XXXXXX")
cleanup() {
    case "$SCRATCH" in
        */qikvrt-runtime-bootstrap-test.*) rm -rf -- "$SCRATCH" ;;
        *) printf '%s\n' "refusing unsafe test cleanup: $SCRATCH" >&2 ;;
    esac
}
trap cleanup EXIT HUP INT TERM

fail() {
    printf '%s\n' "FAIL: $*" >&2
    exit 1
}

SUCCESS_CACHE="$SCRATCH/success"
sh "$BOOTSTRAP" --install --accept-third-party \
    --archive-file "$SOURCE_ARCHIVE" --cache-dir "$SUCCESS_CACHE" >/dev/null
[ -x "$SUCCESS_CACHE/gh/$VERSION/$TARGET/bin/gh" ] || fail "successful install did not create the executable"
[ -z "$(find "$SUCCESS_CACHE/gh/$VERSION" -maxdepth 1 -name '.install-*' -print -quit)" ] || \
    fail "successful install retained a staging directory"
sh "$BOOTSTRAP" --check-only --cache-dir "$SUCCESS_CACHE" >/dev/null || \
    fail "installed cache did not pass its archive-derived byte verification"

ROLLBACK_CACHE="$SCRATCH/rollback"
set +e
QIKVRT_TEST_FAIL_GH_FINAL_VERIFY=1 sh "$BOOTSTRAP" --install --accept-third-party \
    --archive-file "$SOURCE_ARCHIVE" --cache-dir "$ROLLBACK_CACHE" \
    >"$SCRATCH/rollback.stdout" 2>"$SCRATCH/rollback.stderr"
rollback_rc=$?
set -e
[ "$rollback_rc" -eq 1 ] || fail "test-requested final verification failure returned $rollback_rc"
[ ! -e "$ROLLBACK_CACHE/gh/$VERSION/$TARGET" ] || fail "failed final verification retained the installed cache root"
[ -z "$(find "$ROLLBACK_CACHE/gh/$VERSION" -maxdepth 1 -name '.install-*' -print -quit 2>/dev/null)" ] || \
    fail "failed final verification retained a staging directory"

printf '%s\n' "PASS: POSIX GitHub CLI staging cleanup and final-verification rollback"
