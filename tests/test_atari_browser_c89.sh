#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -eu
: "${CC:=cc}"
work="${TMPDIR:-/tmp}/qikvrt-atari-browser-c89.$$"
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work"
"$CC" -std=c90 -pedantic -Wall -Wextra -Werror -Iinclude \
  src/atari_browser_c89.c tests/test_atari_browser_c89.c \
  -o "$work/test_atari_browser_c89"
"$work/test_atari_browser_c89"
"$CC" -std=c90 -pedantic -Wall -Wextra -Werror -Iinclude \
  src/atari_browser_c89.c runtime/atari-megast/qikbrow.c \
  -o "$work/qikbrow"
printf '%s\n' '<html><title>Atari</title><body><h1>QIKVRT</h1><p>C89 browser capsule</p></body></html>' \
  > "$work/page.html"
"$work/qikbrow" "$work/page.html" | grep 'QIKVRT' >/dev/null
