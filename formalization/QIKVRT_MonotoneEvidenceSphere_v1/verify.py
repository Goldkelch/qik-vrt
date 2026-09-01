#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed static and audit verifier for the evidence-sphere Lean core."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent
MODEL = ROOT / "QIKVRTMonotoneEvidenceSphere.lean"
AUDIT = ROOT / "QIKVRTMonotoneEvidenceSphereAxiomAudit.lean"
TOOLCHAIN = ROOT / "lean-toolchain"
SCOPE = ROOT / "PROOF_SCOPE.json"

PREFIX = "QIKVRT.MonotoneEvidenceSphere."
THEOREMS = [
    "MES_T01_append_core_monotone",
    "MES_T02_append_history_monotone",
    "MES_T03_append_preserves_sealed_history",
    "MES_T04_append_membership_monotone",
    "MES_T05_append_alpha_cut_monotone",
    "MES_T06_append_mass_monotone",
    "MES_T07_append_radius_strict_growth",
    "MES_T08_step_core_monotone",
    "MES_T09_step_history_monotone",
    "MES_T10_step_preserves_sealed_history",
    "MES_T11_control_code_fits_nibble",
    "MES_T12_control_code_injective",
    "MES_T13_no_new_relation_selects_hold",
    "MES_T14_no_new_relation_is_local_fixed_point",
    "MES_T15_genuinely_new_relation_selects_append",
    "MES_T16_genuinely_new_relation_is_appended",
    "MES_T17_genuinely_new_relation_strictly_grows_radius",
]
ALLOWED_FOUNDATIONAL_AXIOMS = {"propext", "Quot.sound", "Classical.choice"}


