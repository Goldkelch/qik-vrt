#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Build this source-bound note using the existing v2 proof contract.

Run only after the exact primary document has been returned to the owner.
An existing return receipt is reused, never silently assigned a new time.
This script performs no network operation or publication.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import unittest

D = pathlib.Path(__file__).resolve().parent
ROOT = D.parents[2]
sys.path.insert(0, str(ROOT))
from tools import qikvrt_zenodo_machine_proof as proof

REL = D.relative_to(ROOT).as_posix()
PID = "qikvrt-core-invariant-transport-effect-20260919-v1"
AID = "core-invariant-20260919-v1"
HEAD = "a86054139b49c13c5cd344753b248b46b5daf66f"
TREE = "feff1cae2401a3df83febc3b9458de70d79b818e"
LIC = {"copyright": "Copyright 2026 Ingolf Lohmann", "rights_holder": "Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt"}

def write(name, obj):
    (D/name).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")

def ident(path):
    return {"path": path, **proof.identity(ROOT/path)}

def artifact(path, kind):
    item = ident(path)
    item.pop("bytes")
    return {**item, "kind": kind}

def main():
    primary = f"{REL}/KERNINVARIANTE_DE.md"
    text = (ROOT/primary).read_text(encoding="utf-8")
    sections = re.findall(r"### (C[1-8]) — [^\n]+\n\n(.+?)(?=\n\n### |\n\n## Quellen)", text, re.S)
    if [c for c,_ in sections] != [f"C{i}" for i in range(1,9)]:
        raise RuntimeError("the primary claim inventory must be exactly C1 through C8")
    source_paths = ["src/qikvrt_effect_ack.py", "examples/effect_haltpoint_demo.py", "tests/test_effect_ack_conformance.py"]
    sources = []
    for source_id,path in zip(("REFERENCE_CORE", "REFERENCE_DEMO", "CONFORMANCE_TESTS"), source_paths):
        raw = subprocess.check_output(["git","show",f"{HEAD}:{path}"], cwd=ROOT)
        if raw != (ROOT/path).read_bytes():
            raise RuntimeError("source bytes differ from the bound source subject: "+path)
        sources.append({"source_id":source_id, **ident(path), "repository":"Goldkelch/qik-vrt", "head":HEAD, "tree":TREE, "url":f"https://github.com/Goldkelch/qik-vrt/blob/{HEAD}/{path}"})
    write("SOURCE_BINDINGS.json", {"schema":"qikvrt_core_invariant_sources_v1", "sources":sources, "source_evidence_scope":"Only the named byte-identical sources; no predecessor validation transfer to a publication successor."})

    report_path = D/"BOUNDARY_TEST_REPORT.json"
    if not report_path.exists():
        output = io.StringIO()
        suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_effect_ack_conformance")
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        write("BOUNDARY_TEST_REPORT.json", {"schema":"qikvrt_core_invariant_boundary_report_v1", "observed_at":dt.datetime.now(dt.timezone.utc).isoformat(), "source_head":HEAD, "source_tree":TREE, "source_files":sources, "candidate":ident(primary), "command":"python3 -B -m unittest -v tests.test_effect_ack_conformance", "python":sys.version, "tests_run":result.testsRun, "failures":len(result.failures), "errors":len(result.errors), "skipped":len(result.skipped), "success":result.wasSuccessful(), "log":output.getvalue(), "scope":"Reference-core conformance only; no full repository, successor-head, public URL or external-effect claim."})
        if not result.wasSuccessful():
            raise RuntimeError("conformance failed")
    report = json.loads(report_path.read_text())
    if report["candidate"] != ident(primary) or report["source_files"] != sources or not report["success"]:
        raise RuntimeError("existing execution receipt does not match these bytes")

    claims = []
    for cid, statement in sections:
        classification = "SOURCE_BOUND" if int(cid[1:]) <= 5 else "NORMATIVE"
        source_ids = (["REFERENCE_DEMO"] if cid=="C4" else ["REFERENCE_CORE"]) if classification=="SOURCE_BOUND" else []
        claims.append({"claim_id":cid,"statement":statement,"classification":classification,"status":"BOUND" if source_ids else "DECLARED","boundary":"Exact reference source HEAD/TREE and named source bytes only; no universal or empirical external-effect guarantee." if source_ids else "Methodological declaration and scope limit of this note; not a formal theorem or observed external transaction.","proof_refs":[],"sources":source_ids})
    write("CLAIM_MATRIX.json", {"schema":"qikvrt_core_invariant_claim_matrix_v1","publication_id":PID,"claim_count":len(claims),"primary_artifact":ident(primary),"claims":claims})
    metadata={"title":"Empfang, Freigabe und Wirkungsnachweis: Die Kerninvariante von QIK-VRT","upload_type":"publication","publication_type":"technicalnote","publication_date":"2026-09-19","creators":[{"name":"Lohmann, Ingolf"}],"description":"<p>Quellengebundene technische Notiz zur Kerninvariante TRANSPORT_ACK != EFFECT_ACK und zur DONE-only ordinary-release-Regel. Acht Claims trennen Referenzcode, Integration, Demo, Integritätsgrenze und Kausalnachweis. Keine Behauptung eines neuen formalen Kernelbeweises, universeller Sicherheit oder einer realen externen Transaktion.</p>","version":"1.0.0","language":"deu","access_right":"open","license":"cc-by-nc-nd-4.0","keywords":["QIK-VRT","EFFECT_ACK","provenance","release decision","causality"],"related_identifiers":[{"identifier":"10.5281/zenodo.21498773","relation":"references","scheme":"doi"}],"notes":"Konzept und Persistenzauftrag: Ingolf Lohmann. Redaktion, Quellenprüfung und Paketierung: OpenAI ChatGPT / Codex. Mitgelieferte Quellcodedateien behalten ihre eigenen Dateilizenzen.","prereserve_doi":True}
    write("ZENODO_METADATA.json",metadata)
    candidate={**ident(primary),"name":"KERNINVARIANTE_DE.md","role":"PRIMARY"}
    receipt_path=D/"PREPUBLICATION_RETURN_RECEIPT.json"
    if not receipt_path.exists():
        write("PREPUBLICATION_RETURN_RECEIPT.json",{"_license":{"classification":"machine_readable_prepublication_return_receipt",**LIC},"schema":"qikvrt_prepublication_return_receipt_v2","publication_id":PID,"content_changed":False,"original_files":[],"candidate_files":[ident(primary)],"changed_claim_ids":[],"change_reasons":[],"change_notice_path":None,"return":{"candidate_returned_to_owner":True,"owner_name":"Ingolf Lohmann","owner_type":"NATURAL_PERSON","return_channel":"ChatGPT Work: complete KERNINVARIANTE_DE.md sandbox link delivered before this receipt; newly authored note, not replacement of an earlier manuscript","returned_at":dt.datetime.now(dt.timezone.utc).isoformat(),"visible_change_notice_returned":False}})
    artifacts=[artifact(f"{REL}/{name}",kind) for name,kind in [("CLAIM_MATRIX.json","CLAIM_MATRIX"),("SOURCE_BINDINGS.json","SOURCE"),("BOUNDARY_TEST_REPORT.json","BOUNDARY_TEST"),("PREPUBLICATION_RETURN_RECEIPT.json","RETURN_RECEIPT"),("ZENODO_METADATA.json","OTHER"),("README.md","OTHER")]]
    artifacts += [artifact(p,"SOURCE") for p in source_paths]
    bundle_claims=[{"claim_id":c["claim_id"],"statement":c["statement"],"classification":c["classification"],"status":c["status"],"publication_wording":"SOURCE_ATTRIBUTED" if c["classification"]=="SOURCE_BOUND" else "NORMATIVE_DECLARATION","scope":c["boundary"],"proof_refs":[],"evidence_refs":[],"source_refs":[f"{REL}/SOURCE_BINDINGS.json#{sid}" for sid in c["sources"]]} for c in claims]
    policy_id=proof.identity(ROOT/"policy/zenodo-machine-proof-policy-v2.json")
    policy_id.pop("bytes")
    bundle={"_license":{"classification":"machine_readable_proof_bundle",**LIC},"schema":"qikvrt_zenodo_machine_proof_bundle_v2","policy":{"id":"qikvrt-zenodo-machine-proof-before-publication-v2","path":"policy/zenodo-machine-proof-policy-v2.json","version":"2.0.0",**policy_id},"publication_id":PID,"candidate":{"files":[candidate],"primary_document_path":primary},"claims":bundle_claims,"artifacts":artifacts,"prepublication_return":{"candidate_returned_to_owner":True,"content_changed":False,"change_notice_path":None,"receipt_path":f"{REL}/PREPUBLICATION_RETURN_RECEIPT.json"},"gates":dict.fromkeys(("candidate_frozen","all_claims_dispositioned","formal_claims_have_kernel_receipts","all_references_resolve","open_claims_not_worded_as_facts","returned_bytes_equal_upload_bytes","proof_bundle_in_upload_fileset"),True),"completion_claims":{"machine_proof_complete":True,"zenodo_upload_authorized":True}}
    write("MACHINE_PROOF_BUNDLE.json",bundle)
    bp=f"{REL}/MACHINE_PROOF_BUNDLE.json"
    uploads=[primary]+[a["path"] for a in artifacts]+[bp]
    verified=proof.validate_bundle(ROOT, ROOT/bp, upload_paths=uploads)
    metadata_sha=hashlib.sha256(json.dumps(metadata,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    receipt=ident(f"{REL}/PREPUBLICATION_RETURN_RECEIPT.json")
    statement=f"AUTHORIZE_EXACT_UPLOAD authorization_id={AID} publication_id={PID} return_sha256={receipt['sha256']} metadata_sha256={metadata_sha} machine_proof_sha256={verified['sha256']}"
    (D/"AUTHORIZE_EXACT_UPLOAD.txt").write_text("# PENDING: draft for a subsequent owner decision; not granted.\n"+statement+"\n",encoding="utf-8")
    write("PUBLICATION_CONTROL_PENDING.json",{"schema":"qikvrt_core_invariant_publication_pending_v1","publication_id":PID,"candidate_return_identity":receipt,"proof_identity":verified,"canonical_metadata_sha256":metadata_sha,"intended_upload_paths":uploads,"controls_excluded_from_upload":["AUTHORIZE_EXACT_UPLOAD.txt","PUBLICATION_CONTROL_PENDING.json","build_bundle.py"],"required_statement":statement,"machine_proof_gate_validated":True,"machine_proof_gate_term_boundary":"The schema-fixed zenodo_upload_authorized=true is only the machine-proof gate; independent canonical owner authorization remains absent.","owner_exact_upload_authorized":False,"owner_authorization_record_present":False,"production_mutations":0,"zenodo_record_id":None,"zenodo_public_readback":False,"native_review":False,"main_promotion":False,"EFFECT_ACK_DONE":False,"DONE":False,"PREDECESSOR_EVIDENCE_TRANSFER":False})
    print(json.dumps({"machine_proof_gate":"VALID","claims":len(claims),"upload_files":len(uploads),"owner_exact_upload_authorized":False}))

if __name__=="__main__":
    main()
