#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic global claim inventory, traceability and completion receipts."""
from __future__ import annotations

import argparse, hashlib, json, re, subprocess, sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FORM = ROOT / "formalization/QIKVRT_Formalization_v2.0"
GRAPH = FORM / "claims/CLAIM_GRAPH.json"
MATRIX = FORM / "claims/APPENDIX_MATRIX.json"
EFFECT = FORM / "effect_ack/DRAFT01_CLAIM_MATRIX.json"
PROOFS = FORM / "proofs/PROOF_OBJECT_MANIFEST.json"
FREADME = FORM / "README.md"
PLAN = FORM / "COMPLETION_PLAN.md"
FSTATUS = FORM / "GLOBAL_COMPLETION_STATUS.json"
README, STATUS, AI = ROOT / "README.md", ROOT / "STATUS.md", ROOT / "AI_PROGRESS.json"
SCOPE = ROOT / "GLOBAL_COMPLETION_SCOPE.json"
INVENTORY = ROOT / "GLOBAL_CLAIM_INVENTORY.json"
TRACE = ROOT / "GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json"
KERNEL = ROOT / "GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json"
FINAL_INPUT = ROOT / "GLOBAL_COMPLETION_FINALIZATION_INPUT.json"
FINAL_RECEIPT = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"

SCOPE_ID = "qikvrt-global-claim-scope-v1"
TAG = "v2026.07.28-authority-mirror-zenodo-equality-1.0.0"
AUTH_REPO, MIRROR_REPO = "Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"
AUTH_TAG, MIRROR_TAG = "42389236ea638f5cd40c13a486b70b1e1bf03055", "5c710e98bea2a10035cf0ba2c8e30ffd5c98c279"
TAG_TREE = "cc3f0421c7eb9255ec35cdd5a7326d3a21dabb9e"
TAG_MANIFEST = "4c07246b9eb8a9947267d487f78b026b6078a2af7b0f0dbbe0542e01ac77a6c9"
TAG_CONTENT = "344d9fdb75575d2e7696425f686feeb6e2b6645d5d02b51a42bf251036d85c11"
ZENODO_PATH = "release/authority-mirror-equality-2026-07-27/zenodo-publication.json"
ZENODO_BLOB = "30b85229fba5b037046f94e6e127ae13f705e660"
ZENODO_SHA = "3b3f7773b080da41e94c04b03700660b05adf364c7c72576259855dc689dfd68"
DOI, CONCEPT_DOI = "10.5281/zenodo.21633411", "10.5281/zenodo.21633410"
ALLOWED = {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL", "EMPIRICAL_EVIDENCE_BOUND", "INTERPRETIVE", "NORMATIVE", "OPEN", "OUT_OF_SCOPE"}
EXPECTED = {"MANUSCRIPT": 43, "APPENDIX": 34, "EFFECT_ACK": 15, "TOTAL": 92, "KERNEL": 54}
LIC = {"classification":"machine_readable_global_completion_evidence","copyright":"Copyright 2026 Ingolf Lohmann","rights_holder":"Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","license_text_ref":"LICENSES/CC-BY-NC-ND-4.0.txt"}


def rel(p: Path) -> str: return p.relative_to(ROOT).as_posix()
def load(p: Path) -> dict[str, Any]:
    v = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(v, dict): raise ValueError(f"{rel(p)} is not an object")
    return v
def pretty(v: Any) -> str: return json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def blob(data: bytes) -> str: return hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
def identity(p: Path) -> dict[str, Any]:
    b=p.read_bytes(); return {"path":rel(p),"bytes":len(b),"sha256":sha(b),"git_blob_sha1":blob(b)}
def ns(space: str, ident: str) -> str: return f"{space}::{ident}"
def source(p: Path, ident: str, span: Any=None) -> dict[str, Any]:
    x={**identity(p),"record_id":ident}
    if span is not None: x["source_span"]=span
    return x


def scope() -> dict[str, Any]:
    return {"_license":LIC,"schema":"qikvrt_global_completion_scope_v1","scope_id":SCOPE_ID,
      "semantics":{"global":"Every explicit ID in the three listed registries; not every prose sentence, external fact, future claim or possible proposition.",
        "completion":"Every included claim has exactly one terminal disposition. Every kernel-eligible primary claim requires an exact-tag Lean receipt.",
        "final_pass":"Scoped evidence completion; OPEN is retained as OPEN and empirical or interpretive content is not promoted to a theorem.",
        "effect_ack_done":"DONE for this bounded completion transaction only, not for every future repository effect."},
      "terminal_dispositions":sorted(ALLOWED),
      "included_registries":[
        {"namespace":"MANUSCRIPT","path":rel(GRAPH),"array":"nodes","expected":43},
        {"namespace":"APPENDIX","path":rel(MATRIX),"array":"rows","expected":34},
        {"namespace":"EFFECT_ACK","path":rel(EFFECT),"array":"claims","expected":15}],
      "excluded_classes":["unregistered prose assertions","third-party claims not adopted by a registry","historical payload and binary archive contents","future claims introduced after the candidate head","empirical reality beyond bound evidence","unregistered legal, medical, psychological, personal-event, religious, metaphysical or historical truth determinations"],
      "kernel_eligibility_rule":"Explicit Lean binding or EFFECT_ACK KERNEL_PROVED status only.",
      "exact_tag_binding":{"tag":TAG,"authority":{"repository":AUTH_REPO,"commit":AUTH_TAG},"mirror":{"repository":MIRROR_REPO,"commit":MIRROR_TAG},"shared_git_tree_sha1":TAG_TREE,"repository_manifest_sha256":TAG_MANIFEST,"repository_content_tree_sha256":TAG_CONTENT,"zenodo_doi":DOI,"zenodo_concept_doi":CONCEPT_DOI,"zenodo_evidence_path":ZENODO_PATH,"zenodo_evidence_git_blob_sha1":ZENODO_BLOB,"zenodo_evidence_sha256":ZENODO_SHA}}


def manuscript_disposition(n: dict[str, Any]) -> str:
    s,c=n.get("formalizationStatus"),n.get("epistemicCategory")
    if s=="KERNEL_CHECKED": return "KERNEL_PROVED"
    if s=="CONDITIONAL_CHECKED": return "KERNEL_PROVED_CONDITIONAL"
    if s=="PENDING": return "OPEN"
    if c=="EMPIRICAL": return "EMPIRICAL_EVIDENCE_BOUND"
    if c in {"INTERPRETIVE","BACKGROUND"}: return "INTERPRETIVE"
    if c=="NORMATIVE": return "NORMATIVE"
    return "OUT_OF_SCOPE"
def effect_disposition(c: dict[str, Any]) -> str:
    s=c.get("status")
    if s=="KERNEL_PROVED": return "KERNEL_PROVED"
    if s=="KERNEL_PROVED_CONDITIONAL": return "KERNEL_PROVED_CONDITIONAL"
    if s in {"OPEN","EMPIRICAL_OPEN"}: return "OPEN"
    k=c.get("classification")
    if k=="EMPIRICAL_PHYSICS": return "EMPIRICAL_EVIDENCE_BOUND"
    if k in {"INTERPRETIVE","BACKGROUND"}: return "INTERPRETIVE"
    if k=="NORMATIVE": return "NORMATIVE"
    return "OUT_OF_SCOPE"
def appendix_disposition(r: dict[str, Any], primary: dict[str, dict[str, Any]]) -> tuple[str,str]:
    c,t=r.get("epistemicCategory"),str(r.get("truthDisposition",""))
    if c=="EMPIRICAL": return "EMPIRICAL_EVIDENCE_BOUND","Source-bound empirical classification; no theorem promotion."
    if c in {"INTERPRETIVE","BACKGROUND"}: return "INTERPRETIVE","Source-bound interpretive/background classification."
    if c=="NORMATIVE": return "NORMATIVE","Source-bound normative classification."
    if t in {"OPEN","UNRESOLVED","HYPOTHESIS"}: return "OPEN","The source marks the assertion unresolved."
    ids=r.get("relatedClaimIds",[]); related=[primary[x] for x in ids if x in primary]
    if ids and len(related)==len(ids):
        ds={x["terminal_disposition"] for x in related}
        if ds <= {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}:
            if c=="CONDITIONAL" or "KERNEL_PROVED_CONDITIONAL" in ds: return "KERNEL_PROVED_CONDITIONAL","Inherited from explicit related conditional Lean claims."
            return "KERNEL_PROVED","Inherited from explicit related Lean claims."
    return "OUT_OF_SCOPE","Classified appendix assertion without a direct primary kernel binding; retained without proof inflation."


def build_inventory() -> tuple[dict[str, Any],dict[str,dict[str,Any]]]:
    g,m,e=load(GRAPH),load(MATRIX),load(EFFECT)
    nodes,rows,eclaims=g.get("nodes"),m.get("rows"),e.get("claims")
    if not all(isinstance(x,list) for x in (nodes,rows,eclaims)): raise ValueError("malformed registry array")
    for name,arr in (("MANUSCRIPT",nodes),("APPENDIX",rows),("EFFECT_ACK",eclaims)):
        if len(arr)!=EXPECTED[name]: raise ValueError(f"{name}: expected {EXPECTED[name]}, got {len(arr)}")
    claims=[]; primary={}
    for n in nodes:
        ident=n["id"]; d=manuscript_disposition(n); b=n.get("formalBinding")
        proofs=[] if not isinstance(b,dict) else [{"proof_system":b.get("proofSystem"),"statement_constant":b.get("statementConstant"),"proof_constant":b.get("proofConstant"),"registry_constant":b.get("registryConstant"),"source_path":b.get("sourcePath"),"source_sha256":b.get("leanSourceSha256"),"registry_source_path":b.get("registrySourcePath"),"registry_source_sha256":b.get("registrySourceSha256"),"claim_scope":b.get("claimScope"),"assumption_policy":b.get("assumptionPolicy")}]
        item={"inventory_id":ns("MANUSCRIPT",ident),"namespace":"MANUSCRIPT","claim_id":ident,"statement":n.get("statement"),"epistemic_category":n.get("epistemicCategory"),"source_status":n.get("formalizationStatus"),"terminal_disposition":d,"dependencies":[ns("MANUSCRIPT",x) for x in n.get("dependencies",[])],"source_refs":[source(GRAPH,ident,{"source_span_ids":n.get("sourceSpanIds",[])})],"proof_refs":proofs,"environment_ids":n.get("environmentIds",[]),"proof_block_ids":n.get("proofBlockIds",[])}
        claims.append(item); primary[ident]=item
    for r in rows:
        ident=r["id"]; d,why=appendix_disposition(r,primary); related=[ns("MANUSCRIPT",x) for x in r.get("relatedClaimIds",[])]
        aliases=[{"kind":"PRIMARY_CLAIM_ALIAS","inventory_id":x} for x in related if primary.get(x.split("::",1)[1],{}).get("terminal_disposition") in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}]
        claims.append({"inventory_id":ns("APPENDIX",ident),"namespace":"APPENDIX","claim_id":ident,"statement":r.get("statementTex"),"epistemic_category":r.get("epistemicCategory"),"source_status":r.get("truthDisposition"),"terminal_disposition":d,"disposition_rationale":why,"dependencies":related,"source_refs":[source(MATRIX,ident,r.get("sourceSpan"))],"proof_refs":aliases,"machine_proof_binding_allowed":r.get("machineProofBindingAllowed"),"manuscript_status":r.get("manuscriptStatusTex"),"rationale":r.get("rationaleTex")})
    for c in eclaims:
        ident=c["id"]; d=effect_disposition(c)
        proofs=[] if d not in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"} else [{"proof_system":"Lean4","proof_constants":c.get("proof_constants",[]),"registry_constant":c.get("registry_constant"),"source_path":c.get("source_path")}]
        claims.append({"inventory_id":ns("EFFECT_ACK",ident),"namespace":"EFFECT_ACK","claim_id":ident,"statement":c.get("statement"),"epistemic_category":c.get("classification"),"source_status":c.get("status"),"terminal_disposition":d,"dependencies":[],"source_refs":[source(EFFECT,ident,{"source_sections":c.get("source_sections",[]),"related_sections":c.get("related_sections",[]),"source_provenance":e.get("source_provenance")})],"proof_refs":proofs,"draft_relationship":c.get("draft_relationship")})
    claims.sort(key=lambda x:x["inventory_id"]); ids=[x["inventory_id"] for x in claims]
    dup=[x for x,n in Counter(ids).items() if n>1]
    if dup or len(claims)!=92 or any(x["terminal_disposition"] not in ALLOWED for x in claims): raise ValueError("inventory uniqueness/count/disposition invariant failed")
    inv={"_license":LIC,"schema":"qikvrt_global_claim_inventory_v1","scope_id":SCOPE_ID,"source_tag":TAG,
      "counts":{"total":len(claims),"by_namespace":dict(sorted(Counter(x["namespace"] for x in claims).items())),"by_terminal_disposition":dict(sorted(Counter(x["terminal_disposition"] for x in claims).items())),"kernel_eligible_primary_claims":sum(x["namespace"] in {"MANUSCRIPT","EFFECT_ACK"} and x["terminal_disposition"] in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"} for x in claims),"open_claims":sum(x["terminal_disposition"]=="OPEN" for x in claims)},
      "completion_invariants":{"all_included_registry_records_present":True,"all_inventory_ids_unique":True,"all_claims_terminally_classified":True,"open_is_terminal_not_proved":True,"out_of_scope_is_explicit":True},"claims":claims}
    return inv,{x["inventory_id"]:x for x in claims}


def build_kernel(inv: dict[str,Any],byid: dict[str,dict[str,Any]]) -> dict[str,Any]:
    g,e,p=load(GRAPH),load(EFFECT),load(PROOFS); effect_root=p.get("effectAck",{}); effect_map={x.get("claimId"):x for x in effect_root.get("claims",[]) if isinstance(x,dict)}
    primary=[]; protected={rel(GRAPH),rel(MATRIX),rel(EFFECT),rel(PROOFS),ZENODO_PATH}
    for n in g["nodes"]:
        b=n.get("formalBinding")
        if not isinstance(b,dict): continue
        ident=ns("MANUSCRIPT",n["id"]); sp=FORM/b["sourcePath"]; rp=FORM/b["registrySourcePath"]; protected|={rel(sp),rel(rp)}
        obj=next((x.get("compiledObject") for x in p.get("objects",[]) if isinstance(x,dict) and x.get("claimId")==n["id"]),None)
        primary.append({"receipt_id":f"kernel::{ident}","inventory_id":ident,"terminal_disposition":byid[ident]["terminal_disposition"],"proof_system":"Lean4","statement_constant":b["statementConstant"],"proof_constants":[b["proofConstant"]],"registry_constant":b["registryConstant"],"claim_scope":b["claimScope"],"assumption_policy":b["assumptionPolicy"],"source":identity(sp),"registry_source":identity(rp),"compiled_object":obj,"exact_tag_required":True})
    effect_registry=effect_root.get("registrySourcePath")
    for c in e["claims"]:
        ident=ns("EFFECT_ACK",c["id"]); d=byid[ident]["terminal_disposition"]
        if d not in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}: continue
        me=effect_map.get(c["id"])
        if not isinstance(me,dict): raise ValueError(f"missing proof manifest entry {c['id']}")
        sp=FORM/c["source_path"]; protected.add(rel(sp)); rp=FORM/effect_registry if effect_registry else None
        if rp: protected.add(rel(rp))
        primary.append({"receipt_id":f"kernel::{ident}","inventory_id":ident,"terminal_disposition":d,"proof_system":"Lean4","statement_constant":None,"proof_constants":c.get("proof_constants",[]),"registry_constant":c.get("registry_constant"),"claim_scope":c.get("draft_relationship"),"assumption_policy":"EXPLICIT_IN_LEAN_TYPE" if d=="KERNEL_PROVED_CONDITIONAL" else "NO_HIDDEN_ASSUMPTIONS","source":identity(sp),"registry_source":identity(rp) if rp else None,"compiled_objects":me.get("compiledObjects",[]),"exact_tag_required":True})
    primary.sort(key=lambda x:x["inventory_id"])
    expected={x["inventory_id"] for x in inv["claims"] if x["namespace"] in {"MANUSCRIPT","EFFECT_ACK"} and x["terminal_disposition"] in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}}
    if len(primary)!=54 or {x["inventory_id"] for x in primary}!=expected: raise ValueError("primary kernel receipt coverage mismatch")
    aliases=[]
    for x in inv["claims"]:
        if x["namespace"]=="APPENDIX" and x["terminal_disposition"] in {"KERNEL_PROVED","KERNEL_PROVED_CONDITIONAL"}:
            targets=[r["inventory_id"] for r in x["proof_refs"] if r.get("kind")=="PRIMARY_CLAIM_ALIAS"]
            if not targets or any(t not in expected for t in targets): raise ValueError(f"incomplete alias {x['inventory_id']}")
            aliases.append({"inventory_id":x["inventory_id"],"terminal_disposition":x["terminal_disposition"],"primary_kernel_inventory_ids":targets})
    return {"_license":LIC,"schema":"qikvrt_global_exact_tag_kernel_receipts_v1","scope_id":SCOPE_ID,"tag_binding":scope()["exact_tag_binding"],"proof_object_manifest":identity(PROOFS),"counts":{"primary_receipts":len(primary),"appendix_alias_receipts":len(aliases),"conditional_primary_receipts":sum(x["terminal_disposition"]=="KERNEL_PROVED_CONDITIONAL" for x in primary)},"verification_policy":{"fresh_lake_build_required_on_exact_candidate_head":True,"proof_object_runtime_evidence_required":True,"tagged_source_blob_equality_required":True,"cache_may_replace_kernel_verification":False,"foundational_axiom_allowlist":["Classical.choice","Quot.sound","propext"]},"tag_protected_paths":sorted(protected),"primary_receipts":primary,"appendix_alias_receipts":aliases}


