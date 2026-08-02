#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Generic fail-closed Zenodo publication capability.

The implementation contains no document-, release-, record- or DOI-specific
constants. Effect-bearing identity is supplied by a repository-controlled JSON
manifest. Each file is bound to its Git blob SHA-1; byte size, MD5 and SHA-256
are derived locally and then independently verified by the hardened shared
Zenodo transport before and after publication.

Since 2026-07-28, every new production mutation additionally requires a complete
QIK-VRT machine-proof bundle. A v2 mutation also requires a candidate-specific
platform/repository-bound authorization attestation naming a natural-person
principal. This validator checks repository and policy bindings; it does not
cryptographically authenticate the named person. The authorization is consumed
through an atomic repository-remote Git ref before any Zenodo client is created.
Legacy v1 manifests remain readable for historical verification, but they cannot
create a new Zenodo record.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any, NoReturn

try:
    from tools import qikvrt_zenodo_actions as zenodo
    from tools import qikvrt_zenodo_machine_proof as machine_proof
except ModuleNotFoundError:
    import qikvrt_zenodo_actions as zenodo  # type: ignore[no-redef]
    import qikvrt_zenodo_machine_proof as machine_proof  # type: ignore[no-redef]

SCHEMA = "qikvrt_zenodo_publication_manifest_v1"
SCHEMA_V2 = "qikvrt_zenodo_publication_manifest_v2"
EVIDENCE_SCHEMA = "qikvrt_zenodo_publication_evidence_v1"
EVIDENCE_SCHEMA_V2 = "qikvrt_zenodo_publication_evidence_v2"
OWNER_AUTHORIZATION_SCHEMA = "qikvrt_zenodo_owner_authorization_v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ZENODO_DOI = re.compile(r"^10\.5281/zenodo\.[1-9][0-9]*$")
SAFE_AUTHORIZATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{15,127}$")
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"(?:Z|[+-]\d{2}:\d{2})$"
)
CONSUMPTION_STATE = "EFFECT_RELEASED/AWAITING_REMOTE_RECONCILIATION"
SINGLE_USE_SCOPE = "AUTHORITY_REPOSITORY_GLOBAL_FAIL_CLOSED"
CONSUMPTION_REF_PREFIX = "refs/tags/qikvrt-zenodo-auth/"
CONSUMPTION_KEY_SCHEMA = "qikvrt_zenodo_authorization_consumption_key_v2"
PRODUCTION_REPOSITORY = "Goldkelch/qik-vrt"
PRODUCTION_GITHUB_HOST = "github.com"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN_ENVIRONMENT_VARIABLE = "GITHUB_TOKEN"
MAX_GITHUB_RESPONSE_BYTES = 1024 * 1024
MAX_INVENTORY_PAGES = 100
INVENTORY_PAGE_SIZE = 100
RECOVERY_PHASES = (
    "authorization_consumed",
    "create_requested",
    "record_created",
    "prepared",
    "publish_requested",
    "public_verified",
)
GOVERNANCE_BOUNDARIES = (
    "ADMIN_GOVERNANCE_NOT_ESTABLISHED",
    "REPOSITORY_SECRET_TRUSTS_PRIVILEGED_WRITE_ACTORS",
    "PRIVILEGED_TAG_DELETION_NOT_PREVENTED",
)
OWNER_AUTHORIZED_EFFECTS = (
    "ACQUIRE_REPOSITORY_REMOTE_CONSUMPTION_LOCK",
    "CREATE_PRODUCTION_ZENODO_RECORD",
    "UPLOAD_EXACT_AUTHORIZED_FILES",
    "PUBLISH_PRODUCTION_ZENODO_RECORD",
    "VERIFY_PUBLIC_BYTE_EXACT_REDOWNLOAD",
    "PERSIST_PUBLICATION_EVIDENCE",
)
ALLOWED_METADATA = frozenset(
    {
        "title", "upload_type", "publication_type", "description", "creators",
        "version", "publication_date", "access_right", "license", "language",
        "keywords", "related_identifiers", "notes", "prereserve_doi",
    }
)
REQUIRED_METADATA = frozenset(
    {"title", "upload_type", "description", "creators", "version", "access_right"}
)


def _fail(message: str) -> NoReturn:
    raise zenodo.ZenodoError(message)


def _secret_label(name: str) -> str:
    return (
        "Zenodo access token"
        if name == zenodo.TOKEN_ENVIRONMENT_VARIABLE
        else "GitHub access token"
    )


def _safe_relative(
    root: pathlib.Path, raw: Any, where: str, *, must_exist: bool
) -> pathlib.Path:
    if not isinstance(raw, str) or not raw:
        _fail(f"{where} must be a non-empty repository-relative path")
    relative = pathlib.PurePosixPath(raw)
    if any(part.casefold() == ".git" for part in relative.parts):
        _fail(f"{where} must not resolve inside repository Git metadata")
    try:
        return zenodo._relative_path(root, raw, must_exist=must_exist)
    except zenodo.ZenodoError as exc:
        _fail(f"{where}: {exc}")


def _manifest_path(root: pathlib.Path, path: pathlib.Path) -> pathlib.Path:
    """Return a safe in-repository manifest path, including direct API callers."""
    candidate = path if path.is_absolute() else root / path
    try:
        relative = candidate.resolve(strict=False).relative_to(root.resolve()).as_posix()
    except ValueError:
        _fail("publication manifest must stay inside the repository root")
    return _safe_relative(
        root,
        relative,
        "publication manifest path",
        must_exist=True,
    )


def _canonical_authorization_statement(
    authorization_id: str,
    publication_id: str,
    return_sha256: str,
    metadata_sha256: str,
    machine_proof_sha256: str,
) -> str:
    """Construct the only accepted one-line exact-upload decision statement."""
    return (
        "AUTHORIZE_EXACT_UPLOAD "
        f"authorization_id={authorization_id} "
        f"publication_id={publication_id} "
        f"return_sha256={return_sha256} "
        f"metadata_sha256={metadata_sha256} "
        f"machine_proof_sha256={machine_proof_sha256}"
    )


def _authorization_consumption_key(
    repository: str,
    authorization_id: str,
    publication_id: str,
    statement_sha256: str,
) -> dict[str, str]:
    """Bind single-use consumption to the immutable authorization decision.

    The random authorization nonce remains evidence, but deliberately does not
    select the repository-global lock. Replacing only that nonce therefore
    cannot mint a second effect-bearing identity for the same decision.
    """
    if repository != PRODUCTION_REPOSITORY:
        _fail("authorization consumption key repository is not the pinned authority")
    if SAFE_AUTHORIZATION_ID.fullmatch(authorization_id) is None:
        _fail("authorization consumption key authorization_id is unsafe")
    if not isinstance(publication_id, str) or not publication_id:
        _fail("authorization consumption key publication_id is invalid")
    if HEX64.fullmatch(statement_sha256) is None:
        _fail("authorization consumption key statement digest is invalid")
    material = {
        "schema": CONSUMPTION_KEY_SCHEMA,
        "repository": repository,
        "authorization_id": authorization_id,
        "publication_id": publication_id,
        "statement_sha256": statement_sha256,
    }
    return {
        "algorithm": "SHA-256",
        "schema": CONSUMPTION_KEY_SCHEMA,
        "value": hashlib.sha256(zenodo._json_bytes(material)).hexdigest(),
    }


def _remote_consumption_ref(consumption_key: str) -> str:
    if HEX64.fullmatch(consumption_key) is None:
        _fail("authorization consumption key cannot form a safe GitHub lock ref")
    return CONSUMPTION_REF_PREFIX + consumption_key


def _validate_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not zenodo._is_json_value(value):
        _fail("manifest.metadata must be a JSON object")
    missing = REQUIRED_METADATA - set(value)
    unknown = set(value) - ALLOWED_METADATA
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unknown=" + ",".join(sorted(unknown)))
        _fail("invalid manifest.metadata keys (" + "; ".join(details) + ")")
    zenodo._metadata_identity(value, "manifest")
    if value.get("prereserve_doi") is not True:
        _fail("manifest.metadata.prereserve_doi must equal true")
    if value["access_right"] != "open":
        _fail("manifest.metadata.access_right must equal open")
    if not isinstance(value["description"], str) or not value["description"].strip():
        _fail("manifest.metadata.description must be non-empty")
    return dict(value)


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git object identity


def _identity(raw_path: str, data: bytes) -> dict[str, Any]:
    return {
        "path": raw_path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha": _git_blob_sha(data),
    }


def _bounded_text(
    value: Any,
    where: str,
    maximum: int,
    *,
    allow_line_breaks: bool = False,
) -> str:
    allowed_controls = {"\n", "\r", "\t"} if allow_line_breaks else set()
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or any(
            unicodedata.category(character).startswith("C")
            and character not in allowed_controls
            for character in value
        )
    ):
        _fail(f"{where} must be non-empty, bounded text without control characters")
    return value


def _person_name_identity(value: Any, where: str) -> str:
    raw = _bounded_text(value, where, 200)
    normalized = " ".join(unicodedata.normalize("NFKC", raw).split())
    if normalized.count(",") > 1:
        _fail(f"{where} has an unsupported person-name form")
    if "," in normalized:
        family, given = (part.strip() for part in normalized.split(",", 1))
        if not family or not given:
            _fail(f"{where} has an incomplete family/given name")
        normalized = f"{given} {family}"
    return normalized.casefold()


