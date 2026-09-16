/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
#include <assert.h>
#include "qikvrt/authority_continuation.h"

int main(void)
{
    qikvrt_authority_event event;

    event.kind = QIKVRT_AUTHORITY_EVENT_OTHER;
    event.exact_head = 1;
    event.review_approved = 0;
    event.review_exact_head = 0;
    assert(qikvrt_authority_continue(
        QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY, &event)
        == QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY);

    event.kind = QIKVRT_AUTHORITY_EVENT_REVIEW;
    assert(qikvrt_authority_continue(
        QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY, &event)
        == QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY);

    event.review_approved = 1;
    event.review_exact_head = 1;
    assert(qikvrt_authority_continue(
        QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY, &event)
        == QIKVRT_AUTHORITY_PROGRESS);

    event.exact_head = 0;
    assert(qikvrt_authority_continue(
        QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY, &event)
        == QIKVRT_AUTHORITY_STALLED);

    return 0;
}
