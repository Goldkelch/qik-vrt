import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ReciprocityTest(unittest.TestCase):
    def test_a_to_b_does_not_imply_b_to_a(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "proof")
        router = RecursiveEvidenceRouter([ab])
        self.assertEqual((ab,), router.candidate_route(a, b, "x"))
        with self.assertRaises(NoAdmissibleRoute):
            router.candidate_route(b, a, "x")


if __name__ == "__main__":
    unittest.main()
