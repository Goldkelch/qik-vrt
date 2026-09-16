#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure scope guards; caller-supplied observations are not independently verified."""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

POLICY_PATH = "policy/QIKVRT_GLOBAL_NOOP_EXCLUSION_V1.json"
GLOBAL_CLAIMS = (
    "PASS", "FINAL_PASS", "EFFECT_ACK_DONE", "ZERO_BUGS", "REPOSITORY_NOOP",
    "P2_PASS", "REVIEW_APPROVED", "MAIN_INTEGRATION", "FULL_SYNC",
    "SYMMETRIC_CANONICALITY",
)


def _git_oid(value: Any) -> bool:
    return isinstance(value, str) and value != "0" * 40 and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def bind_local_result(
    result: Mapping[str, Any], *, source_head: str, source_tree: str
) -> dict[str, Any]:
    """Bind source identity, not validation or authority; retain the local state ABI."""
    if not isinstance(result, Mapping) or not _git_oid(source_head) or not _git_oid(source_tree):
        raise ValueError("local result requires an exact source head and tree")
    if result.get("state") in ("DONE", "FINAL_PASS", "EFFECT_ACK_DONE", "REPOSITORY_NOOP"):
        raise ValueError("terminal global state cannot be relabeled as a local result")
    for key, expected in (("state_scope", "LOCAL_OPERATION"),
                          ("repository_completion", "NOT_EVALUATED"),
                          ("subject_binding", "SOURCE_ONLY_NOT_VALIDATION")):
        if key in result and result[key] != expected:
            raise ValueError("local result has conflicting " + key)
    claims = result.get("completion_claims", {})
    if not isinstance(claims, Mapping):
        raise ValueError("completion_claims must be an object")
    for claim in GLOBAL_CLAIMS:
        if result.get(claim, False) is not False or claims.get(claim, False) is not False:
            raise ValueError("local result cannot authorize " + claim)
    for key in ("candidate_validation_transferred", "general_effect_ack_done"):
        if result.get(key, False) is not False:
            raise ValueError("local result cannot assert " + key)
    for key, expected in (("source_head", source_head), ("source_tree", source_tree)):
        if key in result and result[key] != expected:
            raise ValueError("local result cannot rebind " + key)
    scoped = dict(result)
    scoped.update({
        "state_scope": "LOCAL_OPERATION",
        "scope_policy": POLICY_PATH,
        "source_head": source_head,
        "source_tree": source_tree,
        "subject_binding": "SOURCE_ONLY_NOT_VALIDATION",
        "repository_completion": "NOT_EVALUATED",
        "candidate_validation_transferred": False,
        "general_effect_ack_done": False,
        "completion_claims": {**claims, **dict.fromkeys(GLOBAL_CLAIMS, False)},
    })
    return scoped


def exact_validation_admissible(
    observation: Mapping[str, Any], *, expected_repository: str,
    expected_head: str, expected_tree: str,
) -> bool:
    """Check binding/shape of supplied readback, not its authenticity or gate coverage.

    A workflow's event head or green conclusion is not its actual checkout.
    A regenerated, dirty worktree is not the committed candidate being validated.
    This predicate never supplies P3, Main, deployment or effect authorization.
    """
    if (
        not isinstance(observation, Mapping)
        or not isinstance(expected_repository, str)
        or re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", expected_repository) is None
        or not _git_oid(expected_head) or not _git_oid(expected_tree)
    ):
        return False
    return (
        observation.get("repository") == expected_repository
        and observation.get("actual_checkout_head") == expected_head
        and observation.get("actual_checkout_tree") == expected_tree
        and observation.get("job_executed") is True
        and observation.get("validation_passed") is True
        and observation.get("worktree_clean") is True
        and observation.get("candidate_validation_transferred") is False
    )
