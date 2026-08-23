#!/usr/bin/env python3
"""Compile, verify and execute the finite QIK-VRT Spark branch pass.

The emitted Motorola 68000 kernel consumes one already admitted branch-work
flag byte and preserves D3. It performs no Git write or external effect.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / "runtime/m68000/QIKVRT_SPARK_ARCHITECTURE_V1.json"
UPSTREAM_REGISTRY = ROOT / "runtime/m68000/QIKVRT_COMPILED_KERNELS_V1.json"
HEX_PATH = ROOT / "runtime/m68000/qikvrt_spark_branch_pass.hex"

NOOP = 0
HOLD = 1
REOBSERVE = 2
REQUEST_AUTHORITY = 3

EXPECTED_HEX = (
    "08000007662c08000004662e08000005670608000006672a"
    "08000000671c08000001671608000002671008000003670a6018"
    "7001720074004e757002720074014e757003720074004e75"
    "7000720174004e75"
)

MODE_FLAGS = {
    "complete": 0x0F,
    "stale": 0x1F,
    "authority": 0x2F,
    "hold": 0x8F,
    "incomplete": 0x03,
}
DECISION_NAMES = {
    NOOP: "NOOP_COMPLETE",
    HOLD: "HOLD",
    REOBSERVE: "REOBSERVE",
    REQUEST_AUTHORITY: "REQUEST_AUTHORITY",
}


@dataclass(frozen=True)
class Label:
    name: str


@dataclass(frozen=True)
class Op:
    kind: str
    args: tuple


def _word(value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(value)
    return bytes(((value >> 8) & 0xFF, value & 0xFF))


def _program() -> list[Label | Op]:
    return [
        Op("btst", (7, 0)), Op("bne", ("hold",)),
        Op("btst", (4, 0)), Op("bne", ("reobserve",)),
        Op("btst", (5, 0)), Op("beq", ("ready",)),
        Op("btst", (6, 0)), Op("beq", ("request_authority",)),
        Label("ready"),
        Op("btst", (0, 0)), Op("beq", ("reobserve",)),
        Op("btst", (1, 0)), Op("beq", ("reobserve",)),
        Op("btst", (2, 0)), Op("beq", ("reobserve",)),
        Op("btst", (3, 0)), Op("beq", ("reobserve",)),
        Op("bra", ("complete",)),
        Label("hold"),
        Op("moveq", (HOLD, 0)), Op("moveq", (0, 1)), Op("moveq", (0, 2)), Op("rts", ()),
        Label("reobserve"),
        Op("moveq", (REOBSERVE, 0)), Op("moveq", (0, 1)), Op("moveq", (1, 2)), Op("rts", ()),
        Label("request_authority"),
        Op("moveq", (REQUEST_AUTHORITY, 0)), Op("moveq", (0, 1)), Op("moveq", (0, 2)), Op("rts", ()),
        Label("complete"),
        Op("moveq", (NOOP, 0)), Op("moveq", (1, 1)), Op("moveq", (0, 2)), Op("rts", ()),
    ]


def _size(op: Op) -> int:
    return {"btst": 4, "beq": 2, "bne": 2, "bra": 2, "moveq": 2, "rts": 2}[op.kind]


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
    branch_opcodes = {"bra": 0x6000, "bne": 0x6600, "beq": 0x6700}
    for item in program:
        if isinstance(item, Label):
            continue
        if item.kind == "btst":
            bit, dn = item.args
            out += _word(0x0800 | dn)
            out += _word(bit)
        elif item.kind in branch_opcodes:
            (target,) = item.args
            displacement = labels[target] - (pc + 2)
            if not -128 <= displacement <= 127 or displacement == 0:
                raise ValueError((item, displacement))
            out += _word(branch_opcodes[item.kind] | (displacement & 0xFF))
        elif item.kind == "moveq":
            imm, dn = item.args
            out += _word(0x7000 | (dn << 9) | (imm & 0xFF))
        elif item.kind == "rts":
            out += _word(0x4E75)
        else:
            raise ValueError(item.kind)
        pc += _size(item)

    code = bytes(out)
    if code.hex() != EXPECTED_HEX:
        raise AssertionError((EXPECTED_HEX, code.hex()))
    return code


MACHINE = compile_kernel()


def reference(flags: int, d3: int) -> tuple[int, int, int, int]:
    flags &= 0xFF
    d3 &= 0xFF
    if flags & 0x80:
        return HOLD, 0, 0, d3
    if flags & 0x10:
        return REOBSERVE, 0, 1, d3
    if flags & 0x20 and not flags & 0x40:
        return REQUEST_AUTHORITY, 0, 0, d3
    if flags & 0x0F == 0x0F:
        return NOOP, 1, 0, d3
    return REOBSERVE, 0, 1, d3


def execute(code: bytes, flags: int, d3: int) -> tuple[int, int, int, int, int]:
    regs = [0] * 8
    regs[0] = flags & 0xFFFFFFFF
    regs[3] = d3 & 0xFFFFFFFF
    pc = 0
    z = False
    count = 0
    while True:
        if pc + 2 > len(code):
            raise RuntimeError("truncated Spark kernel")
        op = int.from_bytes(code[pc:pc + 2], "big")
        count += 1
        if (op & 0xFFF8) == 0x0800:
            if pc + 4 > len(code):
                raise RuntimeError("truncated BTST")
            dn = op & 7
            bit = int.from_bytes(code[pc + 2:pc + 4], "big")
            if bit > 31:
                raise RuntimeError("invalid BTST bit")
            z = ((regs[dn] >> bit) & 1) == 0
            pc += 4
        elif (op & 0xFF00) in (0x6000, 0x6600, 0x6700):
            kind = op & 0xFF00
            disp = op & 0xFF
            if disp == 0:
                raise RuntimeError("word branch outside bounded kernel")
            if disp & 0x80:
                disp -= 0x100
            take = kind == 0x6000 or (kind == 0x6600 and not z) or (kind == 0x6700 and z)
            pc = pc + 2 + disp if take else pc + 2
        elif (op & 0xF100) == 0x7000:
            dn = (op >> 9) & 7
            imm = op & 0xFF
            if imm & 0x80:
                imm -= 0x100
            regs[dn] = imm & 0xFFFFFFFF
            pc += 2
        elif op == 0x4E75:
            return regs[0], regs[1], regs[2], regs[3], count
        else:
            raise RuntimeError(f"unsupported opcode 0x{op:04x} at {pc}")


def verify_exhaustive(code: bytes = MACHINE) -> dict:
    checked = 0
    max_count = 0
    decision_counts = {str(NOOP): 0, str(HOLD): 0, str(REOBSERVE): 0, str(REQUEST_AUTHORITY): 0}
    for flags in range(256):
        for d3 in range(256):
            actual = execute(code, flags, d3)
            expected = reference(flags, d3)
            if actual[:4] != expected:
                raise AssertionError((flags, d3, expected, actual))
            if actual[3] != d3:
                raise AssertionError(("D3_MUTATED", flags, d3, actual[3]))
            checked += 1
            max_count = max(max_count, actual[4])
            decision_counts[str(actual[0])] += 1
    return {
        "schema": "QIKVRT_SPARK_BRANCH_COMPILER_REPORT_V1",
        "machine_bytes": len(code),
        "machine_hex": code.hex(),
        "flag_values_verified": 256,
        "d3_values_verified": 256,
        "input_pairs_verified": checked,
        "d3_preserved": True,
        "max_dynamic_instructions": max_count,
        "decision_counts": decision_counts,
        "virtual_m68000_execution_observed": True,
        "physical_m68000_execution_observed": False,
        "numeric_physical_speedup_measured": False,
    }


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_contract() -> tuple[dict, bytes]:
    architecture = json.loads(ARCHITECTURE.read_text(encoding="utf-8"))
    registry = json.loads(UPSTREAM_REGISTRY.read_text(encoding="utf-8"))
    required = architecture["required_upstream_kernel_ids"]
    observed = [item["id"] for item in registry["kernels"]]
    if observed != required:
        raise SystemExit(f"BLOCK: upstream compiled-kernel registry mismatch: {observed!r}")
    code = bytes.fromhex(HEX_PATH.read_text(encoding="utf-8").strip())
    if code != MACHINE:
        raise SystemExit("BLOCK: Spark machine bytes differ from deterministic compiler")
    kernel = architecture["spark_kernel"]
    if kernel["machine_bytes"] != len(code) or kernel["hex_path"] != HEX_PATH.relative_to(ROOT).as_posix():
        raise SystemExit("BLOCK: Spark architecture registry mismatch")
    return architecture, code


def run_batch(
    *, repository: str, branch: str, base_sha: str, head_sha: str,
    tree_sha: str, mode: str, batch: int,
) -> dict:
    if mode not in MODE_FLAGS:
        raise ValueError(mode)
    if batch <= 0:
        raise ValueError("batch must be positive")
    architecture, code = load_contract()
    flags = MODE_FLAGS[mode]
    results = []
    for ordinal in range(batch):
        work_unit = {
            "schema": "QIKVRT_SPARK_BRANCH_WORK_UNIT_V1",
            "repository": repository,
            "branch": branch,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "tree_sha": tree_sha,
            "ordinal": ordinal,
            "mode": mode,
            "flags": flags,
        }
        digest = hashlib.sha256(canonical_bytes(work_unit)).hexdigest()
        d3_in = int(digest[:2], 16)
        d0, d1, d2, d3_out, instructions = execute(code, flags, d3_in)
        if d3_out != d3_in:
            raise AssertionError(("D3_MUTATED", d3_in, d3_out))
        results.append({
            "ordinal": ordinal,
            "work_unit_sha256": digest,
            "decision_code": d0,
            "decision": DECISION_NAMES[d0],
            "completion_witness": d1,
            "machine_owned_active": d2,
            "d3_before": d3_in,
            "d3_after": d3_out,
            "dynamic_instructions": instructions,
            "bounded_work_ring_closed": d1 == 1,
        })

    closed = sum(1 for item in results if item["bounded_work_ring_closed"])
    if mode == "complete" and closed != batch:
        raise AssertionError((closed, batch))
    return {
        "schema": "QIKVRT_SPARK_BRANCH_RUNTIME_RECEIPT_V1",
        "architecture": architecture["schema"],
        "repository": repository,
        "branch": branch,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "tree_sha": tree_sha,
        "mode": mode,
        "structural_ring_count": len(architecture["structural_rings"]),
        "control_ring_bits": architecture["two_three_eight_three_binding"]["two_power_three_bits"],
        "control_ring_possible_states": architecture["two_three_eight_three_binding"]["first_ring_possible_states"],
        "evidence_ring_bits": architecture["two_three_eight_three_binding"]["outer_evidence_ring_bits"],
        "upstream_registry_bound": True,
        "compiled_kernel_loaded_once": True,
        "compiler_invocations_at_runtime": 0,
        "higher_level_rule_reinterpreted_per_pass": False,
        "processor_passes": batch,
        "work_units_consumed": batch,
        "bounded_work_units_closed": closed,
        "one_processor_pass_per_work_unit": len(results) == batch,
        "max_dynamic_instructions_observed": max(item["dynamic_instructions"] for item in results),
        "results": results,
        "virtual_m68000_execution_observed": True,
        "physical_m68000_execution_observed": False,
        "physical_atari_mega_st_execution_observed": False,
        "numeric_physical_speedup_measured": False,
        "git_merge_effect_applied": False,
        "authority_main_effect": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--json", action="store_true")
    run = sub.add_parser("run")
    run.add_argument("--repository", required=True)
    run.add_argument("--branch", required=True)
    run.add_argument("--base-sha", required=True)
    run.add_argument("--head-sha", required=True)
    run.add_argument("--tree-sha", required=True)
    run.add_argument("--mode", choices=sorted(MODE_FLAGS), default="complete")
    run.add_argument("--batch", type=int, default=1)
    run.add_argument("--output")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "verify":
        report = verify_exhaustive()
    else:
        report = run_batch(
            repository=args.repository, branch=args.branch, base_sha=args.base_sha,
            head_sha=args.head_sha, tree_sha=args.tree_sha, mode=args.mode, batch=args.batch,
        )
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2 if getattr(args, "json", True) else None) + "\n"
    output = getattr(args, "output", None)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
