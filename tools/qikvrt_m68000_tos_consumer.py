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
)
RECEIPT_MAGIC = b"QIKM68K1"
RECEIPT_VERSION = 1
RECEIPT_SIZE = 192
ITERATIONS = 4 * 65536


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def be16(value: int) -> bytes:
    return struct.pack(">H", value & 0xFFFF)


def be32(value: int) -> bytes:
    return struct.pack(">I", value & 0xFFFFFFFF)


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
        # 68000 word branches and d16(PC) use PC at the extension word.
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
            result[fixup.displacement_offset:fixup.displacement_offset + 2] = be16(displacement)
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
    assembler.word(0x2038 | (dn << 9))
    assembler.word(0x04BA)


def emit_call_benchmark(
    assembler: Asm68k,
    name: str,
    setup_each: Iterable[tuple[int, int]],
    setup_once: Iterable[tuple[int, int]],
    receipt_offset: int,
) -> None:
    for immediate, dn in setup_once:
        moveq(assembler, immediate, dn)
    load_timer(assembler, 6)
    moveq(assembler, 3, 4)  # four outer iterations
    assembler.label(f"{name}_outer")
    moveq(assembler, -1, 5)  # 65536 inner iterations
    assembler.label(f"{name}_inner")
    for immediate, dn in setup_each:
        moveq(assembler, immediate, dn)
    assembler.bsr(name)
    assembler.dbra(5, f"{name}_inner")
    assembler.dbra(4, f"{name}_outer")
    load_timer(assembler, 1)
    assembler.word(0x9286)  # SUB.L D6,D1
    move_l_dn_disp_a0(assembler, 1, receipt_offset)


def load_registry(root: pathlib.Path) -> tuple[dict, list[bytes]]:
    registry_raw = (root / REGISTRY_PATH).read_bytes()
    registry = json.loads(registry_raw)
    if registry.get("schema") != "QIKVRT_COMPILED_M68000_KERNEL_REGISTRY_V1":
        raise ValueError("unexpected M68000 registry schema")
    by_id = {entry["id"]: entry for entry in registry["kernels"]}
    if tuple(kernel_id for kernel_id in KERNEL_IDS if kernel_id not in by_id):
        raise ValueError("required compiled kernel missing from registry")
    kernels: list[bytes] = []
    for kernel_id in KERNEL_IDS:
        entry = by_id[kernel_id]
        raw = bytes.fromhex((root / entry["hex_path"]).read_text(encoding="ascii").strip())
        if len(raw) != entry["machine_bytes"]:
            raise ValueError(f"registry byte length mismatch: {kernel_id}")
        kernels.append(raw)
    return registry, kernels


def receipt_template(registry_raw: bytes, kernels: list[bytes]) -> bytes:
    buffer = bytearray(RECEIPT_SIZE)
    buffer[0:8] = RECEIPT_MAGIC
    buffer[8:12] = be32(RECEIPT_VERSION)
    buffer[12:44] = sha256(registry_raw)
    buffer[44:76] = sha256(kernels[0])
    buffer[76:108] = sha256(kernels[1])
    buffer[108:140] = sha256(kernels[2])
    buffer[140:144] = be32(ITERATIONS)
    return bytes(buffer)


