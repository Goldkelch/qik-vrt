/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
 * Portable successor of src/cloud_transputer/qikvrt_wire_v1.c; same wire bytes. */
#include "qikvrt_transputer.h"
#include <string.h>
qikvrt_u32 qikvrt_fnv1a32(const unsigned char *data, unsigned int n) {
    qikvrt_u32 h=2166136261UL; unsigned int i;
    for(i=0U;i<n;++i){h^=(qikvrt_u32)data[i];h*=16777619UL;}
    return h;
}
static int valid(const qikvrt_wire_frame *f) {
    if(f->direction>1U || f->type<1U || f->type>4U || f->d0>3U || f->d4>4U) return 0;
    if(f->chunk_count==0U || f->chunk_index>=f->chunk_count || f->payload_length>4096U) return 0;
    return f->type==QIKVRT_TYPE_REQUEST ? f->direction==0U : f->direction==1U;
}
static void metadata(const unsigned char *w, qikvrt_wire_frame *f) {
    memset(f,0,sizeof(*f)); f->direction=w[5];f->type=w[6];f->flags=w[7];f->d0=w[8];f->d4=w[9];
    f->session_id=qikvrt_get32(w+12);f->nonce=qikvrt_get32(w+16);f->source_node=qikvrt_get32(w+20);
    f->virtual_time_hi=qikvrt_get32(w+24);f->virtual_time_lo=qikvrt_get32(w+28);
    f->message_id=qikvrt_get32(w+32);f->chunk_index=qikvrt_get32(w+36);
    f->chunk_count=qikvrt_get32(w+40);f->payload_length=qikvrt_get32(w+44);
}
int qikvrt_wire_encode(const qikvrt_wire_frame *f,const unsigned char *payload,
    unsigned char *out,unsigned int cap,unsigned int *written) {
    unsigned int total,plen; unsigned char dg[32];
    if(!f || !out || !written || !valid(f) || (f->payload_length && !payload)) return 0;
    plen=(unsigned int)f->payload_length; total=88U+plen;
    if(cap<total) return 0;
    /* Hash then move before writing the header: payload may be out+84. */
    qikvrt_sha256(payload,plen,dg);
    if(plen)memmove(out+84,payload,plen);
    memset(out,0,84); memcpy(out,"QVRT",4); out[4]=1U;
    out[5]=f->direction;out[6]=f->type;out[7]=f->flags;out[8]=f->d0;out[9]=f->d4;out[11]=84U;
    qikvrt_put32(out+12,f->session_id);qikvrt_put32(out+16,f->nonce);qikvrt_put32(out+20,f->source_node);
    qikvrt_put32(out+24,f->virtual_time_hi);qikvrt_put32(out+28,f->virtual_time_lo);
    qikvrt_put32(out+32,f->message_id);qikvrt_put32(out+36,f->chunk_index);
    qikvrt_put32(out+40,f->chunk_count);qikvrt_put32(out+44,f->payload_length);
    memcpy(out+48,dg,32);
    qikvrt_put32(out+80,qikvrt_fnv1a32(out,80));
    qikvrt_put32(out+84+plen,qikvrt_fnv1a32(out,84U+plen));*written=total;return 1;
}
int qikvrt_wire_view(const unsigned char *w,unsigned int n,qikvrt_wire_frame *f,
    const unsigned char **payload) {
    qikvrt_u32 wide; unsigned int plen; unsigned char dg[32]; qikvrt_wire_frame candidate;
    if(!w || !f || !payload || n<88U || memcmp(w,"QVRT",4)!=0 || w[4]!=1U || w[10]!=0U || w[11]!=84U) return 0;
    wide=qikvrt_get32(w+44);if(wide>4096U)return 0;plen=(unsigned int)wide;
    if(n!=88U+plen)return 0;
    if(qikvrt_get32(w+80)!=qikvrt_fnv1a32(w,80) ||
       qikvrt_get32(w+84+plen)!=qikvrt_fnv1a32(w,84U+plen))return 0;
    qikvrt_sha256(w+84,plen,dg);if(memcmp(dg,w+48,32)!=0)return 0;
    metadata(w,&candidate);if(!valid(&candidate))return 0;
    memcpy(candidate.payload_sha256,dg,32);*f=candidate;
    *payload=w+84;
    return 1;
}
int qikvrt_wire_decode(const unsigned char *w,unsigned int n,qikvrt_wire_frame *f,
    unsigned char *payload,unsigned int cap) {
    const unsigned char *view; qikvrt_wire_frame candidate;
    if(!f || !qikvrt_wire_view(w,n,&candidate,&view) || candidate.payload_length>cap ||
       (candidate.payload_length && !payload))return 0;
    if(candidate.payload_length)memmove(payload,view,(unsigned int)candidate.payload_length);
    *f=candidate;return 1;
}
int qikvrt_pack_bytes(const unsigned char *m,const unsigned char *payload,unsigned int n,
    unsigned char *out,unsigned int cap,unsigned int *written) {
    qikvrt_wire_frame f;
    if(!m)return 0;
    metadata(m,&f);f.payload_length=n;
    return qikvrt_wire_encode(&f,payload,out,cap,written);
}
int qikvrt_unpack_bytes(const unsigned char *w,unsigned int n,unsigned char *m,
    unsigned char *payload,unsigned int cap) {
    qikvrt_wire_frame f;
    if(!m || !qikvrt_wire_decode(w,n,&f,payload,cap))return 0;
    memcpy(m,w,48);return 1;
}
