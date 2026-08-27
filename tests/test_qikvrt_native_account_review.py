# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import pathlib
import unittest

from tools import qikvrt_native_account_review as module


BASE = "a" * 40
HEAD = "b" * 40
TREE = "c" * 40
FINGERPRINT = "d" * 64
REPOSITORY = "Goldkelch/qik-vrt"
ROOT = pathlib.Path(__file__).resolve().parents[1]


class NativeAccountReviewTests(unittest.TestCase):
    def pr(self, *, author="ingolf-lohmann", **overrides):
        value = {
            "number": 884,
            "state": "open",
            "draft": False,
            "user": {"login": author},
            "base": {"ref": "main", "sha": BASE},
            "head": {"sha": HEAD, "repo": {"full_name": REPOSITORY}},
            "requested_reviewers": [{"login": "Goldkelch"}],
        }
        value.update(overrides)
        return value

    def commit(self, **overrides):
        value = {"sha": HEAD, "tree": {"sha": TREE}}
        value.update(overrides)
        return value

    def receipt(self, *, state="APPROVE", requested="Goldkelch", **overrides):
        value = {
            "schema": module.RECEIPT_SCHEMA,
            "repository": REPOSITORY,
            "pr_number": 884,
            "base_sha": BASE,
            "head_sha": HEAD,
            "tree_sha": TREE,
            "evidence_fingerprint": FINGERPRINT,
            "state": state,
            "review_intake": {
                "event_name": "pull_request_target",
                "event_action": "review_requested",
                "requested_reviewer": requested,
                "requested_target_observed": True,
            },
        }
        value.update(overrides)
        return value

    def delegation(self, **overrides):
        value = {
            "schema": module.DELEGATION_SCHEMA,
            "delegation_id": module.DELEGATION_ID,
            "state": module.DELEGATION_ACTIVE,
            "repositories": list(module.REPOSITORIES),
            "configured_platform_accounts": list(module.ACCOUNTS),
            "selection": {
                "pull_request_author_is_eligible": False,
                "same_account_self_review": False,
                "chatgpt_native_signing": False,
                "bot_or_app_identity_substitution": False,
            },
        }
        value.update(overrides)
        return value

    def plan(self, *, pr=None, commit=None, receipt=None, reviews=(), delegation=None, rule=True, transport=True, reobserve=True):
        return module.plan_native_account_review(
            repository=REPOSITORY,
            pr=self.pr() if pr is None else pr,
            commit=self.commit() if commit is None else commit,
            receipt=self.receipt() if receipt is None else receipt,
            reviews=reviews,
            delegation=self.delegation() if delegation is None else delegation,
            native_rule_enforced=rule,
            ledger_transport_exact=transport,
            reobservation_exact=reobserve,
        )

    def test_ingolf_author_selects_goldkelch_with_exact_approval(self):
        value = self.plan()
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["reviewer"], "Goldkelch")
        self.assertEqual(value["event"], "APPROVE")
        self.assertIn(module.MARKER, value["review_body"])
        self.assertFalse(value["independent_natural_person_review"])
        self.assertEqual(module.validate_plan(value)["plan_sha256"], value["plan_sha256"])

    def test_goldkelch_author_selects_ingolf_counterpart(self):
        value = self.plan(
            pr=self.pr(author="Goldkelch"),
            receipt=self.receipt(requested="ingolf-lohmann"),
        )
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["reviewer"], "ingolf-lohmann")

    def test_unconfigured_author_is_fail_closed(self):
        value = self.plan(pr=self.pr(author="ChatGPT"))
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "PULL_REQUEST_AUTHOR_NOT_CONFIGURED_REPOSITORY_ACCOUNT")

    def test_requested_target_must_match_counterpart(self):
        value = self.plan(receipt=self.receipt(requested="ingolf-lohmann"))
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "REQUESTED_REVIEWER_NOT_COUNTERPART")

    def test_projection_requires_exact_requested_review_event(self):
        missing = self.plan(receipt=self.receipt(review_intake=None))
        manual = self.plan(receipt=self.receipt(review_intake={"event_action": "workflow_dispatch"}))
        self.assertEqual(missing["first_blocker"], "REVIEW_INTAKE_INVALID")
        self.assertEqual(manual["first_blocker"], "REVIEW_REQUEST_EVENT_NOT_EXACT")

    def test_trusted_exact_followup_closes_a_live_request(self):
        for intake in (
            {"event_name": "workflow_run", "event_action": "completed"},
            {"event_name": "workflow_dispatch", "event_action": ""},
            {"event_name": "issue_comment", "event_action": "created"},
        ):
            with self.subTest(intake=intake):
                value = self.plan(receipt=self.receipt(review_intake=intake))
                self.assertTrue(value["effect_permitted"])
                self.assertEqual(value["event"], "APPROVE")
                self.assertTrue(value["active_requested_counterpart_required"])

    def test_trusted_exact_followup_requires_counterpart_to_remain_requested(self):
        intake = {"event_name": "workflow_run", "event_action": "completed"}
        value = self.plan(
            pr=self.pr(requested_reviewers=[]),
            receipt=self.receipt(review_intake=intake),
        )
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "REVIEW_REQUEST_EVENT_NOT_EXACT")

    def test_wrong_original_request_target_is_not_rescued_by_live_set(self):
        value = self.plan(receipt=self.receipt(requested="ingolf-lohmann"))
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "REQUESTED_REVIEWER_NOT_COUNTERPART")

    def test_approval_requires_platform_freshness_rules(self):
        value = self.plan(rule=False)
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_request_changes_can_be_projected_without_approval_rule(self):
        value = self.plan(receipt=self.receipt(state="REQUEST_CHANGES"), rule=False)
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "REQUEST_CHANGES")

    def test_comment_with_blocker_supersedes_old_delegated_approval(self):
        old = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        manual_comment = {
            "id": 2,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch"},
            "body": "manual informational comment",
        }
        value = self.plan(
            receipt=self.receipt(state="COMMENT_WITH_BLOCKER"), reviews=[old, manual_comment]
        )
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "REQUEST_CHANGES")
        self.assertFalse(value["retraction_only"])

    def test_stale_negative_projection_stops_for_new_manual_decisive_review(self):
        old = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        manual_comment = {
            "id": 2,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch"},
            "body": "manual informational comment",
        }
        plan = self.plan(
            receipt=self.receipt(state="COMMENT_WITH_BLOCKER"), reviews=[old, manual_comment]
        )
        self.assertTrue(plan["stale_approval_retraction"])
        self.assertEqual(
            module.signer_preflight(
                plan=plan,
                expected_signer="Goldkelch",
                pr=self.pr(),
                commit=self.commit(),
                reviews=[old, manual_comment],
                delegation=self.delegation(),
                token_user={"login": "Goldkelch", "type": "User"},
                collaborator_permission="write",
                native_rule_enforced=True,
                reobservation_exact=True,
            )["action"],
            "POST",
        )
        manual_approval = {
            "id": 3,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": "manual decisive approval",
        }
        blocked = module.signer_preflight(
            plan=plan,
            expected_signer="Goldkelch",
            pr=self.pr(),
            commit=self.commit(),
            reviews=[old, manual_comment, manual_approval],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
        )
        self.assertEqual(blocked["first_blocker"], "MANUAL_TARGET_DECISIVE_REVIEW_PRESENT")

    def test_later_manual_decisive_review_beats_a_higher_review_id(self):
        old = {
            "id": 2,
            "submitted_at": "2026-08-25T14:00:00Z",
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        manual = {
            "id": 1,
            "submitted_at": "2026-08-25T14:01:00Z",
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": "manual later decisive approval",
        }
        value = self.plan(
            receipt=self.receipt(state="COMMENT_WITH_BLOCKER"), reviews=[old, manual]
        )
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "MANUAL_TARGET_REVIEW_PRESENT")

    def test_revoked_delegation_is_terminal_no_effect(self):
        value = self.plan(delegation=self.delegation(state="REVOKED"))
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "DELEGATION_REVOKED_OR_INACTIVE")

    def test_wait_never_creates_native_account_effect(self):
        value = self.plan(receipt=self.receipt(state="WAIT"))
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["event"], module.NO_EFFECT)
        self.assertEqual(value["first_blocker"], "MESH_DISPOSITION_NOT_DECISIVE")

    def test_wait_retracts_only_a_stale_delegated_same_head_approval(self):
        old = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        value = self.plan(receipt=self.receipt(state="WAIT"), reviews=[old])
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "REQUEST_CHANGES")
        self.assertIn("stale delegated approval observed at plan: `true`", value["review_body"])
        self.assertIn("retraction-only projection: `true`", value["review_body"])

    def test_exact_removed_request_retracts_a_stale_delegated_approval(self):
        old = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        intake = {
            "event_name": "pull_request_target",
            "event_action": "review_request_removed",
            "requested_reviewer": "Goldkelch",
            "requested_target_observed": None,
        }
        value = self.plan(receipt=self.receipt(state="APPROVE", review_intake=intake), reviews=[old])
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "REQUEST_CHANGES")
        self.assertTrue(value["retraction_only"])

    def test_exact_followup_projects_a_current_blocker_for_a_live_request(self):
        intake = {
            "event_name": "pull_request_target",
            "event_action": "labeled",
            "requested_reviewer": None,
            "requested_target_observed": None,
        }
        value = self.plan(receipt=self.receipt(state="COMMENT_WITH_BLOCKER", review_intake=intake))
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "REQUEST_CHANGES")
        self.assertFalse(value["retraction_only"])

    def test_comment_event_refreshes_a_live_requested_approval(self):
        old = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        intake = {
            "event_name": "issue_comment",
            "event_action": "edited",
            "requested_reviewer": None,
            "requested_target_observed": None,
        }
        value = self.plan(
            receipt=self.receipt(state="APPROVE", review_intake=intake),
            reviews=[old],
        )
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "APPROVE")
        self.assertFalse(value["retraction_only"])

    def test_marked_comment_does_not_mask_the_last_decisive_delegated_approval(self):
        old = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        marked_comment = {
            "id": 2,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'f' * 64} -->",
        }
        intake = {
            "event_name": "issue_comment",
            "event_action": "created",
            "requested_reviewer": None,
            "requested_target_observed": None,
        }
        value = self.plan(
            receipt=self.receipt(state="WAIT", review_intake=intake),
            reviews=[old, marked_comment],
        )
        self.assertTrue(value["effect_permitted"])
        self.assertTrue(value["retraction_only"])

    def test_completed_workflow_run_refreshes_a_live_requested_approval(self):
        old = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
        }
        intake = {
            "event_name": "workflow_run",
            "event_action": "completed",
            "requested_reviewer": None,
            "requested_target_observed": None,
        }
        value = self.plan(receipt=self.receipt(state="APPROVE", review_intake=intake), reviews=[old])
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "APPROVE")
        self.assertFalse(value["retraction_only"])

    def test_same_fingerprint_dismissal_is_idempotent_and_not_overridden(self):
        comment = {
            "id": 1,
            "commit_id": HEAD,
            "state": "DISMISSED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={FINGERPRINT} -->",
        }
        value = self.plan(reviews=[comment])
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT")

    def test_transport_and_reobservation_must_both_be_exact(self):
        transport = self.plan(transport=False)
        reobserved = self.plan(reobserve=False)
        self.assertEqual(transport["first_blocker"], "LEDGER_TRANSPORT_READBACK_MISMATCH")
        self.assertEqual(reobserved["first_blocker"], "CAUSAL_REVIEW_EVIDENCE_DRIFT")

    def test_base_head_tree_and_role_locality_drift_are_blocked(self):
        for pr, commit, expected in (
            (self.pr(base={"ref": "main", "sha": "e" * 40}), self.commit(), "PULL_REQUEST_BASE_DRIFT"),
            (self.pr(number=885), self.commit(), "PULL_REQUEST_NUMBER_DRIFT"),
            (self.pr(head={"sha": "e" * 40, "repo": {"full_name": REPOSITORY}}), self.commit(), "PULL_REQUEST_HEAD_DRIFT"),
            (self.pr(head={"sha": HEAD, "repo": {"full_name": "other/repo"}}), self.commit(), "PULL_REQUEST_HEAD_NOT_ROLE_LOCAL"),
            (self.pr(), self.commit(tree={"sha": "e" * 40}), "PULL_REQUEST_TREE_DRIFT"),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(self.plan(pr=pr, commit=commit)["first_blocker"], expected)

    def test_manual_target_review_is_preserved(self):
        review = {
            "id": 1,
            "commit_id": HEAD,
            "user": {"login": "Goldkelch"},
            "body": "A manual exact-head review.",
        }
        value = self.plan(reviews=[review])
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "MANUAL_TARGET_REVIEW_PRESENT")

    def test_identical_marked_review_is_idempotent(self):
        review = {
            "id": 1,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": f"<!-- {module.MARKER} fingerprint={FINGERPRINT} -->",
        }
        value = self.plan(reviews=[review])
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT")

    def test_plan_seal_rejects_mutation(self):
        value = self.plan()
        value["event"] = "COMMENT"
        with self.assertRaises(module.NativeAccountReviewError):
            module.validate_plan(value)

    def test_signer_preflight_requires_exact_user_permission_and_counterpart(self):
        plan = self.plan()
        good = module.signer_preflight(
            plan=plan,
            expected_signer="Goldkelch",
            pr=self.pr(),
            commit=self.commit(),
            reviews=[],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
        )
        self.assertEqual(good["action"], "POST")
        removed = module.signer_preflight(
            plan=plan,
            expected_signer="Goldkelch",
            pr=self.pr(requested_reviewers=[]),
            commit=self.commit(),
            reviews=[],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
        )
        self.assertEqual(removed["first_blocker"], "PRE_EFFECT_REQUESTED_REVIEWER_DRIFT")
        for user, permission, expected in (
            ({"login": "github-actions[bot]", "type": "Bot"}, "write", "DELEGATED_ACCOUNT_TOKEN_IDENTITY_MISMATCH"),
            ({"login": "Goldkelch", "type": "User"}, "read", "DELEGATED_ACCOUNT_PERMISSION_INSUFFICIENT"),
        ):
            with self.subTest(expected=expected):
                value = module.signer_preflight(
                    plan=plan,
                    expected_signer="Goldkelch",
                    pr=self.pr(),
                    commit=self.commit(),
                    reviews=[],
                    delegation=self.delegation(),
                    token_user=user,
                    collaborator_permission=permission,
                    native_rule_enforced=True,
                    reobservation_exact=True,
                )
                self.assertEqual(value["first_blocker"], expected)

    def test_signer_preflight_preserves_manual_review_and_drift(self):
        plan = self.plan()
        manual = {
            "id": 1, "commit_id": HEAD, "user": {"login": "Goldkelch"}, "body": "manual"
        }
        preserved = module.signer_preflight(
            plan=plan, expected_signer="Goldkelch", pr=self.pr(), commit=self.commit(),
            reviews=[manual], delegation=self.delegation(), token_user={"login": "Goldkelch", "type": "User"}, collaborator_permission="write",
            native_rule_enforced=True, reobservation_exact=True,
        )
        self.assertEqual(preserved["first_blocker"], "MANUAL_TARGET_REVIEW_PRESENT")
        drift = module.signer_preflight(
            plan=plan, expected_signer="Goldkelch", pr=self.pr(head={"sha": "e" * 40, "repo": {"full_name": REPOSITORY}}), commit=self.commit(),
            reviews=[], delegation=self.delegation(), token_user={"login": "Goldkelch", "type": "User"}, collaborator_permission="write",
            native_rule_enforced=True, reobservation_exact=True,
        )
        self.assertEqual(drift["first_blocker"], "PRE_EFFECT_EXACT_BINDING_DRIFT")
        number_drift = module.signer_preflight(
            plan=plan, expected_signer="Goldkelch", pr=self.pr(number=885), commit=self.commit(),
            reviews=[], delegation=self.delegation(), token_user={"login": "Goldkelch", "type": "User"}, collaborator_permission="write",
            native_rule_enforced=True, reobservation_exact=True,
        )
        self.assertEqual(number_drift["first_blocker"], "PRE_EFFECT_EXACT_BINDING_DRIFT")

    def test_signer_rechecks_delegation_rule_and_causal_reobservation(self):
        plan = self.plan()
        shared = {
            "plan": plan, "expected_signer": "Goldkelch", "pr": self.pr(), "commit": self.commit(),
            "reviews": [], "token_user": {"login": "Goldkelch", "type": "User"},
            "collaborator_permission": "write",
        }
        revoked = module.signer_preflight(
            **shared, delegation=self.delegation(state="REVOKED"), native_rule_enforced=True, reobservation_exact=True,
        )
        self.assertEqual(revoked["first_blocker"], "DELEGATION_REVOKED_OR_INACTIVE")
        drifted = module.signer_preflight(
            **shared, delegation=self.delegation(selection={
                "pull_request_author_is_eligible": False, "same_account_self_review": False,
                "chatgpt_native_signing": False, "bot_or_app_identity_substitution": False,
                "revision": 2,
            }), native_rule_enforced=True, reobservation_exact=True,
        )
        self.assertEqual(drifted["first_blocker"], "PRE_EFFECT_DELEGATION_DRIFT")
        rules = module.signer_preflight(
            **shared, delegation=self.delegation(), native_rule_enforced=False, reobservation_exact=True,
        )
        self.assertEqual(rules["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")
        causal = module.signer_preflight(
            **shared, delegation=self.delegation(), native_rule_enforced=True, reobservation_exact=False,
        )
        self.assertEqual(causal["first_blocker"], "PRE_EFFECT_CAUSAL_REOBSERVATION_DRIFT")

    def test_readback_requires_exact_platform_identity_event_and_binding(self):
        plan = self.plan()
        review = {
            "id": 12,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
        }
        self.assertTrue(module.verify_review_readback(plan=plan, review=review, expected_signer="Goldkelch")["exact"])
        wrong = copy.deepcopy(review)
        wrong["user"]["login"] = "ingolf-lohmann"
        self.assertFalse(module.verify_review_readback(plan=plan, review=wrong, expected_signer="Goldkelch")["exact"])

    def test_no_secret_field_is_emitted_in_plan(self):
        serialized = str(self.plan()).lower()
        self.assertNotIn("token", serialized)
        self.assertNotIn("secret", serialized)

    def test_workflow_keeps_technical_executor_secret_free_and_signers_separate(self):
        technical = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/qikvrt_required_review_gate.yml").read_text(encoding="utf-8")
        self.assertNotIn("QIKVRT_GOLDKELCH_REVIEW_TOKEN", technical)
        self.assertNotIn("QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN", technical)
        self.assertIn("plan-native-account-review:", workflow)
        self.assertIn("QIKVRT_GOLDKELCH_REVIEW_TOKEN", workflow)
        self.assertIn("QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN", workflow)
        self.assertIn("QIKVRT_NATIVE_ACCOUNT_REVIEW_ACTIVATION", workflow)
        self.assertIn("gh api user", workflow)
        self.assertIn('GH_TOKEN="$ACCOUNT_TOKEN" gh api --method POST', workflow)
        self.assertIn("verify-readback", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("run.get('workflow_id') != workflow.get('id')", workflow)
        self.assertIn("allowed_events={'pull_request_target','issue_comment','workflow_run','workflow_dispatch'}", workflow)
        self.assertIn("IMMUTABLE_EXECUTOR_ARTIFACT_RETRACTION_ONLY", workflow)
        self.assertIn("executor artifact name and receipt binding differ", workflow)
        self.assertIn("executor receipt event provenance differs from the trusted run", workflow)
        self.assertIn("PRE_EFFECT_REQUESTED_REVIEWER_DRIFT", (ROOT / "tools/qikvrt_native_account_review.py").read_text(encoding="utf-8"))
        self.assertIn("run.get('path') != trusted_path", workflow)
        self.assertIn("executor ledger commit is not reachable", workflow)
        self.assertEqual(workflow.count('tools/qikvrt_requested_review_executor.py verify'), 3)
        self.assertEqual(workflow.count('--reobservation-exact true'), 3)
        self.assertEqual(workflow.count('--delegation state/authorization/delegations/OWNER_NATIVE_ACCOUNT_REVIEW_AUTOMATION_V1.json'), 1)
        self.assertEqual(workflow.count('--delegation "$root/current-delegation.json"'), 2)
        self.assertEqual(workflow.count('OWNER_NATIVE_ACCOUNT_REVIEW_AUTOMATION_V1.json?ref=main'), 2)
        self.assertIn('artifact/review.json', workflow)
        self.assertIn('artifact/review.diff', workflow)
        self.assertIn('artifact/ledger-write.json', workflow)
        self.assertNotIn('artifact/.qikvrt/mesh-review/review.json', workflow)
        self.assertNotIn('find "$root/artifact" -type f -name review.json', workflow)
        gold = workflow.split("  native-account-review-as-goldkelch:", 1)[1].split("  native-account-review-as-ingolf-lohmann:", 1)[0]
        ingolf = workflow.split("  native-account-review-as-ingolf-lohmann:", 1)[1]
        self.assertIn("QIKVRT_GOLDKELCH_REVIEW_TOKEN", gold)
        self.assertNotIn("QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN", gold)
        self.assertIn("QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN", ingolf)
        self.assertNotIn("QIKVRT_GOLDKELCH_REVIEW_TOKEN", ingolf)


if __name__ == "__main__":
    unittest.main()
