import unittest

from src.qikvrt.recursive_evidence_router import (
    EvidenceEdge,
    NoAdmissibleRoute,
    RecursiveEvidenceRouter,
    Subject,
    Validity,
)


class RecursiveEvidenceRouterTest(unittest.TestCase):
    def setUp(self):
        self.a = Subject("A", "ha", "ta")
        self.b = Subject("B", "hb", "tb")
        self.c = Subject("C", "hc", "tc")

    def edge(self, source, target, validity=Validity.VALID, receipt="proof", superseded_by=None):
        return EvidenceEdge(source, target, "x", (f"{source.node}->{target.node}",), "now", validity, receipt, superseded_by)

    def test_two_edges_create_candidate_not_transferred_evidence(self):
        router = RecursiveEvidenceRouter([self.edge(self.a, self.b), self.edge(self.b, self.c)])
        route = router.candidate_route(self.a, self.c, "x")
        self.assertEqual(2, len(route))
        self.assertFalse(any(e.source == self.a and e.target == self.c for e in router.edges))

    def test_every_edge_is_freshly_reobserved(self):
        router = RecursiveEvidenceRouter([self.edge(self.a, self.b), self.edge(self.b, self.c)])
        seen = []
        receipt = router.traverse(
            self.a, self.c, "x",
            reobserve=lambda e: (seen.append((e.source.node, e.target.node)) or e),
            validate=lambda e: e.proof_receipt == "proof",
        )
        self.assertEqual([("A", "B"), ("B", "C")], seen)
        self.assertTrue(receipt.freshly_validated)
        self.assertEqual(("A->B", "B->C"), receipt.provenance_chain)

    def test_stale_reobservation_fails_closed(self):
        first = self.edge(self.a, self.b)
        router = RecursiveEvidenceRouter([first])
        stale = self.edge(self.a, self.b, Validity.STALE)
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(self.a, self.b, "x", reobserve=lambda _: stale, validate=lambda _: True)

    def test_exact_subject_drift_fails_closed(self):
        edge = self.edge(self.a, self.b)
        router = RecursiveEvidenceRouter([edge])
        moved_b = Subject("B", "new-head", "new-tree")
        drifted = self.edge(self.a, moved_b)
        with self.assertRaises(NoAdmissibleRoute):
            router.traverse(self.a, self.b, "x", reobserve=lambda _: drifted, validate=lambda _: True)

    def test_history_is_append_only_and_supersession_is_new_evidence(self):
        historical = self.edge(self.a, self.b)
        router = RecursiveEvidenceRouter([historical])
        supersession = self.edge(self.a, self.b, Validity.SUPERSEDED, superseded_by="R42")
        router.learn([supersession])
        self.assertEqual(2, len(router.edges))
        self.assertEqual(Validity.VALID, router.edges[0].validity)
        self.assertEqual(Validity.SUPERSEDED, router.edges[1].validity)
        self.assertEqual("R42", router.edges[1].superseded_by)


if __name__ == "__main__":
    unittest.main()
