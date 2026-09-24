import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ValidateAllEdgesTest(unittest.TestCase):
    def test_one_invalid_edge_rejects_whole_route(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p1")
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p2")
        router = RecursiveEvidenceRouter([ab, bc])
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, c, "x", reobserve=lambda e: e, validate=lambda e: e.proof_receipt == "p1")


if __name__ == "__main__":
    unittest.main()
