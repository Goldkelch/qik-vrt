#!/usr/bin/env python3
"""Parse the exact PO-Receipt #226 IED grammar without conflating match and effect."""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / ".qikvrt" / "metagrammatik" / "IED_REGEX_GRAMMAR_V1.json"


def load_pattern() -> re.Pattern[str]:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    return re.compile(spec["regex"])


def classify(text: str) -> dict[str, object]:
    matched = load_pattern().fullmatch(text) is not None
    return {
        "schema": "qikvrt_ied_regex_parse_v1",
        "matched": matched,
        "state": "PARSED" if matched else "HOLD",
        "semantic_proof": False,
        "authority": False,
        "executed": False,
        "effect_ack": False,
    }


def main() -> int:
    text = sys.stdin.read().rstrip("\n")
    result = classify(text)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["matched"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
