#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Serialize the epistemic-spiral carrier, pass it through the real QIK-VRT Transputer bus, and read it back byte-for-byte."""
from __future__ import annotations
import argparse, hashlib, json, os, selectors, subprocess, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT/"docs/assets/epistemic-spiral"
MAX_BODY=62784

def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*args): return subprocess.check_output(["git","-C",str(ROOT),*args],text=True).strip()

class Proc:
    def __init__(self,args):
        self.p=subprocess.Popen(list(map(str,args)),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.buffer=b""; self.events=[]
    def send(self,value):
        self.p.stdin.write(canonical(value)+b"\n"); self.p.stdin.flush()
    def wait(self,predicate,timeout=20):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            while b"\n" in self.buffer:
                line,self.buffer=self.buffer.split(b"\n",1)
                self.events.append(json.loads(line))
            for i,item in enumerate(self.events):
                if predicate(item): return self.events.pop(i)
            sel=selectors.DefaultSelector(); sel.register(self.p.stdout,selectors.EVENT_READ)
            ready=sel.select(max(0,until-time.monotonic())); sel.close()
            if not ready: break
            chunk=os.read(self.p.stdout.fileno(),65536)
            if not chunk: raise RuntimeError(self.p.stderr.read().decode(errors="replace"))
            self.buffer+=chunk
        raise RuntimeError("transputer event timeout: "+repr(self.events))
    def stop(self):
        if self.p.poll() is None: self.p.kill()
        self.p.wait(timeout=5)

def load_bundle():
    manifest=json.loads((ASSET/"manifest.json").read_text(encoding="utf-8"))
    svg=(ASSET/"spiral.svg").read_text(encoding="utf-8")
    i18n=json.loads((ASSET/"i18n.json").read_text(encoding="utf-8"))
    bundle={"schema":"qikvrt_epistemic_spiral_serialized_v1","manifest":manifest,"svg":svg,"i18n":i18n}
    raw=canonical(bundle)
    decoded=json.loads(raw.decode("utf-8"))
    if canonical(decoded)!=raw: raise RuntimeError("canonical serialize/deserialize mismatch")
    if len(raw)>MAX_BODY: raise RuntimeError(f"spiral carrier {len(raw)} exceeds Transputer body bound {MAX_BODY}")
    return bundle,raw

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--binary",type=Path,default=ROOT/"next/target/release/qikvrt-next")
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    binary=args.binary.resolve()
    if not binary.is_file(): raise SystemExit("BLOCK: qikvrt-next binary missing")

    head=git("rev-parse","HEAD"); tree=git("rev-parse","HEAD^{tree}")
    _,raw=load_bundle(); digest=sha(raw)
    processes=[]
    def cli(*a):
        r=subprocess.run([str(binary),*map(str,a)],capture_output=True,timeout=30)
        if r.returncode!=0: raise RuntimeError(r.stderr.decode(errors="replace"))
        return json.loads(r.stdout)
    def start(*a):
        p=Proc([binary,*a]); processes.append(p); return p

    with tempfile.TemporaryDirectory(prefix="qikvrt-spiral-bus-") as td:
        temp=Path(td)
        subject={"repository":"Goldkelch/qik-vrt","subject_id":"epistemic-spiral","head":head,"tree":tree}
        subject_file=temp/"subject.json"; subject_file.write_bytes(canonical(subject))
        subject_digest=sha(("\n".join(subject[k] for k in ("repository","subject_id","head","tree"))+"\n").encode())
        creds=temp/"credentials"
        cli("bus-config",creds,"bus",subject_file,"A","B")
        for name in ("bus","A","B"): cli("init",temp/name,name)
        try:
            server=start("bus-serve",temp/"bus",creds/"bus.json","127.0.0.1:0")
            address=server.wait(lambda v:v.get("state")=="LISTENING")["address"]
            a=start("bus-peer",temp/"A",creds/"A.json",address)
            b=start("bus-peer",temp/"B",creds/"B.json",address)
            for p in (a,b):
                joined=p.wait(lambda v:v.get("state")=="JOINED")
                if joined.get("ordinary_release") is not False: raise RuntimeError("bus admission inferred release")

            a.send({"op":"send","destination":"B","subject":subject_digest,"codec":2,"payload_hex":raw.hex()})
            received=b.wait(lambda v:v.get("state")=="RECEIVED" and v.get("source")=="A")
            incoming=bytes.fromhex(received["payload_hex"])
            if incoming!=raw: raise RuntimeError("Transputer forward bytes changed")

            b.send({"op":"reply","destination":"A","subject":subject_digest,"codec":3,"payload_hex":incoming.hex(),
                    **{k:received[k] for k in ("session","nonce","message_id","correlation")}})
            returned=a.wait(lambda v:v.get("state")=="RECEIVED" and v.get("source")=="B" and v.get("kind")==3)
            roundtrip=bytes.fromhex(returned["payload_hex"])
            if roundtrip!=raw: raise RuntimeError("Transputer return bytes changed")
            checkpoint=cli("verify",temp/"bus")["checkpoint"]
        finally:
            for p in processes: p.stop()

    receipt={
      "schema":"qikvrt_epistemic_spiral_roundtrip_receipt_v1",
      "source_head":head,"source_tree":tree,
      "carrier_sha256":digest,"carrier_bytes":len(raw),
      "serialize_deserialize_equal":True,
      "transputer_forward_equal":True,
      "transputer_return_equal":True,
      "bus_checkpoint":checkpoint,
      "ordinary_release_inferred":False,
      "effect_ack_done":False,
      "next_required_effect":"materialize_in_linux_and_oci_then_observe_firefox_and_public_AI_readback"
    }
    encoded=json.dumps(receipt,sort_keys=True,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(encoded,encoding="utf-8")
    print(encoded,end="")

if __name__=="__main__": main()
