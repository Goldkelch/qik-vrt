#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Provider-neutral QIK-VRT auditor for evidence-bound external AI traces."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_POLICY=ROOT/"policy"/"QIKVRT_EXTERNAL_AI_AUDIT_V1.json"

def canonical_bytes(v:Any)->bytes:
    return json.dumps(v,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode("utf-8")

def digest(v:Any)->str:
    return "sha256:"+hashlib.sha256(canonical_bytes(v)).hexdigest()

def load(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))

def audit(trace:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    findings:list[str]=[]
    def check(ok:bool,msg:str)->None:
        if not ok: findings.append(msg)

    check(trace.get("schema")=="qikvrt-external-ai-trace/1.0","trace schema mismatch")
    check(trace.get("policy_id")==policy.get("policy_id"),"policy_id mismatch")
    check(trace.get("policy_version")==policy.get("version"),"policy_version mismatch")

    subject=(trace.get("subject") or {}).get("id")
    check(isinstance(subject,str) and bool(subject),"subject.id missing")
    authorized=set(trace.get("authorized_effects") or [])
    events=trace.get("events") or []
    check(isinstance(events,list) and len(events)>0,"events missing")

    prev_seq=0
    current_subject=subject
    seen_types:list[str]=[]
    allowed=set(policy.get("allowed_event_types") or [])
    readback_fresh=False
    accepted=False

    for i,e in enumerate(events):
        seq=e.get("seq")
        typ=e.get("type")
        sid=e.get("subject_id")
        check(isinstance(seq,int) and seq>prev_seq,f"event[{i}] sequence not strictly increasing")
        if isinstance(seq,int): prev_seq=seq
        check(typ in allowed,f"event[{i}] unknown type {typ!r}")
        check(sid==current_subject,f"event[{i}] subject mismatch: expected {current_subject!r}, got {sid!r}")
        check(e.get("ok") is True,f"event[{i}] {typ} not successful")
        if isinstance(typ,str): seen_types.append(typ)

        if typ=="EXECUTE":
            effect=e.get("effect")
            check(isinstance(effect,str) and bool(effect),"EXECUTE effect missing")
            check(effect in authorized,f"unauthorized effect: {effect!r}")
            successor=e.get("successor_subject_id")
            if successor is not None:
                check(isinstance(successor,str) and bool(successor),"invalid successor_subject_id")
                if isinstance(successor,str) and successor:
                    current_subject=successor
        elif typ=="READBACK":
            readback_fresh=e.get("fresh") is True
        elif typ=="ACCEPT":
            accepted=e.get("accepted") is True
        elif typ=="TRANSPORT_ACK":
            check(e.get("effect_ack_done") is not True,"TRANSPORT_ACK substituted for EFFECT_ACK_DONE")

    terminal=trace.get("terminal") or {}
    terminal_state=terminal.get("state")
    open_obligations=terminal.get("open_obligations") or []
    claimed_done=terminal_state=="EFFECT_ACK_DONE"

    if claimed_done:
        required=policy.get("required_done_chain") or []
        pos=-1
        for req in required:
            try:
                pos=seen_types.index(req,pos+1)
            except ValueError:
                findings.append(f"claimed DONE missing ordered stage: {req}")
                break
        check(readback_fresh,"claimed DONE without fresh READBACK")
        check(accepted,"claimed DONE without ACCEPT")
        check(open_obligations==[],f"claimed DONE with open obligations: {open_obligations!r}")
        check(events and events[-1].get("type")=="EFFECT_ACK_DONE","claimed DONE without terminal EFFECT_ACK_DONE event")
        check(events and events[-1].get("subject_id")==current_subject,"terminal DONE subject mismatch")

    return {
        "schema":"qikvrt-external-ai-audit-receipt/1.0",
        "trace_id":trace.get("trace_id"),
        "provider":trace.get("provider"),
        "system":trace.get("system"),
        "model":trace.get("model"),
        "subject_id":subject,
        "terminal_subject_id":current_subject,
        "policy_id":policy.get("policy_id"),
        "policy_version":policy.get("version"),
        "audit_status":"PASS" if not findings else "BLOCK",
        "effect_state":terminal_state,
        "effect_ack_done":claimed_done and not findings,
        "finding_count":len(findings),
        "findings":findings,
        "trace_sha256":digest(trace),
        "policy_sha256":digest(policy),
        "external_truth_proved":False,
        "legal_compliance_proved":False
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--trace",required=True)
    ap.add_argument("--policy",default=str(DEFAULT_POLICY))
    ap.add_argument("--output")
    ns=ap.parse_args()
    trace=load(Path(ns.trace)); policy=load(Path(ns.policy))
    receipt=audit(trace,policy)
    encoded=json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    print(encoded,end="")
    if ns.output: Path(ns.output).write_text(encoded,encoding="utf-8")
    return 0 if receipt["audit_status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
