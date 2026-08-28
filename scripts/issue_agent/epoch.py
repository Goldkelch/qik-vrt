#!/usr/bin/env python3
"""Prepare, execute, and reduce one finite N-by-N read/verify/plan epoch."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.issue_agent.binding import canonical_bytes, json_loads_strict, sha256_bytes, validate_request


MAX_NODES = 16
MAX_LANES = 256
OPERATION_SCHEMA = "qikvrt_issue_lane_read_verify_plan_v2"
POSITIVE_INT = re.compile(r"^[1-9][0-9]*$")
FALSE_CLAIMS = {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def sidecar_path(path: Path) -> Path:
    return path.with_suffix(".sha256")


def write_sidecar(path: Path) -> None:
    sidecar_path(path).write_text(
        f"{sha256_bytes(path.read_bytes())}  {path.name}\n",
        encoding="utf-8",
    )


def verify_sidecar(path: Path) -> str:
    sidecar = sidecar_path(path)
    if not sidecar.is_file():
        raise ValueError(f"missing sidecar for {path.name}")
    fields = sidecar.read_text(encoding="utf-8").strip().split()
    if len(fields) != 2 or fields[1] != path.name:
        raise ValueError(f"invalid sidecar for {path.name}")
    actual = sha256_bytes(path.read_bytes())
    if fields[0] != actual:
        raise ValueError(f"digest mismatch for {path.name}")
    return actual


def validate_core_bundle(directory: Path, *, verify_authority: bool) -> dict[str, Any]:
    request_path = directory / "REQUEST.json"
    event_path = directory / "EVENT.json"
    context_path = directory / "CONTEXT.md"
    for path in (request_path, event_path, context_path):
        if not path.is_file():
            raise ValueError(f"missing core artifact {path.name}")
    verify_sidecar(request_path)
    verify_sidecar(event_path)
    request_value = validate_request(
        json_loads_strict(request_path.read_text(encoding="utf-8")),
        repository_root=ROOT,
        verify_git=verify_authority,
    )
    binding = request_value["binding"]
    if sha256_bytes(context_path.read_bytes()) != binding["context_sha256"]:
        raise ValueError("repository context digest differs from request binding")
    event_value = json_loads_strict(event_path.read_text(encoding="utf-8"))
    if event_value != {
        "schema": "qikvrt_issue_agent_event_binding_v1",
        "binding": binding,
        "request_fingerprint": request_value["request_fingerprint"],
    }:
        raise ValueError("event artifact differs from canonical request binding")
    return request_value


def _prepare_bundle_sha256(directory: Path) -> str:
    projection = {
        "REQUEST.json": verify_sidecar(directory / "REQUEST.json"),
        "EVENT.json": verify_sidecar(directory / "EVENT.json"),
        "CONTEXT.md": sha256_bytes((directory / "CONTEXT.md").read_bytes()),
    }
    for name in ("ANSWER.md",):
        path = directory / name
        if path.is_file():
            projection[name] = sha256_bytes(path.read_bytes())
    evaluation_path = directory / "EVALUATION.json"
    if evaluation_path.is_file():
        projection["EVALUATION.json"] = verify_sidecar(evaluation_path)
    return sha256_bytes(canonical_bytes(projection))


def build_epoch(request_value: dict[str, Any], prepare_bundle_sha256: str) -> tuple[dict[str, Any], dict[str, Any]]:
    request_value = validate_request(
        request_value,
        repository_root=ROOT,
        verify_git=False,
    )
    if not re.fullmatch(r"[0-9a-f]{64}", prepare_bundle_sha256):
        raise ValueError("prepare bundle digest is invalid")
    binding = request_value["binding"]
    nodes = binding["active_mesh_nodes"]
    if len(nodes) > MAX_NODES:
        raise ValueError("active mesh exceeds one bounded 256-lane epoch")
    epoch_input = {
        "operation_schema": OPERATION_SCHEMA,
        "request_fingerprint": request_value["request_fingerprint"],
        "prepare_bundle_sha256": prepare_bundle_sha256,
        "authority_head": binding["authority_head"],
        "authority_tree": binding["authority_tree"],
        "handler_policy_sha256": binding["handler_policy_sha256"],
        "registry_sha256": binding["registry_sha256"],
        "intake_code_sha256": binding["intake_code_sha256"],
        "nodes": nodes,
    }
    epoch_id = sha256_bytes(canonical_bytes(epoch_input))
    lanes: list[dict[str, Any]] = []
    node_count = len(nodes)
    for row, source in enumerate(nodes):
        for column, target in enumerate(nodes):
            lane_index = row * node_count + column
            lane_binding = {
                "epoch_id": epoch_id,
                "lane_index": lane_index,
                "row": row,
                "column": column,
                "source_repository": source,
                "target_repository": target,
                "request_fingerprint": request_value["request_fingerprint"],
                "prepare_bundle_sha256": prepare_bundle_sha256,
                "operation_schema": OPERATION_SCHEMA,
            }
            lanes.append({
                **lane_binding,
                "lane_id": sha256_bytes(canonical_bytes(lane_binding)),
                "allowed_operations": ["READ", "VERIFY", "PLAN", "RECEIPT"],
                "writer_authority": False,
                "state": "DECLARED_NOT_EXECUTED",
            })
    if len(lanes) != node_count * node_count or len(lanes) > MAX_LANES:
        raise ValueError("quadratic lane cardinality is invalid")
    epoch = {
        "schema": "qikvrt_issue_work_epoch_v2",
        "epoch_id": epoch_id,
        **epoch_input,
        "node_count": node_count,
        "lane_count": len(lanes),
        "mapping": "lane_index=row*N+column",
        "lanes": lanes,
        "fan_in_order": "ROW_MAJOR_LANE_INDEX_ASCENDING",
        "lane_effect_boundary": "LOCAL_READ_VERIFY_PLAN_RECEIPT_ONLY",
        "fanout_observed": False,
        "lane_work_observed": False,
        "fanin_observed": False,
        "declared_candidate_writer_count": 1,
        "authority_main_writer_admission_observed": False,
        "claims": FALSE_CLAIMS,
    }
    matrix = {
        "schema": "qikvrt_issue_work_matrix_v2",
        "epoch_id": epoch_id,
        "include": [
            {"lane_index": lane["lane_index"], "lane_id": lane["lane_id"]}
            for lane in lanes
        ],
    }
    return epoch, matrix


def prepare(directory: Path, *, verify_authority: bool = True) -> None:
    request_value = validate_core_bundle(directory, verify_authority=verify_authority)
    epoch, matrix = build_epoch(request_value, _prepare_bundle_sha256(directory))
    for name, value in (("WORK_EPOCH.json", epoch), ("MATRIX.json", matrix)):
        path = directory / name
        write_json(path, value)
        write_sidecar(path)
    verify_prepared(directory, verify_authority=verify_authority)


def verify_prepared(directory: Path, *, verify_authority: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    request_value = validate_core_bundle(directory, verify_authority=verify_authority)
    expected_epoch, expected_matrix = build_epoch(request_value, _prepare_bundle_sha256(directory))
    epoch_path = directory / "WORK_EPOCH.json"
    matrix_path = directory / "MATRIX.json"
    verify_sidecar(epoch_path)
    verify_sidecar(matrix_path)
    actual_epoch = json_loads_strict(epoch_path.read_text(encoding="utf-8"))
    actual_matrix = json_loads_strict(matrix_path.read_text(encoding="utf-8"))
    if actual_epoch != expected_epoch:
        raise ValueError("work epoch differs from canonical request projection")
    if actual_matrix != expected_matrix:
        raise ValueError("matrix differs from canonical work epoch")
    return actual_epoch, actual_matrix


def run_identity(run_id: str, run_attempt: str) -> tuple[str, str]:
    if not POSITIVE_INT.fullmatch(run_id) or not POSITIVE_INT.fullmatch(run_attempt):
        raise ValueError("workflow run identity is invalid")
    return run_id, run_attempt


def pair_plan(epoch: dict[str, Any], lane: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical source/target-specific local handoff plan for one lane."""
    relation = "SELF" if lane["source_repository"] == lane["target_repository"] else "CROSS_REPOSITORY_PLANNED_ONLY"
    return {
        "schema": "qikvrt_issue_lane_pair_plan_v1",
        "epoch_id": epoch["epoch_id"],
        "lane_id": lane["lane_id"],
        "lane_index": lane["lane_index"],
        "source_repository": lane["source_repository"],
        "target_repository": lane["target_repository"],
        "relation": relation,
        "operations": [
            {
                "ordinal": 0,
                "operation": "READ_BOUND_LOCAL_PREPARE_BUNDLE",
                "input_sha256": epoch["prepare_bundle_sha256"],
            },
            {
                "ordinal": 1,
                "operation": "VERIFY_EXACT_SOURCE_TARGET_LANE_BINDING",
                "lane_declaration_sha256": sha256_bytes(canonical_bytes(lane)),
            },
            {
                "ordinal": 2,
                "operation": "PLAN_REPOSITORY_NATIVE_HANDOFF",
                "remote_target_contacted": False,
                "substantive_handler_execution": False,
            },
        ],
        "effect_boundary": "LOCAL_PLAN_ONLY",
    }


