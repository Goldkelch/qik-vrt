import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ReciprocalPairTest(unittest.TestCase):
    def test_independent_ab_and_ba_relations_are_both_routable(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p-ab")
        ba = EvidenceEdge(b, a, "x", ("BA",), "now", Validity.VALID, "p-ba")
        router = RecursiveEvidenceRouter([ab, ba])
        self.assertEqual((ab,), router.candidate_route(a, b, "x"))
        self.assertEqual((ba,), router.candidate_route(b, a, "x"))


if __name__ == "__main__":
    unittest.main()
