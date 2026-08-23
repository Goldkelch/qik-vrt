#!/usr/bin/env python3
"""Compile and verify the bounded QIK-VRT Spark branch-pass microkernel.

ABI V1
======
D0.L input  : thirteen-bit branch-work descriptor (0x0000..0x1fff)
D1.L output : 0 IDLE, 1 ACTIVE, 2 HOLD, 3 COMPLETE
D3.B in/out : 0 QUIESCENT, 1 ACTIVE; every other value fails closed

The microkernel classifies one already-materialized bounded work descriptor.
It does not perform a Git merge, network effect, review, or arbitrary branch
implementation in a single CPU call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

IDLE = 0
ACTIVE = 1
HOLD = 2
COMPLETE = 3
FULL_MASK = 0x00001FFF

REQUIRED_PREDICATES = (
    "PROBLEM_BOUND",
    "MODEL_BOUND",
    "EXPLICIT_DISTINCTIONS_BOUND",
    "INVARIANTS_BOUND",
    "ARCHITECTURE_BOUND",
    "IMPLEMENTATION_PRESENT",
    "EXECUTION_OBSERVED",
    "OBSERVATION_ADMITTED",
    "VERIFICATION_SUCCESS",
    "RESULT_COLLECTED",
    "RESULT_PERSISTED",
    "UNNEEDED_RESOURCES_RELEASED",
    "NEXT_STATE_REOBSERVED",
)

RING_LADDER = (
    "0",
    "1",
    "2",
    "2^3=8 bits",
    "2^8=256 byte states",
    "256-bit explicit virtual ring",
    "2^(256^3) symbolic state cardinality",
)

ASM_TEXT = """; QIK-VRT Spark circular branch-pass — Motorola 68000
; D0.L = bounded completion descriptor, valid range 0..$1fff
; D1.L = 0 IDLE, 1 ACTIVE, 2 HOLD, 3 COMPLETE
; D3.B = 0 QUIESCENT, 1 ACTIVE

        cmpi.b  #1,d3
        bhi.s   .hold
        cmpi.l  #$00001fff,d0
        bhi.s   .hold
        beq.s   .complete
        tst.l   d0
        bne.s   .active
        tst.b   d3
        beq.s   .idle
.active:
        moveq   #1,d3
        moveq   #1,d1
        rts
.complete:
        moveq   #0,d3
        moveq   #3,d1
        rts
.idle:
        moveq   #0,d1
        rts
.hold:
        moveq   #2,d1
        rts
