/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

#include <stdio.h>
#include <string.h>

#include "qikvrt/effect_ack.h"

static int failures = 0;
static int checks = 0;

static void expect_true(int condition, const char *message)
{
    checks += 1;
    if (!condition) {
        failures += 1;
        (void)fprintf(stderr, "FAIL: %s\n", message);
    }
}

static void expect_state(
    qikvrt_effect_ack_state actual,
    qikvrt_effect_ack_state expected,
    const char *message)
{
    checks += 1;
    if (actual != expected) {
        failures += 1;
        (void)fprintf(
            stderr,
            "FAIL: %s (expected %s, got %s)\n",
            message,
            qikvrt_effect_ack_state_name(expected),
            qikvrt_effect_ack_state_name(actual));
    }
}

static qikvrt_effect_ack_input complete_input(void)
{
    qikvrt_effect_ack_input input;

    (void)memset(&input, 0, sizeof(input));
    input.transport_ack = 1;
    input.input_identifier_available = 1;
    input.input_digest_valid = 1;
    input.origin_checked = 1;
    input.context_checked = 1;
    input.semantics_reconstructed = 1;
    input.effect_anticipated = 1;
    input.risk_classified = 1;
    input.risk_known = 1;
    input.responsibility_assigned = 1;
    input.responsibility_owner_present = 1;
    input.connection_decided = 1;
    input.connection_decision = QIKVRT_EFFECT_DECISION_RELEASE;
    input.policy_allows_release = 1;
    input.deadline_exceeded = 0;
    input.no_open_questions = 1;
    input.no_next_required_checks = 1;
    input.required_evidence_present = 1;
    input.predecessor_invalid = 0;
    input.integrity_failure = 0;
    return input;
}

/*
 * Deliberately restate CoreDone instead of calling the implementation under
 * test.  This keeps the exhaustive state oracle independent of the production
 * predicate and makes a shared omission observable.
 */
static int expected_core_done_oracle(
    const qikvrt_effect_ack_input *input)
{
    return input->transport_ack != 0
        && input->input_digest_valid != 0
        && input->origin_checked != 0
        && input->context_checked != 0
        && input->semantics_reconstructed != 0
        && input->effect_anticipated != 0
        && input->risk_classified != 0
        && input->risk_known != 0
        && input->responsibility_assigned != 0
        && input->responsibility_owner_present != 0
        && input->connection_decided != 0
        && input->connection_decision == QIKVRT_EFFECT_DECISION_RELEASE
        && input->policy_allows_release != 0
        && input->deadline_exceeded == 0
        && input->no_open_questions != 0
        && input->no_next_required_checks != 0
        && input->required_evidence_present != 0;
}

static qikvrt_effect_ack_state expected_state_oracle(
    const qikvrt_effect_ack_input *input)
{
    if (input->predecessor_invalid != 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }
    if (input->deadline_exceeded != 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }
    if (input->input_identifier_available == 0
            || input->input_digest_valid == 0) {
        return QIKVRT_EFFECT_NACK;
    }
    if (input->integrity_failure != 0) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }
    if (input->connection_decision == QIKVRT_EFFECT_DECISION_BLOCK) {
        return QIKVRT_EFFECT_ACK_BLOCK;
    }
    if (input->connection_decision == QIKVRT_EFFECT_DECISION_ISOLATE) {
        return QIKVRT_EFFECT_ACK_ISOLATE;
    }
    if (input->connection_decision == QIKVRT_EFFECT_DECISION_RELEASE
            && expected_core_done_oracle(input)) {
        return QIKVRT_EFFECT_ACK_DONE;
    }
    return QIKVRT_EFFECT_ACK_CONTINUE;
}

static qikvrt_effect_ack_input input_from_mask(
    unsigned long mask,
    qikvrt_effect_ack_decision decision)
{
    qikvrt_effect_ack_input input;

    (void)memset(&input, 0, sizeof(input));
    input.transport_ack = (mask & (1UL << 0)) != 0UL;
    input.input_identifier_available = (mask & (1UL << 1)) != 0UL;
    input.input_digest_valid = (mask & (1UL << 2)) != 0UL;
    input.origin_checked = (mask & (1UL << 3)) != 0UL;
    input.context_checked = (mask & (1UL << 4)) != 0UL;
    input.semantics_reconstructed = (mask & (1UL << 5)) != 0UL;
    input.effect_anticipated = (mask & (1UL << 6)) != 0UL;
    input.risk_classified = (mask & (1UL << 7)) != 0UL;
    input.risk_known = (mask & (1UL << 8)) != 0UL;
    input.responsibility_assigned = (mask & (1UL << 9)) != 0UL;
    input.responsibility_owner_present = (mask & (1UL << 10)) != 0UL;
    input.connection_decided = (mask & (1UL << 11)) != 0UL;
    input.policy_allows_release = (mask & (1UL << 12)) != 0UL;
    input.deadline_exceeded = (mask & (1UL << 13)) != 0UL;
    input.no_open_questions = (mask & (1UL << 14)) != 0UL;
    input.no_next_required_checks = (mask & (1UL << 15)) != 0UL;
    input.required_evidence_present = (mask & (1UL << 16)) != 0UL;
    input.predecessor_invalid = (mask & (1UL << 17)) != 0UL;
    input.integrity_failure = (mask & (1UL << 18)) != 0UL;
    input.connection_decision = decision;
    return input;
}

