#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact producer envelope for public EFFECT_ACK finalization evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


WORKFLOW_PATH = ".github/workflows/qikvrt_effect_ack_finalize.yml"
PRODUCER_JOB = "zenodo-finalize"
EVIDENCE_PATH = "zenodo-finalization-evidence.json"
SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class EvidenceTransportError(RuntimeError):
    """The public evidence artifact is not the exact same-run producer output."""


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise EvidenceTransportError(f"{label} differs from the exact producer binding")


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise EvidenceTransportError(f"{label} keys differ from the closed contract")


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def pretty_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def build_transport(
    *,
    evidence_bytes: bytes,
    artifact_name: str,
    repository: str,
    workflow_sha: str,
    head_sha: str,
    run_id: int,
    run_attempt: int,
    marker_sha256: str,
    source_commit: str,
    source_tree: str,
    tag_object_sha: str,
) -> dict[str, Any]:
    value = {
        "schema": "qikvrt_effect_ack_zenodo_evidence_transport_v1",
        "producer": {
            "repository": repository,
            "workflow_path": WORKFLOW_PATH,
            "workflow_sha": workflow_sha,
            "head_sha": head_sha,
            "run_id": run_id,
            "run_attempt": run_attempt,
            "job": PRODUCER_JOB,
        },
        "subject": {
            "marker_sha256": marker_sha256,
            "source_commit": source_commit,
            "source_tree": source_tree,
            "tag_object_sha": tag_object_sha,
        },
        "artifact": {
            "name": artifact_name,
            "evidence_path": EVIDENCE_PATH,
            "evidence_sha256": hashlib.sha256(evidence_bytes).hexdigest(),
        },
    }
    value["transport_sha256"] = _canonical_sha256(value)
    return value


def validate_transport(
    *,
    transport_bytes: bytes,
    evidence_bytes: bytes,
    expected_artifact_name: str,
    expected_repository: str,
    expected_workflow_sha: str,
    expected_head_sha: str,
    expected_run_id: int,
    expected_run_attempt: int,
    expected_marker_sha256: str,
    expected_source_commit: str,
    expected_source_tree: str,
    expected_tag_object_sha: str,
    expected_tag: str,
) -> dict[str, Any]:
    try:
        transport = json.loads(transport_bytes)
        evidence = json.loads(evidence_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceTransportError("transport or evidence is not exact JSON") from error

    _exact_keys(
        transport,
        {"schema", "producer", "subject", "artifact", "transport_sha256"},
        "transport",
    )
    _require(
        transport["schema"],
        "qikvrt_effect_ack_zenodo_evidence_transport_v1",
        "transport schema",
    )
    projection = copy.deepcopy(transport)
    supplied_digest = projection.pop("transport_sha256")
    if not isinstance(supplied_digest, str) or not SHA256_RE.fullmatch(
        supplied_digest
    ):
        raise EvidenceTransportError("transport digest is not lowercase SHA-256")
    _require(supplied_digest, _canonical_sha256(projection), "transport digest")

    producer = transport["producer"]
    _exact_keys(
        producer,
        {
            "repository",
            "workflow_path",
            "workflow_sha",
            "head_sha",
            "run_id",
            "run_attempt",
            "job",
        },
        "producer",
    )
    expected_producer = {
        "repository": expected_repository,
        "workflow_path": WORKFLOW_PATH,
        "workflow_sha": expected_workflow_sha,
        "head_sha": expected_head_sha,
        "run_id": expected_run_id,
        "run_attempt": expected_run_attempt,
        "job": PRODUCER_JOB,
    }
    _require(producer, expected_producer, "producer")

    for value, label in (
        (expected_workflow_sha, "workflow SHA"),
        (expected_head_sha, "head SHA"),
        (expected_source_commit, "source commit"),
        (expected_source_tree, "source tree"),
        (expected_tag_object_sha, "tag object SHA"),
    ):
        if not isinstance(value, str) or not SHA1_RE.fullmatch(value):
            raise EvidenceTransportError(f"expected {label} is not lowercase Git SHA-1")
    if not SHA256_RE.fullmatch(expected_marker_sha256):
        raise EvidenceTransportError("expected marker digest is not lowercase SHA-256")
    if (
        not isinstance(expected_run_id, int)
        or isinstance(expected_run_id, bool)
        or expected_run_id <= 0
        or not isinstance(expected_run_attempt, int)
        or isinstance(expected_run_attempt, bool)
        or expected_run_attempt <= 0
    ):
        raise EvidenceTransportError("expected producer run identity is invalid")

    subject = transport["subject"]
    _exact_keys(
        subject,
        {"marker_sha256", "source_commit", "source_tree", "tag_object_sha"},
        "subject",
    )
    _require(
        subject,
        {
            "marker_sha256": expected_marker_sha256,
            "source_commit": expected_source_commit,
            "source_tree": expected_source_tree,
            "tag_object_sha": expected_tag_object_sha,
        },
        "subject",
    )

    artifact = transport["artifact"]
    _exact_keys(
        artifact,
        {"name", "evidence_path", "evidence_sha256"},
        "artifact",
    )
    _require(artifact["name"], expected_artifact_name, "artifact name")
    _require(artifact["evidence_path"], EVIDENCE_PATH, "artifact evidence path")
    _require(
        artifact["evidence_sha256"],
        hashlib.sha256(evidence_bytes).hexdigest(),
        "artifact evidence digest",
    )

    _exact_keys(
        evidence,
        {
            "schema",
            "client_result",
            "final_manifest_sha256",
            "deposited_files",
            "repository",
            "tag",
            "tag_object_sha",
            "target_commit",
            "target_tree",
            "mirror_annotated_tag_verified",
            "github_release_object_absence_verified_at_tag_effect",
            "datatracker_submission_performed",
        },
        "public evidence",
    )
    if (
        evidence["schema"] != "qikvrt_effect_ack_zenodo_finalization_evidence_v1"
        or evidence["repository"] != expected_repository
        or evidence["tag"] != expected_tag
        or evidence["tag_object_sha"] != expected_tag_object_sha
        or evidence["target_commit"] != expected_source_commit
        or evidence["target_tree"] != expected_source_tree
        or evidence["mirror_annotated_tag_verified"] is not True
        or evidence["github_release_object_absence_verified_at_tag_effect"] is not True
        or evidence["datatracker_submission_performed"] is not False
    ):
        raise EvidenceTransportError("public evidence subject differs from the exact cut")
    if not SHA256_RE.fullmatch(str(evidence["final_manifest_sha256"])):
        raise EvidenceTransportError("public evidence manifest digest is invalid")
    client = evidence["client_result"]
    if (
        not isinstance(client, dict)
        or client.get("phase") != "published"
        or client.get("tag") != expected_tag
        or client.get("repositories")
        != ["Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"]
        or client.get("datatracker_submitted") is not False
    ):
        raise EvidenceTransportError("public evidence client result is not exact")
    deposited = evidence["deposited_files"]
    if not isinstance(deposited, dict) or set(deposited) != {"paper", "software"}:
        raise EvidenceTransportError("public evidence deposited-file set is not exact")
    for kind in ("paper", "software"):
        if not isinstance(deposited[kind], list) or not deposited[kind]:
            raise EvidenceTransportError(f"public evidence has no {kind} files")
    return evidence
