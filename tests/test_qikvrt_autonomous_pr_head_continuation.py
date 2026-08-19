import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_pr_head_continuation.yml"


class AutonomousPrHeadContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_time_driven_and_manually_probeable(self):
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn('cron: "7,22,37,52 * * * *"', self.text)

    def test_authority_is_minimal_and_does_not_merge_or_review(self):
        self.assertIn("actions: write", self.text)
        self.assertIn("contents: read", self.text)
        self.assertIn("pull-requests: read", self.text)
        self.assertNotIn("pull-requests: write", self.text)
        self.assertNotIn("/merges", self.text)
        self.assertNotIn("/reviews", self.text)

    def test_discovery_and_productive_edge_are_bounded(self):
        self.assertIn("per_page=30", self.text)
        self.assertIn("break", self.text)
        self.assertIn("zero_job_action_required", self.text)
        self.assertIn("useful_terminal", self.text)
        self.assertIn('test "$live_ref" = "$selected_head"', self.text)
        self.assertIn('test "$live_ref" = "$HEAD_SHA"', self.text)

    def test_only_characteristic_zero_job_action_required_state_is_resumed(self):
        self.assertIn('"$conclusion" = action_required', self.text)
        self.assertIn(".total_count", self.text)
        self.assertIn('"$zero_job_action_required" -gt 0', self.text)
        self.assertIn('"$useful_terminal" -eq 0', self.text)

    def test_named_exact_head_gate_surface_is_restored(self):
        self.assertIn("qikvrt_ci.yml", self.text)
        self.assertIn("qikvrt_collective_review.yml", self.text)
        self.assertIn("qikvrt_global_completion.yml", self.text)
        self.assertIn('-f ref="$HEAD_REF"', self.text)

    def test_continuation_is_exact_head_bound_and_review_authority_stays_separate(self):
        self.assertIn('event_type:"qikvrt_autonomous_exact_head_verify"', self.text)
        self.assertIn("head_sha:$head", self.text)
        self.assertIn("base_sha:$base", self.text)
        self.assertIn("qikvrt_requested_review_executor.yml/dispatches", self.text)
        self.assertIn("cannot fabricate approval", self.text)


if __name__ == "__main__":
    unittest.main()
