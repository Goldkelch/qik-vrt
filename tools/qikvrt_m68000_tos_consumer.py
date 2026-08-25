#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
from dataclasses import dataclass
from typing import Iterable

REGISTRY_PATH = pathlib.Path("runtime/m68000/QIKVRT_COMPILED_KERNELS_V1.json")
KERNEL_IDS = (
    "lean_gate_v1",
    "lean_v2_d3_step_v1",
    "lean_v2_mesh_recovery_v1",
    "lean_spark_branch_pass_v1",
    "lean_spark_branch_plan_v1",
)
RECEIPT_MAGIC = b"QIKM68K2"
RECEIPT_VERSION = 2
RECEIPT_SIZE = 320
ITERATIONS = 4 * 65536

REGISTRY_HASH_OFFSET = 12
KERNEL_HASH_OFFSET = 44
HASH_SIZE = 32
ITERATIONS_OFFSET = KERNEL_HASH_OFFSET + HASH_SIZE * len(KERNEL_IDS)
GATE_OFFSET = 208
D3_OFFSET = 212
MESH_OFFSET = 216
SPARK_PASS_OFFSET = 224
SPARK_PLAN_OFFSET = 240
TICKS_OFFSET = 248
COMPLETE_OFFSET = 268

SPARK_PASS_CASES = (
    (0x0F, (0, 1, 0, 0xA5)),
    (0x1F, (2, 0, 1, 0xA5)),
    (0x2F, (3, 0, 0, 0xA5)),
    (0x8F, (1, 0, 0, 0xA5)),
)
SPARK_PLAN_CASES = (
    (1, 1),
    (2, 0),
    (124, 11),
    (252, 10),
    (248, 2),
)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def be16(value: int) -> bytes:
    return struct.pack(">H", value & 0xFFFF)


def be32(value: int) -> bytes:
    return struct.pack(">I", value & 0xFFFFFFFF)


def moveq_immediate(value: int) -> int:
    value &= 0xFF
    return value - 256 if value >= 128 else value


@dataclass
class Fixup:
    displacement_offset: int
    base_pc: int
    label: str


class Asm68k:
    def __init__(self) -> None:
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[Fixup] = []

    @property
    def pc(self) -> int:
        return len(self.code)

    def word(self, value: int) -> None:
        self.code += be16(value)

    def long(self, value: int) -> None:
        self.code += be32(value)

    def raw(self, data: bytes) -> None:
        self.code += data

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = self.pc

    def pcrel_word(self, opcode: int, label: str) -> None:
        start = self.pc
        self.word(opcode)
        offset = self.pc
        self.word(0)
        self.fixups.append(Fixup(offset, start + 2, label))

    def bsr(self, label: str) -> None:
        self.pcrel_word(0x6100, label)

    def dbra(self, dn: int, label: str) -> None:
        self.pcrel_word(0x51C8 | dn, label)

    def lea_pc(self, label: str, an: int) -> None:
        self.pcrel_word(0x41FA | (an << 9), label)

    def resolve(self) -> bytes:
        result = bytearray(self.code)
        for fixup in self.fixups:
            if fixup.label not in self.labels:
                raise ValueError(f"undefined label: {fixup.label}")
            displacement = self.labels[fixup.label] - fixup.base_pc
            if not -32768 <= displacement <= 32767:
                raise ValueError(f"word displacement out of range: {fixup.label}")
            result[fixup.displacement_offset:fixup.displacement_offset + 2] = be16(
                displacement
            )
        return bytes(result)


def moveq(assembler: Asm68k, immediate: int, dn: int) -> None:
    assembler.word(0x7000 | (dn << 9) | (immediate & 0xFF))


def move_b_dn_disp_a0(assembler: Asm68k, dn: int, displacement: int) -> None:
    assembler.word(0x1140 | dn)
    assembler.word(displacement)


def move_l_dn_disp_a0(assembler: Asm68k, dn: int, displacement: int) -> None:
    assembler.word(0x2140 | dn)
    assembler.word(displacement)


def load_timer(assembler: Asm68k, dn: int) -> None:
    """Read protected TOS hz_200 through XBIOS Supexec."""
    assembler.word(0x2F08)
    assembler.lea_pc("read_hz_200_supervisor", 1)
    assembler.word(0x2F09)
    assembler.word(0x3F3C)
    assembler.word(0x0026)
    assembler.word(0x4E4E)
    assembler.word(0x4FEF)
    assembler.word(0x0006)
    assembler.word(0x205F)
    assembler.word(0x2000 | (dn << 9))


