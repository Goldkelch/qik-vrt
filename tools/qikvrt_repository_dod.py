# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Pure fail-closed repository-wide QIK-VRT Definition-of-Done evaluator."""

import json
import sys

PR_DISPOSITIONS = {"MERGE", "SUPERSEDE", "CLOSE_AS_REDUNDANT", "REJECT_WITH_EVIDENCE"}
BRANCH_DISPOSITIONS = {"MERGED", "SUPERSEDED", "REDUNDANT", "HISTORICAL/RETAINED_BY_POLICY"}


def _bool(value):
    return value is True


def evaluate(observation):
    required = {
        "repository", "main_head", "main_tree", "inventory_complete", "queue_empty",
        "open_issues", "pull_requests", "branches", "known_productive_defects",
        "all_productive_changes_on_main", "main_validation", "effect_readback",
        "ruleset_current"
    }
    missing = sorted(required.difference(observation))
    if missing:
        return _hold("INCOMPLETE_OBSERVATION_ENVELOPE", missing=missing)
    if observation["repository"] != "Goldkelch/qik-vrt":
        return _hold("WRONG_REPOSITORY")
    if not observation["main_head"] or not observation["main_tree"]:
        return _hold("UNBOUND_MAIN")
    if not _bool(observation["inventory_complete"]):
        return _hold("INVENTORY_INCOMPLETE")

    blockers = []
    if not _bool(observation["queue_empty"]):
        blockers.append("PRODUCTIVE_QUEUE_NONEMPTY")
    if observation["open_issues"]:
        blockers.append("OPEN_ISSUE_EXISTS")

    prs = observation["pull_requests"]
    if any(p.get("state") == "open" and p.get("disposition") not in PR_DISPOSITIONS for p in prs):
        blockers.append("OPEN_PULL_REQUEST_UNREGARDED")
    if any(p.get("state") == "open" for p in prs):
        blockers.append("OPEN_PULL_REQUEST_EXISTS")

    branches = observation["branches"]
    if any(b.get("name") != "main" and b.get("disposition") not in BRANCH_DISPOSITIONS for b in branches):
        blockers.append("UNCLASSIFIED_BRANCH_EXISTS")
    if observation["known_productive_defects"]:
        blockers.append("KNOWN_PRODUCTIVE_DEFECT_EXISTS")
    if not _bool(observation["all_productive_changes_on_main"]):
        blockers.append("PRODUCTIVE_CHANGE_OUTSIDE_MAIN_EXISTS")
    if not _bool(observation["ruleset_current"]):
        blockers.append("AUTHORITY_CONTROL_PLANE_DRIFT")

    validation = observation["main_validation"]
    if not (_bool(validation.get("fresh")) and validation.get("head") == observation["main_head"]
            and validation.get("tree") == observation["main_tree"] and validation.get("state") == "PASS"):
        blockers.append("EXACT_MAIN_VALIDATION_MISSING_OR_STALE")

    effect = observation["effect_readback"]
    if not (_bool(effect.get("fresh")) and effect.get("head") == observation["main_head"]
            and effect.get("tree") == observation["main_tree"]
            and effect.get("effect_ack") == "EFFECT_ACK_DONE"
            and _bool(effect.get("observed"))):
        blockers.append("EFFECT_READBACK_MISSING_STALE_OR_WRONG_MAIN")

    if blockers:
        ordered = list(dict.fromkeys(blockers))
        return {
            "schema": "qikvrt_repository_dod_evaluation_v1",
            "state": "CONTINUE",
            "done": False,
            "noop_allowed": False,
            "effect_ack_done": False,
            "first_unsatisfied": ordered[0],
            "blockers": ordered,
            "main_head": observation["main_head"],
            "main_tree": observation["main_tree"]
        }
    return {
        "schema": "qikvrt_repository_dod_evaluation_v1",
        "state": "DONE",
        "done": True,
        "noop_allowed": True,
        "effect_ack_done": True,
        "first_unsatisfied": None,
        "blockers": [],
        "main_head": observation["main_head"],
        "main_tree": observation["main_tree"]
    }


def _hold(reason, **extra):
    result = {
        "schema": "qikvrt_repository_dod_evaluation_v1",
        "state": "HOLD_UNVERIFIED",
        "done": False,
        "noop_allowed": False,
        "effect_ack_done": False,
        "first_unsatisfied": reason,
        "blockers": [reason]
    }
    result.update(extra)
    return result


def main():
    observation = json.load(sys.stdin)
    json.dump(evaluate(observation), sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
