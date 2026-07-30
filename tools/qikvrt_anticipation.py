#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize and verify the bounded QIK-VRT anticipation projection.

This module is deliberately effect-free. It validates an evidence-bound input,
derives one trend and one next effect, and writes only deterministic repository
projections plus two hash-linked checkpoints.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
ROOT_STRING = str(ROOT)
if ROOT_STRING not in sys.path:
    sys.path.insert(0, ROOT_STRING)

from tools.qikvrt_seed_common import (  # noqa: E402
    SeedError,
    canonical_json_bytes,
    read_json,
    write_json,
    write_text,
)


POLICY_PATH = Path("policy/GLOBAL_SYSTEM_CLOSURE_V1.json")
INPUT_PATH = Path("anticipation/INPUT.json")
CURRENT_PATH = Path("anticipation/current.json")
HISTORY_PATH = Path("anticipation/history.jsonl")
TRENDS_PATH = Path("anticipation/trends.json")
DERIVATIVES_PATH = Path("anticipation/derivatives.json")
NEXT_EFFECT_PATH = Path("anticipation/next-effect.json")
CHECKPOINT_1_PATH = Path("receipts/anticipation/0001-contract-bound.json")
CHECKPOINT_2_PATH = Path("receipts/anticipation/0002-anticipation-materialized.json")
POLICY_SCHEMA = "qikvrt_global_system_closure_policy_v1"
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
)


