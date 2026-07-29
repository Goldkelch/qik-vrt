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
import copy, datetime as dt, hashlib, json, pathlib, re, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from collections import Counter
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
QUEUE = BASE / "CONTENT_CLAIM_DISPOSITION_QUEUE.json"
INDEX = BASE / "CONTENT_CLAIM_DISPOSITION_INDEX.json"
UNION_RECEIPT = BASE / "CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json"
FREEZE = BASE / "content-disposition-batch-002/public-candidate-byte-freeze/PUBLIC_CANDIDATE_BYTE_FREEZE_RECEIPT.json"
OUT = BASE / "content-disposition-batch-002/terminal-disposition"
AI_PROGRESS = ROOT / "AI_PROGRESS.json"
AI_STATUS = ROOT / "AI_STATUS.md"
GLOBAL_RECEIPT = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"
GLOBAL_FINALIZATION_INPUT = ROOT / "GLOBAL_COMPLETION_FINALIZATION_INPUT.json"
GLOBAL_RUN_EVIDENCE = ROOT / "evidence/receipts/global-completion-exact-head-runs-2026-07-29.json"
BATCH_ID = "CONTENT-DISPOSITION-BATCH-002"
WORK_UNIT_ID = "EXECUTE-FULL-CLAIM-EXTRACTION-AND-TERMINAL-DISPOSITION-FOR-BATCH-002-20260728"
OBSERVED_AT = "2026-07-28T22:03:32Z"
PROJECTION_UPDATED_AT = "2026-07-29T08:27:51Z"
UNION_OBSERVED_AT = "2026-07-28T16:20:00+02:00"
SOURCE_UNION_RECORDED_AT = "2026-07-28T17:10:00+02:00"
SOURCE_SHA = "4fd73232cc8d2189e14c950b376bb72ffcaf744e"
REMOTE_REF = "evidence/content-disposition-batch-002-terminal-20260728-v1"
AUTH_REPO = "Goldkelch/qik-vrt"
MIRROR_REPO = "ingolf-lohmann/qik-vrt"
SUBJECT_IDS = [
 "SUBJECT-5d4c516db0fdaaf5", "SUBJECT-59493a8ae380798d",
 "SUBJECT-3e026c784df87b95", "SUBJECT-c9d87f4435178b09",
 "SUBJECT-77146b895ce38de4", "SUBJECT-43c59da1cfd26267",
]
CLASSES = {"FORMAL_PROVED","EMPIRICALLY_EVIDENCED","SOURCE_BOUND","NORMATIVE","INTERPRETATIVE","OPEN"}
UNION_RECEIPT_PAYLOAD_KEYS = (
    "union_id", "work_unit_id", "observed_at", "source_binding_sha256",
    "canonical_union_content_sha256", "record_count", "observed_record_count",
    "reconciled_record_count", "claim_subject_count",
    "first_batch_subject_count", "concept_line_count",
    "payload_cluster_count", "duplicate_payload_cluster_count",
)
UNION_STATUS_KEYS = (
    "schema", "union_id", "status_updated_at", "state",
    "completion_claims", "next_deterministic_effect",
)
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
def git_object(spec:str)->str:
    try:
        return subprocess.check_output(["git","rev-parse",spec],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError) as ex:
        fail(f"Git source evidence is unavailable: {spec}: {ex}")

