import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class ProvenanceValueTest(unittest.TestCase):
    def test_provenance_is_immutable_tuple(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("R1", "R2"), "now", Validity.VALID, "p")
        self.assertIsInstance(edge.provenance, tuple)
        self.assertEqual(("R1", "R2"), edge.provenance)


if __name__ == "__main__":
    unittest.main()
