/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#include <stdio.h>
#include <string.h>
#include "qikvrt/effect_ack.h"

static void fill_done_input(qikvrt_effect_ack_input *input)
{
    memset(input, 0, sizeof(*input));
    input->transport_ack = 1;
    input->input_identifier_available = 1;
    input->input_digest_valid = 1;
    input->origin_checked = 1;
    input->context_checked = 1;
    input->semantics_reconstructed = 1;
    input->effect_anticipated = 1;
    input->risk_classified = 1;
    input->risk_known = 1;
    input->responsibility_assigned = 1;
    input->responsibility_owner_present = 1;
    input->connection_decided = 1;
    input->connection_decision = QIKVRT_EFFECT_DECISION_RELEASE;
    input->policy_allows_release = 1;
    input->deadline_exceeded = 0;
    input->no_open_questions = 1;
    input->no_next_required_checks = 1;
    input->required_evidence_present = 1;
    input->predecessor_invalid = 0;
    input->integrity_failure = 0;
}

int main(void)
{
    qikvrt_effect_ack_input input;
    qikvrt_effect_ack_state state;

    fill_done_input(&input);
    state = qikvrt_effect_ack_evaluate(&input);

#ifdef __m68k__
    puts("ARCH=M68000_FAMILY");
#else
    puts("ARCH=NON_M68000_BUILD");
#endif
    printf("EFFECT_ACK_STATE=%s\n", qikvrt_effect_ack_state_name(state));
    printf("ORDINARY_RELEASE=%d\n", qikvrt_effect_ack_ordinary_release(state));

    if (state != QIKVRT_EFFECT_ACK_DONE) {
        return 10;
    }
    if (!qikvrt_effect_ack_ordinary_release(state)) {
        return 11;
    }
    return 0;
}
