import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/issue-autonomous-processing.yml"


class DeterministicIssueWorkflowTest(unittest.TestCase):
    def test_issue_controller_has_no_external_model_execution_path(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("models: read", text)
        self.assertNotIn("scripts/issue_agent/infer.py", text)
        self.assertNotIn("models.github.ai", text)
        self.assertIn("scripts/issue_agent/compile.py", text)
        self.assertIn("id: compiler", text)
        self.assertIn("INFERENCE_OUTCOME: ${{ steps.compiler.outcome }}", text)

    def test_history_preserving_and_authority_boundaries_survive_port(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("git merge-base --is-ancestor", text)
        self.assertIn("issue branch advanced before history-preserving persistence", text)
        self.assertIn("Dispatch and reobserve the exact issue completion authority receipt", text)
        self.assertNotIn("git push --force", text)
        self.assertNotIn("git push --force-with-lease", text)


if __name__ == "__main__":
    unittest.main()
