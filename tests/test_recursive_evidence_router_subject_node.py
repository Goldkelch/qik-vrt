import unittest

from src.qikvrt.recursive_evidence_router import Subject


class NodeIdentityTest(unittest.TestCase):
    def test_same_revision_on_different_nodes_is_distinct_subject(self):
        a = Subject("A", "h", "t")
        b = Subject("B", "h", "t")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
