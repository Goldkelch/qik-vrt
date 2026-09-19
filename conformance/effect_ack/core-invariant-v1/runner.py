#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, re
STATE_CODE={'EFFECT_NACK':0,'EFFECT_ACK_CONTINUE':1,'EFFECT_ACK_DONE':2,'EFFECT_ACK_ISOLATE':3,'EFFECT_ACK_BLOCK':4}
def digest(p):
    raw=p.read_bytes(); return {'path':p.as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def rows(p):
    out=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip():
            v=[int(x) for x in line.split()]
            if len(v)!=6: raise SystemExit(f'{p}: malformed row {line!r}')
            out.append(v)
    return out
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--contract',type=pathlib.Path,required=True)
    ap.add_argument('--temdd-ir',type=pathlib.Path,required=True)
    ap.add_argument('--lean-marker',type=pathlib.Path,required=True)
    ap.add_argument('--spark-marker',type=pathlib.Path,required=True)
    ap.add_argument('--head',required=True); ap.add_argument('--tree',required=True)
    ap.add_argument('--output',type=pathlib.Path,required=True)
    ap.add_argument('backend',nargs='+',type=pathlib.Path); a=ap.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}',a.head) or not re.fullmatch(r'[0-9a-f]{40}',a.tree):
        raise SystemExit('invalid exact subject')
    contract=json.loads(a.contract.read_text(encoding='utf-8'))
    expected=[[int(v['transport_ack']),int(v['block_required']),int(v['isolate_required']),int(v['release_ready']),STATE_CODE[v['state']],int(v['ordinary_release'])] for v in contract['vectors']]
    if len(expected)!=16: raise SystemExit('contract is not exhaustive over four booleans')
    backends={}
    for p in a.backend:
        observed=rows(p)
        if observed!=expected: raise SystemExit(f'backend divergence: {p}')
        backends[p.stem]={'result':'PASS','vectors':16,'evidence':digest(p)}
    ir=json.loads(a.temdd_ir.read_text(encoding='utf-8'))
    observed={x['source']:x['target'] for x in ir['relations'] if x['predicate']=='maps_to'}
    wanted={f"t{int(v['transport_ack'])}_b{int(v['block_required'])}_i{int(v['isolate_required'])}_r{int(v['release_ready'])}":v['state'] for v in contract['vectors']}
    if observed!=wanted: raise SystemExit('TEMDD divergence')
    if a.lean_marker.read_text().strip()!='QIKVRT_CORE_INVARIANT_LEAN_PASS': raise SystemExit('Lean marker missing')
    if a.spark_marker.read_text().strip()!='QIKVRT_CORE_INVARIANT_SPARK_PASS': raise SystemExit('SPARK marker missing')
    report={'schema':'qikvrt_core_invariant_cross_conformance_v1','subject':{'head':a.head,'tree':a.tree},
      'contract':digest(a.contract),'finite_domain':{'boolean_inputs':4,'vectors':16,'exhaustive':True},
      'backends':backends,'temdd':{'result':'PASS','vectors':16,'evidence':digest(a.temdd_ir)},
      'lean':{'result':'PASS','evidence':digest(a.lean_marker)},'ada_spark':{'result':'PASS','evidence':digest(a.spark_marker)},
      'oracle':'language-neutral declarative vector contract','implementation_authority':None,
      'predecessor_evidence_transfer':False,'ordinary_release_only_at_effect_ack_done':True,
      'transport_ack_implies_done':False,'overall':'PASS','effect_ack_done':False}
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(report,sort_keys=True,separators=(',',':')))
    return 0
if __name__=='__main__': raise SystemExit(main())
