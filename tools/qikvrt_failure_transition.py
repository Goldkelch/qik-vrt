#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Resolve a causal failure into the next admissible transition."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "qikvrt_failure_transition_v1"


class TransitionResolutionError(ValueError):
    pass


def _normalize(raw: Mapping[str, Any]) -> dict[str, Any]:
    capability_id = raw.get("id")
    transition = raw.get("transition")
    rank = raw.get("rank")
    admissible = raw.get("admissible")
    if not isinstance(capability_id, str) or not capability_id:
        raise TransitionResolutionError("capability id must be a non-empty string")
    if not isinstance(transition, str) or not transition:
        raise TransitionResolutionError("capability transition must be a non-empty string")
    if isinstance(rank, bool) or not isinstance(rank, int) or rank < 0:
        raise TransitionResolutionError("capability rank must be a non-negative integer")
    if not isinstance(admissible, bool):
        raise TransitionResolutionError("capability admissible must be boolean")
    return {
        "id": capability_id,
        "transition": transition,
        "rank": rank,
        "admissible": admissible,
        "evidence": raw.get("evidence"),
    }


def resolve_failure(
    *,
    cause: str,
    capabilities: Sequence[Mapping[str, Any]] = (),
    external_effect: Mapping[str, Any] | None = None,
    wake_condition: str | None = None,
) -> dict[str, Any]:
    if not isinstance(cause, str) or not cause.strip():
        raise TransitionResolutionError("cause must be a non-empty string")

    candidates = sorted(
        (_normalize(item) for item in capabilities),
        key=lambda item: (item["rank"], item["id"]),
    )
    admissible = [item for item in candidates if item["admissible"]]
    if admissible:
        selected = admissible[0]
        return {
            "schema": SCHEMA,
            "state": "INTERNAL_TRANSITION_REQUIRED",
            "cause": cause.strip(),
            "deadlock": False,
            "retry_permitted": True,
            "identical_retry_permitted": False,
            "candidate_count": len(admissible),
            "selected_capability": selected,
            "next_action": selected["transition"],
            "effect_observed": False,
        }

    if external_effect is not None:
        if not isinstance(external_effect, Mapping) or not external_effect:
            raise TransitionResolutionError("external_effect must be a non-empty mapping")
        if not isinstance(wake_condition, str) or not wake_condition.strip():
            raise TransitionResolutionError(
                "wake_condition is required for an external transition"
            )
        return {
            "schema": SCHEMA,
            "state": "EXTERNAL_TRANSITION_REQUIRED",
            "cause": cause.strip(),
            "deadlock": True,
            "retry_permitted": False,
            "identical_retry_permitted": False,
            "candidate_count": 0,
            "required_external_effect": dict(external_effect),
            "wake_condition": wake_condition.strip(),
            "next_action": "MATERIALIZE_REQUIRED_EXTERNAL_EFFECT",
            "effect_observed": False,
        }

    return {
        "schema": SCHEMA,
        "state": "FAIL_CLOSED",
        "cause": cause.strip(),
        "deadlock": False,
        "retry_permitted": False,
        "identical_retry_permitted": False,
        "candidate_count": 0,
        "next_action": None,
        "effect_observed": False,
    }
