import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class CycleTest(unittest.TestCase):
    def test_cycle_does_not_prevent_minimal_route(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        ba = EvidenceEdge(b, a, "x", ("BA",), "now", Validity.VALID, "p")
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([ab, ba, bc])
        self.assertEqual((ab, bc), router.candidate_route(a, c, "x"))


if __name__ == "__main__":
    unittest.main()
