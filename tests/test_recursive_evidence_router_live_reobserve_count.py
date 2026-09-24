import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class MinimalTraversalTest(unittest.TestCase):
    def test_only_selected_route_edges_are_reobserved(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        cheap = EvidenceEdge(a, c, "x", ("AC",), "now", Validity.VALID, "p", latency=1)
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", latency=10)
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p", latency=10)
        calls = []
        RecursiveEvidenceRouter([cheap, ab, bc]).traverse(
            a, c, "x", reobserve=lambda e: (calls.append(e.provenance[0]) or e), validate=lambda _: True
        )
        self.assertEqual(["AC"], calls)


if __name__ == "__main__":
    unittest.main()
