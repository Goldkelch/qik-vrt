#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# Executable positive and fail-closed contract tests for the adaptive runtime.

set -euo pipefail

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(git -C "$script_dir/.." rev-parse --show-toplevel)
runtime="$root/tools/qikvrt_adaptive_runtime.sh"
policy="$root/policy/COLLECTIVE_ADAPTIVE_COGNITION.json"

mkdir -p "$root/.qikvrt/runtime" "$root/.qikvrt/evidence/collective-adaptive"
scratch=$(mktemp -d "$root/.qikvrt/runtime/adaptive-test.XXXXXX")
test_run_prefix="test-adaptive-${scratch##*.}"
outputs=()

cleanup() {
  local item
  case "$scratch" in
    "$root"/.qikvrt/runtime/adaptive-test.*) rm -rf -- "$scratch" ;;
    *) echo "refusing unsafe scratch cleanup: $scratch" >&2 ;;
  esac
  for item in "${outputs[@]}"; do
    case "$item" in
      "$root"/.qikvrt/evidence/collective-adaptive/test-adaptive-*) rm -rf -- "$item" ;;
      *) echo "refusing unsafe output cleanup: $item" >&2 ;;
    esac
  done
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

make_observation() {
  local path=$1
  local observation_id=$2
  local observer_id=$3
  local description=$4
  python3 -B - "$path" "$observation_id" "$observer_id" "$description" <<'PY'
import json
from pathlib import Path
import sys

path, observation_id, observer_id, description = sys.argv[1:]
document = {
    "schema": "qikvrt_collective_observation_v1",
    "observation_id": observation_id,
    "observer_id": observer_id,
    "subject": "bounded-test-subject",
    "measured_at_utc": "2026-07-22T18:00:00Z",
    "measurements": [
        {
            "name": "verified_cases",
            "value": 2,
            "unit": "count",
            "method": "deterministic fixture count",
        }
    ],
    "findings": [
        {
            "finding_id": "bounded-result",
            "statement": "The bounded fixture was measured.",
            "status": "PASS",
            "measurement_refs": ["verified_cases"],
        }
    ],
    "recommendations": [
        {
            "proposal_id": "review-bounded-change",
            "description": description,
            "rationale": "The measured scope is bounded and still requires review.",
            "risk": "LOW",
            "finding_refs": ["bounded-result"],
        }
    ],
    "limitations": ["Fixture evidence does not authorize a repository effect."],
}
Path(path).write_text(
    json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY
}

expect_block() {
  local label=$1
  local observations=$2
  local output=$3
  outputs+=("$output")
  if "$runtime" --observations "$observations" --output "$output" >"$scratch/$label.stdout" 2>"$scratch/$label.stderr"; then
    fail "$label unexpectedly succeeded"
  fi
  grep -q '^BLOCK:' "$scratch/$label.stderr" || fail "$label did not return a fail-closed diagnostic"
  [[ ! -e "$output" ]] || fail "$label created an output directory"
}

[[ -x "$runtime" ]] || fail "runtime is not executable"
python3 -B -m json.tool "$policy" >/dev/null
bash -n "$runtime" "$0"

tracked_before=$(git -C "$root" status --porcelain=v1 --untracked-files=no)

happy="$scratch/happy"
mkdir -p "$happy"
sentinel="$scratch/observation-content-was-executed"
literal_proposal='Review literal data: $(touch '"$sentinel"') and `false`.'
make_observation "$happy/observer-a.json" "observation-a" "observer-a" "$literal_proposal"
make_observation "$happy/observer-b.json" "observation-b" "observer-b" "$literal_proposal"

symlink_root="$scratch/symlink-root-repository"
symlink_target="$scratch/symlink-root-target"
fake_bin="$scratch/fake-bin"
mkdir -p \
  "$symlink_root/policy" \
  "$symlink_root/tools" \
  "$symlink_root/.qikvrt/evidence" \
  "$symlink_target" \
  "$fake_bin"
cp "$policy" "$symlink_root/policy/COLLECTIVE_ADAPTIVE_COGNITION.json"
cp "$runtime" "$symlink_root/tools/qikvrt_adaptive_runtime.sh"
ln -s "$symlink_target" "$symlink_root/.qikvrt/evidence/collective-adaptive"
python3 -B - "$fake_bin/git" <<'PY'
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(
    "#!/bin/sh\nprintf '%s\\n' \"$QIKVRT_FAKE_ROOT\"\n",
    encoding="utf-8",
)
PY
chmod +x "$fake_bin/git"
if PATH="$fake_bin:$PATH" QIKVRT_FAKE_ROOT="$symlink_root" \
  "$runtime" \
    --observations "$happy" \
    --output "$symlink_root/.qikvrt/evidence/collective-adaptive/symlink-run" \
    >"$scratch/symlink-root.stdout" 2>"$scratch/symlink-root.stderr"; then
  fail "symlinked allowed root unexpectedly succeeded"
fi
grep -q '^BLOCK:' "$scratch/symlink-root.stderr" || fail "symlinked allowed root did not block"
[[ ! -e "$symlink_target/symlink-run" ]] || fail "symlinked allowed root escaped repository confinement"

for required_prohibition in \
  open_or_modify_pull_request \
  network_write \
  auto_install_or_update; do
  policy_case="$scratch/policy-$required_prohibition"
  mkdir -p "$policy_case/policy" "$policy_case/tools"
  cp "$policy" "$policy_case/policy/COLLECTIVE_ADAPTIVE_COGNITION.json"
  cp "$runtime" "$policy_case/tools/qikvrt_adaptive_runtime.sh"
  python3 -B - \
    "$policy_case/policy/COLLECTIVE_ADAPTIVE_COGNITION.json" \
    "$required_prohibition" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
prohibition = sys.argv[2]
document = json.loads(path.read_text(encoding="utf-8"))
document["forbidden_actions"].remove(prohibition)
path.write_text(
    json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY
  policy_output="$policy_case/.qikvrt/evidence/collective-adaptive/policy-test"
  if PATH="$fake_bin:$PATH" QIKVRT_FAKE_ROOT="$policy_case" \
    "$policy_case/tools/qikvrt_adaptive_runtime.sh" \
      --observations "$happy" \
      --output "$policy_output" \
      >"$scratch/policy-$required_prohibition.stdout" \
      2>"$scratch/policy-$required_prohibition.stderr"; then
    fail "weakened policy without $required_prohibition unexpectedly succeeded"
  fi
  grep -q '^BLOCK:' "$scratch/policy-$required_prohibition.stderr" || \
    fail "weakened policy without $required_prohibition did not block"
  [[ ! -e "$policy_output" ]] || \
    fail "weakened policy without $required_prohibition created output"
done

happy_output="$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-happy"
outputs+=("$happy_output")
"$runtime" \
  --observations "$happy" \
  --output "$happy_output" \
  --run-id "${test_run_prefix}-happy" >"$scratch/happy.stdout"

[[ ! -e "$sentinel" ]] || fail "observation text was executed"
[[ -f "$happy_output/evidence.json" ]] || fail "evidence.json missing"
[[ -f "$happy_output/proposal.json" ]] || fail "proposal.json missing"
[[ $(find "$happy_output" -mindepth 1 -maxdepth 1 -type f | wc -l) -eq 2 ]] || fail "unexpected runtime output"

python3 -B - "$happy_output/evidence.json" "$happy_output/proposal.json" "$happy/observer-a.json" "$happy/observer-b.json" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

evidence_path, proposal_path, *observation_paths = map(Path, sys.argv[1:])
evidence_payload = evidence_path.read_bytes()
evidence = json.loads(evidence_payload)
proposal = json.loads(proposal_path.read_text(encoding="utf-8"))

def require(condition, message):
    if not condition:
        raise SystemExit(message)

require(proposal["mode"] == "MEASURE_HASH_PROPOSE_ONLY", "wrong mode")
require(proposal["effect_ack"]["state"] == "EFFECT_ACK_CONTINUE", "false DONE state")
require(proposal["effect_ack"]["ordinary_release"] is False, "ordinary release enabled")
require(proposal["effect_ack"]["runtime_may_issue_done"] is False, "runtime may issue DONE")
require(proposal["human_review"] == {
    "completed": False,
    "required": True,
    "runtime_may_approve": False,
}, "human review boundary changed")
require(len(proposal["mandatory_checks"]) == 8, "mandatory check set changed")
require(all(item["status"] == "PENDING_SEPARATE_REVIEW" for item in proposal["mandatory_checks"]), "check falsely completed")
summary = proposal["collective_summary"]
require(summary["distinct_observer_identifier_count"] == 2, "observer identifier count mismatch")
require(summary["organizational_independence_verified"] is False, "organizational independence falsely verified")
require(summary["causal_independence_verified"] is False, "causal independence falsely verified")
require(summary["person_identity_verified"] is False, "person identity falsely verified")
require(summary["observer_identifier_authentication_verified"] is False, "observer identifier authentication falsely verified")
require(summary["consensus_claimed"] is False, "consensus falsely claimed")
require(proposal["limitations"]["independence_verified"] is False, "output limitation missing")
require(proposal["proposals"][0]["supporting_observer_identifier_count"] == 2, "identifier support count mismatch")
require(proposal["proposals"][0]["content_match"] is True, "identical proposal content marked conflicting")
require(proposal["evidence_sha256"] == hashlib.sha256(evidence_payload).hexdigest(), "evidence binding mismatch")

recorded = {item["file"]: item["sha256"] for item in evidence["observations"]}
for path in observation_paths:
    require(recorded[path.name] == hashlib.sha256(path.read_bytes()).hexdigest(), f"input hash mismatch: {path.name}")
PY

conflict="$scratch/conflict"
mkdir -p "$conflict"
make_observation "$conflict/a.json" "conflict-a" "observer-a" "Review variant A."
make_observation "$conflict/b.json" "conflict-b" "observer-b" "Review variant B."
conflict_output="$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-conflict"
outputs+=("$conflict_output")
"$runtime" --observations "$conflict" --output "$conflict_output" >"$scratch/conflict.stdout"
python3 -B - "$conflict_output/proposal.json" <<'PY'
import json
from pathlib import Path
import sys

proposal = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
group = proposal["proposals"][0]
if group["content_match"] is not False or len(group["variants"]) != 2:
    raise SystemExit("proposal disagreement was not preserved")
if proposal["collective_summary"]["conflicting_proposal_ids"] != ["review-bounded-change"]:
    raise SystemExit("conflict summary mismatch")
if proposal["effect_ack"]["state"] != "EFFECT_ACK_CONTINUE":
    raise SystemExit("conflict changed the fail-closed effect state")
PY

single="$scratch/single"
mkdir -p "$single"
make_observation "$single/one.json" "single-observation" "single-observer" "Review a single observation."
expect_block "single-observer" "$single" "$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-single"

duplicate="$scratch/duplicate-observer"
mkdir -p "$duplicate"
make_observation "$duplicate/a.json" "duplicate-a" "same-observer" "Review duplicate attribution."
make_observation "$duplicate/b.json" "duplicate-b" "same-observer" "Review duplicate attribution."
expect_block "duplicate-observer" "$duplicate" "$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-duplicate"

executable="$scratch/executable-field"
mkdir -p "$executable"
make_observation "$executable/a.json" "executable-a" "observer-a" "Review executable field rejection."
make_observation "$executable/b.json" "executable-b" "observer-b" "Review executable field rejection."
python3 -B - "$executable/b.json" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
document = json.loads(path.read_text(encoding="utf-8"))
document["auto_apply"] = True
path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
PY
expect_block "executable-field" "$executable" "$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-executable"

bad_ref="$scratch/bad-ref"
mkdir -p "$bad_ref"
make_observation "$bad_ref/a.json" "bad-ref-a" "observer-a" "Review bad reference rejection."
make_observation "$bad_ref/b.json" "bad-ref-b" "observer-b" "Review bad reference rejection."
python3 -B - "$bad_ref/b.json" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
document = json.loads(path.read_text(encoding="utf-8"))
document["findings"][0]["measurement_refs"] = ["not-measured"]
path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
PY
expect_block "bad-reference" "$bad_ref" "$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-bad-ref"

symlink_case="$scratch/symlink"
mkdir -p "$symlink_case"
make_observation "$scratch/symlink-target.json" "symlink-a" "observer-a" "Review symlink rejection."
ln -s "$scratch/symlink-target.json" "$symlink_case/a.json"
expect_block "symlink" "$symlink_case" "$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-symlink"

outside="$scratch/outside-output"
if "$runtime" --observations "$happy" --output "$outside" >"$scratch/outside.stdout" 2>"$scratch/outside.stderr"; then
  fail "outside output unexpectedly succeeded"
fi
grep -q '^BLOCK:' "$scratch/outside.stderr" || fail "outside output did not block"
[[ ! -e "$outside" ]] || fail "outside output path was created"

existing="$root/.qikvrt/evidence/collective-adaptive/${test_run_prefix}-existing"
outputs+=("$existing")
mkdir -p "$existing"
if "$runtime" --observations "$happy" --output "$existing" >"$scratch/existing.stdout" 2>"$scratch/existing.stderr"; then
  fail "existing output unexpectedly succeeded"
fi
grep -q '^BLOCK:' "$scratch/existing.stderr" || fail "existing output did not block"

tracked_after=$(git -C "$root" status --porcelain=v1 --untracked-files=no)
[[ "$tracked_after" == "$tracked_before" ]] || fail "tracked repository state changed"

echo "PASS: collective adaptive runtime contract and negative controls"
