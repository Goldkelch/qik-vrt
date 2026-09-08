#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -eu

STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
SQL_UI_PORT="${QIKVRT_SQL_UI_PORT:-8772}"
SQL_PORT="${QIKVRT_SQL_PORT:-5432}"
LOG_DIR=/opt/qikvrt/runtime/cloud-transputer-logs
RUN_DIR=/run/qikvrt
M68K_DIR="$STATE_DIR/m68k"
M68K_BINARY="$M68K_DIR/qikvrt-personal-posix-tcpip"
M68K_EXECUTION="$M68K_DIR/personal-posix-tcpip-execution.txt"
M68K_FILE="$M68K_DIR/personal-posix-tcpip-file.txt"
M68K_SHA="$M68K_DIR/personal-posix-tcpip-sha256.txt"
M68K_RECEIPT="$M68K_DIR/personal-posix-tcpip-receipt.json"
V2_READY="$RUN_DIR/v2-ready.txt"
V1_PID=
SQL_UI_PID=

cleanup() {
  if [ -n "${V1_PID:-}" ] && kill -0 "$V1_PID" 2>/dev/null; then
    kill -TERM "$V1_PID" 2>/dev/null || true
  fi
  if [ -n "${SQL_UI_PID:-}" ] && kill -0 "$SQL_UI_PID" 2>/dev/null; then
    kill -TERM "$SQL_UI_PID" 2>/dev/null || true
  fi
}
trap 'cleanup' INT TERM HUP EXIT

mkdir -p "$M68K_DIR" "$STATE_DIR/sql92/receipts" "$LOG_DIR" "$RUN_DIR"
rm -f "$V2_READY"

m68k-linux-gnu-gcc -std=c90 -pedantic -Wall -Wextra -Werror -static \
  -I/opt/qikvrt/include \
  /opt/qikvrt/src/effect_ack_core.c \
  /opt/qikvrt/src/cloud_transputer/personal_posix_tcpip.c \
  -o "$M68K_BINARY"
file "$M68K_BINARY" > "$M68K_FILE"
qemu-m68k "$M68K_BINARY" > "$M68K_EXECUTION"
grep -q '^ARCH=M68000_FAMILY$' "$M68K_EXECUTION"
grep -q '^PERSONAL_POSIX_PROFILE=QIKVRT_PERSONAL_POSIX_C90_V1$' "$M68K_EXECUTION"
grep -q '^PERSONAL_POSIX_SELFTEST=PASS$' "$M68K_EXECUTION"
grep -q '^STANDALONE_M68000_TCPIP_PACKET_ENGINE=PASS$' "$M68K_EXECUTION"
grep -q '^TCP_HANDSHAKE_SELFTEST=PASS$' "$M68K_EXECUTION"
grep -q '^TCP_HTTP_BOOTSTRAP_SELFTEST=PASS$' "$M68K_EXECUTION"
grep -q '^UDP_SELFTEST=PASS$' "$M68K_EXECUTION"
grep -q '^EFFECT_ACK_STATE=EFFECT_ACK_DONE$' "$M68K_EXECUTION"
grep -q '^EFFECT_ACK_NEGATIVE_STATE=EFFECT_ACK_CONTINUE$' "$M68K_EXECUTION"
grep -q '^EXTERNAL_PACKET_IO=LINUX_OCI_HOST_ADAPTER_REQUIRED$' "$M68K_EXECUTION"
grep -q '^BARE_METAL_NIC_DRIVER=NOT_CLAIMED$' "$M68K_EXECUTION"
grep -q '^FULL_POSIX_1_CONFORMANCE=NOT_CLAIMED$' "$M68K_EXECUTION"
sha256sum "$M68K_BINARY" > "$M68K_SHA"

