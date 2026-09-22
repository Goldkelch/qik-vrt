#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Independent wire oracle and real C90 -> TCP -> C90/Rust -> durable-store round trip."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import selectors
import shutil
import socket
import struct
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
MAX_MESSAGE=62784
def sha(data):return hashlib.sha256(data).hexdigest()
def canon(value):return json.dumps(value,sort_keys=True,separators=(",", ":")).encode()
def subject_sha(s):return sha(("\n".join(s[k] for k in ("repository","subject_id","head","tree"))+"\n").encode())
def fnv(data):
    value=2166136261
    for byte in data:value=((value^byte)*16777619)&0xffffffff
    return value
def encode(payload,*,direction=0,kind=1,flags=0,d0=0,d4=0,session=8,nonce=9,source=10,hi=0,lo=0,message=10,index=0,count=1):
    header=struct.pack(">4s6BH9I",b"QVRT",1,direction,kind,flags,d0,d4,84,session,nonce,source,hi,lo,message,index,count,len(payload))+hashlib.sha256(payload).digest()
    head=header+struct.pack(">I",fnv(header));data=head+payload
    return data+struct.pack(">I",fnv(data))
def split(data):
    frames=[]
    while data:
        assert len(data)>=88
        n=struct.unpack_from(">I",data,44)[0];assert n<=4096 and len(data)>=88+n
        frames.append(data[:88+n]);data=data[88+n:]
    return frames
def decode(frame):
    assert frame[:5]==b"QVRT\1" and frame[10:12]==b"\0T"
    n=struct.unpack_from(">I",frame,44)[0];assert len(frame)==88+n
    assert fnv(frame[:80])==struct.unpack_from(">I",frame,80)[0]
    assert fnv(frame[:-4])==struct.unpack_from(">I",frame,len(frame)-4)[0]
    payload=frame[84:-4];assert hashlib.sha256(payload).digest()==frame[48:80]
    return payload
