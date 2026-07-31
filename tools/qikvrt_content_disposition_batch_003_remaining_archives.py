#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Receipt-bound projection-precedence facade for the final corpus projector.

The historical corpus projector remains byte-identical in the adjacent legacy
module.  This facade delegates every materialization and check to it.  A legacy
check may be accepted only when its sole failure is the expected AI_STATUS.md
drift, the post-promotion handoff receipt is exact, and the newer anticipation
projection independently verifies.  No external effect is authorized here.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from typing import Any, Mapping, Sequence

from tools import qikvrt_content_disposition_batch_003_remaining_archives_legacy as _legacy
from tools.qikvrt_content_disposition_batch_003_remaining_archives_legacy import *  # noqa: F401,F403

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEGACY_MODULE = "tools.qikvrt_content_disposition_batch_003_remaining_archives_legacy"
HANDOFF_RECEIPT = ROOT / "receipts/anticipation/0003-post-promotion-current-main-handoff.json"
ANTICIPATION_TOOL = ROOT / "tools/qikvrt_anticipation.py"

_EXPECTED_LEGACY_DIAGNOSTIC: dict[str, Any] = {
    "effect_ack_done": False,
    "failure_class": "REMAINING_ARCHIVE_CONTENT_DISPOSITION_INVALID",
    "final_pass": False,
    "pass": False,
    "reason": "materialized output drift: AI_STATUS.md",
    "state": "BLOCK",
    "zenodo_mutation_authorized": False,
}
_EXPECTED_FALSE_EFFECT_FIELDS = (
    "authority_merge_performed",
    "doi_mutation_performed",
    "github_release_created",
    "ietf_datatracker_mutation_performed",
    "mirror_mutation_performed",
    "zenodo_mutation_performed",
)


class ProjectionPrecedenceError(RuntimeError):
    """Raised when the newer-status compatibility boundary is not exact."""


def _load_object(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionPrecedenceError(f"invalid handoff receipt: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectionPrecedenceError("handoff receipt must be an object")
    return value


def _validate_handoff_receipt() -> None:
    receipt = _load_object(HANDOFF_RECEIPT)
    if receipt.get("schema") != "qikvrt_post_promotion_current_main_handoff_receipt_v1":
        raise ProjectionPrecedenceError("handoff receipt schema drift")
    if receipt.get("effect") != "CREATE_POST_PROMOTION_CURRENT_MAIN_HANDOFF_CANDIDATE":
        raise ProjectionPrecedenceError("handoff receipt effect drift")
    if receipt.get("receipt_id") != (
        "post-promotion-current-main-handoff-authority-pr288-mirror-pr168-pr289-v1"
    ):
        raise ProjectionPrecedenceError("handoff receipt identity drift")
    claims = receipt.get("completion_claims")
    if not isinstance(claims, Mapping) or any(
        claims.get(key) is not False for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE")
    ):
        raise ProjectionPrecedenceError("handoff receipt completion-claim inflation")
    boundary = receipt.get("effect_boundary")
    if (
        not isinstance(boundary, Mapping)
        or boundary.get("repository_only") is not True
        or boundary.get("external_effect") != "NONE"
        or any(boundary.get(key) is not False for key in _EXPECTED_FALSE_EFFECT_FIELDS)
    ):
        raise ProjectionPrecedenceError("handoff receipt effect boundary drift")
    work_unit = receipt.get("selected_next_work_unit")
    if (
        not isinstance(work_unit, Mapping)
        or work_unit.get("id") != "CURRENT_MAIN_CHILD_PORT_OF_AUTHORITY_PR289"
        or work_unit.get("target_parent")
        != "6836f28622173e45b1330f41a294bbd46f36fec2"
    ):
        raise ProjectionPrecedenceError("handoff receipt work-unit binding drift")


def _parse_exact_legacy_diagnostic(completed: subprocess.CompletedProcess[str]) -> bool:
    candidates = (completed.stderr.strip(), completed.stdout.strip())
    for candidate in candidates:
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if value == _EXPECTED_LEGACY_DIAGNOSTIC:
            return True
    return False


def _run_legacy(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", LEGACY_MODULE, *arguments],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )


def _run_anticipation_check() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(ANTICIPATION_TOOL), "check"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )


def _relay(completed: subprocess.CompletedProcess[str]) -> None:
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)


def _compatible_newer_status(arguments: Sequence[str], legacy: subprocess.CompletedProcess[str]) -> bool:
    if "--check" not in arguments or "--materialize" in arguments:
        return False
    if not _parse_exact_legacy_diagnostic(legacy):
        return False
    try:
        _validate_handoff_receipt()
    except ProjectionPrecedenceError:
        return False
    anticipated = _run_anticipation_check()
    if anticipated.returncode != 0:
        return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        legacy = _run_legacy(arguments)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"BLOCK: legacy corpus projector could not execute: {exc}", file=sys.stderr)
        return 2
    if legacy.returncode == 0:
        _relay(legacy)
        return 0
    if not _compatible_newer_status(arguments, legacy):
        _relay(legacy)
        return legacy.returncode
    result = {
        "completion_claims": {
            "EFFECT_ACK_DONE": False,
            "FINAL_PASS": False,
            "PASS": False,
        },
        "external_effect": "NONE",
        "handoff_receipt": HANDOFF_RECEIPT.relative_to(ROOT).as_posix(),
        "legacy_projection_valid_except": "AI_STATUS.md",
        "schema": "qikvrt_projection_precedence_check_v1",
        "state": "NEWER_RECEIPT_BOUND_ANTICIPATION_STATUS_VALID",
    }
    if "--json" in arguments:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "VALID: newer receipt-bound anticipation status supersedes "
            "legacy AI_STATUS.md only"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
