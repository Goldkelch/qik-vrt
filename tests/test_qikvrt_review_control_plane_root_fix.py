# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import copy
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qikvrt_requested_review_executor_root_fix", ROOT / "tools/qikvrt_requested_review_executor.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

class RequestedReviewControlPlaneRootFixTests(unittest.TestCase):
    def test_main_tip_is_progress_not_historical_identity(self):
        receipt = {
            "repository":"example/qik-vrt", "pr_number":1016, "base_ref":"main",
            "base_sha":"a"*40, "base_tree_sha":"b"*40, "head_sha":"c"*40,
            "tree_sha":"d"*40, "scope_sha256":"e"*64, "diff_sha256":"f"*64,
            "current_main_sha":"1"*40, "current_main_tree_sha":"2"*40,
            "state":"APPROVE", "mesh_disposition":"APPROVE", "first_blocker":None,
            "detail":"old", "evidence_fingerprint":"3"*64, "receipt_payload_sha256":"4"*64,
        }
        successor = copy.deepcopy(receipt)
        successor.update(current_main_sha="5"*40, current_main_tree_sha="6"*40,
                         state="COMMENT_WITH_BLOCKER", mesh_disposition="COMMENT_WITH_BLOCKER",
                         first_blocker="BASE_DRIFT", detail="main advanced",
                         evidence_fingerprint="7"*64, receipt_payload_sha256="8"*64)
        self.assertEqual(MODULE._historical_receipt_binding(receipt), MODULE._historical_receipt_binding(successor))

    def test_executor_uses_only_native_event_ingress_and_never_synthesizes_a_successor(self):
        text=(ROOT/".github/workflows/qikvrt_requested_review_executor.yml").read_text()
        self.assertIn("pull_request_target:", text)
        self.assertIn("pull_request_review:", text)
        self.assertIn("pull_request_review_comment:", text)
        self.assertIn("EXACT_EVENT_SUCCESSOR_REOBSERVATION_REQUIRED_", text)
        self.assertNotIn("workflow_dispatch:", text)
        self.assertNotIn("review_queue_intent", text)
        self.assertNotIn("review_queue_ack", text)
        self.assertNotIn("SUBJECT_PR_NUMBER:", text)
        self.assertNotIn("SUBJECT_HEAD_SHA:", text)

    def test_transport_does_not_bind_moving_base_tip(self):
        core=(ROOT/"tools/qikvrt_requested_review_executor.py").read_text()
        # The selector binds only the stable main base *ref*.  The exact base
        # SHA is then an observed causal fact: a moving main tip yields the
        # explicit BASE_DRIFT hold, rather than retroactively changing the
        # historical receipt's subject identity.
        self.assertIn('if subject["base_ref"] != "main":', core)
        self.assertIn('base = _sha(snapshot.get("base_sha"), "base_sha")', core)
        self.assertIn('if base != current_main:', core)

    def test_canonical_writer_contract_executes_protected_main_receipt_regressions(self):
        makefile = (ROOT / "Makefile").read_text()
        marker = "repository-writer-contract:"
        self.assertIn(marker, makefile)
        contract = makefile.split(marker, 1)[1].split("\n\n", 1)[0]
        self.assertIn("tests.test_qikvrt_protected_main_materialization", contract)
        self.assertIn("tests.test_qikvrt_candidate_pr_receipt", contract)

if __name__ == "__main__":
    unittest.main()
