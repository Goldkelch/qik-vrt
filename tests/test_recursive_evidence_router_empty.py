import unittest

from src.qikvrt.recursive_evidence_router import RecursiveEvidenceRouter, Subject


class EmptyRouteTest(unittest.TestCase):
    def test_same_exact_subject_has_zero_hop_candidate(self):
        a = Subject("A", "ha", "ta")
        router = RecursiveEvidenceRouter([])
        self.assertEqual((), router.candidate_route(a, a, "x"))


if __name__ == "__main__":
    unittest.main()
