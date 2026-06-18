#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Ingolf Lohmann.
# Author/Rights holder: Ingolf Lohmann.
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$ROOT/LOGS"
echo "[QALL] macOS-Start / macOS start" > "$ROOT/LOGS/LAST_RUN.txt"
exec /bin/sh "$ROOT/_payload/_internal/RUN.sh" "$ROOT"
