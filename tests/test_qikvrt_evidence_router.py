import unittest

from tools.qikvrt_evidence_router import (
    CandidateRoute,
    Relation,
    best_admissible_route,
    candidate_route,
    evidence_transitive,
    validate_candidate,
)


class EvidenceRouterTest(unittest.TestCase):
    def relation(self, source, target, receipt, cost=1, **state):
        return Relation(
            source=source,
            target=target,
            receipt=receipt,
            exact_subject=f"{source}-{target}@exact",
            provenance=f"receipt://{receipt}",
            cost=cost,
            **state,
        )

    def test_routing_composes_but_evidence_never_does(self):
        ab = self.relation("A", "B", "ab")
        bc = self.relation("B", "C", "bc")
        candidate = candidate_route(ab, bc)
        self.assertEqual(candidate.nodes, ("A", "B", "C"))
        self.assertEqual(candidate.receipts, ("ab", "bc"))
        self.assertFalse(evidence_transitive(ab, bc))

    def test_fresh_observed_valid_proved_relations_are_admissible(self):
        state = dict(observed=True, valid=True, proved=True)
        ab = self.relation("A", "B", "ab", **state)
        bc = self.relation("B", "C", "bc", **state)
        route = validate_candidate(candidate_route(ab, bc), [ab, bc])
        self.assertEqual(route.exact_subjects, ("A-B@exact", "B-C@exact"))
        self.assertEqual(route.provenance, ("receipt://ab", "receipt://bc"))

    def test_stale_history_remains_addressable_but_not_admissible(self):
        ab = self.relation("A", "B", "ab", observed=True, valid=False, proved=True)
        bc = self.relation("B", "C", "bc", observed=True, valid=True, proved=True)
        with self.assertRaisesRegex(ValueError, "NOT_CURRENTLY_VALID"):
            validate_candidate(candidate_route(ab, bc), [ab, bc])
        self.assertEqual(ab.receipt, "ab")
        self.assertEqual(ab.provenance, "receipt://ab")

    def test_reachable_is_not_observed_or_proved(self):
        ab = self.relation("A", "B", "ab", valid=True, proved=True)
        bc = self.relation("B", "C", "bc", observed=True, valid=True, proved=True)
        with self.assertRaisesRegex(ValueError, "NOT_FRESHLY_OBSERVED"):
            validate_candidate(candidate_route(ab, bc), [ab, bc])

    def test_missing_proof_fails_closed(self):
        ab = self.relation("A", "B", "ab", observed=True, valid=True, proved=False)
        bc = self.relation("B", "C", "bc", observed=True, valid=True, proved=True)
        with self.assertRaisesRegex(ValueError, "NOT_PROVED"):
            validate_candidate(candidate_route(ab, bc), [ab, bc])

    def test_subject_drift_fails_closed(self):
        state = dict(observed=True, valid=True, proved=True)
        ab = self.relation("A", "B", "ab", **state)
        bc = self.relation("B", "C", "bc", **state)
        drifted = CandidateRoute(nodes=("A", "X", "C"), receipts=("ab", "bc"), cost=2)
        with self.assertRaisesRegex(ValueError, "SUBJECT_DRIFT"):
            validate_candidate(drifted, [ab, bc])

    def test_duplicate_receipt_identity_is_rejected(self):
        state = dict(observed=True, valid=True, proved=True)
        ab = self.relation("A", "B", "same", **state)
        bc = self.relation("B", "C", "same", **state)
        candidate = CandidateRoute(nodes=("A", "B", "C"), receipts=("same", "same"), cost=2)
        with self.assertRaisesRegex(ValueError, "IDENTITY_AMBIGUOUS"):
            validate_candidate(candidate, [ab, bc])

    def test_best_path_optimizes_traversal_without_dropping_provenance(self):
        state = dict(observed=True, valid=True, proved=True)
        ab = self.relation("A", "B", "ab", cost=4, **state)
        bc = self.relation("B", "C", "bc", cost=4, **state)
        ax = self.relation("A", "X", "ax", cost=1, **state)
        xc = self.relation("X", "C", "xc", cost=1, **state)
        slow = candidate_route(ab, bc)
        fast = candidate_route(ax, xc)
        selected = best_admissible_route([slow, fast], [ab, bc, ax, xc])
        self.assertEqual(selected.candidate.nodes, ("A", "X", "C"))
        self.assertEqual(selected.provenance, ("receipt://ax", "receipt://xc"))
        self.assertEqual(len(selected.candidate.receipts), len(selected.provenance))

    def test_relation_requires_addressable_provenance(self):
        with self.assertRaisesRegex(ValueError, "ADDRESSABLE_PROVENANCE_REQUIRED"):
            Relation("A", "B", "", "A-B@exact", "receipt://missing")


if __name__ == "__main__":
    unittest.main()
