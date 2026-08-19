#!/usr/bin/env python3
"""Exact reversible boundary for the QIK-VRT four-action M68000 ABI.

Forward:
    semantic action -> exact M68000 bytes
Reverse:
    exact M68000 bytes -> semantic action

The admitted machine words are exactly:
    7000 4e75  NOOP
    7001 4e75  HOLD
    7002 4e75  REOBSERVE
    7003 4e75  REQUEST_AUTHORITY

Each sequence is `MOVEQ #n,D0 ; RTS` on Motorola 68000.  No other byte
sequence is interpreted as a QIK-VRT action by this adapter.
"""
from __future__ import annotations

import argparse
import binascii
import json
import sys
from dataclasses import dataclass

ACTIONS = ("NOOP", "HOLD", "REOBSERVE", "REQUEST_AUTHORITY")
ACTION_TO_CODE = {
    "NOOP": bytes.fromhex("70004e75"),
    "HOLD": bytes.fromhex("70014e75"),
    "REOBSERVE": bytes.fromhex("70024e75"),
    "REQUEST_AUTHORITY": bytes.fromhex("70034e75"),
}
CODE_TO_ACTION = {code: action for action, code in ACTION_TO_CODE.items()}


@dataclass(frozen=True)
class RoundTrip:
    action: str
    machine_hex: str
    instruction: str
    register_result: int


def encode(action: str) -> bytes:
    try:
        return ACTION_TO_CODE[action]
    except KeyError as exc:
        raise ValueError(f"unsupported QIK-VRT action: {action}") from exc


def decode(code: bytes) -> str:
    try:
        return CODE_TO_ACTION[code]
    except KeyError as exc:
        raise ValueError("machine code is outside the exact four-action ABI") from exc


def describe(action: str) -> RoundTrip:
    code = encode(action)
    decoded = decode(code)
    if decoded != action:
        raise AssertionError("roundtrip invariant violated")
    n = ACTIONS.index(action)
    return RoundTrip(
        action=action,
        machine_hex=code.hex(),
        instruction=f"MOVEQ #{n},D0 ; RTS",
        register_result=n,
    )


def verify_bijection() -> list[RoundTrip]:
    if len(ACTION_TO_CODE) != 4 or len(CODE_TO_ACTION) != 4:
        raise AssertionError("four-action cardinality violated")
    rows = [describe(action) for action in ACTIONS]
    if len({row.machine_hex for row in rows}) != 4:
        raise AssertionError("machine-code uniqueness violated")
    return rows


def _parse_hex(value: str) -> bytes:
    compact = "".join(value.split()).lower()
    try:
        raw = binascii.unhexlify(compact)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid hexadecimal machine code") from exc
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--encode", choices=ACTIONS)
    group.add_argument("--decode", metavar="HEX")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.encode is not None:
            row = describe(args.encode)
            print(json.dumps(row.__dict__, sort_keys=True))
            return 0
        if args.decode is not None:
            code = _parse_hex(args.decode)
            action = decode(code)
            row = describe(action)
            if code != encode(action):
                raise AssertionError("reverse/forward byte identity violated")
            print(json.dumps(row.__dict__, sort_keys=True))
            return 0
        rows = verify_bijection()
        print(json.dumps([row.__dict__ for row in rows], sort_keys=True))
        return 0
    except (AssertionError, ValueError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
