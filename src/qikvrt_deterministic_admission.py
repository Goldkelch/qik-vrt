# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Total, fail-closed admission shared by QIK-VRT mesh software and RTL."""
from __future__ import annotations

from enum import Enum


class DeterministicDisposition(str, Enum):
    CONTINUE = "CONTINUE"
    HOLD = "HOLD"
    ACCEPT = "ACCEPT"
    BLOCK = "BLOCK"


def deterministic_disposition(
    frame_complete: bool, canonical_equal: bool, ambiguity_present: bool
) -> DeterministicDisposition:
    """Return the only admission state allowed by the three explicit inputs."""
    for name, value in (
        ("frame_complete", frame_complete),
        ("canonical_equal", canonical_equal),
        ("ambiguity_present", ambiguity_present),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")
    if not frame_complete:
        return DeterministicDisposition.CONTINUE
    if ambiguity_present:
        return DeterministicDisposition.HOLD
    if canonical_equal:
        return DeterministicDisposition.ACCEPT
    return DeterministicDisposition.BLOCK
