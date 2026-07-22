/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#ifndef QIKVRT_EFFECT_ACK_H
#define QIKVRT_EFFECT_ACK_H

#ifdef __cplusplus
extern "C" {
#endif

#define QIKVRT_EFFECT_ACK_STATE_COUNT 5
#define QIKVRT_EFFECT_ACK_DECISION_COUNT 5

typedef enum qikvrt_effect_ack_state {
    QIKVRT_EFFECT_NACK = 0,
    QIKVRT_EFFECT_ACK_CONTINUE = 1,
    QIKVRT_EFFECT_ACK_DONE = 2,
    QIKVRT_EFFECT_ACK_ISOLATE = 3,
    QIKVRT_EFFECT_ACK_BLOCK = 4
} qikvrt_effect_ack_state;

typedef enum qikvrt_effect_ack_decision {
    QIKVRT_EFFECT_DECISION_UNDECIDED = 0,
    QIKVRT_EFFECT_DECISION_CONTINUE = 1,
    QIKVRT_EFFECT_DECISION_RELEASE = 2,
    QIKVRT_EFFECT_DECISION_ISOLATE = 3,
    QIKVRT_EFFECT_DECISION_BLOCK = 4
} qikvrt_effect_ack_decision;

/*
 * This structure is a verified decision snapshot, not a wire decoder.
 * Integrations remain responsible for authentication, freshness, bounds,
 * policy/evidence validation and complete mediation of the protected effect.
 */
typedef struct qikvrt_effect_ack_input {
    int transport_ack;
    int input_identifier_available;
    int input_digest_valid;
    int origin_checked;
    int context_checked;
    int semantics_reconstructed;
    int effect_anticipated;
    int risk_classified;
    int risk_known;
    int responsibility_assigned;
    int responsibility_owner_present;
    int connection_decided;
    qikvrt_effect_ack_decision connection_decision;
    int policy_allows_release;
    int deadline_exceeded;
    int no_open_questions;
    int no_next_required_checks;
    int required_evidence_present;

    int predecessor_invalid;
    int integrity_failure;
} qikvrt_effect_ack_input;

int qikvrt_effect_ack_effect_checkable(
    const qikvrt_effect_ack_input *input);

int qikvrt_effect_ack_core_done(const qikvrt_effect_ack_input *input);

qikvrt_effect_ack_state qikvrt_effect_ack_evaluate(
    const qikvrt_effect_ack_input *input);

int qikvrt_effect_ack_ordinary_release(qikvrt_effect_ack_state state);

const char *qikvrt_effect_ack_state_name(qikvrt_effect_ack_state state);

#ifdef __cplusplus
}
#endif

#endif
