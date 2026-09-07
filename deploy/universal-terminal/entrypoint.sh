#!/bin/sh
set -eu

PROFILE_DIR="${QIKVRT_PROFILE_DIR:-/var/lib/qikvrt/profile}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
RUNTIME_ID="${QIKVRT_RUNTIME_ID:-qikvrt-firefox-terminal}"
HTTP_HOST="${QIKVRT_HTTP_HOST:-127.0.0.1}"
HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
DISPLAY_VALUE="${DISPLAY:-:99}"
START_URL="${QIKVRT_START_URL:-http://qikvrt-gateway:8080/qik-vrt/mesh/v1/}"

mkdir -p /opt/qikvrt/runtime/logs "$PROFILE_DIR" "$STATE_DIR"

PIDS=""
cleanup() {
  # Only PIDs collected from our own children, never a pattern-based kill.
  for pid in $PIDS; do kill "$pid" 2>/dev/null || true; done
}
diagnostics() {
  for log in /opt/qikvrt/runtime/logs/*.log; do
    [ -f "$log" ] || continue
    printf '\n--- %s ---\n' "$log" >&2
    tail -n 80 "$log" >&2
  done
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

test -s /usr/share/novnc/vnc.html
test -s /usr/share/novnc/core/rfb.js

if [ ! -f "$PROFILE_DIR/.qikvrt-profile-initialized" ]; then
  cp -a /opt/qikvrt/runtime/bootstrap-profile/. "$PROFILE_DIR/"
  : > "$PROFILE_DIR/.qikvrt-profile-initialized"
fi

python3 -B /opt/qikvrt/src/qikvrt_effect_ack_http_terminal.py \
  --host "$HTTP_HOST" --port "$HTTP_PORT" \
  > /opt/qikvrt/runtime/logs/effect-ack-http.log 2>&1 &
HTTP_PID=$!
PIDS="$PIDS ${HTTP_PID}"

Xvfb "$DISPLAY_VALUE" -screen 0 1440x900x24 -nolisten tcp \
  > /opt/qikvrt/runtime/logs/xvfb.log 2>&1 &
XVFB_PID=$!
PIDS="$PIDS ${XVFB_PID}"

# A bounded readiness check, not a timing assumption about Xvfb startup.
attempt=0
until xdpyinfo -display "$DISPLAY_VALUE" >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if ! kill -0 "$XVFB_PID" 2>/dev/null || [ "$attempt" -ge 30 ]; then
    diagnostics
    echo "BLOCK: X display did not become ready" >&2
    exit 1
  fi
  sleep 1
done
VNC_ARGS="-display $DISPLAY_VALUE -forever -shared -localhost -rfbport 5900"
if [ -n "${QIKVRT_VNC_PASSWORD_FILE:-}" ]; then
  test -r "$QIKVRT_VNC_PASSWORD_FILE"
  VNC_PASSWORD="$(cat "$QIKVRT_VNC_PASSWORD_FILE")"
  test -n "$VNC_PASSWORD"
  x11vnc -storepasswd "$VNC_PASSWORD" /run/qikvrt-vnc.pass >/dev/null
  VNC_ARGS="$VNC_ARGS -rfbauth /run/qikvrt-vnc.pass"
else
  VNC_ARGS="$VNC_ARGS -nopw"
fi
# shellcheck disable=SC2086
x11vnc $VNC_ARGS > /opt/qikvrt/runtime/logs/x11vnc.log 2>&1 &
VNC_PID=$!
PIDS="$PIDS ${VNC_PID}"

websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:5900 \
  > /opt/qikvrt/runtime/logs/novnc.log 2>&1 &
NOVNC_PID=$!
PIDS="$PIDS ${NOVNC_PID}"

firefox-esr --no-remote --profile "$PROFILE_DIR" "$START_URL" \
  > /opt/qikvrt/runtime/logs/firefox.log 2>&1 &
FIREFOX_PID=$!
PIDS="$PIDS ${FIREFOX_PID}"

python3 -B - "$STATE_DIR/runtime.json" "$RUNTIME_ID" "$PROFILE_DIR" "$START_URL" "$NOVNC_PORT" "$HTTP_HOST" "$HTTP_PORT" <<'PY'
import json,sys,time
path,runtime_id,profile,start_url,novnc_port,http_host,http_port=sys.argv[1:]
obj={
  'schema':'qikvrt_universal_terminal_runtime_state_v2',
  'runtime_id':runtime_id,
  'browser':'firefox-esr',
  'profile_dir':profile,
  'profile_persistent':True,
  'start_url':start_url,
  'novnc_port':int(novnc_port),
  'effect_ack_host':http_host,
  'effect_ack_port':int(http_port),
  'mesh_path':'/qik-vrt/mesh/v1/',
  'started_at_unix':int(time.time()),
  'authenticated_session_storage':'FIREFOX_PROFILE',
  'adapter':'QIKVRT_FIREFOX_TERMINAL_PROXY_V2',
  'external_effect_claimed':False,
  'pass':False,
  'final_pass':False,
  'effect_ack_done':False,
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
PY

attempt=0
until /usr/local/bin/qikvrt-runtime-health >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  for pid in $PIDS; do
    if ! kill -0 "$pid" 2>/dev/null; then
      diagnostics
      echo "BLOCK: required terminal child exited during startup" >&2
      exit 1
    fi
  done
  if [ "$attempt" -ge 30 ]; then
    diagnostics
    echo "BLOCK: terminal health contract did not become ready" >&2
    exit 1
  fi
  sleep 1
done

printf '%s\n' "QIKVRT universal terminal ready: runtime=${RUNTIME_ID} noVNC=0.0.0.0:${NOVNC_PORT} effect_ack=${HTTP_HOST}:${HTTP_PORT} profile=${PROFILE_DIR}"

while :; do
  for pid in $PIDS; do
    if ! kill -0 "$pid" 2>/dev/null; then
      diagnostics
      echo "BLOCK: required terminal child exited" >&2
      exit 1
    fi
  done
  sleep 1
done
