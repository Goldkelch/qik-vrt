#!/usr/bin/env python3
import json
import sys


def evaluate(case):
    required = ["past", "current", "expected", "observed", "cause", "objective"]
    if any(k not in case for k in required):
        return {"status": "HOLD", "reason": "MISSING_REQUIRED_BINDING"}
    if not case["cause"]:
        return {"status": "HOLD", "reason": "CAUSE_NOT_BOUND"}
    if case["objective"] != "HIGHER_QUALITY_IS_BETTER":
        return {"status": "HOLD", "reason": "OBJECTIVE_NOT_BOUND"}

    past = case["past"]
    current = case["current"]
    expected = case["expected"]
    observed = case["observed"]

    later = observed["logical_time"] > current["logical_time"]
    expected_observed = observed["quality"] == expected["quality"]
    changed = observed["quality"] != current["quality"]
    improved = observed["quality"] > current["quality"]
    degraded = observed["quality"] < current["quality"]

    if expected_observed and improved:
        classification = "IMPROVEMENT_EVIDENCED"
    elif changed and degraded:
        classification = "CHANGED_DEGRADED"
    elif changed:
        classification = "CHANGED_NOT_PROVEN_BETTER"
    else:
        classification = "UNCHANGED"

    return {
        "status": "OBSERVED",
        "cause_bound": True,
        "past_to_current_bound": past["id"] != current["id"],
        "expected_equals_observed": expected_observed,
        "later": later,
        "changed": changed,
        "improved": improved,
        "degraded": degraded,
        "later_implies_better": False,
        "classification": classification,
    }


def main():
    data = json.load(sys.stdin)
    result = evaluate(data)
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result["status"] != "HOLD" else 2


if __name__ == "__main__":
    raise SystemExit(main())