def build_lane_receipt(
    directory: Path,
    lane_index: int,
    run_id: str,
    run_attempt: str,
    *,
    verify_authority: bool,
) -> dict[str, Any]:
    run_identity(run_id, run_attempt)
    epoch, matrix = verify_prepared(directory, verify_authority=verify_authority)
    if not isinstance(lane_index, int) or lane_index < 0 or lane_index >= epoch["lane_count"]:
        raise ValueError("lane index is outside the prepared epoch")
    lane = epoch["lanes"][lane_index]
    plan = pair_plan(epoch, lane)
    matrix_lane = matrix["include"][lane_index]
    if matrix_lane != {"lane_index": lane_index, "lane_id": lane["lane_id"]}:
        raise ValueError("matrix lane differs from epoch declaration")
    checks = {
        "request_sha256": verify_sidecar(directory / "REQUEST.json"),
        "event_sha256": verify_sidecar(directory / "EVENT.json"),
        "context_sha256": sha256_bytes((directory / "CONTEXT.md").read_bytes()),
        "work_epoch_sha256": verify_sidecar(directory / "WORK_EPOCH.json"),
        "matrix_sha256": verify_sidecar(directory / "MATRIX.json"),
        "lane_declaration_sha256": sha256_bytes(canonical_bytes(lane)),
        "pair_plan_sha256": sha256_bytes(canonical_bytes(plan)),
    }
    for name in ("ANSWER.md",):
        path = directory / name
        if path.is_file():
            checks[f"{path.stem.lower()}_sha256"] = sha256_bytes(path.read_bytes())
    evaluation_path = directory / "EVALUATION.json"
    if evaluation_path.is_file():
        checks["evaluation_sha256"] = verify_sidecar(evaluation_path)
    return {
        "schema": "qikvrt_issue_work_lane_receipt_v2",
        "epoch_id": epoch["epoch_id"],
        "request_fingerprint": epoch["request_fingerprint"],
        "prepare_bundle_sha256": epoch["prepare_bundle_sha256"],
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "workflow_job": "lane",
        "matrix_lane_index": lane_index,
        "lane_index": lane["lane_index"],
        "lane_id": lane["lane_id"],
        "row": lane["row"],
        "column": lane["column"],
        "source_repository": lane["source_repository"],
        "target_repository": lane["target_repository"],
        "operation_schema": OPERATION_SCHEMA,
        "pair_plan": plan,
        "checks": checks,
        "state": "LOCAL_PAIR_BINDING_AND_PLAN_VERIFIED",
        "remote_target_repository_contacted": False,
        "writer_authority": False,
        "repository_content_effect": "NONE",
        "authority_lifecycle_effect": "NONE",
        "wrapper_transport_effects_declared": ["ACTIONS_ARTIFACT_UPLOAD"],
        "claims": FALSE_CLAIMS,
    }


