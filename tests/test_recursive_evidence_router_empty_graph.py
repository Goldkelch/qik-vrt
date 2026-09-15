import unittest

from src.qikvrt.recursive_evidence_router import NoAdmissibleRoute, RecursiveEvidenceRouter, Subject


class EmptyGraphTest(unittest.TestCase):
    def test_distinct_unreachable_subject_fails_closed(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter().candidate_route(a, b, "x")


if __name__ == "__main__":
    unittest.main()
