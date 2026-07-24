#!/usr/bin/env python3
"""Axiom-audit every completed manuscript proof constant from the claim graph."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import materialize_completion as completion

ROOT = completion.PROJECT_ROOT
GRAPH = completion.DEFAULT_GRAPH
FOUNDATIONAL = {"propext", "Classical.choice", "Quot.sound"}
AUDIT_SOURCE = ROOT / ".lake" / "build" / "AxiomAuditCompletion.lean"


def main() -> int:
    try:
        graph = json.loads(GRAPH.read_text(encoding="utf-8"))
        constants = sorted({
            node["formalBinding"]["proofConstant"]
            for node in graph["nodes"]
            if node.get("formalBinding") is not None
        })
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot build completion axiom audit: {exc}", file=sys.stderr)
        return 1
    if len(constants) != 42:
        print(f"ERROR: expected 42 proof constants, got {len(constants)}", file=sys.stderr)
        return 1

    AUDIT_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_SOURCE.write_text(
        "import QIKVRTFormalization\n\n" +
        "\n".join(f"#print axioms {constant}" for constant in constants) + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["lake", "env", "lean", str(AUDIT_SOURCE)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        print(output, file=sys.stderr)
        return result.returncode

    pattern = re.compile(
        r"^'(?P<name>[^']+)' (?:does not depend on any axioms|"
        r"depends on axioms: \[(?P<axioms>[^]]*)\])$"
    )
    seen: set[str] = set()
    violations: list[str] = []
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if not match or match.group("name") not in constants:
            continue
        name = match.group("name")
        seen.add(name)
        axioms = {
            item.strip()
            for item in (match.group("axioms") or "").split(",")
            if item.strip()
        }
        unexpected = axioms - FOUNDATIONAL
        if unexpected:
            violations.append(f"{name}: forbidden axioms {sorted(unexpected)}")
    missing = set(constants) - seen
    if missing:
        violations.append(f"missing axiom reports: {sorted(missing)}")
    if violations:
        for violation in violations:
            print(f"ERROR: {violation}", file=sys.stderr)
        return 1
    print(
        "PASS completion axiom audit: 42 source-bound proof constants; "
        "only Lean/Std foundational axioms"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
