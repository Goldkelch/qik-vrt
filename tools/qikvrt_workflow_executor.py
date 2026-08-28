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
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ACTIVE_RUN_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})


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


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    path = root / CONTRACT_RELATIVE_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock(f"cannot load workflow executor contract: {exc}") from exc
    result = dict(_mapping(value, "workflow executor contract"))
    if result.get("schema") != "qikvrt_workflow_executor_mesh_contract_v1":
        raise ExecutorBlock("workflow executor contract schema is not v1")
    if result.get("contract_id") != "qikvrt-workflow-executor-mesh-v1":
        raise ExecutorBlock("workflow executor contract id is not recognized")
    return result


def _contract_sha256(root: Path) -> str:
    try:
        return sha256_bytes((root / CONTRACT_RELATIVE_PATH).read_bytes())
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


def _validate_contract_shape(contract: Mapping[str, Any], root: Path) -> None:
    authority = _mapping(contract.get("authority"), "contract authority")
    if authority.get("repository") != "Goldkelch/qik-vrt" or authority.get("entrypoint") != "AI":
        raise ExecutorBlock("contract authority binding is not canonical")
    executor = _mapping(contract.get("executor"), "contract executor")
    for key in ("controller_path", "workflow_path", "watchdog_workflow_path", "monitor_workflow_path"):
        relative_path = _string(executor.get(key), f"contract executor.{key}")
        if not (root / relative_path).is_file():
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

    policy = _mapping(contract.get("dispatch_policy"), "dispatch policy")
    if policy.get("enabled") is not True or policy.get("dispatch_ref") != "main":
        raise ExecutorBlock("dispatch policy is not enabled for main")
    if policy.get("terminal_or_active_exact_run_suppresses_duplicate_dispatch") is not True:
        raise ExecutorBlock("dispatch policy does not suppress duplicate exact-head runs")
    if policy.get("rerun") != "ONLY_REPOSITORY_DECLARED_TRANSIENT_FAILURE":
        raise ExecutorBlock("dispatch policy allows an unbounded rerun")
    required_conditions = set(_string_list(policy.get("required_conditions"), "dispatch conditions"))
    for condition in (
        "CURRENT_MAIN_HEAD_REOBSERVED",
        "CURRENT_MAIN_TREE_REOBSERVED",
        "WORKFLOW_IS_EXACT_TREE_MEMBER",
        "NO_COMPETING_WRITER",
        "NO_EQUIVALENT_EXACT_HEAD_RUN",
        "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT",
    ):
        if condition not in required_conditions:
            raise ExecutorBlock(f"dispatch condition missing: {condition}")
    _string_list(policy.get("writer_workflow_names"), "writer workflow names")
    allowed = policy.get("authorized_workflows")
    if not isinstance(allowed, list) or not allowed:
        raise ExecutorBlock("dispatch policy has no authorized workflow")
    for entry in allowed:
        item = _mapping(entry, "authorized workflow")
        workflow_id = _string(item.get("workflow_id"), "authorized workflow id")
        workflow_path = _string(item.get("workflow_path"), "authorized workflow path")
        if Path(workflow_path).name != workflow_id or not workflow_path.startswith(".github/workflows/"):
            raise ExecutorBlock("authorized workflow id/path binding is invalid")
        _string(item.get("workflow_name"), "authorized workflow name")
        if _string_list(item.get("allowed_events"), "authorized workflow events") != ["workflow_dispatch"]:
            raise ExecutorBlock("authorized workflow has an unbounded event set")
        if item.get("external_effect") != "NONE" or item.get("is_writer") is not False:
            raise ExecutorBlock("authorized workflow exceeds the no-effect observer boundary")

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


