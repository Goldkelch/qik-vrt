# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from datetime import datetime, timezone
from pathlib import Path
import unittest

from tools.qikvrt_requested_review_pending_wakeup import classify_pending_wakeup

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_requested_review_pending_wakeup.yml"
HEAD = "1" * 40


def run(run_id=7, *, status="pending", event="workflow_dispatch", created="2026-09-02T22:54:22Z", title=None):
    return {
        "id": run_id,
        "status": status,
        "event": event,
        "created_at": created,
        "display_title": title or f"QIKVRT requested review pr=958 head={HEAD} fp=event",
    }


def pr(head=HEAD, *, state="open", base="main"):
    return {"state": state, "head": {"sha": head}, "base": {"ref": base}}


class PendingWakeupClassifierTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 2, 23, 0, 0, tzinfo=timezone.utc)

    def test_selects_old_exact_live_pending_when_no_writer_is_active(self):
        value = classify_pending_wakeup(
            pending_runs=[run()], active_runs=[], pull_requests={958: pr()}, now=self.now
        )
        self.assertEqual(value["state"], "WAKEUP_REQUIRED")
        self.assertEqual(value["first_blocker"], "SINGLE_PENDING_SLOT_WITHOUT_ACTIVE_WRITER")
        self.assertEqual(value["run_id"], 7)
        self.assertEqual(value["pr_number"], 958)
        self.assertEqual(value["head_sha"], HEAD)

    def test_active_writer_holds_without_selecting_pending_transport(self):
        value = classify_pending_wakeup(
            pending_runs=[run()],
            active_runs=[run(9, status="in_progress")],
            pull_requests={958: pr()},
            now=self.now,
        )
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["first_blocker"], "REQUESTED_REVIEW_WRITER_ACTIVE")
        self.assertFalse(value["selected"])

    def test_grace_period_prevents_premature_wakeup(self):
        value = classify_pending_wakeup(
            pending_runs=[run(created="2026-09-02T22:59:30Z")],
            active_runs=[], pull_requests={958: pr()}, now=self.now, grace_seconds=120,
        )
        self.assertEqual(value["state"], "NOOP")
        self.assertFalse(value["selected"])
        self.assertEqual(value["observations"][0]["first_blocker"], "PENDING_GRACE_PERIOD_ACTIVE")

    def test_head_drift_is_not_retried(self):
        value = classify_pending_wakeup(
            pending_runs=[run()], active_runs=[], pull_requests={958: pr("2" * 40)}, now=self.now
        )
        self.assertEqual(value["state"], "NOOP")
        self.assertEqual(value["observations"][0]["first_blocker"], "EXACT_SUBJECT_DRIFT")

    def test_generic_workflow_run_is_never_woken(self):
        value = classify_pending_wakeup(
            pending_runs=[run(event="workflow_run", title="QIKVRT requested review pr=event head=event fp=event")],
            active_runs=[], pull_requests={}, now=self.now,
        )
        self.assertEqual(value["state"], "NOOP")


class PendingWakeupWorkflowContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_event_driven_and_main_push_bootstraps_orphan_recovery(self):
        self.assertIn("push:\n    branches: [main]", self.text)
        self.assertIn('"QIKVRT requested review executor"', self.text)
        self.assertNotIn("schedule:", self.text)

    def test_cancellation_has_bounded_readback_before_replacement(self):
        self.assertIn("Cancel orphaned pending transport and require readback", self.text)
        self.assertIn("for delay in 0 2 5 10", self.text)
        self.assertIn('test "$state" != pending', self.text)

    def test_replacement_is_exactly_bound_and_not_candidate_mutation(self):
        self.assertIn("qikvrt_requested_review_executor.yml/dispatches", self.text)
        self.assertIn('test "$observed" = "$HEAD_SHA"', self.text)
        self.assertNotIn("git push", self.text)
        self.assertNotIn("gh pr merge", self.text)


if __name__ == "__main__":
    unittest.main()
