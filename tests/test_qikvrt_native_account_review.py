# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import json
import os
import pathlib
import subprocess
import unittest

from tools import qikvrt_native_account_review as module


BASE = "a" * 40
HEAD = "b" * 40
TREE = "c" * 40
FINGERPRINT = "d" * 64
REPOSITORY = "Goldkelch/qik-vrt"
SIGNER_RUN_ID = 8123
SIGNER_RUN_ATTEMPT = 2
SIGNER_EVALUATOR = "f" * 40
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

    def receipt(
        self,
        *,
        state="TECHNICAL_CONTINUE",
        requested="Goldkelch",
        **overrides,
    ):
        value = {
            "schema": module.RECEIPT_SCHEMA,
            "repository": REPOSITORY,
            "pr_number": 884,
            "base_sha": BASE,
            "head_sha": HEAD,
            "tree_sha": TREE,
            "evidence_fingerprint": FINGERPRINT,
            "state": state,
            "mesh_disposition": state,
            "review_intake": {
                "event_name": "pull_request_target",
                "event_action": "review_requested",
                "requested_reviewer": requested,
                "requested_target_observed": True,
            },
        }
        value.update(overrides)
        return value

    def executor_run(self, *, run_id=7001, run_attempt=2, **overrides):
        value = {"id": run_id, "run_attempt": run_attempt}
        value.update(overrides)
        return value

    def executor_artifact(
        self,
        *,
        artifact_id=9001,
        run_id=7001,
        run_attempt=2,
        name=None,
    ):
        if name is None:
            name = (
                f"qikvrt-mesh-review-pr-884-{HEAD}-{FINGERPRINT}"
                f"-run-{run_id}-attempt-{run_attempt}"
            )
        return {
            "id": artifact_id,
            "name": name,
            "expired": False,
            "digest": "sha256:" + "d" * 64,
            "archive_download_url": (
                f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/"
                f"{artifact_id}/zip"
            ),
        }

    def delegated_review(
        self,
        *,
        review_id=1,
        fingerprint="e" * 64,
        state="COMMENTED",
        submitted_at=None,
    ):
        event = {
            "APPROVED": module.TECHNICAL_CONTINUE,
            "COMMENTED": module.TECHNICAL_CONTINUE,
            "CHANGES_REQUESTED": "REQUEST_CHANGES",
        }[state]
        value = {
            "id": review_id,
            "commit_id": HEAD,
            "state": state,
            "user": {"login": "Goldkelch"},
            "body": module._delegated_review_body(
                base_sha=BASE,
                head_sha=HEAD,
                tree_sha=TREE,
                fingerprint=fingerprint,
                disposition=(
                    module.TECHNICAL_CONTINUE
                    if state in {"APPROVED", "COMMENTED"}
                    else "REQUEST_CHANGES"
                ),
                reviewer="Goldkelch",
                event=event,
                stale_approval_retraction=False,
                retraction_only=False,
                signer_run_id=SIGNER_RUN_ID,
                signer_run_attempt=SIGNER_RUN_ATTEMPT,
                signer_evaluator_sha=SIGNER_EVALUATOR,
            ),
        }
        if submitted_at is not None:
            value["submitted_at"] = submitted_at
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
            "activation_boundary": {
                "external_configuration_verified": True,
                "external_readback_receipt": {
                    "schema": "qikvrt_native_review_secret_environment_readback_v1",
                    "environment": module.SECRET_ENVIRONMENT,
                    "deployment_branch_policy": "SELECTED_BRANCHES_ONLY",
                    "selected_branch": "main",
                    "protected_branches": True,
                    "environment_secret_names": list(
                        module.SECRET_ENVIRONMENT_NAMES
                    ),
                    "repository_scope_secret_names_absent": list(
                        module.FORBIDDEN_BROAD_SECRET_NAMES
                    ),
                    "repository_owner": {
                        "login": "Goldkelch",
                        "id": 1001,
                        "type": "User",
                    },
                    "organization_scope_secret_names_absent": [],
                    "organization_scope_readback": "NOT_APPLICABLE_USER_OWNER",
                    "settings_readback_complete": True,
                    "verified_at": "2026-09-01T09:00:00Z",
                    "verifier_login": "authority-admin",
                },
            },
        }
        value.update(overrides)
        return value

    def plan(self, *, pr=None, commit=None, receipt=None, reviews=(), delegation=None, rule=True, transport=True, reobserve=True, signer_run_id=SIGNER_RUN_ID, signer_run_attempt=SIGNER_RUN_ATTEMPT, signer_evaluator=SIGNER_EVALUATOR):
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
            signer_run_id=signer_run_id,
            signer_run_attempt=signer_run_attempt,
            signer_evaluator_sha=signer_evaluator,
        )

    def authority_fence(self, plan=None, **overrides):
        value = self.plan() if plan is None else plan
        upstream = {
            "schema": "qikvrt_current_executor_attempt_reobservation_v1",
            "exact": True,
            "run_id": 7001,
            "run_attempt": 2,
            "artifact_id": 9001,
            "artifact_name": "qikvrt-mesh-review-pr-884-artifact",
            "trusted_main_sha": SIGNER_EVALUATOR,
        }
        delegation = (
            json.dumps(self.delegation(), sort_keys=True, indent=2) + "\n"
        ).encode()
        inputs = {
            "plan": value,
            "evaluator_sha": SIGNER_EVALUATOR,
            "current_main": {"sha": SIGNER_EVALUATOR},
            "upstream_before": upstream,
            "upstream_after": dict(upstream),
            "rules_before": [{"type": "pull_request"}],
            "rules_after": [{"type": "pull_request"}],
            "delegation_before": delegation,
            "delegation_after": delegation,
            "final_pr": self.pr(),
            "final_commit": self.commit(),
        }
        inputs.update(overrides)
        return module.build_signer_post_effect_authority_fence(**inputs)

    def test_review_page_inventory_is_strict_and_duplicate_safe(self):
        first = self.delegated_review(
            review_id=11, submitted_at="2026-09-01T09:00:00Z"
        )
        second = self.delegated_review(
            review_id=12, submitted_at="2026-09-01T09:01:00Z"
        )
        self.assertEqual(
            [item["id"] for item in module.flatten_review_pages([[first], [second]])],
            [11, 12],
        )
        invalid = (
            {},
            [],
            [[first], {"unexpected": "object-page"}],
            [[first], [first]],
            [[dict(first, id=0)]],
            [["not-a-review"]],
        )
        for pages in invalid:
            with self.subTest(pages=pages), self.assertRaises(
                module.NativeAccountReviewError
            ):
                module.flatten_review_pages(pages)

    def test_plan_and_preflight_reject_noncanonical_review_inventory(self):
        duplicate = [
            self.delegated_review(review_id=11),
            self.delegated_review(review_id=11),
        ]
        with self.assertRaisesRegex(
            module.NativeAccountReviewError, "invalid or duplicate review id"
        ):
            self.plan(reviews=duplicate)
        plan = self.plan()
        with self.assertRaisesRegex(
            module.NativeAccountReviewError, "invalid or duplicate review id"
        ):
            module.signer_preflight(
                plan=plan,
                expected_signer="Goldkelch",
                pr=self.pr(),
                commit=self.commit(),
                reviews=duplicate,
                delegation=self.delegation(),
                token_user={"login": "Goldkelch", "type": "User"},
                collaborator_permission="admin",
                native_rule_enforced=True,
                reobservation_exact=True,
            )

    def test_ingolf_author_selects_goldkelch_for_exact_technical_comment(self):
        value = self.plan()
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["reviewer"], "Goldkelch")
        self.assertEqual(value["event"], module.TECHNICAL_CONTINUE)
        self.assertIn(module.MARKER, value["review_body"])
        self.assertIn(
            "- Technical disposition: `TECHNICAL_CONTINUE`",
            value["review_body"],
        )
        self.assertFalse(value["independent_natural_person_review"])
        self.assertNotIn("manual_review_preserved", value)
        self.assertEqual(value["manual_review_guard"], module.MANUAL_REVIEW_GUARD)
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
                self.assertEqual(value["event"], module.TECHNICAL_CONTINUE)
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

    def test_technical_comment_requires_platform_freshness_rules(self):
        value = self.plan(rule=False)
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_request_changes_can_be_projected_without_approval_rule(self):
        value = self.plan(receipt=self.receipt(state="REQUEST_CHANGES"), rule=False)
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], "REQUEST_CHANGES")

    def test_comment_with_blocker_preserves_manual_same_account_review(self):
        old = self.delegated_review(state="APPROVED")
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
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "MANUAL_TARGET_REVIEW_PRESENT")

    def test_legacy_approval_is_predecessor_only_and_manual_review_is_preserved(self):
        old = self.delegated_review(state="APPROVED")
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
        self.assertFalse(plan["effect_permitted"])
        self.assertFalse(plan["stale_approval_retraction"])
        self.assertEqual(plan["first_blocker"], "MANUAL_TARGET_REVIEW_PRESENT")

    def test_later_manual_decisive_review_beats_a_higher_review_id(self):
        old = self.delegated_review(
            review_id=2, submitted_at="2026-08-25T14:00:00Z"
        )
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

    def test_unverified_or_incomplete_secret_environment_is_authority_hold(self):
        cases = []
        unverified = self.delegation()
        unverified["activation_boundary"] = {
            "external_configuration_verified": False,
            "external_readback_receipt": None,
        }
        cases.append(unverified)
        forbidden_fallback = self.delegation()
        forbidden_fallback["activation_boundary"]["external_readback_receipt"][
            "repository_scope_secret_names_absent"
        ] = []
        cases.append(forbidden_fallback)
        incomplete_or_forbidden = self.delegation()
        incomplete_or_forbidden["activation_boundary"]["external_readback_receipt"][
            "settings_readback_complete"
        ] = False
        cases.append(incomplete_or_forbidden)
        false_user_org_inventory = self.delegation()
        false_user_org_inventory["activation_boundary"]["external_readback_receipt"][
            "organization_scope_readback"
        ] = "VERIFIED_ORGANIZATION_SECRET_INVENTORY"
        false_user_org_inventory["activation_boundary"]["external_readback_receipt"][
            "organization_scope_secret_names_absent"
        ] = list(module.FORBIDDEN_BROAD_SECRET_NAMES)
        cases.append(false_user_org_inventory)
        for delegation in cases:
            with self.subTest(delegation=delegation):
                value = self.plan(delegation=delegation)
                self.assertFalse(value["effect_permitted"])
                self.assertEqual(
                    value["first_blocker"],
                    "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED",
                )

    def test_wait_never_creates_native_account_effect(self):
        value = self.plan(receipt=self.receipt(state="WAIT"))
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["event"], module.NO_EFFECT)
        self.assertEqual(value["first_blocker"], "MESH_DISPOSITION_NOT_DECISIVE")

    def test_legacy_technical_approve_never_maps_to_native_approval(self):
        value = self.plan(receipt=self.receipt(state="APPROVE"))
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["event"], module.NO_EFFECT)
        self.assertEqual(
            value["first_blocker"], "LEGACY_TECHNICAL_APPROVE_RECEIPT"
        )

    def test_policy_and_delegation_forbid_automated_approval_authority(self):
        policy = json.loads(
            (ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json")
            .read_text(encoding="utf-8")
        )
        automation = policy["review_lifecycle"]["account_identity_rule"][
            "delegated_native_account_automation"
        ]
        self.assertEqual(
            automation["technical_continue_projection"],
            "COMMENT_ONLY_NON_DECISIVE",
        )
        self.assertNotIn("APPROVE", automation["may_submit"])
        self.assertEqual(
            automation["required_gate_success_source"],
            "CURRENT_HEAD_UNMARKED_HUMAN_APPROVED_NON_AUTHOR_CODE_OWNER_ONLY",
        )
        delegation = json.loads(
            (
                ROOT
                / "state/authorization/delegations/OWNER_NATIVE_ACCOUNT_REVIEW_AUTOMATION_V1.json"
            ).read_text(encoding="utf-8")
        )
        semantics = delegation["identity_semantics"]
        self.assertEqual(semantics["technical_continue_platform_event"], "COMMENT")
        self.assertFalse(
            semantics["automation_marked_review_may_satisfy_required_gate"]
        )
        self.assertTrue(
            semantics["required_gate_success_requires_unmarked_human_approved_review"]
        )

    def test_wait_never_retracts_a_legacy_marked_approval(self):
        old = self.delegated_review(state="APPROVED")
        value = self.plan(receipt=self.receipt(state="WAIT"), reviews=[old])
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["event"], module.NO_EFFECT)
        self.assertEqual(value["first_blocker"], "MESH_DISPOSITION_NOT_DECISIVE")

    def test_exact_removed_request_does_not_retract_a_legacy_marked_approval(self):
        old = self.delegated_review(state="APPROVED")
        intake = {
            "event_name": "pull_request_target",
            "event_action": "review_request_removed",
            "requested_reviewer": "Goldkelch",
            "requested_target_observed": None,
        }
        value = self.plan(
            pr=self.pr(requested_reviewers=[]),
            receipt=self.receipt(
                state=module.TECHNICAL_CONTINUE,
                review_intake=intake,
            ),
            reviews=[old],
        )
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["event"], module.NO_EFFECT)
        self.assertEqual(value["first_blocker"], "REVIEW_REQUEST_EVENT_NOT_EXACT")

    def test_delayed_removed_delivery_cannot_override_live_rerequest(self):
        old = self.delegated_review()
        intake = {
            "event_name": "pull_request_target",
            "event_action": "review_request_removed",
            "requested_reviewer": "Goldkelch",
            "requested_target_observed": None,
        }
        value = self.plan(
            receipt=self.receipt(
                state=module.TECHNICAL_CONTINUE,
                review_intake=intake,
            ),
            reviews=[old],
        )
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(
            value["first_blocker"],
            "STALE_REVIEW_REQUEST_REMOVAL_LIVE_TARGET_PRESENT",
        )

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

    def test_comment_event_refreshes_a_live_requested_observation(self):
        old = self.delegated_review()
        intake = {
            "event_name": "issue_comment",
            "event_action": "edited",
            "requested_reviewer": None,
            "requested_target_observed": None,
        }
        value = self.plan(
            receipt=self.receipt(
                state=module.TECHNICAL_CONTINUE,
                review_intake=intake,
            ),
            reviews=[old],
        )
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], module.TECHNICAL_CONTINUE)
        self.assertFalse(value["retraction_only"])

    def test_marked_comment_never_renews_a_legacy_marked_approval(self):
        old = self.delegated_review(state="APPROVED")
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
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["event"], module.NO_EFFECT)
        self.assertEqual(value["first_blocker"], "MESH_DISPOSITION_NOT_DECISIVE")

    def test_completed_workflow_run_refreshes_a_live_requested_observation(self):
        old = self.delegated_review()
        intake = {
            "event_name": "workflow_run",
            "event_action": "completed",
            "requested_reviewer": None,
            "requested_target_observed": None,
        }
        value = self.plan(
            receipt=self.receipt(
                state=module.TECHNICAL_CONTINUE,
                review_intake=intake,
            ),
            reviews=[old],
        )
        self.assertTrue(value["effect_permitted"])
        self.assertEqual(value["event"], module.TECHNICAL_CONTINUE)
        self.assertFalse(value["retraction_only"])

    def test_same_fingerprint_dismissal_is_idempotent_and_not_overridden(self):
        original = self.plan()
        comment = {
            "id": 1,
            "commit_id": HEAD,
            "state": "DISMISSED",
            "user": {"login": "Goldkelch"},
            "body": original["review_body"],
        }
        value = self.plan(reviews=[comment])
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(
            value["first_blocker"],
            "DISMISSED_REVIEW_REQUIRES_AUTHORITY_REOBSERVATION",
        )

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
        original = self.plan()
        review = {
            "id": 1,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch"},
            "body": original["review_body"],
        }
        value = self.plan(reviews=[review])
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(value["first_blocker"], "IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT")

    def test_remove_then_rerequest_same_fingerprint_supersedes_exact_negative(self):
        negative = self.plan(receipt=self.receipt(state="REQUEST_CHANGES"))
        self.assertEqual(negative["event"], "REQUEST_CHANGES")
        review = {
            "id": 1,
            "commit_id": HEAD,
            "state": "CHANGES_REQUESTED",
            "user": {"login": "Goldkelch"},
            "body": negative["review_body"],
        }
        renewed = self.plan(reviews=[review])
        self.assertTrue(renewed["effect_permitted"])
        self.assertEqual(renewed["event"], module.TECHNICAL_CONTINUE)

    def test_modified_delegated_body_is_authority_hold_not_duplicate(self):
        original = self.plan()
        review = {
            "id": 1,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch"},
            "body": original["review_body"] + "\nmodified",
        }
        value = self.plan(reviews=[review])
        self.assertFalse(value["effect_permitted"])
        self.assertEqual(
            value["first_blocker"],
            "DELEGATED_ACCOUNT_REVIEW_BODY_OR_STATE_DRIFT",
        )

    def test_cancel_after_exact_post_allows_only_controlled_later_attempt_supersession(self):
        plan = self.plan()
        posted = {
            "id": 17,
            "submitted_at": "2026-09-01T08:00:02Z",
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
        }
        result = module.signer_preflight(
            plan=plan,
            expected_signer="Goldkelch",
            pr=self.pr(),
            commit=self.commit(),
            reviews=[posted],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
        )
        self.assertEqual(result["action"], module.NO_EFFECT)
        self.assertEqual(
            result["first_blocker"],
            "IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT",
        )
        retry = module.signer_preflight(
            plan=plan,
            expected_signer="Goldkelch",
            # GitHub may remove a reviewer from this list after a submitted
            # review. The
            # missing request may authorize adoption only of the exact review
            # posted by the earlier attempt; it never authorizes a fresh POST.
            pr=self.pr(requested_reviewers=[]),
            commit=self.commit(),
            reviews=[posted],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
            current_signer_run_id=SIGNER_RUN_ID,
            current_signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
            current_signer_evaluator_sha=SIGNER_EVALUATOR,
        )
        self.assertEqual(retry["action"], "ADOPT_UNRECEIPTED")
        self.assertEqual(retry["review_id"], posted["id"])

        adopted = module.verify_review_adoption_readback(
            plan=plan,
            review=posted,
            expected_signer="Goldkelch",
            reviews_before=[posted],
            reviews_after=[posted],
            current_signer_run_id=SIGNER_RUN_ID,
            current_signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
        )
        self.assertTrue(adopted["exact"])
        self.assertEqual(adopted["effect_mode"], "ADOPT_UNRECEIPTED")
        self.assertEqual(adopted["new_review_ids"], [])
        receipt = module.build_signer_receipt(
            plan=plan,
            review=posted,
            expected_signer="Goldkelch",
            reviews_before=[posted],
            reviews_after=[posted],
            readback=adopted,
            final_pr=self.pr(requested_reviewers=[]),
            final_commit=self.commit(),
            authority_fence=self.authority_fence(plan),
            repository=REPOSITORY,
            evaluator_sha=SIGNER_EVALUATOR,
            run_id=SIGNER_RUN_ID,
            run_attempt=SIGNER_RUN_ATTEMPT + 1,
        )
        self.assertEqual(
            receipt["effect_readback"]["effect_mode"],
            "ADOPT_UNRECEIPTED",
        )
        self.assertEqual(receipt["review_ordering"]["new_review_ids"], [])

        manual = dict(
            posted,
            id=18,
            state="COMMENTED",
            body="manual same-account review",
            submitted_at="2026-09-01T08:00:03Z",
        )
        blocked = module.signer_preflight(
            plan=plan,
            expected_signer="Goldkelch",
            pr=self.pr(),
            commit=self.commit(),
            reviews=[posted, manual],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
            current_signer_run_id=SIGNER_RUN_ID,
            current_signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
            current_signer_evaluator_sha=SIGNER_EVALUATOR,
        )
        self.assertEqual(blocked["first_blocker"], "MANUAL_TARGET_REVIEW_PRESENT")

    def test_unreceipted_adoption_blocks_later_decisive_or_history_drift(self):
        plan = self.plan()
        posted = {
            "id": 17,
            "submitted_at": "2026-09-01T08:00:02Z",
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
        }
        later = self.delegated_review(
            review_id=18,
            fingerprint=FINGERPRINT,
            state="CHANGES_REQUESTED",
            submitted_at="2026-09-01T08:00:03Z",
        )
        later["user"]["type"] = "User"
        blocked = module.signer_preflight(
            plan=plan,
            expected_signer="Goldkelch",
            pr=self.pr(requested_reviewers=[]),
            commit=self.commit(),
            reviews=[posted, later],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
            current_signer_run_id=SIGNER_RUN_ID,
            current_signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
            current_signer_evaluator_sha=SIGNER_EVALUATOR,
        )
        self.assertEqual(
            blocked["first_blocker"],
            "UNRECEIPTED_DELEGATED_REVIEW_ORDER_DRIFT",
        )
        readback = module.verify_review_adoption_readback(
            plan=plan,
            review=posted,
            expected_signer="Goldkelch",
            reviews_before=[posted],
            reviews_after=[posted, later],
            current_signer_run_id=SIGNER_RUN_ID,
            current_signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
        )
        self.assertFalse(readback["exact"])
        self.assertEqual(readback["first_blocker"], "ADOPTION_REVIEW_HISTORY_DRIFT")

    def test_full_workflow_rerun_adopts_prior_attempt_review_without_post(self):
        attempt_one_plan = self.plan()
        posted = {
            "id": 27,
            "submitted_at": "2026-09-01T08:00:02Z",
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": attempt_one_plan["review_body"],
        }
        attempt_two_plan = self.plan(
            pr=self.pr(requested_reviewers=[]),
            reviews=[posted],
            signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
        )
        self.assertTrue(attempt_two_plan["effect_permitted"])
        self.assertNotEqual(
            attempt_two_plan["review_body"], attempt_one_plan["review_body"]
        )
        self.assertEqual(
            attempt_two_plan["review_body"].split("\n", 1)[1],
            attempt_one_plan["review_body"].split("\n", 1)[1],
        )
        preflight = module.signer_preflight(
            plan=attempt_two_plan,
            expected_signer="Goldkelch",
            pr=self.pr(requested_reviewers=[]),
            commit=self.commit(),
            reviews=[posted],
            delegation=self.delegation(),
            token_user={"login": "Goldkelch", "type": "User"},
            collaborator_permission="write",
            native_rule_enforced=True,
            reobservation_exact=True,
            current_signer_run_id=SIGNER_RUN_ID,
            current_signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
            current_signer_evaluator_sha=SIGNER_EVALUATOR,
        )
        self.assertEqual(preflight["action"], "ADOPT_UNRECEIPTED")
        self.assertEqual(preflight["review"]["body"], attempt_one_plan["review_body"])
        readback = module.verify_review_adoption_readback(
            plan=attempt_two_plan,
            review=posted,
            expected_signer="Goldkelch",
            reviews_before=[posted],
            reviews_after=[posted],
            current_signer_run_id=SIGNER_RUN_ID,
            current_signer_run_attempt=SIGNER_RUN_ATTEMPT + 1,
        )
        receipt = module.build_signer_receipt(
            plan=attempt_two_plan,
            review=posted,
            expected_signer="Goldkelch",
            reviews_before=[posted],
            reviews_after=[posted],
            readback=readback,
            final_pr=self.pr(requested_reviewers=[]),
            final_commit=self.commit(),
            authority_fence=self.authority_fence(attempt_two_plan),
            repository=REPOSITORY,
            evaluator_sha=SIGNER_EVALUATOR,
            run_id=SIGNER_RUN_ID,
            run_attempt=SIGNER_RUN_ATTEMPT + 1,
        )
        self.assertEqual(receipt["origin_run_attempt"], SIGNER_RUN_ATTEMPT)
        self.assertEqual(receipt["run_attempt"], SIGNER_RUN_ATTEMPT + 1)

    def test_new_run_or_evaluator_can_supersede_only_the_canonical_locator(self):
        old = self.plan()
        posted = {
            "id": 17,
            "submitted_at": "2026-09-01T08:00:02Z",
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch"},
            "body": old["review_body"],
        }
        advanced = self.plan(
            reviews=[posted],
            signer_run_id=SIGNER_RUN_ID + 1,
            signer_run_attempt=1,
            signer_evaluator="0" * 40,
        )
        self.assertTrue(advanced["effect_permitted"])
        self.assertNotEqual(advanced["review_body"], old["review_body"])
        self.assertEqual(
            advanced["review_body"].split("\n", 1)[1],
            old["review_body"].split("\n", 1)[1],
        )

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
        self.assertEqual(plan["event"], module.TECHNICAL_CONTINUE)
        self.assertEqual(good["event"], "COMMENT")
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

    def test_final_preflight_rejects_state_that_changed_after_earlier_observation(self):
        plan = self.plan()
        common = {
            "plan": plan,
            "expected_signer": "Goldkelch",
            "commit": self.commit(),
            "delegation": self.delegation(),
            "token_user": {"login": "Goldkelch", "type": "User"},
            "collaborator_permission": "write",
            "native_rule_enforced": True,
            "reobservation_exact": True,
        }
        earlier = module.signer_preflight(pr=self.pr(), reviews=[], **common)
        self.assertEqual(earlier["action"], "POST")

        removed = module.signer_preflight(
            pr=self.pr(requested_reviewers=[]), reviews=[], **common
        )
        self.assertEqual(
            removed["first_blocker"], "PRE_EFFECT_REQUESTED_REVIEWER_DRIFT"
        )

        manual = {
            "id": 19,
            "submitted_at": "2026-09-01T08:00:01Z",
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch"},
            "body": "manual decisive review after the earlier observation",
        }
        superseded = module.signer_preflight(
            pr=self.pr(), reviews=[manual], **common
        )
        self.assertEqual(
            superseded["first_blocker"], "MANUAL_TARGET_REVIEW_PRESENT"
        )

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
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
            "submitted_at": "2026-09-01T08:00:02Z",
        }
        readback = module.verify_review_readback(
            plan=plan,
            review=review,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[review],
        )
        self.assertTrue(readback["exact"])
        self.assertEqual(readback["review_id"], 12)
        self.assertEqual(readback["state"], "COMMENTED")
        self.assertEqual(readback["commit_id"], HEAD)
        self.assertEqual(readback["new_review_ids"], [12])
        wrong = copy.deepcopy(review)
        wrong["user"]["login"] = "ingolf-lohmann"
        self.assertFalse(
            module.verify_review_readback(
                plan=plan,
                review=wrong,
                expected_signer="Goldkelch",
                reviews_before=[],
                reviews_after=[wrong],
            )["exact"]
        )
        tampered_bodies = (
            plan["review_body"] + "\nPASS FINAL_PASS publication EFFECT_ACK_DONE",
            "APPROVED publication\n" + plan["review_body"],
            plan["review_body"] + "\u200b",
        )
        for body in tampered_bodies:
            with self.subTest(body_tamper=body[:24]):
                tampered = copy.deepcopy(review)
                tampered["body"] = body
                result = module.verify_review_readback(
                    plan=plan,
                    review=tampered,
                    expected_signer="Goldkelch",
                    reviews_before=[],
                    reviews_after=[tampered],
                )
                self.assertFalse(result["exact"])
                self.assertEqual(
                    result["first_blocker"],
                    "DELEGATED_ACCOUNT_REVIEW_READBACK_MISMATCH",
                )

    def test_readback_blocks_concurrent_manual_decisive_review(self):
        plan = self.plan()
        submitted = {
            "id": 13,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
            "submitted_at": "2026-09-01T08:00:03Z",
        }
        manual = {
            "id": 12,
            "commit_id": HEAD,
            "state": "CHANGES_REQUESTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": "manual concurrent disposition",
            "submitted_at": "2026-09-01T08:00:02Z",
        }
        result = module.verify_review_readback(
            plan=plan,
            review=submitted,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[manual, submitted],
        )
        self.assertFalse(result["exact"])
        self.assertEqual(
            result["first_blocker"], "CONCURRENT_MANUAL_TARGET_REVIEW"
        )
        self.assertEqual(result["concurrent_review_id"], 12)

    def test_readback_blocks_concurrent_manual_commented_review(self):
        plan = self.plan()
        submitted = {
            "id": 21,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
            "submitted_at": "2026-09-01T08:00:03Z",
        }
        manual_comment = {
            "id": 20,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": "manual comment during the final GET-to-POST window",
            "submitted_at": "2026-09-01T08:00:02Z",
        }
        result = module.verify_review_readback(
            plan=plan,
            review=submitted,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[manual_comment, submitted],
        )
        self.assertFalse(result["exact"])
        self.assertEqual(
            result["first_blocker"], "CONCURRENT_MANUAL_TARGET_REVIEW"
        )
        self.assertEqual(result["concurrent_review_state"], "COMMENTED")

    def test_successful_signer_receipt_binds_job_run_review_and_order(self):
        plan = self.plan()
        producer_attempt = SIGNER_RUN_ATTEMPT + 1
        submitted = {
            "id": 31,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
            "submitted_at": "2026-09-01T08:00:03Z",
        }
        readback = module.verify_review_readback(
            plan=plan,
            review=submitted,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[submitted],
        )
        receipt = module.build_signer_receipt(
            plan=plan,
            review=submitted,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[submitted],
            readback=readback,
            final_pr=self.pr(),
            final_commit=self.commit(),
            authority_fence=self.authority_fence(plan),
            repository=REPOSITORY,
            evaluator_sha=SIGNER_EVALUATOR,
            run_id=SIGNER_RUN_ID,
            run_attempt=producer_attempt,
        )
        workflow = {
            "id": 44,
            "path": module.TRUSTED_SIGNER_WORKFLOW_PATH,
        }
        run = {
            "id": SIGNER_RUN_ID,
            "run_attempt": producer_attempt,
            "workflow_id": workflow["id"],
            "path": module.TRUSTED_SIGNER_WORKFLOW_PATH + "@refs/heads/main",
            "repository": {"full_name": REPOSITORY},
            "event": "workflow_run",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": SIGNER_EVALUATOR,
        }
        jobs = [{
            "id": 55,
            "name": "native-account-review-as-Goldkelch",
            "run_id": SIGNER_RUN_ID,
            "run_attempt": producer_attempt,
            "status": "completed",
            "conclusion": "success",
        }]
        validated = module.validate_signer_receipt(
            receipt,
            review=submitted,
            current_reviews=[submitted],
            repository=REPOSITORY,
            evaluator_sha=SIGNER_EVALUATOR,
            run=run,
            workflow=workflow,
            jobs=jobs,
            artifact_name=receipt["artifact_name"],
        )
        self.assertEqual(validated["review"]["id"], 31)
        self.assertTrue(validated["effect_readback"]["exact"])
        self.assertTrue(validated["post_effect_authority_fence"]["exact"])

        cancelled = dict(run, conclusion="cancelled")
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "SIGNER_RECEIPT_WORKFLOW_RUN_NOT_SUCCESSFUL",
        ):
            module.validate_signer_receipt(
                receipt,
                review=submitted,
                current_reviews=[submitted],
                repository=REPOSITORY,
                evaluator_sha=SIGNER_EVALUATOR,
                run=cancelled,
                workflow=workflow,
                jobs=jobs,
                artifact_name=receipt["artifact_name"],
            )

        for drift in (
            dict(run, path=".github/workflows/untrusted.yml@refs/heads/main"),
            dict(run, head_sha="0" * 40),
        ):
            with self.assertRaisesRegex(
                module.NativeAccountReviewError,
                "SIGNER_RECEIPT_WORKFLOW_RUN_NOT_SUCCESSFUL",
            ):
                module.validate_signer_receipt(
                    receipt,
                    review=submitted,
                    current_reviews=[submitted],
                    repository=REPOSITORY,
                    evaluator_sha=SIGNER_EVALUATOR,
                    run=drift,
                    workflow=workflow,
                    jobs=jobs,
                    artifact_name=receipt["artifact_name"],
                )

        manual = {
            "id": 30,
            "commit_id": HEAD,
            "state": "CHANGES_REQUESTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": "manual final-window review",
            "submitted_at": "2026-09-01T08:00:02Z",
        }
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "SIGNER_RECEIPT_MANUAL_REVIEW_CONFLICT",
        ):
            module.validate_signer_receipt(
                receipt,
                review=submitted,
                current_reviews=[manual, submitted],
                repository=REPOSITORY,
                evaluator_sha=SIGNER_EVALUATOR,
                run=run,
                workflow=workflow,
                jobs=jobs,
                artifact_name=receipt["artifact_name"],
            )

    def test_post_effect_signer_authority_fence_rejects_every_mutable_boundary(self):
        plan = self.plan()
        upstream = {
            "schema": "qikvrt_current_executor_attempt_reobservation_v1",
            "exact": True,
            "run_id": 7001,
            "run_attempt": 2,
            "artifact_id": 9001,
            "artifact_name": "qikvrt-mesh-review-pr-884-artifact",
            "trusted_main_sha": SIGNER_EVALUATOR,
        }
        changed_delegation = (
            json.dumps(
                self.delegation(state="REVOKED"), sort_keys=True, indent=2
            )
            + "\n"
        ).encode()
        cases = (
            (
                "main",
                {"current_main": {"sha": "0" * 40}},
                "SIGNER_POST_EFFECT_MAIN_DRIFT",
            ),
            (
                "upstream",
                {"upstream_after": dict(upstream, run_attempt=3)},
                "SIGNER_POST_EFFECT_UPSTREAM_DRIFT",
            ),
            (
                "rules",
                {"rules_after": []},
                "SIGNER_POST_EFFECT_RULES_DRIFT",
            ),
            (
                "delegation",
                {"delegation_after": changed_delegation},
                "SIGNER_POST_EFFECT_DELEGATION_DRIFT",
            ),
            (
                "head",
                {"final_pr": self.pr(head={"sha": "0" * 40})},
                "SIGNER_POST_EFFECT_SUBJECT_DRIFT",
            ),
        )
        for label, overrides, blocker in cases:
            with self.subTest(label=label), self.assertRaisesRegex(
                module.NativeAccountReviewError, blocker
            ):
                self.authority_fence(plan, **overrides)

    def test_signer_receipt_cannot_be_sealed_after_failed_readback(self):
        plan = self.plan()
        submitted = {
            "id": 31,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
            "submitted_at": "2026-09-01T08:00:03Z",
        }
        manual = {
            "id": 30,
            "commit_id": HEAD,
            "state": "CHANGES_REQUESTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": "manual concurrent review",
            "submitted_at": "2026-09-01T08:00:02Z",
        }
        failed = module.verify_review_readback(
            plan=plan,
            review=submitted,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[manual, submitted],
        )
        with self.assertRaisesRegex(
            module.NativeAccountReviewError, "SIGNER_RECEIPT_READBACK_NOT_EXACT"
        ):
            module.build_signer_receipt(
                plan=plan,
                review=submitted,
                expected_signer="Goldkelch",
                reviews_before=[],
                reviews_after=[manual, submitted],
                readback=failed,
                final_pr=self.pr(),
                final_commit=self.commit(),
                authority_fence=self.authority_fence(plan),
                repository=REPOSITORY,
                evaluator_sha=SIGNER_EVALUATOR,
                run_id=SIGNER_RUN_ID,
                run_attempt=SIGNER_RUN_ATTEMPT,
            )

    def test_readback_blocks_concurrent_marked_non_target_review(self):
        plan = self.plan()
        submitted = {
            "id": 23,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
            "submitted_at": "2026-09-01T08:00:03Z",
        }
        marked_other_head = {
            "id": 22,
            "commit_id": "e" * 40,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": f"<!-- {module.MARKER} fingerprint={'f' * 64} -->",
            "submitted_at": "2026-09-01T08:00:02Z",
        }
        result = module.verify_review_readback(
            plan=plan,
            review=submitted,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[marked_other_head, submitted],
        )
        self.assertFalse(result["exact"])
        self.assertEqual(
            result["first_blocker"], "CONCURRENT_DELEGATED_NON_TARGET_REVIEW"
        )

    def test_readback_ignores_preexisting_legacy_decisive_order_for_comment(self):
        plan = self.plan()
        old = {
            "id": 11,
            "commit_id": HEAD,
            "state": "APPROVED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": f"<!-- {module.MARKER} fingerprint={'e' * 64} -->",
            "submitted_at": None,
        }
        submitted = {
            "id": 12,
            "commit_id": HEAD,
            "state": "COMMENTED",
            "user": {"login": "Goldkelch", "type": "User"},
            "body": plan["review_body"],
            "submitted_at": "2026-09-01T08:00:02Z",
        }
        result = module.verify_review_readback(
            plan=plan,
            review=submitted,
            expected_signer="Goldkelch",
            reviews_before=[old],
            reviews_after=[old, submitted],
        )
        self.assertTrue(result["exact"])

    def test_no_secret_field_is_emitted_in_plan(self):
        serialized = str(self.plan()).lower()
        self.assertNotIn("token", serialized)
        self.assertNotIn("secret", serialized)

    def test_trusted_executor_identity_ignores_dynamic_run_name(self):
        workflow = {
            "id": 335830906,
            "path": module.TRUSTED_EXECUTOR_PATH,
        }
        run = {
            "id": 33484295414,
            "run_attempt": 2,
            "status": "completed",
            "name": "QIKVRT requested review pr=935 head=abc fp=def",
            "workflow_id": workflow["id"],
            "path": module.TRUSTED_EXECUTOR_PATH,
            "repository": {"full_name": REPOSITORY},
            "event": "issue_comment",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": BASE,
        }
        self.assertTrue(
            module.trusted_executor_run_is_valid(
                run, workflow, REPOSITORY, BASE, run["id"], run["run_attempt"]
            )
        )
        for field, drift in (
            ("workflow_id", workflow["id"] + 1),
            ("path", ".github/workflows/untrusted.yml"),
            ("repository", {"full_name": "example/qik-vrt"}),
            ("event", "schedule"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("head_branch", "release/candidate"),
            ("head_sha", "e" * 40),
            ("id", run["id"] + 1),
            ("run_attempt", run["run_attempt"] + 1),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(run)
                changed[field] = drift
                self.assertFalse(
                    module.trusted_executor_run_is_valid(
                        changed,
                        workflow,
                        REPOSITORY,
                        BASE,
                        run["id"],
                        run["run_attempt"],
                    )
                )

        wrong_workflow = dict(workflow, path=".github/workflows/untrusted.yml")
        self.assertFalse(
            module.trusted_executor_run_is_valid(
                run,
                wrong_workflow,
                REPOSITORY,
                BASE,
                run["id"],
                run["run_attempt"],
            )
        )
        self.assertFalse(
            module.trusted_executor_run_is_valid(
                run,
                workflow,
                REPOSITORY,
                "not-a-git-sha",
                run["id"],
                run["run_attempt"],
            )
        )
        self.assertFalse(
            module.trusted_executor_run_is_valid(
                run,
                workflow,
                REPOSITORY,
                BASE,
                run["id"],
                run["run_attempt"] + 1,
            )
        )

    def test_executor_artifact_selects_only_exact_current_attempt(self):
        run = self.executor_run()
        old = self.executor_artifact(artifact_id=9000, run_attempt=1)
        current = self.executor_artifact()
        result = module.select_trusted_executor_artifact(
            run,
            [{"total_count": 2, "artifacts": [old, current]}],
        )
        self.assertEqual(result["artifact_id"], current["id"])
        self.assertEqual(result["producer_run_id"], run["id"])
        self.assertEqual(result["producer_run_attempt"], run["run_attempt"])
        self.assertEqual(result["artifact_total_count"], 2)

    def test_executor_artifact_rejects_old_attempt_reuse(self):
        run = self.executor_run()
        old = self.executor_artifact(run_attempt=run["run_attempt"] - 1)
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "UPSTREAM_EXECUTOR_ARTIFACT_MISSING_OR_AMBIGUOUS",
        ):
            module.select_trusted_executor_artifact(
                run,
                [{"total_count": 1, "artifacts": [old]}],
            )

    def test_executor_artifact_flattens_more_than_one_hundred(self):
        run = self.executor_run()
        noise = [
            self.executor_artifact(
                artifact_id=index + 1,
                name=f"unrelated-artifact-{index + 1}",
            )
            for index in range(100)
        ]
        current = self.executor_artifact(artifact_id=1001)
        result = module.select_trusted_executor_artifact(
            run,
            [
                {"total_count": 101, "artifacts": noise},
                {"total_count": 101, "artifacts": [current]},
            ],
        )
        self.assertEqual(result["artifact_id"], current["id"])
        self.assertEqual(result["artifact_total_count"], 101)

    def test_executor_artifact_rejects_incomplete_total_count(self):
        run = self.executor_run()
        current = self.executor_artifact()
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "UPSTREAM_EXECUTOR_ARTIFACT_TOTAL_COUNT_INCOMPLETE",
        ):
            module.select_trusted_executor_artifact(
                run,
                [{"total_count": 101, "artifacts": [current]}],
            )

    def test_executor_artifact_rejects_duplicate_current_attempt(self):
        run = self.executor_run()
        first = self.executor_artifact(artifact_id=9001)
        second = self.executor_artifact(artifact_id=9002)
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "UPSTREAM_EXECUTOR_ARTIFACT_MISSING_OR_AMBIGUOUS",
        ):
            module.select_trusted_executor_artifact(
                run,
                [{"total_count": 2, "artifacts": [first, second]}],
            )

    def test_executor_artifact_requires_exact_archive_digest(self):
        run = self.executor_run()
        artifact = self.executor_artifact()
        artifact.pop("digest")
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "UPSTREAM_EXECUTOR_ARTIFACT_DIGEST_INVALID",
        ):
            module.select_trusted_executor_artifact(
                run, [{"total_count": 1, "artifacts": [artifact]}]
            )

    def test_producer_binding_seals_exact_attempt_and_artifact_bytes(self):
        artifact = self.executor_artifact()
        files = {
            "review.json": b'{"semantic":"receipt"}\n',
            "review.diff": b"diff --git a/a b/a\n",
            "ledger-write.json": b'{"persisted":true}\n',
            "review-transport.json": b'{"schema":"transport"}\n',
        }
        binding = module.build_trusted_executor_producer_binding(
            repository=REPOSITORY,
            run_id=7001,
            run_attempt=2,
            artifact_name=artifact["name"],
            pr_number=884,
            head_sha=HEAD,
            evidence_fingerprint=FINGERPRINT,
            files=files,
        )
        self.assertEqual(binding["run_attempt"], 2)
        self.assertEqual(
            module.verify_trusted_executor_producer_binding(
                binding,
                repository=REPOSITORY,
                run_id=7001,
                run_attempt=2,
                artifact_name=artifact["name"],
                pr_number=884,
                head_sha=HEAD,
                evidence_fingerprint=FINGERPRINT,
                files=files,
            ),
            binding,
        )
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "exact artifact bytes or attempt",
        ):
            module.verify_trusted_executor_producer_binding(
                binding,
                repository=REPOSITORY,
                run_id=7001,
                run_attempt=2,
                artifact_name=artifact["name"],
                pr_number=884,
                head_sha=HEAD,
                evidence_fingerprint=FINGERPRINT,
                files={**files, "review.diff": b"tampered"},
            )

    def test_attempt_envelope_does_not_change_semantic_review_receipt(self):
        receipt = self.receipt()
        semantic_before = copy.deepcopy(receipt)
        files = {
            "review.json": b'{"semantic":"receipt"}\n',
            "review.diff": b"diff\n",
            "ledger-write.json": b'{"persisted":true}\n',
            "review-transport.json": b'{"schema":"transport"}\n',
        }
        first_artifact = self.executor_artifact(run_attempt=1)
        second_artifact = self.executor_artifact(run_attempt=2)
        first = module.build_trusted_executor_producer_binding(
            repository=REPOSITORY,
            run_id=7001,
            run_attempt=1,
            artifact_name=first_artifact["name"],
            pr_number=884,
            head_sha=HEAD,
            evidence_fingerprint=FINGERPRINT,
            files=files,
        )
        second = module.build_trusted_executor_producer_binding(
            repository=REPOSITORY,
            run_id=7001,
            run_attempt=2,
            artifact_name=second_artifact["name"],
            pr_number=884,
            head_sha=HEAD,
            evidence_fingerprint=FINGERPRINT,
            files=files,
        )
        self.assertEqual(receipt, semantic_before)
        self.assertNotEqual(first["binding_payload_sha256"], second["binding_payload_sha256"])

    def test_pre_effect_attempt_reobservation_rejects_rerun_advance(self):
        workflow = {"id": 335830906, "path": module.TRUSTED_EXECUTOR_PATH}
        run = {
            "id": 7001,
            "run_attempt": 2,
            "status": "completed",
            "conclusion": "success",
            "event": "pull_request_target",
            "workflow_id": workflow["id"],
            "path": module.TRUSTED_EXECUTOR_PATH,
            "head_branch": "main",
            "head_sha": BASE,
            "repository": {"full_name": REPOSITORY},
        }
        artifact = self.executor_artifact()
        pages = [{"total_count": 1, "artifacts": [artifact]}]
        selected = module.select_trusted_executor_artifact(run, pages)
        selection = {
            **{key: value for key, value in selected.items() if key != "artifact"},
            "upstream_run_id": run["id"],
            "upstream_run_attempt": run["run_attempt"],
            "upstream_event": run["event"],
        }
        files = {
            "review.json": b'{"semantic":"receipt"}\n',
            "review.diff": b"diff\n",
            "ledger-write.json": b'{"persisted":true}\n',
            "review-transport.json": b'{"schema":"transport"}\n',
        }
        binding = module.build_trusted_executor_producer_binding(
            repository=REPOSITORY,
            run_id=run["id"],
            run_attempt=run["run_attempt"],
            artifact_name=artifact["name"],
            pr_number=884,
            head_sha=HEAD,
            evidence_fingerprint=FINGERPRINT,
            files=files,
        )
        exact = module.verify_current_trusted_executor_attempt(
            repository=REPOSITORY,
            trusted_main_sha=BASE,
            current_main={"sha": BASE},
            run=run,
            workflow=workflow,
            selection=selection,
            artifact_pages=pages,
            producer_binding=binding,
            files=files,
        )
        self.assertTrue(exact["exact"])
        advanced = copy.deepcopy(run)
        advanced["run_attempt"] = run["run_attempt"] + 1
        advanced["status"] = "in_progress"
        advanced["conclusion"] = None
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "UPSTREAM_EXECUTOR_ATTEMPT_NO_LONGER_CURRENT",
        ):
            module.verify_current_trusted_executor_attempt(
                repository=REPOSITORY,
                trusted_main_sha=BASE,
                current_main={"sha": BASE},
                run=advanced,
                workflow=workflow,
                selection=selection,
                artifact_pages=pages,
                producer_binding=binding,
                files=files,
            )
        completed_successor = copy.deepcopy(advanced)
        completed_successor["status"] = "completed"
        completed_successor["conclusion"] = "success"
        with self.assertRaisesRegex(
            module.NativeAccountReviewError,
            "UPSTREAM_EXECUTOR_ATTEMPT_NO_LONGER_CURRENT",
        ):
            module.verify_current_trusted_executor_attempt(
                repository=REPOSITORY,
                trusted_main_sha=BASE,
                current_main={"sha": BASE},
                run=completed_successor,
                workflow=workflow,
                selection=selection,
                artifact_pages=pages,
                producer_binding=binding,
                files=files,
            )

    def test_workflow_keeps_all_signers_dormant_and_secret_free(self):
        technical = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text(encoding="utf-8")
        technical_tool = (ROOT / "tools/qikvrt_requested_review_executor.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/qikvrt_required_review_gate.yml").read_text(encoding="utf-8")
        self.assertNotIn("QIKVRT_ENV_GOLDKELCH_REVIEW_TOKEN", technical)
        self.assertNotIn("QIKVRT_ENV_INGOLF_LOHMANN_REVIEW_TOKEN", technical)
        self.assertIn("plan-native-account-review:", workflow)
        self.assertEqual(workflow.count("flatten_review_pages(pages)"), 5)
        self.assertNotIn(
            "page if isinstance(page,list) else [page]", workflow
        )
        self.assertNotIn("QIKVRT_ENV_GOLDKELCH_REVIEW_TOKEN", workflow)
        self.assertNotIn("QIKVRT_ENV_INGOLF_LOHMANN_REVIEW_TOKEN", workflow)
        self.assertNotIn("QIKVRT_ENV_NATIVE_ACCOUNT_REVIEW_ACTIVATION", workflow)
        self.assertEqual(workflow.count("AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED"), 2)
        self.assertEqual(
            workflow.count("environment: qikvrt-native-review-authority"), 2
        )
        for legacy in (
            "secrets.QIKVRT_GOLDKELCH_REVIEW_TOKEN",
            "secrets.QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN",
            "secrets.QIKVRT_NATIVE_ACCOUNT_REVIEW_ACTIVATION",
        ):
            self.assertNotIn(legacy, workflow)
        self.assertIn("gh api user", workflow)
        self.assertIn('GH_TOKEN="$account_token" gh api --method POST', workflow)
        self.assertIn("verify-readback", workflow)
        self.assertEqual(workflow.count('--reviews-before "$root/current-reviews.json"'), 6)
        self.assertEqual(workflow.count('--reviews-after "$root/post-reviews.json"'), 6)
        self.assertEqual(workflow.count('post-review-pages.json'), 4)
        self.assertEqual(workflow.count("seal-signer-receipt"), 2)
        self.assertEqual(workflow.count("--authority-fence"), 2)
        self.assertEqual(
            workflow.count("fence=build_signer_post_effect_authority_fence("), 2
        )
        self.assertEqual(
            workflow.count("qikvrt-native-review-signer-receipt-"), 2
        )
        self.assertEqual(
            workflow.count("observe_automated_signer_receipts"), 4
        )
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn(
            "run, workflow, repo, trusted_main_sha, run_id, run_attempt",
            workflow,
        )
        self.assertIn("['git','rev-parse','HEAD']", workflow)
        self.assertIn(
            "UPSTREAM_RUN_ATTEMPT: ${{ github.event.workflow_run.run_attempt }}",
            workflow,
        )
        self.assertIn(
            "github.event.workflow_run.path == '.github/workflows/qikvrt_requested_review_executor.yml'",
            workflow,
        )
        self.assertIn(
            "github.event.workflow_run.repository.full_name == github.repository",
            workflow,
        )
        self.assertNotIn("github.event.workflow_run.name ==", workflow)
        self.assertNotIn("run.get('name')", workflow)
        self.assertEqual(
            workflow.count(
                "gh api --paginate --slurp \\\n"
                "            \"repos/${REPOSITORY}/actions/runs/${UPSTREAM_RUN_ID}/artifacts?per_page=100\""
            ),
            1,
        )
        self.assertIn("['gh','api','--paginate','--slurp',path]", workflow)
        self.assertNotIn(
            'gh api "repos/${REPOSITORY}/actions/runs/${UPSTREAM_RUN_ID}/artifacts?per_page=100"',
            workflow,
        )
        self.assertIn("select_trusted_executor_artifact", workflow)
        self.assertIn("artifact_total_count", workflow)
        self.assertIn("producer_run_attempt", workflow)
        self.assertIn("exact executor run attempt drifted", workflow)
        self.assertIn("IMMUTABLE_EXECUTOR_ARTIFACT_RETRACTION_ONLY", workflow)
        self.assertIn("executor artifact name and receipt binding differ", workflow)
        self.assertIn("executor receipt event provenance differs from the trusted run", workflow)
        self.assertIn("PRE_EFFECT_REQUESTED_REVIEWER_DRIFT", (ROOT / "tools/qikvrt_native_account_review.py").read_text(encoding="utf-8"))
        self.assertIn("executor ledger commit is not reachable", workflow)
        self.assertEqual(workflow.count('tools/qikvrt_requested_review_executor.py verify'), 3)
        self.assertEqual(workflow.count('--reobservation-exact true'), 3)
        self.assertEqual(workflow.count('--delegation state/authorization/delegations/OWNER_NATIVE_ACCOUNT_REVIEW_AUTOMATION_V1.json'), 1)
        self.assertEqual(workflow.count('--delegation "$root/current-delegation.json"'), 2)
        self.assertEqual(workflow.count('OWNER_NATIVE_ACCOUNT_REVIEW_AUTOMATION_V1.json?ref=main'), 4)
        self.assertIn('artifact/review.json', workflow)
        self.assertIn('artifact/review.diff', workflow)
        self.assertIn('artifact/ledger-write.json', workflow)
        self.assertIn('artifact/review-transport.json', workflow)
        self.assertIn('sha256sum "$root/evidence.zip"', workflow)
        self.assertNotIn('artifact/.qikvrt/mesh-review/review.json', workflow)
        self.assertNotIn('find "$root/artifact" -type f -name review.json', workflow)
        self.assertEqual(
            workflow.count(
                "qikvrt-native-account-review-plan-${{ github.run_id }}-"
            ),
            3,
        )
        self.assertIn("${{ steps.plan.outputs.plan_sha256 }}", workflow)
        self.assertEqual(
            workflow.count(
                "${{ needs.plan-native-account-review.outputs.plan_sha256 }}"
            ),
            2,
        )
        self.assertIn(
            "-run-${{ github.run_id }}-attempt-${{ github.run_attempt }}",
            technical,
        )
        self.assertIn("Seal exact producer run attempt transport binding", technical)
        self.assertIn("producer-binding.json", technical)
        self.assertIn("verify_trusted_executor_producer_binding", workflow)
        self.assertNotIn('"producer_run_attempt"', technical_tool)
        self.assertNotIn('"producer_run_id"', technical_tool)
        self.assertIn(
            "qikvrt-required-code-owner-selection-${{ github.run_id }}-${{ github.run_attempt }}-${{ steps.select.outputs.state }}",
            workflow,
        )
        workflow_concurrency = workflow.split("\njobs:\n", 1)[0]
        self.assertIn(
            "group: qikvrt-required-code-owner-review-${{ github.repository }}",
            workflow_concurrency,
        )
        self.assertIn("  queue: max", workflow_concurrency)
        gold = workflow.split("  native-account-review-as-goldkelch:", 1)[1].split("  native-account-review-as-ingolf-lohmann:", 1)[0]
        ingolf = workflow.split("  native-account-review-as-ingolf-lohmann:", 1)[1]
        plan_job = workflow.split("  plan-native-account-review:", 1)[1].split(
            "  native-account-review-as-goldkelch:", 1
        )[0]
        plan_header = plan_job.split("    steps:", 1)[0]
        self.assertIn("      actions: read", plan_header)
        self.assertIn("      contents: read", plan_header)
        self.assertIn("      pull-requests: read", plan_header)
        self.assertNotIn("statuses: write", plan_header)
        gold_header = gold.split("    steps:", 1)[0]
        ingolf_header = ingolf.split("    steps:", 1)[0]
        self.assertIn("    if: false", gold_header)
        self.assertIn("    if: false", ingolf_header)
        signer_lock_prefix = (
            "group: qikvrt-native-account-review-${{ github.repository }}-pr-"
            "${{ needs.plan-native-account-review.outputs.pr }}-reviewer-"
        )
        for signer_header, signer in (
            (gold_header, "Goldkelch"),
            (ingolf_header, "ingolf-lohmann"),
        ):
            self.assertIn("    concurrency:\n", signer_header)
            self.assertIn(signer_lock_prefix + signer, signer_header)
            self.assertIn("      cancel-in-progress: false", signer_header)
            self.assertIn("      queue: max", signer_header)
        publish_header = workflow.split(
            "  publish-required-status:\n", 1
        )[1].split("    steps:\n", 1)[0]
        self.assertIn("qikvrt-required-code-owner-status-", publish_header)
        self.assertIn("needs.plan-required-gate.outputs.pr", publish_header)
        self.assertIn("      queue: max", publish_header)
        self.assertIn("      pull-requests: read", gold_header)
        self.assertIn("      pull-requests: read", ingolf_header)
        self.assertNotIn("pull-requests: write", gold_header)
        self.assertNotIn("pull-requests: write", ingolf_header)
        self.assertNotIn("secrets.QIKVRT_", gold_header)
        self.assertNotIn("secrets.QIKVRT_", ingolf_header)
        gold_before_effect = gold.split(
            "      - name: Reobserve and submit only an exact Goldkelch account review",
            1,
        )[0]
        ingolf_before_effect = ingolf.split(
            "      - name: Reobserve and submit only an exact ingolf-lohmann account review",
            1,
        )[0]
        self.assertNotIn("secrets.QIKVRT_", gold_before_effect)
        self.assertNotIn("secrets.QIKVRT_", ingolf_before_effect)
        for signer_job in (gold, ingolf):
            self.assertEqual(
                signer_job.count("revalidate_upstream_attempt pre-account-token"),
                1,
            )
            self.assertEqual(
                signer_job.count("revalidate_upstream_attempt pre-review-post"),
                1,
            )
            self.assertEqual(
                signer_job.count("revalidate_upstream_attempt post-review-effect"),
                1,
            )
            self.assertIn("verify_current_trusted_executor_attempt", signer_job)
            self.assertLess(
                signer_job.index("revalidate_upstream_attempt pre-account-token"),
                signer_job.index('GH_TOKEN="$account_token" gh api user'),
            )
            final_upstream = signer_job.index(
                "revalidate_upstream_attempt pre-review-post"
            )
            final_pr = signer_job.index('> "$root/current-pr.json"', final_upstream)
            final_delegation = signer_job.index(
                '> "$root/current-delegation-content.json"', final_pr
            )
            final_reviews = signer_job.index(
                '> "$root/current-review-pages.json"', final_delegation
            )
            final_preflight = signer_job.index(
                "tools/qikvrt_native_account_review.py signer-preflight",
                final_reviews,
            )
            review_post = signer_job.index(
                'GH_TOKEN="$account_token" gh api --method POST',
                final_preflight,
            )
            self.assertLess(
                final_upstream,
                final_pr,
            )
            self.assertLess(final_pr, final_delegation)
            self.assertLess(final_delegation, final_reviews)
            self.assertLess(final_reviews, final_preflight)
            self.assertLess(final_preflight, review_post)
            self.assertNotIn("gh api", signer_job[final_preflight:review_post])
            self.assertNotIn(
                "revalidate_upstream_attempt",
                signer_job[final_preflight:review_post],
            )
            post_upstream = signer_job.index(
                "revalidate_upstream_attempt post-review-effect", review_post
            )
            post_main = signer_job.index('> "$root/post-main.json"', post_upstream)
            post_rules = signer_job.index('> "$root/post-rules.json"', post_main)
            post_delegation = signer_job.index(
                '> "$root/post-delegation-content.json"', post_rules
            )
            post_pr = signer_job.index('> "$root/post-pr.json"', post_delegation)
            post_reviews = signer_job.index(
                '> "$root/post-review-pages.json"', post_pr
            )
            fence = signer_job.index(
                "build_signer_post_effect_authority_fence", post_reviews
            )
            receipt = signer_job.index("seal-signer-receipt", fence)
            self.assertLess(post_upstream, post_main)
            self.assertLess(post_main, post_rules)
            self.assertLess(post_rules, post_delegation)
            self.assertLess(post_delegation, post_pr)
            self.assertLess(post_pr, post_reviews)
            self.assertLess(post_reviews, fence)
            self.assertLess(fence, receipt)
            self.assertNotIn("gh api", signer_job[post_reviews:receipt])
            self.assertIn("irreducible final GET-to-POST race", signer_job)
            self.assertIn('account_token="$ACCOUNT_TOKEN"', signer_job)
            self.assertIn(
                "unset ACCOUNT_TOKEN AUTOMATION_ACTIVATION", signer_job
            )
            self.assertNotIn('GH_TOKEN="$ACCOUNT_TOKEN"', signer_job)
            self.assertEqual(signer_job.count("unset account_token"), 1)
            self.assertEqual(
                signer_job.count('GH_TOKEN="$account_token" gh api'), 3
            )
            unset_at = signer_job.index(
                "unset ACCOUNT_TOKEN AUTOMATION_ACTIVATION"
            )
            first_technical_subprocess = signer_job.index(
                'python3 -B -c', unset_at
            )
            self.assertLess(unset_at, first_technical_subprocess)
            self.assertNotIn(
                "export account_token", signer_job[unset_at:]
            )
        self.assertNotIn("secrets.QIKVRT_ENV_GOLDKELCH_REVIEW_TOKEN", gold)
        self.assertNotIn("secrets.QIKVRT_ENV_INGOLF_LOHMANN_REVIEW_TOKEN", ingolf)
        self.assertNotIn("secrets.QIKVRT_ENV_NATIVE_ACCOUNT_REVIEW_ACTIVATION", gold)
        self.assertNotIn("secrets.QIKVRT_ENV_NATIVE_ACCOUNT_REVIEW_ACTIVATION", ingolf)
        self.assertNotIn("QIKVRT_ENV_GOLDKELCH_REVIEW_TOKEN", gold)
        self.assertNotIn("QIKVRT_ENV_INGOLF_LOHMANN_REVIEW_TOKEN", gold)
        self.assertNotIn("QIKVRT_ENV_INGOLF_LOHMANN_REVIEW_TOKEN", ingolf)
        self.assertNotIn("QIKVRT_ENV_GOLDKELCH_REVIEW_TOKEN", ingolf)

    def test_unexported_signer_token_is_absent_from_technical_subprocess_env(self):
        command = r'''
          export ACCOUNT_TOKEN=secret AUTOMATION_ACTIVATION=enabled
          account_token="$ACCOUNT_TOKEN"
          unset ACCOUNT_TOKEN AUTOMATION_ACTIVATION
          python3 -c 'import os; assert "ACCOUNT_TOKEN" not in os.environ; assert "AUTOMATION_ACTIVATION" not in os.environ; assert "GH_TOKEN" not in os.environ'
          GH_TOKEN="$account_token" python3 -c 'import os; assert os.environ.get("GH_TOKEN") == "secret"; assert "ACCOUNT_TOKEN" not in os.environ; assert "AUTOMATION_ACTIVATION" not in os.environ'
        '''
        clean_env = {"PATH": os.environ["PATH"]}
        subprocess.run(
            ["bash", "-euo", "pipefail", "-c", command],
            check=True,
            env=clean_env,
        )


if __name__ == "__main__":
    unittest.main()
