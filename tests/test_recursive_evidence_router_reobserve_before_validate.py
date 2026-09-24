import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class OrderingTest(unittest.TestCase):
    def test_reobserve_precedes_validation(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        order = []
        RecursiveEvidenceRouter([edge]).traverse(
            a, b, "x",
            reobserve=lambda e: (order.append("reobserve") or e),
            validate=lambda e: (order.append("validate") or True),
        )
        self.assertEqual(["reobserve", "validate"], order)


if __name__ == "__main__":
    unittest.main()
