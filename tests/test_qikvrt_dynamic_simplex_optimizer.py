import unittest

from tools.qikvrt_dynamic_simplex_optimizer import (
    D0_HOLD,
    D0_NOOP,
    D0_REOBSERVE,
    D0_REQUEST_AUTHORITY,
    causal_fingerprint,
    decide,
    publication_worthy,
)


def candidate(move_id, **delta):
    return {
        "id": move_id,
        "delta": delta,
        "constraints": {
            "causality_preserved": True,
            "authority_not_widened": True,
            "role_local_identity_preserved": True,
        },
    }


class DynamicSimplexOptimizerTests(unittest.TestCase):
    def test_stale_observation_reobserves_before_optimization(self):
        result = decide({"observation_stale": True, "candidates": [candidate("fix", correctness_defects=-1)]})
        self.assertEqual(result["d0"], D0_REOBSERVE)
        self.assertIsNone(result["selected_move"])

    def test_higher_priority_objective_dominates_lower_priority_gain(self):
        state = {
            "authority_bound": True,
            "candidates": [
                candidate("unsafe-fast", correctness_defects=1, deterministic_latency_or_resource_waste=-100),
                candidate("correct", correctness_defects=-1, deterministic_latency_or_resource_waste=10),
            ],
        }
        result = decide(state)
        self.assertEqual(result["d0"], D0_HOLD)
        self.assertEqual(result["selected_move"]["id"], "correct")

    def test_invariant_violating_vertex_is_not_admissible(self):
        bad = candidate("erase-mirror", activity_without_effect=-10)
        bad["constraints"]["role_local_identity_preserved"] = False
        result = decide({"authority_bound": True, "candidates": [bad]})
        self.assertEqual(result["d0"], D0_NOOP)
        self.assertIsNone(result["selected_move"])

    def test_missing_authority_is_explicit_request_authority(self):
        move = candidate("admin-effect", correctness_defects=-1)
        move["requires_authority"] = True
        result = decide({"authority_bound": False, "candidates": [move]})
        self.assertEqual(result["d0"], D0_REQUEST_AUTHORITY)
        self.assertEqual(result["selected_move"]["id"], "admin-effect")

    def test_active_work_holds_without_selecting_second_move(self):
        result = decide({
            "authority_bound": True,
            "active_work": True,
            "candidates": [candidate("one", exact_head_integrity_gap=-1), candidate("two", avoidable_complexity=-1)],
        })
        self.assertEqual(result["d0"], D0_HOLD)
        self.assertEqual(result["selected_move"]["id"], "one")

    def test_causal_fingerprint_ignores_activity_only_fields(self):
        base = {
            "binding": {"head": "abc", "tree": "def"},
            "stage_states": {"ci": "success"},
            "first_blocker": None,
            "next_effect": "review",
            "role_local_state": {"role": "Authority"},
            "run_id": 1,
            "timestamp": "t1",
            "retry_count": 1,
        }
        changed_activity = dict(base, run_id=99, timestamp="t2", retry_count=5)
        self.assertEqual(causal_fingerprint(base), causal_fingerprint(changed_activity))
        changed_cause = dict(base, next_effect="promotion")
        self.assertNotEqual(causal_fingerprint(base), causal_fingerprint(changed_cause))

    def test_publication_worthiness_requires_all_boundaries(self):
        record = {
            "novel_result_or_reusable_method": True,
            "exact_repository_provenance": True,
            "reproducible_evidence": True,
            "explicit_formal_empirical_interpretive_boundaries": True,
            "archival_package_with_checksums_and_metadata": True,
            "claim_affecting_correctness_blockers": [],
        }
        self.assertTrue(publication_worthy(record))
        record["claim_affecting_correctness_blockers"] = ["UNRESOLVED"]
        self.assertFalse(publication_worthy(record))

    def test_optimizer_never_claims_effect_or_review_authority(self):
        result = decide({"authority_bound": True, "candidates": [candidate("fix", correctness_defects=-1)]})
        self.assertFalse(result["optimizer_effect_ack"])
        self.assertFalse(result["independent_review_authority_implied"])
        self.assertFalse(result["publication_effect_implied"])


if __name__ == "__main__":
    unittest.main()
