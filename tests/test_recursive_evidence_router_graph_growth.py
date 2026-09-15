import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class GraphGrowthTest(unittest.TestCase):
    def test_learning_only_increases_history_length(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        router = RecursiveEvidenceRouter()
        before = len(router.edges)
        router.learn([edge])
        self.assertGreaterEqual(len(router.edges), before)


if __name__ == "__main__":
    unittest.main()
