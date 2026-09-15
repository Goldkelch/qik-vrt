import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class DirectRecursiveTest(unittest.TestCase):
    def test_router_can_choose_direct_or_recursive_path_by_objective(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        direct = EvidenceEdge(a, c, "x", ("AC",), "now", Validity.VALID, "p", latency=50)
        ab = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p", latency=1)
        bc = EvidenceEdge(b, c, "x", ("BC",), "now", Validity.VALID, "p", latency=1)
        self.assertEqual((ab, bc), RecursiveEvidenceRouter([direct, ab, bc]).candidate_route(a, c, "x"))


if __name__ == "__main__":
    unittest.main()
