#!/bin/sh
set -eu

mode="${QIKVRT_SERVICE_MODE:-terminal}"

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

case "$mode" in
  terminal)
    exec /usr/local/bin/qikvrt-universal-terminal
    ;;
  gateway)
    exec nginx -c /opt/qikvrt/deploy/universal-terminal/nginx.conf -g 'daemon off;'
    ;;
  smtpd)
    mkdir -p "${QIKVRT_SMTP_SPOOL:-/var/lib/qikvrt/smtp}"
    exec /usr/local/bin/qikvrt-smtpd \
      --host 0.0.0.0 \
      --port "${QIKVRT_SMTP_PORT:-2525}" \
      --spool "${QIKVRT_SMTP_SPOOL:-/var/lib/qikvrt/smtp}"
    ;;
  snmpd)
    mkdir -p /tmp/qikvrt-snmp
    export SNMP_PERSISTENT_DIR=/tmp/qikvrt-snmp
    exec /usr/sbin/snmpd -f -Lo -C \
      -c /opt/qikvrt/deploy/universal-terminal/snmpd.conf
    ;;
  dnsd)
    exec /usr/sbin/named -g \
      -c /opt/qikvrt/deploy/universal-terminal/named.conf \
      -p "${QIKVRT_DNS_PORT:-5353}"
    ;;
  sshd)
    SSH_STATE="${QIKVRT_SSH_STATE_DIR:-/var/lib/qikvrt/ssh}"
    mkdir -p "$SSH_STATE" /run/sshd
    if [ ! -f "$SSH_STATE/ssh_host_ed25519_key" ]; then
      ssh-keygen -q -t ed25519 -N '' -f "$SSH_STATE/ssh_host_ed25519_key"
    fi
    if [ -n "${QIKVRT_SSH_AUTHORIZED_KEYS:-}" ]; then
      umask 077
      printf '%s\n' "$QIKVRT_SSH_AUTHORIZED_KEYS" > "$SSH_STATE/authorized_keys"
    elif [ ! -f "$SSH_STATE/authorized_keys" ]; then
      : > "$SSH_STATE/authorized_keys"
      chmod 600 "$SSH_STATE/authorized_keys"
    fi
    exec /usr/sbin/sshd -D -e \
      -f /opt/qikvrt/deploy/universal-terminal/sshd_config
    ;;
  sqld)
    DB_PASSWORD="${QIKVRT_DB_PASSWORD:-}"
    if [ -z "$DB_PASSWORD" ]; then
      echo "QIKVRT_DB_PASSWORD is required for sqld" >&2
      exit 64
    fi
    PG_MAJOR="$(ls -1 /usr/lib/postgresql | sort -V | tail -1)"
    PG_BIN="/usr/lib/postgresql/${PG_MAJOR}/bin"
    PGDATA="${QIKVRT_PGDATA:-/var/lib/qikvrt/postgres}"
    mkdir -p "$PGDATA"
    chown -R postgres:postgres "$PGDATA"
    install -d -m 700 -o postgres -g postgres /run/postgresql
    cleanup_sql() {
      rm -f /run/qikvrt-db.pass
      runuser -u postgres -- "$PG_BIN/pg_ctl" -D "$PGDATA" -m fast -w -t 30 stop >/dev/null 2>&1 || true
    }
    trap cleanup_sql EXIT
    trap 'exit 143' TERM
    trap 'exit 130' INT
    if [ ! -s "$PGDATA/PG_VERSION" ]; then
      umask 077
      printf '%s\n' "$DB_PASSWORD" > /run/qikvrt-db.pass
      chown postgres:postgres /run/qikvrt-db.pass
      runuser -u postgres -- "$PG_BIN/initdb" \
        -D "$PGDATA" \
        --username=qikvrt \
        --pwfile=/run/qikvrt-db.pass \
        --auth-local=scram-sha-256 \
        --auth-host=scram-sha-256 \
        --encoding=UTF8
      rm -f /run/qikvrt-db.pass
      {
        printf "%s\n" "listen_addresses='0.0.0.0'"
        printf "%s\n" "port=5432"
        printf "%s\n" "password_encryption='scram-sha-256'"
      } >> "$PGDATA/postgresql.conf"
      printf '%s\n' "host all all 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"
    fi
    # Authenticate locally even during initialization; do not weaken pg_hba.
    # Check again on restart so an interrupted bootstrap can recover safely.
    export PGPASSWORD="$DB_PASSWORD"
    runuser -u postgres -- "$PG_BIN/pg_ctl" -D "$PGDATA" \
      -o "-c listen_addresses='' -c unix_socket_directories=/run/postgresql" \
      -l "$PGDATA/bootstrap.log" -w -t 30 start
    exists="$(runuser -u postgres -- "$PG_BIN/psql" -X -w -h /run/postgresql \
      -U qikvrt -d postgres -At -v ON_ERROR_STOP=1 \
      -c "SELECT 1 FROM pg_database WHERE datname = 'qikvrt'")"
    if [ "$exists" != 1 ]; then
      runuser -u postgres -- "$PG_BIN/createdb" -w -h /run/postgresql -U qikvrt qikvrt
    fi
    runuser -u postgres -- "$PG_BIN/pg_ctl" -D "$PGDATA" -m fast -w -t 30 stop
    unset PGPASSWORD DB_PASSWORD
    trap - EXIT INT TERM
    exec runuser -u postgres -- "$PG_BIN/postgres" -D "$PGDATA" \
      -c unix_socket_directories=/run/postgresql
    ;;
  mirror)
    exec /usr/local/bin/qikvrt-mirror-bootstrap
    ;;
  *)
    echo "unknown QIKVRT_SERVICE_MODE: $mode" >&2
    exit 64
    ;;
esac
