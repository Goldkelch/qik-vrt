#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Roundtrip the canonical epistemic-spiral carrier through qikvrt-next."""
from __future__ import annotations
import argparse, hashlib, json, os, selectors, subprocess, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPIRAL=ROOT/"docs/terminal/epistemic-spiral"
MAX_BODY=62784

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(["git","-C",str(ROOT),*args],text=True).strip()

def load_carrier():
    state=json.loads((SPIRAL/"state.json").read_text(encoding="utf-8"))
    locales=json.loads((SPIRAL/"locales.json").read_text(encoding="utf-8"))
    if state.get("schema")!="qikvrt_epistemic_spiral_state_v1":
        raise RuntimeError("canonical state schema mismatch")
    if locales.get("schema")!="qikvrt_epistemic_spiral_locales_v1":
        raise RuntimeError("canonical locales schema mismatch")
    carrier={"schema":"qikvrt_epistemic_spiral_transputer_carrier_v1","state":state,"locales":locales}
    raw=canonical(carrier)
    if canonical(json.loads(raw.decode("utf-8")))!=raw:
        raise RuntimeError("canonical serialize/deserialize mismatch")
    if len(raw)>MAX_BODY:
        raise RuntimeError(f"spiral carrier {len(raw)} exceeds Transputer body bound {MAX_BODY}")
    return raw

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

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--binary",type=Path,default=ROOT/"next/target/release/qikvrt-next")
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    binary=args.binary.resolve()
    if not binary.is_file(): raise SystemExit("BLOCK: qikvrt-next binary missing")
    head=git("rev-parse","HEAD"); tree=git("rev-parse","HEAD^{tree}")
    raw=load_carrier(); digest=sha256(raw); processes=[]
    def cli(*values):
        result=subprocess.run([str(binary),*map(str,values)],capture_output=True,timeout=30)
        if result.returncode!=0: raise RuntimeError(result.stderr.decode(errors="replace"))
        return json.loads(result.stdout)
    def start(*values):
        proc=Proc([binary,*values]); processes.append(proc); return proc
    with tempfile.TemporaryDirectory(prefix="qikvrt-spiral-transputer-") as directory:
        temp=Path(directory)
        subject={"repository":"Goldkelch/qik-vrt","subject_id":"epistemic-spiral","head":head,"tree":tree}
        subject_file=temp/"subject.json"; subject_file.write_bytes(canonical(subject))
        subject_digest=sha256(("\n".join(subject[k] for k in ("repository","subject_id","head","tree"))+"\n").encode())
        credentials=temp/"credentials"
        cli("bus-config",credentials,"bus",subject_file,"A","B")
        for name in ("bus","A","B"): cli("init",temp/name,name)
        try:
            server=start("bus-serve",temp/"bus",credentials/"bus.json","127.0.0.1:0")
            address=server.wait(lambda value:value.get("state")=="LISTENING")["address"]
            sender=start("bus-peer",temp/"A",credentials/"A.json",address)
            receiver=start("bus-peer",temp/"B",credentials/"B.json",address)
            for proc in (sender,receiver):
                joined=proc.wait(lambda value:value.get("state")=="JOINED")
                if joined.get("ordinary_release") is not False: raise RuntimeError("bus admission inferred ordinary release")
            sender.send({"op":"send","destination":"B","subject":subject_digest,"codec":2,"payload_hex":raw.hex()})
            received=receiver.wait(lambda value:value.get("state")=="RECEIVED" and value.get("source")=="A")
            incoming=bytes.fromhex(received["payload_hex"])
            if incoming!=raw: raise RuntimeError("Transputer forward bytes changed")
            receiver.send({"op":"reply","destination":"A","subject":subject_digest,"codec":3,"payload_hex":incoming.hex(),**{k:received[k] for k in ("session","nonce","message_id","correlation")}})
            returned=sender.wait(lambda value:value.get("state")=="RECEIVED" and value.get("source")=="B" and value.get("kind")==3)
            if bytes.fromhex(returned["payload_hex"])!=raw: raise RuntimeError("Transputer return bytes changed")
        finally:
            for proc in processes: proc.stop()
        checkpoint=cli("verify",temp/"bus")["checkpoint"]
    receipt={
      "schema":"qikvrt_epistemic_spiral_transputer_receipt_v1",
      "source_head":head,"source_tree":tree,
      "carrier_schema":"qikvrt_epistemic_spiral_transputer_carrier_v1",
      "carrier_sha256":digest,"carrier_bytes":len(raw),"max_payload_bytes":MAX_BODY,
      "serialize_deserialize_equal":True,"transputer_forward_equal":True,"transputer_return_equal":True,
      "bus_checkpoint":checkpoint,"ordinary_release_inferred":False,
      "predecessor_evidence_transfer":False,"effect_ack_done":False,
      "next_required_effect":"linux_and_oci_readback_then_firefox_and_public_authoritative_readback"
    }
    encoded=json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(encoded,encoding="utf-8")
    print(encoded,end="")

if __name__=="__main__": main()
