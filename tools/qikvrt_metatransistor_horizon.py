#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Deterministic event/depth classifier for the QIK-VRT Metatransistor Horizon.

The module never performs repository, deployment, publication, approval, merge,
or branch mutations.  It converts one exact event into a serializable terminal
frame and classifies a complete gate vector.  Destructive carrier cutting is
represented only as an exact, reviewable plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from typing import Any, Iterable, Mapping

EXPECTED_GATES = (
    "QIKVRT CI",
    "QIKVRT repository evidence materialization",
    "QIKVRT Collective Proposal Review",
    "QIKVRT code-owner review observer",
    "QIKVRT live status watch",
    "QIKVRT Spark branch work-unit core",
    "QIKVRT zero-bug continuous invariant",
    "QIKVRT explicit HOLD contract",
)
MAX_COMPUTE_DEPTH = 9
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")

READY_CONCLUSIONS = {"success"}
HOLD_CONCLUSIONS = {
    "failure",
    "action_required",
    "timed_out",
    "startup_failure",
    "cancelled",
    "stale",
}
SKIPPED_CONCLUSIONS = {"skipped", "neutral"}


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def require_sha40(value: str, field: str = "head_sha") -> str:
    if not SHA40.fullmatch(value or ""):
        raise ValueError(f"{field} must be an exact 40-hex SHA")
    return value


def classify_gate(action: str | None, conclusion: str | None) -> str:
    """Map a workflow surface to a gate state without claiming PASS."""
    action = (action or "").strip().lower()
    conclusion = (conclusion or "").strip().lower()
    if action in {"requested", "in_progress"}:
        return "CONTINUE"
    if conclusion in READY_CONCLUSIONS:
        return "READY"
    if conclusion in HOLD_CONCLUSIONS:
        return "HOLD"
    if conclusion in SKIPPED_CONCLUSIONS:
        return "SKIPPED"
    return "NOT_OBSERVED"


def default_node(repository: str) -> dict[str, str]:
    if repository == "Goldkelch/qik-vrt":
        return {
            "id": "authority",
            "repository": repository,
            "role": "AUTHORITY",
            "capability": "MASTER_MONITOR_AND_FULL_TERMINAL",
        }
    if repository == "ingolf-lohmann/qik-vrt":
        return {
            "id": "mirror",
            "repository": repository,
            "role": "MIRROR",
            "capability": "MONITOR_AND_FULL_TERMINAL",
        }
    return {
        "id": repository.replace("/", "--").lower(),
        "repository": repository,
        "role": "MESH_NODE",
        "capability": "MONITOR_ONLY",
    }


def normalize_event(source: Mapping[str, Any]) -> dict[str, Any]:
    repository = str(source.get("repository") or "")
    if not repository or "/" not in repository:
        raise ValueError("repository must be owner/name")
    gate = str(source.get("gate") or "")
    if gate not in EXPECTED_GATES:
        raise ValueError("gate is outside the fixed eight-gate set")
    head_sha = require_sha40(str(source.get("head_sha") or ""))
    run_id = int(source.get("run_id") or 0)
    if run_id < 1:
        raise ValueError("run_id must be positive")
    action = str(source.get("action") or "")
    conclusion_raw = source.get("conclusion")
    conclusion = None if conclusion_raw in {None, "", "null"} else str(conclusion_raw)
    node = dict(default_node(repository))
    supplied_node = source.get("node")
    if isinstance(supplied_node, Mapping):
        for key in ("id", "role", "capability"):
            if supplied_node.get(key):
                node[key] = str(supplied_node[key])
    node["repository"] = repository

    pr_number_raw = source.get("pr_number")
    pr_number = int(pr_number_raw) if str(pr_number_raw or "").isdigit() else None
    head_branch = str(source.get("head_branch") or "")
    subject: dict[str, Any] = {
        "kind": "pull_request" if pr_number else "repository_ref",
        "head_sha": head_sha,
        "head_branch": head_branch,
    }
    if pr_number:
        subject["number"] = pr_number

    supplied_cause = str(source.get("causal_fingerprint") or "").lower()
    authoritative = bool(SHA256.fullmatch(supplied_cause)) and str(
        source.get("cause_authority") or ""
    ) == "REPOSITORY_RECEIPT"
    surface_cause = digest(
        {
            "repository": repository,
            "gate": gate,
            "run_id": run_id,
            "head_sha": head_sha,
            "action": action,
            "status": source.get("status"),
            "conclusion": conclusion,
        }
    )
    cause_fingerprint = supplied_cause if authoritative else surface_cause
    cause_authority = "REPOSITORY_RECEIPT" if authoritative else "GITHUB_WORKFLOW_SURFACE"
    state = classify_gate(action, conclusion)
    event_id = str(source.get("event_id") or f"{repository}:{run_id}:{action or 'completed'}")

    event = {
        "schema": "qikvrt_horizon_gate_event_v2",
        "event_id": event_id,
        "source": "github.workflow_run",
        "framework": "KubiKAva",
        "development_model": "TESTED_EVENT_MODEL_DRIVEN_DEVELOPMENT",
        "node": node,
        "subject": subject,
        "gate": gate,
        "run_id": run_id,
        "head_sha": head_sha,
        "status": source.get("status"),
        "conclusion": conclusion,
        "state": state,
        "updated_at": source.get("updated_at"),
        "cause_authority": cause_authority,
        "causal_fingerprint": cause_fingerprint,
        "terminal": {
            "OBSERVE": "WORKFLOW_RUN_EVENT",
            "CLASSIFY": state,
            "D0": head_sha,
            "ACTION": "PROJECT_METATRANSISTOR_TRANSITION",
            "EFFECT": "TRANSPORT_ONLY",
            "READBACK": "REQUIRED",
            "SUCCESSOR": "EVENT_OR_STREAM_RECONNECT",
        },
        "claims": {
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "publication": False,
            "deployment": False,
            "empirical_confirmation": False,
        },
    }
    return event


