import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class TraversalOrderTest(unittest.TestCase):
    def test_receipt_provenance_follows_actual_route_order(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("first",), "now", Validity.VALID, "p")
        bc = EvidenceEdge(b, c, "x", ("second",), "now", Validity.VALID, "p")
        receipt = RecursiveEvidenceRouter([bc, ab]).traverse(a, c, "x", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual(("first", "second"), receipt.provenance_chain)


if __name__ == "__main__":
    unittest.main()
