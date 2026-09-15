import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, RouteReceipt, Subject, Validity


class SuccessEffectBoundaryTest(unittest.TestCase):
    def test_route_success_has_only_evidence_receipt_semantics(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        result = RecursiveEvidenceRouter([edge]).traverse(a, b, "x", reobserve=lambda e: e, validate=lambda _: True)
        self.assertIsInstance(result, RouteReceipt)
        self.assertFalse(hasattr(result, "effect"))


if __name__ == "__main__":
    unittest.main()
