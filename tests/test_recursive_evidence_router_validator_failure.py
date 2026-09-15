import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class ValidatorFailureTest(unittest.TestCase):
    def test_validator_false_is_never_success(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        with self.assertRaisesRegex(NoAdmissibleRoute, "validation failed"):
            RecursiveEvidenceRouter([edge]).traverse(a, b, "x", reobserve=lambda e: e, validate=lambda _: False)


if __name__ == "__main__":
    unittest.main()
