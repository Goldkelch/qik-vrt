import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class FreshProvenanceReceiptTest(unittest.TestCase):
    def test_cached_provenance_is_replaced_by_fresh_readback_in_receipt(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("old",), "t0", Validity.VALID, "p0")
        fresh = EvidenceEdge(a, b, "x", ("new",), "t1", Validity.VALID, "p1")
        receipt = RecursiveEvidenceRouter([cached]).traverse(a, b, "x", reobserve=lambda _: fresh, validate=lambda _: True)
        self.assertEqual(("new",), receipt.provenance_chain)


if __name__ == "__main__":
    unittest.main()
