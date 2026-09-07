#!/bin/sh
set -eu

PROFILE_DIR="${QIKVRT_PROFILE_DIR:-/var/lib/qikvrt/profile}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
RUNTIME_ID="${QIKVRT_RUNTIME_ID:-qikvrt-cloud-transputer-v1}"
HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
PROXY_PORT="${QIKVRT_PROXY_PORT:-${PORT:-8080}}"
PROXY_HOST="${QIKVRT_PROXY_HOST:-127.0.0.1}"
SMTP_PORT="${QIKVRT_SMTP_PORT:-1025}"
DNS_PORT="${QIKVRT_DNS_PORT:-1053}"
SNMP_PORT="${QIKVRT_SNMP_PORT:-1161}"
SSH_PORT="${QIKVRT_SSH_PORT:-2222}"
PGPORT="${QIKVRT_POSTGRES_PORT:-5432}"
GIT_PORT="${QIKVRT_GIT_MIRROR_PORT:-9418}"
DISPLAY_VALUE="${DISPLAY:-:99}"
START_URL="${QIKVRT_START_URL:-https://github.com/Goldkelch/qik-vrt}"
SUBJECT_SHA="${QIKVRT_EXACT_SUBJECT_SHA:-${RAILWAY_GIT_COMMIT_SHA:-${QIKVRT_IMAGE_SUBJECT_SHA:-UNBOUND}}}"
QIKVRT_HOME="$STATE_DIR/home"
PGDATA="$STATE_DIR/postgres"
PGSOCKET="/tmp/qikvrt-postgres"
SSH_DIR="$STATE_DIR/ssh"
MIRROR_DIR="$STATE_DIR/repository-mirror.git"
MIRROR_OBSERVATION="$STATE_DIR/repository-mirror.json"
LOG_DIR="/tmp/qikvrt-logs"

# All services run as the dedicated unprivileged image user.  The deployment
# platform must present writable state/profile mounts to this uid; no runtime
# privilege-escalation/bootstrap path is permitted.
if [ "$(id -u)" != 10001 ]; then
  echo "BLOCK: terminal runtime must execute as uid 10001" >&2
  exit 2
fi

mkdir -p \
  "$LOG_DIR" "$PROFILE_DIR" "$STATE_DIR" "$QIKVRT_HOME/.ssh" \
  "$PGDATA" "$PGSOCKET" "$SSH_DIR" "$STATE_DIR/mail"
test -w "$PROFILE_DIR"
test -w "$STATE_DIR"

if [ ! -f "$PROFILE_DIR/.qikvrt-profile-initialized" ]; then
  cp -a /opt/qikvrt/assets/bootstrap-profile/. "$PROFILE_DIR/"
  : > "$PROFILE_DIR/.qikvrt-profile-initialized"
fi

if ! printf '%s' "$SUBJECT_SHA" | grep -Eq '^[0-9a-f]{40}$'; then
  echo "BLOCK: exact subject SHA unavailable" >&2
  exit 2
fi

python3 -B /opt/qikvrt/src/qikvrt_effect_ack_http_terminal.py \
  --host 127.0.0.1 --port "$HTTP_PORT" >"$LOG_DIR/effect-ack-http.log" 2>&1 &
HTTP_PID=$!

Xvfb "$DISPLAY_VALUE" -screen 0 1440x900x24 -nolisten tcp >"$LOG_DIR/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1
openbox >"$LOG_DIR/openbox.log" 2>&1 &
OPENBOX_PID=$!
xterm -geometry 112x30+20+520 -title "QIK-VRT POSIX terminal" \
  -e /bin/sh -lc 'printf "QIK-VRT POSIX terminal\nD0: 0=NOOP 1=HOLD 2=REOBSERVE 3=REQUEST_AUTHORITY\n"; exec /bin/sh' \
  >"$LOG_DIR/xterm.log" 2>&1 &
XTERM_PID=$!

VNC_ARGS="-display $DISPLAY_VALUE -forever -shared -localhost -rfbport 5900"
if [ -n "${QIKVRT_VNC_PASSWORD_FILE:-}" ]; then
  test -r "$QIKVRT_VNC_PASSWORD_FILE"
  VNC_PASSWORD="$(cat "$QIKVRT_VNC_PASSWORD_FILE")"
  test -n "$VNC_PASSWORD"
  x11vnc -storepasswd "$VNC_PASSWORD" /tmp/qikvrt-vnc.pass >/dev/null
  VNC_ARGS="$VNC_ARGS -rfbauth /tmp/qikvrt-vnc.pass"