def run_lane(
    directory: Path,
    lane_index: int,
    run_id: str,
    run_attempt: str,
    output: Path,
    *,
    verify_authority: bool = True,
) -> None:
    receipt = build_lane_receipt(
        directory,
        lane_index,
        run_id,
        run_attempt,
        verify_authority=verify_authority,
    )
    path = output / "LANE_RECEIPT.json"
    write_json(path, receipt)
    write_sidecar(path)


def _receipt_paths(receipts_root: Path) -> list[Path]:
    files = sorted(path for path in receipts_root.rglob("*") if path.is_file())
    allowed = {"LANE_RECEIPT.json", "LANE_RECEIPT.sha256"}
    if any(path.name not in allowed for path in files):
        raise ValueError("receipt input contains an unexpected file")
    receipts = [path for path in files if path.name == "LANE_RECEIPT.json"]
    if not receipts:
        raise ValueError("no lane receipt was observed")
    return receipts


def _canonical_fanin(
    epoch: dict[str, Any],
    receipts: list[dict[str, Any]],
    run_id: str,
    run_attempt: str,
) -> dict[str, Any]:
    entries = [
        {
            "lane_index": receipt["lane_index"],
            "lane_id": receipt["lane_id"],
            "sha256": sha256_bytes(canonical_bytes(receipt)),
        }
        for receipt in receipts
    ]
    return {
        "schema": "qikvrt_issue_work_fanin_receipt_v2",
        "epoch_id": epoch["epoch_id"],
        "request_fingerprint": epoch["request_fingerprint"],
        "prepare_bundle_sha256": epoch["prepare_bundle_sha256"],
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "expected_lane_count": epoch["lane_count"],
        "received_lane_count": len(receipts),
        "lane_receipts": entries,
        "aggregate_sha256": sha256_bytes(canonical_bytes(entries)),
        "state": "READY_FOR_CANDIDATE_REF_CAS",
        "fanout_observed": True,
        "lane_work_observed": True,
        "fanin_observed": True,
        "candidate_writer_admission_observed": False,
        "authority_main_writer_admission_observed": False,
        "repository_content_effect": "NONE",
        "authority_lifecycle_effect": "NONE",
        "wrapper_transport_effects_declared": ["ACTIONS_ARTIFACT_UPLOAD"],
        "claims": FALSE_CLAIMS,
    }


