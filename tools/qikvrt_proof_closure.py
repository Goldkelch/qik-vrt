#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate a bound QIK-VRT proof-closure witness."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED = (
    "all_required_proofs_valid",
    "provenance_bound",
    "verifier_checked",
    "fresh_independent_readback",
    "boundaries_explicit",
    "no_open_obligations",
    "subject_unchanged",
    "no_predecessor_evidence_transfer",
)

def evaluate(value: dict) -> dict:
    findings=[]
    if value.get("schema")!="qikvrt_proof_closure_witness_v1":
        findings.append("schema mismatch")
    subject=value.get("subject")
    if not isinstance(subject,dict) or not subject.get("id") or not subject.get("digest"):
        findings.append("exact subject identity missing")
    predicates=value.get("predicates")
    if not isinstance(predicates,dict):
        findings.append("predicates missing")
        predicates={}
    for key in REQUIRED:
        if predicates.get(key) is not True:
            findings.append("required predicate not true: "+key)
    obligations=value.get("open_obligations")
    if obligations != []:
        findings.append("open obligations remain")
    claimed=value.get("proof_closure")
    closed=not findings
    if claimed is not closed:
        findings.append("claimed proof_closure differs from evaluated closure")
        closed=False
    return {
      "schema":"qikvrt_proof_closure_receipt_v1",
      "subject":subject,
      "status":"PASS" if closed else "BLOCK",
      "proof_closure":closed,
      "finding_count":len(findings),
      "findings":findings,
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("witness")
    ap.add_argument("--output")
    ns=ap.parse_args()
    value=json.loads(Path(ns.witness).read_text(encoding="utf-8"))
    result=evaluate(value)
    raw=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    print(raw,end="")
    if ns.output: Path(ns.output).write_text(raw,encoding="utf-8")
    return 0 if result["status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