def git_bytes(spec:str)->bytes:
    try:
        return subprocess.check_output(
            ["git","show",spec],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
    except (OSError,subprocess.CalledProcessError) as ex:
        fail(f"Git source bytes are unavailable: {spec}: {ex}")

def git_json(path:str)->dict[str,Any]:
    try:
        value=json.loads(git_bytes(f"{SOURCE_SHA}:{path}"))
    except json.JSONDecodeError as ex:
        fail(f"Git source JSON is invalid: {path}: {ex}")
    if not isinstance(value,dict):
        fail(f"Git source JSON is not an object: {path}")
    return value

def source_evidence_paths()->tuple[str,...]:
    return (
        (OUT/"CONTENT_DISPOSITION_BATCH_002_RECEIPT.json").relative_to(ROOT).as_posix(),
        QUEUE.relative_to(ROOT).as_posix(),
        INDEX.relative_to(ROOT).as_posix(),
        UNION_RECEIPT.relative_to(ROOT).as_posix(),
        AI_PROGRESS.relative_to(ROOT).as_posix(),
        AI_STATUS.relative_to(ROOT).as_posix(),
    )

def build_source_evidence()->dict[str,Any]:
    commit=git_object(f"{SOURCE_SHA}^{{commit}}")
    if commit!=SOURCE_SHA:
        fail("projection-input commit does not resolve to the declared source SHA")
    return {
        "ref_name":REMOTE_REF,
        "commit":commit,
        "blobs":{
            path:git_object(f"{SOURCE_SHA}:{path}")
            for path in source_evidence_paths()
        },
    }

def source_projection_inputs()->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    return (
        git_json(QUEUE.relative_to(ROOT).as_posix()),
        git_json(INDEX.relative_to(ROOT).as_posix()),
        git_json(UNION_RECEIPT.relative_to(ROOT).as_posix()),
    )

def validate_source_union_identity(union_receipt:Mapping[str,Any])->None:
    if union_receipt.get("observed_at")!=SOURCE_UNION_RECORDED_AT:
        fail("source union receipt timestamp is not the known recorded projection timestamp")
    payload={key:union_receipt[key] for key in UNION_RECEIPT_PAYLOAD_KEYS}
    payload["observed_at"]=UNION_OBSERVED_AT
    if union_receipt.get("receipt_payload_sha256")!=sha(canon(payload)):
        fail("source union receipt identity digest does not bind the canonical observation")

def build_global_pass_evidence(global_receipt:Mapping[str,Any])->dict[str,Any]:
    pair=global_receipt.get("candidate_pair")
    checks=global_receipt.get("exact_head_gates")
    equality=global_receipt.get("authority_mirror_equality_receipt_sha256")
    claims=global_receipt.get("claims")
    finalization=readj(GLOBAL_FINALIZATION_INPUT)
    run_evidence=readj(GLOBAL_RUN_EVIDENCE)
    if (
        global_receipt.get("schema")!="qikvrt_global_completion_receipt_v1"
        or global_receipt.get("scope_id")!="qikvrt-global-claim-scope-v1"
        or global_receipt.get("state")!="FINAL_PASS"
        or not isinstance(pair,Mapping)
        or not isinstance(checks,Mapping)
        or set(checks)!={"authority","mirror"}
        or any(
            not isinstance(checks.get(side),Mapping)
            or set(checks[side])!={
                "global_completion","manuscript_proof",
                "mandatory_repository_gates",
            }
            or any(value!="success" for value in checks[side].values())
            for side in ("authority","mirror")
        )
        or not isinstance(claims,Mapping)
        or any(
            claims.get(key) is not True
            for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE")
        )
        or not re.fullmatch(r"[0-9a-f]{64}",str(equality or ""))
    ):
        fail("global scoped PASS receipt is invalid")
    if (
        finalization.get("schema")!="qikvrt_global_completion_finalization_input_v1"
        or finalization.get("scope_id")!="qikvrt-global-claim-scope-v1"
        or finalization.get("state")!="AUTHORIZE_FINALIZATION"
        or finalization.get("candidate_pair")!=pair
        or finalization.get("exact_head_gates")!=checks
        or finalization.get("authority_mirror_equality_receipt_sha256")!=equality
    ):
        fail("global scoped PASS finalization input drift")
    authority_sha=str(pair.get("authority_exact_head",""))
    mirror_sha=str(pair.get("mirror_exact_head",""))
    if not all(re.fullmatch(r"[0-9a-f]{40}",value) for value in (authority_sha,mirror_sha)):
        fail("global scoped PASS exact-head evidence is invalid")
    expected_runs={
        "authority":{
            "repository":AUTH_REPO,
            "exact_head":authority_sha,
            "run_id":30320366228,
            "job_id":90154785419,
        },
        "mirror":{
            "repository":MIRROR_REPO,
            "exact_head":mirror_sha,
            "run_id":30321259580,
            "job_id":90157437963,
        },
    }
    if (
        run_evidence.get("schema")!="qikvrt_global_completion_exact_head_run_evidence_v1"
        or run_evidence.get("scope_id")!="qikvrt-global-claim-scope-v1"
        or run_evidence.get("global_receipt_binding")!={
            "authority_mirror_equality_receipt_sha256":equality,
            "finalization_input_path":GLOBAL_FINALIZATION_INPUT.relative_to(ROOT).as_posix(),
            "finalization_input_sha256":sha(GLOBAL_FINALIZATION_INPUT.read_bytes()),
            "global_receipt_path":GLOBAL_RECEIPT.relative_to(ROOT).as_posix(),
            "global_receipt_sha256":sha(GLOBAL_RECEIPT.read_bytes()),
        }
        or run_evidence.get("boundary",{}).get("current_remote_state_claimed") is not False
        or run_evidence.get("boundary",{}).get("equality_payload_present_in_repository") is not False
    ):
        fail("global exact-head run evidence binding drift")
    for side,expected in expected_runs.items():
        observed=run_evidence.get(side)
        if not isinstance(observed,Mapping):
            fail(f"global exact-head run evidence missing: {side}")
        workflow=observed.get("workflow_run")
        job=observed.get("gate_job")
        if (
            observed.get("repository")!=expected["repository"]
            or observed.get("exact_head")!=expected["exact_head"]
            or not isinstance(workflow,Mapping)
            or workflow.get("run_id")!=expected["run_id"]
            or workflow.get("ref_name")!=f"actions/runs/{expected['run_id']}"
            or workflow.get("status")!="completed"
            or workflow.get("conclusion")!="success"
            or not isinstance(job,Mapping)
            or job.get("job_id")!=expected["job_id"]
            or job.get("conclusion")!="success"
            or not isinstance(job.get("steps"),Mapping)
            or set(job["steps"])!={
                "global_completion","manuscript_proof",
                "mandatory_repository_gates",
            }
            or any(
                step.get("conclusion")!="success"
                for step in job["steps"].values()
                if isinstance(step,Mapping)
            )
            or any(
                not isinstance(step,Mapping)
                for step in job["steps"].values()
            )
        ):
            fail(f"global exact-head run evidence invalid: {side}")
    return {
        "repository":[
            {
                "repository":AUTH_REPO,
                "ref_name":"actions/runs/30320366228",
                "source_sha":authority_sha,
            },
            {
                "repository":MIRROR_REPO,
                "ref_name":"actions/runs/30321259580",
                "source_sha":mirror_sha,
            },
        ],
        "checks":{
            "receipt_gate_matrix":copy.deepcopy(checks),
            "exact_head_runs":{
                side:{
                    "run_id":expected_runs[side]["run_id"],
                    "job_id":expected_runs[side]["job_id"],
                    "gate_steps":copy.deepcopy(run_evidence[side]["gate_job"]["steps"]),
                }
                for side in ("authority","mirror")
            },
        },
        "evidence":{
            "path":GLOBAL_RECEIPT.relative_to(ROOT).as_posix(),
            "sha256":sha(GLOBAL_RECEIPT.read_bytes()),
            "finalization_input_path":GLOBAL_FINALIZATION_INPUT.relative_to(ROOT).as_posix(),
            "finalization_input_sha256":sha(GLOBAL_FINALIZATION_INPUT.read_bytes()),
            "exact_head_run_evidence_path":GLOBAL_RUN_EVIDENCE.relative_to(ROOT).as_posix(),
            "exact_head_run_evidence_sha256":sha(GLOBAL_RUN_EVIDENCE.read_bytes()),
            "candidate_pair":copy.deepcopy(dict(pair)),
            "authority_mirror_equality_receipt_sha256":equality,
            "equality_payload_present_in_repository":False,
        },
    }

def get(url:str, accept:str="application/octet-stream, */*;q=0.1", limit:int=536870912)->bytes:
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
    for raw in re.split(r"\n\s*\n|^#{1,6}\s+|^[-*•]\s+",t,flags=re.M):
        x=" ".join(raw.strip().split())
        if 24<=len(x)<=1200 and not x.startswith(("http://","https://","SPDX-")):
            blocks.append(x)
    return [claim(f"{prefix}-{i:04d}",x,source) for i,x in enumerate(blocks[:300],1)]

def validate_terminal_receipt(receipt:Mapping[str,Any], index:Mapping[str,Any])->None:
    if receipt.get("schema")!="qikvrt_content_disposition_batch_receipt_v2":
        fail("terminal Batch-002 receipt schema invalid")
    if receipt.get("batch_id")!=BATCH_ID or receipt.get("state")!="TERMINALLY_DISPOSITIONED":
        fail("terminal Batch-002 receipt identity invalid")
    for key,expected in (
        ("work_unit_id",WORK_UNIT_ID),
        ("observed_at",OBSERVED_AT),
        ("union_id",index.get("union_id")),
    ):
        if key in receipt and receipt.get(key)!=expected:
            fail(f"terminal Batch-002 receipt {key} drift")
    matrices=receipt.get("subjects")
    if not isinstance(matrices,list) or len(matrices)!=len(SUBJECT_IDS):
        fail("terminal Batch-002 subject index invalid")
    if receipt.get("subject_count")!=len(matrices):
        fail("terminal Batch-002 subject count invalid")
    if [x.get("subject_id") for x in matrices]!=SUBJECT_IDS:
        fail("terminal Batch-002 subject order invalid")
    if receipt.get("claim_count")!=sum(int(x.get("claim_count",0)) for x in matrices):
        fail("terminal Batch-002 claim count invalid")
    if receipt.get("content_change_required_count")!=sum(bool(x.get("content_change_required")) for x in matrices):
        fail("terminal Batch-002 correction count invalid")
    completion=receipt.get("completion_claims")
    if not isinstance(completion,Mapping):
        fail("terminal Batch-002 completion claims missing")
    if completion.get("batch_002_executed") is not True or completion.get("batch_002_terminal_disposition_complete") is not True:
        fail("terminal Batch-002 completion evidence invalid")
    for key in ("all_content_claims_dispositioned","proof_corpus_published_on_zenodo","pass","final_pass","effect_ack_done"):
        if completion.get(key) is not False:
            fail(f"terminal Batch-002 false-completion boundary violated: {key}")
    validation=receipt.get("validation")
    required_validation=("exact_subject_set","all_public_files_byte_reverified","all_claims_terminally_classified","formal_claims_have_machine_proof_bindings","one_claim_matrix_per_subject","no_false_completion")
    if not isinstance(validation,Mapping) or any(validation.get(key) is not True for key in required_validation):
        fail("terminal Batch-002 validation claims invalid")
    if receipt.get("next_deterministic_effect")!="CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002":
        fail("terminal Batch-002 next effect invalid")
    subjects_by_id={str(x["subject_id"]):x for x in index["claim_subjects"]}
    for summary in matrices:
        sid=str(summary["subject_id"])
        if sid not in subjects_by_id:
            fail(f"terminal Batch-002 subject absent from union index: {sid}")
        expected_path=(OUT/"subjects"/sid/"CLAIM_MATRIX.json").relative_to(ROOT).as_posix()
        if summary.get("claim_matrix_path")!=expected_path:
            fail(f"claim matrix path invalid: {sid}")
        matrix_path=ROOT/expected_path
        matrix=readj(matrix_path)
        if summary.get("claim_matrix_sha256")!=sha(canon(matrix)):
            fail(f"claim matrix digest invalid: {sid}")
        if matrix.get("batch_id")!=BATCH_ID or matrix.get("subject_id")!=sid:
            fail(f"claim matrix identity invalid: {sid}")
        if (
            matrix.get("record_ids")!=subjects_by_id[sid].get("record_ids")
            or summary.get("record_ids")!=matrix.get("record_ids")
        ):
            fail(f"claim matrix record binding invalid: {sid}")
        claims=matrix.get("claims")
        if (
            not isinstance(claims,list)
            or matrix.get("claim_count")!=len(claims)
            or matrix.get("claim_count")!=summary.get("claim_count")
        ):
            fail(f"claim matrix count invalid: {sid}")
        if matrix.get("classification_summary")!=summary.get("classification_summary"):
            fail(f"claim matrix classification summary invalid: {sid}")
        classification=matrix.get("classification_summary")
        if (
            not isinstance(classification,Mapping)
            or set(classification)!=CLASSES
            or any(
                isinstance(value,bool) or not isinstance(value,int) or value<0
                for value in classification.values()
            )
            or sum(classification.values())!=matrix["claim_count"]
        ):
            fail(f"claim matrix classification total invalid: {sid}")
        if any(
            not isinstance(item,Mapping)
            or item.get("epistemic_class") not in CLASSES
            or (
                item.get("epistemic_class")=="FORMAL_PROVED"
                and not item.get("proof_refs")
            )
            for item in claims
        ):
            fail(f"claim matrix claim/proof boundary invalid: {sid}")
        decision=matrix.get("content_change_decision")
        if not isinstance(decision,Mapping) or not isinstance(decision.get("required"),bool):
            fail(f"claim matrix content-change decision invalid: {sid}")
        correction=decision["required"]
        expected_state=(
            "DISPOSITIONED_CORRECTION_REQUIRED"
            if correction else
            "DISPOSITIONED_NO_CONTENT_CHANGE"
        )
        if (
            summary.get("content_change_required") is not correction
            or summary.get("state")!=expected_state
            or summary.get("claim_disposition_complete") is not True
        ):
            fail(f"terminal Batch-002 summary/decision binding invalid: {sid}")
        completion_claims=matrix.get("completion_claims")
        if (
            not isinstance(completion_claims,Mapping)
            or completion_claims.get("claim_inventory_complete_for_subject") is not True
            or completion_claims.get("all_claims_terminally_classified") is not True
            or completion_claims.get("formal_claims_have_proof_bindings") is not True
            or completion_claims.get("claim_disposition_complete") is not True
            or any(
                completion_claims.get(key) is not False
                for key in ("pass","final_pass","effect_ack_done")
            )
        ):
            fail(f"claim matrix completion invalid: {sid}")

def validate_ai_progress(progress:Mapping[str,Any])->None:
    required={
        "schema","operation_id","repository","ref_name","source_sha","source_semantics",
        "source_evidence",
        "state","effect_state","percent","percent_scope","current_action",
        "completed_steps","pending_steps","blockers","next_action","updated_at",
        "claims","scopes","incomplete_scope_count","repository_effects",
        "projection_owner","union_receipt_state",
    }
    if not required.issubset(progress):
        fail(f"AI progress missing fields: {sorted(required-set(progress))}")
    if (
        progress.get("schema")!="qikvrt-ai-progress/3.0"
        or progress.get("state") not in {
            "IDLE","RUNNING","WAITING","PASS","BLOCK",
            "FAIL","TIMEOUT","CANCELLED",
        }
    ):
        fail("AI progress durable snapshot identity invalid")
    if not re.fullmatch(r"[0-9a-f]{40}",str(progress.get("source_sha",""))):
        fail("AI progress source SHA invalid")
    source_evidence=progress.get("source_evidence")
    if not isinstance(source_evidence,Mapping):
        fail("AI progress source evidence missing")
    expected_source=build_source_evidence()
    if source_evidence!=expected_source:
        fail("AI progress source evidence does not bind the declared commit and blobs")
    if source_evidence.get("ref_name")!=progress.get("ref_name") or source_evidence.get("commit")!=progress.get("source_sha"):
        fail("AI progress source evidence identity drift")
    try:
        dt.datetime.fromisoformat(str(progress["updated_at"]).replace("Z","+00:00"))
    except ValueError as ex:
        fail(f"AI progress timestamp invalid: {ex}")
    scopes=progress.get("scopes")
    if not isinstance(scopes,Mapping) or progress.get("percent_scope") not in scopes:
        fail("AI progress percent scope invalid")
    if progress.get("percent")!=scopes[progress["percent_scope"]].get("percent"):
        fail("AI progress percentage is not bound to its named scope")
    incomplete=sum(1 for scope in scopes.values() if scope.get("effect_state")!="EFFECT_ACK_DONE")
    if progress.get("incomplete_scope_count")!=incomplete:
        fail("AI progress incomplete-scope count invalid")
    claims=progress.get("claims")
    if not isinstance(claims,Mapping):
        fail("AI progress top-level claims missing")
    if progress.get("effect_state") in {"EFFECT_ACK_CONTINUE","EFFECT_ACK_BLOCK"} and any(claims.get(key) is not False for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE")):
        fail("AI progress top-level release inflation")
    if incomplete and progress.get("effect_state")!="EFFECT_ACK_CONTINUE":
        fail("AI progress incomplete sibling scope requires top-level CONTINUE")
    if not incomplete and (
        progress.get("state")!="PASS"
        or progress.get("effect_state")!="EFFECT_ACK_DONE"
        or any(
            claims.get(key) is not True
            for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE")
        )
    ):
        fail("AI progress complete scopes require top-level PASS/DONE")
    for scope_id,scope in scopes.items():
        if not isinstance(scope,Mapping):
            fail(f"AI progress scope invalid: {scope_id}")
        scope_claims=scope.get("claims")
        if not isinstance(scope_claims,Mapping):
            fail(f"AI progress scope claims missing: {scope_id}")
        effect=scope.get("effect_state")
        values=[scope_claims.get(key) for key in ("PASS","FINAL_PASS","EFFECT_ACK_DONE")]
        if effect=="EFFECT_ACK_DONE":
            if scope.get("state")!="FINAL_PASS" or any(value is not True for value in values):
                fail(f"AI progress DONE scope is not FINAL_PASS: {scope_id}")
            pass_evidence=scope.get("pass_evidence")
            if not isinstance(pass_evidence,Mapping):
                fail(f"AI progress DONE scope lacks PASS evidence: {scope_id}")
            repositories=pass_evidence.get("repository")
            if (
                not isinstance(repositories,list)
                or not repositories
                or any(
                    not isinstance(item,Mapping)
                    or not isinstance(item.get("repository"),str)
                    or not isinstance(item.get("ref_name"),str)
                    or not re.fullmatch(r"[0-9a-f]{40}",str(item.get("source_sha","")))
                    for item in repositories
                )
                or not isinstance(pass_evidence.get("checks"),Mapping)
                or not isinstance(pass_evidence.get("evidence"),Mapping)
            ):
                fail(f"AI progress DONE scope PASS evidence invalid: {scope_id}")
            if scope_id=="qikvrt-global-claim-scope-v1":
                if pass_evidence!=build_global_pass_evidence(readj(GLOBAL_RECEIPT)):
                    fail("AI progress global PASS evidence drift")
        elif effect in {"EFFECT_ACK_CONTINUE","EFFECT_ACK_BLOCK"}:
            if any(value is not False for value in values):
                fail(f"AI progress incomplete scope inflates release: {scope_id}")
        else:
            fail(f"AI progress scope effect state invalid: {scope_id}")
    effects=progress.get("repository_effects")
    if not isinstance(effects,Mapping) or set(effects)!={
        "scope","authority_promotion","mirror_synchronization",
        "reciprocal_equality_receipt","proof_corpus_publication",
    } or any(
        value!="NOT_EVALUATED" for key,value in effects.items() if key!="scope"
    ):
        fail("AI progress transient repository effects must remain unevaluated")
    owner=progress.get("projection_owner")
    if owner!={
        "tool":"tools/qikvrt_content_disposition_batch_002_terminal.py",
        "check_command":"python3 -B tools/qikvrt_content_disposition_batch_002_terminal.py --check-status-projection",
    }:
        fail("AI progress projection owner invalid")

def _project_status_unchecked(
    queue:dict[str,Any],
    index:dict[str,Any],
    union_receipt:dict[str,Any],
    matrices:list[dict[str,Any]],
    total:int,
    corrections:int,
)->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    """Apply the projection after the caller has authenticated its input."""
    queue=copy.deepcopy(queue); index=copy.deepcopy(index); union_receipt=copy.deepcopy(union_receipt)
    if [x.get("subject_id") for x in matrices] != SUBJECT_IDS:
        fail("Batch-002 terminal subject order drift")
    if sum(int(x.get("claim_count",0)) for x in matrices) != total:
        fail("Batch-002 terminal claim-count drift")
    if sum(bool(x.get("content_change_required")) for x in matrices) != corrections:
        fail("Batch-002 terminal correction-count drift")

    byid={str(x["subject_id"]):x for x in index["claim_subjects"]}
    for summary in matrices:
        row=byid[summary["subject_id"]]
        row.update({
            "claim_count":summary["claim_count"],
            "claim_disposition_complete":True,
            "content_change_required":summary["content_change_required"],
            "disposition_state":summary["state"],
            "required_action":"CREATE_CORRECTED_CANDIDATE_AND_RETURN_TO_OWNER" if summary["content_change_required"] else "NONE",
            "claim_matrix_path":summary["claim_matrix_path"],
            "claim_matrix_sha256":summary["claim_matrix_sha256"],
            "classification_summary":summary["classification_summary"],
        })

    records_by_id={int(x["record_id"]):x for x in index["records"]}
    for subject in index["claim_subjects"]:
        if subject.get("claim_disposition_complete") is not True:
            continue
        for rid in subject["record_ids"]:
            record=records_by_id[int(rid)]
            record.update({
                "claim_disposition_complete":True,
                "content_change_required":subject["content_change_required"],
                "disposition_state":subject["disposition_state"],
                "required_action":subject["required_action"],
            })

    remaining=[x for x in index["claim_subjects"] if not x.get("claim_disposition_complete")]
    next_effect=(
        "CREATE_CORRECTED_CANDIDATES_AND_RETURN_TO_OWNER_FOR_BATCH_002"
        if corrections else
        ("EXECUTE_CONTENT_DISPOSITION_BATCH_003" if remaining else "BUILD_RETROSPECTIVE_PROOF_CORPUS")
    )
    index["batch_002"]={
        "batch_id":BATCH_ID,
        "state":"TERMINALLY_DISPOSITIONED",
        "completed_at":OBSERVED_AT,
        "subject_count":len(matrices),
        "claim_count":total,
        "content_change_required_count":corrections,
        "corrected_candidate_count":0,
        "corrected_candidate_required_count":corrections,
        "all_content_change_decisions_complete":True,
        "subjects":matrices,
    }
    index["completion_claims"].update({
        "second_batch_executed":True,
        "second_batch_terminal_disposition_complete":True,
        "all_content_claims_dispositioned":not remaining,
    })
    index["next_deterministic_effect"]=next_effect
    index["observed_at"]=PROJECTION_UPDATED_AT
    index["state"]="BATCH_002_TERMINALLY_DISPOSITIONED"
    if corrections:
        index["state"]+="_CORRECTION_REQUIRED"
    if remaining:
        index["state"]+="_BATCH_003_READY"

    queue["active_batch"]={
        "batch_id":"CONTENT-DISPOSITION-BATCH-003",
        "state":"READY" if remaining else "EMPTY",
        "subject_count":min(6,len(remaining)),
        "subjects":remaining[:6],
    }
    queue["remaining_subject_count"]=max(0,len(remaining)-6)
    queue["remaining_subject_ids"]=[x["subject_id"] for x in remaining[6:]]
    batch_entry={
        "batch_id":BATCH_ID,
        "state":"TERMINALLY_DISPOSITIONED",
        "completed_at":OBSERVED_AT,
        "subject_ids":SUBJECT_IDS,
        "claim_count":total,
        "content_change_required_count":corrections,
    }
    queue["completed_batches"]=[
        x for x in queue.get("completed_batches",[])
        if x.get("batch_id") != BATCH_ID
    ]+[batch_entry]
    queue["completion_claims"].update({
        "second_batch_executed":True,
        "all_content_claims_dispositioned":not remaining,
    })
    queue["next_deterministic_effect"]=next_effect
    queue["observed_at"]=PROJECTION_UPDATED_AT
    if corrections and remaining:
        queue["state"]="BATCH_002_CORRECTION_REQUIRED_BATCH_003_READY"
    elif corrections:
        queue["state"]="BATCH_002_CORRECTION_REQUIRED"
    elif remaining:
        queue["state"]="ACTIVE_BATCH_003_READY"
    else:
        queue["state"]="ALL_CONTENT_CLAIMS_DISPOSITIONED"

    union_receipt["state"]=(
        "CONTENT_DISPOSITION_BATCH_002_TERMINALLY_DISPOSITIONED_CORRECTION_REQUIRED"
        if corrections else
        "CONTENT_DISPOSITION_BATCH_002_TERMINALLY_DISPOSITIONED"
    )
    union_receipt["observed_at"]=UNION_OBSERVED_AT
    union_receipt["status_updated_at"]=PROJECTION_UPDATED_AT
    union_receipt["completion_claims"].update({
        "content_disposition_batch_002_terminal_disposition_complete":True,
        "content_disposition_batch_002_correction_required":bool(corrections),
        "all_content_claims_dispositioned":not remaining,
        "all_required_corrected_candidates_returned_to_owner":False,
        "content_correction_review_complete":False,
        "proof_corpus_published_on_zenodo":False,
        "mirror_synchronized":False,
        "pass":False,
        "final_pass":False,
        "effect_ack_done":False,
    })
    union_receipt["next_deterministic_effect"]=next_effect
    payload={key:union_receipt[key] for key in UNION_RECEIPT_PAYLOAD_KEYS}
    union_receipt["receipt_payload_sha256"]=sha(canon(payload))
    status_payload={key:union_receipt[key] for key in UNION_STATUS_KEYS}
    union_receipt["status_projection_sha256"]=sha(canon(status_payload))
    return queue,index,union_receipt

def project_status(
    queue:dict[str,Any],
    index:dict[str,Any],
    union_receipt:dict[str,Any],
    matrices:list[dict[str,Any]],
    total:int,
    corrections:int,
)->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    """Project only from the exact source snapshot or exact idempotent result."""
    source_queue,source_index,source_union=source_projection_inputs()
    validate_source_union_identity(source_union)
    expected=_project_status_unchecked(
        source_queue,source_index,source_union,matrices,total,corrections,
    )
    supplied=(queue,index,union_receipt)
    source=(source_queue,source_index,source_union)
    if supplied!=source and supplied!=expected:
        fail("refuse mixed, forged, unknown or later status projection input")
    return copy.deepcopy(expected)

def build_ai_progress(
    queue:dict[str,Any],
    index:dict[str,Any],
    union_receipt:dict[str,Any],
    receipt:dict[str,Any],
)->dict[str,Any]:
    global_receipt=readj(GLOBAL_RECEIPT)
    complete=[x for x in index["claim_subjects"] if x.get("claim_disposition_complete")]
    pending=[x for x in index["claim_subjects"] if not x.get("claim_disposition_complete")]
    corpus_id=str(index["union_id"])
    corpus_percent=(len(complete)*100)//len(index["claim_subjects"])
    global_counts=global_receipt["counts"]
    progress={
        "schema":"qikvrt-ai-progress/3.0",
        "operation_id":"zenodo-canonical-union-content-disposition-2026-07-28",
        "repository":"Goldkelch/qik-vrt",
        "ref_name":REMOTE_REF,
        "source_sha":SOURCE_SHA,
        "source_evidence":build_source_evidence(),
        "state":"IDLE",
        "effect_state":"EFFECT_ACK_CONTINUE",
        "percent":corpus_percent,
        "percent_scope":corpus_id,
        "current_action":"No live operation owns this stable handoff snapshot.",
        "completed_steps":[
            "Build the canonical 24-record Zenodo union with 19 byte-distinct claim subjects",
            "Terminally disposition Batch 001 with six subjects",
            f"Terminally disposition Batch 002 with {receipt['subject_count']} subjects and {receipt['claim_count']} claims",
            "Stage Batch 003 deterministically with six subjects and one subject beyond the active batch",
        ],
        "pending_steps":[
            "Create the required corrected Batch-002 candidate and return it to the responsible owner",
            "Terminally disposition the seven remaining Zenodo claim subjects",
            "Build and verify the retrospective proof corpus before any publication effect",
            "Bind any later Authority promotion, Mirror synchronization and symmetric-scope claim to fresh repository evidence",
        ],
        "blockers":[],
        "next_action":queue["next_deterministic_effect"],
        "updated_at":PROJECTION_UPDATED_AT,
        "source_semantics":"Projection input provenance; not a claim about the current remote head.",
        "claims":{"PASS":False,"FINAL_PASS":False,"EFFECT_ACK_DONE":False,"scope_qualified":True},
        "scopes":{
            str(global_receipt["scope_id"]):{
                "state":"FINAL_PASS",
                "effect_state":"EFFECT_ACK_DONE",
                "percent":100,
                "claims":{
                    "PASS":True,
                    "FINAL_PASS":True,
                    "EFFECT_ACK_DONE":True,
                    "kernel_coverage_complete_for_scope":True,
                },
                "counts":{
                    "claims":global_counts["claims"],
                    "primary_kernel_receipts":global_counts["primary_kernel_receipts"],
                    "open_claims":global_counts["open_claims"],
                },
                "evidence":"GLOBAL_COMPLETION_RECEIPT.json",
                "pass_evidence":build_global_pass_evidence(global_receipt),
                "boundary":"Only the three finite registries declared by GLOBAL_COMPLETION_SCOPE.json; OPEN remains OPEN.",
            },
            corpus_id:{
                "state":"CONTINUE",
                "effect_state":"EFFECT_ACK_CONTINUE",
                "percent":corpus_percent,
                "claims":{"PASS":False,"FINAL_PASS":False,"EFFECT_ACK_DONE":False},
                "counts":{
                    "subjects":len(index["claim_subjects"]),
                    "dispositioned_subjects":len(complete),
                    "open_subjects":len(pending),
                    "dispositioned_claims":sum(int(x["claim_count"]) for x in complete),
                },
                "batch_002":{
                    "state":receipt["state"],
                    "subjects":receipt["subject_count"],
                    "claims":receipt["claim_count"],
                    "content_change_required_count":receipt["content_change_required_count"],
                        "evidence":{
                            "path":(OUT/"CONTENT_DISPOSITION_BATCH_002_RECEIPT.json").relative_to(ROOT).as_posix(),
                            "sha256":sha(pretty(receipt).encode("utf-8")),
                        },
                },
                "active_batch":{
                    "batch_id":queue["active_batch"]["batch_id"],
                    "state":queue["active_batch"]["state"],
                    "subjects":queue["active_batch"]["subject_count"],
                },
                "queued_after_active":queue["remaining_subject_count"],
                "evidence":"release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/terminal-disposition/CONTENT_DISPOSITION_BATCH_002_RECEIPT.json",
                "boundary":"Retrospective content-claim disposition only; publication, corpus PASS and owner-return completion remain unproved.",
                "next_action":queue["next_deterministic_effect"],
            },
        },
        "incomplete_scope_count":1,
        "repository_effects":{
            "scope":"Not evaluated by this content-status projection; inspect fresh repository evidence.",
            "authority_promotion":"NOT_EVALUATED",
            "mirror_synchronization":"NOT_EVALUATED",
            "reciprocal_equality_receipt":"NOT_EVALUATED",
            "proof_corpus_publication":"NOT_EVALUATED",
        },
        "projection_owner":{
            "tool":"tools/qikvrt_content_disposition_batch_002_terminal.py",
            "check_command":"python3 -B tools/qikvrt_content_disposition_batch_002_terminal.py --check-status-projection",
        },
        "union_receipt_state":union_receipt["state"],
    }
    validate_ai_progress(progress)
    return progress

def render_ai_status(progress:dict[str,Any])->str:
    global_scope=progress["scopes"]["qikvrt-global-claim-scope-v1"]
    corpus_id=next(key for key in progress["scopes"] if key!="qikvrt-global-claim-scope-v1")
    corpus=progress["scopes"][corpus_id]
    g=global_scope["counts"]; c=corpus["counts"]; b=corpus["batch_002"]; active=corpus["active_batch"]
    corpus_bar="█"*c["dispositioned_subjects"]+"░"*c["open_subjects"]
    return f"""# QIK-VRT Work Status

Repository: `Goldkelch/qik-vrt`

Projection input ref: `{progress['ref_name']}`

Projection source: `{progress['source_sha']}`

Updated at: `{progress['updated_at']}`

Snapshot state: **`{progress['state']}`**. Overall effect state:
**`{progress['effect_state']}`**. No unqualified repository-wide
`PASS`, `FINAL_PASS`, publication, merge, synchronization or symmetric
canonicality is claimed by this handoff.

`[{corpus_bar}] {corpus['percent']}%` — Zenodo-Subject-Disposition
({c['dispositioned_subjects']}/{c['subjects']})

- ✓ Canonical 24-record union and 19 claim subjects bound
- ✓ Batch 001 terminally dispositioned
- ✓ Batch 002 terminally dispositioned
- □ Required corrected Batch-002 candidate and owner return
- □ Seven remaining claim subjects
- □ Retrospective proof corpus and any later publication effect

## Bounded global claim scope

`qikvrt-global-claim-scope-v1`: **`FINAL_PASS`**, 100% inside its declared
finite boundary ({g['claims']} claims, {g['primary_kernel_receipts']} primary
kernel receipts, {g['open_claims']} claims retained `OPEN`). Evidence:
`GLOBAL_COMPLETION_RECEIPT.json` plus the commit-bound run observation
`evidence/receipts/global-completion-exact-head-runs-2026-07-29.json`.
The external equality payload itself is not stored here; the repository binds
only its authorized SHA-256 through the finalization input and scoped receipt.
This historical state does not extend to the Zenodo corpus, unregistered prose,
or current repository symmetry.

## Zenodo canonical-union corpus

`{corpus_id}`: **`CONTINUE`**, {c['dispositioned_subjects']}/{c['subjects']}
subjects dispositioned ({corpus['percent']}%), {c['open_subjects']} open.

- Batch 002: `{b['state']}`, {b['subjects']} subjects, {b['claims']} claims,
  {b['content_change_required_count']} required correction.
- Batch 003: `{active['state']}` with {active['subjects']} subjects;
  {corpus['queued_after_active']} further subject remains beyond the active batch.
- Required content effect: `{corpus['next_action']}`.
- Corpus `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE` and proof-corpus publication:
  **not established**.

## Repository effects

This content-status projection does not evaluate current PR, merge, Authority,
Mirror or reciprocal-equality state. Its ref and SHA identify the projection
input, not a current remote head. Any such claim requires fresh repository
evidence bound to the current commit and run. The `QIKVRT live status watch`
is telemetry only; branch-level watcher output is not exact-head evidence and
does not establish PR, check, merge, promotion or synchronization state.

## BLOCKER

No internal projection blocker. Exact-head gates, responsible-human promotion,
the corrected-candidate owner return and all later irreversible effects remain
mandatory external gates.

## NEXT

`{progress['next_action']}`
"""

def status_projection(check:bool)->int:
    receipt_path=OUT/"CONTENT_DISPOSITION_BATCH_002_RECEIPT.json"
    source_queue,source_index,source_union=source_projection_inputs()
    source_receipt=git_json(receipt_path.relative_to(ROOT).as_posix())
    receipt=copy.deepcopy(source_receipt)
    receipt.update({
        "work_unit_id":WORK_UNIT_ID,
        "observed_at":OBSERVED_AT,
        "union_id":source_index["union_id"],
    })
    validate_terminal_receipt(receipt,source_index)
    matrices=receipt["subjects"]
    queue,index,union_receipt=project_status(
        source_queue,source_index,source_union,matrices,
        int(receipt["claim_count"]),int(receipt["content_change_required_count"]),
    )
    receipt["next_deterministic_effect"]=queue["next_deterministic_effect"]
    validate_terminal_receipt(receipt,index)
    progress=build_ai_progress(queue,index,union_receipt,receipt)
    expected={
        receipt_path:pretty(receipt),
        QUEUE:pretty(queue),
        INDEX:pretty(index),
        UNION_RECEIPT:pretty(union_receipt),
        AI_PROGRESS:pretty(progress),
        AI_STATUS:render_ai_status(progress),
    }
    source={
        path:git_bytes(f"{SOURCE_SHA}:{path.relative_to(ROOT).as_posix()}")
        for path in expected
    }
    current={
        path:path.read_bytes() if path.is_file() else None
        for path in expected
    }
    source_current=all(current[path]==source[path] for path in expected)
    expected_current=all(
        current[path]==text.encode("utf-8")
        for path,text in expected.items()
    )
    if not source_current and not expected_current:
        fail("refuse mixed, forged, unknown or later status artifact set")
    stale=[]
    for path,text in expected.items():
        if check:
            if current[path]!=text.encode("utf-8"):
                stale.append(path.relative_to(ROOT).as_posix())
        elif current[path]!=text.encode("utf-8"):
            path.write_text(text,encoding="utf-8",newline="\n")
    if stale:
        print(json.dumps({"state":"BLOCK","stale_status_projections":stale},ensure_ascii=False))
        return 2
    print(json.dumps({"state":"PASS","status_projection":"byte_current","checked":check},ensure_ascii=False))
    return 0

def main()->int:
    queue,index,union_receipt,freeze=readj(QUEUE),readj(INDEX),readj(UNION_RECEIPT),readj(FREEZE)
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
    queue,index,union_receipt=project_status(queue,index,union_receipt,matrices,total,corrections)
    remaining=[x for x in index["claim_subjects"] if not x.get("claim_disposition_complete")]
    receipt={"_license":{"classification":"machine_readable_content_disposition_batch_receipt","copyright":"Copyright 2026 Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","rights_holder":"Ingolf Lohmann"},"schema":"qikvrt_content_disposition_batch_receipt_v2","batch_id":BATCH_ID,"work_unit_id":WORK_UNIT_ID,"observed_at":OBSERVED_AT,"union_id":index["union_id"],"state":"TERMINALLY_DISPOSITIONED","subject_count":6,"claim_count":total,"subjects":matrices,"content_change_required_count":corrections,"validation":{"exact_subject_set":True,"all_public_files_byte_reverified":True,"all_claims_terminally_classified":True,"formal_claims_have_machine_proof_bindings":True,"one_claim_matrix_per_subject":True,"no_false_completion":True},"completion_claims":{"batch_002_executed":True,"batch_002_terminal_disposition_complete":True,"all_content_claims_dispositioned":not remaining,"proof_corpus_published_on_zenodo":False,"pass":False,"final_pass":False,"effect_ack_done":False},"next_deterministic_effect":queue["next_deterministic_effect"]}
    validate_terminal_receipt(receipt,index)
    progress=build_ai_progress(queue,index,union_receipt,receipt)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"CONTENT_DISPOSITION_BATCH_002_RECEIPT.json").write_text(pretty(receipt),encoding="utf-8")
    (OUT/"CONTENT_CHANGE_DECISIONS.json").write_text(pretty({"batch_id":BATCH_ID,"decisions":decisions}),encoding="utf-8")
    (OUT/"CONTENT_DISPOSITION_BATCH_002_SUBJECT_INDEX.json").write_text(pretty({"batch_id":BATCH_ID,"subjects":matrices}),encoding="utf-8")
    INDEX.write_text(pretty(index),encoding="utf-8"); QUEUE.write_text(pretty(queue),encoding="utf-8")
    UNION_RECEIPT.write_text(pretty(union_receipt),encoding="utf-8")
    AI_PROGRESS.write_text(pretty(progress),encoding="utf-8")
    AI_STATUS.write_text(render_ai_status(progress),encoding="utf-8")
    print(pretty(receipt)); return 0

if __name__=="__main__":
    try:
        if sys.argv[1:]==["--repair-status-projection"]:
            raise SystemExit(status_projection(False))
        if sys.argv[1:]==["--check-status-projection"]:
            raise SystemExit(status_projection(True))
        if sys.argv[1:]:
            fail("usage: qikvrt_content_disposition_batch_002_terminal.py [--repair-status-projection|--check-status-projection]")
        raise SystemExit(main())
    except (E,OSError,KeyError,TypeError,ValueError,json.JSONDecodeError,subprocess.CalledProcessError) as ex:
        print(json.dumps({"state":"BLOCK","failure":str(ex),"pass":False,"final_pass":False,"effect_ack_done":False},ensure_ascii=False))
        raise SystemExit(2)
