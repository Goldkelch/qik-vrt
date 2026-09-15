import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ScopeTest(unittest.TestCase):
    def test_evidence_scope_is_not_silently_widened(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "narrow", ("AB",), "now", Validity.VALID, "proof")
        router = RecursiveEvidenceRouter([edge])
        with self.assertRaises(NoAdmissibleRoute):
            router.candidate_route(a, b, "broad", )


if __name__ == "__main__":
    unittest.main()
