import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class NoSyntheticTransitivityTest(unittest.TestCase):
    def test_traversal_does_not_learn_transitive_edge_implicitly(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([ab, bc])
        router.traverse(a, c, "x", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual([ab, bc], router.edges)


if __name__ == "__main__":
    unittest.main()
