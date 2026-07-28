#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Build the canonical Zenodo union corpus and begin content-claim disposition.

This transaction is deliberately truth-bounded. It unifies two already
persisted evidence sets:

* the authenticated deposition-API observation (11 records), and
* the public reconciliation of the 13 historical minimum IDs.

It does not claim that natural-language content has been fully proved. Instead,
it constructs one canonical record inventory, groups version/concept lines and
byte-equivalent payloads, and opens a deterministic claim-disposition queue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections import defaultdict
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "release" / "zenodo-corpus-proof-2026-07-28"
INVENTORY_PATH = BASE / "ZENODO_CORPUS_INVENTORY.json"
PROOF_INDEX_PATH = BASE / "ZENODO_CORPUS_PROOF_INDEX.json"
OBSERVED_ENVELOPE_DIR = BASE / "proof-envelopes"
RECONCILIATION_DIR = BASE / "public-record-reconciliation"
RECONCILIATION_RECEIPT_PATH = RECONCILIATION_DIR / "PUBLIC_RECORD_RECONCILIATION_RECEIPT.json"
RECONCILED_ENVELOPE_DIR = RECONCILIATION_DIR / "proof-envelopes"
OUTPUT_DIR = BASE / "canonical-union"

CANONICAL_UNION_PATH = OUTPUT_DIR / "CANONICAL_UNION_CORPUS.json"
DISPOSITION_INDEX_PATH = OUTPUT_DIR / "CONTENT_CLAIM_DISPOSITION_INDEX.json"
DISPOSITION_QUEUE_PATH = OUTPUT_DIR / "CONTENT_CLAIM_DISPOSITION_QUEUE.json"
RECEIPT_PATH = OUTPUT_DIR / "CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json"
REPORT_PATH = OUTPUT_DIR / "CANONICAL_UNION_REPORT_DE.md"

SCHEMA_UNION = "qikvrt_zenodo_canonical_union_corpus_v1"
SCHEMA_INDEX = "qikvrt_content_claim_disposition_index_v1"
SCHEMA_QUEUE = "qikvrt_content_claim_disposition_queue_v1"
SCHEMA_RECEIPT = "qikvrt_canonical_union_and_disposition_receipt_v1"
UNION_ID = "qikvrt-zenodo-canonical-union-2026-07-28-v1"
WORK_UNIT_ID = "BUILD-CANONICAL-UNION-CORPUS-AND-BEGIN-CONTENT-CLAIM-DISPOSITION-20260728"

EXPECTED_OBSERVED_IDS = {
    21267021,
    21482023,
    21498773,
    21500322,
    21515074,
    21529081,
    21582781,
    21633411,
    21636774,
    21640160,
    21640173,
}
EXPECTED_RECONCILED_IDS = {
    20712301,
    21244412,
    21245282,
    21245951,
    21247297,
    21247388,
    21252415,
    21252649,
    21266670,
    21488116,
    21498774,
    21501365,
    21518464,
}
EXPECTED_TOTAL = 24
FIRST_BATCH_SIZE = 6
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class UnionError(RuntimeError):
    """Fail-closed union or disposition construction error."""