def emit_call_benchmark(
    assembler: Asm68k,
    name: str,
    setup_each: Iterable[tuple[int, int]],
    setup_once: Iterable[tuple[int, int]],
    receipt_offset: int,
) -> None:
    load_timer(assembler, 6)
    for immediate, dn in setup_once:
        moveq(assembler, immediate, dn)
    moveq(assembler, 3, 4)
    assembler.label(f"{name}_outer")
    moveq(assembler, -1, 5)
    assembler.label(f"{name}_inner")
    for immediate, dn in setup_each:
        moveq(assembler, immediate, dn)
    assembler.bsr(name)
    assembler.dbra(5, f"{name}_inner")
    assembler.dbra(4, f"{name}_outer")
    load_timer(assembler, 1)
    assembler.word(0x9286)
    move_l_dn_disp_a0(assembler, 1, receipt_offset)


def load_registry(root: pathlib.Path) -> tuple[dict, list[bytes]]:
    registry_raw = (root / REGISTRY_PATH).read_bytes()
    registry = json.loads(registry_raw)
    if registry.get("schema") != "QIKVRT_COMPILED_M68000_KERNEL_REGISTRY_V1":
        raise ValueError("unexpected M68000 registry schema")
    entries = registry.get("kernels")
    if not isinstance(entries, list):
        raise ValueError("registry kernels must be a list")
    by_id = {entry["id"]: entry for entry in entries}
    if tuple(kernel_id for kernel_id in KERNEL_IDS if kernel_id not in by_id):
        raise ValueError("required compiled kernel missing from registry")
    kernels: list[bytes] = []
    for kernel_id in KERNEL_IDS:
        entry = by_id[kernel_id]
        raw = bytes.fromhex(
            (root / entry["hex_path"]).read_text(encoding="ascii").strip()
        )
        if len(raw) != entry["machine_bytes"]:
            raise ValueError(f"registry byte length mismatch: {kernel_id}")
        kernels.append(raw)
    if registry.get("compiled_machine_bytes_total") != sum(map(len, kernels)):
        raise ValueError("registry total byte declaration mismatch")
    return registry, kernels


def receipt_template(registry_raw: bytes, kernels: list[bytes]) -> bytes:
    if len(kernels) != len(KERNEL_IDS):
        raise ValueError("kernel count differs")
    buffer = bytearray(RECEIPT_SIZE)
    buffer[0:8] = RECEIPT_MAGIC
    buffer[8:12] = be32(RECEIPT_VERSION)
    buffer[REGISTRY_HASH_OFFSET:REGISTRY_HASH_OFFSET + HASH_SIZE] = sha256(
        registry_raw
    )
    for index, kernel in enumerate(kernels):
        start = KERNEL_HASH_OFFSET + index * HASH_SIZE
        buffer[start:start + HASH_SIZE] = sha256(kernel)
    buffer[ITERATIONS_OFFSET:ITERATIONS_OFFSET + 4] = be32(ITERATIONS)
    return bytes(buffer)


