import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.infer import SYSTEM_PROMPT
from scripts.issue_agent.continuation import build_record
from scripts.issue_agent.promote import promote
from scripts.issue_agent.validate import validate

SOURCE = {
    "repository": "Goldkelch/qik-vrt",
    "ref": "refs/heads/main",
    "head_sha": "4ea0491a5484075215f17dbcd157a2a5f18ef633",
    "tree_sha": "2f3a9ba1bbc645037a937614700e606ac99ebe58",
}


class ValidateIssueAgentBundleTest(unittest.TestCase):
    @staticmethod
    def rebind_continuation(directory: Path, status: dict[str, object]) -> None:
        request = json.loads((directory / "REQUEST.json").read_text(encoding="utf-8"))
        (directory / "CONTINUATION.json").write_text(
            json.dumps(build_record(request, status, source=SOURCE), sort_keys=True),
            encoding="utf-8",
        )

    def make_bundle(self, directory: Path) -> None:
        request_value = {
            "repository": "Goldkelch/qik-vrt",
            "issue_number": 76,
            "title": "Test issue",
            "body": "Bounded test body.",
            "author": "example",
            "html_url": "https://github.com/Goldkelch/qik-vrt/issues/76",
            "created_at": "2026-08-30T12:00:00Z",
        }
        request = json.dumps(request_value, sort_keys=True) + "\n"
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
        status = {
            "status": "CONTINUE",
            "model_inference_completed": True,
            "issue_disposition": "EXECUTE_NOW",
            "disposition_reason": "The request is clear and actionable.",
            "next_action": "Execute the smallest bounded work unit.",
            "closure_recommended": False,
            "automatic_issue_close": False,
            "automatic_merge": False,
            "no_false_pass": True,
        }
        (directory / "STATUS.json").write_text(json.dumps(status), encoding="utf-8")
        (directory / "CONTINUATION.json").write_text(
            json.dumps(build_record(request_value, status, source=SOURCE), sort_keys=True),
            encoding="utf-8",
        )

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
            self.rebind_continuation(directory, status)
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
            self.rebind_continuation(directory, status)
            promote(directory)
            promoted = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertEqual(promoted["status"], "BLOCK")
            self.assertFalse(promoted["automatic_merge"])
            self.assertFalse(promoted["automatic_issue_close"])
            validate(directory)

    def test_promotion_strips_legacy_observation_timestamps_from_durable_status(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text(encoding="utf-8"))
            status.update({
                "generated_at": "2026-08-30T12:00:00Z",
                "validated_disposition_at": "2026-08-30T12:01:00Z",
            })
            status_path.write_text(json.dumps(status), encoding="utf-8")
            self.rebind_continuation(directory, status)
            promote(directory)
            promoted = json.loads(status_path.read_text(encoding="utf-8"))
            self.assertNotIn("generated_at", promoted)
            self.assertNotIn("validated_disposition_at", promoted)
            self.assertNotIn("validated_completion_promoted_at", promoted)
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
            self.rebind_continuation(directory, status)
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


if __name__ == "__main__":
    unittest.main()
