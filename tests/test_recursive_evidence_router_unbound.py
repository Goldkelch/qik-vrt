import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class UnboundEdgeTest(unittest.TestCase):
    def test_missing_exact_subject_binding_is_not_routable(self):
        a = Subject("A", "", "")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "proof")
        router = RecursiveEvidenceRouter([edge])
        with self.assertRaises(NoAdmissibleRoute):
            router.candidate_route(a, b, "x")


if __name__ == "__main__":
    unittest.main()
