#!/usr/bin/env python3
"""Deterministically lower the Lean-proved finite QIK-VRT gate projection.

ABI v1
======
Input D0 bit 0: PASS certificate present
Input D0 bit 1: BLOCK certificate present
Output D0: 0=CONTINUE, 1=PASS, 2=BLOCK

The generated Motorola 68000 program implements the same priority proved in
QIKVRTFormalization/M68000Kernel.lean: BLOCK > PASS > CONTINUE.

This is a source/compiler/reference-interpreter proof path.  It does not claim
that the emitted bytes have executed on physical M68000 hardware.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

GATE_CONTINUE = 0
GATE_PASS = 1
GATE_BLOCK = 2

ASM_TEXT = """; QIK-VRT Lean-proved finite gate kernel — Motorola 68000
; ABI: D0 bit0=pass certificate, bit1=block certificate
; OUT: D0=0 CONTINUE, D0=1 PASS, D0=2 BLOCK
; BLOCK has priority over PASS, matching evaluateGate.

        btst    #1,d0
        beq.s   .no_block
        moveq   #2,d0
        rts
.no_block:
        btst    #0,d0
        beq.s   .continue
        moveq   #1,d0
        rts
.continue:
        moveq   #0,d0
        rts
"""


def _word(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(value)
    return bytes([(value >> 8) & 0xFF, value & 0xFF])


@dataclass(frozen=True)
class Label:
    name: str


@dataclass(frozen=True)
class Op:
    kind: str
    args: tuple


def _program() -> list[Label | Op]:
    return [
        Op("btst", (1, 0)),
        Op("beq", ("no_block",)),
        Op("moveq", (2, 0)),
        Op("rts", ()),
        Label("no_block"),
        Op("btst", (0, 0)),
        Op("beq", ("continue",)),
        Op("moveq", (1, 0)),
        Op("rts", ()),
        Label("continue"),
        Op("moveq", (0, 0)),
        Op("rts", ()),
    ]


def _size(op: Op) -> int:
    return {"btst": 4, "beq": 2, "moveq": 2, "rts": 2}[op.kind]


def compile_kernel() -> bytes:
    program = _program()
    labels: dict[str, int] = {}
    pc = 0
    for item in program:
        if isinstance(item, Label):
            if item.name in labels:
                raise ValueError(f"duplicate label: {item.name}")
            labels[item.name] = pc
        else:
            pc += _size(item)

    out = bytearray()
    pc = 0
    for item in program:
        if isinstance(item, Label):
            continue
        if item.kind == "btst":
            bit, dn = item.args
            if not (0 <= bit <= 31 and 0 <= dn <= 7):
                raise ValueError(item)
            out += _word(0x0800 | dn)
            out += _word(bit)
        elif item.kind == "beq":
            (target,) = item.args
            displacement = labels[target] - (pc + 2)
            if not -128 <= displacement <= 127 or displacement == 0:
                raise ValueError(f"short branch displacement out of range: {displacement}")
            out += _word(0x6700 | (displacement & 0xFF))
        elif item.kind == "moveq":
            imm, dn = item.args
            if not (-128 <= imm <= 127 and 0 <= dn <= 7):
                raise ValueError(item)
            out += _word(0x7000 | (dn << 9) | (imm & 0xFF))
        elif item.kind == "rts":
            out += _word(0x4E75)
        else:
            raise ValueError(item.kind)
        pc += _size(item)
    return bytes(out)


def reference_gate(flags: int) -> int:
    if flags & 0b10:
        return GATE_BLOCK
    if flags & 0b01:
        return GATE_PASS
    return GATE_CONTINUE


def execute_kernel(code: bytes, d0: int) -> tuple[int, int]:
    """Execute only the emitted bounded instruction subset.

    Returns (D0, dynamic_instruction_count). Unknown/truncated opcodes fail
    closed instead of being interpreted permissively.
    """
    pc = 0
    instructions = 0
    d = [0] * 8
    d[0] = d0 & 0xFFFFFFFF
    z = False
    while True:
        if pc + 2 > len(code):
            raise RuntimeError("truncated program")
        op = (code[pc] << 8) | code[pc + 1]
        instructions += 1
        if (op & 0xFFF8) == 0x0800:  # BTST #imm,Dn
            dn = op & 7
            if pc + 4 > len(code):
                raise RuntimeError("truncated BTST")
            bit = (code[pc + 2] << 8) | code[pc + 3]
            if bit > 31:
                raise RuntimeError("invalid BTST bit")
            z = ((d[dn] >> bit) & 1) == 0
            pc += 4
        elif (op & 0xFF00) == 0x6700:  # BEQ.s
            disp = op & 0xFF
            if disp == 0:
                raise RuntimeError("word-displacement BEQ not in bounded kernel")
            if disp & 0x80:
                disp -= 0x100
            pc = pc + 2 + disp if z else pc + 2
        elif (op & 0xF100) == 0x7000:  # MOVEQ #imm,Dn
            dn = (op >> 9) & 7
            imm = op & 0xFF
            if imm & 0x80:
                imm -= 0x100
            d[dn] = imm & 0xFFFFFFFF
            pc += 2
        elif op == 0x4E75:  # RTS
            return d[0], instructions
        else:
            raise RuntimeError(f"unsupported opcode 0x{op:04x} at {pc}")


def verify_exhaustive(code: bytes) -> dict:
    paths: dict[int, int] = {}
    for flags in range(256):
        actual, count = execute_kernel(code, flags)
        expected = reference_gate(flags)
        if actual != expected:
            raise AssertionError((flags, expected, actual))
        paths[flags & 3] = count
    return {
        "verified_inputs": 256,
        "machine_bytes": len(code),
        "machine_hex": code.hex(),
        "dynamic_instructions_by_low2": {str(k): paths[k] for k in sorted(paths)},
        "max_dynamic_instructions": max(paths.values()),
        "physical_m68000_execution_observed": False,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-hex", action="store_true")
    parser.add_argument("--emit-asm", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    code = compile_kernel()
    report = verify_exhaustive(code)
    if args.emit_asm:
        print(ASM_TEXT, end="")
    if args.emit_hex:
        print(code.hex())
    if args.verify or args.json:
        print(json.dumps(report, sort_keys=True, indent=2 if args.json else None))
    if not any((args.emit_asm, args.emit_hex, args.verify, args.json)):
        print(code.hex())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
