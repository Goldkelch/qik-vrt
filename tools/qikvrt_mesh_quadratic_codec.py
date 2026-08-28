# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Reference mapping for the QIK-VRT event mesh quadratic VHDL codec.

The mapping is deliberately total and lossless for a finite frame:
``NODES * NODES`` lanes, each containing ``WORD_BITS`` bits.  A lane at
``(row, column)`` has index ``row * NODES + column``; its bits are serialized
least-significant bit first.  No clock, timer, retry loop, or polling source is
part of this reference function.

The protected wire-frame helpers extend, rather than replace, the canonical
payload mapping.  They use an 8-bit sync field, a 32-bit configured session, a
16-bit expected sequence and a CRC-16/CCITT tag.  A receiver releases a payload
only if all wire values and the expected context match exactly.  The tag detects
the modeled accidental framing errors; it is not an authenticity primitive and
does not claim detection of every channel corruption or constructed collision.
"""
from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from src.qikvrt_deterministic_admission import (
    DeterministicDisposition,
    deterministic_disposition,
)


FRAME_SYNC = 0xA5
FRAME_SYNC_BITS = 8
FRAME_SESSION_BITS = 32
FRAME_SEQUENCE_BITS = 16
FRAME_DIGEST_BITS = 16
FRAME_DIGEST_INITIAL = 0xFFFF
FRAME_DIGEST_POLYNOMIAL = 0x1021


def _positive(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def lane_count(nodes: int) -> int:
    """Return the fixed quadratic lane count for ``nodes`` mesh nodes."""
    _positive("nodes", nodes)
    return nodes * nodes


def frame_bits(nodes: int, word_bits: int) -> int:
    """Return the exact serialized frame width."""
    _positive("word_bits", word_bits)
    return lane_count(nodes) * word_bits


def serial_payload_handshakes(nodes: int, word_bits: int) -> int:
    """Return ready/valid transfers needed for one complete serial frame.

    The RTL emits exactly one frame bit per accepted ``tx_valid``/``tx_ready``
    handshake.  This count is deliberately only a *payload* bound: launch,
    stalls, framing above this codec, hashing, persistence, and mesh delivery
    are separate work and are not included.
    """
    return frame_bits(nodes, word_bits)


def serial_framed_handshakes(nodes: int, word_bits: int) -> int:
    """Return exact wire handshakes for one protected frame.

    The base quadratic payload remains ``N*N*WORD_BITS``.  This bounded
    transport profile adds eight sync bits, thirty-two session bits, sixteen
    sequence bits and sixteen CRC-16 tag bits.  Its wire count is therefore not
    a Receipt/s claim.
    """
    return (
        FRAME_SYNC_BITS
        + FRAME_SESSION_BITS
        + FRAME_SEQUENCE_BITS
        + frame_bits(nodes, word_bits)
        + FRAME_DIGEST_BITS
    )


def ideal_raw_frame_rate(clock_hz: int, nodes: int, word_bits: int) -> Fraction:
    """Return the no-stall payload-only frame-rate upper bound.

    This is ``CLOCK_HZ / (N*N*WORD_BITS)``.  It is not a receipt rate and
    cannot be used as a benchmark for a workload with hashing, storage, or
    network effects.
    """
    _positive("clock_hz", clock_hz)
    return Fraction(clock_hz, serial_payload_handshakes(nodes, word_bits))


def _binary_bits(name: str, bits: Sequence[int], expected_bits: int) -> tuple[int, ...]:
    if len(bits) != expected_bits:
        raise ValueError(f"expected {expected_bits} bits, got {len(bits)}")
    normalized = tuple(bits)
    if any(bit not in (0, 1) for bit in normalized):
        raise ValueError(f"{name} contains a non-bit value")
    return normalized


def _integer_to_lsb_bits(value: int, width: int) -> tuple[int, ...]:
    return tuple((value >> bit) & 1 for bit in range(width))


def _lsb_bits_to_integer(bits: Sequence[int]) -> int:
    return sum(bit << index for index, bit in enumerate(bits))


def _frame_sequence(sequence: int) -> int:
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise ValueError("frame sequence must be an unsigned 16-bit integer")
    if not 0 <= sequence < (1 << FRAME_SEQUENCE_BITS):
        raise ValueError("frame sequence must be an unsigned 16-bit integer")
    return sequence


def _frame_session(session: int) -> int:
    if not isinstance(session, int) or isinstance(session, bool):
        raise ValueError("frame session must be an unsigned 32-bit integer")
    if not 0 <= session < (1 << FRAME_SESSION_BITS):
        raise ValueError("frame session must be an unsigned 32-bit integer")
    return session


def next_expected_sequence(sequence: int) -> int:
    """Advance a finite sequence without wraparound or implicit reuse.

    The highest 16-bit value may be transmitted once.  Continuing requires an
    explicit fresh-session reset/rekeying boundary; reset with the same session
    does not establish cross-reset replay separation.
    """
    sequence = _frame_sequence(sequence)
    if sequence == (1 << FRAME_SEQUENCE_BITS) - 1:
        raise ValueError("frame sequence exhausted; fresh-session reset required")
    return sequence + 1


def frame_digest(session: int, sequence: int, payload_bits: Sequence[int]) -> int:
    """Return the LSB-first CRC-16/CCITT tag used by the RTL wire frame."""
    session = _frame_session(session)
    sequence = _frame_sequence(sequence)
    payload = _binary_bits("payload", payload_bits, len(payload_bits))
    crc = FRAME_DIGEST_INITIAL
    for bit in (
        _integer_to_lsb_bits(session, FRAME_SESSION_BITS)
        + _integer_to_lsb_bits(sequence, FRAME_SEQUENCE_BITS)
        + payload
    ):
        feedback = ((crc >> (FRAME_DIGEST_BITS - 1)) & 1) ^ bit
        crc = (crc << 1) & ((1 << FRAME_DIGEST_BITS) - 1)
        if feedback:
            crc ^= FRAME_DIGEST_POLYNOMIAL
    return crc




def serialize_lanes(lanes: Sequence[int], nodes: int, word_bits: int) -> tuple[int, ...]:
    """Serialize a complete square mesh frame in canonical row-major order."""
    expected_lanes = lane_count(nodes)
    _positive("word_bits", word_bits)
    if len(lanes) != expected_lanes:
        raise ValueError(f"expected {expected_lanes} lanes, got {len(lanes)}")
    limit = 1 << word_bits
    bits: list[int] = []
    for lane in lanes:
        if not isinstance(lane, int) or isinstance(lane, bool) or not 0 <= lane < limit:
            raise ValueError(f"lane must be an unsigned {word_bits}-bit value")
        bits.extend((lane >> bit) & 1 for bit in range(word_bits))
    return tuple(bits)


def deserialize_lanes(bits: Sequence[int], nodes: int, word_bits: int) -> tuple[int, ...]:
    """Invert :func:`serialize_lanes` without heuristic or partial-frame input."""
    expected_bits = frame_bits(nodes, word_bits)
    if len(bits) != expected_bits:
        raise ValueError(f"expected {expected_bits} bits, got {len(bits)}")
    lanes: list[int] = []
    for lane_index in range(lane_count(nodes)):
        word = 0
        offset = lane_index * word_bits
        for bit in range(word_bits):
            value = bits[offset + bit]
            if value not in (0, 1):
                raise ValueError("serialized frame contains a non-bit value")
            word |= value << bit
        lanes.append(word)
    return tuple(lanes)


def serialize_framed_lanes(
    lanes: Sequence[int], nodes: int, word_bits: int, session: int, sequence: int
) -> tuple[int, ...]:
    """Serialize a protected frame with exact sync, session, sequence and tag."""
    session = _frame_session(session)
    sequence = _frame_sequence(sequence)
    payload = serialize_lanes(lanes, nodes, word_bits)
    return (
        _integer_to_lsb_bits(FRAME_SYNC, FRAME_SYNC_BITS)
        + _integer_to_lsb_bits(session, FRAME_SESSION_BITS)
        + _integer_to_lsb_bits(sequence, FRAME_SEQUENCE_BITS)
        + payload
        + _integer_to_lsb_bits(frame_digest(session, sequence, payload), FRAME_DIGEST_BITS)
    )


def deserialize_framed_lanes(
    bits: Sequence[int],
    nodes: int,
    word_bits: int,
    expected_session: int,
    expected_sequence: int,
) -> tuple[int, ...]:
    """Fail closed unless the entire protected wire frame matches exactly.

    The exact modeled short, insertion, reorder, replay/session, and digest
    mismatch cases are rejected before deserialization returns a lane array.
    CRC-16 collisions and unmodeled channel behavior remain outside this
    finite reference claim.
    """
    expected_session = _frame_session(expected_session)
    expected_sequence = _frame_sequence(expected_sequence)
    frame = _binary_bits("framed wire", bits, serial_framed_handshakes(nodes, word_bits))
    sync_end = FRAME_SYNC_BITS
    session_end = sync_end + FRAME_SESSION_BITS
    sequence_end = session_end + FRAME_SEQUENCE_BITS
    payload_end = sequence_end + frame_bits(nodes, word_bits)
    sync = _lsb_bits_to_integer(frame[:sync_end])
    session = _lsb_bits_to_integer(frame[sync_end:session_end])
    sequence = _lsb_bits_to_integer(frame[session_end:sequence_end])
    payload = frame[sequence_end:payload_end]
    digest = _lsb_bits_to_integer(frame[payload_end:])
    if sync != FRAME_SYNC:
        raise ValueError("framed wire sync mismatch")
    if session != expected_session:
        raise ValueError("framed wire session mismatch")
    if sequence != expected_sequence:
        raise ValueError("framed wire sequence mismatch")
    if digest != frame_digest(session, sequence, payload):
        raise ValueError("framed wire digest mismatch")
    return deserialize_lanes(payload, nodes, word_bits)
