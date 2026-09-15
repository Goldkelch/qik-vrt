import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class UnknownEdgeTest(unittest.TestCase):
    def test_unknown_edge_is_not_candidate_shortcut(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        unknown = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.UNKNOWN, "proof")
        router = RecursiveEvidenceRouter([unknown])
        with self.assertRaises(NoAdmissibleRoute):
            router.candidate_route(a, b, "x")


if __name__ == "__main__":
    unittest.main()
