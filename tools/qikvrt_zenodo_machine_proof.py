#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed v2 machine-proof gate for every future Zenodo publication.

The gate proves artifact identity and completeness of claim disposition.  It does
not relabel natural-language interpretation as a mathematical theorem.  Each
claim must be classified, scoped and connected to an exact proof, evidence,
source or explicit OPEN disposition before a production upload is admissible.

The v1 policy and its bundle/return schemas are historical, byte-frozen
contracts.  They can be verified for archival purposes but never authorize a
new production mutation.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NoReturn

POLICY_SCHEMA = "qikvrt_zenodo_machine_proof_policy_v2"
POLICY_ID = "qikvrt-zenodo-machine-proof-before-publication-v2"
POLICY_PATH = "policy/zenodo-machine-proof-policy-v2.json"
POLICY_VERSION = "2.0.0"
POLICY_SHA256 = "933d6322a1e294848c6385d1384ab0ec3862c8675ebe35ec2fc4cad3e0baec47"
POLICY_GIT_BLOB_SHA1 = "e9578d30d22f845e7df684128dcd9332641c00be"
BUNDLE_SCHEMA = "qikvrt_zenodo_machine_proof_bundle_v2"
BUNDLE_SCHEMA_PATH = "policy/qikvrt-zenodo-machine-proof-bundle-v2.schema.json"
RETURN_SCHEMA = "qikvrt_prepublication_return_receipt_v2"
RETURN_SCHEMA_PATH = "policy/qikvrt-prepublication-return-receipt-v2.schema.json"
CANONICAL_KERNEL_RECEIPT_SCHEMA = (
    "qikvrt_canonical_temporal_memory_kernel_receipt_v2"
)
CANONICAL_KERNEL_EVIDENCE_SCHEMA = (
    "qikvrt_canonical_temporal_memory_kernel_evidence_v1"
)
CANONICAL_RECEIPT_STAGE = "H2_SUCCESSOR_MATERIALIZATION"
CANONICAL_VERIFICATION_STAGE = "H1_TARGET_EXACT_HEAD"
CANONICAL_BOOTSTRAP_ROLE = "TRANSITION_SOURCE_ONLY_NOT_ACTIVE_GATE"
CANONICAL_KERNEL_ARTIFACT_NAME = (
    "qikvrt-canonical-temporal-memory-kernel-evidence"
)
CANONICAL_KERNEL_ARTIFACT_FILE_NAME = CANONICAL_KERNEL_ARTIFACT_NAME + ".json"
CANONICAL_KERNEL_PUBLICATION_ID = (
    "qikvrt-canonical-temporal-memory-effect-ack-v1"
)
CANONICAL_KERNEL_RECEIPT_PATH = (
    "docs/publications/2026-07-30-canonical-temporal-memory-effect-ack/"
    "KERNEL_RECEIPT.json"
)
CANONICAL_KERNEL_H0_MATRIX_PATH = (
    "docs/publications/2026-07-30-canonical-temporal-memory-effect-ack/"
    "CLAIM_MATRIX_H0_PENDING.json"
)
CANONICAL_KERNEL_TRANSITION_CLAIM_IDS = (
    "CTM-001",
    "CTM-002",
    "CTM-003",
    "CTM-004",
)
CANONICAL_KERNEL_MARKERS = frozenset(
    {
        "bootstrap_h0",
        "materialization_boundary",
        "receipt_stage",
        "verification_stage",
    }
)

LEGACY_POLICY_SCHEMA = "qikvrt_zenodo_machine_proof_policy_v1"
LEGACY_POLICY_ID = "qikvrt-zenodo-machine-proof-before-publication-v1"
LEGACY_POLICY_PATH = "policy/zenodo-machine-proof-policy-v1.json"
LEGACY_POLICY_VERSION = "1.0.0"
LEGACY_POLICY_SHA256 = (
    "039fe8617a39aaf2b20e99fc30d344f5d879ec26aedbd263647f3308dc19dc60"
)
LEGACY_POLICY_GIT_BLOB_SHA1 = "d931a50d42d6e1302afffbcfcd434861e590ab46"
LEGACY_BUNDLE_SCHEMA = "qikvrt_zenodo_machine_proof_bundle_v1"
LEGACY_BUNDLE_SCHEMA_PATH = (
    "policy/qikvrt-zenodo-machine-proof-bundle-v1.schema.json"
)
LEGACY_BUNDLE_SCHEMA_SHA256 = (
    "b027b4b9071ae4c8d7b31d22ea94ad4ef647a6be9155152b5468f09bf7010504"
)
LEGACY_BUNDLE_SCHEMA_GIT_BLOB_SHA1 = (
    "b79b2b8148c75374d660b4c7b43927bfca80995a"
)
LEGACY_RETURN_SCHEMA = "qikvrt_prepublication_return_receipt_v1"
LEGACY_RETURN_SCHEMA_PATH = (
    "policy/qikvrt-prepublication-return-receipt-v1.schema.json"
)
LEGACY_RETURN_SCHEMA_SHA256 = (
    "3eefc4213d44c0fee8619e05527649595c3cbe030a7742845a0980ab1e51224a"
)
LEGACY_RETURN_SCHEMA_GIT_BLOB_SHA1 = (
    "cca4c690c25df82955e9060abef1a98c4f0c4a43"
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SHA256_ARCHIVE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
PUBLICATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
RFC3339 = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]"
    r"(?:\.[0-9]+)?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
)
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024

LICENSE_KEYS = {
    "classification",
    "copyright",
    "license",
    "license_text_ref",
    "rights_holder",
}
LICENSE_CONSTANTS = {
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}

ALLOWED_CLASSIFICATIONS = frozenset(
    {
        "FORMAL_PROVED",
        "EMPIRICALLY_EVIDENCED",
        "SOURCE_BOUND",
        "NORMATIVE",
        "INTERPRETATIVE",
        "OPEN",
    }
)
EXPECTED_DISPOSITION = {
    "FORMAL_PROVED": ("PROVED", "ESTABLISHED_WITHIN_SCOPE"),
    "EMPIRICALLY_EVIDENCED": ("EVIDENCED", "EMPIRICALLY_SUPPORTED"),
    "SOURCE_BOUND": ("BOUND", "SOURCE_ATTRIBUTED"),
    "NORMATIVE": ("DECLARED", "NORMATIVE_DECLARATION"),
    "INTERPRETATIVE": ("DECLARED", "INTERPRETATIVE_DECLARATION"),
    "OPEN": ("OPEN", "EXPLICITLY_OPEN"),
}
MATRIX_STATUS_ALIASES = {
    "FORMAL_PROVED": {
        "PROVED": "PROVED",
        "KERNEL_VERIFIED": "PROVED",
    },
    "EMPIRICALLY_EVIDENCED": {"EVIDENCED": "EVIDENCED"},
    "SOURCE_BOUND": {"BOUND": "BOUND"},
    "NORMATIVE": {"DECLARED": "DECLARED"},
    "INTERPRETATIVE": {"DECLARED": "DECLARED"},
    "OPEN": {"OPEN": "OPEN"},
}
ALLOWED_ARTIFACT_KINDS = frozenset(
    {
        "CLAIM_MATRIX",
        "KERNEL_RECEIPT",
        "EVIDENCE",
        "SOURCE",
        "BOUNDARY_TEST",
        "CHANGE_NOTICE",
        "RETURN_RECEIPT",
        "OTHER",
    }
)


class ProofGateError(RuntimeError):
    """Safe, fail-closed proof validation failure."""


def fail(message: str) -> NoReturn:
    raise ProofGateError(message)