def fail(message: str):
    raise UnionError(message)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UnionError(f"missing required input: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise UnionError(f"invalid JSON input: {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        fail(f"top-level JSON object required: {path.relative_to(ROOT)}")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def pretty_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_text(path: pathlib.Path, text: str, *, check: bool) -> None:
    if check:
        try:
            existing = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise UnionError(f"missing generated output in --check mode: {path.relative_to(ROOT)}") from exc
        if existing != text:
            fail(f"generated output drift: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: pathlib.Path, value: Any, *, check: bool) -> None:
    write_text(path, pretty_text(value), check=check)


def positive_int(raw: Any, label: str) -> int:
    if isinstance(raw, bool):
        fail(f"{label} must be a positive integer")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise UnionError(f"{label} must be a positive integer") from exc
    if value <= 0:
        fail(f"{label} must be a positive integer")
    return value


def string_or_none(raw: Any) -> str | None:
    return raw if isinstance(raw, str) and raw.strip() else None


def normalized_files(raw_files: Any, *, record_id: int) -> list[dict[str, Any]]:
    if not isinstance(raw_files, list) or not raw_files:
        fail(f"record {record_id} has no public files")
    result: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, raw in enumerate(raw_files):
        if not isinstance(raw, Mapping):
            fail(f"record {record_id} file {index} is not an object")
        name = raw.get("name")
        digest = raw.get("sha256")
        byte_count = raw.get("bytes")
        if not isinstance(name, str) or not name:
            fail(f"record {record_id} file {index} has no name")
        if name in seen_names:
            fail(f"record {record_id} exposes duplicate file name {name!r}")
        seen_names.add(name)
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            fail(f"record {record_id} file {name!r} has invalid SHA-256")
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
            fail(f"record {record_id} file {name!r} has invalid byte count")
        if raw.get("public_byte_redownload_verified") is not True:
            fail(f"record {record_id} file {name!r} is not public-byte verified")
        md5 = raw.get("md5")
        result.append(
            {
                "name": name,
                "bytes": byte_count,
                "md5": md5 if isinstance(md5, str) else None,
                "sha256": digest,
                "public_byte_redownload_verified": True,
            }
        )
    return sorted(result, key=lambda item: (item["name"], item["sha256"]))


def envelope_files(envelope: Mapping[str, Any], *, record_id: int) -> list[dict[str, Any]]:
    direct = envelope.get("public_files")
    if isinstance(direct, list):
        return normalized_files(direct, record_id=record_id)
    record = envelope.get("record")
    if isinstance(record, Mapping):
        nested = record.get("public_files")
        if isinstance(nested, list):
            return normalized_files(nested, record_id=record_id)
    fail(f"record {record_id} envelope exposes no public files")


def named_fileset_signature(files: Sequence[Mapping[str, Any]]) -> str:
    payload = [
        {"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
        for item in files
    ]
    return sha256_bytes(canonical_bytes(payload))


def payload_multiset_signature(files: Sequence[Mapping[str, Any]]) -> str:
    payload = sorted(
        ({"bytes": item["bytes"], "sha256": item["sha256"]} for item in files),
        key=lambda item: (item["sha256"], item["bytes"]),
    )
    return sha256_bytes(canonical_bytes(payload))


def content_candidate_names(files: Sequence[Mapping[str, Any]]) -> list[str]:
    result: list[str] = []
    allowed_suffixes = {
        ".md", ".txt", ".pdf", ".tex", ".html", ".htm", ".xml",
        ".json", ".lean", ".cff", ".csv", ".rst", ".docx", ".odt",
    }
    for item in files:
        name = str(item["name"])
        suffix = pathlib.PurePosixPath(name).suffix.casefold()
        if suffix in allowed_suffixes:
            result.append(name)
    return sorted(result)


def proof_bundle_candidate(files: Sequence[Mapping[str, Any]]) -> bool:
    names = [str(item["name"]).upper() for item in files]
    has_claim_matrix = any("CLAIM_MATRIX" in name for name in names)
    has_kernel_receipt = any("KERNEL_RECEIPT" in name for name in names)
    has_formal_source = any(name.endswith(".LEAN") for name in names)
    return has_claim_matrix and has_kernel_receipt and has_formal_source


def source_artifact(path: pathlib.Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def disposition_for_record(*, claim_coverage: str, required_action: str, files: Sequence[Mapping[str, Any]]) -> tuple[str, str, int]:
    if claim_coverage == "EXISTING_MACHINE_CLAIM_DISPOSITION_BOUND":
        return (
            "EXISTING_CLAIM_GRAPH_REVALIDATION_PENDING",
            required_action or "VERIFY_EXISTING_CLAIM_GRAPH_AND_NO_CONTENT_CHANGE",
            0,
        )
    if proof_bundle_candidate(files):
        return (
            "MACHINE_PROOF_BUNDLE_BINDING_PENDING",
            "VALIDATE_EXISTING_MACHINE_PROOF_BUNDLE_AND_BIND_CONTENT_CLAIMS",
            1,
        )
    if content_candidate_names(files):
        return (
            "CLAIM_EXTRACTION_PENDING",
            required_action or "CONTENT_CLAIM_EXTRACTION_REVIEW_AND_POSSIBLE_VERSIONED_CORRECTION",
            2,
        )
    return (
        "ARCHIVE_CONTENT_EXTRACTION_PENDING",
        required_action or "EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS",
        3,
    )


def build_observed_records(inventory: Mapping[str, Any], proof_index: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if inventory.get("schema") != "qikvrt_zenodo_corpus_inventory_v1":
        fail("unexpected authenticated inventory schema")
    if proof_index.get("schema") != "qikvrt_zenodo_corpus_proof_index_v1":
        fail("unexpected authenticated proof-index schema")
    inventory_rows = inventory.get("records")
    proof_rows = proof_index.get("records")
    if not isinstance(inventory_rows, list) or not isinstance(proof_rows, list):
        fail("authenticated inventory/proof-index records must be arrays")

    inventory_by_id: dict[int, Mapping[str, Any]] = {}
    for row in inventory_rows:
        if not isinstance(row, Mapping):
            fail("authenticated inventory contains non-object record")
        record_id = positive_int(row.get("record_id"), "authenticated record_id")
        if record_id in inventory_by_id:
            fail(f"duplicate authenticated inventory record {record_id}")
        inventory_by_id[record_id] = row

    proof_by_id: dict[int, Mapping[str, Any]] = {}
    for row in proof_rows:
        if not isinstance(row, Mapping):
            fail("authenticated proof index contains non-object record")
        record_id = positive_int(row.get("record_id"), "proof-index record_id")
        if record_id in proof_by_id:
            fail(f"duplicate authenticated proof-index record {record_id}")
        proof_by_id[record_id] = row

    if set(inventory_by_id) != EXPECTED_OBSERVED_IDS:
        fail(f"authenticated observed ID set drift: expected {sorted(EXPECTED_OBSERVED_IDS)}, got {sorted(inventory_by_id)}")
    if set(proof_by_id) != EXPECTED_OBSERVED_IDS:
        fail("authenticated proof-index ID set does not match inventory")

    records: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = [source_artifact(INVENTORY_PATH), source_artifact(PROOF_INDEX_PATH)]
    for record_id in sorted(EXPECTED_OBSERVED_IDS):
        row = inventory_by_id[record_id]
        proof = proof_by_id[record_id]
        envelope_path = OBSERVED_ENVELOPE_DIR / f"zenodo-{record_id}.json"
        envelope = read_json(envelope_path)
        artifacts.append(source_artifact(envelope_path))
        files = envelope_files(envelope, record_id=record_id)
        claim_coverage = str(proof.get("claim_coverage") or "RETROSPECTIVE_RECORD_LEVEL_ENVELOPE_ONLY")
        required_action = str(proof.get("required_action") or "CONTENT_CLAIM_EXTRACTION_REVIEW_AND_POSSIBLE_VERSIONED_CORRECTION")
        disposition_state, disposition_action, priority = disposition_for_record(
            claim_coverage=claim_coverage,
            required_action=required_action,
            files=files,
        )
        records.append({
            "record_id": record_id,
            "doi": string_or_none(row.get("doi")),
            "conceptdoi": string_or_none(row.get("conceptdoi")),
            "title": string_or_none(row.get("title")),
            "version": string_or_none(row.get("version")),
            "metadata_binding_status": "AUTHENTICATED_PUBLIC_METADATA_BOUND",
            "source_membership": ["AUTHENTICATED_API_OBSERVATION"],
            "public_record_canonical_sha256": string_or_none(row.get("public_record_canonical_sha256")),
            "published_state_verified": row.get("published_state_verified") is True,
            "public_files": files,
            "public_file_count": len(files),
            "named_fileset_sha256": named_fileset_signature(files),
            "payload_multiset_sha256": payload_multiset_signature(files),
            "content_candidate_files": content_candidate_names(files),
            "claim_coverage": claim_coverage,
            "disposition_state": disposition_state,
            "required_action": disposition_action,
            "queue_priority": priority,
            "envelope_path": envelope_path.relative_to(ROOT).as_posix(),
        })
    return records, artifacts


def build_reconciled_records(receipt: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if receipt.get("schema") != "qikvrt_public_record_reconciliation_receipt_v1":
        fail("unexpected public reconciliation receipt schema")
    if receipt.get("state") != "RECONCILED":
        fail("public reconciliation receipt is not RECONCILED")
    rows = receipt.get("records")
    if not isinstance(rows, list):
        fail("public reconciliation receipt records must be an array")
    by_id: dict[int, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            fail("public reconciliation receipt contains non-object record")
        record_id = positive_int(row.get("record_id"), "reconciled record_id")
        if record_id in by_id:
            fail(f"duplicate reconciled record {record_id}")
        by_id[record_id] = row
    if set(by_id) != EXPECTED_RECONCILED_IDS:
        fail(f"reconciled ID set drift: expected {sorted(EXPECTED_RECONCILED_IDS)}, got {sorted(by_id)}")

    records: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = [source_artifact(RECONCILIATION_RECEIPT_PATH)]
    for record_id in sorted(EXPECTED_RECONCILED_IDS):
        row = by_id[record_id]
        envelope_path = RECONCILED_ENVELOPE_DIR / f"zenodo-{record_id}.json"
        envelope = read_json(envelope_path)
        artifacts.append(source_artifact(envelope_path))
        files = envelope_files(envelope, record_id=record_id)
        if row.get("public_record_visible") is not True:
            fail(f"reconciled record {record_id} is not publicly visible")
        if row.get("published_state_verified") is not True:
            fail(f"reconciled record {record_id} has no verified published state")
        if row.get("creator_attributed_to_ingolf_lohmann") is not True:
            fail(f"reconciled record {record_id} is not attributed to Ingolf Lohmann")
        if row.get("failure") is not None:
            fail(f"reconciled record {record_id} carries failure {row.get('failure')!r}")
        claim_coverage = "RETROSPECTIVE_RECORD_LEVEL_ENVELOPE_ONLY"
        disposition_state, disposition_action, priority = disposition_for_record(
            claim_coverage=claim_coverage,
            required_action="CONTENT_CLAIM_EXTRACTION_REVIEW_AND_POSSIBLE_VERSIONED_CORRECTION",
            files=files,
        )
        public_hash = envelope.get("public_record_canonical_sha256")
        records.append({
            "record_id": record_id,
            "doi": string_or_none(row.get("doi")),
            "conceptdoi": string_or_none(row.get("conceptdoi")),
            "title": None,
            "version": None,
            "metadata_binding_status": "PUBLIC_IDENTITY_BOUND_TITLE_VERSION_NOT_CAPTURED",
            "source_membership": ["PUBLIC_HISTORICAL_RECONCILIATION"],
            "public_record_canonical_sha256": public_hash if isinstance(public_hash, str) else None,
            "published_state_verified": True,
            "public_files": files,
            "public_file_count": len(files),
            "named_fileset_sha256": named_fileset_signature(files),
            "payload_multiset_sha256": payload_multiset_signature(files),
            "content_candidate_files": content_candidate_names(files),
            "claim_coverage": claim_coverage,
            "disposition_state": disposition_state,
            "required_action": disposition_action,
            "queue_priority": priority,
            "envelope_path": envelope_path.relative_to(ROOT).as_posix(),
        })
    return records, artifacts


def concept_groups(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get("conceptdoi") or f"record:{record['record_id']}")].append(record)
    result: list[dict[str, Any]] = []
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda row: int(row["record_id"]))
        result.append({
            "concept_key": key,
            "record_ids": [int(row["record_id"]) for row in members],
            "record_count": len(members),
            "version_relation_status": "SINGLE_RECORD" if len(members) == 1 else "MULTI_RECORD_LINE_REQUIRES_CONTENT_AWARE_VERSION_ORDER",
        })
    return result


def payload_clusters(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record["payload_multiset_sha256"])].append(record)
    result: list[dict[str, Any]] = []
    for signature in sorted(groups):
        members = sorted(groups[signature], key=lambda row: int(row["record_id"]))
        result.append({
            "cluster_id": f"PAYLOAD-{signature[:16]}",
            "payload_multiset_sha256": signature,
            "record_ids": [int(row["record_id"]) for row in members],
            "record_count": len(members),
            "byte_equivalence_scope": "ordered multiset of public file byte-count and SHA-256 pairs; filenames ignored",
            "duplicate_payload": len(members) > 1,
        })
    return result


def subject_state(members: Sequence[Mapping[str, Any]]) -> tuple[str, str, int]:
    states = {str(member["disposition_state"]) for member in members}
    if "EXISTING_CLAIM_GRAPH_REVALIDATION_PENDING" in states:
        return ("EXISTING_CLAIM_GRAPH_REVALIDATION_PENDING", "VERIFY_EXISTING_CLAIM_GRAPH_AND_NO_CONTENT_CHANGE", 0)
    if "MACHINE_PROOF_BUNDLE_BINDING_PENDING" in states:
        return ("MACHINE_PROOF_BUNDLE_BINDING_PENDING", "VALIDATE_EXISTING_MACHINE_PROOF_BUNDLE_AND_BIND_CONTENT_CLAIMS", 1)
    if "CLAIM_EXTRACTION_PENDING" in states:
        return ("CLAIM_EXTRACTION_PENDING", "EXTRACT_AND_CLASSIFY_CONTENT_CLAIMS", 2)
    return ("ARCHIVE_CONTENT_EXTRACTION_PENDING", "EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS", 3)


def claim_subjects(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record["payload_multiset_sha256"])].append(record)
    subjects: list[dict[str, Any]] = []
    for signature, raw_members in groups.items():
        members = sorted(raw_members, key=lambda row: int(row["record_id"]))
        state, action, priority = subject_state(members)
        candidate_files = sorted({str(name) for member in members for name in member.get("content_candidate_files", [])})
        subjects.append({
            "subject_id": f"SUBJECT-{signature[:16]}",
            "payload_multiset_sha256": signature,
            "representative_record_id": int(members[0]["record_id"]),
            "record_ids": [int(member["record_id"]) for member in members],
            "conceptdois": sorted({str(member["conceptdoi"]) for member in members if member.get("conceptdoi")}),
            "titles": sorted({str(member["title"]) for member in members if member.get("title")}),
            "content_candidate_files": candidate_files,
            "disposition_state": state,
            "required_action": action,
            "queue_priority": priority,
            "content_change_required": "UNDETERMINED_PENDING_CLAIM_REVIEW",
            "claim_count": None,
            "claim_disposition_complete": False,
        })
    return sorted(subjects, key=lambda subject: (int(subject["queue_priority"]), int(subject["representative_record_id"]), str(subject["subject_id"])))


def build_outputs(observed_at: str):
    inventory = read_json(INVENTORY_PATH)
    proof_index = read_json(PROOF_INDEX_PATH)
    reconciliation_receipt = read_json(RECONCILIATION_RECEIPT_PATH)

    observed_records, observed_artifacts = build_observed_records(inventory, proof_index)
    reconciled_records, reconciled_artifacts = build_reconciled_records(reconciliation_receipt)

    observed_ids = {int(record["record_id"]) for record in observed_records}
    reconciled_ids = {int(record["record_id"]) for record in reconciled_records}
    if observed_ids & reconciled_ids:
        fail(f"source corpora overlap: {sorted(observed_ids & reconciled_ids)}")
    records = sorted(observed_records + reconciled_records, key=lambda row: int(row["record_id"]))
    if len(records) != EXPECTED_TOTAL:
        fail(f"canonical union must contain {EXPECTED_TOTAL} records, got {len(records)}")
    if {int(record["record_id"]) for record in records} != EXPECTED_OBSERVED_IDS | EXPECTED_RECONCILED_IDS:
        fail("canonical union ID set mismatch")

    concept_lines = concept_groups(records)
    payloads = payload_clusters(records)
    subjects = claim_subjects(records)
    first_batch = subjects[:FIRST_BATCH_SIZE]
    remaining = subjects[FIRST_BATCH_SIZE:]

    source_artifacts = sorted(observed_artifacts + reconciled_artifacts, key=lambda item: item["path"])
    source_binding_sha256 = sha256_bytes(canonical_bytes(source_artifacts))
    union_payload = {"records": records, "concept_lines": concept_lines, "payload_clusters": payloads}
    union_content_sha256 = sha256_bytes(canonical_bytes(union_payload))

    union = {
        "_license": {"classification": "machine_readable_canonical_zenodo_union_corpus", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
        "schema": SCHEMA_UNION,
        "union_id": UNION_ID,
        "work_unit_id": WORK_UNIT_ID,
        "observed_at": observed_at,
        "source_corpora": {"authenticated_observation_record_count": len(observed_records), "public_reconciliation_record_count": len(reconciled_records), "source_sets_disjoint": True},
        "record_count": len(records),
        "record_ids": [int(record["record_id"]) for record in records],
        "records": records,
        "concept_line_count": len(concept_lines),
        "concept_lines": concept_lines,
        "payload_cluster_count": len(payloads),
        "duplicate_payload_cluster_count": sum(1 for cluster in payloads if cluster["duplicate_payload"]),
        "payload_clusters": payloads,
        "source_artifacts": source_artifacts,
        "source_binding_sha256": source_binding_sha256,
        "canonical_union_content_sha256": union_content_sha256,
    }

    index_records = [{
        "record_id": int(record["record_id"]),
        "doi": record["doi"],
        "conceptdoi": record["conceptdoi"],
        "title": record["title"],
        "version": record["version"],
        "metadata_binding_status": record["metadata_binding_status"],
        "payload_multiset_sha256": record["payload_multiset_sha256"],
        "claim_coverage": record["claim_coverage"],
        "disposition_state": record["disposition_state"],
        "required_action": record["required_action"],
        "queue_priority": record["queue_priority"],
        "content_change_required": "UNDETERMINED_PENDING_CLAIM_REVIEW",
        "claim_disposition_complete": False,
    } for record in records]
    index = {
        "_license": {"classification": "machine_readable_content_claim_disposition_index", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
        "schema": SCHEMA_INDEX,
        "union_id": UNION_ID,
        "work_unit_id": WORK_UNIT_ID,
        "observed_at": observed_at,
        "state": "STARTED",
        "record_count": len(index_records),
        "claim_subject_count": len(subjects),
        "records": index_records,
        "claim_subjects": subjects,
        "completion_claims": {"content_claim_disposition_started": True, "all_content_claims_dispositioned": False, "content_correction_review_complete": False, "all_required_corrected_candidates_returned_to_owner": False},
    }

    queue = {
        "_license": {"classification": "machine_readable_content_claim_disposition_queue", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
        "schema": SCHEMA_QUEUE,
        "union_id": UNION_ID,
        "work_unit_id": WORK_UNIT_ID,
        "observed_at": observed_at,
        "state": "ACTIVE",
        "ordering": ["existing claim graph revalidation", "machine-proof bundle binding", "direct text/content claim extraction", "archive extraction before claim review", "representative record ID ascending"],
        "batch_size": FIRST_BATCH_SIZE,
        "active_batch": {"batch_id": "CONTENT-DISPOSITION-BATCH-001", "subjects": first_batch, "subject_count": len(first_batch), "state": "READY"},
        "remaining_subject_count": len(remaining),
        "remaining_subject_ids": [subject["subject_id"] for subject in remaining],
        "completion_claims": {"queue_constructed": True, "first_batch_selected": True, "first_batch_executed": False, "all_content_claims_dispositioned": False},
        "next_deterministic_effect": "EXECUTE_CONTENT_DISPOSITION_BATCH_001",
    }

    receipt_payload = {
        "union_id": UNION_ID,
        "work_unit_id": WORK_UNIT_ID,
        "observed_at": observed_at,
        "source_binding_sha256": source_binding_sha256,
        "canonical_union_content_sha256": union_content_sha256,
        "record_count": len(records),
        "observed_record_count": len(observed_records),
        "reconciled_record_count": len(reconciled_records),
        "claim_subject_count": len(subjects),
        "first_batch_subject_count": len(first_batch),
        "concept_line_count": len(concept_lines),
        "payload_cluster_count": len(payloads),
        "duplicate_payload_cluster_count": union["duplicate_payload_cluster_count"],
    }
    receipt = {
        "_license": {"classification": "machine_readable_canonical_union_and_disposition_receipt", "copyright": "Copyright 2026 Ingolf Lohmann", "license": "CC-BY-NC-ND-4.0", "rights_holder": "Ingolf Lohmann"},
        "schema": SCHEMA_RECEIPT,
        **receipt_payload,
        "receipt_payload_sha256": sha256_bytes(canonical_bytes(receipt_payload)),
        "state": "CANONICAL_UNION_BUILT_CONTENT_DISPOSITION_STARTED",
        "validation": {
            "authenticated_source_set_exact": observed_ids == EXPECTED_OBSERVED_IDS,
            "reconciled_source_set_exact": reconciled_ids == EXPECTED_RECONCILED_IDS,
            "source_sets_disjoint": not bool(observed_ids & reconciled_ids),
            "canonical_union_record_count": len(records) == EXPECTED_TOTAL,
            "all_records_have_verified_public_files": all(bool(record["public_files"]) and all(file["public_byte_redownload_verified"] for file in record["public_files"]) for record in records),
            "one_disposition_row_per_record": len(index_records) == len(records),
            "payload_equivalence_collapsed_to_claim_subjects": len(subjects) <= len(records),
            "first_batch_selected": len(first_batch) > 0,
            "no_false_completion": True,
        },
        "completion_claims": {
            "canonical_union_built": True,
            "content_claim_disposition_started": True,
            "all_content_claims_dispositioned": False,
            "content_correction_review_complete": False,
            "all_required_corrected_candidates_returned_to_owner": False,
            "proof_corpus_published_on_zenodo": False,
            "mirror_synchronized": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
        "next_deterministic_effect": "EXECUTE_CONTENT_DISPOSITION_BATCH_001",
    }

    report_lines = [
        "<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->",
        "<!-- Copyright 2026 Ingolf Lohmann. -->",
        "",
        "# Kanonischer Zenodo-Vereinigungsbestand und Beginn der Inhalts-Claim-Disposition",
        "",
        f"Beobachtungszeitpunkt: `{observed_at}`",
        "",
        "## Vereinigungsbestand",
        "",
        f"- Authentisiert beobachtete Records: **{len(observed_records)}**",
        f"- Öffentlich rekonsilierte historische Records: **{len(reconciled_records)}**",
        f"- Kanonische Record-Identitäten: **{len(records)}**",
        f"- Concept-Linien: **{len(concept_lines)}**",
        f"- Payload-Cluster: **{len(payloads)}**",
        f"- Bytegleiche Mehrfach-Cluster: **{union['duplicate_payload_cluster_count']}**",
        f"- Einmalig zu prüfende Claim-Subjects: **{len(subjects)}**",
        "",
        "Die zwei Quellmengen sind disjunkt. Bytegleiche Veröffentlichungen werden nicht mehrfach als unabhängige Inhaltsgegenstände behandelt, sondern über ihren Payload-Multiset-Hash zu einem Claim-Subject zusammengeführt.",
        "",
        "## Inhalts-Claim-Disposition",
        "",
        "Die Disposition wurde gestartet, aber noch nicht abgeschlossen. Jeder Record und jedes byteäquivalente Claim-Subject besitzt nun einen terminal benannten nächsten Prüfschritt.",
        "",
        "| Priorität | Subject | Record-IDs | Zustand | Nächster Effekt |",
        "|---:|---|---|---|---|",
    ]
    for subject in first_batch:
        report_lines.append(f"| {subject['queue_priority']} | `{subject['subject_id']}` | `{','.join(str(value) for value in subject['record_ids'])}` | `{subject['disposition_state']}` | `{subject['required_action']}` |")
    report_lines.extend([
        "",
        "## Wahrheitsgrenze",
        "",
        "- Der Vereinigungsbestand und die Queue sind maschinenlesbar gebunden.",
        "- Noch nicht jede natürliche oder technische Inhaltsbehauptung ist dispositioniert.",
        "- Ob eine historische Veröffentlichung korrigiert werden muss, bleibt bis zur Claim-Prüfung `UNDETERMINED_PENDING_CLAIM_REVIEW`.",
        "- Es wurde kein neuer Zenodo-Upload ausgeführt.",
        "- Mirror-Synchronisation und reziproke Equality-Quittung stehen aus.",
        "",
        "Kein `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE` wird behauptet.",
        "",
        "Nächster deterministischer Effekt:",
        "",
        "```text",
        "EXECUTE_CONTENT_DISPOSITION_BATCH_001",
        "```",
        "",
    ])
    report = "\n".join(report_lines)
    return union, index, queue, receipt, report


def validate_outputs(union: Mapping[str, Any], index: Mapping[str, Any], queue: Mapping[str, Any], receipt: Mapping[str, Any]) -> None:
    if union.get("schema") != SCHEMA_UNION:
        fail("union schema invalid")
    if index.get("schema") != SCHEMA_INDEX:
        fail("disposition index schema invalid")
    if queue.get("schema") != SCHEMA_QUEUE:
        fail("disposition queue schema invalid")
    if receipt.get("schema") != SCHEMA_RECEIPT:
        fail("union receipt schema invalid")
    if union.get("record_count") != EXPECTED_TOTAL:
        fail("union record count invalid")
    record_ids = union.get("record_ids")
    if not isinstance(record_ids, list) or len(record_ids) != EXPECTED_TOTAL:
        fail("union record ID list invalid")
    if set(record_ids) != EXPECTED_OBSERVED_IDS | EXPECTED_RECONCILED_IDS:
        fail("union record ID set invalid")
    if index.get("state") != "STARTED":
        fail("content claim disposition is not STARTED")
    if queue.get("state") != "ACTIVE":
        fail("content claim queue is not ACTIVE")
    completion = receipt.get("completion_claims")
    if not isinstance(completion, Mapping):
        fail("receipt completion claims missing")
    if completion.get("canonical_union_built") is not True:
        fail("receipt does not bind canonical union completion")
    if completion.get("content_claim_disposition_started") is not True:
        fail("receipt does not bind disposition start")
    for key in (
        "all_content_claims_dispositioned",
        "content_correction_review_complete",
        "all_required_corrected_candidates_returned_to_owner",
        "proof_corpus_published_on_zenodo",
        "mirror_synchronized",
        "pass",
        "final_pass",
        "effect_ack_done",
    ):
        if completion.get(key) is not False:
            fail(f"false completion boundary violated: {key}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observed-at", required=True, help="fixed transaction timestamp included in deterministic outputs")
    parser.add_argument("--check", action="store_true", help="verify that committed outputs equal deterministic recomputation")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    union, index, queue, receipt, report = build_outputs(args.observed_at)
    validate_outputs(union, index, queue, receipt)
    write_json(CANONICAL_UNION_PATH, union, check=args.check)
    write_json(DISPOSITION_INDEX_PATH, index, check=args.check)
    write_json(DISPOSITION_QUEUE_PATH, queue, check=args.check)
    write_json(RECEIPT_PATH, receipt, check=args.check)
    write_text(REPORT_PATH, report, check=args.check)
    print(f"CANONICAL_UNION_RECORD_COUNT={union['record_count']}")
    print(f"CLAIM_SUBJECT_COUNT={index['claim_subject_count']}")
    print(f"FIRST_BATCH_SUBJECT_COUNT={queue['active_batch']['subject_count']}")
    print(f"STATE={receipt['state']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
