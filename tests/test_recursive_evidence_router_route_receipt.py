import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class RouteReceiptTest(unittest.TestCase):
    def test_receipt_binds_requested_scope(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "scope-1", ("AB",), "now", Validity.VALID, "p")
        receipt = RecursiveEvidenceRouter([edge]).traverse(a, b, "scope-1", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual("scope-1", receipt.requested_scope)


if __name__ == "__main__":
    unittest.main()