def build_text(root: pathlib.Path) -> tuple[bytes, dict]:
    registry_raw = (root / REGISTRY_PATH).read_bytes()
    _, kernels = load_registry(root)
    assembler = Asm68k()

    # A0 permanently points at the writable receipt buffer.
    assembler.lea_pc("receipt", 0)

    # Exact functional observations.
    for value in range(4):
        moveq(assembler, value, 0)
        assembler.bsr("lean_gate_v1")
        move_b_dn_disp_a0(assembler, 0, 144 + value)

    moveq(assembler, 3, 0)
    moveq(assembler, 0, 2)
    moveq(assembler, 0xA5, 3)
    assembler.bsr("lean_v2_d3_step_v1")
    move_b_dn_disp_a0(assembler, 0, 148)
    move_b_dn_disp_a0(assembler, 2, 149)
    move_b_dn_disp_a0(assembler, 3, 150)

    for value in range(8):
        moveq(assembler, value, 0)
        assembler.bsr("lean_v2_mesh_recovery_v1")
        move_b_dn_disp_a0(assembler, 0, 152 + value)

    # 262144 repeated native invocations per kernel, measured against TOS hz_200.
    emit_call_benchmark(assembler, "lean_gate_v1", ((3, 0),), (), 160)
    emit_call_benchmark(
        assembler,
        "lean_v2_d3_step_v1",
        (),
        ((3, 0), (0, 2), (0xA5, 3)),
        164,
    )
    emit_call_benchmark(assembler, "lean_v2_mesh_recovery_v1", ((6, 0),), (), 168)

    moveq(assembler, 1, 1)
    move_l_dn_disp_a0(assembler, 1, 172)  # execution-complete marker

    # GEMDOS Fcreate("QIKVRT.RCP", 0)
    assembler.lea_pc("receipt_name", 1)
    assembler.word(0x3F3C)
    assembler.word(0x0000)  # MOVE.W #0,-(SP)
    assembler.word(0x2F09)  # MOVE.L A1,-(SP)
    assembler.word(0x3F3C)
    assembler.word(0x003C)  # MOVE.W #Fcreate,-(SP)
    assembler.word(0x4E41)  # TRAP #1
    assembler.word(0x508F)  # ADDQ.L #8,SP
    assembler.word(0x3E00)  # MOVE.W D0,D7

    # GEMDOS Fwrite(handle, RECEIPT_SIZE, receipt)
    assembler.lea_pc("receipt", 0)
    assembler.word(0x2F08)  # MOVE.L A0,-(SP)
    assembler.word(0x2F3C)
    assembler.long(RECEIPT_SIZE)
    assembler.word(0x3F07)  # MOVE.W D7,-(SP)
    assembler.word(0x3F3C)
    assembler.word(0x0040)  # MOVE.W #Fwrite,-(SP)
    assembler.word(0x4E41)
    assembler.word(0x4FEF)
    assembler.word(0x000C)  # LEA 12(SP),SP

    # GEMDOS Fclose(handle)
    assembler.word(0x3F07)
    assembler.word(0x3F3C)
    assembler.word(0x003E)
    assembler.word(0x4E41)
    assembler.word(0x588F)  # ADDQ.L #4,SP

    # GEMDOS Pterm0
    assembler.word(0x3F3C)
    assembler.word(0x0000)
    assembler.word(0x4E41)

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
        "schema": "QIKVRT_M68000_TOS_CONSUMER_BUILD_V1",
        "registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
        "kernel_ids": list(KERNEL_IDS),
        "kernel_sha256": [hashlib.sha256(kernel).hexdigest() for kernel in kernels],
        "kernel_bytes": [len(kernel) for kernel in kernels],
        "iterations_per_kernel": ITERATIONS,
        "text_bytes": len(text),
        "receipt_size": RECEIPT_SIZE,
        "physical_hardware": False,
    }
    return text, metadata


def build_tos(root: pathlib.Path) -> tuple[bytes, dict]:
    text, metadata = build_text(root)
    header = b"".join(
        (
            be16(0x601A),
            be32(len(text)),
            be32(0),  # data
            be32(0),  # bss
            be32(0),  # symbols
            be32(0),  # reserved
            be32(0),  # flags
            be16(1),  # absolute / no relocation table
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
    actual_hashes = [raw[12:44], raw[44:76], raw[76:108], raw[108:140]]
    if actual_hashes != expected_hashes:
        raise ValueError("registry/kernel provenance hash mismatch")
    iterations = struct.unpack_from(">I", raw, 140)[0]
    gate = list(raw[144:148])
    d3 = list(raw[148:151])
    mesh = list(raw[152:160])
    ticks = [struct.unpack_from(">I", raw, offset)[0] for offset in (160, 164, 168)]
    completed = struct.unpack_from(">I", raw, 172)[0]
    if iterations != ITERATIONS:
        raise ValueError("benchmark iteration count mismatch")
    if gate != [0, 1, 2, 2]:
        raise ValueError(f"gate observation mismatch: {gate}")
    if d3 != [3, 1, 0xA5]:
        raise ValueError(f"D3 observation mismatch: {d3}")
    if mesh != [0, 0, 0, 0, 1, 1, 1, 2]:
        raise ValueError(f"mesh recovery observation mismatch: {mesh}")
    if completed != 1:
        raise ValueError("TOS execution did not reach completion marker")
    if any(value == 0 for value in ticks):
        raise ValueError(f"benchmark duration was not observable: {ticks}")
    calls_per_second = [iterations * 200.0 / value for value in ticks]
    return {
        "schema": "QIKVRT_M68000_TOS_REOBSERVATION_V1",
        "execution_observed": True,
        "tos_abi_observed": True,
        "m68000_emulator_execution_observed": True,
        "physical_m68000_execution_observed": False,
        "registry_sha256": actual_hashes[0].hex(),
        "kernel_sha256": [value.hex() for value in actual_hashes[1:]],
        "iterations_per_kernel": iterations,
        "gate_outputs": gate,
        "d3_output": {"d0": d3[0], "d2": d3[1], "d3": d3[2]},
        "mesh_outputs": mesh,
        "ticks_200hz": {
            "gate": ticks[0],
            "d3_step": ticks[1],
            "mesh_recovery": ticks[2],
        },
        "calls_per_emulated_second": {
            "gate": calls_per_second[0],
            "d3_step": calls_per_second[1],
            "mesh_recovery": calls_per_second[2],
        },
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
