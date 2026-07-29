#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic QIK-VRT closure and anticipation materializer.

Stage 1 validates the global closure contract and its bounded functionality
evidence. Later stages extend this same executable with deterministic
anticipation projections and inert external-effect intent evaluation.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
ROOT_STRING = str(ROOT)
if ROOT_STRING not in sys.path:
    sys.path.insert(0, ROOT_STRING)

from tools.qikvrt_seed_common import (
    SeedError,
    canonical_json_bytes,
    read_json,
    write_json,
    write_text,
)
from src.qikvrt_effect_ack import EffectState, ResponsibilityProtocol


POLICY_PATH = Path("policy/GLOBAL_SYSTEM_CLOSURE_V1.json")
EVIDENCE_PATH = Path("system-closure/ARCHITECTURE_FUNCTIONALITY_EVIDENCE.json")
INPUT_PATH = Path("anticipation/INPUT.json")
CURRENT_PATH = Path("anticipation/current.json")
HISTORY_PATH = Path("anticipation/history.jsonl")
TRENDS_PATH = Path("anticipation/trends.json")
DERIVATIVES_PATH = Path("anticipation/derivatives.json")
NEXT_EFFECT_PATH = Path("anticipation/next-effect.json")
CHECKPOINT_1_PATH = Path("receipts/anticipation/0001-contract-bound.json")
CHECKPOINT_2_PATH = Path("receipts/anticipation/0002-anticipation-materialized.json")
TARGETED_ENVELOPE_PATH = Path(
    "anticipation/effects/TARGETED_EFFECT_ENVELOPE.json"
)
TARGETED_EVALUATION_PATH = Path(
    "anticipation/effects/TARGETED_EFFECT_EVALUATION.json"
)
ZENODO_QUEUE_PATH = Path(
    "release/system-closure-v1/ZENODO_PUBLICATION_QUEUE.json"
)
CHECKPOINT_3_PATH = Path("receipts/anticipation/0003-effect-intents-gated.json")
POLICY_SCHEMA = "qikvrt_global_system_closure_policy_v1"
EVIDENCE_SCHEMA = "qikvrt_architecture_functionality_evidence_v1"
INPUT_SCHEMA = "qikvrt_anticipation_input_v1"
STATE_SCHEMA = "qikvrt_anticipation_state_v1"
SCOPE_ID = "qikvrt-global-system-closure-v1"
ZERO_SHA256 = "0" * 64
PROJECTION_PATHS = (
    CURRENT_PATH,
    HISTORY_PATH,
    TRENDS_PATH,
    DERIVATIVES_PATH,
    NEXT_EFFECT_PATH,
    CHECKPOINT_1_PATH,
    CHECKPOINT_2_PATH,
    TARGETED_EVALUATION_PATH,
    CHECKPOINT_3_PATH,
)


