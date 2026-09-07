#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -eu

PROFILE_DIR="${QIKVRT_PROFILE_DIR:-/var/lib/qikvrt/profile}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
MIRROR_DIR="${QIKVRT_AUTHORITY_MIRROR_DIR:-/var/lib/qikvrt/mirror/authority.git}"
PERSONAL_POSIX_DIR="${QIKVRT_PERSONAL_POSIX_DIR:-/var/lib/qikvrt/personal-posix}"
MAIL_DIR="${QIKVRT_MAIL_DIR:-/var/lib/qikvrt/mail}"
RUNTIME_ID="${QIKVRT_RUNTIME_ID:-qikvrt-cloud-transputer-1}"
MESH_PUBLIC_URL="${QIKVRT_MESH_PUBLIC_URL:-https://goldkelch.github.io/qik-vrt/cloud-transputer/}"
MESH_DOMAIN="${QIKVRT_MESH_DOMAIN:-qikvrt.mesh.local}"
START_URL="${QIKVRT_START_URL:-https://goldkelch.github.io/qik-vrt/}"
DISPLAY_VALUE="${DISPLAY:-:99}"
HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
PROXY_PORT="${QIKVRT_PROXY_PORT:-8080}"
SSH_PORT="${QIKVRT_SSH_PORT:-2222}"
SMTP_PORT="${QIKVRT_SMTP_PORT:-2525}"
DNS_PORT="${QIKVRT_DNS_PORT:-5353}"
SNMP_PORT="${QIKVRT_SNMP_PORT:-1161}"
SQL_PORT="${QIKVRT_SQL_PORT:-5432}"
RUN_DIR=/run/qikvrt
LOG_DIR=/opt/qikvrt/runtime/cloud-transputer-logs

mkdir -p "$PROFILE_DIR" "$STATE_DIR" "$MIRROR_DIR" "$PERSONAL_POSIX_DIR" "$MAIL_DIR" \
  "$STATE_DIR/m68k" "$STATE_DIR/ssh" "$STATE_DIR/postgresql" "$RUN_DIR" "$LOG_DIR" /run/sshd /run/postgresql
chmod 700 "$STATE_DIR/ssh" "$STATE_DIR/postgresql"
chown -R postgres:postgres "$STATE_DIR/postgresql" /run/postgresql

python3 -B - "$MESH_PUBLIC_URL" <<'PY'
import sys
from urllib.parse import urlsplit
url=sys.argv[1]
p=urlsplit(url)
if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password or p.fragment:
    raise SystemExit('BLOCK: QIKVRT_MESH_PUBLIC_URL must be an absolute HTTP(S) URL without credentials or fragment')
PY

if [ ! -f "$PROFILE_DIR/.qikvrt-profile-initialized" ]; then
  mkdir -p "$PROFILE_DIR/extensions"
  cp /opt/qikvrt/runtime/bootstrap-profile/extensions/qikvrt-ai-terminal@goldkelch.local.xpi "$PROFILE_DIR/extensions/"
  cp /opt/qikvrt/runtime/bootstrap-profile/user.js "$PROFILE_DIR/user.js"
  : > "$PROFILE_DIR/.qikvrt-profile-initialized"
fi

if ! /usr/local/bin/qikvrt-authority-mirror-refresh >"$LOG_DIR/authority-mirror.log" 2>&1; then
  if [ "${QIKVRT_REQUIRE_AUTHORITY_MIRROR:-1}" = 1 ]; then
    cat "$LOG_DIR/authority-mirror.log" >&2 || true
    exit 30
  fi
fi

M68K_PROBE="$STATE_DIR/m68k/qikvrt-effect-ack-probe"
m68k-linux-gnu-gcc -std=c90 -pedantic -Wall -Wextra -Werror -static \
  -I/opt/qikvrt/include \
  /opt/qikvrt/src/effect_ack_core.c \
  /opt/qikvrt/src/cloud_transputer/m68k_effect_ack_probe.c \
  -o "$M68K_PROBE"
