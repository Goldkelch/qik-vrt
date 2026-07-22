#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP_ROOT=${TMPDIR:-/tmp}
BUILD_DIR=$(mktemp -d "$TMP_ROOT/qikvrt-effect-ack-c90.XXXXXX")
trap 'rm -rf "$BUILD_DIR"' EXIT HUP INT TERM

CC=${CC:-cc}

"$CC" \
    -std=c90 \
    -pedantic \
    -Wall \
    -Wextra \
    -Werror \
    -I"$ROOT/include" \
    "$ROOT/src/effect_ack_core.c" \
    "$ROOT/tests/test_effect_ack_core.c" \
    -o "$BUILD_DIR/test_effect_ack_core"

"$BUILD_DIR/test_effect_ack_core"
