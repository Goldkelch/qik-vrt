#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Audit Lean source escapes and `#print axioms` output for Wirkungsquadrat."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "WirkungsquadratKernel.lean"
KEY_THEOREMS = (
    "universal_action_square",
    "ellP_sq",
    "ellP_div_tP",
    "EP_div_pP",
    "ellP_mul_pP",
    "tP_mul_EP",
    "ellP_quantum_anchor",
    "ellP_gravitational_anchor",
    "gravitational_anchor_unique",
    "three_line_core",
)
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def strip_comments(text: str) -> str:
    out: list[str] = []
    depth = 0
    index = 0
    while index < len(text):
        if text.startswith("/-", index):
            depth += 1
            index += 2
            continue
        if depth and text.startswith("-/", index):
            depth -= 1
            index += 2
            continue
        if depth:
            index += 1
            continue
        if text.startswith("--", index):
            end = text.find("\n", index)
            if end == -1:
                break
            out.append("\n")
            index = end + 1
            continue
        out.append(text[index])
        index += 1
    if depth:
        raise SystemExit("BLOCK: unterminated Lean comment")
    return "".join(out)


def audit(log_path: pathlib.Path) -> dict[str, object]:
    source = strip_comments(SOURCE.read_text(encoding="utf-8"))
    forbidden = {
        "sorry": re.compile(r"\bsorry\b"),
        "admit": re.compile(r"\badmit\b"),
        "axiom": re.compile(r"^\s*axiom\b", re.MULTILINE),
        "constant": re.compile(r"^\s*constant\b", re.MULTILINE),
    }
    found_forbidden = [name for name, pattern in forbidden.items() if pattern.search(source)]
    if found_forbidden:
        raise SystemExit(f"BLOCK: forbidden proof escapes: {found_forbidden}")

    log = log_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\b(sorryAx|declaration uses 'sorry'|error:)\b", log, re.IGNORECASE):
        raise SystemExit("BLOCK: Lean log contains a proof escape or compiler error")

    records: dict[str, list[str]] = {}
    for theorem in KEY_THEOREMS:
        matching = [line for line in log.splitlines() if theorem in line and "axiom" in line.lower()]
        if not matching:
            raise SystemExit(f"BLOCK: no axiom-audit line for {theorem}")
        line = matching[-1]
        if "does not depend on any axioms" in line:
            records[theorem] = []
            continue
        match = re.search(r"depends on axioms:\s*\[([^\]]*)\]", line)
        if not match:
            raise SystemExit(f"BLOCK: unrecognized axiom report for {theorem}: {line}")
        axioms = [item.strip() for item in match.group(1).split(",") if item.strip()]
        extra = sorted(set(axioms) - ALLOWED_AXIOMS)
        if extra:
            raise SystemExit(f"BLOCK: non-allowlisted axioms for {theorem}: {extra}")
        records[theorem] = axioms

    return {
        "schema": "qikvrt_wirkungsquadrat_axiom_audit_v1",
        "status": "PASS",
        "source": str(SOURCE.relative_to(ROOT.parent.parent)),
        "proof_escape_count": 0,
        "allowlist": sorted(ALLOWED_AXIOMS),
        "theorems": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    result = audit(args.log)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
