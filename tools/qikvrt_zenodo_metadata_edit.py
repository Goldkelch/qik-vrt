#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed metadata-only correction of one published Zenodo record.

This capability is intentionally narrower than ``qikvrt_zenodo_publish``.  It
never creates a record, creates a version, deletes a file, or uploads a file.
It reuses the hardened Zenodo transport and the repository-global annotated
Git consumption-ref implementation from the generic publisher.

The effect path is:

    exact local validation -> public before-state gate -> consumption ref
    -> second before-state gate -> edit -> metadata PUT -> republish
    -> public after-state gate -> byte-exact file redownload -> receipt

An interrupted effect remains fail-closed.  Intermediate evidence is retained
and blocks automatic retry; a human-reviewed reconciliation is then required.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any, NoReturn

try:
    from tools import qikvrt_zenodo_actions as zenodo
    from tools import qikvrt_zenodo_machine_proof as proof_gate
    from tools import qikvrt_zenodo_publish as publication
except ModuleNotFoundError:
    import qikvrt_zenodo_actions as zenodo  # type: ignore[no-redef]
    import qikvrt_zenodo_machine_proof as proof_gate  # type: ignore[no-redef]
    import qikvrt_zenodo_publish as publication  # type: ignore[no-redef]


SCHEMA = "qikvrt_zenodo_published_metadata_edit_manifest_v1"
PROOF_SCHEMA = "qikvrt_zenodo_metadata_edit_machine_proof_v1"
AUTHORIZATION_SCHEMA = "qikvrt_zenodo_metadata_edit_owner_authorization_v1"
EVIDENCE_SCHEMA = "qikvrt_zenodo_metadata_edit_evidence_v1"
STATE = "edit_published_metadata"
CONFIRM = "EDIT_PUBLISHED_ZENODO_METADATA_ONLY"
PRODUCTION_REPOSITORY = publication.PRODUCTION_REPOSITORY
HEX32 = re.compile(r"^[0-9a-f]{32}$")
HEX40 = publication.HEX40
HEX64 = publication.HEX64
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
EDITABLE_METADATA_FIELDS = frozenset(
    {"description", "keywords", "notes", "related_identifiers"}
)
IMMUTABLE_TARGET_FIELDS = frozenset(
    {
        "title",
        "upload_type",
        "publication_type",
        "creators",
        "version",
        "publication_date",
        "access_right",
        "license",
        "language",
        "prereserve_doi",
    }
)
OWNER_AUTHORIZED_EFFECTS = (
    "ACQUIRE_REPOSITORY_REMOTE_CONSUMPTION_LOCK",
    "OPEN_PUBLISHED_ZENODO_RECORD_FOR_METADATA_EDIT",
    "REPLACE_EXACT_AUTHORIZED_METADATA_ONLY",
    "REPUBLISH_EXISTING_ZENODO_RECORD",
    "VERIFY_PUBLIC_METADATA_AND_FILES_UNCHANGED",
    "PERSIST_METADATA_EDIT_EVIDENCE",
)
PHASES = (
    "authorization_consumed",
    "edit_requested",
    "metadata_updated",
    "republish_requested",
    "public_verified",
)


def _fail(message: str) -> NoReturn:
    raise zenodo.ZenodoError(message)


def _identity(path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    data = zenodo.read_regular_file(path, zenodo.MAX_UPLOAD_BYTES)
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha": publication._git_blob_sha(data),
    }


def _load_bound_identity(
    value: Any,
    root: pathlib.Path,
    where: str,
    *,
    maximum: int = zenodo.MAX_UPLOAD_BYTES,
) -> tuple[pathlib.Path, dict[str, Any], bytes]:
    if not isinstance(value, dict):
        _fail(f"{where} must be an object")
    zenodo._check_exact_keys(
        value,
        {"path", "bytes", "sha256", "git_blob_sha"},
        where,
    )
    path = publication._safe_relative(
        root,
        value["path"],
        where + ".path",
        must_exist=True,
    )
    data = zenodo.read_regular_file(path, maximum)
    observed = {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha": publication._git_blob_sha(data),
    }
    if value != observed:
        _fail(f"{where} differs from the exact repository bytes")
    return path, observed, data


def _load_bound_json(
    value: Any,
    root: pathlib.Path,
    where: str,
) -> tuple[pathlib.Path, dict[str, Any], dict[str, Any], bytes]:
    path, identity, data = _load_bound_identity(
        value,
        root,
        where,
        maximum=zenodo.MAX_JSON_BYTES,
    )
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"{where} is not canonicalizable UTF-8 JSON: {exc}")
    if not isinstance(parsed, dict) or not zenodo._is_json_value(parsed):
        _fail(f"{where} must contain a JSON object")
    return path, identity, parsed, data


def _canonical_metadata_hash(metadata: Mapping[str, Any]) -> str:
    return hashlib.sha256(zenodo._json_bytes(metadata)).hexdigest()


