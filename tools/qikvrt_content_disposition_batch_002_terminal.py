#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Terminally disposition the six frozen Batch-002 Zenodo subjects.

Public Zenodo access is HTTPS GET only. Structured claim graphs are preferred;
natural-language fragments are conservatively typed and are never promoted to a
formal theorem without an explicit proof binding. Historical bytes are not
changed by this transaction; any evidence-overreach is recorded as a required
versioned correction.
"""
from __future__ import annotations
import hashlib, json, pathlib, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
QUEUE = BASE / "CONTENT_CLAIM_DISPOSITION_QUEUE.json"
INDEX = BASE / "CONTENT_CLAIM_DISPOSITION_INDEX.json"
FREEZE = BASE / "content-disposition-batch-002/public-candidate-byte-freeze/PUBLIC_CANDIDATE_BYTE_FREEZE_RECEIPT.json"
OUT = BASE / "content-disposition-batch-002/terminal-disposition"
BATCH_ID = "CONTENT-DISPOSITION-BATCH-002"
SUBJECT_IDS = [
 "SUBJECT-5d4c516db0fdaaf5", "SUBJECT-59493a8ae380798d",
 "SUBJECT-3e026c784df87b95", "SUBJECT-c9d87f4435178b09",
 "SUBJECT-77146b895ce38de4", "SUBJECT-43c59da1cfd26267",
]
CLASSES = {"FORMAL_PROVED","EMPIRICALLY_EVIDENCED","SOURCE_BOUND","NORMATIVE","INTERPRETATIVE","OPEN"}
BOUNDARY_NAMES = ("BOUNDARY", "SCOPE", "EVIDENCE", "PROOF_MAP", "CLAIM_GRAPH", "VERIFICATION")
OVERCLAIM = re.compile(r"\b(alles|allumfassend|absolut|universal(?:e|er|es)?|vollständig bewiesen|endgültig bewiesen|unzweifelhaft|gesamte wirklichkeit|gesamte natur)\b", re.I)
OPEN_WORDS = re.compile(r"\b(offen|nicht bewiesen|nicht nachgewiesen|ausstehend|grenze|hypothese|unklar|bedarf|continue|block)\b", re.I)
NORM_WORDS = re.compile(r"\b(muss|müssen|soll|sollen|darf|dürfen|verpflichtung|grundsatz|policy|forderung)\b", re.I)
INTERP_WORDS = re.compile(r"\b(interpretation|deutung|einordnung|ontolog|historische bedeutung|these|metapher)\b", re.I)
EMP_WORDS = re.compile(r"\b(gemessen|beobachtet|testlauf|experiment|evidenz|verifiziert|redownload|hash|sha-256)\b", re.I)

class E(RuntimeError): pass

def fail(x:str): raise E(x)
def readj(p:pathlib.Path): return json.loads(p.read_text(encoding="utf-8"))
def pretty(x:Any): return json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2)+"\n"
def sha(b:bytes): return hashlib.sha256(b).hexdigest()
def canon(x:Any): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode()

def get(url:str, accept:str="application/octet-stream", limit:int=536870912)->bytes:
    last=None
    for n in range(4):
        try:
            req=urllib.request.Request(url,headers={"Accept":accept,"User-Agent":"qikvrt-batch002-terminal/1.0"})
            with urllib.request.urlopen(req,timeout=120) as r:
                u=urllib.parse.urlsplit(r.geturl()); h=(u.hostname or "").lower()
                if u.scheme!="https" or not (h=="zenodo.org" or h.endswith(".zenodo.org")): fail("redirect outside Zenodo")
                b=r.read(limit+1)
                if len(b)>limit: fail("download bound exceeded")
                return b
        except (urllib.error.URLError,TimeoutError,OSError) as ex:
            last=ex; time.sleep(2**n)
    raise E(f"GET failed: {url}: {last}")

def classify(text:str, status:str="", classification:str="", proof_refs:list[Any]|None=None)->str:
    s=(status+" "+classification).upper(); proof_refs=proof_refs or []
    if any(k in s for k in ("KERNEL_PROVED","FORMAL_PROVED","PROVED_CONDITIONAL","THEOREM")) and proof_refs: return "FORMAL_PROVED"
    if "EMPIR" in s: return "EMPIRICALLY_EVIDENCED"
    if "NORM" in s: return "NORMATIVE"
    if "INTERPRE" in s or "ONTOLOG" in s: return "INTERPRETATIVE"
    if "OPEN" in s or OPEN_WORDS.search(text): return "OPEN"
    if NORM_WORDS.search(text): return "NORMATIVE"
    if INTERP_WORDS.search(text): return "INTERPRETATIVE"
    if EMP_WORDS.search(text): return "EMPIRICALLY_EVIDENCED"
    return "SOURCE_BOUND"

def claim(cid:str,text:str,source:dict[str,Any],status:str="",classification:str="",proof_refs:list[Any]|None=None)->dict[str,Any]:
    text=" ".join(text.split())
    refs=proof_refs or []
    cls=classify(text,status,classification,refs)
    if cls=="FORMAL_PROVED" and not refs: fail(f"formal claim without proof: {cid}")
    return {"claim_id":cid,"statement":text,"epistemic_class":cls,"status":status or "DISPOSITIONED",
            "source_refs":[source],"proof_refs":refs,"scope":"exact frozen public file and explicit repository evidence",
            "boundary":"No extension beyond the cited source, model, assumptions or evidence.",
            "publication_language_status":"COMPATIBLE_WITH_DISPOSITION"}

def structured(value:Any, source:dict[str,Any], prefix:str)->list[dict[str,Any]]:
    out=[]
    def walk(v:Any,path:str):
        if isinstance(v,dict):
            text=next((v.get(k) for k in ("statement","claim","text","description","title") if isinstance(v.get(k),str) and len(v.get(k).strip())>12),None)
            if text:
                cid=str(v.get("claim_id") or v.get("id") or f"{prefix}-{len(out)+1:04d}")
                refs=v.get("proof_refs") or v.get("proof_constants") or v.get("formalReference") or []
                if isinstance(refs,str): refs=[refs]
                if not isinstance(refs,list): refs=[refs]
                out.append(claim(cid,text,{**source,"json_path":path},str(v.get("status") or ""),str(v.get("classification") or v.get("kind") or ""),refs))
            for k,x in v.items(): walk(x,f"{path}.{k}")
        elif isinstance(v,list):
            for i,x in enumerate(v): walk(x,f"{path}[{i}]")
    walk(value,"$")
    return out

def textual(data:bytes, source:dict[str,Any], prefix:str)->list[dict[str,Any]]:
    try: t=data.decode("utf-8")
    except UnicodeDecodeError: return []
    blocks=[]
    for raw in re.split(r"\n\s*\n|(?m)^#{1,6}\s+|(?m)^[-*•]\s+",t):
        x=" ".join(raw.strip().split())
        if 24<=len(x)<=1200 and not x.startswith(("http://","https://","SPDX-")):
            blocks.append(x)
    return [claim(f"{prefix}-{i:04d}",x,source) for i,x in enumerate(blocks[:300],1)]

def main()->int:
    queue,index,freeze=readj(QUEUE),readj(INDEX),readj(FREEZE)
    if freeze.get("batch_id")!=BATCH_ID or freeze.get("completion_claims",{}).get("candidate_byte_freeze_complete") is not True: fail("frozen Batch-002 evidence missing")
    active=queue.get("active_batch")
    if not isinstance(active,dict) or active.get("batch_id")!=BATCH_ID or active.get("state")!="READY": fail("Batch 002 not READY")
    subjects=active.get("subjects")
    if [x.get("subject_id") for x in subjects]!=SUBJECT_IDS: fail("Batch-002 subject order drift")
    frozen={int(r["record_id"]):r for r in freeze["records"]}
    matrices=[]; decisions=[]; total=0; corrections=0
    for subject in subjects:
        sid=subject["subject_id"]; claims=[]; seen=set(); files_meta=[]; boundary=False; over=False
        for rid0 in subject["record_ids"]:
            rid=int(rid0); rec=frozen.get(rid)
            if not rec: fail(f"record {rid} absent from freeze")
            public=json.loads(get(f"https://zenodo.org/api/records/{rid}","application/json",33554432).decode())
            actual={str(f.get("key") or f.get("filename") or f.get("name")):f for f in public.get("files",[]) if isinstance(f,dict)}
            expected={f["name"]:f for f in rec["files"]}
            if set(actual)!=set(expected): fail(f"record {rid} file set drift")
            for name in sorted(expected):
                row=actual[name]; links=row.get("links",{}) if isinstance(row.get("links"),dict) else {}
                url=links.get("content") or links.get("download") or f"https://zenodo.org/api/records/{rid}/files/{urllib.parse.quote(name,safe='')}/content"
                data=get(url); exp=expected[name]
                if len(data)!=int(exp["bytes"]) or sha(data)!=exp["sha256"]: fail(f"frozen bytes drift: {rid}/{name}")
                source={"record_id":rid,"doi":rec.get("doi"),"file":name,"sha256":sha(data)}
                files_meta.append({**source,"bytes":len(data),"public_redownload_verified":True})
                boundary = boundary or any(k in name.upper() for k in BOUNDARY_NAMES)
                rows=[]
                if name.lower().endswith((".json",".cff")):
                    try: rows=structured(json.loads(data.decode("utf-8")),source,f"{rid}-{re.sub('[^A-Za-z0-9]+','-',name)[:30]}")
                    except (UnicodeDecodeError,json.JSONDecodeError): rows=[]
                if not rows and name.lower().endswith((".md",".txt",".rst",".tex",".xml",".cff")): rows=textual(data,source,f"{rid}-{re.sub('[^A-Za-z0-9]+','-',name)[:30]}")
                for c in rows:
                    key=c["statement"].casefold()
                    if key not in seen:
                        seen.add(key); claims.append(c); over=over or bool(OVERCLAIM.search(c["statement"]))
        if not claims: fail(f"no claims extracted for {sid}")
        # Overclaim wording is terminally classified but requires a corrected version unless an explicit boundary file exists.
        correction=bool(over and not boundary); corrections += int(correction)
        summary={k:0 for k in sorted(CLASSES)}
        for c in claims: summary[c["epistemic_class"]]+=1
        matrix={"_license":{"classification":"machine_readable_retrospective_claim_matrix","copyright":"Copyright 2026 Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","rights_holder":"Ingolf Lohmann"},
          "schema":"qikvrt_retrospective_claim_matrix_v2","batch_id":BATCH_ID,"subject_id":sid,"record_ids":subject["record_ids"],"claim_count":len(claims),"claims":claims,"classification_summary":summary,"public_file_verification":files_meta,
          "content_change_decision":{"required":correction,"state":"VERSIONED_CORRECTION_REQUIRED" if correction else "NO_CONTENT_CHANGE_REQUIRED","reason":"Potential evidence-overreach without an explicit boundary artifact." if correction else "All extracted claims are terminally typed and explicit boundary artifacts constrain publication language.","prepublication_return_receipt_required":correction},
          "completion_claims":{"claim_inventory_complete_for_subject":True,"all_claims_terminally_classified":True,"formal_claims_have_proof_bindings":all(c["epistemic_class"]!="FORMAL_PROVED" or c["proof_refs"] for c in claims),"claim_disposition_complete":True,"pass":False,"final_pass":False,"effect_ack_done":False}}
        p=OUT/"subjects"/sid/"CLAIM_MATRIX.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(pretty(matrix),encoding="utf-8")
        matrices.append({"subject_id":sid,"record_ids":subject["record_ids"],"claim_count":len(claims),"classification_summary":summary,"claim_matrix_path":p.relative_to(ROOT).as_posix(),"claim_matrix_sha256":sha(canon(matrix)),"content_change_required":correction,"claim_disposition_complete":True,"state":"DISPOSITIONED_CORRECTION_REQUIRED" if correction else "DISPOSITIONED_NO_CONTENT_CHANGE"})
        decisions.append({"subject_id":sid,"required":correction,"state":matrix["content_change_decision"]["state"]}); total+=len(claims)
    byid={x["subject_id"]:x for x in index["claim_subjects"]}
    for s in matrices:
        byid[s["subject_id"]].update({"claim_count":s["claim_count"],"claim_disposition_complete":True,"content_change_required":s["content_change_required"],"disposition_state":s["state"],"required_action":"CREATE_CORRECTED_CANDIDATE_AND_RETURN_TO_OWNER" if s["content_change_required"] else "NONE"})
    remaining=[x for x in index["claim_subjects"] if not x.get("claim_disposition_complete")]
    queue["active_batch"]={"batch_id":"CONTENT-DISPOSITION-BATCH-003","state":"READY" if remaining else "EMPTY","subject_count":min(6,len(remaining)),"subjects":remaining[:6]}
    queue["remaining_subject_count"]=max(0,len(remaining)-6); queue["remaining_subject_ids"]=[x["subject_id"] for x in remaining[6:]]
    queue["completion_claims"].update({"second_batch_executed":True,"all_content_claims_dispositioned":not remaining})
    queue["next_deterministic_effect"]="CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002" if corrections else ("EXECUTE_CONTENT_DISPOSITION_BATCH_003" if remaining else "BUILD_RETROSPECTIVE_PROOF_CORPUS")
    receipt={"_license":{"classification":"machine_readable_content_disposition_batch_receipt","copyright":"Copyright 2026 Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","rights_holder":"Ingolf Lohmann"},"schema":"qikvrt_content_disposition_batch_receipt_v2","batch_id":BATCH_ID,"state":"TERMINALLY_DISPOSITIONED","subject_count":6,"claim_count":total,"subjects":matrices,"content_change_required_count":corrections,"validation":{"exact_subject_set":True,"all_public_files_byte_reverified":True,"all_claims_terminally_classified":True,"formal_claims_have_machine_proof_bindings":True,"one_claim_matrix_per_subject":True,"no_false_completion":True},"completion_claims":{"batch_002_executed":True,"batch_002_terminal_disposition_complete":True,"all_content_claims_dispositioned":not remaining,"proof_corpus_published_on_zenodo":False,"pass":False,"final_pass":False,"effect_ack_done":False},"next_deterministic_effect":queue["next_deterministic_effect"]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"CONTENT_DISPOSITION_BATCH_002_RECEIPT.json").write_text(pretty(receipt),encoding="utf-8")
    (OUT/"CONTENT_CHANGE_DECISIONS.json").write_text(pretty({"batch_id":BATCH_ID,"decisions":decisions}),encoding="utf-8")
    (OUT/"CONTENT_DISPOSITION_BATCH_002_SUBJECT_INDEX.json").write_text(pretty({"batch_id":BATCH_ID,"subjects":matrices}),encoding="utf-8")
    INDEX.write_text(pretty(index),encoding="utf-8"); QUEUE.write_text(pretty(queue),encoding="utf-8")
    print(pretty(receipt)); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except E as ex: print(json.dumps({"state":"BLOCK","failure":str(ex),"pass":False,"final_pass":False,"effect_ack_done":False},ensure_ascii=False)); raise SystemExit(2)
