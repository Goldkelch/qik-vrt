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
