import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class SourceBindingTest(unittest.TestCase):
    def test_fresh_source_must_match_requested_exact_source(self):
        a = Subject("A", "ha", "ta")
        moved_a = Subject("A", "ha2", "ta2")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        fresh = EvidenceEdge(moved_a, b, "x", ("AB2",), "t1", Validity.VALID, "p2")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([cached]).traverse(a, b, "x", reobserve=lambda _: fresh, validate=lambda _: True)


if __name__ == "__main__":
    unittest.main()
