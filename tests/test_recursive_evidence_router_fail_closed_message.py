import unittest

from src.qikvrt.recursive_evidence_router import NoAdmissibleRoute, RecursiveEvidenceRouter, Subject


class CausalBlockerTest(unittest.TestCase):
    def test_unreachable_error_identifies_scope(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        with self.assertRaisesRegex(NoAdmissibleRoute, "scope='wanted'"):
            RecursiveEvidenceRouter().candidate_route(a, b, "wanted")


if __name__ == "__main__":
    unittest.main()
