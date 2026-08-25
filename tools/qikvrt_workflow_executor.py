#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-head workflow-executor planning and mesh-node continuity checks.

The controller is deliberately repository-local.  It observes Git state and
workflow metadata supplied by the caller, creates a deterministic dispatch
plan, and validates a node-split continuity receipt.  It never calls GitHub,
dispatches a workflow, writes a repository file, or treats a terminal watcher
as a successful gate.  The narrowly authorised Action wrapper performs the
single REST dispatch only after this controller has produced a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
ACTIVE_RUN_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
KNOWN_RUN_STATUSES = ACTIVE_RUN_STATUSES | {"completed"}
IMMUTABLE_SNAPSHOT_FIELDS = (
    "schema",
    "contract_id",
    "repository",
    "contract_path",
    "contract_blob_sha",
    "contract_sha256",
    "head_sha",
    "tree_sha",
    "workflow_inventory",
    "workflow_inventory_sha256",
    "capability_bindings",
)
DISPATCH_RECEIPT_FIELDS = {
    "schema",
    "state",
    "observed_at",
    "dispatch_key",
    "repository",
    "capability_id",
    "workflow_id",
    "workflow_path",
    "workflow_blob_sha",
    "event",
    "ref",
    "head_sha",
    "tree_sha",
    "contract_sha256",
    "declaration_blob_sha",
    "subject_manifest_sha256",
    "transport_acknowledgement_is_gate_execution_evidence",
    "gate_execution_observed",
    "external_effect",
    "completion_claims",
}


