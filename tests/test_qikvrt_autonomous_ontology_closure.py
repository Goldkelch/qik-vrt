# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "operator", ROOT / "tools/qikvrt_autonomous_ontology_closure.py"
)
assert SPEC and SPEC.loader
operator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operator)


class AutonomousOntologyClosureTests(unittest.TestCase):
    def test_repository_contract_is_valid_and_false_pass_free(self):
        policy, queue, status = operator.validate_contract(ROOT)
        expected = {"EFFECT_ACK_DONE": False, "FINAL_PASS": False, "PASS": False}
        self.assertEqual(queue["release_claims"], expected)
        self.assertEqual(status["release_claims"], expected)
        self.assertEqual(policy["effect_state"], "EFFECT_ACK_CONTINUE")

    def test_external_truth_gates_are_never_automatic(self):
        _policy, queue, _status = operator.validate_contract(ROOT)
        blocked = {
            "EXTERNAL_SCIENCE",
            "INDEPENDENT_REPLICATION",
            "IRREVERSIBLE_EXTERNAL_EFFECT",
        }
        for unit in queue["work_units"]:
            if unit["action_class"] in blocked:
                self.assertFalse(unit["automatic"], unit["id"])
                self.assertIsNone(unit["handler"], unit["id"])

    def test_first_deterministic_work_unit_is_qce_discovery(self):
        result = operator.plan(ROOT)
        self.assertEqual(result["state"], "ELIGIBLE")
        self.assertEqual(
            result["work_unit"]["id"], "QCE-DISCOVERY-INDEX-CURRENT-V1"
        )

    def test_workflow_is_api_bound_bounded_and_non_merging(self):
        text = (
            ROOT / ".github/workflows/qikvrt_autonomous_ontology_closure.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("contents: write", text)
        self.assertIn("pull-requests: write", text)
        self.assertIn("actions: read", text)
        self.assertIn("one-work-unit", text)
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("merge_pull_request", text)
        self.assertNotIn("ZENODO_ACCESS_TOKEN", text)

    def test_policy_forbids_false_empirical_and_human_evidence(self):
        policy = json.loads(
            (ROOT / "policy/AUTONOMOUS_ONTOLOGY_CLOSURE_V1.json").read_text(
                encoding="utf-8"
            )
        )
        forbidden = set(policy["forbidden_actions"])
        self.assertIn("FABRICATED_EMPIRICAL_EVIDENCE", forbidden)
        self.assertIn("AUTOMATIC_HUMAN_CERTIFICATION", forbidden)
        self.assertIn("FORCE_PUSH", forbidden)


if __name__ == "__main__":
    unittest.main()
