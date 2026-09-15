import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class CostDomainTest(unittest.TestCase):
    def test_default_cost_components_are_non_negative(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        self.assertGreaterEqual(edge.latency, 0)
        self.assertGreaterEqual(edge.computation, 0)
        self.assertGreaterEqual(edge.stale_risk, 0)


if __name__ == "__main__":
    unittest.main()