class ExecutorBlock(RuntimeError):
    """A fail-closed executor or continuity validation error."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExecutorBlock(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExecutorBlock(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ExecutorBlock(f"{label} must be a list of non-empty strings")
    return list(value)


def _sha(value: Any, label: str) -> str:
    value = _string(value, label)
    if not SHA_RE.fullmatch(value):
        raise ExecutorBlock(f"{label} must be a lower-case 40-character Git SHA")
    return value


def _sha256(value: Any, label: str) -> str:
    value = _string(value, label)
    if not SHA256_RE.fullmatch(value):
        raise ExecutorBlock(f"{label} must be a lower-case 64-character SHA-256")
    return value


def _utc_timestamp(value: Any, label: str) -> str:
    value = _string(value, label)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ExecutorBlock(f"{label} must be a canonical UTC timestamp")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ExecutorBlock(f"{label} must be a valid UTC timestamp") from exc
    return value


def _relative_path(value: Any, label: str) -> str:
    value = _string(value, label)
    parsed = PurePosixPath(value)
    if parsed.is_absolute() or parsed.as_posix() != value or ".." in parsed.parts:
        raise ExecutorBlock(f"{label} must be a normalized repository-relative path")
    return value


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ExecutorBlock(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def _git_bytes(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExecutorBlock(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _tree_entry(root: Path, revision: str, relative_path: str) -> dict[str, str] | None:
    relative_path = _relative_path(relative_path, "tree path")
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-z", revision, "--", relative_path],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExecutorBlock(f"cannot resolve exact-tree path {relative_path}: {detail}")
    entries = [entry for entry in completed.stdout.split(b"\0") if entry]
    if not entries:
        return None
    if len(entries) != 1:
        raise ExecutorBlock(f"exact-tree path is ambiguous: {relative_path}")
    try:
        metadata, encoded_path = entries[0].split(b"\t", 1)
        mode, object_type, blob_sha = metadata.decode("ascii").split(" ", 2)
        actual_path = encoded_path.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ExecutorBlock(f"exact-tree path entry is malformed: {relative_path}") from exc
    if actual_path != relative_path:
        raise ExecutorBlock(f"exact-tree path resolution drift: {relative_path}")
    return {
        "path": actual_path,
        "mode": mode,
        "object_type": object_type,
        "blob_sha": _sha(blob_sha, f"exact-tree object for {relative_path}"),
    }


def _blob_bytes_at(root: Path, revision: str, relative_path: str) -> bytes:
    entry = _tree_entry(root, revision, relative_path)
    if entry is None or entry["object_type"] != "blob":
        raise ExecutorBlock(f"exact-tree blob is absent: {relative_path}")
    return _git_bytes(root, "cat-file", "blob", entry["blob_sha"])


def load_contract(root: Path = ROOT, *, revision: str | None = None) -> dict[str, Any]:
    try:
        raw = (
            _blob_bytes_at(root, revision, CONTRACT_RELATIVE_PATH)
            if revision is not None
            else (root / CONTRACT_RELATIVE_PATH).read_bytes()
        )
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock(f"cannot load workflow executor contract: {exc}") from exc
    result = dict(_mapping(value, "workflow executor contract"))
    if result.get("schema") != "qikvrt_workflow_executor_mesh_contract_v1":
        raise ExecutorBlock("workflow executor contract schema is not v1")
    if result.get("contract_id") != "qikvrt-workflow-executor-mesh-v1":
        raise ExecutorBlock("workflow executor contract id is not recognized")
    return result


def _contract_sha256(root: Path, revision: str | None = None) -> str:
    try:
        raw = (
            _blob_bytes_at(root, revision, CONTRACT_RELATIVE_PATH)
            if revision is not None
            else (root / CONTRACT_RELATIVE_PATH).read_bytes()
        )
        return sha256_bytes(raw)
    except OSError as exc:
        raise ExecutorBlock(f"cannot hash workflow executor contract: {exc}") from exc


def _workflow_inventory(root: Path, revision: str) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", revision, "--", ".github/workflows"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExecutorBlock(f"cannot enumerate workflow tree: {detail}")
    inventory: list[dict[str, str]] = []
    for entry in completed.stdout.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, encoded_path = entry.split(b"\t", 1)
            _mode, object_type, blob_sha = metadata.decode("ascii").split(" ", 2)
            path = encoded_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise ExecutorBlock("workflow inventory contains a malformed Git tree entry") from exc
        if object_type != "blob" or not path.endswith((".yml", ".yaml")):
            continue
        inventory.append({"path": path, "blob_sha": _sha(blob_sha, f"workflow blob for {path}")})
    return sorted(inventory, key=lambda item: item["path"])


def _validate_contract_shape(
    contract: Mapping[str, Any], root: Path, *, revision: str | None = None
) -> None:
    authority = _mapping(contract.get("authority"), "contract authority")
    if authority.get("repository") != "Goldkelch/qik-vrt" or authority.get("entrypoint") != "AI":
        raise ExecutorBlock("contract authority binding is not canonical")
    executor = _mapping(contract.get("executor"), "contract executor")
    for key in ("controller_path", "workflow_path", "watchdog_workflow_path", "monitor_workflow_path"):
        relative_path = _relative_path(executor.get(key), f"contract executor.{key}")
        present = (
            _tree_entry(root, revision, relative_path) is not None
            if revision is not None
            else (root / relative_path).is_file()
        )
        if not present:
            raise ExecutorBlock(f"contract-required file is absent: {relative_path}")
    if executor.get("observation_mode") != "REPOSITORY_NATIVE_EXACT_HEAD_BOUND":
        raise ExecutorBlock("executor observation mode is not exact-head bound")
    if executor.get("stateful_writes") != "ACTION_ARTIFACTS_ONLY":
        raise ExecutorBlock("executor stateful write boundary is not artifact-only")
    if _string_list(executor.get("single_writer_order"), "executor single writer order") != [
        "AUTHORITY",
        "MIRROR",
        "MESH_NODE",
    ]:
        raise ExecutorBlock("executor single writer order is not authority-first")

    inventory_contract = _mapping(contract.get("workflow_inventory"), "workflow inventory contract")
    compatibility_paths = _string_list(
        inventory_contract.get("baseline_compatibility_blobs"),
        "baseline compatibility blobs",
    )
    if (
        inventory_contract.get("baseline")
        != "LATEST_EXACT_COMPATIBLE_EXECUTOR_SNAPSHOT_ARTIFACT_OR_FAIL_CLOSED"
        or compatibility_paths
        != [executor["workflow_path"], executor["controller_path"], CONTRACT_RELATIVE_PATH]
        or inventory_contract.get("no_compatible_prior_executor") != "BOOTSTRAP_EMPTY_LEDGER"
        or inventory_contract.get("compatible_baseline_unavailable_or_invalid") != "HOLD"
    ):
        raise ExecutorBlock("executor baseline recovery is not exact-compatible and fail-closed")

    policy = _mapping(contract.get("dispatch_policy"), "dispatch policy")
    if policy.get("enabled") is not True or policy.get("dispatch_ref") != "main":
        raise ExecutorBlock("dispatch policy is not enabled for main")
    if policy.get("maximum_dispatches_per_run") != 1:
        raise ExecutorBlock("dispatch policy must select exactly zero or one workflow")
    if _string_list(policy.get("dispatch_identity"), "dispatch identity") != [
        "EXACT_HEAD",
        "WORKFLOW_PATH",
        "EVENT",
    ]:
        raise ExecutorBlock("dispatch identity is not exact head/path/event bound")
    if policy.get("terminal_or_active_exact_run_suppresses_duplicate_dispatch") is not True:
        raise ExecutorBlock("dispatch policy does not suppress duplicate exact-head runs")
    if policy.get("equivalent_run_precedence") != "ANY_ACTIVE_HOLDS_ELSE_LATEST_RUN_ID":
        raise ExecutorBlock("equivalent run precedence is not deterministic and fail-closed")
    if policy.get("transport_acknowledged_request_suppresses_duplicate_dispatch") is not True:
        raise ExecutorBlock("dispatch policy does not suppress acknowledged requests")
    if policy.get("rerun") != "ONLY_REPOSITORY_DECLARED_TRANSIENT_FAILURE":
        raise ExecutorBlock("dispatch policy allows an unbounded rerun")
    required_conditions = set(_string_list(policy.get("required_conditions"), "dispatch conditions"))
    for condition in (
        "AUTHORITY_REPOSITORY_IDENTITY",
        "CURRENT_MAIN_HEAD_REOBSERVED",
        "CURRENT_MAIN_TREE_REOBSERVED",
        "WORKFLOW_IS_EXACT_TREE_MEMBER",
        "NO_COMPETING_WRITER",
        "NO_EQUIVALENT_EXACT_HEAD_RUN",
        "PRE_EFFECT_EQUIVALENT_RUN_AND_CROSS_HEAD_WRITER_REOBSERVED",
        "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT",
    ):
        if condition not in required_conditions:
            raise ExecutorBlock(f"dispatch condition missing: {condition}")
    _string_list(policy.get("writer_workflow_names"), "writer workflow names")
    ledger = _mapping(policy.get("dispatch_ledger"), "dispatch ledger")
    if (
        ledger.get("stateful_write") != "ACTION_ARTIFACT_ONLY"
        or ledger.get("history_rewrite") != "FORBIDDEN"
        or ledger.get("failed_state_disposition") != "HOLD_NO_BLIND_RETRY"
        or not isinstance(ledger.get("maximum_entries"), int)
        or isinstance(ledger.get("maximum_entries"), bool)
        or not 1 <= ledger["maximum_entries"] <= 1024
    ):
        raise ExecutorBlock("dispatch ledger exceeds the bounded artifact-only policy")
    accepted_state = _string(ledger.get("accepted_state"), "dispatch ledger accepted state")
    failed_state = _string(ledger.get("failed_state"), "dispatch ledger failed state")
    run_observation = _mapping(policy.get("run_observation"), "run observation")
    if dict(run_observation) != {
        "schema": "qikvrt_workflow_run_observation_v1",
        "scope": "CURRENT_MAIN_EXACT_HEAD_ALL_PAGES",
        "job_attempt_filter": "EXPLICIT_ATTEMPT_ENDPOINT_PLUS_RUN_DETAIL_REOBSERVATION",
        "authority_repository_binding": "OBSERVED_GITHUB_REPOSITORY_EQUALS_CONTRACT_AUTHORITY",
        "exact_head_binding": "OBSERVED_HEAD_EQUALS_SNAPSHOT_HEAD",
        "malformed_or_incomplete_disposition": "HOLD",
    }:
        raise ExecutorBlock("workflow run observation is not complete and latest-attempt bound")
    receipt_contract = _mapping(policy.get("receipt_contract"), "dispatch receipt contract")
    if receipt_contract.get("schema") != "qikvrt_workflow_executor_dispatch_receipt_v1":
        raise ExecutorBlock("dispatch receipt schema is invalid")
    if receipt_contract.get("transport_acknowledgement_is_gate_execution_evidence") is not False:
        raise ExecutorBlock("dispatch acknowledgement overstates gate execution evidence")
    expected_fingerprint_fields = [
        "CONTRACT_SHA256",
        "REPOSITORY",
        "CAPABILITY_ID",
        "DECLARATION_BLOB",
        "SUBJECT_MANIFEST_SHA256",
        "EXACT_HEAD",
        "EXACT_TREE",
        "REF",
        "WORKFLOW_PATH",
        "WORKFLOW_BLOB",
        "EVENT",
    ]
    if _string_list(receipt_contract.get("fingerprint_fields"), "receipt fingerprint fields") != expected_fingerprint_fields:
        raise ExecutorBlock("dispatch receipt fingerprint fields are incomplete")
    claims = _mapping(receipt_contract.get("completion_claims"), "dispatch receipt claims")
    if set(claims) != {
        "INDEPENDENT_APPROVAL",
        "PASS",
        "FINAL_PASS",
        "PUBLICATION",
        "DEPLOYMENT",
        "EFFECT_ACK_DONE",
        "MERGE",
        "EXTERNAL_EFFECT",
    } or any(value is not False for value in claims.values()):
        raise ExecutorBlock("dispatch receipt contains a positive completion or effect claim")
    allowed = policy.get("authorized_workflows")
    if not isinstance(allowed, list) or not allowed:
        raise ExecutorBlock("dispatch policy has no authorized workflow")
    capability_ids: set[str] = set()
    priorities: set[int] = set()
    workflow_paths: set[str] = set()
    for entry in allowed:
        item = _mapping(entry, "authorized workflow")
        capability_id = _string(item.get("capability_id"), "authorized capability id")
        if capability_id in capability_ids:
            raise ExecutorBlock("authorized capability id is duplicated")
        capability_ids.add(capability_id)
        priority = item.get("priority")
        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or priority < 0
            or priority in priorities
        ):
            raise ExecutorBlock("authorized workflow priority is invalid or duplicated")
        priorities.add(priority)
        purpose = _string(item.get("purpose"), "authorized workflow purpose")
        if purpose not in {"CAPABILITY_EXACT_HEAD_GATE", "OBSERVER_CONTINUITY"}:
            raise ExecutorBlock("authorized workflow purpose is invalid")
        workflow_id = _string(item.get("workflow_id"), "authorized workflow id")
        workflow_path = _relative_path(item.get("workflow_path"), "authorized workflow path")
        if Path(workflow_path).name != workflow_id or not workflow_path.startswith(".github/workflows/"):
            raise ExecutorBlock("authorized workflow id/path binding is invalid")
        if workflow_path in workflow_paths:
            raise ExecutorBlock("authorized workflow path is duplicated")
        workflow_paths.add(workflow_path)
        _string(item.get("workflow_name"), "authorized workflow name")
        if _string_list(item.get("allowed_events"), "authorized workflow events") != ["workflow_dispatch"]:
            raise ExecutorBlock("authorized workflow has an unbounded event set")
        if item.get("external_effect") != "NONE" or item.get("is_writer") is not False:
            raise ExecutorBlock("authorized workflow exceeds the no-effect observer boundary")
        subjects = item.get("required_subjects")
        if not isinstance(subjects, list):
            raise ExecutorBlock("authorized workflow subjects must be a list")
        subject_paths: set[str] = set()
        for raw_subject in subjects:
            subject = _mapping(raw_subject, "authorized workflow subject")
            subject_path = _relative_path(subject.get("path"), "authorized subject path")
            if subject_path in subject_paths:
                raise ExecutorBlock("authorized subject path is duplicated")
            subject_paths.add(subject_path)
            if subject.get("mode") not in {"100644", "100755"}:
                raise ExecutorBlock("authorized subject mode is invalid")
            _sha(subject.get("blob_sha"), f"authorized subject blob for {subject_path}")
        if list(subject_paths) and [item["path"] for item in subjects] != sorted(subject_paths):
            raise ExecutorBlock("authorized subject paths are not deterministically sorted")
        evidence_policy = _string(item.get("evidence_policy"), "authorized evidence policy")
        if purpose == "CAPABILITY_EXACT_HEAD_GATE":
            if item.get("artifact_policy") != "EXECUTOR_DISPATCH_RECEIPT_PLUS_RUN_JOB_STEP_EVIDENCE":
                raise ExecutorBlock("capability gate artifact policy is not evidence-bounded")
            if evidence_policy != "SUCCESSFUL_POSITIVE_JOB_AND_REQUIRED_STEPS":
                raise ExecutorBlock("capability gate evidence policy is not positive-job bound")
            if not subjects or workflow_path not in subject_paths:
                raise ExecutorBlock("capability gate does not bind its workflow subject")
            declaration = _mapping(item.get("declaration"), "capability declaration")
            _relative_path(declaration.get("path"), "capability declaration path")
            if declaration.get("capability_id") != capability_id:
                raise ExecutorBlock("capability declaration id drift")
            required_binding = _mapping(
                declaration.get("required_binding_fields"),
                "capability declaration required binding fields",
            )
            if set(required_binding) != {
                "executor_contract_path",
                "workflow_path",
                "policy_path",
                "current_exact_head_gate_required",
                "historical_gate_evidence_transferable",
            }:
                raise ExecutorBlock("capability declaration required binding fields are incomplete")
            for key in ("executor_contract_path", "workflow_path", "policy_path"):
                _relative_path(required_binding.get(key), f"capability binding {key}")
            if (
                required_binding.get("executor_contract_path") != CONTRACT_RELATIVE_PATH
                or required_binding.get("workflow_path") != workflow_path
                or required_binding.get("current_exact_head_gate_required") is not True
                or required_binding.get("historical_gate_evidence_transferable") is not False
            ):
                raise ExecutorBlock("capability declaration required binding weakens exact-head evidence")
            job = _mapping(item.get("required_job_evidence"), "required job evidence")
            if job.get("minimum_job_count") != 1:
                raise ExecutorBlock("capability job evidence must require a positive job count")
            _string(job.get("job_name"), "required job name")
            if not _string_list(job.get("required_successful_steps"), "required successful steps"):
                raise ExecutorBlock("capability job evidence has no required steps")
            provenance = _mapping(item.get("historical_provenance"), "historical provenance")
            if (
                not isinstance(provenance.get("pull_request"), int)
                or isinstance(provenance.get("pull_request"), bool)
                or provenance["pull_request"] <= 0
                or provenance.get("evidence_role") != "BYTE_PROVENANCE_ONLY"
                or provenance.get("transferable_as_current_exact_head_gate_evidence") is not False
            ):
                raise ExecutorBlock("historical provenance transfers or overstates current evidence")
            for key in ("head_sha", "tree_sha", "merge_commit_sha"):
                _sha(provenance.get(key), f"historical provenance {key}")
        elif evidence_policy != "TERMINAL_RUN_SUPPRESSES_DUPLICATE_ONLY" or subjects:
            raise ExecutorBlock("observer continuity policy is not duplicate-only")
        else:
            _string(item.get("required_artifact_prefix"), "observer workflow artifact prefix")

    if accepted_state == failed_state:
        raise ExecutorBlock("dispatch ledger accepted and failed states collide")

    boundaries = _mapping(contract.get("boundaries"), "executor boundaries")
    if boundaries.get("direct_repository_mutation") != "FORBIDDEN":
        raise ExecutorBlock("executor permits direct repository mutation")
    for key in (
        "watchdog_terminality_is_gate_success",
        "action_required_is_trusted_execution",
        "zero_job_is_trusted_execution",
    ):
        if boundaries.get(key) is not False:
            raise ExecutorBlock(f"executor boundary {key} must be false")

    continuity = _mapping(contract.get("mesh_node_split_acceptance"), "mesh node split acceptance")
    if continuity.get("applies_to") != "EVERY_FUTURE_NODE_ADDED_BY_QUEUE_ROW":
        raise ExecutorBlock("mesh node acceptance does not bind every future queue node")
    for key in ("receipt_path", "receipt_schema", "continuity_declaration_schema"):
        _string(continuity.get(key), f"mesh node split acceptance.{key}")
    _string_list(continuity.get("required_acceptance_tests"), "mesh node acceptance tests")
    _string_list(continuity.get("connection_order"), "mesh node connection order")


def workflow_delta(
    current_inventory: Sequence[Mapping[str, str]], baseline: Mapping[str, Any] | None
) -> dict[str, Any]:
    if baseline is None:
        return {"state": "BASELINE_UNAVAILABLE", "added": [], "removed": [], "changed": []}
    previous_raw = baseline.get("workflow_inventory")
    if not isinstance(previous_raw, list):
        raise ExecutorBlock("baseline does not contain a workflow inventory")
    previous: dict[str, str] = {}
    for entry in previous_raw:
        item = _mapping(entry, "baseline workflow inventory entry")
        path = _string(item.get("path"), "baseline workflow path")
        previous[path] = _sha(item.get("blob_sha"), f"baseline workflow blob for {path}")
    current = {item["path"]: item["blob_sha"] for item in current_inventory}
    return {
        "state": "COMPARED",
        "added": sorted(set(current) - set(previous)),
        "removed": sorted(set(previous) - set(current)),
        "changed": sorted(path for path in set(current) & set(previous) if current[path] != previous[path]),
    }


def _validate_baseline_shape(
    baseline: Mapping[str, Any] | None, contract: Mapping[str, Any]
) -> None:
    if baseline is None:
        return
    authority_repository = _string(
        _mapping(contract.get("authority"), "contract authority").get("repository"),
        "Authority repository",
    )
    if (
        baseline.get("schema") != "qikvrt_workflow_executor_snapshot_v1"
        or baseline.get("contract_id") != contract.get("contract_id")
        or baseline.get("repository") != authority_repository
        or baseline.get("contract_path") != CONTRACT_RELATIVE_PATH
        or "dispatch_ledger" not in baseline
    ):
        raise ExecutorBlock("baseline is not a complete Authority executor snapshot")
    _sha(baseline.get("contract_blob_sha"), "baseline contract blob")
    _sha256(baseline.get("contract_sha256"), "baseline contract SHA-256")
    _sha(baseline.get("head_sha"), "baseline head")
    _sha(baseline.get("tree_sha"), "baseline tree")
    inventory = baseline.get("workflow_inventory")
    if not isinstance(inventory, list):
        raise ExecutorBlock("baseline workflow inventory is missing")
    normalized: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for raw_entry in inventory:
        entry = _mapping(raw_entry, "baseline workflow inventory entry")
        path = _relative_path(entry.get("path"), "baseline workflow path")
        if path in seen_paths:
            raise ExecutorBlock("baseline workflow inventory path is duplicated")
        seen_paths.add(path)
        normalized.append(
            {
                "path": path,
                "blob_sha": _sha(entry.get("blob_sha"), f"baseline workflow blob for {path}"),
            }
        )
    if normalized != sorted(normalized, key=lambda item: item["path"]):
        raise ExecutorBlock("baseline workflow inventory is not deterministically sorted")
    if baseline.get("workflow_inventory_sha256") != sha256_bytes(
        canonical_json_bytes(normalized)
    ):
        raise ExecutorBlock("baseline workflow inventory fingerprint drift")


def _declaration_binding(
    root: Path, revision: str, declaration_value: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    if declaration_value is None:
        return None
    declaration = _mapping(declaration_value, "capability declaration")
    path = _relative_path(declaration.get("path"), "capability declaration path")
    capability_id = _string(declaration.get("capability_id"), "capability declaration id")
    entry = _tree_entry(root, revision, path)
    if entry is None:
        return {"path": path, "mode": None, "blob_sha": None, "state": "ABSENT"}
    result: dict[str, Any] = {
        "path": path,
        "mode": entry["mode"],
        "blob_sha": entry["blob_sha"],
        "state": "INVALID",
    }
    if entry["object_type"] != "blob" or entry["mode"] not in {"100644", "100755"}:
        result["state"] = "NOT_A_REGULAR_BLOB"
        return result
    try:
        document = json.loads(_git_bytes(root, "cat-file", "blob", entry["blob_sha"]).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        result["state"] = "INVALID_JSON"
        return result
    if not isinstance(document, Mapping) or not isinstance(document.get("capabilities"), list):
        result["state"] = "INVALID_CAPABILITY_DOCUMENT"
        return result
    matches = [
        item
        for item in document["capabilities"]
        if isinstance(item, Mapping) and item.get("id") == capability_id
    ]
    if len(matches) != 1 or matches[0].get("machine_readable") is not True:
        result["state"] = "CAPABILITY_UNDECLARED_OR_AMBIGUOUS"
        return result
    bindings = document.get("bindings")
    actual_binding = bindings.get(capability_id) if isinstance(bindings, Mapping) else None
    required_binding = declaration.get("required_binding_fields")
    if not isinstance(actual_binding, Mapping) or not isinstance(required_binding, Mapping):
        result["state"] = "CAPABILITY_BINDING_ABSENT"
        return result
    if any(actual_binding.get(key) != expected for key, expected in required_binding.items()):
        result["state"] = "CAPABILITY_BINDING_DRIFT"
        return result
    result["state"] = "DECLARED_MACHINE_READABLE"
    return result


def _capability_bindings(
    root: Path, revision: str, contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    policy = _mapping(contract.get("dispatch_policy"), "dispatch policy")
    bindings: list[dict[str, Any]] = []
    ordered = sorted(
        policy["authorized_workflows"],
        key=lambda item: int(_mapping(item, "authorized workflow")["priority"]),
    )
    for raw_authorized in ordered:
        authorized = _mapping(raw_authorized, "authorized workflow")
        capability_id = _string(authorized.get("capability_id"), "authorized capability id")
        workflow_path = _relative_path(authorized.get("workflow_path"), "authorized workflow path")
        workflow_entry = _tree_entry(root, revision, workflow_path)
        subject_bindings: list[dict[str, Any]] = []
        subject_manifest: list[dict[str, Any]] = []
        for raw_subject in authorized.get("required_subjects", []):
            subject = _mapping(raw_subject, "authorized subject")
            path = _relative_path(subject.get("path"), "authorized subject path")
            expected_mode = _string(subject.get("mode"), "authorized subject mode")
            expected_blob = _sha(subject.get("blob_sha"), f"authorized subject blob for {path}")
            actual = _tree_entry(root, revision, path)
            if actual is None:
                state = "ABSENT"
                actual_mode = None
                actual_blob = None
            elif actual["object_type"] != "blob":
                state = "NOT_A_BLOB"
                actual_mode = actual["mode"]
                actual_blob = actual["blob_sha"]
            elif actual["mode"] != expected_mode:
                state = "MODE_DRIFT"
                actual_mode = actual["mode"]
                actual_blob = actual["blob_sha"]
            elif actual["blob_sha"] != expected_blob:
                state = "BLOB_DRIFT"
                actual_mode = actual["mode"]
                actual_blob = actual["blob_sha"]
            else:
                state = "EXACT"
                actual_mode = actual["mode"]
                actual_blob = actual["blob_sha"]
            subject_bindings.append(
                {
                    "path": path,
                    "expected_mode": expected_mode,
                    "expected_blob_sha": expected_blob,
                    "actual_mode": actual_mode,
                    "actual_blob_sha": actual_blob,
                    "state": state,
                }
            )
            subject_manifest.append(
                {"path": path, "mode": actual_mode, "blob_sha": actual_blob}
            )
        declaration = _declaration_binding(
            root,
            revision,
            _mapping(authorized["declaration"], "capability declaration")
            if "declaration" in authorized
            else None,
        )
        subjects_exact = all(item["state"] == "EXACT" for item in subject_bindings)
        workflow_exact = workflow_entry is not None and workflow_entry["object_type"] == "blob"
        if authorized["purpose"] == "CAPABILITY_EXACT_HEAD_GATE":
            binding_state = (
                "PRESENT_BYTES_DECLARED_CURRENT_GATE_UNOBSERVED"
                if subjects_exact
                and workflow_exact
                and declaration is not None
                and declaration["state"] == "DECLARED_MACHINE_READABLE"
                else "CAPABILITY_BYTES_OR_DECLARATION_DRIFT"
            )
        else:
            binding_state = "OBSERVER_WORKFLOW_BOUND" if workflow_exact else "OBSERVER_WORKFLOW_ABSENT"
        bindings.append(
            {
                "capability_id": capability_id,
                "priority": authorized["priority"],
                "purpose": authorized["purpose"],
                "workflow_path": workflow_path,
                "workflow_blob_sha": workflow_entry["blob_sha"] if workflow_exact else None,
                "declaration": declaration,
                "subject_bindings": subject_bindings,
                "subject_manifest_sha256": sha256_bytes(canonical_json_bytes(subject_manifest)),
                "binding_state": binding_state,
            }
        )
    return bindings


def _dispatch_ledger(
    baseline: Mapping[str, Any] | None, contract: Mapping[str, Any]
) -> list[dict[str, Any]]:
    if baseline is None:
        return []
    if "dispatch_ledger" not in baseline:
        raise ExecutorBlock("baseline dispatch ledger is missing")
    raw = baseline.get("dispatch_ledger")
    if not isinstance(raw, list):
        raise ExecutorBlock("baseline dispatch ledger must be a list")
    policy = _mapping(contract.get("dispatch_policy"), "dispatch policy")
    ledger_contract = _mapping(policy.get("dispatch_ledger"), "dispatch ledger")
    maximum = ledger_contract["maximum_entries"]
    if len(raw) > maximum:
        raise ExecutorBlock("baseline dispatch ledger exceeds its bounded size")
    valid_states = {ledger_contract["accepted_state"], ledger_contract["failed_state"]}
    entries: list[dict[str, Any]] = []
    seen_dispatch_keys: set[str] = set()
    authority_repository = _string(
        _mapping(contract.get("authority"), "contract authority").get("repository"),
        "Authority repository",
    )
    authorized_by_capability = {
        _string(_mapping(item, "authorized workflow").get("capability_id"), "capability id"):
        _mapping(item, "authorized workflow")
        for item in policy.get("authorized_workflows", [])
    }
    for raw_entry in raw:
        entry = dict(_mapping(raw_entry, "dispatch ledger entry"))
        if set(entry) != DISPATCH_RECEIPT_FIELDS:
            raise ExecutorBlock("dispatch ledger receipt fields are not exact")
        if entry.get("schema") != "qikvrt_workflow_executor_dispatch_receipt_v1":
            raise ExecutorBlock("dispatch ledger receipt schema is invalid")
        dispatch_key = _sha256(entry.get("dispatch_key"), "dispatch ledger key")
        if dispatch_key in seen_dispatch_keys:
            raise ExecutorBlock("baseline dispatch ledger contains a duplicate dispatch key")
        seen_dispatch_keys.add(dispatch_key)
        declaration_blob = entry.get("declaration_blob_sha")
        if declaration_blob is not None:
            declaration_blob = _sha(declaration_blob, "dispatch ledger declaration blob")
        basis = {
            "contract_sha256": _sha256(entry.get("contract_sha256"), "dispatch ledger contract SHA-256"),
            "repository": _string(entry.get("repository"), "dispatch ledger repository"),
            "capability_id": _string(entry.get("capability_id"), "dispatch ledger capability id"),
            "declaration_blob_sha": declaration_blob,
            "subject_manifest_sha256": _sha256(
                entry.get("subject_manifest_sha256"), "dispatch ledger subject manifest"
            ),
            "head_sha": _sha(entry.get("head_sha"), "dispatch ledger head"),
            "tree_sha": _sha(entry.get("tree_sha"), "dispatch ledger tree"),
            "ref": _string(entry.get("ref"), "dispatch ledger ref"),
            "workflow_path": _relative_path(
                entry.get("workflow_path"), "dispatch ledger workflow path"
            ),
            "workflow_blob_sha": _sha(
                entry.get("workflow_blob_sha"), "dispatch ledger workflow blob"
            ),
            "event": entry.get("event"),
        }
        if dispatch_key != sha256_bytes(canonical_json_bytes(basis)):
            raise ExecutorBlock("dispatch ledger receipt fingerprint drift")
        authorized = authorized_by_capability.get(basis["capability_id"])
        if (
            basis["repository"] != authority_repository
            or authorized is None
            or entry.get("workflow_id") != authorized.get("workflow_id")
            or basis["workflow_path"] != authorized.get("workflow_path")
            or basis["event"] not in authorized.get("allowed_events", [])
            or basis["ref"] != policy.get("dispatch_ref")
            or entry.get("state") not in valid_states
        ):
            raise ExecutorBlock("dispatch ledger event or state is invalid")
        _utc_timestamp(entry.get("observed_at"), "dispatch ledger observation time")
        claims = _mapping(entry.get("completion_claims"), "dispatch ledger claims")
        expected_claims = _mapping(
            _mapping(policy["receipt_contract"], "receipt contract")["completion_claims"],
            "receipt contract claims",
        )
        if dict(claims) != dict(expected_claims):
            raise ExecutorBlock("dispatch ledger receipt overstates completion")
        if (
            entry.get("transport_acknowledgement_is_gate_execution_evidence") is not False
            or entry.get("gate_execution_observed") is not False
            or entry.get("external_effect") != "NONE"
        ):
            raise ExecutorBlock("dispatch ledger receipt crosses the evidence or effect boundary")
        entries.append(entry)
    return entries


def snapshot(
    root: Path = ROOT,
    *,
    revision: str = "HEAD",
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    head = _sha(_git(root, "rev-parse", "--verify", f"{revision}^{{commit}}"), "exact head")
    tree = _sha(_git(root, "rev-parse", "--verify", f"{head}^{{tree}}"), "exact tree")
    contract = load_contract(root, revision=head)
    _validate_contract_shape(contract, root, revision=head)
    _validate_baseline_shape(baseline, contract)
    contract_entry = _tree_entry(root, head, CONTRACT_RELATIVE_PATH)
    if contract_entry is None or contract_entry["object_type"] != "blob":
        raise ExecutorBlock("workflow executor contract is absent from exact tree")
    inventory = _workflow_inventory(root, head)
    return {
        "schema": "qikvrt_workflow_executor_snapshot_v1",
        "contract_id": contract["contract_id"],
        "repository": _mapping(contract["authority"], "contract authority")["repository"],
        "contract_path": CONTRACT_RELATIVE_PATH,
        "contract_blob_sha": contract_entry["blob_sha"],
        "contract_sha256": _contract_sha256(root, head),
        "head_sha": head,
        "tree_sha": tree,
        "workflow_inventory": inventory,
        "workflow_inventory_sha256": sha256_bytes(canonical_json_bytes(inventory)),
        "workflow_delta": workflow_delta(inventory, baseline),
        "capability_bindings": _capability_bindings(root, head, contract),
        "dispatch_ledger": _dispatch_ledger(baseline, contract),
    }


def _require_current_snapshot_evidence(
    snapshot_value: Mapping[str, Any], root: Path = ROOT
) -> dict[str, Any]:
    fresh = snapshot(root)
    for field in IMMUTABLE_SNAPSHOT_FIELDS:
        if snapshot_value.get(field) != fresh.get(field):
            raise ExecutorBlock(f"snapshot immutable evidence drift: {field}")
    return fresh


def _runs(
    value: Mapping[str, Any] | Sequence[Any],
    *,
    expected_repository: str,
    expected_head: str,
) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        raise ExecutorBlock("workflow run observation must be a complete observation object")
    if (
        value.get("schema") != "qikvrt_workflow_run_observation_v1"
        or value.get("pagination_complete") is not True
        or value.get("repository") != expected_repository
        or value.get("head_sha") != expected_head
    ):
        raise ExecutorBlock(
            "workflow run observation is malformed, pagination-incomplete, or Authority-drifted"
        )
    raw: Any = value.get("workflow_runs")
    if not isinstance(raw, list):
        raise ExecutorBlock("workflow run observation must contain workflow_runs")
    result: list[Mapping[str, Any]] = []
    seen_runs: set[int] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ExecutorBlock(f"workflow run observation row {index} is not an object")
        run_id = item.get("id")
        if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
            raise ExecutorBlock(f"workflow run observation row {index} has an invalid id")
        run_attempt = item.get("run_attempt")
        if (
            not isinstance(run_attempt, int)
            or isinstance(run_attempt, bool)
            or run_attempt <= 0
        ):
            raise ExecutorBlock(f"workflow run observation row {index} has an invalid attempt")
        if run_id in seen_runs:
            raise ExecutorBlock(f"workflow run observation row {index} duplicates a run id")
        seen_runs.add(run_id)
        _string(item.get("name"), f"workflow run name {index}")
        normalized_path = _normalized_run_path(item.get("path"))
        if normalized_path is None:
            raise ExecutorBlock(f"workflow run observation row {index} has no workflow path")
        _relative_path(normalized_path, f"workflow run path {index}")
        _string(item.get("event"), f"workflow run event {index}")
        _sha(item.get("head_sha"), f"workflow run head {index}")
        status = item.get("status")
        if status not in KNOWN_RUN_STATUSES:
            raise ExecutorBlock(f"workflow run observation row {index} has an invalid status")
        conclusion = item.get("conclusion")
        if conclusion is not None and (not isinstance(conclusion, str) or not conclusion):
            raise ExecutorBlock(f"workflow run observation row {index} has an invalid conclusion")
        jobs = item.get("jobs")
        if not isinstance(jobs, list) or any(not isinstance(job, Mapping) for job in jobs):
            raise ExecutorBlock(f"workflow run observation row {index} has invalid job evidence")
        if jobs and item.get("run_detail_reobserved") is not True:
            raise ExecutorBlock(
                f"workflow run observation row {index} lacks post-job run reobservation"
            )
        seen_jobs: set[int] = set()
        for job_index, raw_job in enumerate(jobs):
            job = _mapping(raw_job, f"workflow run job {index}.{job_index}")
            job_id = job.get("id")
            if (
                not isinstance(job_id, int)
                or isinstance(job_id, bool)
                or job_id <= 0
                or job_id in seen_jobs
                or job.get("run_id") != run_id
                or job.get("head_sha") != item.get("head_sha")
                or job.get("run_attempt") != run_attempt
                or job.get("attempt_endpoint_bound") is not True
            ):
                raise ExecutorBlock(
                    f"workflow run job {index}.{job_index} is not bound to its run, head, and attempt"
                )
            seen_jobs.add(job_id)
        result.append(item)
    return result


def _normalized_run_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value.split("@", 1)[0]


def _run_sort_key(run: Mapping[str, Any]) -> tuple[int, str]:
    run_id = run.get("id")
    return (
        run_id if isinstance(run_id, int) and not isinstance(run_id, bool) else -1,
        str(run.get("created_at") or ""),
    )


def _job_gate_state(
    run: Mapping[str, Any], required_value: Mapping[str, Any]
) -> tuple[str, dict[str, Any]]:
    if run.get("status") != "completed":
        return "UNTRUSTED_TERMINAL_STATE", {"run_id": run.get("id"), "job_count": 0}
    if run.get("conclusion") == "action_required":
        return "UNTRUSTED_ACTION_REQUIRED", {"run_id": run.get("id"), "job_count": 0}
    if run.get("conclusion") != "success":
        return "TERMINAL_FAILURE", {"run_id": run.get("id"), "job_count": 0}
    jobs = run.get("jobs")
    if not isinstance(jobs, list) or len(jobs) < required_value.get("minimum_job_count", 1):
        return "UNTRUSTED_ZERO_JOB", {"run_id": run.get("id"), "job_count": 0}
    job_name = required_value.get("job_name")
    run_attempt = run.get("run_attempt")
    matching_jobs = [
        job
        for job in jobs
        if isinstance(job, Mapping)
        and job.get("name") == job_name
        and job.get("run_attempt") == run_attempt
    ]
    required_steps = set(
        _string_list(required_value.get("required_successful_steps"), "required successful steps")
    )
    for job in matching_jobs:
        if job.get("status") != "completed" or job.get("conclusion") != "success":
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        successful_steps = {
            step.get("name")
            for step in steps
            if isinstance(step, Mapping)
            and step.get("status") == "completed"
            and step.get("conclusion") == "success"
        }
        if required_steps.issubset(successful_steps):
            return "CURRENT_EXACT_HEAD_GATE_OBSERVED", {
                "run_id": run.get("id"),
                "run_attempt": run.get("run_attempt"),
                "job_count": len(jobs),
                "job_name": job_name,
                "required_successful_steps": sorted(required_steps),
            }
    return "UNTRUSTED_JOB_OR_STEP_EVIDENCE", {
        "run_id": run.get("id"),
        "job_count": len(jobs),
        "job_name": job_name,
    }


def _dispatch_basis(
    snapshot_value: Mapping[str, Any],
    binding: Mapping[str, Any],
    authorized: Mapping[str, Any],
    ref: str,
) -> dict[str, Any]:
    declaration = binding.get("declaration")
    declaration_blob = (
        _sha(declaration.get("blob_sha"), "capability declaration blob")
        if isinstance(declaration, Mapping) and declaration.get("blob_sha") is not None
        else None
    )
    return {
        "contract_sha256": _sha256(snapshot_value.get("contract_sha256"), "snapshot contract SHA-256"),
        "repository": _string(snapshot_value.get("repository"), "snapshot repository"),
        "capability_id": _string(authorized.get("capability_id"), "authorized capability id"),
        "declaration_blob_sha": declaration_blob,
        "subject_manifest_sha256": _sha256(
            binding.get("subject_manifest_sha256"), "subject manifest SHA-256"
        ),
        "head_sha": _sha(snapshot_value.get("head_sha"), "snapshot head"),
        "tree_sha": _sha(snapshot_value.get("tree_sha"), "snapshot tree"),
        "ref": ref,
        "workflow_path": _relative_path(authorized.get("workflow_path"), "authorized workflow path"),
        "workflow_blob_sha": _sha(binding.get("workflow_blob_sha"), "authorized workflow blob"),
        "event": "workflow_dispatch",
    }


def dispatch_plan(snapshot_value: Mapping[str, Any], runs_value: Mapping[str, Any] | Sequence[Any], ref: str) -> dict[str, Any]:
    contract = load_contract()
    _validate_contract_shape(contract, ROOT)
    policy = _mapping(contract["dispatch_policy"], "dispatch policy")
    if ref != policy["dispatch_ref"]:
        raise ExecutorBlock(f"dispatch ref {ref!r} is not the authorised ref {policy['dispatch_ref']!r}")
    if snapshot_value.get("contract_id") != contract["contract_id"]:
        raise ExecutorBlock("snapshot contract id drift")
    _require_current_snapshot_evidence(snapshot_value, ROOT)
    if snapshot_value.get("repository") != _mapping(contract["authority"], "contract authority")["repository"]:
        raise ExecutorBlock("snapshot repository is not the Authority")
    if snapshot_value.get("contract_sha256") != _contract_sha256(ROOT):
        raise ExecutorBlock("snapshot contract bytes drift")
    head = _sha(snapshot_value.get("head_sha"), "snapshot head")
    tree = _sha(snapshot_value.get("tree_sha"), "snapshot tree")
    inventory = snapshot_value.get("workflow_inventory")
    if not isinstance(inventory, list):
        raise ExecutorBlock("snapshot workflow inventory is missing")
    workflow_blobs = {
        _string(_mapping(item, "snapshot workflow").get("path"), "snapshot workflow path"):
        _sha(_mapping(item, "snapshot workflow").get("blob_sha"), "snapshot workflow blob")
        for item in inventory
    }
    raw_bindings = snapshot_value.get("capability_bindings")
    if not isinstance(raw_bindings, list):
        raise ExecutorBlock("snapshot capability bindings are missing")
    bindings: dict[str, Mapping[str, Any]] = {}
    for raw_binding in raw_bindings:
        binding = _mapping(raw_binding, "snapshot capability binding")
        capability_id = _string(binding.get("capability_id"), "snapshot capability id")
        if capability_id in bindings:
            raise ExecutorBlock("snapshot capability binding is duplicated")
        bindings[capability_id] = binding
    ledger_raw = snapshot_value.get("dispatch_ledger", [])
    if not isinstance(ledger_raw, list):
        raise ExecutorBlock("snapshot dispatch ledger is invalid")
    ledger = _dispatch_ledger({"dispatch_ledger": ledger_raw}, contract)
    authority_repository = _string(
        _mapping(contract["authority"], "contract authority").get("repository"),
        "Authority repository",
    )
    runs = _runs(
        runs_value,
        expected_repository=authority_repository,
        expected_head=head,
    )
    writer_names = set(_string_list(policy["writer_workflow_names"], "writer workflow names"))
    active_writers = [
        {
            "id": run.get("id"),
            "name": run.get("name"),
            "status": run.get("status"),
            "head_sha": run.get("head_sha"),
        }
        for run in runs
        if run.get("name") in writer_names and run.get("status") in ACTIVE_RUN_STATUSES
    ]
    candidates: list[dict[str, Any]] = []
    sequence_open = True
    dispatch_selected = False
    ordered = sorted(
        policy["authorized_workflows"],
        key=lambda item: int(_mapping(item, "authorized workflow")["priority"]),
    )
    for raw_authorized in ordered:
        authorized = _mapping(raw_authorized, "authorized workflow")
        capability_id = _string(authorized["capability_id"], "authorized capability id")
        binding = bindings.get(capability_id)
        if binding is None:
            raise ExecutorBlock(f"snapshot lacks authorized capability binding: {capability_id}")
        path = _string(authorized["workflow_path"], "authorized workflow path")
        workflow_name = _string(authorized["workflow_name"], "authorized workflow name")
        candidate = {
            "capability_id": capability_id,
            "priority": authorized["priority"],
            "purpose": authorized["purpose"],
            "workflow_id": _string(authorized["workflow_id"], "authorized workflow id"),
            "workflow_path": path,
            "workflow_name": workflow_name,
            "ref": ref,
            "head_sha": head,
            "tree_sha": tree,
            "workflow_blob_sha": binding.get("workflow_blob_sha"),
            "subject_manifest_sha256": binding.get("subject_manifest_sha256"),
            "capability_binding": dict(binding),
            "external_effect": authorized["external_effect"],
            "required_artifact_prefix": authorized.get("required_artifact_prefix"),
            "allowed_event": authorized["allowed_events"][0],
            "evidence_state": binding.get("binding_state"),
        }
        if not sequence_open:
            candidate.update(
                {
                    "disposition": "HOLD",
                    "first_blocker": (
                        "HIGHER_PRIORITY_DISPATCH_SELECTED"
                        if dispatch_selected
                        else "EARLIER_PRIORITY_GATE_UNRESOLVED"
                    ),
                }
            )
        elif candidate["workflow_blob_sha"] is None or workflow_blobs.get(path) != candidate["workflow_blob_sha"]:
            candidate.update(
                {
                    "disposition": "HOLD",
                    "first_blocker": "WORKFLOW_ABSENT_OR_BLOB_BINDING_DRIFT",
                }
            )
            sequence_open = False
        elif (
            authorized["purpose"] == "CAPABILITY_EXACT_HEAD_GATE"
            and binding.get("binding_state")
            != "PRESENT_BYTES_DECLARED_CURRENT_GATE_UNOBSERVED"
        ):
            candidate.update(
                {
                    "disposition": "HOLD",
                    "first_blocker": "CAPABILITY_BYTES_OR_DECLARATION_DRIFT",
                }
            )
            sequence_open = False
        elif active_writers:
            candidate.update({"disposition": "HOLD", "first_blocker": "COMPETING_WRITER_ACTIVE"})
            sequence_open = False
        else:
            equivalent = [
                run
                for run in runs
                if run.get("head_sha") == head
                and _normalized_run_path(run.get("path")) == path
                and run.get("event") in authorized["allowed_events"]
            ]
            ambiguous = [
                run
                for run in runs
                if run.get("head_sha") == head
                and run.get("name") == workflow_name
                and run.get("event") in authorized["allowed_events"]
                and _normalized_run_path(run.get("path")) is None
            ]
            active = [run for run in equivalent if run.get("status") in ACTIVE_RUN_STATUSES]
            if active:
                candidate.update({"disposition": "HOLD", "first_blocker": "EQUIVALENT_EXACT_HEAD_RUN_ACTIVE"})
                candidate["evidence_state"] = "CURRENT_EXACT_HEAD_GATE_ACTIVE"
                sequence_open = False
            elif equivalent:
                latest = max(equivalent, key=_run_sort_key)
                if authorized["evidence_policy"] == "SUCCESSFUL_POSITIVE_JOB_AND_REQUIRED_STEPS":
                    gate_state, gate_evidence = _job_gate_state(
                        latest,
                        _mapping(authorized["required_job_evidence"], "required job evidence"),
                    )
                    candidate["gate_evidence"] = gate_evidence
                    candidate["evidence_state"] = gate_state
                    if gate_state == "CURRENT_EXACT_HEAD_GATE_OBSERVED":
                        candidate.update({"disposition": "OBSERVED", "first_blocker": None})
                    else:
                        blocker = {
                            "UNTRUSTED_ACTION_REQUIRED": "EQUIVALENT_EXACT_HEAD_RUN_ACTION_REQUIRED",
                            "UNTRUSTED_ZERO_JOB": "EQUIVALENT_EXACT_HEAD_RUN_ZERO_JOB",
                            "UNTRUSTED_JOB_OR_STEP_EVIDENCE": "EQUIVALENT_EXACT_HEAD_RUN_REQUIRES_JOB_EVIDENCE",
                            "UNTRUSTED_TERMINAL_STATE": "EQUIVALENT_EXACT_HEAD_RUN_UNTRUSTED",
                            "TERMINAL_FAILURE": "EQUIVALENT_EXACT_HEAD_RUN_FAILED",
                        }[gate_state]
                        candidate.update({"disposition": "HOLD", "first_blocker": blocker})
                        sequence_open = False
                else:
                    candidate.update(
                        {
                            "disposition": "HOLD",
                            "first_blocker": "EQUIVALENT_EXACT_HEAD_RUN_TERMINAL",
                            "evidence_state": "TERMINAL_DUPLICATE_SUPPRESSION_ONLY",
                        }
                    )
                    sequence_open = False
            elif ambiguous:
                candidate.update(
                    {
                        "disposition": "HOLD",
                        "first_blocker": "EQUIVALENT_EXACT_HEAD_RUN_IDENTITY_UNTRUSTED",
                    }
                )
                sequence_open = False
            else:
                basis = _dispatch_basis(snapshot_value, binding, authorized, ref)
                dispatch_key = sha256_bytes(canonical_json_bytes(basis))
                candidate["dispatch_basis"] = basis
                candidate["dispatch_key"] = dispatch_key
                acknowledged = any(
                    entry.get("dispatch_key") == dispatch_key
                    and entry.get("state")
                    == _mapping(policy["dispatch_ledger"], "dispatch ledger")["accepted_state"]
                    for entry in ledger
                )
                transport_failed = any(
                    entry.get("dispatch_key") == dispatch_key
                    and entry.get("state")
                    == _mapping(policy["dispatch_ledger"], "dispatch ledger")["failed_state"]
                    for entry in ledger
                )
                if acknowledged:
                    candidate.update(
                        {
                            "disposition": "HOLD",
                            "first_blocker": "EQUIVALENT_DISPATCH_REQUEST_ACKNOWLEDGED",
                            "evidence_state": "DISPATCH_ACKNOWLEDGED_EXECUTION_UNOBSERVED",
                        }
                    )
                    sequence_open = False
                elif transport_failed:
                    candidate.update(
                        {
                            "disposition": "HOLD",
                            "first_blocker": "PRIOR_DISPATCH_TRANSPORT_FAILED",
                            "evidence_state": "TRANSPORT_FAILURE_REOBSERVATION_REQUIRED",
                        }
                    )
                    sequence_open = False
                elif dispatch_selected:
                    candidate.update(
                        {
                            "disposition": "HOLD",
                            "first_blocker": "HIGHER_PRIORITY_DISPATCH_SELECTED",
                        }
                    )
                    sequence_open = False
                else:
                    candidate.update({"disposition": "DISPATCH", "first_blocker": None})
                    dispatch_selected = True
                    sequence_open = False
        candidates.append(candidate)
    if sum(item["disposition"] == "DISPATCH" for item in candidates) > policy["maximum_dispatches_per_run"]:
        raise ExecutorBlock("dispatch plan exceeds the contract maximum")
    return {
        "schema": "qikvrt_workflow_executor_plan_v1",
        "contract_id": contract["contract_id"],
        "observed": dict(snapshot_value),
        "active_writers": active_writers,
        "candidates": candidates,
        "dispatch_ledger": ledger,
        "completion_claims": _mapping(policy["receipt_contract"], "receipt contract")["completion_claims"],
        "state": "DISPATCH_CANDIDATE_READY" if any(item["disposition"] == "DISPATCH" for item in candidates) else "HOLD",
    }


def build_dispatch_receipt(
    plan_value: Mapping[str, Any],
    workflow_id: str,
    transport_state: str,
    observed_at: str,
) -> dict[str, Any]:
    contract = load_contract()
    _validate_contract_shape(contract, ROOT)
    policy = _mapping(contract["dispatch_policy"], "dispatch policy")
    ledger_contract = _mapping(policy["dispatch_ledger"], "dispatch ledger")
    if transport_state not in {ledger_contract["accepted_state"], ledger_contract["failed_state"]}:
        raise ExecutorBlock("dispatch receipt transport state is invalid")
    if (
        plan_value.get("schema") != "qikvrt_workflow_executor_plan_v1"
        or plan_value.get("state") != "DISPATCH_CANDIDATE_READY"
        or plan_value.get("contract_id") != contract["contract_id"]
    ):
        raise ExecutorBlock("dispatch receipt plan is not a ready executor plan")
    candidates = plan_value.get("candidates")
    if not isinstance(candidates, list):
        raise ExecutorBlock("dispatch receipt plan lacks candidates")
    dispatch_candidates = [
        _mapping(item, "dispatch receipt candidate")
        for item in candidates
        if isinstance(item, Mapping) and item.get("disposition") == "DISPATCH"
    ]
    if len(dispatch_candidates) != 1:
        raise ExecutorBlock("dispatch receipt plan does not contain exactly one dispatch")
    selected = [
        item for item in dispatch_candidates if item.get("workflow_id") == workflow_id
    ]
    if len(selected) != 1:
        raise ExecutorBlock("dispatch receipt does not bind exactly one selected workflow")
    candidate = selected[0]
    authorized_matches = [
        _mapping(item, "authorized workflow")
        for item in policy.get("authorized_workflows", [])
        if isinstance(item, Mapping) and item.get("workflow_id") == workflow_id
    ]
    if len(authorized_matches) != 1:
        raise ExecutorBlock("dispatch receipt workflow is not uniquely authorized")
    authorized = authorized_matches[0]
    observed = _mapping(plan_value.get("observed"), "dispatch receipt observed snapshot")
    _require_current_snapshot_evidence(observed, ROOT)
    authority_repository = _string(
        _mapping(contract["authority"], "contract authority").get("repository"),
        "Authority repository",
    )
    observed_head = _sha(observed.get("head_sha"), "dispatch receipt observed head")
    observed_tree = _sha(observed.get("tree_sha"), "dispatch receipt observed tree")
    actual_head = _sha(
        _git(ROOT, "rev-parse", "--verify", "HEAD^{commit}"),
        "dispatch receipt actual head",
    )
    actual_tree = _sha(
        _git(ROOT, "rev-parse", "--verify", f"{actual_head}^{{tree}}"),
        "dispatch receipt actual tree",
    )
    if (
        observed.get("schema") != "qikvrt_workflow_executor_snapshot_v1"
        or observed.get("contract_id") != contract["contract_id"]
        or observed.get("repository") != authority_repository
        or observed.get("contract_sha256") != _contract_sha256(ROOT)
        or observed_head != actual_head
        or observed_tree != actual_tree
    ):
        raise ExecutorBlock("dispatch receipt observed snapshot is not current Authority evidence")
    raw_bindings = observed.get("capability_bindings")
    if not isinstance(raw_bindings, list):
        raise ExecutorBlock("dispatch receipt observed snapshot lacks capability bindings")
    binding_matches = [
        _mapping(item, "dispatch receipt capability binding")
        for item in raw_bindings
        if isinstance(item, Mapping)
        and item.get("capability_id") == authorized.get("capability_id")
    ]
    if len(binding_matches) != 1:
        raise ExecutorBlock("dispatch receipt capability binding is not unique")
    expected_basis = _dispatch_basis(
        observed,
        binding_matches[0],
        authorized,
        _string(candidate.get("ref"), "dispatch receipt candidate ref"),
    )
    basis = dict(_mapping(candidate.get("dispatch_basis"), "dispatch receipt basis"))
    if basis != expected_basis:
        raise ExecutorBlock("dispatch receipt basis does not match the observed authorized capability")
    inventory = observed.get("workflow_inventory")
    workflow_entry = _tree_entry(ROOT, actual_head, basis["workflow_path"])
    if not isinstance(inventory, list) or not any(
        isinstance(item, Mapping)
        and item.get("path") == basis["workflow_path"]
        and item.get("blob_sha") == basis["workflow_blob_sha"]
        for item in inventory
    ) or workflow_entry is None or workflow_entry.get("blob_sha") != basis["workflow_blob_sha"]:
        raise ExecutorBlock("dispatch receipt workflow is not an exact observed tree member")
    expected_claims = dict(
        _mapping(
            _mapping(policy["receipt_contract"], "receipt contract")["completion_claims"],
            "receipt claims",
        )
    )
    if (
        plan_value.get("completion_claims") != expected_claims
        or candidate.get("capability_id") != authorized.get("capability_id")
        or candidate.get("workflow_id") != authorized.get("workflow_id")
        or candidate.get("workflow_path") != authorized.get("workflow_path")
        or candidate.get("workflow_blob_sha") != basis["workflow_blob_sha"]
        or candidate.get("subject_manifest_sha256") != basis["subject_manifest_sha256"]
        or candidate.get("allowed_event") != basis["event"]
        or candidate.get("head_sha") != observed_head
        or candidate.get("tree_sha") != observed_tree
        or candidate.get("external_effect") != "NONE"
        or basis.get("event") != "workflow_dispatch"
        or basis.get("ref") != policy["dispatch_ref"]
        or basis.get("repository") != authority_repository
    ):
        raise ExecutorBlock("dispatch receipt plan exceeds its exact no-effect binding")
    dispatch_key = _sha256(candidate.get("dispatch_key"), "dispatch receipt key")
    if dispatch_key != sha256_bytes(canonical_json_bytes(basis)):
        raise ExecutorBlock("dispatch receipt key drift")
    observation_time = _utc_timestamp(observed_at, "dispatch receipt observation time")
    return {
        "schema": _mapping(policy["receipt_contract"], "receipt contract")["schema"],
        "state": transport_state,
        "observed_at": observation_time,
        "dispatch_key": dispatch_key,
        "repository": basis["repository"],
        "capability_id": candidate["capability_id"],
        "workflow_id": candidate["workflow_id"],
        "workflow_path": basis["workflow_path"],
        "workflow_blob_sha": basis["workflow_blob_sha"],
        "event": basis["event"],
        "ref": basis["ref"],
        "head_sha": basis["head_sha"],
        "tree_sha": basis["tree_sha"],
        "contract_sha256": basis["contract_sha256"],
        "declaration_blob_sha": basis["declaration_blob_sha"],
        "subject_manifest_sha256": basis["subject_manifest_sha256"],
        "transport_acknowledgement_is_gate_execution_evidence": False,
        "gate_execution_observed": False,
        "external_effect": "NONE",
        "completion_claims": expected_claims,
    }


def expected_node_receipt_url(node_repository: str, node_branch: str) -> str:
    _string(node_repository, "node repository")
    _string(node_branch, "node branch")
    contract = load_contract()
    receipt_path = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")["receipt_path"]
    return (
        f"https://raw.githubusercontent.com/{node_repository}/"
        f"{urllib.parse.quote(node_branch, safe='/-._~')}/{receipt_path}"
    )


def validate_node_continuity_declaration(
    document: Mapping[str, Any], node_repository: str, node_branch: str
) -> str:
    contract = load_contract()
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    value = _mapping(document.get(continuity["registration_request_field"]), "workflow executor continuity declaration")
    if value.get("schema") != continuity["continuity_declaration_schema"]:
        raise ExecutorBlock("workflow executor continuity declaration schema is invalid")
    if value.get("receipt_path") != continuity["receipt_path"]:
        raise ExecutorBlock("workflow executor continuity declaration receipt path is invalid")
    receipt_url = _string(value.get("receipt_url"), "workflow executor continuity receipt url")
    if receipt_url != expected_node_receipt_url(node_repository, node_branch):
        raise ExecutorBlock("workflow executor continuity receipt URL is not bound to the node repository and branch")
    if value.get("acceptance_required") is not True:
        raise ExecutorBlock("workflow executor continuity declaration does not require acceptance")
    return receipt_url


def build_node_receipt(node_repository: str, node_branch: str, root: Path = ROOT) -> dict[str, Any]:
    contract = load_contract(root)
    value = snapshot(root)
    executor = _mapping(contract["executor"], "contract executor")
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    return {
        "schema": continuity["receipt_schema"],
        "qikvrt_event": "QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY",
        "node_repository": node_repository,
        "node_branch": node_branch,
        "authority": {
            "repository": _mapping(contract["authority"], "contract authority")["repository"],
            "entrypoint": "AI",
            "contract_id": contract["contract_id"],
            "contract_sha256": value["contract_sha256"],
            "head_sha": value["head_sha"],
            "tree_sha": value["tree_sha"],
        },
        "executor": {
            "controller_path": executor["controller_path"],
            "workflow_path": executor["workflow_path"],
            "watchdog_workflow_path": executor["watchdog_workflow_path"],
            "monitor_workflow_path": executor["monitor_workflow_path"],
        },
        "acceptance": {
            "required_tests": continuity["required_acceptance_tests"],
            "connection_order": continuity["connection_order"],
            "status": "DECLARED_NOT_EXECUTION_EVIDENCE",
        },
        "external_effect": "NONE",
        "completion_claims": contract["completion_claims"],
    }


def validate_node_receipt(
    receipt: Mapping[str, Any], node_repository: str, node_branch: str, root: Path = ROOT
) -> dict[str, Any]:
    contract = load_contract(root)
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    receipt = _mapping(receipt, "node continuity receipt")
    if receipt.get("schema") != continuity["receipt_schema"]:
        raise ExecutorBlock("node continuity receipt schema is invalid")
    if receipt.get("qikvrt_event") != "QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY":
        raise ExecutorBlock("node continuity receipt event is invalid")
    if receipt.get("node_repository") != node_repository or receipt.get("node_branch") != node_branch:
        raise ExecutorBlock("node continuity receipt is not bound to the declared node")
    authority = _mapping(receipt.get("authority"), "node receipt authority")
    contract_authority = _mapping(contract["authority"], "contract authority")
    if authority.get("repository") != contract_authority["repository"] or authority.get("entrypoint") != "AI":
        raise ExecutorBlock("node continuity receipt authority binding is invalid")
    if authority.get("contract_id") != contract["contract_id"]:
        raise ExecutorBlock("node continuity receipt contract id is invalid")
    if authority.get("contract_sha256") != _contract_sha256(root):
        raise ExecutorBlock("node continuity receipt does not bind the current authority contract")
    _sha(authority.get("head_sha"), "node receipt authority head")
    _sha(authority.get("tree_sha"), "node receipt authority tree")

    expected_executor = _mapping(contract["executor"], "contract executor")
    executor = _mapping(receipt.get("executor"), "node receipt executor")
    for key in ("controller_path", "workflow_path", "watchdog_workflow_path", "monitor_workflow_path"):
        if executor.get(key) != expected_executor[key]:
            raise ExecutorBlock(f"node continuity receipt executor binding is invalid: {key}")
    acceptance = _mapping(receipt.get("acceptance"), "node receipt acceptance")
    if _string_list(acceptance.get("required_tests"), "node receipt required tests") != continuity["required_acceptance_tests"]:
        raise ExecutorBlock("node continuity receipt acceptance tests are incomplete")
    if _string_list(acceptance.get("connection_order"), "node receipt connection order") != continuity["connection_order"]:
        raise ExecutorBlock("node continuity receipt connection order is incomplete")
    if acceptance.get("status") != "DECLARED_NOT_EXECUTION_EVIDENCE":
        raise ExecutorBlock("node continuity receipt overstates execution evidence")
    if receipt.get("external_effect") != "NONE":
        raise ExecutorBlock("node continuity receipt exceeds the no-effect boundary")
    claims = _mapping(receipt.get("completion_claims"), "node receipt completion claims")
    for key, expected in _mapping(contract["completion_claims"], "contract completion claims").items():
        if claims.get(key) is not expected:
            raise ExecutorBlock(f"node continuity receipt completion claim is invalid: {key}")
    return {
        "schema": "qikvrt_workflow_executor_node_receipt_validation_v1",
        "state": "NODE_SPLIT_CONTINUITY_ACCEPTANCE_READY",
        "node_repository": node_repository,
        "node_branch": node_branch,
        "contract_sha256": _contract_sha256(root),
        "first_blocker": None,
    }


def _read_json_file(path: Path, label: str) -> Mapping[str, Any] | Sequence[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, (Mapping, list)):
        raise ExecutorBlock(f"{label} must be an object or a list")
    return value


def _emit(value: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(canonical_json_bytes(value).decode("utf-8"), end="")
        return
    print(
        f"{value.get('state', 'OBSERVATION_READY')} "
        f"head={value.get('head_sha', value.get('node_repository', '-'))} "
        f"tree={value.get('tree_sha', '-')}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("snapshot", "check"):
        command = subcommands.add_parser(name)
        command.add_argument("--baseline", type=Path)
        command.add_argument("--expect-head")
        command.add_argument("--json", action="store_true")
    plan = subcommands.add_parser("plan")
    plan.add_argument("--runs-file", type=Path, required=True)
    plan.add_argument("--baseline", type=Path)
    plan.add_argument("--expect-head", required=True)
    plan.add_argument("--ref", required=True)
    plan.add_argument("--json", action="store_true")
    dispatch_receipt = subcommands.add_parser("dispatch-receipt")
    dispatch_receipt.add_argument("--plan-file", type=Path, required=True)
    dispatch_receipt.add_argument("--workflow-id", required=True)
    dispatch_receipt.add_argument("--transport-state", required=True)
    dispatch_receipt.add_argument("--observed-at", required=True)
    dispatch_receipt.add_argument("--json", action="store_true")
    template = subcommands.add_parser("node-receipt-template")
    template.add_argument("--node-repository", required=True)
    template.add_argument("--node-branch", required=True)
    template.add_argument("--json", action="store_true")
    receipt = subcommands.add_parser("validate-node-receipt")
    receipt.add_argument("--receipt", type=Path, required=True)
    receipt.add_argument("--node-repository", required=True)
    receipt.add_argument("--node-branch", required=True)
    receipt.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command in {"snapshot", "check", "plan"}:
            baseline = _read_json_file(arguments.baseline, "baseline") if arguments.baseline else None
            if baseline is not None and not isinstance(baseline, Mapping):
                raise ExecutorBlock("baseline must be an executor snapshot object")
            value = snapshot(baseline=baseline)
            if arguments.expect_head is not None and value["head_sha"] != arguments.expect_head:
                raise ExecutorBlock("EXACT_HEAD_DRIFT")
            if arguments.command == "plan":
                runs = _read_json_file(arguments.runs_file, "workflow runs")
                value = dispatch_plan(value, runs, arguments.ref)
        elif arguments.command == "dispatch-receipt":
            plan_value = _read_json_file(arguments.plan_file, "dispatch plan")
            if not isinstance(plan_value, Mapping):
                raise ExecutorBlock("dispatch plan must be an object")
            value = build_dispatch_receipt(
                plan_value,
                arguments.workflow_id,
                arguments.transport_state,
                arguments.observed_at,
            )
        elif arguments.command == "node-receipt-template":
            value = build_node_receipt(arguments.node_repository, arguments.node_branch)
        else:
            receipt = _read_json_file(arguments.receipt, "node continuity receipt")
            if not isinstance(receipt, Mapping):
                raise ExecutorBlock("node continuity receipt must be an object")
            value = validate_node_receipt(receipt, arguments.node_repository, arguments.node_branch)
        _emit(value, arguments.json)
        return 0
    except ExecutorBlock as exc:
        print(f"BLOCK WORKFLOW_EXECUTOR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
