import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.infer import SYSTEM_PROMPT
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
            "## Required next action\n\nExecute the smallest bounded work unit.\n",
            encoding="utf-8",
        )
        (directory / "STATUS.json").write_text(json.dumps({
            "status": "CONTINUE",
            "issue_disposition": "EXECUTE_NOW",
            "disposition_reason": "The request is clear and actionable.",
            "next_action": "Execute the smallest bounded work unit.",
            "closure_recommended": False,
            "automatic_issue_close": False,
            "automatic_merge": False,
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