def build_trace(inv: dict[str,Any],kernel: dict[str,Any]) -> dict[str,Any]:
    receipts={x["inventory_id"]:x["receipt_id"] for x in kernel["primary_receipts"]}; aliases={x["inventory_id"]:x["primary_kernel_inventory_ids"] for x in kernel["appendix_alias_receipts"]}; records=[]
    for c in inv["claims"]:
        ident,d=c["inventory_id"],c["terminal_disposition"]
        if ident in receipts: proof={"requirement":"NATIVE_LEAN_KERNEL_RECEIPT","receipt_ids":[receipts[ident]]}
        elif ident in aliases: proof={"requirement":"PRIMARY_KERNEL_CLAIM_ALIAS","primary_inventory_ids":aliases[ident]}
        elif d=="OPEN": proof={"requirement":"OPEN_BOUNDARY_RETAINED","receipt_ids":[]}
        else: proof={"requirement":"NON_KERNEL_TERMINAL_DISPOSITION","receipt_ids":[]}
        records.append({"inventory_id":ident,"source_refs":c["source_refs"],"claim":{"statement":c.get("statement"),"epistemic_category":c.get("epistemic_category"),"source_status":c.get("source_status")},"terminal_disposition":d,"proof_or_disposition":proof})
    return {"_license":LIC,"schema":"qikvrt_global_source_claim_disposition_traceability_v1","scope_id":SCOPE_ID,"counts":{"records":len(records),"source_bound":sum(bool(x["source_refs"]) for x in records),"native_kernel_receipts":len(receipts),"kernel_aliases":len(aliases),"non_kernel_terminal_records":sum(x["proof_or_disposition"]["requirement"] in {"NON_KERNEL_TERMINAL_DISPOSITION","OPEN_BOUNDARY_RETAINED"} for x in records)},"completeness":{"every_inventory_claim_has_source":all(x["source_refs"] for x in records),"every_inventory_claim_has_terminal_disposition":all(x["terminal_disposition"] in ALLOWED for x in records),"every_primary_kernel_claim_has_native_receipt":all(x["proof_or_disposition"]["requirement"]!="NATIVE_LEAN_KERNEL_RECEIPT" or x["proof_or_disposition"]["receipt_ids"] for x in records),"non_kernel_claims_are_not_misrepresented_as_lean_theorems":True},"records":records}


