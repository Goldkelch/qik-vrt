#ifndef QIKVRT_WIRE_V1_H
#define QIKVRT_WIRE_V1_H
#define QIKVRT_WIRE_VERSION 1U
#define QIKVRT_WIRE_HEADER_BYTES 84U
#define QIKVRT_WIRE_TRAILER_BYTES 4U
#define QIKVRT_WIRE_MAX_PAYLOAD 4096U
#define QIKVRT_WIRE_MAX_FRAME (QIKVRT_WIRE_HEADER_BYTES + QIKVRT_WIRE_MAX_PAYLOAD + QIKVRT_WIRE_TRAILER_BYTES)
#define QIKVRT_DIRECTION_FORWARD 0U
#define QIKVRT_DIRECTION_REVERSE 1U
#define QIKVRT_TYPE_REQUEST 1U
#define QIKVRT_TYPE_RESPONSE 2U
#define QIKVRT_TYPE_RECEIPT 3U
#define QIKVRT_TYPE_REOBSERVATION 4U
#define QIKVRT_D0_NOOP 0U
#define QIKVRT_D0_HOLD 1U
#define QIKVRT_D0_REOBSERVE 2U
#define QIKVRT_D0_REQUEST_AUTHORITY 3U
#define QIKVRT_D4_EFFECT_NACK 0U
#define QIKVRT_D4_EFFECT_ACK_CONTINUE 1U
#define QIKVRT_D4_EFFECT_ACK_ISOLATE 2U
#define QIKVRT_D4_EFFECT_ACK_BLOCK 3U
#define QIKVRT_D4_EFFECT_ACK_DONE 4U
typedef struct qikvrt_wire_frame_s {
 unsigned char direction,type,flags,d0,d4;
 unsigned int session_id,nonce,source_node,virtual_time_hi,virtual_time_lo;
 unsigned int message_id,chunk_index,chunk_count,payload_length;
 unsigned char payload_sha256[32];
} qikvrt_wire_frame;
unsigned int qikvrt_fnv1a32(const unsigned char *data,unsigned int length);
void qikvrt_sha256(const unsigned char *data,unsigned int length,unsigned char out[32]);
int qikvrt_wire_encode(const qikvrt_wire_frame *frame,const unsigned char *payload,unsigned char *out,unsigned int capacity,unsigned int *written);
int qikvrt_wire_decode(const unsigned char *wire,unsigned int wire_length,qikvrt_wire_frame *frame,unsigned char *payload,unsigned int payload_capacity);
#endif
