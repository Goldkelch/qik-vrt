#!/usr/bin/env python3
"""Run Lean's axiom printer and reject undeclared proof dependencies."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SOURCE = ROOT / "QIKVRTFormalization" / "Claims" / "AxiomAuditAll.lean"
EXPECTED = {
    "QIKVRT.V2.Class.SET001_checked",
    "QIKVRT.V2.Class.MAP001_checked",
    "QIKVRT.V2.QUA003A_prefix_checked",
    "QIKVRT.V2.Class.SET003_checked",
    "QIKVRT.V2.Class.MAP003_checked",
    "QIKVRT.V2.GAT004_checked",
    "QIKVRT.V2.GAT005_checked",
    "QIKVRT.V2.GAT006_checked",
    "QIKVRT.V2.RET011_checked",
    "QIKVRT.V2.GAT002_checked",
    "QIKVRT.V2.DIM006A_additive_checked",
    "QIKVRT.V2.DIM007A_countermodel_checked",
}
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}


def main() -> int:
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

    seen: set[str] = set()
    violations: list[str] = []
    line_pattern = re.compile(
        r"^'(?P<name>[^']+)' (?:does not depend on any axioms|"
        r"depends on axioms: \[(?P<axioms>[^]]*)\])$"
    )
    for line in output.splitlines():
        match = line_pattern.match(line.strip())
        if not match:
            continue
        name = match.group("name")
        if name not in EXPECTED:
            continue
        seen.add(name)
        raw_axioms = match.group("axioms")
        axioms = {
            item.strip() for item in (raw_axioms or "").split(",") if item.strip()
        }
        unexpected = axioms - ALLOWED
        if unexpected:
            violations.append(f"{name}: forbidden axioms {sorted(unexpected)}")

    missing = EXPECTED - seen
    if missing:
        violations.append(f"missing axiom reports: {sorted(missing)}")
    if violations:
        for violation in violations:
            print(f"ERROR: {violation}", file=sys.stderr)
        return 1

    allowed_text = ", ".join(sorted(ALLOWED)) if ALLOWED else "none"
    print(f"PASS axiom audit: 12 checked theorems; allowed axioms: {allowed_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
