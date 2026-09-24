import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class DuplicateHistoryTest(unittest.TestCase):
    def test_append_only_history_can_contain_repeated_observations(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        first = EvidenceEdge(a, b, "x", ("R1",), "t0", Validity.VALID, "p")
        second = EvidenceEdge(a, b, "x", ("R2",), "t1", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([first])
        router.learn([second])
        self.assertEqual([first, second], router.edges)


if __name__ == "__main__":
    unittest.main()
