import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class LearnReturnTest(unittest.TestCase):
    def test_learning_is_history_update_not_effect_ack(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        router = RecursiveEvidenceRouter()
        self.assertIsNone(router.learn([edge]))
        self.assertEqual([edge], router.edges)


if __name__ == "__main__":
    unittest.main()
