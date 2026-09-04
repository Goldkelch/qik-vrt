import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class IssueEventPayloadIntakeTest(unittest.TestCase):
    def test_issue_event_uses_signed_payload_without_api_lookup(self) -> None:
        workflow = (
            ROOT / ".github/workflows/issue-autonomous-processing.yml"
        ).read_text(encoding="utf-8")
        resolve = workflow[
            workflow.index("      - name: Resolve issue") :
            workflow.index("      - name: Bind history-preserving issue work branch")
        ]
        issues_clause = resolve[
            resolve.index("            issues)") :
            resolve.index("            workflow_dispatch)")
        ]
        dispatch_clause = resolve[
            resolve.index("            workflow_dispatch)") :
            resolve.index("            *)")
        ]

        self.assertIn("$GITHUB_EVENT_PATH", issues_clause)
        self.assertIn(
            "jq -c '.issue' \"$GITHUB_EVENT_PATH\" > \"$issue_path\"",
            issues_clause,
        )
        self.assertNotIn("gh api", issues_clause)
        self.assertIn("gh api", dispatch_clause)
        self.assertIn("event_payload_sha256", resolve)
        self.assertIn("issue_sha256", resolve)
        self.assertIn(".repository.full_name == $repository", issues_clause)
        self.assertIn(".issue.number == $number", issues_clause)
        self.assertIn(".issue.pull_request | not", issues_clause)


if __name__ == "__main__":
    unittest.main()
