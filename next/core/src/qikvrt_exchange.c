/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#include "qikvrt_transputer.h"
#include <string.h>

static int route_valid(const unsigned char *p) {
    return p && memcmp(p,"QXT2",4)==0 && p[4]<=7U && p[5]<=7U &&
        p[6]>=1U && p[6]<=3U && p[7]==0U && qikvrt_get32(p+136)<=QIKVRT_MAX_MESSAGE;
}
int qikvrt_route(unsigned char *route,const unsigned char *source,
    const unsigned char *destination,const unsigned char *subject,
    unsigned char sl,unsigned char dl,unsigned char codec,const unsigned char *body,unsigned int length) {
    if(!route || !source || !destination || !subject || (length && !body) ||
       length>QIKVRT_MAX_MESSAGE || sl>7U || dl>7U || codec<1U || codec>3U)return 0;
    memcpy(route,"QXT2",4);route[4]=sl;route[5]=dl;route[6]=codec;route[7]=0;
    memcpy(route+8,source,32);memcpy(route+40,destination,32);memcpy(route+72,subject,32);
    qikvrt_sha256(body,length,route+104);qikvrt_put32(route+136,(qikvrt_u32)length);memcpy(route+140,route+104,32);return 1;
}
int qikvrt_send(const unsigned char *route,const unsigned char *body,unsigned int length,
    const qikvrt_wire_frame *key,unsigned char *workspace,unsigned int capacity,
    qikvrt_emit_fn emit,void *context) {
    unsigned char *payload,digest[32];
    unsigned int chunks,index,offset,n,written; qikvrt_wire_frame f;
    if(!route_valid(route) || !key || !workspace || !emit || (length && !body) ||
       length>QIKVRT_MAX_MESSAGE || qikvrt_get32(route+136)!=(qikvrt_u32)length ||
       capacity<QIKVRT_WIRE_MAX_FRAME)return 0;
    qikvrt_sha256(body,length,digest);if(memcmp(digest,route+104,32)!=0)return 0;
    chunks=length ? (length-1U)/QIKVRT_CHUNK_BYTES+1U : 1U;
    f=*key;f.flags=1;f.chunk_count=(qikvrt_u32)chunks;payload=workspace+84;
    for(index=0;index<chunks;++index) {
        offset=index*QIKVRT_CHUNK_BYTES;n=length-offset;
        if(n>QIKVRT_CHUNK_BYTES)n=QIKVRT_CHUNK_BYTES;
        memcpy(payload,route,QIKVRT_ROUTE_BYTES);
        if(n)memcpy(payload+QIKVRT_ROUTE_BYTES,body+offset,n);
        f.chunk_index=(qikvrt_u32)index;f.payload_length=QIKVRT_ROUTE_BYTES+n;
        if(!qikvrt_wire_encode(&f,payload,workspace,capacity,&written) ||
           !emit(context,workspace,written))return 0;
    }
    return 1;
}
int qikvrt_receiver_init(qikvrt_receiver *r,unsigned char *storage,unsigned int capacity,
    const unsigned char *source,const unsigned char *destination,const unsigned char *subject,
    unsigned char sl,unsigned char dl) {
    if(!r || !storage || !source || !destination || !subject || sl>7U || dl>7U)return 0;
    memset(r,0,sizeof(*r));r->storage=storage;r->capacity=capacity;
    memcpy(r->expected,source,32);memcpy(r->expected+32,destination,32);memcpy(r->expected+64,subject,32);
    r->source_layer=sl;r->destination_layer=dl;return 1;
}
static int same_key(const qikvrt_wire_frame *a,const qikvrt_wire_frame *b) {
    return a->session_id==b->session_id && a->nonce==b->nonce && a->source_node==b->source_node &&
        a->virtual_time_hi==b->virtual_time_hi && a->virtual_time_lo==b->virtual_time_lo &&
        a->message_id==b->message_id && a->chunk_count==b->chunk_count &&
        a->type==b->type && a->direction==b->direction && a->d0==b->d0 && a->d4==b->d4;
}
static int fail(qikvrt_receiver *r){r->failed=1;return 0;}
int qikvrt_receive(qikvrt_receiver *r,const unsigned char *wire,unsigned int n) {
    qikvrt_wire_frame f; qikvrt_u32 bit,mask;
    unsigned int total,index,offset,size,chunks; unsigned char digest[32]; const unsigned char *payload;
    if(!r || r->failed)return 0;
    if(!qikvrt_wire_view(wire,n,&f,&payload) ||
       f.flags!=1U || f.payload_length<QIKVRT_ROUTE_BYTES ||
       !route_valid(payload) || memcmp(payload+8,r->expected,96)!=0 ||
       payload[4]!=r->source_layer || payload[5]!=r->destination_layer)return fail(r);
    if(f.type==1U && memcmp(payload+104,payload+140,32)!=0)return fail(r);
    total=(unsigned int)qikvrt_get32(payload+136);
    chunks=total ? (total-1U)/QIKVRT_CHUNK_BYTES+1U : 1U;
    if(total>r->capacity || f.chunk_count!=(qikvrt_u32)chunks)return fail(r);
    index=(unsigned int)f.chunk_index;offset=index*QIKVRT_CHUNK_BYTES;size=total-offset;
    if(size>QIKVRT_CHUNK_BYTES)size=QIKVRT_CHUNK_BYTES;
    if(f.payload_length!=(qikvrt_u32)(QIKVRT_ROUTE_BYTES+size))return fail(r);
    if(!r->started) {r->key=f;memcpy(r->route,payload,QIKVRT_ROUTE_BYTES);r->started=1;r->length=total;}
    else if(!same_key(&r->key,&f) || memcmp(r->route,payload,QIKVRT_ROUTE_BYTES)!=0)return fail(r);
    bit=(qikvrt_u32)1<<index;
    if(r->seen&bit) {
        if(size && memcmp(r->storage+offset,payload+QIKVRT_ROUTE_BYTES,size)!=0)return fail(r);
        return 3;
    }
    if(size)memcpy(r->storage+offset,payload+QIKVRT_ROUTE_BYTES,size);
    r->seen|=bit;mask=((qikvrt_u32)1<<chunks)-(qikvrt_u32)1;
    if(r->seen!=mask)return 1;
    qikvrt_sha256(r->storage,total,digest);
    if(memcmp(digest,r->route+104,32)!=0)return fail(r);
    r->complete=1;return 2;
}
size_t qikvrt_receiver_size(void){return sizeof(qikvrt_receiver);}
size_t qikvrt_receiver_alignment(void) {
    struct probe {char prefix;qikvrt_receiver value;};
    return offsetof(struct probe,value);
}
unsigned int qikvrt_receiver_length(const qikvrt_receiver *r){return r && r->complete && !r->failed ? r->length : 0U;}
unsigned char qikvrt_receiver_codec(const qikvrt_receiver *r){return r && r->complete && !r->failed ? r->route[6] : 0U;}

void qikvrt_receiver_correlation(const qikvrt_receiver *r,unsigned char out[32]) {
    if(out && r && r->complete && !r->failed)memcpy(out,r->route+140,32);
}
