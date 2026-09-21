/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#include "qikvrt_transputer.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static unsigned char frames[16][QIKVRT_WIRE_MAX_FRAME];
static unsigned int lengths[16],count;
static unsigned char body[QIKVRT_MAX_MESSAGE],restored[QIKVRT_MAX_MESSAGE];
static int capture(void *unused,const unsigned char *frame,unsigned int n) {
    (void)unused;assert(count<16);memcpy(frames[count],frame,n);lengths[count++]=n;return 1;
}
static int blocked(void *unused,const unsigned char *frame,unsigned int n) {
    (void)unused;(void)frame;(void)n;return 0;
}
int main(void) {
    qikvrt_receiver rx; qikvrt_wire_frame key,decoded;
    unsigned char source[32],destination[32],subject[32],route[QIKVRT_ROUTE_BYTES],workspace[QIKVRT_WIRE_MAX_FRAME];
    unsigned char digest[32],internal,wire,payload[4096];
    unsigned int i,a,b,lut,bit,req,binding,authority,distinction,drift,n;
    qikvrt_input input; qikvrt_output output; qikvrt_u32 expected,mask;
    static const unsigned char sha_abc[32]={
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
    qikvrt_sha256((const unsigned char *)"abc",3,digest);assert(memcmp(digest,sha_abc,32)==0);
    assert(qikvrt_fnv1a32((const unsigned char *)"hello",5)==(qikvrt_u32)0x4f9f2cabUL);
    for(lut=0;lut<16;++lut)for(a=0;a<2;++a)for(b=0;b<2;++b)for(bit=0;bit<32;++bit) {
        mask=(qikvrt_u32)1<<bit;expected=(qikvrt_u32)((lut>>(2U*a+b))&1U);
        assert(((qikvrt_boolean_lut(a?mask:0,b?mask:0,(unsigned char)lut)>>bit)&1U)==expected);
    }
    memset(&input,0,sizeof(input));input.lut=6;input.a=7;input.b=3;
    for(req=0;req<4;++req)for(binding=0;binding<3;++binding)for(authority=0;authority<3;++authority)
    for(distinction=0;distinction<3;++distinction)for(drift=0;drift<3;++drift) {
        input.requested=(unsigned char)req;input.binding=(unsigned char)binding;
        input.authority=(unsigned char)authority;input.distinction=(unsigned char)distinction;input.drift=(unsigned char)drift;
        output=qikvrt_evaluate(input);expected=binding==1 && authority==1 && distinction==1 && drift==0 && req<3 ? req:1;
        assert(output.state==expected);assert(output.value_valid==(expected==2));
        assert(output.value==(expected==2?4U:0U));
    }
    for(i=0;i<5;++i){assert(qikvrt_effect_to_wire((unsigned char)i,&wire));assert(qikvrt_effect_from_wire(wire,&internal));assert(internal==i);}
    assert(qikvrt_effect_to_wire(2,&wire) && wire==4);
    assert(!qikvrt_effect_to_wire(5,&wire) && !qikvrt_effect_from_wire(255,&internal));
    for(i=0;i<sizeof(body);++i)body[i]=(unsigned char)(i%251U);
    qikvrt_sha256((const unsigned char *)"sender",6,source);qikvrt_sha256((const unsigned char *)"receiver",8,destination);
    qikvrt_sha256((const unsigned char *)"exact-subject",13,subject);
    assert(qikvrt_route(route,source,destination,subject,1,4,2,body,sizeof(body)));
    memset(&key,0,sizeof(key));key.type=1;key.session_id=8;key.nonce=9;key.message_id=10;
    assert(!qikvrt_send(route,body,sizeof(body),&key,workspace,sizeof(workspace),blocked,0));
    assert(qikvrt_send(route,body,sizeof(body),&key,workspace,sizeof(workspace),capture,0));assert(count==16);
    assert(qikvrt_receiver_init(&rx,restored,sizeof(restored),source,destination,subject,1,4));
    for(i=count;i>0;--i) {
        assert(qikvrt_receive(&rx,frames[i-1],lengths[i-1])==(i==1?2:1));
        assert(qikvrt_receive(&rx,frames[i-1],lengths[i-1])==3);
    }
    assert(qikvrt_receiver_length(&rx)==sizeof(body));assert(memcmp(body,restored,sizeof(body))==0);
    assert(qikvrt_receiver_codec(&rx)==2);
    assert(!qikvrt_wire_decode(frames[0],lengths[0],&decoded,0,4096));
    assert(qikvrt_wire_decode(frames[0],lengths[0],&decoded,payload,sizeof(payload)));
    payload[QIKVRT_ROUTE_BYTES]^=1;assert(qikvrt_wire_encode(&decoded,payload,workspace,sizeof(workspace),&n));
    assert(!qikvrt_receive(&rx,workspace,n)); /* valid frame, conflicting duplicate */
    assert(!qikvrt_receive(&rx,frames[0],lengths[0])); /* poison persists */
    assert(qikvrt_receiver_init(&rx,restored,sizeof(restored),source,destination,subject,1,4));
    assert(qikvrt_receive(&rx,workspace,n)==1);
    for(i=1;i<count-1;++i)assert(qikvrt_receive(&rx,frames[i],lengths[i])==1);
    assert(!qikvrt_receive(&rx,frames[count-1],lengths[count-1])); /* whole-message SHA rejects forged chunk */
    subject[0]^=1;
    assert(qikvrt_receiver_init(&rx,restored,sizeof(restored),source,destination,subject,1,4));
    assert(!qikvrt_receive(&rx,frames[0],lengths[0]));
    puts("PASS C90: LUT/guards, SHA/FNV, state mapping, 16 chunks, reorder/replay, forged chunk, binding, backpressure");
    return 0;
}