else
  VNC_ARGS="$VNC_ARGS -nopw"
fi
# shellcheck disable=SC2086
x11vnc $VNC_ARGS >"$LOG_DIR/x11vnc.log" 2>&1 &
VNC_PID=$!

websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:5900 >"$LOG_DIR/novnc.log" 2>&1 &
NOVNC_PID=$!

python3 -B /opt/qikvrt/src/qikvrt_universal_service_plane.py \
  --state-dir "$STATE_DIR" >"$LOG_DIR/service-plane.log" 2>&1 &
SERVICE_PID=$!

PG_BINDIR="/usr/lib/postgresql/15/bin"
test -x "$PG_BINDIR/initdb"
test -x "$PG_BINDIR/postgres"
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  "$PG_BINDIR/initdb" -D "$PGDATA" \
    --encoding=UTF8 --auth-local=trust --auth-host=trust --no-locale \
    >"$LOG_DIR/postgres-init.log" 2>&1
fi
"$PG_BINDIR/postgres" -D "$PGDATA" \
  -c "listen_addresses=127.0.0.1" \
  -c "port=$PGPORT" \
  -c "unix_socket_directories=$PGSOCKET" \
  -c "max_connections=32" \
  >"$LOG_DIR/postgres.log" 2>&1 &
POSTGRES_PID=$!

i=0
while ! pg_isready -q -h 127.0.0.1 -p "$PGPORT"; do
  i=$((i + 1))
  if [ "$i" -ge 45 ]; then
    echo "BLOCK: PostgreSQL did not become ready" >&2
    exit 1
  fi
  sleep 1
done

psql -X -q -h 127.0.0.1 -p "$PGPORT" -d postgres -v ON_ERROR_STOP=1 <<'SQL'
DO $qikvrt$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qikvrt_terminal') THEN
    CREATE ROLE qikvrt_terminal LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
  END IF;
END
$qikvrt$;
SELECT 'CREATE DATABASE qikvrt_terminal OWNER qikvrt_terminal'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'qikvrt_terminal')\gexec
ALTER DATABASE qikvrt_terminal OWNER TO qikvrt_terminal;
REVOKE TEMPORARY ON DATABASE qikvrt_terminal FROM PUBLIC;
SQL
psql -X -q -h 127.0.0.1 -p "$PGPORT" -d qikvrt_terminal -v ON_ERROR_STOP=1 <<'SQL'
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO qikvrt_terminal;
SQL

HOST_KEY="$SSH_DIR/dropbear_ed25519_host_key"
CLIENT_KEY="$SSH_DIR/qikvrt_local_client_ed25519"
AUTHORIZED_KEYS="$QIKVRT_HOME/.ssh/authorized_keys"
if [ ! -s "$HOST_KEY" ]; then
  dropbearkey -t ed25519 -f "$HOST_KEY" >"$LOG_DIR/dropbear-host-key.log" 2>&1
fi
if [ ! -s "$CLIENT_KEY" ]; then
  dropbearkey -t ed25519 -f "$CLIENT_KEY" >"$LOG_DIR/dropbear-client-key.log" 2>&1
fi
umask 077
dropbearkey -y -f "$CLIENT_KEY" | awk '/^ssh-ed25519 /{print; exit}' >"$AUTHORIZED_KEYS"
if [ -n "${QIKVRT_SSH_AUTHORIZED_KEYS:-}" ]; then
  printf '%s\n' "$QIKVRT_SSH_AUTHORIZED_KEYS" >>"$AUTHORIZED_KEYS"
fi
chmod 700 "$QIKVRT_HOME/.ssh"
chmod 600 "$AUTHORIZED_KEYS" "$CLIENT_KEY" "$HOST_KEY"

dropbear -F -E -s -w -j -k -P /tmp/qikvrt-dropbear.pid \
  -p "127.0.0.1:$SSH_PORT" -r "$HOST_KEY" >"$LOG_DIR/dropbear.log" 2>&1 &
SSH_PID=$!

if [ ! -d "$MIRROR_DIR" ]; then
  git init --bare "$MIRROR_DIR" >/dev/null
