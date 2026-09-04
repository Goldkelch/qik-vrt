#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic QIK-VRT metatransistor mesh data-flow model.

The model deliberately separates four things:

* a repository or terminal subject;
* one authority node and exactly eight mirror/child lanes;
* lossless canonical transport and derealisation receipts;
* fixed-point ALU semantics with explicit overflow and rounding.

It is an executable architecture demonstrator.  It does not perform GitHub
writes, deploy services, or claim physical hardware execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FANOUT = 8
RETIREMENT_DEPTH = 9
MAX_MATERIALIZED_DEPTH = 3
TERMINAL_SLOTS = (0, 7)

GATE_NAMES = (
    "QIKVRT CI",
    "QIKVRT repository evidence materialization",
    "QIKVRT Collective Proposal Review",
    "QIKVRT code-owner review observer",
    "QIKVRT live status watch",
    "QIKVRT Spark branch work-unit core",
    "QIKVRT zero-bug continuous invariant",
    "QIKVRT explicit HOLD contract",
)

ACTIVE_GATE_STATES = frozenset({"REQUESTED", "RUNNING"})
TERMINAL_GATE_STATES = frozenset({"SUCCESS", "HOLD", "SKIPPED", "CANCELLED"})


def canonical_bytes(value: Any) -> bytes:
    """Return the single canonical UTF-8 JSON representation used by the model."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_int(name: str, value: Any, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
    return value


def logical_node_count(depth: int, fanout: int = FANOUT) -> int:
    depth = _require_int("depth", depth, 0, 64)
    fanout = _require_int("fanout", fanout, 1, 1024)
    if fanout == 1:
        return depth + 1
    return (fanout ** (depth + 1) - 1) // (fanout - 1)


def _node_identity(root_subject_sha256: str, path: Sequence[int]) -> str:
    body = {
        "schema": "qikvrt_metatransistor_node_identity_v1",
        "root_subject_sha256": root_subject_sha256,
        "path": list(path),
    }
    return f"qnode-{digest(body)[:24]}"


def root_node(subject: Mapping[str, Any], *, tick: int = 0) -> dict[str, Any]:
    if not isinstance(subject, Mapping) or not subject:
        raise ValueError("subject must be a non-empty mapping")
    tick = _require_int("tick", tick, 0, (1 << 63) - 1)
    subject_copy = dict(subject)
    root_subject_sha256 = digest(subject_copy)
    node_id = _node_identity(root_subject_sha256, ())
    body: dict[str, Any] = {
        "schema": "qikvrt_metatransistor_node_v1",
        "node_id": node_id,
        "root_node_id": node_id,
        "root_subject": subject_copy,
        "root_subject_sha256": root_subject_sha256,
        "parent_node_id": None,
        "authority_node_id": node_id,
        "path": [],
        "depth": 0,
        "slot": None,
        "role": "AUTHORITY",
        "monitor": True,
        "terminal": True,
        "tick": tick,
        "fanout": FANOUT,
        "payload_sha256": None,
        "manifestation_complete": True,
    }
    body["state_sha256"] = digest(body)
    return body


def manifest_children(
    parent: Mapping[str, Any],
    payload: Any,
    *,
    tick: int | None = None,
    terminal_slots: Iterable[int] = TERMINAL_SLOTS,
) -> list[dict[str, Any]]:
    """Manifest one canonical payload in exactly eight child nodes.

    Every child carries the same payload bytes and digest.  The unique lane and
    state digests make the eight receipts distinct while preserving a lossless
    common data image.
    """

    if parent.get("schema") != "qikvrt_metatransistor_node_v1":
        raise ValueError("parent schema mismatch")
    parent_path = list(parent.get("path") or [])
    if any(not isinstance(slot, int) or not 0 <= slot < FANOUT for slot in parent_path):
        raise ValueError("parent path is invalid")
    parent_tick = _require_int("parent.tick", parent.get("tick"), 0, (1 << 63) - 2)
    next_tick = parent_tick + 1 if tick is None else _require_int("tick", tick, parent_tick + 1, (1 << 63) - 1)
    allowed_terminal_slots = tuple(sorted(set(terminal_slots)))
    if any(not isinstance(slot, int) or not 0 <= slot < FANOUT for slot in allowed_terminal_slots):
        raise ValueError("terminal slot out of range")

    payload_copy = json.loads(canonical_bytes(payload).decode("utf-8"))
    payload_bytes = canonical_bytes(payload_copy)
    payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    root_subject_sha256 = str(parent.get("root_subject_sha256") or "")
    if len(root_subject_sha256) != 64:
        raise ValueError("parent root subject digest is invalid")

    children: list[dict[str, Any]] = []
    for slot in range(FANOUT):
        path = [*parent_path, slot]
        child_id = _node_identity(root_subject_sha256, path)
        body: dict[str, Any] = {
            "schema": "qikvrt_metatransistor_node_v1",
            "node_id": child_id,
            "root_node_id": parent["root_node_id"],
            "root_subject": parent["root_subject"],
            "root_subject_sha256": root_subject_sha256,
            "parent_node_id": parent["node_id"],
            "authority_node_id": parent["node_id"],
            "path": path,
            "depth": len(path),
            "slot": slot,
            "role": "MIRROR_AUTHORITY",
            "monitor": True,
            "terminal": slot in allowed_terminal_slots,
            "tick": next_tick,
            "fanout": FANOUT,
            "payload": payload_copy,
            "payload_bytes": len(payload_bytes),
            "payload_sha256": payload_sha256,
            "manifestation_complete": True,
            "serialized_link": {
                "schema": "qikvrt_serialized_terminal_link_v1",
                "format": "CANONICAL_JSON_UTF8",
                "source_node_id": parent["node_id"],
                "target_node_id": child_id,
                "tick": next_tick,
                "payload_sha256": payload_sha256,
                "lossless": True,
            },
            "child_authority_contract": {
                "becomes_authority_for_children": True,
                "child_count": FANOUT,
                "authority_monitor": True,
                "terminal_slots": list(allowed_terminal_slots),
            },
        }
        body["state_sha256"] = digest(body)
        children.append(body)
    return children


def derealize(
    parent: Mapping[str, Any],
    children: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify an exact eight-lane manifestation and recover its payload."""

    if len(children) != FANOUT:
        raise ValueError(f"exactly {FANOUT} children are required")
    by_slot: dict[int, Mapping[str, Any]] = {}
    for child in children:
        slot = child.get("slot")
        if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < FANOUT:
            raise ValueError("child slot is invalid")
        if slot in by_slot:
            raise ValueError("duplicate child slot")
        by_slot[slot] = child
    if tuple(sorted(by_slot)) != tuple(range(FANOUT)):
        raise ValueError("child slot set is incomplete")

    expected_payload_sha256: str | None = None
    recovered_payload: Any = None
    child_receipts: list[str] = []
    for slot in range(FANOUT):
        child = dict(by_slot[slot])
        if child.get("schema") != "qikvrt_metatransistor_node_v1":
            raise ValueError("child schema mismatch")
        if child.get("parent_node_id") != parent.get("node_id"):
            raise ValueError("child parent mismatch")
        if child.get("authority_node_id") != parent.get("node_id"):
            raise ValueError("child authority mismatch")
        state_sha256 = child.pop("state_sha256", None)
        if state_sha256 != digest(child):
            raise ValueError("child state digest mismatch")
        if child.get("manifestation_complete") is not True:
            raise ValueError("child manifestation is incomplete")
        payload = child.get("payload")
        payload_sha256 = hashlib.sha256(canonical_bytes(payload)).hexdigest()
        if payload_sha256 != child.get("payload_sha256"):
            raise ValueError("child payload digest mismatch")
        if expected_payload_sha256 is None:
            expected_payload_sha256 = payload_sha256
            recovered_payload = payload
        elif payload_sha256 != expected_payload_sha256:
            raise ValueError("children carry different payloads")
        child_receipts.append(str(state_sha256))

    receipt: dict[str, Any] = {
        "schema": "qikvrt_metatransistor_derealization_receipt_v1",
        "parent_node_id": parent.get("node_id"),
        "root_node_id": parent.get("root_node_id"),
        "source_tick": parent.get("tick"),
        "manifested_tick": children[0].get("tick"),
        "child_slots": list(range(FANOUT)),
        "child_state_sha256": child_receipts,
        "payload": recovered_payload,
        "payload_sha256": expected_payload_sha256,
        "lossless": True,
        "state": "DEREALIZED",
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def materialize_mesh(
    subject: Mapping[str, Any],
    payload: Any,
    *,
    materialized_depth: int = 2,
    tick: int = 0,
) -> dict[str, Any]:
    materialized_depth = _require_int(
        "materialized_depth", materialized_depth, 0, MAX_MATERIALIZED_DEPTH
    )
    root = root_node(subject, tick=tick)
    nodes = [root]
    frontier = [root]
    levels = [{"depth": 0, "count": 1}]
    for depth in range(1, materialized_depth + 1):
        next_frontier: list[dict[str, Any]] = []
        for parent in frontier:
            next_frontier.extend(manifest_children(parent, payload))
        nodes.extend(next_frontier)
        frontier = next_frontier
        levels.append({"depth": depth, "count": len(frontier)})

    projection: dict[str, Any] = {
        "schema": "qikvrt_metatransistor_mesh_projection_v1",
        "framework": "KubiKAva",
        "method": "TESTED_EVENT_MODEL_DRIVEN_DEVELOPMENT",
        "subject": dict(subject),
        "root_node_id": root["node_id"],
        "fanout": FANOUT,
        "materialized_depth": materialized_depth,
        "retirement_depth": RETIREMENT_DEPTH,
        "materialized_node_count": len(nodes),
        "logical_node_count_at_retirement_depth": logical_node_count(RETIREMENT_DEPTH),
        "levels": levels,
        "nodes": nodes,
        "payload_sha256": hashlib.sha256(canonical_bytes(payload)).hexdigest(),
        "tick": tick,
        "transport": "SERIALIZED_UNIVERSAL_TERMINAL",
        "polling": False,
        "security_profile": "DATAFLOW_DEMONSTRATOR_SECURITY_DEFERRED",
        "physical_hardware_execution": False,
    }
    projection["projection_sha256"] = digest(projection)
    return projection


def _toward_zero_division(value: int, divisor: int) -> tuple[int, int]:
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    quotient, remainder = divmod(magnitude, divisor)
    return sign * quotient, sign * remainder


def _decimal_string(raw: int, scale: int, fractional_bits: int) -> str:
    with localcontext() as context:
        context.prec = max(50, len(str(abs(raw))) + fractional_bits + 8)
        value = Decimal(raw) / Decimal(scale)
        text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def fixed_point_alu(
    operation: str,
    a_raw: int,
    b_raw: int,
    *,
    accumulator_raw: int = 0,
    bits: int = 32,
    fractional_bits: int = 16,
) -> dict[str, Any]:
    """Execute a bounded signed fixed-point ALU transition.

    Multiplication and MAC use explicit toward-zero scaling.  Any discarded raw
    remainder is retained in the receipt, so transport remains lossless even
    when numeric fixed-point rounding is intentionally lossy.
    """

    bits = _require_int("bits", bits, 2, 64)
    fractional_bits = _require_int("fractional_bits", fractional_bits, 0, bits - 1)
    for name, value in (
        ("a_raw", a_raw),
        ("b_raw", b_raw),
        ("accumulator_raw", accumulator_raw),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")

    operation = str(operation).upper()
    if operation not in {"ADD", "SUB", "MUL", "MAC"}:
        raise ValueError("operation must be ADD, SUB, MUL, or MAC")

    scale = 1 << fractional_bits
    discarded_remainder = 0
    unbounded_raw: int
    if operation == "ADD":
        unbounded_raw = a_raw + b_raw
    elif operation == "SUB":
        unbounded_raw = a_raw - b_raw
    else:
        product = a_raw * b_raw
        scaled, discarded_remainder = _toward_zero_division(product, scale)
        unbounded_raw = scaled if operation == "MUL" else accumulator_raw + scaled

    minimum = -(1 << (bits - 1))
    maximum = (1 << (bits - 1)) - 1
    overflow = not minimum <= unbounded_raw <= maximum
    receipt: dict[str, Any] = {
        "schema": "qikvrt_fixed_point_alu_receipt_v1",
        "operation": operation,
        "bits": bits,
        "fractional_bits": fractional_bits,
        "scale": scale,
        "a_raw": a_raw,
        "b_raw": b_raw,
        "accumulator_raw": accumulator_raw,
        "rounding": "TOWARD_ZERO",
        "discarded_product_remainder_raw": discarded_remainder,
        "minimum_raw": minimum,
        "maximum_raw": maximum,
        "unbounded_result_raw": unbounded_raw,
        "overflow": overflow,
        "state": "HOLD" if overflow else "CONTINUE",
        "first_blocker": "FIXED_POINT_OVERFLOW" if overflow else None,
        "result_raw": None if overflow else unbounded_raw,
        "result_decimal": None
        if overflow
        else _decimal_string(unbounded_raw, scale, fractional_bits),
        "transport_lossless": True,
        "numeric_rounding_explicit": True,
        "physical_hardware_execution": False,
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def normalize_gate_state(value: Any) -> str:
    state = str(value or "NOT_OBSERVED").strip().upper()
    aliases = {
        "QUEUED": "REQUESTED",
        "PENDING": "REQUESTED",
        "IN_PROGRESS": "RUNNING",
        "COMPLETED_SUCCESS": "SUCCESS",
        "FAILURE": "HOLD",
        "FAILED": "HOLD",
        "BLOCKED": "HOLD",
        "ACTION_REQUIRED": "HOLD",
        "TIMED_OUT": "HOLD",
        "STARTUP_FAILURE": "HOLD",
        "NEUTRAL": "SKIPPED",
    }
    return aliases.get(state, state)


def classify_gate_set(
    gates: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    causal_depth: int = RETIREMENT_DEPTH,
    carrier_exists: bool = True,
) -> dict[str, Any]:
    """Classify the exact eight-gate set without surface-to-cause inflation."""

    causal_depth = _require_int("causal_depth", causal_depth, 0, 1_000_000)
    if isinstance(gates, Mapping):
        raw = {str(name): value for name, value in gates.items()}
    else:
        raw = {str(item.get("name")): item.get("state") for item in gates}

    normalized = [
        {"name": name, "state": normalize_gate_state(raw.get(name))}
        for name in GATE_NAMES
    ]
    observed = [item for item in normalized if item["state"] != "NOT_OBSERVED"]
    active = [item for item in normalized if item["state"] in ACTIVE_GATE_STATES]
    holds = [item for item in normalized if item["state"] == "HOLD"]
    unknown = [
        item
        for item in normalized
        if item["state"]
        not in ACTIVE_GATE_STATES | TERMINAL_GATE_STATES | {"NOT_OBSERVED"}
    ]

    all_observed = len(observed) == FANOUT
    all_holds = all_observed and len(holds) == FANOUT
    hold_admissible = not carrier_exists and all_holds and causal_depth >= RETIREMENT_DEPTH

    if unknown:
        state = "REOBSERVE"
        action = "REJECT_UNKNOWN_GATE_STATE"
    elif not all_observed:
        state = "REOBSERVE"
        action = "WAIT_FOR_EXACT_EIGHT_GATE_EVENT_SET"
    elif active:
        state = "CONTINUE"
        action = "FOLLOW_ACTIVE_REPOSITORY_EVENT"
    elif all_holds and causal_depth >= RETIREMENT_DEPTH:
        if carrier_exists:
            state = "RETIRE_CANDIDATE"
            action = "PREPARE_EXACT_CARRIER_RETIREMENT"
        else:
            state = "HOLD"
            action = "NO_REPOSITORY_CARRIER_REMAINS"
    elif holds:
        state = "SUCCESSOR"
        action = "ROUTE_FIRST_CAUSAL_GATE_BLOCKER"
    else:
        state = "STABLE"
        action = "AWAIT_NEXT_EVENT"

    first_blocker = holds[0]["name"] if holds else None
    receipt: dict[str, Any] = {
        "schema": "qikvrt_depth9_gate_classification_v1",
        "gate_count": FANOUT,
        "causal_depth": causal_depth,
        "retirement_depth": RETIREMENT_DEPTH,
        "carrier_exists": carrier_exists,
        "all_observed": all_observed,
        "all_holds": all_holds,
        "hold_admissible": hold_admissible,
        "state": state,
        "action": action,
        "first_blocker": first_blocker,
        "gates": normalized,
        "predecessor_evidence_transfer": False,
    }
    receipt["gate_fingerprint"] = digest(
        {
            "causal_depth": causal_depth,
            "carrier_exists": carrier_exists,
            "gates": normalized,
        }
    )
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def retirement_prepare_receipt(
    *,
    subject: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    if classification.get("state") != "RETIRE_CANDIDATE":
        raise ValueError("classification is not RETIRE_CANDIDATE")
    if classification.get("all_holds") is not True:
        raise ValueError("all eight gates must be HOLD")
    receipt: dict[str, Any] = {
        "schema": "qikvrt_depth9_retirement_prepare_v1",
        "subject": dict(subject),
        "gate_fingerprint": classification.get("gate_fingerprint"),
        "causal_depth": classification.get("causal_depth"),
        "reason": "ALL_EIGHT_GATES_HOLD_AT_DEPTH_NINE",
        "next_action": "REOBSERVE_EXACT_CARRIER_THEN_CLOSE_OR_DELETE",
        "effect_performed": False,
        "predecessor_evidence_transfer": False,
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def _demo_payload() -> dict[str, Any]:
    alu = fixed_point_alu("MAC", 384, 128, accumulator_raw=64, bits=16, fractional_bits=8)
    return {
        "kind": "FIXED_POINT_ALU",
        "description": "1.5 * 0.5 + 0.25",
        "alu": alu,
    }


def _write_json(path: Path | None, value: Any) -> None:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if path is None:
        print(text, end="")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="emit a deterministic fixed-point mesh demo")
    demo.add_argument("--depth", type=int, default=2)
    demo.add_argument("--output", type=Path)

    alu = sub.add_parser("alu", help="execute a fixed-point ALU transition")
    alu.add_argument("operation", choices=("ADD", "SUB", "MUL", "MAC"))
    alu.add_argument("a_raw", type=int)
    alu.add_argument("b_raw", type=int)
    alu.add_argument("--accumulator-raw", type=int, default=0)
    alu.add_argument("--bits", type=int, default=32)
    alu.add_argument("--fractional-bits", type=int, default=16)
    alu.add_argument("--output", type=Path)

    classify = sub.add_parser("classify", help="classify a JSON gate map")
    classify.add_argument("input", type=Path)
    classify.add_argument("--causal-depth", type=int, default=RETIREMENT_DEPTH)
    classify.add_argument("--no-carrier", action="store_true")
    classify.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    if args.command == "demo":
        subject = {
            "repository": "Goldkelch/qik-vrt",
            "kind": "demo",
            "ref": "metatransistor/fixed-point-alu",
        }
        projection = materialize_mesh(
            subject,
            _demo_payload(),
            materialized_depth=args.depth,
        )
        root = projection["nodes"][0]
        first_children = [node for node in projection["nodes"] if node["depth"] == 1]
        projection["first_level_derealization"] = derealize(root, first_children)
        _write_json(args.output, projection)
        return 0
    if args.command == "alu":
        _write_json(
            args.output,
            fixed_point_alu(
                args.operation,
                args.a_raw,
                args.b_raw,
                accumulator_raw=args.accumulator_raw,
                bits=args.bits,
                fractional_bits=args.fractional_bits,
            ),
        )
        return 0
    gates = json.loads(args.input.read_text(encoding="utf-8"))
    _write_json(
        args.output,
        classify_gate_set(
            gates,
            causal_depth=args.causal_depth,
            carrier_exists=not args.no_carrier,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
