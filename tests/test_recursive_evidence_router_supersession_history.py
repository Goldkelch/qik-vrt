import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class SupersessionHistoryTest(unittest.TestCase):
    def test_supersession_appends_relation_instead_of_mutating_old_edge(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        old = EvidenceEdge(a, b, "x", ("R17",), "t0", Validity.VALID, "p17")
        router = RecursiveEvidenceRouter([old])
        router.learn([EvidenceEdge(a, b, "x", ("R17", "R42"), "t1", Validity.SUPERSEDED, "p17", "R42")])
        self.assertIs(router.edges[0], old)
        self.assertIsNone(old.superseded_by)
        self.assertEqual("R42", router.edges[1].superseded_by)


if __name__ == "__main__":
    unittest.main()
