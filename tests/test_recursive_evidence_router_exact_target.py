import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ExactTargetTest(unittest.TestCase):
    def test_same_node_name_with_different_tree_is_different_target(self):
        a = Subject("A", "ha", "ta")
        b1 = Subject("B", "hb", "tree-1")
        b2 = Subject("B", "hb", "tree-2")
        edge = EvidenceEdge(a, b1, "x", ("AB",), "now", Validity.VALID, "p")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([edge]).candidate_route(a, b2, "x")


if __name__ == "__main__":
    unittest.main()
