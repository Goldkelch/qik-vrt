from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qikvrt_requirement_closure", ROOT / "tools/qikvrt_requirement_closure.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequirementClosureTests(unittest.TestCase):
    def test_closed_inventory(self):
        result = MODULE.evaluate({"items": [{"stable_id": "REQ-1", "class": "REQUIREMENT", "current_state": "CLOSED_VERIFIED"}]})
        self.assertEqual(result["status"], "CLOSED")

    def test_active_remainder_is_visible(self):
        item = {
            "stable_id": "REQ-2",
            "class": "REQUIREMENT",
            "source_ref": "issue:#2",
            "current_state": "ACTIVE_REMAINDER",
            "first_deterministic_blocker": "REVIEW_REQUIRED",
            "next_history_preserving_action": "obtain independent review",
            "evidence_refs": ["pr:#2"],
        }
        result = MODULE.evaluate({"items": [item]})
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["active_remainder_count"], 1)
        self.assertEqual(result["first_deterministic_blocker"], "REVIEW_REQUIRED")

    def test_silent_or_unknown_state_is_violation(self):
        result = MODULE.evaluate({"items": [{"stable_id": "DEF-1", "class": "KNOWN_DEFECT", "current_state": "SILENT_OPEN"}]})
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["violation_count"], 1)
        self.assertEqual(result["first_deterministic_blocker"], "UNKNOWN_OR_FORBIDDEN_DISPOSITION")

    def test_repair_cannot_close_before_target_observation(self):
        result = MODULE.evaluate({"items": [{"stable_id": "FIX-684", "class": "REPAIR_CANDIDATE", "current_state": "CLOSED_VERIFIED"}]})
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["first_deterministic_blocker"], "REPAIR_CLOSED_WITHOUT_EFFECTIVE_TARGET_OBSERVATION")


if __name__ == "__main__":
    unittest.main()
