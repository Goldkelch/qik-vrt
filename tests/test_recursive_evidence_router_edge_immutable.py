import dataclasses
import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class EdgeImmutabilityTest(unittest.TestCase):
    def test_evidence_edge_is_frozen(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        edge = EvidenceEdge(a, b, "x", ("AB",), "now", Validity.VALID, "p")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            edge.validity = Validity.STALE


if __name__ == "__main__":
    unittest.main()
