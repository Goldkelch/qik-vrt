import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ExplicitLearningTest(unittest.TestCase):
    def test_traversal_does_not_mutate_evidence_history_implicitly(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([edge])
        before = list(router.edges)
        router.traverse(a, b, "x", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual(before, router.edges)


if __name__ == "__main__":
    unittest.main()
