#!/usr/bin/env python3
"""Compile the frozen Lean-v2 Authority/Mirror recoveryChoice to M68000.

Input D0 low byte = CutPoint code:
0 beforePrepare, 1 authorityPrepared, 2 mirrorPrepared, 3 crossVerified,
4 witnessCommitted, 5 authorityAcked, 6 mirrorAcked.

Output D0:
0 predecessor, 1 successor, 2 hold.

The valid-domain truth table is exactly the frozen Lean `recoveryChoice` rule.
Invalid byte values fail closed to HOLD. No physical M68000 execution is claimed.
"""
from __future__ import annotations

import json

PRED = 0
SUCC = 1
HOLD = 2

# CMPI.B #6,D0; BHI.s invalid; CMPI.B #4,D0; BCC.s successor;
# MOVEQ #0,D0; RTS; successor: MOVEQ #1,D0; RTS;
# invalid: MOVEQ #2,D0; RTS
MACHINE = bytes.fromhex("0c000006620e0c000004640470004e7570014e7570024e75")


def lean_reference(cutpoint: int) -> int:
    if not 0 <= cutpoint <= 6:
        raise ValueError("CutPoint outside finite Lean domain")
    return PRED if cutpoint <= 3 else SUCC


def execute(code: bytes, d0: int) -> tuple[int, int]:
    pc = 0
    d0 &= 0xFFFFFFFF
    z = False
    c = False
    count = 0
    while True:
        if pc + 2 > len(code):
            raise RuntimeError("truncated program")
        op = int.from_bytes(code[pc:pc+2], "big")
        count += 1
        if op == 0x0C00:  # CMPI.B #imm,D0
            if pc + 4 > len(code):
                raise RuntimeError("truncated CMPI")
            imm = int.from_bytes(code[pc+2:pc+4], "big") & 0xFF
            value = d0 & 0xFF
            z = value == imm
            c = value < imm
            pc += 4
        elif (op & 0xFF00) == 0x6200:  # BHI.s
            disp = op & 0xFF
            if disp & 0x80:
                disp -= 0x100
            pc = pc + 2 + disp if (not c and not z) else pc + 2
        elif (op & 0xFF00) == 0x6400:  # BCC.s
            disp = op & 0xFF
            if disp & 0x80:
                disp -= 0x100
            pc = pc + 2 + disp if not c else pc + 2
        elif (op & 0xF100) == 0x7000:  # MOVEQ #imm,Dn; kernel uses D0 only
            dn = (op >> 9) & 7
            if dn != 0:
                raise RuntimeError("unexpected destination register")
            imm = op & 0xFF
            if imm & 0x80:
                imm -= 0x100
            d0 = imm & 0xFFFFFFFF
            pc += 2
        elif op == 0x4E75:
            return d0, count
        else:
            raise RuntimeError(f"unsupported opcode 0x{op:04x} at {pc}")


def verify() -> dict:
    valid = 0
    invalid = 0
    max_count = 0
    for cutpoint in range(7):
        actual, count = execute(MACHINE, cutpoint)
        expected = lean_reference(cutpoint)
        if actual != expected:
            raise AssertionError((cutpoint, expected, actual))
        valid += 1
        max_count = max(max_count, count)
    for cutpoint in range(7, 256):
        actual, count = execute(MACHINE, cutpoint)
        if actual != HOLD:
            raise AssertionError((cutpoint, HOLD, actual))
        invalid += 1
        max_count = max(max_count, count)
    return {
        "valid_cutpoints_verified": valid,
        "invalid_cutpoints_fail_closed": invalid,
        "machine_bytes": len(MACHINE),
        "machine_hex": MACHINE.hex(),
        "max_dynamic_instructions": max_count,
        "physical_m68000_execution_observed": False,
        "physical_speedup_measured": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True, indent=2))
