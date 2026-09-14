#!/bin/sh
set -eu

HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"

curl -fsS "http://127.0.0.1:${HTTP_PORT}/.well-known/effect-ack" >/dev/null
pgrep -af 'firefox|firefox-esr' >/dev/null
curl -fsS "http://127.0.0.1:${NOVNC_PORT}/vnc.html" >/dev/null
test -f "${STATE_DIR}/runtime.json"
python3 -B - "${STATE_DIR}/runtime.json" <<'PY'
import json,sys
p=sys.argv[1]
obj=json.load(open(p,encoding='utf-8'))
assert obj['schema']=='qikvrt_universal_terminal_runtime_state_v1'
assert obj['runtime_id']
assert obj['profile_persistent'] is True
assert obj['browser']=='firefox-esr'
assert obj['external_effect_claimed'] is False
PY
