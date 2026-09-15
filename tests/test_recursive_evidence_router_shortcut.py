import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, RecursiveEvidenceRouter, Subject, Validity


class ShortcutTest(unittest.TestCase):
    def test_independently_evidenced_shortcut_can_win_without_deleting_chain(self):
        a = Subject("A", "ha", "ta")
        b = Subject("B", "hb", "tb")
        c = Subject("C", "hc", "tc")
        ab = EvidenceEdge(a, b, "x", ("AB",), "t0", Validity.VALID, "p", latency=3)
        bc = EvidenceEdge(b, c, "x", ("BC",), "t0", Validity.VALID, "p", latency=3)
        shortcut = EvidenceEdge(a, c, "x", ("AB", "BC", "AC-validation"), "t1", Validity.VALID, "p-ac", latency=1)
        router = RecursiveEvidenceRouter([ab, bc, shortcut])
        self.assertEqual((shortcut,), router.candidate_route(a, c, "x"))
        self.assertIn(ab, router.edges)
        self.assertIn(bc, router.edges)


if __name__ == "__main__":
    unittest.main()
