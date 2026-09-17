#!/usr/bin/env python3
import json, os, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_API='https://api.github.com/repos/Goldkelch/qik-vrt'
START=time.time()

def get_json(path):
    req=urllib.request.Request(REPO_API+path,headers={'Accept':'application/vnd.github+json','User-Agent':'qikvrt-mesh-monitor/1'})
    with urllib.request.urlopen(req,timeout=8) as r:
        return json.load(r)

def snapshot():
    out={'schema':'qikvrt_mesh_monitor_v1','observed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'repository':'Goldkelch/qik-vrt'}
    try:
        main=get_json('/commits/main')
        prs=get_json('/pulls?state=open&per_page=100')
        out['main']={'head':main.get('sha'),'tree':main.get('commit',{}).get('tree',{}).get('sha')}
        out['pull_requests']=[{'number':p.get('number'),'title':p.get('title'),'draft':p.get('draft'),'head':p.get('head',{}).get('sha'),'base':p.get('base',{}).get('sha'),'updated_at':p.get('updated_at')} for p in prs]
        out['counts']={'open_prs':len(prs)}
        out['state']='LIVE'
    except Exception as e:
        out['state']='HOLD_UNVERIFIED'; out['error']=type(e).__name__
    return out

PAGE='''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>QIK-VRT Mesh Monitor</title><style>body{font:15px system-ui;background:#0d0d15;color:#f5f5f7;margin:0;padding:24px}main{max-width:1000px;margin:auto}h1{font-size:28px}.k{color:#a9a9b5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.card{border:1px solid #343442;border-radius:14px;padding:14px;background:#15151f}.ok{color:#7ee787}.hold{color:#ffcc66}code{word-break:break-all}table{width:100%;border-collapse:collapse;margin-top:18px}td,th{text-align:left;border-bottom:1px solid #2b2b36;padding:9px 5px;font-size:13px}</style><main><h1>QIK-VRT Mesh Monitor</h1><p class=k>Authoritative public bootstrap view · refresh 5 s · no predecessor evidence transfer</p><div id=x>Loading…</div></main><script>async function u(){try{let r=await fetch('/api/snapshot',{cache:'no-store'}),d=await r.json();let ps=d.pull_requests||[];document.getElementById('x').innerHTML=`<div class=grid><div class=card><span class=k>State</span><h2 class=${d.state==='LIVE'?'ok':'hold'}>${d.state}</h2></div><div class=card><span class=k>Main HEAD</span><p><code>${d.main?.head||'UNKNOWN'}</code></p></div><div class=card><span class=k>Main TREE</span><p><code>${d.main?.tree||'UNKNOWN'}</code></p></div><div class=card><span class=k>Open PRs</span><h2>${d.counts?.open_prs??'—'}</h2></div></div><p class=k>Observed ${d.observed_at}</p><table><thead><tr><th>PR</th><th>Subject</th><th>HEAD</th><th>Draft</th></tr></thead><tbody>${ps.map(p=>`<tr><td>#${p.number}</td><td>${p.title}</td><td><code>${(p.head||'').slice(0,12)}</code></td><td>${p.draft?'yes':'no'}</td></tr>`).join('')}</tbody></table>`}catch(e){document.getElementById('x').innerHTML='<p class=hold>HOLD_UNVERIFIED · snapshot unavailable</p>'}}u();setInterval(u,5000)</script>'''

class H(BaseHTTPRequestHandler):
    def send(self,code,ctype,body):
        b=body.encode(); self.send_response(code); self.send_header('Content-Type',ctype); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path=='/health': return self.send(200,'text/plain','ready\n')
        if self.path.startswith('/api/snapshot'): return self.send(200,'application/json',json.dumps(snapshot(),separators=(',',':')))
        if self.path=='/' or self.path.startswith('/?'): return self.send(200,'text/html; charset=utf-8',PAGE)
        self.send(404,'text/plain','not found\n')
    def log_message(self,fmt,*args): print(fmt%args,flush=True)

port=int(os.getenv('PORT','8080'))
print(json.dumps({'event':'MESH_MONITOR_START','port':port,'started_at':START}),flush=True)
ThreadingHTTPServer(('0.0.0.0',port),H).serve_forever()
