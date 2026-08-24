#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify the Karlsruhe-to-cloud email contract and finite M68000 route core.

The microkernel selects one bounded route disposition. It never opens a socket,
reads credentials, changes DNS, submits SMTP, writes a mailbox, or claims an
external Effect Acknowledgement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/QIKVRT_EMAIL_INFRASTRUCTURE_V1.json"
RUNTIME = ROOT / "runtime/email/QIKVRT_EMAIL_INFRASTRUCTURE_V1.json"
HEX_PATH = ROOT / "runtime/m68000/qikvrt_email_route_select.hex"

COMPLETE = 0
HOLD = 1
REOBSERVE = 2
REQUEST_AUTHORITY = 3

EXPECTED_HEX = (
    "08000000672c08000005662e08000006670608000007672a"
    "08000001671c08000002670e0800000367080800000467026018"
    "7001720074004e757002720074014e757003720074004e75"
    "7000720174004e75"
)
DECISIONS = {
    COMPLETE: "COMPLETE_ACCEPT_ROUTE",
    HOLD: "HOLD",
    REOBSERVE: "REOBSERVE_RETRY",
    REQUEST_AUTHORITY: "REQUEST_AUTHORITY",
}

PROGRAM: tuple[tuple[Any, ...], ...] = (
    ("btst", 0, 0), ("beq", "hold"),
    ("btst", 5, 0), ("bne", "reobserve"),
    ("btst", 6, 0), ("beq", "route"),
    ("btst", 7, 0), ("beq", "request_authority"),
    ("label", "route"),
    ("btst", 1, 0), ("beq", "reobserve"),
    ("btst", 2, 0), ("beq", "hold"),
    ("btst", 3, 0), ("beq", "hold"),
    ("btst", 4, 0), ("beq", "hold"),
    ("bra", "complete"),
    ("label", "hold"),
    ("moveq", HOLD, 0), ("moveq", 0, 1), ("moveq", 0, 2), ("rts",),
    ("label", "reobserve"),
    ("moveq", REOBSERVE, 0), ("moveq", 0, 1), ("moveq", 1, 2), ("rts",),
    ("label", "request_authority"),
    ("moveq", REQUEST_AUTHORITY, 0), ("moveq", 0, 1), ("moveq", 0, 2), ("rts",),
    ("label", "complete"),
    ("moveq", COMPLETE, 0), ("moveq", 1, 1), ("moveq", 0, 2), ("rts",),
)


def _word(value: int) -> bytes:
    return value.to_bytes(2, "big", signed=False)


def _size(op: tuple[Any, ...]) -> int:
    return {
        "label": 0,
        "btst": 4,
        "beq": 2,
        "bne": 2,
        "bra": 2,
        "moveq": 2,
        "rts": 2,
    }[op[0]]


def compile_kernel() -> bytes:
    labels: dict[str, int] = {}
    pc = 0
    for op in PROGRAM:
        if op[0] == "label":
            name = str(op[1])
            if name in labels:
                raise ValueError(f"duplicate label: {name}")
            labels[name] = pc
        else:
            pc += _size(op)

    out = bytearray()
    pc = 0
    branches = {"bra": 0x6000, "bne": 0x6600, "beq": 0x6700}
    for op in PROGRAM:
        kind = str(op[0])
        if kind == "label":
            continue
        if kind == "btst":
            bit, dn = int(op[1]), int(op[2])
            if not (0 <= bit <= 31 and 0 <= dn <= 7):
                raise ValueError(op)
            out += _word(0x0800 | dn)
            out += _word(bit)
        elif kind in branches:
            target = str(op[1])
            displacement = labels[target] - (pc + 2)
            if displacement == 0 or not -128 <= displacement <= 127:
                raise ValueError((op, displacement))
            out += _word(branches[kind] | (displacement & 0xFF))
        elif kind == "moveq":
            value, dn = int(op[1]), int(op[2])
            if not (-128 <= value <= 127 and 0 <= dn <= 7):
                raise ValueError(op)
            out += _word(0x7000 | (dn << 9) | (value & 0xFF))
        elif kind == "rts":
            out += _word(0x4E75)
        else:
            raise ValueError(kind)
        pc += _size(op)

    code = bytes(out)
    if code.hex() != EXPECTED_HEX:
        raise AssertionError((EXPECTED_HEX, code.hex()))
    return code


MACHINE = compile_kernel()


def reference(flags: int, d3: int) -> tuple[int, int, int, int]:
    flags &= 0xFF
    d3 &= 0xFF
    if not flags & 0x01:
        return HOLD, 0, 0, d3
    if flags & 0x20:
        return REOBSERVE, 0, 1, d3
    if flags & 0x40 and not flags & 0x80:
        return REQUEST_AUTHORITY, 0, 0, d3
    if not flags & 0x02:
        return REOBSERVE, 0, 1, d3
    if flags & 0x1C != 0x1C:
        return HOLD, 0, 0, d3
    return COMPLETE, 1, 0, d3


