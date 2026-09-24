#!/usr/bin/env python3
"""Canonical TEMDD event/evidence IR projections.

This module projects the already durable TEMDD ledger into a stable semantic
boundary. Projection never upgrades transport, persistence, a result, or an
assertion inside a payload into EFFECT_ACK, authority, or evidence truth.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
EVENT_ID = re.compile(r"[0-9a-f]{32}:[1-9][0-9]{0,18}\Z")
EPISTEMIC = frozenset({"TRUE", "FALSE", "UNKNOWN", "CONFLICT", "STALE", "UNOBSERVABLE"})
FRESHNESS = frozenset({"FRESH", "STALE"})


class SemanticIRHold(ValueError):
    """Fail-closed semantic projection failure."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise SemanticIRHold(label)
    if len(value) != len(set(value)):
        raise SemanticIRHold(label + "_DUPLICATE")
    return list(value)


def exact_subject(subject: Mapping[str, Any]) -> dict[str, Any]:
    required = {"repository", "pr", "head", "tree"}
    if not isinstance(subject, Mapping) or set(subject) != required:
        raise SemanticIRHold("EXACT_SUBJECT_REQUIRED")
    repository = subject["repository"]
    pr = subject["pr"]
    head = subject["head"]
    tree = subject["tree"]
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise SemanticIRHold("REPOSITORY_REQUIRED")
    if isinstance(pr, bool) or not isinstance(pr, int) or pr < 1:
        raise SemanticIRHold("PR_REQUIRED")
    if not isinstance(head, str) or HEX40.fullmatch(head) is None:
        raise SemanticIRHold("HEAD_REQUIRED")
    if not isinstance(tree, str) or HEX40.fullmatch(tree) is None:
        raise SemanticIRHold("TREE_REQUIRED")
    return {"repository": repository, "pr": pr, "head": head, "tree": tree}


def subject_id(subject: Mapping[str, Any]) -> str:
    return "sha256:" + digest(exact_subject(subject))


def project_event(record: Mapping[str, Any]) -> dict[str, Any]:
    """Project one persisted qikvrt_temdd_event_v1 ledger record to canonical IR."""
    if not isinstance(record, Mapping) or record.get("schema") != "qikvrt_temdd_event_v1":
        raise SemanticIRHold("PERSISTED_TEMDD_EVENT_REQUIRED")
    subject = exact_subject(record.get("subject"))
    event_id = record.get("id")
    if not isinstance(event_id, str) or EVENT_ID.fullmatch(event_id) is None:
        raise SemanticIRHold("LEDGER_EVENT_ID_REQUIRED")
    kind = record.get("kind")
    if kind not in {"OBSERVE", "CLASSIFY", "ACTION", "EFFECT", "READBACK", "SUCCESSOR", "HOLD"}:
        raise SemanticIRHold("EVENT_TYPE_REQUIRED")
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        raise SemanticIRHold("PROVENANCE_REQUIRED")
    producer = provenance.get("source")
    native_event_id = provenance.get("native_event_id")
    source_order = provenance.get("source_order")
    if producer not in {"repository", "transputer"}:
        raise SemanticIRHold("PRODUCER_REQUIRED")
    if not isinstance(native_event_id, str) or not native_event_id:
        raise SemanticIRHold("PRODUCER_EVENT_ID_REQUIRED")
    if isinstance(source_order, bool) or not isinstance(source_order, int) or source_order < 0:
        raise SemanticIRHold("SOURCE_ORDER_REQUIRED")
    observation_order = record.get("observation_order")
    if isinstance(observation_order, bool) or not isinstance(observation_order, int) or observation_order < 1:
        raise SemanticIRHold("OBSERVATION_ORDER_REQUIRED")
    timestamp = record.get("observed_at")
    emitted_at = record.get("emitted_at")
    if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
        raise SemanticIRHold("OBSERVATION_TIMESTAMP_REQUIRED")
    if not isinstance(emitted_at, str) or not emitted_at.endswith("Z"):
        raise SemanticIRHold("EMISSION_TIMESTAMP_REQUIRED")
    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        raise SemanticIRHold("PAYLOAD_OBJECT_REQUIRED")
    ledger_digest = record.get("ledger_digest")
    if not isinstance(ledger_digest, str) or HEX64.fullmatch(ledger_digest) is None:
        raise SemanticIRHold("LEDGER_DIGEST_REQUIRED")
    if record.get("evidence_transfer") != "DENY" or record.get("dod") is not False:
        raise SemanticIRHold("FAIL_CLOSED_LEDGER_FLAGS_REQUIRED")

    causes = _string_list(payload.get("cause_event_ids", []), "CAUSE_EVENT_IDS_INVALID")
    inputs = _string_list(payload.get("inputs", []), "INPUT_REFS_INVALID")
    outputs = _string_list(payload.get("outputs", []), "OUTPUT_REFS_INVALID")
    evidence_refs = _string_list(payload.get("evidence_refs", []), "EVIDENCE_REFS_INVALID")
    decision = payload.get("decision", "UNSPECIFIED")
    if not isinstance(decision, str) or not decision:
        raise SemanticIRHold("DECISION_INVALID")

    return {
        "schema": "temdd_event_ir_v1",
        "event_id": event_id,
        "event_type": kind,
        "subject_id": subject_id(subject),
        "subject_repository": subject["repository"],
        "subject_pr": subject["pr"],
        "subject_head": subject["head"],
        "subject_tree": subject["tree"],
        "producer": producer,
        "producer_event_id": native_event_id,
        "timestamp": timestamp,
        "emitted_at": emitted_at,
        "source_order": source_order,
        "observation_order": observation_order,
        "cause_event_ids": causes,
        "inputs": inputs,
        "outputs": outputs,
        "evidence_refs": evidence_refs,
        "decision": decision,
        "content_digest": ledger_digest,
        "evidence_transfer": "DENY",
    }


