#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only, exact-head pre-deadlock analysis for every QIK-VRT repository instance.

The controller models repository writers and runner pressure as a bounded
resource-allocation graph.  It emits an evidence receipt before a circular wait
or stale writer lease is allowed to become the next repository action.  It does
not cancel jobs, dispatch workflows, mutate refs, merge pull requests, or treat
watchdog terminality as gate success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
ACTIVE_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
WAITING_STATUSES = frozenset({"queued", "waiting", "requested", "pending"})
UNTRUSTED_CONCLUSIONS = frozenset({"action_required", "startup_failure"})
EXECUTED_FAILURE_CONCLUSIONS = frozenset({"failure", "timed_out"})


class ReflexiveWatchdogBlock(RuntimeError):
    """A malformed or drifted observation that must fail closed."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReflexiveWatchdogBlock(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReflexiveWatchdogBlock(f"{label} must be a non-empty string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ReflexiveWatchdogBlock(f"{label} must be a positive integer")
    return value


def _timestamp(value: Any, label: str) -> datetime:
    text = _string(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReflexiveWatchdogBlock(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReflexiveWatchdogBlock(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    path = root / CONTRACT_RELATIVE_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReflexiveWatchdogBlock(f"cannot load workflow executor contract: {exc}") from exc
    contract = dict(_mapping(value, "workflow executor contract"))
    if contract.get("schema") != "qikvrt_workflow_executor_mesh_contract_v1":
        raise ReflexiveWatchdogBlock("workflow executor contract schema is not v1")
    prevention = _mapping(
        contract.get("reflexive_deadlock_prevention"),
        "reflexive deadlock prevention contract",
    )
    if prevention.get("enabled") is not True:
        raise ReflexiveWatchdogBlock("reflexive deadlock prevention is not enabled")
    if prevention.get("applies_to") != ["AUTHORITY", "MIRROR", "EVERY_FUTURE_MESH_NODE"]:
        raise ReflexiveWatchdogBlock("reflexive watchdog is not bound to every repository instance")
    if prevention.get("admission_policy") != "PREEMPTIVE_HOLD_BEFORE_SECOND_WRITER":
        raise ReflexiveWatchdogBlock("reflexive watchdog admission policy is not fail-closed")
    for key in (
        "writer_lease_seconds",
        "queue_lease_seconds",
        "progress_lease_seconds",
        "max_simultaneous_active_writers",
        "max_queued_productive_runs",
    ):
        _positive_int(prevention.get(key), f"reflexive deadlock prevention.{key}")
    return contract


def _runs(value: Mapping[str, Any] | Sequence[Any]) -> list[Mapping[str, Any]]:
    raw: Any = value.get("workflow_runs") if isinstance(value, Mapping) else value
    if not isinstance(raw, list):
        raise ReflexiveWatchdogBlock("workflow run observation must contain workflow_runs")
    return [item for item in raw if isinstance(item, Mapping)]


def _jobs_by_run(value: Mapping[str, Any] | None) -> dict[str, list[Mapping[str, Any]]]:
    if value is None:
        return {}
    raw = value.get("jobs_by_run", value)
    if not isinstance(raw, Mapping):
        raise ReflexiveWatchdogBlock("job observation must be an object keyed by run id")
    result: dict[str, list[Mapping[str, Any]]] = {}
    for run_id, jobs in raw.items():
        if not isinstance(run_id, str) or not isinstance(jobs, list):
            raise ReflexiveWatchdogBlock("job observation contains an invalid run entry")
        result[run_id] = [item for item in jobs if isinstance(item, Mapping)]
    return result


def load_jobs_directory(path: Path) -> dict[str, list[Mapping[str, Any]]]:
    result: dict[str, list[Mapping[str, Any]]] = {}
    if not path.exists():
        return result
    for item in sorted(path.glob("*.json")):
        try:
            value = json.loads(item.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ReflexiveWatchdogBlock(f"cannot load job observation {item.name}: {exc}") from exc
        jobs = _mapping(value, f"job observation {item.name}").get("jobs")
        if not isinstance(jobs, list):
            raise ReflexiveWatchdogBlock(f"job observation {item.name} does not contain jobs")
        result[item.stem] = [entry for entry in jobs if isinstance(entry, Mapping)]
    return result


def _run_time(run: Mapping[str, Any], field: str) -> datetime | None:
    value = run.get(field)
    if not isinstance(value, str) or not value:
        return None
    return _timestamp(value, f"run {run.get('id', '?')} {field}")


def _run_transition_time(run: Mapping[str, Any]) -> datetime:
    for field in ("updated_at", "run_started_at", "created_at"):
        value = _run_time(run, field)
        if value is not None:
            return value
    raise ReflexiveWatchdogBlock(f"run {run.get('id', '?')} has no transition timestamp")


def _run_created_time(run: Mapping[str, Any]) -> datetime:
    value = _run_time(run, "created_at")
    return value if value is not None else _run_transition_time(run)


def _age_seconds(now: datetime, transition: datetime) -> int:
    return max(0, int((now - transition).total_seconds()))


def _run_id(run: Mapping[str, Any]) -> str:
    value = run.get("id")
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str) and value:
        return value
    raise ReflexiveWatchdogBlock("workflow run has no usable id")


def _latest_by_name(runs: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        name = run.get("name")
        if not isinstance(name, str) or not name:
            continue
        current = latest.get(name)
        if current is None or (_run_created_time(run), _run_id(run)) > (
            _run_created_time(current),
            _run_id(current),
        ):
            latest[name] = run
    return sorted(latest.values(), key=lambda item: str(item.get("name")))


def _job_summary(jobs: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    summary = {
        "total": len(jobs),
        "queued": 0,
        "in_progress": 0,
        "success": 0,
        "skipped": 0,
        "executed_failures": 0,
        "other_terminal": 0,
    }
    for job in jobs:
        status = job.get("status")
        conclusion = job.get("conclusion")
        if status in WAITING_STATUSES:
            summary["queued"] += 1
        elif status == "in_progress":
            summary["in_progress"] += 1
        elif status == "completed":
            if conclusion == "success":
                summary["success"] += 1
            elif conclusion == "skipped":
                summary["skipped"] += 1
            elif conclusion in EXECUTED_FAILURE_CONCLUSIONS:
                summary["executed_failures"] += 1
            else:
                summary["other_terminal"] += 1
    return summary


def _normalize_run(run: Mapping[str, Any], jobs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "id": _run_id(run),
        "name": run.get("name"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "event": run.get("event"),
        "head_sha": run.get("head_sha"),
        "created_at": _iso(_run_created_time(run)),
        "updated_at": _iso(_run_transition_time(run)),
        "jobs": _job_summary(jobs),
    }


def _resource_graph(
    active_writers: Sequence[Mapping[str, Any]],
    waiting_productive: Sequence[Mapping[str, Any]],
    active_productive: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    writer_ids = [_run_id(run) for run in active_writers]
    waiting_ids = [_run_id(run) for run in waiting_productive]
    running_ids = [_run_id(run) for run in active_productive if run.get("status") == "in_progress"]
    return {
        "schema": "qikvrt_repository_resource_graph_v1",
        "resources": [
            {
                "resource": "REPOSITORY_WRITE_LEASE",
                "capacity": 1,
                "holders": writer_ids[:1],
                "conflicting_holders_or_requesters": writer_ids[1:],
            },
            {
                "resource": "RUNNER_CAPACITY",
                "capacity": "PLATFORM_MANAGED_UNKNOWN",
                "observed_holders": running_ids,
                "observed_waiters": waiting_ids,
            },
        ],
        "cycle_detected": False,
        "pre_cycle_conflict_detected": len(writer_ids) > 1,
    }


def analyze(
    runs_value: Mapping[str, Any] | Sequence[Any],
    jobs_value: Mapping[str, Any] | None,
    *,
    expected_head: str,
    expected_tree: str,
    repository: str,
    now: datetime,
    baseline: Mapping[str, Any] | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    contract = load_contract(root)
    prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
    writer_names = set(
        _mapping(contract["dispatch_policy"], "dispatch policy").get("writer_workflow_names", [])
    )
    observer_names = set(prevention.get("observer_workflow_names", []))
    if not writer_names or any(not isinstance(item, str) or not item for item in writer_names):
        raise ReflexiveWatchdogBlock("writer workflow names are invalid")
    if any(not isinstance(item, str) or not item for item in observer_names):
        raise ReflexiveWatchdogBlock("observer workflow names are invalid")

    runs = [run for run in _runs(runs_value) if run.get("head_sha") == expected_head]
    jobs_by_run = _jobs_by_run(jobs_value)
    normalized = [
        _normalize_run(run, jobs_by_run.get(_run_id(run), []))
        for run in sorted(runs, key=lambda item: (_run_created_time(item), _run_id(item)))
    ]
    productive = [run for run in runs if run.get("name") not in observer_names]
    active_productive = [run for run in productive if run.get("status") in ACTIVE_STATUSES]
    waiting_productive = [run for run in productive if run.get("status") in WAITING_STATUSES]
    active_writers = [
        run for run in runs if run.get("name") in writer_names and run.get("status") in ACTIVE_STATUSES
    ]

    writer_lease = _positive_int(prevention["writer_lease_seconds"], "writer lease")
    queue_lease = _positive_int(prevention["queue_lease_seconds"], "queue lease")
    progress_lease = _positive_int(prevention["progress_lease_seconds"], "progress lease")
    max_writers = _positive_int(
        prevention["max_simultaneous_active_writers"], "maximum simultaneous active writers"
    )
    max_queued = _positive_int(
        prevention["max_queued_productive_runs"], "maximum queued productive runs"
    )

    stale_writers = [
        {
            "id": _run_id(run),
            "name": run.get("name"),
            "age_seconds": _age_seconds(now, _run_transition_time(run)),
        }
        for run in active_writers
        if _age_seconds(now, _run_transition_time(run)) >= writer_lease
    ]
    queue_ages = [
        {
            "id": _run_id(run),
            "name": run.get("name"),
            "age_seconds": _age_seconds(now, _run_created_time(run)),
        }
        for run in waiting_productive
    ]
    stale_queue = [item for item in queue_ages if item["age_seconds"] >= queue_lease]

    latest = _latest_by_name(runs)
    untrusted = []
    for run in latest:
        if run.get("name") in observer_names or run.get("status") != "completed":
            continue
        run_jobs = jobs_by_run.get(_run_id(run), [])
        conclusion = run.get("conclusion")
        if conclusion in UNTRUSTED_CONCLUSIONS or not run_jobs:
            untrusted.append(
                {
                    "id": _run_id(run),
                    "name": run.get("name"),
                    "conclusion": conclusion,
                    "job_count": len(run_jobs),
                    "reason": (
                        "ACTION_REQUIRED_OR_STARTUP_FAILURE"
                        if conclusion in UNTRUSTED_CONCLUSIONS
                        else "ZERO_JOB_TERMINAL_RUN"
                    ),
                }
            )

    progress_material = [item for item in normalized if item["name"] not in observer_names]
    progress_fingerprint = sha256_bytes(canonical_json_bytes(progress_material))
    baseline_same = False
    baseline_age = None
    if baseline is not None:
        previous_fingerprint = baseline.get("progress_fingerprint")
        previous_observed = baseline.get("observed_at")
        if isinstance(previous_fingerprint, str) and isinstance(previous_observed, str):
            baseline_same = previous_fingerprint == progress_fingerprint
            baseline_age = _age_seconds(now, _timestamp(previous_observed, "baseline observed_at"))

    blocker: str | None = None
    state = "SAFE_PROGRESS"
    disposition = "OBSERVE"
    productive_edge = "CONTINUE_REFLEXIVE_OBSERVATION"
    safe_continuation = "Preserve one writer, exact-head evidence, and the five-minute observer cadence."

    if len(active_writers) > max_writers:
        state = "PREEMPTIVE_HOLD_COMPETING_WRITERS"
        blocker = "MORE_THAN_ONE_ACTIVE_REPOSITORY_WRITER"
        disposition = "HOLD"
        productive_edge = "SERIALIZE_TO_ONE_EXPECTED_HEAD_WRITER"
        safe_continuation = "Do not start or promote a second writer; retain only one exact-head-bound writer."
    elif stale_writers:
        state = "PREEMPTIVE_HOLD_STALE_WRITER_LEASE"
        blocker = "ACTIVE_WRITER_EXCEEDED_PROGRESS_LEASE"
        disposition = "HOLD"
        productive_edge = "REOBSERVE_STALE_WRITER_JOBS_STEPS_AND_RECEIPT"
        safe_continuation = "Keep the writer lease exclusive and diagnose its first deterministic stalled step."
    elif active_productive and baseline_same and baseline_age is not None and baseline_age >= progress_lease:
        state = "PREEMPTIVE_HOLD_NO_PROGRESS_TRANSITION"
        blocker = "ACTIVE_TOPOLOGY_UNCHANGED_BEYOND_PROGRESS_LEASE"
        disposition = "HOLD"
        productive_edge = "REOBSERVE_EXACT_RUN_JOBS_BEFORE_ANY_NEW_WRITER"
        safe_continuation = "Coalesce observers and require a new job or step transition before admitting work."
    elif len(waiting_productive) > max_queued or stale_queue:
        state = "PREEMPTIVE_HOLD_QUEUE_PRESSURE"
        blocker = "RUNNER_QUEUE_EXCEEDED_PREVENTION_THRESHOLD"
        disposition = "HOLD"
        productive_edge = "COALESCE_OBSERVERS_AND_PRESERVE_WRITER_SERIALIZATION"
        safe_continuation = "Cancel only superseded observer runs; do not add another productive writer."
    elif untrusted:
        state = "UNTRUSTED_EXECUTION_GAP"
        blocker = "LATEST_TERMINAL_RUN_LACKS_TRUSTED_JOB_EVIDENCE"
        disposition = "HOLD"
        productive_edge = "OBTAIN_TRUSTED_EXACT_HEAD_JOB_EVIDENCE"
        safe_continuation = "Use a repository-declared trusted exact-head verification path; do not infer success."
    elif not active_productive:
        state = "QUIESCENT_OBSERVATION"
        productive_edge = "KEEP_REFLEXIVE_OBSERVER_FRESH"
        safe_continuation = "Continue periodic observation; quiescence is not a PIPELINE_EMPTY claim."

    resource_graph = _resource_graph(active_writers, waiting_productive, active_productive)
    observed_at = _iso(now)
    receipt = {
        "schema": "qikvrt_reflexive_repository_watchdog_receipt_v1",
        "contract_id": contract["contract_id"],
        "repository": repository,
        "head_sha": expected_head,
        "tree_sha": expected_tree,
        "observed_at": observed_at,
        "state": state,
        "disposition": disposition,
        "first_blocker": blocker,
        "productive_edge": productive_edge,
        "safe_continuation": safe_continuation,
        "effect_already_occurred": False,
        "progress_fingerprint": progress_fingerprint,
        "baseline": {
            "available": baseline is not None,
            "same_progress_fingerprint": baseline_same,
            "age_seconds": baseline_age,
        },
        "leases": {
            "writer_lease_seconds": writer_lease,
            "queue_lease_seconds": queue_lease,
            "progress_lease_seconds": progress_lease,
        },
        "observations": {
            "exact_head_run_count": len(runs),
            "active_productive_runs": [_run_id(run) for run in active_productive],
            "active_writers": [_run_id(run) for run in active_writers],
            "stale_writers": stale_writers,
            "waiting_productive_runs": queue_ages,
            "untrusted_terminal_runs": untrusted,
            "runs": normalized,
        },
        "resource_graph": resource_graph,
        "boundaries": {
            "watchdog_terminality_is_gate_success": False,
            "no_active_runner_is_pipeline_empty": False,
            "action_required_is_trusted_execution": False,
            "zero_job_is_trusted_execution": False,
            "automatic_writer_cancellation": False,
            "repository_mutation": False,
            "external_effect": False,
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
            "DEADLOCK_FREEDOM_PROVED": False,
        },
    }
    receipt["semantic_fingerprint"] = sha256_bytes(
        canonical_json_bytes(
            {
                key: value
                for key, value in receipt.items()
                if key not in {"observed_at", "semantic_fingerprint"}
            }
        )
    )
    return receipt


def _read_json(path: Path, label: str) -> Mapping[str, Any] | Sequence[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReflexiveWatchdogBlock(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, (Mapping, list)):
        raise ReflexiveWatchdogBlock(f"{label} must be an object or list")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subcommands.add_parser("analyze")
    analyze_parser.add_argument("--runs-file", type=Path, required=True)
    analyze_parser.add_argument("--jobs-dir", type=Path, required=True)
    analyze_parser.add_argument("--baseline", type=Path)
    analyze_parser.add_argument("--expect-head", required=True)
    analyze_parser.add_argument("--expect-tree", required=True)
    analyze_parser.add_argument("--repository", required=True)
    analyze_parser.add_argument("--now", required=True)
    analyze_parser.add_argument("--json", action="store_true")
    check_parser = subcommands.add_parser("check-contract")
    check_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "check-contract":
            contract = load_contract()
            prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
            value = {
                "schema": "qikvrt_reflexive_watchdog_contract_check_v1",
                "state": "CONTRACT_BOUND",
                "contract_id": contract["contract_id"],
                "workflow_path": prevention["workflow_path"],
                "controller_path": prevention["controller_path"],
            }
        else:
            runs = _read_json(arguments.runs_file, "workflow runs")
            jobs = {"jobs_by_run": load_jobs_directory(arguments.jobs_dir)}
            baseline = _read_json(arguments.baseline, "baseline") if arguments.baseline else None
            if baseline is not None and not isinstance(baseline, Mapping):
                raise ReflexiveWatchdogBlock("baseline must be an object")
            value = analyze(
                runs,
                jobs,
                expected_head=arguments.expect_head,
                expected_tree=arguments.expect_tree,
                repository=arguments.repository,
                now=_timestamp(arguments.now, "observation time"),
                baseline=baseline,
            )
        if arguments.json:
            print(canonical_json_bytes(value).decode("utf-8"), end="")
        else:
            print(f"{value['state']} first_blocker={value.get('first_blocker')}")
        return 0
    except ReflexiveWatchdogBlock as exc:
        print(f"BLOCK REFLEXIVE_REPOSITORY_WATCHDOG {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
