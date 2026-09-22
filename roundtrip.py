#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI ChatGPT.
"""Run the existing exact-subject C90/store/source Roundtrip checks, not a demo."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "next/tools/run_checks.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="Exact owner/repository of this checkout")
    parser.add_argument("--output-dir", type=Path, required=True, help="New evidence directory outside the checkout")
    parser.add_argument("--cargo", default=os.environ.get("QIKVRT_CARGO", "cargo"))
    parser.add_argument("--ghdl", default=os.environ.get("QIKVRT_GHDL", "ghdl"))
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("EXACT_REPOSITORY_REQUIRED: use owner/repository")
    if sys.flags.optimize or os.environ.get("PYTHONOPTIMIZE", "") not in ("", "0"):
        parser.error("ASSERTIONS_REQUIRED: do not use -O, -OO or PYTHONOPTIMIZE")
    if not RUNNER.is_file() or RUNNER.is_symlink():
        parser.error("ROUNDTRIP_RUNNER_MISSING: no fallback or historical PASS")
    output = args.output_dir.resolve()
    if output == ROOT or ROOT in output.parents or output.exists():
        parser.error("NEW_EXTERNAL_EVIDENCE_DIRECTORY_REQUIRED")
    command = [sys.executable, "-B", str(RUNNER), "--output-dir", str(output),
               "--cargo", args.cargo, "--ghdl", args.ghdl]
    if args.offline:
        command.append("--offline")
    env = dict(os.environ, GITHUB_REPOSITORY=args.repository, PYTHONDONTWRITEBYTECODE="1")
    try:
        return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode
    except OSError as exc:
        print(f"ROUNDTRIP_EXECUTION_FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
