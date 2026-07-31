#!/usr/bin/env python3
"""Run Lean's axiom printer and reject undeclared proof dependencies."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_AUDIT_SOURCE = (
    ROOT / "QIKVRTFormalization" / "Claims" / "AxiomAuditAll.lean"
)
MANUSCRIPT_EXPECTED = {
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
EFFECT_ACK_AUDIT_SOURCE = ROOT / "QIKVRTEffectAck" / "AxiomAudit.lean"
EFFECT_ACK_MATRIX = ROOT / "effect_ack" / "DRAFT01_CLAIM_MATRIX.json"
FOUNDATIONAL_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
EFFECT_ACK_SUPPLEMENTAL = {
    "QIKVRT.EffectAck.V1.Claims.claimIds_count": set(),
    "QIKVRT.EffectAck.V1.Claims.claimIds_pairwise": set(),
}


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def effect_ack_policy() -> dict[str, set[str]]:
    matrix = require_object(
        json.loads(EFFECT_ACK_MATRIX.read_text(encoding="utf-8")),
        "claim matrix",
    )
    claims = matrix.get("claims")
    if not isinstance(claims, list):
        raise ValueError("claim matrix claims must be an array")
    constants: set[str] = set()
    for index, raw_claim in enumerate(claims):
        claim = require_object(raw_claim, f"claim {index}")
        raw_constants = claim.get("proof_constants", [])
        if not isinstance(raw_constants, list):
            raise ValueError(f"claim {index} proof_constants must be an array")
        claim_constants = list(raw_constants)
        registry = claim.get("registry_constant")
        if registry is not None:
            claim_constants.append(registry)
        for constant in claim_constants:
            if not isinstance(constant, str) or not constant:
                raise ValueError(f"claim {index} contains an invalid constant")
            constants.add(constant)
    constants.update(EFFECT_ACK_SUPPLEMENTAL)

    raw_axiom_policy = require_object(
        matrix.get("axiom_policy"),
        "axiom_policy",
    )
    foundational = raw_axiom_policy.get("foundational_allowlist")
    if not isinstance(foundational, list) or set(foundational) != FOUNDATIONAL_AXIOMS:
        raise ValueError("foundational_allowlist does not match the locked policy")
    raw_default = raw_axiom_policy.get("default_expected_axioms")
    if not isinstance(raw_default, list) or not all(
        isinstance(item, str) and item for item in raw_default
    ):
        raise ValueError("default_expected_axioms must be an array of strings")
    default = set(raw_default)
    if default - FOUNDATIONAL_AXIOMS:
        raise ValueError("default_expected_axioms contains forbidden axioms")
    raw_overrides = require_object(
        raw_axiom_policy.get("per_constant_expected_axioms"),
        "per_constant_expected_axioms",
    )
    unknown_constants = set(raw_overrides) - constants
    if unknown_constants:
        raise ValueError(
            f"axiom policy names unknown constants {sorted(unknown_constants)}"
        )
    policy: dict[str, set[str]] = {}
    for constant in constants:
        raw_allowed = raw_overrides.get(constant, raw_default)
        if not isinstance(raw_allowed, list) or not all(
            isinstance(item, str) and item for item in raw_allowed
        ):
            raise ValueError(f"{constant} axiom policy must be strings")
        allowed = set(raw_allowed)
        unknown = allowed - FOUNDATIONAL_AXIOMS
        if unknown:
            raise ValueError(f"{constant} declares forbidden axioms {sorted(unknown)}")
        policy[constant] = allowed

    expected_lines = {f"#print axioms {name}" for name in policy}
    actual_lines = {
        line.strip()
        for line in EFFECT_ACK_AUDIT_SOURCE.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("#print axioms ")
    }
    if actual_lines != expected_lines:
        missing = sorted(expected_lines - actual_lines)
        extra = sorted(actual_lines - expected_lines)
        raise ValueError(
            f"generated EFFECT_ACK audit drift; missing={missing}, extra={extra}"
        )
    return policy


def main() -> int:
    try:
        effect_policy = effect_ack_policy()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid EFFECT_ACK axiom policy: {exc}", file=sys.stderr)
        return 1
    manuscript_policy = {
        name: set(FOUNDATIONAL_AXIOMS) for name in MANUSCRIPT_EXPECTED
    }
    audits = (
        (MANUSCRIPT_AUDIT_SOURCE, manuscript_policy, False),
        (EFFECT_ACK_AUDIT_SOURCE, effect_policy, True),
    )
    seen: set[str] = set()
    violations: list[str] = []
    line_pattern = re.compile(
        r"^'(?P<name>[^']+)' (?:does not depend on any axioms|"
        r"depends on axioms: \[(?P<axioms>[^]]*)\])$"
    )
    expected = set().union(*(policy for _, policy, _ in audits))
    for audit_source, audit_policy, require_exact in audits:
        result = subprocess.run(
            ["lake", "env", "lean", str(audit_source)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            print(output, file=sys.stderr)
            return result.returncode
        for line in output.splitlines():
            match = line_pattern.match(line.strip())
            if not match:
                continue
            name = match.group("name")
            if name not in audit_policy:
                continue
            seen.add(name)
            raw_axioms = match.group("axioms")
            axioms = {
                item.strip()
                for item in (raw_axioms or "").split(",")
                if item.strip()
            }
            unexpected = axioms - audit_policy[name]
            if unexpected:
                violations.append(
                    f"{name}: forbidden axioms {sorted(unexpected)}"
                )
            elif require_exact and axioms != audit_policy[name]:
                violations.append(
                    f"{name}: actual axioms {sorted(axioms)} do not equal "
                    f"declared {sorted(audit_policy[name])}"
                )

    missing = expected - seen
    if missing:
        violations.append(f"missing axiom reports: {sorted(missing)}")
    if violations:
        for violation in violations:
            print(f"ERROR: {violation}", file=sys.stderr)
        return 1

    print(
        f"PASS axiom audit: {len(expected)} checked theorems; "
        f"{len(effect_policy)} EFFECT_ACK constants use per-claim policies"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
