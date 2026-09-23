#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed successor freshness gate for Zenodo-bound QIK-VRT subjects."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, stat, sys
from typing import Any
ROOT=pathlib.Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY="policy/QIKVRT_ZENODO_SUCCESSOR_TARGETS_V1.json"
class GuardError(RuntimeError): pass
def _safe(root:pathlib.Path,raw:str,*,must_exist:bool=True)->pathlib.Path:
    if not isinstance(raw,str) or not raw: raise GuardError("path must be a non-empty string")
    pure=pathlib.PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"",".",".."} for part in pure.parts): raise GuardError(f"unsafe repository-relative path: {raw}")
    path=root.joinpath(*pure.parts); cursor=root
    for part in pure.parts:
        cursor=cursor/part
        if cursor.is_symlink(): raise GuardError(f"symlink path is forbidden: {raw}")
    resolved=path.resolve(strict=False)
    try: resolved.relative_to(root.resolve())
    except ValueError: raise GuardError(f"path escapes repository root: {raw}") from None
    if must_exist:
        try: st=resolved.stat()
        except FileNotFoundError: raise GuardError(f"required file is absent: {raw}") from None
        if not stat.S_ISREG(st.st_mode): raise GuardError(f"required path is not a regular file: {raw}")
    return resolved
def _read_json(path:pathlib.Path)->dict[str,Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeDecodeError,json.JSONDecodeError) as exc: raise GuardError(f"invalid JSON at {path.name}: {exc}") from None
    if not isinstance(value,dict): raise GuardError(f"{path.name} must contain a JSON object")
    return value
def _git_blob(data:bytes)->str: return hashlib.sha1(f"blob {len(data)}\0".encode("ascii")+data).hexdigest()  # noqa: S324
def identity(root:pathlib.Path,raw:str)->dict[str,Any]:
    data=_safe(root,raw).read_bytes()
    return {"path":raw,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"git_blob_sha1":_git_blob(data)}
def _registry(root:pathlib.Path,registry:str)->dict[str,Any]:
    value=_read_json(_safe(root,registry))
    if value.get("schema")!="qikvrt_zenodo_successor_targets_v1": raise GuardError("unsupported successor target registry schema")
    if not isinstance(value.get("targets"),list) or not value["targets"]: raise GuardError("successor target registry must contain targets")
    return value
def target(root:pathlib.Path,target_id:str,registry:str=DEFAULT_REGISTRY)->dict[str,Any]:
    matches=[t for t in _registry(root,registry)["targets"] if isinstance(t,dict) and t.get("id")==target_id]
    if len(matches)!=1: raise GuardError(f"target must resolve exactly once: {target_id}")
    value=matches[0]; paths=value.get("source_paths")
    if not isinstance(paths,list) or not paths or len(paths)!=len(set(paths)): raise GuardError("source_paths must be a non-empty unique list")
    for raw in paths: _safe(root,raw)
    for key in ("candidate_path","publish_request_path","owner_authorization_path","publication_receipt_path"): _safe(root,value[key],must_exist=False)
    return value