file "$M68K_PROBE" > "$STATE_DIR/m68k/file.txt"
qemu-m68k "$M68K_PROBE" > "$STATE_DIR/m68k/execution.txt"
grep -q '^ARCH=M68000_FAMILY$' "$STATE_DIR/m68k/execution.txt"
grep -q '^EFFECT_ACK_STATE=EFFECT_ACK_DONE$' "$STATE_DIR/m68k/execution.txt"
sha256sum "$M68K_PROBE" > "$STATE_DIR/m68k/sha256.txt"

PERSONAL_POSIX_STATE=UNBOUND_OWNER_SOURCE_ABSENT
if [ -f "$PERSONAL_POSIX_DIR/build-qikvrt-m68k.sh" ]; then
  PERSONAL_POSIX_STATE=SOURCE_PRESENT_BUILD_STARTED
  (
    cd "$PERSONAL_POSIX_DIR"
    CC=m68k-linux-gnu-gcc \
    CFLAGS='-std=c90 -pedantic -Wall -Wextra -Werror -static' \
    QIKVRT_M68K_RUNNER=qemu-m68k \
      sh ./build-qikvrt-m68k.sh
  ) > "$LOG_DIR/personal-posix-build.log" 2>&1
  PERSONAL_POSIX_STATE=OWNER_BUILD_ENTRYPOINT_EXECUTED
elif find "$PERSONAL_POSIX_DIR" -mindepth 1 -maxdepth 1 -type f -print -quit | grep -q .; then
  PERSONAL_POSIX_STATE=SOURCE_PRESENT_WITHOUT_DECLARED_BUILD_ENTRYPOINT
fi
if [ "${QIKVRT_REQUIRE_PERSONAL_POSIX:-0}" = 1 ] && [ "$PERSONAL_POSIX_STATE" != OWNER_BUILD_ENTRYPOINT_EXECUTED ]; then
  printf '%s\n' "BLOCK: personal POSIX source/build entrypoint is not exact-bound" >&2
  exit 31
fi

PG_SERVER="$(find /usr/lib/postgresql -type f -path '*/bin/postgres' -print | sort -V | tail -n 1)"
if [ -z "$PG_SERVER" ]; then
  printf '%s\n' "BLOCK: PostgreSQL server binary was not discovered below /usr/lib/postgresql" >&2
  find /usr/lib/postgresql -maxdepth 4 -type f -print >&2 || true
  exit 32
fi
PG_BIN="$(dirname "$PG_SERVER")"
for pg_tool in postgres initdb pg_ctl psql createuser createdb pg_isready; do
  if [ ! -x "$PG_BIN/$pg_tool" ]; then
    printf '%s\n' "BLOCK: required PostgreSQL tool is absent: $PG_BIN/$pg_tool" >&2
    exit 33
  fi
done
printf 'PG_SERVER=%s\nPG_BIN=%s\n' "$PG_SERVER" "$PG_BIN" > "$LOG_DIR/postgresql-discovery.log"

PGDATA="$STATE_DIR/postgresql/data"
if [ ! -f "$PGDATA/PG_VERSION" ]; then
  mkdir -p "$PGDATA"
  chown -R postgres:postgres "$STATE_DIR/postgresql"
  su -s /bin/sh postgres -c "'$PG_BIN/initdb' -D '$PGDATA' --encoding=UTF8 --locale=C --auth-local=trust --auth-host=scram-sha-256" > "$LOG_DIR/postgres-init.log" 2>&1
  cat >> "$PGDATA/postgresql.conf" <<EOF
listen_addresses = '*'
port = $SQL_PORT
unix_socket_directories = '/run/postgresql'
max_connections = 64
EOF
  cat >> "$PGDATA/pg_hba.conf" <<'EOF'
host all all 127.0.0.1/32 trust
host all all ::1/128 trust
host all all 0.0.0.0/0 scram-sha-256
host all all ::0/0 scram-sha-256
EOF
fi
chown -R postgres:postgres "$STATE_DIR/postgresql" /run/postgresql
su -s /bin/sh postgres -c "'$PG_BIN/pg_ctl' -D '$PGDATA' -l '$LOG_DIR/postgresql.log' -w start"

