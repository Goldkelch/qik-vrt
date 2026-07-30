#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed evaluator for an inert target/time/payload outer envelope.

The evaluator performs repository-local validation only. It never dispatches,
writes a receipt, contacts a target, or converts eligibility into authority.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
ROOT_STRING = str(ROOT)
if ROOT_STRING not in sys.path:
    sys.path.insert(0, ROOT_STRING)

from src.qikvrt_effect_ack import (  # noqa: E402
    EffectState,
    ResponsibilityProtocol,
    verify_protocol,
)
from tools.qikvrt_anticipation import (  # noqa: E402
    ClosureError,
    canonical_digest,
    checkpoint_hash,
    is_sha256,
    read_bound_file,
    require_exact_keys,
    safe_relative_path,
    sha256_bytes,
)
from tools.qikvrt_seed_common import (  # noqa: E402
    SeedError,
    canonical_json_bytes,
    read_json,
)


ENVELOPE_SCHEMA = "qikvrt_targeted_effect_envelope_v1"
EVALUATION_SCHEMA = "qikvrt_targeted_effect_evaluation_v1"
ENVELOPE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{7,127}$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REQUIRED_NON_CLAIMS = {
    "transport acknowledgement is effect acknowledgement",
    "delivery was completed",
}


class TargetedEffectError(ClosureError):
    """A targeted-envelope violation that must fail closed."""


def parse_utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise TargetedEffectError(f"{label} must be an RFC3339 UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TargetedEffectError(
            f"{label} must be an RFC3339 UTC timestamp"
        ) from exc
    if parsed.tzinfo != dt.timezone.utc:
        raise TargetedEffectError(f"{label} must be UTC")
    return parsed


