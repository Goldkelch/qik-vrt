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
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
ROOT_STRING = str(ROOT)
if ROOT_STRING not in sys.path:
    sys.path.insert(0, ROOT_STRING)

from tools.qikvrt_seed_common import SeedError, canonical_json_bytes, read_json


POLICY_PATH = Path("policy/GLOBAL_SYSTEM_CLOSURE_V1.json")
EVIDENCE_PATH = Path("system-closure/ARCHITECTURE_FUNCTIONALITY_EVIDENCE.json")
POLICY_SCHEMA = "qikvrt_global_system_closure_policy_v1"
EVIDENCE_SCHEMA = "qikvrt_architecture_functionality_evidence_v1"
SCOPE_ID = "qikvrt-global-system-closure-v1"
ZERO_SHA256 = "0" * 64


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
    return {
        "schema": "qikvrt_global_system_closure_check_v1",
        "scope_id": SCOPE_ID,
        "state": "CONTINUE",
        "effect_state": "EFFECT_ACK_CONTINUE",
        "policy_sha256": canonical_digest(policy),
        "functionality_evidence_sha256": canonical_digest(evidence),
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
        choices=("check",),
        help="validate the current closure contract without writing repository files",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "check":
        try:
            result = check()
        except ClosureError as exc:
            print(f"BLOCK: {exc}")
            return 2
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    raise AssertionError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
