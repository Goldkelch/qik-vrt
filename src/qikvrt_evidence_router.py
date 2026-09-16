# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Standalone, standard-library-only exact-subject evidence routing.

Adapted from the Relation/CandidateRoute design inspected in PR #1096.
No old validation state is imported. Every route call performs fresh reads.
This library selects routes and persists local receipts; it never dispatches
work, grants authority, or establishes P2, Main, deployment or EFFECT_ACK_DONE.
Observer and validator callables are explicit trust boundaries, not oracles.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import heapq
import json
from pathlib import Path
import re
import secrets
import sqlite3
from typing import Callable, Iterable, Protocol

__version__ = "0.1.0"
MAX_RELATIONS = 256
MAX_RECEIPT_BYTES = 1024 * 1024
MAX_JOURNAL_ROWS = 10000
ZERO = "0" * 64


class Hold(ValueError):
    """A concrete fail-closed reason; never a success or effect receipt."""


def _text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise Hold(label)
    if any(ord(c) < 32 for c in value):
        raise Hold(label)


def _hex(value: str, length: int, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{%d}" % length, value):
        raise Hold(label)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


@dataclass(frozen=True)
class Subject:
    repository: str
    head: str
    tree: str

    def __post_init__(self) -> None:
        if not isinstance(self.repository, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise Hold("REPOSITORY_REQUIRED")
        _hex(self.head, 40, "EXACT_HEAD_REQUIRED")
        _hex(self.tree, 40, "EXACT_TREE_REQUIRED")


@dataclass(frozen=True)
class Relation:
    identity: str
    source: str
    target: str
    subject: Subject
    receipt: str
    receipt_sha256: str
    provenance: tuple[str, ...]
    cost: int = 1

    def __post_init__(self) -> None:
        for name in ("identity", "source", "target", "receipt"):
            _text(getattr(self, name), "ADDRESSABLE_RELATION_REQUIRED")
        if not isinstance(self.subject, Subject):
            raise Hold("EXACT_SUBJECT_REQUIRED")
        _hex(self.receipt_sha256, 64, "RECEIPT_HASH_REQUIRED")
        if type(self.cost) is not int or not 0 <= self.cost <= 1000000:
            raise Hold("BOUNDED_NONNEGATIVE_INTEGER_COST_REQUIRED")
        if not isinstance(self.provenance, tuple) or not 1 <= len(self.provenance) <= 64:
            raise Hold("IMMUTABLE_PROVENANCE_REQUIRED")
        for item in self.provenance:
            _text(item, "ADDRESSABLE_PROVENANCE_REQUIRED")


@dataclass(frozen=True)
class Observation:
    relation_id: str
    subject: Subject
    receipt: str
    challenge: str
    payload: bytes


class Observer(Protocol):
    def read_subject(self) -> Subject: ...
    def read_relation(self, relation: Relation, challenge: str) -> Observation: ...


@dataclass(frozen=True)
class CandidateRoute:
    relations: tuple[Relation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.relations, tuple) or not 1 <= len(self.relations) <= MAX_RELATIONS:
            raise Hold("BOUNDED_NONEMPTY_ROUTE_REQUIRED")
        if any(not isinstance(r, Relation) for r in self.relations):
            raise Hold("RELATION_REQUIRED")
        if len({r.identity for r in self.relations}) != len(self.relations):
            raise Hold("DUPLICATE_RELATION_IDENTITY")
        for left, right in zip(self.relations, self.relations[1:]):
            if left.target != right.source:
                raise Hold("RELATIONS_NOT_COMPOSABLE")

    @property
    def nodes(self) -> tuple[str, ...]:
        return (self.relations[0].source,) + tuple(r.target for r in self.relations)

    @property
    def cost(self) -> int:
        return sum(r.cost for r in self.relations)


def candidate_route(left: Relation, right: Relation) -> CandidateRoute:
    return CandidateRoute((left, right))


def evidence_transitive(*_relations: Relation) -> bool:
    return False


class ReceiptJournal:
    """SQLite INSERT-only API with a hash chain and committed readback.

    Owns a caller-selected local file. Not signed, not WORM, not an authority
    service. An externally retained digest is needed to detect rollback or a
    wholesale rewrite by a privileged writer. Concurrent appends serialize.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        if str(path) == ":memory:":
            raise Hold("PERSISTENT_JOURNAL_REQUIRED")
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS receipts "
                       "(seq INTEGER PRIMARY KEY, previous TEXT NOT NULL, "
                       "digest TEXT UNIQUE NOT NULL, body TEXT NOT NULL)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _rows(db: sqlite3.Connection) -> list[tuple]:
        rows = db.execute("SELECT seq, previous, digest, body FROM receipts "
                          "ORDER BY seq LIMIT ?", (MAX_JOURNAL_ROWS + 1,)).fetchall()
        if len(rows) > MAX_JOURNAL_ROWS:
            raise Hold("JOURNAL_BOUND_REACHED")
        previous = ZERO
        for expected, (seq, parent, digest, body) in enumerate(rows, 1):
            actual = hashlib.sha256((previous + "\n" + body).encode("utf-8")).hexdigest()
            if seq != expected or parent != previous or digest != actual:
                raise Hold("JOURNAL_INTEGRITY_FAILURE")
            previous = digest
        return rows

    def verify(self, expected_tip: str | None = None) -> str:
        with self._connect() as db:
            rows = self._rows(db)
        tip = rows[-1][2] if rows else ZERO
        if expected_tip is not None and tip != expected_tip:
            raise Hold("JOURNAL_TIP_MISMATCH")
        return tip

    def append(self, body: dict) -> str:
        encoded = canonical(body).decode("ascii")
        if len(encoded) > MAX_RECEIPT_BYTES:
            raise Hold("RECEIPT_BOUND_EXCEEDED")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = self._rows(db)
            if len(rows) >= MAX_JOURNAL_ROWS:
                raise Hold("JOURNAL_BOUND_REACHED")
            previous = rows[-1][2] if rows else ZERO
            digest = hashlib.sha256((previous + "\n" + encoded).encode()).hexdigest()
            db.execute("INSERT INTO receipts VALUES (?, ?, ?, ?)",
                       (len(rows) + 1, previous, digest, encoded))
        # New connection, after commit: persistence is not inferred from INSERT.
        if self.read(digest) != body:
            raise Hold("JOURNAL_READBACK_MISMATCH")
        return digest

    def read(self, digest: str) -> dict:
        _hex(digest, 64, "RECEIPT_DIGEST_REQUIRED")
        with self._connect() as db:
            rows = self._rows(db)
        for _seq, _previous, actual, body in rows:
            if actual == digest:
                return json.loads(body)
        raise Hold("RECEIPT_NOT_FOUND")


@dataclass(frozen=True)
class Decision:
    subject: Subject
    route: CandidateRoute
    journal_digest: str
    challenge: str
    # Deliberately no authority/effect booleans that callers could promote.


class Router:
    """Minimum-cost path over freshly validated relations, per invocation.

    Discovery is bounded to 256 explicitly supplied relations; there is no
    scanning, polling, network client, shell execution, or automatic dispatch.
    Validators check each edge's payload, never a fabricated transitive edge.
    The returned Decision is historical as soon as its subject changes.
    """

    def __init__(self, subject: Subject, relations: Iterable[Relation],
                 observer: Observer, validator: Callable[[Relation, bytes], bool],
                 journal: ReceiptJournal, *, observer_id: str, validator_id: str):
        if not isinstance(subject, Subject):
            raise Hold("EXACT_SUBJECT_REQUIRED")
        _text(observer_id, "OBSERVER_ID_REQUIRED")
        _text(validator_id, "VALIDATOR_ID_REQUIRED")
        self.subject = subject
        items = []
        for relation in relations:
            if not isinstance(relation, Relation):
                raise Hold("RELATION_REQUIRED")
            items.append(relation)
            if len(items) > MAX_RELATIONS:
                raise Hold("GRAPH_BOUND_EXCEEDED")
        self.relations = tuple(items)
        if not items or len({r.identity for r in items}) != len(items):
            raise Hold("EMPTY_OR_AMBIGUOUS_GRAPH")
        self.observer, self.validator, self.journal = observer, validator, journal
        self.observer_id, self.validator_id = observer_id, validator_id

    def _subject(self) -> None:
        try:
            current = self.observer.read_subject()
        except Exception as exc:
            raise Hold("SUBJECT_READ_FAILED") from exc
        if current != self.subject:
            raise Hold("CURRENT_SUBJECT_DRIFT")

    def _validate(self, relation: Relation, challenge: str) -> None:
        if relation.subject != self.subject:
            raise Hold("PREDECESSOR_OR_FOREIGN_SUBJECT")
        try:
            observed = self.observer.read_relation(relation, challenge)
        except Exception as exc:
            raise Hold("RELATION_READ_FAILED") from exc
        if not isinstance(observed, Observation):
            raise Hold("TYPED_OBSERVATION_REQUIRED")
        if (observed.subject != self.subject or observed.relation_id != relation.identity
                or observed.receipt != relation.receipt or observed.challenge != challenge):
            raise Hold("FRESH_EXACT_OBSERVATION_MISMATCH")
        if type(observed.payload) is not bytes or len(observed.payload) > MAX_RECEIPT_BYTES:
            raise Hold("BOUNDED_RECEIPT_BYTES_REQUIRED")
        if hashlib.sha256(observed.payload).hexdigest() != relation.receipt_sha256:
            raise Hold("RECEIPT_BYTES_MISMATCH")
        try:
            valid = self.validator(relation, observed.payload)
        except Exception as exc:
            raise Hold("VALIDATOR_FAILED") from exc
        if valid is not True:
            raise Hold("RELATION_NOT_VALIDATED")

    def route(self, source: str, target: str) -> Decision:
        _text(source, "SOURCE_REQUIRED")
        _text(target, "TARGET_REQUIRED")
        if source == target:
            raise Hold("NONEMPTY_DISTINCT_ENDPOINTS_REQUIRED")
        challenge = secrets.token_hex(32)
        self._subject()
        graph: dict[str, list[Relation]] = {}
        for relation in self.relations:
            graph.setdefault(relation.source, []).append(relation)
        # Dijkstra; only validated outgoing edges are eligible. No validity
        # cache survives this call. Identity order resolves equal-cost ties.
        queue: list[tuple[int, tuple[str, ...], str]] = [(0, (), source)]
        best = {source: (0, ())}
        paths: dict[str, tuple[Relation, ...]] = {source: ()}
        settled = set()
        rejected = []
        selected = None
        while queue:
            cost, identities, node = heapq.heappop(queue)
            if node in settled or best.get(node) != (cost, identities):
                continue
            settled.add(node)
            if node == target:
                selected = CandidateRoute(paths[node])
                break
            for relation in sorted(graph.get(node, ()), key=lambda r: r.identity):
                if relation.target in settled:
                    continue
                try:
                    self._validate(relation, challenge)
                except Hold as exc:
                    rejected.append({"relation": relation.identity, "reason": str(exc)})
                    continue
                key = (cost + relation.cost, identities + (relation.identity,))
                if relation.target not in best or key < best[relation.target]:
                    best[relation.target] = key
                    paths[relation.target] = paths[node] + (relation,)
                    heapq.heappush(queue, (*key, relation.target))
        if selected is None:
            raise Hold("NO_FRESH_VALIDATED_ROUTE:" + json.dumps(rejected, sort_keys=True))
        # Revalidate the selected edges after selection. This catches changes
        # during discovery; bytes and subjects stay bound to this invocation.
        for relation in selected.relations:
            self._validate(relation, challenge)
        self._subject()
        body = {
            "schema": "qikvrt_evidence_router_decision_v1", "status": "ROUTE_VALIDATED",
            "subject": asdict(self.subject), "challenge": challenge,
            "nodes": list(selected.nodes), "cost": selected.cost,
            "relations": [asdict(r) for r in selected.relations],
            "observer_id": self.observer_id, "validator_id": self.validator_id,
            "rejected_relations": rejected, "predecessor_evidence_transfer": False,
            "evidence_transitivity": False, "effect_authorized": False,
            "effect_ack_done": False,
        }
        # JSON normalization makes tuples/lists identical across disk readback.
        digest = self.journal.append(json.loads(canonical(body)))
        self._subject()
        return Decision(self.subject, selected, digest, challenge)