def build_text(root: pathlib.Path) -> tuple[bytes, dict]:
    registry_raw = (root / REGISTRY_PATH).read_bytes()
    _, kernels = load_registry(root)
    assembler = Asm68k()
    assembler.lea_pc("receipt", 0)

    for value in range(4):
        moveq(assembler, value, 0)
        assembler.bsr("lean_gate_v1")
        move_b_dn_disp_a0(assembler, 0, GATE_OFFSET + value)

    moveq(assembler, 3, 0)
    moveq(assembler, 0, 2)
    moveq(assembler, moveq_immediate(0xA5), 3)
    assembler.bsr("lean_v2_d3_step_v1")
    move_b_dn_disp_a0(assembler, 0, D3_OFFSET)
    move_b_dn_disp_a0(assembler, 2, D3_OFFSET + 1)
    move_b_dn_disp_a0(assembler, 3, D3_OFFSET + 2)

    for value in range(8):
        moveq(assembler, value, 0)
        assembler.bsr("lean_v2_mesh_recovery_v1")
        move_b_dn_disp_a0(assembler, 0, MESH_OFFSET + value)

    moveq(assembler, moveq_immediate(0xA5), 3)
    for index, (flags, _expected) in enumerate(SPARK_PASS_CASES):
        moveq(assembler, moveq_immediate(flags), 0)
        assembler.bsr("lean_spark_branch_pass_v1")
        start = SPARK_PASS_OFFSET + index * 4
        move_b_dn_disp_a0(assembler, 0, start)
        move_b_dn_disp_a0(assembler, 1, start + 1)
        move_b_dn_disp_a0(assembler, 2, start + 2)
        move_b_dn_disp_a0(assembler, 3, start + 3)

    for index, (flags, _expected) in enumerate(SPARK_PLAN_CASES):
        moveq(assembler, moveq_immediate(flags), 0)
        assembler.bsr("lean_spark_branch_plan_v1")
        move_b_dn_disp_a0(assembler, 0, SPARK_PLAN_OFFSET + index)

    emit_call_benchmark(assembler, "lean_gate_v1", ((3, 0),), (), TICKS_OFFSET)
    emit_call_benchmark(
        assembler,
        "lean_v2_d3_step_v1",
        (),
        ((3, 0), (0, 2), (moveq_immediate(0xA5), 3)),
        TICKS_OFFSET + 4,
    )
    emit_call_benchmark(
        assembler,
        "lean_v2_mesh_recovery_v1",
        ((6, 0),),
        (),
        TICKS_OFFSET + 8,
    )
    emit_call_benchmark(
        assembler,
        "lean_spark_branch_pass_v1",
        ((0x0F, 0),),
        ((moveq_immediate(0xA5), 3),),
        TICKS_OFFSET + 12,
    )
    emit_call_benchmark(
        assembler,
        "lean_spark_branch_plan_v1",
        ((moveq_immediate(0xFC), 0),),
        (),
        TICKS_OFFSET + 16,
    )

    moveq(assembler, 1, 1)
    move_l_dn_disp_a0(assembler, 1, COMPLETE_OFFSET)

    assembler.lea_pc("receipt_name", 1)
    assembler.word(0x3F3C)
    assembler.word(0x0000)
    assembler.word(0x2F09)
    assembler.word(0x3F3C)
    assembler.word(0x003C)
    assembler.word(0x4E41)
    assembler.word(0x508F)
    assembler.word(0x3E00)

    assembler.lea_pc("receipt", 0)
    assembler.word(0x2F08)
    assembler.word(0x2F3C)
    assembler.long(RECEIPT_SIZE)
    assembler.word(0x3F07)
    assembler.word(0x3F3C)
    assembler.word(0x0040)
    assembler.word(0x4E41)
    assembler.word(0x4FEF)
    assembler.word(0x000C)

    assembler.word(0x3F07)
    assembler.word(0x3F3C)
    assembler.word(0x003E)
    assembler.word(0x4E41)
    assembler.word(0x588F)
    assembler.word(0x3F3C)
    assembler.word(0x0000)
    assembler.word(0x4E41)

    assembler.label("read_hz_200_supervisor")
    assembler.word(0x2038)
    assembler.word(0x04BA)
    assembler.word(0x4E75)

    for kernel_id, raw in zip(KERNEL_IDS, kernels):
        if assembler.pc & 1:
            assembler.raw(b"\0")
        assembler.label(kernel_id)
        assembler.raw(raw)

    if assembler.pc & 1:
        assembler.raw(b"\0")
    assembler.label("receipt_name")
    assembler.raw(b"QIKVRT.RCP\0")
    if assembler.pc & 1:
        assembler.raw(b"\0")
    assembler.label("receipt")
    assembler.raw(receipt_template(registry_raw, kernels))
    text = assembler.resolve()
    metadata = {
        "schema": "QIKVRT_M68000_TOS_CONSUMER_BUILD_V2",
        "registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
        "kernel_ids": list(KERNEL_IDS),
        "kernel_sha256": [hashlib.sha256(kernel).hexdigest() for kernel in kernels],
        "kernel_bytes": [len(kernel) for kernel in kernels],
        "iterations_per_kernel": ITERATIONS,
        "text_bytes": len(text),
        "receipt_size": RECEIPT_SIZE,
        "timer_access": "XBIOS_SUPEXEC_HZ_200",
        "physical_hardware": False,
    }
    return text, metadata


def build_tos(root: pathlib.Path) -> tuple[bytes, dict]:
    text, metadata = build_text(root)
    header = b"".join(
        (
            be16(0x601A),
            be32(len(text)),
            be32(0),
            be32(0),
            be32(0),
            be32(0),
            be32(0),
            be16(1),
        )
    )
    if len(header) != 28:
        raise AssertionError("invalid TOS header length")
    image = header + text
    metadata["tos_bytes"] = len(image)
    metadata["tos_sha256"] = hashlib.sha256(image).hexdigest()
    return image, metadata