if ! su -s /bin/sh postgres -c "'$PG_BIN/psql' -Atqc \"SELECT 1 FROM pg_roles WHERE rolname='qikvrt'\"" | grep -qx 1; then
  su -s /bin/sh postgres -c "'$PG_BIN/createuser' qikvrt"
fi
if ! su -s /bin/sh postgres -c "'$PG_BIN/psql' -Atqc \"SELECT 1 FROM pg_database WHERE datname='qikvrt'\"" | grep -qx 1; then
  su -s /bin/sh postgres -c "'$PG_BIN/createdb' -O qikvrt qikvrt"
fi
if [ -n "${QIKVRT_SQL_PASSWORD_FILE:-}" ]; then
  test -r "$QIKVRT_SQL_PASSWORD_FILE"
  SQL_PASSWORD="$(cat "$QIKVRT_SQL_PASSWORD_FILE")"
  test -n "$SQL_PASSWORD"
  ESCAPED_PASSWORD="$(printf '%s' "$SQL_PASSWORD" | sed "s/'/''/g")"
  SQL_SECRET_FILE="$RUN_DIR/sql-password.sql"
  umask 077
  printf "ALTER ROLE qikvrt PASSWORD '%s';\n" "$ESCAPED_PASSWORD" > "$SQL_SECRET_FILE"
  su -s /bin/sh postgres -c "'$PG_BIN/psql' -v ON_ERROR_STOP=1 -f '$SQL_SECRET_FILE'"
  rm -f "$SQL_SECRET_FILE"
  unset SQL_PASSWORD ESCAPED_PASSWORD
fi
su -s /bin/sh postgres -c "'$PG_BIN/psql' -v ON_ERROR_STOP=1 -d qikvrt -c 'CREATE TABLE IF NOT EXISTS terminal_state (key VARCHAR(64) PRIMARY KEY, value VARCHAR(256) NOT NULL)' -c \"INSERT INTO terminal_state(key,value) VALUES ('schema','qikvrt_cloud_transputer_v1') ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value\"" >/dev/null

SSH_HOST_KEY="$STATE_DIR/ssh/ssh_host_ed25519_key"
if [ ! -f "$SSH_HOST_KEY" ]; then
  ssh-keygen -q -t ed25519 -N '' -f "$SSH_HOST_KEY"
fi
AUTHORIZED_KEYS="$STATE_DIR/ssh/authorized_keys"
if [ -n "${QIKVRT_SSH_AUTHORIZED_KEYS_FILE:-}" ]; then
  test -r "$QIKVRT_SSH_AUTHORIZED_KEYS_FILE"
  cp "$QIKVRT_SSH_AUTHORIZED_KEYS_FILE" "$AUTHORIZED_KEYS"
fi
touch "$AUTHORIZED_KEYS"
chmod 600 "$AUTHORIZED_KEYS" "$SSH_HOST_KEY"
cat > "$RUN_DIR/sshd_config" <<EOF
Port $SSH_PORT
ListenAddress 0.0.0.0
HostKey $SSH_HOST_KEY
PidFile $RUN_DIR/sshd.pid
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
AuthorizedKeysFile $AUTHORIZED_KEYS
AllowUsers qikvrt
UsePAM no
PrintMotd no
Subsystem sftp internal-sftp
EOF
/usr/sbin/sshd -t -f "$RUN_DIR/sshd_config"
/usr/sbin/sshd -D -e -f "$RUN_DIR/sshd_config" > "$LOG_DIR/sshd.log" 2>&1 &
SSHD_PID=$!

cat > "$RUN_DIR/dnsmasq.conf" <<EOF
port=$DNS_PORT
listen-address=0.0.0.0
bind-dynamic
no-resolv
no-hosts
address=/$MESH_DOMAIN/127.0.0.1
txt-record=$MESH_DOMAIN,QIK-VRT CLOUD TRANSPUTER $RUNTIME_ID
EOF
dnsmasq --keep-in-foreground --conf-file="$RUN_DIR/dnsmasq.conf" > "$LOG_DIR/dnsmasq.log" 2>&1 &
DNS_PID=$!