fi
if git --git-dir="$MIRROR_DIR" remote get-url authority >/dev/null 2>&1; then
  git --git-dir="$MIRROR_DIR" remote set-url authority https://github.com/Goldkelch/qik-vrt.git
else
  git --git-dir="$MIRROR_DIR" remote add authority https://github.com/Goldkelch/qik-vrt.git
fi
if git --git-dir="$MIRROR_DIR" remote get-url mirror >/dev/null 2>&1; then
  git --git-dir="$MIRROR_DIR" remote set-url mirror https://github.com/ingolf-lohmann/qik-vrt.git
else
  git --git-dir="$MIRROR_DIR" remote add mirror https://github.com/ingolf-lohmann/qik-vrt.git
fi
git --git-dir="$MIRROR_DIR" fetch --no-tags --depth=1 authority "$SUBJECT_SHA" \
  >"$LOG_DIR/git-mirror-authority.log" 2>&1
git --git-dir="$MIRROR_DIR" update-ref refs/heads/candidate FETCH_HEAD
git --git-dir="$MIRROR_DIR" symbolic-ref HEAD refs/heads/candidate
git --git-dir="$MIRROR_DIR" fetch --no-tags --depth=1 authority \
  main:refs/remotes/authority/main >>"$LOG_DIR/git-mirror-authority.log" 2>&1 || true
git --git-dir="$MIRROR_DIR" fetch --no-tags --depth=1 mirror \
  main:refs/remotes/mirror/main >"$LOG_DIR/git-mirror-external.log" 2>&1 || true
git daemon --reuseaddr --export-all --base-path="$STATE_DIR" \
  --listen=127.0.0.1 --port="$GIT_PORT" "$MIRROR_DIR" >"$LOG_DIR/git-daemon.log" 2>&1 &
GIT_PID=$!

python3 -B /opt/qikvrt/src/qikvrt_cloud_mirror_observer.py \
  --output "$MIRROR_OBSERVATION" \
  --interval "${QIKVRT_MIRROR_REOBSERVE_SECONDS:-900}" >"$LOG_DIR/authority-mirror.log" 2>&1 &
MIRROR_PID=$!

env \
  QIKVRT_STATE_DIR="$STATE_DIR" \
  QIKVRT_PROXY_HOST="$PROXY_HOST" \
  QIKVRT_PROXY_PORT="$PROXY_PORT" \
  QIKVRT_HTTP_PORT="$HTTP_PORT" \
  QIKVRT_NOVNC_PORT="$NOVNC_PORT" \
  QIKVRT_POSTGRES_PORT="$PGPORT" \
  QIKVRT_PROXY_USERNAME="${QIKVRT_PROXY_USERNAME:-qikvrt}" \
  QIKVRT_PROXY_PASSWORD="${QIKVRT_PROXY_PASSWORD:-}" \
  QIKVRT_PROXY_PASSWORD_FILE="${QIKVRT_PROXY_PASSWORD_FILE:-}" \
  python3 -B /opt/qikvrt/src/qikvrt_terminal_proxy_httpd.py >"$LOG_DIR/terminal-proxy.log" 2>&1 &
PROXY_PID=$!

firefox-esr --no-remote --profile "$PROFILE_DIR" "$START_URL" >"$LOG_DIR/firefox.log" 2>&1 &
FIREFOX_PID=$!

python3 -B - \
  "$STATE_DIR/services.json" "$SUBJECT_SHA" "$PROXY_HOST" "$PROXY_PORT" \
  "$SMTP_PORT" "$DNS_PORT" "$SNMP_PORT" "$SSH_PORT" "$PGPORT" "$GIT_PORT" <<'PY'
