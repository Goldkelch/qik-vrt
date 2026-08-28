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
GATEWATCH_SCOPES = frozenset({"MAIN", "PULL_REQUEST_MAIN", "PULL_REQUEST_STACKED"})
GATEWATCH_STATES = frozenset(
    {
        "SUCCESS",
        "FAILED",
        "MISSING",
        "ACTIVE",
        "UNTRUSTED",
        "NOT_OBSERVED",
        "NOT_APPLICABLE",
    }
)


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


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ReflexiveWatchdogBlock(f"{label} must be a {'possibly empty ' if allow_empty else 'non-empty '}list")
    if any(not isinstance(item, str) or not item for item in value):
        raise ReflexiveWatchdogBlock(f"{label} must contain non-empty strings")
    if len(set(value)) != len(value):
        raise ReflexiveWatchdogBlock(f"{label} must not contain duplicates")
    return list(value)


def _relative_path(value: Any, label: str) -> Path:
    path = Path(_string(value, label))
    if path.is_absolute() or ".." in path.parts:
        raise ReflexiveWatchdogBlock(f"{label} must be a repository-relative path")
    return path


def _head_sha(value: Any, label: str) -> str:
    text = _string(value, label)
    if len(text) != 40 or any(character not in "0123456789abcdef" for character in text):
        raise ReflexiveWatchdogBlock(f"{label} must be a lowercase forty-character Git SHA")
    return text


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
    gatewatch = _mapping(prevention.get("gatewatch"), "reflexive gatewatch profile")
    if gatewatch.get("enabled") is not True:
        raise ReflexiveWatchdogBlock("reflexive gatewatch profile is not enabled")
    _string(gatewatch.get("receipt_path"), "reflexive gatewatch receipt path")
    _positive_int(
        gatewatch.get("observation_freshness_seconds"),
        "reflexive gatewatch observation freshness",
    )
    observed_names = _string_list(
        gatewatch.get("observed_workflow_names"),
        "reflexive gatewatch observed workflow names",
    )
    if set(_string_list(gatewatch.get("gate_states"), "reflexive gatewatch states")) != GATEWATCH_STATES:
        raise ReflexiveWatchdogBlock("reflexive gatewatch states do not match the controller")
    required_by_scope = _mapping(
        gatewatch.get("required_workflow_names_by_scope"),
        "reflexive gatewatch required workflow names by scope",
    )
    if set(required_by_scope) != GATEWATCH_SCOPES:
        raise ReflexiveWatchdogBlock("reflexive gatewatch scopes are incomplete")
    for scope in sorted(GATEWATCH_SCOPES):
        required = _string_list(
            required_by_scope.get(scope),
            f"reflexive gatewatch required workflow names for {scope}",
            allow_empty=True,
        )
        if any(item not in observed_names for item in required):
            raise ReflexiveWatchdogBlock(
                f"reflexive gatewatch required workflow for {scope} is not observed"
            )
    terminal_observation = _mapping(
        gatewatch.get("terminal_observation"), "reflexive terminal observation profile"
    )
    if terminal_observation.get("mode") != "EVENT_DRIVEN_EXACT_HEAD_FAN_IN":
        raise ReflexiveWatchdogBlock("reflexive terminal observation is not event-driven exact-head fan-in")
    if terminal_observation.get("source_event") != "WORKFLOW_RUN_COMPLETED":
        raise ReflexiveWatchdogBlock("reflexive terminal observation source is not workflow_run completed")
    required_terminal_binding = {
        "PULL_REQUEST_NUMBER",
        "PULL_REQUEST_HEAD_SHA",
        "PULL_REQUEST_HEAD_TREE_SHA",
        "SOURCE_WORKFLOW_NAME",
        "SOURCE_WORKFLOW_RUN_ID",
        "SOURCE_WORKFLOW_CONCLUSION",
        "REQUIRED_EXACT_HEAD_GATE_MATRIX",
    }
    if set(
        _string_list(
            terminal_observation.get("required_binding"),
            "reflexive terminal observation binding",
        )
    ) != required_terminal_binding:
        raise ReflexiveWatchdogBlock("reflexive terminal observation binding is incomplete")
    if terminal_observation.get("artifact_projection") != "ACTIONS_ARTIFACT_ONLY":
        raise ReflexiveWatchdogBlock("reflexive terminal observation must remain artifact-only")
    if set(
        _string_list(
            terminal_observation.get("permitted_dispositions"),
            "reflexive terminal observation dispositions",
        )
    ) != {"HOLD", "CONTINUE", "READY_FOR_SEPARATE_AUTHORITY"}:
        raise ReflexiveWatchdogBlock("reflexive terminal observation dispositions are invalid")
    for key in (
        "terminality_is_gate_success",
        "automatic_merge_or_deployment",
        "general_effect_ack_done",
    ):
        if terminal_observation.get(key) is not False:
            raise ReflexiveWatchdogBlock(f"reflexive terminal observation {key} must remain false")
    liveness = _mapping(gatewatch.get("node_liveness"), "reflexive gatewatch node liveness")
    if liveness.get("enabled") is not True:
        raise ReflexiveWatchdogBlock("reflexive gatewatch node liveness is not enabled")
    records_root = _relative_path(liveness.get("records_root"), "node liveness records root")
    for key in ("seed_acceptance_path", "renewal_path", "health_path"):
        record_path = _relative_path(liveness.get(key), f"node liveness {key}")
        if record_path.parent != records_root:
            raise ReflexiveWatchdogBlock(f"node liveness {key} is outside the records root")
    _string(liveness.get("authority_repository"), "node liveness authority repository")
    _positive_int(liveness.get("warning_seconds"), "node liveness warning seconds")
    if liveness.get("all_records_absent_state") != "NOT_APPLICABLE":
        raise ReflexiveWatchdogBlock("node liveness all-records-absent state must be NOT_APPLICABLE")
    if liveness.get("expired_or_overdue_disposition") != "HOLD":
        raise ReflexiveWatchdogBlock("node liveness expired-or-overdue disposition must be HOLD")
    if liveness.get("authority_head_mismatch_disposition") != "HOLD":
        raise ReflexiveWatchdogBlock("node liveness authority-head-mismatch disposition must be HOLD")
    if liveness.get("artifact_only_materialization") is not True:
        raise ReflexiveWatchdogBlock("node liveness materialization must remain artifact-only")
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


