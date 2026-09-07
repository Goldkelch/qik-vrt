#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -eu

STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
PROXY_PORT="${QIKVRT_PROXY_PORT:-8080}"
SSH_PORT="${QIKVRT_SSH_PORT:-2222}"
SMTP_PORT="${QIKVRT_SMTP_PORT:-2525}"
DNS_PORT="${QIKVRT_DNS_PORT:-5353}"
SNMP_PORT="${QIKVRT_SNMP_PORT:-1161}"
SQL_PORT="${QIKVRT_SQL_PORT:-5432}"
MESH_DOMAIN="${QIKVRT_MESH_DOMAIN:-qikvrt.mesh.local}"
MESH_PUBLIC_URL="${QIKVRT_MESH_PUBLIC_URL:-https://goldkelch.github.io/qik-vrt/cloud-transputer/}"
RUN_STATE=/run/qikvrt/runtime.json
READY_ATTEMPTS="${QIKVRT_HEALTH_READY_ATTEMPTS:-8}"

case "$READY_ATTEMPTS" in
  ''|*[!0-9]*) printf '%s\n' 'BLOCK: QIKVRT_HEALTH_READY_ATTEMPTS must be a positive integer' >&2; exit 64 ;;
esac
if [ "$READY_ATTEMPTS" -lt 1 ]; then
  printf '%s\n' 'BLOCK: QIKVRT_HEALTH_READY_ATTEMPTS must be at least 1' >&2
  exit 64
fi

# Finite startup gate only.  The strict probes below remain unchanged and are
# still authoritative.  Each attempt stops at the first not-yet-ready endpoint,
# so the default worst-case delay remains below Docker's 10 s health timeout.
python3 -B - "$HTTP_PORT" "$NOVNC_PORT" "$PROXY_PORT" "$SMTP_PORT" "$SSH_PORT" "$SQL_PORT" "$READY_ATTEMPTS" <<'PY'
import socket
import sys
import time
from urllib.request import urlopen

http_port, novnc_port, proxy_port, smtp_port, ssh_port, sql_port, attempts = map(int, sys.argv[1:])
http_targets = (
    ('effect_ack_direct', f'http://127.0.0.1:{http_port}/.well-known/effect-ack'),
    ('novnc_direct', f'http://127.0.0.1:{novnc_port}/vnc.html'),
    ('proxy_terminal', f'http://127.0.0.1:{proxy_port}/terminal/vnc.html'),
    ('proxy_effect_ack', f'http://127.0.0.1:{proxy_port}/effect-ack/.well-known/effect-ack'),
    ('proxy_runtime_receipt', f'http://127.0.0.1:{proxy_port}/.well-known/qikvrt-cloud-transputer'),
)
tcp_targets = (
    ('smtp', smtp_port),
    ('ssh', ssh_port),
    ('postgresql_tcp', sql_port),
)
last_failure = 'unobserved'
for attempt in range(1, attempts + 1):
    pending = None
    for name, url in http_targets:
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status >= 400:
                    raise RuntimeError(f'HTTP {response.status}')
        except Exception as exc:
            pending = f'{name}: {exc}'
            break
    if pending is None:
        for name, port in tcp_targets:
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                    pass
            except OSError as exc:
                pending = f'{name}: {exc}'
                break
    if pending is None:
        print(f'QIKVRT_READINESS_GATE=READY attempts={attempt}')
        raise SystemExit(0)
    last_failure = pending
    if attempt < attempts:
        time.sleep(0.5)
raise SystemExit(f'BLOCK: bounded runtime readiness failed after {attempts} attempts: {last_failure}')
PY

mark() { printf 'QIKVRT_HEALTH_PROBE=%s\n' "$1"; }

mark effect_ack_direct
curl -fsS "http://127.0.0.1:${HTTP_PORT}/.well-known/effect-ack" >/tmp/qikvrt-health-effect.json
mark novnc_direct
curl -fsS "http://127.0.0.1:${NOVNC_PORT}/vnc.html" >/dev/null
mark proxy_terminal
curl -fsS "http://127.0.0.1:${PROXY_PORT}/terminal/vnc.html" >/dev/null
mark proxy_effect_ack
curl -fsS "http://127.0.0.1:${PROXY_PORT}/effect-ack/.well-known/effect-ack" >/tmp/qikvrt-health-effect-proxy.json
mark proxy_runtime_receipt
curl -fsS "http://127.0.0.1:${PROXY_PORT}/.well-known/qikvrt-cloud-transputer" >/tmp/qikvrt-health-runtime.json
mark firefox_process
pgrep -af 'firefox|firefox-esr' >/dev/null

