import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class RoutingObjectiveTest(unittest.TestCase):
    def test_lower_total_cost_path_is_selected(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        direct = EvidenceEdge(a, c, "x", ("AC",), "now", Validity.VALID, "p", latency=20, computation=1, stale_risk=1)
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", latency=1, computation=1, stale_risk=0)
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p", latency=1, computation=1, stale_risk=0)
        router = RecursiveEvidenceRouter([direct, ab, bc])
        self.assertEqual((ab, bc), router.candidate_route(a, c, "x"))


if __name__ == "__main__":
    unittest.main()