def _latest_by_exact_name(
    runs: Sequence[Mapping[str, Any]], name: str
) -> Mapping[str, Any] | None:
    candidates = [run for run in runs if run.get("name") == name]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (_run_created_time(item), _run_id(item)))


def _gate_state_for_run(
    run: Mapping[str, Any] | None,
    jobs_by_run: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    required: bool,
) -> dict[str, Any]:
    if run is None:
        return {
            "state": "MISSING" if required else "NOT_OBSERVED",
            "reason": "NO_EXACT_HEAD_RUN" if required else "NO_EXACT_HEAD_RUN_NOT_REQUIRED",
            "run": None,
        }
    run_id = _run_id(run)
    jobs = list(jobs_by_run.get(run_id, []))
    summary = _job_summary(jobs)
    status = run.get("status")
    conclusion = run.get("conclusion")
    state: str
    reason: str
    if status in ACTIVE_STATUSES:
        state = "ACTIVE"
        reason = "RUN_NOT_TERMINAL"
    elif status != "completed":
        state = "UNTRUSTED"
        reason = "UNRECOGNIZED_RUN_STATUS"
    elif conclusion in EXECUTED_FAILURE_CONCLUSIONS or summary["executed_failures"]:
        state = "FAILED"
        reason = "EXECUTED_FAILURE"
    elif conclusion == "success" and summary["total"] and summary["success"] and not summary["other_terminal"]:
        state = "SUCCESS"
        reason = "TERMINAL_SUCCESS_WITH_EXECUTED_JOB_EVIDENCE"
    elif conclusion in UNTRUSTED_CONCLUSIONS:
        state = "UNTRUSTED"
        reason = "ACTION_REQUIRED_OR_STARTUP_FAILURE"
    elif not jobs:
        state = "UNTRUSTED"
        reason = "ZERO_JOB_TERMINAL_RUN"
    else:
        state = "UNTRUSTED"
        reason = "TERMINAL_RUN_LACKS_TRUSTED_SUCCESS_EVIDENCE"
    return {
        "state": state,
        "reason": reason,
        "run": {
            "id": run_id,
            "status": status,
            "conclusion": conclusion,
            "created_at": _iso(_run_created_time(run)),
            "updated_at": _iso(_run_transition_time(run)),
            "jobs": summary,
        },
    }


