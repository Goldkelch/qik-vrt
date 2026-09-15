import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class SupersededHintTest(unittest.TestCase):
    def test_valid_label_with_superseded_by_is_not_candidate(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("R17", "R42"), "now", Validity.VALID, "proof", "R42")
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([edge]).candidate_route(a, b, "x")


if __name__ == "__main__":
    unittest.main()
