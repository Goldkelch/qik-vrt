import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class FinalTargetDriftTest(unittest.TestCase):
    def test_last_fresh_target_must_equal_requested_exact_target(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        moved_c = Subject("C", "hc2", "tc2")
        ab = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        bc = EvidenceEdge(b, c, "x", ("BC",), "t0", Validity.VALID, "p")
        fresh_bc = EvidenceEdge(b, moved_c, "x", ("BC2",), "t1", Validity.VALID, "p2")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([ab, bc]).traverse(a, c, "x", reobserve=lambda e: fresh_bc if e is bc else e, validate=lambda _: True)


if __name__ == "__main__":
    unittest.main()
