#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed machine-proof gate for every future Zenodo publication.

The gate proves artifact identity and completeness of claim disposition.  It does
not relabel natural-language interpretation as a mathematical theorem.  Each
claim must be classified, scoped and connected to an exact proof, evidence,
source or explicit OPEN disposition before a production upload is admissible.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NoReturn

POLICY_SCHEMA = "qikvrt_zenodo_machine_proof_policy_v1"
POLICY_ID = "qikvrt-zenodo-machine-proof-before-publication-v1"
POLICY_PATH = "policy/zenodo-machine-proof-policy-v1.json"
BUNDLE_SCHEMA = "qikvrt_zenodo_machine_proof_bundle_v1"
RETURN_SCHEMA = "qikvrt_prepublication_return_receipt_v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024

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


def validate_return_receipt(
    root: pathlib.Path,
    receipt_path: str,
    publication_id: str,
    candidate_by_path: Mapping[str, Mapping[str, Any]],
    expected_content_changed: bool,
    expected_change_notice: str | None,
) -> dict[str, Any]:
    path = safe_relative(root, receipt_path, "prepublication_return.receipt_path")
    value, _raw = load_json(path, "prepublication return receipt")
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
            "change_notice_path",
            "return",
        },
        "prepublication return receipt",
    )
    if value["schema"] != RETURN_SCHEMA:
        fail("unsupported prepublication return receipt schema")
    if value["publication_id"] != publication_id:
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
    if not isinstance(original_files, list) or not isinstance(changed_claim_ids, list):
        fail("prepublication return receipt original/change lists are invalid")
    if expected_content_changed:
        if not original_files or not changed_claim_ids or expected_change_notice is None:
            fail("changed content lacks original identity, changed claims or change notice")
        safe_relative(root, expected_change_notice, "change notice path")
    else:
        if expected_change_notice is not None or changed_claim_ids:
            fail("unchanged content must not declare a change notice or changed claims")

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
    require_text(returned_to["returned_at"], "return.returned_at")
    if expected_content_changed and returned_to["visible_change_notice_returned"] is not True:
        fail("changed content was not returned with a visible change notice")
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
    publication_id = require_text(value["publication_id"], "publication_id")
    if SAFE_ID.fullmatch(publication_id) is None:
        fail("publication_id is unsafe")

    policy = value["policy"]
    if not isinstance(policy, dict):
        fail("policy must be an object")
    exact_keys(policy, {"id", "path", "version"}, "policy")
    if policy != {"id": POLICY_ID, "path": POLICY_PATH, "version": "1.0.0"}:
        fail("proof bundle is not bound to the active Zenodo proof policy")
    policy_path = safe_relative(root, POLICY_PATH, "policy.path")
    policy_value, _ = load_json(policy_path, "active Zenodo proof policy")
    if policy_value.get("schema") != POLICY_SCHEMA:
        fail("active Zenodo proof policy schema differs")

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
    if not any(item["kind"] == "CLAIM_MATRIX" for item in artifacts):
        fail("proof bundle lacks a bound CLAIM_MATRIX artifact")

    claims = value["claims"]
    if not isinstance(claims, list) or not claims:
        fail("claims must be non-empty")
    claim_ids: set[str] = set()
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
        elif classification == "EMPIRICALLY_EVIDENCED" and not references["evidence_refs"]:
            fail(f"empirical claim {claim_id} lacks evidence")
        elif classification == "SOURCE_BOUND" and not references["source_refs"]:
            fail(f"source-bound claim {claim_id} lacks a source")
        elif classification in {"NORMATIVE", "INTERPRETATIVE", "OPEN"}:
            if references["proof_refs"]:
                fail(f"{classification} claim {claim_id} may not masquerade as a formal proof")

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
        upload_set = set(upload_paths)
        if bundle_relative not in upload_set:
            fail("MACHINE_PROOF_BUNDLE.json is absent from the Zenodo upload fileset")
        required_uploads = set(candidate_by_path) | set(artifact_by_path) | {bundle_relative}
        missing = required_uploads - upload_set
        if missing:
            fail("proof-bearing upload omits required files: " + ",".join(sorted(missing)))

    return {
        "schema": BUNDLE_SCHEMA,
        "publication_id": publication_id,
        "path": bundle_relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
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
