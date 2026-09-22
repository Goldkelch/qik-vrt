/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Draft03 finite snapshot carrier. */
#include "qikvrt/effect_ack.h"
static int bit(unsigned long m, unsigned int n)
{
    return (m & (1UL << n)) != 0UL;
}
unsigned long full_core(unsigned long m, unsigned long r, unsigned long d)
{
    qikvrt_effect_ack_input x;
    /* Rejection is outside the five protocol states. */
    if (r >= 5UL || d >= 5UL) return 5UL;
    x.transport_ack = bit(m, 0);
    x.input_identifier_available = bit(m, 1);
    x.input_digest_valid = bit(m, 2);
    x.origin_checked = bit(m, 3);
    x.context_checked = bit(m, 4);
    x.semantics_reconstructed = bit(m, 5);
    x.effect_anticipated = bit(m, 6);
    x.risk_classified = bit(m, 7);
    x.risk_known = r != 0UL;
    x.responsibility_assigned = bit(m, 8);
    x.responsibility_owner_present = bit(m, 9);
    x.connection_decided = bit(m, 10);
    x.connection_decision = (qikvrt_effect_ack_decision)d;
    x.policy_allows_release = bit(m, 11);
    x.deadline_exceeded = bit(m, 12);
    x.no_open_questions = bit(m, 13);
    x.no_next_required_checks = bit(m, 14);
    x.required_evidence_present = bit(m, 15);
    x.predecessor_invalid = bit(m, 16);
    x.integrity_failure = bit(m, 17);
    return (unsigned long)qikvrt_effect_ack_evaluate(&x);
}
unsigned long full_admit(unsigned long derived, unsigned long declared,
                         unsigned long m)
{
    return derived == 2UL && declared == 2UL && m == 511UL ? 1UL : 0UL;
}
