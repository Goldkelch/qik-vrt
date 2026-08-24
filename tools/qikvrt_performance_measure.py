#!/usr/bin/env python3
"""Fail-closed before/after metric for issue #854 repair effectiveness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("metric input must be an object")
    return value


def count_blockers(snapshot: dict) -> int:
    zero_job = snapshot.get("zero_job_action_required_over_24h")
    stale = snapshot.get("stale_base_over_7d")
    if not isinstance(zero_job, int) or zero_job < 0:
        raise ValueError("zero_job_action_required_over_24h must be a non-negative integer")
    if not isinstance(stale, int) or stale < 0:
        raise ValueError("stale_base_over_7d must be a non-negative integer")
    return zero_job + stale


def evaluate(before: dict, after: dict) -> dict:
    b = count_blockers(before)
    a = count_blockers(after)
    gain = b - a
    return {
        "schema": "qikvrt_repair_performance_measure_v1",
        "before": b,
        "after": a,
        "gain": gain,
        "improvement_evidenced": gain > 0,
        "disposition": "IMPROVEMENT_EVIDENCED" if gain > 0 else "HOLD",
        "pass": False,
        "final_pass": False,
        "general_effect_ack_done": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = evaluate(load(args.before), load(args.after))
    Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
