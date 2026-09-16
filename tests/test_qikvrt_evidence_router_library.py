# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Run with python3 -B -m unittest discover -s tests -v (no pip required)."""
from dataclasses import replace
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qikvrt_evidence_router import (CandidateRoute, Hold, Observation,
    ReceiptJournal, Relation, Router, Subject, candidate_route, evidence_transitive)

S = Subject("Goldkelch/qik-vrt", "967d026c891addd706a7b28976a57a7901af696a",
            "f9095100581ed7ef23a8effe00370b322fc52a19")
OLD = replace(S, head="b4cf734917296829f74ff8ed7bd7e9f54a6f0e72")
PAYLOAD = b'{"primes":[2,3,5,7,11,13,17,19,23,29]}'


def edge(identity="ab", source="A", target="B", cost=1, subject=S):
    return Relation("urn:edge:" + identity, source, target, subject,
                    "urn:receipt:" + identity, hashlib.sha256(PAYLOAD).hexdigest(),
                    ("urn:provenance:" + identity,), cost)


class Reader:
    def __init__(self):
        self.subject = S
        self.reads = []
        self.subject_reads = 0
        self.change_on_read = None
        self.transform = lambda observation: observation

    def read_subject(self):
        self.subject_reads += 1
        if self.change_on_read == self.subject_reads:
            return OLD
        return self.subject

    def read_relation(self, relation, challenge):
        self.reads.append((relation.identity, challenge))
        return self.transform(Observation(relation.identity, self.subject,
                             relation.receipt, challenge, PAYLOAD))


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = ReceiptJournal(Path(self.temp.name) / "receipts.sqlite")
        self.reader = Reader()
        self.edges = (edge(), edge("bc", "B", "C"))

    def router(self, edges=None, validator=None):
        return Router(S, self.edges if edges is None else edges, self.reader,
                      validator or (lambda _r, payload: payload == PAYLOAD),
                      self.journal, observer_id="local-test-reader",
                      validator_id="local-test-validator")

    def test_route_preserves_every_relation_and_subject(self):
        result = self.router().route("A", "C")
        receipt = self.journal.read(result.journal_digest)
        self.assertEqual(result.route.nodes, ("A", "B", "C"))
        self.assertEqual(result.route.cost, 2)
        self.assertEqual(receipt["subject"], {"repository": S.repository, "head": S.head, "tree": S.tree})
        self.assertEqual([r["identity"] for r in receipt["relations"]], [r.identity for r in self.edges])
        self.assertEqual([r["provenance"] for r in receipt["relations"]], [[r.provenance[0]] for r in self.edges])
        self.assertFalse(receipt["effect_ack_done"])
        self.assertFalse(receipt["effect_authorized"])
        self.assertFalse(receipt["predecessor_evidence_transfer"])
        self.assertFalse(receipt["evidence_transitivity"])

    def test_predecessor_in_current_readback_rejected(self):
        self.reader.subject = OLD
        with self.assertRaisesRegex(Hold, "CURRENT_SUBJECT_DRIFT"):
            self.router().route("A", "C")

    def test_tree_drift_rejected_even_with_same_head(self):
        self.reader.subject = replace(S, tree="a" * 40)
        with self.assertRaisesRegex(Hold, "CURRENT_SUBJECT_DRIFT"):
            self.router().route("A", "C")

    def test_foreign_repository_rejected(self):
        self.reader.subject = replace(S, repository="ingolf-lohmann/qik-vrt")
        with self.assertRaisesRegex(Hold, "CURRENT_SUBJECT_DRIFT"):
            self.router().route("A", "C")

    def test_predecessor_relation_not_transferred(self):
        with self.assertRaisesRegex(Hold, "PREDECESSOR_OR_FOREIGN_SUBJECT"):
            self.router((edge(subject=OLD), self.edges[1])).route("A", "C")

    def test_replayed_challenge_rejected(self):
        self.reader.transform = lambda o: replace(o, challenge="old-invocation")
        with self.assertRaisesRegex(Hold, "FRESH_EXACT_OBSERVATION_MISMATCH"):
            self.router().route("A", "C")

    def test_observation_head_drift_rejected(self):
        self.reader.transform = lambda o: replace(o, subject=OLD)
        with self.assertRaisesRegex(Hold, "FRESH_EXACT_OBSERVATION_MISMATCH"):
            self.router().route("A", "C")

    def test_wrong_relation_identity_rejected(self):
        self.reader.transform = lambda o: replace(o, relation_id="urn:other")
        with self.assertRaisesRegex(Hold, "FRESH_EXACT_OBSERVATION_MISMATCH"):
            self.router().route("A", "C")

    def test_wrong_receipt_address_rejected(self):
        self.reader.transform = lambda o: replace(o, receipt="urn:wrong")
        with self.assertRaisesRegex(Hold, "FRESH_EXACT_OBSERVATION_MISMATCH"):
            self.router().route("A", "C")

    def test_tampered_payload_rejected(self):
        self.reader.transform = lambda o: replace(o, payload=b"tampered")
        with self.assertRaisesRegex(Hold, "RECEIPT_BYTES_MISMATCH"):
            self.router().route("A", "C")

    def test_unbounded_payload_rejected(self):
        self.reader.transform = lambda o: replace(o, payload=b"x" * (1024 * 1024 + 1))
        with self.assertRaisesRegex(Hold, "BOUNDED_RECEIPT_BYTES_REQUIRED"):
            self.router().route("A", "C")

    def test_truthy_nonboolean_validation_not_accepted(self):
        for value in (1, "PASS", {"pass": True}, None, False):
            with self.subTest(value=value), self.assertRaisesRegex(Hold, "RELATION_NOT_VALIDATED"):
                self.router(validator=lambda _r, _p: value).route("A", "C")

    def test_validator_exception_holds(self):
        def broken(_r, _p):
            raise RuntimeError("validator unavailable")
        with self.assertRaisesRegex(Hold, "VALIDATOR_FAILED"):
            self.router(validator=broken).route("A", "C")

    def test_reader_exception_holds(self):
        def broken(*_args):
            raise OSError("source unavailable")
        self.reader.read_relation = broken
        with self.assertRaisesRegex(Hold, "RELATION_READ_FAILED"):
            self.router().route("A", "C")

    def test_subject_reader_exception_holds(self):
        def broken():
            raise OSError("unavailable")
        self.reader.read_subject = broken
        with self.assertRaisesRegex(Hold, "SUBJECT_READ_FAILED"):
            self.router().route("A", "C")

    def test_every_invocation_is_fresh(self):
        router = self.router()
        first = router.route("A", "C")
        first_reads = len(self.reader.reads)
        second = router.route("A", "C")
        self.assertNotEqual(first.challenge, second.challenge)
        self.assertNotEqual(first.journal_digest, second.journal_digest)
        self.assertEqual(len(self.reader.reads), 2 * first_reads)
        self.assertGreaterEqual(first_reads, 4)

    def test_mid_operation_subject_drift_holds(self):
        self.reader.change_on_read = 2
        with self.assertRaisesRegex(Hold, "CURRENT_SUBJECT_DRIFT"):
            self.router().route("A", "C")
        self.assertEqual(self.journal.verify(), "0" * 64)

    def test_post_persistence_drift_returns_no_decision(self):
        self.reader.change_on_read = 3
        with self.assertRaisesRegex(Hold, "CURRENT_SUBJECT_DRIFT"):
            self.router().route("A", "C")
        self.assertNotEqual(self.journal.verify(), "0" * 64)  # historical receipt retained

    def test_selected_edge_changed_during_selection_holds(self):
        count = [0]
        def changed(observation):
            count[0] += 1
            return replace(observation, payload=b"changed") if count[0] == 3 else observation
        self.reader.transform = changed
        with self.assertRaisesRegex(Hold, "RECEIPT_BYTES_MISMATCH"):
            self.router().route("A", "C")

    def test_minimum_cost_route(self):
        result = self.router(self.edges + (edge("ac", "A", "C", 5),)).route("A", "C")
        self.assertEqual(result.route.cost, 2)
        self.assertEqual(result.route.nodes, ("A", "B", "C"))

    def test_invalid_shortcut_is_not_evidence(self):
        shortcut = edge("ac", "A", "C", 0)
        result = self.router(self.edges + (shortcut,),
            validator=lambda r, _p: r != shortcut).route("A", "C")
        self.assertEqual(result.route.cost, 2)
        self.assertEqual(len(self.journal.read(result.journal_digest)["rejected_relations"]), 1)

    def test_valid_shortcut_preserves_declared_provenance(self):
        shortcut = replace(edge("ac", "A", "C", 1),
                           provenance=("urn:edge:ab", "urn:edge:bc", "urn:own:ac"))
        result = self.router(self.edges + (shortcut,)).route("A", "C")
        self.assertEqual(result.route.relations, (shortcut,))
        self.assertEqual(len(self.journal.read(result.journal_digest)["relations"][0]["provenance"]), 3)
        self.assertFalse(evidence_transitive(*self.edges))

    def test_zero_cost_cycle_is_bounded(self):
        result = self.router((edge(cost=0), edge("ba", "B", "A", 0), self.edges[1])).route("A", "C")
        self.assertEqual(result.route.cost, 1)

    def test_ties_are_deterministic_under_input_permutations(self):
        choices = self.edges + (edge("ad", "A", "D"), edge("dc", "D", "C"))
        routes = {self.router(order).route("A", "C").route.nodes for order in itertools.permutations(choices)}
        self.assertEqual(routes, {("A", "B", "C")})

    def test_disconnected_route_rejected(self):
        with self.assertRaisesRegex(Hold, "RELATIONS_NOT_COMPOSABLE"):
            candidate_route(self.edges[0], edge("xc", "X", "C"))

    def test_empty_route_not_a_noop_success(self):
        with self.assertRaises(Hold):
            CandidateRoute(())
        with self.assertRaises(Hold):
            self.router().route("A", "A")

    def test_empty_graph_and_duplicate_ids_rejected(self):
        for edges in ((), (self.edges[0], self.edges[0])):
            with self.assertRaisesRegex(Hold, "EMPTY_OR_AMBIGUOUS_GRAPH"):
                self.router(edges)

    def test_graph_input_is_bounded(self):
        with self.assertRaisesRegex(Hold, "GRAPH_BOUND_EXCEEDED"):
            self.router(edge(str(n)) for n in itertools.count())

    def test_invalid_subject_fields(self):
        for field, value in (("repository", "main"), ("head", "main"), ("tree", ""), ("head", True)):
            with self.subTest(field=field, value=value), self.assertRaises(Hold):
                replace(S, **{field: value})

    def test_relation_type_and_provenance_bounds(self):
        for kwargs in ({"cost": -1}, {"cost": True}, {"cost": 0.5}, {"cost": 1000001},
                       {"provenance": ()}, {"provenance": ["mutable"]},
                       {"provenance": ("",)}, {"receipt_sha256": "green"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(Hold):
                replace(edge(), **kwargs)

    def test_reopen_journal_and_readback(self):
        result = self.router().route("A", "C")
        reopened = ReceiptJournal(self.journal.path)
        self.assertEqual(reopened.verify(result.journal_digest), result.journal_digest)
        self.assertEqual(reopened.read(result.journal_digest)["status"], "ROUTE_VALIDATED")

    def test_tampered_journal_rejected(self):
        self.router().route("A", "C")
        with sqlite3.connect(self.journal.path) as db:
            db.execute("UPDATE receipts SET body='{}' WHERE seq=1")
        with self.assertRaisesRegex(Hold, "JOURNAL_INTEGRITY_FAILURE"):
            self.router().route("A", "C")

    def test_retained_tip_detects_rollback(self):
        result = self.router().route("A", "C")
        with sqlite3.connect(self.journal.path) as db:
            db.execute("DELETE FROM receipts")
        with self.assertRaisesRegex(Hold, "JOURNAL_TIP_MISMATCH"):
            self.journal.verify(result.journal_digest)

    def test_minimum_cost_matches_exhaustive_three_node_oracle(self):
        pairs = (("A", "B"), ("A", "C"), ("B", "A"),
                 ("B", "C"), ("C", "A"), ("C", "B"))
        for weights in itertools.product((-1, 0, 1), repeat=6):
            edges = tuple(edge(str(i), a, b, cost) for i, ((a, b), cost)
                          in enumerate(zip(pairs, weights)) if cost >= 0)
            expected = []
            if weights[1] >= 0:
                expected.append(weights[1])
            if weights[0] >= 0 and weights[3] >= 0:
                expected.append(weights[0] + weights[3])
            with self.subTest(weights=weights):
                if not expected:
                    with self.assertRaises(Hold):
                        self.router(edges).route("A", "C")
                else:
                    result = self.router(edges).route("A", "C")
                    self.assertEqual(result.route.cost, min(expected))

    def test_memory_journal_not_persistence(self):
        with self.assertRaisesRegex(Hold, "PERSISTENT_JOURNAL_REQUIRED"):
            ReceiptJournal(":memory:")

    def test_missing_receipt_never_passes(self):
        with self.assertRaisesRegex(Hold, "RECEIPT_NOT_FOUND"):
            self.journal.read("1" * 64)


if __name__ == "__main__":
    unittest.main()
