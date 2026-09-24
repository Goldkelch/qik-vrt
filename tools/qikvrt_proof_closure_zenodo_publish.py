#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Publish the exact Proof Closure document bundle and independently read it back."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, urllib.parse, urllib.request
from tools import qikvrt_zenodo_actions as zenodo

ROOT=pathlib.Path(__file__).resolve().parents[1]
META=ROOT/"release/proof-closure-zenodo-v1/ZENODO_METADATA.json"
FILES=(
  ROOT/"docs/publications/2026-09-24-proof-closure/PROOF_CLOSURE_DE.md",
  ROOT/"docs/publications/2026-09-24-proof-closure/PROOF_CLOSURE_EN.md",
  ROOT/"docs/publications/2026-09-24-proof-closure/PROOF_CLOSURE_CONTRACT.json",
  ROOT/"docs/publications/2026-09-24-proof-closure/CLAIM_MATRIX.json",
  ROOT/"docs/publications/2026-09-24-proof-closure/README.md",
)
TITLE="Proof Closure: The Terminal Meta-Condition for an Evidence-Bound Subject"
VERSION="1.0.0"

def file_entry(path):
    data=path.read_bytes()
    return {
      "path":path.relative_to(ROOT).as_posix(),
      "name":path.name,
      "size":len(data),
      "md5":hashlib.md5(data).hexdigest(),
      "sha256":hashlib.sha256(data).hexdigest(),
    },data

def public_json(url):
    req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"qik-vrt-proof-closure-readback/1"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def public_bytes(url,limit):
    parts=urllib.parse.urlsplit(url)
    if parts.scheme!="https" or parts.hostname!="zenodo.org":
        raise RuntimeError("public download escaped zenodo.org")
    req=urllib.request.Request(url,headers={"User-Agent":"qik-vrt-proof-closure-readback/1"})
    with urllib.request.urlopen(req,timeout=60) as r:
        raw=r.read(limit+1)
    if len(raw)>limit:
        raise RuntimeError("public download exceeded expected size")
    return raw

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",required=True)
    ns=ap.parse_args()
    token=os.environ.get("ZENODO_ACCESS_TOKEN","")
    if len(token)<20:
        raise SystemExit("BLOCK: missing Zenodo token")
    metadata=json.loads(META.read_text(encoding="utf-8"))
    if metadata.get("title")!=TITLE or metadata.get("version")!=VERSION:
        raise SystemExit("BLOCK: metadata identity differs")
    entries=[]
    verified={}
    for p in FILES:
        e,data=file_entry(p)
        entries.append(e)
        verified[("paper",e["name"])]=data

    client=zenodo.ZenodoClient(token,"https://zenodo.org/api")
    matches=[]
    for item in client.list_owned_depositions():
        md=item.get("metadata") if isinstance(item.get("metadata"),dict) else {}
        if md.get("title")==TITLE and md.get("version")==VERSION:
            matches.append(item)
    if len(matches)>1:
        raise SystemExit("BLOCK: multiple matching owner depositions")
    if matches:
        candidate=matches[0]
        record_id=zenodo._record_id(candidate,"proof closure deposition")
        doi=zenodo._doi_from_deposition(candidate,"proof closure deposition")
    else:
        candidate=client.create_paper(metadata)
        record_id=zenodo._record_id(candidate,"proof closure deposition")
        doi=zenodo._doi_from_deposition(candidate,"proof closure deposition")

    state,current=client.get_deposition_or_record(record_id)
    if state=="draft":
        state=client.prepare_draft("paper",record_id,metadata,entries,verified,doi)
    public=client.publish_and_poll(record_id,metadata,entries,doi,state=="published")

    # Independent public readback: no bearer token.
    public_record=public_json(f"https://zenodo.org/api/records/{record_id}")
    public_files=public_record.get("files") or []
    by_name={}
    for item in public_files:
        name=item.get("key",item.get("filename"))
        if isinstance(name,str):
            by_name[name]=item
    readback=[]
    for e in entries:
        item=by_name.get(e["name"])
        if not isinstance(item,dict):
            raise SystemExit("BLOCK: public record missing "+e["name"])
        links=item.get("links") or {}
        url=links.get("content") or links.get("self") or links.get("download")
        if not isinstance(url,str):
            raise SystemExit("BLOCK: public file has no download link")
        raw=public_bytes(url,e["size"])
        if len(raw)!=e["size"] or hashlib.sha256(raw).hexdigest()!=e["sha256"]:
            raise SystemExit("BLOCK: public byte readback differs for "+e["name"])
        readback.append({"name":e["name"],"bytes":e["size"],"sha256":e["sha256"],"readback":"PASS"})

    receipt={
      "schema":"qikvrt_proof_closure_zenodo_receipt_v1",
      "publication_id":"qikvrt-proof-closure-2026-09-24-v1",
      "state":"published",
      "record_id":record_id,
      "doi":doi,
      "public_record_url":f"https://zenodo.org/records/{record_id}",
      "files":readback,
      "public_byte_readback":"PASS",
      "effect_ack_done":True
    }
    pathlib.Path(ns.output).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
