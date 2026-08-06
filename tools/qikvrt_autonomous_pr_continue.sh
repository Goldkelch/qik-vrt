#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -euo pipefail

OPT_IN_MARKER='<!-- qikvrt-autonomous-self-heal:enabled -->'
CONTRACT_PATH='state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json'
SELECTION_JSON='/tmp/qikvrt-autonomous-selection.json'
CONFLICT_PATHS='/tmp/qikvrt-autonomous-merge-conflicts.txt'
REPAIR_RESULT='/tmp/qikvrt-autonomous-repair.json'
REPAIR_PATHS='/tmp/qikvrt-autonomous-repair-paths.txt'
DISPATCH_JSON='/tmp/qikvrt-autonomous-dispatch.json'
COMMENT_FILE='/tmp/qikvrt-autonomous-comment.md'

require_env() {
  local name="$1"
  if test -z "${!name:-}"; then
    printf 'BLOCK: required environment variable %s is absent\n' "$name" >&2
    exit 2
  fi
}

for name in GH_TOKEN GITHUB_REPOSITORY GITHUB_SERVER_URL GITHUB_RUN_ID; do
  require_env "$name"
done

for command in gh git python3; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'BLOCK: required command %s is absent\n' "$command" >&2
    exit 2
  }
done

select_candidate() {
  local pages='/tmp/qikvrt-autonomous-open-pr-pages.json'
  gh api --paginate --slurp \
    "repos/${GITHUB_REPOSITORY}/pulls?state=open&per_page=100" \
    > "$pages"
  python3 -B - "$pages" "$SELECTION_JSON" "$OPT_IN_MARKER" "$GITHUB_REPOSITORY" <<'PY'
import json
import pathlib
import sys

pages_path, output_path, marker, repository = sys.argv[1:]
pages = json.loads(pathlib.Path(pages_path).read_text(encoding='utf-8'))
candidates = []
for page in pages:
    for pr in page:
        head = pr.get('head') or {}
        head_repo = (head.get('repo') or {}).get('full_name')
        if pr.get('draft') is not True or head_repo != repository:
            continue
        if marker not in (pr.get('body') or ''):
            continue
        if (pr.get('base') or {}).get('ref') != 'main':
            continue
        candidates.append(pr)
candidates.sort(key=lambda item: int(item['number']))
value = {'found': False}
if candidates:
    pr = candidates[0]
    value = {
        'found': True,
        'pr_number': int(pr['number']),
        'head_ref': pr['head']['ref'],
        'head_sha': pr['head']['sha'],
        'base_ref': pr['base']['ref'],
        'observed_base_sha': pr['base']['sha'],
    }
pathlib.Path(output_path).write_text(
    json.dumps(value, sort_keys=True) + '\n', encoding='utf-8'
)
PY
}

json_field() {
  local field="$1"
  python3 -B - "$SELECTION_JSON" "$field" <<'PY'
import json
import pathlib
import sys
value = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
item = value[sys.argv[2]]
if isinstance(item, bool):
    print('true' if item else 'false')
else:
    print(item)
PY
}

validate_conflicts() {
  python3 -B - "$CONTRACT_PATH" "$CONFLICT_PATHS" <<'PY'
import json
import pathlib
import sys

contract_path, conflicts_path = map(pathlib.Path, sys.argv[1:])
contract = json.loads(contract_path.read_text(encoding='utf-8'))
policy = contract['pull_request_continuation']['generated_merge_conflict_policy']
if policy['mode'] != 'ALLOWLIST_ONLY_REGENERATE_IMMEDIATELY':
    raise SystemExit('BLOCK: generated merge-conflict policy mode differs')
if policy['temporary_resolution_side'] != 'CURRENT_MAIN':
    raise SystemExit('BLOCK: generated merge-conflict temporary side differs')
if policy['non_allowlisted_conflict'] != 'BLOCK':
    raise SystemExit('BLOCK: non-allowlisted conflict policy differs')
allowed = set(policy['allowed_paths'])
conflicts = {
    line.strip()
    for line in conflicts_path.read_text(encoding='utf-8').splitlines()
    if line.strip()
}
unexpected = sorted(conflicts - allowed)
if unexpected:
    raise SystemExit('BLOCK: non-regenerable merge conflicts: ' + ', '.join(unexpected))
PY
}

