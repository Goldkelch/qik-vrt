import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class PredecessorTransferTest(unittest.TestCase):
    def test_old_head_evidence_cannot_answer_new_head_request(self):
        a_old = Subject("A", "old", "tree-old")
        a_new = Subject("A", "new", "tree-new")
        b = Subject("B", "hb", "tb")
        old_edge = EvidenceEdge(a_old, b, "x", ("old-receipt",), "t0", Validity.VALID, "old-proof")
        router = RecursiveEvidenceRouter([old_edge])
        with self.assertRaises(NoAdmissibleRoute):
            router.candidate_route(a_new, b, "x")


if __name__ == "__main__":
    unittest.main()
