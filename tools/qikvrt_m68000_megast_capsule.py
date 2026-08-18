#!/usr/bin/env python3
"""Build the minimal QIK-VRT M68000 decision capsule and Atari TOS program.

The executable core is deliberately tiny. QIK-VRT identity, causal and evidence
metadata stay outside executable authority in a deterministic sidecar capsule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

MAGIC = b"QIKM68K1"
SENTINEL_PATH = b"C:\\QIKVRT.OK\0"
ACTIONS = {"NOOP": 0, "HOLD": 1, "REOBSERVE": 2, "REQUEST_AUTHORITY": 3}


def decision_code(action: int) -> bytes:
    if action not in range(4):
        raise ValueError("unsupported QIK M68000 action")
    # MOVEQ #action,D0 ; RTS
    return struct.pack(">HH", 0x7000 | action, 0x4E75)


def tos_text(action: int) -> bytes:
    if action not in range(4):
        raise ValueError("unsupported QIK M68000 action")
    # Observable TOS wrapper. A host-visible sentinel is created only after
    # the hardwired capsule has executed and returned successfully.
    #
    #   BSR.S capsule
    #   LEA filename(PC),A0
    #   MOVE.W #0,-(SP) ; MOVE.L A0,-(SP) ; MOVE.W #$3C,-(SP) ; TRAP #1
    #   MOVE.W D0,-(SP) ; MOVE.W #$3E,-(SP) ; TRAP #1
    #   MOVE.W #0,-(SP) ; MOVE.W #$4C,-(SP) ; TRAP #1
    # capsule: MOVEQ #action,D0 ; RTS
    # filename: "C:\\QIKVRT.OK\0"
    #
    # M68000 PC-relative d16 addressing uses the extension-word address as
    # the PC base. The filename begins at byte offset 40 and the LEA extension
    # word is at offset 4, therefore d16 = 36 = 0x0024.
    words = (
        0x6122,
        0x41FA, 0x0024,
        0x3F3C, 0x0000,
        0x2F08,
        0x3F3C, 0x003C,
        0x4E41,
        0x3F00,
        0x3F3C, 0x003E,
        0x4E41,
        0x3F3C, 0x0000,
        0x3F3C, 0x004C,
        0x4E41,
        0x7000 | action,
        0x4E75,
    )
    return struct.pack(">" + "H" * len(words), *words) + SENTINEL_PATH


def tos_prg(action: int) -> bytes:
    text = tos_text(action)
    # Atari GEMDOS executable header: magic, text, data, bss, symbols,
    # reserved, flags, absolute/no-relocation marker.
    header = struct.pack(">HLLLLLLH", 0x601A, len(text), 0, 0, 0, 0, 0, 1)
    return header + text


def digest_bytes(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def capsule(action_name: str, metadata: dict[str, str]) -> bytes:
    action = ACTIONS[action_name]
    code = decision_code(action)
    fields = [
        metadata["source_binding"],
        metadata["causal_graph"],
        metadata["authority"],
        metadata["evidence"],
        metadata["role_identity"],
    ]
    payload = b"".join(digest_bytes(x) for x in fields)
    # magic + version + action + code length + metadata digest block + code
    return MAGIC + struct.pack(">BBH", 1, action, len(code)) + payload + code


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--action", choices=ACTIONS, required=True)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--capsule", type=Path, required=True)
    p.add_argument("--tos-prg", type=Path, required=True)
    args = p.parse_args()
    meta = json.loads(args.metadata.read_text(encoding="utf-8"))
    required = {"source_binding", "causal_graph", "authority", "evidence", "role_identity"}
    if set(meta) != required or not all(isinstance(meta[k], str) and meta[k] for k in required):
        raise SystemExit("HOLD: incomplete or non-canonical QIK metadata")
    args.capsule.write_bytes(capsule(args.action, meta))
    args.tos_prg.write_bytes(tos_prg(ACTIONS[args.action]))
    print(f"action={args.action} capsule={args.capsule} tos_prg={args.tos_prg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