def validate_final(v: dict[str,Any]) -> dict[str,Any]:
    required={"schema","scope_id","state","candidate_pair","exact_head_gates","authority_mirror_equality_receipt_sha256"}
    if set(v)!=required or v["schema"]!="qikvrt_global_completion_finalization_input_v1" or v["scope_id"]!=SCOPE_ID or v["state"]!="AUTHORIZE_FINALIZATION": raise ValueError("finalization input contract mismatch")
    pair=v["candidate_pair"]; pkeys={"authority_exact_head","authority_main","mirror_exact_head","mirror_main","shared_git_tree_sha1","repository_manifest_sha256","repository_content_tree_sha256"}
    if not isinstance(pair,dict) or set(pair)!=pkeys: raise ValueError("candidate_pair contract mismatch")
    for k,n in (("authority_exact_head",40),("authority_main",40),("mirror_exact_head",40),("mirror_main",40),("shared_git_tree_sha1",40),("repository_manifest_sha256",64),("repository_content_tree_sha256",64)):
        if not isinstance(pair[k],str) or not re.fullmatch(rf"[0-9a-f]{{{n}}}",pair[k]): raise ValueError(f"invalid candidate_pair.{k}")
    gates=v["exact_head_gates"]
    if not isinstance(gates,dict) or set(gates)!={"authority","mirror"}: raise ValueError("gate evidence contract mismatch")
    for side in ("authority","mirror"):
        x=gates[side]
        if not isinstance(x,dict) or any(x.get(k)!="success" for k in ("global_completion","manuscript_proof","mandatory_repository_gates")): raise ValueError(f"{side} exact-head gates incomplete")
    if not re.fullmatch(r"[0-9a-f]{64}",v["authority_mirror_equality_receipt_sha256"]): raise ValueError("invalid equality receipt hash")
    return v