def _validate_rfc3339(value: Any, where: str) -> str:
    raw = _bounded_text(value, where, 64)
    if RFC3339.fullmatch(raw) is None:
        _fail(f"{where} must be an RFC3339 timestamp with UTC or numeric offset")
    try:
        parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        _fail(f"{where} must be a valid RFC3339 timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _fail(f"{where} must include a UTC or numeric offset")
    return raw


def _materialize_file(value: Any, root: pathlib.Path, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail(f"{where} must be an object")
    zenodo._check_exact_keys(value, {"path", "name", "git_blob_sha"}, where)
    path = _safe_relative(root, value["path"], f"{where}.path", must_exist=True)
    name = value["name"]
    if (
        not isinstance(name, str)
        or not name
        or pathlib.PurePosixPath(name).name != name
        or name in {".", ".."}
    ):
        _fail(f"{where}.name must be a safe basename")
    expected_blob = value["git_blob_sha"]
    if not isinstance(expected_blob, str) or HEX40.fullmatch(expected_blob) is None:
        _fail(f"{where}.git_blob_sha must be lowercase Git SHA-1")
    data = zenodo.read_regular_file(path, zenodo.MAX_UPLOAD_BYTES)
    actual_blob = _git_blob_sha(data)
    if actual_blob != expected_blob:
        _fail(f"Git blob mismatch for {value['path']}")
    return {
        "path": path.relative_to(root).as_posix(),
        "name": name,
        "size": len(data),
        "md5": hashlib.md5(data).hexdigest(),  # noqa: S324 - Zenodo transport checksum
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha": actual_blob,
    }


def _validate_machine_proof(
    value: Any,
    root: pathlib.Path,
    files: list[dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("manifest.machine_proof must be an object")
    zenodo._check_exact_keys(
        value,
        {"path", "git_blob_sha", "policy_id"},
        "manifest.machine_proof",
    )
    if value["policy_id"] != machine_proof.POLICY_ID:
        _fail("manifest.machine_proof.policy_id differs from the active policy")
    path = _safe_relative(
        root,
        value["path"],
        "manifest.machine_proof.path",
        must_exist=True,
    )
    bundle, raw = zenodo._load_json_file(path)
    observed_blob = _git_blob_sha(raw)
    expected_blob = value["git_blob_sha"]
    if not isinstance(expected_blob, str) or HEX40.fullmatch(expected_blob) is None:
        _fail("manifest.machine_proof.git_blob_sha must be lowercase Git SHA-1")
    if observed_blob != expected_blob:
        _fail("machine-proof bundle Git blob mismatch")
    upload_paths = [entry["path"] for entry in files]
    try:
        receipt = machine_proof.validate_bundle(
            root,
            path,
            upload_paths=upload_paths,
        )
    except machine_proof.ProofGateError as exc:
        _fail("machine-proof gate rejected publication: " + str(exc))
    if receipt["git_blob_sha1"] != expected_blob:
        _fail("machine-proof validator returned a different Git blob identity")
    returned = bundle["prepublication_return"]
    return_path = _safe_relative(
        root,
        returned["receipt_path"],
        "machine proof prepublication return receipt",
        must_exist=True,
    )
    return_value, return_raw = zenodo._load_json_file(return_path)
    return_identity = _identity(return_path.relative_to(root).as_posix(), return_raw)
    returned_at = _validate_rfc3339(
        return_value["return"]["returned_at"],
        "prepublication return receipt return.returned_at",
    )
    returned_candidate_files = [
        {
            "path": item["path"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
            "git_blob_sha": item["git_blob_sha1"],
        }
        for item in return_value["candidate_files"]
    ]
    return {
        "policy_id": machine_proof.POLICY_ID,
        "publication_id": receipt["publication_id"],
        "path": receipt["path"],
        "bytes": receipt["bytes"],
        "sha256": receipt["sha256"],
        "git_blob_sha": receipt["git_blob_sha1"],
        "candidate_return_receipt": return_identity,
        "prepublication_returned_at": returned_at,
        "returned_candidate_files": returned_candidate_files,
        "claim_count": receipt["claim_count"],
        "machine_proof_complete": True,
        "zenodo_upload_authorized": True,
    }


def _validate_identity(
    value: Any,
    expected: Mapping[str, Any],
    where: str,
) -> None:
    if not isinstance(value, dict):
        _fail(f"{where} must be an object")
    zenodo._check_exact_keys(
        value,
        {"path", "bytes", "sha256", "git_blob_sha"},
        where,
    )
    if (
        not isinstance(value["path"], str)
        or not value["path"]
        or isinstance(value["bytes"], bool)
        or not isinstance(value["bytes"], int)
        or value["bytes"] < 0
        or not isinstance(value["sha256"], str)
        or HEX64.fullmatch(value["sha256"]) is None
        or not isinstance(value["git_blob_sha"], str)
        or HEX40.fullmatch(value["git_blob_sha"]) is None
    ):
        _fail(f"{where} contains an invalid bound identity")
    if value != expected:
        _fail(f"{where} differs from the exact repository bytes")


def _validate_owner_authorization(
    value: Any,
    root: pathlib.Path,
    repository: str,
    metadata: Mapping[str, Any],
    files: list[dict[str, Any]],
    proof: Mapping[str, Any],
    evidence_path: pathlib.Path,
    source_head: str,
) -> dict[str, Any]:
    """Validate a repository-bound attestation naming a natural-person principal.

    The checks establish exact repository, policy, candidate and decision
    consistency. They do not cryptographically authenticate the named person.
    """
    if not isinstance(value, dict):
        _fail("manifest.owner_authorization must be an object")
    zenodo._check_exact_keys(
        value,
        {"path", "bytes", "sha256", "git_blob_sha"},
        "manifest.owner_authorization",
    )
    path = _safe_relative(
        root,
        value["path"],
        "manifest.owner_authorization.path",
        must_exist=True,
    )
    raw_path = path.relative_to(root).as_posix()
    upload_paths = {entry["path"] for entry in files}
    evidence_relative = evidence_path.relative_to(root).as_posix()
    if evidence_path.name != "zenodo-publication.json":
        _fail("v2 publication evidence must use the zenodo-publication.json basename")
    if evidence_relative in upload_paths:
        _fail("publication evidence must not overwrite or enter the upload fileset")
    if raw_path in upload_paths:
        _fail("owner authorization must remain repository-side and not be uploaded")
    if raw_path in {
        proof["path"],
        proof["candidate_return_receipt"]["path"],
        evidence_relative,
    }:
        _fail("owner authorization creates a control-artifact identity cycle")

    authorization, raw = zenodo._load_json_file(path)
    observed = _identity(raw_path, raw)
    _validate_identity(value, observed, "manifest.owner_authorization")
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
            "candidate_return_receipt",
            "canonical_metadata_sha256",
            "uploads",
            "machine_proof",
            "authorized_effects",
            "publication_evidence_path",
            "authorization_event",
        },
        "owner authorization",
    )
    license_value = authorization["_license"]
    if not isinstance(license_value, dict):
        _fail("owner authorization._license must be an object")
    zenodo._check_exact_keys(
        license_value,
        {
            "classification",
            "copyright",
            "license",
            "license_text_ref",
            "rights_holder",
        },
        "owner authorization._license",
    )
    if license_value["classification"] != "owner_effect_authorization":
        _fail("owner authorization license classification differs")
    for key in ("copyright", "license", "license_text_ref", "rights_holder"):
        _bounded_text(license_value[key], f"owner authorization._license.{key}", 500)
    if authorization["schema"] != OWNER_AUTHORIZATION_SCHEMA:
        _fail("unsupported owner authorization schema")

    authorization_id = authorization["authorization_id"]
    nonce = authorization["nonce"]
    if (
        not isinstance(authorization_id, str)
        or SAFE_AUTHORIZATION_ID.fullmatch(authorization_id) is None
    ):
        _fail("owner authorization authorization_id is unsafe")
    if (
        not isinstance(nonce, str)
        or HEX64.fullmatch(nonce) is None
        or nonce == "0" * 64
    ):
        _fail("owner authorization nonce must be a non-zero lowercase 256-bit value")
    if authorization["single_use"] is not True:
        _fail("owner authorization must be explicitly single-use")
    if authorization["single_use_scope"] != SINGLE_USE_SCOPE:
        _fail(
            "owner authorization single-use scope must be repository-execution "
            "fail-closed"
        )
    nonce_digest_value = hashlib.sha256(nonce.encode("ascii")).hexdigest()

    principal = authorization["principal"]
    if not isinstance(principal, dict):
        _fail("owner authorization principal must be an object")
    zenodo._check_exact_keys(principal, {"name", "type"}, "owner authorization principal")
    if principal["type"] != "NATURAL_PERSON":
        _fail("owner authorization principal must be a natural person")
    principal_name = _bounded_text(
        principal["name"],
        "owner authorization principal.name",
        200,
    )
    principal_identity = _person_name_identity(
        principal_name,
        "owner authorization principal.name",
    )
    creator_identities = {
        _person_name_identity(
            creator.get("name"),
            f"manifest.metadata.creators[{index}].name",
        )
        for index, creator in enumerate(metadata["creators"])
    }
    if principal_identity not in creator_identities:
        _fail("owner authorization principal is not a manifest metadata creator")
    if license_value["rights_holder"] != principal_name:
        _fail("owner authorization rights_holder differs from its principal")
    policy_path = _safe_relative(
        root,
        machine_proof.POLICY_PATH,
        "active machine-proof policy",
        must_exist=True,
    )
    policy_value, _policy_raw = zenodo._load_json_file(policy_path)
    activation = policy_value.get("activation")
    policy_principal = (
        activation.get("principal") if isinstance(activation, dict) else None
    )
    if (
        not isinstance(policy_principal, dict)
        or set(policy_principal) != {"name", "type"}
        or policy_principal != principal
    ):
        _fail(
            "owner authorization principal differs from the active policy "
            "activation principal"
        )

    if authorization["publication_id"] != proof["publication_id"]:
        _fail("owner authorization publication_id differs from the machine proof")
    if (
        authorization["repository"] != repository
        or not isinstance(repository, str)
        or zenodo.SAFE_REPOSITORY.fullmatch(repository) is None
    ):
        _fail("owner authorization repository differs from the manifest repository")
    if authorization["source_head"] != source_head:
        _fail("owner authorization source_head differs from the v2 manifest")
    if authorization["publication_evidence_path"] != evidence_relative:
        _fail("owner authorization publication_evidence_path differs from the manifest")

    expected_metadata_sha256 = hashlib.sha256(
        zenodo._json_bytes(metadata)
    ).hexdigest()
    if authorization["canonical_metadata_sha256"] != expected_metadata_sha256:
        _fail("owner authorization canonical metadata digest differs")

    _validate_identity(
        authorization["candidate_return_receipt"],
        proof["candidate_return_receipt"],
        "owner authorization candidate_return_receipt",
    )
    expected_proof = {
        key: proof[key] for key in ("path", "bytes", "sha256", "git_blob_sha")
    }
    expected_statement = _canonical_authorization_statement(
        authorization_id,
        authorization["publication_id"],
        proof["candidate_return_receipt"]["sha256"],
        expected_metadata_sha256,
        expected_proof["sha256"],
    )
    event = authorization["authorization_event"]
    if not isinstance(event, dict):
        _fail("owner authorization authorization_event must be an object")
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
        "owner authorization authorization_event",
    )
    event_channel = _bounded_text(
        event["channel"],
        "owner authorization authorization_event.channel",
        200,
    )
    event_authorized_at = _validate_rfc3339(
        event["authorized_at"],
        "owner authorization authorization_event.authorized_at",
    )
    if event["decision"] != "AUTHORIZE_EXACT_UPLOAD":
        _fail(
            "owner authorization authorization_event decision must equal "
            "AUTHORIZE_EXACT_UPLOAD"
        )
    event_time = datetime.datetime.fromisoformat(
        event_authorized_at.replace("Z", "+00:00")
    )
    return_time = datetime.datetime.fromisoformat(
        proof["prepublication_returned_at"].replace("Z", "+00:00")
    )
    if event_time < return_time:
        _fail("owner authorization predates the candidate prepublication return")
    exact_statement = _bounded_text(
        event["exact_statement"],
        "owner authorization authorization_event.exact_statement",
        8192,
    )
    if exact_statement != expected_statement:
        _fail(
            "owner authorization authorization_event exact_statement differs "
            "from the exact canonical authorization statement"
        )
    statement_sha256 = hashlib.sha256(
        exact_statement.encode("utf-8")
    ).hexdigest()
    if event["statement_sha256"] != statement_sha256:
        _fail("owner authorization authorization_event statement digest differs")
    consumption_key = _authorization_consumption_key(
        repository,
        authorization_id,
        authorization["publication_id"],
        statement_sha256,
    )
    consumption_ref = _remote_consumption_ref(consumption_key["value"])
    event_principal = event["principal"]
    if not isinstance(event_principal, dict):
        _fail("owner authorization authorization_event.principal must be an object")
    zenodo._check_exact_keys(
        event_principal,
        {"name", "type"},
        "owner authorization authorization_event.principal",
    )
    if event_principal != principal:
        _fail("owner authorization authorization_event principal differs")
    if (
        event["candidate_return_receipt_sha256"]
        != proof["candidate_return_receipt"]["sha256"]
    ):
        _fail(
            "owner authorization authorization_event candidate return receipt "
            "digest differs"
        )
    _validate_identity(
        authorization["machine_proof"],
        expected_proof,
        "owner authorization machine_proof",
    )

    uploads = authorization["uploads"]
    if not isinstance(uploads, list) or len(uploads) != len(files):
        _fail("owner authorization uploads differ from the manifest upload set")
    for index, item in enumerate(uploads):
        where = f"owner authorization uploads[{index}]"
        if not isinstance(item, dict):
            _fail(f"{where} must be an object")
        zenodo._check_exact_keys(
            item,
            {"path", "name", "bytes", "sha256", "git_blob_sha"},
            where,
        )
    expected_uploads = [
        {
            "path": entry["path"],
            "name": entry["name"],
            "bytes": entry["size"],
            "sha256": entry["sha256"],
            "git_blob_sha": entry["git_blob_sha"],
        }
        for entry in files
    ]
    if uploads != expected_uploads:
        _fail("owner authorization uploads differ from the exact manifest bytes")
    if authorization["authorized_effects"] != list(OWNER_AUTHORIZED_EFFECTS):
        _fail("owner authorization allowed effects differ from the publisher effect set")

    return {
        "schema": OWNER_AUTHORIZATION_SCHEMA,
        **observed,
        "authorization_id": authorization_id,
        "nonce_digest": {
            "algorithm": "SHA-256",
            "value": nonce_digest_value,
        },
        "consumption_key": consumption_key,
        "single_use": True,
        "single_use_scope": SINGLE_USE_SCOPE,
        "remote_consumption_ref": consumption_ref,
        "attestation_scope": "PLATFORM_REPOSITORY_BOUND",
        "principal_authentication": "NOT_CRYPTOGRAPHICALLY_VERIFIED",
        "principal": dict(principal),
        "publication_id": authorization["publication_id"],
        "repository": repository,
        "source_head": source_head,
        "publication_evidence_path": evidence_relative,
        "canonical_metadata_sha256": expected_metadata_sha256,
        "candidate_return_receipt": dict(proof["candidate_return_receipt"]),
        "authorization_event": {
            "channel": event_channel,
            "authorized_at": event_authorized_at,
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": expected_statement,
            "statement_sha256": statement_sha256,
            "principal": dict(principal),
            "candidate_return_receipt_sha256": proof[
                "candidate_return_receipt"
            ]["sha256"],
        },
        "machine_proof": expected_proof,
        "authorized_effects": list(OWNER_AUTHORIZED_EFFECTS),
        "upload_count": len(files),
    }


def load_manifest(path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    """Load v1 for history or v2 for a proof-bearing new publication."""
    path = _manifest_path(root, path)
    value, raw = zenodo._load_json_file(path)
    schema = value.get("schema")
    common_keys = {
        "schema",
        "state",
        "confirm",
        "repository",
        "metadata",
        "files",
        "evidence_path",
    }
    if schema == SCHEMA:
        zenodo._check_exact_keys(value, common_keys, "manifest")
    elif schema == SCHEMA_V2:
        zenodo._check_exact_keys(
            value,
            common_keys | {"source_head", "machine_proof", "owner_authorization"},
            "manifest",
        )
    else:
        _fail("unsupported publication manifest schema")
    if value["state"] != "publish" or value["confirm"] != "PUBLISH_TO_PRODUCTION_ZENODO":
        _fail("production publication is not explicitly authorized")
    repository = value["repository"]
    expected_repository = os.environ.get("GITHUB_REPOSITORY")
    if not isinstance(repository, str) or (
        expected_repository is not None and repository != expected_repository
    ):
        _fail("manifest repository differs from the executing repository")
    metadata = _validate_metadata(value["metadata"])
    raw_files = value["files"]
    if not isinstance(raw_files, list) or not 1 <= len(raw_files) <= 100:
        _fail("manifest.files must contain between 1 and 100 entries")
    files = [
        _materialize_file(item, root, f"manifest.files[{index}]")
        for index, item in enumerate(raw_files)
    ]
    if len({item["name"] for item in files}) != len(files):
        _fail("manifest.files contains duplicate upload names")
    if len({item["path"] for item in files}) != len(files):
        _fail("manifest.files contains duplicate repository paths")
    evidence_path = _safe_relative(
        root, value["evidence_path"], "manifest.evidence_path", must_exist=False
    )
    proof = None
    owner_authorization = None
    source_head = None
    if schema == SCHEMA_V2:
        if evidence_path == path:
            _fail("v2 publication evidence must not overwrite its manifest")
        # This is the frozen pre-authorization source head. Comparing it to the
        # later execution commit would introduce an impossible self-reference.
        source_head = value["source_head"]
        if not isinstance(source_head, str) or HEX40.fullmatch(source_head) is None:
            _fail("manifest.source_head must be a lowercase Git commit SHA-1")
        proof = _validate_machine_proof(value["machine_proof"], root, files)
        owner_authorization = _validate_owner_authorization(
            value["owner_authorization"],
            root,
            repository,
            metadata,
            files,
            proof,
            evidence_path,
            source_head,
        )
    result = {
        "schema": schema,
        "repository": repository,
        "metadata": metadata,
        "files": files,
        "machine_proof": proof,
        "evidence_path": evidence_path,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }
    if schema == SCHEMA_V2:
        result["source_head"] = source_head
        result["owner_authorization"] = owner_authorization
    return result


def verify_files(
    manifest: Mapping[str, Any], root: pathlib.Path, token: str
) -> dict[tuple[str, str], bytes]:
    verified: dict[tuple[str, str], bytes] = {}
    for entry in manifest["files"]:
        shared_entry = {
            key: entry[key] for key in ("path", "name", "size", "md5", "sha256")
        }
        verified[("publication", entry["name"])] = zenodo._file_bytes(
            root, shared_entry, token
        )
    return verified


def _shared_entries(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: entry[key] for key in ("path", "name", "size", "md5", "sha256")}
        for entry in files
    ]


def _git(
    root: pathlib.Path,
    *arguments: str,
    accepted: frozenset[int] = frozenset({0}),
    input_text: str | None = None,
) -> tuple[int, str]:
    # Do not inherit the workflow environment: both publication credentials
    # are network-only capabilities and must never enter a child process.
    subprocess_environment = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    subprocess_environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            env=subprocess_environment,
            input=input_text,
            stdin=subprocess.DEVNULL if input_text is None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _fail(f"cannot execute the repository Git gate: {exc}")
    if completed.returncode not in accepted:
        _fail(
            "repository Git gate rejected operation "
            + " ".join(arguments[:2])
        )
    return completed.returncode, completed.stdout.strip()


def _validate_repository_source_head(
    root: pathlib.Path,
    manifest_path: pathlib.Path,
    manifest: Mapping[str, Any],
) -> str:
    """Bind the pre-authorization candidate head to the clean execution head."""
    _status, current_head = _git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if HEX40.fullmatch(current_head) is None:
        _fail("repository execution HEAD is not a lowercase Git commit SHA-1")
    github_sha = os.environ.get("GITHUB_SHA")
    if (
        not isinstance(github_sha, str)
        or HEX40.fullmatch(github_sha) is None
        or github_sha != current_head
    ):
        _fail("GITHUB_SHA differs from the checked-out repository execution HEAD")

    source_head = manifest["source_head"]
    _status, resolved_source = _git(
        root,
        "rev-parse",
        "--verify",
        f"{source_head}^{{commit}}",
    )
    if resolved_source != source_head:
        _fail("manifest.source_head does not resolve to its exact Git commit")
    ancestor_status, _output = _git(
        root,
        "merge-base",
        "--is-ancestor",
        source_head,
        current_head,
        accepted=frozenset({0, 1}),
    )
    if ancestor_status != 0:
        _fail("repository execution HEAD is not a descendant of manifest.source_head")

    for candidate in manifest["machine_proof"]["returned_candidate_files"]:
        _status, source_blob = _git(
            root,
            "rev-parse",
            "--verify",
            f"{source_head}:{candidate['path']}",
        )
        if source_blob != candidate["git_blob_sha"]:
            _fail(
                "candidate-return Git blob differs from manifest.source_head for "
                + candidate["path"]
            )

    try:
        manifest_relative = manifest_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        _fail("v2 manifest must be inside the repository execution root")
    manifest_raw = zenodo.read_regular_file(manifest_path, zenodo.MAX_JSON_BYTES)
    active_policy_path = _safe_relative(
        root,
        machine_proof.POLICY_PATH,
        "active machine-proof policy",
        must_exist=True,
    )
    active_policy, active_policy_raw = zenodo._load_json_file(active_policy_path)
    schema_contracts = active_policy.get("schema_contracts")
    if not isinstance(schema_contracts, dict):
        _fail("active machine-proof policy lacks exact schema contracts")
    bundle_contract = schema_contracts.get("machine_proof_bundle")
    return_contract = schema_contracts.get("prepublication_return_receipt")
    if not isinstance(bundle_contract, dict) or not isinstance(return_contract, dict):
        _fail("active machine-proof policy schema contracts are incomplete")
    control_specs = (
        (
            machine_proof.POLICY_PATH,
            machine_proof.POLICY_GIT_BLOB_SHA1,
            active_policy_raw,
        ),
        (
            machine_proof.BUNDLE_SCHEMA_PATH,
            bundle_contract.get("git_blob_sha1"),
            None,
        ),
        (
            machine_proof.RETURN_SCHEMA_PATH,
            return_contract.get("git_blob_sha1"),
            None,
        ),
        (
            machine_proof.LEGACY_POLICY_PATH,
            machine_proof.LEGACY_POLICY_GIT_BLOB_SHA1,
            None,
        ),
        (
            machine_proof.LEGACY_BUNDLE_SCHEMA_PATH,
            machine_proof.LEGACY_BUNDLE_SCHEMA_GIT_BLOB_SHA1,
            None,
        ),
        (
            machine_proof.LEGACY_RETURN_SCHEMA_PATH,
            machine_proof.LEGACY_RETURN_SCHEMA_GIT_BLOB_SHA1,
            None,
        ),
    )
    control_blobs: dict[str, str] = {}
    for relative, expected_blob, already_read in control_specs:
        if not isinstance(expected_blob, str) or HEX40.fullmatch(expected_blob) is None:
            _fail("machine-proof policy/schema control has an invalid Git identity")
        control_path = _safe_relative(
            root,
            relative,
            "machine-proof policy/schema execution control",
            must_exist=True,
        )
        control_raw = (
            already_read
            if already_read is not None
            else zenodo.read_regular_file(control_path, zenodo.MAX_JSON_BYTES)
        )
        observed_blob = _git_blob_sha(control_raw)
        if observed_blob != expected_blob:
            _fail(
                "machine-proof policy/schema bytes differ from their exact "
                "v1/v2 contract for "
                + relative
            )
        control_blobs[relative] = observed_blob
    if len(control_blobs) != 6:
        _fail("machine-proof execution controls must contain six distinct paths")

    execution_blobs = {
        entry["path"]: entry["git_blob_sha"] for entry in manifest["files"]
    }
    execution_blobs[manifest_relative] = _git_blob_sha(manifest_raw)
    execution_blobs[manifest["owner_authorization"]["path"]] = manifest[
        "owner_authorization"
    ]["git_blob_sha"]
    execution_blobs.update(control_blobs)
    if len(execution_blobs) != len(manifest["files"]) + 2 + len(control_blobs):
        _fail("upload and control paths overlap in the v2 execution scope")

    for raw_path, expected_blob in execution_blobs.items():
        execution_status, execution_blob = _git(
            root,
            "rev-parse",
            "--verify",
            f"{current_head}:{raw_path}",
            accepted=frozenset({0, 128}),
        )
        if execution_status != 0 or execution_blob != expected_blob:
            _fail(
                "upload/control bytes are not committed at the execution HEAD for "
                + raw_path
            )
    _status, dirty = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *sorted(execution_blobs),
    )
    if dirty:
        _fail("upload/control paths are not clean at the repository execution HEAD")
    return current_head


def _reject_tokens_in_publication_bytes(
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    manifest: Mapping[str, Any],
    verified: Mapping[tuple[str, str], bytes],
    secrets_by_name: Mapping[str, str],
) -> None:
    """Reject both network capabilities throughout outbound/control bytes."""
    control_paths = (
        ("publication manifest", manifest_path, zenodo.MAX_JSON_BYTES),
        (
            "owner authorization",
            _safe_relative(
                root,
                manifest["owner_authorization"]["path"],
                "normalized owner authorization path",
                must_exist=True,
            ),
            zenodo.MAX_JSON_BYTES,
        ),
        (
            "machine-proof bundle",
            _safe_relative(
                root,
                manifest["machine_proof"]["path"],
                "normalized machine-proof bundle path",
                must_exist=True,
            ),
            zenodo.MAX_JSON_BYTES,
        ),
        (
            "prepublication return receipt",
            _safe_relative(
                root,
                manifest["machine_proof"]["candidate_return_receipt"]["path"],
                "normalized prepublication return receipt path",
                must_exist=True,
            ),
            zenodo.MAX_JSON_BYTES,
        ),
    )
    byte_sets: list[tuple[str, bytes]] = [
        (
            "canonical Zenodo metadata",
            zenodo._json_bytes(manifest["metadata"]),
        )
    ]
    byte_sets.extend(
        (where, zenodo.read_regular_file(path, maximum))
        for where, path, maximum in control_paths
    )
    byte_sets.extend(
        (f"upload {name}", data)
        for (_kind, name), data in verified.items()
    )
    for where, data in byte_sets:
        for name, secret in secrets_by_name.items():
            if secret and secret.encode("utf-8") in data:
                _fail(f"{where} contains the {_secret_label(name)}")


def _validated_network_secrets() -> dict[str, str]:
    zenodo_token = os.environ.get(zenodo.TOKEN_ENVIRONMENT_VARIABLE, "")
    github_token = os.environ.get(GITHUB_TOKEN_ENVIRONMENT_VARIABLE, "")
    for name, token in (
        (zenodo.TOKEN_ENVIRONMENT_VARIABLE, zenodo_token),
        (GITHUB_TOKEN_ENVIRONMENT_VARIABLE, github_token),
    ):
        if len(token) < 20 or any(character.isspace() for character in token):
            _fail(f"{name} is missing or structurally invalid")
    if zenodo_token == github_token:
        _fail("GitHub and Zenodo credentials must be distinct capabilities")
    return {
        zenodo.TOKEN_ENVIRONMENT_VARIABLE: zenodo_token,
        GITHUB_TOKEN_ENVIRONMENT_VARIABLE: github_token,
    }


def _origin_repository_identity(raw: str) -> str:
    """Accept only the pinned GitHub HTTPS/SSH authority origin."""
    if (
        not isinstance(raw, str)
        or not raw
        or raw != raw.strip()
        or any(character in raw for character in ("\x00", "\r", "\n"))
    ):
        _fail("origin push URL is structurally invalid")
    expected_path = "/Goldkelch/qik-vrt"
    if raw in {
        "git@github.com:Goldkelch/qik-vrt",
        "git@github.com:Goldkelch/qik-vrt.git",
    }:
        return PRODUCTION_REPOSITORY
    if "://" in raw:
        parsed = urllib.parse.urlsplit(raw)
        try:
            port = parsed.port
        except ValueError:
            _fail("origin URL has an invalid port")
        if (
            parsed.query
            or parsed.fragment
            or parsed.path not in {expected_path, expected_path + ".git"}
        ):
            _fail("origin URL differs from the pinned GitHub repository path")
        if (
            parsed.scheme == "https"
            and parsed.netloc == PRODUCTION_GITHUB_HOST
            and parsed.username is None
            and parsed.password is None
            and port is None
        ):
            return PRODUCTION_REPOSITORY
        if (
            parsed.scheme == "ssh"
            and parsed.netloc == "git@" + PRODUCTION_GITHUB_HOST
            and parsed.username == "git"
            and parsed.password is None
            and port is None
        ):
            return PRODUCTION_REPOSITORY
    _fail("origin must be exact GitHub HTTPS or SSH for Goldkelch/qik-vrt")


def _validate_origin_repository(root: pathlib.Path, repository: str) -> None:
    if repository != PRODUCTION_REPOSITORY:
        _fail("manifest repository is not the pinned production authority")
    _status, raw_urls = _git(
        root,
        "remote",
        "get-url",
        "--push",
        "--all",
        "origin",
    )
    urls = raw_urls.splitlines()
    if len(urls) != 1:
        _fail("origin must have exactly one repository-bound push URL")
    if _origin_repository_identity(urls[0]) != PRODUCTION_REPOSITORY:
        _fail("origin differs from the pinned production authority")


class _NoCredentialRedirect(urllib.request.HTTPRedirectHandler):
    """Never relay a bearer credential through an HTTP redirect."""

    def redirect_request(  # type: ignore[override]
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


def _github_api_request(
    method: str,
    path: str,
    token: str,
    *,
    payload: Mapping[str, Any] | None = None,
    accept: tuple[int, ...] = (200,),
) -> tuple[int, dict[str, Any]]:
    """Use only the pinned GitHub Git-Data REST origin, with redacted errors."""
    repository_prefix = "/repos/Goldkelch/qik-vrt/"
    if not path.startswith(repository_prefix) or any(
        character in path for character in ("\x00", "\r", "\n", "?", "#")
    ):
        _fail("GitHub API path escaped the pinned production repository")
    if len(token) < 20 or any(character.isspace() for character in token):
        _fail(f"{GITHUB_TOKEN_ENVIRONMENT_VARIABLE} is missing or structurally invalid")
    if method not in {"GET", "POST"}:
        _fail("unsupported GitHub Git-Data API method")
    url = GITHUB_API_BASE + path
    body = None if payload is None else zenodo._json_bytes(payload)
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "User-Agent": "qik-vrt-zenodo-publisher",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
    )
    opener = urllib.request.build_opener(_NoCredentialRedirect())
    response: Any
    try:
        response = opener.open(request, timeout=30)
    except urllib.error.HTTPError as exc:
        response = exc
    except (OSError, urllib.error.URLError) as exc:
        _fail(f"GitHub Git-Data API transport failed: {type(exc).__name__}")
    try:
        status = int(response.status)
        if response.geturl() != url:
            _fail("GitHub Git-Data API response origin changed")
        raw = response.read(MAX_GITHUB_RESPONSE_BYTES + 1)
    finally:
        response.close()
    if len(raw) > MAX_GITHUB_RESPONSE_BYTES:
        _fail("GitHub Git-Data API response exceeded its byte limit")
    if status not in accept:
        # Response bodies are intentionally not reflected: they are untrusted
        # and can contain credential-shaped input echoed by an upstream proxy.
        _fail(f"GitHub Git-Data API rejected {method} (HTTP {status})")
    if not raw:
        return status, {}
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("GitHub Git-Data API returned invalid JSON")
    if not isinstance(value, dict):
        _fail("GitHub Git-Data API returned a non-object response")
    serialized = zenodo._json_bytes(value)
    if token.encode("utf-8") in serialized:
        _fail("GitHub Git-Data API response contained its bearer credential")
    return status, value


def _github_ref_path(ref: str) -> str:
    if not ref.startswith("refs/tags/"):
        _fail("remote authorization consumption ref is not a tag ref")
    suffix = ref.removeprefix("refs/")
    return "/repos/Goldkelch/qik-vrt/git/ref/" + urllib.parse.quote(
        suffix,
        safe="/",
    )


def _validate_github_ref_response(
    value: Mapping[str, Any],
    ref: str,
    tag_object: str,
) -> None:
    target = value.get("object")
    if (
        value.get("ref") != ref
        or not isinstance(target, dict)
        or target.get("sha") != tag_object
        or target.get("type") != "tag"
    ):
        _fail("GitHub consumption ref differs from its exact annotated tag")


def _canonical_github_tagger_date(raw: str) -> str:
    parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    normalized = parsed.astimezone(datetime.timezone.utc).isoformat()
    return normalized.replace("+00:00", "Z")


def _expected_consumption_tag(
    manifest: Mapping[str, Any],
    execution_head: str,
) -> dict[str, Any]:
    authorization = manifest["owner_authorization"]
    ref = authorization["remote_consumption_ref"]
    consumption_key = authorization["consumption_key"]
    message = (
        "schema=qikvrt_zenodo_remote_consumption_tag_v1\n"
        f"repository={manifest['repository']}\n"
        f"authorization_id={authorization['authorization_id']}\n"
        f"publication_id={authorization['publication_id']}\n"
        f"authorization_statement_sha256="
        f"{authorization['authorization_event']['statement_sha256']}\n"
        f"authorization_consumption_key={consumption_key['value']}\n"
        f"authorization_nonce_sha256={authorization['nonce_digest']['value']}\n"
        f"manifest_sha256={manifest['manifest_sha256']}\n"
        f"source_head={manifest['source_head']}\n"
        f"execution_head={execution_head}\n"
    )
    return {
        "tag": ref.removeprefix("refs/tags/"),
        "message": message,
        "object": execution_head,
        "type": "commit",
        "tagger": {
            "name": "QIK-VRT Zenodo Publisher",
            "email": "qik-vrt-zenodo@users.noreply.github.com",
            "date": _canonical_github_tagger_date(
                authorization["authorization_event"]["authorized_at"]
            ),
        },
    }


def _validate_github_tag_response(
    value: Mapping[str, Any],
    expected: Mapping[str, Any],
    tag_object: str,
) -> None:
    target = value.get("object")
    tagger = value.get("tagger")
    if (
        value.get("sha") != tag_object
        or value.get("tag") != expected["tag"]
        or value.get("message") != expected["message"]
        or not isinstance(target, dict)
        or target.get("sha") != expected["object"]
        or target.get("type") != "commit"
        or not isinstance(tagger, dict)
        or {key: tagger.get(key) for key in ("name", "email", "date")}
        != expected["tagger"]
    ):
        _fail("GitHub annotated consumption tag differs from the exact decision")


def _read_exact_existing_consumption_lock(
    manifest: Mapping[str, Any],
    execution_head: str,
    github_token: str,
    ref_value: Mapping[str, Any],
) -> dict[str, str]:
    ref = manifest["owner_authorization"]["remote_consumption_ref"]
    target = ref_value.get("object")
    tag_object = target.get("sha") if isinstance(target, dict) else None
    if not isinstance(tag_object, str) or HEX40.fullmatch(tag_object) is None:
        _fail("existing GitHub consumption ref has an invalid tag identity")
    _validate_github_ref_response(ref_value, ref, tag_object)
    status, tag_value = _github_api_request(
        "GET",
        "/repos/Goldkelch/qik-vrt/git/tags/" + tag_object,
        github_token,
        accept=(200, 404),
    )
    if status != 200:
        _fail("existing GitHub consumption ref lacks its annotated tag object")
    _validate_github_tag_response(
        tag_value,
        _expected_consumption_tag(manifest, execution_head),
        tag_object,
    )
    return {
        "remote": "github_git_data_api",
        "api_origin": GITHUB_API_BASE,
        "repository": manifest["repository"],
        "ref": ref,
        "tag_object": tag_object,
        "object_type": "tag",
        "execution_head": execution_head,
        "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
        "recovery_mode": "EXISTING_EXACT_REF_NO_CREATE",
    }


def _acquire_remote_consumption_lock(
    root: pathlib.Path,
    manifest: Mapping[str, Any],
    execution_head: str,
    github_token: str,
) -> dict[str, str]:
    """Consume one decision through GitHub's atomic create-only Ref API."""
    authorization = manifest["owner_authorization"]
    repository = manifest["repository"]
    ref = authorization["remote_consumption_ref"]
    consumption_key = authorization["consumption_key"]
    if ref != _remote_consumption_ref(consumption_key["value"]):
        _fail("normalized owner authorization remote consumption ref differs")
    _validate_origin_repository(root, repository)
    ref_path = _github_ref_path(ref)
    existing_status, existing = _github_api_request(
        "GET",
        ref_path,
        github_token,
        accept=(200, 404),
    )
    if existing_status == 200:
        return _read_exact_existing_consumption_lock(
            manifest,
            execution_head,
            github_token,
            existing,
        )

    expected_tag = _expected_consumption_tag(manifest, execution_head)
    tag_status, tag_value = _github_api_request(
        "POST",
        "/repos/Goldkelch/qik-vrt/git/tags",
        github_token,
        payload=expected_tag,
        accept=(201,),
    )
    if tag_status != 201:
        _fail("GitHub did not create the annotated consumption tag object")
    tag_object = tag_value.get("sha")
    if not isinstance(tag_object, str) or HEX40.fullmatch(tag_object) is None:
        _fail("GitHub returned an invalid annotated consumption tag identity")
    _validate_github_tag_response(tag_value, expected_tag, tag_object)

    create_status, created = _github_api_request(
        "POST",
        "/repos/Goldkelch/qik-vrt/git/refs",
        github_token,
        payload={"ref": ref, "sha": tag_object},
        accept=(201, 422),
    )
    if create_status != 201:
        raced_status, raced = _github_api_request(
            "GET",
            ref_path,
            github_token,
            accept=(200, 404),
        )
        if raced_status != 200:
            _fail(
                "remote authorization consumption lock was rejected without an "
                "exact recoverable ref"
            )
        return _read_exact_existing_consumption_lock(
            manifest,
            execution_head,
            github_token,
            raced,
        )
    _validate_github_ref_response(created, ref, tag_object)
    observed_status, observed = _github_api_request(
        "GET",
        ref_path,
        github_token,
        accept=(200,),
    )
    if observed_status != 200:
        _fail("GitHub consumption ref disappeared after create-only acquisition")
    _validate_github_ref_response(observed, ref, tag_object)
    return {
        "remote": "github_git_data_api",
        "api_origin": GITHUB_API_BASE,
        "repository": repository,
        "ref": ref,
        "tag_object": tag_object,
        "object_type": "tag",
        "execution_head": execution_head,
        "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
        "recovery_mode": "NEWLY_CREATED_REF",
    }


def _create_consumption_receipt(
    path: pathlib.Path,
    value: Mapping[str, Any],
    secrets_by_name: Mapping[str, str],
) -> None:
    """Persist a local recovery marker after the remote ref consumed authorization."""
    serialized = zenodo._json_bytes(value) + b"\n"
    for name, secret in secrets_by_name.items():
        if secret and secret.encode("utf-8") in serialized:
            _fail(
                "refusing to write recovery evidence containing the "
                + _secret_label(name)
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        _fail(
            "publication evidence or authorization consumption receipt already "
            "exists; remote reconciliation is required"
        )
    except OSError as exc:
        _fail(f"cannot create authorization consumption receipt: {exc.strerror}")
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(serialized):
            written = os.write(descriptor, serialized[offset:])
            if written <= 0:
                _fail("authorization consumption receipt write made no progress")
            offset += written
        os.fsync(descriptor)
    except OSError as exc:
        _fail(
            "authorization consumption receipt write failed; its path remains "
            f"consumed for reconciliation: {exc.strerror}"
        )
    finally:
        os.close(descriptor)


def _atomic_recovery_evidence(
    path: pathlib.Path,
    value: Mapping[str, Any],
    secrets_by_name: Mapping[str, str],
) -> None:
    serialized = zenodo._json_bytes(value) + b"\n"
    for name, secret in secrets_by_name.items():
        if secret and secret.encode("utf-8") in serialized:
            _fail(
                "refusing to write recovery evidence containing the "
                + _secret_label(name)
            )
    # The shared helper uses create-fsync-replace and rejects result symlinks.
    zenodo._atomic_json(
        path,
        value,
        secrets_by_name.get(zenodo.TOKEN_ENVIRONMENT_VARIABLE, ""),
    )


def _load_evidence_without_secrets(
    path: pathlib.Path,
    secrets_by_name: Mapping[str, str],
) -> tuple[dict[str, Any], bytes]:
    value, raw = zenodo._load_json_file(
        path,
        secrets_by_name.get(zenodo.TOKEN_ENVIRONMENT_VARIABLE, ""),
    )
    for name, secret in secrets_by_name.items():
        if secret and secret.encode("utf-8") in raw:
            _fail(f"publication evidence contains the {_secret_label(name)}")
    return value, raw


def _reject_owner_authorization_replay(
    root: pathlib.Path,
    authorization: Mapping[str, Any],
    secrets_by_name: Mapping[str, str],
    *,
    current_evidence_path: pathlib.Path | None = None,
) -> None:
    """Reject a decision key, ID or nonce consumed by any other evidence."""
    authorization_id = authorization["authorization_id"]
    nonce_digest = authorization["nonce_digest"]
    consumption_key = authorization["consumption_key"]
    inspected = 0

    def walk_error(exc: OSError) -> NoReturn:
        _fail(f"cannot inspect publication evidence for authorization replay: {exc}")

    for directory, names, filenames in os.walk(
        root,
        topdown=True,
        onerror=walk_error,
        followlinks=False,
    ):
        base = pathlib.Path(directory)
        names[:] = [
            name
            for name in names
            if name != ".git" and not (base / name).is_symlink()
        ]
        if "zenodo-publication.json" not in filenames:
            continue
        inspected += 1
        if inspected > 4096:
            _fail("publication evidence replay scan exceeds the bounded file count")
        evidence_path = base / "zenodo-publication.json"
        if (
            current_evidence_path is not None
            and evidence_path.resolve() == current_evidence_path.resolve()
        ):
            continue
        evidence, _raw = _load_evidence_without_secrets(
            evidence_path,
            secrets_by_name,
        )
        if evidence.get("schema") not in {EVIDENCE_SCHEMA, EVIDENCE_SCHEMA_V2}:
            continue
        consumed = evidence.get("owner_authorization")
        if not isinstance(consumed, dict):
            continue
        if (
            consumed.get("authorization_id") == authorization_id
            or consumed.get("nonce_digest") == nonce_digest
            or consumed.get("consumption_key") == consumption_key
        ):
            _fail(
                "owner authorization decision key, authorization_id or nonce has "
                "already been consumed by publication evidence"
            )


def _recovery_binding(
    manifest: Mapping[str, Any],
    execution_head: str,
) -> dict[str, Any]:
    authorization = manifest["owner_authorization"]
    return {
        "schema": CONSUMPTION_KEY_SCHEMA,
        "repository": manifest["repository"],
        "authorization_id": authorization["authorization_id"],
        "publication_id": authorization["publication_id"],
        "statement_sha256": authorization["authorization_event"][
            "statement_sha256"
        ],
        "consumption_key": authorization["consumption_key"],
        "manifest_sha256": manifest["manifest_sha256"],
        "source_head": manifest["source_head"],
        "execution_head": execution_head,
    }


def _recovery_flags(phase: str) -> dict[str, bool | str]:
    try:
        position = RECOVERY_PHASES.index(phase)
    except ValueError:
        _fail("publication recovery phase is unsupported")
    return {
        "phase": phase,
        "authorization_consumed": position >= RECOVERY_PHASES.index(
            "authorization_consumed"
        ),
        "create_requested": position >= RECOVERY_PHASES.index("create_requested"),
        "record_created": position >= RECOVERY_PHASES.index("record_created"),
        "prepared": position >= RECOVERY_PHASES.index("prepared"),
        "publish_requested": position >= RECOVERY_PHASES.index(
            "publish_requested"
        ),
        "public_verified": position >= RECOVERY_PHASES.index("public_verified"),
        "duplicate_remote_mutation_forbidden": True,
        "remote_state_requires_reconciliation": phase != "public_verified",
    }


def _public_record_identity(
    published: Mapping[str, Any],
    record_id: int,
    doi: str,
) -> tuple[str, str]:
    if zenodo._record_id(published, "gated public evidence") != record_id:
        _fail("gated public record ID differs from recovery evidence")
    if zenodo._doi_from_deposition(published, "gated public evidence") != doi:
        _fail("gated public DOI differs from recovery evidence")
    metadata = published.get("metadata")
    conceptdoi = published.get("conceptdoi") or (
        metadata.get("conceptdoi") if isinstance(metadata, dict) else None
    )
    if not isinstance(conceptdoi, str) or ZENODO_DOI.fullmatch(conceptdoi) is None:
        _fail("gated public record lacks a valid Zenodo concept DOI")
    links = published.get("links")
    candidate = links.get("html") if isinstance(links, dict) else None
    record_url = (
        candidate
        if isinstance(candidate, str)
        else f"https://zenodo.org/records/{record_id}"
    )
    parts = urllib.parse.urlsplit(record_url)
    try:
        port = parts.port
    except ValueError:
        _fail("gated public record URL has an invalid port")
    origin = f"{parts.scheme}://{parts.hostname or ''}"
    if (
        parts.scheme != "https"
        or origin not in zenodo.ALLOWED_ORIGINS
        or parts.username is not None
        or parts.password is not None
        or port not in (None, 443)
        or parts.query
        or parts.fragment
        or parts.path != f"/records/{record_id}"
    ):
        _fail("gated public record URL is not the exact allowlisted Zenodo record")
    return conceptdoi, record_url


def _phase_evidence(
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    manifest: Mapping[str, Any],
    execution_head: str,
    remote_consumption: Mapping[str, Any],
    phase: str,
    *,
    record_id: int | None = None,
    doi: str | None = None,
    published: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    flags = _recovery_flags(phase)
    evidence: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA_V2,
        "state": "published" if phase == "public_verified" else CONSUMPTION_STATE,
        "phase": phase,
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": manifest["manifest_sha256"],
        "machine_proof": manifest["machine_proof"],
        "owner_authorization": manifest["owner_authorization"],
        "remote_consumption": dict(remote_consumption),
        "repository": manifest["repository"],
        "repository_commit": execution_head,
        "source_head": manifest["source_head"],
        "binding": _recovery_binding(manifest, execution_head),
        "governance_boundaries": list(GOVERNANCE_BOUNDARIES),
        "recovery": flags,
    }
    has_record = RECOVERY_PHASES.index(phase) >= RECOVERY_PHASES.index(
        "record_created"
    )
    if has_record:
        if (
            isinstance(record_id, bool)
            or not isinstance(record_id, int)
            or record_id <= 0
            or not isinstance(doi, str)
            or zenodo.DOI.fullmatch(doi) is None
        ):
            _fail("record-bearing recovery evidence lacks an exact record ID or DOI")
        evidence.update(
            {
                "record_id": record_id,
                "doi": doi,
                "title": manifest["metadata"]["title"],
                "version": manifest["metadata"]["version"],
                "files": manifest["files"],
            }
        )
    if phase == "public_verified":
        if not isinstance(published, Mapping):
            _fail("public_verified recovery evidence lacks the gated public record")
        conceptdoi, record_url = _public_record_identity(
            published,
            record_id,
            doi,
        )
        evidence.update(
            {
                "conceptdoi": conceptdoi,
                "record_url": record_url,
            }
        )
    return evidence


def _validate_recovery_evidence(
    value: Mapping[str, Any],
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    manifest: Mapping[str, Any],
    execution_head: str,
) -> dict[str, Any]:
    if value.get("schema") == EVIDENCE_SCHEMA:
        _fail(
            "legacy v1 publication evidence is immutable and requires manual "
            "reconciliation"
        )
    if value.get("schema") != EVIDENCE_SCHEMA_V2:
        _fail("publication recovery evidence schema is unsupported")
    phase = value.get("phase")
    if not isinstance(phase, str) or phase not in RECOVERY_PHASES:
        _fail("publication recovery evidence phase is unsupported")
    expected_state = "published" if phase == "public_verified" else CONSUMPTION_STATE
    if value.get("state") != expected_state:
        _fail("publication recovery evidence state differs from its phase")
    expected_keys = {
        "schema",
        "state",
        "phase",
        "manifest_path",
        "manifest_sha256",
        "machine_proof",
        "owner_authorization",
        "remote_consumption",
        "repository",
        "repository_commit",
        "source_head",
        "binding",
        "governance_boundaries",
        "recovery",
    }
    if RECOVERY_PHASES.index(phase) >= RECOVERY_PHASES.index("record_created"):
        expected_keys |= {"record_id", "doi", "title", "version", "files"}
    if phase == "public_verified":
        expected_keys |= {"conceptdoi", "record_url"}
    zenodo._check_exact_keys(value, expected_keys, "publication recovery evidence")
    expected_binding = _recovery_binding(manifest, execution_head)
    if value.get("binding") != expected_binding:
        _fail("publication recovery evidence differs from the exact authorization")
    if value.get("governance_boundaries") != list(GOVERNANCE_BOUNDARIES):
        _fail("publication recovery governance boundaries differ")
    expected_manifest_path = manifest_path.relative_to(root).as_posix()
    exact_common = {
        "manifest_path": expected_manifest_path,
        "manifest_sha256": manifest["manifest_sha256"],
        "machine_proof": manifest["machine_proof"],
        "owner_authorization": manifest["owner_authorization"],
        "repository": manifest["repository"],
        "repository_commit": execution_head,
        "source_head": manifest["source_head"],
        "recovery": _recovery_flags(phase),
    }
    for key, expected in exact_common.items():
        if value.get(key) != expected:
            _fail(f"publication recovery evidence {key} binding differs")
    remote = value.get("remote_consumption")
    authorization = manifest["owner_authorization"]
    if not isinstance(remote, dict):
        _fail("publication recovery evidence lacks remote consumption identity")
    zenodo._check_exact_keys(
        remote,
        {
            "remote",
            "api_origin",
            "repository",
            "ref",
            "tag_object",
            "object_type",
            "execution_head",
            "acquisition",
            "recovery_mode",
        },
        "publication recovery remote_consumption",
    )
    if (
        remote["remote"] != "github_git_data_api"
        or remote["api_origin"] != GITHUB_API_BASE
        or remote["repository"] != PRODUCTION_REPOSITORY
        or remote["ref"] != authorization["remote_consumption_ref"]
        or not isinstance(remote["tag_object"], str)
        or HEX40.fullmatch(remote["tag_object"]) is None
        or remote["object_type"] != "tag"
        or remote["execution_head"] != execution_head
        or remote["acquisition"] != "GITHUB_GIT_DATA_REST_CREATE_ONLY"
        or remote["recovery_mode"]
        not in {"NEWLY_CREATED_REF", "EXISTING_EXACT_REF_NO_CREATE"}
    ):
        _fail("publication recovery remote consumption binding differs")
    has_record = RECOVERY_PHASES.index(phase) >= RECOVERY_PHASES.index(
        "record_created"
    )
    if has_record:
        record_id = value.get("record_id")
        doi = value.get("doi")
        if (
            isinstance(record_id, bool)
            or not isinstance(record_id, int)
            or record_id <= 0
            or not isinstance(doi, str)
            or zenodo.DOI.fullmatch(doi) is None
            or value.get("title") != manifest["metadata"]["title"]
            or value.get("version") != manifest["metadata"]["version"]
            or value.get("files") != manifest["files"]
        ):
            _fail("publication recovery record binding differs")
    elif "record_id" in value or "doi" in value:
        _fail("pre-record recovery evidence may not claim a Zenodo record")
    if phase == "public_verified":
        conceptdoi, record_url = _public_record_identity(
            {
                "id": value["record_id"],
                "doi": value["doi"],
                "conceptdoi": value.get("conceptdoi"),
                "links": {"html": value.get("record_url")},
            },
            value["record_id"],
            value["doi"],
        )
        if (
            value.get("conceptdoi") != conceptdoi
            or value.get("record_url") != record_url
        ):
            _fail("public_verified public identity differs")
    return dict(value)


def _verify_remote_consumption_lock(
    remote: Mapping[str, Any],
    manifest: Mapping[str, Any],
    execution_head: str,
    github_token: str,
) -> None:
    status, observed = _github_api_request(
        "GET",
        _github_ref_path(remote["ref"]),
        github_token,
        accept=(200, 404),
    )
    if status != 200:
        _fail("persisted GitHub consumption ref is absent during reconciliation")
    exact = _read_exact_existing_consumption_lock(
        manifest,
        execution_head,
        github_token,
        observed,
    )
    if exact["tag_object"] != remote["tag_object"]:
        _fail("persisted GitHub consumption tag identity changed")


def _owned_deposition_inventory_pass(
    client: zenodo.ZenodoClient,
    token: str,
) -> list[dict[str, Any]]:
    """Read every bounded legacy-deposition page from the pinned Zenodo origin."""
    base_url = zenodo.validate_base_url(client.base_url)
    opener = urllib.request.build_opener(_NoCredentialRedirect())
    observed: dict[int, dict[str, Any]] = {}
    for page in range(1, MAX_INVENTORY_PAGES + 1):
        query = urllib.parse.urlencode(
            {"page": page, "size": INVENTORY_PAGE_SIZE}
        )
        url = base_url + "/deposit/depositions?" + query
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + token,
                "User-Agent": "qik-vrt-zenodo-publisher",
            },
        )
        response: Any
        try:
            response = opener.open(request, timeout=60)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, urllib.error.URLError) as exc:
            _fail(f"Zenodo inventory transport failed: {type(exc).__name__}")
        try:
            status = int(response.status)
            if response.geturl() != url:
                _fail("Zenodo inventory response URL changed")
            raw = response.read(zenodo.MAX_JSON_BYTES + 1)
        finally:
            response.close()
        if status != 200:
            _fail(f"Zenodo inventory request was rejected (HTTP {status})")
        if len(raw) > zenodo.MAX_JSON_BYTES:
            _fail("Zenodo inventory page exceeded its byte limit")
        if token.encode("utf-8") in raw:
            _fail("Zenodo inventory response contained its bearer credential")
        try:
            page_value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            _fail("Zenodo inventory returned invalid JSON")
        if not isinstance(page_value, list) or not all(
            isinstance(item, dict) for item in page_value
        ):
            _fail("Zenodo inventory page must be an array of objects")
        if len(page_value) > INVENTORY_PAGE_SIZE:
            _fail("Zenodo inventory exceeded the requested page-size bound")
        if not page_value:
            return [observed[key] for key in sorted(observed)]
        for item in page_value:
            record_id = zenodo._record_id(item, "owned deposition inventory")
            if record_id in observed:
                _fail("Zenodo paginated inventory repeated a record ID")
            observed[record_id] = item
        if len(page_value) < INVENTORY_PAGE_SIZE:
            return [observed[key] for key in sorted(observed)]
    _fail("Zenodo owned-deposition inventory exceeded its bounded page count")


