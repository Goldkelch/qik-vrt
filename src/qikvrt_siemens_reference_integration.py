#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

SCHEMA = "qikvrt_siemens_reference_integration_v1"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class TwinState:
    entity: str
    version: int
    position_m: float
    velocity_mps: float
    temperature_c: float

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TwinState":
        required = {"entity", "version", "position_m", "velocity_mps", "temperature_c"}
        if set(raw) != required:
            raise ValueError("state fields must match the closed reference schema")
        if not isinstance(raw["entity"], str) or not raw["entity"]:
            raise ValueError("entity must be non-empty")
        if not isinstance(raw["version"], int) or raw["version"] < 0:
            raise ValueError("version must be a non-negative integer")
        return cls(
            entity=raw["entity"], version=raw["version"],
            position_m=float(raw["position_m"]), velocity_mps=float(raw["velocity_mps"]),
            temperature_c=float(raw["temperature_c"]),
        )


def observe(state: TwinState) -> dict[str, Any]:
    body = asdict(state)
    return {"schema": SCHEMA, "phase": "OBSERVE", "subject": body, "subject_sha256": digest(body)}


def prepare(state: TwinState, *, target_velocity_mps: float) -> dict[str, Any]:
    if target_velocity_mps < 0 or target_velocity_mps > 120:
        raise ValueError("target velocity outside bounded reference domain")
    proposal = {
        "entity": state.entity,
        "expected_version": state.version,
        "target_velocity_mps": float(target_velocity_mps),
    }
    return {
        "schema": SCHEMA, "phase": "PREPARE", "protected_effect_executed": False,
        "source_subject_sha256": digest(asdict(state)), "proposal": proposal,
        "proposal_sha256": digest(proposal),
    }


def simulate(state: TwinState, prepared: dict[str, Any], *, dt_s: float = 1.0) -> TwinState:
    if prepared.get("phase") != "PREPARE":
        raise ValueError("prepared record required")
    proposal = prepared["proposal"]
    if proposal["entity"] != state.entity or proposal["expected_version"] != state.version:
        raise ValueError("stale or mismatched exact subject")
    velocity = float(proposal["target_velocity_mps"])
    return TwinState(
        entity=state.entity,
        version=state.version + 1,
        position_m=state.position_m + velocity * dt_s,
        velocity_mps=velocity,
        temperature_c=state.temperature_c + abs(velocity - state.velocity_mps) * 0.001,
    )


def commit_simulated(state: TwinState, prepared: dict[str, Any]) -> tuple[TwinState, dict[str, Any]]:
    new_state = simulate(state, prepared)
    effect = {
        "schema": SCHEMA,
        "phase": "AUTHORITY_COMMIT",
        "adapter": "SIMULATED_DIGITAL_TWIN_ONLY",
        "physical_effect": False,
        "previous_subject_sha256": digest(asdict(state)),
        "result_subject_sha256": digest(asdict(new_state)),
        "proposal_sha256": prepared["proposal_sha256"],
    }
    return new_state, effect


def reobserve(previous: TwinState, current: TwinState, effect: dict[str, Any]) -> dict[str, Any]:
    exact = (
        current.entity == previous.entity
        and current.version == previous.version + 1
        and effect.get("result_subject_sha256") == digest(asdict(current))
    )
    receipt = {
        "schema": SCHEMA,
        "phase": "EFFECT_ACK" if exact else "HOLD_UNVERIFIED",
        "effect_ack": bool(exact),
        "physical_effect_ack": False,
        "subject": asdict(current),
        "subject_sha256": digest(asdict(current)),
        "effect_sha256": digest(effect),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def run_roundtrip(initial: TwinState, target_velocity_mps: float) -> dict[str, Any]:
    observation = observe(initial)
    prepared = prepare(initial, target_velocity_mps=target_velocity_mps)
    result, effect = commit_simulated(initial, prepared)
    receipt = reobserve(initial, result, effect)
    return {
        "schema": SCHEMA,
        "boundary": "REFERENCE_SIMULATION_NOT_SIEMENS_TENANT_OR_PHYSICAL_ACTUATION",
        "observation": observation,
        "prepared": prepared,
        "effect": effect,
        "receipt": receipt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="QIK-VRT Siemens/Horizon executable reference integration")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--target-velocity", type=float, required=True)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    initial = TwinState.from_dict(json.loads(args.input.read_text(encoding="utf-8")))
    result = run_roundtrip(initial, args.target_velocity)
    encoded = canonical(result).decode("utf-8")
    print(encoded)
    if args.journal:
        args.journal.parent.mkdir(parents=True, exist_ok=True)
        with args.journal.open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
    return 0 if result["receipt"]["effect_ack"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
