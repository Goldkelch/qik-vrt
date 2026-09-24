/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#include "qikvrt_bus.h"
#include "qikvrt/effect_ack.h"
#include <string.h>
unsigned char qikvrt_bus_admission(unsigned char authenticated,unsigned char policy_bound) {
    qikvrt_effect_ack_input input;unsigned char state;
    memset(&input,0,sizeof(input));input.transport_ack=1;input.input_identifier_available=1;
    input.input_digest_valid=1;input.origin_checked=authenticated==1U;
    input.context_checked=policy_bound==1U;input.integrity_failure=authenticated!=1U;
    input.connection_decision=policy_bound==1U ? QIKVRT_EFFECT_DECISION_CONTINUE:QIKVRT_EFFECT_DECISION_BLOCK;
    if(!qikvrt_effect_to_wire((unsigned char)qikvrt_effect_ack_evaluate(&input),&state))return 3U;
    return state;
}
void qikvrt_bus_init(qikvrt_bus *bus){if(bus)memset(bus,0,sizeof(*bus));}
int qikvrt_bus_bind(qikvrt_bus *bus,unsigned int slot,const unsigned char id[32]) {
    unsigned int i;
    if(!bus || !id || slot>=QIKVRT_BUS_PEERS)return 0;
    for(i=0;i<QIKVRT_BUS_PEERS;++i)if(i!=slot && bus->peers[i].present && memcmp(bus->peers[i].id,id,32)==0)return 0;
    if(bus->peers[slot].present && memcmp(bus->peers[slot].id,id,32)!=0)return 0;
    memcpy(bus->peers[slot].id,id,32);bus->peers[slot].present=1;return 1;
}
int qikvrt_bus_route(qikvrt_bus *bus,unsigned int source,const unsigned char *wire,unsigned int length,unsigned int *destination) {
    qikvrt_wire_frame f;const unsigned char *payload;qikvrt_bus_call *call=0;
    unsigned int target,i,free_slot=QIKVRT_BUS_PENDING,total,chunks,size,offset;
    unsigned int from,to;qikvrt_u32 bit,mask;unsigned char route_digest[32];
    if(!bus || !destination || source>=QIKVRT_BUS_PEERS || !bus->peers[source].present ||
       !qikvrt_wire_view(wire,length,&f,&payload) || f.flags!=1U || f.payload_length<QIKVRT_ROUTE_BYTES)return 0;
    if(memcmp(payload,"QXT2",4)!=0 || payload[4]>7U || payload[5]>7U || payload[6]<1U || payload[6]>3U || payload[7]!=0U ||
       memcmp(payload+8,bus->peers[source].id,32)!=0 || qikvrt_get32(payload+136)>QIKVRT_MAX_MESSAGE)return 0;
    for(target=0;target<QIKVRT_BUS_PEERS;++target)if(bus->peers[target].present && memcmp(payload+40,bus->peers[target].id,32)==0)break;
    if(target==QIKVRT_BUS_PEERS || target==source)return 0;
    total=(unsigned int)qikvrt_get32(payload+136);chunks=total?(total-1U)/QIKVRT_CHUNK_BYTES+1U:1U;
    if(f.chunk_count!=(qikvrt_u32)chunks)return 0;
    offset=(unsigned int)f.chunk_index*QIKVRT_CHUNK_BYTES;size=total-offset;
    if(size>QIKVRT_CHUNK_BYTES)size=QIKVRT_CHUNK_BYTES;
    if(f.payload_length!=(qikvrt_u32)(QIKVRT_ROUTE_BYTES+size))return 0;
    qikvrt_sha256(payload,QIKVRT_ROUTE_BYTES,route_digest);
    from=f.direction==0U?source:target;to=f.direction==0U?target:source;
    for(i=0;i<QIKVRT_BUS_PENDING;++i) {
        qikvrt_bus_call *p=&bus->pending[i];
        if(!p->occupied || p->completed) {if(free_slot==QIKVRT_BUS_PENDING)free_slot=i;}
        if(p->occupied && p->source==from && p->destination==to && p->session==f.session_id && p->nonce==f.nonce && p->message==f.message_id) {call=p;break;}
    }
    if(f.direction==0U) {
        if(memcmp(payload+104,payload+140,32)!=0 || f.d4!=0U)return 0;
        if(!call) {
            if(free_slot==QIKVRT_BUS_PENDING)return 0;
            call=&bus->pending[free_slot];memset(call,0,sizeof(*call));call->occupied=1;
            call->source=(unsigned char)source;call->destination=(unsigned char)target;
            call->session=f.session_id;call->nonce=f.nonce;call->message=f.message_id;
            call->request_chunks=chunks;memcpy(call->subject,payload+72,32);memcpy(call->correlation,payload+140,32);
            memcpy(call->request_route,route_digest,32);
        }
        if(call->request_chunks!=chunks || memcmp(call->request_route,route_digest,32)!=0)return 0;
    } else if(!call || call->request_seen!=(((qikvrt_u32)1<<call->request_chunks)-(qikvrt_u32)1))return 0;
    if(memcmp(call->subject,payload+72,32)!=0 || memcmp(call->correlation,payload+140,32)!=0)return 0;
    bit=(qikvrt_u32)1<<(unsigned int)f.chunk_index;mask=((qikvrt_u32)1<<chunks)-(qikvrt_u32)1;
    if(f.direction==0U)call->request_seen|=bit;
    else {
        if(call->completed && memcmp(call->reply_route,route_digest,32)!=0){call->reply_chunks=0;call->reply_seen=0;call->completed=0;}
        if(!call->reply_chunks){call->reply_chunks=chunks;memcpy(call->reply_digest,payload+104,32);memcpy(call->reply_route,route_digest,32);}
        if(call->reply_chunks!=chunks || memcmp(call->reply_route,route_digest,32)!=0)return 0;
        call->reply_seen|=bit;if(call->reply_seen==mask)call->completed=1;
    }
    *destination=target;return 1;
}
size_t qikvrt_bus_size(void){return sizeof(qikvrt_bus);}
size_t qikvrt_bus_alignment(void){struct probe{char p;qikvrt_bus value;};return offsetof(struct probe,value);}