def reduce_receipts(
    directory: Path,
    receipts_root: Path,
    run_id: str,
    run_attempt: str,
    output: Path,
    *,
    verify_authority: bool = True,
) -> None:
    run_identity(run_id, run_attempt)
    epoch, _ = verify_prepared(directory, verify_authority=verify_authority)
    receipts_by_index: dict[int, dict[str, Any]] = {}
    lane_ids: set[str] = set()
    try:
        for path in _receipt_paths(receipts_root):
            verify_sidecar(path)
            receipt = json_loads_strict(path.read_text(encoding="utf-8"))
            index = receipt.get("lane_index")
            if not isinstance(index, int) or index in receipts_by_index:
                raise ValueError("duplicate or invalid lane index")
            if receipt.get("lane_id") in lane_ids:
                raise ValueError("duplicate lane id")
            expected = build_lane_receipt(
                directory,
                index,
                run_id,
                run_attempt,
                verify_authority=verify_authority,
            )
            if receipt != expected:
                raise ValueError(f"lane receipt {index} differs from canonical executed plan")
            receipts_by_index[index] = receipt
            lane_ids.add(receipt["lane_id"])
        expected_indexes = set(range(epoch["lane_count"]))
        actual_indexes = set(receipts_by_index)
        if actual_indexes != expected_indexes:
            missing = sorted(expected_indexes - actual_indexes)
            surplus = sorted(actual_indexes - expected_indexes)
            raise ValueError(f"lane receipt cardinality mismatch missing={missing} surplus={surplus}")
        receipts = [receipts_by_index[index] for index in range(epoch["lane_count"])]
        combined_path = output / "LANE_RECEIPTS.json"
        write_json(combined_path, receipts)
        write_sidecar(combined_path)
        fanin_path = output / "FANIN.json"
        write_json(fanin_path, _canonical_fanin(epoch, receipts, run_id, run_attempt))
        write_sidecar(fanin_path)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        hold = {
            "schema": "qikvrt_issue_work_fanin_hold_v2",
            "epoch_id": epoch["epoch_id"],
            "request_fingerprint": epoch["request_fingerprint"],
            "workflow_run_id": run_id,
            "workflow_run_attempt": run_attempt,
            "state": "HOLD",
            "failure_class": "INCOMPLETE_OR_INVALID_LANE_RECEIPT_SET",
            "reason": str(exc),
            "candidate_writer_admission_observed": False,
            "authority_main_writer_admission_observed": False,
            "repository_content_effect": "NONE",
            "authority_lifecycle_effect": "NONE",
            "wrapper_transport_effects_declared": ["ACTIONS_ARTIFACT_UPLOAD"],
            "claims": FALSE_CLAIMS,
        }
        hold_path = output / "FANIN.json"
        write_json(hold_path, hold)
        write_sidecar(hold_path)
        raise ValueError(str(exc)) from exc