def _list_all_owned_depositions(
    client: zenodo.ZenodoClient,
    token: str,
) -> list[dict[str, Any]]:
    """Require two identical complete passes before making uniqueness claims."""
    first = _owned_deposition_inventory_pass(client, token)
    second = _owned_deposition_inventory_pass(client, token)
    if zenodo._json_bytes(first) != zenodo._json_bytes(second):
        _fail("Zenodo owned-deposition inventory changed between complete passes")
    return first


def _inventory_publication_identity_candidate(
    value: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> bool:
    actual = value.get("metadata")
    return (
        isinstance(actual, dict)
        and actual.get("title") == metadata["title"]
        and actual.get("version") == metadata["version"]
        and zenodo._metadata_matches(
            actual.get("creators"),
            metadata["creators"],
        )
    )


def _canonical_inventory_candidates(
    client: zenodo.ZenodoClient,
    zenodo_token: str,
    metadata: Mapping[str, Any],
    entries: list[dict[str, Any]],
) -> list[tuple[int, str, dict[str, Any] | None]]:
    inventory = _list_all_owned_depositions(client, zenodo_token)
    matches: list[tuple[int, str, dict[str, Any] | None]] = []
    for item in inventory:
        if not _inventory_publication_identity_candidate(item, metadata):
            continue
        record_id = zenodo._record_id(item, "create-request recovery inventory")
        state, current = client.get_deposition_or_record(record_id)
        doi = zenodo._doi_from_deposition(current, "create-request recovery record")
        if state == "published":
            if not zenodo._published_metadata_matches(
                current.get("metadata"),
                metadata,
            ):
                _fail(
                    "publication-identity candidate has divergent public metadata"
                )
            public = client.wait_for_gated_record(
                record_id,
                metadata,
                entries,
                doi,
                published=True,
                initial=current,
            )
            matches.append((record_id, doi, public))
            continue
        expected_metadata = dict(metadata)
        expected_metadata.pop("prereserve_doi", None)
        if not zenodo._metadata_matches(current.get("metadata"), expected_metadata):
            _fail(
                "publication-identity candidate has divergent draft metadata"
            )
        server_files = client._server_files(current)
        if server_files:
            client.gate_record(
                current,
                record_id,
                metadata,
                entries,
                doi,
                published=False,
            )
        matches.append((record_id, doi, None))
    return matches


def _recover_create_requested_record(
    client: zenodo.ZenodoClient,
    zenodo_token: str,
    metadata: Mapping[str, Any],
    entries: list[dict[str, Any]],
) -> tuple[int, str, dict[str, Any] | None]:
    """Resolve exactly one prior create POST; never issue another create."""
    matches = _canonical_inventory_candidates(
        client,
        zenodo_token,
        metadata,
        entries,
    )
    if len(matches) != 1:
        _fail(
            "create-request recovery requires exactly one canonically matching "
            f"owned deposition; observed {len(matches)}"
        )
    return matches[0]


def _gate_precreate_inventory(
    client: zenodo.ZenodoClient,
    zenodo_token: str,
    metadata: Mapping[str, Any],
    entries: list[dict[str, Any]],
) -> None:
    """Prove absence before the first create intent; never silently adopt a record."""
    matches = _canonical_inventory_candidates(
        client,
        zenodo_token,
        metadata,
        entries,
    )
    if matches:
        _fail(
            "pre-create inventory contains an exact existing draft/public record; "
            "durable recovery evidence does not authorize rebinding"
        )


def _complete_exact_record(
    evidence_path: pathlib.Path,
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    manifest: Mapping[str, Any],
    execution_head: str,
    remote_consumption: Mapping[str, Any],
    record_id: int,
    doi: str,
    client: zenodo.ZenodoClient,
    verified: Mapping[tuple[str, str], bytes],
    secrets_by_name: Mapping[str, str],
    *,
    already_public: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = manifest["metadata"]
    entries = _shared_entries(manifest["files"])
    if already_public is None:
        preparation = client.prepare_draft(
            "publication",
            record_id,
            metadata,
            entries,
            verified,
            doi,
        )
        if preparation == "published":
            published = client.wait_for_gated_record(
                record_id,
                metadata,
                entries,
                doi,
                published=True,
            )
        elif preparation == "draft":
            prepared = _phase_evidence(
                manifest_path,
                root,
                manifest,
                execution_head,
                remote_consumption,
                "prepared",
                record_id=record_id,
                doi=doi,
            )
            _atomic_recovery_evidence(evidence_path, prepared, secrets_by_name)
            publish_requested = _phase_evidence(
                manifest_path,
                root,
                manifest,
                execution_head,
                remote_consumption,
                "publish_requested",
                record_id=record_id,
                doi=doi,
            )
            # The intent is durable before the request. On a crash, the rerun
            # reconciles this exact record and never creates a replacement.
            _atomic_recovery_evidence(
                evidence_path,
                publish_requested,
                secrets_by_name,
            )
            published = client.publish_and_poll(
                record_id,
                metadata,
                entries,
                doi,
                False,
            )
        else:
            _fail("Zenodo draft preparation returned an unsupported state")
    else:
        published = already_public
    final = _phase_evidence(
        manifest_path,
        root,
        manifest,
        execution_head,
        remote_consumption,
        "public_verified",
        record_id=record_id,
        doi=doi,
        published=published,
    )
    _atomic_recovery_evidence(evidence_path, final, secrets_by_name)
    return final


def _resume_publication(
    evidence: Mapping[str, Any],
    evidence_path: pathlib.Path,
    manifest_path: pathlib.Path,
    root: pathlib.Path,
    manifest: Mapping[str, Any],
    execution_head: str,
    verified: Mapping[tuple[str, str], bytes],
    client: zenodo.ZenodoClient,
    secrets_by_name: Mapping[str, str],
) -> dict[str, Any]:
    phase = evidence["phase"]
    remote_consumption = evidence["remote_consumption"]
    _verify_remote_consumption_lock(
        remote_consumption,
        manifest,
        execution_head,
        secrets_by_name[GITHUB_TOKEN_ENVIRONMENT_VARIABLE],
    )
    metadata = manifest["metadata"]
    entries = _shared_entries(manifest["files"])

    if phase == "authorization_consumed":
        _gate_precreate_inventory(
            client,
            secrets_by_name[zenodo.TOKEN_ENVIRONMENT_VARIABLE],
            metadata,
            entries,
        )
        create_requested = _phase_evidence(
            manifest_path,
            root,
            manifest,
            execution_head,
            remote_consumption,
            "create_requested",
        )
        _atomic_recovery_evidence(
            evidence_path,
            create_requested,
            secrets_by_name,
        )
        draft = client.create_paper(metadata)
        record_id = zenodo._record_id(draft, "generic publication deposition")
        doi = zenodo._doi_from_deposition(draft, "generic publication deposition")
        record_created = _phase_evidence(
            manifest_path,
            root,
            manifest,
            execution_head,
            remote_consumption,
            "record_created",
            record_id=record_id,
            doi=doi,
        )
        _atomic_recovery_evidence(
            evidence_path,
            record_created,
            secrets_by_name,
        )
        return _complete_exact_record(
            evidence_path,
            manifest_path,
            root,
            manifest,
            execution_head,
            remote_consumption,
            record_id,
            doi,
            client,
            verified,
            secrets_by_name,
        )

    if phase == "create_requested":
        record_id, doi, already_public = _recover_create_requested_record(
            client,
            secrets_by_name[zenodo.TOKEN_ENVIRONMENT_VARIABLE],
            metadata,
            entries,
        )
        record_created = _phase_evidence(
            manifest_path,
            root,
            manifest,
            execution_head,
            remote_consumption,
            "record_created",
            record_id=record_id,
            doi=doi,
        )
        _atomic_recovery_evidence(
            evidence_path,
            record_created,
            secrets_by_name,
        )
        return _complete_exact_record(
            evidence_path,
            manifest_path,
            root,
            manifest,
            execution_head,
            remote_consumption,
            record_id,
            doi,
            client,
            verified,
            secrets_by_name,
            already_public=already_public,
        )

    record_id = evidence["record_id"]
    doi = evidence["doi"]
    if phase == "public_verified":
        public = client.wait_for_gated_record(
            record_id,
            metadata,
            entries,
            doi,
            published=True,
        )
        expected_final = _phase_evidence(
            manifest_path,
            root,
            manifest,
            execution_head,
            remote_consumption,
            "public_verified",
            record_id=record_id,
            doi=doi,
            published=public,
        )
        if evidence != expected_final:
            _fail("public_verified evidence differs from the gated public record")
        return dict(evidence)
    state, current = client.get_deposition_or_record(record_id)
    if state == "published":
        public = client.wait_for_gated_record(
            record_id,
            metadata,
            entries,
            doi,
            published=True,
            initial=current,
        )
        return _complete_exact_record(
            evidence_path,
            manifest_path,
            root,
            manifest,
            execution_head,
            remote_consumption,
            record_id,
            doi,
            client,
            verified,
            secrets_by_name,
            already_public=public,
        )
    return _complete_exact_record(
        evidence_path,
        manifest_path,
        root,
        manifest,
        execution_head,
        remote_consumption,
        record_id,
        doi,
        client,
        verified,
        secrets_by_name,
    )


def publish(manifest_path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    manifest_path = _manifest_path(root, manifest_path)
    manifest = load_manifest(manifest_path, root)
    if (
        manifest["schema"] != SCHEMA_V2
        or manifest["machine_proof"] is None
        or manifest.get("owner_authorization") is None
    ):
        _fail(
            "NO_MACHINE_PROOF_NO_ZENODO_UPLOAD: legacy v1 manifests are read-only "
            "and may not start a new production mutation"
        )
    if (
        manifest["repository"] != PRODUCTION_REPOSITORY
        or os.environ.get("GITHUB_REPOSITORY") != PRODUCTION_REPOSITORY
    ):
        _fail("production publisher repository identity is missing or mismatched")
    secrets_by_name = _validated_network_secrets()
    zenodo_token = secrets_by_name[zenodo.TOKEN_ENVIRONMENT_VARIABLE]
    github_token = secrets_by_name[GITHUB_TOKEN_ENVIRONMENT_VARIABLE]
    base_url = zenodo.validate_base_url(
        os.environ.get("ZENODO_API_BASE", zenodo.DEFAULT_BASE_URL)
    )
    evidence_path = manifest["evidence_path"]
    if not evidence_path.exists():
        _reject_owner_authorization_replay(
            root,
            manifest["owner_authorization"],
            secrets_by_name,
        )
    execution_head = _validate_repository_source_head(root, manifest_path, manifest)
    _validate_origin_repository(root, manifest["repository"])
    verified = verify_files(manifest, root, zenodo_token)
    _reject_tokens_in_publication_bytes(
        manifest_path,
        root,
        manifest,
        verified,
        secrets_by_name,
    )
    if evidence_path.exists():
        evidence_value, _raw = _load_evidence_without_secrets(
            evidence_path,
            secrets_by_name,
        )
        evidence = _validate_recovery_evidence(
            evidence_value,
            manifest_path,
            root,
            manifest,
            execution_head,
        )
        _reject_owner_authorization_replay(
            root,
            manifest["owner_authorization"],
            secrets_by_name,
            current_evidence_path=evidence_path,
        )
        client = zenodo.ZenodoClient(zenodo_token, base_url)
        return _resume_publication(
            evidence,
            evidence_path,
            manifest_path,
            root,
            manifest,
            execution_head,
            verified,
            client,
            secrets_by_name,
        )

    remote_consumption = _acquire_remote_consumption_lock(
        root,
        manifest,
        execution_head,
        github_token,
    )
    initial_phase = (
        "create_requested"
        if remote_consumption["recovery_mode"] == "EXISTING_EXACT_REF_NO_CREATE"
        else "authorization_consumed"
    )
    consumption = _phase_evidence(
        manifest_path,
        root,
        manifest,
        execution_head,
        remote_consumption,
        initial_phase,
    )
    _create_consumption_receipt(evidence_path, consumption, secrets_by_name)
    client = zenodo.ZenodoClient(zenodo_token, base_url)
    return _resume_publication(
        consumption,
        evidence_path,
        manifest_path,
        root,
        manifest,
        execution_head,
        verified,
        client,
        secrets_by_name,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish a Git-blob-bound, machine-proved repository manifest to Zenodo"
    )
    parser.add_argument(
        "--manifest", required=True, help="repository-relative publication manifest"
    )
    args = parser.parse_args(argv)
    root = pathlib.Path.cwd().resolve()
    try:
        manifest_path = _safe_relative(root, args.manifest, "--manifest", must_exist=True)
        evidence = publish(manifest_path, root)
        print("ZENODO_PUBLICATION_STATE=published")
        print(f"ZENODO_RECORD_ID={evidence['record_id']}")
        print(f"ZENODO_DOI={evidence['doi']}")
        return 0
    except zenodo.ZenodoError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
