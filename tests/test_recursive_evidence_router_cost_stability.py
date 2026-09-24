import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class CostEvidenceSeparationTest(unittest.TestCase):
    def test_cost_does_not_change_evidence_validity(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cheap = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", latency=1)
        expensive = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", latency=100)
        self.assertEqual(Validity.VALID, cheap.validity)
        self.assertEqual(Validity.VALID, expensive.validity)


if __name__ == "__main__":
    unittest.main()
