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
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("upstream_run_id:", self.text)
        self.assertIn("carrier_run_id:", self.text)
        self.assertIn("predecessor_bridge_run_id:", self.text)
        self.assertIn("UPSTREAM_RUN_ID", self.text)
        self.assertIn("qikvrt-required-code-owner-selection-${UPSTREAM_RUN_ID}-CANDIDATE", self.text)
        self.assertIn("qikvrt_required_code_owner_review_selection_v1", self.text)
        self.assertIn("UPSTREAM_CANDIDATE_ARTIFACT_MISSING_OR_AMBIGUOUS", self.text)

    def test_canonical_required_review_is_the_only_bridge_source(self):
        self.assertIn("upstream_conclusion", self.text)
        self.assertIn('"$upstream_conclusion" != success', self.text)
        self.assertIn("UPSTREAM_RUN_NOT_EXACT_ELIGIBLE", self.text)
        self.assertIn(".github/workflows/qikvrt_required_review_gate.yml", self.text)
        self.assertIn("UPSTREAM_RUN_ID", self.text)
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
        self.assertIn("EFFECT_WORKFLOW: qikvrt_autonomous_ruleset_effect_loop.yml", self.text)
        self.assertIn('actions/workflows/${EFFECT_WORKFLOW}/dispatches', self.text)
        self.assertIn('mode:"PR"', self.text)
        self.assertIn("expected_head:$head", self.text)
        self.assertIn("upstream_run_id:$upstream", self.text)
        self.assertIn("bridge_run_id:$bridge", self.text)
        self.assertIn("recovery_mode:$recovery", self.text)
        self.assertIn("recovery_of_effect_run_id:$recovery_of", self.text)
        self.assertNotIn("qikvrt_ruleset_reconcile.py", self.text)
        self.assertNotIn("rulesets/19344903", self.text)
        self.assertNotIn("--method PUT", self.text)
        self.assertNotIn("--method PATCH", self.text)

    def test_bridge_uses_bounded_readbacks_and_durable_dispatch_intent(self):
        self.assertIn("tools/qikvrt_github_observe.py", self.text)
        self.assertIn("--write-bytes", self.text)
        self.assertIn("tools/qikvrt_effect_attempts.py create", self.text)
        self.assertIn("workflow_dispatch_intent", self.text)
        self.assertIn("ATTEMPTED_PENDING_READBACK", self.text)
        self.assertIn("RULESET_EFFECT_DISPATCH_UNCONFIRMED", self.text)
        self.assertIn("readback:effect-run:", self.text)
        self.assertIn("readback:terminal-exact-effect:", self.text)
        self.assertIn("TERMINAL_EXACT_EFFECT_RECEIPT_PROVENANCE_INVALID", self.text)
        self.assertIn("tools/qikvrt_ruleset_effect_recovery.py", self.text)
        self.assertIn("EXACT_UPSTREAM_EFFECT_RUN_READBACK_MALFORMED", self.text)
        self.assertIn("SCHEDULED_RULESET_PR_CARRIER", self.text)
        self.assertEqual(self.text.count("gh api"), 1)

    def test_bridge_proves_and_classifies_every_existing_exact_effect_before_new_intent(self):
        self.assertIn("EXACT_SUBJECT_PULL_READBACK_MALFORMED", self.text)
        self.assertIn("malformed pull observation", self.text)
        self.assertIn("load_predecessor_bridge_receipt", self.text)
        self.assertIn("decide_existing_exact_effect", self.text)
        self.assertIn("classify_terminal_effect", self.text)
        immediate_readback = self.text.index("Re-read every state immediately before a fresh")
        intent = self.text.index("--kind workflow_dispatch_intent")
        self.assertLess(immediate_readback, intent)
        self.assertGreaterEqual(
            self.text[:intent].count("decide_existing_exact_effect"),
            2,
        )

    def test_bridge_recovery_provenance_handles_normal_apply_and_get_only_reobserve(self):
        self.assertIn('recovery_mode=APPLY', self.text)
        self.assertIn('recovery_mode="$(jq -r .next_recovery_mode', self.text)
        self.assertIn('REOBSERVE_UNCONFIRMED', self.text)
        self.assertIn('args+=(--bridge-run-id "$prior_bridge")', self.text)
        self.assertIn('args+=(--recovery-of-effect-run-id "$prior_origin")', self.text)
        self.assertNotIn('args+=(--bridge-run-id "$prior_bridge" --recovery-of-effect-run-id "${prior_origin:-}")', self.text)

    def test_every_terminal_bridge_receipt_has_versioned_predecessor_provenance(self):
        """A scheduled successor must distinguish no-effect bind exits from effect exits."""

        provenance = 'receipt_provenance_version:"qikvrt_ruleset_effect_dispatch_bridge_provenance_v1"'
        self.assertGreaterEqual(self.text.count(provenance), 7)
        self.assertGreaterEqual(self.text.count('subject_binding:"UNBOUND"'), 3)
        self.assertGreaterEqual(self.text.count('subject_binding:"BOUND"'), 4)
        self.assertIn('repository:$repository', self.text)
        self.assertIn('bridge_run_id:($run|tonumber)', self.text)
        self.assertIn('upstream_run_id:(if ($upstream|test("^[1-9][0-9]*$")) then ($upstream|tonumber) else null end)', self.text)

        predecessor = self.text[
            self.text.index('load_predecessor_bridge_receipt()'):
            self.text.index('classify_terminal_effect()')
        ]
        self.assertIn('.receipt_provenance_version == "qikvrt_ruleset_effect_dispatch_bridge_provenance_v1"', predecessor)
        self.assertIn('.bridge_run_id == ($predecessor | tonumber)', predecessor)
        self.assertIn('if .subject_binding == "UNBOUND" then', predecessor)
        self.assertIn('.effect_transport_attempted == false and .effect_observed == false', predecessor)
        self.assertIn('elif .subject_binding == "BOUND" then', predecessor)

    def test_bridge_preserves_typed_installation_quota_from_both_text_and_binary_reads(self):
        self.assertGreaterEqual(self.text.count('else\n              rc=$?'), 4)
        self.assertIn('if [ "$rc" -eq 75 ]', self.text)
        self.assertIn('GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED', self.text)

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
