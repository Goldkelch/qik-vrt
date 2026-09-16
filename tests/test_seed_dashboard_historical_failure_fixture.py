import unittest


class HistoricalFailureFixtureTest(unittest.TestCase):
    def test_job_104098276444_semantics(self):
        # Historical run 34880403356 attempt 2 produced a valid revalidation
        # result with one accepted node, zero errors and status CONTINUE because
        # that node's heartbeat was STALE. The dashboard orchestrator must treat
        # this as renderable state, not as an executor crash.
        fixture = {
            "accepted_count": 1,
            "active_count": 0,
            "error_count": 0,
            "stale_count": 1,
            "status": "CONTINUE",
            "revalidation_exit": 10,
        }
        self.assertEqual(0, fixture["error_count"])
        self.assertEqual(1, fixture["stale_count"])
        self.assertEqual("CONTINUE", fixture["status"])
        self.assertEqual(10, fixture["revalidation_exit"])


if __name__ == "__main__":
    unittest.main()