def source_set(root:pathlib.Path,value:dict[str,Any])->list[dict[str,Any]]: return [identity(root,p) for p in value["source_paths"]]
def source_set_sha256(items:list[dict[str,Any]])->str:
    raw=json.dumps(items,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
def candidate_payload(root:pathlib.Path,value:dict[str,Any])->dict[str,Any]:
    items=source_set(root,value)
    return {"schema":"qikvrt_zenodo_auto_successor_candidate_v1","target_id":value["id"],"publication_id":value["publication_id"],"state":"MATERIALIZED_AWAITING_EXACT_OWNER_AUTHORIZATION","source_files":items,"source_set_sha256":source_set_sha256(items),"predecessor_evidence_transfer":False,"candidate_specific_owner_authorization_required":True,"public_effect_ack_done":False}
def _atomic_json(path:pathlib.Path,value:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True); raw=(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode("utf-8")
    tmp=path.with_name("."+path.name+f".{os.getpid()}.tmp"); fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
    try:
        with os.fdopen(fd,"wb",closefd=True) as h: h.write(raw); h.flush(); os.fsync(h.fileno())
        os.replace(tmp,path)
    finally:
        if tmp.exists(): tmp.unlink()
def materialize(root:pathlib.Path,target_id:str,registry:str=DEFAULT_REGISTRY)->dict[str,Any]:
    value=target(root,target_id,registry); payload=candidate_payload(root,value); _atomic_json(_safe(root,value["candidate_path"],must_exist=False),payload); return payload
def _candidate_current(root,value,current):
    path=_safe(root,value["candidate_path"],must_exist=False)
    if not path.exists(): return False,"MISSING"
    c=_read_json(path); expected=candidate_payload(root,value); return (c==expected,"CURRENT" if c==expected else "STALE")
def _manifest_current(root,value,current):
    path=_safe(root,value["publish_request_path"],must_exist=False)
    if not path.exists(): return False,"MISSING"
    m=_read_json(path); files=m.get("files")
    if not isinstance(files,list): return False,"INVALID"
    by={f.get("path"):f for f in files if isinstance(f,dict) and isinstance(f.get("path"),str)}
    for item in current:
        f=by.get(item["path"])
        if not isinstance(f,dict) or f.get("git_blob_sha")!=item["git_blob_sha1"]: return False,"STALE"
    return True,"CURRENT"
def _receipt_current(root,value,current):
    path=_safe(root,value["publication_receipt_path"],must_exist=False)
    if not path.exists(): return False,"MISSING"
    r=_read_json(path)
    if r.get("state")!="published": return False,"NOT_PUBLISHED"
    files=r.get("files")
    if not isinstance(files,list): return False,"INVALID"
    by={f.get("path"):f for f in files if isinstance(f,dict) and isinstance(f.get("path"),str)}
    for item in current:
        f=by.get(item["path"])
        if not isinstance(f,dict) or f.get("git_blob_sha")!=item["git_blob_sha1"]: return False,"STALE"
    doi=r.get("doi")
    if not isinstance(doi,str) or not doi.startswith("10.5281/zenodo."): return False,"INVALID_DOI"
    return True,"CURRENT"
def evaluate(root:pathlib.Path,target_id:str,registry:str=DEFAULT_REGISTRY)->dict[str,Any]:
    value=target(root,target_id,registry); current=source_set(root,value)
    c,cs=_candidate_current(root,value,current); m,ms=_manifest_current(root,value,current); r,rs=_receipt_current(root,value,current)
    return {"target_id":target_id,"source_set_sha256":source_set_sha256(current),"candidate":{"current":c,"state":cs},"publish_request":{"current":m,"state":ms},"public_receipt":{"current":r,"state":rs},"owner_authorization_path":value["owner_authorization_path"],"PUBLICATION_EFFECT_ACK_DONE":c and m and r}
def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--repository-root",default="."); p.add_argument("--registry",default=DEFAULT_REGISTRY); sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("materialize"); a.add_argument("--target",required=True)
    a=sub.add_parser("check"); a.add_argument("--target",required=True); a.add_argument("--require-publish-request",action="store_true"); a.add_argument("--require-public-effect",action="store_true")
    a=sub.add_parser("status"); a.add_argument("--target",required=True)
    args=p.parse_args(argv); root=pathlib.Path(args.repository_root).resolve()
    try:
        if args.command=="materialize": materialize(root,args.target,args.registry)
        result=evaluate(root,args.target,args.registry); print(json.dumps(result,ensure_ascii=False,sort_keys=True))
        if args.command=="check":
            if not result["candidate"]["current"]: return 2
            if args.require_publish_request and not result["publish_request"]["current"]: return 3
            if args.require_public_effect and not result["PUBLICATION_EFFECT_ACK_DONE"]: return 4
        return 0
    except GuardError as exc: print("BLOCK: "+str(exc),file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