static void test_closed_state_set_and_names(void)
{
    const char *expected[QIKVRT_EFFECT_ACK_STATE_COUNT];
    int index;

    expected[0] = "EFFECT_NACK";
    expected[1] = "EFFECT_ACK_CONTINUE";
    expected[2] = "EFFECT_ACK_DONE";
    expected[3] = "EFFECT_ACK_ISOLATE";
    expected[4] = "EFFECT_ACK_BLOCK";

    expect_true(QIKVRT_EFFECT_ACK_STATE_COUNT == 5, "exactly five states");
    for (index = 0; index < QIKVRT_EFFECT_ACK_STATE_COUNT; index += 1) {
        expect_true(
            strcmp(
                qikvrt_effect_ack_state_name(
                    (qikvrt_effect_ack_state)index),
                expected[index]) == 0,
            "state has the normative name");
    }
    expect_true(
        strcmp(
            qikvrt_effect_ack_state_name((qikvrt_effect_ack_state)99),
            "INVALID_EFFECT_ACK_STATE") == 0,
        "unknown state is not mapped into the closed set");
}

static void test_effect_checkable_truth_table(void)
{
    qikvrt_effect_ack_input input;

    input = complete_input();
    input.input_identifier_available = 0;
    input.input_digest_valid = 0;
    expect_true(
        !qikvrt_effect_ack_effect_checkable(&input),
        "missing identifier and digest is not effect-checkable");

    input.input_identifier_available = 1;
    expect_true(
        !qikvrt_effect_ack_effect_checkable(&input),
        "identifier alone is not effect-checkable");

    input.input_identifier_available = 0;
    input.input_digest_valid = 1;
    expect_true(
        !qikvrt_effect_ack_effect_checkable(&input),
        "digest alone is not effect-checkable");

    input.input_identifier_available = 1;
    expect_true(
        qikvrt_effect_ack_effect_checkable(&input),
        "identifier and digest are effect-checkable without transport ACK");
    expect_true(
        !qikvrt_effect_ack_effect_checkable(0),
        "null snapshot is not effect-checkable");
}

static void test_each_done_conjunct(void)
{
    qikvrt_effect_ack_input input;
    int index;

    input = complete_input();
    expect_true(qikvrt_effect_ack_core_done(&input), "all 17 DONE gates pass");
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_DONE,
        "all 17 DONE gates select DONE");

    for (index = 0; index < 17; index += 1) {
        input = complete_input();
        switch (index) {
        case 0:
            input.transport_ack = 0;
            break;
        case 1:
            input.input_digest_valid = 0;
            break;
        case 2:
            input.origin_checked = 0;
            break;
        case 3:
            input.context_checked = 0;
            break;
        case 4:
            input.semantics_reconstructed = 0;
            break;
        case 5:
            input.effect_anticipated = 0;
            break;
        case 6:
            input.risk_classified = 0;
            break;
        case 7:
            input.risk_known = 0;
            break;
        case 8:
            input.responsibility_assigned = 0;
            break;
        case 9:
            input.responsibility_owner_present = 0;
            break;
        case 10:
            input.connection_decided = 0;
            break;
        case 11:
            input.connection_decision = QIKVRT_EFFECT_DECISION_CONTINUE;
            break;
        case 12:
            input.policy_allows_release = 0;
            break;
        case 13:
            input.deadline_exceeded = 1;
            break;
        case 14:
            input.no_open_questions = 0;
            break;
        case 15:
            input.no_next_required_checks = 0;
            break;
        case 16:
            input.required_evidence_present = 0;
            break;
        }
        expect_true(
            !qikvrt_effect_ack_core_done(&input),
            "each individual DONE gate is necessary");
        expect_true(
            !qikvrt_effect_ack_ordinary_release(
                qikvrt_effect_ack_evaluate(&input)),
            "a failed DONE gate never permits ordinary release");
    }
    expect_true(!qikvrt_effect_ack_core_done(0), "null snapshot is not DONE");
}

