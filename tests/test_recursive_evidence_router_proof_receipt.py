import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ProofReceiptTest(unittest.TestCase):
    def test_missing_proof_receipt_can_fail_admission(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "proof-required", ("AB",), "now", Validity.VALID, None)
        router = RecursiveEvidenceRouter([edge])
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, b, "proof-required", reobserve=lambda e: e, validate=lambda e: e.proof_receipt is not None)


if __name__ == "__main__":
    unittest.main()
