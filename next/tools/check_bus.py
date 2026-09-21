#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Three full-duplex TCP peers, EAP admission, targeted replies and crash recovery."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import selectors
import socket
import struct
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
def canonical(v):return json.dumps(v,sort_keys=True,separators=(",", ":")).encode()
def sha(b):return hashlib.sha256(b).hexdigest()

class Process:
    def __init__(self,args):
        self.p=subprocess.Popen(list(map(str,args)),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.buffer=b"";self.events=[]
    def send(self,value):self.p.stdin.write(canonical(value)+b"\n");self.p.stdin.flush()
    def wait(self,predicate,timeout=12):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            for index,item in enumerate(self.events):
                if predicate(item):return self.events.pop(index)
            while b"\n" in self.buffer:
                line,self.buffer=self.buffer.split(b"\n",1);self.events.append(json.loads(line))
            for index,item in enumerate(self.events):
                if predicate(item):return self.events.pop(index)
            sel=selectors.DefaultSelector();sel.register(self.p.stdout,selectors.EVENT_READ)
            ready=sel.select(max(0,until-time.monotonic()));sel.close()
            if not ready:break
            chunk=os.read(self.p.stdout.fileno(),65536)
            if not chunk:raise AssertionError(self.p.stderr.read().decode())
            self.buffer+=chunk
        raise AssertionError(("event timeout",self.events,self.buffer))
    def stop(self):
        if self.p.poll() is None:self.p.kill()
        self.p.wait(timeout=5)
    def graceful(self):
        self.p.stdin.close();self.p.wait(timeout=5)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"target/release/qikvrt-next")
    p.add_argument("--output",type=Path)
    a=p.parse_args();binary=a.binary.resolve();processes=[]
    def cli(*args,data=None):
        r=subprocess.run([str(binary),*map(str,args)],input=data,capture_output=True,timeout=30)
        assert r.returncode==0,r.stderr.decode();return json.loads(r.stdout)
    def start(*args):
        proc=Process([binary,*args]);processes.append(proc);return proc
    catalog=json.loads((ROOT/"component-catalog.json").read_text())
    subject={**catalog["source"],"subject_id":"universal-transputer"}
    digest=sha(("\n".join(subject[k] for k in ("repository","subject_id","head","tree"))+"\n").encode())
    def command(event,a,b):return {"event_id":event,"node_id":"universal-transputer","subject":subject,"cause_event_ids":[],
        "operation":{"op":"evaluate","a":a,"b":b,"lut":6,"requested":2,"binding":1,"authority":1,"distinction":1,"drift":0}}
    def send(peer,to,data,codec=1):peer.send({"op":"send","destination":to,"subject":digest,"codec":codec,"payload_hex":data.hex()})
    def receipt(peer,event):
        def match(v):
            if v.get("state")!="RECEIVED" or v.get("kind")!=3:return False
            try:x=json.loads(bytes.fromhex(v["payload_hex"]))
            except (ValueError,KeyError):return False
            return x.get("result",{}).get("record",{}).get("command",{}).get("event_id")==event
        got=peer.wait(match);body=json.loads(bytes.fromhex(got["payload_hex"]))
        assert got["ordinary_release"] is False and body["effect_ack_done"] is False
        return got,body
    with tempfile.TemporaryDirectory(prefix="qikvrt-bus-") as temporary:
        temp=Path(temporary);subject_file=temp/"subject.json";subject_file.write_bytes(canonical(subject))
        credentials=temp/"credentials";cli("bus-config",credentials,"bus",subject_file,"A","B","C")
        artifact=temp/"artifact";artifact.write_bytes(b"test component with stable identity")
        for name in ["bus","A","B","C"]:
            cli("init",temp/name,name)
            if name!="bus":
                obj=cli("put",temp/name,artifact)["sha256"]
                register={"event_id":"initial-register","node_id":"universal-transputer","subject":subject,"cause_event_ids":[],"operation":{"op":"register","artifact":obj,"entrypoint":"next/AI"}}
                cli("run",temp/name,data=canonical(register)+b"\n")
        try:
            server=start("bus-serve",temp/"bus",credentials/"bus.json","127.0.0.1:0")
            address=server.wait(lambda v:v.get("state")=="LISTENING")["address"]
            left=start("bus-peer",temp/"A",credentials/"A.json",address,"--worker")
            right=start("bus-peer",temp/"B",credentials/"B.json",address,"--worker")
            console=start("bus-peer",temp/"C",credentials/"C.json",address)
            for peer in [left,right,console]:
                joined=peer.wait(lambda v:v.get("state")=="JOINED")
                assert joined["wire_d4"]==1 and joined["ordinary_release"] is False
            # Both directions carry requests before waiting for either response.
            send(left,"B",canonical(command("A-to-B",13,9)))
            send(right,"A",canonical(command("B-to-A",20,8)))
            l,lr=receipt(left,"A-to-B");r,rr=receipt(right,"B-to-A")
            assert (l["source"],l["destination"],lr["result"]["record"]["result"]["value"])==("B","A",4)
            assert (r["source"],r["destination"],rr["result"]["record"]["result"]["value"])==("A","B",28)
            # Two independent requests to the third peer, answered in reverse order.
            bodies=[bytes(range(251))*17,b"second request"]
            received=[]
            for body in bodies:
                send(left,"C",body,2)
                got=console.wait(lambda v:v.get("state")=="RECEIVED" and v.get("kind")==1)
                assert bytes.fromhex(got["payload_hex"])==body;received.append(got)
            bad={"op":"reply","destination":"A","subject":digest,"codec":3,"payload_hex":b"wrong correlation".hex(),
                **{k:received[0][k] for k in ["session","nonce","message_id"]},"correlation":"0"*64}
            console.send(bad)
            refused=console.wait(lambda v:v.get("state")=="RECEIVED" and v.get("source")=="bus" and v.get("wire_d4")==0)
            assert json.loads(bytes.fromhex(refused["payload_hex"]))["effect_ack"]=="EFFECT_NACK"
            for got in received[::-1]:
                console.send({"op":"reply","destination":"A","subject":digest,"codec":3,"payload_hex":("reply:"+got["correlation"]).encode().hex(),
                    **{k:got[k] for k in ["session","nonce","message_id","correlation"]}})
            returned=[]
            for _ in received:
                got=left.wait(lambda v:v.get("state")=="RECEIVED" and v.get("source")=="C" and v.get("kind")==3)
                assert bytes.fromhex(got["payload_hex"])==("reply:"+got["correlation"]).encode();returned.append(got["correlation"])
            assert returned==[v["correlation"] for v in received[::-1]]
            # Recycle the finite C90 cache, then send a later EAP observation
            # for an older call. Its original request is recovered from history.
            for i in range(40):
                send(left,"B",canonical(command("burst-"+str(i),i,1)))
                receipt(left,"burst-"+str(i))
            old=received[0]
            console.send({"op":"reply","destination":"A","subject":digest,"codec":3,"payload_hex":b"later EAP observation".hex(),
                **{k:old[k] for k in ["session","nonce","message_id","correlation"]}})
            late=left.wait(lambda v:v.get("state")=="RECEIVED" and v.get("source")=="C" and v.get("payload_hex")==b"later EAP observation".hex())
            assert late["correlation"]==old["correlation"]
            # A valid participant with a bad per-frame MAC never reaches the bus log.
            console.graceful()
            key=bytes.fromhex(json.loads((credentials/"C.json").read_text())["key"])
            host,port=address.rsplit(":",1)
            connection=None
            for _ in range(20):
                connection=socket.create_connection((host,int(port)),timeout=3);f=connection.makefile("rwb",buffering=0)
                challenge=json.loads(f.readline());nonce=bytes.fromhex(challenge["challenge"])
                proof=hmac.new(key,b"JOIN\nbus\nC\n"+nonce,hashlib.sha256).hexdigest()
                f.write(canonical({"id":"C","proof":proof})+b"\n");joined=json.loads(f.readline())
                if joined.get("state")=="JOINED":break
                f.close();connection.close();time.sleep(.01)
            assert joined["state"]=="JOINED"
            proof=bytes.fromhex(joined.pop("proof"));assert hmac.compare_digest(proof,hmac.new(key,b"ACCEPT\n"+nonce+canonical(joined),hashlib.sha256).digest())
            raw=subprocess.check_output([str(binary),"packet","C","A",digest,"2",str(artifact)],timeout=10)
            f.write(struct.pack(">QI",0,len(raw))+raw+b"\0"*32)
            # Previously queued traffic may already be in the opposite TCP
            # direction. Drain it; the invalid incoming MAC must close this link.
            drained=0
            while True:
                old=f.read(8192)
                if not old:break
                drained+=len(old);assert drained<100000
            f.close();connection.close()
            assert not (temp/"bus"/"objects"/sha(raw)).exists()
            send(left,"B",canonical(command("after-invalid-MAC",7,3)));receipt(left,"after-invalid-MAC")
            # Queue an effect request while its receiver is absent, then kill the bus.
            right.stop()
            send(left,"B",canonical(command("offline-queue",31,16)))
            server.wait(lambda v:v.get("state")=="QUEUED" and v.get("destination")=="B" and
                b"offline-queue" in (temp/"bus"/"objects"/v["frame"]).read_bytes())
            originals={name:{f.name:f.read_bytes() for f in (temp/name/"events").glob("*.json")} for name in ["bus","A","B"]}
            server.stop();left.stop()
            server=start("bus-serve",temp/"bus",credentials/"bus.json","127.0.0.1:0")
            address=server.wait(lambda v:v.get("state")=="LISTENING")["address"]
            left=start("bus-peer",temp/"A",credentials/"A.json",address,"--worker")
            right=start("bus-peer",temp/"B",credentials/"B.json",address,"--worker")
            left.wait(lambda v:v.get("state")=="JOINED");right.wait(lambda v:v.get("state")=="JOINED")
            _,result=receipt(left,"offline-queue")
            assert result["result"]["record"]["result"]["value"]==15
            for peer in [left,right,server]:peer.stop()
            for name,files in originals.items():
                for filename,data in files.items():assert (temp/name/"events"/filename).read_bytes()==data
            results={}
            for name in ["A","B"]:
                history=[];after=0
                while True:
                    page=cli("history",temp/name,after)
                    if not page:break
                    history.extend(page);after=page[-1]["record"]["sequence"]
                events=[v["record"]["command"]["event_id"] for v in history if v["record"]["command"]["operation"]["op"]=="evaluate"]
                assert len(events)==len(set(events));results[name]=events
            assert set(results["B"])=={"A-to-B","after-invalid-MAC","offline-queue"}|{"burst-"+str(i) for i in range(40)},results
            assert results["A"]==["B-to-A"],results
            # IP version is an adapter choice; the same C90 bus also runs on IPv6.
            server6=start("bus-serve",temp/"bus",credentials/"bus.json","[::1]:0")
            addr6=server6.wait(lambda v:v.get("state")=="LISTENING")["address"]
            peer6=start("bus-peer",temp/"C",credentials/"C.json",addr6)
            assert peer6.wait(lambda v:v.get("state")=="JOINED")["wire_d4"]==1
            peer6.stop();server6.stop()
            checkpoint=cli("verify",temp/"bus")["checkpoint"]
        finally:
            for proc in processes:proc.stop()
    report={"state":"PASS","scope":"authenticated_full_duplex_c90_bus","ip_versions":[4,6],"concurrent_participants":3,
        "simultaneous_requests_in_both_directions":True,"reverse_order_targeted_replies":True,"wrong_correlation_eap_nack":True,
        "bad_packet_mac_rejected":True,"offline_request_survives_bus_sigkill":True,"original_record_bytes_unchanged":True,
        "model_effects_executed_once":{name:len(events) for name,events in results.items()},"completed_calls_beyond_cache_capacity":40,
        "late_response_after_cache_reconstruction":True,"bus_checkpoint":checkpoint,"ordinary_release_inferred":False}
    if a.output:a.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
