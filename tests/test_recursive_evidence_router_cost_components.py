import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class CostComponentsTest(unittest.TestCase):
    def test_high_stale_risk_can_make_short_route_worse(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        risky = EvidenceEdge(a, c, "x", ("AC",), "now", Validity.VALID, "p", latency=1, computation=1, stale_risk=100)
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", latency=2, computation=1, stale_risk=0)
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p", latency=2, computation=1, stale_risk=0)
        self.assertEqual((ab, bc), RecursiveEvidenceRouter([risky, ab, bc]).candidate_route(a, c, "x"))


if __name__ == "__main__":
    unittest.main()