def exact_keys(value: Mapping[str, Any], expected: set[str], where: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unknown=" + ",".join(sorted(unknown)))
        fail(f"invalid {where} keys ({'; '.join(details)})")


def safe_relative(
    root: pathlib.Path, raw: Any, where: str, *, must_exist: bool = True
) -> pathlib.Path:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        fail(f"{where} must be a non-empty repository-relative path")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        fail(f"unsafe repository-relative path in {where}: {raw}")
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            fail(f"{where} contains a symbolic link: {raw}")
    resolved_root = root.resolve()
    resolved = root.joinpath(*relative.parts).resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        fail(f"{where} escapes the repository root")
    if must_exist and not resolved.is_file():
        fail(f"{where} is missing: {raw}")
    return resolved


def read_regular(path: pathlib.Path, limit: int = MAX_FILE_BYTES) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        fail(f"cannot open regular file {path.name}: {exc.strerror}")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            fail(f"not a regular file: {path}")
        if before.st_size > limit:
            fail(f"file exceeds size bound: {path}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                fail(f"file exceeds size bound: {path}")
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if identity_before != identity_after or total != before.st_size:
            fail(f"file changed while being read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def load_json(path: pathlib.Path, where: str) -> tuple[dict[str, Any], bytes]:
    raw = read_regular(path, MAX_JSON_BYTES)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid JSON in {where}: {exc}")
    if not isinstance(value, dict):
        fail(f"{where} must contain a JSON object")
    return value, raw


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def identity(path: pathlib.Path) -> dict[str, Any]:
    data = read_regular(path)
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": git_blob_sha1(data),
    }


def require_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"{where} must be a non-empty string")
    return value


def require_digest(value: Any, pattern: re.Pattern[str], where: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        fail(f"{where} has an invalid digest")
    return value


def require_publication_id(value: Any, where: str) -> str:
    publication_id = require_text(value, where)
    if PUBLICATION_ID.fullmatch(publication_id) is None:
        fail(
            f"{where} must match the v2 publication_id schema "
            "[A-Za-z0-9][A-Za-z0-9._-]{0,127}"
        )
    return publication_id


def validate_rfc3339(value: Any, where: str) -> str:
    raw = require_text(value, where)
    if RFC3339.fullmatch(raw) is None:
        fail(f"{where} must be an RFC3339 date-time with UTC or numeric offset")
    try:
        parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        fail(f"{where} must be a valid RFC3339 date-time")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        fail(f"{where} must include a UTC or numeric offset")
    return raw


def validate_license(
    value: Any,
    where: str,
    *,
    classification: str,
) -> None:
    if not isinstance(value, dict):
        fail(f"{where} must be an object")
    exact_keys(value, LICENSE_KEYS, where)
    require_text(value["copyright"], where + ".copyright")
    expected_constants = {
        "classification": classification,
        **LICENSE_CONSTANTS,
    }
    for key, expected in expected_constants.items():
        if value[key] != expected:
            fail(f"{where}.{key} differs from the exact v2 license contract")


def validate_bound_identity(
    root: pathlib.Path,
    value: Mapping[str, Any],
    where: str,
    *,
    include_bytes: bool,
) -> tuple[str, dict[str, Any]]:
    expected = {"path", "sha256", "git_blob_sha1"}
    if include_bytes:
        expected |= {"bytes", "name", "role"}
    else:
        expected |= {"kind"}
    exact_keys(value, expected, where)
    raw_path = require_text(value["path"], where + ".path")
    path = safe_relative(root, raw_path, where + ".path")
    observed = identity(path)
    if observed["sha256"] != require_digest(value["sha256"], HEX64, where + ".sha256"):
        fail(f"SHA-256 mismatch for {raw_path}")
    if observed["git_blob_sha1"] != require_digest(
        value["git_blob_sha1"], HEX40, where + ".git_blob_sha1"
    ):
        fail(f"Git blob mismatch for {raw_path}")
    if include_bytes:
        if isinstance(value["bytes"], bool) or not isinstance(value["bytes"], int):
            fail(f"{where}.bytes must be an integer")
        if value["bytes"] != observed["bytes"]:
            fail(f"byte-size mismatch for {raw_path}")
        require_text(value["name"], where + ".name")
        if value["role"] not in {"PRIMARY", "SUPPLEMENT", "PROOF_BUNDLE"}:
            fail(f"{where}.role is invalid")
    else:
        if value["kind"] not in ALLOWED_ARTIFACT_KINDS:
            fail(f"{where}.kind is invalid")
    return raw_path, observed


def reference_base(reference: str) -> str:
    return reference.split("#", 1)[0]


def reference_fragment(reference: str, where: str) -> str:
    _base, separator, fragment = reference.partition("#")
    if not separator or not fragment:
        fail(f"{where} must contain an exact identifier fragment")
    return fragment


def require_unique_text_list(value: Any, where: str) -> list[str]:
    if not isinstance(value, list):
        fail(f"{where} must be a string list")
    result: list[str] = []
    for index, item in enumerate(value):
        text = require_text(item, f"{where}[{index}]")
        result.append(text)
    if len(result) != len(set(result)):
        fail(f"{where} must not contain duplicates")
    return result


def validate_schema_contract_file(
    root: pathlib.Path,
    binding: Any,
    where: str,
    *,
    expected_path: str,
    expected_schema: str,
) -> dict[str, str]:
    if not isinstance(binding, dict):
        fail(f"{where} must be an object")
    exact_keys(binding, {"path", "sha256", "git_blob_sha1"}, where)
    if binding["path"] != expected_path:
        fail(f"{where}.path differs from the active schema contract")
    expected_sha256 = require_digest(
        binding["sha256"],
        HEX64,
        where + ".sha256",
    )
    expected_blob = require_digest(
        binding["git_blob_sha1"],
        HEX40,
        where + ".git_blob_sha1",
    )
    schema_path = safe_relative(root, expected_path, where + ".path")
    schema_value, schema_raw = load_json(schema_path, where)
    observed_sha256 = hashlib.sha256(schema_raw).hexdigest()
    observed_blob = git_blob_sha1(schema_raw)
    if observed_sha256 != expected_sha256 or observed_blob != expected_blob:
        fail(f"{where} exact byte identity differs")
    properties = schema_value.get("properties")
    schema_property = (
        properties.get("schema") if isinstance(properties, dict) else None
    )
    if (
        schema_value.get("$schema")
        != "https://json-schema.org/draft/2020-12/schema"
        or not isinstance(schema_property, dict)
        or schema_property.get("const") != expected_schema
    ):
        fail(f"{where} semantic schema identity differs")
    return {
        "path": expected_path,
        "sha256": observed_sha256,
        "git_blob_sha1": observed_blob,
    }


def validate_legacy_contract_freeze(root: pathlib.Path) -> dict[str, Any]:
    """Verify the historical v1 bytes without authorizing a new mutation."""
    root = root.resolve()
    policy_path = safe_relative(
        root,
        LEGACY_POLICY_PATH,
        "legacy v1 Zenodo proof policy",
    )
    policy_value, policy_raw = load_json(
        policy_path,
        "legacy v1 Zenodo proof policy",
    )
    observed_policy_sha256 = hashlib.sha256(policy_raw).hexdigest()
    observed_policy_blob = git_blob_sha1(policy_raw)
    if (
        observed_policy_sha256 != LEGACY_POLICY_SHA256
        or observed_policy_blob != LEGACY_POLICY_GIT_BLOB_SHA1
    ):
        fail("legacy v1 Zenodo proof policy is not byte-frozen")
    legacy_rule = policy_value.get("legacy_rule")
    prepublication_return = policy_value.get("prepublication_return")
    if (
        policy_value.get("schema") != LEGACY_POLICY_SCHEMA
        or policy_value.get("version") != LEGACY_POLICY_VERSION
        or not isinstance(legacy_rule, dict)
        or legacy_rule.get("legacy_manifest_may_start_new_production_mutation")
        is not False
        or not isinstance(prepublication_return, dict)
        or prepublication_return.get("required_receipt_schema")
        != LEGACY_RETURN_SCHEMA
    ):
        fail("legacy v1 Zenodo proof policy semantic freeze differs")

    schema_contracts = {
        "machine_proof_bundle": validate_schema_contract_file(
            root,
            {
                "path": LEGACY_BUNDLE_SCHEMA_PATH,
                "sha256": LEGACY_BUNDLE_SCHEMA_SHA256,
                "git_blob_sha1": LEGACY_BUNDLE_SCHEMA_GIT_BLOB_SHA1,
            },
            "legacy v1 machine-proof bundle schema",
            expected_path=LEGACY_BUNDLE_SCHEMA_PATH,
            expected_schema=LEGACY_BUNDLE_SCHEMA,
        ),
        "prepublication_return_receipt": validate_schema_contract_file(
            root,
            {
                "path": LEGACY_RETURN_SCHEMA_PATH,
                "sha256": LEGACY_RETURN_SCHEMA_SHA256,
                "git_blob_sha1": LEGACY_RETURN_SCHEMA_GIT_BLOB_SHA1,
            },
            "legacy v1 prepublication return receipt schema",
            expected_path=LEGACY_RETURN_SCHEMA_PATH,
            expected_schema=LEGACY_RETURN_SCHEMA,
        ),
    }
    return {
        "policy": {
            "id": LEGACY_POLICY_ID,
            "path": LEGACY_POLICY_PATH,
            "version": LEGACY_POLICY_VERSION,
            "sha256": observed_policy_sha256,
            "git_blob_sha1": observed_policy_blob,
        },
        "schema_contracts": schema_contracts,
        "historical_read_only": True,
        "production_mutation_authorized": False,
    }


def validate_active_schema_contracts(
    root: pathlib.Path,
    policy_value: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    contracts = policy_value.get("schema_contracts")
    if not isinstance(contracts, dict):
        fail("active Zenodo proof policy lacks schema_contracts")
    exact_keys(
        contracts,
        {"machine_proof_bundle", "prepublication_return_receipt"},
        "active Zenodo proof policy schema_contracts",
    )
    return {
        "machine_proof_bundle": validate_schema_contract_file(
            root,
            contracts["machine_proof_bundle"],
            "active v2 machine-proof bundle schema",
            expected_path=BUNDLE_SCHEMA_PATH,
            expected_schema=BUNDLE_SCHEMA,
        ),
        "prepublication_return_receipt": validate_schema_contract_file(
            root,
            contracts["prepublication_return_receipt"],
            "active v2 prepublication return receipt schema",
            expected_path=RETURN_SCHEMA_PATH,
            expected_schema=RETURN_SCHEMA,
        ),
    }


def validate_active_policy(
    root: pathlib.Path,
    binding: Any,
) -> dict[str, Any]:
    if not isinstance(binding, dict):
        fail("policy must be an object")
    if (
        binding.get("id") == LEGACY_POLICY_ID
        or binding.get("path") == LEGACY_POLICY_PATH
        or binding.get("version") == LEGACY_POLICY_VERSION
    ):
        fail(
            "legacy v1 proof policy is historical/read-only and cannot "
            "authorize a new production mutation"
        )
    expected_binding = {
        "id": POLICY_ID,
        "path": POLICY_PATH,
        "version": POLICY_VERSION,
        "sha256": POLICY_SHA256,
        "git_blob_sha1": POLICY_GIT_BLOB_SHA1,
    }
    exact_keys(binding, set(expected_binding), "policy")
    if binding != expected_binding:
        fail("proof bundle is not bound to the exact active Zenodo proof policy")

    policy_path = safe_relative(root, POLICY_PATH, "policy.path")
    policy_value, policy_raw = load_json(policy_path, "active Zenodo proof policy")
    observed_sha256 = hashlib.sha256(policy_raw).hexdigest()
    observed_blob = git_blob_sha1(policy_raw)
    if (
        observed_sha256 != POLICY_SHA256
        or observed_blob != POLICY_GIT_BLOB_SHA1
    ):
        fail("active Zenodo proof policy exact byte identity/semantics differ")
    activation = policy_value.get("activation")
    prepublication_return = policy_value.get("prepublication_return")
    legacy_rule = policy_value.get("legacy_rule")
    supersedes = policy_value.get("supersedes")
    hard_gates = policy_value.get("hard_gates")
    if (
        policy_value.get("schema") != POLICY_SCHEMA
        or policy_value.get("policy_id") != POLICY_ID
        or policy_value.get("version") != POLICY_VERSION
        or not isinstance(activation, dict)
        or activation.get("principal")
        != {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}
        or policy_value.get("allowed_claim_classifications")
        != list(EXPECTED_DISPOSITION)
        or policy_value.get("claim_status_by_classification")
        != {
            classification: [EXPECTED_DISPOSITION[classification][0]]
            for classification in EXPECTED_DISPOSITION
        }
        or not isinstance(prepublication_return, dict)
        or prepublication_return.get("required_receipt_schema") != RETURN_SCHEMA
        or supersedes
        != {"policy_id": LEGACY_POLICY_ID, "version": LEGACY_POLICY_VERSION}
        or not isinstance(legacy_rule, dict)
        or legacy_rule.get("legacy_v1_bundle_and_return_schemas_are_byte_frozen")
        is not True
        or legacy_rule.get("legacy_manifest_may_start_new_production_mutation")
        is not False
        or not isinstance(hard_gates, list)
        or "NO_V2_PROOF_CONTRACT_NO_NEW_PRODUCTION_MUTATION" not in hard_gates
        or "NO_TOKEN_IN_METADATA_AUTHORIZATION_PROOF_OR_UPLOAD_BYTES"
        not in hard_gates
    ):
        fail("active Zenodo proof policy semantic contract differs")
    schema_contracts = validate_active_schema_contracts(root, policy_value)
    validate_legacy_contract_freeze(root)
    return {
        "id": POLICY_ID,
        "path": POLICY_PATH,
        "version": POLICY_VERSION,
        "sha256": observed_sha256,
        "git_blob_sha1": observed_blob,
        "schema_contracts": schema_contracts,
    }


def validate_kernel_matrix_identity(
    root: pathlib.Path,
    value: Any,
    where: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{where} must be an object")
    exact_keys(value, {"path", "bytes", "sha256", "git_blob_sha1"}, where)
    raw_path = require_text(value["path"], where + ".path")
    safe_relative(root, raw_path, where + ".path", must_exist=False)
    if (
        isinstance(value["bytes"], bool)
        or not isinstance(value["bytes"], int)
        or value["bytes"] < 0
    ):
        fail(f"{where}.bytes must be a non-negative integer")
    require_digest(value["sha256"], HEX64, where + ".sha256")
    require_digest(value["git_blob_sha1"], HEX40, where + ".git_blob_sha1")
    return dict(value)


def validate_persisted_kernel_evidence(
    root: pathlib.Path,
    artifact: Any,
    where: str,
) -> tuple[dict[str, Any], str]:
    if not isinstance(artifact, dict):
        fail(f"{where} must be an object")
    exact_keys(
        artifact,
        {
            "archive_digest",
            "archive_size_bytes",
            "created_at",
            "expires_at",
            "file",
            "id",
            "name",
        },
        where,
    )
    artifact_id = artifact["id"]
    if (
        isinstance(artifact_id, bool)
        or not isinstance(artifact_id, int)
        or artifact_id <= 0
    ):
        fail(f"{where}.id must be a positive integer")
    if artifact["name"] != CANONICAL_KERNEL_ARTIFACT_NAME:
        fail(f"{where}.name differs from the canonical artifact name")
    if (
        not isinstance(artifact["archive_digest"], str)
        or SHA256_ARCHIVE_DIGEST.fullmatch(artifact["archive_digest"]) is None
    ):
        fail(f"{where}.archive_digest has an invalid digest")
    archive_size = artifact["archive_size_bytes"]
    if (
        isinstance(archive_size, bool)
        or not isinstance(archive_size, int)
        or archive_size <= 0
    ):
        fail(f"{where}.archive_size_bytes must be a positive integer")
    created_at = validate_rfc3339(
        artifact["created_at"],
        where + ".created_at",
    )
    expires_at = validate_rfc3339(
        artifact["expires_at"],
        where + ".expires_at",
    )
    created_timestamp = datetime.datetime.fromisoformat(
        created_at.replace("Z", "+00:00")
    )
    expires_timestamp = datetime.datetime.fromisoformat(
        expires_at.replace("Z", "+00:00")
    )
    if expires_timestamp <= created_timestamp:
        fail(f"{where}.expires_at must be later than created_at")

    file_value = artifact["file"]
    if not isinstance(file_value, dict):
        fail(f"{where}.file must be an object")
    exact_keys(
        file_value,
        {"bytes", "git_blob_sha1", "name", "persisted_path", "sha256"},
        where + ".file",
    )
    if (
        isinstance(file_value["bytes"], bool)
        or not isinstance(file_value["bytes"], int)
        or file_value["bytes"] < 0
    ):
        fail(f"{where}.file.bytes must be a non-negative integer")
    if file_value["name"] != CANONICAL_KERNEL_ARTIFACT_FILE_NAME:
        fail(f"{where}.file.name differs from the canonical evidence name")
    raw_path = require_text(
        file_value["persisted_path"],
        where + ".file.persisted_path",
    )
    path = safe_relative(
        root,
        raw_path,
        where + ".file.persisted_path",
    )
    evidence, raw = load_json(path, where + " raw evidence")
    observed = {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
    }
    require_digest(
        file_value["sha256"],
        HEX64,
        where + ".file.sha256",
    )
    require_digest(
        file_value["git_blob_sha1"],
        HEX40,
        where + ".file.git_blob_sha1",
    )
    for key, observed_value in observed.items():
        if file_value[key] != observed_value:
            fail(f"{where}.file exact raw evidence identity differs")
    return evidence, raw_path


def validate_kernel_candidate(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{where} must be an object")
    for key in ("branch", "head", "repository", "tree"):
        if key not in value:
            fail(f"{where} is missing {key}")
    require_text(value["branch"], where + ".branch")
    require_text(value["repository"], where + ".repository")
    require_digest(value["head"], HEX40, where + ".head")
    require_digest(value["tree"], HEX40, where + ".tree")
    return dict(value)


def validate_kernel_workflow_alignment(
    summary: Any,
    evidence_workflow: Any,
    candidate: Mapping[str, Any],
    where: str,
) -> None:
    if not isinstance(summary, dict):
        fail(f"{where} must be an object")
    if not isinstance(evidence_workflow, dict):
        fail(f"{where} raw evidence workflow must be an object")
    if (
        summary.get("conclusion") != "success"
        or summary.get("exact_head_bound") is not True
    ):
        fail(f"{where} must be a successful exact-head workflow")
    summary_sha = require_digest(summary.get("sha"), HEX40, where + ".sha")
    evidence_sha = require_digest(
        evidence_workflow.get("sha"),
        HEX40,
        where + " raw evidence workflow.sha",
    )
    if summary_sha != candidate["head"] or evidence_sha != candidate["head"]:
        fail(f"{where}.sha differs from its verified candidate head")
    for key in ("event", "run_id", "run_attempt"):
        if key not in summary or key not in evidence_workflow:
            fail(f"{where} lacks {key} alignment")
        if str(summary[key]) != str(evidence_workflow[key]):
            fail(f"{where}.{key} differs from its raw evidence")
    if evidence_workflow.get("repository") != candidate["repository"]:
        fail(f"{where} raw evidence repository differs")
    if evidence_workflow.get("ref") != "refs/heads/" + candidate["branch"]:
        fail(f"{where} raw evidence ref differs")


def validate_kernel_source_alignment(
    receipt_source: Any,
    evidence_source: Any,
    where: str,
) -> None:
    if not isinstance(receipt_source, dict) or not isinstance(
        evidence_source,
        dict,
    ):
        fail(f"{where} source identities must be objects")
    for key, pattern in (
        ("sha256", HEX64),
        ("git_blob_sha1", HEX40),
    ):
        receipt_digest = require_digest(
            receipt_source.get(key),
            pattern,
            where + f" receipt source.{key}",
        )
        evidence_digest = require_digest(
            evidence_source.get(key),
            pattern,
            where + f" raw evidence source.{key}",
        )
        if receipt_digest != evidence_digest:
            fail(f"{where} source {key} differs")
    receipt_bytes = receipt_source.get("bytes")
    evidence_bytes = evidence_source.get("bytes")
    if (
        isinstance(receipt_bytes, bool)
        or not isinstance(receipt_bytes, int)
        or receipt_bytes < 0
        or evidence_bytes != receipt_bytes
    ):
        fail(f"{where} source byte identity differs")


def load_persisted_kernel_matrix(
    root: pathlib.Path,
    value: Any,
    where: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    matrix_identity = validate_kernel_matrix_identity(root, value, where)
    matrix_path = safe_relative(
        root,
        matrix_identity["path"],
        where + ".path",
    )
    matrix, raw = load_json(matrix_path, where)
    observed_identity = {
        "path": matrix_identity["path"],
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
    }
    if matrix_identity != observed_identity:
        fail(f"{where} exact persisted H0 matrix identity differs")
    return matrix_identity, matrix


def validate_local_kernel_identity(
    root: pathlib.Path,
    recorded: Mapping[str, Any],
    where: str,
    *,
    local_path: str | None = None,
) -> None:
    raw_path = recorded["path"] if local_path is None else local_path
    path = safe_relative(root, raw_path, where + ".path")
    if identity(path) != {
        key: recorded[key]
        for key in ("bytes", "sha256", "git_blob_sha1")
    }:
        fail(f"{where} differs from local repository bytes")


def validate_kernel_allowed_changes(
    transition: Mapping[str, Any],
    publication_id: str,
) -> tuple[str, ...]:
    exact_keys(
        transition,
        {
            "allowed_changes",
            "proof_refs_and_statements_unchanged",
            "source_claim_matrix",
            "target_claim_matrix",
            "target_exact_head_confirmation_required",
        },
        "canonical kernel receipt v2 claim_transition",
    )
    if transition["proof_refs_and_statements_unchanged"] is not True:
        fail(
            "canonical kernel receipt v2 must preserve proof refs and "
            "statements"
        )
    allowed_changes = transition["allowed_changes"]
    if not isinstance(allowed_changes, dict):
        fail("canonical kernel receipt v2 allowed_changes must be an object")
    exact_keys(
        allowed_changes,
        {
            "claim_ids",
            "classification",
            "matrix_proof_state",
            "status",
        },
        "canonical kernel receipt v2 allowed_changes",
    )
    claim_ids = allowed_changes["claim_ids"]
    if (
        not isinstance(claim_ids, list)
        or not claim_ids
        or not all(isinstance(claim_id, str) and claim_id for claim_id in claim_ids)
        or len(claim_ids) != len(set(claim_ids))
    ):
        fail(
            "canonical kernel receipt v2 allowed_changes.claim_ids must be "
            "non-empty and unique"
        )
    expected = {
        "claim_ids": claim_ids,
        "classification": {
            "from": "FORMAL_PENDING_KERNEL",
            "to": "FORMAL_PROVED",
        },
        "matrix_proof_state": {
            "from": "AWAITING_EXACT_HEAD_KERNEL_RECEIPT",
            "to": "KERNEL_VERIFIED",
        },
        "status": {
            "from": (
                "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_KERNEL_RECEIPT"
            ),
            "to": "KERNEL_VERIFIED",
        },
    }
    if allowed_changes != expected:
        fail("canonical kernel receipt v2 allowed_changes contract differs")
    if (
        publication_id == CANONICAL_KERNEL_PUBLICATION_ID
        and tuple(claim_ids) != CANONICAL_KERNEL_TRANSITION_CLAIM_IDS
    ):
        fail(
            "canonical kernel receipt v2 transition must be scoped to "
            "CTM-001..CTM-004"
        )
    return tuple(claim_ids)


def validate_kernel_matrix_transition(
    source: Any,
    target: Any,
    allowed_changes: Mapping[str, Any],
) -> None:
    if not isinstance(source, dict) or not isinstance(target, dict):
        fail("canonical kernel receipt v2 persisted matrices must be objects")
    expected_target = copy.deepcopy(source)
    proof_state = allowed_changes["matrix_proof_state"]
    if source.get("proof_state") != proof_state["from"]:
        fail("canonical kernel receipt v2 H0 matrix proof_state differs")
    expected_target["proof_state"] = proof_state["to"]

    source_claims = expected_target.get("claims")
    target_claims = target.get("claims")
    if not isinstance(source_claims, list) or not isinstance(target_claims, list):
        fail("canonical kernel receipt v2 matrices require claim arrays")
    source_claim_ids = [
        claim.get("claim_id") if isinstance(claim, dict) else None
        for claim in source_claims
    ]
    target_claim_ids = [
        claim.get("claim_id") if isinstance(claim, dict) else None
        for claim in target_claims
    ]
    if (
        any(not isinstance(claim_id, str) or not claim_id for claim_id in source_claim_ids)
        or len(source_claim_ids) != len(set(source_claim_ids))
        or target_claim_ids != source_claim_ids
    ):
        fail("canonical kernel receipt v2 claim matrix inventories differ")

    allowed_ids = set(allowed_changes["claim_ids"])
    if not allowed_ids.issubset(set(source_claim_ids)):
        fail("canonical kernel receipt v2 allowed claim IDs are absent from H0")
    classification = allowed_changes["classification"]
    status = allowed_changes["status"]
    for claim in source_claims:
        if claim["claim_id"] not in allowed_ids:
            continue
        if (
            claim.get("classification") != classification["from"]
            or claim.get("status") != status["from"]
        ):
            fail("canonical kernel receipt v2 H0 allowed claim state differs")
        claim["classification"] = classification["to"]
        claim["status"] = status["to"]
    if target != expected_target:
        fail(
            "canonical kernel receipt v2 matrix transition exceeds allowed "
            "changes"
        )


def validate_kernel_formal_evidence(
    root: pathlib.Path,
    evidence: Mapping[str, Any],
    *,
    receipt_plan: Mapping[str, Any],
    receipt_compiled_object: Mapping[str, Any],
    receipt_source: Mapping[str, Any],
    receipt_theorems: Sequence[str],
    receipt_axioms: Mapping[str, Any],
    expected_claim_proof_refs: Mapping[str, Sequence[str]],
    formal_claim_count: int,
    where: str,
) -> list[dict[str, Any]]:
    evidence_plan = validate_kernel_matrix_identity(
        root,
        evidence.get("plan"),
        where + ".plan",
    )
    evidence_compiled_object = validate_kernel_matrix_identity(
        root,
        evidence.get("compiled_object"),
        where + ".compiled_object",
    )
    if evidence_plan != dict(receipt_plan):
        fail(f"{where} plan differs from the receipt")
    if evidence_compiled_object != dict(receipt_compiled_object):
        fail(f"{where} compiled_object differs from the receipt")
    evidence_theorem_count = evidence.get("theorem_count")
    if (
        isinstance(evidence_theorem_count, bool)
        or not isinstance(evidence_theorem_count, int)
        or evidence_theorem_count != len(receipt_theorems)
    ):
        fail(f"{where} theorem_count differs from the theorem inventory")
    evidence_formal_claim_count = evidence.get("formal_claim_count")
    if (
        isinstance(evidence_formal_claim_count, bool)
        or not isinstance(evidence_formal_claim_count, int)
        or evidence_formal_claim_count != formal_claim_count
    ):
        fail(f"{where} formal_claim_count differs from the receipt")

    bindings = evidence.get("formal_bindings")
    if not isinstance(bindings, list) or len(bindings) != formal_claim_count:
        fail(f"{where} formal_bindings count differs")
    observed_claim_ids: list[str] = []
    observed_theorems: set[str] = set()
    normalized_bindings: list[dict[str, Any]] = []
    for index, binding in enumerate(bindings):
        binding_where = f"{where}.formal_bindings[{index}]"
        if not isinstance(binding, dict):
            fail(f"{binding_where} must be an object")
        exact_keys(
            binding,
            {
                "axioms_by_theorem",
                "claim_id",
                "compiled_object_sha256",
                "proof_refs",
                "source_sha256",
            },
            binding_where,
        )
        claim_id = require_text(binding["claim_id"], binding_where + ".claim_id")
        proof_refs = binding["proof_refs"]
        if (
            not isinstance(proof_refs, list)
            or not proof_refs
            or not all(isinstance(ref, str) and ref for ref in proof_refs)
            or len(proof_refs) != len(set(proof_refs))
            or not set(proof_refs).issubset(set(receipt_theorems))
        ):
            fail(f"{binding_where}.proof_refs differ from theorem inventory")
        expected_proof_refs = expected_claim_proof_refs.get(claim_id)
        if expected_proof_refs is None or proof_refs != list(expected_proof_refs):
            fail(f"{binding_where}.proof_refs differ from its matrix claim")
        if binding["compiled_object_sha256"] != receipt_compiled_object["sha256"]:
            fail(f"{binding_where} compiled object binding differs")
        if binding["source_sha256"] != receipt_source["sha256"]:
            fail(f"{binding_where} source binding differs")
        expected_axioms = {
            theorem: receipt_axioms[theorem] for theorem in proof_refs
        }
        if binding["axioms_by_theorem"] != expected_axioms:
            fail(f"{binding_where} axiom binding differs")
        observed_claim_ids.append(claim_id)
        observed_theorems.update(proof_refs)
        normalized_bindings.append(dict(binding))
    if (
        len(observed_claim_ids) != len(set(observed_claim_ids))
        or set(observed_claim_ids) != set(expected_claim_proof_refs)
    ):
        fail(f"{where} formal binding claim inventory differs")
    if observed_theorems != set(receipt_theorems):
        fail(f"{where} formal binding theorem inventory differs")
    return normalized_bindings


def validate_kernel_execution_evidence(
    root: pathlib.Path,
    evidence: Mapping[str, Any],
    *,
    receipt_entrypoint: Mapping[str, Any],
    receipt_toolchain: Mapping[str, Any],
    receipt_runtime: Mapping[str, Any],
    where: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    evidence_entrypoint = validate_kernel_matrix_identity(
        root,
        evidence.get("entrypoint"),
        where + ".entrypoint",
    )
    if evidence_entrypoint != dict(receipt_entrypoint):
        fail(f"{where} entrypoint differs from the receipt")

    evidence_toolchain = evidence.get("lean_toolchain")
    if not isinstance(evidence_toolchain, dict):
        fail(f"{where}.lean_toolchain must be an object")
    exact_keys(
        evidence_toolchain,
        {"bytes", "git_blob_sha1", "path", "sha256", "value"},
        where + ".lean_toolchain",
    )
    toolchain_identity = validate_kernel_matrix_identity(
        root,
        {
            key: evidence_toolchain[key]
            for key in ("bytes", "git_blob_sha1", "path", "sha256")
        },
        where + ".lean_toolchain",
    )
    if evidence_toolchain["value"] != receipt_toolchain["lean_toolchain"]:
        fail(f"{where} lean toolchain value differs from the receipt")
    if evidence_toolchain["sha256"] != receipt_toolchain["sha256"]:
        fail(f"{where} lean toolchain digest differs from the receipt")
    receipt_toolchain_path = pathlib.PurePosixPath(receipt_toolchain["path"])
    evidence_toolchain_path = pathlib.PurePosixPath(toolchain_identity["path"])
    if (
        len(evidence_toolchain_path.parts) > len(receipt_toolchain_path.parts)
        or receipt_toolchain_path.parts[-len(evidence_toolchain_path.parts) :]
        != evidence_toolchain_path.parts
    ):
        fail(f"{where} lean toolchain path differs from the receipt")
    local_toolchain_path = safe_relative(
        root,
        receipt_toolchain["path"],
        where + ".lean_toolchain local path",
    )
    if identity(local_toolchain_path) != {
        key: evidence_toolchain[key]
        for key in ("bytes", "sha256", "git_blob_sha1")
    }:
        fail(f"{where} lean toolchain differs from local repository bytes")

    evidence_runtime = evidence.get("runtime")
    if not isinstance(evidence_runtime, dict):
        fail(f"{where}.runtime must be an object")
    exact_keys(
        evidence_runtime,
        {
            "cache_replaces_kernel_verification",
            "dynamic_axiom_audit",
            "exact_source_kernel_check",
            "fresh_project_build_required_before_object_binding",
        },
        where + ".runtime",
    )
    if (
        evidence_runtime["cache_replaces_kernel_verification"] is not False
        or evidence_runtime[
            "fresh_project_build_required_before_object_binding"
        ]
        is not True
    ):
        fail(f"{where} runtime kernel/cache boundary differs")
    for step_name in ("dynamic_axiom_audit", "exact_source_kernel_check"):
        step = evidence_runtime[step_name]
        step_where = f"{where}.runtime.{step_name}"
        if not isinstance(step, dict):
            fail(f"{step_where} must be an object")
        exact_keys(step, {"argv", "exit_code", "output_sha256"}, step_where)
        if (
            not isinstance(step["argv"], list)
            or not step["argv"]
            or not all(isinstance(arg, str) and arg for arg in step["argv"])
        ):
            fail(f"{step_where}.argv must be a non-empty string list")
        if step["exit_code"] != 0:
            fail(f"{step_where}.exit_code must equal zero")
        require_digest(
            step["output_sha256"],
            HEX64,
            step_where + ".output_sha256",
        )
    if (
        evidence_runtime["dynamic_axiom_audit"]["output_sha256"]
        != receipt_runtime["dynamic_axiom_audit_output_sha256"]
        or evidence_runtime["exact_source_kernel_check"]["exit_code"]
        != receipt_runtime["exact_source_kernel_check_exit_code"]
        or evidence_runtime["exact_source_kernel_check"]["output_sha256"]
        != receipt_runtime["exact_source_kernel_check_output_sha256"]
    ):
        fail(f"{where} runtime differs from the receipt")
    return (
        evidence_entrypoint,
        dict(evidence_toolchain),
        dict(evidence_runtime),
    )


def validate_canonical_kernel_receipt_v2(
    root: pathlib.Path,
    receipt: Mapping[str, Any],
    publication_id: str,
    claim_matrix_identity: Mapping[str, Any],
) -> None:
    if receipt.get("schema") != CANONICAL_KERNEL_RECEIPT_SCHEMA:
        fail("canonical kernel receipt context requires the exact v2 schema")
    if receipt.get("state") != "KERNEL_VERIFIED":
        fail("canonical kernel receipt v2 state must equal KERNEL_VERIFIED")
    if receipt.get("scope_id") != publication_id:
        fail("canonical kernel receipt v2 scope differs")
    if receipt.get("receipt_stage") != CANONICAL_RECEIPT_STAGE:
        fail("canonical kernel receipt v2 H2 receipt_stage differs")
    if receipt.get("verification_stage") != CANONICAL_VERIFICATION_STAGE:
        fail("canonical kernel receipt v2 H1 verification_stage differs")

    transition = receipt.get("claim_transition")
    if not isinstance(transition, dict):
        fail("canonical kernel receipt v2 lacks claim_transition")
    formal_claim_ids = validate_kernel_allowed_changes(
        transition,
        publication_id,
    )
    if transition.get("target_exact_head_confirmation_required") is not False:
        fail("canonical kernel receipt v2 target H1 confirmation is not closed")
    source_matrix = validate_kernel_matrix_identity(
        root,
        transition.get("source_claim_matrix"),
        "canonical kernel receipt v2 source_claim_matrix",
    )
    target_matrix = validate_kernel_matrix_identity(
        root,
        transition.get("target_claim_matrix"),
        "canonical kernel receipt v2 target_claim_matrix",
    )
    if source_matrix == target_matrix:
        fail("canonical kernel receipt v2 H0 and H1 matrices must differ")
    if target_matrix != dict(claim_matrix_identity):
        fail("canonical kernel receipt v2 target matrix differs from the bundle")

    receipt_source = validate_kernel_matrix_identity(
        root,
        receipt.get("source"),
        "canonical kernel receipt v2 source",
    )
    source_path = safe_relative(
        root,
        receipt_source["path"],
        "canonical kernel receipt v2 source.path",
    )
    if {
        "path": receipt_source["path"],
        **identity(source_path),
    } != receipt_source:
        fail("canonical kernel receipt v2 source differs from repository bytes")
    receipt_axioms = receipt.get("axioms_by_theorem")
    if not isinstance(receipt_axioms, dict):
        fail("canonical kernel receipt v2 axioms_by_theorem must be an object")
    receipt_theorems = receipt.get("theorems")
    if (
        not isinstance(receipt_theorems, list)
        or not receipt_theorems
        or not all(
            isinstance(theorem, str) and theorem
            for theorem in receipt_theorems
        )
        or len(receipt_theorems) != len(set(receipt_theorems))
        or set(receipt_axioms) != set(receipt_theorems)
        or not all(
            isinstance(axioms, list)
            and len(axioms) == len(set(axioms))
            and all(isinstance(axiom, str) and axiom for axiom in axioms)
            for axioms in receipt_axioms.values()
        )
    ):
        fail("canonical kernel receipt v2 theorem/axiom inventory differs")
    receipt_theorem_count = receipt.get("theorem_count")
    if (
        isinstance(receipt_theorem_count, bool)
        or not isinstance(receipt_theorem_count, int)
        or receipt_theorem_count != len(receipt_theorems)
    ):
        fail("canonical kernel receipt v2 theorem_count differs")
    formal_claim_count = receipt.get("formal_claim_count")
    if (
        isinstance(formal_claim_count, bool)
        or not isinstance(formal_claim_count, int)
        or formal_claim_count != len(formal_claim_ids)
    ):
        fail("canonical kernel receipt v2 formal_claim_count differs")
    receipt_plan = validate_kernel_matrix_identity(
        root,
        receipt.get("plan"),
        "canonical kernel receipt v2 plan",
    )
    receipt_compiled_object = validate_kernel_matrix_identity(
        root,
        receipt.get("compiled_object"),
        "canonical kernel receipt v2 compiled_object",
    )
    validate_local_kernel_identity(
        root,
        receipt_plan,
        "canonical kernel receipt v2 plan",
    )
    receipt_entrypoint = validate_kernel_matrix_identity(
        root,
        receipt.get("entrypoint"),
        "canonical kernel receipt v2 entrypoint",
    )
    receipt_toolchain = receipt.get("toolchain")
    if not isinstance(receipt_toolchain, dict):
        fail("canonical kernel receipt v2 toolchain must be an object")
    exact_keys(
        receipt_toolchain,
        {"lean_toolchain", "locked", "path", "sha256"},
        "canonical kernel receipt v2 toolchain",
    )
    require_text(
        receipt_toolchain["lean_toolchain"],
        "canonical kernel receipt v2 toolchain.lean_toolchain",
    )
    if receipt_toolchain["locked"] is not True:
        fail("canonical kernel receipt v2 toolchain must be locked")
    toolchain_path = require_text(
        receipt_toolchain["path"],
        "canonical kernel receipt v2 toolchain.path",
    )
    require_digest(
        receipt_toolchain["sha256"],
        HEX64,
        "canonical kernel receipt v2 toolchain.sha256",
    )
    project_prefix = pathlib.PurePosixPath(toolchain_path).parent
    raw_entrypoint_path = pathlib.PurePosixPath(receipt_entrypoint["path"])
    if raw_entrypoint_path.parts[: len(project_prefix.parts)] == (
        project_prefix.parts
    ):
        local_entrypoint_path = raw_entrypoint_path.as_posix()
    else:
        local_entrypoint_path = (
            project_prefix / raw_entrypoint_path
        ).as_posix()
    validate_local_kernel_identity(
        root,
        receipt_entrypoint,
        "canonical kernel receipt v2 entrypoint",
        local_path=local_entrypoint_path,
    )
    receipt_runtime = receipt.get("runtime")
    if not isinstance(receipt_runtime, dict):
        fail("canonical kernel receipt v2 runtime must be an object")
    exact_keys(
        receipt_runtime,
        {
            "dynamic_axiom_audit_output_sha256",
            "exact_source_kernel_check_exit_code",
            "exact_source_kernel_check_output_sha256",
        },
        "canonical kernel receipt v2 runtime",
    )
    require_digest(
        receipt_runtime["dynamic_axiom_audit_output_sha256"],
        HEX64,
        "canonical kernel receipt v2 runtime dynamic axiom digest",
    )
    require_digest(
        receipt_runtime["exact_source_kernel_check_output_sha256"],
        HEX64,
        "canonical kernel receipt v2 runtime exact source digest",
    )
    if receipt_runtime["exact_source_kernel_check_exit_code"] != 0:
        fail(
            "canonical kernel receipt v2 runtime exact source exit code "
            "must equal zero"
        )

    bootstrap = receipt.get("bootstrap_h0")
    if not isinstance(bootstrap, dict):
        fail("canonical kernel receipt v2 lacks bootstrap_h0")
    exact_keys(
        bootstrap,
        {
            "artifact",
            "claim_matrix",
            "persisted_claim_matrix",
            "role",
            "verified_candidate",
            "workflow",
        },
        "canonical kernel receipt v2 bootstrap_h0",
    )
    if bootstrap["role"] != CANONICAL_BOOTSTRAP_ROLE:
        fail("canonical kernel receipt v2 H0 bootstrap role differs")
    bootstrap_matrix = validate_kernel_matrix_identity(
        root,
        bootstrap["claim_matrix"],
        "canonical kernel receipt v2 bootstrap_h0.claim_matrix",
    )
    if bootstrap_matrix != source_matrix:
        fail("canonical kernel receipt v2 H0 matrix differs from transition source")
    persisted_h0_identity, persisted_h0_matrix = load_persisted_kernel_matrix(
        root,
        bootstrap["persisted_claim_matrix"],
        "canonical kernel receipt v2 bootstrap_h0.persisted_claim_matrix",
    )
    for key in ("bytes", "sha256", "git_blob_sha1"):
        if persisted_h0_identity[key] != bootstrap_matrix[key]:
            fail(
                "canonical kernel receipt v2 persisted H0 identity differs "
                "from the historical source identity"
            )
    if persisted_h0_identity["path"] == bootstrap_matrix["path"]:
        fail(
            "canonical kernel receipt v2 persisted H0 matrix must use a "
            "distinct path"
        )
    if (
        publication_id == CANONICAL_KERNEL_PUBLICATION_ID
        and persisted_h0_identity["path"] != CANONICAL_KERNEL_H0_MATRIX_PATH
    ):
        fail("canonical kernel receipt v2 persisted H0 matrix path differs")

    target_path = safe_relative(
        root,
        target_matrix["path"],
        "canonical kernel receipt v2 target_claim_matrix.path",
    )
    persisted_h1_matrix, target_raw = load_json(
        target_path,
        "canonical kernel receipt v2 target claim matrix",
    )
    if target_matrix != {
        "path": target_matrix["path"],
        "bytes": len(target_raw),
        "sha256": hashlib.sha256(target_raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(target_raw),
    }:
        fail("canonical kernel receipt v2 exact target matrix identity differs")
    validate_kernel_matrix_transition(
        persisted_h0_matrix,
        persisted_h1_matrix,
        transition["allowed_changes"],
    )
    expected_claim_proof_refs: dict[str, tuple[str, ...]] = {}
    for claim in persisted_h1_matrix["claims"]:
        claim_id = claim["claim_id"]
        if claim_id not in formal_claim_ids:
            continue
        proof_refs = claim.get("proof_refs")
        if (
            not isinstance(proof_refs, list)
            or not proof_refs
            or not all(isinstance(ref, str) and ref for ref in proof_refs)
            or len(proof_refs) != len(set(proof_refs))
        ):
            fail(
                "canonical kernel receipt v2 formal matrix claim proof_refs "
                "differ"
            )
        expected_claim_proof_refs[claim_id] = tuple(proof_refs)
    if set(expected_claim_proof_refs) != set(formal_claim_ids):
        fail(
            "canonical kernel receipt v2 formal matrix claim inventory "
            "differs"
        )
    bootstrap_candidate = validate_kernel_candidate(
        bootstrap["verified_candidate"],
        "canonical kernel receipt v2 bootstrap_h0.verified_candidate",
    )
    bootstrap_evidence, bootstrap_evidence_path = (
        validate_persisted_kernel_evidence(
            root,
            bootstrap["artifact"],
            "canonical kernel receipt v2 bootstrap_h0.artifact",
        )
    )
    if (
        bootstrap_evidence.get("schema") != CANONICAL_KERNEL_EVIDENCE_SCHEMA
        or bootstrap_evidence.get("state") != "KERNEL_VERIFIED"
        or bootstrap_evidence.get("publication_id") != publication_id
    ):
        fail("canonical kernel receipt v2 H0 raw evidence contract differs")
    observed_bootstrap_matrix = validate_kernel_matrix_identity(
        root,
        bootstrap_evidence.get("claim_matrix"),
        "canonical kernel receipt v2 H0 raw evidence claim_matrix",
    )
    if observed_bootstrap_matrix != source_matrix:
        fail("canonical kernel receipt v2 H0 raw evidence matrix differs")
    validate_kernel_workflow_alignment(
        bootstrap["workflow"],
        bootstrap_evidence.get("workflow"),
        bootstrap_candidate,
        "canonical kernel receipt v2 bootstrap_h0.workflow",
    )
    validate_kernel_source_alignment(
        receipt_source,
        bootstrap_evidence.get("source"),
        "canonical kernel receipt v2 H0",
    )
    if bootstrap_evidence.get("axioms_by_theorem") != receipt_axioms:
        fail("canonical kernel receipt v2 H0 axioms differ")
    bootstrap_bindings = validate_kernel_formal_evidence(
        root,
        bootstrap_evidence,
        receipt_plan=receipt_plan,
        receipt_compiled_object=receipt_compiled_object,
        receipt_source=receipt_source,
        receipt_theorems=receipt_theorems,
        receipt_axioms=receipt_axioms,
        expected_claim_proof_refs=expected_claim_proof_refs,
        formal_claim_count=formal_claim_count,
        where="canonical kernel receipt v2 H0 raw evidence",
    )
    bootstrap_execution = validate_kernel_execution_evidence(
        root,
        bootstrap_evidence,
        receipt_entrypoint=receipt_entrypoint,
        receipt_toolchain=receipt_toolchain,
        receipt_runtime=receipt_runtime,
        where="canonical kernel receipt v2 H0 raw evidence",
    )

    active_candidate = validate_kernel_candidate(
        receipt.get("verified_candidate"),
        "canonical kernel receipt v2 verified_candidate",
    )
    if active_candidate["head"] == bootstrap_candidate["head"]:
        fail("canonical kernel receipt v2 active fields still identify H0")
    active_artifact = receipt.get("artifact")
    if isinstance(active_artifact, dict):
        if active_artifact.get("id") == bootstrap["artifact"]["id"]:
            fail("canonical kernel receipt v2 H0/H1 artifact IDs must differ")
        if (
            active_artifact.get("archive_digest")
            == bootstrap["artifact"]["archive_digest"]
        ):
            fail(
                "canonical kernel receipt v2 H0/H1 archive digests must "
                "differ"
            )
        active_file = active_artifact.get("file")
        if (
            isinstance(active_file, dict)
            and active_file.get("sha256")
            == bootstrap["artifact"]["file"]["sha256"]
        ):
            fail(
                "canonical kernel receipt v2 H0/H1 raw file SHA-256 must "
                "differ"
            )
    active_evidence, active_evidence_path = validate_persisted_kernel_evidence(
        root,
        active_artifact,
        "canonical kernel receipt v2 active H1 artifact",
    )
    if active_evidence_path == bootstrap_evidence_path:
        fail("canonical kernel receipt v2 active artifact still identifies H0")
    if (
        active_evidence.get("schema") != CANONICAL_KERNEL_EVIDENCE_SCHEMA
        or active_evidence.get("state") != "KERNEL_VERIFIED"
        or active_evidence.get("publication_id") != publication_id
    ):
        fail("canonical kernel receipt v2 H1 raw evidence contract differs")
    observed_target_matrix = validate_kernel_matrix_identity(
        root,
        active_evidence.get("claim_matrix"),
        "canonical kernel receipt v2 H1 raw evidence claim_matrix",
    )
    if observed_target_matrix != target_matrix:
        fail("canonical kernel receipt v2 H1 raw evidence target matrix differs")
    validate_kernel_workflow_alignment(
        receipt.get("workflow"),
        active_evidence.get("workflow"),
        active_candidate,
        "canonical kernel receipt v2 active H1 workflow",
    )
    validate_kernel_source_alignment(
        receipt_source,
        active_evidence.get("source"),
        "canonical kernel receipt v2 H1",
    )
    if active_evidence.get("axioms_by_theorem") != receipt_axioms:
        fail("canonical kernel receipt v2 H1 axioms differ")
    active_bindings = validate_kernel_formal_evidence(
        root,
        active_evidence,
        receipt_plan=receipt_plan,
        receipt_compiled_object=receipt_compiled_object,
        receipt_source=receipt_source,
        receipt_theorems=receipt_theorems,
        receipt_axioms=receipt_axioms,
        expected_claim_proof_refs=expected_claim_proof_refs,
        formal_claim_count=formal_claim_count,
        where="canonical kernel receipt v2 H1 raw evidence",
    )
    if active_bindings != bootstrap_bindings:
        fail("canonical kernel receipt v2 H0/H1 formal bindings differ")
    active_execution = validate_kernel_execution_evidence(
        root,
        active_evidence,
        receipt_entrypoint=receipt_entrypoint,
        receipt_toolchain=receipt_toolchain,
        receipt_runtime=receipt_runtime,
        where="canonical kernel receipt v2 H1 raw evidence",
    )
    if active_execution != bootstrap_execution:
        fail("canonical kernel receipt v2 H0/H1 execution evidence differs")

    boundary = receipt.get("materialization_boundary")
    if not isinstance(boundary, dict):
        fail("canonical kernel receipt v2 lacks materialization_boundary")
    exact_keys(
        boundary,
        {
            "containing_head_binding",
            "containing_tree_binding",
            "predecessor_head",
            "required_relation",
            "self_inclusion_claimed",
            "stage",
        },
        "canonical kernel receipt v2 materialization_boundary",
    )
    if boundary != {
        "stage": "H2",
        "required_relation": "SINGLE_PARENT_SUCCESSOR",
        "predecessor_head": active_candidate["head"],
        "containing_head_binding": "EXTERNAL_TO_RECEIPT",
        "containing_tree_binding": "EXTERNAL_TO_RECEIPT",
        "self_inclusion_claimed": False,
    }:
        fail("canonical kernel receipt v2 H2 materialization boundary differs")


def validate_claim_matrix_projection(
    claim_matrix_file: pathlib.Path,
    publication_id: str,
    bundle_claim_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    matrix, _raw = load_json(claim_matrix_file, "bound CLAIM_MATRIX artifact")
    required_top_level = {"publication_id", "claim_count", "claims"}
    missing_top_level = required_top_level - set(matrix)
    if missing_top_level:
        fail(
            "bound CLAIM_MATRIX lacks required keys: "
            + ",".join(sorted(missing_top_level))
        )
    if matrix["publication_id"] != publication_id:
        fail("bound CLAIM_MATRIX publication_id differs")
    matrix_claims = matrix["claims"]
    claim_count = matrix["claim_count"]
    if (
        isinstance(claim_count, bool)
        or not isinstance(claim_count, int)
        or claim_count < 1
        or not isinstance(matrix_claims, list)
        or claim_count != len(matrix_claims)
    ):
        fail("bound CLAIM_MATRIX claim_count differs from its claim inventory")

    matrix_claim_by_id: dict[str, Mapping[str, Any]] = {}
    required_claim_keys = {
        "claim_id",
        "statement",
        "classification",
        "status",
        "boundary",
        "proof_refs",
        "sources",
    }
    for index, matrix_claim in enumerate(matrix_claims):
        where = f"bound CLAIM_MATRIX claims[{index}]"
        if not isinstance(matrix_claim, dict):
            fail(where + " must be an object")
        missing_claim_keys = required_claim_keys - set(matrix_claim)
        if missing_claim_keys:
            fail(
                f"{where} lacks required keys: "
                + ",".join(sorted(missing_claim_keys))
            )
        claim_id = require_text(matrix_claim["claim_id"], where + ".claim_id")
        if SAFE_ID.fullmatch(claim_id) is None or claim_id in matrix_claim_by_id:
            fail("bound CLAIM_MATRIX claim IDs must be safe and unique")
        matrix_claim_by_id[claim_id] = matrix_claim

    matrix_ids = set(matrix_claim_by_id)
    bundle_ids = set(bundle_claim_by_id)
    if matrix_ids != bundle_ids or claim_count != len(bundle_ids):
        missing = sorted(matrix_ids - bundle_ids)
        extra = sorted(bundle_ids - matrix_ids)
        details: list[str] = []
        if missing:
            details.append("missing_from_bundle=" + ",".join(missing))
        if extra:
            details.append("absent_from_matrix=" + ",".join(extra))
        fail(
            "bundle claims differ bidirectionally from the bound CLAIM_MATRIX"
            + (": " + "; ".join(details) if details else "")
        )

    for claim_id in sorted(matrix_ids):
        matrix_claim = matrix_claim_by_id[claim_id]
        bundle_claim = bundle_claim_by_id[claim_id]
        where = f"bound CLAIM_MATRIX claim {claim_id}"
        statement = require_text(matrix_claim["statement"], where + ".statement")
        boundary = require_text(matrix_claim["boundary"], where + ".boundary")
        classification = matrix_claim["classification"]
        if classification not in ALLOWED_CLASSIFICATIONS:
            fail(f"{where}.classification is invalid")
        if (
            statement != bundle_claim["statement"]
            or classification != bundle_claim["classification"]
            or boundary != bundle_claim["scope"]
        ):
            fail(
                f"{claim_id} statement/classification/boundary projection "
                "differs from the bound CLAIM_MATRIX"
            )

        matrix_status = require_text(matrix_claim["status"], where + ".status")
        normalized_status = MATRIX_STATUS_ALIASES[classification].get(matrix_status)
        if normalized_status is None or normalized_status != bundle_claim["status"]:
            fail(f"{claim_id} status projection differs from the bound CLAIM_MATRIX")

        matrix_theorems = set(
            require_unique_text_list(
                matrix_claim["proof_refs"],
                where + ".proof_refs",
            )
        )
        bundle_theorems = {
            reference_fragment(
                reference,
                f"bundle claim {claim_id} proof reference",
            )
            for reference in bundle_claim["proof_refs"]
        }
        if matrix_theorems != bundle_theorems:
            fail(
                f"{claim_id} formal theorem fragments differ from the bound "
                "CLAIM_MATRIX"
            )

        matrix_sources = set(
            require_unique_text_list(
                matrix_claim["sources"],
                where + ".sources",
            )
        )
        bundle_source_ids = [
            reference_fragment(
                reference,
                f"bundle claim {claim_id} source/evidence reference",
            )
            for reference in (
                *bundle_claim["evidence_refs"],
                *bundle_claim["source_refs"],
            )
        ]
        if len(bundle_source_ids) != len(set(bundle_source_ids)):
            fail(f"bundle claim {claim_id} source IDs must be unique")
        if matrix_sources != set(bundle_source_ids):
            fail(
                f"{claim_id} source IDs differ from the bound CLAIM_MATRIX"
            )


def validate_return_receipt(
    root: pathlib.Path,
    receipt_path: str,
    publication_id: str,
    candidate_by_path: Mapping[str, Mapping[str, Any]],
    claim_ids: set[str],
    expected_content_changed: bool,
    expected_change_notice: str | None,
) -> dict[str, Any]:
    path = safe_relative(root, receipt_path, "prepublication_return.receipt_path")
    value, _raw = load_json(path, "prepublication return receipt")
    if value.get("schema") == LEGACY_RETURN_SCHEMA:
        fail(
            "legacy v1 prepublication return receipts are historical/read-only "
            "and cannot authorize a new production mutation"
        )
    exact_keys(
        value,
        {
            "_license",
            "schema",
            "publication_id",
            "content_changed",
            "original_files",
            "candidate_files",
            "changed_claim_ids",
            "change_reasons",
            "change_notice_path",
            "return",
        },
        "prepublication return receipt",
    )
    if value["schema"] != RETURN_SCHEMA:
        fail("unsupported prepublication return receipt schema")
    validate_license(
        value["_license"],
        "prepublication return receipt._license",
        classification="machine_readable_prepublication_return_receipt",
    )
    receipt_publication_id = require_publication_id(
        value["publication_id"],
        "prepublication return receipt.publication_id",
    )
    if receipt_publication_id != publication_id:
        fail("prepublication return receipt publication_id differs")
    if value["content_changed"] is not expected_content_changed:
        fail("prepublication return receipt content_changed differs")
    if value["change_notice_path"] != expected_change_notice:
        fail("prepublication return receipt change_notice_path differs")

    candidate_files = value["candidate_files"]
    if not isinstance(candidate_files, list) or not candidate_files:
        fail("prepublication return receipt candidate_files must be non-empty")
    returned: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(candidate_files):
        where = f"prepublication return receipt candidate_files[{index}]"
        if not isinstance(item, dict):
            fail(where + " must be an object")
        exact_keys(item, {"path", "bytes", "sha256", "git_blob_sha1"}, where)
        raw_path = require_text(item["path"], where + ".path")
        if raw_path in returned:
            fail("duplicate candidate path in prepublication return receipt")
        if (
            isinstance(item["bytes"], bool)
            or not isinstance(item["bytes"], int)
            or item["bytes"] < 0
        ):
            fail(f"{where}.bytes must be a non-negative integer")
        require_digest(item["sha256"], HEX64, where + ".sha256")
        require_digest(item["git_blob_sha1"], HEX40, where + ".git_blob_sha1")
        observed_path = safe_relative(root, raw_path, where + ".path")
        observed = identity(observed_path)
        if item["bytes"] != observed["bytes"]:
            fail(f"returned candidate byte-size mismatch for {raw_path}")
        if item["sha256"] != observed["sha256"]:
            fail(f"returned candidate SHA-256 mismatch for {raw_path}")
        if item["git_blob_sha1"] != observed["git_blob_sha1"]:
            fail(f"returned candidate Git blob mismatch for {raw_path}")
        returned[raw_path] = dict(item)
    if set(returned) != set(candidate_by_path):
        fail("returned candidate file set differs from the frozen upload candidate")
    for raw_path, candidate in candidate_by_path.items():
        item = returned[raw_path]
        for key in ("bytes", "sha256", "git_blob_sha1"):
            if item[key] != candidate[key]:
                fail(f"returned bytes differ from upload candidate for {raw_path}")

    original_files = value["original_files"]
    changed_claim_ids = value["changed_claim_ids"]
    change_reasons = value["change_reasons"]
    if not isinstance(original_files, list):
        fail("prepublication return receipt original_files must be a list")
    originals: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(original_files):
        where = f"prepublication return receipt original_files[{index}]"
        if not isinstance(item, dict):
            fail(where + " must be an object")
        exact_keys(item, {"path", "bytes", "sha256", "git_blob_sha1"}, where)
        raw_path = require_text(item["path"], where + ".path")
        if raw_path in originals:
            fail("duplicate original path in prepublication return receipt")
        if (
            isinstance(item["bytes"], bool)
            or not isinstance(item["bytes"], int)
            or item["bytes"] < 0
        ):
            fail(f"{where}.bytes must be a non-negative integer")
        require_digest(item["sha256"], HEX64, where + ".sha256")
        require_digest(item["git_blob_sha1"], HEX40, where + ".git_blob_sha1")
        observed_path = safe_relative(root, raw_path, where + ".path")
        observed = identity(observed_path)
        for key in ("bytes", "sha256", "git_blob_sha1"):
            if item[key] != observed[key]:
                fail(f"original file identity mismatch for {raw_path}")
        originals[raw_path] = dict(item)

    changed_ids = require_unique_text_list(
        changed_claim_ids,
        "prepublication return receipt changed_claim_ids",
    )
    if any(SAFE_ID.fullmatch(claim_id) is None for claim_id in changed_ids):
        fail("prepublication return receipt changed claim IDs are unsafe")
    if not set(changed_ids).issubset(claim_ids):
        fail("prepublication return receipt names an unknown changed claim ID")
    if not isinstance(change_reasons, list):
        fail("prepublication return receipt change_reasons must be a list")
    reasons_by_claim: dict[str, dict[str, str]] = {}
    for index, item in enumerate(change_reasons):
        where = f"prepublication return receipt change_reasons[{index}]"
        if not isinstance(item, dict):
            fail(where + " must be an object")
        exact_keys(
            item,
            {
                "claim_id",
                "reason",
                "original_sha256",
                "corrected_sha256",
                "exact_candidate_path",
            },
            where,
        )
        claim_id = require_text(item["claim_id"], where + ".claim_id")
        if SAFE_ID.fullmatch(claim_id) is None or claim_id in reasons_by_claim:
            fail("change reasons must use safe, unique claim IDs")
        reason = require_text(item["reason"], where + ".reason")
        original_sha256 = require_digest(
            item["original_sha256"],
            HEX64,
            where + ".original_sha256",
        )
        corrected_sha256 = require_digest(
            item["corrected_sha256"],
            HEX64,
            where + ".corrected_sha256",
        )
        candidate_path = require_text(
            item["exact_candidate_path"],
            where + ".exact_candidate_path",
        )
        safe_relative(
            root,
            candidate_path,
            where + ".exact_candidate_path",
        )
        if candidate_path not in returned:
            fail(f"{where} exact_candidate_path is not a returned candidate")
        if corrected_sha256 != returned[candidate_path]["sha256"]:
            fail(f"{where} corrected SHA-256 differs from the returned candidate")
        if original_sha256 not in {
            original["sha256"] for original in originals.values()
        }:
            fail(f"{where} original SHA-256 is absent from original_files")
        if original_sha256 == corrected_sha256:
            fail(f"{where} does not identify changed bytes")
        reasons_by_claim[claim_id] = {
            "reason": reason,
            "original_sha256": original_sha256,
            "corrected_sha256": corrected_sha256,
            "exact_candidate_path": candidate_path,
        }

    if expected_content_changed:
        if not originals or not changed_ids or expected_change_notice is None:
            fail("changed content lacks original identity, changed claims or change notice")
        if set(reasons_by_claim) != set(changed_ids):
            fail("changed claim IDs and change reasons differ")
        notice_path = safe_relative(root, expected_change_notice, "change notice path")
        if notice_path.suffix.casefold() != ".md":
            fail("visible change notice must be a Markdown document")
        notice_raw = read_regular(notice_path, MAX_JSON_BYTES)
        try:
            notice_text = notice_raw.decode("utf-8")
        except UnicodeDecodeError:
            fail("visible change notice must be valid UTF-8")
        normalized_notice = " ".join(notice_text.split())
        if not normalized_notice:
            fail("visible change notice must not be empty")
        for claim_id, reason_binding in reasons_by_claim.items():
            if (
                claim_id not in normalized_notice
                or " ".join(reason_binding["reason"].split())
                not in normalized_notice
            ):
                fail(
                    "visible change notice omits a changed claim ID or its "
                    f"machine-bound reason: {claim_id}"
                )
    else:
        if (
            expected_change_notice is not None
            or originals
            or changed_ids
            or reasons_by_claim
        ):
            fail(
                "unchanged content must not declare originals, a change notice, "
                "changed claims or change reasons"
            )

    returned_to = value["return"]
    if not isinstance(returned_to, dict):
        fail("prepublication return receipt return must be an object")
    exact_keys(
        returned_to,
        {
            "candidate_returned_to_owner",
            "owner_name",
            "owner_type",
            "return_channel",
            "returned_at",
            "visible_change_notice_returned",
        },
        "prepublication return receipt return",
    )
    if (
        returned_to["candidate_returned_to_owner"] is not True
        or returned_to["owner_name"] != "Ingolf Lohmann"
        or returned_to["owner_type"] != "NATURAL_PERSON"
    ):
        fail("candidate-specific return to Ingolf Lohmann is not acknowledged")
    require_text(returned_to["return_channel"], "return.return_channel")
    validate_rfc3339(returned_to["returned_at"], "return.returned_at")
    if expected_content_changed and returned_to["visible_change_notice_returned"] is not True:
        fail("changed content was not returned with a visible change notice")
    if (
        not expected_content_changed
        and returned_to["visible_change_notice_returned"] is not False
    ):
        fail("unchanged content may not claim a visible change notice return")
    return value


def validate_bundle(
    root: pathlib.Path,
    bundle_path: pathlib.Path,
    *,
    upload_paths: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Validate one complete proof bundle and return its normalized identity."""
    root = root.resolve()
    bundle_path = bundle_path.resolve()
    try:
        bundle_relative = bundle_path.relative_to(root).as_posix()
    except ValueError:
        fail("proof bundle must be inside the repository root")
    value, raw = load_json(bundle_path, "machine proof bundle")
    if value.get("schema") == LEGACY_BUNDLE_SCHEMA:
        fail(
            "legacy v1 machine-proof bundles are historical/read-only and "
            "cannot authorize a new production mutation"
        )
    exact_keys(
        value,
        {
            "_license",
            "schema",
            "policy",
            "publication_id",
            "candidate",
            "claims",
            "artifacts",
            "prepublication_return",
            "gates",
            "completion_claims",
        },
        "machine proof bundle",
    )
    if value["schema"] != BUNDLE_SCHEMA:
        fail("unsupported machine proof bundle schema")
    validate_license(
        value["_license"],
        "machine proof bundle._license",
        classification="machine_readable_proof_bundle",
    )
    publication_id = require_publication_id(
        value["publication_id"],
        "publication_id",
    )

    policy_identity = validate_active_policy(root, value["policy"])

    candidate = value["candidate"]
    if not isinstance(candidate, dict):
        fail("candidate must be an object")
    exact_keys(candidate, {"files", "primary_document_path"}, "candidate")
    raw_files = candidate["files"]
    if not isinstance(raw_files, list) or not raw_files:
        fail("candidate.files must be non-empty")
    candidate_by_path: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_files):
        if not isinstance(item, dict):
            fail(f"candidate.files[{index}] must be an object")
        raw_path, observed = validate_bound_identity(
            root, item, f"candidate.files[{index}]", include_bytes=True
        )
        if raw_path in candidate_by_path:
            fail("candidate.files contains duplicate paths")
        normalized = dict(item)
        normalized.update(observed)
        candidate_by_path[raw_path] = normalized
    primary = require_text(candidate["primary_document_path"], "candidate.primary_document_path")
    if primary not in candidate_by_path:
        fail("primary_document_path is absent from candidate.files")
    if candidate_by_path[primary]["role"] != "PRIMARY":
        fail("primary_document_path does not have PRIMARY role")

    artifacts = value["artifacts"]
    if not isinstance(artifacts, list) or not artifacts:
        fail("artifacts must be non-empty")
    artifact_by_path: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            fail(f"artifacts[{index}] must be an object")
        raw_path, _observed = validate_bound_identity(
            root, item, f"artifacts[{index}]", include_bytes=False
        )
        if raw_path in artifact_by_path:
            fail("artifacts contains duplicate paths")
        artifact_by_path[raw_path] = dict(item)
    candidate_artifact_overlap = set(candidate_by_path) & set(artifact_by_path)
    if candidate_artifact_overlap:
        fail(
            "candidate and artifact path sets overlap: "
            + ",".join(sorted(candidate_artifact_overlap))
        )
    if bundle_relative in candidate_by_path or bundle_relative in artifact_by_path:
        fail("proof bundle may not self-bind through candidate or artifact paths")
    claim_matrix_paths = [
        raw_path
        for raw_path, item in artifact_by_path.items()
        if item["kind"] == "CLAIM_MATRIX"
    ]
    if len(claim_matrix_paths) != 1:
        fail("proof bundle must contain exactly one bound CLAIM_MATRIX artifact")
    claim_matrix_path = claim_matrix_paths[0]
    claim_matrix_file = safe_relative(
        root,
        claim_matrix_path,
        "bound CLAIM_MATRIX artifact",
    )
    claim_matrix_identity = {
        "path": claim_matrix_path,
        **identity(claim_matrix_file),
    }

    claims = value["claims"]
    if not isinstance(claims, list) or not claims:
        fail("claims must be non-empty")
    claim_ids: set[str] = set()
    bundle_claim_by_id: dict[str, Mapping[str, Any]] = {}
    verified_kernel_receipts: dict[str, set[str]] = {}
    for index, claim in enumerate(claims):
        where = f"claims[{index}]"
        if not isinstance(claim, dict):
            fail(where + " must be an object")
        exact_keys(
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
        claim_id = require_text(claim["claim_id"], where + ".claim_id")
        if SAFE_ID.fullmatch(claim_id) is None or claim_id in claim_ids:
            fail("claim IDs must be safe and unique")
        claim_ids.add(claim_id)
        bundle_claim_by_id[claim_id] = claim
        require_text(claim["statement"], where + ".statement")
        require_text(claim["scope"], where + ".scope")
        classification = claim["classification"]
        if classification not in ALLOWED_CLASSIFICATIONS:
            fail(where + ".classification is invalid")
        expected_status, expected_wording = EXPECTED_DISPOSITION[classification]
        if claim["status"] != expected_status or claim["publication_wording"] != expected_wording:
            fail(f"{claim_id} has a disposition inconsistent with {classification}")
        references: dict[str, Sequence[str]] = {}
        for key in ("proof_refs", "evidence_refs", "source_refs"):
            raw_refs = claim[key]
            if not isinstance(raw_refs, list) or not all(
                isinstance(ref, str) and ref for ref in raw_refs
            ):
                fail(f"{where}.{key} must be a string list")
            references[key] = raw_refs
            for reference in raw_refs:
                base = reference_base(reference)
                if base not in artifact_by_path:
                    fail(f"unresolved {key} reference for {claim_id}: {reference}")
        if classification == "FORMAL_PROVED":
            if not references["proof_refs"]:
                fail(f"formal claim {claim_id} lacks a proof reference")
            if not all(
                artifact_by_path[reference_base(ref)]["kind"] == "KERNEL_RECEIPT"
                for ref in references["proof_refs"]
            ):
                fail(f"formal claim {claim_id} is not bound to a kernel receipt")
            for reference in references["proof_refs"]:
                receipt_path = reference_base(reference)
                if receipt_path in verified_kernel_receipts:
                    theorem_inventory = verified_kernel_receipts[receipt_path]
                else:
                    receipt_file = safe_relative(
                        root,
                        receipt_path,
                        f"kernel receipt referenced by {claim_id}",
                    )
                    receipt_value, _receipt_raw = load_json(
                        receipt_file,
                        f"kernel receipt referenced by {claim_id}",
                    )
                    canonical_context = (
                        receipt_path == CANONICAL_KERNEL_RECEIPT_PATH
                        or publication_id == CANONICAL_KERNEL_PUBLICATION_ID
                        or bool(
                            CANONICAL_KERNEL_MARKERS.intersection(
                                receipt_value
                            )
                        )
                    )
                    if (
                        canonical_context
                        and receipt_value.get("schema")
                        != CANONICAL_KERNEL_RECEIPT_SCHEMA
                    ):
                        fail(
                            "canonical kernel receipt context requires the "
                            "exact v2 schema"
                        )
                    if (
                        receipt_value.get("schema")
                        == CANONICAL_KERNEL_RECEIPT_SCHEMA
                    ):
                        validate_canonical_kernel_receipt_v2(
                            root,
                            receipt_value,
                            publication_id,
                            claim_matrix_identity,
                        )
                    if receipt_value.get("state") != "KERNEL_VERIFIED":
                        fail(
                            f"kernel receipt {receipt_path} state must equal "
                            "KERNEL_VERIFIED"
                        )
                    receipt_ids = [
                        receipt_value[key]
                        for key in ("publication_id", "scope_id")
                        if key in receipt_value
                    ]
                    if (
                        not receipt_ids
                        or any(
                            not isinstance(receipt_id, str)
                            or receipt_id != publication_id
                            for receipt_id in receipt_ids
                        )
                    ):
                        fail(
                            f"kernel receipt {receipt_path} publication/scope "
                            "identity differs"
                        )
                    workflow = receipt_value.get("workflow")
                    if (
                        not isinstance(workflow, dict)
                        or workflow.get("conclusion") != "success"
                        or workflow.get("exact_head_bound") is not True
                    ):
                        fail(
                            f"kernel receipt {receipt_path} lacks a successful "
                            "exact-head workflow"
                        )
                    theorems = receipt_value.get("theorems")
                    if (
                        not isinstance(theorems, list)
                        or not theorems
                        or not all(
                            isinstance(theorem, str) and theorem
                            for theorem in theorems
                        )
                        or len(theorems) != len(set(theorems))
                    ):
                        fail(
                            f"kernel receipt {receipt_path} theorem inventory "
                            "must be non-empty and unique"
                        )
                    theorem_inventory = set(theorems)
                    transition = receipt_value.get("claim_transition")
                    if transition is not None:
                        if not isinstance(transition, dict):
                            fail(
                                f"kernel receipt {receipt_path} claim_transition "
                                "must be an object"
                            )
                        if (
                            transition.get(
                                "target_exact_head_confirmation_required"
                            )
                            is not False
                        ):
                            fail(
                                f"kernel receipt {receipt_path} still requires "
                                "target exact-head confirmation"
                            )
                        target_matrix = transition.get("target_claim_matrix")
                        if not isinstance(target_matrix, dict):
                            fail(
                                f"kernel receipt {receipt_path} lacks its target "
                                "claim matrix"
                            )
                        exact_keys(
                            target_matrix,
                            {"path", "bytes", "sha256", "git_blob_sha1"},
                            f"kernel receipt {receipt_path} target_claim_matrix",
                        )
                        if target_matrix != claim_matrix_identity:
                            fail(
                                f"kernel receipt {receipt_path} target claim "
                                "matrix differs from the bound CLAIM_MATRIX"
                            )
                    verified_kernel_receipts[receipt_path] = theorem_inventory
                _base, separator, fragment = reference.partition("#")
                if (
                    not separator
                    or not fragment
                    or "#" in fragment
                    or fragment not in theorem_inventory
                ):
                    fail(
                        f"formal claim {claim_id} proof reference must contain "
                        "an exact theorem fragment present in the kernel receipt"
                    )
        elif classification == "EMPIRICALLY_EVIDENCED" and not references["evidence_refs"]:
            fail(f"empirical claim {claim_id} lacks evidence")
        elif classification == "SOURCE_BOUND" and not references["source_refs"]:
            fail(f"source-bound claim {claim_id} lacks a source")
        elif classification in {"NORMATIVE", "INTERPRETATIVE", "OPEN"}:
            if references["proof_refs"]:
                fail(f"{classification} claim {claim_id} may not masquerade as a formal proof")

    validate_claim_matrix_projection(
        claim_matrix_file,
        publication_id,
        bundle_claim_by_id,
    )

    returned = value["prepublication_return"]
    if not isinstance(returned, dict):
        fail("prepublication_return must be an object")
    exact_keys(
        returned,
        {
            "content_changed",
            "candidate_returned_to_owner",
            "receipt_path",
            "change_notice_path",
        },
        "prepublication_return",
    )
    if returned["candidate_returned_to_owner"] is not True:
        fail("candidate has not been returned to Ingolf Lohmann before upload")
    if not isinstance(returned["content_changed"], bool):
        fail("prepublication_return.content_changed must be boolean")
    receipt_path = require_text(returned["receipt_path"], "prepublication_return.receipt_path")
    change_notice = returned["change_notice_path"]
    if change_notice is not None:
        require_text(change_notice, "prepublication_return.change_notice_path")
    if receipt_path not in artifact_by_path or artifact_by_path[receipt_path]["kind"] != "RETURN_RECEIPT":
        fail("prepublication return receipt is not a bound RETURN_RECEIPT artifact")
    if returned["content_changed"]:
        if change_notice is None:
            fail("changed content lacks CHANGE_NOTICE")
        if change_notice not in artifact_by_path or artifact_by_path[change_notice]["kind"] != "CHANGE_NOTICE":
            fail("change notice is not a bound CHANGE_NOTICE artifact")
    elif change_notice is not None:
        fail("unchanged content may not declare a change notice")
    validate_return_receipt(
        root,
        receipt_path,
        publication_id,
        candidate_by_path,
        claim_ids,
        returned["content_changed"],
        change_notice,
    )

    gates = value["gates"]
    if not isinstance(gates, dict):
        fail("gates must be an object")
    required_gates = {
        "all_claims_dispositioned",
        "all_references_resolve",
        "candidate_frozen",
        "formal_claims_have_kernel_receipts",
        "open_claims_not_worded_as_facts",
        "proof_bundle_in_upload_fileset",
        "returned_bytes_equal_upload_bytes",
    }
    exact_keys(gates, required_gates, "gates")
    if any(gates[key] is not True for key in required_gates):
        fail("every machine-proof gate must equal true")

    completion = value["completion_claims"]
    if not isinstance(completion, dict):
        fail("completion_claims must be an object")
    exact_keys(completion, {"machine_proof_complete", "zenodo_upload_authorized"}, "completion_claims")
    if completion != {"machine_proof_complete": True, "zenodo_upload_authorized": True}:
        fail("proof bundle does not authorize the exact Zenodo upload")

    if upload_paths is not None:
        upload_list = list(upload_paths)
        normalized_uploads: list[str] = []
        for index, raw_path in enumerate(upload_list):
            path = require_text(raw_path, f"upload_paths[{index}]")
            safe_relative(root, path, f"upload_paths[{index}]")
            normalized_uploads.append(path)
        if len(normalized_uploads) != len(set(normalized_uploads)):
            fail("Zenodo upload fileset contains duplicate repository paths")
        upload_set = set(normalized_uploads)
        required_uploads = (
            set(candidate_by_path) | set(artifact_by_path) | {bundle_relative}
        )
        missing = required_uploads - upload_set
        extra = upload_set - required_uploads
        if missing or extra:
            details: list[str] = []
            if missing:
                details.append("missing=" + ",".join(sorted(missing)))
            if extra:
                details.append("extra=" + ",".join(sorted(extra)))
            fail(
                "Zenodo upload fileset differs from the exact proof-bearing set: "
                + "; ".join(details)
            )

    return {
        "schema": BUNDLE_SCHEMA,
        "publication_id": publication_id,
        "path": bundle_relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
        "policy": policy_identity,
        "claim_count": len(claims),
        "candidate_file_count": len(candidate_by_path),
        "artifact_count": len(artifact_by_path),
        "machine_proof_complete": True,
        "zenodo_upload_authorized": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a QIK-VRT Zenodo machine-proof bundle")
    parser.add_argument("--proof-bundle", required=True)
    parser.add_argument("--upload-path", action="append", default=[])
    args = parser.parse_args(argv)
    root = pathlib.Path.cwd().resolve()
    try:
        bundle_path = safe_relative(root, args.proof_bundle, "--proof-bundle")
        receipt = validate_bundle(
            root,
            bundle_path,
            upload_paths=args.upload_path if args.upload_path else None,
        )
    except ProofGateError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    print("ZENODO_MACHINE_PROOF_STATE=verified")
    print("ZENODO_MACHINE_PROOF_SHA256=" + receipt["sha256"])
    print("ZENODO_MACHINE_PROOF_GIT_BLOB=" + receipt["git_blob_sha1"])
    print("ZENODO_MACHINE_PROOF_CLAIMS=" + str(receipt["claim_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
