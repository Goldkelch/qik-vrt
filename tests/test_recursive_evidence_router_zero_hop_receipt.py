import unittest

from src.qikvrt.recursive_evidence_router import RecursiveEvidenceRouter, Subject


class ZeroHopReceiptTest(unittest.TestCase):
    def test_zero_hop_traversal_is_route_receipt_only(self):
        a = Subject("A", "ha", "ta")
        receipt = RecursiveEvidenceRouter().traverse(a, a, "x", reobserve=lambda e: e, validate=lambda e: True)
        self.assertEqual((), receipt.path)
        self.assertTrue(receipt.freshly_validated)
        self.assertFalse(hasattr(receipt, "effect_ack_done"))


if __name__ == "__main__":
    unittest.main()
