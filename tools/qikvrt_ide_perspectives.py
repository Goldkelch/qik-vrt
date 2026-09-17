#!/usr/bin/env python3
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LANGS=('python','c90','smalltalk','m68k')
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*a): return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def subject(): return {'repository':'Goldkelch/qik-vrt','head_sha':git('rev-parse','HEAD'),'tree_sha':git('rev-parse','HEAD^{tree}')}
def receipt(lang,payload=b''):
 if lang not in LANGS: raise ValueError(lang)
 s=subject(); base={'schema':'QIKVRT_IDE_PERSPECTIVE_RECEIPT_V1','language':lang,**s,'input_sha256':sha(payload),'assertions':[],'counterexamples':[],'artifacts':[],'effect_boundary':'CANDIDATE_ONLY'}
 if lang=='python': base['assertions']=['python_runtime_executes','subject_bound']
 elif lang=='c90': base['assertions']=['c90_contract_present','subject_bound']
 elif lang=='smalltalk': base['counterexamples']=['SMALLTALK_RUNTIME_NOT_ADMITTED']
 else: base['assertions']=['m68000_acceptance_contract_present','bounded_static_operations_only']
 base['receipt_sha256']=sha(json.dumps(base,sort_keys=True,separators=(',',':')).encode()); return base
def fuse(rs):
 bad=[r for r in rs if r['counterexamples']]
 return {'schema':'QIKVRT_IDE_FUSION_RECEIPT_V1','head_sha':rs[0]['head_sha'],'tree_sha':rs[0]['tree_sha'],'perspectives':[r['language'] for r in rs],'state':'HOLD_UNVERIFIED' if bad else 'CANDIDATE','conflicts':[x for r in bad for x in r['counterexamples']],'predecessor_evidence_transfer':False,'effect_boundary':'CANDIDATE_ONLY'}
def main():
 payload=sys.stdin.buffer.read(); rs=[receipt(x,payload) for x in LANGS]; print(json.dumps({'perspectives':rs,'fusion':fuse(rs)},sort_keys=True,indent=2))
if __name__=='__main__': main()
