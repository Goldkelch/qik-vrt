#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -eu

AUTHORITY_URL="${QIKVRT_AUTHORITY_URL:-https://github.com/Goldkelch/qik-vrt.git}"
MIRROR_DIR="${QIKVRT_AUTHORITY_MIRROR_DIR:-/var/lib/qikvrt/mirror/authority.git}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
RECEIPT="${STATE_DIR}/authority-mirror.json"

case "$AUTHORITY_URL" in
  https://github.com/Goldkelch/qik-vrt.git) ;;
  *)
    printf '%s\n' "BLOCK: authority URL is not the canonical Goldkelch/qik-vrt HTTPS remote" >&2
    exit 20
    ;;
esac

mkdir -p "$(dirname "$MIRROR_DIR")" "$STATE_DIR"

if [ ! -f "$MIRROR_DIR/HEAD" ]; then
  if [ -d "$MIRROR_DIR" ]; then
    rmdir "$MIRROR_DIR" 2>/dev/null || {
      printf '%s\n' "BLOCK: mirror target exists but is not an empty/valid bare repository" >&2
      exit 21
    }
  fi
  git clone --mirror --filter=blob:none "$AUTHORITY_URL" "$MIRROR_DIR"
else
  test "$(git --git-dir="$MIRROR_DIR" remote get-url origin)" = "$AUTHORITY_URL"
  git --git-dir="$MIRROR_DIR" remote update --prune
fi

MAIN_SHA="$(git --git-dir="$MIRROR_DIR" rev-parse --verify refs/heads/main^{commit})"
MAIN_TREE="$(git --git-dir="$MIRROR_DIR" rev-parse --verify refs/heads/main^{tree})"
ORIGIN="$(git --git-dir="$MIRROR_DIR" remote get-url origin)"

python3 -B - "$RECEIPT" "$ORIGIN" "$MAIN_SHA" "$MAIN_TREE" <<'PY'
import json
import os
import sys
import time

path, origin, head, tree = sys.argv[1:]
value = {
    "schema": "qikvrt_cloud_transputer_authority_mirror_receipt_v1",
    "authority_repository": "Goldkelch/qik-vrt",
    "origin": origin,
    "main_head_sha": head,
    "main_tree_sha": tree,
    "observed_at_unix": int(time.time()),
    "operation": "BOUNDED_REMOTE_UPDATE",
    "polling": False,
    "writeback_to_authority": False,
    "force_push": False,
    "pass": False,
    "final_pass": False,
    "effect_ack_done": False,
}
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
    json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
os.replace(tmp, path)
PY

printf '%s\n' "AUTHORITY_MIRROR_HEAD=$MAIN_SHA"
printf '%s\n' "AUTHORITY_MIRROR_TREE=$MAIN_TREE"
