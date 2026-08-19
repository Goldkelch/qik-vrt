# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_required_review_gate",
    ROOT / "tools/qikvrt_required_review_gate.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequiredCodeOwnerReviewGateTests(unittest.TestCase):
    head = "b" * 40

    def pr(self, **overrides):
        value = {"number": 641, "head": {"sha": self.head}, "user": {"login": "integration-author"}}
        value.update(overrides)
        return value

    def enforced_rules(self):
        return [{"type": "pull_request", "parameters": {
            "required_approving_review_count": 1,
            "require_code_owner_review": True,
            "dismiss_stale_reviews_on_push": True,
            "require_last_push_approval": True,
        }}]

    def approval(self, **overrides):
        value = {
            "id": 3,
            "submitted_at": "2026-08-16T16:00:00Z",
            "state": "APPROVED",
            "commit_id": self.head,
            "user": {"login": "Goldkelch"},
        }
        value.update(overrides)
        return value

    def status(self, **overrides):
        value = {
            "id": 10,
            "context": "QIKVRT requested review execution",
            "state": "failure",
            "description": "failure: CODE_OWNER_RULE_NOT_ENFORCED",
            "target_url": "https://github.com/Goldkelch/qik-vrt/actions/runs/1",
            "created_at": "2026-08-19T20:00:00Z",
            "updated_at": "2026-08-19T20:00:00Z",
        }
        value.update(overrides)
        return value

    def evaluate(self, reviews, *, rules=None, pr=None):
        return MODULE.evaluate_required_review(
            self.pr() if pr is None else pr,
            self.enforced_rules() if rules is None else rules,
            reviews,
        )

    def publish(self, statuses, *, state="failure", description="failure: CODE_OWNER_RULE_NOT_ENFORCED"):
        return MODULE.decide_status_publication(
            statuses,
            context="QIKVRT requested review execution",
            state=state,
            description=description,
        )

    def test_native_rule_must_enforce_all_freshness_requirements(self):
        weak = self.enforced_rules(); weak[0]["parameters"]["require_code_owner_review"] = False
        result = self.evaluate([], rules=weak)
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_RULE_NOT_ENFORCED"))

    def test_native_rule_requires_stale_dismissal_and_last_push_approval(self):
        for field in ("dismiss_stale_reviews_on_push", "require_last_push_approval"):
            with self.subTest(field=field):
                weak = self.enforced_rules(); weak[0]["parameters"][field] = False
                result = self.evaluate([], rules=weak)
                self.assertEqual(result["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_no_review_is_pending_not_approval(self):
        result = self.evaluate([])
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("pending", "CODE_OWNER_REVIEW_MISSING"))

    def test_wrong_reviewer_cannot_satisfy_gate(self):
        result = self.evaluate([self.approval(user={"login": "someone-else"})])
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_MISSING")

    def test_old_head_approval_is_stale(self):
        result = self.evaluate([self.approval(commit_id="a" * 40)])
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_STALE")

    def test_exact_head_approval_passes(self):
        result = self.evaluate([self.approval()])
        self.assertEqual(result["gate_state"], "success")
        self.assertEqual(result["head_sha"], self.head)
        self.assertIsNone(result["first_blocker"])

    def test_current_head_changes_requested_supersedes_prior_approval(self):
        result = self.evaluate([
            self.approval(id=3, submitted_at="2026-08-16T16:00:00Z"),
            self.approval(id=4, submitted_at="2026-08-16T16:01:00Z", state="CHANGES_REQUESTED"),
        ])
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_REVIEW_CHANGES_REQUESTED"))

    def test_dismissed_exact_head_review_requires_new_approval(self):
        result = self.evaluate([self.approval(state="DISMISSED")])
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_DISMISSED")

    def test_pr_author_cannot_satisfy_independent_gate(self):
        result = self.evaluate([self.approval()], pr=self.pr(user={"login": "Goldkelch"}))
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_REVIEW_SELF_APPROVAL"))

    def test_status_description_is_stable_and_bounded(self):
        result = self.evaluate([], rules=[])
        description = MODULE.status_description(result)
        self.assertEqual(description, "failure: CODE_OWNER_RULE_NOT_ENFORCED")
        self.assertLessEqual(len(description), 140)

    def test_unchanged_head_context_state_is_noop_even_when_run_url_changed(self):
        result = self.publish([
            self.status(target_url="https://github.com/Goldkelch/qik-vrt/actions/runs/old"),
        ])
        self.assertEqual(result["status_publication"], "NOOP")
        self.assertEqual(result["status_publication_reason"], "UNCHANGED_HEAD_CONTEXT_STATE")

    def test_material_gate_transition_requires_status_write(self):
        result = self.publish([
            self.status(state="pending", description="pending: CODE_OWNER_REVIEW_MISSING"),
        ])
        self.assertEqual(result["status_publication"], "WRITE")
        self.assertEqual(result["status_publication_reason"], "MATERIAL_GATE_TRANSITION")

    def test_other_context_cannot_suppress_required_review_status(self):
        result = self.publish([
            self.status(context="unrelated context"),
        ])
        self.assertEqual(result["status_publication"], "WRITE")
        self.assertIsNone(result["previous_status_id"])

    def test_latest_matching_status_controls_publication(self):
        result = self.publish([
            self.status(
                id=10,
                state="failure",
                description="failure: CODE_OWNER_RULE_NOT_ENFORCED",
                updated_at="2026-08-19T19:00:00Z",
            ),
            self.status(
                id=11,
                state="pending",
                description="pending: CODE_OWNER_REVIEW_MISSING",
                updated_at="2026-08-19T20:00:00Z",
            ),
        ])
        self.assertEqual(result["status_publication"], "WRITE")
        self.assertEqual(result["previous_status_id"], 11)

    def test_workflow_reads_combined_latest_status_and_skips_unchanged_post(self):
        workflow = (ROOT / ".github/workflows/qikvrt_required_review_gate.yml").read_text(encoding="utf-8")
        self.assertIn("commits/{head}/status", workflow)
        self.assertIn("STATUS_PUBLICATION_NOOP", workflow)
        self.assertIn("if publication['status_publication'] == STATUS_PUBLICATION_NOOP:", workflow)
        self.assertLess(workflow.index("rules=gh_json"), workflow.index("for number in numbers:"))


if __name__ == "__main__":
    unittest.main()
