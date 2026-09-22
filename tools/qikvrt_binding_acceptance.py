# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fixed-profile Binding/Acceptance validator; no network or external effects.

An evidence mapping is an input from a trusted, subject-bound evidence evaluator,
NOT evidence authenticated by this module. The CLI supplies no such evaluator and
cannot authorize ACCEPTED. Fixture profiles are used only by private test helpers.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Mapping

FILENAME = 'NDR_DSN_ACCEPTANCE_DELTA_V1(1).json'
DIGEST = '936686c7b6c1e249e8b31215d5111b76a78e494d0ea822a505bd309f946e278e'
PREDICATES = (
    'requirements_approved', 'acceptance_tests_executed',
    'end_to_end_validated', 'communication_effect_ack_done',
    'same_subject_binding', 'current_evidence',
    'no_contradictory_required_evidence',
)
BYTE_IDS = ('VERIFIED', 'NOT_VERIFIED', 'UNKNOWN')
MAX_RECORD_BYTES = 512
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class _Profile:
    filename: str
    digest: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r'[A-Za-z0-9_.()-]+', self.filename):
            raise ValueError('invalid profile filename')
        if not re.fullmatch(r'[0-9a-f]{64}', self.digest):
            raise ValueError('invalid profile digest')


_PROFILE = _Profile(FILENAME, DIGEST)


@dataclass(frozen=True)
class Record:
    byte_id: str
    predicates: tuple[bool, ...]
    status: str


@dataclass(frozen=True)
class Result:
    outcome: str
    reason: str
    observed_byte_id: str = 'UNKNOWN'
    claimed_status: str | None = None
    acceptance_status: str = 'OPEN'
    accepted: bool = False
    external_effect_executed: bool = False


class SyntaxError(ValueError):
    """The complete input does not match the fixed profile's ABNF."""


def _parse(raw: bytes, profile: _Profile) -> Record:
    if type(raw) is not bytes or len(raw) > MAX_RECORD_BYTES:
        raise SyntaxError('invalid-record-bytes')
    first = ('artifact ' + profile.filename + ' sha256 ' + profile.digest
             + ' EXACT_FILE_BYTES\r\n').encode('ascii')
    pattern = (re.escape(first)
               + rb'acceptance (VERIFIED|NOT_VERIFIED|UNKNOWN)'
               + rb'((?: (?:true|false)){7}) (OPEN|ACCEPTED)\r\n')
    match = re.fullmatch(pattern, raw)
    if match is None:
        raise SyntaxError('noncanonical-record')
    return Record(match[1].decode('ascii'),
                  tuple(item == b'true' for item in match[2][1:].split(b' ')),
                  match[3].decode('ascii'))


def parse(raw: bytes) -> Record:
    """Recognize this exact two-line ABNF profile, not general ABNF."""
    return _parse(raw, _PROFILE)


def expected_status(byte_id: str, predicates: tuple[bool, ...]) -> str:
    """Pure state projection. This function does not verify bytes or evidence."""
    if byte_id not in BYTE_IDS:
        raise ValueError('invalid byte identity')
    if (type(predicates) is not tuple or len(predicates) != 7
            or any(type(value) is not bool for value in predicates)):
        raise ValueError('exactly seven actual booleans required')
    return 'ACCEPTED' if byte_id == 'VERIFIED' and all(predicates) else 'OPEN'


def _evidence_projection(evidence: Mapping[str, bool | None] | None) -> tuple[bool, ...]:
    if evidence is None:
        return (False,) * 7
    if not isinstance(evidence, Mapping) or set(evidence) - set(PREDICATES):
        raise ValueError('invalid-evidence-fields')
    values = tuple(evidence.get(name) for name in PREDICATES)
    if any(value is not None and type(value) is not bool for value in values):
        raise ValueError('evidence-values-must-be-bool-or-unknown')
    # false on the wire means not established true; it is not an assertion that
    # the external event did not happen. Missing evidence maps to UNKNOWN/false.
    return tuple(value is True for value in values)


def _validate(raw: bytes, artifact: bytes | None,
              evidence: Mapping[str, bool | None] | None,
              profile: _Profile) -> Result:
    try:
        record = _parse(raw, profile)
    except SyntaxError as error:
        return Result('ABNF_REJECT', str(error))
    if artifact is None:
        return Result('BINDING_REJECT', 'artifact-unavailable',
                      claimed_status=record.status)
    if type(artifact) is not bytes or len(artifact) > MAX_ARTIFACT_BYTES:
        return Result('BINDING_REJECT', 'invalid-artifact-bytes',
                      claimed_status=record.status)
    observed = 'VERIFIED' if hashlib.sha256(artifact).hexdigest() == profile.digest else 'NOT_VERIFIED'
    if observed != 'VERIFIED':
        return Result('BINDING_REJECT', 'artifact-digest-mismatch', observed, record.status)
    if record.byte_id != observed:
        return Result('BINDING_REJECT', 'byte-id-assertion-mismatch', observed, record.status)
    # Binding has priority over semantic failures. The pure projection can be
    # tested independently, but it never overrides an earlier binding rejection.
    if record.status != expected_status(record.byte_id, record.predicates):
        return Result('SEMANTIC_REJECT', 'status-does-not-match-conjunction', observed, record.status)
    try:
        assessed = _evidence_projection(evidence)
    except ValueError as error:
        return Result('SEMANTIC_REJECT', str(error), observed, record.status)
    if assessed != record.predicates:
        return Result('SEMANTIC_REJECT', 'predicates-do-not-match-assessed-evidence', observed, record.status)
    status = expected_status(observed, assessed)
    return Result('VALID', 'record-valid', observed, record.status, status, status == 'ACCEPTED')


def validate(raw: bytes, artifact: bytes | None,
             *, evidence: Mapping[str, bool | None] | None = None) -> Result:
    """Check syntax, bytes, then state/evidence consistency in that order.

    Caller precondition for trusted evidence: assess origin, authority, subject,
    current policy, freshness, contradictions and scope outside this pure kernel.
    A record cannot provide its own evidence. Do not pass its flags as evidence.
    None/missing assessments are unknown, not affirmative evidence. A valid OPEN
    record is not Acceptance. No returned result proves an external effect.
    """
    return _validate(raw, artifact, evidence, _PROFILE)


def _read_regular(path: Path, limit: int) -> bytes:
    if not hasattr(os, 'O_NOFOLLOW'):
        raise OSError('safe no-follow reads unsupported on this platform')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise OSError('not a bounded regular file')
        raw = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
    if len(raw) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise OSError('file changed during read or exceeds limit')
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = _read_regular(args.record, MAX_RECORD_BYTES)
    except OSError:
        result = Result('ABNF_REJECT', 'record-unavailable-or-unsafe')
    else:
        try:
            artifact = _read_regular(args.artifact, MAX_ARTIFACT_BYTES)
        except OSError:
            artifact = None
        result = validate(raw, artifact)
    print(json.dumps(asdict(result), sort_keys=True, allow_nan=False))
    return 0 if result.outcome == 'VALID' else 1


if __name__ == '__main__':
    raise SystemExit(main())
