import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ReachabilityAdmissionTest(unittest.TestCase):
    def test_reachable_cached_edge_can_still_fail_fresh_admission(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        self.assertEqual((cached,), RecursiveEvidenceRouter([cached]).candidate_route(a, b, "x"))
        stale = EvidenceEdge(a, b, "x", ("AB",), "t1", Validity.STALE, "p")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([cached]).traverse(a, b, "x", reobserve=lambda _: stale, validate=lambda _: True)


if __name__ == "__main__":
    unittest.main()
