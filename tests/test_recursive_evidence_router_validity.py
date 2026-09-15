import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ValidityTest(unittest.TestCase):
    def test_only_valid_edges_are_candidate_routes(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        for state in (Validity.STALE, Validity.UNKNOWN, Validity.UNBOUND, Validity.SUPERSEDED):
            with self.subTest(state=state):
                edge = EvidenceEdge(a, b, "x", ("AB",), "now", state, "proof")
                with self.assertRaises(NoAdmissibleRoute):
                    RecursiveEvidenceRouter([edge]).candidate_route(a, b, "x")


if __name__ == "__main__":
    unittest.main()
