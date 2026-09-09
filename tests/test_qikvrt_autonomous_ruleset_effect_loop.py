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
        self.assertIn("workflow_dispatch:", self.text)
        self.assertNotIn("workflow_run:", self.text)
        self.assertNotIn("schedule:", self.text)
        self.assertIn("options: [PR, MAIN]", self.text)

    def test_consumes_only_exact_dispatch_bound_subject(self):
        self.assertIn("DISPATCH_PR_NUMBER_INVALID", self.text)
        self.assertIn("DISPATCH_EXPECTED_HEAD_INVALID", self.text)
        self.assertIn("DISPATCH_CANDIDATE", self.text)
        self.assertIn("EXACT_RULESET_BLOCKER_STATUS_MISSING", self.text)
        self.assertIn("UPSTREAM_REQUIRED_REVIEW_PROVENANCE_INVALID", self.text)
        self.assertIn("UPSTREAM_SELECTION_PROVENANCE_MISMATCH", self.text)
        self.assertIn("qikvrt-required-code-owner-selection-", self.text)
        self.assertIn("predecessor_evidence_transfer", self.text)

    def test_pr_app_authority_is_bound_to_the_exact_bridge_and_upstream_before_token_mint(self):
        selection = self.text.index("Select exact dispatch-bound ruleset-repair subject and active carriers")
        app_token = self.text.index("actions/create-github-app-token")
        self.assertLess(selection, app_token)
        self.assertIn("DISPATCH_BRIDGE_RUN_ID_INVALID", self.text)
        self.assertIn("BRIDGE_PROVENANCE_INVALID", self.text)
        self.assertIn("UPSTREAM_REQUIRED_REVIEW_PROVENANCE_INVALID", self.text)
        self.assertIn("UPSTREAM_SELECTION_ARTIFACT_MISSING_OR_AMBIGUOUS", self.text)
        self.assertIn("bridge_run_id", self.text)
        self.assertIn("recovery_mode", self.text)
        self.assertIn("recovery_of_effect_run_id", self.text)

    def test_reuses_full_current_ruleset_reconciler(self):
        self.assertIn("tools/qikvrt_ruleset_reconcile.py", self.text)
        self.assertIn("--apply", self.text)
        self.assertIn("--receipt", self.text)
        self.assertNotIn('gh api "repos/${REPOSITORY}/rulesets/19344903"', self.text)

    def test_admin_authority_is_nonterminal_and_repository_routed(self):
        self.assertIn("QIKVRT_RULESET_ADMIN_TOKEN", self.text)
        self.assertIn("QIKVRT_RULESET_APP_ID", self.text)
        self.assertIn("QIKVRT_RULESET_APP_PRIVATE_KEY", self.text)
        self.assertIn(
            "actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349",
            self.text,
        )
        self.assertIn("steps.app-token.outputs.token", self.text)
        self.assertIn("permission-administration: write", self.text)
        self.assertNotIn("|| secrets.QIKVRT_RULESET_ADMIN_TOKEN", self.text)
        self.assertIn("continue-on-error: true", self.text)
        self.assertIn("APP_CONFIG_OUTCOME", self.text)
        self.assertIn('if [ "$APP_CONFIG_OUTCOME" != success ]', self.text)
        self.assertIn('elif [ "$APP_CONFIGURED" = false ]', self.text)
        self.assertIn('elif [ "$APP_CONFIGURED" != true ]', self.text)
        self.assertIn("QIKVRT_RULESET_GITHUB_APP_CONFIGURATION_MISSING", self.text)
        self.assertIn("QIKVRT_RULESET_GITHUB_APP_CONFIGURATION_CHECK_FAILED", self.text)
        self.assertIn("QIKVRT_RULESET_GITHUB_APP_CONFIGURATION_STATE_INVALID", self.text)
        self.assertIn("QIKVRT_RULESET_GITHUB_APP_TOKEN_MINT_FAILED", self.text)
        self.assertNotIn("QIKVRT_GITHUB_ADMIN_TOKEN", self.text)
        self.assertIn("REQUEST_AUTHORITY", self.text)
        self.assertIn("state=pending", self.text)
        self.assertIn("issues: write", self.text)
        self.assertIn("qikvrt-ruleset-authority:", self.text)
        self.assertIn("issues/${PR_NUMBER}/comments", self.text)
        self.assertIn("issues/comments/${comment_id}", self.text)
        self.assertNotIn("required_approving_review_count: 0", self.text)
        self.assertNotIn("require_code_owner_review: false", self.text)

    def test_unexpected_reconciliation_failure_stays_a_failing_hold(self):
        self.assertIn("state: \"HOLD\"", self.text)
        self.assertIn("REOBSERVE_EXACT_RULESET_API_AND_READBACK_EVIDENCE", self.text)
        self.assertIn("ruleset reconciliation did not produce an authority-only blocker", self.text)
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.text)

    def test_every_github_read_uses_the_bounded_read_only_observer(self):
        self.assertIn("tools/qikvrt_github_observe.py", self.text)
        self.assertIn("run_gh_api_read", self.text)
        self.assertIn("GitHubInstallationRateLimit", self.text)
        self.assertGreaterEqual(self.text.count("gh_read()"), 4)
        raw_api_lines = [
            line.strip()
            for line in self.text.splitlines()
            if "gh api" in line
        ]
        self.assertTrue(raw_api_lines)
        self.assertTrue(
            all("--method" in line for line in raw_api_lines),
            "read-only gh api calls must pass through gh_read/run_gh_api_read",
        )

    def test_quota_and_uncertain_mutation_holds_are_explicit(self):
        self.assertIn("GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED", self.text)
        self.assertIn("bounded 0/15/45", (ROOT / "tools/qikvrt_ruleset_reconcile.py").read_text(encoding="utf-8"))
        self.assertIn("effect_transport_attempted", self.text)
        self.assertIn("POST_UNCONFIRMED_RATE_LIMIT", self.text)
        self.assertIn("POST_UNCONFIRMED_TRANSPORT_FAILED", self.text)
        self.assertGreaterEqual(self.text.count("hold_reason:"), 6)
        self.assertGreaterEqual(self.text.count("d0: 2"), 6)

    def test_privileged_effect_history_is_write_ahead_append_only_and_carried_by_every_hold(self):
        self.assertIn("tools/qikvrt_effect_attempts.py create", self.text)
        self.assertIn("--effect-attempt-ledger \"$root/effect-attempts.json\"", self.text)
        self.assertIn("ATTEMPTED_PENDING_READBACK", self.text)
        self.assertGreaterEqual(self.text.count("append_effect_attempt()"), 3)
        self.assertGreaterEqual(self.text.count("effect_attempts: $effect_attempts"), 5)
        self.assertGreaterEqual(self.text.count("effect_summary()"), 5)
        self.assertIn("EFFECT_ATTEMPT_LEDGER_APPEND_FAILED", self.text)

    def test_status_publication_is_remote_deduplicated_before_any_post(self):
        self.assertGreaterEqual(
            self.text.count('statuses/${EXPECTED_HEAD}?per_page=100'),
            2,
        )
        self.assertGreaterEqual(
            self.text.count("EXACT_SUBJECT_DRIFT_IMMEDIATELY_BEFORE_SUCCESS_STATUS_POST"),
            1,
        )
        self.assertGreaterEqual(
            self.text.count("EXACT_SUBJECT_DRIFT_IMMEDIATELY_BEFORE_AUTHORITY_STATUS_POST"),
            1,
        )
        self.assertIn("commit_status_readback", self.text)

    def test_hold_requires_absence_of_repository_carriers(self):
        self.assertIn("tools/qikvrt_hold_admissibility.py", self.text)
        self.assertIn("--pull-request-carrier", self.text)
        self.assertIn("--branch-carrier", self.text)
        self.assertIn("hold_admissible", self.text)
        self.assertIn("HOLD_ADMISSIBLE=false", self.text)
        self.assertIn('state: "HOLD"', self.text)
        self.assertNotIn("steps.reconcile.outputs.state == 'HOLD'", self.text)
        self.assertNotIn("Publish exact authority HOLD", self.text)

    def test_single_apply_receipt_is_exact_and_feedback_free(self):
        self.assertGreaterEqual(
            self.text.count(".base.sha // empty"),
            3,
        )
        self.assertGreaterEqual(
            self.text.count(".head.repo.full_name // empty"),
            3,
        )
        self.assertGreaterEqual(
            self.text.count(".head.ref // empty"),
            3,
        )
        self.assertIn("qikvrt_ruleset_single_apply_receipt_v1", self.text)
        self.assertNotIn("APPLY_REQUIRED", self.text)
        self.assertNotIn("ALREADY_APPLIED", self.text)
        self.assertNotIn("steps.apply_receipt", self.text)
        self.assertIn("qikvrt-ruleset-apply:", self.text)
        self.assertIn("Record and read back completed exact-subject reconciliation receipt", self.text)
        self.assertIn("reconciliation_receipt_sha256", self.text)
        self.assertNotIn("Current reconciliation receipt SHA-256", self.text)
        self.assertNotIn("--arg reconciliation_line", self.text)
        self.assertIn("authenticated reconciliation was read back", self.text)
        self.assertIn("Exact trusted Main: ${EXPECTED_MAIN}", self.text)
        self.assertIn('jq -r .user.login <<<"$readback"', self.text)
        self.assertIn("full_exact_subject_verified", self.text)
        self.assertIn("if: always() && steps.select.outputs.state == 'CANDIDATE'", self.text)
        self.assertIn("Publish exact non-feedback ruleset-current status", self.text)
        self.assertIn("ruleset CURRENT; exact subject receipt reobserved", self.text)
        self.assertIn("REQUEST_AUTHORITY: exact PR continuation is published separately", self.text)
        self.assertIn("steps.reconcile.outputs.state == 'REQUEST_AUTHORITY'", self.text)
        self.assertNotIn("qikvrt_required_review_gate.yml/dispatches", self.text)
        self.assertNotIn("Dispatch one fresh same-head review-gate reobservation", self.text)

    def test_main_mode_is_exact_bound_artifact_only_and_nonfeedback(self):
        self.assertIn("MAIN_CANDIDATE", self.text)
        self.assertIn("DISPATCH_EXPECTED_MAIN_INVALID", self.text)
        self.assertIn("DISPATCH_EXPECTED_POLICY_SHA_INVALID", self.text)
        self.assertIn("REQUESTED_POLICY_SHA", self.text)
        self.assertIn("TRUSTED_MAIN_READBACK_FAILED_BEFORE_SELECTION", self.text)
        self.assertIn("RULESET_POLICY_READ_FAILED_BEFORE_MAIN_SELECTION", self.text)
        self.assertIn("TRUSTED_MAIN_READBACK_FAILED_DURING_MAIN_SELECTION", self.text)
        self.assertIn("RULESET_POLICY_READ_FAILED_DURING_MAIN_SELECTION", self.text)
        self.assertIn("RULESET_SELECTION_EXECUTION_FAILED", self.text)
        self.assertIn("HOLD_UNVERIFIED: ruleset selection", self.text)
        self.assertIn("Record current Main reconciliation artifact receipt", self.text)
        self.assertIn("qikvrt_ruleset_main_reconciliation_receipt_v1", self.text)
        self.assertIn("REQUEST_AUTHORITY: Main reconciliation has no PR carrier", self.text)
        main_receipt = self.text.split(
            "      - name: Record current Main reconciliation artifact receipt", 1
        )[1].split(
            "      - name: Record and read back completed exact-subject reconciliation receipt", 1
        )[0]
        self.assertNotIn("issues/${PR_NUMBER}/comments", main_receipt)
        self.assertNotIn("statuses/${EXPECTED_HEAD}", main_receipt)
        self.assertNotIn("workflow_dispatches", main_receipt)

    def test_main_terminal_receipt_is_normalized_for_a_run_bound_recovery_lookup(self):
        self.assertIn("policy=${{ inputs.mode == 'MAIN' && inputs.expected_policy_sha || 'none' }}", self.text)
        self.assertIn("Normalize every terminal Main reconciliation into a stable recovery receipt", self.text)
        self.assertIn("main-reconciliation-receipt.json", self.text)
        self.assertIn("TERMINAL_MAIN_RECONCILIATION_UNVERIFIED", self.text)
        self.assertIn("qikvrt_ruleset_main_reconciliation_receipt_v1", self.text)
        self.assertIn("NEXT_SCHEDULED_MAIN_CARRIER", self.text)
        artifact = self.text.split("      - name: Preserve exact selection, effect, continuation, and readback receipts", 1)[1]
        self.assertIn("qikvrt-autonomous-ruleset-effect-${{ github.run_id }}", artifact)
        self.assertNotIn("overwrite:", artifact)

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
