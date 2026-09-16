# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Permanent regression for CONTINUATION_CHAIN_DROPS_BEFORE_EXECUTION.

Real witness: QIKVRT autonomous PR-head continuation run 35035933030,
triggered for PR #1105 head 2c6ca7f74c9aeb278230ccdad52c1b344307514e,
concluded cancelled before GitHub created any job.
"""
from pathlib import Path
import unittest
import json
import subprocess
import sys

from tools.qikvrt_pr_head_recovery import classify_observations

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/qikvrt_autonomous_pr_head_continuation.yml'

class ContinuationZeroJobCancelledRegression(unittest.TestCase):
    def test_continuation_contract_cannot_accept_pre_job_cancel_as_progress(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        # A repository event must have a runnable continuation job.  A
        # cancelled run with jobs=0 is an adverse terminal state, never NOOP,
        # success, or evidence that the successor chain progressed.
        self.assertIn('jobs:', text)
        self.assertIn('continue-one-stalled-internal-pr:', text)
        self.assertIn('cancel-in-progress: false', text)
        self.assertNotIn('if: false', text)

    def test_zero_job_cancelled_is_named_as_a_permanent_adverse_state(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('ZERO_JOB_CANCELLED', text)
        self.assertIn('CONTINUATION_CHAIN_DROPS_BEFORE_EXECUTION', text)


    def witness(self, **changes):
        value = dict(id=35035933030,
                     name="QIKVRT autonomous PR-head continuation",
                     status="completed", conclusion="cancelled", jobs_total=0,
                     created_at="2026-09-15T23:30:04Z")
        value.update(changes)
        return value

    def test_zero_job_cancelled_holds_even_with_a_green_exact_head_status(self):
        for status in ("missing", "pending", "success", "failure", "error"):
            with self.subTest(status=status):
                result = classify_observations([self.witness()], exact_head_status=status)
                self.assertEqual((result.d0, result.state, result.reason),
                                 (1, "HOLD", "ZERO_JOB_CANCELLED"))
                self.assertFalse(result.to_mapping()["productive_effect"])
                self.assertEqual(result.to_mapping()["effect_ack"], "NOT_REQUIRED")

    def test_cancellation_cannot_authorize_an_action_required_retry(self):
        stalled = self.witness(id=35035933031, name="QIKVRT CI",
                               conclusion="action_required")
        result = classify_observations([self.witness(), stalled])
        self.assertEqual((result.d0, result.reason), (1, "ZERO_JOB_CANCELLED"))

    def test_executed_cancelled_job_remains_an_executed_failure(self):
        result = classify_observations([self.witness(jobs_total=1)])
        self.assertEqual((result.d0, result.reason), (1, "EXECUTED_FAILURE_PRESENT"))

    def test_later_executed_success_supersedes_historical_cancellation(self):
        later = self.witness(id=35035933031, conclusion="success", jobs_total=1,
                             created_at="2026-09-15T23:31:04Z")
        result = classify_observations([later, self.witness()])
        self.assertEqual(result.d0, 0)
        self.assertFalse(result.to_mapping()["productive_effect"])

    def test_later_cancellation_is_not_masked_by_historical_success(self):
        earlier = self.witness(id=35035933029, conclusion="success", jobs_total=1,
                               created_at="2026-09-15T23:29:04Z")
        result = classify_observations([earlier, self.witness()])
        self.assertEqual((result.d0, result.reason), (1, "ZERO_JOB_CANCELLED"))

    def test_cli_preserves_the_adverse_state_without_an_effect(self):
        run = subprocess.run(
            [sys.executable, "-B", str(ROOT / "tools/qikvrt_pr_head_recovery.py"),
             "classify", "--input", "-", "--exact-head-status", "success"],
            input=json.dumps([self.witness()]), text=True,
            capture_output=True, check=True)
        result = json.loads(run.stdout)
        self.assertEqual((result["d0"], result["reason"]), (1, "ZERO_JOB_CANCELLED"))
        self.assertFalse(result["productive_effect"])

    def test_pending_runs_queue_without_removing_the_single_writer_lock(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        concurrency = text.split("\nconcurrency:\n", 1)[1].split("\njobs:", 1)[0]
        self.assertIn("qikvrt-autonomous-pr-head-continuation-", concurrency)
        self.assertIn("github.repository", concurrency)
        self.assertIn("  queue: max\n", concurrency)
        self.assertIn("  cancel-in-progress: false", concurrency)
        self.assertNotIn("github.run_id", concurrency)

    def test_aggregate_hold_checks_all_decisions_not_only_the_last_one(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("any(.[]; .reason == \"ZERO_JOB_CANCELLED\")", text)
        self.assertIn("any(.[]; .d0 == 1)", text)
        self.assertNotIn("jq -e 'select(.d0 == 1)'", text)

    def test_candidate_execution_is_read_only_and_exact_head_bound(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("  pull_request:\n", text)
        self.assertIn("if: github.event_name != 'pull_request'", text)
        candidate = text.split("\n  continue-candidate-pr-head:\n", 1)[1]
        self.assertIn("contents: read", candidate)
        self.assertIn("actions: read", candidate)
        self.assertNotIn(": write", candidate)
        self.assertNotIn("--method POST", candidate)
        self.assertNotIn("ref: main", candidate)
        self.assertIn("ref: ${{ env.EXPECTED_HEAD }}", candidate)
        self.assertIn("READ_ONLY_CANDIDATE_CONTINUATION", candidate)
        self.assertIn("/attempts/${GITHUB_RUN_ATTEMPT}/jobs", candidate)
        self.assertIn(".started_at != null", candidate)
        self.assertIn('test "$live" = "$EXPECTED_HEAD"', candidate)
        self.assertIn("productive_effect:false", candidate)

if __name__ == '__main__':
    unittest.main()
