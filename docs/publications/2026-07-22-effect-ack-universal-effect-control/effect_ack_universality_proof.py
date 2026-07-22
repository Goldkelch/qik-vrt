#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Executable proof obligations for the QIK-VRT EFFECT_ACK control model.

The script proves finite properties of the abstract version-1 decision model
by exhaustive enumeration.  It also checks a small canonical repository codec,
the necessity of complete gate mediation, a forward-only anticipation model,
and a finite countermodel to universal exact reverse engineering.

It deliberately does not claim full draft -01 wire conformance, empirical
physical safety, IETF consensus, or recovery of information absent from the
observation.  Those boundaries are part of the generated report.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import itertools
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


MODEL_ID = "qikvrt-effect-ack-universality-proof-v1"


class State(str, Enum):
    NACK = "EFFECT_NACK"
    CONTINUE = "EFFECT_ACK_CONTINUE"
    DONE = "EFFECT_ACK_DONE"
    ISOLATE = "EFFECT_ACK_ISOLATE"
    BLOCK = "EFFECT_ACK_BLOCK"


class Decision(str, Enum):
    UNDECIDED = "UNDECIDED"
    CONTINUE = "CONTINUE"
    RELEASE = "RELEASE"
    ISOLATE = "ISOLATE"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class Snapshot:
    transport_ack: bool
    input_identifier_available: bool
    input_digest_valid: bool
    predecessor_invalid: bool
    deadline_exceeded: bool
    integrity_failure: bool
    origin_checked: bool
    context_checked: bool
    semantics_reconstructed: bool
    effect_anticipated: bool
    risk_classified: bool
    risk_known: bool
    responsibility_assigned: bool
    responsibility_owner_present: bool
    connection_decided: bool
    policy_allows_release: bool
    no_open_questions: bool
    no_next_required_checks: bool
    required_evidence_complete: bool
    connection_decision: Decision


BOOLEAN_FIELDS = tuple(
    name
    for name in Snapshot.__dataclass_fields__
    if name != "connection_decision"
)


