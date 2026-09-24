from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_repository_native_watch.yml"


class RepositoryNativeWatchWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.body = WORKFLOW.read_text(encoding="utf-8")

    def test_repository_native_triggers_are_persistent(self) -> None:
        body = self.body
        self.assertIn('cron: "*/5 * * * *"', body)
        self.assertIn("pull_request_target:", body)
        self.assertIn("types: [synchronize, reopened, closed]", body)
        self.assertIn("issues:", body)
        self.assertIn("workflow_dispatch:", body)

    def test_watch_never_executes_candidate_code(self) -> None:
        body = self.body
        self.assertNotIn("actions/checkout", body)
        self.assertIn("contents: read", body)
        self.assertNotIn("contents: write", body)
        self.assertIn("actions: read", body)
        self.assertNotIn("actions: write", body)

    def test_exact_subject_binding_is_fail_closed(self) -> None:
        body = self.body
        self.assertIn('[ "$run_pr_count" -ne 1 ]', body)
        self.assertIn('[ "$run_pr_head" != "$baseline" ]', body)
        self.assertIn('[ "$run_head" != "$baseline" ]', body)
        self.assertIn("BASELINE_PREDECESSOR_ONLY", body)
        self.assertIn("EXACT_CURRENT_HEAD", body)

    def test_predecessor_and_effect_boundaries_are_explicit(self) -> None:
        body = self.body
        self.assertIn("predecessor_evidence_transfer:false", body)
        self.assertIn("effect_ack_done:false", body)
        self.assertIn("PREDECESSOR_EVIDENCE_TRANSFER=false", body)
        self.assertIn("EFFECT_ACK_DONE=false", body)

    def test_transition_identity_excludes_observation_time(self) -> None:
        body = self.body
        self.assertIn("transition_json=", body)
        self.assertIn("jq 'del(.observed_at)'", body)
        self.assertIn('receipt_id="$(sha256sum "$transition_json"', body)
        self.assertNotIn('receipt_id="$(sha256sum "$receipt_json"', body)

    def test_trigger_receipt_is_freshly_read_back(self) -> None:
        body = self.body
        self.assertIn("watch receipt comment readback mismatch", body)
        self.assertIn("watch issue close readback mismatch", body)
        self.assertIn("qikvrt-repository-watch-receipt:", body)


if __name__ == "__main__":
    unittest.main()