parse_repair_result() {
  python3 -B - "$REPAIR_RESULT" "$REPAIR_PATHS" <<'PY'
import json
import pathlib
import sys

result_path, paths_path = map(pathlib.Path, sys.argv[1:])
value = json.loads(result_path.read_text(encoding='utf-8'))
if value['state'] not in {'NOOP', 'CANDIDATE_READY'}:
    raise SystemExit(f"BLOCK: unexpected self-heal state {value['state']}")
paths = value.get('changed_paths', [])
if not isinstance(paths, list) or not all(isinstance(path, str) and path for path in paths):
    raise SystemExit('BLOCK: self-heal changed_paths are invalid')
paths_path.write_text(''.join(f'{path}\n' for path in paths), encoding='utf-8')
PY
}

assert_conflicts_regenerated() {
  python3 -B - "$CONFLICT_PATHS" "$REPAIR_PATHS" <<'PY'
import pathlib
import sys
conflicts = {
    line.strip()
    for line in pathlib.Path(sys.argv[1]).read_text(encoding='utf-8').splitlines()
    if line.strip()
}
repaired = {
    line.strip()
    for line in pathlib.Path(sys.argv[2]).read_text(encoding='utf-8').splitlines()
    if line.strip()
}
missing = sorted(conflicts - repaired)
if missing:
    raise SystemExit('BLOCK: temporarily resolved projections were not regenerated: ' + ', '.join(missing))
PY
}

select_candidate
if test "$(json_field found)" != 'true'; then
  echo 'NOOP: no opted-in same-repository draft PR requires continuation.'
  exit 0
fi

PR_NUMBER="$(json_field pr_number)"
HEAD_REF="$(json_field head_ref)"
EXPECTED_HEAD="$(json_field head_sha)"
BASE_REF="$(json_field base_ref)"
OBSERVED_BASE="$(json_field observed_base_sha)"

test "$BASE_REF" = 'main'
test "${#EXPECTED_HEAD}" -eq 40
test "${#OBSERVED_BASE}" -eq 40

checked_main="$(git rev-parse --verify HEAD^{commit})"
live_main="$(gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/main" --jq '.object.sha')"
test "$checked_main" = "$live_main"
live_head="$(gh api "repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}" --jq '.head.sha')"
test "$live_head" = "$EXPECTED_HEAD"

git config user.name 'qik-vrt-autonomous-pr-continuation'
git config user.email 'qik-vrt-autonomous-pr-continuation@users.noreply.github.com'
git fetch origin "+refs/heads/${HEAD_REF}:refs/remotes/origin/${HEAD_REF}"
git switch -C "$HEAD_REF" "$EXPECTED_HEAD"
test "$(git rev-parse --verify HEAD^{commit})" = "$EXPECTED_HEAD"

merge_created=false
generated_conflicts_resolved=false
conflict_summary='none'
: > "$CONFLICT_PATHS"

if ! git merge-base --is-ancestor "$live_main" HEAD; then
  set +e
  git merge --no-ff --no-commit "$live_main"
  merge_status=$?
  set -e
  if test "$merge_status" -ne 0; then
    git diff --name-only --diff-filter=U | sort -u > "$CONFLICT_PATHS"
    if ! test -s "$CONFLICT_PATHS"; then
      git merge --abort || true
      echo 'BLOCK: merge failed without an inspectable conflict set' >&2
      exit 2
    fi
    if ! validate_conflicts; then
      git merge --abort || true
      exit 2
    fi
    while IFS= read -r path; do
      test -n "$path"
      git checkout --theirs -- "$path"
      git add -- "$path"
    done < "$CONFLICT_PATHS"
    test -z "$(git diff --name-only --diff-filter=U)"
    generated_conflicts_resolved=true
    conflict_summary="$(paste -sd, "$CONFLICT_PATHS")"
  fi
  git commit -m "merge(autonomy): integrate main into PR ${PR_NUMBER} before deterministic repair"
  merge_created=true
fi

