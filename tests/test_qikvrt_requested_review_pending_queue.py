# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/qikvrt_requested_review_executor.yml")


class RequestedReviewPendingQueueTests(unittest.TestCase):
    def test_preserves_pending_exact_head_runs(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        expression = "$" + "{{ github.repository }}"
        block = (
            "concurrency:\n"
            f"  group: qikvrt-requested-review-executor-{expression}\n"
            "  cancel-in-progress: false\n"
            "  queue: max\n"
        )
        self.assertEqual(text.count(block), 1)
        obsolete = (
            f"group: qikvrt-requested-review-executor-{expression}\n"
            "  cancel-in-progress: false\n\n"
        )
        self.assertNotIn(obsolete, text)


if __name__ == "__main__":
    unittest.main()