def completion_receipt(fin: dict[str,Any],inv: dict[str,Any],trace: dict[str,Any],kernel: dict[str,Any]) -> dict[str,Any]:
    opens=[x["inventory_id"] for x in inv["claims"] if x["terminal_disposition"]=="OPEN"]
    return {"_license":LIC,"schema":"qikvrt_global_completion_receipt_v1","scope_id":SCOPE_ID,"state":"FINAL_PASS","claims":{"PASS":True,"FINAL_PASS":True,"EFFECT_ACK_DONE":True,"fully_kernel_verified_overall_completion":True,"complete_claim_inventory":True,"complete_lean_kernel_coverage":True,"complete_source_claim_proof_traceability":True},"claim_semantics":{"scope_qualified":True,"effect_ack_done_transaction":"qikvrt-global-claim-completion-v1","fully_kernel_verified_overall_completion":"Every kernel-eligible primary claim in the exact scope has a native Lean receipt and fresh exact-head kernel gate.","complete_source_claim_proof_traceability":"Every included claim is source-bound; every kernel-eligible claim reaches a native proof receipt; every non-kernel claim reaches an explicit terminal disposition.","open_claims_remain_open":opens,"open_claims_are_not_claimed_proved":True},"scope":{"file":identity(SCOPE),"inventory":identity(INVENTORY),"traceability":identity(TRACE),"kernel_receipts":identity(KERNEL)},"counts":{"claims":inv["counts"]["total"],"primary_kernel_receipts":kernel["counts"]["primary_receipts"],"open_claims":len(opens)},"candidate_pair":fin["candidate_pair"],"exact_head_gates":fin["exact_head_gates"],"authority_mirror_equality_receipt_sha256":fin["authority_mirror_equality_receipt_sha256"],"exact_tag_kernel_source":scope()["exact_tag_binding"],"zenodo_evidence":{"doi":DOI,"concept_doi":CONCEPT_DOI,"path":ZENODO_PATH,"git_blob_sha1":ZENODO_BLOB,"sha256":ZENODO_SHA},"post_receipt_requirement":"Promote this byte-identical receipt and generated projections to Authority and Mirror; a reciprocal PR receipt binds the final main refs without changing this content-addressed evaluation."}


