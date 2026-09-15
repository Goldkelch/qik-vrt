import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class LearningOrderTest(unittest.TestCase):
    def test_delta_evidence_is_appended_in_observed_order(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("R1",), "t1", Validity.VALID, "p1")
        bc = EvidenceEdge(b, c, "x", ("R2",), "t2", Validity.VALID, "p2")
        router = RecursiveEvidenceRouter()
        router.learn([ab, bc])
        self.assertEqual([ab, bc], router.edges)


if __name__ == "__main__":
    unittest.main()
