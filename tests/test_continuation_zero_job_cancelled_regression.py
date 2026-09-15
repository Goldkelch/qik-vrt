# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Permanent regression for CONTINUATION_CHAIN_DROPS_BEFORE_EXECUTION.

Real witness: QIKVRT autonomous PR-head continuation run 35035933030,
triggered for PR #1105 head 2c6ca7f74c9aeb278230ccdad52c1b344307514e,
concluded cancelled before GitHub created any job.
"""
from pathlib import Path
import unittest

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

if __name__ == '__main__':
    unittest.main()
