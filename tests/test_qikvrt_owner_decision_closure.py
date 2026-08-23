# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import copy
import pathlib
import unittest

from tools.qikvrt_owner_decision_closure import classify


BASE = "1" * 40
HEAD = "2" * 40
TREE = "3" * 40
SCOPE = ["src/closure.py", "tests/test_closure.py"]


def snapshot():
    binding = {"base_sha": BASE, "head_sha": HEAD, "tree_sha": TREE, "scope": SCOPE}
    return {
        "product_owner_login": "ingolf-lohmann",
        "required_code_owner": "Goldkelch",
        "owner_decision": {
            "state": "APPROVED",
            "author_login": "ingolf-lohmann",
            "source_id": 704,
            "binding": copy.deepcopy(binding),
        },
        "current_binding": copy.deepcopy(binding),
        "pr_state": "open",
        "draft": False,
        "head_is_descendant": True,
        "paths_changed_since_decision": [],
        "materialization_paths": [
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        ],
        "required_workflows": ["CI", "Integrity"],
        "workflows": [
            {"id": 10, "name": "CI", "head_sha": HEAD, "status": "completed", "conclusion": "success", "run_number": 1, "run_attempt": 1},
            {"id": 11, "name": "Integrity", "head_sha": HEAD, "status": "completed", "conclusion": "success", "run_number": 1, "run_attempt": 1},
        ],
        "statuses": [],
        "reviews": [],
        "requested_reviewers": ["Goldkelch"],
    }


class OwnerDecisionClosureTests(unittest.TestCase):
    def test_workflow_is_trusted_main_bounded_and_has_no_merge_path(self):
        workflow = pathlib.Path(".github/workflows/qikvrt_owner_decision_closure.yml").read_text(encoding="utf-8")
        self.assertIn("ref: main", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("test \"$live\" = \"$EXPECTED_HEAD\"", workflow)
        self.assertIn("requested_reviewers", workflow)
        self.assertNotIn("gh pr merge", workflow)
        self.assertNotIn("merge_pull_request", workflow)

    def test_missing_workflow_is_auto_resolvable(self):
        value = snapshot()
        value["workflows"].pop()
        result = classify(value)
        self.assertEqual(result["classification"], "AUTO_RESOLVABLE")
        self.assertEqual(result["phase"], "VERIFY")
        self.assertEqual(result["dispatch_workflows"], ["Integrity"])

    def test_active_workflow_is_waiting(self):
        value = snapshot()
        value["workflows"][0].update(status="in_progress", conclusion=None)
        result = classify(value)
        self.assertEqual(result["classification"], "WAITING")
        self.assertEqual(result["phase"], "VERIFY")

    def test_adverse_workflow_is_true_blocker(self):
        value = snapshot()
        value["workflows"][0]["conclusion"] = "failure"
        result = classify(value)
        self.assertEqual(result["classification"], "TRUE_BLOCKER")
        self.assertEqual(result["first_blocker"], "EXACT_HEAD_WORKFLOW_ADVERSE")

    def test_projection_only_descendant_drift_rebinds_without_transferring_evidence(self):
        value = snapshot()
        value["current_binding"]["head_sha"] = "4" * 40
        value["current_binding"]["tree_sha"] = "5" * 40
        value["paths_changed_since_decision"] = ["REPOSITORY_FILE_MANIFEST.json"]
        result = classify(value)
        self.assertEqual(result["classification"], "AUTO_RESOLVABLE")
        self.assertEqual(result["phase"], "RESOLVE")
        self.assertTrue(result["stale_exact_head_evidence"])

    def test_semantic_drift_requires_new_owner_decision(self):
        value = snapshot()
        value["current_binding"]["head_sha"] = "4" * 40
        value["current_binding"]["tree_sha"] = "5" * 40
        value["paths_changed_since_decision"] = ["src/closure.py"]
        result = classify(value)
        self.assertEqual(result["classification"], "TRUE_BLOCKER")
        self.assertEqual(result["first_blocker"], "OWNER_DECISION_BINDING_DRIFT")

    def test_requested_review_waits_without_impersonation(self):
        result = classify(snapshot())
        self.assertEqual(result["classification"], "WAITING")
        self.assertFalse(result["request_reviewer"])
        self.assertEqual(result["review_authority"], "INDEPENDENT_NATIVE_GITHUB_REVIEW_REQUIRED")

    def test_unrequested_reviewer_is_requested_once(self):
        value = snapshot()
        value["requested_reviewers"] = []
        result = classify(value)
        self.assertEqual(result["classification"], "AUTO_RESOLVABLE")
        self.assertTrue(result["request_reviewer"])

    def test_bot_comment_cannot_satisfy_independent_review(self):
        value = snapshot()
        value["reviews"] = [{"id": 20, "user": {"login": "github-actions[bot]"}, "state": "APPROVED", "commit_id": HEAD, "submitted_at": "2026-08-23T00:00:00Z"}]
        result = classify(value)
        self.assertEqual(result["classification"], "WAITING")

    def test_independent_approval_plus_native_status_continues(self):
        value = snapshot()
        value["reviews"] = [{"id": 20, "user": {"login": "Goldkelch"}, "state": "APPROVED", "commit_id": HEAD, "submitted_at": "2026-08-23T00:00:00Z"}]
        value["statuses"] = [{"id": 30, "context": "QIKVRT required code-owner review", "state": "success", "updated_at": "2026-08-23T00:01:00Z"}]
        result = classify(value)
        self.assertEqual(result["classification"], "CONTINUE")
        self.assertFalse(result["completion_claims"]["MERGE"])
        self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
