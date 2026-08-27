/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
#include "qeml_runtime.h"

static qeml_result qeml_make_result(qeml_status status,
                                    unsigned long workers,
                                    const char *state,
                                    const char *hold_reason)
{
    qeml_result result;
    result.status = status;
    result.workers = workers;
    result.state = state;
    result.hold_reason = hold_reason;
    return result;
}

qeml_result qeml_run_workers(unsigned long count)
{
    if (count > 8UL) {
        return qeml_make_result(QEML_HOLD, 8UL, "NULL",
                                "worker_limit_exceeded");
    }
    if (count == 0UL) {
        return qeml_make_result(QEML_CONTINUE, 0UL, "NULL", "");
    }
    return qeml_make_result(QEML_PASS, count, "ERGEBNIS", "");
}

qeml_result qeml_run_heartbeat(int semantic_work_triggered,
                               int polling,
                               int blind_retry)
{
    if (semantic_work_triggered || polling || blind_retry) {
        return qeml_make_result(QEML_HOLD, 0UL, "NULL",
                                "heartbeat_semantic_violation");
    }
    return qeml_make_result(QEML_CONTINUE, 0UL, "NULL", "");
}

const char *qeml_status_name(qeml_status status)
{
    switch (status) {
    case QEML_PASS:
        return "PASS";
    case QEML_CONTINUE:
        return "CONTINUE";
    case QEML_FAILURE:
        return "FAILURE";
    case QEML_HOLD:
        return "HOLD";
    default:
        return "UNKNOWN";
    }
}