class ProofFailure(RuntimeError):
    """Raised when a machine-checked obligation does not hold."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProofFailure(message)


def core_done_conditions(snapshot: Snapshot) -> dict[str, bool]:
    """The abstracted conjunction from draft -01 section 4.1."""

    return {
        "transport_ack": snapshot.transport_ack,
        "input_digest_valid": snapshot.input_digest_valid,
        "origin_checked": snapshot.origin_checked,
        "context_checked": snapshot.context_checked,
        "semantics_reconstructed": snapshot.semantics_reconstructed,
        "effect_anticipated": snapshot.effect_anticipated,
        "risk_classified": snapshot.risk_classified,
        "risk_known": snapshot.risk_known,
        "responsibility_assigned": snapshot.responsibility_assigned,
        "responsibility_owner_present": snapshot.responsibility_owner_present,
        "connection_decided": snapshot.connection_decided,
        "connection_decision_release": (
            snapshot.connection_decision is Decision.RELEASE
        ),
        "policy_allows_release": snapshot.policy_allows_release,
        "deadline_not_exceeded": not snapshot.deadline_exceeded,
        "no_open_questions": snapshot.no_open_questions,
        "no_next_required_checks": snapshot.no_next_required_checks,
        "required_evidence_complete": snapshot.required_evidence_complete,
    }


def core_done(snapshot: Snapshot) -> bool:
    return all(core_done_conditions(snapshot).values())


def effect_checkable_reception(snapshot: Snapshot) -> bool:
    """Finite abstraction of an identifiable, digest-bound reception.

    Transport receipt remains a separate CoreDone condition.  This helper is
    intentionally narrower than a behavioral refinement of the current Python
    evaluator, which is outside the scope of this proof model.
    """

    return snapshot.input_identifier_available and snapshot.input_digest_valid


def select_state(snapshot: Snapshot) -> State:
    """Abstract refinement of the priority algorithm in draft -01 section 4.2."""

    if snapshot.predecessor_invalid:
        return State.BLOCK
    if snapshot.deadline_exceeded:
        return State.BLOCK
    if not effect_checkable_reception(snapshot):
        return State.NACK
    if snapshot.integrity_failure:
        return State.BLOCK
    if snapshot.connection_decision is Decision.BLOCK:
        return State.BLOCK
    if snapshot.connection_decision is Decision.ISOLATE:
        return State.ISOLATE
    if snapshot.connection_decision is Decision.RELEASE and core_done(snapshot):
        return State.DONE
    return State.CONTINUE


def ordinary_release(state: State, *, wire_valid_and_authenticated: bool = True) -> bool:
    """Consumer-side release wrapper used by the proof model."""

    return wire_valid_and_authenticated and state is State.DONE


def file_sha256(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    payload = path.read_bytes()
    return {
        "path": path.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


EXPECTED_WIRE_FIELDS = (
    "wire_version",
    "message_type",
    "protocol_root_id",
    "protocol_version",
    "protocol_id",
    "previous_protocol_id",
    "previous_protocol_hash",
    "protocol_hash",
    "input_id",
    "input_hash",
    "state",
    "transport_ack",
    "origin_checked",
    "context_checked",
    "semantics_reconstructed",
    "effect_anticipated",
    "risk_classified",
    "risk_level",
    "responsibility_assigned",
    "responsibility_owner",
    "connection_decided",
    "connection_decision",
    "policy_id",
    "policy_version",
    "policy_hash",
    "policy_allows_release",
    "ordinary_release",
    "evaluation_timeout_ms",
    "deadline_exceeded",
    "reasons",
    "evidence_refs",
    "required_evidence_refs",
    "open_questions",
    "next_required_checks",
    "created_utc",
)

EXPECTED_STATES = tuple(state.value for state in State)
EXPECTED_DECISIONS = tuple(decision.value for decision in Decision)
EXPECTED_CORE_DONE_LINES = (
    "r.transport_ack",
    "and sha256_identifier(r.input_hash)",
    "and r.origin_checked",
    "and r.context_checked",
    "and r.semantics_reconstructed",
    "and r.effect_anticipated",
    "and r.risk_classified",
    'and r.risk_level != "UNKNOWN"',
    "and r.responsibility_assigned",
    'and r.responsibility_owner != ""',
    "and r.connection_decided",
    'and r.connection_decision == "RELEASE"',
    "and r.policy_allows_release",
    "and not r.deadline_exceeded",
    "and r.open_questions == []",
    "and r.next_required_checks == []",
    "and set(r.required_evidence_refs) <= set(r.evidence_refs)",
)
EXPECTED_STATE_COUNTS = {
    State.NACK.value: 491_520,
    State.CONTINUE.value: 49_151,
    State.DONE.value: 1,
    State.ISOLATE.value: 16_384,
    State.BLOCK.value: 2_064_384,
}


def inspect_draft_xml(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    root = ET.fromstring(payload)
    sources = [
        "".join(element.itertext())
        for element in root.iter()
        if element.tag.endswith("sourcecode")
    ]

    cddl = next(source for source in sources if "effect-ack-record = {" in source)
    record_block = cddl.split("effect-ack-record = {", 1)[1].split("}\n", 1)[0]
    fields = tuple(re.findall(r"^\s{2}([a-z][a-z0-9_]*)\s*:", record_block, re.M))
    require(fields == EXPECTED_WIRE_FIELDS, "draft -01 wire field set/order mismatch")

    effect_state_block = cddl.split("effect-state =", 1)[1].split("risk-level", 1)[0]
    states = tuple(re.findall(r'"(EFFECT_[A-Z_]+)"', effect_state_block))
    require(states == EXPECTED_STATES, "draft -01 state set/order mismatch")

    decision_block = cddl.split("connection-decision =", 1)[1].split("sha256-id", 1)[0]
    decisions = tuple(re.findall(r'"([A-Z]+)"', decision_block))
    require(decisions == EXPECTED_DECISIONS, "draft -01 decision set/order mismatch")

    core = next(source for source in sources if "r.transport_ack" in source)
    core_lines = tuple(line.strip() for line in core.strip().splitlines())
    require(
        core_lines == EXPECTED_CORE_DONE_LINES,
        "draft -01 CoreDone text/order mismatch",
    )

    priority = next(source for source in sources if "predecessor_invalid" in source)
    priority_tokens = (
        "predecessor_invalid",
        "deadline_exceeded",
        "not effect_checkable_reception",
        "integrity_failure",
        "connection_decision == BLOCK",
        "connection_decision == ISOLATE",
        "connection_decision == RELEASE",
        "state = EFFECT_ACK_CONTINUE",
        "ordinary_release = (state == EFFECT_ACK_DONE)",
    )
    positions = tuple(priority.index(token) for token in priority_tokens)
    require(positions == tuple(sorted(positions)), "draft -01 priority order mismatch")

    return {
        **(file_sha256(path) or {}),
        "wireFields": len(fields),
        "states": list(states),
        "connectionDecisions": list(decisions),
        "coreDoneConjuncts": len(core_lines),
        "priorityAnchors": list(priority_tokens),
    }


def inspect_runtime_fields(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    protocol = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ResponsibilityProtocol"
    )
    fields = tuple(
        node.target.id
        for node in protocol.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    )
    missing = sorted(set(EXPECTED_WIRE_FIELDS) - set(fields))
    extra = sorted(set(fields) - set(EXPECTED_WIRE_FIELDS))
    return {
        **(file_sha256(path) or {}),
        "responsibilityProtocolFields": len(fields),
        "missingDraft01Fields": missing,
        "extraNonDraft01Fields": extra,
        "fullDraft01FieldSet": not missing and not extra,
    }


RepoEntry = tuple[str, int, bytes]
RepoSnapshot = tuple[RepoEntry, ...]


def encode_repository(repository: Iterable[RepoEntry]) -> bytes:
    entries = sorted(repository, key=lambda item: item[0])
    if len({path for path, _, _ in entries}) != len(entries):
        raise ValueError("duplicate repository path")
    document = {
        "schema": "qikvrt-canonical-repository-snapshot-v1",
        "entries": [
            {"path": path, "mode": mode, "bytes_hex": payload.hex()}
            for path, mode, payload in entries
        ],
    }
    return json.dumps(
        document,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def decode_repository(encoded: bytes) -> RepoSnapshot:
    document = json.loads(encoded.decode("ascii"))
    if document.get("schema") != "qikvrt-canonical-repository-snapshot-v1":
        raise ValueError("unsupported repository snapshot schema")
    result = tuple(
        sorted(
            (
                str(item["path"]),
                int(item["mode"]),
                bytes.fromhex(str(item["bytes_hex"])),
            )
            for item in document["entries"]
        )
    )
    if len({path for path, _, _ in result}) != len(result):
        raise ValueError("duplicate repository path")
    return result


def enumerate_small_repositories() -> list[RepoSnapshot]:
    paths = ("a", "b")
    alternatives: tuple[tuple[int, bytes] | None, ...] = (
        None,
        (0o100644, b""),
        (0o100644, b"A"),
        (0o100644, b"\x00"),
        (0o100755, b""),
        (0o100755, b"A"),
        (0o100755, b"\x00"),
    )
    repositories: list[RepoSnapshot] = []
    for choices in itertools.product(alternatives, repeat=len(paths)):
        entries: list[RepoEntry] = []
        for path, choice in zip(paths, choices, strict=True):
            if choice is not None:
                mode, payload = choice
                entries.append((path, mode, payload))
        repositories.append(tuple(entries))
    return repositories


def select_state_oracle(snapshot: Snapshot) -> State:
    """Independently structured first-match oracle for the priority rule."""

    prioritized_rules = (
        (snapshot.predecessor_invalid, State.BLOCK),
        (snapshot.deadline_exceeded, State.BLOCK),
        (not effect_checkable_reception(snapshot), State.NACK),
        (snapshot.integrity_failure, State.BLOCK),
        (snapshot.connection_decision is Decision.BLOCK, State.BLOCK),
        (snapshot.connection_decision is Decision.ISOLATE, State.ISOLATE),
        (
            snapshot.connection_decision is Decision.RELEASE
            and core_done(snapshot),
            State.DONE,
        ),
        (True, State.CONTINUE),
    )
    return next(state for applies, state in prioritized_rules if applies)


def check_protocol_state_space() -> tuple[dict[str, int], int, int]:
    state_counts = {state.value: 0 for state in State}
    abstract_assignments = 0
    transport_ack_nonrelease_cases = 0

    for bits in itertools.product((False, True), repeat=len(BOOLEAN_FIELDS)):
        values = dict(zip(BOOLEAN_FIELDS, bits, strict=True))
        for decision in Decision:
            snapshot = Snapshot(**values, connection_decision=decision)
            state = select_state(snapshot)
            abstract_assignments += 1
            state_counts[state.value] += 1

            require(isinstance(state, State), "selector returned a non-state")
            require(
                state is select_state_oracle(snapshot),
                "implementation selector disagrees with the priority oracle",
            )
            require(
                ordinary_release(state) == (state is State.DONE),
                "DONE-only release equivalence failed",
            )
            require(
                not ordinary_release(state, wire_valid_and_authenticated=False),
                "invalid consumer admission produced release",
            )

            if snapshot.transport_ack and state is not State.DONE:
                transport_ack_nonrelease_cases += 1

            if state is State.DONE:
                require(
                    not snapshot.predecessor_invalid,
                    "DONE reached with an invalid predecessor",
                )
                require(
                    not snapshot.integrity_failure,
                    "DONE reached with an integrity failure",
                )
                require(
                    effect_checkable_reception(snapshot),
                    "DONE reached without an effect-checkable reception",
                )
                require(
                    all(core_done_conditions(snapshot).values()),
                    "DONE reached without the complete CoreDone conjunction",
                )

    require(
        abstract_assignments == (2 ** len(BOOLEAN_FIELDS)) * len(Decision),
        "abstract assignment count is incomplete",
    )
    require(
        state_counts == EXPECTED_STATE_COUNTS,
        "state distribution differs from the frozen proof oracle",
    )
    require(
        all(count > 0 for count in state_counts.values()),
        "one or more normative states are unreachable",
    )
    require(
        transport_ack_nonrelease_cases == 1_310_719,
        "unexpected transport-ACK/non-DONE witness count",
    )
    return state_counts, abstract_assignments, transport_ack_nonrelease_cases


def all_done_snapshot() -> Snapshot:
    return Snapshot(
        transport_ack=True,
        input_identifier_available=True,
        input_digest_valid=True,
        predecessor_invalid=False,
        deadline_exceeded=False,
        integrity_failure=False,
        origin_checked=True,
        context_checked=True,
        semantics_reconstructed=True,
        effect_anticipated=True,
        risk_classified=True,
        risk_known=True,
        responsibility_assigned=True,
        responsibility_owner_present=True,
        connection_decided=True,
        policy_allows_release=True,
        no_open_questions=True,
        no_next_required_checks=True,
        required_evidence_complete=True,
        connection_decision=Decision.RELEASE,
    )


def check_each_done_condition() -> list[str]:
    baseline = all_done_snapshot()
    require(select_state(baseline) is State.DONE, "all-DONE baseline is not DONE")
    checked: list[str] = []

    for condition in core_done_conditions(baseline):
        values = asdict(baseline)
        values["connection_decision"] = baseline.connection_decision
        if condition == "connection_decision_release":
            values["connection_decision"] = Decision.UNDECIDED
        elif condition == "deadline_not_exceeded":
            values["deadline_exceeded"] = True
        else:
            values[condition] = False
        altered = Snapshot(**values)
        require(
            select_state(altered) is not State.DONE,
            f"CoreDone condition is not necessary in baseline: {condition}",
        )
        require(
            not ordinary_release(select_state(altered)),
            f"ordinary release survived removal of condition: {condition}",
        )
        checked.append(condition)

    require(
        tuple(checked)
        == tuple(
            (
                "transport_ack",
                "input_digest_valid",
                "origin_checked",
                "context_checked",
                "semantics_reconstructed",
                "effect_anticipated",
                "risk_classified",
                "risk_known",
                "responsibility_assigned",
                "responsibility_owner_present",
                "connection_decided",
                "connection_decision_release",
                "policy_allows_release",
                "deadline_not_exceeded",
                "no_open_questions",
                "no_next_required_checks",
                "required_evidence_complete",
            )
        ),
        "the abstract CoreDone condition list changed",
    )
    return checked


def check_priority_collisions() -> list[dict[str, str]]:
    baseline = all_done_snapshot()
    cases: list[tuple[str, dict[str, Any], State]] = (
        (
            "invalid predecessor dominates every local release fact",
            {"predecessor_invalid": True, "deadline_exceeded": True},
            State.BLOCK,
        ),
        (
            "deadline dominates missing effect-checkable reception",
            {"deadline_exceeded": True, "input_identifier_available": False},
            State.BLOCK,
        ),
        (
            "missing effect-checkable reception dominates local integrity failure",
            {
                "input_identifier_available": False,
                "integrity_failure": True,
                "connection_decision": Decision.BLOCK,
            },
            State.NACK,
        ),
        (
            "integrity failure dominates an isolate decision",
            {
                "integrity_failure": True,
                "connection_decision": Decision.ISOLATE,
            },
            State.BLOCK,
        ),
        (
            "explicit block dominates otherwise complete release facts",
            {"connection_decision": Decision.BLOCK},
            State.BLOCK,
        ),
        (
            "explicit isolate dominates otherwise complete release facts",
            {"connection_decision": Decision.ISOLATE},
            State.ISOLATE,
        ),
        (
            "continue decision cannot become DONE",
            {"connection_decision": Decision.CONTINUE},
            State.CONTINUE,
        ),
    )
    results: list[dict[str, str]] = []
    for name, changes, expected in cases:
        values = asdict(baseline)
        values["connection_decision"] = baseline.connection_decision
        values.update(changes)
        actual = select_state(Snapshot(**values))
        require(actual is expected, f"priority collision failed: {name}")
        results.append({"case": name, "state": actual.value})
    return results


def check_gate_mediation() -> dict[str, Any]:
    conforming_cases = 0
    protected_executor_invocations = 0
    for state, consumer_admission in itertools.product(State, (False, True)):
        executor_invocation = ordinary_release(
            state,
            wire_valid_and_authenticated=consumer_admission,
        )
        require(
            not executor_invocation
            or (state is State.DONE and consumer_admission),
            "protected executor was invoked outside admitted DONE",
        )
        protected_executor_invocations += int(executor_invocation)
        conforming_cases += 1

    bypass_counterexample = {
        "state": State.CONTINUE.value,
        "gate_release": ordinary_release(State.CONTINUE),
        "alternate_path_reaches_executor": True,
        "protected_effect_command_requested": True,
    }
    require(
        bool(bypass_counterexample["protected_effect_command_requested"]),
        "bypass counterexample did not request an effect",
    )
    require(
        bypass_counterexample["state"] != State.DONE.value,
        "bypass counterexample unexpectedly used DONE",
    )
    return {
        "conforming_cases": conforming_cases,
        "protected_executor_invocations": protected_executor_invocations,
        "bypass_counterexample": bypass_counterexample,
    }


def check_forward_anticipation() -> dict[str, Any]:
    baseline = all_done_snapshot()
    values = asdict(baseline)
    values["connection_decision"] = baseline.connection_decision
    values["effect_anticipated"] = False
    without_analysis = Snapshot(**values)
    require(select_state(baseline) is State.DONE, "anticipation baseline is not DONE")
    require(
        select_state(without_analysis) is State.CONTINUE,
        "removing only effect_anticipated did not suspend release",
    )
    require(
        not ordinary_release(select_state(without_analysis)),
        "missing effect analysis still produced release",
    )

    def present_decision(forecast: str) -> str:
        return "PREPARE_OR_RELEASE" if forecast == "CLEAR" else "SUSPEND"

    forecasts = ("CLEAR", "HAZARD")
    later_outcomes = ("CLEAR", "HAZARD")
    cases = 0
    for forecast in forecasts:
        reference = present_decision(forecast)
        for later_outcome in later_outcomes:
            del later_outcome
            require(
                present_decision(forecast) == reference,
                "later outcome acted as a backward input",
            )
            cases += 1
    require(
        present_decision("CLEAR") != present_decision("HAZARD"),
        "present forecast did not affect the present toy decision",
    )
    return {
        "draft_gate_witness": {
            "with_effect_analysis": select_state(baseline).value,
            "without_effect_analysis": select_state(without_analysis).value,
            "ordinary_release_without_effect_analysis": False,
        },
        "illustrative_forward_causal_model": {
            "cases": cases,
            "forecast_changes_present_decision": True,
            "later_outcome_is_not_a_backward_input": True,
        },
        "semantic_boundary": (
            "effect_anticipated asserts that effect analysis occurred; "
            "it does not standardize a forecast model or assert a favorable outcome"
        ),
    }


def check_repository_codec() -> dict[str, Any]:
    repositories = enumerate_small_repositories()
    encodings: dict[bytes, RepoSnapshot] = {}
    for repository in repositories:
        encoded = encode_repository(repository)
        require(
            decode_repository(encoded) == tuple(sorted(repository)),
            "repository codec round-trip failed",
        )
        require(
            encode_repository(reversed(repository)) == encoded,
            "repository encoding depends on entry order",
        )
        require(
            encoded not in encodings or encodings[encoded] == repository,
            "two distinct bounded repositories share an encoding",
        )
        encodings[encoded] = repository

    pairwise_comparisons = 0
    aggregate_round_trips = 0
    for left, right in itertools.product(repositories, repeat=2):
        left_encoded = encode_repository(left)
        right_encoded = encode_repository(right)
        require(
            (left_encoded == right_encoded) == (left == right),
            "bounded repository equality/encoding equivalence failed",
        )
        pairwise_comparisons += 1

        aggregate: RepoSnapshot = tuple(
            sorted(
                (
                    ("sources/seed.present", 0o100644, b"1"),
                    ("sources/node.present", 0o100644, b"1"),
                    *(
                        (f"seed/{path}", mode, payload)
                        for path, mode, payload in left
                    ),
                    *(
                        (f"node/{path}", mode, payload)
                        for path, mode, payload in right
                    ),
                )
            )
        )
        aggregate_encoded = encode_repository(aggregate)
        require(
            decode_repository(aggregate_encoded) == aggregate,
            "source-tagged aggregate round-trip failed",
        )
        require(
            encode_repository(reversed(aggregate)) == aggregate_encoded,
            "source-tagged aggregate replicas are not byte-identical",
        )
        aggregate_round_trips += 1

    require(
        len(encodings) == len(repositories),
        "bounded repository encoding is not injective",
    )
    require(pairwise_comparisons == 2_401, "repository pair universe is incomplete")
    require(aggregate_round_trips == 2_401, "aggregate universe is incomplete")
    return {
        "bounded_repository_models": len(repositories),
        "round_trips": len(repositories),
        "distinct_encodings": len(encodings),
        "pairwise_equality_encoding_comparisons": pairwise_comparisons,
        "source_tagged_aggregate_round_trips": aggregate_round_trips,
        "canonical_under_entry_reordering": True,
        "boundary": (
            "toy model only: two paths, regular-file modes and three payloads; "
            "Git history, refs, symlinks, submodules, LFS and external dependencies "
            "are outside this model"
        ),
    }


def check_finite_factorization_and_inversion() -> dict[str, Any]:
    """Exhaust finite witnesses for semantic factorization and exact inversion."""

    functions_3_to_2 = tuple(itertools.product((0, 1), repeat=3))
    factorization_pairs = 0
    nonfactorization_pairs = 0
    checked_pairs = 0
    for observation, semantics in itertools.product(functions_3_to_2, repeat=2):
        candidate_decoders = tuple(itertools.product((0, 1), repeat=2))
        decoder_exists = any(
            all(decoder[observation[index]] == semantics[index] for index in range(3))
            for decoder in candidate_decoders
        )
        constant_on_fibers = all(
            observation[left] != observation[right]
            or semantics[left] == semantics[right]
            for left, right in itertools.product(range(3), repeat=2)
        )
        require(
            decoder_exists == constant_on_fibers,
            "finite semantic factorization criterion failed",
        )
        factorization_pairs += int(decoder_exists)
        nonfactorization_pairs += int(not decoder_exists)
        checked_pairs += 1

    require(checked_pairs == 64, "factorization pair universe is incomplete")
    require(factorization_pairs == 28, "unexpected factorization count")
    require(nonfactorization_pairs == 36, "unexpected nonfactorization count")

    functions_3_to_3 = tuple(itertools.product(range(3), repeat=3))
    left_invertible_3_to_3 = 0
    for observation in functions_3_to_3:
        left_inverse_exists = any(
            all(candidate[observation[index]] == index for index in range(3))
            for candidate in functions_3_to_3
        )
        injective = len(set(observation)) == 3
        require(
            left_inverse_exists == injective,
            "left inverse/injectivity equivalence failed for 3-to-3 mapping",
        )
        left_invertible_3_to_3 += int(left_inverse_exists)
    require(left_invertible_3_to_3 == 6, "unexpected 3-to-3 inverse count")

    candidate_left_inverses_2_to_3 = tuple(itertools.product(range(3), repeat=2))
    left_invertible_3_to_2 = 0
    for observation in functions_3_to_2:
        left_inverse_exists = any(
            all(candidate[observation[index]] == index for index in range(3))
            for candidate in candidate_left_inverses_2_to_3
        )
        require(
            not left_inverse_exists,
            "a 3-to-2 observation unexpectedly had an exact left inverse",
        )
        left_invertible_3_to_2 += int(left_inverse_exists)

    return {
        "semantic_factorization": {
            "function_pairs_checked": checked_pairs,
            "factorizable": factorization_pairs,
            "not_factorizable": nonfactorization_pairs,
            "criterion": "semantics is constant on every observation fiber",
        },
        "exact_historical_inversion": {
            "mappings_3_to_3": len(functions_3_to_3),
            "injective_and_left_invertible_3_to_3": left_invertible_3_to_3,
            "mappings_3_to_2": len(functions_3_to_2),
            "left_invertible_3_to_2": left_invertible_3_to_2,
            "criterion": "an exact left inverse requires an injective observation",
        },
    }


def build_report(draft_txt: Path, draft_xml: Path, runtime: Path) -> dict[str, Any]:
    for label, path in (
        ("draft text", draft_txt),
        ("draft XML", draft_xml),
        ("Python reference runtime", runtime),
    ):
        require(path.is_file(), f"missing {label}: {path}")

    draft_inspection = inspect_draft_xml(draft_xml)
    runtime_inspection = inspect_runtime_fields(runtime)
    state_counts, abstract_assignments, transport_nonrelease = (
        check_protocol_state_space()
    )
    done_conditions = check_each_done_condition()
    priority_collisions = check_priority_collisions()
    mediation = check_gate_mediation()
    anticipation = check_forward_anticipation()
    repository_codec = check_repository_codec()
    factorization_and_inversion = check_finite_factorization_and_inversion()

    checks = [
        {
            "id": "SPEC-001",
            "status": "PASS",
            "claim": (
                "The supplied draft -01 XML contains the frozen 35-field wire "
                "record, five states, five decisions, exact 17-line CoreDone "
                "conjunction and expected state-priority anchors."
            ),
            "inspection": draft_inspection,
        },
        {
            "id": "EA-001",
            "status": "PASS",
            "claim": (
                "Every abstract flag assignment selects exactly one of the five "
                "version-1 states and matches an independently structured "
                "first-match priority oracle."
            ),
            "cases": abstract_assignments,
            "priority_collision_witnesses": priority_collisions,
        },
        {
            "id": "EA-002",
            "status": "PASS",
            "claim": "Ordinary release occurs if and only if the selected state is EFFECT_ACK_DONE and the consumer admission is valid.",
            "cases": abstract_assignments * 2,
        },
        {
            "id": "EA-003",
            "status": "PASS",
            "claim": (
                "Transport acknowledgement is not sufficient for ordinary "
                "release: these assignments contain transport_ack=true but do "
                "not select DONE."
            ),
            "nonrelease_witnesses_with_transport_ack": transport_nonrelease,
            "transport_ack_only_witness_state": State.NACK.value,
        },
        {
            "id": "EA-004",
            "status": "PASS",
            "claim": "Every abstract DONE conjunct is individually necessary in the all-DONE baseline.",
            "conditions": done_conditions,
        },
        {
            "id": "EA-005",
            "status": "PASS_CONDITIONAL",
            "claim": (
                "Under the stated assumptions, a non-DONE state cannot request "
                "ordinary execution through the protected wrapper."
            ),
            "assumptions": [
                "complete mediation of every protected executor path",
                "schema-valid, authenticated, fresh and chain-valid consumer admission",
                "consumer rederivation of state, policy and evidence bindings",
                "a faithful executor for any later physical interpretation",
            ],
            **mediation,
        },
        {
            "id": "EA-006",
            "status": "PASS_MODEL_CONDITIONAL",
            "claim": "A present forecast may change a present decision without a later outcome acting as a backward input.",
            **anticipation,
        },
        {
            "id": "REP-001",
            "status": "PASS_BOUNDED_MODEL",
            "claim": (
                "The toy canonical repository codec is injective, exactly "
                "decodable and replica-stable over its complete bounded universe."
            ),
            **repository_codec,
        },
        {
            "id": "RE-001",
            "status": "PASS_BOUNDED_MODEL_WITH_COUNTEREXAMPLES",
            "claim": (
                "In the complete finite universes tested, effect-relevant "
                "semantics factors through an observation exactly when it is "
                "constant on observation fibers; exact historical inversion "
                "requires injectivity."
            ),
            **factorization_and_inversion,
        },
        {
            "id": "RUNTIME-001",
            "status": (
                "PASS_FULL_FIELD_SET"
                if runtime_inspection["fullDraft01FieldSet"]
                else "CONTINUE_PARTIAL_CORE_ONLY"
            ),
            "claim": (
                "Static field inspection reports whether the current Python "
                "ResponsibilityProtocol record has the exact draft -01 wire field set."
            ),
            "inspection": runtime_inspection,
        },
    ]

    return {
        "schemaVersion": "1.0.0",
        "model": MODEL_ID,
        "overallStatus": "PASS_WITH_EXPLICIT_BOUNDARIES",
        "implementationStatus": (
            "DONE_FULL_FIELD_SET"
            if runtime_inspection["fullDraft01FieldSet"]
            else "CONTINUE_DRAFT01_WIRE_IMPLEMENTATION"
        ),
        "inputs": {
            "ietfDraftText": file_sha256(draft_txt),
            "ietfDraftXml": draft_inspection,
            "pythonReferenceRuntime": runtime_inspection,
        },
        "abstractModel": {
            "booleanFields": len(BOOLEAN_FIELDS),
            "connectionDecisions": len(Decision),
            "effectCheckableReception": (
                "input_identifier_available AND input_digest_valid; "
                "transport_ack remains a separate CoreDone condition"
            ),
            "assignments": abstract_assignments,
            "consumerAdmissionVariants": abstract_assignments * 2,
        },
        "stateCounts": state_counts,
        "checks": checks,
        "boundaries": {
            "modelToSpecBinding": (
                "STRUCTURAL_XML_ANCHORS_CHECKED; BEHAVIORAL REFINEMENT OF EVERY "
                "WIRE, PARSER, AUTHENTICATION AND DEPLOYMENT PATH NOT PROVED"
            ),
            "fullDraft01WireConformance": "CONTINUE_NOT_PROVED_BY_THIS_MODEL",
            "pythonRuntimeBehavior": "NOT_PROVED_BY_ABSTRACT_ENUMERATION",
            "deploymentNonBypassability": (
                "CONDITIONAL_ON_COMPLETE_MEDIATION_AND_NO_SIDE_CHANNEL"
            ),
            "physicalSafety": "REQUIRES_HARDWARE_SENSOR_ACTUATOR_FAULT_MODEL_AND_EMPIRICAL_VALIDATION",
            "universalHistoricalOrSemanticReconstruction": "FALSE_WITHOUT_INJECTIVE_INFORMATION_COMPLETE_OBSERVATION",
            "semanticReconstructionEngine": "OUTSIDE_MODEL",
            "universalPolicyOrEvidenceLanguage": "NOT_DEFINED_BY_DRAFT_01",
            "universalTerminationOrEventualDONE": "NOT_PROVED",
            "computabilityAndResources": (
                "EXECUTABLE RECONSTRUCTION REQUIRES EFFECTIVE COMPUTABILITY, "
                "SUFFICIENT ACCESS, AUTHORIZATION, TIME AND RESOURCES"
            ),
            "ietfConsensusOrRfcStatus": "NOT_CLAIMED",
        },
    }


def main() -> int:
    require(__debug__, "optimized Python mode (-O) is not permitted for this proof run")
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft-txt", type=Path, required=True)
    parser.add_argument("--draft-xml", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_report(args.draft_txt, args.draft_xml, args.runtime)
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
