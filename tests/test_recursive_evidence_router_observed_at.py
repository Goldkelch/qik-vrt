import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ObservationIdentityTest(unittest.TestCase):
    def test_route_receipt_preserves_fresh_observation_objects(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        cached = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "proof")
        fresh = EvidenceEdge(a, b, "x", ("AB", "fresh"), "t1", Validity.VALID, "proof-fresh")
        receipt = RecursiveEvidenceRouter([cached]).traverse(
            a, b, "x", reobserve=lambda _: fresh, validate=lambda e: e.observed_at == "t1"
        )
        self.assertEqual("t1", receipt.path[0].observed_at)
        self.assertEqual("proof-fresh", receipt.path[0].proof_receipt)


if __name__ == "__main__":
    unittest.main()
