import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ExactSourceTreeTest(unittest.TestCase):
    def test_same_head_with_different_tree_is_distinct_source(self):
        a1 = Subject("A", "h", "tree-1")
        a2 = Subject("A", "h", "tree-2")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a1, b, "x", ("AB",), "now", Validity.VALID, "p")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([edge]).candidate_route(a2, b, "x")


if __name__ == "__main__":
    unittest.main()