def verify_reduction(directory: Path, *, verify_authority: bool = True) -> None:
    epoch, _ = verify_prepared(directory, verify_authority=verify_authority)
    receipts_path = directory / "LANE_RECEIPTS.json"
    fanin_path = directory / "FANIN.json"
    verify_sidecar(receipts_path)
    verify_sidecar(fanin_path)
    receipts = json_loads_strict(receipts_path.read_text(encoding="utf-8"))
    fanin = json_loads_strict(fanin_path.read_text(encoding="utf-8"))
    if not isinstance(receipts, list) or len(receipts) != epoch["lane_count"]:
        raise ValueError("combined lane receipt count differs from epoch")
    run_id, run_attempt = run_identity(
        str(fanin.get("workflow_run_id")),
        str(fanin.get("workflow_run_attempt")),
    )
    expected_receipts = [
        build_lane_receipt(
            directory,
            index,
            run_id,
            run_attempt,
            verify_authority=verify_authority,
        )
        for index in range(epoch["lane_count"])
    ]
    if receipts != expected_receipts:
        raise ValueError("combined lane receipts differ from canonical executed plans")
    if fanin != _canonical_fanin(epoch, expected_receipts, run_id, run_attempt):
        raise ValueError("fan-in differs from canonical receipt reduction")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("prepare", "verify-prepare", "verify-reduction"):
        command = sub.add_parser(mode)
        command.add_argument("directory", type=Path)
    lane = sub.add_parser("run-lane")
    lane.add_argument("directory", type=Path)
    lane.add_argument("--lane-index", required=True, type=int)
    lane.add_argument("--run-id", required=True)
    lane.add_argument("--run-attempt", required=True)
    lane.add_argument("--output", required=True, type=Path)
    reducer = sub.add_parser("reduce")
    reducer.add_argument("directory", type=Path)
    reducer.add_argument("--receipts-root", required=True, type=Path)
    reducer.add_argument("--run-id", required=True)
    reducer.add_argument("--run-attempt", required=True)
    reducer.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "prepare":
            prepare(args.directory)
        elif args.mode == "verify-prepare":
            verify_prepared(args.directory)
        elif args.mode == "run-lane":
            run_lane(
                args.directory,
                args.lane_index,
                args.run_id,
                args.run_attempt,
                args.output,
            )
        elif args.mode == "reduce":
            reduce_receipts(
                args.directory,
                args.receipts_root,
                args.run_id,
                args.run_attempt,
                args.output,
            )
        else:
            verify_reduction(args.directory)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"BLOCK: {exc}") from exc


if __name__ == "__main__":
    main()
