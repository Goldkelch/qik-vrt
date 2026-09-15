import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class TargetScopeTest(unittest.TestCase):
    def test_wrong_scope_direct_edge_cannot_answer_target_request(self):
        a = Subject("A", "ha", "ta")
        c = Subject("C", "hc", "tc")
        wrong = EvidenceEdge(a, c, "other", ("AC",), "now", Validity.VALID, "p")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([wrong]).candidate_route(a, c, "wanted")


if __name__ == "__main__":
    unittest.main()