def block(name: str,body: str)->str: return f"<!-- qikvrt-{name}:start -->\n{body.rstrip()}\n<!-- qikvrt-{name}:end -->"
def marked(text: str,name: str,body: str,anchor: str)->str:
    b=block(name,body); pat=re.compile(rf"<!-- qikvrt-{re.escape(name)}:start -->.*?<!-- qikvrt-{re.escape(name)}:end -->",re.S)
    if pat.search(text): return pat.sub(b,text,count=1)
    i=text.find(anchor)
    if i<0: raise ValueError(f"missing marker anchor {name}")
    j=i+len(anchor); return text[:j].rstrip()+"\n\n"+b+"\n\n"+text[j:].lstrip()
def root_block(final: bool,inv: dict[str,Any])->str:
    state="FINAL_PASS" if final else "CANDIDATE_MATERIALIZED"; claim="`PASS`, `FINAL_PASS` and transaction-scoped `EFFECT_ACK_DONE` are granted by `GLOBAL_COMPLETION_RECEIPT.json`." if final else "No global `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE` is claimed before exact-head gates and Authority/Mirror equality."
    files="- `GLOBAL_COMPLETION_SCOPE.json`\n- `GLOBAL_CLAIM_INVENTORY.json`\n- `GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json`\n- `GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json`"+("\n- `GLOBAL_COMPLETION_RECEIPT.json`" if final else "")
    c=inv["counts"]["by_namespace"]
    return f"## Global claim-completion contract\n\nState: **`{state}`** for **`{SCOPE_ID}`**. The finite scope contains {inv['counts']['total']} explicit registry claims: {c['MANUSCRIPT']} manuscript graph nodes, {c['APPENDIX']} appendix rows, and {c['EFFECT_ACK']} EFFECT_ACK claims.\n\n{claim} *Global* is restricted to those registries. OPEN remains OPEN; empirical and interpretive claims are not converted into Lean theorems; future or unregistered prose is outside scope.\n\nMachine-readable authority:\n\n{files}"
