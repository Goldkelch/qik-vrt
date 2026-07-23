#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed, read-only bootstrap for a fresh human or AI repository session."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "AI_CONTEXT.json"


class BootError(RuntimeError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BootError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BootError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise BootError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def run_read_only(command: list[str], label: str) -> None:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootError(f"{label} could not execute: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise BootError(f"{label} failed with exit {completed.returncode}: {detail}")
    output = completed.stdout.strip()
    if output:
        print(output)


def validate_required_read_order(context: dict[str, Any]) -> list[str]:
    order = context.get("required_read_order")
    if not isinstance(order, list) or not order:
        raise BootError("AI_CONTEXT.json.required_read_order must be a non-empty list")
    if not all(isinstance(item, str) and item for item in order):
        raise BootError("required_read_order contains an invalid path")
    missing = [item for item in order if not (ROOT / item).is_file()]
    if missing:
        raise BootError("required repository authorities are missing: " + ", ".join(missing))
    return order


def verify_repository_identity(context: dict[str, Any]) -> tuple[str, str]:
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, check=True,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        ).stdout.strip()
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootError(f"repository identity unavailable: {exc}") from exc
    if Path(top).resolve() != ROOT.resolve():
        raise BootError("bootloader is not executing at the repository root")
    canonical = context.get("project", {}).get("canonicality", {}).get("repositories", [])
    if not isinstance(canonical, list) or not canonical:
        raise BootError("canonical repository set is absent")
    return sha, ",".join(str(item) for item in canonical)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", default="all",
        choices=("core", "ietf", "formal", "audio", "publication", "all"),
        help="runtime profile to validate without installing or mutating state",
    )
    parser.add_argument(
        "--skip-runtime-check", action="store_true",
        help="validate repository handoff only; do not invoke bootstrap check-only",
    )
    args = parser.parse_args(argv)

    try:
        context = load_object(CONTEXT)
        if context.get("entrypoint") != "AI":
            raise BootError("AI_CONTEXT.json does not bind the root AI entrypoint")
        order = validate_required_read_order(context)
        sha, repositories = verify_repository_identity(context)

        run_read_only([sys.executable, "-B", "tools/ai_handoff.py"], "AI handoff validation")

        cache_validator = ROOT / "tools/qikvrt_tool_cache.py"
        if cache_validator.is_file():
            run_read_only(
                [sys.executable, "-B", str(cache_validator.relative_to(ROOT)), "verify"],
                "tool-cache coverage validation",
            )

        if not args.skip_runtime_check:
            bootstrap = ROOT / "tools/bootstrap-runtime.sh"
            if bootstrap.is_file():
                completed = subprocess.run(
                    ["sh", str(bootstrap.relative_to(ROOT)), "--check-only", "--profile", args.profile],
                    cwd=ROOT, check=False, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
                )
                if completed.returncode not in (0, 20):
                    detail = (completed.stderr or completed.stdout).strip()
                    raise BootError(
                        f"runtime check-only failed with exit {completed.returncode}: {detail}"
                    )
                print(f"RUNTIME_CHECK_EXIT={completed.returncode}")

        print("AI_BOOT_STATUS=READY")
        print(f"GIT_COMMIT={sha}")
        print(f"CANONICAL_REPOSITORIES={repositories}")
        print("READ_ORDER=" + " -> ".join(order))
        print(f"RUNTIME_PROFILE={args.profile}")
        print("NEXT_ACTION=Read the declared authorities, inspect task-relevant evidence, then execute only from verified repository state.")
        return 0
    except BootError as exc:
        print(f"AI_BOOT_BLOCK: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
