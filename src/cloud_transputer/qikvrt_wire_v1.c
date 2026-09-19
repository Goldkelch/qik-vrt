#include "qikvrt_wire_v1.h"
#include <string.h>
static void p16(unsigned char*p,unsigned int v){p[0]=(unsigned char)(v>>8U);p[1]=(unsigned char)v;}
static void p32(unsigned char*p,unsigned int v){p[0]=(unsigned char)(v>>24U);p[1]=(unsigned char)(v>>16U);p[2]=(unsigned char)(v>>8U);p[3]=(unsigned char)v;}
static unsigned int g16(const unsigned char*p){return ((unsigned int)p[0]<<8U)|(unsigned int)p[1];}
static unsigned int g32(const unsigned char*p){return ((unsigned int)p[0]<<24U)|((unsigned int)p[1]<<16U)|((unsigned int)p[2]<<8U)|(unsigned int)p[3];}
unsigned int qikvrt_fnv1a32(const unsigned char*d,unsigned int n){unsigned int h=2166136261U,i;for(i=0U;i<n;++i){h^=(unsigned int)d[i];h*=16777619U;}return h;}
static int valid(const qikvrt_wire_frame*f){
 if(f->direction>1U||f->type<1U||f->type>4U||f->d0>3U||f->d4>4U)return 0;
 if(f->chunk_count==0U||f->chunk_index>=f->chunk_count||f->payload_length>QIKVRT_WIRE_MAX_PAYLOAD)return 0;
 if(f->type==QIKVRT_TYPE_REQUEST&&f->direction!=QIKVRT_DIRECTION_FORWARD)return 0;
 if(f->type!=QIKVRT_TYPE_REQUEST&&f->direction!=QIKVRT_DIRECTION_REVERSE)return 0;
 return 1;
}
int qikvrt_wire_encode(const qikvrt_wire_frame*f,const unsigned char*payload,unsigned char*out,unsigned int cap,unsigned int*written){
 unsigned int total,hc,fc;unsigned char dg[32];
 if(!f||!out||!written||!valid(f)||(f->payload_length&&!payload))return 0;
 total=84U+f->payload_length+4U;if(cap<total)return 0;memset(out,0,total);
 out[0]='Q';out[1]='V';out[2]='R';out[3]='T';out[4]=1U;out[5]=f->direction;out[6]=f->type;out[7]=f->flags;out[8]=f->d0;out[9]=f->d4;p16(out+10U,84U);
 p32(out+12U,f->session_id);p32(out+16U,f->nonce);p32(out+20U,f->source_node);p32(out+24U,f->virtual_time_hi);p32(out+28U,f->virtual_time_lo);p32(out+32U,f->message_id);p32(out+36U,f->chunk_index);p32(out+40U,f->chunk_count);p32(out+44U,f->payload_length);
 qikvrt_sha256(payload,f->payload_length,dg);memcpy(out+48U,dg,32U);hc=qikvrt_fnv1a32(out,80U);p32(out+80U,hc);if(f->payload_length)memcpy(out+84U,payload,f->payload_length);fc=qikvrt_fnv1a32(out,84U+f->payload_length);p32(out+84U+f->payload_length,fc);*written=total;return 1;
}
int qikvrt_wire_decode(const unsigned char*w,unsigned int n,qikvrt_wire_frame*f,unsigned char*payload,unsigned int pcap){
 unsigned int plen,total;unsigned char dg[32];
 if(!w||!f||n<88U)return 0;
 if(w[0]!='Q'||w[1]!='V'||w[2]!='R'||w[3]!='T'||w[4]!=1U||g16(w+10U)!=84U)return 0;
 plen=g32(w+44U);if(plen>4096U)return 0;total=84U+plen+4U;if(n!=total||pcap<plen)return 0;
 if(g32(w+80U)!=qikvrt_fnv1a32(w,80U))return 0;
 if(g32(w+84U+plen)!=qikvrt_fnv1a32(w,84U+plen))return 0;
 qikvrt_sha256(w+84U,plen,dg);
 if(memcmp(dg,w+48U,32U)!=0)return 0;
 memset(f,0,sizeof(*f));f->direction=w[5];f->type=w[6];f->flags=w[7];f->d0=w[8];f->d4=w[9];f->session_id=g32(w+12U);f->nonce=g32(w+16U);f->source_node=g32(w+20U);f->virtual_time_hi=g32(w+24U);f->virtual_time_lo=g32(w+28U);f->message_id=g32(w+32U);f->chunk_index=g32(w+36U);f->chunk_count=g32(w+40U);f->payload_length=plen;memcpy(f->payload_sha256,w+48U,32U);if(!valid(f))return 0;if(plen)memcpy(payload,w+84U,plen);return 1;
}