"""


@dataclass(frozen=True)
class Label:
    name: str


@dataclass(frozen=True)
class Op:
    kind: str
    args: tuple[object, ...]


def _word(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(value)
    return value.to_bytes(2, "big")


def _long(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(value)
    return value.to_bytes(4, "big")


def _program() -> list[Label | Op]:
    return [
        Op("cmpi_b", (1, 3)),
        Op("bhi", ("hold",)),
        Op("cmpi_l", (FULL_MASK, 0)),
        Op("bhi", ("hold",)),
        Op("beq", ("complete",)),
        Op("tst_l", (0,)),
        Op("bne", ("active",)),
        Op("tst_b", (3,)),
        Op("beq", ("idle",)),
        Label("active"),
        Op("moveq", (1, 3)),
        Op("moveq", (ACTIVE, 1)),
        Op("rts", ()),
        Label("complete"),
        Op("moveq", (0, 3)),
        Op("moveq", (COMPLETE, 1)),
        Op("rts", ()),
        Label("idle"),
        Op("moveq", (IDLE, 1)),
        Op("rts", ()),
        Label("hold"),
        Op("moveq", (HOLD, 1)),
        Op("rts", ()),
    ]


def _size(op: Op) -> int:
    return {
        "cmpi_b": 4,
        "cmpi_l": 6,
        "bhi": 2,
        "beq": 2,
        "bne": 2,
        "tst_l": 2,
        "tst_b": 2,
        "moveq": 2,
        "rts": 2,
    }[op.kind]


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
        if item.kind == "cmpi_b":
            imm, dn = item.args
            if not (isinstance(imm, int) and isinstance(dn, int) and 0 <= imm <= 0xFF and 0 <= dn <= 7):
                raise ValueError(item)
            out += _word(0x0C00 | dn)
            out += _word(imm)
        elif item.kind == "cmpi_l":
            imm, dn = item.args
            if not (isinstance(imm, int) and isinstance(dn, int) and 0 <= imm <= 0xFFFFFFFF and 0 <= dn <= 7):
                raise ValueError(item)
            out += _word(0x0C80 | dn)
            out += _long(imm)
        elif item.kind in {"bhi", "beq", "bne"}:
            (target,) = item.args
            if not isinstance(target, str):
                raise ValueError(item)
            displacement = labels[target] - (pc + 2)
            if not -128 <= displacement <= 127 or displacement == 0:
                raise ValueError(f"short branch displacement out of range: {displacement}")
            base = {"bhi": 0x6200, "beq": 0x6700, "bne": 0x6600}[item.kind]
            out += _word(base | (displacement & 0xFF))
        elif item.kind == "tst_l":
            (dn,) = item.args
            if not isinstance(dn, int) or not 0 <= dn <= 7:
                raise ValueError(item)
            out += _word(0x4A80 | dn)
        elif item.kind == "tst_b":
            (dn,) = item.args
            if not isinstance(dn, int) or not 0 <= dn <= 7:
                raise ValueError(item)
            out += _word(0x4A00 | dn)
        elif item.kind == "moveq":
            imm, dn = item.args
            if not (isinstance(imm, int) and isinstance(dn, int) and -128 <= imm <= 127 and 0 <= dn <= 7):
                raise ValueError(item)
            out += _word(0x7000 | (dn << 9) | (imm & 0xFF))
        elif item.kind == "rts":
            out += _word(0x4E75)
        else:
            raise ValueError(item.kind)
        pc += _size(item)
    return bytes(out)


def reference_branch_pass(mask: int, d3: int) -> tuple[int, int]:
    if not 0 <= mask <= 0xFFFFFFFF:
        raise ValueError("D0 outside 32-bit register domain")
    if not 0 <= d3 <= 0xFF:
        raise ValueError("D3 outside byte domain")
    if d3 > 1 or mask > FULL_MASK:
        return HOLD, d3
    if mask == FULL_MASK:
        return COMPLETE, 0
    if mask == 0 and d3 == 0:
        return IDLE, 0
    return ACTIVE, 1


def execute_kernel(code: bytes, mask: int, d3: int) -> tuple[int, int, int, int]:
    regs = [0] * 8
    regs[0] = mask & 0xFFFFFFFF
    regs[3] = d3 & 0xFFFFFFFF
    pc = 0
    z = False
    c = False
    count = 0
    while True:
        if pc + 2 > len(code):
            raise RuntimeError("truncated program")
        op = int.from_bytes(code[pc:pc + 2], "big")
        count += 1
        if (op & 0xFFF8) == 0x0C00:  # CMPI.B #imm,Dn
            if pc + 4 > len(code):
                raise RuntimeError("truncated CMPI.B")
            dn = op & 7
            imm = int.from_bytes(code[pc + 2:pc + 4], "big") & 0xFF
            value = regs[dn] & 0xFF
            z = value == imm
            c = value < imm
            pc += 4
        elif (op & 0xFFF8) == 0x0C80:  # CMPI.L #imm,Dn
            if pc + 6 > len(code):
                raise RuntimeError("truncated CMPI.L")
            dn = op & 7
            imm = int.from_bytes(code[pc + 2:pc + 6], "big")
            value = regs[dn] & 0xFFFFFFFF
            z = value == imm
            c = value < imm
            pc += 6
        elif (op & 0xFF00) in {0x6200, 0x6600, 0x6700}:
            disp = op & 0xFF
            if disp == 0:
                raise RuntimeError("word displacement outside bounded kernel")
            if disp & 0x80:
                disp -= 0x100
            condition = {
                0x6200: (not c and not z),
                0x6600: (not z),
                0x6700: z,
            }[op & 0xFF00]
            pc = pc + 2 + disp if condition else pc + 2
        elif (op & 0xFFF8) == 0x4A80:  # TST.L Dn
            dn = op & 7
            z = (regs[dn] & 0xFFFFFFFF) == 0
            c = False
            pc += 2
        elif (op & 0xFFF8) == 0x4A00:  # TST.B Dn
            dn = op & 7
            z = (regs[dn] & 0xFF) == 0
            c = False
            pc += 2
        elif (op & 0xF100) == 0x7000:  # MOVEQ #imm,Dn
            dn = (op >> 9) & 7
            imm = op & 0xFF
            if imm & 0x80:
                imm -= 0x100
            regs[dn] = imm & 0xFFFFFFFF
            pc += 2
        elif op == 0x4E75:
            return regs[0], regs[1], regs[3], count
        else:
            raise RuntimeError(f"unsupported opcode 0x{op:04x} at {pc}")


def verify() -> dict[str, object]:
    code = compile_kernel()
    max_instructions = 0
    valid_pairs = 0
    for mask in range(FULL_MASK + 1):
        for d3 in (0, 1):
            out_mask, disposition, out_d3, count = execute_kernel(code, mask, d3)
            expected_disposition, expected_d3 = reference_branch_pass(mask, d3)
            if out_mask != mask or (disposition, out_d3) != (expected_disposition, expected_d3):
                raise AssertionError((mask, d3, expected_disposition, expected_d3, out_mask, disposition, out_d3))
            max_instructions = max(max_instructions, count)
            valid_pairs += 1

    invalid_lifecycle_pairs = 0
    for d3 in range(2, 256):
        for mask in (0, 1, FULL_MASK):
            out_mask, disposition, out_d3, count = execute_kernel(code, mask, d3)
            if out_mask != mask or disposition != HOLD or out_d3 != d3:
                raise AssertionError((mask, d3, out_mask, disposition, out_d3))
            max_instructions = max(max_instructions, count)
            invalid_lifecycle_pairs += 1

    invalid_descriptor_pairs = 0
    for mask in tuple(range(FULL_MASK + 1, FULL_MASK + 257)) + (0xFFFFFFFF,):
        for d3 in (0, 1):
            out_mask, disposition, out_d3, count = execute_kernel(code, mask, d3)
            if out_mask != mask or disposition != HOLD or out_d3 != d3:
                raise AssertionError((mask, d3, out_mask, disposition, out_d3))
            max_instructions = max(max_instructions, count)
            invalid_descriptor_pairs += 1

    return {
        "schema": "QIKVRT_SPARK_BRANCH_PASS_M68000_REPORT_V1",
        "machine_bytes": len(code),
        "machine_hex": code.hex(),
        "max_dynamic_instructions": max_instructions,
        "full_mask_hex": f"0x{FULL_MASK:08x}",
        "required_predicates": list(REQUIRED_PREDICATES),
        "ring_ladder": list(RING_LADDER),
        "valid_descriptor_lifecycle_pairs_verified": valid_pairs,
        "invalid_lifecycle_pairs_fail_closed": invalid_lifecycle_pairs,
        "invalid_descriptor_samples_fail_closed": invalid_descriptor_pairs,
        "branch_pass_complete_is_git_merge": False,
        "symbolic_outer_ring_eagerly_materialized": False,
        "physical_m68000_execution_observed": False,
        "physical_speedup_measured": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
