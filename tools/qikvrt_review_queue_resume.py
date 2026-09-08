#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed validation for resuming immutable requested-review queue chains."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

HEX40 = frozenset("0123456789abcdef")
HEX64 = HEX40


class QueueResumeError(ValueError):
    """Raised when a persisted acknowledgement cannot be safely resumed."""


def _sha(value: Any, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in HEX40 for character in value)
    ):
        raise QueueResumeError(f"invalid {label}")
    return value


def classify_existing_queue_ack(
    acknowledgement: Mapping[str, Any] | None,
    *,
    repository: str,
    pr_number: int,
    head_sha: str,
    predecessor_fingerprint: str,
) -> dict[str, Any]:
    """Classify an immutable predecessor acknowledgement without rewriting it.

    An absent acknowledgement means the caller may create the normal
    predecessor->successor edge.  A valid existing acknowledgement means that
    predecessor was already consumed by an earlier causal reobservation and a
    rerun must resume from the durable queue frontier instead of attempting an
    alternate edge at the same append-only path.
    """
    head = _sha(head_sha, 40, "head_sha")
    predecessor = _sha(predecessor_fingerprint, 64, "predecessor_fingerprint")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise QueueResumeError("invalid repository")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number <= 0:
        raise QueueResumeError("invalid pr_number")
    if acknowledgement is None:
        return {
            "state": "ABSENT",
            "predecessor_fingerprint": predecessor,
            "successor_fingerprint": None,
        }
    if not isinstance(acknowledgement, Mapping):
        raise QueueResumeError("acknowledgement is not an object")
    if acknowledgement.get("schema") != "qikvrt_mesh_review_queue_ack_v1":
        raise QueueResumeError("acknowledgement schema mismatch")
    if acknowledgement.get("state") != "SUPERSEDED_BY_CAUSAL_REOBSERVATION":
        raise QueueResumeError("acknowledgement state mismatch")
    if acknowledgement.get("repository") != repository:
        raise QueueResumeError("acknowledgement repository mismatch")
    if acknowledgement.get("pr_number") != pr_number:
        raise QueueResumeError("acknowledgement PR mismatch")
    if acknowledgement.get("head_sha") != head:
        raise QueueResumeError("acknowledgement head mismatch")
    if acknowledgement.get("predecessor_fingerprint") != predecessor:
        raise QueueResumeError("acknowledgement predecessor mismatch")
    successor = _sha(
        acknowledgement.get("successor_fingerprint"),
        64,
        "acknowledgement successor_fingerprint",
    )
    if successor == predecessor:
        raise QueueResumeError("acknowledgement is not causal progress")
    claims = acknowledgement.get("completion_claims")
    if not isinstance(claims, Mapping) or any(claims.get(key) is not False for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE", "MERGE")):
        raise QueueResumeError("acknowledgement completion boundary mismatch")
    return {
        "state": "ALREADY_SUPERSEDED",
        "predecessor_fingerprint": predecessor,
        "successor_fingerprint": successor,
    }
