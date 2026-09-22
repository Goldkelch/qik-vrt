#!/usr/bin/env python3
"""TEMDD v1 IR adapter.

The v0.1 language/parser remains unchanged. This adapter produces the v1
canonical IR envelope as an explicit successor representation.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.qikvrt_temdd import parse

SEMANTIC_CONTRACT = [
    "T13_CAUSAL_BINDING",
    "T14_EVIDENCE_NON_TRANSFER",
    "T15_EFFECT_CONSTRUCTION",
    "T16_CONFORMANCE_BINDING",
]

def adapt(text: str) -> dict:
    old = parse(text)
    return {
        "schema": "temdd_ir_v1",
        "ir_version": "1",
        "language_version": old["version"],
        "authority": old["authority"],
        "subject": old["subject"],
        "request": old["request"],
        "handlers": old["handlers"],
        "dod": old["dod"],
        "semantic_contract": list(SEMANTIC_CONTRACT),
    }

def main(argv) -> int:
    if len(argv) != 2:
        return 64
    try:
        ir = adapt(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("BLOCK " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(ir, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
