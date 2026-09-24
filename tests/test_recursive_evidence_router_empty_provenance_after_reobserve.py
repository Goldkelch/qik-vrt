import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class FreshProvenanceTest(unittest.TestCase):
    def test_fresh_edge_without_provenance_fails_validation(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        fresh = EvidenceEdge(a, b, "x", (), "t1", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([cached])
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, b, "x", reobserve=lambda _: fresh, validate=lambda e: bool(e.provenance))


if __name__ == "__main__":
    unittest.main()
