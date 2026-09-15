import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class LiveStateTest(unittest.TestCase):
    def test_receipt_path_exposes_exact_source_and_target_subjects(self):
        a = Subject("Authority", "head-a", "tree-a")
        b = Subject("Mirror", "head-b", "tree-b")
        edge = EvidenceEdge(a, b, "state", ("receipt",), "now", Validity.VALID, "proof")
        receipt = RecursiveEvidenceRouter([edge]).traverse(a, b, "state", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual("head-a", receipt.path[0].source.head)
        self.assertEqual("tree-a", receipt.path[0].source.tree)
        self.assertEqual("head-b", receipt.path[0].target.head)
        self.assertEqual("tree-b", receipt.path[0].target.tree)


if __name__ == "__main__":
    unittest.main()
