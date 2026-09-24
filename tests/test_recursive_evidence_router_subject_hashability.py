import unittest

from src.qikvrt.recursive_evidence_router import Subject


class SubjectIdentityTest(unittest.TestCase):
    def test_head_tree_are_part_of_graph_identity(self):
        old = Subject("A", "h1", "t1")
        new = Subject("A", "h2", "t2")
        self.assertNotEqual(old, new)
        self.assertEqual(2, len({old, new}))


if __name__ == "__main__":
    unittest.main()
