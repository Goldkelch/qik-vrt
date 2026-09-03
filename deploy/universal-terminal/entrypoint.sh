#!/bin/sh
set -eu

mkdir -p /opt/qikvrt/runtime/logs /opt/qikvrt/runtime/profile

python3 -B /opt/qikvrt/src/qikvrt_effect_ack_http_terminal.py \
  --host 127.0.0.1 --port "${QIKVRT_HTTP_PORT:-8771}" \
  > /opt/qikvrt/runtime/logs/effect-ack-http.log 2>&1 &
HTTP_PID=$!

Xvfb "${DISPLAY:-:99}" -screen 0 1440x900x24 -nolisten tcp \
  > /opt/qikvrt/runtime/logs/xvfb.log 2>&1 &
XVFB_PID=$!

sleep 1
x11vnc -display "${DISPLAY:-:99}" -forever -shared -nopw -localhost -rfbport 5900 \
  > /opt/qikvrt/runtime/logs/x11vnc.log 2>&1 &
VNC_PID=$!

websockify --web=/usr/share/novnc/ "${QIKVRT_NOVNC_PORT:-6080}" localhost:5900 \
  > /opt/qikvrt/runtime/logs/novnc.log 2>&1 &
NOVNC_PID=$!

firefox-esr --no-remote --profile /opt/qikvrt/runtime/profile \
  "${QIKVRT_START_URL:-https://goldkelch.github.io/qik-vrt/}" \
  > /opt/qikvrt/runtime/logs/firefox.log 2>&1 &
FIREFOX_PID=$!

cleanup() {
  kill "$FIREFOX_PID" "$NOVNC_PID" "$VNC_PID" "$XVFB_PID" "$HTTP_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

printf '%s\n' "QIKVRT universal terminal ready: noVNC=0.0.0.0:${QIKVRT_NOVNC_PORT:-6080} effect_ack=127.0.0.1:${QIKVRT_HTTP_PORT:-8771}"

while kill -0 "$HTTP_PID" 2>/dev/null && kill -0 "$FIREFOX_PID" 2>/dev/null; do
  sleep 1
done

exit 1
