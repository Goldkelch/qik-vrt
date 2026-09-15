import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class ScopeIdentityTest(unittest.TestCase):
    def test_same_relation_different_scope_is_distinct_evidence_object(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        x = EvidenceEdge(a, b, "x", ("R",), "now", Validity.VALID, "p")
        y = EvidenceEdge(a, b, "y", ("R",), "now", Validity.VALID, "p")
        self.assertNotEqual(x, y)


if __name__ == "__main__":
    unittest.main()
