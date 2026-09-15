import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class StaleHistoryAdmissionTest(unittest.TestCase):
    def test_cached_valid_history_cannot_override_fresh_supersession(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        historical = EvidenceEdge(a, b, "x", ("R17",), "t0", Validity.VALID, "proof-R17")
        router = RecursiveEvidenceRouter([historical])
        freshly_superseded = EvidenceEdge(a, b, "x", ("R17", "R42"), "t1", Validity.SUPERSEDED, "proof-R17", "R42")
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, b, "x", reobserve=lambda _: freshly_superseded, validate=lambda _: True)


if __name__ == "__main__":
    unittest.main()
