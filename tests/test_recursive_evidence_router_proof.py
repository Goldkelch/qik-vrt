import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ProofLivenessTest(unittest.TestCase):
    def test_cached_proof_is_not_fresh_proof(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "cached-proof")
        router = RecursiveEvidenceRouter([edge])
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, b, "x", reobserve=lambda e: e, validate=lambda _: False)


if __name__ == "__main__":
    unittest.main()