SNMP_COMMUNITY=qikvrt-local
SNMP_SOURCE=127.0.0.1
if [ -n "${QIKVRT_SNMP_COMMUNITY_FILE:-}" ]; then
  test -r "$QIKVRT_SNMP_COMMUNITY_FILE"
  SNMP_COMMUNITY="$(cat "$QIKVRT_SNMP_COMMUNITY_FILE")"
  test -n "$SNMP_COMMUNITY"
  SNMP_SOURCE=default
fi
cat > "$RUN_DIR/snmpd.conf" <<EOF
agentaddress udp:$SNMP_PORT
rocommunity $SNMP_COMMUNITY $SNMP_SOURCE
sysLocation QIK-VRT Cloud Transputer
sysContact Ingolf Lohmann
sysName $RUNTIME_ID
EOF
/usr/sbin/snmpd -f -Lo -C -c "$RUN_DIR/snmpd.conf" > "$LOG_DIR/snmpd.log" 2>&1 &
SNMP_PID=$!

python3 -B /opt/qikvrt/src/cloud_transputer/smtpd.py \
  --host 0.0.0.0 --port "$SMTP_PORT" --domain "$MESH_DOMAIN" --mail-root "$MAIL_DIR" \
  > "$LOG_DIR/smtpd.log" 2>&1 &
SMTP_PID=$!

python3 -B /opt/qikvrt/src/qikvrt_effect_ack_http_terminal.py \
  --host 127.0.0.1 --port "$HTTP_PORT" > "$LOG_DIR/effect-ack-http.log" 2>&1 &
EFFECT_PID=$!

Xvfb "$DISPLAY_VALUE" -screen 0 1440x900x24 -nolisten tcp > "$LOG_DIR/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1
VNC_ARGS="-display $DISPLAY_VALUE -forever -shared -localhost -rfbport 5900"
if [ -n "${QIKVRT_VNC_PASSWORD_FILE:-}" ]; then
  test -r "$QIKVRT_VNC_PASSWORD_FILE"
  VNC_PASSWORD="$(cat "$QIKVRT_VNC_PASSWORD_FILE")"
  test -n "$VNC_PASSWORD"
  x11vnc -storepasswd "$VNC_PASSWORD" "$RUN_DIR/vnc.pass" >/dev/null
  VNC_ARGS="$VNC_ARGS -rfbauth $RUN_DIR/vnc.pass"
else
  VNC_ARGS="$VNC_ARGS -nopw"
fi
# shellcheck disable=SC2086
x11vnc $VNC_ARGS > "$LOG_DIR/x11vnc.log" 2>&1 &
VNC_PID=$!
websockify --web=/usr/share/novnc/ "$NOVNC_PORT" localhost:5900 > "$LOG_DIR/novnc.log" 2>&1 &
NOVNC_PID=$!
firefox-esr --no-remote --profile "$PROFILE_DIR" "$START_URL" > "$LOG_DIR/firefox.log" 2>&1 &
FIREFOX_PID=$!

cat > "$RUN_DIR/nginx.conf" <<EOF
worker_processes 1;
pid $RUN_DIR/nginx.pid;
error_log $LOG_DIR/nginx-error.log info;
events { worker_connections 256; }
http {
  access_log $LOG_DIR/nginx-access.log;
  server {
    listen $PROXY_PORT;
    server_name _;
    location = / { return 302 /terminal/vnc.html; }
    location /terminal/ {
      proxy_pass http://127.0.0.1:$NOVNC_PORT/;
      proxy_http_version 1.1;
      proxy_set_header Upgrade \$http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_set_header Host \$host;
      proxy_read_timeout 3600s;
    }
    location /effect-ack/ {
      proxy_pass http://127.0.0.1:$HTTP_PORT/;
      proxy_set_header Host 127.0.0.1;
    }
    location = /.well-known/qikvrt-cloud-transputer {
      default_type application/json;
      alias $RUN_DIR/runtime.json;
    }
  }
}
EOF
nginx -t -c "$RUN_DIR/nginx.conf"
nginx -c "$RUN_DIR/nginx.conf" -g 'daemon off;' > "$LOG_DIR/nginx.log" 2>&1 &
NGINX_PID=$!

