import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class DeltaEvidenceTest(unittest.TestCase):
    def test_better_route_is_added_without_destroying_old_route(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        old = EvidenceEdge(a, c, "x", ("AC-old",), "t0", Validity.VALID, "p", latency=10)
        ab = EvidenceEdge(a, b, "x", ("AB",), "t1", Validity.VALID, "p", latency=1)
        bc = EvidenceEdge(b, c, "x", ("BC",), "t1", Validity.VALID, "p", latency=1)
        router = RecursiveEvidenceRouter([old])
        router.learn([ab, bc])
        self.assertIn(old, router.edges)
        self.assertEqual((ab, bc), router.candidate_route(a, c, "x"))


if __name__ == "__main__":
    unittest.main()
