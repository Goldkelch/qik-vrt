# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Reference mapping for the QIK-VRT event mesh quadratic VHDL codec.

The mapping is deliberately total and lossless for a finite frame:
``NODES * NODES`` lanes, each containing ``WORD_BITS`` bits.  A lane at
``(row, column)`` has index ``row * NODES + column``; its bits are serialized
least-significant bit first.  No clock, timer, retry loop, or polling source is
part of this reference function.
"""
from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction

from src.qikvrt_deterministic_admission import (
    DeterministicDisposition,
    deterministic_disposition,
)


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


def ideal_raw_frame_rate(clock_hz: int, nodes: int, word_bits: int) -> Fraction:
    """Return the no-stall payload-only frame-rate upper bound.

    This is ``CLOCK_HZ / (N*N*WORD_BITS)``.  It is not a receipt rate and
    cannot be used as a benchmark for a workload with hashing, storage, or
    network effects.
    """
    _positive("clock_hz", clock_hz)
    return Fraction(clock_hz, serial_payload_handshakes(nodes, word_bits))




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
