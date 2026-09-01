# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import pathlib
import unittest

from tools import qikvrt_review_admission_recovery as module
from tools import qikvrt_native_account_review as native_review


REPOSITORY = "Goldkelch/qik-vrt"
REPOSITORY_ID = 1271407206
MAIN = "a" * 40
PATH = ".github/workflows/qikvrt_requested_review_executor.yml"
LOCATOR = "qikvrt-rr-v3"
ROOT = pathlib.Path(__file__).resolve().parents[1]


class ReviewAdmissionRecoveryTests(unittest.TestCase):
    def source_run(self, **overrides):
        value = {
            "id": 33483459999,
            "run_attempt": 1,
            "workflow_id": 8100,
            "path": PATH,
            "repository": {
                "id": REPOSITORY_ID, "full_name": REPOSITORY,
            },
            "event": "pull_request_target",
            # pull_request_target executes from the trusted default branch;
            # the candidate identity exists only in pull_requests[].head.
            "head_branch": "main",
            "head_sha": MAIN,
            "display_title": (
                f"{LOCATOR} e={MAIN} p=event h=event f=event i=event a=event"
            ),
            "status": "completed",
            "conclusion": "cancelled",
            "created_at": "2026-09-01T08:25:00Z",
            "jobs_total": 0,
            "artifacts_total": 0,
            "pull_requests": [{
                "number": 935,
                "head": {
                    "ref": "release/pr935", "sha": "b" * 40,
                    # This is the real Workflow Runs REST embedded repo shape:
                    # it has id/name/url and does not promise full_name.
                    "repo": {
                        "id": REPOSITORY_ID, "name": "qik-vrt",
                        "url": f"https://api.github.com/repositories/{REPOSITORY_ID}",
                    },
                },
                "base": {
                    "ref": "main", "sha": MAIN,
                    "repo": {
                        "id": REPOSITORY_ID, "name": "qik-vrt",
                        "url": f"https://api.github.com/repositories/{REPOSITORY_ID}",
                    },
                },
            }],
        }
        value.update(overrides)
        return value

    def config(self):
        return {
            8100: {
                "path": PATH,
                "activation_locator": LOCATOR,
                "allowed_events": [
                    "pull_request_target",
                    "issue_comment",
                    "workflow_run",
                    "workflow_dispatch",
                ],
            }
        }

    def selection(self):
        value = module.select_recovery(
            [self.source_run()],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
        )
        value["live_subject"] = self.live_subject()
        return value

    def live_subject(self):
        return {
            "pr_number": 935,
            "head_sha": "b" * 40,
            "head_tree_sha": "d" * 40,
            "head_repository": REPOSITORY,
            "head_ref": "release/pr935",
            "base_sha": MAIN,
            "base_tree_sha": "e" * 40,
            "base_repository": REPOSITORY,
            "base_ref": "main",
        }

    def intent(self):
        return module.build_recovery_intent(
            self.selection(),
            recovery_repository=REPOSITORY,
            recovery_workflow_id=8200,
            recovery_workflow_path=(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            recovery_head_sha=MAIN,
        )

    def pull_request(self, number=935, head_sha="b" * 40):
        return {
            "number": number,
            "commits": 1,
            "state": "open",
            "head": {
                "sha": head_sha,
                "ref": f"release/pr{number}",
                "repo": {"full_name": REPOSITORY},
            },
            "base": {
                "sha": MAIN,
                "ref": "main",
                "repo": {"full_name": REPOSITORY},
            },
        }

    def human_review(
        self,
        *,
        review_id=7001,
        state="COMMENTED",
        submitted_at="2026-09-01T08:20:00Z",
        body="independent review",
        login="human-reviewer",
        user_id=4401,
        user_type="User",
        commit_id="b" * 40,
    ):
        return {
            "id": review_id,
            "state": state,
            "submitted_at": submitted_at,
            "body": body,
            "commit_id": commit_id,
            "user": {
                "id": user_id,
                "login": login,
                "type": user_type,
            },
        }

    def pr_commits(self, head_sha="b" * 40, tree_sha="d" * 40):
        return [{
            "sha": head_sha,
            "commit": {"tree": {"sha": tree_sha}},
        }]

    def human_observation(self, reviews, *, pull_requests=None):
        prs = pull_requests or [self.pull_request()]
        return module.observe_human_review_facts(
            prs,
            reviews_by_pr={pr["number"]: reviews for pr in prs},
            commits_by_pr={
                pr["number"]: self.pr_commits(pr["head"]["sha"])
                for pr in prs
            },
            repository=REPOSITORY,
            current_main_sha=MAIN,
            current_main_tree_sha="e" * 40,
        )

    def delegated_signer_fixture(self):
        pr = {
            "number": 935,
            "state": "open",
            "draft": False,
            "user": {"login": "ingolf-lohmann"},
            "base": {"ref": "main", "sha": MAIN},
            "head": {
                "sha": "b" * 40,
                "repo": {"full_name": REPOSITORY},
            },
            "requested_reviewers": [{"login": "Goldkelch"}],
        }
        receipt = {
            "schema": native_review.RECEIPT_SCHEMA,
            "repository": REPOSITORY,
            "pr_number": 935,
            "base_sha": MAIN,
            "head_sha": "b" * 40,
            "tree_sha": "d" * 40,
            "evidence_fingerprint": "f" * 64,
            "state": "TECHNICAL_CONTINUE",
            "mesh_disposition": "TECHNICAL_CONTINUE",
            "review_intake": {
                "event_name": "pull_request_target",
                "event_action": "review_requested",
                "requested_reviewer": "Goldkelch",
                "requested_target_observed": True,
            },
        }
        delegation = {
            "schema": native_review.DELEGATION_SCHEMA,
            "delegation_id": native_review.DELEGATION_ID,
            "state": native_review.DELEGATION_ACTIVE,
            "repositories": list(native_review.REPOSITORIES),
            "configured_platform_accounts": list(native_review.ACCOUNTS),
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
                    "environment": native_review.SECRET_ENVIRONMENT,
                    "deployment_branch_policy": "SELECTED_BRANCHES_ONLY",
                    "selected_branch": "main",
                    "protected_branches": True,
                    "environment_secret_names": list(
                        native_review.SECRET_ENVIRONMENT_NAMES
                    ),
                    "repository_scope_secret_names_absent": list(
                        native_review.FORBIDDEN_BROAD_SECRET_NAMES
                    ),
                    "repository_owner": {
                        "login": "Goldkelch", "id": 1001, "type": "User",
                    },
                    "organization_scope_secret_names_absent": [],
                    "organization_scope_readback": "NOT_APPLICABLE_USER_OWNER",
                    "settings_readback_complete": True,
                    "verified_at": "2026-09-01T09:00:00Z",
                    "verifier_login": "authority-admin",
                },
            },
        }
        plan = native_review.plan_native_account_review(
            repository=REPOSITORY,
            pr=pr,
            commit={"sha": "b" * 40, "tree": {"sha": "d" * 40}},
            receipt=receipt,
            reviews=[],
            delegation=delegation,
            native_rule_enforced=True,
            ledger_transport_exact=True,
            reobservation_exact=True,
            signer_run_id=8123,
            signer_run_attempt=1,
            signer_evaluator_sha=MAIN,
        )
        review = {
            "id": 7701,
            "state": "COMMENTED",
            "submitted_at": "2026-09-01T09:05:00Z",
            "body": plan["review_body"],
            "commit_id": "b" * 40,
            "user": {"id": 4001, "login": "Goldkelch", "type": "User"},
        }
        run = {
            "id": 8123,
            "run_attempt": 1,
            "workflow_id": 8201,
            "path": ".github/workflows/qikvrt_required_review_gate.yml",
            "repository": {"id": REPOSITORY_ID, "full_name": REPOSITORY},
            "event": "workflow_run",
            "head_branch": "main",
            "head_sha": MAIN,
            "display_title": (
                "QIKVRT required code-owner review admission-v2 "
                f"evaluator-{MAIN} source=9911"
            ),
            "status": "completed",
            "conclusion": "cancelled",
            "created_at": "2026-09-01T09:00:00Z",
            "jobs_total": 3,
            "artifacts_total": 1,
            "pull_requests": [],
        }
        return plan, review, pr, run

    def wakeup_intent(self, fact):
        return module.build_review_wakeup_intent(
            fact,
            head_ref="release/pr935",
            recovery_repository=REPOSITORY,
            recovery_repository_id=REPOSITORY_ID,
            recovery_workflow_id=8200,
            recovery_workflow_path=(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            recovery_head_sha=MAIN,
            requested_workflow_id=8100,
            requested_workflow_path=PATH,
            requested_workflow_sha=MAIN,
        )

    def wakeup_core_payload(self, intent, *, run_id=9001, run_attempt=1):
        return module.build_review_wakeup_core_payload(
            intent,
            producer_run_id=run_id,
            producer_run_attempt=run_attempt,
            producer_event="schedule",
        )

    def accepted_wakeup_core(self, intent, payload, *, child_run_id=9911):
        from tests.test_qikvrt_ruleset_outbox import MemoryBackend, artifact
        from tools import qikvrt_ruleset_outbox as core

        backend = MemoryBackend()
        core_intent = core.append_intent(
            backend, payload=payload, artifact=artifact(payload)
        )
        core.prepare_transport(
            backend,
            lane="exact-review-dispatch",
            sequence=core_intent["sequence"],
            attempt=1,
            request=core.request_for_transport_attempt(core_intent, 1),
            actor_run_id=9001,
            actor_run_attempt=1,
        )
        inputs = core_intent["payload"]["request"]["inputs"]
        title = (
            f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
            f"h={inputs['head']} f={inputs['fingerprint']} "
            f"i={core_intent['fingerprint']} a=1"
        )
        child = {
            "run_id": child_run_id,
            "run_attempt": 1,
            "workflow_id": 8100,
            "workflow_path": PATH,
            "event": "workflow_dispatch",
            "repository": REPOSITORY,
            "head_sha": MAIN,
            "status": "queued",
            "conclusion": None,
            "display_title": title,
        }
        core.record_acceptance(
            backend,
            lane="exact-review-dispatch",
            sequence=core_intent["sequence"],
            attempt=1,
            child=child,
        )
        return core.lookup_fingerprint(
            backend,
            lane="exact-review-dispatch",
            fingerprint=core_intent["fingerprint"],
        )

    def test_current_activation_zero_job_source_reruns_once(self):
        value = self.selection()
        self.assertEqual(value["state"], "RERUN_ATTEMPT_2")
        self.assertTrue(value["rerun_required"])
        self.assertEqual(value["selected"]["run_attempt"], 1)
        self.assertFalse(any(value["completion_claims"].values()))

    def test_live_legacy_zero_job_fixture_is_not_recoverable(self):
        # Exact live shape 33483449928 predates the admission-v2 witness.
        legacy = self.source_run(
            id=33483449928,
            display_title="QIKVRT requested review pr=935 head=event fp=event",
        )
        value = module.select_recovery(
            [legacy],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
        )
        self.assertEqual(value["state"], "EMPTY")

    def test_shared_outbox_requested_v3_child_is_not_local_retry_source(self):
        shared = self.source_run(
            event="workflow_dispatch",
            display_title=(
                f"qikvrt-rr-v3 e={MAIN} p=935 h={'b' * 40} "
                f"f={'1' * 64} i={'2' * 64} a=1"
            ),
            pull_requests=[],
        )
        value = module.select_recovery(
            [shared],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
        )
        self.assertEqual(value["state"], "EMPTY")

    def test_attempt_two_is_d0_3_and_never_attempt_three(self):
        value = module.select_recovery(
            [self.source_run(run_attempt=2)],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
        )
        self.assertEqual(value["state"], "RETRY_EXHAUSTED_D0_3")
        self.assertEqual(value["d0"], 3)
        self.assertFalse(value["rerun_required"])
        terminal = module.build_terminal_receipt(value)
        advanced = module.select_recovery(
            [
                self.source_run(run_attempt=2),
                self.source_run(id=33483460000),
            ],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
            consumed_sources={terminal["source_key"]},
        )
        self.assertEqual(advanced["selected"]["run_id"], 33483460000)

    def test_nonzero_jobs_or_artifacts_and_incomplete_source_are_rejected(self):
        cases = (
            self.source_run(jobs_total=1),
            self.source_run(artifacts_total=1),
            self.source_run(status="in_progress", conclusion=None),
            self.source_run(
                head_sha="c" * 40,
                pull_requests=[{
                    "number": 935,
                    "head": {
                        "ref": "release/pr935", "sha": "b" * 40,
                        "repo": {"id": REPOSITORY_ID},
                    },
                    "base": {
                        "ref": "main", "sha": MAIN,
                        "repo": {"id": REPOSITORY_ID},
                    },
                }],
            ),
            self.source_run(path=".github/workflows/untrusted.yml"),
            self.source_run(repository={"full_name": "elsewhere/qik-vrt"}),
        )
        for run in cases:
            with self.subTest(run=run):
                value = module.select_recovery(
                    [run],
                    target_configs=self.config(),
                    repository=REPOSITORY,
                    repository_id=REPOSITORY_ID,
                    current_main_sha=MAIN,
                    current_run_id=999,
                )
                self.assertEqual(value["state"], "EMPTY")

    def test_every_retryable_terminal_zero_job_result_is_bounded_and_main_advance_is_terminal(self):
        for conclusion in (
            "success", "failure", "cancelled", "skipped", "neutral",
            "timed_out", "startup_failure", "stale",
            "future_terminal_value",
        ):
            with self.subTest(conclusion=conclusion):
                value = module.select_recovery(
                    [self.source_run(conclusion=conclusion)],
                    target_configs=self.config(),
                    repository=REPOSITORY,
                    repository_id=REPOSITORY_ID,
                    current_main_sha=MAIN,
                    current_run_id=999,
                )
                self.assertEqual(value["state"], "RERUN_ATTEMPT_2")
        action_required = module.select_recovery(
            [self.source_run(conclusion="action_required")],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
        )
        self.assertEqual(action_required["state"], "ACTION_REQUIRED_D0_3")
        self.assertEqual(action_required["d0"], 3)
        self.assertFalse(action_required["rerun_required"])
        self.assertEqual(
            action_required["first_blocker"],
            "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
        )
        action_required_terminal = module.build_terminal_receipt(action_required)
        self.assertEqual(
            action_required_terminal["first_blocker"],
            "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
        )
        with self.assertRaises(module.AdmissionRecoveryError):
            module.build_recovery_intent(
                action_required,
                recovery_repository=REPOSITORY,
                recovery_workflow_id=8200,
                recovery_workflow_path=(
                    ".github/workflows/qikvrt_review_admission_recovery.yml"
                ),
                recovery_head_sha=MAIN,
            )
        advanced = module.select_recovery(
            [self.source_run()],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha="c" * 40,
            current_run_id=999,
        )
        self.assertEqual(advanced["state"], "SUPERSEDED_EVALUATOR_D0_3")
        self.assertEqual(advanced["d0"], 3)
        self.assertFalse(advanced["rerun_required"])
        terminal = module.build_terminal_receipt(advanced)
        self.assertEqual(terminal["state"], "SUPERSEDED_EVALUATOR_D0_3")
        self.assertEqual(
            terminal["first_blocker"],
            "ZERO_JOB_RECOVERY_EVALUATOR_SUPERSEDED",
        )
        forged = copy.deepcopy(terminal)
        forged["first_blocker"] = "PASS_LIKE_FREE_FORM_CLAIM"
        forged.pop("receipt_sha256")
        forged["receipt_sha256"] = module._canonical_sha256(forged)
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "boundary differs"
        ):
            module.validate_terminal_receipt(forged)

    def test_intent_is_sealed_technical_only_and_preeffect_exact(self):
        intent = self.intent()
        self.assertFalse(intent["native_account_review_authorized"])
        repeated = module.build_recovery_intent(
            self.selection(),
            recovery_repository=REPOSITORY,
            recovery_workflow_id=8200,
            recovery_workflow_path=(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            recovery_head_sha=MAIN,
        )
        self.assertEqual(intent, repeated)
        binding = module.build_recovery_producer_binding(
            intent, recovery_run_id=8800, recovery_run_attempt=1
        )
        self.assertEqual(binding["intent_sha256"], intent["intent_sha256"])
        effect = module.plan_recovery_effect(
            intent,
            source_run=self.source_run(),
            source_jobs_total=0,
            source_artifacts_total=0,
            current_main_sha=MAIN,
            live_subject=self.live_subject(),
            current_recovery_producer_binding=binding,
            current_recovery_run_id=8800,
            current_recovery_run_attempt=1,
        )
        self.assertEqual(effect["authorized_attempt"], 2)
        self.assertFalse(effect["native_account_review_authorized"])
        replay = module.plan_recovery_effect(
            intent,
            source_run=self.source_run(),
            source_jobs_total=0,
            source_artifacts_total=0,
            current_main_sha=MAIN,
            live_subject=self.live_subject(),
            current_recovery_producer_binding=binding,
            current_recovery_run_id=8800,
            current_recovery_run_attempt=2,
        )
        self.assertEqual(
            replay["effect"], "POLL_ONLY_CONSUMED_SAME_RUN_ATTEMPT_2"
        )
        self.assertFalse(replay["new_rerun_post_authorized"])

        tampered = copy.deepcopy(intent)
        tampered["source"]["event"] = "workflow_dispatch"
        with self.assertRaisesRegex(module.AdmissionRecoveryError, "digest"):
            module.plan_recovery_effect(
                tampered,
                source_run=self.source_run(),
                source_jobs_total=0,
                source_artifacts_total=0,
                current_main_sha=MAIN,
                live_subject=self.live_subject(),
                current_recovery_producer_binding=binding,
                current_recovery_run_id=8800,
                current_recovery_run_attempt=1,
            )

    def test_preeffect_source_drift_and_attempt2_readback_are_bound(self):
        intent = self.intent()
        binding = module.build_recovery_producer_binding(
            intent, recovery_run_id=8800, recovery_run_attempt=1
        )
        with self.assertRaisesRegex(module.AdmissionRecoveryError, "drifted"):
            module.plan_recovery_effect(
                intent,
                source_run=self.source_run(
                    status="in_progress", conclusion=None
                ),
                source_jobs_total=0,
                source_artifacts_total=0,
                current_main_sha=MAIN,
                live_subject=self.live_subject(),
                current_recovery_producer_binding=binding,
                current_recovery_run_id=8800,
                current_recovery_run_attempt=1,
            )

        drifted_subject = self.live_subject()
        drifted_subject["head_tree_sha"] = "f" * 40
        with self.assertRaisesRegex(module.AdmissionRecoveryError, "subject drifted"):
            module.plan_recovery_effect(
                intent,
                source_run=self.source_run(),
                source_jobs_total=0,
                source_artifacts_total=0,
                current_main_sha=MAIN,
                live_subject=drifted_subject,
                current_recovery_producer_binding=binding,
                current_recovery_run_id=8800,
                current_recovery_run_attempt=1,
            )

        rerun = self.source_run(
            run_attempt=2, status="queued", conclusion=None
        )
        result = module.verify_rerun_readback(intent, rerun)
        self.assertTrue(result["transport_ack_observed"])
        self.assertEqual(result["rerun_attempt"], 2)
        self.assertFalse(result["native_account_review_authorized"])

        with self.assertRaisesRegex(module.AdmissionRecoveryError, "differs"):
            module.verify_rerun_readback(
                intent, {**rerun, "head_sha": "d" * 40}
            )

    def test_recovery_workflow_splits_read_plan_from_exact_actions_write(self):
        workflow = (
            ROOT / ".github/workflows/qikvrt_review_admission_recovery.yml"
        ).read_text(encoding="utf-8")
        plan = workflow.split("  plan-one:\n", 1)[1].split(
            "  rerun-one:\n", 1
        )[0]
        effect = workflow.split("  rerun-one:\n", 1)[1]
        self.assertIn("permissions: {}", workflow)
        self.assertIn("      actions: read", plan)
        self.assertNotIn("actions: write", plan)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("statuses: write", workflow)
        self.assertNotIn("QIKVRT_GOLDKELCH_REVIEW_TOKEN", workflow)
        self.assertNotIn("QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN", workflow)
        self.assertIn("      actions: write", effect)
        self.assertIn("Preserve content-addressed recovery intent", plan)
        self.assertLess(
            workflow.index("Preserve content-addressed recovery intent"),
            workflow.index("Revalidate and rerun the same exact source"),
        )
        self.assertIn("X-GitHub-Api-Version: 2026-03-10", effect)
        self.assertIn("plan_recovery_effect", effect)
        self.assertIn("qikvrt-admission-recovery-terminal-", workflow)
        self.assertIn("consumed_sources=consumed", workflow)
        self.assertEqual(
            workflow.count(
                "GH_TOKEN: ${{ secrets.QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN }}"
            ),
            6,
        )
        for step in (
            "Persist only the sealed admission-inbox plan by exact FF-CAS",
            "Persist source transition on the sharded FIFO before any rerun",
            "Append exact same-run attempt-two acceptance",
            "Persist only the sealed review-observation plan by exact FF-CAS",
            "Append intent or terminal state with an exact FF-CAS update",
            "Append exact ACK with an FF-CAS update",
        ):
            self.assertIn(step, workflow)
        for readback in (
            "ADMISSION_INBOX_INGEST_FILE_READBACK_DRIFT",
            "ADMISSION_INBOX_PERSIST_FILE_READBACK_DRIFT",
            "ADMISSION_INBOX_ACCEPT_FILE_READBACK_DRIFT",
            "REVIEW_OBSERVATION_FILE_READBACK_DRIFT",
            "REVIEW_WAKEUP_FILE_READBACK_DIFFERS",
            "REVIEW_WAKEUP_ACK_FILE_READBACK_DIFFERS",
        ):
            self.assertIn(readback, workflow)
        self.assertIn(
            "prepare-child-rerun --lane \"$CORE_LANE\"", workflow
        )
        self.assertIn(
            "accept-child-rerun --lane \"$CORE_LANE\"", workflow
        )
        self.assertIn("CORE_MESH_REVIEW_CHILD_ZERO_JOB", workflow)
        self.assertIn("CORE_EXACT_REVIEW_CHILD_ZERO_JOB", workflow)
        self.assertIn("prepare-shared-core-child-rerun:", workflow)
        self.assertIn("accept-shared-core-child-rerun:", workflow)
        self.assertIn("plan-shared-core-child-rerun-terminal:", workflow)
        self.assertIn("terminalize-shared-core-child-rerun:", workflow)
        observer_block = workflow.split(
            "  plan-shared-core-child-rerun-terminal:\n", 1
        )[1].split("  terminalize-shared-core-child-rerun:\n", 1)[0]
        terminalizer_block = workflow.split(
            "  terminalize-shared-core-child-rerun:\n", 1
        )[1].split("  persist-admission-source:\n", 1)[0]
        self.assertNotIn("environment:", observer_block)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", observer_block)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", observer_block)
        self.assertIn("environment: qikvrt-outbox-ledger-authority", terminalizer_block)
        self.assertIn("queue: max", terminalizer_block)
        self.assertEqual(
            terminalizer_block.count(
                "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN"
            ), 3,
        )
        self.assertEqual(
            terminalizer_block.count(
                "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN"
            ), 4,
        )
        self.assertEqual(
            terminalizer_block.count(
                "${{ secrets.QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN }}"
            ),1,
        )
        self.assertEqual(
            terminalizer_block.count(
                "${{ secrets.QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN }}"
            ),2,
        )
        self.assertIn("record-observation --lane \"$CORE_LANE\"", terminalizer_block)
        self.assertIn("terminalize --lane \"$CORE_LANE\"", terminalizer_block)
        self.assertIn(
            "validate_shared_review_core_child_rerun_terminal_readback",
            terminalizer_block,
        )
        self.assertIn(
            "needs.terminalize-shared-core-child-rerun.result == 'success'",
            workflow,
        )
        self.assertIn("shared_core_terminal_readback", workflow)
        self.assertIn("ADOPT_DURABLE_SHARED_CORE_TERMINAL", workflow)
        self.assertIn("core_terminal_adoption_required", workflow)
        self.assertIn("core-child-rerun-preterminal-lookup.json", workflow)
        self.assertIn("item.get('expired') is False", workflow)
        self.assertIn("CORE_OBSERVATION_ARTIFACT_BYTES_DRIFT", workflow)
        self.assertNotIn(
            "CORE_ACCEPT_ARTIFACT: ${{ needs.accept-shared-core-child-rerun.outputs.artifact_name }}\n"
            "    steps:",
            workflow.split("  accept-shared-core-child-rerun:\n", 1)[1].split(
                "  persist-admission-rerun-readback:\n", 1
            )[0],
        )
        core_blocks = {
            "prepare-shared-core-child-rerun": workflow.split(
                "  prepare-shared-core-child-rerun:\n", 1
            )[1].split("  rerun-one:\n", 1)[0],
            "accept-shared-core-child-rerun": workflow.split(
                "  accept-shared-core-child-rerun:\n", 1
            )[1].split("  persist-admission-rerun-readback:\n", 1)[0],
        }
        for block_name, block in core_blocks.items():
            self.assertIn("environment: qikvrt-outbox-ledger-authority", block)
            self.assertIn("queue: max", block)
            self.assertEqual(
                block.count("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN"), 2
            )
            self.assertEqual(
                block.count("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN"), 2
            )
            self.assertIn("reobserve_shared_review_core_child_recovery", block)
        self.assertIn("core-post-prepare-lookup.json", workflow)
        self.assertIn("core-post-accept-lookup.json", workflow)
        self.assertIn("POLL_ONLY_CONSUMED_SAME_RUN_ATTEMPT_2", workflow)
        self.assertIn("RERUN_TRANSPORT_UNACKNOWLEDGED_D0_3", workflow)
        self.assertIn("RERUN_TRANSPORT_UNACKNOWLEDGED", workflow)
        self.assertNotIn("DISPATCH_ATTEMPT_2", workflow)
        for writer_job in (
            "ingest-admission-source", "persist-admission-source",
            "prepare-shared-core-child-rerun",
            "accept-shared-core-child-rerun",
            "terminalize-shared-core-child-rerun",
            "persist-admission-rerun-readback",
            "advance-review-observation", "persist-review-wakeup",
            "persist-review-wakeup-ack",
        ):
            block=__import__("re").split(
                r"\n  (?=[a-zA-Z0-9_-]+:\n)",
                workflow.split(f"  {writer_job}:\n",1)[1],
                maxsplit=1,
            )[0]
            self.assertIn("queue: max",block,writer_job)

        # Compile every embedded Python program, including the side chain that
        # runs only after the original preparation actor is terminal.
        lines=workflow.splitlines()
        programs=[]
        index=0
        while index < len(lines):
            if "<<'PY'" not in lines[index]:
                index += 1
                continue
            start=index
            index += 1
            body=[]
            while index < len(lines) and lines[index].strip() != "PY":
                body.append(lines[index])
                index += 1
            self.assertLess(index,len(lines),f"unclosed heredoc at {start+1}")
            indents=[len(item)-len(item.lstrip()) for item in body if item.strip()]
            indent=min(indents) if indents else 0
            programs.append("\n".join(item[indent:] for item in body))
            index += 1
        self.assertGreaterEqual(len(programs),31)
        for program in programs:
            compile(program,"<review-admission-workflow>","exec")

    def test_real_workflow_run_embedded_repo_shape_is_accepted(self):
        source = self.source_run()
        self.assertNotIn("full_name", source["pull_requests"][0]["head"]["repo"])
        value = self.selection()
        self.assertEqual(value["state"], "RERUN_ATTEMPT_2")
        wrong = copy.deepcopy(source)
        wrong["pull_requests"][0]["head"]["repo"]["id"] += 1
        selected = module.select_recovery(
            [wrong],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
        )
        self.assertEqual(selected["state"], "EMPTY")

    def test_admission_source_inbox_is_sharded_deduped_and_bounded(self):
        source = module.build_admission_inbox_source(
            self.source_run(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            target_configs=self.config(),
        )
        exact = module.validate_admission_inbox_source(source)
        slot = module.build_admission_inbox_slot(exact, sequence=1001)
        self.assertEqual(
            module.validate_admission_inbox_slot(slot)["source"], exact
        )
        self.assertIn(
            exact["source_fingerprint"],
            module.admission_inbox_locator_path(
                exact["source_fingerprint"]
            ),
        )
        self.assertTrue(
            module.admission_inbox_slot_path(1001).endswith(
                "/00000000000000001001.json"
            )
        )
        # More than GitHub's filtered-run cap is irrelevant to one exact slot.
        foreign = [f"foreign-{index}" for index in range(1001)]
        self.assertEqual(len(foreign), 1001)
        self.assertEqual(
            module.validate_admission_inbox_slot(slot)["sequence"], 1001
        )

    def test_recovery_ledger_genesis_is_external_and_deletion_protected(self):
        genesis = module.build_recovery_ledger_genesis(
            lane="admission-source-rerun",
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            initialized_at="2026-09-01T08:00:00Z",
        )
        exact = module.validate_recovery_ledger_genesis(
            genesis,
            lane="admission-source-rerun",
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
        )
        self.assertTrue(exact["no_silent_reinitialization"])
        self.assertTrue(exact["deletion_protection_required"])
        self.assertTrue(exact["update_protection_required"])
        self.assertTrue(exact["non_fast_forward_protection_required"])
        self.assertEqual(
            exact["writer_environment"], "qikvrt-outbox-ledger-authority"
        )
        wakeup_genesis = module.build_recovery_ledger_genesis(
            lane="review-wakeup",
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            initialized_at="2026-09-01T08:00:00Z",
        )
        self.assertEqual(
            module.validate_recovery_ledger_genesis(
                wakeup_genesis,
                lane="review-wakeup",
                repository=REPOSITORY,
                repository_id=REPOSITORY_ID,
            )["record_schema_epoch"],
            "qikvrt_human_review_transition_fact_v2",
        )
        self.assertEqual(
            wakeup_genesis["migration_policy"],
            "EXTERNAL_EMPTY_GENESIS_NO_IN_PLACE_MIGRATION",
        )
        extra = copy.deepcopy(wakeup_genesis)
        extra["PASS"] = True
        extra.pop("genesis_sha256")
        extra["genesis_sha256"] = module._canonical_sha256(extra)
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "genesis shape differs"
        ):
            module.validate_recovery_ledger_genesis(
                extra,
                lane="review-wakeup",
                repository=REPOSITORY,
                repository_id=REPOSITORY_ID,
            )
        tampered = copy.deepcopy(genesis)
        tampered["no_silent_reinitialization"] = False
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "digest"
        ):
            module.validate_recovery_ledger_genesis(
                tampered,
                lane="admission-source-rerun",
                repository=REPOSITORY,
                repository_id=REPOSITORY_ID,
            )

    def test_recovery_ledger_authority_requires_exact_sole_app_ruleset(self):
        lane = "review-wakeup"
        ruleset = {
            "id": 9191,
            "target": "branch",
            "source_type": "Repository",
            "source": REPOSITORY,
            "enforcement": "active",
            "conditions": {"ref_name": {
                "include": ["refs/heads/qikvrt/review-wakeup-ledger-v1"],
                "exclude": [],
            }},
            "rules": [
                {"type": "update"},
                {"type": "deletion"},
                {"type": "non_fast_forward"},
            ],
            "bypass_actors": [{
                "actor_id": 42,
                "actor_type": "Integration",
                "bypass_mode": "always",
            }],
        }
        branch_rules = [
            {"type": item["type"], "ruleset_id": 9191}
            for item in ruleset["rules"]
        ]

        def api(path):
            if path == "installation":
                return {"app_id": 42}
            if path == "repos/Goldkelch/qik-vrt":
                return {"owner": {
                    "login": "Goldkelch", "type": "User", "id": 293941403,
                }}
            if "/rules/branches/" in path:
                return branch_rules
            if path.endswith("/rulesets/9191"):
                return ruleset
            if "/git/ref/heads/" in path:
                return {"object": {"sha": "9" * 40}}
            if path.endswith("/environments/qikvrt-outbox-ledger-authority"):
                return {
                    "name": "qikvrt-outbox-ledger-authority",
                    "protection_rules": [{"type": "required_reviewers"}],
                    "deployment_branch_policy": {
                        "protected_branches": False,
                        "custom_branch_policies": True,
                    },
                }
            if "/deployment-branch-policies?" in path:
                return {
                    "total_count": 1,
                    "branch_policies": [{"name": "main", "type": "branch"}],
                }
            if "/environments/qikvrt-outbox-ledger-authority/secrets?" in path:
                return {
                    "total_count": 2,
                    "secrets": [
                        {"name": "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN"},
                        {"name": "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN"},
                    ],
                }
            if path.startswith("repos/Goldkelch/qik-vrt/actions/secrets?"):
                return {"total_count": 0, "secrets": []}
            if path.startswith("orgs/Goldkelch/actions/secrets?"):
                raise AssertionError("user-owner org inventory must not be read")
            raise AssertionError(path)

        proof = module.verify_recovery_ledger_authority(
            lane=lane,
            repository=REPOSITORY,
            writer_actor_id=42,
            writer_group="qikvrt-outbox-ledger-v2-review-wakeup",
            api=api,
        )
        self.assertTrue(proof["verified"])
        self.assertTrue(proof["external_configuration_verified"])
        self.assertEqual(proof["deployment_branch"], "main")
        self.assertTrue(proof["repository_scope_fallback_names_absent"])
        self.assertTrue(proof["organization_scope_fallback_names_absent"])
        self.assertEqual(
            proof["repository_owner"],
            {"login": "Goldkelch", "type": "User", "id": 293941403},
        )
        self.assertEqual(
            proof["organization_scope_readback"],
            "NOT_APPLICABLE_USER_OWNER",
        )
        effect_proof = module.build_recovery_ledger_effect_authority_readback(
            proof,
            lane=lane,
            evaluator_sha=MAIN,
            effect_run_id=9001,
            effect_run_attempt=2,
            effect_run_started_at="2026-09-01T08:01:02Z",
        )
        self.assertEqual(
            module.validate_recovery_ledger_effect_authority_readback(
                effect_proof, lane=lane
            ),
            effect_proof,
        )
        self.assertIn(
            effect_proof["readback_sha256"],
            module.recovery_ledger_effect_authority_readback_path(
                effect_proof, lane=lane
            ),
        )

        def broad_secret_api(path):
            value = api(path)
            if path.startswith("repos/Goldkelch/qik-vrt/actions/secrets?"):
                return {
                    "total_count": 1,
                    "secrets": [{
                        "name": "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN"
                    }],
                }
            return value

        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,
            "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED",
        ):
            module.verify_recovery_ledger_authority(
                lane=lane,
                repository=REPOSITORY,
                writer_actor_id=42,
                writer_group="qikvrt-outbox-ledger-v2-review-wakeup",
                api=broad_secret_api,
            )

        def organization_api(path):
            if path == "repos/Goldkelch/qik-vrt":
                return {"owner": {
                    "login": "Goldkelch",
                    "type": "Organization",
                    "id": 293941403,
                }}
            if path.startswith("orgs/Goldkelch/actions/secrets?"):
                return {"total_count": 0, "secrets": []}
            return api(path)

        organization_proof = module.verify_recovery_ledger_authority(
            lane=lane,
            repository=REPOSITORY,
            writer_actor_id=42,
            writer_group="qikvrt-outbox-ledger-v2-review-wakeup",
            api=organization_api,
        )
        self.assertEqual(
            organization_proof["organization_scope_readback"],
            "VERIFIED_ORGANIZATION_SECRET_INVENTORY",
        )

        def missing_organization_inventory_api(path):
            if path == "repos/Goldkelch/qik-vrt":
                return {"owner": {
                    "login": "Goldkelch",
                    "type": "Organization",
                    "id": 293941403,
                }}
            if path.startswith("orgs/Goldkelch/actions/secrets?"):
                raise RuntimeError("404 organization secret inventory")
            return api(path)

        with self.assertRaisesRegex(RuntimeError, "404"):
            module.verify_recovery_ledger_authority(
                lane=lane,
                repository=REPOSITORY,
                writer_actor_id=42,
                writer_group="qikvrt-outbox-ledger-v2-review-wakeup",
                api=missing_organization_inventory_api,
            )
        forged = copy.deepcopy(ruleset)
        forged["bypass_actors"].append({
            "actor_id": 43,
            "actor_type": "Integration",
            "bypass_mode": "always",
        })
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "authority differs"
        ):
            module.validate_recovery_ledger_rulesets(
                [forged], lane=lane, writer_actor_id=42
            )
        broad = copy.deepcopy(ruleset)
        broad["conditions"]["ref_name"]["include"] = ["refs/heads/qikvrt/*"]
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "absent or ambiguous"
        ):
            module.validate_recovery_ledger_rulesets(
                [broad], lane=lane, writer_actor_id=42
            )

    def test_admission_reconcile_cursor_is_bounded_and_wraps_fairly(self):
        cursor = module.empty_admission_scan_cursor()
        cursor = module.bind_admission_scan_window(
            cursor,
            upper_created_at="2026-09-01T08:00:00Z",
            repository_created_at="2026-01-01T00:00:00Z",
        )
        capped = module.shrink_admission_scan_window(
            cursor, declared_total=1000
        )
        self.assertEqual(len(capped["deferred_windows"]), 1)
        self.assertGreater(
            capped["window_lower_created_at"],
            cursor["window_lower_created_at"],
        )
        cursor = capped
        first_page = list(range(120, 100, -1))
        cursor = module.advance_admission_scan_cursor(
            cursor, declared_total=27, observed_run_ids=first_page
        )
        self.assertEqual((cursor["target_index"], cursor["page"]), (0, 2))
        cursor = module.advance_admission_scan_cursor(
            cursor,
            declared_total=27,
            observed_run_ids=list(range(100, 93, -1)),
        )
        self.assertEqual((cursor["target_index"], cursor["page"]), (1, 1))
        self.assertEqual(
            cursor["last_completed_inventory"]["declared_total"], 27
        )
        cursor = module.advance_admission_scan_cursor(
            cursor,
            declared_total=0,
            observed_run_ids=[],
            next_upper_created_at="2026-09-01T09:00:00Z",
        )
        self.assertEqual(
            (cursor["target_index"], cursor["page"], cursor["generation"]),
            (0, 1, 1),
        )
        self.assertEqual(len(cursor["deferred_windows"]), 0)
        self.assertLess(
            cursor["window_upper_created_at"], "2026-09-01T08:00:00Z"
        )

        wrapping = module.bind_admission_scan_window(
            module.empty_admission_scan_cursor(),
            upper_created_at="2026-09-01T08:00:00Z",
            repository_created_at="2026-08-31T08:00:00Z",
        )
        wrapping = module.advance_admission_scan_cursor(
            wrapping, declared_total=0, observed_run_ids=[]
        )
        wrapping = module.advance_admission_scan_cursor(
            wrapping,
            declared_total=0,
            observed_run_ids=[],
            next_upper_created_at="2026-09-01T09:00:00Z",
        )
        self.assertEqual(wrapping["generation"], 2)
        self.assertEqual(
            wrapping["window_upper_created_at"], "2026-09-01T09:00:00Z"
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "page inventory"
        ):
            module.advance_admission_scan_cursor(
                cursor,
                declared_total=21,
                observed_run_ids=list(range(21)),
            )
        workflow = (
            ROOT / ".github/workflows/qikvrt_review_admission_recovery.yml"
        ).read_text(encoding="utf-8")
        ingest = workflow.split(
            "  plan-admission-source-ingest:\n", 1
        )[1].split(
            "  ingest-admission-source:\n", 1
        )[0]
        self.assertIn("scan['window_lower_created_at']+'..'", ingest)
        self.assertIn("declared_total >= scan['filtered_result_cap']", ingest)
        self.assertIn("shrink_admission_scan_window", ingest)
        self.assertIn("observed_run_ids=page_run_ids", ingest)
        self.assertIn("inventory_restart_count", ingest)
        self.assertIn("restart_admission_scan_inventory(scan)", ingest)
        self.assertNotIn("ADMISSION_INBOX_FILTER_CAP_AFTER_PAGE_ONE", ingest)
        self.assertNotIn("runs?per_page={scan['page_size']}&page=", ingest)

    def test_admission_scan_inventory_restarts_on_partial_shift_or_total_drift(self):
        def sealed():
            return module.bind_admission_scan_window(
                module.empty_admission_scan_cursor(),
                upper_created_at="2026-09-01T08:00:00Z",
                repository_created_at="2026-01-01T00:00:00Z",
            )

        first_ids = list(range(200, 180, -1))
        page_two_ids = list(range(180, 175, -1))
        collecting = module.advance_admission_scan_cursor(
            sealed(), declared_total=25, observed_run_ids=first_ids
        )
        self.assertEqual(collecting["target_run_ids"], first_ids)
        self.assertEqual(collecting["page"], 2)

        completed = module.advance_admission_scan_cursor(
            collecting, declared_total=25, observed_run_ids=page_two_ids
        )
        self.assertEqual(completed["target_index"], 1)
        self.assertEqual(completed["page"], 1)
        self.assertIsNone(completed["target_declared_total"])
        self.assertEqual(completed["target_run_ids"], [])
        self.assertEqual(
            completed["last_completed_inventory"]["ordered_run_ids_sha256"],
            module._canonical_sha256(first_ids + page_two_ids),
        )

        for label, total, ids in (
            ("partial", 25, page_two_ids[:3]),
            ("shifted", 25, [first_ids[-1], *page_two_ids[:-1]]),
            ("total-drift", 26, page_two_ids),
        ):
            with self.subTest(label=label):
                restarted = module.advance_admission_scan_cursor(
                    collecting,
                    declared_total=total,
                    observed_run_ids=ids,
                )
                self.assertEqual(restarted["target_index"], 0)
                self.assertEqual(restarted["page"], 1)
                self.assertIsNone(restarted["target_declared_total"])
                self.assertEqual(restarted["target_run_ids"], [])
                self.assertEqual(restarted["inventory_restart_count"], 1)

        # An incomplete first page is also a restart, never a short-page
        # completion or absence claim.
        partial_first = module.advance_admission_scan_cursor(
            sealed(), declared_total=25, observed_run_ids=first_ids[:19]
        )
        self.assertEqual(partial_first["page"], 1)
        self.assertEqual(partial_first["inventory_restart_count"], 1)
        self.assertIsNone(partial_first["last_completed_inventory"])

        out_of_order = module.advance_admission_scan_cursor(
            sealed(),
            declared_total=20,
            observed_run_ids=[*first_ids[:-2], first_ids[-1], first_ids[-2]],
        )
        self.assertEqual(out_of_order["page"], 1)
        self.assertEqual(out_of_order["inventory_restart_count"], 1)

        duplicate_page = module.advance_admission_scan_cursor(
            sealed(),
            declared_total=20,
            observed_run_ids=[*first_ids[:-1], first_ids[-2]],
        )
        self.assertEqual(duplicate_page["page"], 1)
        self.assertEqual(duplicate_page["inventory_restart_count"], 1)

        page_boundary_shift = module.advance_admission_scan_cursor(
            collecting,
            declared_total=25,
            observed_run_ids=[250, *page_two_ids[:-1]],
        )
        self.assertEqual(page_boundary_shift["page"], 1)
        self.assertEqual(page_boundary_shift["inventory_restart_count"], 1)

        cap_after_page_one = module.restart_admission_scan_inventory(collecting)
        self.assertEqual(cap_after_page_one["target_index"], 0)
        self.assertEqual(cap_after_page_one["page"], 1)
        self.assertIsNone(cap_after_page_one["target_declared_total"])
        self.assertEqual(cap_after_page_one["target_run_ids"], [])
        self.assertEqual(cap_after_page_one["inventory_restart_count"], 1)
        self.assertEqual(
            cap_after_page_one["window_upper_created_at"],
            collecting["window_upper_created_at"],
        )
        sharded_after_cap_restart = module.shrink_admission_scan_window(
            cap_after_page_one, declared_total=1000
        )
        self.assertEqual(sharded_after_cap_restart["page"], 1)
        self.assertEqual(sharded_after_cap_restart["target_index"], 0)
        self.assertGreater(
            sharded_after_cap_restart["window_lower_created_at"],
            cap_after_page_one["window_lower_created_at"],
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "no sealed prior page"
        ):
            module.restart_admission_scan_inventory(sealed())

    def test_admission_scan_v2_migration_rescans_without_absence(self):
        current = module.bind_admission_scan_window(
            module.empty_admission_scan_cursor(),
            upper_created_at="2026-09-01T08:00:00Z",
            repository_created_at="2026-01-01T00:00:00Z",
        )
        legacy = {
            key: copy.deepcopy(value)
            for key, value in current.items()
            if key
            not in {
                "target_declared_total",
                "target_run_ids",
                "target_run_ids_sha256",
                "inventory_restart_count",
                "last_completed_inventory",
            }
        }
        legacy["schema"] = "qikvrt_review_admission_scan_cursor_v2"
        legacy["page"] = 17
        migrated = module.migrate_admission_scan_cursor(legacy)
        self.assertEqual(
            migrated["schema"], "qikvrt_review_admission_scan_cursor_v3"
        )
        self.assertEqual(migrated["page"], 1)
        self.assertEqual(migrated["inventory_restart_count"], 1)
        self.assertEqual(
            migrated["window_upper_created_at"],
            legacy["window_upper_created_at"],
        )
        self.assertEqual(migrated["target_run_ids"], [])
        self.assertIsNone(migrated["target_declared_total"])
        self.assertEqual(
            module.migrate_admission_scan_cursor(migrated), migrated
        )

    def test_admission_same_second_cap_is_durable_quarantine_and_rotates(self):
        before = module.bind_admission_scan_window(
            module.empty_admission_scan_cursor(),
            upper_created_at="2026-09-01T08:00:01Z",
            repository_created_at="2026-09-01T08:00:00Z",
        )
        after = module.shrink_admission_scan_window(
            before, declared_total=1000
        )
        self.assertEqual(after["target_index"], 1)
        self.assertEqual(after["quarantined_window_count"], 1)
        self.assertEqual(
            after["quarantined_windows"][-1]["result"],
            "INCOMPLETE_NOT_ABSENCE",
        )
        self.assertEqual(
            after["quarantined_windows"][-1]["continuation_strategy"],
            "EXACT_SOURCE_RUN_ID_EVENT_OR_AUTHORITY_SUPPLIED_ID",
        )
        self.assertFalse(
            after["quarantined_windows"][-1]["absence_authorized"]
        )
        record = module.build_admission_scan_quarantine_record(before, after)
        self.assertIn(
            record["record_sha256"],
            module.admission_scan_quarantine_path(record),
        )
        module.validate_admission_scan_quarantine_record(record)
        self.assertEqual(record["authority_state"], "HOLD")

    def test_admission_inbox_continuation_is_technical_not_pass(self):
        source = module.build_admission_inbox_source(
            self.source_run(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            target_configs=self.config(),
        )
        slot = module.build_admission_inbox_slot(source, sequence=1)
        run = self.source_run(jobs_total=1, artifacts_total=0)
        receipt = module.build_admission_inbox_continuation(
            slot, run, jobs_total=1, artifacts_total=0
        )
        exact = module.validate_admission_inbox_continuation(receipt, slot)
        self.assertEqual(exact["d0"], 2)
        self.assertEqual(
            exact["effect_ack"],
            "TECHNICAL_CONTINUATION_PENDING_REOBSERVATION",
        )
        self.assertFalse(exact["completion_claims"]["PASS"])
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "not materialized"
        ):
            module.build_admission_inbox_continuation(
                slot, self.source_run(), jobs_total=0, artifacts_total=0
            )

    def test_human_review_fact_excludes_body_and_bots_not_quoted_marker(self):
        human = self.human_review(body="first wording")
        bot = self.human_review(
            review_id=7002,
            login="github-actions[bot]",
            user_id=4402,
            user_type="Bot",
        )
        marker_quoting_human = self.human_review(
            review_id=7003,
            login="human-but-technical",
            user_id=4403,
            body="qikvrt-mesh-review:v1 technical disposition",
        )
        first = self.human_observation([human, bot, marker_quoting_human])
        second_human = self.human_review(body="edited wording is not sealed")
        second = self.human_observation([
            second_human, bot, marker_quoting_human
        ])
        self.assertEqual(len(first["facts"]), 2)
        self.assertEqual(first["facts"], second["facts"])
        fact = first["facts"][0]
        self.assertNotIn("body", fact)
        self.assertNotIn("first wording", repr(fact))
        self.assertEqual(
            first["subjects"][0]["excluded_review_ids"], [7002]
        )

    def test_wakeup_intent_binds_observed_head_ref_and_repository(self):
        fact = self.human_observation([self.human_review()])["facts"][0]
        self.assertEqual(fact["head_ref"], "release/pr935")
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "head ref differs"
        ):
            module.build_review_wakeup_intent(
                fact, head_ref="unobserved/ref",
                recovery_repository=REPOSITORY,
                recovery_repository_id=REPOSITORY_ID,
                recovery_workflow_id=8200,
                recovery_workflow_path=(
                    ".github/workflows/qikvrt_review_admission_recovery.yml"
                ),
                recovery_head_sha=MAIN,
                requested_workflow_id=8100,
                requested_workflow_path=PATH,
                requested_workflow_sha=MAIN,
            )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "repository differs"
        ):
            module.build_review_wakeup_intent(
                fact, head_ref=fact["head_ref"],
                recovery_repository="Other/repository",
                recovery_repository_id=REPOSITORY_ID,
                recovery_workflow_id=8200,
                recovery_workflow_path=(
                    ".github/workflows/qikvrt_review_admission_recovery.yml"
                ),
                recovery_head_sha=MAIN,
                requested_workflow_id=8100,
                requested_workflow_path=PATH,
                requested_workflow_sha=MAIN,
            )

    def test_review_observation_frontier_is_bounded_sharded_and_body_free(self):
        fact = self.human_observation([self.human_review(body="not sealed")])[
            "facts"
        ][0]
        scan = module.empty_review_observation_scan()
        self.assertEqual(
            module.validate_review_observation_scan(scan)["pull_page_size"], 1
        )
        meta = module.empty_review_observation_queue_meta()
        self.assertEqual(
            module.validate_review_observation_queue_meta(meta)[
                "drain_sequence"
            ],
            1,
        )
        slot = module.build_review_observation_slot(
            fact, sequence=1001, generation=7
        )
        exact = module.validate_review_observation_slot(slot)
        self.assertEqual(exact["fact"], fact)
        self.assertNotIn("body", repr(exact))
        self.assertTrue(
            module.review_observation_slot_path(1001).endswith(
                "/00000000000000001001.json"
            )
        )
        self.assertIn(
            fact["fact_fingerprint"],
            module.review_observation_locator_path(
                fact["fact_fingerprint"]
            ),
        )
        resume = module.build_review_observation_subject_cursor(
            self.pull_request(),
            self.pr_commits(),
            repository=REPOSITORY,
            current_main_sha=MAIN,
            current_main_tree_sha="e" * 40,
            next_review_page=2,
            generation=7,
            last_ack_review_id=fact["review_id"],
            last_ack_fact_fingerprint=fact["fact_fingerprint"],
        )
        self.assertEqual(
            module.validate_review_observation_subject_cursor(resume)[
                "next_review_page"
            ],
            2,
        )
        self.assertEqual(resume["quantum_pages"], 1)
        self.assertEqual(resume["ack_recheck_quantum"], 1)
        self.assertEqual(
            resume["last_ack_cursor"]["review_id"], fact["review_id"]
        )
        self.assertIn(
            "pr-935.json", module.review_observation_subject_cursor_path(935)
        )

    def test_exact_head_singleton_does_not_claim_commit_history_completeness(self):
        for declared in (2,101,251):
            pull=self.pull_request()
            pull["commits"]=declared
            observation=module.observe_human_review_facts(
                [pull],reviews_by_pr={935:[self.human_review()]},
                commits_by_pr={935:self.pr_commits()},
                repository=REPOSITORY,current_main_sha=MAIN,
                current_main_tree_sha="e"*40,
                commit_observation_mode="EXACT_HEAD_SINGLETON",
            )
            self.assertEqual(
                observation["subjects"][0]["commit_observation_mode"],
                "EXACT_HEAD_SINGLETON",
            )
            self.assertEqual(
                observation["subjects"][0]["head_tree_sha"],"d"*40
            )
            resume=module.build_review_observation_subject_cursor(
                pull,self.pr_commits(),repository=REPOSITORY,
                current_main_sha=MAIN,current_main_tree_sha="e"*40,
                next_review_page=2,generation=1,
                commit_observation_mode="EXACT_HEAD_SINGLETON",
            )
            self.assertEqual(resume["pull"]["commits"],declared)
            module.validate_review_observation_subject_cursor(resume)
        pull=self.pull_request()
        pull["commits"]=2
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"pagination is incomplete"
        ):
            module.observe_human_review_facts(
                [pull],reviews_by_pr={935:[self.human_review()]},
                commits_by_pr={935:self.pr_commits()},
                repository=REPOSITORY,current_main_sha=MAIN,
                current_main_tree_sha="e"*40,
            )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"extra commits"
        ):
            module.observe_human_review_facts(
                [pull],reviews_by_pr={935:[self.human_review()]},
                commits_by_pr={935:[*self.pr_commits("a"*40),*self.pr_commits()]},
                repository=REPOSITORY,current_main_sha=MAIN,
                current_main_tree_sha="e"*40,
                commit_observation_mode="EXACT_HEAD_SINGLETON",
            )

    def test_current_dismissal_and_prior_ack_absence_are_distinct_facts(self):
        submitted = self.human_observation([
            self.human_review(state="APPROVED")
        ])["facts"][0]
        dismissed = self.human_observation([
            self.human_review(state="DISMISSED")
        ])["facts"][0]
        self.assertEqual(dismissed["review_state"], "DISMISSED")
        self.assertNotEqual(
            submitted["fact_fingerprint"], dismissed["fact_fingerprint"]
        )

        absent_observation = self.human_observation([])
        absent = module.build_review_absence_facts(
            absent_observation, [submitted]
        )
        self.assertEqual(len(absent), 1)
        self.assertEqual(absent[0]["transition_kind"], "REVIEW_ABSENT")
        self.assertEqual(absent[0]["review_state"], "ABSENT")
        self.assertEqual(absent[0]["prior_review_state"], "APPROVED")

    def test_review_removal_and_dismissal_require_exact_review_id_get(self):
        approved_review = self.human_review(state="APPROVED")
        approved = self.human_observation([approved_review])["facts"][0]
        paginated_without_review = self.human_observation([])
        absent = module.build_review_absence_facts(
            paginated_without_review, [approved]
        )[0]
        absent_intent = self.wakeup_intent(absent)
        absent_core_payload = self.wakeup_core_payload(absent_intent)

        # A page-shift can omit an existing review.  The exact ID read wins and
        # prevents the moving paginated list from manufacturing a removal.
        found = module.build_direct_review_observation(
            review_id=approved["review_id"], review=approved_review
        )
        self.assertNotIn("body", repr(found))
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "still exists"
        ):
            module.validate_review_wakeup_preeffect(
                absent_intent,
                paginated_without_review,
                transport_attempt=1,
                core_payload=absent_core_payload,
                direct_review_observation=found,
            )

        not_found = module.build_direct_review_observation(
            review_id=approved["review_id"], review=None
        )
        absence_plan = module.validate_review_wakeup_preeffect(
            absent_intent,
            paginated_without_review,
            transport_attempt=1,
            core_payload=absent_core_payload,
            direct_review_observation=not_found,
        )
        self.assertEqual(
            absence_plan["direct_review_observation_sha256"],
            not_found["observation_sha256"],
        )

        dismissed_review = self.human_review(state="DISMISSED")
        dismissed = self.human_observation([dismissed_review])["facts"][0]
        dismissed_intent = self.wakeup_intent(dismissed)
        dismissed_core_payload = self.wakeup_core_payload(dismissed_intent)
        dismissed_direct = module.build_direct_review_observation(
            review_id=dismissed["review_id"], review=dismissed_review
        )
        # Even if pagination shifts, the exact ID GET is sufficient for the
        # current dismissed-state fact and seals no body bytes.
        dismissal_plan = module.validate_review_wakeup_preeffect(
            dismissed_intent,
            paginated_without_review,
            transport_attempt=1,
            core_payload=dismissed_core_payload,
            direct_review_observation=dismissed_direct,
        )
        self.assertEqual(
            dismissal_plan["direct_review_observation_sha256"],
            dismissed_direct["observation_sha256"],
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "required"
        ):
            module.validate_review_wakeup_preeffect(
                dismissed_intent,
                paginated_without_review,
                transport_attempt=1,
                core_payload=dismissed_core_payload,
            )

    def test_oldest_unseen_fairness_has_no_scalar_cursor(self):
        newer_pr = self.pull_request(number=936, head_sha="c" * 40)
        observation = module.observe_human_review_facts(
            [self.pull_request(), newer_pr],
            reviews_by_pr={
                935: [self.human_review(
                    review_id=7001,
                    submitted_at="2026-09-01T08:20:00Z",
                )],
                936: [self.human_review(
                    review_id=7002,
                    submitted_at="2026-09-01T08:21:00Z",
                    commit_id="c" * 40,
                )],
            },
            commits_by_pr={
                935: self.pr_commits(),
                936: self.pr_commits("c" * 40, "f" * 40),
            },
            repository=REPOSITORY,
            current_main_sha=MAIN,
            current_main_tree_sha="e" * 40,
        )
        first, second = observation["facts"]
        selected = module.select_review_wakeup_transition(
            list(reversed(observation["facts"])),
            acknowledged_fingerprints=set(),
            terminal_fingerprints=set(),
            reusable_intents={},
        )
        self.assertEqual(selected["fact"], first)
        advanced = module.select_review_wakeup_transition(
            observation["facts"],
            acknowledged_fingerprints={first["fact_fingerprint"]},
            terminal_fingerprints=set(),
            reusable_intents={},
        )
        self.assertEqual(advanced["fact"], second)
        self.assertNotIn("cursor", repr(selected).lower())

    def test_orphan_intent_is_terminal_after_one_consumed_transport(self):
        fact = self.human_observation([self.human_review()])["facts"][0]
        intent = self.wakeup_intent(fact)
        first = module.build_review_wakeup_producer_binding(
            intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        self.assertEqual(
            first["orphan_lookup_created_from"], "2026-09-01T08:29:59Z"
        )
        reusable = {
            fact["fact_fingerprint"]: {
                "intent": intent,
                "transport_attempts": {first["transport_attempt"]},
            }
        }
        exhausted = module.select_review_wakeup_transition(
            [fact],
            acknowledged_fingerprints=set(),
            terminal_fingerprints=set(),
            reusable_intents=reusable,
        )
        self.assertEqual(exhausted["state"], "CORE_TRANSPORT_PENDING")
        self.assertEqual(exhausted["intent"], intent)
        self.assertEqual(exhausted["transport_attempt"], 1)
        self.assertEqual(
            exhausted["first_blocker"],
            "SHARED_CORE_EXACT_REVIEW_NOT_YET_ACCEPTED",
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "exceeds bound"
        ):
            module.build_review_wakeup_producer_binding(
                intent,
                recovery_run_id=9002,
                recovery_run_attempt=1,
                recovery_run_started_at="2026-09-01T09:30:00Z",
                transport_attempt=2,
            )

    def test_preeffect_and_ack_bind_exact_stable_requested_child(self):
        observation = self.human_observation([self.human_review()])
        fact = observation["facts"][0]
        intent = self.wakeup_intent(fact)
        core_payload = self.wakeup_core_payload(intent)
        for mutate in (
            lambda value: value.update(schema="evil"),
            lambda value: value.update(unsealed_claim="PASS"),
            lambda value: value["producer"].update(unsealed_claim="PASS"),
            lambda value: value["target"].update(unsealed_claim="PASS"),
            lambda value: value["causal"].update(unsealed_claim="PASS"),
        ):
            malformed = copy.deepcopy(core_payload)
            mutate(malformed)
            with self.assertRaisesRegex(
                module.AdmissionRecoveryError, "not canonical"
            ):
                module.validate_review_wakeup_core_payload(malformed, intent)
        plan = module.validate_review_wakeup_preeffect(
            intent, observation, transport_attempt=1,
            core_payload=core_payload,
        )
        self.assertTrue(plan["dispatch_request"]["return_run_details"])
        self.assertEqual(
            plan["dispatch_request"]["inputs"]["evaluator_sha"], MAIN
        )
        self.assertEqual(
            plan["dispatch_request"]["inputs"]["transport_intent_sha256"],
            module.review_wakeup_core_fingerprint(intent, core_payload),
        )
        self.assertEqual(
            plan["dispatch_request"]["inputs"]["transport_attempt"], "1"
        )
        expected_title = (
            f"qikvrt-rr-v3 e={MAIN} p=935 h={'b' * 40} "
            f"f={fact['fact_fingerprint']} "
            f"i={module.review_wakeup_core_fingerprint(intent, core_payload)} a=1"
        )
        self.assertEqual(plan["expected_child_title"], expected_title)
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "exceeds bound"
        ):
            module.review_wakeup_child_title(
                intent, transport_attempt=2, core_payload=core_payload,
            )
        binding = module.build_review_wakeup_producer_binding(
            intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        lookup = self.accepted_wakeup_core(intent, core_payload)
        contradictory_lookup = copy.deepcopy(lookup)
        contradictory_lookup["lookup_state"] = "TERMINAL"
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "locator differs"
        ):
            module.build_review_wakeup_ack(
                intent, binding, core_payload, contradictory_lookup,
                current_main_sha=MAIN,
            )
        for field in ("transport", "acceptance"):
            with self.subTest(hostile_core_map=field):
                extra_core_record = copy.deepcopy(lookup)
                extra_core_record[field]["PASS"] = True
                with self.assertRaisesRegex(
                    module.AdmissionRecoveryError, "locator differs"
                ):
                    module.build_review_wakeup_ack(
                        intent,
                        binding,
                        core_payload,
                        extra_core_record,
                        current_main_sha=MAIN,
                    )
        ack = module.build_review_wakeup_ack(
            intent, binding, core_payload, lookup, current_main_sha=MAIN
        )
        self.assertEqual(ack["fact"], fact)
        self.assertTrue(ack["child_proof"]["transport_ack_observed"])
        self.assertEqual(
            ack["child_proof"]["core_authority"]["state"],
            "CORE_ATTEMPT_1_ACCEPTED_LOCATOR",
        )
        foreign_locator = copy.deepcopy(
            ack["child_proof"]["core_authority"]
        )
        foreign_locator["fingerprint"] = "f" * 64
        foreign_locator["intent_path"] = (
            "intents/exact-review-dispatch/00000000000000000001-"
            + "f" * 64 + ".json"
        )
        foreign_locator.pop("authority_sha256")
        foreign_locator["authority_sha256"] = module._canonical_sha256(
            foreign_locator
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "authority differs"
        ):
            module.validate_review_wakeup_core_acceptance_proof(
                foreign_locator, intent
            )
        extra_child_claim = copy.deepcopy(
            ack["child_proof"]["core_authority"]
        )
        extra_child_claim["child"]["unsealed_claim"] = "PASS"
        from tools.qikvrt_ruleset_outbox import digest as core_digest
        extra_child_claim["accepted_child_sha256"] = core_digest(
            extra_child_claim["child"]
        )
        extra_child_claim.pop("authority_sha256")
        extra_child_claim["authority_sha256"] = module._canonical_sha256(
            extra_child_claim
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "authority differs"
        ):
            module.validate_review_wakeup_core_acceptance_proof(
                extra_child_claim, intent
            )
        drifted = copy.deepcopy(lookup)
        drifted["fingerprint"] = "0" * 64
        with self.assertRaisesRegex(module.AdmissionRecoveryError, "locator"):
            module.build_review_wakeup_ack(
                intent, binding, core_payload, drifted, current_main_sha=MAIN
            )
        drifted = copy.deepcopy(lookup)
        drifted["acceptance"]["1"]["child"]["run_id"] += 1
        from tools.qikvrt_ruleset_outbox import OutboxBlock
        with self.assertRaises((module.AdmissionRecoveryError, OutboxBlock)):
            module.build_review_wakeup_ack(
                intent, binding, core_payload, drifted, current_main_sha=MAIN,
            )

    def test_shared_core_same_run_attempt_two_has_one_exact_authority_chain(self):
        from tests.test_qikvrt_ruleset_outbox import MemoryBackend
        from tools import qikvrt_ruleset_outbox as core

        backend = MemoryBackend()
        raw_payload = {
            "schema": core.PAYLOAD_SCHEMA,
            "repository": REPOSITORY,
            "lane": "exact-review-dispatch",
            "main_head_sha": MAIN,
            "producer": {
                "workflow_path": (
                    ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"
                ),
                "workflow_sha": MAIN,
                "workflow_id": 7000,
                "run_id": 7001,
                "run_attempt": 1,
                "event": "repository_dispatch",
            },
            "subject": {
                "pull_request": 935,
                "head_repository": REPOSITORY,
                "head_ref": "release/pr935",
                "head_sha": "b" * 40,
                "head_tree_sha": "d" * 40,
                "base_ref": "main",
                "base_sha": MAIN,
            },
            "target": {
                "workflow_id": 8100,
                "workflow_path": PATH,
                "event": "workflow_dispatch",
            },
            "request": {
                "ref": "main",
                "return_run_details": True,
                "inputs": {
                    "pr": "935",
                    "head": "b" * 40,
                    "fingerprint": "c" * 64,
                    "evaluator_sha": MAIN,
                    "transport_intent_sha256": "0" * 64,
                    "transport_attempt": "1",
                },
            },
            "causal": {
                "d0": 2, "state": "REOBSERVE", "productive_effect": False,
            },
        }
        payload = core.seal_review_transport_payload(raw_payload)
        intent_artifact = {
            "id": 8001,
            "name": "exact-review-intent",
            "archive_sha256": "e" * 64,
            "payload_sha256": core.sha256_bytes(
                core.canonical_bytes(core.validate_payload(payload))
            ),
            "producer_run_id": 7001,
            "producer_run_attempt": 1,
            "producer_workflow_id": 7000,
        }
        core_intent = core.append_intent(
            backend, payload=payload, artifact=intent_artifact
        )
        core.prepare_transport(
            backend,
            lane="exact-review-dispatch",
            sequence=core_intent["sequence"],
            attempt=1,
            request=core.request_for_transport_attempt(core_intent, 1),
            actor_run_id=7002,
            actor_run_attempt=1,
        )
        title = (
            f"qikvrt-rr-v3 e={MAIN} p=935 h={'b' * 40} "
            f"f={'c' * 64} i={core_intent['fingerprint']} a=1"
        )
        core_child_one = {
            "run_id": 9911,
            "run_attempt": 1,
            "workflow_id": 8100,
            "workflow_path": PATH,
            "event": "workflow_dispatch",
            "repository": REPOSITORY,
            "head_sha": MAIN,
            "status": "queued",
            "conclusion": None,
            "display_title": title,
        }
        core.record_acceptance(
            backend, lane="exact-review-dispatch",
            sequence=core_intent["sequence"], attempt=1,
            child=core_child_one,
        )
        core_lookup = core.lookup_fingerprint(
            backend, lane="exact-review-dispatch",
            fingerprint=core_intent["fingerprint"],
        )
        source_run = {
            "id": 9911,
            "run_attempt": 1,
            "workflow_id": 8100,
            "path": PATH,
            "repository": {"id": REPOSITORY_ID, "full_name": REPOSITORY},
            "event": "workflow_dispatch",
            "head_branch": "main",
            "head_sha": MAIN,
            "display_title": title,
            "status": "completed",
            "conclusion": "cancelled",
            "created_at": "2026-09-01T08:31:00Z",
            "pull_requests": [],
            "jobs_total": 0,
            "artifacts_total": 0,
        }
        source = module.build_admission_inbox_source(
            source_run,
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            target_configs=self.config(),
            exact_review_core_lookup=core_lookup,
        )
        self.assertEqual(
            source["source_kind"], "CORE_EXACT_REVIEW_CHILD_ZERO_JOB"
        )
        self.assertEqual(
            source["origin_authority"]["acceptance"]["child"]["status"],
            "queued",
        )
        self.assertEqual(
            source["origin_authority"]["source"]["conclusion"],
            "cancelled",
        )
        completed_acceptance_lookup = copy.deepcopy(core_lookup)
        completed_child = completed_acceptance_lookup["acceptance"]["1"]["child"]
        completed_child["status"] = "completed"
        completed_child["conclusion"] = "cancelled"
        completed_acceptance_lookup["acceptance"]["1"]["child_sha256"] = (
            core.digest(completed_child)
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "accepted shared review Core child"
        ):
            module.build_admission_inbox_source(
                source_run,
                repository=REPOSITORY,
                repository_id=REPOSITORY_ID,
                current_main_sha=MAIN,
                target_configs=self.config(),
                exact_review_core_lookup=completed_acceptance_lookup,
            )
        action_run = copy.deepcopy(source_run)
        action_run["conclusion"] = "action_required"
        action_source = module.build_admission_inbox_source(
            action_run,
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            target_configs=self.config(),
            exact_review_core_lookup=core_lookup,
        )
        self.assertFalse(
            action_source["origin_authority"]["same_run_recovery_required"]
        )
        self.assertTrue(
            action_source["origin_authority"]["terminal_hold_required"]
        )
        action_selection = module.select_recovery(
            [action_run],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
            bound_requested_run_ids={action_run["id"]},
        )
        self.assertEqual(action_selection["state"], "ACTION_REQUIRED_D0_3")
        action_terminal = module.build_terminal_receipt(action_selection)
        self.assertEqual(
            action_terminal["first_blocker"],
            "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "does not authorize"
        ):
            module.build_shared_review_core_retry_evidence(
                action_source["origin_authority"],
                source=action_source["source"],
            )
        slot = module.build_admission_inbox_slot(source, sequence=7)
        selection = module.select_recovery(
            [source_run],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
            bound_requested_run_ids={9911},
        )
        self.assertEqual(selection["state"], "RERUN_ATTEMPT_2")
        selection["origin_authority"] = source["origin_authority"]
        selection["source_kind"] = source["source_kind"]
        selection["live_subject"] = {
            "pr_number": 935,
            "head_sha": "b" * 40,
            "head_tree_sha": "d" * 40,
            "head_repository": REPOSITORY,
            "head_ref": "release/pr935",
            "base_sha": MAIN,
            "base_tree_sha": "e" * 40,
            "base_repository": REPOSITORY,
            "base_ref": "main",
        }
        intent = module.build_recovery_intent(
            selection,
            recovery_repository=REPOSITORY,
            recovery_workflow_id=8200,
            recovery_workflow_path=(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            recovery_head_sha=MAIN,
        )
        rerun_record = {
            "schema": "qikvrt_review_admission_inbox_child_rerun_v1",
            "sequence": 7,
            "source_fingerprint": slot["source_fingerprint"],
            "source_sha256": slot["source_sha256"],
            "intent": intent,
            "producer_binding": module.build_recovery_producer_binding(
                intent, recovery_run_id=8800, recovery_run_attempt=1
            ),
            "state": "PRE_EFFECT_REOBSERVED",
            "authority_boundary": "RECOVERY_ONLY",
            "productive_effect": False,
        }
        attempt_two = {
            **source_run,
            "run_attempt": 2,
            "status": "queued",
            "conclusion": None,
        }
        readback = module.verify_rerun_readback(intent, attempt_two)
        acceptance = module.build_admission_rerun_acceptance(
            slot=slot, rerun_record=rerun_record,
            child_run=attempt_two, readback=readback,
        )
        self.assertEqual(
            module.build_admission_rerun_acceptance(
                slot=slot,rerun_record=rerun_record,
                child_run={
                    **attempt_two,"status":"completed","conclusion":"failure",
                },readback=readback,
            ),acceptance,
        )
        retry = module.build_exact_review_core_retry_evidence(
            source["origin_authority"], source=source["source"]
        )
        core_preparation = core.prepare_child_rerun(
            backend,
            lane="exact-review-dispatch",
            sequence=core_intent["sequence"],
            transport_attempt=1,
            retry_evidence=retry,
            actor_run_id=8800,
            actor_run_attempt=1,
        )
        forged_preparation=copy.deepcopy(core_preparation)
        forged_preparation["cas"]={}
        forged_preparation["ledger_head"]="f"*40
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"CAS receipt differs"
        ):
            module.validate_shared_review_core_rerun_preparation(
                forged_preparation,origin=source["origin_authority"]
            )
        prepared_recovery=module.reobserve_shared_review_core_child_recovery(
            core.lookup_fingerprint(
                backend,lane="exact-review-dispatch",
                fingerprint=core_intent["fingerprint"],
            ),origin=source["origin_authority"],
        )
        owner_effect=module.plan_recovery_effect(
            intent,source_run=source_run,source_jobs_total=0,
            source_artifacts_total=0,current_main_sha=MAIN,
            live_subject=selection["live_subject"],
            current_shared_review_core_preparation=prepared_recovery["preparation"],
            current_recovery_producer_binding=rerun_record["producer_binding"],
            current_recovery_run_id=8800,current_recovery_run_attempt=1,
        )
        self.assertEqual(
            owner_effect["effect"],"RERUN_SAME_SOURCE_RUN_ATTEMPT_2"
        )
        self.assertTrue(owner_effect["new_rerun_post_authorized"])
        replay_effect=module.plan_recovery_effect(
            intent,source_run=source_run,source_jobs_total=0,
            source_artifacts_total=0,current_main_sha=MAIN,
            live_subject=selection["live_subject"],
            current_shared_review_core_preparation=prepared_recovery["preparation"],
            current_recovery_producer_binding=rerun_record["producer_binding"],
            current_recovery_run_id=8801,current_recovery_run_attempt=1,
        )
        self.assertEqual(
            replay_effect["effect"],
            "POLL_ONLY_CONSUMED_SAME_RUN_ATTEMPT_2",
        )
        self.assertFalse(replay_effect["new_rerun_post_authorized"])
        core_child_two = {
            **core_child_one,
            "run_attempt": 2,
            "status": "queued",
            "conclusion": None,
        }
        core_acceptance = core.record_child_rerun_acceptance(
            backend,
            lane="exact-review-dispatch",
            sequence=core_intent["sequence"],
            transport_attempt=1,
            child=core_child_two,
        )
        forged_core_acceptance=copy.deepcopy(core_acceptance)
        forged_core_acceptance["cas"]={}
        forged_core_acceptance["ledger_head"]="f"*40
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"CAS receipt differs"
        ):
            module.validate_shared_review_core_rerun_acceptance(
                forged_core_acceptance,origin=source["origin_authority"],
                child_run=attempt_two,
            )
        current_lookup = core.lookup_fingerprint(
            backend, lane="exact-review-dispatch",
            fingerprint=core_intent["fingerprint"],
        )
        recovered = module.reobserve_shared_review_core_child_recovery(
            current_lookup, origin=source["origin_authority"]
        )
        self.assertEqual(recovered["state"], "ACCEPTED")
        self.assertIn("durable_readback", recovered["preparation"])
        self.assertIn("durable_readback", recovered["acceptance"])
        completed_attempt_two={
            **attempt_two,"status":"completed","conclusion":"failure",
        }
        self.assertEqual(
            module.validate_shared_review_core_rerun_acceptance(
                recovered["acceptance"],origin=source["origin_authority"],
                child_run=completed_attempt_two,
            ),recovered["acceptance"],
        )
        drifted_attempt_two={**completed_attempt_two,"id":9912}
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"acceptance differs"
        ):
            module.validate_shared_review_core_rerun_acceptance(
                recovered["acceptance"],origin=source["origin_authority"],
                child_run=drifted_attempt_two,
            )
        adoption = module.plan_shared_review_core_attempt_two_adoption(
            intent, child_run=attempt_two, current_main_sha=MAIN,
            live_subject=selection["live_subject"],
            core_preparation=recovered["preparation"],
            core_acceptance=recovered["acceptance"],
        )
        self.assertEqual(
            adoption["effect"], "ADOPT_EXISTING_SAME_RUN_ATTEMPT_2"
        )
        self.assertFalse(adoption["new_rerun_post_authorized"])
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "durable Shared-Core readback"
        ):
            module.build_admission_attempt_authority_chain(
                slot=slot, rerun_record=rerun_record, acceptance=acceptance,
                core_preparation=core_preparation,
                core_acceptance=core_acceptance,
            )
        chain = module.build_admission_attempt_authority_chain(
            slot=slot, rerun_record=rerun_record, acceptance=acceptance,
            core_preparation=recovered["preparation"],
            core_acceptance=recovered["acceptance"],
        )
        self.assertEqual(chain["source_run_id"], 9911)
        self.assertEqual(chain["origin_run_attempt"], 1)
        self.assertEqual(chain["authorized_run_attempt"], 2)
        self.assertEqual(chain["core_authority"]["sequence"], core_intent["sequence"])
        self.assertTrue(chain["core_authority"]["same_run_recovery"])
        self.assertEqual(
            module.validate_admission_attempt_authority_chain(chain), chain
        )
        unrelated = copy.deepcopy(chain)
        unrelated["acceptance"]["child"]["id"] = 9912
        with self.assertRaises(module.AdmissionRecoveryError):
            module.validate_admission_attempt_authority_chain(unrelated)

    def test_mesh_shared_core_zero_job_uses_same_run_recovery_authority(self):
        from tests.test_qikvrt_ruleset_outbox import MemoryBackend, artifact, payload
        from tools import qikvrt_ruleset_outbox as core

        backend = MemoryBackend()
        sealed = payload("mesh-review-successor-dispatch", run_id=7031)
        intent_record = core.append_intent(
            backend, payload=sealed, artifact=artifact(sealed)
        )
        core.prepare_transport(
            backend, lane="mesh-review-successor-dispatch",
            sequence=intent_record["sequence"], attempt=1,
            request=core.request_for_transport_attempt(intent_record, 1),
            actor_run_id=7032, actor_run_attempt=1,
        )
        inputs=intent_record["payload"]["request"]["inputs"]
        title=(
            f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
            f"h={inputs['head']} f={inputs['fingerprint']} "
            f"i={intent_record['fingerprint']} a=1"
        )
        child={
            "run_id": 9921, "run_attempt": 1, "workflow_id": 77,
            "workflow_path": PATH, "event": "workflow_dispatch",
            "repository": REPOSITORY, "head_sha": inputs["evaluator_sha"],
            "status": "queued", "conclusion": None,
            "display_title": title,
        }
        core.record_acceptance(
            backend, lane="mesh-review-successor-dispatch",
            sequence=intent_record["sequence"], attempt=1, child=child,
        )
        lookup=core.lookup_fingerprint(
            backend, lane="mesh-review-successor-dispatch",
            fingerprint=intent_record["fingerprint"],
        )
        run={
            "id":9921,"run_attempt":1,"workflow_id":77,"path":PATH,
            "repository":{"id":REPOSITORY_ID,"full_name":REPOSITORY},
            "event":"workflow_dispatch","head_branch":"main",
            "head_sha":inputs["evaluator_sha"],"display_title":title,
            "status":"completed","conclusion":"cancelled",
            "created_at":"2026-09-01T08:32:00Z","pull_requests":[],
        }
        source=module.build_admission_inbox_source(
            run,repository=REPOSITORY,repository_id=REPOSITORY_ID,
            current_main_sha=inputs["evaluator_sha"],
            target_configs={77:{
                "path":PATH,"activation_locator":LOCATOR,
                "allowed_events":["workflow_dispatch"],
            }},mesh_review_core_lookup=lookup,
        )
        self.assertEqual(source["source_kind"],"CORE_MESH_REVIEW_CHILD_ZERO_JOB")
        self.assertEqual(
            source["origin_authority"]["lane"],
            "mesh-review-successor-dispatch",
        )
        retry=module.build_shared_review_core_retry_evidence(
            source["origin_authority"],source=source["source"]
        )
        prepared=core.prepare_child_rerun(
            backend,lane="mesh-review-successor-dispatch",
            sequence=intent_record["sequence"],transport_attempt=1,
            retry_evidence=retry,actor_run_id=8900,actor_run_attempt=1,
        )
        self.assertEqual(
            module.validate_shared_review_core_rerun_preparation(
                prepared,origin=source["origin_authority"]
            ),prepared,
        )
        slot=module.build_admission_inbox_slot(source,sequence=8)
        selection=module.select_recovery(
            [{**run,"jobs_total":0,"artifacts_total":0}],target_configs={77:{
                "path":PATH,"activation_locator":LOCATOR,
                "allowed_events":["workflow_dispatch"],
            }},repository=REPOSITORY,repository_id=REPOSITORY_ID,
            current_main_sha=inputs["evaluator_sha"],current_run_id=999,
            bound_requested_run_ids={9921},
        )
        selection["source_kind"]=source["source_kind"]
        selection["origin_authority"]=source["origin_authority"]
        selection["live_subject"]={
            "pr_number":int(inputs["pr"]),"head_sha":inputs["head"],
            "head_tree_sha":"d"*40,"head_repository":REPOSITORY,
            "head_ref":"release/mesh","base_sha":inputs["evaluator_sha"],
            "base_tree_sha":"e"*40,"base_repository":REPOSITORY,
            "base_ref":"main",
        }
        intent=module.build_recovery_intent(
            selection,recovery_repository=REPOSITORY,
            recovery_workflow_id=8200,
            recovery_workflow_path=(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),recovery_head_sha=inputs["evaluator_sha"],
        )
        rerun_record={
            "schema":"qikvrt_review_admission_inbox_child_rerun_v1",
            "sequence":8,"source_fingerprint":slot["source_fingerprint"],
            "source_sha256":slot["source_sha256"],"intent":intent,
            "producer_binding":module.build_recovery_producer_binding(
                intent,recovery_run_id=8900,recovery_run_attempt=1
            ),"state":"PRE_EFFECT_REOBSERVED",
            "authority_boundary":"RECOVERY_ONLY","productive_effect":False,
        }
        attempt_two={
            **run,"run_attempt":2,"status":"queued","conclusion":None,
        }
        local_readback=module.verify_rerun_readback(intent,attempt_two)
        local_acceptance=module.build_admission_rerun_acceptance(
            slot=slot,rerun_record=rerun_record,child_run=attempt_two,
            readback=local_readback,
        )
        recovered_child={
            **child,"run_attempt":2,"status":"queued","conclusion":None,
        }
        core.record_child_rerun_acceptance(
            backend,lane="mesh-review-successor-dispatch",
            sequence=intent_record["sequence"],transport_attempt=1,
            child=recovered_child,
        )
        durable=module.reobserve_shared_review_core_child_recovery(
            core.lookup_fingerprint(
                backend,lane="mesh-review-successor-dispatch",
                fingerprint=intent_record["fingerprint"],
            ),origin=source["origin_authority"],
        )
        chain=module.build_admission_attempt_authority_chain(
            slot=slot,rerun_record=rerun_record,acceptance=local_acceptance,
            core_preparation=durable["preparation"],
            core_acceptance=durable["acceptance"],
        )
        self.assertEqual(chain["pr_number"],int(inputs["pr"]))
        self.assertEqual(chain["head_sha"],inputs["head"])
        self.assertEqual(chain["head_tree_sha"],"d"*40)
        self.assertEqual(
            module.validate_admission_attempt_authority_chain(chain),chain
        )

    def test_shared_core_no_attempt_two_is_temporal_and_terminal_fixed_point(self):
        from tests.test_qikvrt_ruleset_outbox import MemoryBackend, artifact, payload
        from tools import qikvrt_ruleset_outbox as core

        backend=MemoryBackend()
        sealed=payload("exact-review-dispatch",run_id=7051)
        intent=core.append_intent(
            backend,payload=sealed,artifact=artifact(sealed)
        )
        core.prepare_transport(
            backend,lane=intent["lane"],sequence=intent["sequence"],
            attempt=1,request=core.request_for_transport_attempt(intent,1),
            actor_run_id=7052,actor_run_attempt=1,
        )
        inputs=intent["payload"]["request"]["inputs"]
        title=(
            f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
            f"h={inputs['head']} f={inputs['fingerprint']} "
            f"i={intent['fingerprint']} a=1"
        )
        accepted={
            "run_id":9941,"run_attempt":1,"workflow_id":77,
            "workflow_path":PATH,"event":"workflow_dispatch",
            "repository":REPOSITORY,"head_sha":inputs["evaluator_sha"],
            "status":"queued","conclusion":None,"display_title":title,
        }
        core.record_acceptance(
            backend,lane=intent["lane"],sequence=intent["sequence"],
            attempt=1,child=accepted,
        )
        run={
            "id":9941,"run_attempt":1,"workflow_id":77,"path":PATH,
            "repository":{"id":REPOSITORY_ID,"full_name":REPOSITORY},
            "event":"workflow_dispatch","head_branch":"main",
            "head_sha":inputs["evaluator_sha"],"display_title":title,
            "status":"completed","conclusion":"cancelled",
            "created_at":"2026-09-01T08:00:00Z","pull_requests":[],
        }
        source=module.build_admission_inbox_source(
            run,repository=REPOSITORY,repository_id=REPOSITORY_ID,
            current_main_sha=inputs["evaluator_sha"],
            target_configs={77:{
                "path":PATH,"activation_locator":LOCATOR,
                "allowed_events":["workflow_dispatch"],
            }},exact_review_core_lookup=core.lookup_fingerprint(
                backend,lane=intent["lane"],fingerprint=intent["fingerprint"]
            ),
        )
        origin=source["origin_authority"]
        retry=module.build_shared_review_core_retry_evidence(
            origin,source=source["source"]
        )
        core.prepare_child_rerun(
            backend,lane=intent["lane"],sequence=intent["sequence"],
            transport_attempt=1,retry_evidence=retry,
            actor_run_id=9051,actor_run_attempt=1,
        )
        durable=module.reobserve_shared_review_core_child_recovery(
            core.lookup_fingerprint(
                backend,lane=intent["lane"],fingerprint=intent["fingerprint"]
            ),origin=origin,
        )
        actor={
            "id":9051,"run_attempt":1,"status":"completed",
            "conclusion":"cancelled",
            "created_at":"2026-09-01T08:30:00Z",
            "updated_at":"2026-09-01T08:31:00Z",
            "repository":{"full_name":REPOSITORY},
        }
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"absence observation differs"
        ):
            module.build_shared_review_core_child_rerun_absence_observation(
                origin,durable["preparation"],target_run=run,
                target_jobs_total=0,target_artifacts_total=0,
                preparation_actor_run=actor,
                observation_started_at="2026-09-01T08:31:00Z",
                observation_completed_at="2026-09-01T08:32:00Z",
            )
        observation=(
            module.build_shared_review_core_child_rerun_absence_observation(
                origin,durable["preparation"],target_run=run,
                target_jobs_total=0,target_artifacts_total=0,
                preparation_actor_run=actor,
                observation_started_at="2026-09-01T08:31:01Z",
                observation_completed_at="2026-09-01T08:32:00Z",
            )
        )
        producer={
            "workflow_path":(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            "workflow_sha":inputs["evaluator_sha"],"workflow_id":903,
            "run_id":9052,"run_attempt":1,"event":"schedule",
        }
        observation_receipt=core.record_authority_observation(
            backend,lane=intent["lane"],sequence=intent["sequence"],
            observation=observation,producer=producer,artifact={
                "id":10052,
                "name":(
                    "qikvrt-outbox-authority-observation-exact-review-dispatch-"
                    f"{intent['sequence']}-CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED-"
                    "run-9052-attempt-1"
                ),
                "archive_sha256":"e"*64,
                "payload_sha256":core.sha256_bytes(
                    core.canonical_bytes(observation)
                ),
                "producer_run_id":9052,"producer_run_attempt":1,
                "producer_workflow_id":903,
            },
        )
        forged=copy.deepcopy(observation_receipt)
        forged["cas"]={}
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"CAS receipt differs"
        ):
            module.build_shared_review_core_child_rerun_terminal_evidence(
                origin,forged
            )
        evidence=(
            module.build_shared_review_core_child_rerun_terminal_evidence(
                origin,observation_receipt
            )
        )
        terminal=core.terminalize(
            backend,lane=intent["lane"],sequence=intent["sequence"],
            evidence=evidence,
        )
        self.assertEqual(terminal["d0"],3)
        fixed=core.lookup_fingerprint(
            backend,lane=intent["lane"],fingerprint=intent["fingerprint"]
        )
        self.assertEqual(fixed["state"],"TERMINAL")
        self.assertEqual(fixed["terminal"]["d0"],3)
        readback=(
            module.validate_shared_review_core_child_rerun_terminal_readback(
                origin,evidence,terminal,fixed
            )
        )
        self.assertEqual(
            readback["state"],"TERMINAL_D0_3_DURABLY_REOBSERVED"
        )
        self.assertEqual(readback["terminal"],fixed["terminal"])
        replayed_terminal=core.terminalize(
            backend,lane=intent["lane"],sequence=intent["sequence"],
            evidence=fixed["terminal"]["evidence"],
        )
        replayed_lookup=core.lookup_fingerprint(
            backend,lane=intent["lane"],fingerprint=intent["fingerprint"]
        )
        replayed_readback=(
            module.validate_shared_review_core_child_rerun_terminal_readback(
                origin,fixed["terminal"]["evidence"],
                replayed_terminal,replayed_lookup,
            )
        )
        self.assertEqual(
            replayed_readback["state"],
            "TERMINAL_D0_3_DURABLY_REOBSERVED",
        )
        raw_receipt=copy.deepcopy(terminal)
        raw_receipt["cas"]={}
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"CAS receipt differs"
        ):
            module.validate_shared_review_core_child_rerun_terminal_readback(
                origin,evidence,raw_receipt,fixed
            )
        volatile=copy.deepcopy(fixed)
        volatile["terminal"]["evidence"]["reason"]=(
            "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED_TAMPERED"
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError,"terminal readback differs"
        ):
            module.validate_shared_review_core_child_rerun_terminal_readback(
                origin,evidence,terminal,volatile
            )

    def test_shared_core_action_required_is_terminal_not_same_run_retry(self):
        from tests.test_qikvrt_ruleset_outbox import MemoryBackend, artifact, payload
        from tools import qikvrt_ruleset_outbox as core

        for offset,lane in enumerate(
            ("exact-review-dispatch","mesh-review-successor-dispatch")
        ):
            with self.subTest(lane=lane):
                backend=MemoryBackend()
                sealed=payload(lane,run_id=7350+offset*20)
                sealed["request"]["inputs"]["transport_intent_sha256"]="0"*64
                if lane == "exact-review-dispatch":
                    sealed["subject"]={
                        "pull_request":935,"head_repository":REPOSITORY,
                        "head_ref":"feature/review","head_sha":"b"*40,
                        "head_tree_sha":"d"*40,"base_ref":"main",
                        "base_sha":"a"*40,
                    }
                else:
                    queue={
                        "pr_number":935,"head_sha":"b"*40,
                        "tree_sha":"d"*40,"base_sha":"a"*40,
                    }
                    sealed["subject"]={
                        "schema":"qikvrt_mesh_review_successor_subject_v1",
                        "queue_path":"state/mesh/review-queue/pr-935.json",
                        "queue_intent_sha256":core.compact_digest(queue),
                        "queue_intent":queue,
                        "source_ledger_commit":"f"*40,
                        "receipt_sha256":"1"*64,"diff_sha256":"2"*64,
                        "productive_effect":False,
                    }
                sealed=core.seal_review_transport_payload(sealed)
                intent=core.append_intent(
                    backend,payload=sealed,artifact=artifact(sealed)
                )
                core.prepare_transport(
                    backend,lane=lane,sequence=intent["sequence"],attempt=1,
                    request=core.request_for_transport_attempt(intent,1),
                    actor_run_id=7351+offset*20,actor_run_attempt=1,
                )
                inputs=intent["payload"]["request"]["inputs"]
                title=(
                    f"qikvrt-rr-v3 e={inputs['evaluator_sha']} "
                    f"p={inputs['pr']} h={inputs['head']} "
                    f"f={inputs['fingerprint']} i={intent['fingerprint']} a=1"
                )
                accepted={
                    "run_id":9961+offset,"run_attempt":1,"workflow_id":77,
                    "workflow_path":PATH,"event":"workflow_dispatch",
                    "repository":REPOSITORY,"head_sha":inputs["evaluator_sha"],
                    "status":"queued","conclusion":None,
                    "display_title":title,
                }
                core.record_acceptance(
                    backend,lane=lane,sequence=intent["sequence"],attempt=1,
                    child=accepted,
                )
                run={
                    "id":accepted["run_id"],"run_attempt":1,
                    "workflow_id":77,"path":PATH,
                    "repository":{"id":REPOSITORY_ID,"full_name":REPOSITORY},
                    "event":"workflow_dispatch","head_branch":"main",
                    "head_sha":inputs["evaluator_sha"],"display_title":title,
                    "status":"completed","conclusion":"action_required",
                    "created_at":"2026-09-01T08:00:00Z",
                    "updated_at":"2026-09-01T08:30:00Z","pull_requests":[],
                }
                lookup=core.lookup_fingerprint(
                    backend,lane=lane,fingerprint=intent["fingerprint"]
                )
                source=module.build_admission_inbox_source(
                    run,repository=REPOSITORY,repository_id=REPOSITORY_ID,
                    current_main_sha=inputs["evaluator_sha"],
                    target_configs={77:{
                        "path":PATH,"activation_locator":LOCATOR,
                        "allowed_events":["workflow_dispatch"],
                    }},
                    exact_review_core_lookup=(
                        lookup if lane == "exact-review-dispatch" else None
                    ),
                    mesh_review_core_lookup=(
                        lookup if lane == "mesh-review-successor-dispatch" else None
                    ),
                )
                origin=source["origin_authority"]
                selection=module.select_recovery(
                    [{**run,"jobs_total":0,"artifacts_total":0}],
                    target_configs={77:{
                        "path":PATH,"activation_locator":LOCATOR,
                        "allowed_events":["workflow_dispatch"],
                    }},repository=REPOSITORY,repository_id=REPOSITORY_ID,
                    current_main_sha=inputs["evaluator_sha"],
                    current_run_id=99999,
                    bound_requested_run_ids={run["id"]},
                )
                receipt=module.build_terminal_receipt(selection)
                live_subject={
                    "pr_number":int(inputs["pr"]),
                    "head_sha":inputs["head"],"head_tree_sha":"d"*40,
                    "head_repository":REPOSITORY,"head_ref":"feature/review",
                    "base_sha":inputs["evaluator_sha"],
                    "base_tree_sha":"e"*40,"base_repository":REPOSITORY,
                    "base_ref":"main",
                }
                observation=(
                    module.build_shared_review_core_action_required_observation(
                        origin,target_run=run,target_jobs_total=0,
                        target_artifacts_total=0,admission_receipt=receipt,
                        current_main_sha=inputs["evaluator_sha"],
                        live_subject=live_subject,
                        observation_started_at="2026-09-01T08:31:00Z",
                        observation_completed_at="2026-09-01T08:32:00Z",
                    )
                )
                self.assertEqual(
                    observation["blocker"],
                    "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
                )
                with self.assertRaisesRegex(
                    module.AdmissionRecoveryError,"does not authorize"
                ):
                    module.build_shared_review_core_retry_evidence(
                        origin,source=source["source"]
                    )
                producer={
                    "workflow_path":(
                        ".github/workflows/qikvrt_review_admission_recovery.yml"
                    ),
                    "workflow_sha":inputs["evaluator_sha"],"workflow_id":903,
                    "run_id":7450+offset,"run_attempt":1,"event":"schedule",
                }
                observation_receipt=core.record_authority_observation(
                    backend,lane=lane,sequence=intent["sequence"],
                    observation=observation,producer=producer,artifact={
                        "id":8450+offset,
                        "name":(
                            f"qikvrt-outbox-authority-observation-{lane}-"
                            f"{intent['sequence']}-"
                            "SOURCE_ATTEMPT_1_ACTION_REQUIRED-"
                            f"run-{producer['run_id']}-attempt-1"
                        ),
                        "archive_sha256":"e"*64,
                        "payload_sha256":core.sha256_bytes(
                            core.canonical_bytes(observation)
                        ),
                        "producer_run_id":producer["run_id"],
                        "producer_run_attempt":1,"producer_workflow_id":903,
                    },
                )
                evidence=(
                    module.build_shared_review_core_action_required_terminal_evidence(
                        origin,observation_receipt
                    )
                )
                terminal=core.terminalize(
                    backend,lane=lane,sequence=intent["sequence"],
                    evidence=evidence,
                )
                durable=core.lookup_fingerprint(
                    backend,lane=lane,fingerprint=intent["fingerprint"]
                )
                readback=(
                    module.validate_shared_review_core_action_required_terminal_readback(
                        origin,receipt,evidence,terminal,durable
                    )
                )
                self.assertEqual(
                    readback["effect_ack"],
                    "ACTION_REQUIRED_HOLD_TERMINAL_REOBSERVED",
                )
                self.assertFalse(readback["approval_authorized"])
                self.assertFalse(readback["required_gate_success_authorized"])
                replay=core.terminalize(
                    backend,lane=lane,sequence=intent["sequence"],
                    evidence=durable["terminal"]["evidence"],
                )
                self.assertEqual(
                    module.validate_shared_review_core_action_required_terminal_readback(
                        origin,receipt,durable["terminal"]["evidence"],
                        replay,core.lookup_fingerprint(
                            backend,lane=lane,fingerprint=intent["fingerprint"]
                        ),
                    )["state"],
                    "TERMINAL_D0_3_DURABLY_REOBSERVED",
                )

    def test_admission_observer_is_limited_to_exact_and_mesh_child_rerun(self):
        from tests.test_qikvrt_ruleset_outbox import MemoryBackend, artifact, payload
        from tools import qikvrt_ruleset_outbox as core

        producer={
            "workflow_path":(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            "workflow_sha":"a"*40,
            "workflow_id":903,"run_id":9052,"run_attempt":1,
            "event":"schedule",
        }
        for lane in ("exact-review-dispatch","mesh-review-successor-dispatch"):
            backend=MemoryBackend()
            sealed=payload(lane,run_id=7100)
            intent=core.append_intent(
                backend,payload=sealed,artifact=artifact(sealed)
            )
            self.assertEqual(
                core._normalize_authority_observer(
                    producer,intent=intent,
                    blocker="CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
                ),producer,
            )
        for lane in (
            "ruleset-dispatch","reconciler-rerun",
            "requested-review-dispatch","exact-head-dispatch",
        ):
            backend=MemoryBackend()
            sealed=payload(lane,run_id=7200)
            intent=core.append_intent(
                backend,payload=sealed,artifact=artifact(sealed)
            )
            with self.assertRaises(core.OutboxBlock):
                core._normalize_authority_observer(
                    producer,intent=intent,
                    blocker="CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
                )

    def test_shared_core_new_run_transport_is_one_shot(self):
        from tests.test_qikvrt_ruleset_outbox import MemoryBackend, artifact, payload
        from tools import qikvrt_ruleset_outbox as core

        backend=MemoryBackend()
        sealed=payload("mesh-review-successor-dispatch",run_id=7041)
        intent=core.append_intent(
            backend,payload=sealed,artifact=artifact(sealed)
        )
        with self.assertRaisesRegex(core.OutboxBlock,"one-shot"):
            core.request_for_transport_attempt(intent,2)
        inputs=intent["payload"]["request"]["inputs"]
        forbidden_title=(
            f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
            f"h={inputs['head']} f={inputs['fingerprint']} "
            f"i={intent['fingerprint']} a=2"
        )
        self.assertIsNone(module._requested_v3_locator(forbidden_title))

    def test_gate_post_effect_receipt_loss_reruns_same_run_without_review_post(self):
        plan, review, pr, run = self.delegated_signer_fixture()
        evidence = module.build_delegated_signer_receipt_recovery_evidence(
            plan=plan,
            run=run,
            repository=REPOSITORY,
            current_main_sha=MAIN,
            pr=pr,
            head_commit={"sha": "b" * 40, "tree": {"sha": "d" * 40}},
            reviews=[review],
            jobs_total=3,
            artifacts_total=1,
            signer_receipt_blocker=(
                "SIGNER_RECEIPT_ARTIFACT_MISSING_OR_AMBIGUOUS"
            ),
            artifact_inventory_sha256="1" * 64,
        )
        self.assertFalse(evidence["new_review_post_authorized"])
        self.assertTrue(evidence["technical_reobservation_only"])
        self.assertFalse(evidence["approval_authorized"])
        self.assertFalse(evidence["required_gate_success_authorized"])
        self.assertEqual(evidence["review"]["state"], "COMMENTED")
        required_config = {
            8201: {
                "path": ".github/workflows/qikvrt_required_review_gate.yml",
                "activation_locator": (
                    "QIKVRT required code-owner review admission-v2"
                ),
                "allowed_events": ["workflow_run", "workflow_dispatch"],
            }
        }
        source = module.build_admission_signer_recovery_source(
            run,
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            target_configs=required_config,
            recovery_evidence=evidence,
        )
        self.assertEqual(
            source["source_kind"], "DELEGATED_SIGNER_RECEIPT_RECOVERY"
        )
        selected = module._projection(run)
        selection = {
            "state": "RERUN_ATTEMPT_2",
            "selected": selected,
            "source_kind": source["source_kind"],
            "origin_authority": source["origin_authority"],
            "rerun_required": True,
            "d0": 2,
        }
        intent = module.build_recovery_intent(
            selection,
            recovery_repository=REPOSITORY,
            recovery_workflow_id=8200,
            recovery_workflow_path=(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            recovery_head_sha=MAIN,
        )
        effect = module.plan_recovery_effect(
            intent,
            source_run=run,
            source_jobs_total=3,
            source_artifacts_total=1,
            current_main_sha=MAIN,
            current_signer_recovery_evidence=evidence,
            current_recovery_producer_binding=(
                module.build_recovery_producer_binding(
                    intent, recovery_run_id=8800, recovery_run_attempt=1
                )
            ),
            current_recovery_run_id=8800,
            current_recovery_run_attempt=1,
        )
        self.assertEqual(effect["source_run_id"], 8123)
        self.assertEqual(effect["authorized_attempt"], 2)
        self.assertFalse(effect["native_account_review_authorized"])
        signer_replay = module.plan_recovery_effect(
            intent,
            source_run=run,
            source_jobs_total=3,
            source_artifacts_total=1,
            current_main_sha=MAIN,
            current_signer_recovery_evidence=evidence,
            current_recovery_producer_binding=(
                module.build_recovery_producer_binding(
                    intent, recovery_run_id=8800, recovery_run_attempt=1
                )
            ),
            current_recovery_run_id=8800,
            current_recovery_run_attempt=2,
        )
        self.assertFalse(signer_replay["new_rerun_post_authorized"])
        slot = module.build_admission_inbox_slot(source, sequence=11)
        attempt_two = {**run, "run_attempt": 2, "conclusion": "success"}
        signer_receipt = {
            "schema": "qikvrt_native_account_review_signer_receipt_v1",
            "repository": REPOSITORY,
            "evaluator_sha": MAIN,
            "run_id": 8123,
            "run_attempt": 2,
            "origin_run_id": 8123,
            "origin_run_attempt": 1,
            "plan_sha256": "3" * 64,
            "evidence_fingerprint": "f" * 64,
            "pr_number": 935,
            "head_sha": "b" * 40,
            "tree_sha": "d" * 40,
            "review": {
                "id": 7701,
                "state": "COMMENTED",
                "body_sha256": evidence["review"]["body_sha256"],
            },
            "effect_readback": {
                "effect_mode": "ADOPT_UNRECEIPTED",
                "state": "COMMENTED",
            },
            "completion_claims": {
                "PASS": False, "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False, "MERGE": False,
            },
            "receipt_sha256": "2" * 64,
        }
        continuation = module.build_admission_signer_receipt_continuation(
            slot, attempt_two, jobs_total=4, artifacts_total=2,
            signer_receipt=signer_receipt,
        )
        self.assertEqual(
            module.validate_admission_signer_receipt_continuation(
                continuation, slot
            ), continuation,
        )
        self.assertEqual(
            continuation["first_causal_continuation"],
            "EXACT_ATTEMPT_2_TECHNICAL_RECEIPT_REOBSERVED",
        )
        self.assertTrue(continuation["technical_reobservation_only"])
        self.assertFalse(continuation["approval_authorized"])
        self.assertFalse(continuation["required_gate_success_authorized"])
        terminal = module.build_terminal_receipt({
            "state": "SIGNER_RECEIPT_RECOVERY_EXHAUSTED_D0_3",
            "selected": {**selected, "run_attempt": 2},
            "rerun_required": False,
            "d0": 3,
            "first_blocker": (
                "DELEGATED_SIGNER_RECEIPT_ATTEMPT_2_ADVERSE"
            ),
        })
        self.assertEqual(terminal["d0"], 3)
        self.assertEqual(
            terminal["first_blocker"],
            "DELEGATED_SIGNER_RECEIPT_ATTEMPT_2_ADVERSE",
        )
        manual = copy.deepcopy(review)
        manual["body"] = "independent manual review"
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "manual, conflicting, dismissed"
        ):
            module.build_delegated_signer_receipt_recovery_evidence(
                plan=plan, run=run, repository=REPOSITORY,
                current_main_sha=MAIN, pr=pr,
                head_commit={"sha": "b" * 40, "tree": {"sha": "d" * 40}},
                reviews=[manual], jobs_total=3, artifacts_total=1,
                signer_receipt_blocker=(
                    "SIGNER_RECEIPT_ARTIFACT_MISSING_OR_AMBIGUOUS"
                ),
                artifact_inventory_sha256="1" * 64,
            )
        historical_marked_approval = copy.deepcopy(review)
        historical_marked_approval["state"] = "APPROVED"
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "manual, conflicting, dismissed"
        ):
            module.build_delegated_signer_receipt_recovery_evidence(
                plan=plan, run=run, repository=REPOSITORY,
                current_main_sha=MAIN, pr=pr,
                head_commit={"sha": "b" * 40, "tree": {"sha": "d" * 40}},
                reviews=[historical_marked_approval],
                jobs_total=3, artifacts_total=1,
                signer_receipt_blocker=(
                    "SIGNER_RECEIPT_ARTIFACT_MISSING_OR_AMBIGUOUS"
                ),
                artifact_inventory_sha256="1" * 64,
            )
        unmarked_human_approval = copy.deepcopy(review)
        unmarked_human_approval["state"] = "APPROVED"
        unmarked_human_approval["body"] = "independent human approval"
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "manual, conflicting, dismissed"
        ):
            module.build_delegated_signer_receipt_recovery_evidence(
                plan=plan, run=run, repository=REPOSITORY,
                current_main_sha=MAIN, pr=pr,
                head_commit={"sha": "b" * 40, "tree": {"sha": "d" * 40}},
                reviews=[unmarked_human_approval],
                jobs_total=3, artifacts_total=1,
                signer_receipt_blocker=(
                    "SIGNER_RECEIPT_ARTIFACT_MISSING_OR_AMBIGUOUS"
                ),
                artifact_inventory_sha256="1" * 64,
            )
        workflow = (
            ROOT / ".github/workflows/qikvrt_review_admission_recovery.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "build_delegated_signer_receipt_recovery_evidence", workflow
        )
        self.assertIn("observe_automated_signer_receipts", workflow)
        self.assertIn("DELEGATED_SIGNER_RECEIPT_RECOVERY", workflow)
        self.assertIn("SIGNER_RECOVERY_RECEIPT_ARTIFACT_NOW_PRESENT", workflow)
        self.assertIn(
            "SIGNER_RECEIPT_RECOVERY_EXHAUSTED_D0_3", workflow
        )
        self.assertIn("build_admission_signer_receipt_continuation", workflow)
        dismissed = copy.deepcopy(review)
        dismissed["state"] = "DISMISSED"
        with self.assertRaises(module.AdmissionRecoveryError):
            module.build_delegated_signer_receipt_recovery_evidence(
                plan=plan, run=run, repository=REPOSITORY,
                current_main_sha=MAIN, pr=pr,
                head_commit={"sha": "b" * 40, "tree": {"sha": "d" * 40}},
                reviews=[dismissed], jobs_total=3, artifacts_total=1,
                signer_receipt_blocker=(
                    "SIGNER_RECEIPT_ARTIFACT_MISSING_OR_AMBIGUOUS"
                ),
                artifact_inventory_sha256="1" * 64,
            )
        with self.assertRaises(module.AdmissionRecoveryError):
            module.build_delegated_signer_receipt_recovery_evidence(
                plan=plan, run=run, repository=REPOSITORY,
                current_main_sha=MAIN, pr=pr,
                head_commit={"sha": "b" * 40, "tree": {"sha": "d" * 40}},
                reviews=[review], jobs_total=3, artifacts_total=1,
                signer_receipt_blocker="VALID_RECEIPT_PRESENT",
                artifact_inventory_sha256="1" * 64,
            )

    def test_durable_ledger_reuses_orphan_and_records_transport_only_ack(self):
        observation = self.human_observation([self.human_review()])
        fact = observation["facts"][0]
        intent = self.wakeup_intent(fact)
        first = module.build_review_wakeup_producer_binding(
            intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        after_intent = module.record_review_wakeup_intent(
            None, intent, first
        )
        entry = module.validate_review_wakeup_record(after_intent)
        self.assertEqual(
            entry["record_path"],
            module.review_wakeup_record_path(fact["fact_fingerprint"]),
        )
        reusable = {
            fact["fact_fingerprint"]: {
                "intent": entry["intent"],
                "transport_attempts": {
                    attempt["transport_attempt"]
                    for attempt in entry["attempts"]
                },
            }
        }
        next_run = module.select_review_wakeup_transition(
            [fact],
            acknowledged_fingerprints=set(),
            terminal_fingerprints=set(),
            reusable_intents=reusable,
        )
        self.assertEqual(next_run["state"], "CORE_TRANSPORT_PENDING")
        core_payload = self.wakeup_core_payload(intent)
        lookup = self.accepted_wakeup_core(intent, core_payload)
        ack = module.build_review_wakeup_ack(
            intent, first, core_payload, lookup, current_main_sha=MAIN
        )
        self.assertEqual(
            ack["effect_ack"], "TRANSPORT_ACCEPTED_PENDING_REOBSERVATION"
        )
        self.assertFalse(ack["completion_claims"]["EFFECT_ACK_DONE"])
        after_ack = module.record_review_wakeup_ack(after_intent, ack)
        self.assertEqual(
            module.validate_review_wakeup_record(after_ack)["ack"],
            ack,
        )
        subject_transition = module.build_review_wakeup_subject_ack_transition(
            None, ack
        )
        subject = subject_transition["subject_after"]
        self.assertEqual(
            module.validate_review_wakeup_subject(subject)
            ["acknowledged_review_count"],
            1,
        )
        self.assertEqual(
            module.validate_review_wakeup_subject_ack_slot(
                subject_transition["slot"], subject=fact
            )["fact"],
            fact,
        )
        advanced_subject = module.advance_review_wakeup_subject_recheck(subject)
        self.assertEqual(advanced_subject["recheck_sequence"], 1)

    def test_durable_ledger_consumed_transport_becomes_terminal_fixed_point(self):
        fact = self.human_observation([self.human_review()])["facts"][0]
        intent = self.wakeup_intent(fact)
        binding = module.build_review_wakeup_producer_binding(
            intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        record = module.record_review_wakeup_intent(None, intent, binding)
        receipt = module.build_review_wakeup_terminal(
            intent, transport_attempts={1}
        )
        terminal_binding = module.build_review_wakeup_terminal_binding(
            receipt,
            intent,
            recovery_run_id=9003,
            recovery_run_attempt=1,
            terminalizer_workflow_sha=MAIN,
        )
        terminal = module.record_review_wakeup_terminal(
            record, receipt, terminal_binding
        )
        entry = module.validate_review_wakeup_record(terminal)
        self.assertEqual(len(entry["attempts"]), 1)
        self.assertEqual(entry["terminal"]["receipt"]["d0"], 3)
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "terminal"
        ):
            module.record_review_wakeup_intent(
                terminal,
                intent,
                module.build_review_wakeup_producer_binding(
                    intent,
                    recovery_run_id=9004,
                    recovery_run_attempt=1,
                    recovery_run_started_at="2026-09-01T10:30:00Z",
                    transport_attempt=1,
                ),
            )

    def test_orphan_frontier_recursively_splits_and_seals_exact_absence(self):
        fact = self.human_observation([self.human_review()])["facts"][0]
        intent = self.wakeup_intent(fact)
        binding = module.build_review_wakeup_producer_binding(
            intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        frontier = module.build_review_wakeup_orphan_frontier(
            intent, binding, observed_to="2026-09-01T08:30:09Z"
        )
        split = module.advance_review_wakeup_orphan_frontier(
            frontier,
            intent,
            binding,
            declared_total=1000,
            filtered_run_ids=[],
            exact_matching_children=[],
        )
        self.assertEqual(split["state"], "PENDING")
        self.assertEqual(len(split["pending_windows"]), 2)
        newer = module.advance_review_wakeup_orphan_frontier(
            split,
            intent,
            binding,
            declared_total=2,
            filtered_run_ids=[41, 42],
            exact_matching_children=[],
        )
        complete = module.advance_review_wakeup_orphan_frontier(
            newer,
            intent,
            binding,
            declared_total=0,
            filtered_run_ids=[],
            exact_matching_children=[],
        )
        self.assertEqual(complete["state"], "COMPLETE")
        self.assertEqual(complete["filtered_run_count"], 2)
        observation = module.build_review_wakeup_orphan_observation_from_frontier(
            intent, binding, complete
        )
        self.assertEqual(observation["result"], "ORPHAN_NO_BOUND_SUCCESSOR")
        self.assertEqual(observation["frontier_sha256"], complete["frontier_sha256"])
        module.validate_review_wakeup_orphan_observation(
            intent, binding, observation
        )

    def test_same_second_orphan_cap_is_quarantined_not_absence(self):
        fact = self.human_observation([self.human_review()])["facts"][0]
        intent = self.wakeup_intent(fact)
        binding = module.build_review_wakeup_producer_binding(
            intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        frontier = module.build_review_wakeup_orphan_frontier(
            intent, binding, observed_to="2026-09-01T08:30:00Z"
        )
        quarantined = module.advance_review_wakeup_orphan_frontier(
            frontier,
            intent,
            binding,
            declared_total=1000,
            filtered_run_ids=[],
            exact_matching_children=[],
        )
        self.assertEqual(quarantined["state"], "QUARANTINED_CAP_HOLD")
        self.assertEqual(quarantined["pending_windows"], [])
        with self.assertRaisesRegex(module.AdmissionRecoveryError, "absence"):
            module.build_review_wakeup_orphan_observation_from_frontier(
                intent, binding, quarantined
            )

    def test_active_old_main_is_terminalized_before_next_current_fact(self):
        old_fact = self.human_observation([self.human_review()])["facts"][0]
        old_intent = self.wakeup_intent(old_fact)
        old_binding = module.build_review_wakeup_producer_binding(
            old_intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        pending = module.record_review_wakeup_intent(
            None, old_intent, old_binding
        )
        active = module.build_review_wakeup_active(old_intent)
        self.assertEqual(
            module.bind_review_wakeup_active_record(active, pending), pending
        )

        newer_main = "f" * 40
        core_payload = self.wakeup_core_payload(old_intent)
        resolution = module.build_review_wakeup_core_resolution(
            old_intent,
            core_payload,
            {"lookup_state": "NOT_FOUND"},
            observed_main_sha=newer_main,
        )
        receipt = module.build_review_wakeup_terminal(
            old_intent,
            transport_attempts={1},
            first_blocker=(
                "REQUESTED_REVIEW_WAKEUP_TRANSITION_SUPERSEDED"
            ),
            core_resolution=resolution,
        )
        terminal_binding = module.build_review_wakeup_terminal_binding(
            receipt,
            old_intent,
            recovery_run_id=9002,
            recovery_run_attempt=1,
            terminalizer_workflow_sha=newer_main,
        )
        self.assertEqual(
            terminal_binding["intent_evaluator_sha"], MAIN
        )
        self.assertEqual(
            terminal_binding["terminalizer_workflow_sha"], newer_main
        )
        terminal_record = module.record_review_wakeup_terminal(
            pending, receipt, terminal_binding
        )
        module.validate_review_wakeup_record(terminal_record)

        new_pr = self.pull_request()
        new_pr["base"]["sha"] = newer_main
        new_observation = module.observe_human_review_facts(
            [new_pr],
            reviews_by_pr={new_pr["number"]: [self.human_review()]},
            commits_by_pr={new_pr["number"]: self.pr_commits()},
            repository=REPOSITORY,
            current_main_sha=newer_main,
            current_main_tree_sha="1" * 40,
        )
        next_selection = module.select_review_wakeup_transition(
            new_observation["facts"],
            acknowledged_fingerprints=set(),
            terminal_fingerprints={old_fact["fact_fingerprint"]},
            reusable_intents={},
        )
        self.assertEqual(next_selection["state"], "DISPATCH_ATTEMPT_1")
        self.assertNotEqual(
            next_selection["fact"]["fact_fingerprint"],
            old_fact["fact_fingerprint"],
        )

    def test_core_resolution_is_exact_and_supersession_requires_not_found_proof(self):
        fact = self.human_observation([self.human_review()])["facts"][0]
        intent = self.wakeup_intent(fact)
        payload = self.wakeup_core_payload(intent)
        newer_main = "f" * 40
        resolution = module.build_review_wakeup_core_resolution(
            intent,
            payload,
            {"lookup_state": "NOT_FOUND"},
            observed_main_sha=newer_main,
        )
        module.validate_review_wakeup_core_resolution(
            resolution, intent, payload, {"lookup_state": "NOT_FOUND"}
        )
        receipt = module.build_review_wakeup_terminal(
            intent,
            transport_attempts={1},
            first_blocker="REQUESTED_REVIEW_WAKEUP_TRANSITION_SUPERSEDED",
            core_resolution=resolution,
        )
        self.assertEqual(
            receipt["core_resolution"]["state"], "SUPERSEDED_NO_CORE_RECORD"
        )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "supersession proof is missing"
        ):
            module.build_review_wakeup_terminal(
                intent,
                transport_attempts={1},
                first_blocker="REQUESTED_REVIEW_WAKEUP_TRANSITION_SUPERSEDED",
            )
        extra = copy.deepcopy(resolution)
        extra["unsealed_claim"] = "PASS"
        extra.pop("resolution_sha256")
        extra["resolution_sha256"] = module._canonical_sha256(extra)
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "resolution shape differs"
        ):
            module.build_review_wakeup_terminal(
                intent,
                transport_attempts={1},
                first_blocker="REQUESTED_REVIEW_WAKEUP_TRANSITION_SUPERSEDED",
                core_resolution=extra,
            )
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "current wake-up cannot resolve"
        ):
            module.build_review_wakeup_core_resolution(
                intent,
                payload,
                {"lookup_state": "NOT_FOUND"},
                observed_main_sha=MAIN,
            )

    def test_core_terminal_without_acceptance_is_a_durable_terminal_fixed_point(self):
        from tests.test_qikvrt_ruleset_outbox import (
            MemoryBackend,
            ambiguity_exhaustion,
            artifact,
            persist_authority_observation,
            terminal_evidence,
        )
        from tools import qikvrt_ruleset_outbox as core

        old_fact = self.human_observation([self.human_review()])["facts"][0]
        intent = self.wakeup_intent(old_fact)
        binding = module.build_review_wakeup_producer_binding(
            intent,
            recovery_run_id=9001,
            recovery_run_attempt=1,
            recovery_run_started_at="2026-09-01T08:30:00Z",
            transport_attempt=1,
        )
        record = module.record_review_wakeup_intent(None, intent, binding)
        payload = self.wakeup_core_payload(intent)
        backend = MemoryBackend()
        core_intent = core.append_intent(
            backend, payload=payload, artifact=artifact(payload)
        )
        core.prepare_transport(
            backend,
            lane=core_intent["lane"],
            sequence=core_intent["sequence"],
            attempt=1,
            request=core.request_for_transport_attempt(core_intent, 1),
            actor_run_id=9001,
            actor_run_attempt=1,
        )
        observation = {
            "schema": core.AUTHORITY_OBSERVATION_SCHEMA,
            "blocker": "OUTBOX_EVALUATOR_SUPERSEDED",
            "lane": core_intent["lane"],
            "sequence": core_intent["sequence"],
            "fingerprint": core_intent["fingerprint"],
            "sealed_main_head_sha": MAIN,
            "observed_main_head_sha": "f" * 40,
            "verified": True,
            "productive_effect": False,
        }
        observation_record = persist_authority_observation(
            backend, core_intent, observation, run_id=9002
        )
        core.terminalize(
            backend,
            lane=core_intent["lane"],
            sequence=core_intent["sequence"],
            evidence=terminal_evidence({
                "d0": 3,
                "state": "REQUEST_AUTHORITY",
                "reason": observation["blocker"],
                "exhaustion": ambiguity_exhaustion(
                    core_intent, observation["blocker"], observation_record
                ),
                "productive_effect": False,
            }),
        )
        lookup = core.lookup_fingerprint(
            backend,
            lane=core_intent["lane"],
            fingerprint=core_intent["fingerprint"],
        )
        self.assertEqual(lookup["lookup_state"], "TERMINAL")
        self.assertIsNone(lookup["acceptance"].get("1"))
        resolution = module.build_review_wakeup_core_resolution(
            intent, payload, lookup, observed_main_sha="f" * 40
        )
        self.assertEqual(resolution["state"], "CORE_TERMINAL_NO_ACCEPTANCE")
        synthetic = copy.deepcopy(lookup)
        synthetic["terminal"].pop("evidence")
        with self.assertRaises(core.OutboxBlock):
            module.build_review_wakeup_core_resolution(
                intent, payload, synthetic, observed_main_sha="f" * 40
            )
        foreign_acceptance = copy.deepcopy(lookup)
        foreign_acceptance["acceptance"] = {"1": None, "PASS": True}
        with self.assertRaisesRegex(
            module.AdmissionRecoveryError, "terminal resolution differs"
        ):
            module.build_review_wakeup_core_resolution(
                intent,
                payload,
                foreign_acceptance,
                observed_main_sha="f" * 40,
            )
        receipt = module.build_review_wakeup_terminal(
            intent,
            transport_attempts={1},
            first_blocker=(
                "SHARED_CORE_EXACT_REVIEW_TERMINAL_WITHOUT_ACCEPTANCE"
            ),
            core_resolution=resolution,
        )
        terminal_binding = module.build_review_wakeup_terminal_binding(
            receipt,
            intent,
            recovery_run_id=9002,
            recovery_run_attempt=1,
            terminalizer_workflow_sha=MAIN,
        )
        terminal = module.record_review_wakeup_terminal(
            record, receipt, terminal_binding
        )
        self.assertEqual(
            terminal["terminal"]["receipt"]["core_resolution"], resolution
        )
        newer_review = self.human_review(
            review_id=7002, submitted_at="2026-09-01T08:21:00Z"
        )
        newer_fact = self.human_observation([newer_review])["facts"][0]
        selected = module.select_review_wakeup_transition(
            [old_fact, newer_fact],
            acknowledged_fingerprints=set(),
            terminal_fingerprints={old_fact["fact_fingerprint"]},
            reusable_intents={},
        )
        self.assertEqual(selected["state"], "DISPATCH_ATTEMPT_1")
        self.assertEqual(selected["fact"], newer_fact)

    def test_zero_job_terminal_binding_survives_main_advance(self):
        exhausted = module.select_recovery(
            [self.source_run(run_attempt=2)],
            target_configs=self.config(),
            repository=REPOSITORY,
            repository_id=REPOSITORY_ID,
            current_main_sha=MAIN,
            current_run_id=999,
        )
        receipt = module.build_terminal_receipt(exhausted)
        binding = module.build_terminal_producer_binding(
            receipt,
            recovery_repository=REPOSITORY,
            recovery_workflow_id=8200,
            recovery_workflow_path=(
                ".github/workflows/qikvrt_review_admission_recovery.yml"
            ),
            recovery_head_sha=MAIN,
            recovery_run_id=9000,
            recovery_run_attempt=1,
        )
        # Validation is historical and takes no current-main argument.
        exact = module.validate_terminal_producer_binding(receipt, binding)
        self.assertEqual(exact["recovery_head_sha"], MAIN)

    def test_scheduled_wakeup_is_complete_read_only_and_durable_before_effect(self):
        workflow = (
            ROOT / ".github/workflows/qikvrt_review_admission_recovery.yml"
        ).read_text(encoding="utf-8")
        planner = workflow.split("  plan-review-wakeup:\n", 1)[1].split(
            "  persist-review-wakeup:\n", 1
        )[0]
        collector = workflow.split(
            "  plan-review-observation:\n", 1
        )[1].split("  advance-review-observation:\n", 1)[0]
        collector_writer = workflow.split(
            "  advance-review-observation:\n", 1
        )[1].split("  plan-review-wakeup:\n", 1)[0]
        persist = workflow.split("  persist-review-wakeup:\n", 1)[1].split(
            "  observe-review-wakeup-core:\n", 1
        )[0]
        observer = workflow.split(
            "  observe-review-wakeup-core:\n", 1
        )[1].split("  enqueue-review-wakeup-core:\n", 1)[0]
        enqueue = workflow.split(
            "  enqueue-review-wakeup-core:\n", 1
        )[1].split("  persist-review-wakeup-ack:\n", 1)[0]
        ack_writer = workflow.split("  persist-review-wakeup-ack:\n", 1)[1]
        self.assertIn("      actions: read", planner)
        self.assertNotIn("actions: write", planner)
        self.assertNotIn("secrets.", planner)
        self.assertNotIn("pull-requests: write", observer + enqueue + ack_writer)
        self.assertNotIn("statuses: write", observer + enqueue + ack_writer)
        self.assertNotIn("QIKVRT_GOLDKELCH_REVIEW_TOKEN", workflow)
        self.assertNotIn("QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN", workflow)
        self.assertNotIn("QIKVRT code-owner review observer", workflow)

        self.assertIn("      contents: read", collector)
        self.assertNotIn("actions: write", collector)
        self.assertNotIn("qikvrt-outbox-ledger-authority", collector)
        self.assertNotIn("secrets.", collector)
        self.assertIn(
            "secrets.QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", collector_writer
        )
        self.assertIn("qikvrt-outbox-ledger-authority", collector_writer)
        self.assertIn("verify_recovery_ledger_authority", collector_writer)
        self.assertIn("direction=asc&per_page=1&page=", collector)
        self.assertNotIn("/pulls/{pull['number']}/commits?", collector)
        self.assertIn("repos/{repo}/commits/{head_sha}", collector)
        self.assertIn("pull-commits endpoint, which is capped at 250", collector)
        self.assertIn("/reviews?", collector)
        self.assertIn("per_page=100&page=", collector)
        self.assertNotIn("--paginate", collector)
        self.assertIn("review_observation_scan_path", collector)
        self.assertIn("review_observation_slot_path", collector)
        self.assertIn("build_review_absence_facts", collector)
        self.assertIn("/reviews/\"", collector)
        self.assertIn("allow_404=True", collector)
        self.assertIn("ACK_RECHECK", collector)
        self.assertIn("One review page is the durable per-subject quantum", collector)
        self.assertIn("build_review_observation_subject_cursor", collector)
        self.assertNotIn(
            "pulls?state=open&base=main&sort=created&direction=asc&per_page=100",
            planner,
        )
        self.assertNotIn("pulls/{number}/reviews?per_page=100", planner)
        self.assertNotIn("pulls/{number}/commits?per_page=100", planner)
        self.assertGreaterEqual(
            workflow.count("commit_observation_mode='EXACT_HEAD_SINGLETON'"),
            4,
        )
        self.assertNotIn("head -n", planner)
        self.assertNotIn("[:100]", planner)
        self.assertNotIn("actions/artifacts?", planner)
        self.assertNotIn(
            "actions/workflows/qikvrt_review_admission_recovery.yml/runs?per_page=100",
            planner,
        )
        self.assertIn("qikvrt/review-wakeup-ledger-v1", planner)
        self.assertIn(
            "Append intent or terminal state with an exact FF-CAS update",
            persist,
        )
        self.assertIn("'force':False", persist)
        self.assertIn("select_review_wakeup_transition", planner)
        self.assertIn("transport_attempts", planner)
        self.assertIn("observation_sequence", planner)

        durable = "Preserve append-only human-review wake-up INTENT before dispatch"
        enqueue_name = "Enqueue Shared-Core witness CAS only"
        self.assertLess(workflow.index(durable), workflow.index(enqueue_name))
        tool = (
            ROOT / "tools/qikvrt_review_admission_recovery.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"return_run_details": True', tool)
        self.assertIn("inputs[evaluator_sha]", (
            ROOT / ".github/workflows/qikvrt_requested_review_executor.yml"
        ).read_text(encoding="utf-8"))
        self.assertIn("X-GitHub-Api-Version: 2026-03-10", observer + enqueue)
        self.assertIn("lookup-fingerprint --lane exact-review-dispatch", observer)
        self.assertIn("enqueue --lane exact-review-dispatch", enqueue)
        self.assertNotIn("prepare-transport --lane exact-review-dispatch", enqueue)
        self.assertNotIn("accept --lane exact-review-dispatch", enqueue)
        self.assertIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", observer)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", observer)
        self.assertIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", enqueue)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", enqueue)
        self.assertIn("build_review_wakeup_ack", observer)
        self.assertIn("core-lookup.json", observer + ack_writer)
        self.assertIn("CORE_ATTEMPT_1_ACCEPTED_LOCATOR", tool)
        self.assertIn("persist-review-wakeup-ack:", workflow)
        self.assertNotIn(
            "actions/workflows/qikvrt_requested_review_executor.yml/dispatches",
            observer + enqueue + ack_writer,
        )
        self.assertNotIn("requested-run-pages-", observer + enqueue + ack_writer)
        self.assertNotIn("accepted-producer-binding.json", observer + ack_writer)
        self.assertIn("custom-ledger-head.txt", observer + ack_writer)
        self.assertIn("core-resolution.zip", ack_writer)
        self.assertIn(
            "if sys.argv[1] == intent['requested_workflow_sha']", observer
        )
        self.assertIn("resolution='ENQUEUE_CORE'", observer)
        self.assertIn("SUPERSEDED_NO_CORE_RECORD", observer + ack_writer)
        self.assertIn("CORE_TERMINAL_NO_ACCEPTANCE", observer + ack_writer)
        self.assertIn("core_resolution['terminal_path']", ack_writer)
        self.assertIn("core_resolution['terminal_sha256']", ack_writer)
        self.assertIn("if subject_path is not None", ack_writer)
        self.assertIn("'sha':None", ack_writer)
        self.assertIn("observation_meta_after['drain_sequence']", ack_writer)
        self.assertIn("record_review_wakeup_terminal", ack_writer)
        self.assertIn(
            "if subject_after is not None else None", ack_writer
        )
        self.assertIn("TRANSPORT_ACCEPTED_PENDING_REOBSERVATION", (
            ROOT / "tools/qikvrt_review_admission_recovery.py"
        ).read_text(encoding="utf-8"))

    def test_zero_job_workflow_binds_repo_id_and_historical_terminal_owner(self):
        workflow = (
            ROOT / ".github/workflows/qikvrt_review_admission_recovery.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("repository_id=int(repository['id'])", workflow)
        self.assertIn("build_terminal_producer_binding", workflow)
        self.assertIn("validate_terminal_producer_binding", workflow)
        self.assertIn("terminal-producer-binding.json", workflow)
        self.assertIn(
            "admission_inbox_terminal_path(sequence)", workflow
        )
        self.assertIn("qikvrt/review-admission-inbox-v1", workflow)
        self.assertIn("inbox_ledger_head", workflow)
        self.assertNotIn("recovery_runs=", workflow)
        self.assertNotIn(
            "actions/workflows/qikvrt_review_admission_recovery.yml/runs?",
            workflow,
        )
        self.assertNotIn("repos/{repo}/actions/artifacts?per_page=100", workflow)

    def test_target_workflows_publish_requested_v3_and_required_v2_locators(self):
        requested = (
            ROOT / ".github/workflows/qikvrt_requested_review_executor.yml"
        ).read_text(encoding="utf-8")
        required = (
            ROOT / ".github/workflows/qikvrt_required_review_gate.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("QIKVRT requested review admission-v2", requested)
        self.assertIn("QIKVRT required code-owner review admission-v2", required)
        self.assertIn("run-name: qikvrt-rr-v3 e=${{ github.workflow_sha }}", requested)
        self.assertIn("transport_intent_sha256:", requested)
        self.assertIn("transport_attempt:", requested)
        self.assertIn("evaluator-${{ github.workflow_sha }}", required)


if __name__ == "__main__":
    unittest.main()
