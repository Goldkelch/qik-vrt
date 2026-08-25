from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/GITHUB_API_RATE_LIMIT_HOLD_V1.json"
REFLEXIVE = ROOT / ".github/workflows/qikvrt_reflexive_repository_watchdog.yml"
LIVE = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"


class EventDrivenMonitorPlatformHoldTests(unittest.TestCase):
    def test_rate_limit_is_registered_as_external_platform_hold(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertEqual(policy["failure_class"], "GITHUB_API_RATE_LIMIT")
        self.assertEqual(policy["disposition"], "HOLD_EXTERNAL_PLATFORM")
        action = policy["bounded_action"]
        self.assertTrue(action["persist_exact_head_tree_and_error_digest"])
        self.assertTrue(action["emit_typed_receipt"])
        self.assertFalse(action["semantic_work_performed"])
        self.assertFalse(action["blind_retry"])
        self.assertFalse(action["dispatch"])
        self.assertFalse(action["candidate_mutation"])
        self.assertFalse(action["success_inference"])
        self.assertFalse(
            policy["continuation"]["elapsed_time_alone_authorizes_domain_work"]
        )
        self.assertTrue(
            all(value is False for value in policy["completion_claims"].values())
        )

    def test_live_status_is_one_shot_event_driven_and_rate_limit_safe(self) -> None:
        workflow = LIVE.read_text(encoding="utf-8")
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [completed]", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertNotIn("sleep 5", workflow)
        self.assertNotIn("while :", workflow)
        self.assertIn("one exact event-bound repository snapshot", workflow)
        self.assertIn("head_sha=$head", workflow)
        self.assertIn("GITHUB_API_RATE_LIMIT", workflow)
        self.assertIn("platform-hold.json", workflow)
        self.assertIn("polling: false", workflow)
        self.assertIn("include-hidden-files: true", workflow)
        self.assertNotIn("/dispatches", workflow)
        self.assertNotIn("gh pr merge", workflow)

    def test_watchdog_fail_safe_persists_receipt_without_domain_work(self) -> None:
        workflow = REFLEXIVE.read_text(encoding="utf-8")
        self.assertIn("Lost-event fail-safe only", workflow)
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn("GITHUB_API_RATE_LIMIT", workflow)
        self.assertIn("HOLD_EXTERNAL_PLATFORM", workflow)
        self.assertIn("platform-hold.json", workflow)
        self.assertIn("reflexive-watchdog-receipt.json", workflow)
        self.assertIn("gatewatch-receipt.json", workflow)
        self.assertIn("include-hidden-files: true", workflow)
        self.assertNotIn("/dispatches", workflow)
        self.assertNotIn("gh pr merge", workflow)


if __name__ == "__main__":
    unittest.main()
