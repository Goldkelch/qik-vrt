#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -eu

STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
SQL_UI_PORT="${QIKVRT_SQL_UI_PORT:-8772}"
M68K_DIR="$STATE_DIR/m68k"
VERIFY_SQL_EFFECT="${QIKVRT_VERIFY_SQL_EFFECT_ACK:-0}"
TMP_DIR="$(mktemp -d /tmp/qikvrt-v2-health.XXXXXX)"
CAPABILITY_JSON="$TMP_DIR/sql92-capability.json"
STATE_JSON="$TMP_DIR/sql92-state.json"
trap 'rm -rf "$TMP_DIR"' EXIT

case "$VERIFY_SQL_EFFECT" in
  0|1) ;;
  *) printf '%s\n' 'BLOCK: QIKVRT_VERIFY_SQL_EFFECT_ACK must be 0 or 1' >&2; exit 64 ;;
esac

/usr/local/bin/qikvrt-cloud-transputer-health-v1

mark() { printf 'QIKVRT_V2_HEALTH_PROBE=%s\n' "$1"; }

mark personal_posix_m68000
file "$M68K_DIR/qikvrt-personal-posix-tcpip" | grep -Eqi '68000|m68k|Motorola'
grep -q '^ARCH=M68000_FAMILY$' "$M68K_DIR/personal-posix-tcpip-execution.txt"
grep -q '^PERSONAL_POSIX_SELFTEST=PASS$' "$M68K_DIR/personal-posix-tcpip-execution.txt"
grep -q '^STANDALONE_M68000_TCPIP_PACKET_ENGINE=PASS$' "$M68K_DIR/personal-posix-tcpip-execution.txt"
grep -q '^EFFECT_ACK_STATE=EFFECT_ACK_DONE$' "$M68K_DIR/personal-posix-tcpip-execution.txt"

mark personal_posix_receipt
python3 -B - "$M68K_DIR/personal-posix-tcpip-receipt.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding='utf-8'))
assert r['schema']=='qikvrt_personal_posix_m68000_tcpip_receipt_v1'
assert r['profile']=='QIKVRT_PERSONAL_POSIX_C90_V1'
assert r['m68000_machine_execution_observed'] is True
assert r['posix_profile_selftest']=='PASS'
assert r['standalone_tcp_ip_packet_engine']=='PASS'
assert r['existing_effect_ack_core_linked'] is True
assert r['effect_ack_done_local_selftest'] is True
assert r['negative_effect_ack_fail_closed'] is True
assert r['external_packet_io_adapter']=='LINUX_OCI_HOST_ADAPTER'
assert r['bare_metal_nic_driver_claimed'] is False
assert r['full_posix_1_conformance_claimed'] is False
assert r['physical_m68000_execution_claimed'] is False
assert r['repository_or_publication_effect_claimed'] is False
assert r['pass'] is False and r['final_pass'] is False and r['global_effect_ack_done'] is False
PY

mark sql92_ui
curl -fsS "http://127.0.0.1:${SQL_UI_PORT}/" | grep -q 'QIK-VRT SQL92 / EFFECT_ACK terminal'
curl -fsS "http://127.0.0.1:${SQL_UI_PORT}/.well-known/qikvrt-sql92" >"$CAPABILITY_JSON"
python3 -B - "$CAPABILITY_JSON" <<'PY'
import json,sys
c=json.load(open(sys.argv[1],encoding='utf-8'))
assert c['schema']=='qikvrt_sql92_terminal_capability_v1'
assert c['modes']==['prepare','commit','readback']
assert c['full_sql92_conformance_claimed'] is False
assert c['transport_ack_is_effect_ack'] is False
PY

if [ "$VERIFY_SQL_EFFECT" = 1 ]; then
  mark sql92_effect_ack_prepare_commit_readback
  python3 -B - "$SQL_UI_PORT" <<'PY'
import base64,json,sys,urllib.error,urllib.request
port=int(sys.argv[1])
base=f'http://127.0.0.1:{port}'
body={
  'schema':'qikvrt_sql92_request_v1',
  'sql':'SELECT 20 + 22 AS answer',
  'readback_sql':'SELECT 20 + 22 AS answer',
}
payload=json.dumps(body,sort_keys=True,separators=(',',':')).encode()
req=urllib.request.Request(base+'/prepare',data=payload,method='POST',headers={
  'Content-Type':'application/json','Effect-Ack-Request':'v=1, mode=prepare'})
with urllib.request.urlopen(req,timeout=5) as response:
    prep=json.load(response)
assert prep['state']=='PREPARED_NO_EFFECT' and prep['ordinary_release'] is False
token64=base64.b64encode(prep['commit_token'].encode('ascii')).decode('ascii')
hash64=base64.b64encode(bytes.fromhex(prep['request_hash'])).decode('ascii')
header=f'v=1, mode=commit, token=:{token64}:, hash=:{hash64}:'
req=urllib.request.Request(base+'/commit',data=payload,method='POST',headers={
  'Content-Type':'application/json','Effect-Ack-Request':header})
try:
    response=urllib.request.urlopen(req,timeout=10)
except urllib.error.HTTPError as exc:
    body=exc.read().decode('utf-8','replace')
    raise SystemExit(f'SQL EFFECT_NACK HTTP {exc.code}: {body}')
with response:
    result=json.load(response)
r=result['receipt']
assert r['effect_ack_state']=='EFFECT_ACK_DONE'
assert r['effect_domain']=='LOCAL_QIKVRT_DATABASE_ONLY'
assert r['ordinary_release'] is True
assert r['result_rows']==['42'] and r['readback_rows']==['42']
assert r['authoritative_external_effect'] is False
assert r['repository_effect'] is False and r['publication_effect'] is False
PY
else
  mark sql92_effect_ack_available_no_commit
fi

mark sql92_state_binds_runtime_and_authority_mirror
curl -fsS "http://127.0.0.1:${SQL_UI_PORT}/state" >"$STATE_JSON"
python3 -B - "$STATE_JSON" "$VERIFY_SQL_EFFECT" <<'PY'
import json,sys
s=json.load(open(sys.argv[1],encoding='utf-8'))
require_effect=sys.argv[2]=='1'
assert s['schema']=='qikvrt_sql92_terminal_state_v1'
assert s['runtime'] is not None
assert s['authority-mirror'] is not None
assert s['authority-mirror']['authority_repository']=='Goldkelch/qik-vrt'
assert len(s['authority-mirror']['main_head_sha'])==40
assert len(s['authority-mirror']['main_tree_sha'])==40
assert isinstance(s['receipt_count'],int) and s['receipt_count'] >= (1 if require_effect else 0)
PY

mark complete
