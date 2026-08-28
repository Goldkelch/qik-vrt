#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""QIK-VRT EFFECT_ACK reference state machine.

This module implements the five-state effect acknowledgement gate described by
``draft-lohmann-qikvrt-effect-ack-01``.  It deliberately has no network, file
system, subprocess, or user-interface side effects. The synchronous workload
is bounded by configured input limits and guarded by a cooperative deadline.

The check fields in :class:`EffectAckRequest` are verified claims supplied by
an integration boundary; this pure state machine does not authenticate an
origin, inspect an external evidence store, or execute policy code. Production
adapters must derive those claims from authenticated checks, restrict who may
construct release requests, and retain at least one trusted protocol hash (or
signature) outside the chain when adversarial rewrite detection is required.

The central invariant is::

    ordinary_release(result) == (result.state is EFFECT_ACK_DONE)

Technical receipt, a successful function return, or a transport ACK never
constitutes permission for downstream effect on its own.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Sequence


SHA256_RE = re.compile(r"^(?:sha256:)?([0-9a-fA-F]{64})$")
PROTOCOL_SCHEMA = "qikvrt_responsibility_protocol_v1"
DEFAULT_MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
DEFAULT_TIMEOUT_MS = 100
MAX_IDENTIFIER_CHARS = 256
MAX_OWNER_CHARS = 256
MAX_METADATA_ITEMS = 128
MAX_METADATA_ITEM_CHARS = 1024


class EffectState(str, Enum):
    """The complete and closed QIK-VRT EFFECT_ACK state set."""

    EFFECT_NACK = "EFFECT_NACK"
    EFFECT_ACK_CONTINUE = "EFFECT_ACK_CONTINUE"
    EFFECT_ACK_DONE = "EFFECT_ACK_DONE"
    EFFECT_ACK_ISOLATE = "EFFECT_ACK_ISOLATE"
    EFFECT_ACK_BLOCK = "EFFECT_ACK_BLOCK"


# Public protocol constants for callers that prefer the normative wire names
# over enum qualification.  They are enum members, not a second state model.
EFFECT_NACK = EffectState.EFFECT_NACK
EFFECT_ACK_CONTINUE = EffectState.EFFECT_ACK_CONTINUE
EFFECT_ACK_DONE = EffectState.EFFECT_ACK_DONE
EFFECT_ACK_ISOLATE = EffectState.EFFECT_ACK_ISOLATE
EFFECT_ACK_BLOCK = EffectState.EFFECT_ACK_BLOCK


class ConnectionDecision(str, Enum):
    """Responsible disposition requested by the effect gate."""

    UNDECIDED = "UNDECIDED"
    CONTINUE = "CONTINUE"
    RELEASE = "RELEASE"
    ISOLATE = "ISOLATE"
    BLOCK = "BLOCK"


