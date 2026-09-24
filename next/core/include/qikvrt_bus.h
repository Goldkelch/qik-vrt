/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#ifndef QIKVRT_BUS_H
#define QIKVRT_BUS_H
#include "qikvrt_transputer.h"
#define QIKVRT_BUS_PEERS 16U
#define QIKVRT_BUS_PENDING 32U
typedef struct qikvrt_bus_peer_s {unsigned char id[32];int present;} qikvrt_bus_peer;
typedef struct qikvrt_bus_call_s {
    unsigned char source,destination,subject[32],correlation[32],reply_digest[32];
    unsigned char request_route[32],reply_route[32];
    qikvrt_u32 session,nonce,message,request_seen,reply_seen;
    unsigned int request_chunks,reply_chunks;
    int occupied,completed;
} qikvrt_bus_call;
typedef struct qikvrt_bus_s {
    qikvrt_bus_peer peers[QIKVRT_BUS_PEERS];
    qikvrt_bus_call pending[QIKVRT_BUS_PENDING];
} qikvrt_bus;
/* Uses the existing Draft03 C90 decision core, mapped explicitly to wire D4.
 * Admission is CONTINUE for bounded bus participation, never ordinary release. */
unsigned char qikvrt_bus_admission(unsigned char authenticated,unsigned char policy_bound);
void qikvrt_bus_init(qikvrt_bus *bus);
int qikvrt_bus_bind(qikvrt_bus *bus,unsigned int slot,const unsigned char id[32]);
/* Validate and advance the bounded routing/correlation state. Input identity
 * comes from an authenticated transport adapter or a verified durable replay.
 * The caller persists accepted frames before forwarding. 0 means HOLD;
 * neither 1 nor a forwarded peer's D4 state authorizes any local effect. */
int qikvrt_bus_route(qikvrt_bus *bus,unsigned int source,const unsigned char *frame,
    unsigned int length,unsigned int *destination);
size_t qikvrt_bus_size(void);
size_t qikvrt_bus_alignment(void);
#endif
