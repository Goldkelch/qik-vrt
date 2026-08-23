#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -eu

QIKVRT_HOME=${QIKVRT_HOME:-/var/lib/qikvrt}
PROFILE=${QIKVRT_FIREFOX_PROFILE:-$QIKVRT_HOME/firefox-profile}
DISPLAY=${DISPLAY:-:99}
export QIKVRT_HOME PROFILE DISPLAY
mkdir -p "$PROFILE/extensions" "$QIKVRT_HOME/receipts" "$HOME/.vnc"
cp /opt/qikvrt/qikvrt-terminal.xpi "$PROFILE/extensions/qikvrt-ai-terminal@goldkelch.local.xpi"
cat > "$PROFILE/user.js" <<'EOF'
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.tabs.warnOnClose", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("extensions.autoDisableScopes", 0);
user_pref("extensions.enabledScopes", 15);
user_pref("xpinstall.signatures.required", false);
EOF

pids=""
cleanup() {
  for pid in $pids; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

start_backend() {
  python3 /opt/qikvrt/src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771 >"$QIKVRT_HOME/backend.log" 2>&1 &
  pids="$pids $!"
  i=0
  until python3 /opt/qikvrt/appliance/protocol_probe.py --health-only >/dev/null 2>&1; do
    i=$((i + 1))
    [ "$i" -lt 60 ] || { cat "$QIKVRT_HOME/backend.log" >&2; exit 2; }
    sleep 0.25
  done
}

start_display() {
  Xvfb "$DISPLAY" -screen 0 1280x800x24 -nolisten tcp >"$QIKVRT_HOME/xvfb.log" 2>&1 &
  pids="$pids $!"
  i=0
  while [ ! -e "/tmp/.X11-unix/X${DISPLAY#:}" ]; do
    i=$((i + 1))
    [ "$i" -lt 60 ] || { cat "$QIKVRT_HOME/xvfb.log" >&2; exit 2; }
    sleep 0.25
  done
  openbox-session >"$QIKVRT_HOME/openbox.log" 2>&1 &
  pids="$pids $!"
}

start_firefox() {
  firefox-esr --no-remote --new-instance --profile "$PROFILE" about:blank >"$QIKVRT_HOME/firefox.log" 2>&1 &
  pids="$pids $!"
}

case "${1:-serve}" in
  backend)
    exec python3 /opt/qikvrt/src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771
    ;;
  protocol-smoke)
    start_backend
    python3 /opt/qikvrt/appliance/protocol_probe.py --output "$QIKVRT_HOME/receipts/protocol.json"
    ;;
  smoke)
    start_backend
    start_display
    start_firefox
    python3 /opt/qikvrt/appliance/firefox_probe.py --profile "$PROFILE" --output "$QIKVRT_HOME/receipts/firefox.json"
    ;;
  serve)
    start_backend
    start_display
    start_firefox
    x11vnc -display "$DISPLAY" -forever -shared -nopw -rfbport 5900 >"$QIKVRT_HOME/x11vnc.log" 2>&1 &
    pids="$pids $!"
    websockify --web=/usr/share/novnc/ 6080 127.0.0.1:5900 >"$QIKVRT_HOME/novnc.log" 2>&1 &
    pids="$pids $!"
    wait
    ;;
  *)
    echo "usage: qikvrt-appliance {serve|smoke|protocol-smoke|backend}" >&2
    exit 2
    ;;
esac
