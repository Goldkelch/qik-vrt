#!/usr/bin/env python3
"""Transactional claim/receipt adapter for the existing workflow-executor artifact store."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path

class ClaimBlock(RuntimeError): pass

def canonical(v): return (json.dumps(v,sort_keys=True,separators=(",",":"))+"\n").encode()
def claim_id(v): return hashlib.sha256(canonical(v)).hexdigest()

def make_claim(plan, work_unit, carrier, authority):
    obs=plan.get("observed",{})
    head,tree=obs.get("head_sha"),obs.get("tree_sha")
    if not (isinstance(head,str) and len(head)==40 and isinstance(tree,str) and len(tree)==40):
        raise ClaimBlock("exact HEAD/TREE missing")
    body={"schema":"qikvrt_executor_claim_v1","head_sha":head,"tree_sha":tree,
          "work_unit":work_unit,"carrier":carrier,"authority":authority}
    body["claim_id"]=claim_id(body)
    return body

def reserve(claim, root):
    root.mkdir(parents=True,exist_ok=True)
    p=root/(claim["claim_id"]+".json")
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    try: fd=os.open(p,flags,0o600)
    except FileExistsError: raise ClaimBlock("claim already reserved")
    with os.fdopen(fd,"wb") as f: f.write(canonical(claim))
    if json.loads(p.read_text()) != claim: raise ClaimBlock("reservation readback mismatch")
    return p

def append_receipt(claim, effect, receipt_file):
    if effect.get("head_sha") != claim["head_sha"] or effect.get("tree_sha") != claim["tree_sha"]:
        raise ClaimBlock("effect subject drift")
    receipt={"schema":"qikvrt_executor_receipt_v1","claim_id":claim["claim_id"],
             "head_sha":claim["head_sha"],"tree_sha":claim["tree_sha"],
             "work_unit":claim["work_unit"],"carrier":claim["carrier"],
             "effect":effect,"state":"RECOVERY_STEP_VERIFIED_CONTINUE",
             "effect_ack_done":False}
    receipt_file.parent.mkdir(parents=True,exist_ok=True)
    line=canonical(receipt)
    with receipt_file.open("ab") as f:
        f.write(line); f.flush(); os.fsync(f.fileno())
    last=receipt_file.read_bytes().splitlines()[-1]+b"\n"
    if last != line: raise ClaimBlock("receipt readback mismatch")
    return receipt

def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="cmd",required=True)
    c=s.add_parser("claim"); c.add_argument("--plan",type=Path,required=True); c.add_argument("--work-unit",required=True); c.add_argument("--carrier",required=True); c.add_argument("--authority",required=True); c.add_argument("--store",type=Path,required=True)
    r=s.add_parser("receipt"); r.add_argument("--claim",type=Path,required=True); r.add_argument("--effect",type=Path,required=True); r.add_argument("--receipts",type=Path,required=True)
    a=p.parse_args()
    try:
        if a.cmd=="claim":
            v=make_claim(json.loads(a.plan.read_text()),a.work_unit,a.carrier,a.authority); path=reserve(v,a.store); print(json.dumps({"claim":v,"reservation":str(path)},sort_keys=True))
        else:
            v=append_receipt(json.loads(a.claim.read_text()),json.loads(a.effect.read_text()),a.receipts); print(json.dumps(v,sort_keys=True))
        return 0
    except (ClaimBlock,OSError,ValueError,json.JSONDecodeError) as e:
        print("BLOCK CLAIM_RECEIPT_ADAPTER "+str(e),file=__import__("sys").stderr); return 2
if __name__=="__main__": raise SystemExit(main())
