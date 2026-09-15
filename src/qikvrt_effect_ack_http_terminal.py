#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
HOST='127.0.0.1'; DEFAULT_PORT=8771

def git_read(*args):
    try:return subprocess.check_output(['git',*args],text=True,stderr=subprocess.DEVNULL,timeout=2).strip()
    except Exception:return None

class Ledger:
    def __init__(self,state_dir):
        self.dir=Path(state_dir); self.dir.mkdir(parents=True,exist_ok=True); self.path=self.dir/'temdd-events.jsonl'; self.lock=threading.Lock(); self.cond=threading.Condition(self.lock); self.next_id=1
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                try:self.next_id=max(self.next_id,int(json.loads(line)['event_id'])+1)
                except Exception:pass
    def append(self,kind,message,**extra):
        with self.cond:
            e={'event_id':self.next_id,'kind':kind,'message':message,'observed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**extra}; self.next_id+=1
            with self.path.open('a',encoding='utf-8') as f:f.write(json.dumps(e,sort_keys=True,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
            self.cond.notify_all();return e
    def after(self,cursor):
        out=[]
        if self.path.exists():
            for line in self.path.read_text(encoding='utf-8').splitlines():
                try:
                    e=json.loads(line)
                    if int(e['event_id'])>cursor:out.append(e)
                except Exception:pass
        return out
LEDGER=None

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def json(self,code,obj):
        b=json.dumps(obj,sort_keys=True).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
    def do_GET(self):
        u=urlparse(self.path)
        if u.path in ('/AI','/AI/'):
            p=Path('/opt/qikvrt/docs/terminal/temdd/index.html')
            if not p.exists():return self.json(503,{'state':'HOLD','reason':'TEMDD surface unavailable'})
            b=p.read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b);return
        if u.path=='/api/temdd/events':return self.sse(u)
        if u.path=='/terminal/state':return self.json(200,{'schema':'qikvrt_terminal_backend_state_v2','repository_head':git_read('rev-parse','HEAD'),'repository_tree':git_read('rev-parse','HEAD^{tree}'),'temdd_event_stream':'/api/temdd/events','event_ledger':str(LEDGER.path),'external_effects':'NONE'})
        if u.path=='/.well-known/effect-ack':return self.json(200,{'schema':'qikvrt_effect_ack_http_capability_v1','versions':[1],'temdd_event_stream':'/api/temdd/events','external_effects':'NONE'})
        self.json(404,{'state':'HOLD','reason':'not found'})
    def sse(self,u):
        q=parse_qs(u.query); raw=q.get('after',[self.headers.get('Last-Event-ID','0')])[0]
        try:cursor=max(0,int(raw or 0))
        except ValueError:return self.json(400,{'state':'HOLD','reason':'invalid event cursor'})
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-cache, no-transform');self.send_header('Connection','keep-alive');self.send_header('X-Accel-Buffering','no');self.end_headers()
        try:
            while True:
                emitted=False
                for e in LEDGER.after(cursor):
                    cursor=int(e['event_id']); data=json.dumps(e,sort_keys=True,separators=(',',':'));self.wfile.write(f'id: {cursor}\nevent: temdd\ndata: {data}\n\n'.encode());self.wfile.flush();emitted=True
                if not emitted:
                    self.wfile.write(b': keepalive\n\n');self.wfile.flush()
                    with LEDGER.cond:LEDGER.cond.wait(timeout=15)
        except (BrokenPipeError,ConnectionResetError):return
    def do_POST(self):
        if self.path!='/api/temdd/events':return self.json(404,{'state':'HOLD','reason':'not found'})
        try:
            n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n)); kind=str(body.get('kind','EVENT')); msg=str(body.get('message',''))
            e=LEDGER.append(kind,msg,subject=body.get('subject'),dod=bool(body.get('dod',False)));self.json(201,e)
        except Exception as exc:self.json(400,{'state':'HOLD','reason':str(exc)})
    def log_message(self,*args):pass

def main():
    global LEDGER
    p=argparse.ArgumentParser();p.add_argument('--host',default=HOST);p.add_argument('--port',type=int,default=DEFAULT_PORT);p.add_argument('--state-dir',default='/var/lib/qikvrt/state');a=p.parse_args()
    if a.host not in {'127.0.0.1','localhost'}:raise SystemExit('BLOCK: terminal bridge is loopback-only')
    LEDGER=Ledger(a.state_dir);LEDGER.append('RUNTIME_START','TEMDD event producer ready',subject=git_read('rev-parse','HEAD'))
    ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
if __name__=='__main__':main()
