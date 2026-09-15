import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class EdgeScopeReceiptTest(unittest.TestCase):
    def test_validated_path_keeps_edge_scope(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        receipt = RecursiveEvidenceRouter([edge]).traverse(a, b, "x", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual("x", receipt.path[0].scope)


if __name__ == "__main__":
    unittest.main()
