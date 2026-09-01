#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build the deterministic QIK-VRT MLP Atari TOS program.

The generated GEMDOS executable is a minimal, absolute Motorola 68000 program.
It executes the already-bound MLP register leaf, validates D0/D1/D2, writes the
canonical REQUESTED frame to a temporary file, closes it, atomically renames it
to C:\\MLP.OPEN, and terminates with Pterm(0). Any mismatch follows a fail-closed
path and never publishes C:\\MLP.OPEN.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Final

MLP_LEAF: Final[bytes] = bytes.fromhex("7203740170034e75")
TEMP_PATH: Final[bytes] = b"C:\\MLP.TMP\0"
OPEN_PATH: Final[bytes] = b"C:\\MLP.OPEN\0"
REQUEST_FRAME: Final[bytes] = (
    b"QIKMLP1\r\n"
    b"PROGRAM MLP\r\n"
    b"ACTION OPEN_FIREFOX\r\n"
    b"STATE REQUESTED\r\n"
    b"AUTHORITY MISSING\r\n"
    b"EFFECT REQUESTED\r\n"
    b"END\r\n"
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Fixup:
    extension_offset: int
    label: str


class TextBuilder:
    """Tiny label-aware encoder for the fixed 68000 instruction subset used here."""

    def __init__(self) -> None:
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[Fixup] = []

    def word(self, value: int) -> None:
        self.data.extend(struct.pack(">H", value & 0xFFFF))

    def long(self, value: int) -> None:
        self.data.extend(struct.pack(">L", value & 0xFFFFFFFF))

    def raw(self, value: bytes) -> None:
        self.data.extend(value)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = len(self.data)

    def pc_word(self, opcode: int, label: str) -> None:
        self.word(opcode)
        extension_offset = len(self.data)
        self.word(0)
        self.fixups.append(Fixup(extension_offset, label))

    def finish(self) -> bytes:
        result = bytearray(self.data)
        for fixup in self.fixups:
            if fixup.label not in self.labels:
                raise ValueError(f"unknown label: {fixup.label}")
            # M68000 word branch and d16(PC) displacements are relative to
            # the address of the extension word (the PC value after the
            # opcode word has been consumed), matching the repository's
            # verified QIKVRT.TOS control-flow contract.
            displacement = self.labels[fixup.label] - fixup.extension_offset
            if not -32768 <= displacement <= 32767:
                raise ValueError(f"PC-relative displacement out of range: {fixup.label}")
            result[fixup.extension_offset : fixup.extension_offset + 2] = struct.pack(
                ">h", displacement
            )
        return bytes(result)


def build_text() -> bytes:
    b = TextBuilder()

    # Execute and validate the exact MLP semantic leaf:
    # D0=3 REQUEST_AUTHORITY, D1=3 semantic/type witnesses, D2=1 REQUESTED.
    b.pc_word(0x6100, "leaf")  # BSR.W leaf
    for register, expected in ((0, 3), (1, 3), (2, 1)):
        b.word(0x0C40 | register)  # CMPI.W #expected,Dn
        b.word(expected)
        b.pc_word(0x6600, "fail")  # BNE.W fail

    # Fcreate("C:\\MLP.TMP", 0)
    b.pc_word(0x41FA, "temp_path")  # LEA temp_path(PC),A0
    b.word(0x3F3C)
    b.word(0x0000)  # MOVE.W #0,-(SP)
    b.word(0x2F08)  # MOVE.L A0,-(SP)
    b.word(0x3F3C)
    b.word(0x003C)  # MOVE.W #Fcreate,-(SP)
    b.word(0x4E41)  # TRAP #1
    b.word(0x508F)  # ADDQ.L #8,SP
    b.word(0x4A80)  # TST.L D0
    b.pc_word(0x6B00, "fail")  # BMI.W fail
    b.word(0x3600)  # MOVE.W D0,D3 (preserve handle)

    # Fwrite(handle, len(REQUEST_FRAME), REQUEST_FRAME)
    b.pc_word(0x41FA, "request_frame")  # LEA request_frame(PC),A0
    b.word(0x2F08)  # MOVE.L A0,-(SP)
    b.word(0x2F3C)  # MOVE.L #length,-(SP)
    b.long(len(REQUEST_FRAME))
    b.word(0x3F03)  # MOVE.W D3,-(SP)
    b.word(0x3F3C)
    b.word(0x0040)  # MOVE.W #Fwrite,-(SP)
    b.word(0x4E41)  # TRAP #1
    b.word(0x4FEF)
    b.word(0x000C)  # LEA 12(SP),SP
    b.word(0x0C80)  # CMPI.L #length,D0
    b.long(len(REQUEST_FRAME))
    b.pc_word(0x6600, "close_fail")  # BNE.W close_fail

    # Fclose(handle)
    b.word(0x3F03)
    b.word(0x3F3C)
    b.word(0x003E)
    b.word(0x4E41)
    b.word(0x588F)  # ADDQ.L #4,SP
    b.word(0x4A80)
    b.pc_word(0x6B00, "cleanup_fail")

    # Frename(0, "C:\\MLP.TMP", "C:\\MLP.OPEN")
    b.pc_word(0x41FA, "temp_path")  # A0=old
    b.pc_word(0x43FA, "open_path")  # A1=new
    b.word(0x2F09)  # MOVE.L A1,-(SP)
    b.word(0x2F08)  # MOVE.L A0,-(SP)
    b.word(0x3F3C)
    b.word(0x0000)
    b.word(0x3F3C)
    b.word(0x0056)
    b.word(0x4E41)
    b.word(0x4FEF)
    b.word(0x000C)
    b.word(0x4A80)
    b.pc_word(0x6B00, "cleanup_fail")

    # Pterm(0)
    b.word(0x3F3C)
    b.word(0x0000)
    b.word(0x3F3C)
    b.word(0x004C)
    b.word(0x4E41)

    # Fwrite failed: close the temporary file before deleting it.
    b.label("close_fail")
    b.word(0x3F03)
    b.word(0x3F3C)
    b.word(0x003E)
    b.word(0x4E41)
    b.word(0x588F)

    # Fdelete("C:\\MLP.TMP")
    b.label("cleanup_fail")
    b.pc_word(0x41FA, "temp_path")
    b.word(0x2F08)
    b.word(0x3F3C)
    b.word(0x0041)
    b.word(0x4E41)
    b.word(0x5C8F)  # ADDQ.L #6,SP

    # Pterm(1)
    b.label("fail")
    b.word(0x3F3C)
    b.word(0x0001)
    b.word(0x3F3C)
    b.word(0x004C)
    b.word(0x4E41)

    b.label("leaf")
    b.raw(MLP_LEAF)
    b.label("temp_path")
    b.raw(TEMP_PATH)
    b.label("open_path")
    b.raw(OPEN_PATH)
    b.label("request_frame")
    b.raw(REQUEST_FRAME)
    return b.finish()


def build_tos_prg() -> bytes:
    text = build_text()
    # GEMDOS executable header: magic, text, data, bss, symbols, reserved,
    # flags, absolute/no-relocation marker. The image uses only PC-relative data.
    header = struct.pack(">HLLLLLLH", 0x601A, len(text), 0, 0, 0, 0, 0, 1)
    return header + text


def build_receipt(image: bytes, source_head: str, source_tree: str) -> dict[str, object]:
    return {
        "schema": "qikvrt_mlp_tos_build_receipt_v1",
        "source_head": source_head,
        "source_tree": source_tree,
        "binary_path": "MLP.TOS/MLP.TOS",
        "binary_size": len(image),
        "binary_sha256": sha256_hex(image),
        "text_sha256": sha256_hex(build_text()),
        "m68000_leaf_hex": MLP_LEAF.hex(),
        "m68000_leaf_sha256": sha256_hex(MLP_LEAF),
        "request_frame_sha256": sha256_hex(REQUEST_FRAME),
        "request_path": "C:\\MLP.OPEN",
        "temporary_path": "C:\\MLP.TMP",
        "register_contract": {"D0": 3, "D1": 3, "D2": 1},
        "effect_boundary": {
            "state": "REQUESTED",
            "authority": "MISSING",
            "observed": False,
            "acknowledged": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--source-head", default="UNBOUND")
    parser.add_argument("--source-tree", default="UNBOUND")
    args = parser.parse_args()

    image = build_tos_prg()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    print(f"mlp_tos={args.output} bytes={len(image)} sha256={sha256_hex(image)}")

    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt = build_receipt(image, args.source_head, args.source_tree)
        args.receipt.write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(f"receipt={args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
