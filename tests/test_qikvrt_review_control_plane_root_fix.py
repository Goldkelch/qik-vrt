# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import copy
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_executor_root_fix",
    ROOT / "tools/qikvrt_requested_review_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequestedReviewControlPlaneRootFixTests(unittest.TestCase):
    def test_main_tip_is_progress_not_historical_identity(self):
        receipt = {
            "repository": "example/qik-vrt",
            "pr_number": 1016,
            "base_ref": "main",
            "base_sha": "a" * 40,
            "base_tree_sha": "b" * 40,
            "head_sha": "c" * 40,
            "tree_sha": "d" * 40,
            "scope_sha256": "e" * 64,
            "diff_sha256": "f" * 64,
            "current_main_sha": "1" * 40,
            "current_main_tree_sha": "2" * 40,
            "state": "APPROVE",
            "mesh_disposition": "APPROVE",
            "first_blocker": None,
            "detail": "old",
            "evidence_fingerprint": "3" * 64,
            "receipt_payload_sha256": "4" * 64,
        }
        successor = copy.deepcopy(receipt)
        successor.update(
            current_main_sha="5" * 40,
            current_main_tree_sha="6" * 40,
            state="COMMENT_WITH_BLOCKER",
            mesh_disposition="COMMENT_WITH_BLOCKER",
            first_blocker="BASE_DRIFT",
            detail="main advanced",
            evidence_fingerprint="7" * 64,
            receipt_payload_sha256="8" * 64,
        )
        self.assertEqual(
            MODULE._historical_receipt_binding(receipt),
            MODULE._historical_receipt_binding(successor),
        )

    def test_recursive_queue_is_subject_scoped(self):
        text = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("SUBJECT_PR_NUMBER: ${{ steps.select.outputs.pr }}", text)
        self.assertIn("SUBJECT_HEAD_SHA: ${{ steps.decision.outputs.head }}", text)
        self.assertIn("str(intent.get('pr_number')) != os.environ['SUBJECT_PR_NUMBER']", text)
        self.assertIn("intent.get('head_sha') != os.environ['SUBJECT_HEAD_SHA']", text)

    def test_transport_does_not_bind_moving_base_tip(self):
        text = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("'base_sha':pr.get('base',{}).get('sha') == os.environ['EXPECTED_BASE']", text)
        self.assertIn("'base_ref':pr.get('base',{}).get('ref') == 'main'", text)
        self.assertIn("'full_causal_binding'", text)


if __name__ == "__main__":
    unittest.main()