class ClosureError(RuntimeError):
    """A contract or state violation that must fail closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def require_exact_keys(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ClosureError(f"{label} must contain exactly {sorted(keys)}")
    return value


def validate_policy(value: Mapping[str, Any]) -> None:
    require_exact_keys(
        value,
        {
            "_license",
            "schema",
            "scope_id",
            "version",
            "authority",
            "entrypoint",
            "canonical_chain",
            "persistence_stages",
            "monotonic_improvement",
            "effect_boundary",
            "recovery",
            "targeted_delivery",
            "zenodo",
            "completion_claims",
        },
        "closure policy",
    )
    if value["schema"] != POLICY_SCHEMA or value["scope_id"] != SCOPE_ID:
        raise ClosureError("closure policy identity mismatch")
    if value["entrypoint"] != "AI":
        raise ClosureError("closure entrypoint must remain AI")
    if value["canonical_chain"] != [
        "INTERACTION",
        "EVIDENCE",
        "WORK_UNIT",
        "CANDIDATE",
        "GATES",
        "EFFECT_ACK",
        "EFFECT",
        "RECEIPT",
        "OBSERVATION",
    ]:
        raise ClosureError("canonical chain drift")
    if value["effect_boundary"]["required_release_state"] != "EFFECT_ACK_DONE":
        raise ClosureError("EFFECT_ACK_DONE must remain the only release state")
    if value["effect_boundary"]["adaptive_runtime_may_issue_done"] is not False:
        raise ClosureError("adaptive runtime must not issue EFFECT_ACK_DONE")
    if value["zenodo"]["hard_gate"] != "NO_MACHINE_PROOF_NO_ZENODO_UPLOAD":
        raise ClosureError("Zenodo machine-proof gate drift")
    claims = value["completion_claims"]
    if claims != {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}:
        raise ClosureError("stage-1 policy contains a false completion claim")


def validate_functionality_evidence(value: Mapping[str, Any]) -> None:
    require_exact_keys(
        value,
        {
            "_license",
            "schema",
            "scope_id",
            "claim",
            "authority_evidence",
            "demonstrated_chain",
            "non_claims",
            "effect_state",
        },
        "functionality evidence",
    )
    if value["schema"] != EVIDENCE_SCHEMA or value["scope_id"] != SCOPE_ID:
        raise ClosureError("functionality evidence identity mismatch")
    claim = value["claim"]
    if claim["classification"] != "EMPIRICALLY_EVIDENCED":
        raise ClosureError("functionality evidence must remain empirical")
    if claim["status"] != "EVIDENCED":
        raise ClosureError("functionality evidence status drift")
    authority = value["authority_evidence"]
    if authority["repository"] != "Goldkelch/qik-vrt":
        raise ClosureError("functionality evidence repository drift")
    if authority["pull_request"] != 202 or authority["merged"] is not False:
        raise ClosureError("functionality evidence PR boundary drift")
    for key in ("base_sha", "head_sha", "tree_sha"):
        raw = authority[key]
        if not isinstance(raw, str) or len(raw) != 40:
            raise ClosureError(f"invalid {key}")
    workflows = authority["successful_exact_head_workflows"]
    if (
        authority["successful_exact_head_workflow_count"] != len(workflows)
        or len(set(workflows)) != len(workflows)
        or len(workflows) != 6
    ):
        raise ClosureError("exact-head workflow evidence is inconsistent")
    non_claims = set(value["non_claims"])
    required_non_claims = {
        "formal proof of the Denk-Mengenlehre thesis",
        "pull request merge",
        "Authority and Mirror equality",
        "Zenodo publication",
        "repository-wide PASS",
        "repository-wide FINAL_PASS",
        "repository-wide EFFECT_ACK_DONE",
    }
    if not required_non_claims.issubset(non_claims):
        raise ClosureError("functionality evidence overclaims its scope")
    if value["effect_state"] != "EFFECT_ACK_CONTINUE":
        raise ClosureError("functionality evidence must remain CONTINUE")


def classify_monotonic_transition(
    previous: Mapping[str, int], candidate: Mapping[str, int]
) -> str:
    """Classify a declared metric transition without inferring hidden quality."""
    if set(previous) != set(candidate) or not previous:
        raise ClosureError("metric sets must be equal and non-empty")
    if any(type(value) is not int for value in [*previous.values(), *candidate.values()]):
        raise ClosureError("metrics must be integers")
    if previous == candidate:
        return "BYTE_STABLE_NO_OP"
    if any(candidate[key] < previous[key] for key in previous):
        return "REJECTED_REGRESSION"
    if any(candidate[key] > previous[key] for key in previous):
        return "NON_REGRESSING_GATE_IMPROVEMENT"
    raise ClosureError("unclassifiable metric transition")


def checkpoint_hash(
    checkpoint: Mapping[str, Any], *, previous_checkpoint_sha256: str
) -> str:
    """Bind a checkpoint to its predecessor without hashing its own hash field."""
    if (
        not isinstance(previous_checkpoint_sha256, str)
        or len(previous_checkpoint_sha256) != 64
        or any(character not in "0123456789abcdef" for character in previous_checkpoint_sha256)
    ):
        raise ClosureError("previous checkpoint SHA-256 is invalid")
    payload = dict(checkpoint)
    payload.pop("checkpoint_sha256", None)
    payload["previous_checkpoint_sha256"] = previous_checkpoint_sha256
    return canonical_digest(payload)


def json_line(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def parse_utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ClosureError(f"{label} must be an RFC3339 UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ClosureError(f"{label} must be an RFC3339 UTC timestamp") from exc
    if parsed.tzinfo != dt.timezone.utc:
        raise ClosureError(f"{label} must be UTC")
    return parsed


def safe_relative_path(raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ClosureError(f"{label} must be a repository-relative path")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ClosureError(f"{label} is unsafe")
    return path


def bound_file(root: Path, raw_path: Any, label: str) -> tuple[Path, bytes]:
    relative = safe_relative_path(raw_path, label)
    path = root / relative
    current = path
    while current != root:
        if current.is_symlink():
            raise ClosureError(f"{label} traverses a symlink")
        current = current.parent
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ClosureError(f"{label} cannot be read: {exc}") from exc
    if not path.is_file():
        raise ClosureError(f"{label} is not a regular file")
    return relative, payload


def validate_input(value: Mapping[str, Any]) -> None:
    require_exact_keys(
        value,
        {
            "_license",
            "schema",
            "scope_id",
            "repository",
            "source_revision",
            "observed_at",
            "observations",
            "next_effect",
            "completion_claims",
        },
        "anticipation input",
    )
    if value["schema"] != INPUT_SCHEMA or value["scope_id"] != SCOPE_ID:
        raise ClosureError("anticipation input identity mismatch")
    if value["repository"] != "Goldkelch/qik-vrt":
        raise ClosureError("anticipation repository drift")
    source_revision = value["source_revision"]
    if (
        not isinstance(source_revision, str)
        or not source_revision.startswith("git-tree:")
        or len(source_revision) != 49
    ):
        raise ClosureError("anticipation source revision must bind one Git tree")
    observations = value["observations"]
    if not isinstance(observations, list) or len(observations) < 2:
        raise ClosureError("INSUFFICIENT_VERIFIED_OBSERVATIONS")
    state_ids: set[str] = set()
    previous_time = ""
    metric_keys: set[str] | None = None
    for index, observation in enumerate(observations):
        require_exact_keys(
            observation,
            {
                "state_id",
                "observed_at",
                "classification",
                "productive_chain_position",
                "metrics",
                "evidence",
            },
            f"observations[{index}]",
        )
        state_id = observation["state_id"]
        if not isinstance(state_id, str) or not state_id or state_id in state_ids:
            raise ClosureError("observation state IDs must be unique non-empty strings")
        state_ids.add(state_id)
        observed_at = observation["observed_at"]
        if not isinstance(observed_at, str) or not observed_at.endswith("Z"):
            raise ClosureError("observation timestamps must be RFC3339 UTC")
        if previous_time and observed_at < previous_time:
            raise ClosureError("observations must be ordered")
        previous_time = observed_at
        metrics = observation["metrics"]
        if (
            not isinstance(metrics, Mapping)
            or not metrics
            or any(type(item) is not int or item < 0 for item in metrics.values())
        ):
            raise ClosureError("observation metrics must be non-negative integers")
        keys = set(metrics)
        if metric_keys is None:
            metric_keys = keys
        elif keys != metric_keys:
            raise ClosureError("observation metric sets differ")
        evidence = observation["evidence"]
        if (
            not isinstance(evidence, list)
            or not evidence
            or any(not isinstance(item, str) or not item for item in evidence)
        ):
            raise ClosureError("every observation needs evidence")
    next_effect = value["next_effect"]
    require_exact_keys(
        next_effect,
        {
            "effect_id",
            "description",
            "executor_capability",
            "preconditions",
            "expected_receipt",
        },
        "next effect",
    )
    if not next_effect["effect_id"] or not next_effect["expected_receipt"]:
        raise ClosureError("NEXT_EFFECT_NOT_SELECTED")
    if value["completion_claims"] != {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
    }:
        raise ClosureError("anticipation input contains a false completion claim")


def load_targeted_envelope(root: Path = ROOT) -> dict[str, Any]:
    try:
        value = read_json(root / TARGETED_ENVELOPE_PATH, "targeted effect envelope")
    except SeedError as exc:
        raise ClosureError(str(exc)) from exc
    require_exact_keys(
        value,
        {
            "_license",
            "schema",
            "envelope_id",
            "effect_scope",
            "payload",
            "target",
            "timing",
            "authorization",
            "checkpoint",
            "dispatch",
            "non_claims",
        },
        "targeted effect envelope",
    )
    if value["schema"] != "qikvrt_targeted_effect_envelope_v1":
        raise ClosureError("targeted effect envelope schema drift")
    if (
        not isinstance(value["envelope_id"], str)
        or not value["envelope_id"]
        or len(value["envelope_id"]) > 128
    ):
        raise ClosureError("targeted effect envelope ID is invalid")
    require_exact_keys(
        value["payload"], {"path", "bytes", "sha256"}, "targeted payload"
    )
    require_exact_keys(
        value["target"],
        {
            "node_guid",
            "repository",
            "ref",
            "registry_path",
            "registry_entry_sha256",
            "registry_index_path",
            "registry_index_sha256",
            "registry_status_path",
            "registry_status_sha256",
        },
        "targeted node",
    )
    try:
        node_guid = str(uuid.UUID(value["target"]["node_guid"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ClosureError("target node GUID is invalid") from exc
    if node_guid != value["target"]["node_guid"]:
        raise ClosureError("target node GUID is not canonical")
    require_exact_keys(
        value["timing"],
        {"not_before_utc", "expires_utc", "evaluated_at_utc"},
        "target timing",
    )
    not_before = parse_utc(value["timing"]["not_before_utc"], "not_before_utc")
    expires = parse_utc(value["timing"]["expires_utc"], "expires_utc")
    parse_utc(value["timing"]["evaluated_at_utc"], "evaluated_at_utc")
    if not_before >= expires:
        raise ClosureError("target delivery time window is empty")
    require_exact_keys(
        value["authorization"],
        {
            "responsible_human",
            "origin_authenticated",
            "effect_ack_state",
            "effect_ack_protocol_path",
            "effect_ack_protocol_hash",
            "effect_ack_evaluated_at_utc",
        },
        "target authorization",
    )
    states = {state.value for state in EffectState}
    if value["authorization"]["effect_ack_state"] not in states:
        raise ClosureError("target authorization has an invalid EFFECT_ACK state")
    if type(value["authorization"]["origin_authenticated"]) is not bool:
        raise ClosureError("origin_authenticated must be boolean")
    protocol_hash = value["authorization"]["effect_ack_protocol_hash"]
    if protocol_hash is not None and (
        not isinstance(protocol_hash, str)
        or not protocol_hash.startswith("sha256:")
        or len(protocol_hash) != 71
        or any(character not in "0123456789abcdef" for character in protocol_hash[7:])
    ):
        raise ClosureError("effect ACK protocol hash is invalid")
    protocol_path = value["authorization"]["effect_ack_protocol_path"]
    if protocol_path is not None:
        safe_relative_path(protocol_path, "effect_ack_protocol_path")
    effect_evaluated = value["authorization"]["effect_ack_evaluated_at_utc"]
    if effect_evaluated is not None:
        parse_utc(effect_evaluated, "effect_ack_evaluated_at_utc")
    require_exact_keys(
        value["checkpoint"],
        {"previous_checkpoint_path", "previous_checkpoint_sha256"},
        "target checkpoint",
    )
    if value["checkpoint"]["previous_checkpoint_path"] != CHECKPOINT_2_PATH.as_posix():
        raise ClosureError("target envelope predecessor path drift")
    require_exact_keys(
        value["dispatch"],
        {"state", "attempted", "transport_ack", "effect_receipt"},
        "target dispatch",
    )
    if value["dispatch"] != {
        "state": "NOT_DISPATCHED",
        "attempted": False,
        "transport_ack": False,
        "effect_receipt": None,
    }:
        raise ClosureError("tracked targeted envelope must remain inert")
    if (
        not isinstance(value["non_claims"], list)
        or "transport acknowledgement is effect acknowledgement"
        not in value["non_claims"]
        or "delivery was completed" not in value["non_claims"]
    ):
        raise ClosureError("target envelope non-claims are incomplete")
    return value


def targeted_effect_subject(envelope: Mapping[str, Any]) -> bytes:
    """Canonical bytes that make an EFFECT_ACK decision target/time specific."""
    return canonical_json_bytes(
        {
            "schema": "qikvrt_targeted_effect_subject_v1",
            "envelope_id": envelope["envelope_id"],
            "effect_scope": envelope["effect_scope"],
            "payload": envelope["payload"],
            "target": envelope["target"],
            "timing": {
                "not_before_utc": envelope["timing"]["not_before_utc"],
                "expires_utc": envelope["timing"]["expires_utc"],
                "evaluated_at_utc": envelope["timing"]["evaluated_at_utc"],
            },
            "checkpoint": envelope["checkpoint"],
        }
    )


def evaluate_targeted_envelope(
    envelope: Mapping[str, Any], root: Path = ROOT
) -> dict[str, Any]:
    """Evaluate one signed-outer-envelope candidate without network or dispatch."""
    target = envelope["target"]
    payload = envelope["payload"]
    timing = envelope["timing"]
    authorization = envelope["authorization"]
    failures: list[str] = []
    checks: dict[str, bool] = {}

    _payload_path, payload_bytes = bound_file(root, payload["path"], "payload.path")
    checks["payload_bytes_exact"] = (
        type(payload["bytes"]) is int
        and payload["bytes"] == len(payload_bytes)
        and payload["sha256"] == sha256_bytes(payload_bytes)
    )
    if not checks["payload_bytes_exact"]:
        failures.append("PAYLOAD_HASH_OR_SIZE_MISMATCH")

    registry_bindings = (
        ("registry_path", "registry_entry_sha256"),
        ("registry_index_path", "registry_index_sha256"),
        ("registry_status_path", "registry_status_sha256"),
    )
    registry_values: dict[str, dict[str, Any]] = {}
    for path_key, hash_key in registry_bindings:
        relative, raw = bound_file(root, target[path_key], f"target.{path_key}")
        exact = target[hash_key] == sha256_bytes(raw)
        checks[f"{path_key}_exact"] = exact
        if not exact:
            failures.append(f"{path_key.upper()}_DIGEST_MISMATCH")
        try:
            registry_values[path_key] = read_json(
                root / relative, f"target.{path_key}"
            )
        except SeedError as exc:
            raise ClosureError(str(exc)) from exc

    index_matches = [
        node
        for node in registry_values["registry_index_path"].get("nodes", [])
        if node.get("guid") == target["node_guid"]
    ]
    status_matches = [
        node
        for node in registry_values["registry_status_path"].get("nodes", [])
        if node.get("guid") == target["node_guid"]
    ]
    checks["exactly_one_index_match"] = len(index_matches) == 1
    checks["exactly_one_status_match"] = len(status_matches) == 1
    if not checks["exactly_one_index_match"] or not checks["exactly_one_status_match"]:
        failures.append("TARGET_NODE_NOT_UNIQUE")

    node_entry = registry_values["registry_path"]
    checks["registry_entry_identity_exact"] = (
        node_entry.get("guid") == target["node_guid"]
        and node_entry.get("repository") == target["repository"]
        and node_entry.get("node_branch") == target["ref"]
    )
    if not checks["registry_entry_identity_exact"]:
        failures.append("TARGET_REGISTRY_ENTRY_MISMATCH")

    index_node = index_matches[0] if len(index_matches) == 1 else {}
    checks["index_identity_exact"] = (
        index_node.get("repository") == target["repository"]
        and index_node.get("node_branch") == target["ref"]
        and index_node.get("registry_path") == target["registry_path"]
    )
    checks["target_active"] = (
        index_node.get("registry_status") == "ACCEPTED"
        and index_node.get("policy_status") == "ACTIVE"
        and index_node.get("effective_status") == "ACTIVE"
    )
    if not checks["index_identity_exact"]:
        failures.append("TARGET_INDEX_IDENTITY_MISMATCH")
    if not checks["target_active"]:
        failures.append("TARGET_NODE_NOT_ACTIVE")

    evaluated_at = parse_utc(timing["evaluated_at_utc"], "evaluated_at_utc")
    not_before = parse_utc(timing["not_before_utc"], "not_before_utc")
    expires = parse_utc(timing["expires_utc"], "expires_utc")
    status_node = status_matches[0] if len(status_matches) == 1 else {}
    try:
        heartbeat_expires = parse_utc(
            status_node.get("expires_utc"), "target heartbeat expires_utc"
        )
    except ClosureError:
        heartbeat_expires = dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    checks["target_fresh"] = (
        status_node.get("heartbeat_status") == "FRESH"
        and heartbeat_expires > evaluated_at
    )
    if not checks["target_fresh"]:
        failures.append("TARGET_NODE_NOT_FRESH")
    checks["not_before_reached"] = evaluated_at >= not_before
    checks["not_expired"] = evaluated_at < expires
    if not checks["not_expired"]:
        failures.append("DELIVERY_WINDOW_EXPIRED")

    checkpoint = read_json(root / CHECKPOINT_2_PATH, "checkpoint 2")
    checks["checkpoint_exact"] = (
        envelope["checkpoint"]["previous_checkpoint_sha256"]
        == checkpoint.get("checkpoint_sha256")
    )
    if not checks["checkpoint_exact"]:
        failures.append("PREVIOUS_CHECKPOINT_MISMATCH")

    checks["responsible_human_named"] = (
        authorization["responsible_human"] == "Ingolf Lohmann"
    )
    checks["origin_authenticated"] = authorization["origin_authenticated"] is True
    checks["effect_ack_protocol_verified"] = False
    protocol_path = authorization["effect_ack_protocol_path"]
    if protocol_path is not None:
        try:
            protocol_value = read_json(
                root / safe_relative_path(protocol_path, "effect_ack_protocol_path"),
                "effect ACK protocol",
            )
            protocol = ResponsibilityProtocol.from_dict(protocol_value)
        except (SeedError, ValueError, TypeError, KeyError) as exc:
            failures.append("EFFECT_ACK_PROTOCOL_INVALID")
        else:
            subject = targeted_effect_subject(envelope)
            checks["effect_ack_protocol_verified"] = (
                protocol.state is EffectState.EFFECT_ACK_DONE
                and protocol.protocol_hash
                == authorization["effect_ack_protocol_hash"]
                and protocol.input_id == envelope["envelope_id"]
                and protocol.input_hash == "sha256:" + sha256_bytes(subject)
                and protocol.responsibility_owner
                == authorization["responsible_human"]
                and protocol.created_utc
                == authorization["effect_ack_evaluated_at_utc"]
                == envelope["timing"]["evaluated_at_utc"]
            )
            if not checks["effect_ack_protocol_verified"]:
                failures.append("EFFECT_ACK_PROTOCOL_BINDING_MISMATCH")
    checks["effect_ack_done"] = (
        authorization["effect_ack_state"] == EffectState.EFFECT_ACK_DONE.value
        and checks["effect_ack_protocol_verified"]
    )
    if (
        authorization["effect_ack_state"] == EffectState.EFFECT_ACK_DONE.value
        and not checks["effect_ack_protocol_verified"]
    ):
        failures.append("FALSE_EFFECT_ACK_DONE")
    integrity_failure = any(
        failure.endswith("MISMATCH")
        or failure in {
            "TARGET_NODE_NOT_UNIQUE",
            "TARGET_NODE_NOT_ACTIVE",
            "TARGET_NODE_NOT_FRESH",
            "DELIVERY_WINDOW_EXPIRED",
            "EFFECT_ACK_PROTOCOL_INVALID",
            "FALSE_EFFECT_ACK_DONE",
        }
        for failure in failures
    )
    if integrity_failure:
        state = "BLOCK"
    elif not checks["not_before_reached"]:
        state = "CONTINUE_NOT_YET_DUE"
    elif not (
        checks["responsible_human_named"]
        and checks["origin_authenticated"]
        and checks["effect_ack_done"]
    ):
        state = "CONTINUE_AWAITING_FRESH_EFFECT_ACK"
    else:
        state = "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_DISPATCH"
    eligible = state == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_DISPATCH"
    return {
        "schema": "qikvrt_targeted_effect_evaluation_v1",
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": canonical_digest(envelope),
        "evaluated_at_utc": timing["evaluated_at_utc"],
        "state": state,
        "checks": checks,
        "failure_classes": sorted(set(failures)),
        "dispatch_eligible": eligible,
        "dispatch_attempted": False,
        "transport_ack_is_effect_ack": False,
        "effect_state": authorization["effect_ack_state"],
        "next_effect": (
            "REVALIDATE_TARGET_NODE_AND_REEVALUATE_EFFECT_ACK"
            if not eligible
            else "HAND_TO_SEPARATELY_AUTHORIZED_IDEMPOTENT_EXECUTOR"
        ),
    }


def load_zenodo_queue(root: Path = ROOT) -> dict[str, Any]:
    try:
        value = read_json(root / ZENODO_QUEUE_PATH, "Zenodo publication queue")
    except SeedError as exc:
        raise ClosureError(str(exc)) from exc
    require_exact_keys(
        value,
        {
            "_license",
            "schema",
            "scope_id",
            "source_revision",
            "candidate_id",
            "state",
            "publication_intent_recorded",
            "exact_candidate_upload_authorization",
            "candidate",
            "proof",
            "gates",
            "network_effect",
            "hard_gate",
            "next_effect",
            "completion_claims",
        },
        "Zenodo publication queue",
    )
    if (
        value["schema"] != "qikvrt_zenodo_publication_queue_v1"
        or value["scope_id"] != SCOPE_ID
        or value["state"] != "BLOCKED_AWAITING_MACHINE_PROOF"
    ):
        raise ClosureError("Zenodo queue identity or state drift")
    if value["hard_gate"] != "NO_MACHINE_PROOF_NO_ZENODO_UPLOAD":
        raise ClosureError("Zenodo queue hard gate drift")
    if value["exact_candidate_upload_authorization"] is not False:
        raise ClosureError("Zenodo queue must not pre-authorize an upload")
    if value["candidate"] != {
        "frozen": False,
        "files": [],
        "primary_document_path": None,
    }:
        raise ClosureError("Zenodo queue has an unfrozen or ambiguous candidate")
    if any(value["gates"].values()):
        raise ClosureError("Zenodo queue contains a premature satisfied gate")
    if any(value["network_effect"].values()):
        raise ClosureError("Zenodo queue contains a false network effect")
    if any(value["completion_claims"].values()):
        raise ClosureError("Zenodo queue contains a false completion claim")
    proof = value["proof"]
    for key in ("lean_toolchain", "lakefile"):
        path = safe_relative_path(proof[key], f"proof.{key}")
        if not (root / path).is_file():
            raise ClosureError(f"declared Lean/Lake source is missing: {path}")
    for path_key, present_key in (
        ("kernel_receipt_path", "kernel_receipt_present"),
        ("machine_proof_bundle_path", "machine_proof_bundle_present"),
    ):
        path = safe_relative_path(proof[path_key], f"proof.{path_key}")
        actual = (root / path).is_file()
        if proof[present_key] is not actual:
            raise ClosureError(f"Zenodo queue presence drift: {path}")
    return value


def evaluate_zenodo_queue(value: Mapping[str, Any]) -> dict[str, Any]:
    missing_gates = sorted(key for key, passed in value["gates"].items() if not passed)
    return {
        "schema": "qikvrt_zenodo_queue_evaluation_v1",
        "candidate_id": value["candidate_id"],
        "state": "BLOCKED_AWAITING_MACHINE_PROOF",
        "hard_gate": value["hard_gate"],
        "missing_gates": missing_gates,
        "network_mutation_allowed": False,
        "network_mutation_attempted": False,
        "next_effect": value["next_effect"],
    }


def observation_projection(observation: Mapping[str, Any]) -> dict[str, Any]:
    digest_basis = {
        "state_id": observation["state_id"],
        "observed_at": observation["observed_at"],
        "classification": observation["classification"],
        "productive_chain_position": observation["productive_chain_position"],
        "metrics": observation["metrics"],
        "evidence": observation["evidence"],
    }
    return {
        **digest_basis,
        "state_digest": canonical_digest(digest_basis),
    }


def derive_trend(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(observations) < 2:
        raise ClosureError("INSUFFICIENT_VERIFIED_OBSERVATIONS")
    transition_classes = [
        classify_monotonic_transition(
            observations[index - 1]["metrics"], observations[index]["metrics"]
        )
        for index in range(1, len(observations))
    ]
    if "REJECTED_REGRESSION" in transition_classes:
        direction = "REGRESSING"
        productive_progress = False
    elif "NON_REGRESSING_GATE_IMPROVEMENT" in transition_classes:
        direction = "ADVANCING"
        productive_progress = True
    else:
        direction = "STABLE"
        productive_progress = False
    return {
        "direction": direction,
        "basis": transition_classes,
        "productive_progress": productive_progress,
    }


def derive_derivatives(
    observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if len(observations) < 2:
        raise ClosureError("INSUFFICIENT_VERIFIED_OBSERVATIONS")
    previous = observations[-2]["metrics"]
    current = observations[-1]["metrics"]
    return [
        {
            "order": 1,
            "name": key,
            "value": current[key] - previous[key],
            "interpretation": "latest verified discrete metric difference",
        }
        for key in sorted(previous)
    ]


def default_planner(input_value: Mapping[str, Any]) -> dict[str, Any]:
    return dict(input_value["next_effect"])


def build_projections(
    policy: Mapping[str, Any],
    evidence: Mapping[str, Any],
    input_value: Mapping[str, Any],
    *,
    planner: Callable[[Mapping[str, Any]], dict[str, Any]] = default_planner,
) -> dict[Path, bytes]:
    validate_policy(policy)
    validate_functionality_evidence(evidence)
    validate_input(input_value)
    observations = [
        observation_projection(item) for item in input_value["observations"]
    ]
    trend = derive_trend(input_value["observations"])
    derivatives = derive_derivatives(input_value["observations"])
    next_effect = planner(input_value)
    if next_effect != input_value["next_effect"]:
        raise ClosureError("TREND_DERIVATION_NONDETERMINISTIC")
    basis = {
        "policy_sha256": canonical_digest(policy),
        "functionality_evidence_sha256": canonical_digest(evidence),
        "input_sha256": canonical_digest(input_value),
        "source_revision": input_value["source_revision"],
    }
    provenance_digest = canonical_digest(basis)
    current = {
        "schema_version": STATE_SCHEMA,
        "observation_id": "gsc-anticipation-0002",
        "repository": input_value["repository"],
        "observed_at": input_value["observed_at"],
        "current_state": {
            "state_id": observations[-1]["state_id"],
            "classification": observations[-1]["classification"],
            "productive_chain_position": observations[-1][
                "productive_chain_position"
            ],
            "scope_id": SCOPE_ID,
            "effect_state": "EFFECT_ACK_CONTINUE",
        },
        "state_history": [
            {
                "state_id": item["state_id"],
                "observed_at": item["observed_at"],
                "state_digest": item["state_digest"],
            }
            for item in observations
        ],
        "trend": trend,
        "derivatives": derivatives,
        "anticipated_state": {
            "state_id": "global-system-closure-effect-intents-gated",
            "derivation_rule": "earliest safe incomplete persistence stage",
            "deterministic": True,
        },
        "next_effect": next_effect,
        "execution": {
            "status": "PENDING",
            "automatically_dispatched": False,
            "failure_class": None,
        },
        "evidence": [
            str(POLICY_PATH),
            str(EVIDENCE_PATH),
            str(INPUT_PATH),
        ],
        "provenance": {
            "source_revision": input_value["source_revision"],
            "sha256": provenance_digest,
        },
    }
    trends = {
        "schema": "qikvrt_anticipation_trends_v1",
        "scope_id": SCOPE_ID,
        "source_revision": input_value["source_revision"],
        "trend": trend,
        "observation_count": len(observations),
    }
    derivative_projection = {
        "schema": "qikvrt_anticipation_derivatives_v1",
        "scope_id": SCOPE_ID,
        "source_revision": input_value["source_revision"],
        "derivatives": derivatives,
    }
    next_effect_projection = {
        "schema": "qikvrt_anticipation_next_effect_v1",
        "scope_id": SCOPE_ID,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "next_effect": next_effect,
        "dispatch_authorized": False,
        "completion_claims": input_value["completion_claims"],
    }
    history_bytes = (
        "\n".join(json_line(item) for item in observations) + "\n"
    ).encode("utf-8")
    primary_outputs = {
        CURRENT_PATH: canonical_json_bytes(current),
        HISTORY_PATH: history_bytes,
        TRENDS_PATH: canonical_json_bytes(trends),
        DERIVATIVES_PATH: canonical_json_bytes(derivative_projection),
        NEXT_EFFECT_PATH: canonical_json_bytes(next_effect_projection),
    }
    checkpoint_1 = {
        "schema": "qikvrt_closure_checkpoint_v1",
        "scope_id": SCOPE_ID,
        "checkpoint_id": "gsc-0001-contract-bound",
        "stage": "CONTRACT_BOUND",
        "observed_at": input_value["observed_at"],
        "source_revision": input_value["source_revision"],
        "previous_checkpoint_sha256": ZERO_SHA256,
        "bindings": basis,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "external_effect": "NONE",
        "completion_claims": input_value["completion_claims"],
    }
    checkpoint_1["checkpoint_sha256"] = checkpoint_hash(
        checkpoint_1, previous_checkpoint_sha256=ZERO_SHA256
    )
    output_bindings = {
        path.as_posix(): {
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
        }
        for path, raw in primary_outputs.items()
    }
    checkpoint_2 = {
        "schema": "qikvrt_closure_checkpoint_v1",
        "scope_id": SCOPE_ID,
        "checkpoint_id": "gsc-0002-anticipation-materialized",
        "stage": "ANTICIPATION_MATERIALIZED",
        "observed_at": input_value["observed_at"],
        "source_revision": input_value["source_revision"],
        "previous_checkpoint_sha256": checkpoint_1["checkpoint_sha256"],
        "bindings": output_bindings,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "external_effect": "NONE",
        "completion_claims": input_value["completion_claims"],
    }
    checkpoint_2["checkpoint_sha256"] = checkpoint_hash(
        checkpoint_2,
        previous_checkpoint_sha256=checkpoint_1["checkpoint_sha256"],
    )
    return {
        **primary_outputs,
        CHECKPOINT_1_PATH: canonical_json_bytes(checkpoint_1),
        CHECKPOINT_2_PATH: canonical_json_bytes(checkpoint_2),
    }


def build_stage3_outputs(
    base_outputs: Mapping[Path, bytes],
    input_value: Mapping[str, Any],
    envelope: Mapping[str, Any],
    targeted_evaluation: Mapping[str, Any],
    zenodo_queue: Mapping[str, Any],
    zenodo_evaluation: Mapping[str, Any],
    root: Path = ROOT,
) -> dict[Path, bytes]:
    current = json.loads(base_outputs[CURRENT_PATH])
    stage3_observation_input = {
        "state_id": "global-system-closure-effect-intents-gated",
        "observed_at": envelope["timing"]["evaluated_at_utc"],
        "classification": "TEILFORTSCHRITT",
        "productive_chain_position": "EFFECT_INTENTS_GATED",
        "metrics": {
            "bound_artifact_groups": 7,
            "verified_gate_groups": 8,
        },
        "evidence": [
            TARGETED_ENVELOPE_PATH.as_posix(),
            TARGETED_EVALUATION_PATH.as_posix(),
            ZENODO_QUEUE_PATH.as_posix(),
            "schemas/qikvrt-targeted-effect-envelope.schema.json",
            zenodo_queue["source_revision"],
        ],
    }
    all_observation_inputs = [
        *copy.deepcopy(input_value["observations"]),
        stage3_observation_input,
    ]
    stage3_observation = observation_projection(stage3_observation_input)
    trend = derive_trend(all_observation_inputs)
    derivatives = derive_derivatives(all_observation_inputs)
    next_effect = {
        "effect_id": "REVALIDATE_TARGET_AND_BUILD_MACHINE_PROOF",
        "description": (
            "Revalidate the exact target node and build the candidate-specific "
            "claim inventory and Lean/Lake proof plan; perform no external effect."
        ),
        "executor_capability": "qikvrt.repository.anticipation.v1",
        "preconditions": [
            "TARGET_NODE_ACTIVE_AND_FRESH",
            "EXACT_CANDIDATE_FROZEN",
            "COMPLETE_CLAIM_INVENTORY",
            "LEAN_LAKE_KERNEL_RECEIPTS_WHERE_APPLICABLE",
            "FRESH_EFFECT_SPECIFIC_EFFECT_ACK_DONE_BEFORE_ANY_DISPATCH",
        ],
        "expected_receipt": "receipts/anticipation/0004-candidate-verified.json",
    }
    current["schema_version"] = STATE_SCHEMA
    current["observation_id"] = "gsc-anticipation-0003"
    current["observed_at"] = stage3_observation["observed_at"]
    current["current_state"] = {
        "state_id": stage3_observation["state_id"],
        "classification": stage3_observation["classification"],
        "productive_chain_position": stage3_observation[
            "productive_chain_position"
        ],
        "scope_id": SCOPE_ID,
        "effect_state": "EFFECT_ACK_CONTINUE",
    }
    current["state_history"].append(
        {
            "state_id": stage3_observation["state_id"],
            "observed_at": stage3_observation["observed_at"],
            "state_digest": stage3_observation["state_digest"],
        }
    )
    current["trend"] = trend
    current["derivatives"] = derivatives
    current["anticipated_state"] = {
        "state_id": "global-system-closure-candidate-verified",
        "derivation_rule": "earliest safe incomplete persistence stage",
        "deterministic": True,
    }
    current["next_effect"] = next_effect
    combined_failures = sorted(
        {
            *targeted_evaluation["failure_classes"],
            *zenodo_evaluation["missing_gates"],
        }
    )
    current["execution"] = {
        "status": "BLOCKED",
        "automatically_dispatched": False,
        "failure_class": ",".join(combined_failures),
    }
    current["evidence"] = [
        POLICY_PATH.as_posix(),
        EVIDENCE_PATH.as_posix(),
        INPUT_PATH.as_posix(),
        TARGETED_ENVELOPE_PATH.as_posix(),
        TARGETED_EVALUATION_PATH.as_posix(),
        ZENODO_QUEUE_PATH.as_posix(),
    ]
    stage3_basis = {
        "stage2_source_revision": input_value["source_revision"],
        "stage3_source_revision": zenodo_queue["source_revision"],
        "targeted_envelope_sha256": canonical_digest(envelope),
        "targeted_evaluation_sha256": canonical_digest(targeted_evaluation),
        "zenodo_queue_sha256": canonical_digest(zenodo_queue),
        "zenodo_evaluation_sha256": canonical_digest(zenodo_evaluation),
    }
    current["provenance"] = {
        "source_revision": zenodo_queue["source_revision"],
        "sha256": canonical_digest(stage3_basis),
    }
    trends = {
        "schema": "qikvrt_anticipation_trends_v1",
        "scope_id": SCOPE_ID,
        "source_revision": zenodo_queue["source_revision"],
        "trend": trend,
        "observation_count": len(all_observation_inputs),
    }
    derivative_projection = {
        "schema": "qikvrt_anticipation_derivatives_v1",
        "scope_id": SCOPE_ID,
        "source_revision": zenodo_queue["source_revision"],
        "derivatives": derivatives,
    }
    next_effect_projection = {
        "schema": "qikvrt_anticipation_next_effect_v1",
        "scope_id": SCOPE_ID,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "next_effect": next_effect,
        "dispatch_authorized": False,
        "targeted_delivery_state": targeted_evaluation["state"],
        "zenodo_queue_state": zenodo_evaluation["state"],
        "completion_claims": input_value["completion_claims"],
    }
    history_records = [
        observation_projection(item) for item in all_observation_inputs
    ]
    final_primary = {
        CURRENT_PATH: canonical_json_bytes(current),
        HISTORY_PATH: (
            "\n".join(json_line(item) for item in history_records) + "\n"
        ).encode("utf-8"),
        TRENDS_PATH: canonical_json_bytes(trends),
        DERIVATIVES_PATH: canonical_json_bytes(derivative_projection),
        NEXT_EFFECT_PATH: canonical_json_bytes(next_effect_projection),
        TARGETED_EVALUATION_PATH: canonical_json_bytes(targeted_evaluation),
    }
    checkpoint_2 = json.loads(base_outputs[CHECKPOINT_2_PATH])
    additional_bindings: dict[str, dict[str, Any]] = {}
    for relative in (
        TARGETED_ENVELOPE_PATH,
        ZENODO_QUEUE_PATH,
        Path("schemas/qikvrt-targeted-effect-envelope.schema.json"),
    ):
        _path, raw = bound_file(root, relative.as_posix(), relative.as_posix())
        additional_bindings[relative.as_posix()] = {
            "bytes": len(raw),
            "sha256": sha256_bytes(raw),
        }
    output_bindings = {
        path.as_posix(): {"bytes": len(raw), "sha256": sha256_bytes(raw)}
        for path, raw in final_primary.items()
    }
    checkpoint_3 = {
        "schema": "qikvrt_closure_checkpoint_v1",
        "scope_id": SCOPE_ID,
        "checkpoint_id": "gsc-0003-effect-intents-gated",
        "stage": "EFFECT_INTENTS_GATED",
        "observed_at": envelope["timing"]["evaluated_at_utc"],
        "source_revision": zenodo_queue["source_revision"],
        "previous_checkpoint_sha256": checkpoint_2["checkpoint_sha256"],
        "bindings": {**output_bindings, **additional_bindings},
        "effect_state": "EFFECT_ACK_CONTINUE",
        "external_effect": "NONE_INTENTS_ONLY",
        "recovery": (
            "No remote effect exists to roll back. After any future attempted "
            "remote effect, observe and use idempotent replay or forward repair."
        ),
        "completion_claims": input_value["completion_claims"],
    }
    checkpoint_3["checkpoint_sha256"] = checkpoint_hash(
        checkpoint_3,
        previous_checkpoint_sha256=checkpoint_2["checkpoint_sha256"],
    )
    return {
        **final_primary,
        CHECKPOINT_1_PATH: base_outputs[CHECKPOINT_1_PATH],
        CHECKPOINT_2_PATH: base_outputs[CHECKPOINT_2_PATH],
        CHECKPOINT_3_PATH: canonical_json_bytes(checkpoint_3),
    }


def load_anticipation_input(root: Path = ROOT) -> dict[str, Any]:
    try:
        value = read_json(root / INPUT_PATH, "anticipation input")
    except SeedError as exc:
        raise ClosureError(str(exc)) from exc
    validate_input(value)
    return value


def expected_projections(root: Path = ROOT) -> dict[Path, bytes]:
    policy, evidence = load_contract(root)
    input_value = load_anticipation_input(root)
    base_outputs = build_projections(policy, evidence, input_value)
    envelope = load_targeted_envelope(root)
    targeted_evaluation = evaluate_targeted_envelope(envelope, root)
    zenodo_queue = load_zenodo_queue(root)
    zenodo_evaluation = evaluate_zenodo_queue(zenodo_queue)
    return build_stage3_outputs(
        base_outputs,
        input_value,
        envelope,
        targeted_evaluation,
        zenodo_queue,
        zenodo_evaluation,
        root,
    )


def materialize(root: Path = ROOT) -> dict[str, Any]:
    outputs = expected_projections(root)
    for relative, raw in outputs.items():
        if relative == HISTORY_PATH:
            write_text(root / relative, raw.decode("utf-8"))
        else:
            value = json.loads(raw)
            write_json(root / relative, value)
    return {
        "schema": "qikvrt_anticipation_materialization_receipt_v1",
        "state": "MATERIALIZED",
        "paths": [path.as_posix() for path in outputs],
        "output_count": len(outputs),
        "effect_state": "EFFECT_ACK_CONTINUE",
        "external_effect": "NONE",
    }


def verify_projections(root: Path = ROOT) -> dict[str, str]:
    outputs = expected_projections(root)
    verified: dict[str, str] = {}
    for relative, expected in outputs.items():
        path = root / relative
        try:
            actual = path.read_bytes()
        except OSError as exc:
            raise ClosureError(f"missing projection {relative}: {exc}") from exc
        if actual != expected:
            raise ClosureError(f"projection drift: {relative}")
        verified[relative.as_posix()] = sha256_bytes(actual)
    return verified


def load_contract(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        policy = read_json(root / POLICY_PATH, "closure policy")
        evidence = read_json(root / EVIDENCE_PATH, "functionality evidence")
    except SeedError as exc:
        raise ClosureError(str(exc)) from exc
    validate_policy(policy)
    validate_functionality_evidence(evidence)
    return policy, evidence


def check(root: Path = ROOT) -> dict[str, Any]:
    policy, evidence = load_contract(root)
    verified = verify_projections(root)
    return {
        "schema": "qikvrt_global_system_closure_check_v1",
        "scope_id": SCOPE_ID,
        "state": "CONTINUE",
        "effect_state": "EFFECT_ACK_CONTINUE",
        "policy_sha256": canonical_digest(policy),
        "functionality_evidence_sha256": canonical_digest(evidence),
        "verified_projection_count": len(verified),
        "latest_checkpoint_sha256": json.loads(
            (root / CHECKPOINT_3_PATH).read_text(encoding="utf-8")
        )["checkpoint_sha256"],
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("check", "materialize"),
        help="materialize or validate deterministic closure projections",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "materialize":
            result = materialize()
        else:
            result = check()
    except (ClosureError, SeedError, OSError, ValueError) as exc:
        print(f"BLOCK: {exc}")
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