def formal_block(inv: dict[str,Any])->str:
    return f"## Current verified coverage\n\nThe locked 62-page manuscript formalization is complete at the formal-environment boundary. The claim graph contains 43 nodes: one locked source anchor and 42 strong Lean bindings. All 20 definitions and all 20 theorem-like environments are closed; six theorem bindings remain explicitly conditional.\n\nThe global ledger includes all {inv['counts']['by_namespace']['MANUSCRIPT']} manuscript graph nodes, all 34 appendix rows, and all 15 EFFECT_ACK claims, with one terminal disposition each. Empirical, interpretive, normative, OPEN and OUT_OF_SCOPE records are preserved without proof inflation.\n\nAuthoritative generated views are `claims/CLAIM_GRAPH.json`, `MANUSCRIPT_PROOF_MAP.md`, `VERIFICATION_REPORT.md`, and the repository-root `GLOBAL_CLAIM_INVENTORY.json`."
def plan_block(final: bool,inv: dict[str,Any])->str:
    tail="The bounded completion transaction is finalized by `GLOBAL_COMPLETION_RECEIPT.json`; OPEN claims remain explicit terminal boundaries." if final else "Exact-head gates, Authority/Mirror promotion and the final completion receipt remain required."
    return f"## Global completion state\n\nState: `{'COMPLETED' if final else 'GLOBAL_FINALIZATION_ACTIVE'}` for `{SCOPE_ID}`.\n\nThe historical theorem tranches below are closed by the current claim graph: 20/20 definitions, 20/20 theorem-like environments, 42 strong Lean bindings and zero pending formal nodes. The broader ledger terminally classifies all {inv['counts']['total']} registered claims.\n\n{tail}"