mark smtp
python3 -B - "$SMTP_PORT" <<'PY'
import socket,sys
port=int(sys.argv[1])
with socket.create_connection(('127.0.0.1',port),timeout=3) as sock:
    banner=sock.recv(4096)
    if not banner.startswith(b'220 '): raise SystemExit('bad SMTP banner')
    sock.sendall(b'EHLO health.qikvrt\r\n')
    data=sock.recv(4096)
    if b'250' not in data: raise SystemExit('bad SMTP EHLO')
    sock.sendall(b'QUIT\r\n')
PY

mark dns
dig +time=2 +tries=1 @127.0.0.1 -p "$DNS_PORT" "$MESH_DOMAIN" A | grep -Eq '[[:space:]]A[[:space:]]+127\.0\.0\.1'
mark ssh
ssh-keyscan -T 3 -p "$SSH_PORT" 127.0.0.1 2>/dev/null | grep -q 'ssh-ed25519'

mark snmp
SNMP_COMMUNITY=qikvrt-local
if [ -n "${QIKVRT_SNMP_COMMUNITY_FILE:-}" ]; then
  SNMP_COMMUNITY="$(cat "$QIKVRT_SNMP_COMMUNITY_FILE")"
fi
snmpget -v2c -c "$SNMP_COMMUNITY" -t 2 -r 0 "127.0.0.1:${SNMP_PORT}" 1.3.6.1.2.1.1.1.0 >/dev/null

mark postgresql_discovery
PG_SERVER="$(find /usr/lib/postgresql -type f -path '*/bin/postgres' -print | sort -V | tail -n 1)"
test -n "$PG_SERVER"
PG_BIN="$(dirname "$PG_SERVER")"
test -x "$PG_BIN/pg_isready"
test -x "$PG_BIN/psql"
mark postgresql_tcp
"$PG_BIN/pg_isready" -h 127.0.0.1 -p "$SQL_PORT" -d qikvrt -U qikvrt >/dev/null
mark sql92
SQL92_VALUE="$(su -s /bin/sh postgres -c "'$PG_BIN/psql' -p '$SQL_PORT' -U qikvrt -d qikvrt -Atqc 'SELECT 20 + 22'")"
test "$SQL92_VALUE" = 42

mark m68000_file
file "$STATE_DIR/m68k/qikvrt-effect-ack-probe" | grep -Eqi '68000|m68k|Motorola'
mark m68000_execution
grep -q '^ARCH=M68000_FAMILY$' "$STATE_DIR/m68k/execution.txt"
grep -q '^EFFECT_ACK_STATE=EFFECT_ACK_DONE$' "$STATE_DIR/m68k/execution.txt"

mark authority_mirror
test -f "$STATE_DIR/authority-mirror.json"
mark exact_runtime_receipts
python3 -B - "$STATE_DIR/authority-mirror.json" "$RUN_STATE" "$MESH_PUBLIC_URL" /tmp/qikvrt-health-effect.json /tmp/qikvrt-health-effect-proxy.json /tmp/qikvrt-health-runtime.json <<'PY'
import json,sys
mirror_path,runtime_path,expected_url,effect_path,effect_proxy_path,proxy_runtime_path=sys.argv[1:]
mirror=json.load(open(mirror_path,encoding='utf-8'))
assert mirror['schema']=='qikvrt_cloud_transputer_authority_mirror_receipt_v1'
assert mirror['authority_repository']=='Goldkelch/qik-vrt'
assert mirror['origin']=='https://github.com/Goldkelch/qik-vrt.git'
assert len(mirror['main_head_sha'])==40 and len(mirror['main_tree_sha'])==40
assert mirror['polling'] is False
assert mirror['writeback_to_authority'] is False
runtime=json.load(open(runtime_path,encoding='utf-8'))
assert runtime['schema']=='qikvrt_cloud_transputer_runtime_v1'
assert runtime['mesh_public_url']==expected_url
assert runtime['profile_persistent'] is True
assert runtime['m68000_effect_ack_probe_executed'] is True
assert runtime['standalone_m68000_tcp_ip_stack_claimed'] is False
assert runtime['kernel_backed_posix_tcp_ip'] is True
assert runtime['external_effect_claimed'] is False
assert runtime['pass'] is False and runtime['final_pass'] is False and runtime['effect_ack_done'] is False
effect=json.load(open(effect_path,encoding='utf-8'))
effect_proxy=json.load(open(effect_proxy_path,encoding='utf-8'))
assert effect==effect_proxy
assert effect['schema']=='qikvrt_effect_ack_http_capability_v1'
assert effect['modes']==['prepare','commit']
proxy_runtime=json.load(open(proxy_runtime_path,encoding='utf-8'))
assert proxy_runtime==runtime
PY
mark complete