python3 -B - "$M68K_RECEIPT" "$M68K_BINARY" "$M68K_EXECUTION" /opt/qikvrt/src/cloud_transputer/personal_posix_tcpip.c <<'PY'
import hashlib,json,os,sys,time
receipt_path,binary_path,execution_path,source_path=sys.argv[1:]
def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()
lines=[line.rstrip('\n') for line in open(execution_path,encoding='utf-8')]
value={
  'schema':'qikvrt_personal_posix_m68000_tcpip_receipt_v1',
  'profile':'QIKVRT_PERSONAL_POSIX_C90_V1',
  'source_sha256':digest(source_path),
  'm68000_binary_sha256':digest(binary_path),
  'm68000_machine_execution_observed':True,
  'execution_lines':lines,
  'posix_profile_selftest':'PASS',
  'standalone_tcp_ip_scope':'IPV4_TCP_UDP_PACKET_ENGINE_WITH_TCP_HTTP_BOOTSTRAP_V1',
  'standalone_tcp_ip_packet_engine':'PASS',
  'existing_effect_ack_core_linked':True,
  'effect_ack_done_local_selftest':True,
  'negative_effect_ack_fail_closed':True,
  'external_packet_io_adapter':'LINUX_OCI_HOST_ADAPTER',
  'bare_metal_nic_driver_claimed':False,
  'full_posix_1_conformance_claimed':False,
  'physical_m68000_execution_claimed':False,
  'repository_or_publication_effect_claimed':False,
  'observed_at_unix':int(time.time()),
  'pass':False,
  'final_pass':False,
  'global_effect_ack_done':False,
}
tmp=receipt_path+'.tmp'
with open(tmp,'w',encoding='utf-8',newline='\n') as handle:
    json.dump(value,handle,ensure_ascii=False,indent=2,sort_keys=True);handle.write('\n')
os.replace(tmp,receipt_path)
PY

python3 -B /opt/qikvrt/src/cloud_transputer/sql92_gateway.py \
  --host 127.0.0.1 --port "$SQL_UI_PORT" --pg-port "$SQL_PORT" --state-dir "$STATE_DIR" \
  > "$LOG_DIR/sql92-gateway.log" 2>&1 &
SQL_UI_PID=$!

sleep 1
kill -0 "$SQL_UI_PID" 2>/dev/null || {
  cat "$LOG_DIR/sql92-gateway.log" >&2 || true
  exit 40
}

# Preserve an explicit operator override; the stock image default still opens
# the local SQL/EFFECT_ACK control surface from inside Firefox.
if [ -z "${QIKVRT_START_URL:-}" ] || [ "${QIKVRT_START_URL}" = "https://goldkelch.github.io/qik-vrt/" ]; then
  export QIKVRT_START_URL="http://127.0.0.1:${SQL_UI_PORT}/"
fi

# The inherited V1 supervisor performs its own bounded health check.  During
# that one startup check the V2 public runtime overlay does not exist yet, so
# the health script is explicitly told that it is observing PRECOMPOSE state.
QIKVRT_V2_STARTUP_PRECOMPOSE=1 /usr/local/bin/qikvrt-cloud-transputer-v1 &
V1_PID=$!

ready=0
for attempt in $(seq 1 180); do
  if [ -s "$RUN_DIR/ready.txt" ] && [ -s "$RUN_DIR/runtime.json" ] && [ -s "$STATE_DIR/runtime.json" ]; then
    ready=1
    break
  fi
  if ! kill -0 "$V1_PID" 2>/dev/null; then
    set +e
    wait "$V1_PID"
    rc=$?
    set -e
    printf 'BLOCK: inherited cloud-transputer supervisor exited before V2 composition rc=%s\n' "$rc" >&2
    exit 41
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  printf '%s\n' 'BLOCK: inherited runtime did not reach bounded READY before V2 composition' >&2
  exit 42
fi

python3 -B /opt/qikvrt/src/cloud_transputer/runtime_v2_compose.py \
  --runtime "$RUN_DIR/runtime.json" \
  --m68k-receipt "$M68K_RECEIPT" \
  --output "$RUN_DIR/runtime.json" \
  --output "$STATE_DIR/runtime.json" \
  > "$LOG_DIR/runtime-v2-compose.json"

# Reobserve the composed, public runtime before advertising the stronger V2
# readiness marker.  This liveness check is deliberately non-effecting.
QIKVRT_VERIFY_SQL_EFFECT_ACK=0 /usr/local/bin/qikvrt-cloud-transputer-health \
  > "$LOG_DIR/v2-post-compose-health.log" 2>&1
printf '%s\n' 'QIKVRT_CLOUD_TRANSPUTER_V2_READY' > "$V2_READY"

set +e
wait "$V1_PID"
rc=$?
set -e
exit "$rc"
