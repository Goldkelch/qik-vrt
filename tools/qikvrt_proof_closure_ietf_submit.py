#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Submit the exact Proof Closure -00 RFCXML through the official IETF API."""
from __future__ import annotations
import argparse, json, pathlib, time, urllib.parse, urllib.request

XML=pathlib.Path("external/ietf/draft-lohmann-qikvrt-proof-closure-00.xml")
ENDPOINT="https://datatracker.ietf.org/api/submission"
USER="ingolf.lohmann@live.com"
EXPECTED_NAME="draft-lohmann-qikvrt-proof-closure"

def multipart(fields,filename,raw):
    boundary="----qikvrtproofclosure20260924"
    parts=[]
    for name,value in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"xml\"; filename=\"{filename}\"\r\nContent-Type: application/xml\r\n\r\n".encode()+raw+b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts),"multipart/form-data; boundary="+boundary

def get_json(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"qik-vrt-proof-closure-ietf/1"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    ns=ap.parse_args()
    raw=XML.read_bytes()
    body,ctype=multipart({"user":USER},XML.name,raw)
    req=urllib.request.Request(ENDPOINT,data=body,method="POST",headers={
      "Content-Type":ctype,"Accept":"application/json","User-Agent":"qik-vrt-proof-closure-ietf/1"
    })
    with urllib.request.urlopen(req,timeout=90) as r:
        result=json.loads(r.read().decode("utf-8"))
    if result.get("name")!=EXPECTED_NAME or str(result.get("rev"))!="00":
        raise SystemExit("BLOCK: IETF submission identity differs")
    status_url=result.get("status_url")
    if not isinstance(status_url,str) or not status_url.startswith("https://datatracker.ietf.org/"):
        raise SystemExit("BLOCK: invalid IETF status URL")
    status={"state":"validating"}
    for _ in range(30):
        status=get_json(status_url)
        if status.get("state")!="validating":
            break
        time.sleep(2)
    state=status.get("state")
    if state in {None,"validating","cancel"}:
        raise SystemExit("BLOCK: IETF validation did not reach an admissible state")
    receipt={
      "schema":"qikvrt_proof_closure_ietf_submission_receipt_v1",
      "document":EXPECTED_NAME+"-00",
      "submission_id":result.get("id"),
      "status_url":status_url,
      "state":state,
      "author_confirmation_required":state=="auth",
      "posted":state not in {"auth","manual","awaiting_auth"},
      "ietf_consensus_claimed":False
    }
    pathlib.Path(ns.output).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
