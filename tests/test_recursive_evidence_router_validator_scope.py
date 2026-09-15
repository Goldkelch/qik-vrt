import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ScopePolicyTest(unittest.TestCase):
    def test_scope_specific_validator_can_reject_edge(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "strict", ("AB",), "now", Validity.VALID, "weak-proof")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([edge]).traverse(a, b, "strict", reobserve=lambda e: e, validate=lambda e: e.proof_receipt == "strong-proof")


if __name__ == "__main__":
    unittest.main()
