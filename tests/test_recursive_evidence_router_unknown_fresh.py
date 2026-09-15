import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class FreshUnknownTest(unittest.TestCase):
    def test_cached_valid_edge_fails_when_live_state_is_unknown(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p")
        unknown = EvidenceEdge(a, b, "x", ("AB",), "t1", Validity.UNKNOWN, "p")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([cached]).traverse(a, b, "x", reobserve=lambda _: unknown, validate=lambda _: True)


if __name__ == "__main__":
    unittest.main()
