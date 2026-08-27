/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
#ifndef QIKVRT_QEML_RUNTIME_H
#define QIKVRT_QEML_RUNTIME_H

typedef enum qeml_status {
    QEML_PASS = 0,
    QEML_CONTINUE = 10,
    QEML_FAILURE = 20,
    QEML_HOLD = 30
} qeml_status;

typedef struct qeml_result {
    qeml_status status;
    unsigned long workers;
    const char *state;
    const char *hold_reason;
} qeml_result;

#define QEML_PROCESS_OK 0
#define QEML_PROCESS_USAGE 64

qeml_result qeml_run_workers(unsigned long count);
qeml_result qeml_run_heartbeat(int semantic_work_triggered,
                               int polling,
                               int blind_retry);
const char *qeml_status_name(qeml_status status);

#endif
