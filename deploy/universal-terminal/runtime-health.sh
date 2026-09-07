#!/bin/sh
set -eu

HTTP_PORT="${QIKVRT_HTTP_PORT:-8771}"
NOVNC_PORT="${QIKVRT_NOVNC_PORT:-6080}"
PROXY_PORT="${QIKVRT_PROXY_PORT:-${PORT:-8080}}"
SSH_PORT="${QIKVRT_SSH_PORT:-2222}"
PGPORT="${QIKVRT_POSTGRES_PORT:-5432}"
GIT_PORT="${QIKVRT_GIT_MIRROR_PORT:-9418}"
STATE_DIR="${QIKVRT_STATE_DIR:-/var/lib/qikvrt/state}"
SUBJECT_SHA="${QIKVRT_EXACT_SUBJECT_SHA:-${RAILWAY_GIT_COMMIT_SHA:-${QIKVRT_IMAGE_SUBJECT_SHA:-UNBOUND}}}"

curl -fsS "http://127.0.0.1:${HTTP_PORT}/.well-known/effect-ack" >/tmp/qikvrt-health-effect.json
pgrep -af 'firefox|firefox-esr' >/dev/null
pgrep -x openbox >/dev/null
pgrep -x xterm >/dev/null
curl -fsS "http://127.0.0.1:${NOVNC_PORT}/vnc.html" >/dev/null
curl -fsS "http://127.0.0.1:${PROXY_PORT}/healthz" >/tmp/qikvrt-health-proxy.json

python3 -B /opt/qikvrt/src/qikvrt_universal_service_plane.py --self-test

pg_isready -q -h 127.0.0.1 -p "$PGPORT"
psql -X -qAt -h 127.0.0.1 -p "$PGPORT" -U qikvrt_terminal -d qikvrt_terminal \
  -v ON_ERROR_STOP=1 -c 'SELECT 1' | grep -qx '1'

test "$(dbclient -y -i "$STATE_DIR/ssh/qikvrt_local_client_ed25519" \
  -p "$SSH_PORT" qikvrt@127.0.0.1 'printf QIKVRT_SSH_EXEC=PASS' 2>/dev/null)" = "QIKVRT_SSH_EXEC=PASS"

MIRROR_HEAD="$(git ls-remote "git://127.0.0.1:${GIT_PORT}/repository-mirror.git" refs/heads/candidate | awk '{print $1}')"
test -n "$MIRROR_HEAD"
if printf '%s' "$SUBJECT_SHA" | grep -Eq '^[0-9a-f]{40}$'; then
  test "$MIRROR_HEAD" = "$SUBJECT_SHA"
fi

test -s /opt/qikvrt/assets/m68000/qikvrt_terminal_bootstrap.bin
(
  cd /opt/qikvrt/assets/m68000
  sha256sum -c qikvrt_terminal_bootstrap.bin.sha256 >/dev/null
  sha256sum -c qikvrt_terminal_bootstrap.o.sha256 >/dev/null
  grep -Eiq 'm68k|mc68000' qikvrt_terminal_bootstrap.objdump.txt
)

test -f "$STATE_DIR/runtime.json"
test -f "$STATE_DIR/services.json"
test -f "$STATE_DIR/repository-mirror.json"

python3 -B - \
  "$STATE_DIR/runtime.json" \
  "$STATE_DIR/services.json" \
  "$STATE_DIR/repository-mirror.json" \
  /tmp/qikvrt-health-effect.json \
  /tmp/qikvrt-health-proxy.json <<'PY'
import json,re,sys
runtime,services,mesh,effect,proxy=[json.load(open(p,encoding='utf-8')) for p in sys.argv[1:]]
assert runtime['schema']=='qikvrt_universal_terminal_runtime_state_v1'
assert runtime['profile_persistent'] is True
assert runtime['browser']=='firefox-esr'
assert runtime['visible_posix_surface']=='xterm'
assert runtime['external_effect_claimed'] is False
assert services['schema']=='qikvrt_cloud_transputer_services_v1'
required={'httpd_proxy','smtpd','dnsd','snmpd','sshd','sql','git_mirror'}
assert required <= set(services['services'])
assert services['m68000_bootstrap']['source_language']=='ANSI_C90'
assert services['m68000_bootstrap']['machine_target']=='MC68000'
assert services['m68000_bootstrap']['complete_posix_translation_claimed'] is False
assert services['m68000_bootstrap']['physical_m68000_execution_claimed'] is False
assert mesh['schema']=='qikvrt_cloud_authority_mirror_observation_v1'
for role,repo in (('authority','Goldkelch/qik-vrt'),('mirror','ingolf-lohmann/qik-vrt')):
    node=mesh[role]
    assert node['repository']==repo
    assert re.fullmatch(r'[0-9a-f]{40}',node['head_sha'])
    assert re.fullmatch(r'[0-9a-f]{40}',node['root_tree_sha'])
assert mesh['synchronization_claimed'] is False
assert mesh['effect_class']=='OBSERVE_ONLY'
assert effect['schema']=='qikvrt_effect_ack_http_capability_v1'
assert effect['modes']==['prepare','commit']
assert effect['external_effects']=='NONE'
assert proxy['schema']=='qikvrt_terminal_proxy_health_v1'
assert proxy['state']=='READY'
assert proxy['external_effect_claimed'] is False
PY
