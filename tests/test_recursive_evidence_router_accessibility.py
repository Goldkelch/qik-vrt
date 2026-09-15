import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class AccessibilityTest(unittest.TestCase):
    def test_shortcut_receipt_keeps_underlying_chain_identifiers(self):
        a = Subject("A", "ha", "ta")
        c = Subject("C", "hc", "tc")
        shortcut = EvidenceEdge(a, c, "x", ("R-AB", "R-BC", "R-AC"), "now", Validity.VALID, "proof-ac")
        receipt = RecursiveEvidenceRouter([shortcut]).traverse(a, c, "x", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual(("R-AB", "R-BC", "R-AC"), receipt.provenance_chain)


if __name__ == "__main__":
    unittest.main()