import hashlib,json,pathlib,sys
path,subject,proxy_host,proxy_port,smtp,dns,snmp,ssh,postgres,git_port=sys.argv[1:]
binary=pathlib.Path('/opt/qikvrt/assets/m68000/qikvrt_terminal_bootstrap.bin')
obj={
  'schema':'qikvrt_cloud_transputer_services_v1',
  'subject_head_sha':subject,
  'services':{
    'httpd_proxy':{'bind':proxy_host,'port':int(proxy_port),'authentication':'BASIC_REQUIRED_FOR_NON_LOOPBACK'},
    'smtpd':{'bind':'127.0.0.1','port':int(smtp),'relay':'LOCAL_ONLY'},
    'dnsd':{'bind':'127.0.0.1','port':int(dns),'mode':'AUTHORITATIVE_ONLY_NO_RECURSION'},
    'snmpd':{'bind':'127.0.0.1','port':int(snmp),'mode':'READ_ONLY_GET'},
    'sshd':{'bind':'127.0.0.1','port':int(ssh),'authentication':'PUBLIC_KEY_ONLY_NO_FORWARDING'},
    'sql':{
      'engine':'PostgreSQL',
      'bind':'127.0.0.1',
      'port':int(postgres),
      'web_gateway':'/qikvrt/sql',
      'gateway_role':'qikvrt_terminal',
      'sql92_full_conformance_claimed':False,
    },
    'git_mirror':{
      'bind':'127.0.0.1',
      'port':int(git_port),
      'mode':'READ_ONLY_EXPORT',
      'candidate_ref':'refs/heads/candidate',
      'external_mirror_synchronization_claimed':False,
    },
  },
  'terminal_pattern':{'D0':{'0':'NOOP','1':'HOLD','2':'REOBSERVE','3':'REQUEST_AUTHORITY'}},
  'm68000_bootstrap':{
    'source_language':'ANSI_C90',
    'machine_target':'MC68000',
    'artifact':'/opt/qikvrt/assets/m68000/qikvrt_terminal_bootstrap.bin',
    'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
    'complete_posix_translation_claimed':False,
    'physical_m68000_execution_claimed':False,
  },
  'external_effect_claimed':False,
  'pass':False,
  'final_pass':False,
  'effect_ack_done':False,
}
pathlib.Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY

python3 -B - \
  "$STATE_DIR/runtime.json" "$RUNTIME_ID" "$PROFILE_DIR" "$START_URL" \
  "$NOVNC_PORT" "$PROXY_PORT" "$SUBJECT_SHA" <<'PY'
import json,pathlib,sys,time
path,runtime_id,profile,start_url,novnc_port,proxy_port,subject=sys.argv[1:]
obj={
  'schema':'qikvrt_universal_terminal_runtime_state_v1',
  'runtime_id':runtime_id,
  'browser':'firefox-esr',
  'visible_posix_surface':'xterm',
  'profile_dir':profile,
  'profile_persistent':True,
  'start_url':start_url,
  'novnc_port':int(novnc_port),
  'public_proxy_port':int(proxy_port),
  'subject_head_sha':subject,
  'started_at_unix':int(time.time()),
  'authenticated_session_storage':'FIREFOX_PROFILE',
  'adapter':'QIKVRT_FIREFOX_TERMINAL_PROXY_V1',
  'service_plane':'QIKVRT_UNIVERSAL_SERVICE_PLANE_V1',
  'external_effect_claimed':False,
  'pass':False,
  'final_pass':False,
  'effect_ack_done':False,
}
pathlib.Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY

cleanup() {
  kill \
    "$FIREFOX_PID" "$PROXY_PID" "$MIRROR_PID" "$GIT_PID" "$SSH_PID" \
    "$POSTGRES_PID" "$SERVICE_PID" "$NOVNC_PID" "$VNC_PID" "$XTERM_PID" \
    "$OPENBOX_PID" "$XVFB_PID" "$HTTP_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

printf '%s\n' \
  "QIKVRT cloud transputer ready: runtime=$RUNTIME_ID proxy=$PROXY_HOST:$PROXY_PORT noVNC=127.0.0.1:$NOVNC_PORT effect_ack=127.0.0.1:$HTTP_PORT subject=$SUBJECT_SHA"

while \
  kill -0 "$HTTP_PID" 2>/dev/null &&
  kill -0 "$FIREFOX_PID" 2>/dev/null &&
  kill -0 "$NOVNC_PID" 2>/dev/null &&
  kill -0 "$SERVICE_PID" 2>/dev/null &&
  kill -0 "$POSTGRES_PID" 2>/dev/null &&
  kill -0 "$SSH_PID" 2>/dev/null &&
  kill -0 "$GIT_PID" 2>/dev/null &&
  kill -0 "$MIRROR_PID" 2>/dev/null &&
  kill -0 "$PROXY_PID" 2>/dev/null
do
  sleep 1
done

echo "BLOCK: one or more universal terminal processes stopped" >&2
exit 1
