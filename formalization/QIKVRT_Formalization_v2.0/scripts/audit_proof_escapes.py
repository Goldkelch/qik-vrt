#!/usr/bin/env python3
"""Reject Lean proof placeholders and project-level axiom declarations."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEAN_ROOT = ROOT / "QIKVRTFormalization"
FORBIDDEN_CODE = re.compile(r"\b(?:sorry|admit|axiom|constant)\b")


def strip_comments_and_strings(source: str) -> str:
    """Replace nested comments and strings with spaces while preserving lines."""
    output: list[str] = []
    index = 0
    block_depth = 0
    in_string = False
    escaped = False
    while index < len(source):
        current = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if block_depth:
            if current == "/" and following == "-":
                block_depth += 1
                output.extend("  ")
                index += 2
            elif current == "-" and following == "/":
                block_depth -= 1
                output.extend("  ")
                index += 2
            else:
                output.append("\n" if current == "\n" else " ")
                index += 1
            continue
        if in_string:
            output.append("\n" if current == "\n" else " ")
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                in_string = False
            index += 1
            continue
        if current == "-" and following == "-":
            while index < len(source) and source[index] != "\n":
                output.append(" ")
                index += 1
            continue
        if current == "/" and following == "-":
            block_depth = 1
            output.extend("  ")
            index += 2
            continue
        if current == '"':
            in_string = True
            output.append(" ")
            index += 1
            continue
        output.append(current)
        index += 1
    return "".join(output)


def lexical_violations(path: Path) -> list[str]:
    code = strip_comments_and_strings(path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for match in FORBIDDEN_CODE.finditer(code):
        line = code.count("\n", 0, match.start()) + 1
        violations.append(f"{path.relative_to(ROOT)}:{line}: forbidden `{match.group(0)}`")
    return violations


def main() -> int:
    files = sorted(LEAN_ROOT.rglob("*.lean"))
    violations = [item for path in files for item in lexical_violations(path)]
    for path in files:
        result = subprocess.run(
            ["lake", "env", "lean", "-E", "hasSorry", str(path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            violations.append(
                f"{path.relative_to(ROOT)}: Lean -E hasSorry failed:\n"
                f"{result.stdout}{result.stderr}"
            )
    if violations:
        for violation in violations:
            print(f"ERROR: {violation}", file=sys.stderr)
        return 1
    print(f"PASS proof-escape audit: {len(files)} Lean files; no sorry/admit/axiom/constant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
