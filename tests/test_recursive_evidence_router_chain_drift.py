import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ChainDriftTest(unittest.TestCase):
    def test_intermediate_subject_must_equal_previous_fresh_target(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        cached_ab = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        cached_bc = EvidenceEdge(b, c, "x", ("BC",), "t0", Validity.VALID, "p")
        router = RecursiveEvidenceRouter([cached_ab, cached_bc])
        moved_b = Subject("B", "hb2", "tb2")
        fresh_ab = EvidenceEdge(a, moved_b, "x", ("AB2",), "t1", Validity.VALID, "p2")
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, c, "x", reobserve=lambda e: fresh_ab if e is cached_ab else e, validate=lambda _: True)


if __name__ == "__main__":
    unittest.main()
