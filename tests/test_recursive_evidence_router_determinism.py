import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class DeterminismTest(unittest.TestCase):
    def test_same_graph_order_produces_same_route(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p")
        direct = EvidenceEdge(a, c, "x", ("AC",), "now", Validity.VALID, "p", latency=10)
        edges = [ab, bc, direct]
        self.assertEqual(
            RecursiveEvidenceRouter(edges.copy()).candidate_route(a, c, "x"),
            RecursiveEvidenceRouter(edges.copy()).candidate_route(a, c, "x"),
        )


if __name__ == "__main__":
    unittest.main()
