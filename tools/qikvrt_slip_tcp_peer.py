#!/usr/bin/env python3
import argparse, json, os, select, struct, time
from pathlib import Path

END=0xC0; ESC=0xDB; ESC_END=0xDC; ESC_ESC=0xDD
NONCE=b'QIKVRT-NONCE-0001'; REPLY=b'QIK-ACK:'+NONCE; GUEST_CONFIRM=b'QIKDONE'
LOCAL_IP=b'\x0a\x00\x00\x01'; GUEST_IP=b'\x0a\x00\x00\x02'
LOCAL_PORT=8771; GUEST_PORT=49152; PEER_SEQ=0x55667788

def checksum(data):
    if len(data)&1: data+=b'\0'
    total=sum(struct.unpack('!%dH'%(len(data)//2),data))
    while total>>16: total=(total&0xffff)+(total>>16)
    return (~total)&0xffff

def packet(seq, ack, flags, payload=b'', ident=0x2001):
    tcp0=struct.pack('!HHIIBBHHH',LOCAL_PORT,GUEST_PORT,seq,ack,0x50,flags,4096,0,0)+payload
    pseudo=LOCAL_IP+GUEST_IP+struct.pack('!BBH',0,6,len(tcp0))
    tc=checksum(pseudo+tcp0)
    tcp=struct.pack('!HHIIBBHHH',LOCAL_PORT,GUEST_PORT,seq,ack,0x50,flags,4096,tc,0)+payload
    total=20+len(tcp)
    ip0=struct.pack('!BBHHHBBH4s4s',0x45,0,total,ident,0x4000,64,6,0,LOCAL_IP,GUEST_IP)
    ic=checksum(ip0)
    return struct.pack('!BBHHHBBH4s4s',0x45,0,total,ident,0x4000,64,6,ic,LOCAL_IP,GUEST_IP)+tcp

def slip_encode(data):
    out=bytearray([END])
    for b in data:
        out.extend((ESC,ESC_END) if b==END else (ESC,ESC_ESC) if b==ESC else (b,))
    out.append(END); return bytes(out)

def frames(buf):
    decoded=bytearray(); in_frame=False; esc=False
    for b in buf:
        if b==END:
            if in_frame and decoded: yield bytes(decoded)
            decoded.clear(); in_frame=True; esc=False; continue
        if not in_frame: continue
        if esc:
            decoded.append(END if b==ESC_END else ESC if b==ESC_ESC else b); esc=False
        elif b==ESC: esc=True
        else: decoded.append(b)

def tcp_fields(pkt):
    if len(pkt)<40 or pkt[0]>>4!=4 or pkt[9]!=6: raise ValueError('not IPv4/TCP')
    ihl=(pkt[0]&15)*4; src,dst=pkt[12:16],pkt[16:20]
    sport,dport,seq,ack=struct.unpack('!HHII',pkt[ihl:ihl+12]); off=(pkt[ihl+12]>>4)*4
    flags=pkt[ihl+13]; payload=pkt[ihl+off:]
    return src,dst,sport,dport,seq,ack,flags,payload

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--guest-out',required=True); ap.add_argument('--guest-in',required=True); ap.add_argument('--receipt',required=True); ap.add_argument('--timeout',type=float,default=20)
    a=ap.parse_args()
    fd_out=os.open(a.guest_out,os.O_RDWR|os.O_NONBLOCK); fd_in=os.open(a.guest_in,os.O_RDWR|os.O_NONBLOCK)
    raw=bytearray(); state='WAIT_SYN'; seen=[]; start=time.time(); success=False
    response_sent=False; guest_confirmed=False
    try:
      while time.time()-start<a.timeout and not success:
        r,_,_=select.select([fd_out],[],[],0.2)
        if not r: continue
        chunk=os.read(fd_out,4096)
        if not chunk: continue
        raw.extend(chunk)
        if raw.count(END)<2: continue
        last=raw.rfind(bytes([END])); complete=bytes(raw[:last+1]); del raw[:last]
        for pkt in frames(complete):
          if state=='WAIT_GUEST_CONFIRM':
            seen.append({'kind':'guest_confirm','payload_hex':pkt.hex()})
            if pkt==GUEST_CONFIRM:
              guest_confirmed=True; success=True; state='DONE'
            continue
          src,dst,sport,dport,seq,ack,flags,payload=tcp_fields(pkt)
          seen.append({'kind':'tcp','seq':seq,'ack':ack,'flags':flags,'payload_hex':payload.hex()})
          if state=='WAIT_SYN' and src==GUEST_IP and dst==LOCAL_IP and sport==GUEST_PORT and dport==LOCAL_PORT and flags&0x02 and seq==0x11223344:
            os.write(fd_in,slip_encode(packet(PEER_SEQ,seq+1,0x12,ident=0x2001))); state='WAIT_NONCE'
          elif state=='WAIT_NONCE' and src==GUEST_IP and dst==LOCAL_IP and sport==GUEST_PORT and dport==LOCAL_PORT and seq==0x11223345 and ack==PEER_SEQ+1 and payload==NONCE:
            os.write(fd_in,slip_encode(packet(PEER_SEQ+1,seq+len(payload),0x18,REPLY,ident=0x2002)))
            response_sent=True; state='WAIT_GUEST_CONFIRM'
    finally:
      os.close(fd_out); os.close(fd_in)
    receipt={
      'schema':'qikvrt_slip_tcp_peer_receipt_v1','success':success,'state':state,
      'guest_ip':'10.0.0.2','peer_ip':'10.0.0.1','guest_port':GUEST_PORT,'peer_port':LOCAL_PORT,
      'nonce':NONCE.decode(),'response':REPLY.decode(),'response_sent':response_sent,
      'guest_post_response_confirmation_observed':guest_confirmed,'observed_frames':seen
    }
    Path(a.receipt).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))
    raise SystemExit(0 if success else 2)
if __name__=='__main__': main()
