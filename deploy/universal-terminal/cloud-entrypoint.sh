#!/bin/sh
set -eu

PIDS=""
MANDATORY=""

register_pid() {
  name="$1"
  pid="$2"
  PIDS="$PIDS $pid"
  MANDATORY="$MANDATORY $name:$pid"
}

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

emit_health() {
  state="$1"
  tmp=/tmp/qikvrt-mesh-health.json.tmp
  commit="${RAILWAY_GIT_COMMIT_SHA:-${QIKVRT_EXACT_HEAD:-unknown}}"
  cat > "$tmp" <<EOF
{"schema":"qikvrt_cloud_transputer_mesh_health_v1","state":"$state","commit":"$commit","roles":{"terminal":"READY","gateway":"READY","m68k":"READY","smtp":"READY","dns":"READY","snmp":"READY"},"optional":{"ssh":"${SSH_STATE:-DISABLED}","sql":"${SQL_STATE:-DISABLED}","mirror":"${MIRROR_STATE:-DISABLED}"},"effect_ack":"NOT_IMPLIED"}
EOF
  mv "$tmp" /tmp/qikvrt-mesh-health.json
  chmod 0644 /tmp/qikvrt-mesh-health.json
}

# Public cloud materialization: one OCI carrier, many bounded Mesh roles.
# Railway exposes only nginx :8080. The remaining roles communicate inside
# the container namespace; Compose remains the fixed-IP multi-container form.
export QIKVRT_HTTP_HOST=127.0.0.1
export QIKVRT_START_URL="${QIKVRT_CLOUD_START_URL:-http://127.0.0.1:8080/qik-vrt/mesh/v1/}"

/usr/local/bin/qikvrt-universal-terminal &
TERMINAL_PID=$!
register_pid terminal "$TERMINAL_PID"

QIKVRT_SERVICE_MODE=m68k /usr/local/bin/qikvrt-service-entrypoint &
M68K_PID=$!
register_pid m68k "$M68K_PID"

QIKVRT_SERVICE_MODE=smtpd QIKVRT_SMTP_PORT=2525 /usr/local/bin/qikvrt-service-entrypoint &
SMTP_PID=$!
register_pid smtp "$SMTP_PID"

QIKVRT_SERVICE_MODE=dnsd QIKVRT_DNS_PORT=5353 /usr/local/bin/qikvrt-service-entrypoint &
DNS_PID=$!
register_pid dns "$DNS_PID"

QIKVRT_SERVICE_MODE=snmpd /usr/local/bin/qikvrt-service-entrypoint &
SNMP_PID=$!
register_pid snmp "$SNMP_PID"

SSH_STATE=DISABLED
if [ "${QIKVRT_CLOUD_ENABLE_SSH:-0}" = 1 ]; then
  QIKVRT_SERVICE_MODE=sshd /usr/local/bin/qikvrt-service-entrypoint &
  SSH_PID=$!
  PIDS="$PIDS $SSH_PID"
  MANDATORY="$MANDATORY ssh:$SSH_PID"
  SSH_STATE=READY
fi

SQL_STATE=DISABLED
if [ -n "${QIKVRT_DB_PASSWORD:-}" ]; then
  QIKVRT_SERVICE_MODE=sqld /usr/local/bin/qikvrt-service-entrypoint &
  SQL_PID=$!
  PIDS="$PIDS $SQL_PID"
  MANDATORY="$MANDATORY sql:$SQL_PID"
  SQL_STATE=READY
fi

MIRROR_STATE=DISABLED
if [ "${QIKVRT_CLOUD_ENABLE_MIRROR:-0}" = 1 ]; then
  QIKVRT_SERVICE_MODE=mirror /usr/local/bin/qikvrt-service-entrypoint &
  MIRROR_PID=$!
  PIDS="$PIDS $MIRROR_PID"
  MANDATORY="$MANDATORY mirror:$MIRROR_PID"
  MIRROR_STATE=READY
fi

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
register_pid gateway "$GATEWAY_PID"

emit_health STARTING

attempt=0
while :; do
  failed=""
  for item in $MANDATORY; do
    name=${item%%:*}
    pid=${item#*:}
    if ! kill -0 "$pid" 2>/dev/null; then
      failed="$name"
      break
    fi
  done
  if [ -n "$failed" ]; then
    echo "BLOCK: cloud Mesh role exited during startup: $failed" >&2
    exit 1
  fi
  if /usr/local/bin/qikvrt-runtime-health >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:8080/qik-vrt/mesh/v1/ >/dev/null; then
    emit_health READY
    curl -fsS http://127.0.0.1:8080/qik-vrt/mesh/v1/healthz >/dev/null
    break
  fi
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    echo "BLOCK: cloud Transputer Mesh did not become ready" >&2
    exit 1
  fi
  sleep 1
done

printf '%s\n' "QIKVRT cloud Transputer Mesh ready: terminal+gateway+m68k+smtp+dns+snmp"
printf '%s\n' "QIKVRT Mesh health: http://0.0.0.0:8080/qik-vrt/mesh/v1/healthz"

while :; do
  for item in $MANDATORY; do
    name=${item%%:*}
    pid=${item#*:}
    if ! kill -0 "$pid" 2>/dev/null; then
      emit_health BLOCKED
      echo "BLOCK: cloud Mesh role exited: $name" >&2
      exit 1
    fi
  done
  sleep 2
done
