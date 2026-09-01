# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import copy
import hashlib
import io
import json
import pathlib
import sys
import textwrap
import unittest
import zipfile
from unittest import mock

from tools import qikvrt_native_account_review as native_review

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
    context = "QIKVRT required code-owner review"

    def test_workflow_embedded_python_blocks_compile(self):
        workflow = (
            ROOT / ".github/workflows/qikvrt_required_review_gate.yml"
        ).read_text(encoding="utf-8")
        lines = workflow.splitlines()
        blocks: list[str] = []
        index = 0
        while index < len(lines):
            if "<<'PY'" not in lines[index]:
                index += 1
                continue
            index += 1
            while index < len(lines) and lines[index].strip().startswith(
                (">", "2>")
            ):
                index += 1
            body: list[str] = []
            while index < len(lines) and lines[index].strip() != "PY":
                body.append(lines[index])
                index += 1
            self.assertLess(index, len(lines), "unterminated embedded Python block")
            blocks.append(textwrap.dedent("\n".join(body)))
            index += 1
        self.assertGreater(len(blocks), 0)
        for number, source in enumerate(blocks, start=1):
            compile(source, f"qikvrt_required_review_gate.yml:python-{number}", "exec")

    def pr(self, **overrides):
        value = {"number": 641, "head": {"sha": self.head}, "user": {"login": "integration-author"}}
        value.update(overrides)
        return value

    def status_plan_pr(self, **overrides):
        value = self.pr(
            state="open",
            draft=False,
            head={
                "sha": self.head,
                "ref": "feature",
                "repo": {"full_name": "example/qik-vrt"},
            },
            base={
                "sha": "a" * 40,
                "ref": "main",
                "repo": {"full_name": "example/qik-vrt"},
            },
        )
        value.update(overrides)
        return value

    def status_plan_commit(self, **overrides):
        value = {"sha": self.head, "tree": {"sha": "c" * 40}}
        value.update(overrides)
        return value

    def event_pr(self, number=641, *, head=None, repository="example/qik-vrt"):
        return {
            "number": number,
            "url": f"https://api.github.com/repos/{repository}/pulls/{number}",
            "head": {"sha": self.head if head is None else head},
        }

    def executor_dispatch_authority_fixture(self):
        from tools.qikvrt_requested_review_executor import requested_review_run_title

        evaluator = "a" * 40
        fingerprint = "c" * 64
        intent_sha = "d" * 64
        workflow_id = 55
        title = requested_review_run_title(
            evaluator_sha=evaluator,
            pr_number=641,
            head_sha=self.head,
            fingerprint=fingerprint,
            transport_intent_sha256=intent_sha,
            transport_attempt=1,
        )
        run = {
            "id": 777,
            "run_attempt": 1,
            "workflow_id": workflow_id,
            "path": ".github/workflows/qikvrt_requested_review_executor.yml@main",
            "repository": {"full_name": "example/qik-vrt"},
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": evaluator,
            "display_title": title,
        }
        child = {
            "run_id": 777,
            "run_attempt": 1,
            "workflow_id": workflow_id,
            "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
            "event": "workflow_dispatch",
            "repository": "example/qik-vrt",
            "head_sha": evaluator,
            "display_title": title,
        }
        lookup = {
            "lane": "exact-review-dispatch",
            "intent": {
                "sequence": 1,
                "fingerprint": intent_sha,
                "payload": {
                    "repository": "example/qik-vrt",
                    "main_head_sha": evaluator,
                    "request": {
                        "ref": "main",
                        "return_run_details": True,
                        "inputs": {
                            "pr": "641",
                            "head": self.head,
                            "fingerprint": fingerprint,
                            "evaluator_sha": evaluator,
                            "transport_intent_sha256": intent_sha,
                            "transport_attempt": "1",
                        },
                    },
                    "target": {
                        "workflow_id": workflow_id,
                        "workflow_path": ".github/workflows/qikvrt_requested_review_executor.yml",
                        "event": "workflow_dispatch",
                    },
                },
            },
            "acceptance": {"1": {"child": child}},
            "child_recovery": {},
        }
        return evaluator, workflow_id, run, lookup

    def enforced_rules(self):
        return [
            {"type": "pull_request", "parameters": {
                "required_approving_review_count": 1,
                "require_code_owner_review": True,
                "dismiss_stale_reviews_on_push": True,
                "require_last_push_approval": True,
            }},
            {"type": "required_status_checks", "parameters": {
                "required_status_checks": [
                    {"context": "test", "integration_id": 15368},
                    {
                        "context": "QIKVRT required code-owner review",
                        "integration_id": 15368,
                    },
                ],
            }},
        ]

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

    def marked_approval(self, **overrides):
        value = self.approval(
            body=native_review._delegated_review_body(
                base_sha="a" * 40,
                head_sha=self.head,
                tree_sha="c" * 40,
                fingerprint="d" * 64,
                disposition=native_review.TECHNICAL_CONTINUE,
                reviewer="Goldkelch",
                event=native_review.TECHNICAL_CONTINUE,
                stale_approval_retraction=False,
                retraction_only=False,
                signer_run_id=8123,
                signer_run_attempt=2,
                signer_evaluator_sha="f" * 40,
            )
        )
        value.update(overrides)
        return value

    def marked_comment(self, **overrides):
        value = self.marked_approval(state="COMMENTED")
        value.update(overrides)
        return value

    def signer_authority_fence(self, plan):
        fence = {
            "schema": native_review.SIGNER_POST_EFFECT_FENCE_SCHEMA,
            "repository": plan["repository"],
            "evaluator_sha": plan["signer_evaluator_sha"],
            "main_sha": plan["signer_evaluator_sha"],
            "upstream": {
                "schema": "qikvrt_current_executor_attempt_reobservation_v1",
                "exact": True,
                "run_id": 7001,
                "run_attempt": 1,
                "artifact_id": 9001,
                "artifact_name": "qikvrt-mesh-review-pr-641-fixture",
                "trusted_main_sha": plan["signer_evaluator_sha"],
            },
            "rules_sha256": "1" * 64,
            "delegation_sha256": plan["delegation_sha256"],
            "subject": {
                "pr_number": plan["pr_number"],
                "base_sha": plan["base_sha"],
                "head_sha": plan["head_sha"],
                "tree_sha": plan["tree_sha"],
            },
            "exact": True,
            "productive_effect": False,
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
                "MERGE": False,
            },
        }
        fence["fence_sha256"] = native_review._sha256(fence)
        return fence

    def ingolf_approval(self, **overrides):
        return self.approval(user={"login": "ingolf-lohmann"}, **overrides)

    def status(self, **overrides):
        value = {
            "id": 10,
            "context": self.context,
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
            context=self.context,
            state=state,
            description=description,
        )

    def test_native_rule_must_enforce_all_freshness_requirements(self):
        weak = self.enforced_rules()
        weak[0]["parameters"]["require_code_owner_review"] = False
        result = self.evaluate([], rules=weak)
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_RULE_NOT_ENFORCED"))

    def test_native_rule_must_require_the_review_gate_status(self):
        weak = self.enforced_rules()
        weak[1]["parameters"]["required_status_checks"] = [
            {"context": "test", "integration_id": 15368}
        ]
        result = self.evaluate([], rules=weak)
        self.assertEqual(
            (result["gate_state"], result["first_blocker"]),
            ("failure", "CODE_OWNER_RULE_NOT_ENFORCED"),
        )

    def test_no_review_is_pending_not_approval(self):
        result = self.evaluate([])
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("pending", "CODE_OWNER_REVIEW_MISSING"))

    def test_duplicate_or_invalid_review_inventory_fails_closed(self):
        review = self.approval()
        for values in ([review, copy.deepcopy(review)], [dict(review, id=0)]):
            with self.subTest(values=values), self.assertRaisesRegex(
                MODULE.ReviewGateInputError, "invalid or duplicate review id"
            ):
                self.evaluate(values)

    def test_counterpart_unavailable_returns_bound_subject_not_runtime_error(self):
        with mock.patch.object(
            MODULE, "_code_owners", return_value=("integration-author",)
        ):
            result = MODULE.evaluate_required_review(
                self.pr(), self.enforced_rules(), []
            )
        self.assertEqual(result["first_blocker"], "CODE_OWNER_COUNTERPART_UNAVAILABLE")
        self.assertEqual(result["pr_number"], 641)
        self.assertEqual(result["head_sha"], self.head)

    def test_exact_head_approval_passes(self):
        result = self.evaluate([self.approval()])
        self.assertEqual(result["gate_state"], "success")
        self.assertEqual(result["head_sha"], self.head)

    def test_marked_approval_without_successful_signer_receipt_holds(self):
        review = self.marked_approval()
        result = self.evaluate([review])
        self.assertEqual(
            (result["gate_state"], result["first_blocker"]),
            ("pending", "AUTOMATED_REVIEW_NOT_CODE_OWNER_AUTHORITY"),
        )
        self.assertIn("technical evidence only", result["detail"])

    def test_marked_approval_requires_explicit_verified_review_id(self):
        review = self.marked_approval()
        result = MODULE.evaluate_required_review(
            self.pr(),
            self.enforced_rules(),
            [review],
            verified_automated_review_ids=[review["id"]],
        )
        self.assertEqual(result["gate_state"], "pending")
        self.assertEqual(
            result["first_blocker"],
            "AUTOMATED_REVIEW_NOT_CODE_OWNER_AUTHORITY",
        )

    def test_concurrent_manual_changes_cannot_be_overridden_by_unreceipted_auto(self):
        manual = self.approval(
            id=12,
            submitted_at="2026-09-01T08:00:02Z",
            state="CHANGES_REQUESTED",
            body="manual final-window review",
        )
        automated = self.marked_approval(
            id=13, submitted_at="2026-09-01T08:00:03Z"
        )
        result = self.evaluate([manual, automated])
        self.assertEqual(
            (result["gate_state"], result["first_blocker"]),
            ("failure", "CODE_OWNER_REVIEW_CHANGES_REQUESTED"),
        )

    def test_human_review_with_marker_substring_remains_authoritative(self):
        manual = self.approval(
            state="CHANGES_REQUESTED",
            body=(
                "Human review discussing "
                f"{native_review.MARKER} without a canonical automation locator"
            ),
        )
        result = self.evaluate([manual])
        self.assertEqual(
            (result["gate_state"], result["first_blocker"]),
            ("failure", "CODE_OWNER_REVIEW_CHANGES_REQUESTED"),
        )

    def test_completed_successful_signer_receipt_is_audit_only(self):
        repository = "Goldkelch/qik-vrt"
        evaluator = "f" * 40
        review = self.marked_comment()
        plan = native_review._sealed({
            **native_review._base_plan(
                repository=repository,
                pr_number=641,
                expected_base="a" * 40,
                expected_head=self.head,
                expected_tree="c" * 40,
                fingerprint="d" * 64,
                first_blocker=None,
                detail="exact delegated signer fixture",
                delegation_state=native_review.DELEGATION_ACTIVE,
                delegation_sha256="e" * 64,
                signer_run_id=8123,
                signer_run_attempt=2,
                signer_evaluator_sha=evaluator,
            ),
            "reviewer": "Goldkelch",
            "event": native_review.TECHNICAL_CONTINUE,
            "effect_permitted": True,
            "review_body": review["body"],
            "active_requested_counterpart_required": True,
        })
        review = dict(review, user={"login": "Goldkelch", "type": "User"})
        readback = native_review.verify_review_readback(
            plan=plan,
            review=review,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[review],
        )
        receipt = native_review.build_signer_receipt(
            plan=plan,
            review=review,
            expected_signer="Goldkelch",
            reviews_before=[],
            reviews_after=[review],
            readback=readback,
            final_pr={
                "number": 641,
                "state": "open",
                "base": {"ref": "main", "sha": "a" * 40},
                "head": {"sha": self.head},
            },
            final_commit={"sha": self.head, "tree": {"sha": "c" * 40}},
            authority_fence=self.signer_authority_fence(plan),
            repository=repository,
            evaluator_sha=evaluator,
            run_id=8123,
            run_attempt=2,
        )
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as zipped:
            zipped.writestr(
                "signer-receipt.json",
                json.dumps(receipt, sort_keys=True, indent=2) + "\n",
            )
        archive = stream.getvalue()
        artifact_url = (
            f"https://api.github.com/repos/{repository}/actions/artifacts/99/zip"
        )
        workflow = {
            "id": 44,
            "path": native_review.TRUSTED_SIGNER_WORKFLOW_PATH,
        }
        run = {
            "id": 8123,
            "run_attempt": 2,
            "workflow_id": 44,
            "path": native_review.TRUSTED_SIGNER_WORKFLOW_PATH + "@main",
            "repository": {"full_name": repository},
            "event": "workflow_run",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": evaluator,
        }
        jobs_page = [{
            "total_count": 1,
            "jobs": [{
                "id": 55,
                "name": "native-account-review-as-Goldkelch",
                "run_id": 8123,
                "run_attempt": 2,
                "status": "completed",
                "conclusion": "success",
            }],
        }]
        artifacts_page = [{
            "total_count": 1,
            "artifacts": [{
                "id": 99,
                "name": receipt["artifact_name"],
                "expired": False,
                "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
                "archive_download_url": artifact_url,
            }],
        }]

        observed_api_paths = []

        def api_json(path):
            observed_api_paths.append(path)
            if path.endswith("qikvrt_required_review_gate.yml"):
                return workflow
            # The receipt is bound to attempt 2.  A later effectless rerun may
            # make GET /runs/{id} report attempt 3; the immutable attempt-2
            # receipt must still be evaluated through the historical endpoint.
            if path.endswith("/actions/runs/8123/attempts/2"):
                return run
            raise AssertionError(f"unexpected mutable run lookup: {path}")

        def api_pages(path):
            return jobs_page if "/jobs?" in path else artifacts_page

        verified, blockers = MODULE.observe_automated_signer_receipts(
            repository=repository,
            evaluator_sha=evaluator,
            pr=self.pr(user={"login": "ingolf-lohmann"}),
            reviews=[review],
            required_code_owners=("Goldkelch", "ingolf-lohmann"),
            api_json=api_json,
            api_pages=api_pages,
            api_bytes=lambda url: archive if url == artifact_url else b"",
        )
        self.assertFalse(blockers)
        self.assertEqual(set(verified), {review["id"]})
        self.assertIn(
            f"repos/{repository}/actions/runs/8123/attempts/2",
            observed_api_paths,
        )
        self.assertNotIn(f"repos/{repository}/actions/runs/8123", observed_api_paths)
        result = MODULE.evaluate_required_review(
            self.pr(user={"login": "ingolf-lohmann"}),
            self.enforced_rules(),
            [review],
            verified_automated_review_ids=tuple(verified),
        )
        self.assertEqual(result["gate_state"], "pending")
        self.assertEqual(
            result["first_blocker"],
            "AUTOMATED_REVIEW_NOT_CODE_OWNER_AUTHORITY",
        )

        cancelled = dict(run, conclusion="cancelled")

        def cancelled_api(path):
            return (
                workflow
                if path.endswith("qikvrt_required_review_gate.yml")
                else cancelled
            )

        verified, blockers = MODULE.observe_automated_signer_receipts(
            repository=repository,
            evaluator_sha=evaluator,
            pr=self.pr(user={"login": "ingolf-lohmann"}),
            reviews=[review],
            required_code_owners=("Goldkelch", "ingolf-lohmann"),
            api_json=cancelled_api,
            api_pages=api_pages,
            api_bytes=lambda _: archive,
        )
        self.assertFalse(verified)
        self.assertIn("SIGNER_RECEIPT_WORKFLOW_RUN_NOT_SUCCESSFUL", blockers[review["id"]])

    def test_current_head_changes_requested_supersedes_prior_approval(self):
        result = self.evaluate([
            self.approval(id=3, submitted_at="2026-08-16T16:00:00Z"),
            self.approval(id=4, submitted_at="2026-08-16T16:01:00Z", state="CHANGES_REQUESTED"),
        ])
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_REVIEW_CHANGES_REQUESTED"))

    def test_each_reviewer_latest_state_is_bound_and_any_live_changes_dominates(self):
        gold_changes = self.approval(
            id=20,
            submitted_at="2026-09-01T08:00:00Z",
            state="CHANGES_REQUESTED",
            body="Goldkelch requests changes",
        )
        ingolf_later_approval = self.ingolf_approval(
            id=21,
            submitted_at="2026-09-01T08:01:00Z",
            body="independent approval",
        )
        result = self.evaluate([gold_changes, ingolf_later_approval])
        self.assertEqual(
            (result["gate_state"], result["first_blocker"]),
            ("failure", "CODE_OWNER_REVIEW_CHANGES_REQUESTED"),
        )

        gold_latest_approval = self.approval(
            id=22,
            submitted_at="2026-09-01T08:02:00Z",
            body="Goldkelch later approval",
        )
        recovered = self.evaluate(
            [gold_changes, ingolf_later_approval, gold_latest_approval]
        )
        self.assertEqual(recovered["gate_state"], "success")
        self.assertEqual(recovered["review_id"], 22)

    def test_nondecisive_comment_does_not_supersede_current_approval(self):
        result = self.evaluate([
            self.approval(id=3, submitted_at="2026-08-16T16:00:00Z"),
            self.approval(id=4, submitted_at="2026-08-16T16:01:00Z", state="COMMENTED"),
        ])
        self.assertEqual(result["gate_state"], "success")

    def test_pr_author_cannot_satisfy_independent_gate(self):
        result = self.evaluate([self.approval()], pr=self.pr(user={"login": "Goldkelch"}))
        self.assertEqual((result["gate_state"], result["first_blocker"]), ("failure", "CODE_OWNER_REVIEW_SELF_APPROVAL"))

    def test_goldkelch_author_requires_ingolf_counterpart(self):
        result = self.evaluate(
            [self.ingolf_approval()],
            pr=self.pr(user={"login": "Goldkelch"}),
        )
        self.assertEqual(result["gate_state"], "success")
        self.assertEqual(result["review_author"], "ingolf-lohmann")
        self.assertEqual(result["eligible_code_owners"], ["ingolf-lohmann"])

    def test_ingolf_author_requires_goldkelch_counterpart(self):
        result = self.evaluate(
            [self.approval()],
            pr=self.pr(user={"login": "ingolf-lohmann"}),
        )
        self.assertEqual(result["gate_state"], "success")
        self.assertEqual(result["review_author"], "Goldkelch")
        self.assertEqual(result["eligible_code_owners"], ["Goldkelch"])

    def test_unchanged_head_context_state_is_noop_even_when_run_url_changed(self):
        result = self.publish([self.status(target_url="https://github.com/Goldkelch/qik-vrt/actions/runs/old")])
        self.assertEqual(result["status_publication"], "NOOP")
        self.assertEqual(result["status_publication_reason"], "UNCHANGED_HEAD_CONTEXT_STATE")

    def test_material_gate_transition_requires_status_write(self):
        result = self.publish([
            self.status(state="pending", description="pending: CODE_OWNER_REVIEW_MISSING")
        ])
        self.assertEqual(result["status_publication"], "WRITE")

    def test_status_effect_plan_seals_exact_subject_rules_reviews_and_statuses(self):
        plan = MODULE.build_status_effect_plan(
            self.status_plan_pr(),
            self.status_plan_commit(),
            self.enforced_rules(),
            [self.approval()],
            [],
            context=self.context,
        )
        self.assertEqual(MODULE.validate_status_effect_plan(plan), plan)
        self.assertTrue(plan["status_effect_authorized"])
        self.assertFalse(plan["review_effect_authorized"])
        self.assertEqual(plan["subject"]["head_tree_sha"], "c" * 40)
        self.assertEqual(plan["decision"]["gate_state"], "success")

        changed = MODULE.build_status_effect_plan(
            self.status_plan_pr(),
            self.status_plan_commit(),
            self.enforced_rules(),
            [self.approval(state="CHANGES_REQUESTED")],
            [],
            context=self.context,
        )
        self.assertNotEqual(changed["plan_sha256"], plan["plan_sha256"])
        self.assertNotEqual(
            changed["observation_sha256"]["reviews"],
            plan["observation_sha256"]["reviews"],
        )

    def test_status_effect_plan_tamper_and_subject_drift_fail_closed(self):
        plan = MODULE.build_status_effect_plan(
            self.status_plan_pr(), self.status_plan_commit(),
            self.enforced_rules(), [], [], context=self.context,
        )
        tampered = copy.deepcopy(plan)
        tampered["publication"]["status_state"] = "success"
        with self.assertRaises(MODULE.ReviewGateInputError):
            MODULE.validate_status_effect_plan(tampered)
        with self.assertRaisesRegex(
            MODULE.ReviewGateInputError, "commit differs"
        ):
            MODULE.build_status_effect_plan(
                self.status_plan_pr(),
                self.status_plan_commit(sha="d" * 40),
                self.enforced_rules(), [], [], context=self.context,
            )

    def test_post_effect_status_fence_covers_main_subject_rules_and_reviews(self):
        plan = MODULE.build_status_effect_plan(
            self.status_plan_pr(), self.status_plan_commit(),
            self.enforced_rules(), [self.approval()], [], context=self.context,
        )
        unchanged = dict(
            expected_main_sha="e" * 40,
            observed_main={"sha": "e" * 40},
            observed_pr=self.status_plan_pr(),
            observed_commit=self.status_plan_commit(),
            observed_rules=self.enforced_rules(),
            observed_reviews=[self.approval()],
        )
        self.assertIsNone(
            MODULE.status_post_effect_drift_blocker(plan, **unchanged)
        )

        cases = {
            "main": ("observed_main", {"sha": "f" * 40}, "POST_EFFECT_MAIN_DRIFT"),
            "head": (
                "observed_pr",
                self.status_plan_pr(head={
                    "sha": "d" * 40,
                    "ref": "feature",
                    "repo": {"full_name": "example/qik-vrt"},
                }),
                "POST_EFFECT_SUBJECT_DRIFT",
            ),
            "base": (
                "observed_pr",
                self.status_plan_pr(base={
                    "sha": "d" * 40,
                    "ref": "main",
                    "repo": {"full_name": "example/qik-vrt"},
                }),
                "POST_EFFECT_SUBJECT_DRIFT",
            ),
            "tree": (
                "observed_commit",
                self.status_plan_commit(tree={"sha": "d" * 40}),
                "POST_EFFECT_SUBJECT_DRIFT",
            ),
            "rules": ("observed_rules", [], "POST_EFFECT_RULES_DRIFT"),
            "reviews": ("observed_reviews", [], "POST_EFFECT_REVIEW_DRIFT"),
        }
        for label, (field, value, blocker) in cases.items():
            with self.subTest(label=label):
                observed = copy.deepcopy(unchanged)
                observed[field] = value
                self.assertEqual(
                    MODULE.status_post_effect_drift_blocker(plan, **observed),
                    blocker,
                )

    def test_bot_review_context_cannot_suppress_code_owner_status(self):
        result = self.publish([
            self.status(context="QIKVRT requested review execution")
        ])
        self.assertEqual(result["status_publication"], "WRITE")
        self.assertIsNone(result["previous_status_id"])

    def test_latest_matching_status_controls_publication(self):
        result = self.publish([
            self.status(id=10, updated_at="2026-08-19T19:00:00Z"),
            self.status(id=11, state="pending", description="pending: CODE_OWNER_REVIEW_MISSING", updated_at="2026-08-19T20:00:00Z"),
        ])
        self.assertEqual(result["previous_status_id"], 11)
        self.assertEqual(result["status_publication"], "WRITE")

    def test_workflow_uses_distinct_idempotent_code_owner_context(self):
        workflow = (ROOT / ".github/workflows/qikvrt_required_review_gate.yml").read_text(encoding="utf-8")
        self.assertIn("STATUS_CONTEXT: QIKVRT required code-owner review", workflow)
        self.assertIn("REQUIRED_CODE_OWNERS_JSON: '[\"Goldkelch\",\"ingolf-lohmann\"]'", workflow)
        self.assertNotIn("STATUS_CONTEXT: QIKVRT requested review execution", workflow)
        self.assertIn("commits/{head}/statuses?per_page=100", workflow)
        self.assertIn("STATUS_PUBLICATION_NOOP", workflow)
        self.assertNotIn("\n  schedule:\n", workflow)
        self.assertNotIn("pulls?state=open", workflow)
        self.assertIn("select_required_review_targets", workflow)
        self.assertIn("EVENT_WORKFLOW_RUN_HEAD: ${{ github.event.workflow_run.head_sha || '' }}", workflow)
        self.assertNotIn("EVENT_EXPECTED_HEAD: ${{ github.event.workflow_run.head_sha", workflow)
        self.assertIn("qikvrt-required-code-owner-selection-", workflow)
        self.assertIn("permissions: {}", workflow)
        self.assertEqual(workflow.count("ref: ${{ github.workflow_sha }}"), 6)
        self.assertEqual(workflow.count("Bind exact evaluator checkout"), 6)
        self.assertNotIn("          ref: main", workflow)
        self.assertIn("github.workflow_sha == github.sha", workflow)
        planner = workflow.split("  plan-required-gate:\n", 1)[1].split(
            "  publish-required-status:\n", 1
        )[0]
        effect = workflow.split("  publish-required-status:\n", 1)[1].split(
            "  plan-native-account-review:\n", 1
        )[0]
        self.assertNotIn("statuses: write", planner)
        self.assertIn("statuses: read", planner)
        self.assertIn("statuses: write", effect)
        self.assertIn("build_status_effect_plan", planner)
        self.assertIn("validate_status_effect_plan", effect)
        self.assertIn("REQUIRED_STATUS_PLAN_PREEFFECT_DRIFT", effect)
        self.assertIn("REQUIRED_STATUS_EFFECT_EVALUATOR_SUPERSEDED", effect)
        self.assertIn("status_post_effect_drift_blocker", effect)
        self.assertIn("POST_EFFECT_CORRECTION", effect)
        self.assertIn("not isinstance(pages,list) or not pages", planner)
        self.assertIn("not isinstance(raw,list) or not raw", effect)
        self.assertIn("isinstance(value,bool) or not isinstance(value,int)", planner)
        self.assertIn("isinstance(value,bool) or not isinstance(value,int)", effect)
        self.assertLess(effect.index("post_main=api("), effect.index("post_rules=api("))
        self.assertLess(effect.index("post_rules=api("), effect.index("post_reviews=pages("))
        self.assertLess(effect.index("post_reviews=pages("), effect.index("observed=pages("))
        self.assertLess(
            effect.index("statuses=pages("),
            effect.index("'gh','api','--method','POST'"),
        )
        self.assertLess(
            workflow.index("pr=gh_json(f'repos/{repo}/pulls/{number}')"),
            workflow.index("rules=gh_json(f'repos/{repo}/rules/branches/main')"),
        )

    def test_manual_executor_dispatch_cannot_reach_gate_without_durable_authority(self):
        workflow = (ROOT / ".github/workflows/qikvrt_required_review_gate.yml").read_text(
            encoding="utf-8"
        )
        verifier = workflow.split(
            "  verify-upstream-dispatch-authority:\n", 1
        )[1].split("  plan-required-gate:\n", 1)[0]
        planner = workflow.split("  plan-required-gate:\n", 1)[1].split(
            "  publish-required-status:\n", 1
        )[0]
        native = workflow.split("  plan-native-account-review:\n", 1)[1].split(
            "  native-review-goldkelch:\n", 1
        )[0]
        self.assertIn("environment: qikvrt-outbox-ledger-authority", verifier)
        self.assertIn("actions: read", verifier)
        self.assertIn("contents: read", verifier)
        self.assertNotIn("contents: write", verifier)
        self.assertNotIn("pull-requests: write", verifier)
        self.assertIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", verifier)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", verifier)
        self.assertIn("verify_upstream_executor_dispatch_authority", verifier)
        self.assertIn("_read_intent_by_fingerprint", verifier)
        self.assertNotIn("verify_recovery_ledger_authority", verifier)
        self.assertIn("_read_intent_by_fingerprint", verifier)
        self.assertIn("lookup(", verifier)
        self.assertIn("custom_wakeup_transport_authority_used", verifier)
        self.assertIn("Enforce independent upstream dispatch authority", workflow)
        self.assertIn("needs: verify-upstream-dispatch-authority", planner)
        self.assertIn(
            "needs.verify-upstream-dispatch-authority.outputs.admitted == 'true'",
            planner,
        )
        self.assertIn("needs: verify-upstream-dispatch-authority", native)
        self.assertIn(
            "needs.verify-upstream-dispatch-authority.outputs.admitted == 'true'",
            native,
        )

    def test_target_selection_requires_one_exact_event_or_dispatch_subject(self):
        dispatch = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="641",
            workflow_event="",
            workflow_run_head="",
            event_prs=[],
        )
        self.assertEqual(dispatch["state"], "CANDIDATE")
        self.assertEqual(dispatch["pr_numbers"], [641])

        no_event = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="",
            workflow_event="pull_request",
            workflow_run_head="a" * 40,
            event_prs=[],
        )
        self.assertEqual(no_event["state"], "NO_EVENT_SUBJECT")
        self.assertEqual(
            no_event["first_blocker"], "NO_EXACT_WORKFLOW_RUN_PULL_REQUEST"
        )
        self.assertEqual(no_event["status_publication"], "FORBIDDEN")

        ambiguous = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="",
            workflow_event="pull_request",
            workflow_run_head="a" * 40,
            event_prs=[
                self.event_pr(641),
                self.event_pr(642),
            ],
        )
        self.assertEqual(ambiguous["state"], "AMBIGUOUS_EVENT_SUBJECT")
        self.assertEqual(
            ambiguous["first_blocker"], "WORKFLOW_RUN_MULTIPLE_PULL_REQUESTS"
        )
        self.assertEqual(ambiguous["status_publication"], "FORBIDDEN")

        scheduled = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="",
            workflow_event="schedule",
            workflow_run_head="a" * 40,
            event_prs=[self.event_pr()],
        )
        self.assertEqual(scheduled["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(
            scheduled["first_blocker"], "SCHEDULED_OR_MANUAL_WORKFLOW_RUN_FORBIDDEN"
        )

        cross_repository = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="",
            workflow_event="pull_request",
            workflow_run_head="a" * 40,
            event_prs=[self.event_pr(repository="other/qik-vrt")],
        )
        self.assertEqual(cross_repository["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(
            cross_repository["first_blocker"],
            "WORKFLOW_RUN_PULL_REQUEST_NOT_ROLE_LOCAL",
        )

    def test_workflow_run_uses_associated_pr_head_not_trusted_main_head(self):
        trusted_main_head = "a" * 40
        result = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="",
            workflow_event="pull_request_target",
            workflow_run_head=trusted_main_head,
            event_prs=[self.event_pr(head=self.head)],
        )
        self.assertEqual(result["state"], "CANDIDATE")
        self.assertEqual(result["pr_numbers"], [641])
        self.assertEqual(result["expected_head"], self.head)
        self.assertEqual(result["workflow_run_head"], trusted_main_head)

    def test_workflow_run_pr_head_is_required_and_fail_closed(self):
        missing = self.event_pr()
        missing["head"] = {}
        result = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="",
            workflow_event="pull_request_target",
            workflow_run_head="a" * 40,
            event_prs=[missing],
        )
        self.assertEqual(result["state"], "INELIGIBLE_EVENT_TARGET")
        self.assertEqual(
            result["first_blocker"], "WORKFLOW_RUN_PULL_REQUEST_HEAD_MISSING"
        )
        self.assertIsNone(result["expected_head"])

    def test_workflow_dispatch_child_uses_only_exact_v3_locator_as_wakeup(self):
        from tools.qikvrt_requested_review_executor import requested_review_run_title

        evaluator = "a" * 40
        title = requested_review_run_title(
            evaluator_sha=evaluator,
            pr_number=641,
            head_sha=self.head,
            fingerprint="c" * 64,
            transport_intent_sha256="d" * 64,
            transport_attempt=1,
        )
        result = MODULE.select_required_review_targets(
            repository="example/qik-vrt",
            requested_pr="",
            workflow_event="workflow_dispatch",
            workflow_run_head=evaluator,
            event_prs=[],
            workflow_run_display_title=title,
            trusted_evaluator_sha=evaluator,
        )
        self.assertEqual(result["state"], "CANDIDATE")
        self.assertEqual(result["pr_numbers"], [641])
        self.assertEqual(result["expected_head"], self.head)

        for bad_title, trusted in ((title + " suffix", evaluator), (title, "e" * 40)):
            blocked = MODULE.select_required_review_targets(
                repository="example/qik-vrt",
                requested_pr="",
                workflow_event="workflow_dispatch",
                workflow_run_head=evaluator,
                event_prs=[],
                workflow_run_display_title=bad_title,
                trusted_evaluator_sha=trusted,
            )
            self.assertNotEqual(blocked["state"], "CANDIDATE")

    def test_upstream_executor_dispatch_requires_exact_protected_acceptance(self):
        evaluator, workflow_id, run, lookup = (
            self.executor_dispatch_authority_fixture()
        )
        admitted = MODULE.verify_upstream_executor_dispatch_authority(
            repository="example/qik-vrt",
            evaluator_sha=evaluator,
            executor_workflow_id=workflow_id,
            run=run,
            core_lookups=[lookup],
        )
        self.assertTrue(admitted["admitted"])
        self.assertEqual(
            admitted["source"]["kind"],
            "PROTECTED_SHARED_OUTBOX_ACCEPTANCE",
        )
        self.assertEqual(admitted["source"]["lane"], "exact-review-dispatch")

        missing = MODULE.verify_upstream_executor_dispatch_authority(
            repository="example/qik-vrt",
            evaluator_sha=evaluator,
            executor_workflow_id=workflow_id,
            run=run,
        )
        self.assertFalse(missing["admitted"])
        self.assertEqual(
            missing["first_blocker"],
            "UPSTREAM_EXECUTOR_DISPATCH_AUTHORITY_MISSING",
        )

        incomplete = MODULE.verify_upstream_executor_dispatch_authority(
            repository="example/qik-vrt",
            evaluator_sha=evaluator,
            executor_workflow_id=workflow_id,
            run=run,
            core_lookups=[lookup],
            core_lookups_complete=False,
        )
        self.assertFalse(incomplete["admitted"])
        self.assertEqual(
            incomplete["first_blocker"],
            "UPSTREAM_EXECUTOR_DISPATCH_AUTHORITY_READBACK_INCOMPLETE",
        )

    def test_custom_wakeup_ledger_is_not_a_transport_authority(self):
        workflow = (
            ROOT / ".github" / "workflows" / "qikvrt_required_review_gate.yml"
        ).read_text(encoding="utf-8")
        verifier = workflow.split(
            "  verify-upstream-dispatch-authority:\n", 1
        )[1].split("  plan-required-gate:\n", 1)[0]
        self.assertNotIn("review_wakeup_record_path", verifier)
        self.assertNotIn("verify_recovery_ledger_authority", verifier)
        self.assertNotIn("review_wakeup_record=", verifier)
        self.assertIn("'custom_wakeup_transport_authority_used':False", verifier)

    def test_dispatch_title_or_inputs_cannot_replace_independent_authority(self):
        evaluator, workflow_id, run, lookup = (
            self.executor_dispatch_authority_fixture()
        )
        for mutation in ("child", "input", "lane", "run"):
            changed_run = copy.deepcopy(run)
            changed_lookup = copy.deepcopy(lookup)
            if mutation == "child":
                changed_lookup["acceptance"]["1"]["child"]["run_id"] += 1
            elif mutation == "input":
                changed_lookup["intent"]["payload"]["request"]["inputs"][
                    "head"
                ] = "e" * 40
            elif mutation == "lane":
                changed_lookup["lane"] = "ruleset-dispatch"
            else:
                changed_run["head_sha"] = "e" * 40
            result = MODULE.verify_upstream_executor_dispatch_authority(
                repository="example/qik-vrt",
                evaluator_sha=evaluator,
                executor_workflow_id=workflow_id,
                run=changed_run,
                core_lookups=[changed_lookup],
            )
            self.assertFalse(result["admitted"], mutation)

    def test_same_run_attempt_two_requires_shared_core_child_recovery(self):
        evaluator, workflow_id, run, lookup = (
            self.executor_dispatch_authority_fixture()
        )
        run["run_attempt"] = 2
        recovered_child = copy.deepcopy(lookup["acceptance"]["1"]["child"])
        recovered_child.update(
            run_attempt=2,
            status="completed",
            conclusion="success",
        )
        lookup["child_recovery"] = {
            "1": {"acceptance": {"child": recovered_child}}
        }
        admitted = MODULE.verify_upstream_executor_dispatch_authority(
            repository="example/qik-vrt",
            evaluator_sha=evaluator,
            executor_workflow_id=workflow_id,
            run=run,
            core_lookups=[lookup],
        )
        self.assertTrue(admitted["admitted"])
        self.assertEqual(admitted["source"]["child_run_attempt"], 2)

        for label, changed_lookup in (
            ("missing", {**lookup, "child_recovery": {}}),
            (
                "unrelated run",
                {
                    **lookup,
                    "child_recovery": {
                        "1": {
                            "acceptance": {
                                "child": {**recovered_child, "run_id": 999999}
                            }
                        }
                    },
                },
            ),
        ):
            with self.subTest(label=label):
                blocked = MODULE.verify_upstream_executor_dispatch_authority(
                    repository="example/qik-vrt",
                    evaluator_sha=evaluator,
                    executor_workflow_id=workflow_id,
                    run=run,
                    core_lookups=[changed_lookup],
                )
                self.assertFalse(blocked["admitted"])
                self.assertEqual(
                    blocked["first_blocker"],
                    "UPSTREAM_EXECUTOR_DISPATCH_AUTHORITY_MISSING",
                )

    def test_two_independent_dispatch_authorities_hold_as_ambiguous(self):
        evaluator, workflow_id, run, lookup = (
            self.executor_dispatch_authority_fixture()
        )
        duplicate = copy.deepcopy(lookup)
        duplicate["lane"] = "requested-review-dispatch"
        result = MODULE.verify_upstream_executor_dispatch_authority(
            repository="example/qik-vrt",
            evaluator_sha=evaluator,
            executor_workflow_id=workflow_id,
            run=run,
            core_lookups=[lookup, duplicate],
        )
        self.assertFalse(result["admitted"])
        self.assertEqual(
            result["first_blocker"],
            "UPSTREAM_EXECUTOR_DISPATCH_AUTHORITY_AMBIGUOUS",
        )


if __name__ == "__main__":
    unittest.main()