def reframe(frame,payload):
    h=frame[:44]+struct.pack(">I",len(payload))+hashlib.sha256(payload).digest()
    h+=struct.pack(">I",fnv(h));h+=payload
    return h+struct.pack(">I",fnv(h))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary",type=Path,default=ROOT/"target/release/qikvrt-next")
    p.add_argument("--c90",type=Path,default=ROOT/"core/build/qikvrt-c90")
    p.add_argument("--output",type=Path)
    a=p.parse_args();binary=a.binary.resolve();c90=a.c90.resolve()
    def run(exe,*args,data=None,good=True):
        r=subprocess.run([str(exe),*map(str,args)],input=data,capture_output=True,timeout=40)
        if good:assert r.returncode==0,r.stderr.decode(errors="replace")
        return r
    def cli(*args,data=None):return json.loads(run(binary,*args,data=data).stdout)
    source_hash=sha(b"left");dest_hash=sha(b"right");binding=sha(b"fixed subject")
    catalog=json.loads((ROOT/"component-catalog.json").read_text());rng=random.Random(19090)
    boundaries=[0,1,55,56,63,64,255,3924,3925,4096,8192,MAX_MESSAGE]
    with tempfile.TemporaryDirectory(prefix="qikvrt-exchange-") as temp:
        temp=Path(temp);body_path=temp/"body.bin"
        # Compile the byte-frozen predecessor, and compare a separate Python encoder.
        legacy=temp/"legacy.so"
        run("cc","-std=c90","-pedantic-errors","-O2","-shared","-fPIC",
            ROOT.parent/"src/cloud_transputer/qikvrt_wire_v1.c",
            ROOT.parent/"src/cloud_transputer/qikvrt_sha256_v1.c","-o",legacy)
        class Header(ctypes.Structure):
            _fields_=[(k,ctypes.c_ubyte) for k in ("direction","type","flags","d0","d4")]+[(k,ctypes.c_uint) for k in
                ("session_id","nonce","source_node","virtual_time_hi","virtual_time_lo","message_id","chunk_index","chunk_count","payload_length")]+[("payload_sha256",ctypes.c_ubyte*32)]
        lib=ctypes.CDLL(str(legacy));lib.qikvrt_wire_encode.argtypes=[ctypes.POINTER(Header),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)]
        legacy_cases=0
        for length in [0,1,55,56,63,64,255,1024,4096]:
            for kind in range(1,5):
                data=rng.randbytes(length);s=rng.getrandbits(32);nonce=rng.getrandbits(32)
                frame=encode(data,direction=int(kind!=1),kind=kind,d4=kind,session=s,nonce=nonce,source=0xffffffff,hi=0x87654321,lo=0xfedcba98)
                h=Header(direction=int(kind!=1),type=kind,d4=kind,session_id=s,nonce=nonce,source_node=0xffffffff,
                    virtual_time_hi=0x87654321,virtual_time_lo=0xfedcba98,message_id=10,chunk_count=1,payload_length=length)
                output=ctypes.create_string_buffer(4184);written=ctypes.c_uint()
                assert lib.qikvrt_wire_encode(ctypes.byref(h),data,output,4184,ctypes.byref(written))==1
                assert output.raw[:written.value]==frame
                assert run(c90,"roundtrip",data=frame).stdout==frame
                legacy_cases+=1
        for length in boundaries:
            body=rng.randbytes(length);body_path.write_bytes(body)
            packet=run(c90,"send",source_hash,dest_hash,binding,2,body_path).stdout
            parts=split(packet)
            rebuilt=[]
            for i,part in enumerate(parts):
                payload=decode(part)
                assert payload[:8]==b"QXT2\1\4\2\0"
                assert payload[8:104]==bytes.fromhex(source_hash+dest_hash+binding)
                assert payload[104:136]==hashlib.sha256(body).digest()
                assert struct.unpack_from(">I",payload,136)[0]==length
                assert struct.unpack_from(">I",part,36)[0]==i
                rebuilt.append(payload[172:])
            assert b"".join(rebuilt)==body
            assert run(binary,"unpack","left","right",binding,data=packet).stdout==body
            reverse=run(binary,"packet","left","right",binding,2,body_path).stdout
            assert run(c90,"receive",source_hash,dest_hash,binding,data=reverse).stdout==body
            assert run(binary,"unpack","left","right",binding,data=b"".join(parts[::-1]+parts[:1])).stdout==body
        full=parts
        negative_cases=0
        malformed=[b"".join(full[:-1]),b"".join(full)[:-1],b"".join(full)+b"x"]
        forged=bytearray(decode(full[0]));forged[172]^=1
        malformed.append(reframe(full[0],forged)+b"".join(full[1:]))
        malformed.append(full[0]+reframe(full[0],forged)+b"".join(full[1:]))
        for damaged in malformed:
            assert run(binary,"unpack","left","right",binding,data=damaged,good=False).returncode!=0
            assert run(c90,"receive",source_hash,dest_hash,binding,data=damaged,good=False).returncode!=0
            negative_cases+=1
        for sender,receiver,subject in [("wrong","right",binding),("left","wrong",binding),("left","right","0"*64)]:
            assert run(binary,"unpack",sender,receiver,subject,data=b"".join(full),good=False).returncode!=0
            negative_cases+=1
        # Two independent repository stores. Destination receives only protocol bytes.
        left=temp/"left";right=temp/"right"
        cli("init",left,"left");cli("init",right,"right")
        imported=json.loads(run(sys.executable,ROOT/"tools/carrier.py","import","--binary",binary,"--store",left).stdout)
        catalog_digest=imported["catalog_sha256"]
        history=cli("history",left)
        original_files={str(f.relative_to(left)):f.read_bytes() for f in left.rglob("*") if f.is_file() and f.name!="writer.lock"}
        original_checkpoint=cli("verify",left)["checkpoint"]
        snapshot=cli("snapshot",left)["snapshot"]
        transfers=0;restarts=0
        def start(subject):
            process=subprocess.Popen([str(binary),"mesh-serve",str(right),"left",subject,"127.0.0.1:0"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            sel=selectors.DefaultSelector();sel.register(process.stdout,selectors.EVENT_READ)
            assert sel.select(10),"mesh listener did not start";sel.close()
            ready=json.loads(process.stdout.readline());assert ready["state"]=="LISTENING"
            host,port=ready["address"].rsplit(":",1)
            return process,ready["address"],(host,int(port))
        def tcp_packet(endpoint,packet):
            with socket.create_connection(endpoint,timeout=5) as sock:
                for offset in range(0,len(packet),127):sock.sendall(packet[offset:offset+127])
                sock.shutdown(socket.SHUT_WR);reply=b""
                while True:
                    data=sock.recv(8192)
                    if not data:break
                    reply+=data
                return reply
        universal=next(h["record"]["command"] for h in history if h["record"]["command"]["node_id"]=="universal-transputer")
        binding=subject_sha(universal["subject"])
        process,address,endpoint=start(binding)
        try:
            for obj in sorted((left/"objects").iterdir()):
                ack=cli("mesh-send","left","right",binding,2,obj,address)
                assert ack["result"]["sha256"]==obj.name and ack["effect_ack_done"] is False
                transfers+=1
            # C90 sender -> arbitrarily fragmented TCP -> C90/Rust -> fsync -> reverse wire receipt.
            body_path.write_bytes(canon(universal))
            request=run(c90,"send",source_hash,dest_hash,binding,1,body_path).stdout
            reply=tcp_packet(endpoint,request)
            ack=json.loads(run(binary,"unpack","left","right",binding,"reverse",data=reply).stdout)
            assert ack["result"]["state"]=="PERSISTED" and ack["effect_ack_done"] is False
            checkpoint=ack["checkpoint"]
            # Malformed peer traffic must not end the listener.
            assert tcp_packet(endpoint,b"broken")==b""
            replay=cli("mesh-send","left","right",binding,1,body_path,address)
            assert replay["result"]["replayed"] is True and replay["checkpoint"]==checkpoint
            spoof=json.loads(canon(universal));spoof["event_id"]="wrong-subject";spoof["subject"]["head"]="0"*40
            body_path.write_bytes(canon(spoof));held=cli("mesh-send","left","right",binding,1,body_path,address)
            assert held["result"]["reason"]=="PAYLOAD_SUBJECT_MISMATCH" and held["checkpoint"]==checkpoint
            preserve={**universal,"event_id":"preserve-original-store","operation":{"op":"preserve_store","snapshot":snapshot}}
            body_path.write_bytes(canon(preserve))
            assert cli("mesh-send","left","right",binding,1,body_path,address)["result"]["state"]=="PERSISTED"
            # Compile and execute a TEMDD program received as a C90-carried object.
            program=('temdd 0.1; authority owner = "Ingolf Lohmann"; subject universal-transputer { repository = "Goldkelch/qik-vrt"; binding = exact; } '
                'request r { target = CONTINUITY; } on event { follow exact; effect boolean_lut { require authority; require validation; commit; readback; } } until { IDENTITY_RETAINED; }').encode()
            body_path.write_bytes(program);stored=cli("mesh-send","left","right",binding,2,body_path,address)
            event={**universal,"event_id":"c90-temdd-native","cause_event_ids":[universal["event_id"]],"operation":{"op":"program","source":sha(program),"event":"event","input":{
                "a":13,"b":9,"lut":6,"requested":2,"binding":1,"authority":1,"distinction":1,"drift":0}}}
            assert stored["result"]["sha256"]==sha(program)
            body_path.write_bytes(canon(event));request=run(c90,"send",source_hash,dest_hash,binding,1,body_path).stdout
            response=json.loads(run(binary,"unpack","left","right",binding,"reverse",data=tcp_packet(endpoint,request)).stdout)
            assert response["result"].get("state")=="PERSISTED",response
            assert response["result"]["record"]["result"]["native_effect"]["value"]==4,response
            assert response["result"]["record"]["command"]["cause_event_ids"]==[universal["event_id"]]
        finally:process.kill();process.wait(timeout=5);restarts+=1
        assert cli("verify",right)["checkpoint"]==response["checkpoint"]
        for item in history:
            command=item["record"]["command"]
            if command["node_id"]=="universal-transputer":continue
            binding=subject_sha(command["subject"]);body_path.write_bytes(canon(command))
            process,address,endpoint=start(binding)
            try:assert cli("mesh-send","left","right",binding,1,body_path,address)["result"]["state"]=="PERSISTED"
            finally:process.kill();process.wait(timeout=5);restarts+=1
        assert cli("discover",right)["node_count"]==10
        # Simulate loss of the sender; reconstruction must use the destination alone.
        shutil.rmtree(left)
        original=temp/"original-store-restored"
        assert cli("restore-store",right,snapshot,original)["checkpoint"]==original_checkpoint
        for path,data in original_files.items():assert (original/path).read_bytes()==data,path
        assert cli("history",original)==history
        restored=temp/"restored"
        run(sys.executable,ROOT/"tools/carrier.py","restore","--binary",binary,"--store",right,"--digest",catalog_digest,"--destination",restored)
        for entry in catalog["files"]:assert sha((restored/entry["path"]).read_bytes())==entry["sha256"]
        preserved=cli("verify",right)["checkpoint"]
    result={"state":"PASS","scope":"portable_wire_and_two_store_mesh","legacy_byte_identity_cases":legacy_cases,
        "bidirectional_c90_rust_size_boundaries":boundaries,"negative_transfers_rejected":negative_cases,
        "objects_copied_over_tcp":transfers,"receiver_sigkill_restarts":restarts,"preserved_components":10,
        "source_files_restored_without_sender":len(catalog["files"]),"temdd_c90_native_result":4,
        "destination_checkpoint":preserved,"original_store_snapshot_restored_byte_exact":True,"effect_ack_done_inferred":False}
    if a.output:a.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