def validate_envelope(value: Mapping[str, Any]) -> None:
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
    if value["schema"] != ENVELOPE_SCHEMA:
        raise TargetedEffectError("targeted effect envelope schema drift")
    if not isinstance(value["envelope_id"], str) or not ENVELOPE_ID_RE.fullmatch(
        value["envelope_id"]
    ):
        raise TargetedEffectError("targeted effect envelope ID is invalid")
    if (
        not isinstance(value["effect_scope"], str)
        or not value["effect_scope"].strip()
        or len(value["effect_scope"]) > 256
    ):
        raise TargetedEffectError("targeted effect scope is invalid")

    payload = require_exact_keys(
        value["payload"], {"path", "bytes", "sha256"}, "targeted payload"
    )
    safe_relative_path(payload["path"], "payload.path")
    if type(payload["bytes"]) is not int or payload["bytes"] < 1:
        raise TargetedEffectError("payload byte count is invalid")
    if not is_sha256(payload["sha256"]):
        raise TargetedEffectError("payload SHA-256 is invalid")

    target = require_exact_keys(
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
        node_guid = str(uuid.UUID(target["node_guid"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise TargetedEffectError("target node GUID is invalid") from exc
    if node_guid != target["node_guid"]:
        raise TargetedEffectError("target node GUID is not canonical")
    if not isinstance(target["repository"], str) or not REPOSITORY_RE.fullmatch(
        target["repository"]
    ):
        raise TargetedEffectError("target repository is invalid")
    if (
        not isinstance(target["ref"], str)
        or not target["ref"].strip()
        or len(target["ref"]) > 256
    ):
        raise TargetedEffectError("target ref is invalid")
    for path_key, hash_key in (
        ("registry_path", "registry_entry_sha256"),
        ("registry_index_path", "registry_index_sha256"),
        ("registry_status_path", "registry_status_sha256"),
    ):
        safe_relative_path(target[path_key], f"target.{path_key}")
        if not is_sha256(target[hash_key]):
            raise TargetedEffectError(f"target.{hash_key} is invalid")

    timing = require_exact_keys(
        value["timing"],
        {"not_before_utc", "expires_utc", "evaluated_at_utc"},
        "target timing",
    )
    not_before = parse_utc(timing["not_before_utc"], "not_before_utc")
    expires = parse_utc(timing["expires_utc"], "expires_utc")
    parse_utc(timing["evaluated_at_utc"], "evaluated_at_utc")
    if not_before >= expires:
        raise TargetedEffectError("target delivery time window is empty")

    authorization = require_exact_keys(
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
    if (
        not isinstance(authorization["responsible_human"], str)
        or not authorization["responsible_human"].strip()
        or len(authorization["responsible_human"]) > 256
    ):
        raise TargetedEffectError("responsible human is invalid")
    if type(authorization["origin_authenticated"]) is not bool:
        raise TargetedEffectError("origin_authenticated must be boolean")
    if authorization["effect_ack_state"] not in {
        state.value for state in EffectState
    }:
        raise TargetedEffectError("target authorization has an invalid state")
    protocol_values = (
        authorization["effect_ack_protocol_path"],
        authorization["effect_ack_protocol_hash"],
        authorization["effect_ack_evaluated_at_utc"],
    )
    if any(item is not None for item in protocol_values):
        if any(item is None for item in protocol_values):
            raise TargetedEffectError("effect ACK binding must be all-or-none")
        safe_relative_path(protocol_values[0], "effect_ack_protocol_path")
        protocol_hash = protocol_values[1]
        if (
            not isinstance(protocol_hash, str)
            or not protocol_hash.startswith("sha256:")
            or not is_sha256(protocol_hash[7:])
        ):
            raise TargetedEffectError("effect ACK protocol hash is invalid")
        parse_utc(protocol_values[2], "effect_ack_evaluated_at_utc")
    if (
        authorization["effect_ack_state"] == EffectState.EFFECT_ACK_DONE.value
        and any(item is None for item in protocol_values)
    ):
        raise TargetedEffectError("EFFECT_ACK_DONE requires a complete protocol")

    checkpoint = require_exact_keys(
        value["checkpoint"],
        {"previous_checkpoint_path", "previous_checkpoint_sha256"},
        "target checkpoint",
    )
    safe_relative_path(
        checkpoint["previous_checkpoint_path"], "previous_checkpoint_path"
    )
    if not is_sha256(checkpoint["previous_checkpoint_sha256"]):
        raise TargetedEffectError("previous checkpoint SHA-256 is invalid")

    dispatch = require_exact_keys(
        value["dispatch"],
        {"state", "attempted", "transport_ack", "effect_receipt"},
        "target dispatch",
    )
    if dispatch != {
        "state": "NOT_DISPATCHED",
        "attempted": False,
        "transport_ack": False,
        "effect_receipt": None,
    }:
        raise TargetedEffectError("tracked targeted envelope must remain inert")
    non_claims = value["non_claims"]
    if (
        not isinstance(non_claims, list)
        or any(not isinstance(item, str) or not item for item in non_claims)
        or len(non_claims) != len(set(non_claims))
        or not REQUIRED_NON_CLAIMS.issubset(non_claims)
    ):
        raise TargetedEffectError("target envelope non-claims are incomplete")


def targeted_effect_subject(envelope: Mapping[str, Any]) -> bytes:
    """Canonical bytes that make an EFFECT_ACK target- and time-specific."""
    return canonical_json_bytes(
        {
            "schema": "qikvrt_targeted_effect_subject_v1",
            "envelope_id": envelope["envelope_id"],
            "effect_scope": envelope["effect_scope"],
            "payload": envelope["payload"],
            "target": envelope["target"],
            "timing": envelope["timing"],
            "checkpoint": envelope["checkpoint"],
        }
    )


def verify_checkpoint_binding(
    envelope: Mapping[str, Any], root: Path
) -> bool:
    checkpoint_binding = envelope["checkpoint"]
    relative, _raw = read_bound_file(
        root,
        checkpoint_binding["previous_checkpoint_path"],
        "previous_checkpoint_path",
    )
    try:
        checkpoint = read_json(root / relative, "previous checkpoint")
    except SeedError as exc:
        raise TargetedEffectError(str(exc)) from exc
    if not isinstance(checkpoint, Mapping):
        return False
    previous_hash = checkpoint.get("previous_checkpoint_sha256")
    observed_hash = checkpoint.get("checkpoint_sha256")
    if not is_sha256(previous_hash) or not is_sha256(observed_hash):
        return False
    recomputed = checkpoint_hash(
        checkpoint, previous_checkpoint_sha256=previous_hash
    )
    return (
        observed_hash == recomputed
        and checkpoint_binding["previous_checkpoint_sha256"] == observed_hash
    )


def evaluate_targeted_envelope(
    envelope: Mapping[str, Any], root: Path = ROOT
) -> dict[str, Any]:
    """Evaluate one inert candidate without network, write, or dispatch."""
    validate_envelope(envelope)
    target = envelope["target"]
    payload = envelope["payload"]
    timing = envelope["timing"]
    authorization = envelope["authorization"]
    failures: list[str] = []
    checks: dict[str, bool] = {}

    _payload_path, payload_bytes = read_bound_file(
        root, payload["path"], "payload.path"
    )
    checks["payload_bytes_exact"] = (
        payload["bytes"] == len(payload_bytes)
        and payload["sha256"] == sha256_bytes(payload_bytes)
    )
    if not checks["payload_bytes_exact"]:
        failures.append("PAYLOAD_HASH_OR_SIZE_MISMATCH")

    registry_values: dict[str, dict[str, Any]] = {}
    for path_key, hash_key in (
        ("registry_path", "registry_entry_sha256"),
        ("registry_index_path", "registry_index_sha256"),
        ("registry_status_path", "registry_status_sha256"),
    ):
        relative, raw = read_bound_file(root, target[path_key], f"target.{path_key}")
        exact = target[hash_key] == sha256_bytes(raw)
        checks[f"{path_key}_exact"] = exact
        if not exact:
            failures.append(f"{path_key.upper()}_DIGEST_MISMATCH")
        try:
            registry_value = read_json(root / relative, f"target.{path_key}")
        except SeedError as exc:
            raise TargetedEffectError(str(exc)) from exc
        if not isinstance(registry_value, dict):
            raise TargetedEffectError(f"target.{path_key} must contain an object")
        registry_values[path_key] = registry_value

    index_nodes = registry_values["registry_index_path"].get("nodes")
    status_nodes = registry_values["registry_status_path"].get("nodes")
    if not isinstance(index_nodes, list) or not isinstance(status_nodes, list):
        raise TargetedEffectError("registry index and status nodes must be arrays")
    index_matches = [
        node
        for node in index_nodes
        if isinstance(node, Mapping) and node.get("guid") == target["node_guid"]
    ]
    status_matches = [
        node
        for node in status_nodes
        if isinstance(node, Mapping) and node.get("guid") == target["node_guid"]
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
    except TargetedEffectError:
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

    checks["checkpoint_exact"] = verify_checkpoint_binding(envelope, root)
    if not checks["checkpoint_exact"]:
        failures.append("PREVIOUS_CHECKPOINT_MISMATCH")

    checks["responsible_human_named"] = bool(
        authorization["responsible_human"].strip()
    )
    checks["origin_authenticated"] = authorization["origin_authenticated"] is True
    checks["effect_ack_protocol_verified"] = False
    protocol_path = authorization["effect_ack_protocol_path"]
    if protocol_path is not None:
        try:
            protocol_value = read_json(
                root
                / safe_relative_path(protocol_path, "effect_ack_protocol_path"),
                "effect ACK protocol",
            )
            protocol = ResponsibilityProtocol.from_dict(protocol_value)
            verify_protocol(protocol)
        except (
            ClosureError,
            SeedError,
            ValueError,
            TypeError,
            KeyError,
        ):
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
                == timing["evaluated_at_utc"]
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
        or failure
        in {
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
        "schema": EVALUATION_SCHEMA,
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
            "REVALIDATE_TARGET_AND_REEVALUATE_EFFECT_ACK"
            if not eligible
            else "HAND_TO_SEPARATELY_AUTHORIZED_IDEMPOTENT_EXECUTOR"
        ),
    }


def load_envelope(root: Path, relative_path: str) -> dict[str, Any]:
    path = safe_relative_path(relative_path, "envelope")
    try:
        value = read_json(root / path, "targeted effect envelope")
    except SeedError as exc:
        raise TargetedEffectError(str(exc)) from exc
    validate_envelope(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate = subparsers.add_parser(
        "evaluate", help="evaluate one repository-local inert envelope"
    )
    evaluate.add_argument("--envelope", required=True)
    evaluate.add_argument(
        "--repository-root", type=Path, default=ROOT, help=argparse.SUPPRESS
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        envelope = load_envelope(arguments.repository_root, arguments.envelope)
        result = evaluate_targeted_envelope(envelope, arguments.repository_root)
    except (ClosureError, SeedError, OSError, ValueError) as exc:
        print(f"BLOCK: {exc}")
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