def _gatewatch_observation(
    contract: Mapping[str, Any],
    runs: Sequence[Mapping[str, Any]],
    jobs_by_run: Mapping[str, Sequence[Mapping[str, Any]]],
    scope: str,
) -> dict[str, Any]:
    if scope not in GATEWATCH_SCOPES:
        raise ReflexiveWatchdogBlock(f"gatewatch observation scope is invalid: {scope}")
    prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
    profile = _mapping(prevention["gatewatch"], "reflexive gatewatch profile")
    observed_names = _string_list(
        profile["observed_workflow_names"], "reflexive gatewatch observed workflow names"
    )
    required_by_scope = _mapping(
        profile["required_workflow_names_by_scope"],
        "reflexive gatewatch required workflow names by scope",
    )
    required_names = set(
        _string_list(
            required_by_scope[scope],
            f"reflexive gatewatch required workflow names for {scope}",
            allow_empty=True,
        )
    )
    gates = []
    for name in observed_names:
        gate = _gate_state_for_run(
            _latest_by_exact_name(runs, name), jobs_by_run, required=name in required_names
        )
        if gate["state"] not in GATEWATCH_STATES:
            raise ReflexiveWatchdogBlock("gatewatch produced an undeclared gate state")
        gates.append({"name": name, "required": name in required_names, **gate})
    failures = [gate for gate in gates if gate["state"] == "FAILED"]
    required_gaps = [
        gate
        for gate in gates
        if gate["required"] and gate["state"] in {"MISSING", "UNTRUSTED"}
    ]
    active_required = [gate for gate in gates if gate["required"] and gate["state"] == "ACTIVE"]
    return {
        "schema": "qikvrt_exact_head_trusted_gate_matrix_v1",
        "scope": scope,
        "required_workflow_names": sorted(required_names),
        "gates": gates,
        "executed_failures": failures,
        "required_evidence_gaps": required_gaps,
        "active_required_gates": active_required,
    }


def _record_bytes(path: Path, label: str) -> tuple[Mapping[str, Any] | None, dict[str, Any]]:
    if not path.exists():
        return None, {"path": path.as_posix(), "present": False}
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, {
            "path": path.as_posix(),
            "present": True,
            "state": "INVALID",
            "reason": f"MALFORMED_{label.upper()}_RECORD",
        }
    if not isinstance(value, Mapping):
        return None, {
            "path": path.as_posix(),
            "present": True,
            "state": "INVALID",
            "reason": f"MALFORMED_{label.upper()}_RECORD",
        }
    return value, {
        "path": path.as_posix(),
        "present": True,
        "content_sha256": sha256_bytes(raw),
    }


