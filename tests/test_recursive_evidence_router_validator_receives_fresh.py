import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class FreshValidationTest(unittest.TestCase):
    def test_validator_receives_reobserved_edge(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("cached",), "t0", Validity.VALID, "p0")
        fresh = EvidenceEdge(a, b, "x", ("fresh",), "t1", Validity.VALID, "p1")
        seen = []
        RecursiveEvidenceRouter([cached]).traverse(a, b, "x", reobserve=lambda _: fresh, validate=lambda e: (seen.append(e) or True))
        self.assertEqual([fresh], seen)


if __name__ == "__main__":
    unittest.main()
