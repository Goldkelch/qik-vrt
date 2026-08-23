#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
export DISPLAY="${DISPLAY:-:99}"
export HOME="${HOME:-/home/qikvrt}"
export QIKVRT_STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/effect-ack}"
mkdir -p "$HOME/.mozilla" "$QIKVRT_STATE_DIR" /run/qikvrt
python3 /opt/qikvrt/effect_ack_gateway.py --host 127.0.0.1 --port 8771 --state-dir "$QIKVRT_STATE_DIR" > /run/qikvrt/effect-ack.log 2>&1 & GATEWAY_PID=$!
Xvfb "$DISPLAY" -screen 0 "${QIKVRT_SCREEN:-1280x800x24}" -nolisten tcp > /run/qikvrt/xvfb.log 2>&1 & XVFB_PID=$!
for _ in $(seq 1 100); do curl -fsS http://127.0.0.1:8771/healthz >/dev/null 2>&1 && break; sleep .1; done
openbox > /run/qikvrt/openbox.log 2>&1 & OPENBOX_PID=$!
PASSWORD="${QIKVRT_VNC_PASSWORD:-qikvrt}"
x11vnc -storepasswd "$PASSWORD" /run/qikvrt/vnc.pass >/dev/null
x11vnc -display "$DISPLAY" -rfbauth /run/qikvrt/vnc.pass -forever -shared -localhost > /run/qikvrt/x11vnc.log 2>&1 & VNC_PID=$!
NOVNC_PROXY="$(command -v novnc_proxy || true)"
[[ -n "$NOVNC_PROXY" ]] || NOVNC_PROXY=/usr/share/novnc/utils/novnc_proxy
"$NOVNC_PROXY" --listen 0.0.0.0:6080 --vnc localhost:5900 > /run/qikvrt/novnc.log 2>&1 & NOVNC_PID=$!
python3 /opt/qikvrt/launch_firefox.py > /run/qikvrt/firefox-launch.log 2>&1 & FIREFOX_PID=$!
for _ in $(seq 1 300); do
  [[ -s /run/qikvrt/firefox-session.json ]] && break
  kill -0 "$FIREFOX_PID" 2>/dev/null || break
  sleep .1
done
[[ -s /run/qikvrt/firefox-session.json ]] || { cat /run/qikvrt/firefox-launch.log >&2 || true; exit 2; }
cat <<EOF
QIKVRT_MESH_APPLIANCE_READY
NO_VNC=http://127.0.0.1:6080/vnc.html
VNC_PASSWORD=$PASSWORD
EFFECT_ACK=http://127.0.0.1:8771/.well-known/effect-ack
BROWSER_RECEIPT=/run/qikvrt/firefox-session.json
EXTERNAL_EFFECT=NONE
EOF
terminate(){ kill "$FIREFOX_PID" "$NOVNC_PID" "$VNC_PID" "$OPENBOX_PID" "$XVFB_PID" "$GATEWAY_PID" 2>/dev/null || true; wait || true; }
trap terminate INT TERM EXIT
wait "$FIREFOX_PID"