def _node_liveness_observation(
    contract: Mapping[str, Any],
    *,
    root: Path,
    directory: Path | None,
    authority_head: str | None,
    now: datetime,
) -> dict[str, Any]:
    prevention = _mapping(contract["reflexive_deadlock_prevention"], "reflexive prevention")
    profile = _mapping(
        _mapping(prevention["gatewatch"], "reflexive gatewatch profile")["node_liveness"],
        "reflexive gatewatch node liveness",
    )
    records_root = directory if directory is not None else root / _relative_path(
        profile["records_root"], "node liveness records root"
    )
    paths = {
        "seed_acceptance": records_root / Path(profile["seed_acceptance_path"]).name,
        "renewal": records_root / Path(profile["renewal_path"]).name,
        "health": records_root / Path(profile["health_path"]).name,
    }
    loaded = {name: _record_bytes(path, name) for name, path in paths.items()}
    records = {name: dict(metadata) for name, (_, metadata) in loaded.items()}
    present_count = sum(1 for value in records.values() if value["present"])
    if present_count == 0:
        for value in records.values():
            value["state"] = "NOT_APPLICABLE"
            value["reason"] = "NO_NODE_LOCAL_LIVENESS_RECORDS"
        return {
            "schema": "qikvrt_node_liveness_gatewatch_v1",
            "state": "NOT_APPLICABLE",
            "records_root": records_root.as_posix(),
            "authority_head": authority_head,
            "records": records,
            "blocking_records": [],
        }
    if present_count != len(records):
        for value in records.values():
            if not value["present"]:
                value["state"] = "MISSING"
                value["reason"] = "PARTIAL_NODE_LIVENESS_RECORD_SET"
        return {
            "schema": "qikvrt_node_liveness_gatewatch_v1",
            "state": "HOLD",
            "records_root": records_root.as_posix(),
            "authority_head": authority_head,
            "records": records,
            "blocking_records": [
                {"record": name, "reason": value.get("reason")}
                for name, value in records.items()
                if value.get("state") in {"MISSING", "INVALID"}
            ],
        }

    invalid = [
        {"record": name, "reason": metadata.get("reason", "MALFORMED_NODE_LIVENESS_RECORD")}
        for name, (document, metadata) in loaded.items()
        if document is None
    ]
    if invalid:
        return {
            "schema": "qikvrt_node_liveness_gatewatch_v1",
            "state": "HOLD",
            "records_root": records_root.as_posix(),
            "authority_head": authority_head,
            "records": records,
            "blocking_records": invalid,
        }

    acceptance, _ = loaded["seed_acceptance"]
    renewal, _ = loaded["renewal"]
    health, _ = loaded["health"]
    acceptance_metadata = records["seed_acceptance"]
    renewal_metadata = records["renewal"]
    health_metadata = records["health"]
    assert acceptance is not None and renewal is not None and health is not None
    warning_seconds = _positive_int(profile["warning_seconds"], "node liveness warning seconds")
    blocking: list[dict[str, str]] = []

    if authority_head is None:
        acceptance_metadata["state"] = "UNTRUSTED"
        acceptance_metadata["reason"] = "AUTHORITY_HEAD_UNOBSERVED"
        blocking.append({"record": "seed_acceptance", "reason": "AUTHORITY_HEAD_UNOBSERVED"})
    else:
        observed = acceptance.get("observed_authority_commit")
        if observed == authority_head:
            acceptance_metadata["state"] = "FRESH"
            acceptance_metadata["reason"] = "AUTHORITY_HEAD_EXACTLY_BOUND"
        else:
            acceptance_metadata["state"] = "STALE"
            acceptance_metadata["reason"] = "SEED_ACCEPTANCE_AUTHORITY_HEAD_STALE"
            acceptance_metadata["observed_authority_commit"] = observed
            blocking.append(
                {"record": "seed_acceptance", "reason": "SEED_ACCEPTANCE_AUTHORITY_HEAD_STALE"}
            )

    try:
        due = _timestamp(renewal.get("next_renewal_due_utc"), "node renewal due")
        renewal_metadata["next_renewal_due_utc"] = _iso(due)
        seconds = int((due - now).total_seconds())
        if seconds <= 0:
            renewal_metadata["state"] = "OVERDUE"
            renewal_metadata["reason"] = "NODE_REGISTRATION_RENEWAL_OVERDUE"
            blocking.append({"record": "renewal", "reason": "NODE_REGISTRATION_RENEWAL_OVERDUE"})
        elif seconds <= warning_seconds:
            renewal_metadata["state"] = "EXPIRING"
            renewal_metadata["reason"] = "NODE_REGISTRATION_RENEWAL_DUE_SOON"
        else:
            renewal_metadata["state"] = "FRESH"
            renewal_metadata["reason"] = "NODE_REGISTRATION_RENEWAL_CURRENT"
    except ReflexiveWatchdogBlock:
        renewal_metadata["state"] = "INVALID"
        renewal_metadata["reason"] = "MALFORMED_RENEWAL_DUE"
        blocking.append({"record": "renewal", "reason": "MALFORMED_RENEWAL_DUE"})

    try:
        expires = _timestamp(health.get("expires_utc"), "node health expiry")
        health_metadata["expires_utc"] = _iso(expires)
        seconds = int((expires - now).total_seconds())
        if seconds <= 0:
            health_metadata["state"] = "EXPIRED"
            health_metadata["reason"] = "NODE_HEALTH_EXPIRED"
            blocking.append({"record": "health", "reason": "NODE_HEALTH_EXPIRED"})
        elif seconds <= warning_seconds:
            health_metadata["state"] = "EXPIRING"
            health_metadata["reason"] = "NODE_HEALTH_EXPIRING_SOON"
        else:
            health_metadata["state"] = "FRESH"
            health_metadata["reason"] = "NODE_HEALTH_CURRENT"
    except ReflexiveWatchdogBlock:
        health_metadata["state"] = "INVALID"
        health_metadata["reason"] = "MALFORMED_HEALTH_EXPIRY"
        blocking.append({"record": "health", "reason": "MALFORMED_HEALTH_EXPIRY"})

    return {
        "schema": "qikvrt_node_liveness_gatewatch_v1",
        "state": "HOLD" if blocking else "OBSERVE",
        "records_root": records_root.as_posix(),
        "authority_head": authority_head,
        "records": records,
        "blocking_records": blocking,
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
    observation_scope: str = "MAIN",
    node_liveness_dir: Path | None = None,
    authority_head: str | None = None,
) -> dict[str, Any]:
    contract = load_contract(root)
    if authority_head is not None:
        authority_head = _head_sha(authority_head, "authority head observation")
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

    gatewatch = _gatewatch_observation(contract, runs, jobs_by_run, observation_scope)
    liveness = _node_liveness_observation(
        contract,
        root=root,
        directory=node_liveness_dir,
        authority_head=authority_head,
        now=now,
    )

    progress_material = [item for item in normalized if item["name"] not in observer_names]
    progress_fingerprint = sha256_bytes(canonical_json_bytes(progress_material))
    baseline_same = False
    baseline_binding_same = False
    baseline_age = None
    if baseline is not None:
        previous_fingerprint = baseline.get("progress_fingerprint")
        previous_observed = baseline.get("observed_at")
        previous_head = baseline.get("head_sha")
        previous_tree = baseline.get("tree_sha")
        if (
            isinstance(previous_fingerprint, str)
            and isinstance(previous_observed, str)
            and previous_head == expected_head
            and previous_tree == expected_tree
        ):
            baseline_binding_same = True
            baseline_same = previous_fingerprint == progress_fingerprint
            baseline_age = _age_seconds(now, _timestamp(previous_observed, "baseline observed_at"))

    blocker: str | None = None
    state = "SAFE_PROGRESS"
    disposition = "OBSERVE"
    productive_edge = "CONTINUE_REFLEXIVE_OBSERVATION"
    safe_continuation = "Preserve one writer, exact-head evidence, and the next declared source-event observation edge."

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
    elif gatewatch["executed_failures"]:
        state = "PREEMPTIVE_HOLD_EXECUTED_GATE_FAILURE"
        blocker = "TRUSTED_GATE_EXECUTED_FAILURE"
        disposition = "HOLD"
        productive_edge = "REPAIR_OR_REOBSERVE_FIRST_FAILED_TRUSTED_GATE"
        safe_continuation = "Do not infer a terminal gate success; retain the exact failed run and job evidence."
    elif liveness["blocking_records"]:
        first_liveness_blocker = liveness["blocking_records"][0]
        state = "PREEMPTIVE_HOLD_NODE_LIVENESS"
        blocker = first_liveness_blocker["reason"]
        disposition = "HOLD"
        productive_edge = "RENEW_OR_REOBSERVE_FIRST_BLOCKING_NODE_LIVENESS_RECORD"
        safe_continuation = "Keep the gatewatch read-only; do not fabricate a liveness renewal or acceptance record."
    elif gatewatch["required_evidence_gaps"]:
        state = "PREEMPTIVE_HOLD_REQUIRED_GATE_EVIDENCE"
        blocker = "REQUIRED_TRUSTED_GATE_EVIDENCE_MISSING_OR_UNTRUSTED"
        disposition = "HOLD"
        productive_edge = "OBTAIN_TRUSTED_EXACT_HEAD_REQUIRED_GATE_EVIDENCE"
        safe_continuation = "Wait for an exact-head required gate with executed trusted job evidence."
    elif (
        baseline_binding_same
        and baseline_age is not None
        and baseline_age >= _positive_int(
            _mapping(prevention["gatewatch"], "reflexive gatewatch profile")[
                "observation_freshness_seconds"
            ],
            "reflexive gatewatch observation freshness",
        )
    ):
        state = "PREEMPTIVE_HOLD_OBSERVATION_CADENCE_BREACH"
        blocker = "EXACT_HEAD_GATEWATCH_RECEIPT_EXCEEDED_FRESHNESS_BOUND"
        disposition = "HOLD"
        productive_edge = "REESTABLISH_EXACT_HEAD_EVENT_BOUND_GATEWATCH_RECEIPT"
        safe_continuation = "Do not infer an observation edge from an old receipt; reobserve only from a declared exact-head source event."
    elif untrusted:
        state = "UNTRUSTED_EXECUTION_GAP"
        blocker = "LATEST_TERMINAL_RUN_LACKS_TRUSTED_JOB_EVIDENCE"
        disposition = "HOLD"
        productive_edge = "OBTAIN_TRUSTED_EXACT_HEAD_JOB_EVIDENCE"
        safe_continuation = "Use a repository-declared trusted exact-head verification path; do not infer success."
    elif not active_productive:
        state = "QUIESCENT_OBSERVATION"
        productive_edge = "AWAIT_NEXT_DECLARED_SOURCE_EVENT"
        safe_continuation = "Await the next declared source event; quiescence is not a PIPELINE_EMPTY claim."

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
            "same_head_and_tree": baseline_binding_same,
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
        "gatewatch": {
            **gatewatch,
            "observation_freshness_seconds": _positive_int(
                _mapping(prevention["gatewatch"], "reflexive gatewatch profile")[
                    "observation_freshness_seconds"
                ],
                "reflexive gatewatch observation freshness",
            ),
            "node_liveness": liveness,
        },
        "resource_graph": resource_graph,
        "boundaries": {
            "watchdog_terminality_is_gate_success": False,
            "no_active_runner_is_pipeline_empty": False,
            "action_required_is_trusted_execution": False,
            "zero_job_is_trusted_execution": False,
            "gatewatch_terminality_is_gate_success": False,
            "liveness_record_observation_mutates_repository": False,
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
    analyze_parser.add_argument("--observation-scope", choices=sorted(GATEWATCH_SCOPES), default="MAIN")
    analyze_parser.add_argument("--node-liveness-dir", type=Path)
    analyze_parser.add_argument("--authority-head-file", type=Path)
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
            authority_head = None
            if arguments.authority_head_file is not None:
                try:
                    authority_head = arguments.authority_head_file.read_text(encoding="utf-8").strip()
                except (OSError, UnicodeError) as exc:
                    raise ReflexiveWatchdogBlock(f"cannot load authority head observation: {exc}") from exc
                authority_head = _head_sha(authority_head, "authority head observation")
            value = analyze(
                runs,
                jobs,
                expected_head=arguments.expect_head,
                expected_tree=arguments.expect_tree,
                repository=arguments.repository,
                now=_timestamp(arguments.now, "observation time"),
                baseline=baseline,
                observation_scope=arguments.observation_scope,
                node_liveness_dir=arguments.node_liveness_dir,
                authority_head=authority_head,
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