class RiskLevel(str, Enum):
    UNKNOWN = "UNKNOWN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ProtocolIntegrityError(ValueError):
    """Raised when an immutable protocol or its hash chain is inconsistent."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _valid_utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z") or len(value) > 64:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0


def _stable_strings(values: Iterable[str]) -> tuple[str, ...]:
    """Return a normalized, de-duplicated and deterministically sorted tuple."""

    normalized = {
        unicodedata.normalize("NFC", str(value)).strip()
        for value in values
        if str(value).strip()
    }
    return tuple(sorted(normalized))


def _validate_text_collection(
    name: str,
    values: Sequence[str],
    *,
    hash_references: bool = False,
) -> None:
    if len(values) > MAX_METADATA_ITEMS:
        raise ValueError(f"{name} exceeds {MAX_METADATA_ITEMS} items")
    for value in values:
        if len(value) > MAX_METADATA_ITEM_CHARS:
            raise ValueError(
                f"{name} item exceeds {MAX_METADATA_ITEM_CHARS} characters"
            )
        if hash_references and normalize_sha256(value) != value:
            raise ValueError(f"{name} must contain canonical sha256 references")


def _normalize_json(value: Any) -> Any:
    """Normalize a JSON value for deterministic UTF-8 canonicalization."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        raise TypeError("canonical QIK-VRT JSON does not permit floating-point values")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", str(key))
            if normalized_key in result:
                raise ValueError("duplicate key after Unicode NFC normalization")
            result[normalized_key] = _normalize_json(item)
        return result
    if isinstance(value, (tuple, list)):
        return [_normalize_json(item) for item in value]
    raise TypeError(f"not canonical-JSON compatible: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """Serialize deterministic JSON: UTF-8/NFC, sorted keys, no excess space."""

    return json.dumps(
        _normalize_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_identifier(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def normalize_sha256(value: str | None) -> str | None:
    if value is None or not isinstance(value, str):
        return None
    match = SHA256_RE.fullmatch(value.strip())
    if not match:
        return None
    return "sha256:" + match.group(1).lower()


@dataclass(frozen=True, slots=True)
class EffectAckRequest:
    """Immutable evidence snapshot submitted to the synchronous haltpoint.

    ``payload`` is the received information unit.  ``declared_input_hash`` is
    optional, but when supplied it is required to match the payload exactly.
    The payload itself is intentionally excluded from the Responsibility
    Protocol; the protocol binds it by SHA-256 instead.
    """

    protocol_root_id: str
    input_id: str
    payload: bytes | None
    transport_ack: bool
    declared_input_hash: str | None = None
    origin_checked: bool = False
    context_checked: bool = False
    semantics_reconstructed: bool = False
    effect_anticipated: bool = False
    risk_classified: bool = False
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    responsibility_assigned: bool = False
    responsibility_owner: str = ""
    connection_decision: ConnectionDecision = ConnectionDecision.UNDECIDED
    policy_allows_release: bool = False
    reasons: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    required_evidence_refs: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    next_required_checks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.payload is not None and not isinstance(self.payload, bytes):
            raise TypeError("payload must be bytes or None")
        for name in ("protocol_root_id", "input_id", "responsibility_owner"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be str")
        if self.declared_input_hash is not None and not isinstance(
            self.declared_input_hash, str
        ):
            raise TypeError("declared_input_hash must be str or None")
        if not isinstance(self.risk_level, RiskLevel):
            object.__setattr__(self, "risk_level", RiskLevel(self.risk_level))
        if not isinstance(self.connection_decision, ConnectionDecision):
            object.__setattr__(
                self,
                "connection_decision",
                ConnectionDecision(self.connection_decision),
            )
        for name in (
            "transport_ack",
            "origin_checked",
            "context_checked",
            "semantics_reconstructed",
            "effect_anticipated",
            "risk_classified",
            "responsibility_assigned",
            "policy_allows_release",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be bool")
        if len(self.protocol_root_id) > MAX_IDENTIFIER_CHARS:
            raise ValueError(
                f"protocol_root_id exceeds {MAX_IDENTIFIER_CHARS} characters"
            )
        if len(self.input_id) > MAX_IDENTIFIER_CHARS:
            raise ValueError(f"input_id exceeds {MAX_IDENTIFIER_CHARS} characters")
        if len(self.responsibility_owner) > MAX_OWNER_CHARS:
            raise ValueError(
                f"responsibility_owner exceeds {MAX_OWNER_CHARS} characters"
            )
        for name in (
            "reasons",
            "evidence_refs",
            "required_evidence_refs",
            "open_questions",
            "next_required_checks",
        ):
            raw = getattr(self, name)
            if not isinstance(raw, (tuple, list)):
                raise TypeError(f"{name} must be a sequence of strings")
            if len(raw) > MAX_METADATA_ITEMS:
                raise ValueError(f"{name} exceeds {MAX_METADATA_ITEMS} items")
            if any(not isinstance(value, str) for value in raw):
                raise TypeError(f"{name} must contain strings")
        object.__setattr__(
            self,
            "protocol_root_id",
            unicodedata.normalize("NFC", self.protocol_root_id.strip()),
        )
        object.__setattr__(
            self, "input_id", unicodedata.normalize("NFC", self.input_id.strip())
        )
        object.__setattr__(
            self,
            "responsibility_owner",
            unicodedata.normalize("NFC", self.responsibility_owner.strip()),
        )
        for name in (
            "reasons",
            "evidence_refs",
            "required_evidence_refs",
            "open_questions",
            "next_required_checks",
        ):
            object.__setattr__(self, name, _stable_strings(getattr(self, name)))
        for name in ("reasons", "open_questions", "next_required_checks"):
            _validate_text_collection(name, getattr(self, name))
        for name in ("evidence_refs", "required_evidence_refs"):
            _validate_text_collection(
                name, getattr(self, name), hash_references=True
            )


@dataclass(frozen=True, slots=True)
class ResponsibilityProtocol:
    """Immutable, versioned and hash-linked EFFECT_ACK decision record."""

    schema: str
    protocol_root_id: str
    protocol_version: int
    protocol_id: str
    previous_protocol_id: str | None
    previous_protocol_hash: str | None
    protocol_hash: str
    input_id: str
    input_hash: str
    state: EffectState
    transport_ack: bool
    origin_checked: bool
    context_checked: bool
    semantics_reconstructed: bool
    effect_anticipated: bool
    risk_classified: bool
    risk_level: RiskLevel
    responsibility_assigned: bool
    responsibility_owner: str
    connection_decided: bool
    connection_decision: ConnectionDecision
    policy_allows_release: bool
    ordinary_release: bool
    reasons: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    required_evidence_refs: tuple[str, ...]
    open_questions: tuple[str, ...]
    next_required_checks: tuple[str, ...]
    created_utc: str

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, Enum):
                value = value.value
            elif isinstance(value, tuple):
                value = list(value)
            result[item.name] = value
        return result

    def to_json(self, *, pretty: bool = False) -> str:
        if pretty:
            return json.dumps(
                self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2
            )
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ResponsibilityProtocol":
        data = dict(raw)
        data["state"] = EffectState(data["state"])
        data["risk_level"] = RiskLevel(data["risk_level"])
        data["connection_decision"] = ConnectionDecision(
            data["connection_decision"]
        )
        for name in (
            "reasons",
            "evidence_refs",
            "required_evidence_refs",
            "open_questions",
            "next_required_checks",
        ):
            data[name] = tuple(data.get(name, ()))
        protocol = cls(**data)
        verify_protocol(protocol)
        return protocol


@dataclass(frozen=True, slots=True)
class EffectAckResult:
    state: EffectState
    protocol: ResponsibilityProtocol

    def __post_init__(self) -> None:
        if not isinstance(self.state, EffectState):
            raise TypeError("state must be EffectState")
        if not isinstance(self.protocol, ResponsibilityProtocol):
            raise TypeError("protocol must be ResponsibilityProtocol")
        verify_protocol(self.protocol)
        if self.protocol.state is not self.state:
            raise ProtocolIntegrityError("result state and protocol state differ")

    @property
    def ordinary_release(self) -> bool:
        return self.state is EffectState.EFFECT_ACK_DONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "ordinary_release": self.ordinary_release,
            "responsibility_protocol": self.protocol.to_dict(),
        }


_VOLATILE_PROTOCOL_FIELDS = frozenset({"created_utc", "protocol_hash"})


def protocol_hash_projection(protocol: ResponsibilityProtocol) -> dict[str, Any]:
    return {
        key: value
        for key, value in protocol.to_dict().items()
        if key not in _VOLATILE_PROTOCOL_FIELDS
    }


def compute_protocol_hash(protocol: ResponsibilityProtocol) -> str:
    encoded = canonical_json(protocol_hash_projection(protocol)).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def verify_protocol(protocol: ResponsibilityProtocol) -> None:
    """Verify the intrinsic integrity and release invariant of one version."""

    errors: list[str] = []
    if protocol.schema != PROTOCOL_SCHEMA:
        errors.append("unsupported schema")
    for name, limit in (
        ("protocol_root_id", MAX_IDENTIFIER_CHARS),
        ("protocol_id", MAX_IDENTIFIER_CHARS + 32),
        ("input_id", MAX_IDENTIFIER_CHARS),
    ):
        value = getattr(protocol, name)
        if not isinstance(value, str) or not value or len(value) > limit:
            errors.append(f"{name} must be a non-empty bounded string")
    if not _valid_utc_timestamp(protocol.created_utc):
        errors.append("created_utc must be an RFC 3339 UTC timestamp")
    if not isinstance(protocol.responsibility_owner, str) or len(
        protocol.responsibility_owner
    ) > MAX_OWNER_CHARS:
        errors.append("responsibility_owner must be a bounded string")
    for name in (
        "transport_ack",
        "origin_checked",
        "context_checked",
        "semantics_reconstructed",
        "effect_anticipated",
        "risk_classified",
        "responsibility_assigned",
        "connection_decided",
        "policy_allows_release",
        "ordinary_release",
    ):
        if type(getattr(protocol, name)) is not bool:
            errors.append(f"{name} must be bool")
    if not isinstance(protocol.state, EffectState):
        errors.append("state must be EffectState")
    if not isinstance(protocol.risk_level, RiskLevel):
        errors.append("risk_level must be RiskLevel")
    if not isinstance(protocol.connection_decision, ConnectionDecision):
        errors.append("connection_decision must be ConnectionDecision")
    if type(protocol.protocol_version) is not int:
        errors.append("protocol_version must be int")
    elif protocol.protocol_version < 1:
        errors.append("protocol_version must be positive")
    expected_id = f"{protocol.protocol_root_id}:v{protocol.protocol_version}"
    if protocol.protocol_id != expected_id:
        errors.append("protocol_id does not match root and version")
    if protocol.protocol_version == 1:
        if protocol.previous_protocol_id is not None:
            errors.append("version 1 must not have previous_protocol_id")
        if protocol.previous_protocol_hash is not None:
            errors.append("version 1 must not have previous_protocol_hash")
    elif not protocol.previous_protocol_id or not protocol.previous_protocol_hash:
        errors.append("versioned protocol must link its predecessor")
    if protocol.previous_protocol_id is not None and not isinstance(
        protocol.previous_protocol_id, str
    ):
        errors.append("previous_protocol_id must be string or null")
    elif (
        isinstance(protocol.previous_protocol_id, str)
        and len(protocol.previous_protocol_id) > MAX_IDENTIFIER_CHARS + 32
    ):
        errors.append("previous_protocol_id exceeds size limit")
    if normalize_sha256(protocol.protocol_hash) != protocol.protocol_hash:
        errors.append("protocol_hash must be canonical sha256")
    if (
        protocol.previous_protocol_hash is not None
        and normalize_sha256(protocol.previous_protocol_hash)
        != protocol.previous_protocol_hash
    ):
        errors.append("previous_protocol_hash must be canonical sha256")
    if (
        protocol.input_hash != "UNAVAILABLE"
        and normalize_sha256(protocol.input_hash) != protocol.input_hash
    ):
        errors.append("input_hash must be canonical sha256 or UNAVAILABLE")
    for name in (
        "reasons",
        "evidence_refs",
        "required_evidence_refs",
        "open_questions",
        "next_required_checks",
    ):
        if not isinstance(getattr(protocol, name), tuple):
            errors.append(f"{name} must be immutable tuple")
    try:
        _validate_text_collection("reasons", protocol.reasons)
        _validate_text_collection("open_questions", protocol.open_questions)
        _validate_text_collection(
            "next_required_checks", protocol.next_required_checks
        )
        _validate_text_collection(
            "evidence_refs", protocol.evidence_refs, hash_references=True
        )
        _validate_text_collection(
            "required_evidence_refs",
            protocol.required_evidence_refs,
            hash_references=True,
        )
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    try:
        expected_hash = compute_protocol_hash(protocol)
        if protocol.protocol_hash != expected_hash:
            errors.append("protocol_hash mismatch")
    except (TypeError, ValueError) as exc:
        errors.append(f"protocol canonicalization failed: {exc}")
    release_expected = protocol.state is EffectState.EFFECT_ACK_DONE
    if protocol.ordinary_release != release_expected:
        errors.append("ordinary release is permitted only for EFFECT_ACK_DONE")
    if protocol.state is EffectState.EFFECT_ACK_DONE:
        missing = _done_gate_failures_from_protocol(protocol)
        if missing:
            errors.append("false EFFECT_ACK_DONE: " + ",".join(missing))
    if errors:
        raise ProtocolIntegrityError("; ".join(errors))


def verify_protocol_chain(
    protocols: Sequence[ResponsibilityProtocol],
    *,
    trusted_protocol_hashes: Mapping[str, str] | None = None,
) -> None:
    """Verify intrinsic hashes plus root, version and predecessor links.

    A self-contained hash chain detects accidental mutation relative to the
    hashes it carries.  Detection of an attacker who rewrites the chain and
    recomputes every hash additionally requires at least one hash retained in a
    trusted external store (or a signature layer).  ``trusted_protocol_hashes``
    supplies such anchors as ``{protocol_id: protocol_hash}``.
    """

    if not protocols:
        raise ProtocolIntegrityError("protocol chain is empty")
    for index, protocol in enumerate(protocols):
        verify_protocol(protocol)
        if index == 0:
            if protocol.protocol_version != 1:
                raise ProtocolIntegrityError("protocol chain must start at version 1")
            continue
        previous = protocols[index - 1]
        if protocol.protocol_root_id != previous.protocol_root_id:
            raise ProtocolIntegrityError("protocol root changed within chain")
        if protocol.protocol_version != previous.protocol_version + 1:
            raise ProtocolIntegrityError("protocol versions are not contiguous")
        if protocol.previous_protocol_id != previous.protocol_id:
            raise ProtocolIntegrityError("previous_protocol_id link mismatch")
        if protocol.previous_protocol_hash != previous.protocol_hash:
            raise ProtocolIntegrityError("previous_protocol_hash link mismatch")
        if protocol.input_id != previous.input_id:
            raise ProtocolIntegrityError("input_id changed within protocol chain")
        if protocol.input_hash != previous.input_hash:
            raise ProtocolIntegrityError("input_hash changed within protocol chain")
    if trusted_protocol_hashes is not None:
        if not trusted_protocol_hashes:
            raise ProtocolIntegrityError("trusted protocol anchor set is empty")
        by_id = {protocol.protocol_id: protocol for protocol in protocols}
        matched = False
        for protocol_id, trusted_hash in trusted_protocol_hashes.items():
            if normalize_sha256(trusted_hash) != trusted_hash:
                raise ProtocolIntegrityError("trusted anchor is not canonical sha256")
            if protocol_id not in by_id:
                continue
            matched = True
            if by_id[protocol_id].protocol_hash != trusted_hash:
                raise ProtocolIntegrityError(
                    f"trusted protocol hash mismatch for {protocol_id}"
                )
        if not matched:
            raise ProtocolIntegrityError("no trusted anchor belongs to this chain")


def _done_gate_failures_from_protocol(
    protocol: ResponsibilityProtocol,
) -> tuple[str, ...]:
    failures: list[str] = []
    checks = (
        (protocol.transport_ack, "TRANSPORT_NOT_ACKNOWLEDGED"),
        (
            normalize_sha256(protocol.input_hash) == protocol.input_hash,
            "INPUT_HASH_UNAVAILABLE",
        ),
        (protocol.origin_checked, "ORIGIN_UNCHECKED"),
        (protocol.context_checked, "CONTEXT_UNCHECKED"),
        (protocol.semantics_reconstructed, "SEMANTICS_UNRECONSTRUCTED"),
        (protocol.effect_anticipated, "EFFECT_UNANTICIPATED"),
        (protocol.risk_classified, "RISK_UNCLASSIFIED"),
        (protocol.risk_level is not RiskLevel.UNKNOWN, "RISK_UNKNOWN"),
        (protocol.responsibility_assigned, "RESPONSIBILITY_UNASSIGNED"),
        (bool(protocol.responsibility_owner), "RESPONSIBILITY_OWNER_MISSING"),
        (protocol.connection_decided, "CONNECTION_UNDECIDED"),
        (
            protocol.connection_decision is ConnectionDecision.RELEASE,
            "RELEASE_NOT_SELECTED",
        ),
        (protocol.policy_allows_release, "POLICY_DENIES_RELEASE"),
        (not protocol.open_questions, "OPEN_QUESTIONS_REMAIN"),
        (not protocol.next_required_checks, "REQUIRED_CHECKS_REMAIN"),
        (
            all(
                reference in protocol.evidence_refs
                for reference in protocol.required_evidence_refs
            ),
            "REQUIRED_EVIDENCE_ABSENT",
        ),
    )
    for condition, reason in checks:
        if not condition:
            failures.append(reason)
    return tuple(failures)


class EffectAckEngine:
    """Deterministic evaluator with bounded inputs and cooperative deadline.

    The default clock is local and non-blocking. Dependency injection exists
    for deterministic tests; production callers MUST provide only a trusted,
    non-blocking clock. A preemptive wall-clock guarantee requires an outer
    process supervisor because Python cannot interrupt CPU scheduling.
    """

    def __init__(
        self,
        *,
        max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if type(max_payload_bytes) is not int:
            raise TypeError("max_payload_bytes must be int")
        if max_payload_bytes < 0:
            raise ValueError("max_payload_bytes must be non-negative")
        if not callable(clock_ns):
            raise TypeError("clock_ns must be callable")
        self.max_payload_bytes = max_payload_bytes
        self._clock_ns = clock_ns

    def evaluate(
        self,
        request: EffectAckRequest,
        *,
        previous_protocol: ResponsibilityProtocol | None = None,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        created_utc: str | None = None,
    ) -> EffectAckResult:
        """Evaluate one snapshot and always return one of the five states.

        No application callback or external I/O is performed. If the
        cooperative deadline is exhausted, the result is a protective BLOCK
        with an explicit continuation path. A corrupt predecessor also
        produces a new BLOCK record rather than escaping the effect gate.
        """

        # ``created_utc`` is volatile audit metadata and is excluded from the
        # protocol hash.  Accepting a value rather than an arbitrary timestamp
        # callback keeps the decision path free of user-provided blocking code.
        timestamp = created_utc if created_utc is not None else _utc_now()
        if not _valid_utc_timestamp(timestamp):
            raise ValueError("created_utc must be an RFC 3339 UTC timestamp")

        if type(timeout_ms) is not int:
            raise TypeError("timeout_ms must be int")
        start_ns = self._clock_ns()
        deadline_ns = start_ns + max(timeout_ms, 0) * 1_000_000
        deadline_exceeded = timeout_ms <= 0

        previous_error: str | None = None
        if previous_protocol is not None:
            try:
                verify_protocol(previous_protocol)
            except ProtocolIntegrityError as exc:
                previous_error = str(exc)

        facts = self._evaluate_facts(request)
        if previous_protocol is not None and previous_error is None:
            binding_failures: list[str] = []
            if previous_protocol.protocol_root_id != request.protocol_root_id:
                binding_failures.append("protocol_root_id")
            if previous_protocol.input_id != (request.input_id or "UNAVAILABLE"):
                binding_failures.append("input_id")
            if previous_protocol.input_hash != facts["input_hash"]:
                binding_failures.append("input_hash")
            if binding_failures:
                previous_error = (
                    "previous protocol binding mismatch: "
                    + ",".join(binding_failures)
                )
        deadline_exceeded = deadline_exceeded or self._clock_ns() > deadline_ns

        if previous_error:
            state = EffectState.EFFECT_ACK_BLOCK
            system_reasons = (
                "PREVIOUS_PROTOCOL_INTEGRITY_FAILURE",
                previous_error,
            )
            next_checks = ("REBUILD_OR_RECOVER_VERIFIED_PROTOCOL_CHAIN",)
        elif deadline_exceeded:
            state = EffectState.EFFECT_ACK_BLOCK
            system_reasons = ("SYNCHRONOUS_DEADLINE_EXCEEDED",)
            next_checks = ("CONTINUE_EVIDENCE_CHECK_ASYNCHRONOUSLY",)
        else:
            state, system_reasons, next_checks = self._decide(request, facts)

        incident_evidence: tuple[str, ...] = ()
        protocol_root_override: str | None = None
        build_previous = previous_protocol
        if previous_error and previous_protocol is not None:
            # Do not serialize an untrusted, already-invalid record here: it
            # might contain attacker-controlled unbounded collections.  A
            # bounded forensic handle still makes the incident reproducible.
            incident_material = "|".join(
                (
                    str(previous_protocol.protocol_id)[: MAX_IDENTIFIER_CHARS + 32],
                    str(previous_protocol.protocol_hash)[:71],
                    previous_error[:MAX_METADATA_ITEM_CHARS],
                )
            ).encode("utf-8")
            incident_hash = sha256_identifier(incident_material)
            incident_evidence = (incident_hash,)
            protocol_root_override = "qikvrt:incident:" + incident_hash.removeprefix(
                "sha256:"
            )
            # A damaged or differently bound predecessor cannot be part of a
            # valid chain.  The failure therefore starts a unique quarantined
            # incident chain instead of colliding with the old ``root:v1``.
            build_previous = None

        protocol = self._build_protocol(
            request=request,
            state=state,
            input_hash=facts["input_hash"],
            system_reasons=system_reasons,
            system_next_checks=next_checks,
            system_evidence_refs=incident_evidence,
            protocol_root_override=protocol_root_override,
            created_utc=timestamp,
            previous_protocol=build_previous,
        )

        # Hashing and canonicalization are also inside the synchronous budget.
        if (
            state is not EffectState.EFFECT_ACK_BLOCK
            and self._clock_ns() > deadline_ns
        ):
            protocol = self._build_protocol(
                request=request,
                state=EffectState.EFFECT_ACK_BLOCK,
                input_hash=facts["input_hash"],
                system_reasons=("SYNCHRONOUS_DEADLINE_EXCEEDED",),
                system_next_checks=("CONTINUE_EVIDENCE_CHECK_ASYNCHRONOUSLY",),
                system_evidence_refs=incident_evidence,
                protocol_root_override=protocol_root_override,
                created_utc=timestamp,
                previous_protocol=build_previous,
            )
            state = EffectState.EFFECT_ACK_BLOCK

        verify_protocol(protocol)
        return EffectAckResult(state=state, protocol=protocol)

    def _evaluate_facts(self, request: EffectAckRequest) -> dict[str, Any]:
        payload_too_large = bool(
            request.payload is not None
            and len(request.payload) > self.max_payload_bytes
        )
        declared = normalize_sha256(request.declared_input_hash)
        malformed_declared_hash = bool(
            request.declared_input_hash is not None and declared is None
        )

        if request.payload is None or payload_too_large:
            actual = None
        else:
            actual = sha256_identifier(request.payload)
        hash_mismatch = bool(declared and actual and declared != actual)
        # Draft -03 defines an effect-checkable reception by an available
        # input identifier and digest.  Transport receipt remains a separate
        # mandatory CoreDone conjunct, so its absence selects CONTINUE rather
        # than granting release or erasing an otherwise checkable input.
        effect_checkable = bool(request.input_id and (actual or declared))
        return {
            "effect_checkable": effect_checkable,
            "payload_too_large": payload_too_large,
            "malformed_declared_hash": malformed_declared_hash,
            "hash_mismatch": hash_mismatch,
            "input_hash": actual or declared or "UNAVAILABLE",
        }

    def _decide(
        self, request: EffectAckRequest, facts: Mapping[str, Any]
    ) -> tuple[EffectState, tuple[str, ...], tuple[str, ...]]:
        if not facts["effect_checkable"]:
            return (
                EffectState.EFFECT_NACK,
                ("NO_EFFECT_CHECKABLE_RECEPTION",),
                ("ESTABLISH_EFFECT_CHECKABLE_RECEPTION",),
            )
        integrity_reasons: list[str] = []
        if facts["payload_too_large"]:
            integrity_reasons.append("PAYLOAD_EXCEEDS_SYNCHRONOUS_LIMIT")
        if facts["malformed_declared_hash"]:
            integrity_reasons.append("DECLARED_INPUT_HASH_MALFORMED")
        if facts["hash_mismatch"]:
            integrity_reasons.append("INPUT_HASH_MISMATCH")
        if integrity_reasons:
            return (
                EffectState.EFFECT_ACK_BLOCK,
                tuple(integrity_reasons),
                ("REPAIR_AND_REVERIFY_INPUT_HASH_BINDING",),
            )
        if request.connection_decision is ConnectionDecision.BLOCK:
            return (
                EffectState.EFFECT_ACK_BLOCK,
                ("RESPONSIBLE_CONNECTION_DECISION_BLOCK",),
                ("FOLLOW_DOCUMENTED_REPAIR_OR_REVIEW_PATH",),
            )
        if request.connection_decision is ConnectionDecision.ISOLATE:
            return (
                EffectState.EFFECT_ACK_ISOLATE,
                ("RESPONSIBLE_CONNECTION_DECISION_ISOLATE",),
                ("EXAMINE_EFFECT_IN_CONTAINMENT",),
            )

        provisional = self._provisional_protocol(request, facts["input_hash"])
        missing = _done_gate_failures_from_protocol(provisional)
        if (
            request.connection_decision is ConnectionDecision.RELEASE
            and not missing
        ):
            return (
                EffectState.EFFECT_ACK_DONE,
                ("ALL_RELEASE_GATES_SATISFIED",),
                (),
            )
        return (
            EffectState.EFFECT_ACK_CONTINUE,
            missing or ("EFFECT_CHECK_CONTINUES",),
            missing or ("CONTINUE_RESPONSIBLE_EFFECT_CHECK",),
        )

    def _provisional_protocol(
        self, request: EffectAckRequest, input_hash: str
    ) -> ResponsibilityProtocol:
        """Create a non-hashed temporary record for gate completeness checks."""

        return ResponsibilityProtocol(
            schema=PROTOCOL_SCHEMA,
            protocol_root_id=request.protocol_root_id,
            protocol_version=1,
            protocol_id=f"{request.protocol_root_id}:v1",
            previous_protocol_id=None,
            previous_protocol_hash=None,
            protocol_hash="",
            input_id=request.input_id,
            input_hash=input_hash,
            state=EffectState.EFFECT_ACK_CONTINUE,
            transport_ack=request.transport_ack,
            origin_checked=request.origin_checked,
            context_checked=request.context_checked,
            semantics_reconstructed=request.semantics_reconstructed,
            effect_anticipated=request.effect_anticipated,
            risk_classified=request.risk_classified,
            risk_level=request.risk_level,
            responsibility_assigned=request.responsibility_assigned,
            responsibility_owner=request.responsibility_owner,
            connection_decided=(
                request.connection_decision is not ConnectionDecision.UNDECIDED
            ),
            connection_decision=request.connection_decision,
            policy_allows_release=request.policy_allows_release,
            ordinary_release=False,
            reasons=(),
            evidence_refs=request.evidence_refs,
            required_evidence_refs=request.required_evidence_refs,
            open_questions=request.open_questions,
            next_required_checks=request.next_required_checks,
            created_utc="",
        )

    def _build_protocol(
        self,
        *,
        request: EffectAckRequest,
        state: EffectState,
        input_hash: str,
        system_reasons: Iterable[str],
        system_next_checks: Iterable[str],
        system_evidence_refs: Iterable[str],
        protocol_root_override: str | None,
        created_utc: str,
        previous_protocol: ResponsibilityProtocol | None,
    ) -> ResponsibilityProtocol:
        reasons = _stable_strings((*request.reasons, *system_reasons))
        next_checks = _stable_strings(
            (*request.next_required_checks, *system_next_checks)
        )
        evidence_refs = _stable_strings(
            (*request.evidence_refs, *system_evidence_refs)
        )

        deterministic = {
            "input_id": request.input_id or "UNAVAILABLE",
            "input_hash": input_hash,
            "state": state,
            "transport_ack": request.transport_ack,
            "origin_checked": request.origin_checked,
            "context_checked": request.context_checked,
            "semantics_reconstructed": request.semantics_reconstructed,
            "effect_anticipated": request.effect_anticipated,
            "risk_classified": request.risk_classified,
            "risk_level": request.risk_level,
            "responsibility_assigned": request.responsibility_assigned,
            "responsibility_owner": request.responsibility_owner,
            "connection_decided": (
                request.connection_decision is not ConnectionDecision.UNDECIDED
            ),
            "connection_decision": request.connection_decision,
            "policy_allows_release": request.policy_allows_release,
            "ordinary_release": state is EffectState.EFFECT_ACK_DONE,
            "reasons": reasons,
            "evidence_refs": evidence_refs,
            "required_evidence_refs": request.required_evidence_refs,
            "open_questions": request.open_questions,
            "next_required_checks": next_checks,
        }

        if previous_protocol is not None and self._same_decision_content(
            previous_protocol, deterministic
        ):
            return previous_protocol

        version = 1 if previous_protocol is None else previous_protocol.protocol_version + 1
        root = protocol_root_override or request.protocol_root_id or "UNAVAILABLE"
        previous_id = None if previous_protocol is None else previous_protocol.protocol_id
        previous_hash = (
            None if previous_protocol is None else previous_protocol.protocol_hash
        )
        unhashed = ResponsibilityProtocol(
            schema=PROTOCOL_SCHEMA,
            protocol_root_id=root,
            protocol_version=version,
            protocol_id=f"{root}:v{version}",
            previous_protocol_id=previous_id,
            previous_protocol_hash=previous_hash,
            protocol_hash="",
            created_utc=created_utc,
            **deterministic,
        )
        protocol_hash = compute_protocol_hash(unhashed)
        return ResponsibilityProtocol(
            **{
                **unhashed.to_dict(),
                "state": unhashed.state,
                "risk_level": unhashed.risk_level,
                "connection_decision": unhashed.connection_decision,
                "reasons": unhashed.reasons,
                "evidence_refs": unhashed.evidence_refs,
                "required_evidence_refs": unhashed.required_evidence_refs,
                "open_questions": unhashed.open_questions,
                "next_required_checks": unhashed.next_required_checks,
                "protocol_hash": protocol_hash,
            }
        )

    @staticmethod
    def _same_decision_content(
        previous: ResponsibilityProtocol, deterministic: Mapping[str, Any]
    ) -> bool:
        for key, value in deterministic.items():
            if getattr(previous, key) != value:
                return False
        return True


def effect_ack_sync(
    request: EffectAckRequest,
    *,
    previous_protocol: ResponsibilityProtocol | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    created_utc: str | None = None,
) -> EffectAckResult:
    """Convenience entry point for the synchronous QIK-VRT haltpoint."""

    return EffectAckEngine().evaluate(
        request,
        previous_protocol=previous_protocol,
        timeout_ms=timeout_ms,
        created_utc=created_utc,
    )


def ordinary_release(result: EffectAckResult) -> bool:
    """Return release permission; true for exactly one protocol state."""

    return result.state is EffectState.EFFECT_ACK_DONE


__all__ = [
    "ConnectionDecision",
    "DEFAULT_MAX_PAYLOAD_BYTES",
    "DEFAULT_TIMEOUT_MS",
    "EFFECT_ACK_BLOCK",
    "EFFECT_ACK_CONTINUE",
    "EFFECT_ACK_DONE",
    "EFFECT_ACK_ISOLATE",
    "EFFECT_NACK",
    "EffectAckEngine",
    "EffectAckRequest",
    "EffectAckResult",
    "EffectState",
    "PROTOCOL_SCHEMA",
    "ProtocolIntegrityError",
    "ResponsibilityProtocol",
    "RiskLevel",
    "canonical_json",
    "compute_protocol_hash",
    "effect_ack_sync",
    "normalize_sha256",
    "ordinary_release",
    "protocol_hash_projection",
    "sha256_identifier",
    "verify_protocol",
    "verify_protocol_chain",
]
