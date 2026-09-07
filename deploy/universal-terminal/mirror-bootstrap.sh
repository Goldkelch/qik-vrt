#!/bin/sh
set -eu

AUTHORITY_URL="${QIKVRT_AUTHORITY_URL:-https://github.com/Goldkelch/qik-vrt.git}"
MIRROR_URL="${QIKVRT_MIRROR_URL:-https://github.com/ingolf-lohmann/qik-vrt.git}"
ROOT="${QIKVRT_MIRROR_STATE_DIR:-/var/lib/qikvrt/mirror}"
REPO="${ROOT}/qik-vrt.git"
STATE="${ROOT}/mirror-state.json"

mkdir -p "$ROOT"

if [ ! -d "$REPO/objects" ]; then
  git clone --mirror "$AUTHORITY_URL" "$REPO"
else
  git --git-dir="$REPO" remote set-url origin "$AUTHORITY_URL"
  git --git-dir="$REPO" fetch --prune origin \
    '+refs/heads/*:refs/heads/*' \
    '+refs/tags/*:refs/tags/*'
fi

if git --git-dir="$REPO" remote get-url mirror >/dev/null 2>&1; then
  git --git-dir="$REPO" remote set-url mirror "$MIRROR_URL"
else
  git --git-dir="$REPO" remote add mirror "$MIRROR_URL"
fi

AUTHORITY_HEAD="$(git --git-dir="$REPO" rev-parse refs/heads/main)"
AUTHORITY_TREE="$(git --git-dir="$REPO" rev-parse "${AUTHORITY_HEAD}^{tree}")"
MIRROR_HEAD="$(git ls-remote "$MIRROR_URL" refs/heads/main | awk 'NR==1 {print $1}')"

python3 -B - "$STATE" "$AUTHORITY_URL" "$MIRROR_URL" "$AUTHORITY_HEAD" "$AUTHORITY_TREE" "$MIRROR_HEAD" <<'PY'
import json,sys,time
path,authority_url,mirror_url,authority_head,authority_tree,mirror_head=sys.argv[1:]
obj={
  "schema":"qikvrt_authority_connected_runtime_mirror_v1",
  "authority_url":authority_url,
  "mirror_url":mirror_url,
  "authority_main_head":authority_head,
  "authority_main_tree":authority_tree,
  "observed_mirror_main_head":mirror_head or None,
  "synchronized":bool(mirror_head) and mirror_head == authority_head,
  "mutation_performed":False,
  "served_protocol":"git",
  "served_port":9418,
  "observed_at_unix":int(time.time()),
}
open(path,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
PY

exec git daemon \
  --reuseaddr \
  --export-all \
  --verbose \
  --base-path="$ROOT" \
  --listen=0.0.0.0 \
  --port=9418 \
  "$ROOT"
