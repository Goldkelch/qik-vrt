import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ReobserveAllTest(unittest.TestCase):
    def test_three_hop_route_reobserves_three_edges(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        d = Subject("D", "hd", "td")
        edges = [
            EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p"),
            EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p"),
            EvidenceEdge(c, d, "x", ("CD",), "now", Validity.VALID, "p"),
        ]
        seen = []
        RecursiveEvidenceRouter(edges).traverse(a, d, "x", reobserve=lambda e: (seen.append(e) or e), validate=lambda _: True)
        self.assertEqual(edges, seen)


if __name__ == "__main__":
    unittest.main()
