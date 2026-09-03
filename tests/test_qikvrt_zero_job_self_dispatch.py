from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_zero_job_self_dispatch.yml"


class ZeroJobSelfDispatchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_uses_event_bound_pull_request_subject(self) -> None:
        self.assertIn("github.event.workflow_run.pull_requests", self.text)
        self.assertIn("EVENT_PRS", self.text)
        self.assertIn("expected exactly one event-bound PR subject", self.text)
        self.assertIn("event_head", self.text)
        self.assertIn('test "$event_head" = "$HEAD_SHA"', self.text)

    def test_does_not_rediscover_all_open_pull_requests(self) -> None:
        self.assertNotIn('pulls?state=open&head=${GITHUB_REPOSITORY_OWNER}:', self.text)
        self.assertNotIn('pulls?state=open', self.text)
        self.assertIn('gh api "repos/${GITHUB_REPOSITORY}/pulls/${pr}"', self.text)

    def test_rebinds_live_exact_subject_before_effect(self) -> None:
        self.assertIn('test "$live_repo" = "$GITHUB_REPOSITORY"', self.text)
        self.assertIn('test "$base_ref" = main', self.text)
        self.assertIn('test "$live_head" = "$HEAD_SHA"', self.text)
        self.assertIn('event_type:"qikvrt_autonomous_exact_head_verify"', self.text)
        self.assertIn('reason:"ZERO_JOB_ACTION_REQUIRED"', self.text)

    def test_never_converts_recovery_into_completion(self) -> None:
        self.assertNotIn("EFFECT_ACK_DONE=true", self.text)
        self.assertNotIn("FINAL_PASS=true", self.text)
        self.assertIn("REOBSERVE/D0=2 dispatched", self.text)


if __name__ == "__main__":
    unittest.main()