FIREFOX_VERSION="$(firefox-esr --version 2>/dev/null | head -n 1)"
M68K_SHA256="$(awk '{print $1}' "$STATE_DIR/m68k/sha256.txt")"
MIRROR_HEAD=UNOBSERVED
MIRROR_TREE=UNOBSERVED
if [ -f "$STATE_DIR/authority-mirror.json" ]; then
  MIRROR_HEAD="$(python3 -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["main_head_sha"])' "$STATE_DIR/authority-mirror.json")"
  MIRROR_TREE="$(python3 -B -c 'import json,sys; print(json.load(open(sys.argv[1]))["main_tree_sha"])' "$STATE_DIR/authority-mirror.json")"
fi

python3 -B - "$RUN_DIR/runtime.json" "$STATE_DIR/runtime.json" "$RUNTIME_ID" "$MESH_PUBLIC_URL" "$FIREFOX_VERSION" "$M68K_SHA256" "$PERSONAL_POSIX_STATE" "$MIRROR_HEAD" "$MIRROR_TREE" "$PROXY_PORT" "$SSH_PORT" "$SMTP_PORT" "$DNS_PORT" "$SNMP_PORT" "$SQL_PORT" <<'PY'
import json,os,sys,time
(run_path,state_path,runtime_id,public_url,firefox_version,m68k_sha,personal_posix_state,mirror_head,mirror_tree,proxy_port,ssh_port,smtp_port,dns_port,snmp_port,sql_port)=sys.argv[1:]
value={
  'schema':'qikvrt_cloud_transputer_runtime_v1','runtime_id':runtime_id,
  'mesh_public_url':public_url,'firefox_version':firefox_version,
  'profile_persistent':True,
  'service_ports':{'http_proxy':int(proxy_port),'ssh':int(ssh_port),'smtp':int(smtp_port),'dns':int(dns_port),'snmp':int(snmp_port),'postgresql':int(sql_port)},
  'm68000_effect_ack_probe_sha256':m68k_sha,'m68000_effect_ack_probe_executed':True,
  'personal_posix_state':personal_posix_state,'standalone_m68000_tcp_ip_stack_claimed':False,
  'kernel_backed_posix_tcp_ip':True,'authority_mirror_main_head':mirror_head,
  'authority_mirror_main_tree':mirror_tree,'authority_mirror_polling':False,
  'started_at_unix':int(time.time()),
  'public_cloud_reachability_readback':'UNOBSERVED_UNTIL_EXTERNAL_RUNTIME_ORIGIN_IS_AUTHENTICATED',
  'external_effect_claimed':False,'pass':False,'final_pass':False,'effect_ack_done':False,
}
for path in (run_path,state_path):
  tmp=path+'.tmp'
  with open(tmp,'w',encoding='utf-8',newline='\n') as handle:
    json.dump(value,handle,ensure_ascii=False,indent=2,sort_keys=True); handle.write('\n')
  os.replace(tmp,path)
PY

cleanup() {
  kill "$NGINX_PID" "$FIREFOX_PID" "$NOVNC_PID" "$VNC_PID" "$XVFB_PID" \
       "$EFFECT_PID" "$SMTP_PID" "$SNMP_PID" "$DNS_PID" "$SSHD_PID" 2>/dev/null || true
  su -s /bin/sh postgres -c "'$PG_BIN/pg_ctl' -D '$PGDATA' -m fast stop" >/dev/null 2>&1 || true
}
trap cleanup INT TERM EXIT

/usr/local/bin/qikvrt-cloud-transputer-health
printf '%s\n' "QIKVRT cloud transputer ready: runtime=$RUNTIME_ID proxy=0.0.0.0:$PROXY_PORT stable_mesh=$MESH_PUBLIC_URL"

while kill -0 "$NGINX_PID" 2>/dev/null \
  && kill -0 "$FIREFOX_PID" 2>/dev/null \
  && kill -0 "$EFFECT_PID" 2>/dev/null \
  && kill -0 "$SMTP_PID" 2>/dev/null \
  && kill -0 "$DNS_PID" 2>/dev/null \
  && kill -0 "$SNMP_PID" 2>/dev/null \
  && kill -0 "$SSHD_PID" 2>/dev/null; do
  sleep 1
done
exit 1
