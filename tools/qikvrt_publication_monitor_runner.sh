#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# POSIX runner. The collector performs public GETs; only this explicit wrapper
# may commit the data-only monitor ref. It never publishes to an external venue.
set -eu
mode=${1:?probe or persist}
store=${2:?state checkout}
audit=${3:?new audit directory}
case "$mode" in probe|persist) ;; *) exit 2;; esac
code=$(pwd)
case "$store" in /*) ;; *) echo 'BLOCK: absolute state path required' >&2; exit 2;; esac
case "$audit" in /*) ;; *) echo 'BLOCK: absolute audit path required' >&2; exit 2;; esac
[ ! -e "$audit" ] || { echo 'BLOCK: audit path already exists' >&2; exit 2; }
mkdir -p "$audit"
{ python3 --version; git --version; uname -s; } > "$audit/TOOLCHAIN.txt"
ref=qikvrt/publication-monitor-state-v1
expected_origin=https://github.com/Goldkelch/qik-vrt
origin=$(git -C "$store" remote get-url origin)
[ "$origin" = "$expected_origin" ] || [ "$origin" = "$expected_origin.git" ] || {
    echo 'BLOCK: wrong state repository' >&2; exit 2;
}
source_head=$(git rev-parse --verify HEAD)
source_tree=$(git rev-parse --verify 'HEAD^{tree}')
old_head=$(git -C "$store" rev-parse --verify HEAD)
old_tree=$(git -C "$store" rev-parse --verify 'HEAD^{tree}')
python3 -B tools/qikvrt_publication_monitor.py validate --store "$store" > "$audit/STATE_BEFORE.json"
python3 -B tests/test_qikvrt_publication_monitor.py > "$audit/REGRESSIONS.log" 2>&1
python3 -B tools/qikvrt_publication_monitor.py observe --store "$store" \
    --source-head "$source_head" --source-tree "$source_tree" \
    --run-id "${GITHUB_RUN_ID:?}-${GITHUB_RUN_ATTEMPT:?}" \
    --receipt "$audit/LOCAL_PREPARATION.json" > "$audit/COLLECTOR.log"
python3 -B tools/qikvrt_publication_monitor.py validate --store "$store" > "$audit/STATE_AFTER.json"
[ "$(git rev-parse --verify HEAD)" = "$source_head" ]
[ -z "$(git status --porcelain --untracked-files=all)" ] || {
    echo 'BLOCK: source checkout mutated' >&2; exit 2;
}
cp -R "$store/monitor" "$audit/monitor"
rm -f "$audit/monitor/.lock"
export QPM_SOURCE_HEAD="$source_head" QPM_SOURCE_TREE="$source_tree"
export QPM_STATE_BEFORE_HEAD="$old_head" QPM_STATE_BEFORE_TREE="$old_tree"
export QPM_MODE="$mode" QPM_AUDIT="$audit"
python3 -B - <<'PY'
import json, os
from pathlib import Path
fields = ('SOURCE_HEAD','SOURCE_TREE','STATE_BEFORE_HEAD','STATE_BEFORE_TREE','MODE')
data = {key.lower(): os.environ['QPM_'+key] for key in fields}
data['schema'] = 'qikvrt.publication-monitor.runner-binding.v1'
data['repository_persistence_readback'] = False
data['external_publication_writes'] = 0
Path(os.environ['QPM_AUDIT'],'RUN_BINDING.json').write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
PY
[ "$mode" = persist ] || exit 0
[ "${GITHUB_REPOSITORY:-}" = Goldkelch/qik-vrt ]
[ "${GITHUB_REF:-}" = refs/heads/main ]
[ "$(git ls-remote origin refs/heads/main | cut -f1)" = "$source_head" ] || {
    echo 'BLOCK: source Main advanced' >&2; exit 2;
}
# Same admitted writer: materialize -> persist -> independently fetch -> readback.
# A non-force push is the authoritative compare-and-swap, never force-with-lease.
git -C "$store" fetch --no-tags --depth=1 origin "refs/heads/$ref"
[ "$(git -C "$store" rev-parse FETCH_HEAD)" = "$old_head" ] || {
    echo 'BLOCK: state successor already exists; preserve local audit' >&2; exit 2;
}
git -C "$store" add -- monitor/state.json monitor/history
if [ -d "$store/monitor/responses" ]; then git -C "$store" add -- monitor/responses; fi
# Never stage an unexpected path, a link or an executable from a public response.
git -C "$store" diff --cached --name-only > "$audit/STAGED_PATHS.txt"
python3 -B - "$store" "$audit/STAGED_PATHS.txt" <<'PY'
import pathlib,sys
root=pathlib.Path(sys.argv[1])
for name in pathlib.Path(sys.argv[2]).read_text().splitlines():
    if not (name=='monitor/state.json' or name.startswith(('monitor/history/','monitor/responses/'))):
        raise SystemExit('BLOCK: non-state staged path')
    if (root/name).is_symlink(): raise SystemExit('BLOCK: state symlink')
PY
git -C "$store" -c user.name='github-actions[bot]' \
    -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    commit -m "monitor: persist public observation ${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
new_head=$(git -C "$store" rev-parse HEAD)
new_tree=$(git -C "$store" rev-parse 'HEAD^{tree}')
set +e
git -C "$store" push origin "HEAD:refs/heads/$ref" > "$audit/PUSH.log" 2>&1
push_status=$?
# A failed/ambiguous transport still receives a fresh remote observation.
git -C "$store" fetch --no-tags --depth=1 origin "refs/heads/$ref" > "$audit/READBACK.log" 2>&1
fetch_status=$?
set -e
export QPM_NEW_HEAD="$new_head" QPM_NEW_TREE="$new_tree"
export QPM_PUSH_STATUS="$push_status" QPM_FETCH_STATUS="$fetch_status" QPM_STORE="$store"
python3 -B - <<'PY'
import hashlib,json,os,pathlib,subprocess
root=pathlib.Path(os.environ['QPM_STORE']);audit=pathlib.Path(os.environ['QPM_AUDIT'])
def git(*args): return subprocess.check_output(['git','-C',str(root),*args])
remote=git('rev-parse','FETCH_HEAD').decode().strip() if os.environ['QPM_FETCH_STATUS']=='0' else None
body=git('show',remote+':monitor/state.json') if remote else None
prepared=(root/'monitor/state.json').read_bytes()
receipt={'schema':'qikvrt.publication-monitor.repository-readback.v1',
 'repository':'Goldkelch/qik-vrt','state_ref':'qikvrt/publication-monitor-state-v1',
 'before_head':os.environ['QPM_STATE_BEFORE_HEAD'],'written_head':os.environ['QPM_NEW_HEAD'],
 'written_tree':os.environ['QPM_NEW_TREE'],'observed_head':remote,
 'prepared_state_sha256':hashlib.sha256(prepared).hexdigest(),
 'readback_state_sha256':hashlib.sha256(body).hexdigest() if body is not None else None,
 'push_transport_status':int(os.environ['QPM_PUSH_STATUS']),
 'repository_persistence_readback':remote==os.environ['QPM_NEW_HEAD'] and body==prepared,
 'external_publication_writes':0,'general_effect_ack_done':False}
(audit/'REPOSITORY_READBACK.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(json.dumps(receipt,sort_keys=True))
if not receipt['repository_persistence_readback']: raise SystemExit('BLOCK: remote state not verified')
PY