static void test_priority_order(void)
{
    qikvrt_effect_ack_input input;

    input = complete_input();
    input.input_identifier_available = 0;
    input.input_digest_valid = 0;
    input.predecessor_invalid = 1;
    input.connection_decision = QIKVRT_EFFECT_DECISION_ISOLATE;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_BLOCK,
        "predecessor BLOCK precedes NACK and ISOLATE");

    input = complete_input();
    input.input_identifier_available = 0;
    input.deadline_exceeded = 1;
    input.connection_decision = QIKVRT_EFFECT_DECISION_ISOLATE;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_BLOCK,
        "deadline BLOCK precedes NACK and ISOLATE");

    input = complete_input();
    input.input_identifier_available = 0;
    input.connection_decision = QIKVRT_EFFECT_DECISION_ISOLATE;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_NACK,
        "NACK dominates ISOLATE");

    input = complete_input();
    input.connection_decision = QIKVRT_EFFECT_DECISION_ISOLATE;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_ISOLATE,
        "ISOLATE dominates release eligibility");

    input = complete_input();
    input.connection_decision = QIKVRT_EFFECT_DECISION_CONTINUE;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_CONTINUE,
        "CONTINUE dominates DONE when release was not selected");

    input = complete_input();
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_DONE,
        "DONE is selected only after all higher-priority states are absent");

    input = complete_input();
    input.integrity_failure = 1;
    input.input_identifier_available = 0;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_NACK,
        "NACK precedes local integrity BLOCK");

    input = complete_input();
    input.input_identifier_available = 0;
    input.connection_decision = QIKVRT_EFFECT_DECISION_BLOCK;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_NACK,
        "NACK precedes explicit BLOCK");

    input = complete_input();
    input.integrity_failure = 1;
    input.connection_decision = QIKVRT_EFFECT_DECISION_ISOLATE;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_BLOCK,
        "integrity BLOCK precedes explicit ISOLATE");

    input = complete_input();
    input.connection_decision = QIKVRT_EFFECT_DECISION_BLOCK;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_BLOCK,
        "explicit BLOCK prevents otherwise complete release");

    input = complete_input();
    input.connection_decision = (qikvrt_effect_ack_decision)99;
    expect_state(
        qikvrt_effect_ack_evaluate(&input),
        QIKVRT_EFFECT_ACK_BLOCK,
        "unknown decision fails closed to BLOCK");

    expect_state(
        qikvrt_effect_ack_evaluate(0),
        QIKVRT_EFFECT_ACK_BLOCK,
        "null snapshot fails closed to BLOCK");
}

static void test_exhaustive_state_selection(void)
{
    unsigned long mask;
    unsigned long limit;
    int decision;

    limit = 1UL << 19;
    for (mask = 0UL; mask < limit; mask += 1UL) {
        for (decision = 0;
                decision < QIKVRT_EFFECT_ACK_DECISION_COUNT;
                decision += 1) {
            qikvrt_effect_ack_input input;
            qikvrt_effect_ack_state actual;
            qikvrt_effect_ack_state expected;

            input = input_from_mask(
                mask,
                (qikvrt_effect_ack_decision)decision);
            actual = qikvrt_effect_ack_evaluate(&input);
            expected = expected_state_oracle(&input);
            expect_state(
                actual,
                expected,
                "exhaustive state agrees with first-match oracle");
            expect_true(
                actual >= QIKVRT_EFFECT_NACK
                    && actual <= QIKVRT_EFFECT_ACK_BLOCK,
                "exhaustive outcome belongs to the closed state set");
            expect_true(
                qikvrt_effect_ack_ordinary_release(actual)
                    == (actual == QIKVRT_EFFECT_ACK_DONE),
                "exhaustive ordinary release is equivalent to DONE");
            if (failures != 0) {
                return;
            }
        }
    }
}

static void test_done_only_release(void)
{
    int index;

    for (index = 0; index < QIKVRT_EFFECT_ACK_STATE_COUNT; index += 1) {
        expect_true(
            qikvrt_effect_ack_ordinary_release(
                (qikvrt_effect_ack_state)index)
                == (index == (int)QIKVRT_EFFECT_ACK_DONE),
            "ordinary release is true exactly for DONE");
    }
    expect_true(
        !qikvrt_effect_ack_ordinary_release((qikvrt_effect_ack_state)99),
        "unknown state never permits ordinary release");
}

int main(void)
{
    test_closed_state_set_and_names();
    test_effect_checkable_truth_table();
    test_each_done_conjunct();
    test_priority_order();
    test_exhaustive_state_selection();
    test_done_only_release();

    if (failures != 0) {
        (void)fprintf(
            stderr,
            "EFFECT_ACK C90 core: %d of %d checks failed\n",
            failures,
            checks);
        return 1;
    }

    (void)printf("EFFECT_ACK C90 core: PASS (%d checks)\n", checks);
    return 0;
}
