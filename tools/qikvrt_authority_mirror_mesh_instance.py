#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build a strict, read-only Authority/Mirror mesh instance.

The instance deliberately separates a mesh-wide observation object from a
shared canonical ``main``. Two repositories may be jointly observable while
their heads, trees, integrity evidence, and lifecycle remain distinct.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections.abc import Mapping
from typing import Any


INPUT_SCHEMA = "qikvrt_authority_mirror_observation_input_v1"
SCHEMA = "qikvrt_authority_mirror_mesh_instance_v1"
TERMINAL_PROJECTION_SCHEMA = "qikvrt_terminal_projection_v1"
MESH_INSTANCE_ID = "QIKVRT_AUTHORITY_MIRROR_MESH_V1"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class MeshInstanceError(ValueError):
    """Raised when an observation cannot support a strict mesh instance."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for input and projection binding."""
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MeshInstanceError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise MeshInstanceError(f"{label} must contain exactly {sorted(keys)}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(ord(ch) < 32 for ch in value):
        raise MeshInstanceError(f"{label} must be non-empty text without controls")
    return value


def _sha1(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA1_RE.fullmatch(value):
        raise MeshInstanceError(f"{label} must be a lowercase Git SHA-1")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise MeshInstanceError(f"{label} must be a lowercase SHA-256")
    return value


def _count(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise MeshInstanceError(f"{label} must be an integer >= {minimum}")
    return value


def _normalize_integrity(value: Any, label: str) -> dict[str, str] | None:
    if value is None:
        return None
    integrity = _mapping(value, label)
    required = {"repository_file_manifest_sha256", "sha256sums_sha256"}
    _exact_keys(integrity, required, label)
    return {
        "repository_file_manifest_sha256": _sha256(
            integrity["repository_file_manifest_sha256"],
            f"{label}.repository_file_manifest_sha256",
        ),
        "sha256sums_sha256": _sha256(
            integrity["sha256sums_sha256"],
            f"{label}.sha256sums_sha256",
        ),
    }


def _normalize_node(value: Any, expected_role: str) -> dict[str, Any]:
    node = _mapping(value, expected_role.lower())
    _exact_keys(
        node,
        {
            "repository",
            "role",
            "ref_name",
            "head_sha",
            "root_tree_sha",
            "inventory",
            "integrity",
        },
        expected_role.lower(),
    )
    repository = _text(node["repository"], f"{expected_role}.repository")
    if "/" not in repository or repository.startswith("/") or repository.endswith("/"):
        raise MeshInstanceError(f"{expected_role}.repository must be owner/name")
    if node["role"] != expected_role:
        raise MeshInstanceError(f"{expected_role}.role must be {expected_role}")
    if node["ref_name"] != "main":
        raise MeshInstanceError(f"{expected_role}.ref_name must be main")

    inventory = _mapping(node["inventory"], f"{expected_role}.inventory")
    _exact_keys(
        inventory,
        {"open_issues", "open_pull_requests", "branches"},
        f"{expected_role}.inventory",
    )
    branches = _count(inventory["branches"], f"{expected_role}.inventory.branches", minimum=1)

    return {
        "repository": repository,
        "role": expected_role,
        "ref_name": "main",
        "head_sha": _sha1(node["head_sha"], f"{expected_role}.head_sha"),
        "root_tree_sha": _sha1(node["root_tree_sha"], f"{expected_role}.root_tree_sha"),
        "inventory": {
            "open_issues": _count(inventory["open_issues"], f"{expected_role}.inventory.open_issues"),
            "open_pull_requests": _count(
                inventory["open_pull_requests"],
                f"{expected_role}.inventory.open_pull_requests",
            ),
            "branches": branches,
        },
        "integrity": _normalize_integrity(node["integrity"], f"{expected_role}.integrity"),
    }


def _normalize_input(value: Any) -> dict[str, Any]:
    observation = _mapping(value, "observation")
    _exact_keys(
        observation,
        {"schema", "observation_id", "observed_at", "authority", "mirror"},
        "observation",
    )
    if observation["schema"] != INPUT_SCHEMA:
        raise MeshInstanceError(f"observation.schema must be {INPUT_SCHEMA}")
    normalized = {
        "schema": INPUT_SCHEMA,
        "observation_id": _text(observation["observation_id"], "observation_id"),
        "observed_at": _text(observation["observed_at"], "observed_at"),
        "authority": _normalize_node(observation["authority"], "AUTHORITY"),
        "mirror": _normalize_node(observation["mirror"], "MIRROR"),
    }
    if normalized["authority"]["repository"] == normalized["mirror"]["repository"]:
        raise MeshInstanceError("authority and mirror repositories must be distinct")
    return normalized


def _relationship(authority: Mapping[str, Any], mirror: Mapping[str, Any]) -> dict[str, Any]:
    same_tree = authority["root_tree_sha"] == mirror["root_tree_sha"]
    same_head = authority["head_sha"] == mirror["head_sha"]
    integrity_available = authority["integrity"] is not None and mirror["integrity"] is not None
    integrity_equal = integrity_available and authority["integrity"] == mirror["integrity"]

    if not same_tree:
        state = "DIVERGED"
        first_blocker = "AUTHORITY_MIRROR_ROOT_TREE_DIFFER"
        next_action = "REOBSERVE_OR_FOLLOW_HISTORY_PRESERVING_WHOLE_TREE_CONVERGENCE"
        content_state = "NOT_DERIVED"
        content_reason = "AUTHORITY_MIRROR_ROOT_TREE_DIFFER"
    elif not integrity_equal:
        state = "TREE_EQUALITY_UNVERIFIED_INTEGRITY"
        first_blocker = "PAIR_INTEGRITY_EVIDENCE_MISSING_OR_DIFFERENT"
        next_action = "REOBSERVE_COMPLETE_PAIR_INTEGRITY_EVIDENCE"
        content_state = "TREE_EQUALITY_ONLY"
        content_reason = "NO_MATCHING_PAIR_INTEGRITY_BINDING"
    else:
        state = "CONTENT_EQUIVALENT_NOT_RECIPROCAL_RECEIPT_BOUND"
        first_blocker = "RECIPROCAL_WHOLE_TREE_RECEIPT_NOT_BOUND"
        next_action = "MATERIALIZE_RECIPROCAL_WHOLE_TREE_RECEIPT_AFTER_EXACT_REOBSERVATION"
        content_state = "PAIR_CONTENT_OBSERVED"
        content_reason = "CONTENT_PAIR_OBSERVED_BUT_NO_RECIPROCAL_RECEIPT"

    return {
        "state": state,
        "same_head_observed": same_head,
        "same_root_tree_observed": same_tree,
        "matching_integrity_pair_observed": integrity_equal,
        "first_deterministic_blocker": first_blocker,
        "next_admitted_action": next_action,
        "canonical_content": {
            "state": content_state,
            "mesh_main_ref": None,
            "root_tree_sha": authority["root_tree_sha"] if same_tree else None,
            "reason": content_reason,
        },
    }


def _aggregate_inventory(authority: Mapping[str, Any], mirror: Mapping[str, Any]) -> dict[str, Any]:
    authority_inventory = authority["inventory"]
    mirror_inventory = mirror["inventory"]
    return {
        "semantics": "ARITHMETIC_SUM_ONLY_NO_EQUALITY_OR_LIFECYCLE_INFERENCE",
        "open_issues": authority_inventory["open_issues"] + mirror_inventory["open_issues"],
        "open_pull_requests": (
            authority_inventory["open_pull_requests"] + mirror_inventory["open_pull_requests"]
        ),
        "branches": authority_inventory["branches"] + mirror_inventory["branches"],
        "non_main_branch_refs": (
            authority_inventory["branches"] - 1 + mirror_inventory["branches"] - 1
        ),
        "non_main_ref_is_lifecycle_or_gc_authority": False,
    }


def build_mesh_instance(value: Any) -> dict[str, Any]:
    """Materialize one lossless, exact-input-bound mesh observation envelope."""
    observation = _normalize_input(value)
    authority = observation["authority"]
    mirror = observation["mirror"]
    relationship = _relationship(authority, mirror)
    return {
        "schema": SCHEMA,
        "mesh_instance_id": MESH_INSTANCE_ID,
        "topology": "AUTHORITY_MIRROR_PAIR",
        "observation": {
            "observation_id": observation["observation_id"],
            "observed_at": observation["observed_at"],
            "canonical_input_schema": INPUT_SCHEMA,
            "canonical_input_sha256": canonical_json_sha256(observation),
        },
        "nodes": {"authority": authority, "mirror": mirror},
        "relationship": relationship,
        "inventory_aggregation": _aggregate_inventory(authority, mirror),
        "effect_class": "OBSERVE_ONLY",
        "terminal_projection_contract": {
            "pipeline": [
                "CANONICAL_EVENT_ENVELOPE",
                "AUDIENCE_RESOLUTION",
                "LOSSLESS_VIEW_SELECTION",
                "TERMINAL_PROJECTION",
            ],
            "audiences": ["EXECUTIVE", "EXPERT", "FULL"],
            "full_projection": "CANONICAL_ENVELOPE_WITHOUT_SEMANTIC_COMPRESSION",
        },
        "completion_claims": {
            "mesh_general_instance_materialized": True,
            "mesh_canonical_main_derived": False,
            "authority_mirror_equality_claimed": False,
            "merge": False,
            "synchronization": False,
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def terminal_projection(instance: Mapping[str, Any], audience: str) -> dict[str, Any]:
    """Project the one envelope without transferring evidence between views."""
    if audience not in {"EXECUTIVE", "EXPERT", "FULL"}:
        raise MeshInstanceError("audience must be EXECUTIVE, EXPERT, or FULL")
    envelope = _mapping(instance, "instance")
    if envelope.get("schema") != SCHEMA:
        raise MeshInstanceError(f"instance.schema must be {SCHEMA}")
    digest = canonical_json_sha256(envelope)
    relationship = _mapping(envelope.get("relationship"), "instance.relationship")
    executive = {
        "mesh_instance_id": envelope["mesh_instance_id"],
        "state": relationship["state"],
        "canonical_content_state": relationship["canonical_content"]["state"],
        "first_deterministic_blocker": relationship["first_deterministic_blocker"],
        "next_admitted_action": relationship["next_admitted_action"],
        "effect_class": envelope["effect_class"],
        "inventory_aggregation": envelope["inventory_aggregation"],
    }
    result: dict[str, Any] = {
        "schema": TERMINAL_PROJECTION_SCHEMA,
        "audience": audience,
        "canonical_envelope_sha256": digest,
        "executive": executive,
    }
    if audience == "EXPERT":
        result["expert"] = {
            "observation": envelope["observation"],
            "nodes": envelope["nodes"],
            "relationship": relationship,
            "completion_claims": envelope["completion_claims"],
        }
    elif audience == "FULL":
        result["full"] = envelope
    return result


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=pathlib.Path, help="canonical observation JSON")
    parser.add_argument(
        "--audience",
        default="FULL",
        choices=("EXECUTIVE", "EXPERT", "FULL"),
        help="lossless terminal projection audience",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        instance = build_mesh_instance(raw)
        print(json.dumps(terminal_projection(instance, args.audience), ensure_ascii=False, indent=2, sort_keys=True))
    except (OSError, json.JSONDecodeError, MeshInstanceError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
