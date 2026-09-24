import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ExplicitScopeTest(unittest.TestCase):
    def test_scope_is_part_of_edge_value(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        x = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        y = EvidenceEdge(a, b, "y", ("AB",), "now", Validity.VALID, "p")
        self.assertNotEqual(x, y)
        router = RecursiveEvidenceRouter([x, y])
        self.assertEqual((x,), router.candidate_route(a, b, "x"))
        self.assertEqual((y,), router.candidate_route(a, b, "y"))


if __name__ == "__main__":
    unittest.main()