class VerificationError(RuntimeError):
    """A precise declared verification condition was not met."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_shape() -> dict[str, Any]:
    model = MODEL.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    observed_theorems = re.findall(r"(?m)^theorem\s+([A-Za-z0-9_]+)", model)
    observed_audits = re.findall(
        r"(?m)^#print axioms\s+([A-Za-z0-9_]+)\s*$", audit
    )
    require(observed_theorems == THEOREMS, "Lean theorem inventory differs")
    require(observed_audits == THEOREMS, "axiom audit inventory differs")
    require(
        TOOLCHAIN.read_text(encoding="utf-8").strip()
        == "leanprover/lean4:v4.19.0",
        "Lean toolchain is not pinned to 4.19.0",
    )
    combined = model + "\n" + audit
    forbidden = {
        "project axiom": r"(?m)^\s*axiom\b",
        "unsafe declaration": r"(?m)^\s*unsafe\b",
        "proof hole": r"(?m)\b(?:sorry|admit)\b",
    }
    for label, pattern in forbidden.items():
        require(re.search(pattern, combined) is None, f"forbidden {label} found")
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    require(
        scope.get("schema") == "qikvrt.monotone-evidence-sphere-proof-scope.v1",
        "proof-scope schema differs",
    )
    require(
        scope.get("attribution", {}).get("originator") == "Ingolf Lohmann",
        "proof-scope originator binding differs",
    )
    artifact = scope.get("historical_artifact", {})
    require(
        artifact.get("sha256")
        == "38b0e62a46214a7cb9943dd3ef08283a70ae7e15ba22a59a9e53506f2945e311",
        "historical evidence-sphere binding differs",
    )
    require(
        scope.get("state") == "CANDIDATE_AWAITING_EXACT_HEAD_LEAN_RECEIPT",
        "proof-scope state was promoted without a fresh receipt",
    )
    return {
        "toolchain": "leanprover/lean4:v4.19.0",
        "theorem_count": len(THEOREMS),
        "theorems": THEOREMS,
        "model_sha256": sha256(MODEL),
        "axiom_audit_sha256": sha256(AUDIT),
        "proof_scope_sha256": sha256(SCOPE),
    }


def parse_axiom_output(path: pathlib.Path) -> dict[str, list[str]]:
    reports: dict[str, list[str]] = {}
    no_axioms = re.compile(r"^'([^']+)' does not depend on any axioms$")
    with_axioms = re.compile(r"^'([^']+)' depends on axioms: \[(.*)\]$")
    logical_lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw[:1].isspace():
            require(
                bool(logical_lines)
                and " depends on axioms: [" in logical_lines[-1]
                and not logical_lines[-1].rstrip().endswith("]"),
                f"unexpected wrapped axiom-audit output: {raw!r}",
            )
            logical_lines[-1] += raw.strip()
        else:
            logical_lines.append(raw)
    for raw in logical_lines:
        line = raw.strip()
        if not line:
            continue
        match = no_axioms.fullmatch(line)
        if match is not None:
            reports[match.group(1)] = []
            continue
        match = with_axioms.fullmatch(line)
        if match is not None:
            reports[match.group(1)] = [
                part.strip() for part in match.group(2).split(",") if part.strip()
            ]
            continue
        raise VerificationError(f"unexpected axiom-audit output: {line!r}")
    expected = [PREFIX + name for name in THEOREMS]
    require(list(reports) == expected, "axiom output has a different theorem order or inventory")
    unexpected = sorted(
        {axiom for values in reports.values() for axiom in values}
        - ALLOWED_FOUNDATIONAL_AXIOMS
    )
    require(not unexpected, f"unexpected project axiom dependencies: {unexpected}")
    return reports


def receipt(
    source: dict[str, Any], reports: dict[str, list[str]], args: argparse.Namespace
) -> dict[str, Any]:
    assert args.head is not None
    assert args.tree is not None
    assert args.repository is not None
    assert args.run_id is not None
    assert args.run_attempt is not None
    return {
        "schema": "qikvrt.monotone-evidence-sphere-lean-receipt.v1",
        "repository": args.repository,
        "source_commit": args.head,
        "source_tree": args.tree,
        "workflow_run_id": args.run_id,
        "workflow_run_attempt": args.run_attempt,
        "lean_toolchain": source["toolchain"],
        "model": {
            "path": MODEL.name,
            "sha256": source["model_sha256"],
            "bytes": MODEL.stat().st_size,
        },
        "axiom_audit": {
            "path": AUDIT.name,
            "sha256": source["axiom_audit_sha256"],
            "bytes": AUDIT.stat().st_size,
        },
        "proof_scope": {
            "path": SCOPE.name,
            "sha256": source["proof_scope_sha256"],
            "bytes": SCOPE.stat().st_size,
        },
        "axiom_output": {
            "path": args.axiom_output.name,
            "sha256": sha256(args.axiom_output),
            "bytes": args.axiom_output.stat().st_size,
        },
        "theorem_count": source["theorem_count"],
        "axioms_by_theorem": reports,
        "allowed_foundational_axioms": sorted(ALLOWED_FOUNDATIONAL_AXIOMS),
        "formal_result": "APPEND_ONLY_EVIDENCE_SPHERE_MODEL_VERIFIED",
        "formal_scope": [
            "accepted-core monotonicity",
            "sealed-history preservation",
            "natural membership, mass and radius monotonicity",
            "four-control four-bit model code",
            "model-local admission fixed point for a supplied no-new-relation input",
            "fresh-relation admission to the declared append path",
        ],
        "not_established": [
            "physical-sphere correspondence",
            "quantum-field correspondence",
            "human agency claim",
            "hardware synthesis or bitstream",
            "physical FPGA execution",
            "performance or energy result",
            "repository completion, merge or publication",
        ],
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--axiom-output", type=pathlib.Path)
    parser.add_argument("--write-receipt", type=pathlib.Path)
    parser.add_argument("--head")
    parser.add_argument("--tree")
    parser.add_argument("--repository")
    parser.add_argument("--run-id")
    parser.add_argument("--run-attempt")
    args = parser.parse_args(argv)
    try:
        source = source_shape()
        result: dict[str, Any] = {"source": source, "result": "SOURCE_SHAPE_VALID"}
        if args.axiom_output is not None:
            require(args.axiom_output.is_file(), "axiom-output file is missing")
            reports = parse_axiom_output(args.axiom_output)
            result["axioms_by_theorem"] = reports
            result["result"] = "LEAN_AXIOM_AUDIT_VALID"
            if args.write_receipt is not None:
                payload = receipt(source, reports, args)
                canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                payload["receipt_payload_sha256"] = hashlib.sha256(canonical).hexdigest()
                args.write_receipt.parent.mkdir(parents=True, exist_ok=True)
                args.write_receipt.write_text(
                    json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
                )
                result["receipt"] = str(args.write_receipt)
        elif args.write_receipt is not None:
            raise VerificationError("--write-receipt requires --axiom-output")
        print(json.dumps(result, sort_keys=True, indent=2))
    except VerificationError as error:
        print(f"BLOCK {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