def _gate_vector(gates: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    vector = []
    for name in EXPECTED_GATES:
        gate = dict(gates.get(name) or {})
        vector.append(
            {
                "name": name,
                "state": str(gate.get("state") or "NOT_OBSERVED"),
                "causal_fingerprint": str(gate.get("causal_fingerprint") or ""),
                "cause_authority": str(gate.get("cause_authority") or ""),
                "run_id": gate.get("run_id"),
            }
        )
    return vector


def classify_projection(
    *,
    head_sha: str,
    gates: Mapping[str, Mapping[str, Any]],
    previous: Mapping[str, Any] | None = None,
    active_writer: bool = False,
    successor_observed: bool = False,
    carrier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    head_sha = require_sha40(head_sha)
    previous = dict(previous or {})
    carrier = dict(carrier or {})
    vector = _gate_vector(gates)
    complete = all(item["state"] != "NOT_OBSERVED" for item in vector)
    all_hold = complete and all(item["state"] == "HOLD" for item in vector)
    vector_fingerprint = digest({"head_sha": head_sha, "gates": vector})
    hold_count = sum(item["state"] == "HOLD" for item in vector)
    # The carrier is depth position one; every held gate adds one tooth.
    # Eight held gates therefore bind the owner-defined dead-end depth nine.
    depth = min(MAX_COMPUTE_DEPTH, hold_count + 1) if hold_count else 0
    if active_writer or successor_observed:
        depth = 0

    authoritative_vector = complete and all(
        item["cause_authority"] == "REPOSITORY_RECEIPT"
        and bool(SHA256.fullmatch(item["causal_fingerprint"]))
        for item in vector
    )
    carrier_present = any(
        bool(carrier.get(key)) for key in ("pull_request_open", "issue_open", "branch_exists")
    )
    exact_carrier = bool(carrier.get("exact_head_current", False))
    protected = bool(carrier.get("protected", True))
    default_branch = bool(carrier.get("default_branch", True))
    cut_candidate = complete and all_hold and depth >= MAX_COMPUTE_DEPTH
    cut_eligible = (
        cut_candidate
        and authoritative_vector
        and carrier_present
        and exact_carrier
        and not protected
        and not default_branch
    )
    if cut_eligible:
        disposition = "CUT_ELIGIBLE"
    elif cut_candidate:
        disposition = "CUT_CANDIDATE_REQUIRES_EXACT_RECEIPT"
    elif all_hold:
        disposition = "CONTINUE_DEPTH_OBSERVATION"
    elif complete:
        disposition = "CONTINUE"
    else:
        disposition = "REOBSERVE_INCOMPLETE_VECTOR"

    prune_plan = {
        "executable": cut_eligible,
        "automatic": False,
        "ordered_actions": [
            "READBACK_EXACT_SUBJECT_AND_CARRIER",
            "PERSIST_CUT_RECEIPT",
            "CLOSE_PULL_REQUEST_NOT_PLANNED_IF_OPEN",
            "CLOSE_EXCLUSIVE_ISSUE_CARRIER_IF_OPEN",
            "DELETE_UNPROTECTED_NONDEFAULT_BRANCH_IF_HEAD_UNCHANGED",
            "READBACK_ALL_CARRIER_ABSENCE",
        ],
        "reason": "ALL_GATES_HOLD_AT_COMPUTE_DEPTH_9",
    }
    return {
        "schema": "qikvrt_metatransistor_projection_v1",
        "head_sha": head_sha,
        "gate_count": len(EXPECTED_GATES),
        "complete": complete,
        "all_hold": all_hold,
        "computation_depth": depth,
        "max_compute_depth": MAX_COMPUTE_DEPTH,
        "vector_fingerprint": vector_fingerprint,
        "authoritative_vector": authoritative_vector,
        "active_writer": active_writer,
        "successor_observed": successor_observed,
        "cut_candidate": cut_candidate,
        "cut_eligible": cut_eligible,
        "disposition": disposition,
        "prune_plan": prune_plan,
        "gates": vector,
        "claims": {
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "empirical_confirmation": False,
        },
    }


def build_terminal_frame(
    *,
    node_id: str,
    sequence: int,
    payload: Mapping[str, Any],
    previous_hash: str | None = None,
) -> dict[str, Any]:
    if sequence < 0:
        raise ValueError("sequence must be non-negative")
    if previous_hash is not None and not SHA256.fullmatch(previous_hash):
        raise ValueError("previous_hash must be 64 lowercase hex characters")
    frame = {
        "schema": "qikvrt_serialized_metatransistor_frame_v1",
        "node_id": node_id,
        "sequence": sequence,
        "previous_hash": previous_hash,
        "payload": dict(payload),
        "lossless": True,
        "predecessor_evidence_transfer": False,
    }
    frame["frame_hash"] = digest(frame)
    return frame


def verify_terminal_frame(frame: Mapping[str, Any]) -> bool:
    supplied = str(frame.get("frame_hash") or "")
    if not SHA256.fullmatch(supplied):
        return False
    body = dict(frame)
    body.pop("frame_hash", None)
    return digest(body) == supplied and body.get("lossless") is True


def _read_json(path: str | None) -> Any:
    if path:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def _event_from_args(args: argparse.Namespace) -> dict[str, Any]:
    source = {
        "repository": args.repository,
        "gate": args.gate,
        "run_id": args.run_id,
        "head_sha": args.head_sha,
        "head_branch": args.head_branch,
        "action": args.action,
        "status": args.status or None,
        "conclusion": args.conclusion or None,
        "updated_at": args.updated_at or None,
        "pr_number": args.pr_number or None,
        "event_id": args.event_id or None,
    }
    return normalize_event(source)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    event = sub.add_parser("event")
    event.add_argument("--repository", required=True)
    event.add_argument("--gate", required=True)
    event.add_argument("--run-id", required=True, type=int)
    event.add_argument("--head-sha", required=True)
    event.add_argument("--head-branch", default="")
    event.add_argument("--action", required=True)
    event.add_argument("--status", default="")
    event.add_argument("--conclusion", default="")
    event.add_argument("--updated-at", default="")
    event.add_argument("--pr-number", default="")
    event.add_argument("--event-id", default="")

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("--input")

    frame = sub.add_parser("frame")
    frame.add_argument("--input")
    frame.add_argument("--node-id", required=True)
    frame.add_argument("--sequence", required=True, type=int)
    frame.add_argument("--previous-hash")

    verify = sub.add_parser("verify-frame")
    verify.add_argument("--input")

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "event":
        result = _event_from_args(args)
    elif args.command == "aggregate":
        source = _read_json(args.input)
        result = classify_projection(
            head_sha=str(source["head_sha"]),
            gates=source.get("gates") or {},
            previous=source.get("previous") or {},
            active_writer=bool(source.get("active_writer", False)),
            successor_observed=bool(source.get("successor_observed", False)),
            carrier=source.get("carrier") or {},
        )
    elif args.command == "frame":
        result = build_terminal_frame(
            node_id=args.node_id,
            sequence=args.sequence,
            payload=_read_json(args.input),
            previous_hash=args.previous_hash,
        )
    else:
        frame_value = _read_json(args.input)
        result = {"valid": verify_terminal_frame(frame_value)}
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
