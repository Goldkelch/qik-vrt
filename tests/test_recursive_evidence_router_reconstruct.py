import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ReconstructionTest(unittest.TestCase):
    def test_route_receipt_preserves_complete_provenance_chain(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("R1", "R2"), "now", Validity.VALID, "p1")
        bc = EvidenceEdge(b, c, "x", ("R3",), "now", Validity.VALID, "p2")
        receipt = RecursiveEvidenceRouter([ab, bc]).traverse(
            a, c, "x", reobserve=lambda e: e, validate=lambda _: True
        )
        self.assertEqual(("R1", "R2", "R3"), receipt.provenance_chain)
        self.assertEqual((ab, bc), receipt.path)


if __name__ == "__main__":
    unittest.main()
