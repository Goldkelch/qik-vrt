# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Pure fail-closed repository-wide QIK-VRT Definition-of-Done evaluator."""

from __future__ import annotations

import json
import sys

PR_DISPOSITIONS = {"MERGE", "SUPERSEDE", "CLOSE_AS_REDUNDANT", "REJECT_WITH_EVIDENCE"}
BRANCH_DISPOSITIONS = {"MERGED", "SUPERSEDED", "REDUNDANT", "HISTORICAL/RETAINED_BY_POLICY", "PRODUCTIVE_CURRENT_CANDIDATE", "PRODUCTIVE_UNMERGED"}
ORDER = (
    "ZERO_BUGS",
    "ALL_PULL_REQUESTS_REGARDED",
    "ALL_BRANCHES_REGARDED",
    "ALL_PRODUCTIVE_BRANCHES_MERGED",
    "FRESH_EXACT_MAIN_VALIDATION_PASS",
    "FRESH_EXACT_MAIN_EFFECT_READBACK",
)


def _bool(value):
    return value is True


def _exact_subject(value, head, tree):
    return (
        isinstance(value, dict)
        and _bool(value.get("fresh"))
        and value.get("head") == head
        and value.get("tree") == tree
    )


def evaluate(observation):
    required = {
        "repository",
        "subject_head",
        "subject_tree",
        "inventory_complete",
        "zero_bugs",
        "pull_requests",
        "branches",
        "all_productive_branches_merged",
        "main_validation",
        "effect_readback",
    }
    missing = sorted(required.difference(observation))
    if missing:
        return _hold("INCOMPLETE_OBSERVATION_ENVELOPE", missing=missing)
    if observation["repository"] != "Goldkelch/qik-vrt":
        return _hold("WRONG_REPOSITORY")

    head = observation["subject_head"]
    tree = observation["subject_tree"]
    if not isinstance(head, str) or len(head) != 40 or not isinstance(tree, str) or len(tree) != 40:
        return _hold("UNBOUND_SUBJECT")
    if not _bool(observation["inventory_complete"]):
        return _hold("INVENTORY_INCOMPLETE", subject_head=head, subject_tree=tree)

    zero = observation["zero_bugs"]
    zero_ok = (
        _exact_subject(zero, head, tree)
        and zero.get("state") in {"ZERO_KNOWN_DETERMINISTIC_BUGS_LOCAL", "PASS"}
        and _bool(zero.get("known_deterministic_defects_zero"))
    )

    prs = observation["pull_requests"]
    prs_ok = (
        isinstance(prs, list)
        and all(isinstance(p, dict) and p.get("disposition") in PR_DISPOSITIONS for p in prs)
    )

    branches = observation["branches"]
    branches_ok = (
        isinstance(branches, list)
        and all(
            isinstance(b, dict)
            and (
                b.get("name") == "main"
                or b.get("disposition") in BRANCH_DISPOSITIONS
            )
            for b in branches
        )
    )

    productive_ok = _bool(observation["all_productive_branches_merged"])

    validation = observation["main_validation"]
    main_ok = (
        _exact_subject(validation, head, tree)
        and validation.get("state") == "PASS"
    )

    effect = observation["effect_readback"]
    effect_ok = (
        _exact_subject(effect, head, tree)
        and _bool(effect.get("observed"))
        and effect.get("effect_ack") == "EFFECT_ACK_DONE"
    )

    conjuncts = {
        "ZERO_BUGS": zero_ok,
        "ALL_PULL_REQUESTS_REGARDED": prs_ok,
        "ALL_BRANCHES_REGARDED": branches_ok,
        "ALL_PRODUCTIVE_BRANCHES_MERGED": productive_ok,
        "FRESH_EXACT_MAIN_VALIDATION_PASS": main_ok,
        "FRESH_EXACT_MAIN_EFFECT_READBACK": effect_ok,
    }
    blockers = [name for name in ORDER if not conjuncts[name]]
    done = not blockers
    return {
        "schema": "qikvrt_repository_dod_evaluation_v1",
        "state": "DONE" if done else "CONTINUE",
        "done": done,
        "effect_ack_done": done and effect_ok,
        "noop_evaluated": False,
        "noop_allowed": None,
        "conjuncts": conjuncts,
        "first_unsatisfied": blockers[0] if blockers else None,
        "blockers": blockers,
        "subject_head": head,
        "subject_tree": tree,
    }


def _hold(reason, **extra):
    result = {
        "schema": "qikvrt_repository_dod_evaluation_v1",
        "state": "HOLD_UNVERIFIED",
        "done": False,
        "effect_ack_done": False,
        "noop_evaluated": False,
        "noop_allowed": None,
        "conjuncts": None,
        "first_unsatisfied": reason,
        "blockers": [reason],
    }
    result.update(extra)
    return result


def main():
    observation = json.load(sys.stdin)
    json.dump(evaluate(observation), sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
