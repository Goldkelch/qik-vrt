#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

POLICY_PATH = Path("policy/PERFECT_OPTIMUM_V1.json")


def load_policy(path: Path = POLICY_PATH):
    return json.loads(path.read_text(encoding="utf-8"))


def compare_metrics(before, after, policy):
    metrics = {m["id"]: m for m in policy["bound_metrics"]}
    non_regression = True
    strict_progress = False
    findings = []
    for metric_id, spec in metrics.items():
        if metric_id not in before or metric_id not in after:
            findings.append(f"MISSING_METRIC:{metric_id}")
            non_regression = False
            continue
        b, a = before[metric_id], after[metric_id]
        direction = spec["direction"]
        if direction == "minimize":
            if a > b:
                non_regression = False
                findings.append(f"REGRESSION:{metric_id}:{b}->{a}")
            elif a < b:
                strict_progress = True
        elif direction == "maximize":
            if a < b:
                non_regression = False
                findings.append(f"REGRESSION:{metric_id}:{b}->{a}")
            elif a > b:
                strict_progress = True
        elif direction == "exact":
            target = spec["target"]
            if a != target:
                non_regression = False
                findings.append(f"TARGET_VIOLATION:{metric_id}:{a}!={target}")
            if b != target and a == target:
                strict_progress = True
        else:
            non_regression = False
            findings.append(f"UNKNOWN_DIRECTION:{metric_id}:{direction}")
    return non_regression, strict_progress, findings


def evaluate(before, after, invariant_checks, policy):
    invariants_ok = all(bool(v) for v in invariant_checks.values())
    non_regression, strict_progress, findings = compare_metrics(before, after, policy)
    if not invariants_ok:
        findings.extend(f"INVARIANT_FAILED:{k}" for k, v in invariant_checks.items() if not v)
    decision = "ACCEPT_CANDIDATE" if invariants_ok and non_regression and strict_progress else "HOLD"
    return {
        "schema": "qikvrt_perfect_optimum_evaluation_v1",
        "decision": decision,
        "invariants_ok": invariants_ok,
        "non_regression": non_regression,
        "strict_progress": strict_progress,
        "findings": findings,
        "before": before,
        "after": after,
    }


def self_check(policy):
    required = {
        "schema", "hard_invariants", "improvement_order", "bound_metrics",
        "recursive_application", "registered_improvers", "decision"
    }
    missing = sorted(required - set(policy))
    registered = {x["id"] for x in policy.get("registered_improvers", [])}
    return {
        "schema": "qikvrt_perfect_optimum_self_check_v1",
        "policy_complete": not missing,
        "missing_keys": missing,
        "registered_improvers": sorted(registered),
        "arbitrary_source_self_modification": policy["recursive_application"].get("arbitrary_source_self_modification"),
        "self_application_safe": (
            not missing
            and policy["recursive_application"].get("candidate_must_evaluate_itself_under_same_rule") is True
            and policy["recursive_application"].get("post_effect_reobservation_required") is True
            and policy["recursive_application"].get("predecessor_evidence_transfer") is False
            and policy["recursive_application"].get("arbitrary_source_self_modification") == "HOLD"
            and "integrity_trio_materializer" in registered
        )
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--before")
    parser.add_argument("--after")
    parser.add_argument("--invariants")
    args = parser.parse_args()
    policy = load_policy()
    if args.self_check:
        result = self_check(policy)
    else:
        if not (args.before and args.after and args.invariants):
            parser.error("--before, --after and --invariants are required unless --self-check is used")
        result = evaluate(
            json.loads(Path(args.before).read_text()),
            json.loads(Path(args.after).read_text()),
            json.loads(Path(args.invariants).read_text()),
            policy,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result.get("self_application_safe", result.get("decision") == "ACCEPT_CANDIDATE") else 1)


if __name__ == "__main__":
    main()
