import json
import unittest
from pathlib import Path

from tools.qikvrt_repair_effectiveness_guard import classify


class RepairEffectivenessGuardTests(unittest.TestCase):
    def test_non_repair_is_not_closed(self):
        self.assertEqual(classify({"repair": False})["state"], "NOT_REPAIR")

    def test_verified_pr_without_promotion_binding_is_not_closed(self):
        result = classify({"repair": True, "promotion_bound": False, "effective_on_main": False, "regression_probe_success": False})
        self.assertEqual(result, {"state": "NEED_PROMOTION_BINDING", "closed": False})

    def test_verified_repair_not_on_main_is_not_closed(self):
        result = classify({"repair": True, "promotion_bound": True, "effective_on_main": False, "regression_probe_success": True})
        self.assertEqual(result, {"state": "VERIFIED_NOT_EFFECTIVE", "closed": False})

    def test_main_effect_without_probe_is_not_closed(self):
        result = classify({"repair": True, "promotion_bound": True, "effective_on_main": True, "regression_probe_success": False})
        self.assertEqual(result, {"state": "EFFECTIVE_UNPROBED", "closed": False})

    def test_only_main_effect_plus_probe_is_closed(self):
        result = classify({"repair": True, "promotion_bound": True, "effective_on_main": True, "regression_probe_success": True})
        self.assertEqual(result, {"state": "CLOSED", "closed": True})

    def test_recurrent_classes_are_registered_with_probes(self):
        policy = json.loads(Path("policy/REPAIR_EFFECTIVENESS_CLOSURE_V1.json").read_text())
        classes = policy["failure_classes"]
        self.assertIn("BOT_AUTHORED_ZERO_JOB_HEAD_FALSE_NOOP", classes)
        self.assertIn("PROMOTION_READINESS_REVIEW_STATE_MACHINE_DEADLOCK", classes)
        self.assertIn("REQUIRED_REVIEW_STATUS_FIXED_POINT_DUPLICATION", classes)
        self.assertIn("REPAIRED_FAILURE_CLASS_RECURS_BECAUSE_TRUSTED_RUNTIME_IS_STALE", classes)
        for entry in classes.values():
            self.assertTrue(entry["regression_modules"])

    def test_guard_does_not_repeat_activity_only_statuses(self):
        workflow = Path(".github/workflows/qikvrt_repair_effectiveness_guard.yml").read_text()
        self.assertGreaterEqual(workflow.count("post_status_if_changed()"), 2)
        self.assertIn("UNCHANGED_HEAD_CONTEXT_STATE", workflow)
        self.assertIn("ACTIVITY_ONLY_STATUS_WRITE_FORBIDDEN", Path("policy/REPAIR_EFFECTIVENESS_CLOSURE_V1.json").read_text())


if __name__ == "__main__":
    unittest.main()
