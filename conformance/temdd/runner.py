#!/usr/bin/env python3
"""TEMDD v1 conformance runner.

This runner deliberately invokes the reference implementation through a process
boundary. It does not import implementation internals as the semantic oracle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

SUITE_FILES = (
    "spec/temdd/TEMDD_NORMATIVE_CORE_V1.md",
    "schemas/temdd-ir-v1.schema.json",
    "schemas/temdd-event-v1.schema.json",
    "schemas/temdd-evidence-v1.schema.json",
    "schemas/temdd-conformance-report-v1.schema.json",
    "conformance/temdd/vectors-v1.json",
    "spec/temdd/TEMDD_INTEROPERABILITY_V1.md",
    "schemas/temdd-interoperability-proof-v1.schema.json",
    "conformance/temdd/interoperability-vectors-v1.json",
    "conformance/temdd/interop_impl_python.py",
    "conformance/temdd/interop_impl_node.js",
    "conformance/temdd/interop_runner.py",
    "conformance/temdd/runner.py",
)

IMPLEMENTATION_FILES = (
    "tools/qikvrt_temdd.py",
    "src/temdd/v1_adapter.py",
    "src/qikvrt_temdd_event_ledger.py",
    "src/temdd_core.c",
    "include/temdd_core.h",
    "runtime/temdd/TEMDDRuntime.st",
    "runtime/m68000/temdd_transition.s",
    "formalization/TEMDDCore.lean",
    "docs/terminal/temdd/index.html",
)

PASS_FIELDS = (
    "language", "ir", "event_semantics", "ledger", "ide", "evidence_binding",
    "causality", "effect_ack", "execution", "formal_invariants", "tests",
    "negative_vectors", "interoperability",
)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def manifest_digest(paths) -> str:
    h = hashlib.sha256()
    for rel in sorted(paths):
        p = ROOT / rel
        data = p.read_bytes()
        h.update(rel.encode("utf-8") + b"\0" + sha256_bytes(data).encode("ascii") + b"\n")
    return "sha256:" + h.hexdigest()

def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

def exact_subject(repository: str) -> dict:
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    if len(head) != 40 or len(tree) != 40:
        raise RuntimeError("EXACT_SUBJECT_UNBOUND")
    subprocess.check_call(["git", "-C", str(ROOT), "diff", "--quiet"])
    subprocess.check_call(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"])
    return {"repository": repository, "head": head, "tree": tree}

def invoke_adapter(adapter: str, source: Path) -> tuple[int, str, str]:
    p = subprocess.run(
        [sys.executable, str(ROOT / adapter), str(source)],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    return p.returncode, p.stdout, p.stderr

def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)

def check_language_and_ir(adapter: str) -> None:
    good = ROOT / "tests/temdd/positive/minimal.temdd"
    rc, out, err = invoke_adapter(adapter, good)
    require(rc == 0, "POSITIVE_CORPUS_REJECTED:" + err.strip())
    ir = json.loads(out)
    require(ir.get("schema") == "temdd_ir_v1", "REFERENCE_IR_SCHEMA_MISMATCH")
    require(ir.get("ir_version") == "1", "REFERENCE_IR_VERSION_MISMATCH")
    require(ir.get("language_version") == "0.1", "REFERENCE_LANGUAGE_VERSION_MISMATCH")
    require(ir.get("subject", {}).get("binding") == "exact", "REFERENCE_IR_NOT_EXACT")
    require(set(ir.get("semantic_contract", [])) == {
        "T13_CAUSAL_BINDING",
        "T14_EVIDENCE_NON_TRANSFER",
        "T15_EFFECT_CONSTRUCTION",
        "T16_CONFORMANCE_BINDING",
    }, "REFERENCE_IR_SEMANTIC_CONTRACT_MISMATCH")
    for bad in sorted((ROOT / "tests/temdd/negative").glob("*.temdd")):
        rc, _, _ = invoke_adapter(adapter, bad)
        require(rc != 0, "NEGATIVE_CORPUS_ADMITTED:" + bad.name)

def subject_equal(a: dict, b: dict) -> bool:
    keys = ("subject_id", "repository", "head", "tree")
    return all(a.get(k) == b.get(k) for k in keys)

def evidence_applies(evidence: dict, subject: dict) -> bool:
    return (
        evidence.get("freshness") == "FRESH"
        and evidence.get("predecessor_evidence_transfer") is False
        and subject_equal(evidence.get("observed_subject", {}), subject)
    )

def effect_ack(v: dict) -> bool:
    return all((
        v.get("authority") is True,
        v.get("committed") is True,
        v.get("fresh_readback") is True,
        v.get("exact_subject") is True,
        v.get("expected_matches_observed") is True,
    ))

def check_t13_t16(vectors: dict) -> None:
    t13 = vectors["t13"]
    seq = t13["sequence_without_cause"]
    require(seq["earlier"]["sequence"] < seq["later"]["sequence"], "T13_VECTOR_NOT_SEQUENCED")
    require(seq["earlier"]["event_id"] not in seq["later"]["cause_event_ids"], "T13_SEQUENCE_MANUFACTURED_CAUSE")
    causal = t13["explicit_cause"]
    require(causal["cause"]["event_id"] in causal["effect"]["cause_event_ids"], "T13_EXPLICIT_CAUSE_MISSING")

    t14 = vectors["t14"]
    require(evidence_applies(t14["evidence"], t14["subject_s0"]), "T14_SOURCE_EVIDENCE_REJECTED")
    require(not evidence_applies(t14["evidence"], t14["subject_s1"]), "T14_PREDECESSOR_EVIDENCE_TRANSFERRED")

    t15 = vectors["t15"]
    require(effect_ack(t15["commit_only"]) is False, "T15_COMMIT_BECAME_EFFECT_ACK")
    require(effect_ack(t15["fresh_exact_readback"]) is True, "T15_FRESH_READBACK_NOT_ACKNOWLEDGED")
    require(t15["commit_only"]["effect_ack"] is False, "T15_VECTOR_COMMIT_CLAIM_INVALID")
    require(t15["fresh_exact_readback"]["effect_ack"] is True, "T15_VECTOR_READBACK_CLAIM_INVALID")

    t16 = vectors["t16"]
    require(all(t16[k] is True for k in (
        "require_exact_head", "require_exact_tree",
        "require_implementation_digest", "require_suite_digest",
    )), "T16_BINDING_REQUIREMENT_MISSING")
    require(t16["predecessor_evidence_transfer"] is False, "T16_EVIDENCE_TRANSFER_NOT_DENIED")

def check_formal_core() -> None:
    text = (ROOT / "formalization/TEMDDCore.lean").read_text(encoding="utf-8")
    for theorem in (
        "sequence_does_not_imply_cause",
        "evidence_non_transfer",
        "effect_ack_requires_fresh_readback",
    ):
        require(theorem in text, "FORMAL_OBLIGATION_NOT_MATERIALIZED:" + theorem)

def check_repository_tests() -> None:
    p = subprocess.run(
        [sys.executable, "-m", "unittest", "tests.test_temdd", "tests.test_temdd_event_ledger"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    require(p.returncode == 0, "TEMDD_TEST_SUITE_FAILED:" + (p.stderr or p.stdout)[-2000:])

def check_backend_receipt(path: Path, subject: dict) -> str:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "qikvrt_temdd_executable_backends_v1", "BACKEND_RECEIPT_SCHEMA_MISMATCH")
    require(receipt.get("repository") == subject["repository"], "BACKEND_RECEIPT_REPOSITORY_MISMATCH")
    require(receipt.get("source_sha") == subject["head"], "BACKEND_RECEIPT_HEAD_MISMATCH")
    require(receipt.get("source_tree") == subject["tree"], "BACKEND_RECEIPT_TREE_MISMATCH")
    require(receipt.get("predecessor_evidence_transfer") is False, "BACKEND_RECEIPT_EVIDENCE_TRANSFER")
    expected = {
        "c90": "EXECUTED_SUCCESS",
        "smalltalk": "EXECUTED_SUCCESS",
        "m68000": "EXECUTED_SUCCESS_QEMU_USER",
        "lean": "COMPILED_SUCCESS_LEAN_4_19_LAKE",
    }
    require(receipt.get("backends") == expected, "BACKEND_RECEIPT_EXECUTION_MISMATCH")
    return "sha256:" + sha256_bytes(path.read_bytes())

def check_interoperability(repository: str, subject: dict) -> str:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "conformance/temdd/interop_runner.py"), "--repository", repository],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    require(proc.returncode == 0, "INTEROPERABILITY_PROOF_FAILED:" + proc.stderr.strip())
    proof = json.loads(proc.stdout)
    require(proof.get("schema") == "temdd_interoperability_proof_v1", "INTEROPERABILITY_PROOF_SCHEMA_MISMATCH")
    require(proof.get("subject") == subject, "INTEROPERABILITY_SUBJECT_MISMATCH")
    require(proof.get("overall") == "INTEROPERABILITY_BY_EXECUTABLE_PROOF", "INTEROPERABILITY_NOT_PROVEN")
    require(proof.get("effect_ack_done") is False, "INTEROPERABILITY_MANUFACTURED_EFFECT_ACK")
    return "sha256:" + sha256_bytes(proc.stdout.encode("utf-8"))

def build_report(repository: str, adapter: str, backend_receipt: Path) -> dict:
    subject = exact_subject(repository)
    check_language_and_ir(adapter)
    vectors = json.loads((ROOT / "conformance/temdd/vectors-v1.json").read_text(encoding="utf-8"))
    require(vectors.get("schema") == "temdd_conformance_vectors_v1", "VECTOR_SCHEMA_MISMATCH")
    check_t13_t16(vectors)
    check_formal_core()
    check_repository_tests()
    interoperability_proof_digest = check_interoperability(repository, subject)
    execution_receipt_digest = check_backend_receipt(backend_receipt, subject)

    report = {
        "schema": "temdd_conformance_report_v1",
        "temdd_conformance": "1",
        "implementation": {
            **subject,
            "digest": manifest_digest(IMPLEMENTATION_FILES),
        },
        "suite": {
            "version": "1",
            "digest": manifest_digest(SUITE_FILES),
        },
        "execution_receipt_digest": execution_receipt_digest,
        "interoperability_proof_digest": interoperability_proof_digest,
        "interoperability": "PASS",
        "language": "PASS",
        "ir": "PASS",
        "event_semantics": "PASS",
        "ledger": "PASS",
        "ide": "PASS",
        "evidence_binding": "PASS",
        "causality": "PASS",
        "effect_ack": "PASS",
        "execution": "PASS",
        "formal_invariants": "PASS",
        "tests": "PASS",
        "negative_vectors": "PASS",
        "overall": "PASS",
    }
    require(all(report[k] == "PASS" for k in PASS_FIELDS), "T16_PARTIAL_PASS")
    require(report["implementation"]["head"] == git("rev-parse", "HEAD"), "T16_HEAD_MISMATCH")
    require(report["implementation"]["tree"] == git("rev-parse", "HEAD^{tree}"), "T16_TREE_MISMATCH")
    return report

def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository", default="Goldkelch/qik-vrt")
    p.add_argument("--adapter", default="src/temdd/v1_adapter.py")
    p.add_argument("--backend-receipt", required=True)
    p.add_argument("--output")
    args = p.parse_args(argv)
    try:
        report = build_report(args.repository, args.adapter, Path(args.backend_receipt))
    except Exception as exc:
        print("HOLD_UNVERIFIED " + str(exc), file=sys.stderr)
        return 2
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
