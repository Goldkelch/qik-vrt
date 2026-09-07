#!/bin/sh
set -eu

HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"

curl --max-time 2 -fsS "http://127.0.0.1:${HTTP_PORT}/.well-known/effect-ack" >/dev/null
pgrep -af 'firefox|firefox-esr' >/dev/null
curl --max-time 2 -fsS "http://127.0.0.1:${NOVNC_PORT}/vnc.html" >/dev/null
test -f "${STATE_DIR}/runtime.json"
python3 -B - "${STATE_DIR}/runtime.json" <<'PY'
import json,sys
p=sys.argv[1]
obj=json.load(open(p,encoding='utf-8'))
assert obj['schema']=='qikvrt_universal_terminal_runtime_state_v2'
assert obj['runtime_id']
assert obj['profile_persistent'] is True
assert obj['browser']=='firefox-esr'
assert obj['external_effect_claimed'] is False
assert obj['effect_ack_host'] in {'127.0.0.1', 'localhost'}
assert obj['mesh_path']=='/qik-vrt/mesh/v1/'
assert obj['pass'] is False
assert obj['final_pass'] is False
assert obj['effect_ack_done'] is False
PY
