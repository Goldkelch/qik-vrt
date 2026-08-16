#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build a read-only terminal snapshot for autonomous self-heal observation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "qikvrt_self_heal_terminal_snapshot_v1"
TERMINAL_PATTERN = "QIKVRT_TERMINAL_PATTERN_V1"
REMOTE_MISMATCH = "canonical source remote URL mismatch"
REMOTE_REPAIR = "MATERIALIZE_POLICY_BOUND_CANONICAL_UPSTREAM_REMOTE"


def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _run(value: Mapping[str, Any]) -> Mapping[str, Any]:
    runs = value.get("workflow_runs")
    if isinstance(runs, list) and runs and isinstance(runs[0], Mapping):
        return runs[0]
    return value


def _jobs(value: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    jobs = value.get("jobs", [])
    if not isinstance(jobs, list):
        return []
    return [item for item in jobs if isinstance(item, Mapping)]


def _first_failed_step(jobs: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    for job in jobs:
        steps = job.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, Mapping) and step.get("conclusion") == "failure":
                return {
                    "job": job.get("name"),
                    "job_id": job.get("id"),
                    "step": step.get("name"),
                    "step_number": step.get("number"),
                }
    return None


def classify(self_heal_run: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    state = receipt.get("state")
    detail = receipt.get("detail")
    failure_class = receipt.get("failure_class")
    conclusion = self_heal_run.get("conclusion")

    if state == "HOLD" and detail == REMOTE_MISMATCH:
        return {
            "kind": "SOURCE_OR_WORKFLOW_CONTRACT_DEFECT",
            "expected_fail_closed_hold": True,
            "actual_defect": True,
            "first_deterministic_blocker": REMOTE_MISMATCH,
            "smallest_action": REMOTE_REPAIR,
            "administrator_action_required": False,
        }
    if state == "HOLD":
        return {
            "kind": "EXPECTED_FAIL_CLOSED_HOLD",
            "expected_fail_closed_hold": True,
            "actual_defect": False,
            "first_deterministic_blocker": detail or failure_class or "UNSPECIFIED_FAIL_CLOSED_HOLD",
            "smallest_action": "REOBSERVE_OR_REPAIR_THE_EXACT_REPORTED_PRECONDITION",
            "administrator_action_required": False,
        }
    if conclusion == "failure" and not receipt:
        return {
            "kind": "WORKFLOW_EVIDENCE_DEFECT",
            "expected_fail_closed_hold": False,
            "actual_defect": True,
            "first_deterministic_blocker": "FAILED_SELF_HEAL_RUN_WITHOUT_RECEIPT",
            "smallest_action": "RESTORE_FAIL_CLOSED_RECEIPT_PRESERVATION",
            "administrator_action_required": False,
        }
    return {
        "kind": "OBSERVE",
        "expected_fail_closed_hold": False,
        "actual_defect": False,
        "first_deterministic_blocker": None,
        "smallest_action": "NONE",
        "administrator_action_required": False,
    }


def build_snapshot(
    *,
    repository: str,
    observed_at: str,
    head: str,
    tree: str,
    self_heal_runs: Mapping[str, Any],
    self_heal_jobs: Mapping[str, Any],
    self_heal_receipt: Mapping[str, Any],
    watchdog_runs: Mapping[str, Any],
    watchdog_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    self_heal = _run(self_heal_runs)
    watchdog = _run(watchdog_runs)
    jobs = _jobs(self_heal_jobs)
    classification = classify(self_heal, self_heal_receipt)
    observations = watchdog_receipt.get("observations", {})
    leases = watchdog_receipt.get("leases", {})
    resource_graph = watchdog_receipt.get("resource_graph", {})

    if not isinstance(observations, Mapping):
        observations = {}
    if not isinstance(leases, Mapping):
        leases = {}
    if not isinstance(resource_graph, Mapping):
        resource_graph = {}

    return {
        "schema": SCHEMA,
        "terminal_pattern": TERMINAL_PATTERN,
        "repository": repository,
        "observed_at": observed_at,
        "main": {"head": head, "tree": tree},
        "self_heal": {
            "run": {
                "id": self_heal.get("id"),
                "run_number": self_heal.get("run_number"),
                "event": self_heal.get("event"),
                "status": self_heal.get("status"),
                "conclusion": self_heal.get("conclusion"),
                "head_sha": self_heal.get("head_sha"),
                "html_url": self_heal.get("html_url"),
            },
            "first_failed_step": _first_failed_step(jobs),
            "receipt": {
                "state": self_heal_receipt.get("state"),
                "failure_class": self_heal_receipt.get("failure_class"),
                "detail": self_heal_receipt.get("detail"),
                "completion_claims": self_heal_receipt.get("completion_claims", {}),
            },
        },
        "reflexive_watchdog": {
            "run": {
                "id": watchdog.get("id"),
                "run_number": watchdog.get("run_number"),
                "status": watchdog.get("status"),
                "conclusion": watchdog.get("conclusion"),
                "head_sha": watchdog.get("head_sha"),
                "html_url": watchdog.get("html_url"),
            },
            "state": watchdog_receipt.get("state"),
            "disposition": watchdog_receipt.get("disposition"),
            "first_blocker": watchdog_receipt.get("first_blocker"),
            "productive_edge": watchdog_receipt.get("productive_edge"),
        },
        "writer_lease": {
            "active_productive_runs": observations.get("active_productive_runs", []),
            "active_writers": observations.get("active_writers", []),
            "stale_writers": observations.get("stale_writers", []),
            "waiting_productive_runs": observations.get("waiting_productive_runs", []),
            "untrusted_terminal_runs": observations.get("untrusted_terminal_runs", []),
            "leases": dict(leases),
            "resource_graph": dict(resource_graph),
        },
        "classification": classification,
        "terminal_semantics": {
            "mode": "PASSIVE_MONITOR",
            "repository_writes": False,
            "effect_execution": False,
            "repository_to_client": "OBSERVATION_SNAPSHOT",
            "client_to_repository": "NONE",
            "bidirectional_terminal": "READ_PATH_ONLY_UNTIL_SEPARATELY_AUTHORIZED_ADAPTER_EXISTS",
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--observed-at", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--self-heal-runs", type=Path, required=True)
    parser.add_argument("--self-heal-jobs", type=Path, required=True)
    parser.add_argument("--self-heal-receipt", type=Path, required=True)
    parser.add_argument("--watchdog-runs", type=Path, required=True)
    parser.add_argument("--watchdog-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    snapshot = build_snapshot(
        repository=args.repository,
        observed_at=args.observed_at,
        head=args.head,
        tree=args.tree,
        self_heal_runs=_load(args.self_heal_runs),
        self_heal_jobs=_load(args.self_heal_jobs),
        self_heal_receipt=_load(args.self_heal_receipt),
        watchdog_runs=_load(args.watchdog_runs),
        watchdog_receipt=_load(args.watchdog_receipt),
    )
    text = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
