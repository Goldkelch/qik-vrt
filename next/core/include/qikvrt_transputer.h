/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#ifndef QIKVRT_TRANSPUTER_H
#define QIKVRT_TRANSPUTER_H
#include "qikvrt_wire_v1.h"
#include <stddef.h>

#define QIKVRT_OBSERVE 0U
#define QIKVRT_HOLD 1U
#define QIKVRT_CONTINUE 2U
#define QIKVRT_ROUTE_BYTES 172U
#define QIKVRT_CHUNK_BYTES (QIKVRT_WIRE_MAX_PAYLOAD-QIKVRT_ROUTE_BYTES)
#define QIKVRT_MAX_CHUNKS 16U
#define QIKVRT_MAX_MESSAGE (QIKVRT_MAX_CHUNKS*QIKVRT_CHUNK_BYTES)
#define QIKVRT_CODEC_COMMAND 1U
#define QIKVRT_CODEC_OBJECT 2U
#define QIKVRT_CODEC_RECEIPT 3U

typedef struct qikvrt_input_s {
    qikvrt_u32 a, b;
    unsigned char lut, requested, binding, authority, distinction, drift;
} qikvrt_input;
typedef struct qikvrt_output_s {
    qikvrt_u32 value;
    unsigned char state, value_valid;
} qikvrt_output;
qikvrt_u32 qikvrt_boolean_lut(qikvrt_u32 a, qikvrt_u32 b, unsigned char lut);
qikvrt_output qikvrt_evaluate(qikvrt_input input);
/* Stable octet ABI: input = BE32(a), BE32(b), six controls; output =
 * BE32(value), state, valid. No native struct layout crosses a language. */
void qikvrt_evaluate_bytes(const unsigned char *input, unsigned char *output);
int qikvrt_effect_to_wire(unsigned char internal, unsigned char *wire);
int qikvrt_effect_from_wire(unsigned char wire, unsigned char *internal);

/* QXT2 route inside the unchanged QVRT v1 payload. Layer IDs 0..7,
 * source/destination/exact-subject SHA256, whole-message SHA256 and size.
 * Digests identify bytes; they are NOT credentials or effect approval. */
int qikvrt_route(unsigned char *route,
    const unsigned char *source, const unsigned char *destination,
    const unsigned char *subject, unsigned char source_layer,
    unsigned char destination_layer, unsigned char codec,
    const unsigned char *body, unsigned int length);
/* A caller-owned transport callback must copy/consume a complete frame.
 * Backpressure/failure returns zero; no retry, discard, or DONE inference. */
typedef int (*qikvrt_emit_fn)(void *context, const unsigned char *frame, unsigned int length);
int qikvrt_send(const unsigned char *route,
    const unsigned char *body, unsigned int length, const qikvrt_wire_frame *key,
    unsigned char *frame_workspace, unsigned int capacity,
    qikvrt_emit_fn emit, void *context);

/* Incremental receiver. Storage belongs to its caller. One transfer at a
 * time, any chunk order; same-byte retransmission is harmless; conflicts
 * poison this receiver until the caller explicitly initializes a new one. */
typedef struct qikvrt_receiver_s {
    unsigned char expected[96], source_layer, destination_layer;
    unsigned char route[QIKVRT_ROUTE_BYTES];
    unsigned char *storage;
    unsigned int capacity, length;
    qikvrt_u32 seen;
    qikvrt_wire_frame key;
    int started, failed, complete;
} qikvrt_receiver;
int qikvrt_receiver_init(qikvrt_receiver *r, unsigned char *storage,
    unsigned int capacity, const unsigned char *source,
    const unsigned char *destination, const unsigned char *subject,
    unsigned char source_layer, unsigned char destination_layer);
/* 0=HOLD, 1=partial, 2=complete (bytes checked), 3=duplicate. Never effect ACK. */
int qikvrt_receive(qikvrt_receiver *r, const unsigned char *frame, unsigned int length);
size_t qikvrt_receiver_size(void);
size_t qikvrt_receiver_alignment(void);
unsigned int qikvrt_receiver_length(const qikvrt_receiver *r);
unsigned char qikvrt_receiver_codec(const qikvrt_receiver *r);
void qikvrt_receiver_correlation(const qikvrt_receiver *r,unsigned char out[32]);

/* Single-frame octet FFI, avoiding native header layout across languages. */
int qikvrt_pack_bytes(const unsigned char *metadata, const unsigned char *payload,
    unsigned int length, unsigned char *out, unsigned int capacity, unsigned int *written);
int qikvrt_unpack_bytes(const unsigned char *frame, unsigned int length,
    unsigned char *metadata, unsigned char *payload, unsigned int capacity);
#endif
