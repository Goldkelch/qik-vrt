#!/usr/bin/env python3
"""Compile the Lean-v2 finite D0/D2/D3 projection to Motorola 68000 bytes.

Runtime ABI:
- D0 contains an already validated QIK-VRT decision code 0..3 and is preserved.
- D2 contains the IED phase code 0=INTELLIGENCE, 1=EVIDENCE, 2=DEVELOPMENT.
- D3 contains the stable 8-bit semantic witness and is never written.
- valid D2 advances modulo three; invalid D2 fails closed by returning D0=1 HOLD.

The formal refinement claim covers valid finite-domain inputs. The invalid-D2
HOLD branch is an implementation safety extension, not a strengthening of the
Lean physical or authority claims.
"""
from __future__ import annotations

import json

# CMPI.B #2,D2; BHI.s invalid; BEQ.s wrap; ADDQ.B #1,D2; RTS;
# wrap: MOVEQ #0,D2; RTS; invalid: MOVEQ #1,D0; RTS
MACHINE = bytes.fromhex("0c020002620a670452024e7574004e7570014e75")


def formal_projection(d0: int, d2: int, d3: int) -> tuple[int, int, int]:
    if not 0 <= d0 <= 3:
        raise ValueError("decision outside Fin 4")
    if not 0 <= d2 <= 2:
        raise ValueError("phase outside Fin 3")
    if not 0 <= d3 <= 255:
        raise ValueError("D3 outside Byte")
    return d0, (d2 + 1) % 3, d3


def execute(code: bytes, d0: int, d2: int, d3: int) -> tuple[int, int, int, int]:
    regs = [0] * 8
    regs[0], regs[2], regs[3] = d0 & 0xFFFFFFFF, d2 & 0xFFFFFFFF, d3 & 0xFFFFFFFF
    pc = 0
    z = False
    c = False
    count = 0
    while True:
        if pc + 2 > len(code):
            raise RuntimeError("truncated program")
        op = int.from_bytes(code[pc:pc+2], "big")
        count += 1
        if (op & 0xFFF8) == 0x0C00:  # CMPI.B #imm,Dn
            if pc + 4 > len(code):
                raise RuntimeError("truncated CMPI")
            dn = op & 7
            imm = int.from_bytes(code[pc+2:pc+4], "big") & 0xFF
            value = regs[dn] & 0xFF
            z = value == imm
            c = value < imm
            pc += 4
        elif (op & 0xFF00) == 0x6200:  # BHI.s = !C && !Z
            disp = op & 0xFF
            if disp & 0x80:
                disp -= 0x100
            pc = pc + 2 + disp if (not c and not z) else pc + 2
        elif (op & 0xFF00) == 0x6700:  # BEQ.s
            disp = op & 0xFF
            if disp & 0x80:
                disp -= 0x100
            pc = pc + 2 + disp if z else pc + 2
        elif (op & 0xF1F8) == 0x5000:  # ADDQ.B #n,Dn, n=8 encodes 8
            data = (op >> 9) & 7
            amount = 8 if data == 0 else data
            dn = op & 7
            regs[dn] = (regs[dn] & ~0xFF) | (((regs[dn] & 0xFF) + amount) & 0xFF)
            pc += 2
        elif (op & 0xF100) == 0x7000:  # MOVEQ #imm,Dn
            dn = (op >> 9) & 7
            imm = op & 0xFF
            if imm & 0x80:
                imm -= 0x100
            regs[dn] = imm & 0xFFFFFFFF
            pc += 2
        elif op == 0x4E75:
            return regs[0], regs[2], regs[3], count
        else:
            raise RuntimeError(f"unsupported opcode 0x{op:04x} at {pc}")


def verify() -> dict:
    max_count = 0
    checked = 0
    for d0 in range(4):
        for d2 in range(3):
            for d3 in range(256):
                actual = execute(MACHINE, d0, d2, d3)
                expected = formal_projection(d0, d2, d3)
                if actual[:3] != expected:
                    raise AssertionError((d0, d2, d3, expected, actual))
                max_count = max(max_count, actual[3])
                checked += 1
    for invalid_phase in range(3, 256):
        d0, _d2, d3, count = execute(MACHINE, 0, invalid_phase, 0xA5)
        if d0 != 1 or d3 != 0xA5:
            raise AssertionError((invalid_phase, d0, d3))
        max_count = max(max_count, count)
    return {
        "valid_state_tuples_verified": checked,
        "valid_state_tuples_expected": 4 * 3 * 256,
        "invalid_phase_values_fail_closed": 253,
        "machine_bytes": len(MACHINE),
        "machine_hex": MACHINE.hex(),
        "max_dynamic_instructions": max_count,
        "d3_preserved": True,
        "physical_m68000_execution_observed": False,
        "physical_speedup_measured": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True, indent=2))
