#!/usr/bin/env python3
"""Emit and verify the proof-bound QIK-VRT Spark branch planner for M68000.

D0.b encodes eight normalized branch invariants. D0 returns one complete
bounded branch-plan id. GitHub effects remain host-owned and serially
reobserved; this kernel only selects the plan.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

PLAN_NAMES = (
    "ALREADY_COMPLETE", "HOLD_INVALID", "REBASE_TO_CLOSE",
    "REBASE_TO_AUTHORITY", "MATERIALIZE_TO_CLOSE",
    "MATERIALIZE_TO_AUTHORITY", "VERIFY_TO_CLOSE", "VERIFY_TO_AUTHORITY",
    "REPAIR_TO_CLOSE", "REPAIR_TO_AUTHORITY", "MERGE_TO_CLOSE",
    "REQUEST_AUTHORITY",
)
(
    PLAN_ALREADY_COMPLETE, PLAN_HOLD_INVALID, PLAN_REBASE_TO_CLOSE,
    PLAN_REBASE_TO_AUTHORITY, PLAN_MATERIALIZE_TO_CLOSE,
    PLAN_MATERIALIZE_TO_AUTHORITY, PLAN_VERIFY_TO_CLOSE,
    PLAN_VERIFY_TO_AUTHORITY, PLAN_REPAIR_TO_CLOSE, PLAN_REPAIR_TO_AUTHORITY,
    PLAN_MERGE_TO_CLOSE, PLAN_REQUEST_AUTHORITY,
) = range(12)

FLAG_MALFORMED = 1 << 0
FLAG_MAIN_EFFECT = 1 << 1
FLAG_BASE_CURRENT = 1 << 2
FLAG_INTEGRITY_CURRENT = 1 << 3
FLAG_GATES_TERMINAL = 1 << 4
FLAG_GATES_NON_ADVERSE = 1 << 5
FLAG_MERGEABLE = 1 << 6
FLAG_AUTHORITY_AVAILABLE = 1 << 7

MACHINE_HEX = (
    "08000000670470014e7508000001670470004e7508000002660e080000076704"
    "70024e7570034e7508000003660e08000007670470044e7570054e7508000004"
    "660e08000007670470064e7570074e7508000005660e08000007670470084e75"
    "70094e7508000006660e08000007670470084e7570094e75080000076704700a"
    "4e75700b4e75"
)


def compile_kernel() -> bytes:
    """Deterministically emit the reviewed assembler artifact."""
    return bytes.fromhex(MACHINE_HEX)


MACHINE = compile_kernel()


def reference_plan(flags: int) -> int:
    if not 0 <= flags <= 255:
        raise ValueError("flags outside byte")
    authority = bool(flags & FLAG_AUTHORITY_AVAILABLE)
    if flags & FLAG_MALFORMED:
        return PLAN_HOLD_INVALID
    if flags & FLAG_MAIN_EFFECT:
        return PLAN_ALREADY_COMPLETE
    pairs = (
        (FLAG_BASE_CURRENT, PLAN_REBASE_TO_CLOSE, PLAN_REBASE_TO_AUTHORITY),
        (FLAG_INTEGRITY_CURRENT, PLAN_MATERIALIZE_TO_CLOSE,
         PLAN_MATERIALIZE_TO_AUTHORITY),
        (FLAG_GATES_TERMINAL, PLAN_VERIFY_TO_CLOSE, PLAN_VERIFY_TO_AUTHORITY),
        (FLAG_GATES_NON_ADVERSE, PLAN_REPAIR_TO_CLOSE, PLAN_REPAIR_TO_AUTHORITY),
        (FLAG_MERGEABLE, PLAN_REPAIR_TO_CLOSE, PLAN_REPAIR_TO_AUTHORITY),
    )
    for bit, close_plan, authority_plan in pairs:
        if not flags & bit:
            return close_plan if authority else authority_plan
    return PLAN_MERGE_TO_CLOSE if authority else PLAN_REQUEST_AUTHORITY


def execute_kernel(code: bytes, d0: int) -> tuple[int, int]:
    pc, z, count = 0, False, 0
    d0 &= 0xFFFFFFFF
    while True:
        if pc + 2 > len(code):
            raise RuntimeError("truncated Spark kernel")
        op = int.from_bytes(code[pc:pc + 2], "big")
        count += 1
        if op == 0x0800:  # BTST #imm,D0
            if pc + 4 > len(code):
                raise RuntimeError("truncated BTST")
            bit = int.from_bytes(code[pc + 2:pc + 4], "big")
            if bit > 31:
                raise RuntimeError("invalid BTST bit")
            z = ((d0 >> bit) & 1) == 0
            pc += 4
        elif op & 0xFF00 in {0x6600, 0x6700}:  # BNE.s / BEQ.s
            disp = op & 0xFF
            if disp == 0:
                raise RuntimeError("word branch outside bounded kernel")
            if disp & 0x80:
                disp -= 0x100
            take = (not z) if op & 0xFF00 == 0x6600 else z
            pc = pc + 2 + disp if take else pc + 2
        elif op & 0xF100 == 0x7000:  # MOVEQ #imm,D0
            d0 = op & 0xFF
            pc += 2
        elif op == 0x4E75:  # RTS
            return d0, count
        else:
            raise RuntimeError(f"unsupported opcode 0x{op:04x} at {pc}")


def verify_exhaustive(code: bytes = MACHINE) -> dict[str, object]:
    population = {name: 0 for name in PLAN_NAMES}
    maximum = 0
    for flags in range(256):
        actual, count = execute_kernel(code, flags)
        expected = reference_plan(flags)
        if actual != expected:
            raise AssertionError((flags, expected, actual))
        population[PLAN_NAMES[actual]] += 1
        maximum = max(maximum, count)
        authority = bool(flags & FLAG_AUTHORITY_AVAILABLE)
        if actual in {2, 4, 6, 8, 10} and not authority:
            raise AssertionError(("merge plan without authority", flags, actual))
        if actual == PLAN_ALREADY_COMPLETE and not flags & FLAG_MAIN_EFFECT:
            raise AssertionError(("completion without main effect", flags))
        if flags & FLAG_MALFORMED and actual != PLAN_HOLD_INVALID:
            raise AssertionError(("malformed did not hold", flags))
    return {
        "schema": "QIKVRT_SPARK_BRANCH_M68000_COMPILER_V1",
        "machine_bytes": len(code), "machine_hex": code.hex(),
        "verified_flag_bytes": 256, "plan_codes_observed": list(range(12)),
        "plan_population": {k: v for k, v in population.items() if v},
        "max_dynamic_instructions": maximum,
        "merge_plan_without_authority": 0,
        "completion_without_main_effect": 0,
        "malformed_input_without_hold": 0,
        "physical_m68000_execution_observed": False,
        "physical_speedup_measured": False,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-hex", type=Path)
    parser.add_argument("--emit-hex", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = verify_exhaustive()
    if args.output_hex:
        args.output_hex.parent.mkdir(parents=True, exist_ok=True)
        args.output_hex.write_text(MACHINE.hex() + "\n", encoding="ascii")
    if args.emit_hex:
        print(MACHINE.hex())
    if args.json or not (args.output_hex or args.emit_hex):
        print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
