import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class LearningTest(unittest.TestCase):
    def test_learning_changes_discovery_not_validation_requirement(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "proof")
        router = RecursiveEvidenceRouter()
        router.learn([edge])
        calls = []
        router.traverse(a, b, "x", reobserve=lambda e: (calls.append("reobserve") or e), validate=lambda e: (calls.append("validate") or True))
        self.assertEqual(["reobserve", "validate"], calls)


if __name__ == "__main__":
    unittest.main()
