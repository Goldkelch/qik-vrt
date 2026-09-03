#!/bin/sh
set -eu

PROFILE_DIR="${QIKVRT_PROFILE_DIR:-/var/lib/qikvrt/profile}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
RUNTIME_ID="${QIKVRT_RUNTIME_ID:-qikvrt-firefox-terminal}"
HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
DISPLAY_VALUE="${DISPLAY:-:99}"
START_URL="${QIKVRT_START_URL:-https://arxiv.org/}"

mkdir -p /opt/qikvrt/runtime/logs "$PROFILE_DIR" "$STATE_DIR"

if [ ! -f "$PROFILE_DIR/.qikvrt-profile-initialized" ]; then
  cp -a /opt/qikvrt/runtime/bootstrap-profile/. "$PROFILE_DIR/"
  : > "$PROFILE_DIR/.qikvrt-profile-initialized"
fi

python3 -B /opt/qikvrt/src/qikvrt_effect_ack_http_terminal.py \
  --host 127.0.0.1 --port "$HTTP_PORT" \
  > /opt/qikvrt/runtime/logs/effect-ack-http.log 2>&1 &
HTTP_PID=$!

Xvfb "$DISPLAY_VALUE" -screen 0 1440x900x24 -nolisten tcp \
  > /opt/qikvrt/runtime/logs/xvfb.log 2>&1 &
XVFB_PID=$!

sleep 1
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

websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:5900 \
  > /opt/qikvrt/runtime/logs/novnc.log 2>&1 &
NOVNC_PID=$!

firefox-esr --no-remote --profile "$PROFILE_DIR" "$START_URL" \
  > /opt/qikvrt/runtime/logs/firefox.log 2>&1 &
FIREFOX_PID=$!

python3 -B - "$STATE_DIR/runtime.json" "$RUNTIME_ID" "$PROFILE_DIR" "$START_URL" "$NOVNC_PORT" <<'PY'
import json,sys,time
path,runtime_id,profile,start_url,novnc_port=sys.argv[1:]
obj={
  'schema':'qikvrt_universal_terminal_runtime_state_v1',
  'runtime_id':runtime_id,
  'browser':'firefox-esr',
  'profile_dir':profile,
  'profile_persistent':True,
  'start_url':start_url,
  'novnc_port':int(novnc_port),
  'started_at_unix':int(time.time()),
  'authenticated_session_storage':'FIREFOX_PROFILE',
  'adapter':'QIKVRT_FIREFOX_TERMINAL_PROXY_V1',
  'external_effect_claimed':False,
  'pass':False,
  'final_pass':False,
  'effect_ack_done':False,
}
open(path,'w',encoding='utf-8').write(json.dumps(obj,indent=2,sort_keys=True)+'\n')
PY

cleanup() {
  kill "$FIREFOX_PID" "$NOVNC_PID" "$VNC_PID" "$XVFB_PID" "$HTTP_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

printf '%s\n' "QIKVRT universal terminal ready: runtime=${RUNTIME_ID} noVNC=0.0.0.0:${NOVNC_PORT} effect_ack=127.0.0.1:${HTTP_PORT} profile=${PROFILE_DIR}"

while kill -0 "$HTTP_PID" 2>/dev/null && kill -0 "$FIREFOX_PID" 2>/dev/null && kill -0 "$NOVNC_PID" 2>/dev/null; do
  sleep 1
done

exit 1
