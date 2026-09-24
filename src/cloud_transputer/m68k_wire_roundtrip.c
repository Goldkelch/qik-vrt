#include "qikvrt_wire_v1.h"
#include <stdio.h>
#include <string.h>
static void hx(const char*n,const unsigned char*p,unsigned int z){unsigned int i;printf("%s=",n);for(i=0U;i<z;++i)printf("%02x",(unsigned int)p[i]);printf("\n");}
static int bind(const qikvrt_wire_frame*a,const qikvrt_wire_frame*b){return a->session_id==b->session_id&&a->nonce==b->nonce&&a->message_id==b->message_id&&a->chunk_index==b->chunk_index&&a->chunk_count==b->chunk_count;}
int main(void){
 static const unsigned char msg[]="SIEHWIESOBESSER!\nDefinitiv tief.\nq.e.d.\nIngolf Lohmann\n";
 unsigned char rq[QIKVRT_WIRE_MAX_FRAME],rc[QIKVRT_WIRE_MAX_FRAME],dec[QIKVRT_WIRE_MAX_PAYLOAD],state[QIKVRT_WIRE_MAX_PAYLOAD],rh[32],rp[32];
 unsigned int rqn=0U,rcn=0U,mlen=(unsigned int)(sizeof(msg)-1U);qikvrt_wire_frame q,qd,r,rd;
 memset(&q,0,sizeof(q));q.direction=0U;q.type=1U;q.d0=2U;q.d4=0U;q.session_id=0x51494b56U;q.nonce=0x20260913U;q.source_node=2U;q.virtual_time_lo=20260913U;q.message_id=1U;q.chunk_count=1U;q.payload_length=mlen;
 if(!qikvrt_wire_encode(&q,msg,rq,sizeof(rq),&rqn))return 10;
 if(!qikvrt_wire_decode(rq,rqn,&qd,dec,sizeof(dec)))return 11;
 if(qd.payload_length!=mlen||memcmp(dec,msg,mlen)!=0)return 12;
 memcpy(state,dec,mlen);if(memcmp(state,msg,mlen)!=0)return 13;qikvrt_sha256(rq,rqn,rh);memcpy(rp,rh,32U);
 memset(&r,0,sizeof(r));r.direction=1U;r.type=3U;r.d0=0U;r.d4=4U;r.session_id=qd.session_id;r.nonce=qd.nonce;r.source_node=6U;r.virtual_time_lo=qd.virtual_time_lo;r.message_id=qd.message_id;r.chunk_count=qd.chunk_count;r.payload_length=32U;
 if(!qikvrt_wire_encode(&r,rp,rc,sizeof(rc),&rcn))return 14;
 if(!qikvrt_wire_decode(rc,rcn,&rd,dec,sizeof(dec)))return 15;
 if(!bind(&qd,&rd)||rd.d4!=4U||rd.payload_length!=32U||memcmp(dec,rh,32U)!=0)return 16;
 printf("WIRE_PROTOCOL=QIKVRT_WIRE_V1\nBYTE_ORDER=BIG_ENDIAN\nREQUEST_ROUNDTRIP=PASS\nLOCAL_STATE_REOBSERVED=PASS\nRECEIPT_BINDING=PASS\nREVERSE_ROUNDTRIP=PASS\nTRANSPORT_ACK_NOT_EFFECT_ACK=TRUE\nLOCAL_REFERENCE_EFFECT_ACK_DONE=TRUE\nGENERAL_EFFECT_ACK_DONE=FALSE\n");hx("REQUEST_HEX",rq,rqn);hx("RECEIPT_HEX",rc,rcn);return 0;
}