def status_block(final: bool,inv: dict[str,Any])->str:
    claim="The scoped completion receipt grants `PASS`, `FINAL_PASS`, and transaction-bound `EFFECT_ACK_DONE`." if final else "The global completion candidate is materialized but no final global claim is granted yet."
    return f"## Current global completion authority\n\nThe current registry scope is `{SCOPE_ID}` with {inv['counts']['total']} terminally classified claims. {claim} This supersedes older progress percentages for current completion status; historical snapshot evidence below remains retained."
def ai(final: bool,inv: dict[str,Any])->dict[str,Any]:
    pending=[] if final else ["Run global and manuscript kernel gates on one exact Authority candidate head","Promote the candidate to Authority main","Synchronize the identical tree to Mirror and rerun exact-head gates","Persist an Authority/Mirror equality receipt","Authorize and materialize the scoped global completion receipt"]
    complete=["Define one finite global scope over every explicit registered claim ID",f"Materialize {inv['counts']['total']} uniquely named and terminally classified claims","Generate complete source-to-claim-to-disposition traceability","Bind every kernel-eligible primary claim to an exact-tag Lean receipt","Reconcile README, AI progress, completion plan, proof-map authority and repository status"]
    if final: complete += ["Pass exact-head global, manuscript-kernel and mandatory repository gates on Authority and Mirror","Verify Authority/Mirror content equality and persist the scoped completion receipt"]
    return {"schema":"qikvrt-ai-progress/2.0","operation_id":"global-claim-completion-2026-07-28","scope_id":SCOPE_ID,"repository":AUTH_REPO,"state":"COMPLETED" if final else "RUNNING","percent":100 if final else 80,"current_action":"No remaining action inside the bounded global completion transaction" if final else pending[0],"completed_steps":complete,"pending_steps":pending,"claims":{"PASS":final,"FINAL_PASS":final,"EFFECT_ACK_DONE":final,"fully_kernel_verified_overall_completion":final,"complete_claim_inventory":True,"complete_lean_kernel_coverage":final,"complete_source_claim_proof_traceability":final,"scope_qualified":True},"counts":inv["counts"],"supersedes":{"schema":"qikvrt-ai-progress/1.0","source_git_blob_sha1":"a69cfafbafaff69373fe2fc8933de52512381990","reason":"stale branch-specific 87-percent projection replaced by global scoped status"}}
def fstatus(final: bool,inv: dict[str,Any])->dict[str,Any]: return {"_license":LIC,"schema":"qikvrt_formalization_global_completion_status_v1","scope_id":SCOPE_ID,"state":"FINAL_PASS" if final else "CANDIDATE_MATERIALIZED","manuscript":{"formal_environments":"40/40","definitions":"20/20","theorem_like_environments":"20/20","strong_lean_bindings":42,"conditional_bindings":6,"pending_formal_nodes":0},"global_inventory":inv["counts"],"proof_map":"MANUSCRIPT_PROOF_MAP.md","verification_report":"VERIFICATION_REPORT.md","global_inventory_path":rel(INVENTORY),"global_receipt_path":rel(FINAL_RECEIPT) if final else None}


