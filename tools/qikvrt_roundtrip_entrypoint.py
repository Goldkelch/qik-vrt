#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI ChatGPT.
"""Prepend one discoverable Roundtrip entry without replacing existing instructions."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = ("README.md", "AI", "AGENTS.md", "next/README.md", "next/AI")
START = b"<!-- qikvrt-roundtrip-first:v1 -->\n"
END = b"<!-- /qikvrt-roundtrip-first:v1 -->\n\n"


def prefix(relative: str) -> bytes:
    link = "../" if relative.startswith("next/") else ""
    return (START + (
        "## Zuerst: ausfuehrbarer Roundtrip-Beweis / Start here\n\n"
        f"Read [{link}ROUNDTRIP.md]({link}ROUNDTRIP.md) first. "
        f"The executable entrypoint is [{link}roundtrip.py]({link}roundtrip.py).\n"
        "From the repository root, with the locked target toolchain available:\n\n"
        "```sh\n"
        "python3 -B roundtrip.py --repository Goldkelch/qik-vrt --output-dir ../roundtrip-evidence\n"
        "```\n\n"
        "Use this checkout's actual owner/repository for a Mirror or fork. "
        "Choose a new output directory for every execution. "
        "The runner calls the existing exact-HEAD/TREE suite: C90, bus, store, "
        "restart, byte-preserving source recovery and rebuild. "
        "Runner presence is not execution evidence. The prime-search experiment "
        "has a separate, currently missing original-artifact binding; it is not "
        "replaced by this suite. Existing instructions follow unchanged.\n\n"
    ).encode("utf-8") + END)


def materialize(root: Path, *, check: bool) -> list[str]:
    pending = []
    for relative in PATHS:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"ENTRYPOINT_MISSING_OR_UNSAFE: {relative}")
        raw = path.read_bytes()
        block = prefix(relative)
        if raw.startswith(block):
            continue
        if START in raw or END in raw:
            raise ValueError(f"CONFLICTING_ENTRYPOINT_PREFIX: {relative}")
        pending.append((path, block + raw))
    if check and pending:
        raise ValueError("ROUNDTRIP_NOT_FIRST: " + ", ".join(str(p.relative_to(root)) for p, _ in pending))
    if not check:
        for path, raw in pending:
            path.write_bytes(raw)
    return [str(path.relative_to(root)) for path, _ in pending]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        changed = materialize(ROOT, check=args.check)
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + "\n")
    print("ENTRYPOINT_CHECK_PASS" if args.check else "ENTRYPOINTS_MATERIALIZED: " + ", ".join(changed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
