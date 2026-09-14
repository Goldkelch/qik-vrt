#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCI = ROOT / "docs/science"
LIVE = ROOT / "state/live/QIKVRT_LIVE_EVENTS.jsonl"
PUBLIC_LIVE = SCI / "live-events.jsonl"


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None


def classify(path: Path, claim: dict) -> str:
    text = (str(path) + ' ' + json.dumps(claim, ensure_ascii=False)).lower()
    if any(k in text for k in ['physics','planck','qce','spacetime','causal','measurement']): return 'physics'
    if any(k in text for k in ['math','theorem','algebra','group','fixed-point','fixpunkt']): return 'mathematics'
    if any(k in text for k in ['philosoph','ontology','epistem']): return 'philosophy'
    if any(k in text for k in ['econom','business','wirtschaft']): return 'economics'
    if any(k in text for k in ['language','semantic','sprache']): return 'language'
    return 'computer-science'


def collect_claims():
    grouped = defaultdict(list)
    for p in sorted(ROOT.glob('docs/publications/**/CLAIM_MATRIX.json')):
        data = read_json(p)
        if not isinstance(data, dict):
            continue
        for c in data.get('claims', []):
            if not isinstance(c, dict):
                continue
            grouped[classify(p, c)].append({
                'id': c.get('claim_id') or c.get('id'),
                'statement': c.get('statement'),
                'classification': c.get('classification') or c.get('class'),
                'status': c.get('status'),
                'scope': c.get('scope') or c.get('boundary'),
                'source': p.relative_to(ROOT).as_posix(),
                'proof_refs': c.get('proof_refs', []),
            })
    return dict(grouped)


def collect_lean():
    out=[]
    for p in sorted(ROOT.rglob('*.lean')):
        if '.lake' in p.parts or '.git' in p.parts: continue
        raw=p.read_bytes()
        out.append({'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(raw).hexdigest()})
    return out


def collect_terminals():
    nodes=[]
    known=ROOT/'registry/KNOWN_NODE_REQUESTS.tsv'
    if known.exists():
        with known.open(encoding='utf-8', newline='') as f:
            for row in csv.reader(f, delimiter='\t'):
                if not row or row[0].startswith('#'): continue
                nodes.append({'id': row[0], 'raw': row})
    seed='Goldkelch/qik-vrt'
    ids=[seed]+[n['id'] for n in nodes if n['id']!=seed]
    edges=[]
    for n in ids[1:]:
        edges += [{'from':seed,'to':n},{'from':n,'to':seed}]
    adj=defaultdict(list)
    for e in edges: adj[e['from']].append(e['to'])
    shortcuts=[]
    for src in ids:
        dist={src:0}; q=deque([src])
        while q:
            u=q.popleft()
            for v in adj[u]:
                if v not in dist: dist[v]=dist[u]+1; q.append(v)
        for dst,d in dist.items():
            if src!=dst: shortcuts.append({'from':src,'to':dst,'hops':d})
    return {'nodes':ids,'edges':edges,'shortcuts':shortcuts,'derivation':'BFS over explicit registry-derived links; timestamps never define causality'}


def main():
    SCI.mkdir(parents=True, exist_ok=True); LIVE.parent.mkdir(parents=True, exist_ok=True)
    head=os.getenv('QIKVRT_EXACT_SHA') or os.getenv('GITHUB_SHA') or 'UNBOUND'
    run=os.getenv('GITHUB_RUN_ID') or 'local'
    event=os.getenv('QIKVRT_SOURCE_EVENT') or os.getenv('GITHUB_EVENT_NAME') or 'local'
    claims=collect_claims(); lean=collect_lean(); terminals=collect_terminals()
    lake=(ROOT/'lakefile.lean').exists() or (ROOT/'lakefile.toml').exists()
    toolchain=(ROOT/'lean-toolchain').read_text(encoding='utf-8').strip() if (ROOT/'lean-toolchain').exists() else None
    status={
      'schema':'qikvrt_science_status_v1','observed_at':utcnow(),'exact_subject':head,
      'lean':{'source_files':len(lean),'toolchain':toolchain},'lake':{'configured':lake},
      'proof_execution':{'state':'OBSERVED_NOT_INFERRED','note':'This materializer inventories sources. A successful Lean/Lake workflow receipt must be bound separately to this exact subject.'},
      'dod':'HOLD_UNVERIFIED',
      'boundary':'Formal proof status is scoped to declared models; empirical and ontological claims remain separate.'
    }
    index={'schema':'qikvrt_science_index_v1','exact_subject':head,'categories':claims,'lean_sources':lean,
           'urls':{'status':'status.json','terminals':'terminals.json','live_events':'live-events.jsonl'}}
    (SCI/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (SCI/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (SCI/'terminals.json').write_text(json.dumps(terminals,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    eid=f"{head}:{run}:{event}"
    envelope={'schema':'qikvrt_live_event_v1','event_id':eid,'observed_at':utcnow(),'repository':'Goldkelch/qik-vrt',
      'subject':{'kind':'trusted_main' if os.getenv('GITHUB_REF_NAME')=='main' else 'repository','head_sha':head},
      'phase':'P6' if os.getenv('GITHUB_REF_NAME')=='main' else 'P2','verb':'READBACK','causal_state':'REOBSERVE','d0':2,
      'source':{'type':event,'id':run},'predecessor_event_ids':[],'productive_effect':False,'effect_ack':'NOT_REQUIRED',
      'payload':{'science_index':'docs/science/index.json','proof_status':'docs/science/status.json','terminal_graph':'docs/science/terminals.json'}}
    existing=LIVE.read_text(encoding='utf-8') if LIVE.exists() else ''
    if eid not in existing:
        with LIVE.open('a',encoding='utf-8') as f: f.write(json.dumps(envelope,separators=(',',':'),ensure_ascii=False)+'\n')
    PUBLIC_LIVE.write_text(LIVE.read_text(encoding='utf-8'),encoding='utf-8')

if __name__=='__main__': main()