def snapshot(
    root: Path = ROOT,
    *,
    revision: str = "HEAD",
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = load_contract(root)
    _validate_contract_shape(contract, root)
    head = _sha(_git(root, "rev-parse", "--verify", f"{revision}^{{commit}}"), "exact head")
    tree = _sha(_git(root, "rev-parse", "--verify", f"{revision}^{{tree}}"), "exact tree")
    inventory = _workflow_inventory(root, revision)
    inventory_by_path = {item["path"]: item["blob_sha"] for item in inventory}
    for authorized in _mapping(contract["dispatch_policy"], "dispatch policy")["authorized_workflows"]:
        path = _mapping(authorized, "authorized workflow")["workflow_path"]
        if path not in inventory_by_path:
            raise ExecutorBlock(f"authorized workflow is absent from exact tree: {path}")
    return {
        "schema": "qikvrt_workflow_executor_snapshot_v1",
        "contract_id": contract["contract_id"],
        "contract_path": CONTRACT_RELATIVE_PATH,
        "contract_sha256": _contract_sha256(root),
        "head_sha": head,
        "tree_sha": tree,
        "workflow_inventory": inventory,
        "workflow_inventory_sha256": sha256_bytes(canonical_json_bytes(inventory)),
        "workflow_delta": workflow_delta(inventory, baseline),
    }


def _runs(value: Mapping[str, Any] | Sequence[Any]) -> list[Mapping[str, Any]]:
    raw: Any = value.get("workflow_runs") if isinstance(value, Mapping) else value
    if not isinstance(raw, list):
        raise ExecutorBlock("workflow run observation must contain workflow_runs")
    return [item for item in raw if isinstance(item, Mapping)]


def dispatch_plan(snapshot_value: Mapping[str, Any], runs_value: Mapping[str, Any] | Sequence[Any], ref: str) -> dict[str, Any]:
    contract = load_contract()
    policy = _mapping(contract["dispatch_policy"], "dispatch policy")
    if ref != policy["dispatch_ref"]:
        raise ExecutorBlock(f"dispatch ref {ref!r} is not the authorised ref {policy['dispatch_ref']!r}")
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
    runs = _runs(runs_value)
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
    for raw_authorized in policy["authorized_workflows"]:
        authorized = _mapping(raw_authorized, "authorized workflow")
        path = _string(authorized["workflow_path"], "authorized workflow path")
        workflow_name = _string(authorized["workflow_name"], "authorized workflow name")
        candidate = {
            "workflow_id": _string(authorized["workflow_id"], "authorized workflow id"),
            "workflow_path": path,
            "workflow_name": workflow_name,
            "ref": ref,
            "head_sha": head,
            "tree_sha": tree,
            "workflow_blob_sha": workflow_blobs.get(path),
            "external_effect": authorized["external_effect"],
            "required_artifact_prefix": authorized["required_artifact_prefix"],
        }
        if candidate["workflow_blob_sha"] is None:
            candidate.update({"disposition": "HOLD", "first_blocker": "WORKFLOW_ABSENT_FROM_EXACT_TREE"})
        elif active_writers:
            candidate.update({"disposition": "HOLD", "first_blocker": "COMPETING_WRITER_ACTIVE"})
        else:
            equivalent = [
                run
                for run in runs
                if run.get("name") == workflow_name and run.get("head_sha") == head
            ]
            active = [run for run in equivalent if run.get("status") in ACTIVE_RUN_STATUSES]
            if active:
                candidate.update({"disposition": "HOLD", "first_blocker": "EQUIVALENT_EXACT_HEAD_RUN_ACTIVE"})
            elif equivalent:
                trusted = all(
                    run.get("conclusion") not in {"action_required", None} for run in equivalent
                )
                candidate.update(
                    {
                        "disposition": "HOLD",
                        "first_blocker": (
                            "EQUIVALENT_EXACT_HEAD_RUN_REQUIRES_JOB_EVIDENCE"
                            if not trusted
                            else "EQUIVALENT_EXACT_HEAD_RUN_TERMINAL"
                        ),
                    }
                )
            else:
                candidate.update({"disposition": "DISPATCH", "first_blocker": None})
        candidates.append(candidate)
    return {
        "schema": "qikvrt_workflow_executor_plan_v1",
        "contract_id": contract["contract_id"],
        "observed": dict(snapshot_value),
        "active_writers": active_writers,
        "candidates": candidates,
        "state": "DISPATCH_CANDIDATE_READY" if any(item["disposition"] == "DISPATCH" for item in candidates) else "HOLD",
    }


def _positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExecutorBlock(f"{label} must be a positive integer")
    return value


def _validate_dispatch_candidate_binding(
    candidate_value: Mapping[str, Any],
    snapshot_value: Mapping[str, Any],
    repository: str,
    *,
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind a dispatch candidate to the local exact-head contract and tree.

    The Action keeps the original snapshot alongside the plan.  That artifact
    is useful evidence, but it is not trusted on its own: this validator
    recomputes the local exact ``HEAD`` snapshot and requires byte-equivalent
    workflow inventory data before it accepts the candidate.  It therefore
    cannot turn a self-consistent, supplied candidate/run pair into accepted
    evidence for a different workflow, commit, tree, or workflow blob.
    """

    candidate = dict(_mapping(candidate_value, "dispatch candidate"))
    supplied_snapshot = dict(_mapping(snapshot_value, "dispatch snapshot"))
    contract = load_contract(root)
    _validate_contract_shape(contract, root)
    authority = _mapping(contract.get("authority"), "dispatch contract authority")
    if repository != authority.get("repository"):
        raise ExecutorBlock("dispatch repository differs from the contract authority")

    exact_snapshot = snapshot(root)
    for field in ("schema", "contract_id", "contract_path", "contract_sha256", "head_sha", "tree_sha"):
        if supplied_snapshot.get(field) != exact_snapshot.get(field):
            raise ExecutorBlock(f"dispatch snapshot differs from the local exact snapshot: {field}")

    supplied_inventory = supplied_snapshot.get("workflow_inventory")
    if not isinstance(supplied_inventory, list):
        raise ExecutorBlock("dispatch snapshot workflow inventory is missing")
    supplied_inventory_sha256 = sha256_bytes(canonical_json_bytes(supplied_inventory))
    if supplied_snapshot.get("workflow_inventory_sha256") != supplied_inventory_sha256:
        raise ExecutorBlock("dispatch snapshot workflow inventory digest is invalid")
    if supplied_inventory != exact_snapshot["workflow_inventory"]:
        raise ExecutorBlock("dispatch snapshot workflow inventory differs from the local exact tree")
    if supplied_snapshot.get("workflow_inventory_sha256") != exact_snapshot["workflow_inventory_sha256"]:
        raise ExecutorBlock("dispatch snapshot workflow inventory digest differs from the local exact tree")

    workflow_id = _string(candidate.get("workflow_id"), "dispatch candidate workflow id")
    workflow_path = _string(candidate.get("workflow_path"), "dispatch candidate workflow path")
    workflow_name = _string(candidate.get("workflow_name"), "dispatch candidate workflow name")
    expected_ref = _string(candidate.get("ref"), "dispatch candidate ref")
    expected_head = _sha(candidate.get("head_sha"), "dispatch candidate head")
    expected_tree = _sha(candidate.get("tree_sha"), "dispatch candidate tree")
    workflow_blob_sha = _sha(candidate.get("workflow_blob_sha"), "dispatch candidate workflow blob")

    policy = _mapping(contract.get("dispatch_policy"), "dispatch policy")
    if expected_ref != policy.get("dispatch_ref"):
        raise ExecutorBlock("dispatch candidate ref differs from the contract dispatch ref")
    authorized = [
        _mapping(value, "authorized dispatch workflow")
        for value in policy.get("authorized_workflows", [])
    ]
    matched = [
        value
        for value in authorized
        if value.get("workflow_id") == workflow_id
        and value.get("workflow_path") == workflow_path
        and value.get("workflow_name") == workflow_name
    ]
    if len(matched) != 1:
        raise ExecutorBlock("dispatch candidate workflow id/path/name is not exactly contract-authorized")
    authorized_workflow = matched[0]
    if candidate.get("external_effect") != authorized_workflow.get("external_effect"):
        raise ExecutorBlock("dispatch candidate external-effect boundary differs from the contract")
    if candidate.get("required_artifact_prefix") != authorized_workflow.get("required_artifact_prefix"):
        raise ExecutorBlock("dispatch candidate artifact boundary differs from the contract")
    if expected_head != exact_snapshot["head_sha"] or expected_tree != exact_snapshot["tree_sha"]:
        raise ExecutorBlock("dispatch candidate head or tree differs from the local exact snapshot")

    inventory_by_path = {
        value["path"]: value["blob_sha"]
        for value in exact_snapshot["workflow_inventory"]
    }
    if inventory_by_path.get(workflow_path) != workflow_blob_sha:
        raise ExecutorBlock("dispatch candidate workflow blob differs from the local exact tree")
    return candidate, exact_snapshot


def validate_dispatch_reobservation(
    dispatch_request_bytes: bytes,
    dispatch_response_bytes: bytes,
    workflow_value: Mapping[str, Any],
    run_value: Mapping[str, Any],
    candidate: Mapping[str, Any],
    snapshot_value: Mapping[str, Any],
    repository: str,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate the one causal REST reobservation following a dispatch POST.

    The workflow-dispatch endpoint returns the created run identifier.  This
    validator deliberately consumes that identifier directly: it does not list
    runs, retry, sleep, or infer a relationship from a matching workflow name.
    The resulting receipt is technical transport evidence only and cannot
    promote a workflow conclusion into a gate, merge, deployment, or effect.
    """

    try:
        request_value = json.loads(dispatch_request_bytes.decode("utf-8"))
        response_value = json.loads(dispatch_response_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock("dispatch request or response is not exact UTF-8 JSON") from exc
    request = _mapping(request_value, "dispatch request")
    response = _mapping(response_value, "dispatch response")
    candidate, exact_snapshot = _validate_dispatch_candidate_binding(
        candidate, snapshot_value, repository, root=root
    )
    candidate_workflow_id = _string(candidate.get("workflow_id"), "dispatch candidate workflow id")
    expected_ref = _string(candidate.get("ref"), "dispatch candidate ref")
    expected_head = _sha(candidate.get("head_sha"), "dispatch candidate head")
    expected_tree = _sha(candidate.get("tree_sha"), "dispatch candidate tree")
    workflow_path = _string(candidate.get("workflow_path"), "dispatch candidate workflow path")
    workflow_name = _string(candidate.get("workflow_name"), "dispatch candidate workflow name")
    workflow_blob_sha = _sha(candidate.get("workflow_blob_sha"), "dispatch candidate workflow blob")
    if dict(request) != {"ref": expected_ref}:
        raise ExecutorBlock("dispatch request differs from the exact main ref")
    if set(response) != {"workflow_run_id", "run_url", "html_url"}:
        raise ExecutorBlock("dispatch response fields differ from the documented exact response")
    run_id = _positive_integer(response.get("workflow_run_id"), "dispatch response workflow_run_id")
    expected_run_url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}"
    expected_html_url = f"https://github.com/{repository}/actions/runs/{run_id}"
    if response.get("run_url") != expected_run_url or response.get("html_url") != expected_html_url:
        raise ExecutorBlock("dispatch response URLs do not bind the returned run id and repository")

    workflow = _mapping(workflow_value, "dispatched workflow")
    workflow_id = _positive_integer(workflow.get("id"), "dispatched workflow id")
    if workflow.get("name") != workflow_name or workflow.get("path") != workflow_path:
        raise ExecutorBlock("dispatched workflow id/path/name does not match the authorized candidate")
    if workflow.get("state") != "active":
        raise ExecutorBlock("dispatched workflow is not active")

    run = _mapping(run_value, "dispatched workflow run")
    if _positive_integer(run.get("id"), "reobserved workflow run id") != run_id:
        raise ExecutorBlock("reobserved workflow run id differs from dispatch response")
    if _positive_integer(run.get("workflow_id"), "reobserved workflow id") != workflow_id:
        raise ExecutorBlock("reobserved workflow id differs from authorized workflow")
    if run.get("name") != workflow_name or run.get("event") != "workflow_dispatch":
        raise ExecutorBlock("reobserved run name or event is not the authorized dispatch")
    if _sha(run.get("head_sha"), "reobserved workflow head") != expected_head:
        raise ExecutorBlock("reobserved workflow head differs from exact dispatch head")
    if run.get("head_branch") != expected_ref:
        raise ExecutorBlock("reobserved workflow branch differs from exact dispatch ref")
    head_commit = _mapping(run.get("head_commit"), "reobserved workflow head commit")
    if _sha(head_commit.get("tree_id"), "reobserved workflow head tree") != expected_tree:
        raise ExecutorBlock("reobserved workflow tree differs from exact dispatch tree")
    run_repository = _mapping(run.get("repository"), "reobserved run repository")
    head_repository = _mapping(run.get("head_repository"), "reobserved run head repository")
    if run_repository.get("full_name") != repository or head_repository.get("full_name") != repository:
        raise ExecutorBlock("reobserved run repository or head repository differs from Authority")
    status = _string(run.get("status"), "reobserved workflow status")
    if status not in ACTIVE_RUN_STATUSES | {"completed"}:
        raise ExecutorBlock("reobserved workflow status is not an admitted dispatch lifecycle state")

    return {
        "schema": "qikvrt_workflow_executor_dispatch_reobservation_v1",
        "state": "DISPATCH_ACCEPTED_EXACT_RUN_REOBSERVED",
        "repository": repository,
        "dispatch": {
            "request_sha256": sha256_bytes(dispatch_request_bytes),
            "response_sha256": sha256_bytes(dispatch_response_bytes),
            "workflow_run_id": run_id,
            "run_url": expected_run_url,
            "html_url": expected_html_url,
        },
        "workflow": {
            "id": workflow_id,
            "candidate_id": candidate_workflow_id,
            "path": workflow_path,
            "name": workflow_name,
            "blob_sha": workflow_blob_sha,
        },
        "exact_snapshot": {
            "contract_sha256": exact_snapshot["contract_sha256"],
            "head_sha": exact_snapshot["head_sha"],
            "tree_sha": exact_snapshot["tree_sha"],
            "workflow_inventory_sha256": exact_snapshot["workflow_inventory_sha256"],
        },
        "run": {
            "id": run_id,
            "event": "workflow_dispatch",
            "head_sha": expected_head,
            "tree_sha": expected_tree,
            "ref": expected_ref,
            "status": status,
        },
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
            "DEPLOYMENT": False,
        },
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


def _read_bytes(path: Path, label: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ExecutorBlock(f"cannot read {label}: {exc}") from exc


def _read_json_object(path: Path, label: str) -> Mapping[str, Any]:
    value = _read_json_file(path, label)
    return _mapping(value, label)


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
    template = subcommands.add_parser("node-receipt-template")
    template.add_argument("--node-repository", required=True)
    template.add_argument("--node-branch", required=True)
    template.add_argument("--json", action="store_true")
    receipt = subcommands.add_parser("validate-node-receipt")
    receipt.add_argument("--receipt", type=Path, required=True)
    receipt.add_argument("--node-repository", required=True)
    receipt.add_argument("--node-branch", required=True)
    receipt.add_argument("--json", action="store_true")
    dispatch = subcommands.add_parser("validate-dispatch-reobservation")
    dispatch.add_argument("--dispatch-request", type=Path, required=True)
    dispatch.add_argument("--dispatch-response", type=Path, required=True)
    dispatch.add_argument("--workflow", type=Path, required=True)
    dispatch.add_argument("--run", type=Path, required=True)
    dispatch.add_argument("--candidate", type=Path, required=True)
    dispatch.add_argument("--snapshot", type=Path, required=True)
    dispatch.add_argument("--repository", required=True)
    dispatch.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command in {"snapshot", "check", "plan"}:
            baseline = _read_json_file(arguments.baseline, "baseline") if arguments.baseline else None
            value = snapshot(baseline=baseline if isinstance(baseline, Mapping) else None)
            if arguments.expect_head is not None and value["head_sha"] != arguments.expect_head:
                raise ExecutorBlock("EXACT_HEAD_DRIFT")
            if arguments.command == "plan":
                runs = _read_json_file(arguments.runs_file, "workflow runs")
                value = dispatch_plan(value, runs, arguments.ref)
        elif arguments.command == "node-receipt-template":
            value = build_node_receipt(arguments.node_repository, arguments.node_branch)
        elif arguments.command == "validate-node-receipt":
            receipt = _read_json_file(arguments.receipt, "node continuity receipt")
            if not isinstance(receipt, Mapping):
                raise ExecutorBlock("node continuity receipt must be an object")
            value = validate_node_receipt(receipt, arguments.node_repository, arguments.node_branch)
        else:
            value = validate_dispatch_reobservation(
                _read_bytes(arguments.dispatch_request, "dispatch request"),
                _read_bytes(arguments.dispatch_response, "dispatch response"),
                _read_json_object(arguments.workflow, "dispatched workflow"),
                _read_json_object(arguments.run, "dispatched workflow run"),
                _read_json_object(arguments.candidate, "dispatch candidate"),
                _read_json_object(arguments.snapshot, "dispatch snapshot"),
                _string(arguments.repository, "repository"),
            )
        _emit(value, arguments.json)
        return 0
    except ExecutorBlock as exc:
        print(f"BLOCK WORKFLOW_EXECUTOR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