test -z "$(git status --porcelain=v1 --untracked-files=all)"
python3 -B tools/qikvrt_autonomous_self_heal.py apply > "$REPAIR_RESULT"
cat "$REPAIR_RESULT"
parse_repair_result

if test "$generated_conflicts_resolved" = true; then
  test -s "$REPAIR_PATHS"
  assert_conflicts_regenerated
fi

if test -s "$REPAIR_PATHS"; then
  python3 -B tools/qikvrt_anticipation.py check
  python3 -B tools/qikvrt_publication_overview.py check
  python3 -B tools/qikvrt_integrity.py verify
  python3 -B -m unittest -v \
    tests.test_qikvrt_publication_overview \
    tests.test_qikvrt_autonomous_self_heal \
    tests.test_qikvrt_autonomous_pr_continuation
  mapfile -t changed_paths < "$REPAIR_PATHS"
  git add -- "${changed_paths[@]}"
  actual_staged="$(git diff --cached --name-only | sort)"
  expected_staged="$(sort "$REPAIR_PATHS")"
  test "$actual_staged" = "$expected_staged"
  test -z "$(git status --porcelain=v1 | grep '^??' || true)"
  git commit -m "fix(autonomy): repair exact PR ${PR_NUMBER} repository projections"
fi

if test "$merge_created" = false && ! test -s "$REPAIR_PATHS"; then
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  echo "NOOP: PR ${PR_NUMBER} is already current and deterministic projections are clean."
  exit 0
fi

make test
python3 -B tools/qikvrt_publication_overview.py check
python3 -B tools/qikvrt_integrity.py verify

test -z "$(git status --porcelain=v1 --untracked-files=all)"
candidate_head="$(git rev-parse --verify HEAD^{commit})"
live_main_before_push="$(gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/main" --jq '.object.sha')"
test "$live_main_before_push" = "$live_main"
live_head_before_push="$(gh api "repos/${GITHUB_REPOSITORY}/pulls/${PR_NUMBER}" --jq '.head.sha')"
test "$live_head_before_push" = "$EXPECTED_HEAD"

git push origin "HEAD:refs/heads/${HEAD_REF}"

gh api --method POST "repos/${GITHUB_REPOSITORY}/statuses/${candidate_head}" \
  -f state=pending \
  -f context='QIKVRT autonomous exact-head verification' \
  -f description='Exact repaired head awaits repository-dispatch re-verification' \
  -f target_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

python3 -B - "$DISPATCH_JSON" "$GITHUB_REPOSITORY" "$PR_NUMBER" "$HEAD_REF" "$candidate_head" "$EXPECTED_HEAD" "$live_main" <<'PY'
import json
import pathlib
import sys

output, repository, pr_number, head_ref, head_sha, source_head, base_sha = sys.argv[1:]
value = {
    'event_type': 'qikvrt_autonomous_exact_head_verify',
    'client_payload': {
        'repository': repository,
        'pull_request': int(pr_number),
        'head_ref': head_ref,
        'head_sha': head_sha,
        'source_head_sha': source_head,
        'base_sha': base_sha,
    },
}
pathlib.Path(output).write_text(json.dumps(value) + '\n', encoding='utf-8')
PY

gh api --method POST "repos/${GITHUB_REPOSITORY}/dispatches" --input "$DISPATCH_JSON"

cat > "$COMMENT_FILE" <<EOF_COMMENT
<!-- qikvrt-autonomous-pr-continuation -->
Autonomous deterministic continuation materialized a history-preserving successor.

- previous exact head: \`${EXPECTED_HEAD}\`
- current candidate head: \`${candidate_head}\`
- current main merged: \`${live_main}\`
- generated projection conflicts regenerated: \`${generated_conflicts_resolved}\`
- conflict paths: \`${conflict_summary}\`
- external effects: none
- next state: exact-head repository-dispatch verification

Human scientific review and any separately authorized publication effect remain independent downstream gates. No repository-wide PASS, FINAL_PASS, or EFFECT_ACK_DONE is claimed.
EOF_COMMENT

gh pr comment "$PR_NUMBER" --body-file "$COMMENT_FILE"
