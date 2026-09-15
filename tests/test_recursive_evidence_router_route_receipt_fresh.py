import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class FreshReceiptFlagTest(unittest.TestCase):
    def test_successful_traversal_marks_fresh_validation(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        receipt = RecursiveEvidenceRouter([edge]).traverse(a, b, "x", reobserve=lambda e: e, validate=lambda _: True)
        self.assertIs(receipt.freshly_validated, True)


if __name__ == "__main__":
    unittest.main()
