import unittest

from src.qikvrt.recursive_evidence_router import EvidenceEdge, NoAdmissibleRoute, RecursiveEvidenceRouter, Subject, Validity


class NoPredecessorShortcutTest(unittest.TestCase):
    def test_old_source_shortcut_does_not_apply_to_successor_source(self):
        old = Subject("A", "old", "tree-old")
        new = Subject("A", "new", "tree-new")
        c = Subject("C", "hc", "tc")
        shortcut = EvidenceEdge(old, c, "x", ("old-chain",), "t0", Validity.VALID, "old-proof", latency=1)
        with self.assertRaises(NoAdmissibleRoute):
            RecursiveEvidenceRouter([shortcut]).candidate_route(new, c, "x")


if __name__ == "__main__":
    unittest.main()
