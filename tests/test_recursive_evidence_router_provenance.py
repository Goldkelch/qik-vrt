import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ProvenanceTest(unittest.TestCase):
    def test_provenance_free_edge_is_not_routable(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", (), "now", Validity.VALID, "proof")
        router = RecursiveEvidenceRouter([edge])
        with self.assertRaises(NoAdmissibleRoute):
            router.candidate_route(a, b, "x")


if __name__ == "__main__":
    unittest.main()
