#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed decision core for expected-head-bound QIK-VRT promotion.

This module intentionally does not mutate GitHub. It evaluates an exact live
snapshot and returns either PROMOTABLE or the first deterministic blocker.
The GitHub workflow is responsible for reobserving the same head/base again
immediately before changing draft state or merging.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Iterable, Mapping, Sequence

PROMOTION_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
SUCCESS_CONCLUSIONS = {"success"}
NON_ADVERSE_CONCLUSIONS = {"success", "skipped"}


class PromotionBlock(ValueError):
    """Raised when a snapshot is structurally invalid rather than merely blocked."""


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise PromotionBlock(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise PromotionBlock(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _run_number(run: Mapping[str, Any]) -> int:
    value = run.get("run_number", -1)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PromotionBlock("workflow run_number must be an integer")
    return value


def collapse_latest_runs(runs: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Return the newest run per workflow name.

    Trusted exact-head proxy execution can legitimately supersede an older
    action_required/zero-job registration on the same commit. Promotion must
    therefore use the newest observed execution for each workflow name rather
    than treating historical registrations as permanently adverse.
    """
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        if not isinstance(run, Mapping):
            raise PromotionBlock("workflow run must be an object")
        name = run.get("name")
        if not isinstance(name, str) or not name:
            raise PromotionBlock("workflow run name is missing")
        current = latest.get(name)
        if current is None or _run_number(run) > _run_number(current):
            latest[name] = run
    return latest


def _blocked(snapshot: Mapping[str, Any], failure_class: str, detail: str) -> dict[str, Any]:
    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "BLOCK",
        "first_blocker": failure_class,
        "detail": detail,
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": snapshot.get("expected_head_sha"),
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
        },
    }


def evaluate_promotion(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one promotion candidate against the live fail-closed contract."""
    if not isinstance(snapshot, Mapping):
        raise PromotionBlock("snapshot must be an object")

    current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    expected_head = _sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    current_head = _sha(snapshot.get("current_head_sha"), "current_head_sha")

    if current_main != base:
        return _blocked(snapshot, "BASE_DRIFT", f"current main {current_main} != candidate base {base}")
    if current_head != expected_head:
        return _blocked(snapshot, "HEAD_DRIFT", f"current head {current_head} != expected head {expected_head}")
    if snapshot.get("mergeable") is not True:
        return _blocked(snapshot, "NOT_MERGEABLE", "candidate is not currently mergeable")
    if snapshot.get("external_effect") != "NONE":
        return _blocked(snapshot, "EXTERNAL_EFFECT_BOUNDARY", "candidate crosses an external-effect boundary")

    overlaps = snapshot.get("competing_writer_overlaps", [])
    if not isinstance(overlaps, list):
        raise PromotionBlock("competing_writer_overlaps must be a list")
    if overlaps:
        return _blocked(snapshot, "COMPETING_WRITER_OVERLAP", f"overlapping open writer(s): {overlaps}")

    required = snapshot.get("required_gates")
    if not isinstance(required, list) or not required or not all(
        isinstance(name, str) and name for name in required
    ):
        raise PromotionBlock("required_gates must be a non-empty list of names")
    runs = snapshot.get("workflow_runs")
    if not isinstance(runs, list):
        raise PromotionBlock("workflow_runs must be a list")
    latest = collapse_latest_runs(runs)

    for gate in required:
        run = latest.get(gate)
        if run is None:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_MISSING", f"required workflow is absent: {gate}")
        if run.get("status") != "completed":
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_TERMINAL", f"required workflow is not terminal: {gate}")
        if run.get("conclusion") not in SUCCESS_CONCLUSIONS:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN", f"required workflow is not successful: {gate}={run.get('conclusion')}")

    for name, run in sorted(latest.items()):
        if name in required:
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_TERMINAL", f"workflow is not terminal: {name}")
        if conclusion not in NON_ADVERSE_CONCLUSIONS:
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_GREEN", f"workflow is adverse: {name}={conclusion}")

    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "PROMOTABLE",
        "first_blocker": None,
        "detail": "all exact-head promotion conditions are satisfied",
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": expected_head,
        "current_main_sha": current_main,
        "latest_workflows": {
            name: {
                "run_number": _run_number(run),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
            }
            for name, run in sorted(latest.items())
        },
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
        },
    }


def _load_snapshot(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise PromotionBlock("snapshot JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate",))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        result = evaluate_promotion(_load_snapshot(args.input))
    except (OSError, ValueError, json.JSONDecodeError, PromotionBlock) as exc:
        result = {
            "schema": "qikvrt_expected_head_promotion_decision_v1",
            "state": "BLOCK",
            "first_blocker": "INVALID_PROMOTION_SNAPSHOT",
            "detail": str(exc),
            "external_effect": "NONE",
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") == "PROMOTABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
