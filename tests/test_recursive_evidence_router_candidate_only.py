import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class CandidatePurityTest(unittest.TestCase):
    def test_candidate_discovery_does_not_change_evidence_history(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([edge])
        before = tuple(router.edges)
        router.candidate_route(a, b, "x")
        self.assertEqual(before, tuple(router.edges))


if __name__ == "__main__":
    unittest.main()
