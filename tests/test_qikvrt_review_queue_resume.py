import unittest

from tools.qikvrt_review_queue_resume import (
    QueueResumeError,
    classify_existing_queue_ack,
)


REPO = "Goldkelch/qik-vrt"
HEAD = "d" * 40
PREDECESSOR = "4" * 64
SUCCESSOR = "5" * 64


def acknowledgement(**updates):
    value = {
        "schema": "qikvrt_mesh_review_queue_ack_v1",
        "state": "SUPERSEDED_BY_CAUSAL_REOBSERVATION",
        "repository": REPO,
        "pr_number": 1060,
        "head_sha": HEAD,
        "predecessor_fingerprint": PREDECESSOR,
        "successor_fingerprint": SUCCESSOR,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }
    value.update(updates)
    return value


class ReviewQueueResumeTests(unittest.TestCase):
    def classify(self, value):
        return classify_existing_queue_ack(
            value,
            repository=REPO,
            pr_number=1060,
            head_sha=HEAD,
            predecessor_fingerprint=PREDECESSOR,
        )

    def test_absent_ack_allows_normal_edge_creation(self):
        result = self.classify(None)
        self.assertEqual(result["state"], "ABSENT")
        self.assertIsNone(result["successor_fingerprint"])

    def test_existing_ack_resumes_instead_of_rewriting_predecessor(self):
        result = self.classify(acknowledgement())
        self.assertEqual(result["state"], "ALREADY_SUPERSEDED")
        self.assertEqual(result["predecessor_fingerprint"], PREDECESSOR)
        self.assertEqual(result["successor_fingerprint"], SUCCESSOR)

    def test_exact_subject_mismatch_fails_closed(self):
        cases = [
            acknowledgement(repository="other/qik-vrt"),
            acknowledgement(pr_number=1061),
            acknowledgement(head_sha="e" * 40),
            acknowledgement(predecessor_fingerprint="6" * 64),
        ]
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(QueueResumeError):
                    self.classify(value)

    def test_invalid_schema_state_or_completion_boundary_fails_closed(self):
        cases = [
            acknowledgement(schema="other"),
            acknowledgement(state="DONE"),
            acknowledgement(completion_claims={
                "PASS": True,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
                "MERGE": False,
            }),
        ]
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(QueueResumeError):
                    self.classify(value)

    def test_non_progressing_or_invalid_successor_fails_closed(self):
        for successor in (PREDECESSOR, "not-a-sha"):
            with self.subTest(successor=successor):
                with self.assertRaises(QueueResumeError):
                    self.classify(acknowledgement(successor_fingerprint=successor))


if __name__ == "__main__":
    unittest.main()
