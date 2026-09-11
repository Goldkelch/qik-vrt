#!/bin/sh
set -eu

PIDS=""
cleanup() {
  for pid in $PIDS; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in $PIDS; do
    wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

# A public cloud carrier is one container: keep the Effect-Ack reference
# backend and noVNC on loopback-facing process ports and expose only nginx
# on :8080. Firefox opens the canonical Mesh origin in this same namespace.
export QIKVRT_HTTP_HOST=127.0.0.1
export QIKVRT_START_URL="${QIKVRT_CLOUD_START_URL:-http://127.0.0.1:8080/qik-vrt/mesh/v1/}"

/usr/local/bin/qikvrt-universal-terminal &
TERMINAL_PID=$!
PIDS="$PIDS $TERMINAL_PID"

# nginx runs as Debian's unprivileged nobody account. Materialize every
# writable path as that account; do not add CAP_CHOWN or other capabilities.
runuser -u nobody -- mkdir -p \
  /tmp/nginx-client-body \
  /tmp/nginx-proxy \
  /tmp/nginx-fastcgi \
  /tmp/nginx-uwsgi \
  /tmp/nginx-scgi
runuser -u nobody -- nginx \
  -c /opt/qikvrt/deploy/universal-terminal/nginx.conf \
  -g 'daemon off;' &
GATEWAY_PID=$!
PIDS="$PIDS $GATEWAY_PID"

# Bounded startup contract: both children must stay alive and the canonical
# HTTP surface plus terminal health must become readable before READY.
attempt=0
while :; do
  kill -0 "$TERMINAL_PID" 2>/dev/null || {
    echo "BLOCK: cloud terminal child exited during startup" >&2
    exit 1
  }
  kill -0 "$GATEWAY_PID" 2>/dev/null || {
    echo "BLOCK: cloud gateway child exited during startup" >&2
    exit 1
  }
  if /usr/local/bin/qikvrt-runtime-health >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:8080/qik-vrt/mesh/v1/healthz >/dev/null \
    && curl -fsS http://127.0.0.1:8080/qik-vrt/mesh/v1/ >/dev/null; then
    break
  fi
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    echo "BLOCK: cloud Mesh surface did not become ready" >&2
    exit 1
  fi
  sleep 1
done

printf '%s\n' "QIKVRT cloud universal terminal ready: mesh=0.0.0.0:8080/qik-vrt/mesh/v1/"

while :; do
  kill -0 "$TERMINAL_PID" 2>/dev/null || {
    echo "BLOCK: cloud terminal child exited" >&2
    exit 1
  }
  kill -0 "$GATEWAY_PID" 2>/dev/null || {
    echo "BLOCK: cloud gateway child exited" >&2
    exit 1
  }
  sleep 1
done
