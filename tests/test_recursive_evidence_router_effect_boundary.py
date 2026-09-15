import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class EffectBoundaryTest(unittest.TestCase):
    def test_successful_traversal_returns_route_receipt_not_effect_ack(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "proof")
        receipt = RecursiveEvidenceRouter([edge]).traverse(
            a, b, "x", reobserve=lambda e: e, validate=lambda _: True
        )
        self.assertTrue(receipt.freshly_validated)
        self.assertFalse(hasattr(receipt, "effect_ack_done"))


if __name__ == "__main__":
    unittest.main()
