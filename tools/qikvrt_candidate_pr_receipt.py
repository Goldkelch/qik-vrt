#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate one exact draft pull-request candidate readback."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from collections.abc import Sequence
from typing import Any


SHA = re.compile(r"^[0-9a-f]{40}$")


def _sha(value: str, label: str) -> str:
    if not SHA.fullmatch(value):
        raise ValueError(f"{label} must be a 40-character lowercase SHA")
    return value


def candidate_provenance(repository: pathlib.Path, candidate_head: str) -> dict[str, Any]:
    """Read immutable commit/tree/parent facts for one locally available commit."""
    candidate_head = _sha(candidate_head, "expected head")

    def git(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(repository), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    resolved_head = git("rev-parse", "--verify", f"{candidate_head}^{{commit}}")
    tree = git("rev-parse", "--verify", f"{candidate_head}^{{tree}}")
    parent_line = git("rev-list", "--parents", "-n", "1", candidate_head)
    parts = parent_line.split()
    if not parts or parts[0] != resolved_head:
        raise ValueError("candidate ancestry readback does not bind the requested commit")
    return {
        "commit": _sha(resolved_head, "candidate commit"),
        "tree": _sha(tree, "candidate tree"),
        "parents": [_sha(parent, "candidate parent") for parent in parts[1:]],
    }


def validate_pr_readback(
    readback: dict[str, Any],
    *,
    expected_base: str,
    expected_head: str,
    expected_branch: str,
) -> tuple[dict[str, Any], int, str]:
    expected_base = _sha(expected_base, "expected base")
    expected_head = _sha(expected_head, "expected head")
    required = {
        "isDraft": True,
        "baseRefName": "main",
        "baseRefOid": expected_base,
        "headRefName": expected_branch,
        "headRefOid": expected_head,
    }
    observed = {key: readback.get(key) for key in required}
    if observed != required:
        raise ValueError(
            "draft candidate readback mismatch "
            + json.dumps({"required": required, "observed": observed}, sort_keys=True)
        )
    number = readback.get("number")
    url = readback.get("url")
    if not isinstance(number, int) or number < 1:
        raise ValueError("draft candidate readback has no positive pull-request number")
    if not isinstance(url, str) or not url.startswith("https://github.com/"):
        raise ValueError("draft candidate readback has no canonical GitHub URL")
    return required, number, url


def validate(
    readback: dict[str, Any],
    *,
    expected_base: str,
    expected_head: str,
    expected_branch: str,
    expected_tree: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    required, number, url = validate_pr_readback(
        readback,
        expected_base=expected_base,
        expected_head=expected_head,
        expected_branch=expected_branch,
    )
    expected_base = _sha(expected_base, "expected base")
    expected_head = _sha(expected_head, "expected head")
    expected_tree = _sha(expected_tree, "expected tree")

    expected_provenance = {
        "commit": expected_head,
        "tree": expected_tree,
        "parents": [expected_base],
    }
    observed_provenance = {
        "commit": provenance.get("commit"),
        "tree": provenance.get("tree"),
        "parents": provenance.get("parents"),
    }
    if observed_provenance != expected_provenance:
        raise ValueError(
            "draft candidate provenance mismatch "
            + json.dumps(
                {
                    "required": expected_provenance,
                    "observed": observed_provenance,
                },
                sort_keys=True,
            )
        )
    return {
        "state": "DRAFT_CANDIDATE_REOBSERVED",
        "pull_request": {"number": number, "url": url, **required},
        "candidate_commit": expected_provenance,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readback", required=True, type=pathlib.Path)
    parser.add_argument("--expected-base", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--repository", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--receipt", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.readback.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("pull-request readback must be a JSON object")
        validate_pr_readback(
            value,
            expected_base=args.expected_base,
            expected_head=args.expected_head,
            expected_branch=args.expected_branch,
        )
        result = validate(
            value,
            expected_base=args.expected_base,
            expected_head=args.expected_head,
            expected_branch=args.expected_branch,
            expected_tree=args.expected_tree,
            provenance=candidate_provenance(args.repository, args.expected_head),
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        result = {
            "state": "HOLD_UNVERIFIED",
            "first_blocker": str(exc),
            "next_action": "REOBSERVE_EXACT_DRAFT_CANDIDATE_PULL_REQUEST",
            "continuation_required": True,
        }
        exit_code = 2
    else:
        exit_code = 0
    raw = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(raw, encoding="utf-8")
    sys.stdout.write(raw)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