def execute(code: bytes, flags: int, d3: int) -> tuple[int, int, int, int, int]:
    regs = [0] * 8
    regs[0] = flags & 0xFFFFFFFF
    regs[3] = d3 & 0xFFFFFFFF
    pc = 0
    zero = False
    count = 0
    while True:
        if pc + 2 > len(code):
            raise RuntimeError("truncated kernel")
        word = int.from_bytes(code[pc:pc + 2], "big")
        count += 1
        if word & 0xFFF8 == 0x0800:
            if pc + 4 > len(code):
                raise RuntimeError("truncated BTST")
            dn = word & 7
            bit = int.from_bytes(code[pc + 2:pc + 4], "big")
            zero = ((regs[dn] >> bit) & 1) == 0
            pc += 4
        elif word & 0xFF00 in (0x6000, 0x6600, 0x6700):
            kind = word & 0xFF00
            disp = word & 0xFF
            if disp == 0:
                raise RuntimeError("word branch forbidden")
            if disp & 0x80:
                disp -= 0x100
            take = (
                kind == 0x6000
                or (kind == 0x6600 and not zero)
                or (kind == 0x6700 and zero)
            )
            pc = pc + 2 + disp if take else pc + 2
        elif word & 0xF100 == 0x7000:
            dn = (word >> 9) & 7
            value = word & 0xFF
            if value & 0x80:
                value -= 0x100
            regs[dn] = value & 0xFFFFFFFF
            pc += 2
        elif word == 0x4E75:
            return regs[0], regs[1], regs[2], regs[3], count
        else:
            raise RuntimeError(f"unsupported opcode 0x{word:04x} at {pc}")


def verify_exhaustive(code: bytes = MACHINE) -> dict[str, Any]:
    counts = {str(value): 0 for value in DECISIONS}
    maximum = 0
    checked = 0
    for flags in range(256):
        for d3 in range(256):
            actual = execute(code, flags, d3)
            expected = reference(flags, d3)
            if actual[:4] != expected:
                raise AssertionError((flags, d3, expected, actual))
            if actual[3] != d3:
                raise AssertionError(("D3_MUTATED", flags, d3, actual))
            counts[str(actual[0])] += 1
            maximum = max(maximum, actual[4])
            checked += 1
    return {
        "schema": "qikvrt_email_m68000_verification_receipt_v1",
        "kernel_id": "email_route_select_v1",
        "machine_bytes": len(code),
        "machine_hex": code.hex(),
        "machine_sha256": hashlib.sha256(code).hexdigest(),
        "input_pairs_verified": checked,
        "flag_values_verified": 256,
        "d3_values_verified": 256,
        "max_dynamic_instructions": maximum,
        "decision_counts": counts,
        "d3_preserved": True,
        "virtual_m68000_execution_observed": True,
        "physical_m68000_execution_observed": False,
        "network_effect": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def validate_contract() -> dict[str, Any]:
    policy = load_json(POLICY)
    runtime = load_json(RUNTIME)
    if policy.get("schema") != "qikvrt_email_infrastructure_policy_v1":
        raise ValueError("policy schema mismatch")
    if runtime.get("schema") != "qikvrt_email_runtime_registry_v1":
        raise ValueError("runtime schema mismatch")
    if policy["historical_anchor"]["id"] != "KARLSRUHE_CSNET_1984":
        raise ValueError("historical anchor mismatch")
    if len(policy["layers"]) != 18:
        raise ValueError("mail layer count mismatch")
    if len(policy["standards"]) < 24:
        raise ValueError("standards inventory incomplete")
    if len(policy["cloud_variants"]) < 16:
        raise ValueError("cloud variant inventory incomplete")
    event = policy["event_model"]
    if event["normal_operation"] != "EVENT_DRIVEN_ONLY":
        raise ValueError("regular operation is not event driven")
    if event["polling"] != "FORBIDDEN_AS_REGULAR_DOMAIN_WORK_MODE":
        raise ValueError("polling boundary mismatch")
    if event["append_only_receipts"] is not True:
        raise ValueError("append-only receipt boundary missing")
    if runtime["external_effect"] != "NONE":
        raise ValueError("runtime external effect boundary mismatch")
    persisted = bytes.fromhex(HEX_PATH.read_text(encoding="utf-8").strip())
    if persisted != MACHINE:
        raise ValueError("persisted machine bytes differ from deterministic compiler")
    return {
        "policy_schema": policy["schema"],
        "runtime_schema": runtime["schema"],
        "historical_anchor": policy["historical_anchor"]["id"],
        "layer_count": len(policy["layers"]),
        "standard_count": len(policy["standards"]),
        "cloud_variant_count": len(policy["cloud_variants"]),
        "event_driven_only": True,
        "append_only_receipts": True,
    }


def route_receipt(flags: int, d3: int, message_id: str = "") -> dict[str, Any]:
    d0, d1, d2, d3_out, instructions = execute(MACHINE, flags, d3)
    return {
        "schema": "qikvrt_email_route_receipt_v1",
        "message_id_sha256": hashlib.sha256(message_id.encode("utf-8")).hexdigest(),
        "flags": flags & 0xFF,
        "decision_code": d0,
        "decision": DECISIONS[d0],
        "completion_witness": d1,
        "machine_owned_reobservation": d2,
        "d3_before": d3 & 0xFF,
        "d3_after": d3_out,
        "dynamic_instructions": instructions,
        "message_content_persisted": False,
        "credential_accessed": False,
        "dns_changed": False,
        "mail_sent_or_received": False,
        "network_effect": False,
        "effect_ack_done": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--output")
    route = commands.add_parser("route")
    route.add_argument("--flags", type=lambda raw: int(raw, 0), required=True)
    route.add_argument("--d3", type=lambda raw: int(raw, 0), default=0)
    route.add_argument("--message-id", default="")
    args = parser.parse_args()

    if args.command == "verify":
        report = {
            "schema": "qikvrt_email_infrastructure_verification_v1",
            "contract": validate_contract(),
            "machine": verify_exhaustive(),
            "external_effect": "NONE",
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        }
    else:
        report = route_receipt(args.flags, args.d3, args.message_id)

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output = getattr(args, "output", None)
    if output:
        Path(output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