class ClosureError(RuntimeError):
    """A contract or projection violation that must fail closed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_digest(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def require_exact_keys(
    value: Any, keys: set[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ClosureError(f"{label} must contain exactly {sorted(keys)}")
    return value


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def safe_relative_path(raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise ClosureError(f"{label} must be a repository-relative path")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ClosureError(f"{label} is unsafe")
    return path


def read_bound_file(root: Path, raw_path: Any, label: str) -> tuple[Path, bytes]:
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
            "status_projection",
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
    if value["persistence_stages"] != [
        "CONTRACT_BOUND",
        "ANTICIPATION_MATERIALIZED",
        "EFFECT_INTENTS_GATED",
        "CANDIDATE_VERIFIED",
        "AUTHORITY_OBSERVED",
        "MIRROR_OBSERVED",
        "RECEIPT_CLOSED",
    ]:
        raise ClosureError("persistence-stage drift")
    monotonic = value["monotonic_improvement"]
    if monotonic["accepted_transitions"] != [
        "NON_REGRESSING_GATE_IMPROVEMENT",
        "BYTE_STABLE_NO_OP",
    ]:
        raise ClosureError("monotonic transition contract drift")
    if (
        monotonic["regression_becomes_canonical"] is not False
        or monotonic["unmeasured_improvement_claim_allowed"] is not False
    ):
        raise ClosureError("monotonic policy permits an unproved improvement")
    effect = value["effect_boundary"]
    if (
        effect["required_release_state"] != "EFFECT_ACK_DONE"
        or effect["default_state"] != "EFFECT_ACK_CONTINUE"
        or effect["transport_ack_is_effect_ack"] is not False
        or effect["adaptive_runtime_may_issue_done"] is not False
    ):
        raise ClosureError("EFFECT_ACK boundary drift")
    status = value["status_projection"]
    if (
        status["source_paths"] != ["AI_PROGRESS.json", "AI_STATUS.md"]
        or status["scope_separation_required"] is not True
        or status["repository_wide_completion_inference_allowed"] is not False
        or status["external_effects_may_be_dispatched"] is not False
    ):
        raise ClosureError("status-projection boundary drift")
    if value["completion_claims"] != {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
    }:
        raise ClosureError("closure policy contains a false completion claim")


def validate_source_bindings(
    source_bindings: Any, root: Path | None = None
) -> dict[str, dict[str, Any]]:
    if not isinstance(source_bindings, list) or len(source_bindings) < 2:
        raise ClosureError("source_bindings must contain at least two files")
    result: dict[str, dict[str, Any]] = {}
    for index, binding in enumerate(source_bindings):
        require_exact_keys(
            binding, {"path", "bytes", "sha256"}, f"source_bindings[{index}]"
        )
        relative = safe_relative_path(binding["path"], f"source_bindings[{index}].path")
        key = relative.as_posix()
        if key in result:
            raise ClosureError("source binding paths must be unique")
        if (
            type(binding["bytes"]) is not int
            or binding["bytes"] < 1
            or not is_sha256(binding["sha256"])
        ):
            raise ClosureError(f"invalid source binding for {key}")
        if root is not None:
            _, payload = read_bound_file(root, key, f"source binding {key}")
            if len(payload) != binding["bytes"]:
                raise ClosureError(f"source binding byte count drift: {key}")
            if sha256_bytes(payload) != binding["sha256"]:
                raise ClosureError(f"source binding digest drift: {key}")
        result[key] = {
            "bytes": binding["bytes"],
            "sha256": binding["sha256"],
        }
    required = {"AI_PROGRESS.json", "AI_STATUS.md"}
    if not required.issubset(result):
        raise ClosureError("current status source bindings are incomplete")
    return result


def validate_input(value: Mapping[str, Any], root: Path | None = None) -> None:
    require_exact_keys(
        value,
        {
            "_license",
            "schema",
            "scope_id",
            "repository",
            "source_revision",
            "observed_at",
            "source_bindings",
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
    validate_source_bindings(value["source_bindings"], root)
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
            raise ClosureError("observation state IDs must be unique")
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
    if value["observed_at"] != observations[-1]["observed_at"]:
        raise ClosureError("top-level observed_at must equal the latest observation")
    next_effect = value["next_effect"]
    require_exact_keys(
        next_effect,
        {
            "effect_id",
            "anticipated_state_id",
            "description",
            "executor_capability",
            "preconditions",
            "expected_receipt",
        },
        "next effect",
    )
    if (
        not next_effect["effect_id"]
        or not next_effect["anticipated_state_id"]
        or not next_effect["expected_receipt"]
        or not isinstance(next_effect["preconditions"], list)
        or not next_effect["preconditions"]
    ):
        raise ClosureError("NEXT_EFFECT_NOT_SELECTED")
    if value["completion_claims"] != {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
    }:
        raise ClosureError("anticipation input contains a false completion claim")


def classify_monotonic_transition(
    previous: Mapping[str, int], candidate: Mapping[str, int]
) -> str:
    """Classify only the declared metric map; infer no hidden quality."""
    if set(previous) != set(candidate) or not previous:
        raise ClosureError("metric sets must be equal and non-empty")
    if any(type(value) is not int for value in [*previous.values(), *candidate.values()]):
        raise ClosureError("metrics must be integers")
    if canonical_json_bytes(previous) == canonical_json_bytes(candidate):
        return "BYTE_STABLE_NO_OP"
    if any(candidate[key] < previous[key] for key in previous):
        return "REJECTED_REGRESSION"
    if any(candidate[key] > previous[key] for key in previous):
        return "NON_REGRESSING_GATE_IMPROVEMENT"
    raise ClosureError("unclassifiable metric transition")


def checkpoint_hash(
    checkpoint: Mapping[str, Any], *, previous_checkpoint_sha256: str
) -> str:
    if not is_sha256(previous_checkpoint_sha256):
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


def observation_projection(observation: Mapping[str, Any]) -> dict[str, Any]:
    digest_basis = {
        "state_id": observation["state_id"],
        "observed_at": observation["observed_at"],
        "classification": observation["classification"],
        "productive_chain_position": observation["productive_chain_position"],
        "metrics": observation["metrics"],
        "evidence": observation["evidence"],
    }
    return {**digest_basis, "state_digest": canonical_digest(digest_basis)}


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
    input_value: Mapping[str, Any],
    *,
    planner: Callable[[Mapping[str, Any]], dict[str, Any]] = default_planner,
) -> dict[Path, bytes]:
    validate_policy(policy)
    validate_input(input_value)
    observations = [
        observation_projection(item) for item in input_value["observations"]
    ]
    trend = derive_trend(input_value["observations"])
    derivatives = derive_derivatives(input_value["observations"])
    next_effect = planner(input_value)
    if next_effect != input_value["next_effect"]:
        raise ClosureError("TREND_DERIVATION_NONDETERMINISTIC")
    source_bindings = validate_source_bindings(input_value["source_bindings"])
    basis = {
        "policy_sha256": canonical_digest(policy),
        "input_sha256": canonical_digest(input_value),
        "source_revision": input_value["source_revision"],
        "source_bindings": source_bindings,
    }
    current = {
        "schema_version": STATE_SCHEMA,
        "observation_id": "gsc-anticipation-current-main-0002",
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
            "state_id": next_effect["anticipated_state_id"],
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
            str(INPUT_PATH),
            *sorted(source_bindings),
        ],
        "provenance": {
            "source_revision": input_value["source_revision"],
            "sha256": canonical_digest(basis),
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
        "checkpoint_id": "gsc-current-main-0001-contract-bound",
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
        path.as_posix(): {"bytes": len(raw), "sha256": sha256_bytes(raw)}
        for path, raw in primary_outputs.items()
    }
    checkpoint_2 = {
        "schema": "qikvrt_closure_checkpoint_v1",
        "scope_id": SCOPE_ID,
        "checkpoint_id": "gsc-current-main-0002-anticipation-materialized",
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


def load_policy(root: Path = ROOT) -> dict[str, Any]:
    try:
        policy = read_json(root / POLICY_PATH, "closure policy")
    except SeedError as exc:
        raise ClosureError(str(exc)) from exc
    validate_policy(policy)
    return policy


def load_anticipation_input(root: Path = ROOT) -> dict[str, Any]:
    try:
        value = read_json(root / INPUT_PATH, "anticipation input")
    except SeedError as exc:
        raise ClosureError(str(exc)) from exc
    validate_input(value, root)
    return value


def expected_projections(root: Path = ROOT) -> dict[Path, bytes]:
    return build_projections(load_policy(root), load_anticipation_input(root))


def materialize(root: Path = ROOT) -> dict[str, Any]:
    outputs = expected_projections(root)
    for relative, raw in outputs.items():
        if relative == HISTORY_PATH:
            write_text(root / relative, raw.decode("utf-8"))
        else:
            write_json(root / relative, json.loads(raw))
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
        try:
            actual = (root / relative).read_bytes()
        except OSError as exc:
            raise ClosureError(f"missing projection {relative}: {exc}") from exc
        if actual != expected:
            raise ClosureError(f"projection drift: {relative}")
        verified[relative.as_posix()] = sha256_bytes(actual)
    return verified


def check(root: Path = ROOT) -> dict[str, Any]:
    policy = load_policy(root)
    verified = verify_projections(root)
    latest = json.loads((root / CHECKPOINT_2_PATH).read_text(encoding="utf-8"))
    return {
        "schema": "qikvrt_global_system_closure_check_v1",
        "scope_id": SCOPE_ID,
        "state": "CONTINUE",
        "effect_state": "EFFECT_ACK_CONTINUE",
        "policy_sha256": canonical_digest(policy),
        "verified_projection_count": len(verified),
        "latest_checkpoint_sha256": latest["checkpoint_sha256"],
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
        result = materialize() if arguments.command == "materialize" else check()
    except (ClosureError, SeedError, OSError, ValueError) as exc:
        print(f"BLOCK: {exc}")
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
