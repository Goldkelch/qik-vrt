import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class TargetBindingTest(unittest.TestCase):
    def test_target_head_tree_drift_is_not_predecessor_transfer(self):
        a = Subject("A", "ha", "ta")
        old_b = Subject("B", "old-head", "old-tree")
        new_b = Subject("B", "new-head", "new-tree")
        cached = EvidenceEdge(a, old_b, "x", ("AB",), "t0", Validity.VALID, "proof")
        fresh = EvidenceEdge(a, new_b, "x", ("AB-new",), "t1", Validity.VALID, "proof-new")
        router = RecursiveEvidenceRouter([cached])
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(a, old_b, "x", reobserve=lambda _: fresh, validate=lambda _: True)


if __name__ == "__main__":
    unittest.main()
