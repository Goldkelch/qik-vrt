import json
import tempfile
import unittest
from pathlib import Path

from tools.qikvrt_performance_measure import evaluate

ROOT = Path(__file__).resolve().parents[1]
REPAIR = ROOT / "policy/MESH_AUTONOMOUS_DETERMINISTIC_REPAIR_V1.json"
PREVENTION = ROOT / "policy/PREVENTION_MECHANISMS_V1.json"


class PreventionContractTests(unittest.TestCase):
    def test_every_failure_class_has_prevention(self):
        policy = json.loads(REPAIR.read_text(encoding="utf-8"))
        for name, spec in policy["failure_classes"].items():
            self.assertTrue(spec.get("prevention_mechanism"), name)

    def test_event_model_is_fail_closed(self):
        policy = json.loads(REPAIR.read_text(encoding="utf-8"))
        event = policy["event_model"]
        self.assertTrue(event["semantic_work_requires_authenticated_content_bound_event"])
        self.assertTrue(event["timer_only_semantic_work_forbidden"])
        self.assertTrue(event["blind_retry_forbidden"])

    def test_prevention_invariants_cover_required_guards(self):
        value = json.loads(PREVENTION.read_text(encoding="utf-8"))["invariants"]
        required = {
            "literal_exact_head_required",
            "stale_review_transfer_forbidden",
            "sibling_tip_regeneration_forbidden",
            "duplicate_event_idempotence_required",
            "event_reorder_tolerance_required",
            "event_cycle_detection_required",
            "expected_head_cas_required_for_branch_mutation",
            "integrity_manifest_sha256_required",
            "model_failure_must_not_block_deterministic_ready_work",
        }
        self.assertTrue(required.issubset(value))
        self.assertTrue(all(value[key] for key in required))

    def test_performance_gain_requires_strict_improvement(self):
        before = {"zero_job_action_required_over_24h": 4, "stale_base_over_7d": 2}
        same = {"zero_job_action_required_over_24h": 4, "stale_base_over_7d": 2}
        better = {"zero_job_action_required_over_24h": 1, "stale_base_over_7d": 1}
        self.assertEqual(evaluate(before, same)["disposition"], "HOLD")
        self.assertEqual(evaluate(before, better)["disposition"], "IMPROVEMENT_EVIDENCED")
        self.assertFalse(evaluate(before, better)["pass"])


if __name__ == "__main__":
    unittest.main()
