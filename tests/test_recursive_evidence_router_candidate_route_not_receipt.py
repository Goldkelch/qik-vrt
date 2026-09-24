import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, RouteReceipt, Subject, Validity


class CandidateTypeTest(unittest.TestCase):
    def test_candidate_is_plain_edge_path_not_validated_receipt(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        candidate = RecursiveEvidenceRouter([edge]).candidate_route(a, b, "x")
        self.assertIsInstance(candidate, tuple)
        self.assertNotIsInstance(candidate, RouteReceipt)


if __name__ == "__main__":
    unittest.main()
