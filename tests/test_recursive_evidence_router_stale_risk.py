import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class StaleRiskTest(unittest.TestCase):
    def test_stale_risk_score_does_not_label_evidence_stale(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", stale_risk=999)
        self.assertEqual(Validity.VALID, edge.validity)
        self.assertEqual(999, edge.stale_risk)


if __name__ == "__main__":
    unittest.main()
