# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_ruleset_effect_loop.yml"


class AutonomousRulesetEffectLoopContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_event_driven_without_polling(self):
        self.assertIn(
            'workflows:\n      - "QIKVRT required code-owner review"',
            self.text,
        )
        self.assertIn("types: [completed]", self.text)
        self.assertIn("workflow_dispatch:", self.text)
        self.assertNotIn("schedule:", self.text)

    def test_consumes_exact_trusted_selection_artifact(self):
        self.assertIn(
            "qikvrt-required-code-owner-selection-{run_id}-CANDIDATE",
            self.text,
        )
        self.assertIn("UPSTREAM_GATE_PROVENANCE_INVALID", self.text)
        self.assertIn("run.get(\"workflow_id\") != workflow.get(\"id\")", self.text)
        self.assertIn('run.get("head_sha") != live_main', self.text)
        self.assertIn("UPSTREAM_SELECTION_BINDING_INVALID", self.text)
        self.assertIn("EXACT_RULESET_BLOCKER_STATUS_MISSING", self.text)
        self.assertIn("predecessor_evidence_transfer", self.text)

    def test_reuses_full_current_ruleset_reconciler(self):
        self.assertIn("tools/qikvrt_ruleset_reconcile.py", self.text)
        self.assertIn('--snapshot "$root/live-ruleset-before.json"', self.text)
        self.assertIn("--apply", self.text)
        self.assertIn("--receipt", self.text)
        self.assertIn("rulesets/19344903", self.text)

    def test_admin_authority_is_nonterminal_and_repository_routed(self):
        self.assertIn("QIKVRT_RULESET_ADMIN_TOKEN", self.text)
        self.assertNotIn("QIKVRT_GITHUB_ADMIN_TOKEN", self.text)
        self.assertIn("REQUEST_AUTHORITY", self.text)
        self.assertIn("state=pending", self.text)
        self.assertIn("issues: write", self.text)
        self.assertIn("qikvrt-ruleset-authority:", self.text)
        self.assertIn("issues/${PR_NUMBER}/comments", self.text)
        self.assertIn("issues/comments/${comment_id}", self.text)
        self.assertNotIn("required_approving_review_count: 0", self.text)
        self.assertNotIn("require_code_owner_review: false", self.text)

    def test_hold_requires_absence_of_repository_carriers(self):
        self.assertIn("tools/qikvrt_hold_admissibility.py", self.text)
        self.assertIn("--pull-request-carrier", self.text)
        self.assertIn("--branch-carrier", self.text)
        self.assertIn("hold_admissible", self.text)
        self.assertIn("HOLD_ADMISSIBLE=false", self.text)
        self.assertNotIn('"state": "HOLD"', self.text)
        self.assertNotIn("steps.reconcile.outputs.state == 'HOLD'", self.text)
        self.assertNotIn("Publish exact authority HOLD", self.text)

    def test_effect_and_same_head_reobservation_are_fenced(self):
        self.assertGreaterEqual(
            self.text.count('pulls/${PR_NUMBER}" --jq .head.sha'),
            3,
        )
        self.assertGreaterEqual(
            self.text.count('commits/main" --jq .sha'),
            3,
        )
        self.assertGreaterEqual(
            self.text.count('git/ref/heads/${HEAD_REF}" --jq .object.sha'),
            3,
        )
        self.assertIn(
            "steps.reconcile.outputs.state == 'CURRENT'",
            self.text,
        )
        self.assertIn(
            "qikvrt_required_review_gate.yml/dispatches",
            self.text,
        )
        self.assertIn(
            "ruleset CURRENT; exact-head gate reobservation dispatched",
            self.text,
        )

    def test_no_review_merge_or_publication_bypass_exists(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("event=APPROVE", self.text)
        self.assertNotIn("pulls/reviews", self.text)
        self.assertNotIn("zenodo", self.text.lower())
        self.assertNotIn("arxiv", self.text.lower())
        self.assertNotIn("wikipedia", self.text.lower())
        self.assertNotIn("EFFECT_ACK_DONE=true", self.text)


if __name__ == "__main__":
    unittest.main()
