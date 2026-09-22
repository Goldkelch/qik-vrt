/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#include "qikvrt_transputer.h"
qikvrt_u32 qikvrt_get32(const unsigned char *p) {
    return ((qikvrt_u32)p[0]<<24U)|((qikvrt_u32)p[1]<<16U)|
           ((qikvrt_u32)p[2]<<8U)|(qikvrt_u32)p[3];
}
void qikvrt_put32(unsigned char *p, qikvrt_u32 v) {
    p[0]=(unsigned char)(v>>24U); p[1]=(unsigned char)(v>>16U);
    p[2]=(unsigned char)(v>>8U); p[3]=(unsigned char)v;
}
qikvrt_u32 qikvrt_boolean_lut(qikvrt_u32 a, qikvrt_u32 b, unsigned char lut) {
    return ((~a&~b)&((qikvrt_u32)0-(qikvrt_u32)(lut&1U))) |
        ((~a&b)&((qikvrt_u32)0-(qikvrt_u32)((lut>>1U)&1U))) |
        ((a&~b)&((qikvrt_u32)0-(qikvrt_u32)((lut>>2U)&1U))) |
        ((a&b)&((qikvrt_u32)0-(qikvrt_u32)((lut>>3U)&1U)));
}
qikvrt_output qikvrt_evaluate(qikvrt_input i) {
    qikvrt_output o;
    o.state=QIKVRT_HOLD;
    if(i.binding==1U && i.authority==1U && i.distinction==1U &&
       i.drift==0U && i.lut<=15U && i.requested<=QIKVRT_CONTINUE) o.state=i.requested;
    o.value_valid=(unsigned char)(o.state==QIKVRT_CONTINUE);
    o.value=o.value_valid ? qikvrt_boolean_lut(i.a,i.b,i.lut) : (qikvrt_u32)0;
    return o;
}
void qikvrt_evaluate_bytes(const unsigned char *in, unsigned char *out) {
    qikvrt_input i; qikvrt_output o;
    if(!in || !out) return;
    i.a=qikvrt_get32(in); i.b=qikvrt_get32(in+4);
    i.lut=in[8]; i.requested=in[9]; i.binding=in[10];
    i.authority=in[11]; i.distinction=in[12]; i.drift=in[13];
    o=qikvrt_evaluate(i); qikvrt_put32(out,o.value); out[4]=o.state; out[5]=o.value_valid;
}
int qikvrt_effect_to_wire(unsigned char internal, unsigned char *wire) {
    static const unsigned char map[5]={0,1,4,2,3};
    if(!wire || internal>4U) return 0;
    *wire=map[internal]; return 1;
}
int qikvrt_effect_from_wire(unsigned char wire, unsigned char *internal) {
    static const unsigned char map[5]={0,1,3,4,2};
    if(!internal || wire>4U) return 0;
    *internal=map[wire]; return 1;
}
