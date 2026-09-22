#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
"""Process-boundary acceptance: SIGKILL, relocation, replay and offline restore."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import select
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from carrier import target_catalog, import_catalog, restore as restore_catalog

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary",type=Path,default=ROOT/"target/release/qikvrt-next")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args();binary=args.binary.resolve()
    def call(*cmd,raw=None,good=True):
        r=subprocess.run([str(binary),*map(str,cmd)],input=raw,capture_output=True,timeout=30)
        if good and r.returncode:raise AssertionError(r.stderr.decode())
        return r
    def value(*cmd,raw=None):return json.loads(call(*cmd,raw=raw).stdout)
    catalog=json.loads((ROOT/"component-catalog.json").read_text())
    source=catalog["source"]
    subject={**source,"subject_id":"transputer"}
    def command(i,operation):return {"event_id":i,"node_id":"durable-test-node","subject":subject,"cause_event_ids":[],"operation":operation}
    parser_cases=0
    for path in sorted((ROOT/"reference/tests/temdd").rglob("*.temdd")):
        r=call("compile",path,good=False)
        legacy=subprocess.run([sys.executable,str(ROOT/"reference/tools/qikvrt_temdd.py"),str(path)],capture_output=True)
        if "positive" in path.parts:
            assert r.returncode==0 and legacy.returncode==0
            assert json.loads(r.stdout)==json.loads(legacy.stdout)
        else:assert r.returncode!=0 and legacy.returncode!=0,path
        parser_cases+=1
    with tempfile.TemporaryDirectory(prefix="qikvrt-continuity-") as tmp:
        tmp=Path(tmp);store=tmp/"persistent";value("init",store,"acceptance-transputer")
        imported=subprocess.run([sys.executable,str(ROOT/"tools/carrier.py"),"import","--binary",str(binary),"--store",str(store)],capture_output=True,timeout=120)
        assert imported.returncode==0,imported.stderr.decode()
        receipt=json.loads(imported.stdout);digest=receipt["catalog_sha256"]
        initial=value("discover",store)
        assert initial["node_count"]==10
        register=command("register-durable",{"op":"register","artifact":digest,"entrypoint":"deploy/universal-terminal/cloud-entrypoint.sh"})
        result=value("run",store,raw=json.dumps(register).encode()+b"\n")
        assert result["state"]=="PERSISTED"
        anchor_before=value("verify",store)["checkpoint"]
        replay=value("run",store,raw=json.dumps(register).encode()+b"\n")
        assert replay["replayed"] is True and value("verify",store)["checkpoint"]==anchor_before
        # A malformed input must not terminate the event loop or discard the next request.
        valid=command("after-invalid",{"op":"reachability","reachable":False,"ttl_seconds":60})
        responses=call("run",store,raw=b'{bad json}\n'+json.dumps(valid).encode()+b"\n").stdout.splitlines()
        assert [json.loads(x)["state"] for x in responses]==["HOLD","PERSISTED"]
        timings=[]
        for restart in range(8):
            owner=subprocess.Popen([str(binary),"serve",str(store),"127.0.0.1:0"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                ready=json.loads(owner.stdout.readline());assert ready["state"]=="LISTENING"
                url="http://"+ready["address"]
                def get(path):
                    with urllib.request.urlopen(url+path,timeout=5) as r:return json.loads(r.read())
                event=command("restart-"+str(restart),{"op":"evaluate","a":13,"b":9,"lut":6,"requested":2,"binding":1,"authority":1,"distinction":1,"drift":0})
                req=urllib.request.Request(url+"/api/execute",data=json.dumps(event).encode(),headers={"Content-Type":"application/json"})
                start=time.perf_counter_ns()
                with urllib.request.urlopen(req,timeout=5) as r:ack=json.loads(r.read())
                timings.append(time.perf_counter_ns()-start)
                assert ack["state"]=="PERSISTED" and ack["record"]["result"]["value"]==4
                d=get("/api/directory");assert d["node_count"]==11
                assert any(n["node_id"]=="universal-transputer" for n in d["nodes"])
                # No active-writer bypass in another process.
                assert call("discover",store,good=False).returncode!=0
                with urllib.request.urlopen(url+"/AI",timeout=5) as r:assert "TEMDD" in r.read().decode()
                rejected=command("denied-origin-"+str(restart),event["operation"])
                wrong=urllib.request.Request(url+"/api/execute",data=json.dumps(rejected).encode(),headers={"Content-Type":"application/json","Origin":"https://untrusted.example"})
                try:urllib.request.urlopen(wrong,timeout=5);raise AssertionError("cross-origin request accepted")
                except urllib.error.HTTPError as e:
                    assert e.code==400 and json.loads(e.read())=={"state":"HOLD","reason":"SAME_ORIGIN_REQUIRED","done":False}
                if restart==0:
                    checkpoint=get("/api/checkpoint")
                    records={f.name:f.read_bytes() for f in (store/"events").glob("*.json")}
                    host,port=ready["address"].rsplit(":",1)
                    for size in (400,60000):
                        body=json.dumps(command("denied-split-"+str(size),event["operation"])).encode()
                        body+=b" "*max(0,size-len(body))
                        with socket.create_connection((host,int(port)),timeout=5) as client:
                            header=("POST /api/execute HTTP/1.1\r\nHost: "+ready["address"]+
                                "\r\nOrigin: https://untrusted.example\r\nContent-Type: application/json\r\nContent-Length: "+str(len(body))+"\r\n\r\n").encode()
                            client.sendall(header)
                            assert not select.select([client],[],[],0.05)[0],"rejection sent before bounded body was consumed"
                            client.sendall(body)
                            response=http.client.HTTPResponse(client);response.begin()
                            assert response.status==400
                            assert json.loads(response.read())=={"state":"HOLD","reason":"SAME_ORIGIN_REQUIRED","done":False}
                        assert get("/api/checkpoint")==checkpoint
                        assert {f.name:f.read_bytes() for f in (store/"events").glob("*.json")}==records
                    valid=command("after-origin-rejection",event["operation"])
                    req=urllib.request.Request(url+"/api/execute",data=json.dumps(valid).encode(),headers={"Content-Type":"application/json"})
                    with urllib.request.urlopen(req,timeout=5) as r:ack=json.loads(r.read())
                    assert ack["state"]=="PERSISTED" and ack["record"]["result"]["value"]==4
            finally:
                owner.kill();owner.wait(timeout=5)
            after=value("verify",store)["checkpoint"]
            assert after["sequence"]==14+restart,after
            assert after["digest"]==ack["digest"]
        # Three successive relocations retain every committed byte and node.
        for generation in range(3):
            moved=tmp/("recovered-"+str(generation));shutil.copytree(store,moved)
            before=value("verify",store)["checkpoint"]
            shutil.rmtree(store);store=moved
            assert value("verify",store)["checkpoint"]==before
            assert value("discover",store)["node_count"]==11
            destination=tmp/("source-restore-"+str(generation))
            restore=subprocess.run([sys.executable,str(ROOT/"tools/carrier.py"),"restore","--binary",str(binary),"--store",str(store),"--digest",digest,"--destination",str(destination)],capture_output=True,timeout=120)
            assert restore.returncode==0,restore.stderr.decode()
            for entry in catalog["files"]:
                assert hashlib.sha256((destination/entry["path"]).read_bytes()).hexdigest()==entry["sha256"]
        # Preserve this exact successor as a new version of the stable identity.
        originals={f.name:f.read_bytes() for f in (store/"events").glob("*.json")}
        successor=target_catalog(ROOT.parent,"HEAD",os.environ.get("GITHUB_REPOSITORY","Goldkelch/qik-vrt"))
        successor_receipt=import_catalog(binary,store,ROOT.parent,successor)
        discovered=value("discover",store)
        transputer=next(n for n in discovered["nodes"] if n["node_id"]=="universal-transputer")
        assert len(transputer["registered_versions"])==2
        for name,data in originals.items():assert (store/"events"/name).read_bytes()==data
        recovered=tmp/"recovered-current-target"
        restore_catalog(binary,store,successor_receipt["catalog_sha256"],recovered)
        # Build using only recovered sources; neither Git nor the original source
        # directory participates in this C90/assembler build.
        built=subprocess.run(["make","-C",str(recovered/"next/core"),"test","assembly"],capture_output=True,timeout=120)
        assert built.returncode==0,built.stdout.decode()+built.stderr.decode()
        preserved=value("verify",store)["checkpoint"]
        # Tail loss must fail closed; retain all other evidence.
        last=store/"events"/(str(preserved["sequence"]).zfill(20)+".json")
        last.unlink()
        failed=call("verify",store,good=False)
        assert failed.returncode!=0 and b"ACKNOWLEDGED_HISTORY_MISSING" in failed.stderr
        assert call("init",store,"empty-reset",good=False).returncode!=0
        assert len(list((store/"anchors").glob("*.json")))==preserved["sequence"]
    result={"state":"PASS","scope":"process_and_source_continuity","legacy_parser_cases":parser_cases,
        "sigkill_restarts":8,"successive_relocations":3,"components_preserved":10,
        "files_restored_each_time":len(catalog["files"]),"acknowledged_events_preserved":preserved["sequence"],
        "durable_http_ack_latency_ns":timings,"median_durable_http_ack_ns":sorted(timings)[len(timings)//2],
        "missing_history_reinitialized":False,"catalog_sha256":digest,"physical_hardware_tested":False,
        "successor_source":successor["source"],"successor_catalog_sha256":successor_receipt["catalog_sha256"],
        "successor_files_restored":len(successor["files"]),"transputer_versions_preserved":2,
        "restored_successor_c90_and_assembler_executed":True,
        "split_body_origin_rejections":2,"complete_rejection_readback":True,
        "rejected_requests_preserve_checkpoint_and_event_bytes":True,
        "same_process_valid_request_after_rejection":True}
    if args.output:args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
