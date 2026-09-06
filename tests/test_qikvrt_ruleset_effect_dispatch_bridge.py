# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_ruleset_effect_dispatch_bridge.yml"


class RulesetEffectDispatchBridgeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_bridge_is_event_driven_and_exact_upstream_bound(self):
        self.assertIn('"QIKVRT required code-owner review"', self.text)
        self.assertIn('"QIKVRT requested review executor"', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertNotIn("schedule:", self.text)
        self.assertIn("UPSTREAM_RUN_ID", self.text)
        self.assertIn("qikvrt-required-code-owner-selection-${UPSTREAM_RUN_ID}-CANDIDATE", self.text)
        self.assertIn("qikvrt-mesh-review-selection-${UPSTREAM_RUN_ID}-CANDIDATE", self.text)
        self.assertIn("qikvrt_required_code_owner_review_selection_v1", self.text)
        self.assertIn("qikvrt_requested_review_selection_v1", self.text)
        self.assertIn("UPSTREAM_CANDIDATE_ARTIFACT_MISSING_OR_AMBIGUOUS", self.text)

    def test_failed_executor_can_supply_selection_but_not_review_receipt(self):
        self.assertIn("upstream_conclusion", self.text)
        self.assertIn("success|failure", self.text)
        self.assertIn("selection_basis", self.text)
        self.assertIn("EXACT_EVENT_OR_DISPATCH", self.text)
        self.assertIn("review_execution", self.text)
        self.assertNotIn("mesh-review/review.json", self.text)
        self.assertNotIn("INVALID_REVIEW_SNAPSHOT", self.text)

    def test_deduplicated_failure_status_is_subject_not_run_url_bound(self):
        self.assertIn("failure: CODE_OWNER_RULE_NOT_ENFORCED", self.text)
        self.assertIn("EXACT_RULESET_BLOCKER_STATUS_MISSING", self.text)
        self.assertNotIn("target_url", self.text)

    def test_bridge_uses_admin_credential_only_to_reach_single_effect_writer(self):
        self.assertIn("GH_TOKEN: ${{ secrets.QIKVRT_RULESET_ADMIN_TOKEN }}", self.text)
        self.assertIn("test -n \"${GH_TOKEN:-}\"", self.text)
        self.assertIn("qikvrt_autonomous_ruleset_effect_loop.yml/dispatches", self.text)
        self.assertIn("expected_head:$head", self.text)
        self.assertNotIn("qikvrt_ruleset_reconcile.py", self.text)
        self.assertNotIn("rulesets/19344903", self.text)
        self.assertNotIn("--method PUT", self.text)
        self.assertNotIn("--method PATCH", self.text)

    def test_no_review_merge_or_publication_effect(self):
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("event=APPROVE", self.text)
        self.assertNotIn("pulls/reviews", self.text)
        self.assertNotIn("zenodo", self.text.lower())
        self.assertNotIn("arxiv", self.text.lower())
        self.assertNotIn("wikipedia", self.text.lower())
        self.assertNotIn("EFFECT_ACK_DONE", self.text)


if __name__ == "__main__":
    unittest.main()
