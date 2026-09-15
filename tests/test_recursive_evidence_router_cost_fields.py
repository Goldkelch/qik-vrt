import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class RoutingObjectiveFieldsTest(unittest.TestCase):
    def test_latency_computation_and_stale_risk_are_independent_fields(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", latency=2, computation=3, stale_risk=5)
        self.assertEqual((2, 3, 5), (edge.latency, edge.computation, edge.stale_risk))


if __name__ == "__main__":
    unittest.main()
