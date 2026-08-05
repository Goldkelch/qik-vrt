#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Create a source- and execution-bound QCE Lean kernel receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parent
MODEL = ROOT / "VRTCore_QCE_Model.lean"
AUDIT = ROOT / "VRTCore_QCE_AxiomAudit.lean"


class ReceiptError(RuntimeError):
    pass


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        raise ReceiptError(
            f"command failed ({proc.returncode}): {' '.join(command)}\n{proc.stdout}"
        )
    return proc.stdout


def parse_axioms(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    no_axioms = re.compile(r"^'([^']+)' does not depend on any axioms$")
    with_axioms = re.compile(r"^'([^']+)' depends on axioms: \[(.*)\]$")
    for line in text.splitlines():
        match = no_axioms.match(line.strip())
        if match:
            result[match.group(1)] = []
            continue
        match = with_axioms.match(line.strip())
        if match:
            result[match.group(1)] = [
                item.strip() for item in match.group(2).split(",") if item.strip()
            ]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", type=pathlib.Path, required=True)
    parser.add_argument("--axiom-output", type=pathlib.Path, required=True)
    parser.add_argument("--verification-output", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "UNKNOWN"))
    parser.add_argument("--commit", default=os.environ.get("GITHUB_SHA", "UNKNOWN"))
    parser.add_argument("--tree", default="UNRESOLVED_BY_RECEIPT_GENERATOR")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "LOCAL"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    args = parser.parse_args()

    if not args.lean.is_file():
        raise ReceiptError(f"Lean executable not found: {args.lean}")
    version = run([str(args.lean), "--version"]).strip()
    if "version 4.19.0" not in version:
        raise ReceiptError(f"expected Lean 4.19.0, got {version}")

    theorem_names = re.findall(r"(?m)^theorem\s+([A-Za-z0-9_]+)", MODEL.read_text())
    audit_directives = re.findall(r"(?m)^#print axioms\s+", AUDIT.read_text())
    if len(theorem_names) != 36 or len(audit_directives) != 36:
        raise ReceiptError("expected exactly 36 theorems and 36 axiom directives")

    axiom_text = args.axiom_output.read_text(encoding="utf-8")
    axioms = parse_axioms(axiom_text)
    if len(axioms) != 36:
        raise ReceiptError(f"axiom output binds {len(axioms)} of 36 theorems")
    allowed = {"propext", "Quot.sound", "Classical.choice"}
    unexpected = sorted({a for values in axioms.values() for a in values} - allowed)
    if unexpected:
        raise ReceiptError(f"unexpected axiom dependencies: {unexpected}")

    verification_text = args.verification_output.read_text(encoding="utf-8")
    verification = json.loads(verification_text)
    if verification.get("result") != "FORMAL_MODEL_VERIFIED":
        raise ReceiptError("verification output is not FORMAL_MODEL_VERIFIED")

    receipt = {
        "schema": "qikvrt-qce-kernel-receipt/1.0",
        "publication_id": "qikvrt-quantum-causal-emergence-v1",
        "state": "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE",
        "effect_state": "EFFECT_ACK_CONTINUE",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "source_binding": {
            "repository": args.repository,
            "commit": args.commit,
            "tree": args.tree,
            "candidate_path": str(ROOT.relative_to(ROOT.parents[2])),
            "model_sha256": sha256(MODEL),
            "axiom_audit_sha256": sha256(AUDIT),
        },
        "workflow_binding": {
            "run_id": str(args.run_id),
            "run_attempt": str(args.run_attempt),
        },
        "toolchain": {
            "lean_version": version,
            "target": "4.19.0",
            "target_commit": "6caaee842e9495688c1567e78c0e68dbb96942aa",
            "imports": ["Std"],
        },
        "kernel_execution": {
            "named_theorems": 36,
            "accepted_theorems": 36,
            "axiom_audit_directives": 36,
            "axioms_by_theorem": axioms,
            "project_axioms": 0,
            "sorry_or_admit": 0,
            "unsafe_declarations": 0,
            "axiom_output_sha256": sha256(args.axiom_output),
            "verification_output_sha256": sha256(args.verification_output),
        },
        "formal_scope": {
            "finite_model_contract_kernel_accepted": True,
            "physical_correspondence_established": False,
            "physical_closure": False,
            "historical_priority_adjudicated": False,
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "RECEIPT_CREATED", "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReceiptError as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        raise SystemExit(1) from error
