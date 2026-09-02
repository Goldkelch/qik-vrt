#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministically classify open main-targeting PRs after trusted-main advances.

This observer is intentionally narrow. It does not mutate candidate branches, merge,
approve, publish, or transfer predecessor evidence. It only compares the exact base
commit recorded by GitHub for each open role-local PR with the exact current main
commit and emits a machine-readable BASE_DRIFT disposition when they differ.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Mapping, Sequence


class BaseDriftObservationError(ValueError):
    pass


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise BaseDriftObservationError(f"{label} is not a lowercase Git SHA-1")
    return value


def classify_pull_request(repository: str, current_main_sha: str, pull_request: Mapping[str, Any]) -> dict[str, Any]:
    main = _sha(current_main_sha, "current_main_sha")
    number = pull_request.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise BaseDriftObservationError("pull request number is invalid")
    if pull_request.get("state") != "open":
        raise BaseDriftObservationError("pull request is not open")
    base = pull_request.get("base")
    head = pull_request.get("head")
    if not isinstance(base, Mapping) or not isinstance(head, Mapping):
        raise BaseDriftObservationError("pull request lacks exact Git bindings")
    if base.get("ref") != "main":
        return {
            "schema": "qikvrt_base_drift_observation_v1",
            "repository": repository,
            "pr_number": number,
            "state": "NOOP_NON_MAIN_BASE",
            "first_blocker": None,
            "next_action": "NOOP",
            "productive_effect": False,
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "MERGE": False},
        }
    base_sha = _sha(base.get("sha"), "base.sha")
    head_sha = _sha(head.get("sha"), "head.sha")
    head_repo = head.get("repo")
    head_repo_name = head_repo.get("full_name") if isinstance(head_repo, Mapping) else None
    if head_repo_name != repository:
        return {
            "schema": "qikvrt_base_drift_observation_v1",
            "repository": repository,
            "pr_number": number,
            "head_sha": head_sha,
            "base_sha": base_sha,
            "current_main_sha": main,
            "state": "HOLD_UNTRUSTED_HEAD_REPOSITORY",
            "first_blocker": "HEAD_REPOSITORY_NOT_ROLE_LOCAL",
            "next_action": "HOLD",
            "productive_effect": False,
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "MERGE": False},
        }
    drift = base_sha != main
    return {
        "schema": "qikvrt_base_drift_observation_v1",
        "repository": repository,
        "pr_number": number,
        "head_sha": head_sha,
        "base_sha": base_sha,
        "current_main_sha": main,
        "state": "HOLD_UNVERIFIED" if drift else "CURRENT_BASE",
        "first_blocker": "BASE_DRIFT" if drift else None,
        "detail": f"base {base_sha} != current main {main}" if drift else f"base {base_sha} == current main {main}",
        "next_action": "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN" if drift else "NOOP",
        "productive_effect": False,
        "candidate_branch_mutation": False,
        "evidence_transfer_allowed": False,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "MERGE": False},
    }


def classify_all(repository: str, current_main_sha: str, pull_requests: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    observations = [classify_pull_request(repository, current_main_sha, pr) for pr in pull_requests]
    observations.sort(key=lambda item: int(item["pr_number"]))
    return observations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--current-main", required=True)
    parser.add_argument("--pull-requests-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raw = json.load(open(args.pull_requests_json, encoding="utf-8"))
    if not isinstance(raw, list):
        raise BaseDriftObservationError("pull request input must be a list")
    result = {
        "schema": "qikvrt_base_drift_observation_set_v1",
        "repository": args.repository,
        "current_main_sha": _sha(args.current_main, "current_main_sha"),
        "observations": classify_all(args.repository, args.current_main, raw),
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "MERGE": False},
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
