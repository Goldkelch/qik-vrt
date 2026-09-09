import unittest

from tools.qikvrt_hold_not_deadlock import classify_queue


class HoldNotDeadlockTests(unittest.TestCase):
    def test_exact_bound_pending_run_is_never_cancelled(self):
        result = classify_queue([
            {"id": 10, "run_number": 7, "status": "pending", "display_title": "QIKVRT requested review pr=1047 head=abc fp=def", "pull_requests": [{"number": 1047}]},
        ])
        self.assertEqual(result["state"], "NOOP")
        self.assertEqual(result["protected_exact_run_ids"], [10])

    def test_oldest_generic_pending_run_is_selected_once(self):
        result = classify_queue([
            {"id": 12, "run_number": 9, "status": "pending", "display_title": "QIKVRT requested review pr=event head=event fp=event", "pull_requests": []},
            {"id": 11, "run_number": 8, "status": "queued", "display_title": "QIKVRT requested review pr=event head=event fp=event", "pull_requests": []},
            {"id": 20, "run_number": 10, "status": "pending", "display_title": "QIKVRT requested review pr=1047 head=abc fp=def", "pull_requests": [{"number": 1047}]},
        ])
        self.assertEqual(result["state"], "CANCEL_ONE_STALE_GENERIC")
        self.assertEqual(result["cancel_run_id"], 11)
        self.assertEqual(result["stale_generic_count"], 2)
        self.assertEqual(result["protected_exact_run_ids"], [20])

    def test_completed_generic_run_does_not_own_queue(self):
        result = classify_queue([
            {"id": 13, "run_number": 9, "status": "completed", "display_title": "QIKVRT requested review pr=event head=event fp=event", "pull_requests": []},
        ])
        self.assertEqual(result["state"], "NOOP")


if __name__ == "__main__":
    unittest.main()
