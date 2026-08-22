#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

POLICY = Path("policy/ZERO_BUG_CONTINUOUS_V1.json")


def load_policy():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def evaluate(observation, policy=None):
    policy = policy or load_policy()
    required = {
        "exact_head_and_tree_bound": bool(observation.get("exact_head_and_tree_bound")),
        "known_deterministic_defects_zero": observation.get("known_deterministic_defects", 1) == 0,
        "repository_integrity_verifies": bool(observation.get("repository_integrity_verifies")),
        "required_exact_head_gates_non_adverse": bool(observation.get("required_exact_head_gates_non_adverse")),
        "productive_writer_count_at_most_one": observation.get("productive_writer_count", 2) <= 1,
        "stale_evidence_reuse_zero": observation.get("stale_evidence_reuse", 1) == 0,
        "registered_improvers_only": bool(observation.get("registered_improvers_only")),
        "reobserve_after_every_mutation": bool(observation.get("reobserve_after_every_mutation")),
    }
    missing = [k for k in policy["hard_invariants"] if not required.get(k, False)]
    state = "ZERO_KNOWN_DETERMINISTIC_BUGS" if not missing else "HOLD_DEFECT_IDENTIFIED"
    return {
        "schema": "qikvrt_zero_bug_evaluation_v1",
        "state": state,
        "invariants": required,
        "failed_invariants": missing,
        "universal_bug_freedom_claimed": False,
    }


def self_check(policy=None):
    policy = policy or load_policy()
    return {
        "schema": "qikvrt_zero_bug_self_check_v1",
        "complete": all(k in policy for k in ("schema", "hard_invariants", "state_machine", "repair_order", "continuous_revision")),
        "after_mutation": policy["state_machine"].get("after_mutation"),
        "later_is_better": policy["continuous_revision"].get("later_is_better"),
        "arbitrary_unregistered_self_modification": policy["continuous_revision"].get("arbitrary_unregistered_self_modification"),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--self-check", action="store_true")
    p.add_argument("--observation")
    args = p.parse_args()
    if args.self_check:
        result = self_check()
        ok = result["complete"] and result["after_mutation"] == "HOLD_UNVERIFIED" and result["later_is_better"] is False
    else:
        if not args.observation:
            p.error("--observation required")
        result = evaluate(json.loads(Path(args.observation).read_text(encoding="utf-8")))
        ok = result["state"] == "ZERO_KNOWN_DETERMINISTIC_BUGS"
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