def _validate_edit_metadata(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not zenodo._is_json_value(value):
        _fail(f"{where} must be a JSON object")
    missing = publication.REQUIRED_METADATA - set(value)
    unknown = set(value) - publication.ALLOWED_METADATA
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unknown=" + ",".join(sorted(unknown)))
        _fail(f"invalid {where} keys (" + "; ".join(details) + ")")
    if "prereserve_doi" in value:
        _fail(
            f"{where}.prereserve_doi is forbidden when editing an existing DOI"
        )
    zenodo._metadata_identity(value, where)
    if value["access_right"] != "open":
        _fail(f"{where}.access_right must equal open")
    if not isinstance(value["description"], str) or not value["description"].strip():
        _fail(f"{where}.description must be non-empty")
    return dict(value)


def _validate_metadata_transition(
    before: Any,
    after: Any,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    before_value = _validate_edit_metadata(before, "metadata_before")
    after_value = _validate_edit_metadata(after, "metadata_after")
    changed = sorted(
        key
        for key in set(before_value) | set(after_value)
        if before_value.get(key) != after_value.get(key)
    )
    if not changed:
        _fail("metadata-only correction must change at least one metadata field")
    forbidden = set(changed) - EDITABLE_METADATA_FIELDS
    if forbidden:
        _fail(
            "metadata-only correction changes a non-allowlisted field: "
            + ",".join(sorted(forbidden))
        )
    for key in IMMUTABLE_TARGET_FIELDS:
        if before_value.get(key) != after_value.get(key):
            _fail(f"metadata-only correction changed immutable field {key}")
    return before_value, after_value, changed


def _validate_target(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("manifest.target must be an object")
    zenodo._check_exact_keys(
        value,
        {
            "record_id",
            "concept_record_id",
            "doi",
            "concept_doi",
            "before_revision",
            "before_etag",
            "before_public_metadata_sha256",
            "expected_after_revision",
        },
        "manifest.target",
    )
    record_id = zenodo._safe_int(value["record_id"], "manifest.target.record_id")
    concept_id = zenodo._safe_int(
        value["concept_record_id"],
        "manifest.target.concept_record_id",
    )
    before_revision = zenodo._safe_int(
        value["before_revision"],
        "manifest.target.before_revision",
    )
    after_revision = zenodo._safe_int(
        value["expected_after_revision"],
        "manifest.target.expected_after_revision",
    )
    if record_id < 1 or concept_id < 1 or before_revision < 1:
        _fail("manifest target record, concept and revision must be positive")
    if after_revision != before_revision + 1:
        _fail("expected after revision must equal before revision plus one")
    doi = value["doi"]
    concept_doi = value["concept_doi"]
    if (
        not isinstance(doi, str)
        or publication.ZENODO_DOI.fullmatch(doi) is None
        or not isinstance(concept_doi, str)
        or publication.ZENODO_DOI.fullmatch(concept_doi) is None
    ):
        _fail("manifest target DOI identities are invalid")
    etag = publication._bounded_text(
        value["before_etag"],
        "manifest.target.before_etag",
        512,
    )
    public_metadata_sha256 = value["before_public_metadata_sha256"]
    if (
        not isinstance(public_metadata_sha256, str)
        or HEX64.fullmatch(public_metadata_sha256) is None
    ):
        _fail("manifest target public metadata digest is invalid")
    return {
        "record_id": record_id,
        "concept_record_id": concept_id,
        "doi": doi,
        "concept_doi": concept_doi,
        "before_revision": before_revision,
        "before_etag": etag,
        "before_public_metadata_sha256": public_metadata_sha256,
        "expected_after_revision": after_revision,
    }


def _validate_files(value: Any) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 100:
        _fail("manifest.files must contain between 1 and 100 immutable files")
    files: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        where = f"manifest.files[{index}]"
        if not isinstance(item, dict):
            _fail(f"{where} must be an object")
        zenodo._check_exact_keys(item, {"name", "size", "md5", "sha256"}, where)
        name = item["name"]
        if (
            not isinstance(name, str)
            or not name
            or pathlib.PurePosixPath(name).name != name
            or name in {".", ".."}
        ):
            _fail(f"{where}.name must be a safe basename")
        size = item["size"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            _fail(f"{where}.size must be a non-negative integer")
        md5 = item["md5"]
        sha256 = item["sha256"]
        if not isinstance(md5, str) or HEX32.fullmatch(md5) is None:
            _fail(f"{where}.md5 must be lowercase hexadecimal")
        if not isinstance(sha256, str) or HEX64.fullmatch(sha256) is None:
            _fail(f"{where}.sha256 must be lowercase hexadecimal")
        files.append({"name": name, "size": size, "md5": md5, "sha256": sha256})
    if [item["name"] for item in files] != sorted(item["name"] for item in files):
        _fail("manifest.files must be sorted by name")
    if len({item["name"] for item in files}) != len(files):
        _fail("manifest.files contains duplicate names")
    return files, hashlib.sha256(zenodo._json_bytes(files)).hexdigest()


def _validate_proof(
    value: Any,
    root: pathlib.Path,
    *,
    publication_id: str,
    target: Mapping[str, Any],
    metadata_before_identity: Mapping[str, Any],
    metadata_after_identity: Mapping[str, Any],
    file_inventory_sha256: str,
) -> dict[str, Any]:
    proof_path, identity, bundle, _raw = _load_bound_json(
        value,
        root,
        "manifest.machine_proof",
    )
    zenodo._check_exact_keys(
        bundle,
        {
            "_license",
            "schema",
            "policy",
            "publication_id",
            "target",
            "metadata_before",
            "metadata_after",
            "file_inventory_sha256",
            "artifacts",
            "claims",
            "prepublication_return",
            "gates",
            "completion_claims",
        },
        "metadata-edit machine proof",
    )
    proof_gate.validate_license(
        bundle["_license"],
        "metadata-edit machine proof._license",
        classification="machine_readable_proof_bundle",
    )
    if bundle["schema"] != PROOF_SCHEMA:
        _fail("unsupported metadata-edit machine-proof schema")
    if bundle["publication_id"] != publication_id:
        _fail("metadata-edit machine proof publication_id differs")
    active_policy = proof_gate.validate_active_policy(root, bundle["policy"])
    if bundle["target"] != dict(target):
        _fail("metadata-edit machine proof target differs")
    if bundle["metadata_before"] != dict(metadata_before_identity):
        _fail("metadata-edit machine proof before metadata differs")
    if bundle["metadata_after"] != dict(metadata_after_identity):
        _fail("metadata-edit machine proof after metadata differs")
    if bundle["file_inventory_sha256"] != file_inventory_sha256:
        _fail("metadata-edit machine proof file inventory differs")

    artifacts = bundle["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        _fail("metadata-edit machine proof artifacts must be non-empty")
    artifacts_by_path: dict[str, dict[str, Any]] = {}
    for index, raw_artifact in enumerate(artifacts):
        where = f"metadata-edit machine proof artifacts[{index}]"
        if not isinstance(raw_artifact, dict):
            _fail(f"{where} must be an object")
        zenodo._check_exact_keys(
            raw_artifact,
            {"path", "bytes", "sha256", "git_blob_sha", "kind"},
            where,
        )
        kind = raw_artifact["kind"]
        if kind not in {
            "CHANGE_NOTICE",
            "RETURN_RECEIPT",
            "SOURCE",
            "EVIDENCE",
            "BOUNDARY_TEST",
            "CLAIM_MATRIX",
            "OTHER",
        }:
            _fail(f"{where}.kind is invalid")
        bound = {key: raw_artifact[key] for key in ("path", "bytes", "sha256", "git_blob_sha")}
        path, observed, _data = _load_bound_identity(bound, root, where)
        relative = path.relative_to(root).as_posix()
        if relative in artifacts_by_path:
            _fail("metadata-edit machine proof contains duplicate artifact paths")
        artifacts_by_path[relative] = {**observed, "kind": kind}
    if proof_path.relative_to(root).as_posix() in artifacts_by_path:
        _fail("metadata-edit machine proof may not self-bind")

    claims = bundle["claims"]
    if not isinstance(claims, list) or not claims:
        _fail("metadata-edit machine proof claims must be non-empty")
    claim_ids: set[str] = set()
    for index, claim in enumerate(claims):
        where = f"metadata-edit machine proof claims[{index}]"
        if not isinstance(claim, dict):
            _fail(f"{where} must be an object")
        zenodo._check_exact_keys(
            claim,
            {
                "claim_id",
                "statement",
                "classification",
                "status",
                "publication_wording",
                "scope",
                "proof_refs",
                "evidence_refs",
                "source_refs",
            },
            where,
        )
        claim_id = publication._bounded_text(claim["claim_id"], where + ".claim_id", 128)
        if SAFE_ID.fullmatch(claim_id) is None or claim_id in claim_ids:
            _fail("metadata-edit machine proof claim IDs must be safe and unique")
        claim_ids.add(claim_id)
        publication._bounded_text(claim["statement"], where + ".statement", 10000, allow_line_breaks=True)
        publication._bounded_text(claim["scope"], where + ".scope", 2000, allow_line_breaks=True)
        classification = claim["classification"]
        if classification not in proof_gate.ALLOWED_CLASSIFICATIONS:
            _fail(f"{where}.classification is invalid")
        expected_status, expected_wording = proof_gate.EXPECTED_DISPOSITION[classification]
        if claim["status"] != expected_status or claim["publication_wording"] != expected_wording:
            _fail(f"{claim_id} disposition differs from {classification}")
        references: dict[str, list[str]] = {}
        for key in ("proof_refs", "evidence_refs", "source_refs"):
            refs = claim[key]
            if (
                not isinstance(refs, list)
                or not all(isinstance(item, str) and item for item in refs)
                or len(refs) != len(set(refs))
            ):
                _fail(f"{where}.{key} must be a unique string list")
            references[key] = refs
            for reference in refs:
                base = proof_gate.reference_base(reference)
                if base not in artifacts_by_path:
                    _fail(f"unresolved {key} reference for {claim_id}: {reference}")
                if "#" in reference:
                    fragment = proof_gate.reference_fragment(reference, f"{where}.{key}")
                    proof_gate.validate_reference_fragment_target(
                        root / base,
                        fragment,
                        f"{where}.{key}",
                    )
        if classification == "FORMAL_PROVED":
            _fail("metadata-edit proof may not introduce FORMAL_PROVED claims")
        if classification == "EMPIRICALLY_EVIDENCED" and not references["evidence_refs"]:
            _fail(f"empirical metadata claim {claim_id} lacks evidence")
        if classification == "SOURCE_BOUND" and not references["source_refs"]:
            _fail(f"source-bound metadata claim {claim_id} lacks a source")
        if classification in {"NORMATIVE", "INTERPRETATIVE", "OPEN"} and references["proof_refs"]:
            _fail(f"{classification} metadata claim {claim_id} may not claim a formal proof")

    returned = bundle["prepublication_return"]
    if not isinstance(returned, dict):
        _fail("metadata-edit machine proof prepublication_return must be an object")
    zenodo._check_exact_keys(
        returned,
        {"content_changed", "candidate_returned_to_owner", "receipt_path", "change_notice_path"},
        "metadata-edit machine proof prepublication_return",
    )
    if returned["content_changed"] is not True or returned["candidate_returned_to_owner"] is not True:
        _fail("metadata correction must be changed content returned to the owner")
    receipt_path = returned["receipt_path"]
    notice_path = returned["change_notice_path"]
    if (
        not isinstance(receipt_path, str)
        or artifacts_by_path.get(receipt_path, {}).get("kind") != "RETURN_RECEIPT"
        or not isinstance(notice_path, str)
        or artifacts_by_path.get(notice_path, {}).get("kind") != "CHANGE_NOTICE"
    ):
        _fail("metadata correction return receipt or change notice is not bound")
    candidate = {
        metadata_after_identity["path"]: {
            "path": metadata_after_identity["path"],
            "bytes": metadata_after_identity["bytes"],
            "sha256": metadata_after_identity["sha256"],
            "git_blob_sha1": metadata_after_identity["git_blob_sha"],
            "role": "PRIMARY",
        }
    }
    receipt = proof_gate.validate_return_receipt(
        root,
        receipt_path,
        publication_id,
        candidate,
        claim_ids,
        True,
        notice_path,
    )
    returned_at = publication._validate_rfc3339(
        receipt["return"]["returned_at"],
        "metadata-edit prepublication return returned_at",
    )

    required_gates = {
        "all_metadata_claims_dispositioned",
        "all_references_resolve",
        "metadata_candidate_frozen",
        "changed_fields_allowlisted",
        "title_unchanged",
        "files_declared_immutable",
        "prepublication_return_complete",
    }
    gates = bundle["gates"]
    if not isinstance(gates, dict):
        _fail("metadata-edit machine proof gates must be an object")
    zenodo._check_exact_keys(gates, required_gates, "metadata-edit machine proof gates")
    if any(gates[key] is not True for key in required_gates):
        _fail("every metadata-edit machine-proof gate must equal true")
    expected_completion = {
        "machine_proof_complete": True,
        "metadata_edit_authorized": True,
        "zenodo_file_upload_authorized": False,
    }
    if bundle["completion_claims"] != expected_completion:
        _fail("metadata-edit completion claims differ from metadata-only scope")
    control_specs = (
        (proof_gate.POLICY_PATH, proof_gate.POLICY_GIT_BLOB_SHA1),
        (
            proof_gate.BUNDLE_SCHEMA_PATH,
            active_policy["schema_contracts"]["machine_proof_bundle"]["git_blob_sha1"],
        ),
        (
            proof_gate.RETURN_SCHEMA_PATH,
            active_policy["schema_contracts"]["prepublication_return_receipt"]["git_blob_sha1"],
        ),
        (proof_gate.LEGACY_POLICY_PATH, proof_gate.LEGACY_POLICY_GIT_BLOB_SHA1),
        (
            proof_gate.LEGACY_BUNDLE_SCHEMA_PATH,
            proof_gate.LEGACY_BUNDLE_SCHEMA_GIT_BLOB_SHA1,
        ),
        (
            proof_gate.LEGACY_RETURN_SCHEMA_PATH,
            proof_gate.LEGACY_RETURN_SCHEMA_GIT_BLOB_SHA1,
        ),
    )
    control_identities: list[dict[str, Any]] = []
    for control_path, expected_blob in control_specs:
        path = publication._safe_relative(
            root,
            control_path,
            "metadata-edit proof control",
            must_exist=True,
        )
        observed = _identity(path, root)
        if observed["git_blob_sha"] != expected_blob:
            _fail("metadata-edit proof control Git identity differs for " + control_path)
        control_identities.append(observed)
    return {
        **identity,
        "schema": PROOF_SCHEMA,
        "publication_id": publication_id,
        "claim_count": len(claims),
        "artifacts": list(artifacts_by_path.values()),
        "control_identities": control_identities,
        "candidate_return_receipt": artifacts_by_path[receipt_path],
        "change_notice": artifacts_by_path[notice_path],
        "returned_at": returned_at,
        "machine_proof_complete": True,
        "metadata_edit_authorized": True,
        "zenodo_file_upload_authorized": False,
    }


def _validate_authorization(
    value: Any,
    root: pathlib.Path,
    *,
    repository: str,
    source_head: str,
    publication_id: str,
    target: Mapping[str, Any],
    metadata_after: Mapping[str, Any],
    machine_proof: Mapping[str, Any],
    file_inventory_sha256: str,
    evidence_path: pathlib.Path,
) -> dict[str, Any]:
    _path, identity, authorization, _raw = _load_bound_json(
        value,
        root,
        "manifest.owner_authorization",
    )
    zenodo._check_exact_keys(
        authorization,
        {
            "_license",
            "schema",
            "authorization_id",
            "nonce",
            "single_use",
            "single_use_scope",
            "principal",
            "publication_id",
            "repository",
            "source_head",
            "target",
            "candidate_return_receipt",
            "canonical_metadata_sha256",
            "machine_proof",
            "file_inventory_sha256",
            "authorized_effects",
            "metadata_edit_evidence_path",
            "authorization_event",
        },
        "metadata-edit owner authorization",
    )
    if authorization["schema"] != AUTHORIZATION_SCHEMA:
        _fail("unsupported metadata-edit owner authorization schema")
    proof_gate.validate_license(
        authorization["_license"],
        "metadata-edit owner authorization._license",
        classification="owner_effect_authorization",
    )
    if authorization["single_use"] is not True or authorization["single_use_scope"] != publication.SINGLE_USE_SCOPE:
        _fail("metadata-edit owner authorization must be repository-global single-use")
    if authorization["repository"] != repository or authorization["source_head"] != source_head:
        _fail("metadata-edit owner authorization repository/source head differs")
    if authorization["publication_id"] != publication_id:
        _fail("metadata-edit owner authorization publication_id differs")
    if authorization["target"] != dict(target):
        _fail("metadata-edit owner authorization target differs")
    if authorization["file_inventory_sha256"] != file_inventory_sha256:
        _fail("metadata-edit owner authorization file inventory differs")
    if authorization["metadata_edit_evidence_path"] != evidence_path.relative_to(root).as_posix():
        _fail("metadata-edit owner authorization evidence path differs")
    principal = authorization["principal"]
    if principal != {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}:
        _fail("metadata-edit owner authorization principal differs")
    authorization_id = authorization["authorization_id"]
    if not isinstance(authorization_id, str) or publication.SAFE_AUTHORIZATION_ID.fullmatch(authorization_id) is None:
        _fail("metadata-edit authorization_id is invalid")
    nonce = authorization["nonce"]
    if not isinstance(nonce, str) or HEX64.fullmatch(nonce) is None:
        _fail("metadata-edit authorization nonce must be lowercase SHA-256 material")
    nonce_digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()

    expected_return = {
        key: machine_proof["candidate_return_receipt"][key]
        for key in ("path", "bytes", "sha256", "git_blob_sha")
    }
    if authorization["candidate_return_receipt"] != expected_return:
        _fail("metadata-edit owner authorization return receipt differs")
    expected_proof = {
        key: machine_proof[key]
        for key in ("path", "bytes", "sha256", "git_blob_sha")
    }
    if authorization["machine_proof"] != expected_proof:
        _fail("metadata-edit owner authorization proof identity differs")
    metadata_sha256 = _canonical_metadata_hash(metadata_after)
    if authorization["canonical_metadata_sha256"] != metadata_sha256:
        _fail("metadata-edit owner authorization metadata digest differs")
    if authorization["authorized_effects"] != list(OWNER_AUTHORIZED_EFFECTS):
        _fail("metadata-edit owner authorization effect set differs")

    event = authorization["authorization_event"]
    if not isinstance(event, dict):
        _fail("metadata-edit owner authorization event must be an object")
    zenodo._check_exact_keys(
        event,
        {
            "channel",
            "authorized_at",
            "decision",
            "exact_statement",
            "statement_sha256",
            "principal",
            "candidate_return_receipt_sha256",
        },
        "metadata-edit owner authorization event",
    )
    authorized_at = publication._validate_rfc3339(
        event["authorized_at"],
        "metadata-edit owner authorization authorized_at",
    )
    return_time = datetime.datetime.fromisoformat(
        machine_proof["returned_at"].replace("Z", "+00:00")
    )
    event_time = datetime.datetime.fromisoformat(authorized_at.replace("Z", "+00:00"))
    if event_time < return_time:
        _fail("metadata-edit owner authorization predates candidate return")
    expected_statement = publication._canonical_authorization_statement(
        authorization_id,
        publication_id,
        expected_return["sha256"],
        metadata_sha256,
        expected_proof["sha256"],
    )
    if (
        event["decision"] != "AUTHORIZE_EXACT_UPLOAD"
        or event["exact_statement"] != expected_statement
        or event["principal"] != principal
        or event["candidate_return_receipt_sha256"] != expected_return["sha256"]
    ):
        _fail("metadata-edit authorization event differs from the exact canonical decision")
    statement_sha256 = hashlib.sha256(expected_statement.encode("utf-8")).hexdigest()
    if event["statement_sha256"] != statement_sha256:
        _fail("metadata-edit authorization statement digest differs")
    consumption_key = publication._authorization_consumption_key(
        repository,
        authorization_id,
        publication_id,
        statement_sha256,
    )
    return {
        **identity,
        "schema": AUTHORIZATION_SCHEMA,
        "authorization_id": authorization_id,
        "nonce_digest": {"algorithm": "SHA-256", "value": nonce_digest},
        "consumption_key": consumption_key,
        "remote_consumption_ref": publication._remote_consumption_ref(consumption_key["value"]),
        "single_use": True,
        "single_use_scope": publication.SINGLE_USE_SCOPE,
        "principal": dict(principal),
        "publication_id": publication_id,
        "repository": repository,
        "source_head": source_head,
        "canonical_metadata_sha256": metadata_sha256,
        "candidate_return_receipt": expected_return,
        "machine_proof": expected_proof,
        "file_inventory_sha256": file_inventory_sha256,
        "authorized_effects": list(OWNER_AUTHORIZED_EFFECTS),
        "authorization_event": {
            "channel": publication._bounded_text(event["channel"], "metadata-edit authorization channel", 200),
            "authorized_at": authorized_at,
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": expected_statement,
            "statement_sha256": statement_sha256,
            "principal": dict(principal),
            "candidate_return_receipt_sha256": expected_return["sha256"],
        },
    }


def load_manifest(path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    path = publication._manifest_path(root, path)
    value, raw = zenodo._load_json_file(path)
    zenodo._check_exact_keys(
        value,
        {
            "schema",
            "state",
            "confirm",
            "repository",
            "source_head",
            "publication_id",
            "target",
            "metadata_before",
            "metadata_after",
            "files",
            "machine_proof",
            "owner_authorization",
            "evidence_path",
        },
        "metadata-edit manifest",
    )
    if value["schema"] != SCHEMA or value["state"] != STATE or value["confirm"] != CONFIRM:
        _fail("published metadata edit is not explicitly authorized by its manifest")
    repository = value["repository"]
    if repository != PRODUCTION_REPOSITORY:
        _fail("metadata-edit manifest repository differs from the production authority")
    expected_repository = os.environ.get("GITHUB_REPOSITORY")
    if expected_repository is not None and expected_repository != repository:
        _fail("GITHUB_REPOSITORY differs from the metadata-edit manifest")
    source_head = value["source_head"]
    if not isinstance(source_head, str) or HEX40.fullmatch(source_head) is None:
        _fail("metadata-edit manifest source_head must be lowercase Git SHA-1")
    publication_id = value["publication_id"]
    if not isinstance(publication_id, str) or SAFE_ID.fullmatch(publication_id) is None:
        _fail("metadata-edit publication_id is invalid")
    target = _validate_target(value["target"])
    _before_path, before_identity, before_raw, _before_bytes = _load_bound_json(
        value["metadata_before"], root, "manifest.metadata_before"
    )
    _after_path, after_identity, after_raw, _after_bytes = _load_bound_json(
        value["metadata_after"], root, "manifest.metadata_after"
    )
    metadata_before, metadata_after, changed_fields = _validate_metadata_transition(
        before_raw,
        after_raw,
    )
    files, file_inventory_sha256 = _validate_files(value["files"])
    machine_proof = _validate_proof(
        value["machine_proof"],
        root,
        publication_id=publication_id,
        target=target,
        metadata_before_identity=before_identity,
        metadata_after_identity=after_identity,
        file_inventory_sha256=file_inventory_sha256,
    )
    evidence_path = publication._safe_relative(
        root,
        value["evidence_path"],
        "metadata-edit manifest evidence_path",
        must_exist=False,
    )
    if evidence_path.name != "zenodo-metadata-edit.json":
        _fail("metadata-edit evidence must use zenodo-metadata-edit.json basename")
    evidence_relative = evidence_path.relative_to(root).as_posix()
    protected_paths = {
        path.relative_to(root).as_posix(),
        before_identity["path"],
        after_identity["path"],
        machine_proof["path"],
        *(item["path"] for item in machine_proof["artifacts"]),
        *(item["path"] for item in machine_proof["control_identities"]),
    }
    if evidence_relative in protected_paths:
        _fail("metadata-edit evidence path overlaps immutable control bytes")
    authorization = _validate_authorization(
        value["owner_authorization"],
        root,
        repository=repository,
        source_head=source_head,
        publication_id=publication_id,
        target=target,
        metadata_after=metadata_after,
        machine_proof=machine_proof,
        file_inventory_sha256=file_inventory_sha256,
        evidence_path=evidence_path,
    )
    return {
        "schema": SCHEMA,
        "repository": repository,
        "source_head": source_head,
        "publication_id": publication_id,
        "target": target,
        "metadata_before": metadata_before,
        "metadata_before_identity": before_identity,
        "metadata_after": metadata_after,
        "metadata_after_identity": after_identity,
        "metadata_before_sha256": _canonical_metadata_hash(metadata_before),
        "metadata_after_sha256": _canonical_metadata_hash(metadata_after),
        "changed_fields": changed_fields,
        "files": files,
        "file_inventory_sha256": file_inventory_sha256,
        "machine_proof": machine_proof,
        "owner_authorization": authorization,
        "evidence_path": evidence_path,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _validate_repository_heads(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
    manifest: Mapping[str, Any],
) -> str:
    _status, current_head = publication._git(root, "rev-parse", "--verify", "HEAD^{commit}")
    github_sha = os.environ.get("GITHUB_SHA")
    if HEX40.fullmatch(current_head) is None or github_sha != current_head:
        _fail("metadata-edit execution HEAD is not exact GITHUB_SHA")
    source_head = manifest["source_head"]
    _status, resolved_source = publication._git(root, "rev-parse", "--verify", f"{source_head}^{{commit}}")
    if resolved_source != source_head:
        _fail("metadata-edit source_head does not resolve exactly")
    ancestor, _output = publication._git(
        root,
        "merge-base",
        "--is-ancestor",
        source_head,
        current_head,
        accepted=frozenset({0, 1}),
    )
    if ancestor != 0:
        _fail("metadata-edit execution HEAD is not a descendant of source_head")

    current_paths: dict[str, str] = {}
    manifest_relative = manifest_path.relative_to(root).as_posix()
    manifest_raw = zenodo.read_regular_file(manifest_path, zenodo.MAX_JSON_BYTES)
    current_paths[manifest_relative] = publication._git_blob_sha(manifest_raw)
    for identity in (
        manifest["metadata_before_identity"],
        manifest["metadata_after_identity"],
        manifest["machine_proof"],
        manifest["owner_authorization"],
        *manifest["machine_proof"]["artifacts"],
        *manifest["machine_proof"]["control_identities"],
    ):
        path = identity["path"]
        blob = identity["git_blob_sha"]
        if path in current_paths and current_paths[path] != blob:
            _fail("metadata-edit execution scope has conflicting Git identities")
        current_paths[path] = blob
    source_paths = {
        key: value
        for key, value in current_paths.items()
        if key not in {manifest_relative, manifest["owner_authorization"]["path"]}
    }
    for head, paths, where in (
        (source_head, source_paths, "source"),
        (current_head, current_paths, "execution"),
    ):
        for raw_path, expected_blob in paths.items():
            status, observed = publication._git(
                root,
                "rev-parse",
                "--verify",
                f"{head}:{raw_path}",
                accepted=frozenset({0, 128}),
            )
            if status != 0 or observed != expected_blob:
                _fail(f"metadata-edit {where} Git blob differs for {raw_path}")
    _status, dirty = publication._git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *sorted(current_paths),
    )
    if dirty:
        _fail("metadata-edit execution paths are not clean at execution HEAD")
    return current_head


def _record_revision(value: Mapping[str, Any], where: str) -> int:
    revision = value.get("revision")
    if isinstance(revision, str) and revision.isdecimal():
        revision = int(revision)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        _fail(f"{where} has no positive revision")
    return revision


def _public_read(
    client: zenodo.ZenodoClient,
    record_id: int,
    *,
    accept: Sequence[int] = (200,),
) -> tuple[zenodo.HttpResponse, dict[str, Any]]:
    return client.request("GET", f"/api/records/{record_id}", accept=accept)


def _snapshot(
    response: zenodo.HttpResponse,
    record: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    expected_metadata: Mapping[str, Any],
    before: bool,
) -> dict[str, Any]:
    target = manifest["target"]
    record_id = zenodo._record_id(record, "metadata-edit public record")
    concept_id = zenodo._concept_id(record, "metadata-edit public record")
    doi = zenodo._doi_from_deposition(record, "metadata-edit public record")
    concept_doi = record.get("conceptdoi")
    if (
        record_id != target["record_id"]
        or concept_id != target["concept_record_id"]
        or doi != target["doi"]
        or concept_doi != target["concept_doi"]
    ):
        _fail("published metadata-edit target identity changed")
    revision = _record_revision(record, "metadata-edit public record")
    expected_revision = (
        target["before_revision"]
        if before
        else target["expected_after_revision"]
    )
    if revision != expected_revision:
        _fail("published metadata-edit target revision changed")
    etag = zenodo._header(response, "ETag")
    if not isinstance(etag, str) or not etag:
        _fail("published metadata-edit target omitted ETag")
    if before and etag != target["before_etag"]:
        _fail("published metadata-edit before ETag changed")
    if not before and etag == target["before_etag"]:
        _fail("published metadata-edit after ETag did not change")
    actual_metadata = record.get("metadata")
    if not zenodo._published_metadata_matches(actual_metadata, expected_metadata):
        _fail("published metadata differs from the exact metadata candidate")
    if not isinstance(actual_metadata, dict):
        _fail("published metadata is not an object")
    public_metadata_sha256 = hashlib.sha256(zenodo._json_bytes(actual_metadata)).hexdigest()
    if before and public_metadata_sha256 != target["before_public_metadata_sha256"]:
        _fail("published before metadata response digest changed")
    return {
        "record_id": record_id,
        "concept_record_id": concept_id,
        "doi": doi,
        "concept_doi": concept_doi,
        "revision": revision,
        "etag": etag,
        "canonical_metadata_sha256": _canonical_metadata_hash(expected_metadata),
        "public_metadata_response_sha256": public_metadata_sha256,
        "file_inventory_sha256": manifest["file_inventory_sha256"],
    }


def _verify_public(
    client: zenodo.ZenodoClient,
    manifest: Mapping[str, Any],
    *,
    before: bool,
) -> dict[str, Any]:
    response, record = _public_read(client, manifest["target"]["record_id"])
    expected = manifest["metadata_before"] if before else manifest["metadata_after"]
    snapshot = _snapshot(response, record, manifest, expected_metadata=expected, before=before)
    client.gate_files(record, manifest["files"])
    return snapshot


def _verify_public_lightweight(
    client: zenodo.ZenodoClient,
    manifest: Mapping[str, Any],
    *,
    before: bool,
) -> dict[str, Any]:
    response, record = _public_read(client, manifest["target"]["record_id"])
    expected = manifest["metadata_before"] if before else manifest["metadata_after"]
    snapshot = _snapshot(response, record, manifest, expected_metadata=expected, before=before)
    server_files = client._server_files(record)
    by_name = {client._server_file_name(item): item for item in server_files}
    if len(by_name) != len(server_files) or set(by_name) != {item["name"] for item in manifest["files"]}:
        _fail("Zenodo file inventory changed during metadata edit")
    for expected_file in manifest["files"]:
        observed = by_name[expected_file["name"]]
        size = observed.get("filesize", observed.get("size"))
        if isinstance(size, str) and size.isdecimal():
            size = int(size)
        checksum = observed.get("checksum")
        if size != expected_file["size"] or checksum not in (
            expected_file["md5"],
            "md5:" + expected_file["md5"],
        ):
            _fail("Zenodo file size/checksum changed during metadata edit")
    return snapshot


def _wait_editable_deposition(
    client: zenodo.ZenodoClient,
    manifest: Mapping[str, Any],
    expected_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    record_id = manifest["target"]["record_id"]
    expected = dict(expected_metadata)
    expected.pop("prereserve_doi", None)
    for attempt in range(client.poll_attempts):
        status, value = client.get(
            f"/api/deposit/depositions/{record_id}",
            accept=(200, 202, 404),
        )
        # Zenodo's published-record edit state remains ``submitted`` while
        # ``state=inprogress``: metadata is writable, but files stay locked.
        # Requiring that exact state prevents this controller from accepting a
        # new/unsubmitted deposition whose files would also be mutable.
        if (
            status == 200
            and value.get("submitted") is True
            and value.get("state") == "inprogress"
        ):
            if zenodo._record_id(value, "metadata-edit draft") != record_id:
                _fail("metadata-edit draft record ID changed")
            if zenodo._concept_id(value, "metadata-edit draft") != manifest["target"]["concept_record_id"]:
                _fail("metadata-edit draft concept changed")
            if zenodo._doi_from_deposition(value, "metadata-edit draft") != manifest["target"]["doi"]:
                _fail("metadata-edit draft DOI changed")
            if not zenodo._metadata_matches(value.get("metadata"), expected):
                _fail("metadata-edit draft metadata differs")
            client.gate_files(value, manifest["files"])
            return value
        if attempt + 1 < client.poll_attempts:
            client.sleeper(client.poll_interval)
    _fail("timed out waiting for editable metadata-only deposition")


def _wait_public_after(
    client: zenodo.ZenodoClient,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    last_error: zenodo.ZenodoError | None = None
    for attempt in range(client.poll_attempts):
        response, record = _public_read(
            client,
            manifest["target"]["record_id"],
            accept=(200, 202, 404),
        )
        if response.status == 200:
            try:
                snapshot = _snapshot(
                    response,
                    record,
                    manifest,
                    expected_metadata=manifest["metadata_after"],
                    before=False,
                )
                client.gate_files(record, manifest["files"])
                return snapshot, record
            except zenodo.ZenodoError as exc:
                last_error = exc
        if attempt + 1 < client.poll_attempts:
            client.sleeper(client.poll_interval)
    if last_error is not None:
        _fail("republished metadata record failed its public gate: " + str(last_error))
    _fail("timed out waiting for republished metadata record")


def _execute_remote(
    client: zenodo.ZenodoClient,
    manifest: Mapping[str, Any],
    persist_phase: Callable[[str, Mapping[str, Any] | None], None],
) -> dict[str, Any]:
    record_id = manifest["target"]["record_id"]
    response, _empty = client.request(
        "POST",
        f"/api/deposit/depositions/{record_id}/actions/edit",
        accept=(201,),
        parse_json=False,
    )
    if response.status != 201:
        _fail("Zenodo did not open the published record for metadata edit")
    persist_phase("edit_requested", None)
    _wait_editable_deposition(client, manifest, manifest["metadata_before"])
    client.request(
        "PUT",
        f"/api/deposit/depositions/{record_id}",
        payload={"metadata": manifest["metadata_after"]},
        accept=(200,),
    )
    persist_phase("metadata_updated", None)
    _wait_editable_deposition(client, manifest, manifest["metadata_after"])
    client.request(
        "POST",
        f"/api/deposit/depositions/{record_id}/actions/publish",
        accept=(202,),
        parse_json=False,
    )
    persist_phase("republish_requested", None)
    after, _record = _wait_public_after(client, manifest)
    persist_phase("public_verified", after)
    return after


def _evidence(
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    manifest: Mapping[str, Any],
    execution_head: str,
    remote_consumption: Mapping[str, Any],
    phase: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if phase not in PHASES:
        _fail("metadata-edit evidence phase is invalid")
    authorization = manifest["owner_authorization"]
    return {
        "schema": EVIDENCE_SCHEMA,
        "state": "PUBLIC_VERIFIED" if phase == "public_verified" else publication.CONSUMPTION_STATE,
        "phase": phase,
        "repository": manifest["repository"],
        "source_head": manifest["source_head"],
        "execution_head": execution_head,
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": manifest["manifest_sha256"],
        "publication_id": manifest["publication_id"],
        "target": dict(manifest["target"]),
        "changed_fields": list(manifest["changed_fields"]),
        "metadata_before_sha256": manifest["metadata_before_sha256"],
        "metadata_after_sha256": manifest["metadata_after_sha256"],
        "file_inventory_sha256": manifest["file_inventory_sha256"],
        "machine_proof": {
            key: manifest["machine_proof"][key]
            for key in ("path", "bytes", "sha256", "git_blob_sha")
        },
        "owner_authorization": {
            "authorization_id": authorization["authorization_id"],
            "nonce_digest": authorization["nonce_digest"],
            "consumption_key": authorization["consumption_key"],
            "remote_consumption_ref": authorization["remote_consumption_ref"],
            "statement_sha256": authorization["authorization_event"]["statement_sha256"],
        },
        "remote_consumption": dict(remote_consumption),
        "before": dict(before),
        "after": dict(after) if after is not None else None,
        "files_uploaded": False,
        "files_deleted": False,
        "record_created": False,
        "version_created": False,
        "public_verified": phase == "public_verified",
        "effect_ack_done": phase == "public_verified",
    }


def _validate_existing_final(
    value: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    if (
        value.get("schema") != EVIDENCE_SCHEMA
        or value.get("phase") != "public_verified"
        or value.get("manifest_sha256") != manifest["manifest_sha256"]
        or value.get("publication_id") != manifest["publication_id"]
        or value.get("target") != manifest["target"]
        or value.get("metadata_after_sha256") != manifest["metadata_after_sha256"]
        or value.get("file_inventory_sha256") != manifest["file_inventory_sha256"]
        or value.get("files_uploaded") is not False
        or value.get("files_deleted") is not False
        or value.get("public_verified") is not True
    ):
        _fail("existing metadata-edit evidence differs from the exact final effect")


def _reject_replay(
    root: pathlib.Path,
    authorization: Mapping[str, Any],
    current_evidence: pathlib.Path,
) -> None:
    inspected = 0
    for path in root.rglob("*.json"):
        if path.resolve() == current_evidence.resolve() or ".git" in path.parts or path.is_symlink():
            continue
        if path.name not in {"zenodo-metadata-edit.json", "zenodo-publication.json"}:
            continue
        inspected += 1
        if inspected > 4096:
            _fail("metadata-edit replay scan exceeded bounded evidence count")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            _fail("cannot inspect repository evidence for metadata-edit replay")
        observed = value.get("owner_authorization") if isinstance(value, dict) else None
        if not isinstance(observed, dict):
            continue
        if (
            observed.get("authorization_id") == authorization["authorization_id"]
            or observed.get("nonce_digest") == authorization["nonce_digest"]
            or observed.get("consumption_key") == authorization["consumption_key"]
        ):
            _fail("metadata-edit owner authorization was already consumed")


def edit_published_metadata(
    manifest_path: pathlib.Path,
    root: pathlib.Path,
) -> dict[str, Any]:
    manifest_path = publication._manifest_path(root, manifest_path)
    manifest = load_manifest(manifest_path, root)
    if os.environ.get("GITHUB_REPOSITORY") != PRODUCTION_REPOSITORY:
        _fail("production metadata editor repository identity is missing or mismatched")
    secrets = publication._validated_network_secrets()
    execution_head = _validate_repository_heads(root, manifest_path, manifest)
    publication._validate_origin_repository(root, manifest["repository"])
    for identity in (
        manifest["metadata_before_identity"],
        manifest["metadata_after_identity"],
        manifest["machine_proof"],
        manifest["owner_authorization"],
    ):
        data = zenodo.read_regular_file(root / identity["path"], zenodo.MAX_UPLOAD_BYTES)
        for name, secret in secrets.items():
            if secret.encode("utf-8") in data:
                _fail(f"metadata-edit control bytes contain the {publication._secret_label(name)}")

    base_url = zenodo.validate_base_url(os.environ.get("ZENODO_API_BASE", zenodo.DEFAULT_BASE_URL))
    client = zenodo.ZenodoClient(secrets[zenodo.TOKEN_ENVIRONMENT_VARIABLE], base_url)
    evidence_path = manifest["evidence_path"]
    if evidence_path.exists():
        existing, _raw = publication._load_evidence_without_secrets(evidence_path, secrets)
        if existing.get("phase") != "public_verified":
            _fail(
                "metadata edit has intermediate consumed evidence at phase "
                + str(existing.get("phase"))
                + "; explicit remote reconciliation is required"
            )
        _validate_existing_final(existing, manifest)
        publication._verify_remote_consumption_lock(
            existing["remote_consumption"],
            manifest,
            execution_head,
            secrets[publication.GITHUB_TOKEN_ENVIRONMENT_VARIABLE],
        )
        after = _verify_public(client, manifest, before=False)
        if after != existing["after"]:
            _fail("public metadata-edit state changed after final evidence")
        return dict(existing)

    _reject_replay(root, manifest["owner_authorization"], evidence_path)
    before = _verify_public(client, manifest, before=True)
    remote = publication._acquire_remote_consumption_lock(
        root,
        manifest,
        execution_head,
        secrets[publication.GITHUB_TOKEN_ENVIRONMENT_VARIABLE],
    )
    if remote["recovery_mode"] != "NEWLY_CREATED_REF":
        _fail("metadata-edit authorization ref already exists; explicit reconciliation is required")
    initial = _evidence(
        manifest_path,
        root,
        manifest,
        execution_head,
        remote,
        "authorization_consumed",
        before,
        None,
    )
    publication._create_consumption_receipt(evidence_path, initial, secrets)
    second_before = _verify_public_lightweight(client, manifest, before=True)
    if second_before != before:
        _fail("published record changed between preflight and consumed authorization")

    latest = initial

    def persist(phase: str, after: Mapping[str, Any] | None) -> None:
        nonlocal latest
        latest = _evidence(
            manifest_path,
            root,
            manifest,
            execution_head,
            remote,
            phase,
            before,
            after,
        )
        publication._atomic_recovery_evidence(evidence_path, latest, secrets)

    _execute_remote(client, manifest, persist)
    return latest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Edit only exact authorized metadata on an existing published Zenodo record"
    )
    parser.add_argument("--manifest", required=True, help="repository-relative metadata-edit manifest")
    args = parser.parse_args(argv)
    root = pathlib.Path.cwd().resolve()
    try:
        manifest_path = publication._safe_relative(root, args.manifest, "--manifest", must_exist=True)
        evidence = edit_published_metadata(manifest_path, root)
        print("ZENODO_METADATA_EDIT_STATE=public_verified")
        print(f"ZENODO_RECORD_ID={evidence['target']['record_id']}")
        print(f"ZENODO_DOI={evidence['target']['doi']}")
        return 0
    except zenodo.ZenodoError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