def parse_receipt(raw: bytes, root: pathlib.Path) -> dict:
    if len(raw) != RECEIPT_SIZE:
        raise ValueError(f"receipt size {len(raw)} != {RECEIPT_SIZE}")
    registry_raw = (root / REGISTRY_PATH).read_bytes()
    _, kernels = load_registry(root)
    if raw[:8] != RECEIPT_MAGIC:
        raise ValueError("receipt magic mismatch")
    version = struct.unpack_from(">I", raw, 8)[0]
    if version != RECEIPT_VERSION:
        raise ValueError("receipt version mismatch")

    expected_hashes = [sha256(registry_raw)] + [sha256(kernel) for kernel in kernels]
    actual_hashes = [raw[REGISTRY_HASH_OFFSET:REGISTRY_HASH_OFFSET + HASH_SIZE]]
    for index in range(len(kernels)):
        start = KERNEL_HASH_OFFSET + index * HASH_SIZE
        actual_hashes.append(raw[start:start + HASH_SIZE])
    if actual_hashes != expected_hashes:
        raise ValueError("registry/kernel provenance hash mismatch")

    iterations = struct.unpack_from(">I", raw, ITERATIONS_OFFSET)[0]
    gate = list(raw[GATE_OFFSET:GATE_OFFSET + 4])
    d3 = list(raw[D3_OFFSET:D3_OFFSET + 3])
    mesh = list(raw[MESH_OFFSET:MESH_OFFSET + 8])
    spark_pass_flat = list(raw[SPARK_PASS_OFFSET:SPARK_PASS_OFFSET + 16])
    spark_pass = [
        spark_pass_flat[index:index + 4]
        for index in range(0, len(spark_pass_flat), 4)
    ]
    spark_plan = list(raw[SPARK_PLAN_OFFSET:SPARK_PLAN_OFFSET + 5])
    ticks = [
        struct.unpack_from(">I", raw, TICKS_OFFSET + index * 4)[0]
        for index in range(len(KERNEL_IDS))
    ]
    completed = struct.unpack_from(">I", raw, COMPLETE_OFFSET)[0]

    if iterations != ITERATIONS:
        raise ValueError("benchmark iteration count mismatch")
    if gate != [0, 1, 2, 2]:
        raise ValueError(f"gate observation mismatch: {gate}")
    if d3 != [3, 1, 0xA5]:
        raise ValueError(f"D3 observation mismatch: {d3}")
    if mesh != [0, 0, 0, 0, 1, 1, 1, 2]:
        raise ValueError(f"mesh recovery observation mismatch: {mesh}")
    expected_pass = [list(expected) for _flags, expected in SPARK_PASS_CASES]
    if spark_pass != expected_pass:
        raise ValueError(f"Spark pass observation mismatch: {spark_pass}")
    expected_plan = [expected for _flags, expected in SPARK_PLAN_CASES]
    if spark_plan != expected_plan:
        raise ValueError(f"Spark plan observation mismatch: {spark_plan}")
    if completed != 1:
        raise ValueError("TOS execution did not reach completion marker")
    if any(value == 0 for value in ticks):
        raise ValueError(f"benchmark duration was not observable: {ticks}")

    calls_per_second = [ITERATIONS * 200.0 / value for value in ticks]
    names = (
        "gate",
        "d3_step",
        "mesh_recovery",
        "spark_branch_pass",
        "spark_branch_plan",
    )
    return {
        "schema": "QIKVRT_M68000_TOS_REOBSERVATION_V2",
        "execution_observed": True,
        "tos_abi_observed": True,
        "m68000_emulator_execution_observed": True,
        "spark_m68000_emulator_execution_observed": True,
        "physical_m68000_execution_observed": False,
        "registry_sha256": actual_hashes[0].hex(),
        "kernel_ids": list(KERNEL_IDS),
        "kernel_sha256": [value.hex() for value in actual_hashes[1:]],
        "iterations_per_kernel": iterations,
        "gate_outputs": gate,
        "d3_output": {"d0": d3[0], "d2": d3[1], "d3": d3[2]},
        "mesh_outputs": mesh,
        "spark_branch_pass_outputs": [
            {
                "decision_code": value[0],
                "completion_witness": value[1],
                "machine_owned_active": value[2],
                "d3": value[3],
            }
            for value in spark_pass
        ],
        "spark_branch_plan_outputs": spark_plan,
        "ticks_200hz": dict(zip(names, ticks)),
        "calls_per_emulated_second": dict(zip(names, calls_per_second)),
        "physical_speedup_measured": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--hex-output", type=pathlib.Path)
    parser.add_argument("--verify-receipt", type=pathlib.Path)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.verify_receipt:
        report = parse_receipt(arguments.verify_receipt.read_bytes(), root)
    else:
        image, report = build_tos(root)
        if arguments.output:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_bytes(image)
        if arguments.hex_output:
            arguments.hex_output.parent.mkdir(parents=True, exist_ok=True)
            arguments.hex_output.write_text(image.hex() + "\n", encoding="ascii")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
