#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed planner for future QIK-VRT mesh replica work.

This controller validates an exact-head request and a caller-supplied liveness
observation. It has no apply operation: it emits only ``NOOP`` or ``HOLD`` and
performs no network, clone, fork, ref, credential, or repository mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/MESH_REPLICA_ORCHESTRATION_CONTRACT_V1.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\Z")


class ReplicaPlanBlock(RuntimeError):
    """An invalid plan input or unsafe planning precondition."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReplicaPlanBlock(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReplicaPlanBlock(f"{label} must be a non-empty string")
    return value


def _sha(value: Any, label: str) -> str:
    value = _string(value, label)
    if not SHA_RE.fullmatch(value):
        raise ReplicaPlanBlock(f"{label} must be a lower-case 40-character Git SHA")
    return value


def _sha256(value: Any, label: str) -> str:
    value = _string(value, label)
    if not SHA256_RE.fullmatch(value):
        raise ReplicaPlanBlock(f"{label} must be a lower-case SHA-256")
    return value


def _bounded_identifier(value: Any, label: str) -> str:
    value = _string(value, label)
    if not IDENTIFIER_RE.fullmatch(value):
        raise ReplicaPlanBlock(f"{label} is not a bounded identifier")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReplicaPlanBlock(f"{label} must be a non-negative integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    value = _nonnegative_int(value, label)
    if value == 0:
        raise ReplicaPlanBlock(f"{label} must be positive")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ReplicaPlanBlock(f"{label} must be a list of non-empty strings")
    return list(value)


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
        raise ReplicaPlanBlock(f"local identity observation failed: {detail}")
    return completed.stdout.strip()


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    path = root / CONTRACT_RELATIVE_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplicaPlanBlock(f"cannot load replica orchestration contract: {exc}") from exc
    result = dict(_mapping(value, "replica orchestration contract"))
    if result.get("schema") != "qikvrt_mesh_replica_orchestration_contract_v1":
        raise ReplicaPlanBlock("replica orchestration contract schema is invalid")
    if result.get("contract_id") != "qikvrt-mesh-replica-orchestration-v1":
        raise ReplicaPlanBlock("replica orchestration contract id is invalid")
    return result


def _contract_sha256(root: Path) -> str:
    try:
        return sha256_bytes((root / CONTRACT_RELATIVE_PATH).read_bytes())
    except OSError as exc:
        raise ReplicaPlanBlock(f"cannot hash replica orchestration contract: {exc}") from exc


def _validate_contract(contract: Mapping[str, Any], root: Path) -> None:
    authority = _mapping(contract.get("authority"), "contract authority")
    if authority.get("repository") != "Goldkelch/qik-vrt" or authority.get("entrypoint") != "AI":
        raise ReplicaPlanBlock("replica orchestration authority binding is invalid")
    if authority.get("workflow_executor_contract_path") != "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json":
        raise ReplicaPlanBlock("replica orchestration does not bind the workflow executor contract")
    controller = _mapping(contract.get("controller"), "contract controller")
    if controller.get("path") != "tools/qikvrt_mesh_replica_orchestrator.py":
        raise ReplicaPlanBlock("replica orchestration controller path is invalid")
    if not (root / controller["path"]).is_file():
        raise ReplicaPlanBlock("replica orchestration controller is absent")
    if contract.get("mode") != "PLAN_VALIDATE_ONLY" or contract.get("apply_mode") != "NOT_IMPLEMENTED":
        raise ReplicaPlanBlock("replica orchestration is not plan-only")
    if contract.get("execution_effect") != "NONE":
        raise ReplicaPlanBlock("replica orchestration exceeds the no-effect boundary")
    for key, expected in (("repository_writes", "NONE"), ("network", "NONE"), ("process_execution", "LOCAL_GIT_REV_PARSE_ONLY")):
        if controller.get(key) != expected:
            raise ReplicaPlanBlock(f"replica orchestration controller.{key} is not bounded")
    allowed = _string_list(contract.get("allowed_source_repositories"), "allowed source repositories")
    if allowed != ["Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"]:
        raise ReplicaPlanBlock("replica orchestration source allowlist is invalid")
    caps = _mapping(contract.get("resource_caps"), "resource caps")
    for key in (
        "max_parallel_read_only_replicas",
        "max_ttl_seconds",
        "max_disk_bytes_per_replica",
        "max_cpu_seconds_per_replica",
        "max_network_bytes_per_replica",
    ):
        _positive_int(caps.get(key), f"resource caps.{key}")
    admission = _mapping(contract.get("admission"), "admission")
    for key in (
        "require_exact_source_head_and_tree",
        "require_exact_observation_head_and_tree",
        "require_fresh_bound_node_liveness",
    ):
        if admission.get(key) is not True:
            raise ReplicaPlanBlock(f"replica orchestration admission.{key} is not required")
    if admission.get("accepted_node_liveness") != "FRESH_BOUND":
        raise ReplicaPlanBlock("replica orchestration liveness state is invalid")
    if _nonnegative_int(admission.get("max_active_productive_writers"), "max active writers") != 0:
        raise ReplicaPlanBlock("replica orchestration permits a competing productive writer")
    if _nonnegative_int(admission.get("max_queued_productive_runs"), "max queued runs") != 2:
        raise ReplicaPlanBlock("replica orchestration queue cap is invalid")
    if contract.get("requires_exact_execution_authorization") is not True:
        raise ReplicaPlanBlock("replica orchestration does not require exact execution authorization")
    if not isinstance(contract.get("forbidden_operations"), list) or "git_clone" not in contract["forbidden_operations"]:
        raise ReplicaPlanBlock("replica orchestration clone boundary is absent")


def local_snapshot(root: Path = ROOT) -> dict[str, str]:
    contract = load_contract(root)
    _validate_contract(contract, root)
    return {
        "repository": _mapping(contract["authority"], "contract authority")["repository"],
        "head_sha": _sha(_git(root, "rev-parse", "--verify", "HEAD^{commit}"), "local head"),
        "tree_sha": _sha(_git(root, "rev-parse", "--verify", "HEAD^{tree}"), "local tree"),
        "contract_sha256": _contract_sha256(root),
    }


def _validate_request(request: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    request = _mapping(request, "replica request")
    if request.get("schema") != "qikvrt_mesh_replica_request_v1":
        raise ReplicaPlanBlock("request.schema is invalid")
    request_id = _bounded_identifier(request.get("request_id"), "request_id")
    if request.get("mode") != "PLAN_VALIDATE_ONLY":
        raise ReplicaPlanBlock("request.mode must be PLAN_VALIDATE_ONLY")
    source = _mapping(request.get("source"), "source")
    repository = _string(source.get("repository"), "source.repository")
    if repository not in _string_list(contract["allowed_source_repositories"], "allowed source repositories"):
        raise ReplicaPlanBlock("source.repository is not allowlisted")
    if source.get("ref") != "main":
        raise ReplicaPlanBlock("source.ref must be main")
    target = _mapping(request.get("target"), "target")
    task = _mapping(request.get("task"), "task")
    resources = _mapping(request.get("resources"), "resources")
    synchronization = _mapping(request.get("synchronization"), "synchronization")
    if type(synchronization.get("requested")) is not bool:
        raise ReplicaPlanBlock("synchronization.requested must be boolean")
    return {
        "request_id": request_id,
        "source": {
            "repository": repository,
            "ref": "main",
            "head_sha": _sha(source.get("head_sha"), "source.head_sha"),
            "tree_sha": _sha(source.get("tree_sha"), "source.tree_sha"),
        },
        "target": {
            "kind": _string(target.get("kind"), "target.kind"),
            "identifier": _bounded_identifier(target.get("identifier"), "target.identifier"),
        },
        "task": {
            "selector": _bounded_identifier(task.get("selector"), "task.selector"),
            "sha256": _sha256(task.get("sha256"), "task.sha256"),
        },
        "resources": {
            "replica_count": _positive_int(resources.get("replica_count"), "resources.replica_count"),
            "ttl_seconds": _positive_int(resources.get("ttl_seconds"), "resources.ttl_seconds"),
            "disk_bytes": _positive_int(resources.get("disk_bytes"), "resources.disk_bytes"),
            "cpu_seconds": _positive_int(resources.get("cpu_seconds"), "resources.cpu_seconds"),
            "network_bytes": _nonnegative_int(resources.get("network_bytes"), "resources.network_bytes"),
        },
        "synchronization": {
            "requested": synchronization["requested"],
            "direction": _string(synchronization.get("direction"), "synchronization.direction"),
            "path_allowlist": _string_list(synchronization.get("path_allowlist"), "synchronization.path_allowlist"),
        },
    }


def _validate_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    observation = _mapping(observation, "replica observation")
    if observation.get("schema") != "qikvrt_mesh_replica_observation_v1":
        raise ReplicaPlanBlock("observation.schema is invalid")
    authority = _mapping(observation.get("authority"), "observation authority")
    if authority.get("repository") != "Goldkelch/qik-vrt":
        raise ReplicaPlanBlock("observation authority.repository is invalid")
    planned = _string_list(observation.get("planned_request_ids"), "planned_request_ids")
    if len(planned) != len(set(planned)):
        raise ReplicaPlanBlock("planned_request_ids contains a duplicate")
    return {
        "authority": {
            "repository": authority["repository"],
            "head_sha": _sha(authority.get("head_sha"), "observation authority.head_sha"),
            "tree_sha": _sha(authority.get("tree_sha"), "observation authority.tree_sha"),
        },
        "node_liveness": _string(observation.get("node_liveness"), "node_liveness"),
        "active_productive_writers": _nonnegative_int(observation.get("active_productive_writers"), "active_productive_writers"),
        "queued_productive_runs": _nonnegative_int(observation.get("queued_productive_runs"), "queued_productive_runs"),
        "planned_request_ids": planned,
    }


def _result(snapshot: Mapping[str, str], request: Mapping[str, Any] | None, state: str, blocker: str, detail: str) -> dict[str, Any]:
    return {
        "schema": "qikvrt_mesh_replica_orchestration_plan_v1",
        "contract_id": "qikvrt-mesh-replica-orchestration-v1",
        "mode": "PLAN_VALIDATE_ONLY",
        "authority_snapshot": dict(snapshot),
        "request_id": request.get("request_id") if request else None,
        "request_sha256": sha256_bytes(canonical_json_bytes(request)) if request else None,
        "state": state,
        "first_blocker": blocker,
        "detail": detail,
        "execution_effect": "NONE",
        "permitted_actions": [],
        "future_execution_required": "EXACT_SEPARATE_AUTHORIZATION_AND_REVIEWED_APPLY_MODE",
    }


def plan_replica(request: Mapping[str, Any], observation: Mapping[str, Any], root: Path = ROOT) -> dict[str, Any]:
    contract = load_contract(root)
    _validate_contract(contract, root)
    snapshot = local_snapshot(root)
    try:
        checked_request = _validate_request(request, contract)
    except ReplicaPlanBlock as exc:
        return _result(snapshot, None, "HOLD", "REQUEST_INVALID", str(exc))
    try:
        checked_observation = _validate_observation(observation)
    except ReplicaPlanBlock as exc:
        return _result(snapshot, checked_request, "HOLD", "OBSERVATION_INVALID", str(exc))
    if checked_request["source"]["repository"] != snapshot["repository"]:
        return _result(snapshot, checked_request, "HOLD", "SOURCE_REPOSITORY_NOT_CURRENT_AUTHORITY", "source repository is not the current authority")
    if checked_request["source"]["head_sha"] != snapshot["head_sha"] or checked_request["source"]["tree_sha"] != snapshot["tree_sha"]:
        return _result(snapshot, checked_request, "HOLD", "SOURCE_HEAD_TREE_DRIFT", "request is not bound to local exact head and tree")
    if checked_observation["authority"]["head_sha"] != snapshot["head_sha"] or checked_observation["authority"]["tree_sha"] != snapshot["tree_sha"]:
        return _result(snapshot, checked_request, "HOLD", "OBSERVATION_HEAD_TREE_DRIFT", "observation is not bound to local exact head and tree")
    admission = _mapping(contract["admission"], "admission")
    if checked_observation["active_productive_writers"] > admission["max_active_productive_writers"]:
        return _result(snapshot, checked_request, "HOLD", "COMPETING_PRODUCTIVE_WRITER", "another productive writer is active")
    if checked_observation["queued_productive_runs"] > admission["max_queued_productive_runs"]:
        return _result(snapshot, checked_request, "HOLD", "QUEUE_CAPACITY_EXCEEDED", "productive queue capacity is exhausted")
    if checked_observation["node_liveness"] != admission["accepted_node_liveness"]:
        return _result(snapshot, checked_request, "HOLD", "MESH_NODE_LIVENESS_UNVERIFIED", "no fresh bound node liveness receipt is available")
    if checked_request["request_id"] in checked_observation["planned_request_ids"]:
        return _result(snapshot, checked_request, "NOOP", "DUPLICATE_EXACT_REQUEST", "request already has an exact planning disposition")
    if checked_request["target"]["kind"] != "LOCAL_ISOLATED_READ_ONLY":
        return _result(snapshot, checked_request, "HOLD", "REMOTE_TARGET_NOT_AUTHORIZED", "only local read-only planning is recognized")
    if checked_request["synchronization"]["requested"]:
        return _result(snapshot, checked_request, "HOLD", "SYNCHRONIZATION_REQUIRES_SEPARATE_AUTHORIZATION", "synchronization execution is not implemented")
    caps = _mapping(contract["resource_caps"], "resource caps")
    resources = checked_request["resources"]
    if resources["replica_count"] > caps["max_parallel_read_only_replicas"] or resources["ttl_seconds"] > caps["max_ttl_seconds"] or resources["disk_bytes"] > caps["max_disk_bytes_per_replica"] or resources["cpu_seconds"] > caps["max_cpu_seconds_per_replica"] or resources["network_bytes"] > caps["max_network_bytes_per_replica"]:
        return _result(snapshot, checked_request, "HOLD", "RESOURCE_CAP_EXCEEDED", "request exceeds a fixed plan-only resource cap")
    return _result(snapshot, checked_request, "HOLD", "APPLY_MODE_NOT_IMPLEMENTED", "exact execution authorization and an independently reviewed apply mode are required")


def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplicaPlanBlock(f"cannot load {label}: {exc}") from exc
    return _mapping(value, label)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    plan = subcommands.add_parser("plan")
    plan.add_argument("--request", type=Path, required=True)
    plan.add_argument("--observation", type=Path, required=True)
    plan.add_argument("--expect-head", required=True)
    plan.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        snapshot = local_snapshot()
        if snapshot["head_sha"] != _sha(arguments.expect_head, "expected head"):
            raise ReplicaPlanBlock("EXACT_HEAD_DRIFT")
        value = plan_replica(_read_json(arguments.request, "request"), _read_json(arguments.observation, "observation"))
        if arguments.json:
            print(canonical_json_bytes(value).decode("utf-8"), end="")
        else:
            print(f"{value['state']} {value['first_blocker']} head={snapshot['head_sha']} tree={snapshot['tree_sha']}")
        return 0
    except ReplicaPlanBlock as exc:
        print(f"BLOCK MESH_REPLICA_ORCHESTRATION {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
