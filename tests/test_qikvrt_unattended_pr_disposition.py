# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import unittest

from tools.qikvrt_unattended_pr_disposition import DISPOSITIONS, classify


HEAD = "a" * 40
MAIN = "b" * 40


def observation(**overrides):
    value = {
        "repository": "Goldkelch/qik-vrt",
        "pull_request": 929,
        "head_sha": HEAD,
        "base_sha": MAIN,
        "current_main_sha": MAIN,
        "state": "open",
        "merged": False,
        "superseded": False,
        "active_workflows": 0,
        "failed_workflows": 0,
        "gates_complete": True,
        "review_required": True,
        "review_satisfied": True,
        "external_effect_pending": False,
        "first_causal_blocker": None,
    }
    value.update(overrides)
    return value


class UnattendedPrDispositionTests(unittest.TestCase):
    def test_state_set_matches_canonical_backlog(self):
        self.assertEqual(
            DISPOSITIONS,
            {
                "ACTIVE_EXECUTION",
                "READY_FOR_INDEPENDENT_REVIEW",
                "HOLD_WITH_FIRST_CAUSAL_BLOCKER",
                "REBIND_REQUIRED",
                "MERGE_READY",
                "EXTERNAL_EFFECT_PENDING",
                "CLOSE_AS_SUPERSEDED",
                "MERGED",
                "CLOSED_NOT_PLANNED_WITH_CAUSE",
            },
        )

    def test_merged_is_terminal(self):
        result = classify(observation(state="closed", merged=True))
        self.assertEqual(result.disposition, "MERGED")
        self.assertEqual(result.next_action, "NOOP")

    def test_closed_without_merge_preserves_cause(self):
        result = classify(
            observation(
                state="closed",
                first_causal_blocker="NOT_PLANNED",
            )
        )
        self.assertEqual(result.disposition, "CLOSED_NOT_PLANNED_WITH_CAUSE")
        self.assertEqual(result.first_causal_blocker, "NOT_PLANNED")

    def test_supersession_precedes_execution(self):
        result = classify(observation(superseded=True, active_workflows=2))
        self.assertEqual(result.disposition, "CLOSE_AS_SUPERSEDED")

    def test_base_drift_precedes_downstream_gate_state(self):
        result = classify(
            observation(
                base_sha="c" * 40,
                active_workflows=3,
                failed_workflows=1,
                first_causal_blocker="DOWNSTREAM",
            )
        )
        self.assertEqual(result.disposition, "REBIND_REQUIRED")
        self.assertEqual(result.first_causal_blocker, "BASE_DRIFT")
        self.assertEqual(
            result.next_action,
            "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
        )

    def test_active_execution_precedes_review(self):
        result = classify(
            observation(active_workflows=1, review_satisfied=False)
        )
        self.assertEqual(result.disposition, "ACTIVE_EXECUTION")

    def test_explicit_first_blocker_is_preserved(self):
        result = classify(
            observation(first_causal_blocker="CODE_OWNER_RULE_NOT_ENFORCED")
        )
        self.assertEqual(result.disposition, "HOLD_WITH_FIRST_CAUSAL_BLOCKER")
        self.assertEqual(
            result.first_causal_blocker,
            "CODE_OWNER_RULE_NOT_ENFORCED",
        )

    def test_failed_gate_fails_closed(self):
        result = classify(observation(failed_workflows=1))
        self.assertEqual(result.disposition, "HOLD_WITH_FIRST_CAUSAL_BLOCKER")
        self.assertEqual(result.first_causal_blocker, "EXACT_HEAD_GATE_FAILURE")

    def test_incomplete_evidence_cannot_be_merge_ready(self):
        result = classify(observation(gates_complete=False))
        self.assertEqual(result.disposition, "HOLD_WITH_FIRST_CAUSAL_BLOCKER")
        self.assertEqual(result.first_causal_blocker, "EXACT_HEAD_EVIDENCE_INCOMPLETE")

    def test_review_boundary_is_explicit(self):
        result = classify(observation(review_satisfied=False))
        self.assertEqual(result.disposition, "READY_FOR_INDEPENDENT_REVIEW")

    def test_external_effect_boundary_follows_internal_convergence(self):
        result = classify(observation(external_effect_pending=True))
        self.assertEqual(result.disposition, "EXTERNAL_EFFECT_PENDING")

    def test_merge_ready_requires_complete_internal_evidence(self):
        result = classify(observation())
        self.assertEqual(result.disposition, "MERGE_READY")
        value = result.to_mapping()
        self.assertFalse(value["PASS"])
        self.assertFalse(value["FINAL_PASS"])
        self.assertFalse(value["EFFECT_ACK_DONE"])

    def test_missing_required_evidence_is_rejected(self):
        candidate = observation()
        del candidate["gates_complete"]
        with self.assertRaises(ValueError):
            classify(candidate)

    def test_inconsistent_merged_open_state_is_rejected(self):
        with self.assertRaises(ValueError):
            classify(observation(merged=True))


if __name__ == "__main__":
    unittest.main()
