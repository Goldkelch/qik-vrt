import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ScopeChainTest(unittest.TestCase):
    def test_mixed_scope_edges_do_not_form_route(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        bc = EvidenceEdge(b, c, "y", ("BC",), "now", Validity.VALID, "p")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([ab, bc]).candidate_route(a, c, "x")


if __name__ == "__main__":
    unittest.main()
