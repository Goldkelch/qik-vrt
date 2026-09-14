# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import unittest

from tools.qikvrt_requested_review_stale_work_unit_reaper import classify_run


HEAD = "a" * 40
MAIN = "b" * 40
FP = "c" * 64


def run(event="workflow_dispatch", status="pending", head=HEAD):
    return {
        "event": event,
        "status": status,
        "display_title": f"QIKVRT requested review pr=922 head={head} fp={FP}",
    }


def pr(head=HEAD, base=MAIN, state="open"):
    return {
        "number": 922,
        "state": state,
        "head": {"sha": head},
        "base": {"sha": base},
    }


class RequestedReviewStaleWorkUnitReaperTests(unittest.TestCase):
    def test_stale_head_recursive_child_is_cancelled(self):
        value = classify_run(run(), pr(head="d" * 40), MAIN)
        self.assertTrue(value["cancel"])
        self.assertEqual(value["first_blocker"], "STALE_HEAD")
        self.assertEqual(value["next_action"], "CANCEL_STALE_RECURSIVE_TRANSPORT_ONLY")

    def test_base_drift_recursive_child_is_cancelled(self):
        value = classify_run(run(), pr(base="e" * 40), MAIN)
        self.assertTrue(value["cancel"])
        self.assertEqual(value["first_blocker"], "BASE_DRIFT")
        self.assertEqual(value["next_action"], "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN")

    def test_current_recursive_child_is_kept(self):
        value = classify_run(run(), pr(), MAIN)
        self.assertFalse(value["cancel"])
        self.assertEqual(value["state"], "KEEP")

    def test_native_pr_observation_is_never_cancelled(self):
        value = classify_run(run(event="pull_request_target"), pr(base="e" * 40), MAIN)
        self.assertFalse(value["cancel"])
        self.assertEqual(value["state"], "KEEP")

    def test_unbound_title_fails_closed_without_cancellation(self):
        candidate = run()
        candidate["display_title"] = "unbound"
        value = classify_run(candidate, pr(), MAIN)
        self.assertFalse(value["cancel"])
        self.assertEqual(value["first_blocker"], "RECURSIVE_WORK_UNIT_TITLE_UNBOUND")


if __name__ == "__main__":
    unittest.main()
