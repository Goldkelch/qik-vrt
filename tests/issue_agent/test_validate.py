import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.infer import SYSTEM_PROMPT
from scripts.issue_agent.promote import promote
from scripts.issue_agent.validate import validate


class ValidateIssueAgentBundleTest(unittest.TestCase):
    def make_bundle(self, directory: Path) -> None:
        request = json.dumps({"issue_number": 76}, sort_keys=True) + "\n"
        (directory / "REQUEST.json").write_text(request, encoding="utf-8")
        digest = hashlib.sha256(request.encode()).hexdigest()
        (directory / "REQUEST.sha256").write_text(f"{digest}  REQUEST.json\n", encoding="utf-8")
        (directory / "CONTEXT.md").write_text("context\n", encoding="utf-8")
        (directory / "ANSWER.md").write_text(
            "## Issue disposition\n\nEXECUTE_NOW\n\n"
            "## Disposition reason\n\nThe request is clear and actionable.\n\n"
            "## Required next action\n\nExecute the smallest bounded work unit.\n\n"
            "## Gate result\n\nCONTINUE\n",
            encoding="utf-8",
        )
        (directory / "STATUS.json").write_text(json.dumps({
            "status": "CONTINUE",
            "model_inference_completed": True,
            "issue_disposition": "EXECUTE_NOW",
            "disposition_reason": "The request is clear and actionable.",
            "next_action": "Execute the smallest bounded work unit.",
            "closure_recommended": False,
            "automatic_issue_close": False,
            "automatic_merge": False,
            "generated_at": "2026-08-25T00:00:00Z",
            "request_sha256": digest,
            "transaction_id": f"issue-76-{digest[:24]}",
            "no_false_pass": True,
        }), encoding="utf-8")

    def test_valid_bundle_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            validate(directory)

    def test_automatic_merge_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status["automatic_merge"] = True
            status_path.write_text(json.dumps(status), encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate(directory)

    def test_missing_issue_disposition_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            del status["issue_disposition"]
            status_path.write_text(json.dumps(status), encoding="utf-8")
            with self.assertRaises(SystemExit):
                validate(directory)

    def test_closure_disposition_may_use_none_next_action(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({
                "issue_disposition": "CLOSE_INVALID_OR_UNSUPPORTED",
                "disposition_reason": "The request is not reproducible from repository evidence.",
                "next_action": "NONE",
                "closure_recommended": True,
            })
            status_path.write_text(json.dumps(status), encoding="utf-8")
            validate(directory)

    def test_execute_now_remains_nonterminal_after_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            promote(directory)
            status = json.loads((directory / "STATUS.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "CONTINUE")
            self.assertFalse(status["automatic_merge"])
            self.assertFalse(status["automatic_issue_close"])
            self.assertFalse(status["mirror_sync_required"])
            self.assertFalse(status["common_tag_required"])
            validate(directory)

    def test_blocked_disposition_is_persisted_without_model_inference(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            (directory / "ANSWER.md").write_text(
                "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
                "## Disposition reason\n\nMODEL_INFERENCE_UNAVAILABLE\n\n"
                "## Required next action\n\nRetry when trusted inference is available.\n\n"
                "## Gate result\n\nBLOCK\n",
                encoding="utf-8",
            )
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({
                "model_inference_completed": False,
                "issue_disposition": "BLOCKED_WITH_NEXT_ACTION",
                "disposition_reason": "MODEL_INFERENCE_UNAVAILABLE",
                "next_action": "Retry when trusted inference is available.",
                "closure_recommended": False,
            })
            status_path.write_text(json.dumps(status), encoding="utf-8")
            promote(directory)
            promoted = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(promoted["status"], "BLOCK")
            self.assertFalse(promoted["automatic_merge"])
            self.assertFalse(promoted["automatic_issue_close"])
            validate(directory)

    def test_terminal_closure_alone_promotes_to_done(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            (directory / "ANSWER.md").write_text(
                "## Issue disposition\n\nCLOSE_COMPLETED\n\n"
                "## Disposition reason\n\nThe canonical successor fully evidences completion.\n\n"
                "## Required next action\n\nNONE\n\n"
                "## Gate result\n\nCONTINUE\n",
                encoding="utf-8",
            )
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({
                "issue_disposition": "CLOSE_COMPLETED",
                "disposition_reason": "The canonical successor fully evidences completion.",
                "next_action": "NONE",
                "closure_recommended": True,
            })
            status_path.write_text(json.dumps(status), encoding="utf-8")
            promote(directory)
            promoted = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(promoted["status"], "DONE")
            self.assertTrue(promoted["automatic_merge"])
            self.assertTrue(promoted["automatic_issue_close"])
            self.assertTrue(promoted["mirror_sync_required"])
            self.assertTrue(promoted["common_tag_required"])
            validate(directory)

    def test_policy_and_owner_delegation_are_active_and_fail_closed(self):
        policy = json.loads((
            ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
        ).read_text(encoding="utf-8"))
        delegation = json.loads((
            ROOT / "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
        ).read_text(encoding="utf-8"))
        continuation = json.loads((
            ROOT / "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json"
        ).read_text(encoding="utf-8"))

        self.assertEqual(
            policy["schema"],
            "qikvrt_requested_review_and_issue_lifecycle_policy_v1",
        )
        self.assertEqual(policy["status"], "ACTIVE")
        self.assertEqual(
            policy["issue_lifecycle"]["unclassified_open_issue"],
            "FORBIDDEN",
        )
        self.assertEqual(
            set(policy["issue_lifecycle"]["allowed_dispositions"]),
            {
                "EXECUTE_NOW",
                "CLARIFICATION_REQUIRED",
                "BLOCKED_WITH_NEXT_ACTION",
                "CLOSE_COMPLETED",
                "CLOSE_NOT_PLANNED",
                "CLOSE_INVALID_OR_UNSUPPORTED",
            },
        )
        self.assertEqual(delegation["state"], "ACTIVE")
        self.assertEqual(
            delegation["combined_source_sha256"],
            "1f66e77ab105f24c95c4d275e1deab5cc97aa0dcc896a1c833fb12cafd06eec6",
        )
        self.assertTrue(
            delegation["authorization_scope"][
                "perform_requested_substantive_reviews_without_reinteraction"
            ]
        )
        self.assertTrue(
            delegation["authorization_scope"]["triage_every_observed_open_issue"]
        )
        self.assertFalse(
            policy["mandatory_boundaries"]["merge_or_promotion_implicitly_authorized"]
        )
        self.assertFalse(
            policy["mandatory_boundaries"]["external_publication_or_submission_authorized"]
        )
        self.assertIn(
            "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json",
            continuation["related_delegations"],
        )

    def test_issue_agent_prompt_requires_one_lifecycle_disposition(self):
        for token in (
            "EXECUTE_NOW",
            "CLARIFICATION_REQUIRED",
            "BLOCKED_WITH_NEXT_ACTION",
            "CLOSE_COMPLETED",
            "CLOSE_NOT_PLANNED",
            "CLOSE_INVALID_OR_UNSUPPORTED",
        ):
            self.assertIn(token, SYSTEM_PROMPT)
        self.assertIn("Do not leave an issue in an unclassified waiting state", SYSTEM_PROMPT)

    def test_failed_inference_materialization_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            command = [
                sys.executable,
                str(ROOT / "scripts/issue_agent/finalize.py"),
                "--directory",
                str(directory),
                "--inference-outcome",
                "failure",
            ]
            subprocess.run(command, cwd=ROOT, check=True)
            first = {
                path.name: path.read_bytes()
                for path in directory.iterdir()
                if path.is_file()
            }
            subprocess.run(command, cwd=ROOT, check=True)
            second = {
                path.name: path.read_bytes()
                for path in directory.iterdir()
                if path.is_file()
            }
            self.assertEqual(first, second)

    def test_issue_writer_is_history_preserving_and_integrity_atomic(self):
        workflow = (
            ROOT / ".github/workflows/issue-autonomous-processing.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("$RUNNER_TEMP/qikvrt-issue.json", workflow)
        self.assertIn(
            "group: qikvrt-repository-evidence-issue-agent/",
            workflow,
        )
        self.assertNotIn("git checkout -B", workflow)
        self.assertNotIn("git push --force", workflow)
        self.assertNotIn("git push --force-with-lease", workflow)
        self.assertIn("git merge-base --is-ancestor", workflow)
        self.assertIn("issue branch advanced before history-preserving persistence", workflow)
        self.assertIn("git push origin \"HEAD:refs/heads/$BRANCH\"", workflow)

        generate = workflow.index("tools/qikvrt_integrity.py generate")
        verify = workflow.index("tools/qikvrt_integrity.py verify", generate)
        gates = workflow.index("make test", verify)
        persistence = workflow.index(
            "- name: Create or update issue work branch and pull request"
        )
        stage = workflow.index('"evidence/issues/$ISSUE_NUMBER"', persistence)
        commit = workflow.index('git commit -m "issue-agent: process issue')
        push = workflow.index('git push origin "HEAD:refs/heads/$BRANCH"')
        self.assertLess(generate, verify)
        self.assertLess(verify, gates)
        self.assertLess(gates, stage)
        self.assertLess(stage, commit)
        self.assertLess(commit, push)
        for path in (
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        ):
            self.assertIn(path, workflow[stage:commit])
        self.assertIn("persisted_head", workflow[push:])

    def test_internal_bot_pr_materialization_is_admitted_without_bot_push_loop(self):
        workflow = (
            ROOT / ".github/workflows/qikvrt_batch04_integrity.yml"
        ).read_text(encoding="utf-8")
        predicate_end = workflow.index("    runs-on:", workflow.index("  materialize:"))
        predicate = workflow[workflow.index("    if:", workflow.index("  materialize:")):predicate_end]
        self.assertIn("github.event_name == 'pull_request'", predicate)
        self.assertIn(
            "github.event.pull_request.head.repo.full_name == github.repository",
            predicate,
        )
        self.assertIn("github.actor != 'dependabot[bot]'", predicate)
        self.assertIn("github.event_name == 'workflow_dispatch'", predicate)
        self.assertIn("github.event_name == 'push'", predicate)
        self.assertIn("github.actor != 'github-actions[bot]'", predicate)
        pull_request_clause = predicate[:predicate.index("github.event_name == 'workflow_dispatch'")]
        self.assertNotIn("github.actor != 'github-actions[bot]'", pull_request_clause)

    def test_backlog_resume_is_explicit_not_time_driven(self):
        workflow = (
            ROOT / ".github/workflows/issue-agent-backlog-resume.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("minimum_age_seconds", workflow)
        self.assertNotIn("generated_at", workflow)
        self.assertIn("workflow_dispatch:", workflow)


if __name__ == "__main__":
    unittest.main()
