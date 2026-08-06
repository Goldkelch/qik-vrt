# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

SPEC = importlib.util.spec_from_file_location(
    "operator_v2", TOOLS / "qikvrt_autonomous_ontology_closure_v2.py"
)
assert SPEC and SPEC.loader
operator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operator)


class AutonomousOntologyClosureV2Tests(unittest.TestCase):
    def test_contract_is_false_pass_free_and_progressing(self):
        policy, queue, status = operator.load_contract(ROOT)
        expected = {"EFFECT_ACK_DONE": False, "FINAL_PASS": False, "PASS": False}
        self.assertEqual(policy["release_claims"], expected)
        self.assertEqual(queue["release_claims"], expected)
        self.assertEqual(status["release_claims"], expected)
        self.assertEqual(status["completed_work_units"], [])
        self.assertEqual(queue["effect_state"], "EFFECT_ACK_CONTINUE")

    def test_first_unit_is_qce_discovery(self):
        result = operator.plan(ROOT)
        self.assertEqual(result["state"], "ELIGIBLE")
        self.assertEqual(
            result["work_unit"]["id"], "QCE-DISCOVERY-INDEX-CURRENT-V1"
        )

    def test_completed_unit_advances_to_qce_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for source in (
                ROOT / "policy/AUTONOMOUS_ONTOLOGY_CLOSURE_V1.json",
                ROOT / "state/ontology-autonomy/QUEUE_V2.json",
                ROOT / "state/ontology-autonomy/STATUS_V2.json",
            ):
                target = root / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            status_path = root / "state/ontology-autonomy/STATUS_V2.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["completed_work_units"] = ["QCE-DISCOVERY-INDEX-CURRENT-V1"]
            status["predecessor_results"] = {
                "QCE-DISCOVERY-INDEX-CURRENT-V1": {
                    "state": "SUCCESSOR_ALREADY_EXISTS",
                    "successor_pr": 1,
                }
            }
            status_path.write_text(
                json.dumps(status, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            result = operator.plan(root)
            self.assertEqual(result["state"], "ELIGIBLE")
            self.assertEqual(
                result["work_unit"]["id"],
                "QCE-KERNEL-RECEIPT-PERSISTENCE-CURRENT-V1",
            )

    def test_external_truth_gates_are_not_automatic(self):
        _policy, queue, _status = operator.load_contract(ROOT)
        external = {
            "EXTERNAL_SCIENCE",
            "INDEPENDENT_REPLICATION",
            "IRREVERSIBLE_EXTERNAL_EFFECT",
        }
        for unit in queue["work_units"]:
            if unit["action_class"] in external:
                self.assertFalse(unit["automatic"], unit["id"])
                self.assertIsNone(unit["handler"], unit["id"])

    def test_success_states_are_bounded_repository_results(self):
        self.assertIn("SUCCESSOR_CREATED", operator.SUCCESS_STATES)
        self.assertIn("RECEIPT_SUCCESSOR_CREATED", operator.SUCCESS_STATES)
        self.assertIn("AUDIO_REVIEW_REQUEST_CREATED", operator.SUCCESS_STATES)
        self.assertIn("UNIFIED_WORK_UNITS_CREATED", operator.SUCCESS_STATES)
        self.assertNotIn("PASS", operator.SUCCESS_STATES)
        self.assertNotIn("FINAL_PASS", operator.SUCCESS_STATES)
        self.assertNotIn("EFFECT_ACK_DONE", operator.SUCCESS_STATES)

    def test_workflow_is_serial_idempotent_and_non_merging(self):
        workflow = (
            ROOT / ".github/workflows/qikvrt_autonomous_ontology_closure_v2.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("STATUS_V2.json", workflow)
        self.assertIn("semantic", workflow.lower())
        self.assertIn("qikvrt/ontology-autonomy-state", workflow)
        self.assertNotIn("gh pr merge", workflow)
        self.assertNotIn("ZENODO_ACCESS_TOKEN", workflow)

    def test_v1_superseder_removes_the_static_executor(self):
        workflow = (
            ROOT
            / ".github/workflows/qikvrt_autonomous_ontology_closure_v1_supersede.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("qikvrt_autonomous_ontology_closure.yml", workflow)
        self.assertIn("SUPERSEDED_BY_PROGRESSING_V2", workflow)
        self.assertIn("--method DELETE", workflow)


if __name__ == "__main__":
    unittest.main()
