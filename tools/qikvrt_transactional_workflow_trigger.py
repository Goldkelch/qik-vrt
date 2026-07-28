#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations
import argparse, hashlib, json, pathlib, sys
from typing import Any

def digest(path: pathlib.Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def emit(state:str,failure_class:str|None,details:dict[str,Any],code:int)->int:
    print(json.dumps({'schema':'qikvrt_transactional_workflow_trigger_receipt_v1','state':state,'failure_class':failure_class,'details':details,'completion_claims':{'pass':False,'final_pass':False,'effect_ack_done':False}},sort_keys=True,indent=2)); return code

def load_json(path:pathlib.Path)->Any: return json.loads(path.read_text(encoding='utf-8'))

def verify(root:pathlib.Path,manifest_path:pathlib.Path,changed_paths_path:pathlib.Path)->int:
    try: manifest=load_json(root/manifest_path)
    except Exception as exc: return emit('BLOCK','MANIFEST_UNREADABLE',{'error':str(exc)},2)
    if manifest.get('schema')!='qikvrt_transactional_workflow_trigger_v1': return emit('BLOCK','MANIFEST_SCHEMA_INVALID',{},3)
    txid=manifest.get('transaction_id'); ready_rel=manifest.get('ready_marker')
    if not isinstance(txid,str) or not txid or not isinstance(ready_rel,str) or not ready_rel: return emit('BLOCK','MANIFEST_REQUIRED_FIELD_INVALID',{},4)
    ready=root/ready_rel
    if not ready.is_file(): return emit('BLOCK','READY_MARKER_MISSING',{'path':ready_rel},5)
    try: ready_doc=load_json(ready)
    except Exception as exc: return emit('BLOCK','READY_MARKER_UNREADABLE',{'error':str(exc)},6)
    if ready_doc.get('state')!='READY' or ready_doc.get('transaction_id')!=txid: return emit('BLOCK','READY_MARKER_INVALID',{'path':ready_rel},7)
    changed={line.strip().replace('\\','/') for line in changed_paths_path.read_text(encoding='utf-8').splitlines() if line.strip()}
    allowed=set(manifest.get('allowed_changed_paths') or []); unexpected=sorted(changed-allowed)
    if unexpected: return emit('BLOCK','UNEXPECTED_CHANGED_PATH',{'paths':unexpected},8)
    missing=sorted(set(manifest.get('required_changed_paths') or [])-changed)
    if missing: return emit('BLOCK','REQUIRED_CHANGED_PATH_MISSING',{'paths':missing},9)
    verified=[]
    for row in manifest.get('required_files') or []:
        rel=row.get('path') if isinstance(row,dict) else None; expected=row.get('sha256') if isinstance(row,dict) else None
        if not isinstance(rel,str) or not isinstance(expected,str): return emit('BLOCK','REQUIRED_FILE_BINDING_INVALID',{'binding':row},10)
        path=root/rel
        if not path.is_file(): return emit('BLOCK','REQUIRED_FILE_MISSING',{'path':rel},11)
        observed=digest(path)
        if observed!=expected: return emit('BLOCK','REQUIRED_FILE_HASH_MISMATCH',{'path':rel,'expected':expected,'observed':observed},12)
        verified.append({'path':rel,'sha256':observed})
    claims=manifest.get('completion_claims') or {}
    if any(claims.get(k) is not False for k in ('pass','final_pass','effect_ack_done')): return emit('BLOCK','FALSE_COMPLETION_CLAIM_IN_TRIGGER_MANIFEST',{},13)
    return emit('TRANSACTION_TRIGGER_VERIFIED',None,{'transaction_id':txid,'base_commit':manifest.get('base_commit'),'changed_paths':sorted(changed),'verified_files':verified,'ready_marker':ready_rel},0)

def main()->int:
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True); v=sub.add_parser('verify'); v.add_argument('--root',default='.'); v.add_argument('--manifest',required=True); v.add_argument('--changed-paths',required=True); a=p.parse_args()
    return verify(pathlib.Path(a.root),pathlib.Path(a.manifest),pathlib.Path(a.changed_paths)) if a.command=='verify' else 64

if __name__=='__main__': sys.exit(main())
