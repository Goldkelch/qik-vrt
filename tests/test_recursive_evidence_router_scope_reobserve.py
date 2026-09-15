import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class FreshScopeTest(unittest.TestCase):
    def test_reobserved_edge_cannot_change_requested_scope(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        fresh = EvidenceEdge(a, b, "y", ("AB",), "t1", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([cached])
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, b, "x", reobserve=lambda _: fresh, validate=lambda e: e.scope == "x")


if __name__ == "__main__":
    unittest.main()
