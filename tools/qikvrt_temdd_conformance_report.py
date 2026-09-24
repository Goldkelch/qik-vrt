#!/usr/bin/env python3
"""Generate one exact-subject TEMDD v1 conformance report.

The report is intentionally scoped: PASS means the declared TEMDD conformance
suite reached this final step on one immutable HEAD/TREE. It is not P3, Main,
production deployment, or general EFFECT_ACK_DONE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"[0-9a-f]{40}\Z")

IMPLEMENTATION_FILES = (
    "tools/qikvrt_temdd.py",
    "src/qikvrt_temdd_semantic_ir.py",
    "src/qikvrt_temdd_event_ledger.py",
    "runtime/temdd/TEMDDRuntime.st",
    "src/temdd_core.c",
    "runtime/m68000/temdd_transition.s",
)
SUITE_FILES = (
    "spec/temdd/TEMDD_LANGUAGE_SPEC_V0_1.md",
    "spec/temdd/TEMDD_NORMATIVE_T13_T16_V0_1.json",
    "spec/temdd/TEMDD_CONFORMANCE_MATRIX_V0_1.json",
    "spec/temdd/TEMDD_Syntax_V0_1.ebnf",
    "schemas/temdd-ir-v0.1.schema.json",
    "schemas/temdd-event-v1.schema.json",
    "schemas/temdd-evidence-v1.schema.json",
    "schemas/temdd-conformance-report-v1.schema.json",
    "tools/qikvrt_temdd_conformance.py",
    "tests/test_temdd.py",
    "tests/test_temdd_semantic_ir.py",
    "tests/test_temdd_conformance_report.py",
    "tests/temdd/positive/minimal.temdd",
    "formalization/TEMDDCore.lean",
    "formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/TEMDD/T13T16.lean",
    "formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/TEMDD/AxiomAudit.lean",
)


class ConformanceReportHold(ValueError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def inventory(paths):
    rows = []
    for name in sorted(paths):
        path = ROOT / name
        if not path.is_file():
            raise ConformanceReportHold("MISSING_SUITE_FILE:" + name)
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    return rows


def inventory_digest(rows) -> str:
    return "sha256:" + hashlib.sha256(canonical(rows)).hexdigest()


def git_subject():
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"], text=True).strip()
    if HEX40.fullmatch(head) is None or HEX40.fullmatch(tree) is None:
        raise ConformanceReportHold("UNOBSERVABLE_GIT_SUBJECT")
    return head, tree


def build_report(repository: str, head: str, tree: str, backend_receipt: dict):
    actual_head, actual_tree = git_subject()
    if (head, tree) != (actual_head, actual_tree):
        raise ConformanceReportHold("EXACT_SUBJECT_DRIFT")
    if backend_receipt.get("source_sha") != head or backend_receipt.get("source_tree") != tree:
        raise ConformanceReportHold("BACKEND_RECEIPT_SUBJECT_MISMATCH")
    expected_backends = {
        "c90": "EXECUTED_SUCCESS",
        "smalltalk": "EXECUTED_SUCCESS",
        "m68000": "EXECUTED_SUCCESS_QEMU_USER",
        "lean": "COMPILED_SUCCESS_LEAN_4_19_LAKE",
    }
    if backend_receipt.get("backends") != expected_backends:
        raise ConformanceReportHold("BACKEND_RECEIPT_INCOMPLETE")
    if backend_receipt.get("predecessor_evidence_transfer") is not False:
        raise ConformanceReportHold("PREDECESSOR_EVIDENCE_TRANSFER_FORBIDDEN")

    implementation = inventory(IMPLEMENTATION_FILES)
    suite = inventory(SUITE_FILES)
    return {
        "schema": "temdd_conformance_report_v1",
        "temdd_conformance": "1",
        "implementation": {
            "repository": repository,
            "head": head,
            "tree": tree,
            "digest": inventory_digest(implementation),
        },
        "suite": {
            "version": "1",
            "digest": inventory_digest(suite),
            "files": suite,
        },
        "language": "PASS",
        "ir": "PASS",
        "ide": "PASS",
        "event_semantics": "PASS",
        "ledger": "PASS",
        "evidence_binding": "PASS",
        "causality": "PASS",
        "effect_ack": "PASS",
        "formal_invariants": "PASS",
        "tests": "PASS",
        "negative_vectors": "PASS",
        "backends": expected_backends,
        "overall": "PASS",
        "predecessor_evidence_transfer": False,
        "stable_language_claim": False,
        "main_adoption": False,
        "production_effect": False,
        "effect_ack_done": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--backend-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.backend_receipt.read_text(encoding="utf-8"))
    report = build_report(args.repository, args.head, args.tree, receipt)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "TEMDD_CONFORMANCE_REPORT PASS "
        + args.head
        + " "
        + args.tree
        + " "
        + report["suite"]["digest"]
    )


if __name__ == "__main__":
    main()
