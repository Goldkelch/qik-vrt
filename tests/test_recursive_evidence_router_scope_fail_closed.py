import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class NoScopeWideningTest(unittest.TestCase):
    def test_related_scope_is_not_implicitly_widened(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "proof-status", ("AB",), "now", Validity.VALID, "p")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([edge]).candidate_route(a, b, "effect-status")


if __name__ == "__main__":
    unittest.main()
