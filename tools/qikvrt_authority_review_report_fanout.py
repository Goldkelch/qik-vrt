#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bind an Authority review fanout to one executor-run artifact.

``workflow_run.head_sha`` is an execution SHA.  For direct pull-request
review events GitHub executes on the synthetic PR merge ref, so that value is
not authority for the candidate head.  The trusted executor's uniquely named
artifact is the source-run-local binding instead.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


SOURCE_ARTIFACT_NAME = re.compile(
    r"^qikvrt-mesh-review-pr-([1-9][0-9]*)-([0-9a-f]{40})-([0-9a-f]{64})$"
)


class AuthorityReviewReportBindingError(ValueError):
    """Raised when a completed executor run has no exact report subject."""


def source_artifact_binding(*, artifacts: Any) -> dict[str, str | int]:
    """Return one candidate binding from the authenticated source-run artifacts.

    The caller obtains ``artifacts`` from
    ``actions/runs/<source-run-id>/artifacts``. Only an unexpired, exactly
    named executor evidence artifact is accepted. The artifact endpoint
    authenticates its source run; its name supplies the exact PR/head/
    fingerprint tuple. A workflow-run ``pull_requests`` array is deliberately
    not an input: GitHub can omit that advisory association even while the
    source-run artifact remains present and exact.
    """
    if not isinstance(artifacts, Mapping):
        raise AuthorityReviewReportBindingError("SOURCE_RUN_ARTIFACTS_INVALID")
    entries = artifacts.get("artifacts")
    if (
        not isinstance(entries, Sequence)
        or isinstance(entries, (str, bytes))
    ):
        raise AuthorityReviewReportBindingError("SOURCE_RUN_ARTIFACTS_INVALID")

    matches: list[tuple[Mapping[str, Any], re.Match[str]]] = []
    for artifact in entries:
        if not isinstance(artifact, Mapping) or artifact.get("expired") is not False:
            continue
        name = artifact.get("name")
        match = SOURCE_ARTIFACT_NAME.fullmatch(name) if isinstance(name, str) else None
        if match is not None:
            matches.append((artifact, match))
    if len(matches) != 1:
        raise AuthorityReviewReportBindingError(
            "SOURCE_RUN_ARTIFACT_MISSING_OR_AMBIGUOUS"
        )

    artifact, match = matches[0]
    artifact_pr = int(match.group(1))
    name = artifact.get("name")
    assert isinstance(name, str)
    return {
        "artifact_name": name,
        "pr_number": artifact_pr,
        "head_sha": match.group(2),
        "evidence_fingerprint": match.group(3),
    }
