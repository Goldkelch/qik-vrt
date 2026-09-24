import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class FreshValidTest(unittest.TestCase):
    def test_fresh_exact_valid_edge_is_admissible(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("cached",), "t0", Validity.VALID, "p0")
        fresh = EvidenceEdge(a, b, "x", ("fresh",), "t1", Validity.VALID, "p1")
        receipt = RecursiveEvidenceRouter([cached]).traverse(a, b, "x", reobserve=lambda _: fresh, validate=lambda e: e.proof_receipt == "p1")
        self.assertEqual((fresh,), receipt.path)
        self.assertEqual(("fresh",), receipt.provenance_chain)


if __name__ == "__main__":
    unittest.main()
