import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, Subject, Validity


class ShorterNotStrongerTest(unittest.TestCase):
    def test_cost_has_no_evidence_strength_semantics(self):
        a = Subject("A", "ha", "ta")
        c = Subject("C", "hc", "tc")
        short = EvidenceEdge(a, c, "x", ("short",), "now", Validity.VALID, "p", latency=1)
        long = EvidenceEdge(a, c, "x", ("long",), "now", Validity.VALID, "p", latency=100)
        self.assertEqual(short.validity, long.validity)
        self.assertNotEqual(short.latency, long.latency)


if __name__ == "__main__":
    unittest.main()
