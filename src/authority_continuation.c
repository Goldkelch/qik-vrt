/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
#include "qikvrt/authority_continuation.h"

qikvrt_authority_state qikvrt_authority_continue(
    qikvrt_authority_state current,
    const qikvrt_authority_event *event)
{
    if (event == 0 || event->exact_head == 0) {
        return QIKVRT_AUTHORITY_STALLED;
    }
    if (event->kind != QIKVRT_AUTHORITY_EVENT_REVIEW) {
        return current;
    }
    if (event->review_approved != 0 && event->review_exact_head != 0) {
        return QIKVRT_AUTHORITY_PROGRESS;
    }
    return current;
}

const char *qikvrt_authority_state_name(qikvrt_authority_state state)
{
    switch (state) {
    case QIKVRT_AUTHORITY_WAITING_PRODUCTIVELY:
        return "WAITING_PRODUCTIVELY";
    case QIKVRT_AUTHORITY_STALLED:
        return "STALLED";
    case QIKVRT_AUTHORITY_PROGRESS:
        return "PROGRESS";
    }
    return "INVALID_AUTHORITY_STATE";
}
