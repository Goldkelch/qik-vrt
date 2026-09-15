#!/usr/bin/env python3
"""TEMDD v0.1 deterministic reference parser/elaborator."""
import json, re, sys
from pathlib import Path
ID=r"[A-Za-z][A-Za-z0-9_-]*"
def parse(text):
    def one(p,label):
        m=re.search(p,text,re.S)
        if not m: raise ValueError("missing "+label)
        return m
    v=one(r"^\s*temdd\s+([0-9.]+)\s*;","version").group(1)
    a=one(r"authority\s+"+ID+r"\s*=\s*\"([^\"]+)\"\s*;","authority").group(1)
    s=one(r"subject\s+("+ID+r")\s*\{(.*?)\}","subject")
    repo=one(r"repository\s*=\s*\"([^\"]+)\"\s*;","repository in subject").group(1) if False else None
    sb=s.group(2); rm=re.search(r"repository\s*=\s*\"([^\"]+)\"\s*;",sb); bm=re.search(r"binding\s*=\s*(exact)\s*;",sb)
    if not rm or not bm: raise ValueError("subject must have repository and exact binding")
    q=one(r"request\s+("+ID+r")\s*\{\s*target\s*=\s*("+ID+r")\s*;\s*\}","request")
    handlers=[]
    for m in re.finditer(r"on\s+(event|blocker)\s*\{(.*?)\}",text,re.S):
        body=m.group(2); stm=[x.strip() for x in body.split(';') if x.strip()]
        handlers.append({"event":m.group(1),"statements":stm})
    d=one(r"until\s*\{(.*?)\}","until").group(1).strip().rstrip(';')
    dod=[x.strip() for x in d.split('&&') if x.strip()]
    if not handlers or not dod: raise ValueError("handlers and DoD required")
    return {"schema":"temdd_ir_v0_1","version":v,"authority":a,"subject":{"name":s.group(1),"repository":rm.group(1),"binding":"exact"},"request":{"name":q.group(1),"target":q.group(2)},"handlers":handlers,"dod":dod}
def main(argv):
    if len(argv)!=2: return 64
    try: ir=parse(Path(argv[1]).read_text(encoding='utf-8'))
    except (OSError,ValueError) as e: print("BLOCK "+str(e),file=sys.stderr); return 2
    print(json.dumps(ir,sort_keys=True,separators=(',',':'))); return 0
if __name__=='__main__': raise SystemExit(main(sys.argv))