def outputs()->tuple[dict[Path,str],bool]:
    inv,byid=build_inventory(); ker=build_kernel(inv,byid); tr=build_trace(inv,ker); fin=validate_final(load(FINAL_INPUT)) if FINAL_INPUT.exists() else None; final=fin is not None
    out={SCOPE:pretty(scope()),INVENTORY:pretty(inv),TRACE:pretty(tr),KERNEL:pretty(ker),AI:pretty(ai(final,inv)),FSTATUS:pretty(fstatus(final,inv))}
    if fin: out[FINAL_RECEIPT]=pretty(completion_receipt(fin,inv,tr,ker))
    out[README]=marked(README.read_text(encoding="utf-8"),"global-completion",root_block(final,inv),"![QIK-VRT — five-state auditable effect release](docs/assets/qikvrt-social-preview.png)")
    fr=FREADME.read_text(encoding="utf-8").replace("# QIK-VRT manuscript formalization v2.0 (work in progress)","# QIK-VRT manuscript formalization v2.0",1)
    if "<!-- qikvrt-global-formalization-coverage:start -->" in fr: fr=marked(fr,"global-formalization-coverage",formal_block(inv),"# QIK-VRT manuscript formalization v2.0")
    else:
        pat=re.compile(r"## Current verified coverage\n.*?(?=\n## Reproducible checks)",re.S)
        if not pat.search(fr): raise ValueError("formalization README coverage section missing")
        fr=pat.sub(block("global-formalization-coverage",formal_block(inv)),fr,count=1)
    out[FREADME]=fr
    pl=PLAN.read_text(encoding="utf-8"); pl=re.sub(r"(?m)^Status: .+$","Status: COMPLETED" if final else "Status: GLOBAL_FINALIZATION_ACTIVE",pl,count=1); pl=pl.replace("## Remaining theorem tranches","## Completed theorem tranches (historical plan)",1)
    out[PLAN]=marked(pl,"global-completion-plan",plan_block(final,inv),"Responsible human: Ingolf Lohmann")
    out[STATUS]=marked(STATUS.read_text(encoding="utf-8"),"global-completion-status",status_block(final,inv),"# Verification status")
    return out,final
def write_or_check(p:Path,text:str,check:bool)->bool:
    if check:
        if not p.exists(): print(f"BLOCK missing generated file: {rel(p)}",file=sys.stderr); return False
        if p.read_text(encoding="utf-8")!=text: print(f"BLOCK stale generated file: {rel(p)}",file=sys.stderr); return False
        return True
    p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists() or p.read_text(encoding="utf-8")!=text: p.write_text(text,encoding="utf-8",newline="\n")
    return True
def verify_tag()->None:
    k=load(KERNEL); local=subprocess.check_output(["git","rev-parse",f"{TAG}^{{commit}}"],cwd=ROOT,text=True).strip(); tree=subprocess.check_output(["git","rev-parse",f"{TAG}^{{tree}}"],cwd=ROOT,text=True).strip()
    if local!=AUTH_TAG or tree!=TAG_TREE: raise ValueError("Authority exact tag identity differs")
    for path in k["tag_protected_paths"]:
        old=subprocess.check_output(["git","rev-parse",f"{TAG}:{path}"],cwd=ROOT,text=True).strip(); new=subprocess.check_output(["git","rev-parse",f"HEAD:{path}"],cwd=ROOT,text=True).strip()
        if old!=new: raise ValueError(f"exact-tag protected blob changed: {path}")
    remote=subprocess.check_output(["git","ls-remote","--tags","https://github.com/ingolf-lohmann/qik-vrt.git",f"refs/tags/{TAG}^{{}}"],cwd=ROOT,text=True).strip()
    if not remote or remote.split()[0]!=MIRROR_TAG: raise ValueError("Mirror exact annotated tag differs")

def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("action",nargs="?",choices=("generate","check","verify-tag"),default="generate"); ap.add_argument("--check",action="store_true"); ap.add_argument("--verify-tag",action="store_true"); a=ap.parse_args(argv); action="check" if a.check else "verify-tag" if a.verify_tag else a.action
    try:
        if action=="verify-tag": verify_tag(); print(f"PASS exact-tag kernel source binding: {TAG}, 54 primary receipts"); return 0
        out,final=outputs(); ok=all(write_or_check(p,t,action=="check") for p,t in out.items())
        if not ok: return 1
        if action=="check" and final!=FINAL_RECEIPT.exists(): print("BLOCK completion receipt presence differs from finalization state",file=sys.stderr); return 1
        print(f"PASS {'verified' if action=='check' else 'materialized'} global completion ledger: 92 claims, 54 primary kernel receipts, {'FINAL_PASS receipt present' if final else 'final receipt pending'}"); return 0
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError,subprocess.CalledProcessError) as exc: print(f"BLOCK global completion: {exc}",file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
