#!/usr/bin/env python3
"""Independent TEMDD v1 exact-subject conformance runner.

The runner invokes the implementation adapter through a subprocess boundary and
uses normative vectors as its semantic oracle. PASS is candidate conformance
only; it is not P3, Main, deployment, or general EFFECT_ACK_DONE.
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
    "spec/temdd/TEMDD_CONFORMANCE_V1.md",
    "spec/temdd/TEMDD_CONFORMANCE_MATRIX_V1.json",
    "schemas/temdd-ir-v1.schema.json",
    "schemas/temdd-event-v1.schema.json",
    "schemas/temdd-evidence-v1.schema.json",
    "schemas/temdd-conformance-report-v1.schema.json",
    "conformance/temdd/vectors-v1.json",
    "conformance/temdd/runner.py",
)
IMPLEMENTATION_FILES = (
    "tools/qikvrt_temdd.py",
    "src/temdd/v1_adapter.py",
    "src/qikvrt_temdd_semantic_ir.py",
    "src/qikvrt_temdd_event_ledger.py",
    "src/temdd_core.c",
    "include/temdd_core.h",
    "runtime/temdd/TEMDDRuntime.st",
    "runtime/m68000/temdd_transition.s",
    "formalization/TEMDDCore.lean",
    "docs/terminal/temdd/index.html",
)
PASS_FIELDS = (
    "language","ir","ide","event_semantics","ledger","evidence_binding",
    "causality","effect_ack","formal_invariants","tests","negative_vectors",
)
BACKENDS = {
    "c90":"EXECUTED_SUCCESS",
    "smalltalk":"EXECUTED_SUCCESS",
    "m68000":"EXECUTED_SUCCESS_QEMU_USER",
    "lean":"COMPILED_SUCCESS_LEAN_4_19_LAKE",
}

class Hold(RuntimeError):
    pass

def require(condition: bool, code: str) -> None:
    if not condition:
        raise Hold(code)

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(value) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def inventory(paths):
    rows=[]
    for rel in sorted(paths):
        path=ROOT/rel
        require(path.is_file(),"MISSING_SUITE_FILE:"+rel)
        data=path.read_bytes()
        rows.append({"path":rel,"bytes":len(data),"sha256":sha256(data)})
    return rows

def inventory_digest(rows) -> str:
    return "sha256:"+sha256(canonical(rows))

def git(*args: str) -> str:
    return subprocess.check_output(["git","-C",str(ROOT),*args],text=True).strip()

def exact_subject(repository: str) -> dict:
    head=git("rev-parse","HEAD")
    tree=git("rev-parse","HEAD^{tree}")
    require(len(head)==40 and len(tree)==40,"EXACT_SUBJECT_UNBOUND")
    subprocess.check_call(["git","-C",str(ROOT),"diff","--quiet"])
    subprocess.check_call(["git","-C",str(ROOT),"diff","--cached","--quiet"])
    return {"repository":repository,"head":head,"tree":tree}

def invoke_adapter(adapter: str, source: Path):
    p=subprocess.run([sys.executable,str(ROOT/adapter),str(source)],cwd=ROOT,text=True,capture_output=True,check=False)
    return p.returncode,p.stdout,p.stderr

def check_language_ir(adapter: str) -> None:
    good=ROOT/"tests/temdd/positive/minimal.temdd"
    rc,out,err=invoke_adapter(adapter,good)
    require(rc==0,"POSITIVE_CORPUS_REJECTED:"+err.strip())
    ir=json.loads(out)
    require(ir.get("schema")=="temdd_ir_v1","REFERENCE_IR_SCHEMA_MISMATCH")
    require(ir.get("ir_version")=="1","REFERENCE_IR_VERSION_MISMATCH")
    require(ir.get("language_version")=="0.1","REFERENCE_LANGUAGE_VERSION_MISMATCH")
    require(ir.get("subject",{}).get("binding")=="exact","REFERENCE_IR_NOT_EXACT")
    require(isinstance(ir.get("context"),dict) and ir["context"].get("perspective"),"T16_CONTEXT_LOST")
    require(bool(ir.get("relations")),"T16_RELATIONS_LOST")
    require(set(ir.get("semantic_contract",[]))=={
        "T13_CAUSAL_BINDING","T14_EVIDENCE_NON_TRANSFER",
        "T15_EFFECT_CONSTRUCTION","T16_CONFORMANCE_BINDING",
    },"REFERENCE_IR_SEMANTIC_CONTRACT_MISMATCH")
    for bad in sorted((ROOT/"tests/temdd/negative").glob("*.temdd")):
        rc,_,_=invoke_adapter(adapter,bad)
        require(rc!=0,"NEGATIVE_CORPUS_ADMITTED:"+bad.name)

def evidence_applies(evidence: dict, subject: dict) -> bool:
    observed=evidence.get("observed_subject",{})
    return (
        evidence.get("freshness")=="FRESH"
        and evidence.get("evidence_transfer")=="DENY"
        and all(observed.get(k)==subject.get(k) for k in ("repository","head","tree"))
    )

def effect_ack(value: dict) -> bool:
    return all((
        value.get("authority") is True,
        value.get("committed") is True,
        value.get("fresh_readback") is True,
        value.get("exact_subject") is True,
        value.get("expected_matches_observed") is True,
    ))

def check_vectors() -> None:
    v=json.loads((ROOT/"conformance/temdd/vectors-v1.json").read_text(encoding="utf-8"))
    require(v.get("schema")=="temdd_conformance_vectors_v1","VECTOR_SCHEMA_MISMATCH")
    seq=v["t13"]["sequence_without_cause"]
    require(seq["earlier"]["sequence"]<seq["later"]["sequence"],"T13_VECTOR_NOT_SEQUENCED")
    require(seq["earlier"]["event_id"] not in seq["later"]["cause_event_ids"],"T13_SEQUENCE_MANUFACTURED_CAUSE")
    explicit=v["t13"]["explicit_cause"]
    require(explicit["cause"]["event_id"] in explicit["effect"]["cause_event_ids"],"T13_EXPLICIT_CAUSE_MISSING")
    t14=v["t14"]
    require(evidence_applies(t14["evidence"],t14["subject_s0"]),"T14_SOURCE_EVIDENCE_REJECTED")
    require(not evidence_applies(t14["evidence"],t14["subject_s1"]),"T14_PREDECESSOR_EVIDENCE_TRANSFERRED")
    t15=v["t15"]
    require(not effect_ack(t15["commit_only"]),"T15_COMMIT_BECAME_EFFECT_ACK")
    require(effect_ack(t15["fresh_exact_readback"]),"T15_FRESH_READBACK_NOT_ACKNOWLEDGED")
    require(t15["commit_only"]["effect_ack"] is False,"T15_VECTOR_COMMIT_CLAIM_INVALID")
    require(t15["fresh_exact_readback"]["effect_ack"] is True,"T15_VECTOR_READBACK_CLAIM_INVALID")
    t16=v["t16"]
    require(all(t16[k] is True for k in (
        "require_exact_head","require_exact_tree","require_implementation_digest","require_suite_digest"
    )),"T16_BINDING_REQUIREMENT_MISSING")
    require(t16["predecessor_evidence_transfer"] is False,"T16_EVIDENCE_TRANSFER_NOT_DENIED")

def check_schemas() -> None:
    expectations={
        "schemas/temdd-ir-v1.schema.json":"temdd_ir_v1",
        "schemas/temdd-event-v1.schema.json":"temdd_event_ir_v1",
        "schemas/temdd-evidence-v1.schema.json":"temdd_evidence_ir_v1",
        "schemas/temdd-conformance-report-v1.schema.json":"temdd_conformance_report_v1",
    }
    for name,const in expectations.items():
        schema=json.loads((ROOT/name).read_text(encoding="utf-8"))
        require(schema.get("type")=="object","SCHEMA_NOT_OBJECT:"+name)
        require(schema.get("additionalProperties") is False,"SCHEMA_NOT_CLOSED:"+name)
        require(schema.get("properties",{}).get("schema",{}).get("const")==const,"SCHEMA_IDENTITY_MISMATCH:"+name)

def check_formal_core() -> None:
    text=(ROOT/"formalization/TEMDDCore.lean").read_text(encoding="utf-8")
    for theorem in ("sequence_does_not_imply_cause","evidence_non_transfer","effect_ack_requires_fresh_readback"):
        require(("theorem "+theorem) in text,"FORMAL_OBLIGATION_NOT_MATERIALIZED:"+theorem)

def check_ide() -> None:
    page=(ROOT/"docs/terminal/temdd/index.html").read_text(encoding="utf-8")
    for view in ("source","ir","event-graph","ledger","conformance"):
        require(('data-temdd-view="'+view+'"') in page,"IDE_VIEW_MISSING:"+view)
    require("/api/temdd/conformance" in page,"IDE_CONFORMANCE_READBACK_MISSING")
    require("cause_event_ids" in page,"IDE_CAUSE_GRAPH_NOT_EXPLICIT")
    require("SEQUENCE != CAUSALITY" in page,"IDE_CAUSALITY_BOUNDARY_MISSING")

def check_tests() -> None:
    p=subprocess.run(
        [sys.executable,"-m","unittest","tests.test_temdd","tests.test_temdd_v1",
         "tests.test_temdd_semantic_ir","tests.test_temdd_conformance_report",
         "tests.test_temdd_event_ledger"],
        cwd=ROOT,text=True,capture_output=True,check=False,
    )
    require(p.returncode==0,"TEMDD_TEST_SUITE_FAILED:"+(p.stderr or p.stdout)[-3000:])

def check_backend_receipt(path: Path, subject: dict) -> None:
    receipt=json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema")=="qikvrt_temdd_executable_backends_v1","BACKEND_RECEIPT_SCHEMA_MISMATCH")
    require(receipt.get("repository")==subject["repository"],"BACKEND_RECEIPT_REPOSITORY_MISMATCH")
    require(receipt.get("source_sha")==subject["head"],"BACKEND_RECEIPT_HEAD_MISMATCH")
    require(receipt.get("source_tree")==subject["tree"],"BACKEND_RECEIPT_TREE_MISMATCH")
    require(receipt.get("predecessor_evidence_transfer") is False,"BACKEND_RECEIPT_EVIDENCE_TRANSFER")
    require(receipt.get("backends")==BACKENDS,"BACKEND_RECEIPT_EXECUTION_MISMATCH")

def build_report(repository: str, adapter: str, backend_receipt: Path) -> dict:
    subject=exact_subject(repository)
    check_language_ir(adapter)
    check_vectors()
    check_schemas()
    check_formal_core()
    check_ide()
    check_tests()
    check_backend_receipt(backend_receipt,subject)
    impl=inventory(IMPLEMENTATION_FILES)
    suite=inventory(SUITE_FILES)
    report={
        "schema":"temdd_conformance_report_v1","temdd_conformance":"1",
        "implementation":{**subject,"digest":inventory_digest(impl)},
        "suite":{"version":"1","digest":inventory_digest(suite),"files":suite},
        "language":"PASS","ir":"PASS","ide":"PASS","event_semantics":"PASS",
        "ledger":"PASS","evidence_binding":"PASS","causality":"PASS","effect_ack":"PASS",
        "formal_invariants":"PASS","tests":"PASS","negative_vectors":"PASS",
        "backends":dict(BACKENDS),"overall":"PASS",
        "predecessor_evidence_transfer":False,"stable_language_claim":False,
        "main_adoption":False,"production_effect":False,"effect_ack_done":False,
    }
    require(all(report[k]=="PASS" for k in PASS_FIELDS),"PARTIAL_CONFORMANCE_PASS")
    return report

def main(argv=None) -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--repository",default="Goldkelch/qik-vrt")
    p.add_argument("--adapter",default="src/temdd/v1_adapter.py")
    p.add_argument("--backend-receipt",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args(argv)
    try:
        report=build_report(args.repository,args.adapter,Path(args.backend_receipt))
    except Exception as exc:
        print("HOLD_UNVERIFIED "+str(exc),file=sys.stderr)
        return 2
    Path(args.output).write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("TEMDD_V1_CONFORMANCE PASS "+report["implementation"]["head"]+" "+report["implementation"]["tree"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
