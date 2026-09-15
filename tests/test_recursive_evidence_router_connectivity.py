import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ConnectivityTest(unittest.TestCase):
    def test_neighbor_relation_remains_usable_without_external_cognition(self):
        local = Subject("repo-native", "h1", "t1")
        neighbor = Subject("neighbor-terminal", "h2", "t2")
        relation = EvidenceEdge(local, neighbor, "interop", ("neighbor-receipt",), "now", Validity.VALID, "proof")
        router = RecursiveEvidenceRouter([relation])
        receipt = router.traverse(local, neighbor, "interop", reobserve=lambda e: e, validate=lambda _: True)
        self.assertEqual((relation,), receipt.path)


if __name__ == "__main__":
    unittest.main()
