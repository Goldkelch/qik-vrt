# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_ruleset_effect_dispatch_bridge.yml"
EFFECT_WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_ruleset_effect_loop.yml"


class RulesetEffectDispatchBridgeContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_bridge_is_event_driven_and_exact_upstream_bound(self):
        self.assertIn('"QIKVRT required code-owner review"', self.text)
        self.assertNotIn('"QIKVRT requested review executor"', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertNotIn("schedule:", self.text)
        self.assertIn("UPSTREAM_RUN_ID", self.text)
        self.assertIn("qikvrt-required-code-owner-selection-${UPSTREAM_RUN_ID}-CANDIDATE", self.text)
        self.assertIn("qikvrt_required_code_owner_review_selection_v1", self.text)
        self.assertIn("UPSTREAM_CANDIDATE_ARTIFACT_MISSING_OR_AMBIGUOUS", self.text)

    def test_canonical_required_review_is_the_only_bridge_source(self):
        self.assertIn("upstream_conclusion", self.text)
        self.assertIn('test "$upstream_conclusion" = success', self.text)
        self.assertIn("selection_kind=required-review", self.text)
        self.assertNotIn("success|failure", self.text)
        self.assertNotIn("qikvrt-mesh-review-selection", self.text)
        self.assertNotIn("selection_basis", self.text)
        self.assertNotIn("review_execution", self.text)

    def test_deduplicated_failure_status_is_subject_not_run_url_bound(self):
        self.assertIn("failure: CODE_OWNER_RULE_NOT_ENFORCED", self.text)
        self.assertIn("EXACT_RULESET_BLOCKER_STATUS_MISSING", self.text)
        self.assertNotIn("target_url", self.text)

    def test_bridge_uses_ordinary_job_token_to_reach_single_effect_writer(self):
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.text)
        self.assertNotIn("secrets.QIKVRT_RULESET_ADMIN_TOKEN", self.text)
        self.assertNotIn("test -n \"${GH_TOKEN:-}\"", self.text)
        self.assertIn("qikvrt_autonomous_ruleset_effect_loop.yml/dispatches", self.text)
        self.assertIn('mode:"PR"', self.text)
        self.assertIn("expected_head:$head", self.text)
        self.assertNotIn("qikvrt_ruleset_reconcile.py", self.text)
        self.assertNotIn("rulesets/19344903", self.text)
        self.assertNotIn("--method PUT", self.text)
        self.assertNotIn("--method PATCH", self.text)

    def test_bridge_is_the_only_workflow_run_ingress_to_effect_writer(self):
        effect = EFFECT_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_run:", self.text)
        self.assertIn("workflow_dispatch:", effect)
        self.assertNotIn("workflow_run:", effect)
        self.assertNotIn("qikvrt_required_review_gate.yml/dispatches", effect)

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