def project_evidence(
    event: Mapping[str, Any],
    *,
    evidence_id: str,
    evidence_type: str,
    content_digest: str,
    freshness: str,
    epistemic: str,
) -> dict[str, Any]:
    """Construct evidence IR from one canonical TEMDD event projection."""
    if not isinstance(event, Mapping) or event.get("schema") != "temdd_event_ir_v1":
        raise SemanticIRHold("CANONICAL_EVENT_IR_REQUIRED")
    if not isinstance(evidence_id, str) or not evidence_id:
        raise SemanticIRHold("EVIDENCE_ID_REQUIRED")
    if not isinstance(evidence_type, str) or not evidence_type:
        raise SemanticIRHold("EVIDENCE_TYPE_REQUIRED")
    if not isinstance(content_digest, str) or HEX64.fullmatch(content_digest) is None:
        raise SemanticIRHold("EVIDENCE_DIGEST_REQUIRED")
    if freshness not in FRESHNESS:
        raise SemanticIRHold("EVIDENCE_FRESHNESS_INVALID")
    if epistemic not in EPISTEMIC:
        raise SemanticIRHold("EVIDENCE_EPISTEMIC_INVALID")
    subject = {
        "repository": event["subject_repository"],
        "pr": event["subject_pr"],
        "head": event["subject_head"],
        "tree": event["subject_tree"],
    }
    return {
        "schema": "temdd_evidence_ir_v1",
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "observed_subject": {
            "subject_id": subject_id(subject),
            **exact_subject(subject),
        },
        "producer_event": event["event_id"],
        "content_digest": content_digest,
        "freshness": freshness,
        "epistemic": epistemic,
        "provenance": {
            "producer": event["producer"],
            "producer_event_id": event["producer_event_id"],
            "source_order": event["source_order"],
            "observation_order": event["observation_order"],
            "observed_at": event["timestamp"],
        },
        "evidence_transfer": "DENY",
    }


def evidence_admitted(evidence: Mapping[str, Any], subject: Mapping[str, Any]) -> bool:
    """Only fresh evidence bound to exactly the same subject is admissible."""
    if not isinstance(evidence, Mapping) or evidence.get("schema") != "temdd_evidence_ir_v1":
        return False
    if evidence.get("evidence_transfer") != "DENY" or evidence.get("freshness") != "FRESH":
        return False
    observed = evidence.get("observed_subject")
    if not isinstance(observed, Mapping):
        return False
    exact = exact_subject(subject)
    return (
        observed.get("subject_id") == subject_id(exact)
        and all(observed.get(key) == exact[key] for key in ("repository", "pr", "head", "tree"))
    )
