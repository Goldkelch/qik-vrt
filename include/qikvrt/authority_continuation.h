/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
#ifndef QIKVRT_AUTHORITY_CONTINUATION_H
#define QIKVRT_AUTHORITY_CONTINUATION_H

typedef enum qikvrt_authority_state {
    QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY = 0,
    QIKVRT_AUTHORITY_STALLED = 1,
    QIKVRT_AUTHORITY_PROGRESS = 2
} qikvrt_authority_state;

typedef enum qikvrt_authority_event_kind {
    QIKVRT_AUTHORITY_EVENT_OTHER = 0,
    QIKVRT_AUTHORITY_EVENT_REVIEW = 1
} qikvrt_authority_event_kind;

typedef struct qikvrt_authority_event {
    qikvrt_authority_event_kind kind;
    int exact_head;
    int review_approved;
    int review_exact_head;
} qikvrt_authority_event;

qikvrt_authority_state qikvrt_authority_continue(
    qikvrt_authority_state current,
    const qikvrt_authority_event *event);

const char *qikvrt_authority_state_name(qikvrt_authority_state state);

#endif
