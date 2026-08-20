#!/bin/sh
set -eu

: "${EMUTOS_ROM_PATH:?EMUTOS_ROM_PATH is required}"
: "${EMUTOS_ROM_SHA256:?EMUTOS_ROM_SHA256 is required}"

test -f "$EMUTOS_ROM_PATH"
echo "$EMUTOS_ROM_SHA256  $EMUTOS_ROM_PATH" | sha256sum -c -
test -f /mlp/shared/MLP.TOS

rm -f /mlp/shared/MLP.OPEN /mlp/receipts/MLP.HOST

Xvfb :99 -screen 0 1280x800x24 >/mlp/receipts/xvfb.log 2>&1 &
XVFB_PID=$!
fluxbox >/mlp/receipts/fluxbox.log 2>&1 &
FLUX_PID=$!
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 >/mlp/receipts/x11vnc.log 2>&1 &
VNC_PID=$!

cleanup() {
  kill "$VNC_PID" "$FLUX_PID" "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

hatari \
  --machine megast \
  --cpulevel 0 \
  --cpuclock 8 \
  --compatible true \
  --cpu-exact true \
  --addr24 true \
  --fpu none \
  --mmu false \
  --memsize 1 \
  --tos "$EMUTOS_ROM_PATH" \
  --harddrive /mlp/shared \
  --gemdos-time host \
  --auto 'C:\\MLP.TOS' \
  >/mlp/receipts/hatari.log 2>&1 &
HATARI_PID=$!

while kill -0 "$HATARI_PID" 2>/dev/null; do
  if [ -f /mlp/shared/MLP.OPEN ]; then
    /usr/local/bin/qikvrt-mlp-host /mlp/shared/MLP.OPEN /mlp/receipts/MLP.HOST
    wait "$HATARI_PID" || true
    exit 0
  fi
  sleep 1
done

printf '%s\n' 'HOLD: Hatari exited before MLP.OPEN was observed' >&2
exit 5
