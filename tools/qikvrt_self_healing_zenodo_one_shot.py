#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed one-shot wrapper for one exact self-healing publication.

This module adds no Zenodo transport. It binds the existing hardened generic
publisher to one publication ID, one owner authorization ID, and one exact
candidate hash tuple. The check path is repository-internal and read-only.
The execute path remains unreachable until a compatible committed v2 manifest
exists and an explicit workflow-dispatch confirmation is supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from typing import Any, NoReturn

from tools import qikvrt_zenodo_publish as publisher

PUBLICATION_ID = "qikvrt-self-healing-repository-collective-intelligence-v1"
AUTHORIZATION_ID = (
    "qikvrt-self-healing-repository-collective-intelligence-v1-4fa477b9"
)
CONFIRMATION = "PUBLISH_TO_PRODUCTION_ZENODO"
REPOSITORY = "Goldkelch/qik-vrt"
AUTHORIZATION_PATH = pathlib.PurePosixPath(
    "work-units/REQUEST_EXACT_ZENODO_AUTHORIZATION_SELF_HEALING_REPOSITORY_V1.json"
)
MANIFEST_PATH = pathlib.PurePosixPath(
    "release/self-healing-repository-collective-intelligence-zenodo-v1/"
    "PUBLISH_REQUEST.json"
)
CANDIDATE_HASHES = {
    "machine_proof": (
        pathlib.PurePosixPath(
            "release/self-healing-repository-collective-intelligence-zenodo-v1/"
            "MACHINE_PROOF_BUNDLE.json"
        ),
        "4fa477b9b2160382c1c231911e0bae20db05471599352c247a390672bb4fd5cc",
    ),
    "metadata": (
        pathlib.PurePosixPath(
            "release/self-healing-repository-collective-intelligence-zenodo-v1/"
            "ZENODO_METADATA.json"
        ),
        "acebc139ecda233dc9b47fdf565f2fbbeea8340ea045cc842d363e7f3a6e12f6",
    ),
    "return_receipt": (
        pathlib.PurePosixPath(
            "release/self-healing-repository-collective-intelligence-zenodo-v1/"
            "PREPUBLICATION_RETURN_RECEIPT.json"
        ),
        "7d056139f355e1b81bdf040ff674e2fc0c69d66f3477f87eb38d7d6ff48513b9",
    ),
}
EXPECTED_STATEMENT = (
    "AUTHORIZE_EXACT_UPLOAD "
    f"authorization_id={AUTHORIZATION_ID} "
    f"publication_id={PUBLICATION_ID} "
    "return_sha256=7d056139f355e1b81bdf040ff674e2fc0c69d66f3477f87eb38d7d6ff48513b9 "
    "metadata_sha256=acebc139ecda233dc9b47fdf565f2fbbeea8340ea045cc842d363e7f3a6e12f6 "
    "machine_proof_sha256=4fa477b9b2160382c1c231911e0bae20db05471599352c247a390672bb4fd5cc"
)


class BoundaryError(RuntimeError):
    """A deterministic pre-effect gate is not satisfied."""


def fail(message: str) -> NoReturn:
    raise BoundaryError(message)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read canonical JSON {path}: {type(exc).__name__}")
    if not isinstance(value, dict):
        fail(f"canonical JSON is not an object: {path}")
    return value


def sha256_file(path: pathlib.Path) -> str:
    try:
        data = path.read_bytes()
    except OSError as exc:
        fail(f"cannot read candidate file {path}: {type(exc).__name__}")
    return hashlib.sha256(data).hexdigest()


def validate_authorization(root: pathlib.Path) -> dict[str, Any]:
    value = load_json(root / AUTHORIZATION_PATH)
    authorization = value.get("authorization")
    completion = value.get("completion_claims")
    candidate = value.get("candidate")
    if value.get("schema") != "qikvrt_zenodo_mutation_authorization_request_v1":
        fail("AUTHORIZATION_SCHEMA_MISMATCH")
    if value.get("publication_id") != PUBLICATION_ID:
        fail("AUTHORIZATION_PUBLICATION_ID_MISMATCH")
    if value.get("state") != "AUTHORIZED_PENDING_ZENODO_MUTATION":
        fail("AUTHORIZATION_STATE_NOT_PENDING_MUTATION")
    if not isinstance(authorization, dict) or authorization.get("authorized") is not True:
        fail("EXACT_OWNER_AUTHORIZATION_NOT_ESTABLISHED")
    if authorization.get("authorized_by") != "Ingolf Lohmann":
        fail("AUTHORIZATION_PRINCIPAL_MISMATCH")
    if authorization.get("exact_statement_observed") != EXPECTED_STATEMENT:
        fail("AUTHORIZATION_STATEMENT_MISMATCH")
    if value.get("required_exact_statement") != EXPECTED_STATEMENT:
        fail("REQUIRED_AUTHORIZATION_STATEMENT_MISMATCH")
    if not isinstance(completion, dict):
        fail("AUTHORIZATION_COMPLETION_CLAIMS_MISSING")
    if completion.get("zenodo_mutation_authorized") is not True:
        fail("ZENODO_MUTATION_NOT_AUTHORIZED")
    if completion.get("zenodo_publication_complete") is not False:
        fail("AUTHORIZATION_FALSE_PUBLICATION_COMPLETION")
    if not isinstance(candidate, dict):
        fail("AUTHORIZATION_CANDIDATE_BINDING_MISSING")
    expected = {
        "machine_proof_sha256": CANDIDATE_HASHES["machine_proof"][1],
        "metadata_sha256": CANDIDATE_HASHES["metadata"][1],
        "prepublication_return_receipt_sha256": CANDIDATE_HASHES[
            "return_receipt"
        ][1],
    }
    for key, expected_value in expected.items():
        if candidate.get(key) != expected_value:
            fail(f"AUTHORIZATION_{key.upper()}_MISMATCH")
    return value


def validate_candidate_hashes(root: pathlib.Path) -> None:
    for label, (relative, expected) in CANDIDATE_HASHES.items():
        observed = sha256_file(root / relative)
        if observed != expected:
            fail(f"{label.upper()}_SHA256_MISMATCH")


def validate_manifest(root: pathlib.Path) -> dict[str, Any]:
    path = root / MANIFEST_PATH
    if not path.is_file():
        fail("PUBLICATION_MANIFEST_NOT_MATERIALIZED")
    try:
        manifest = publisher.load_manifest(path, root)
    except Exception as exc:  # hardened publisher supplies the exact detail
        fail(f"PUBLICATION_MANIFEST_REJECTED:{type(exc).__name__}")
    if manifest.get("schema") != publisher.SCHEMA_V2:
        fail("PUBLICATION_MANIFEST_NOT_V2")
    if manifest.get("repository") != REPOSITORY:
        fail("PUBLICATION_MANIFEST_REPOSITORY_MISMATCH")
    authorization = manifest.get("owner_authorization")
    if not isinstance(authorization, dict):
        fail("PUBLICATION_MANIFEST_OWNER_AUTHORIZATION_MISSING")
    if authorization.get("publication_id") != PUBLICATION_ID:
        fail("PUBLICATION_MANIFEST_PUBLICATION_ID_MISMATCH")
    if authorization.get("authorization_id") != AUTHORIZATION_ID:
        fail("PUBLICATION_MANIFEST_AUTHORIZATION_ID_MISMATCH")
    return manifest


def preflight(root: pathlib.Path) -> dict[str, Any]:
    validate_authorization(root)
    validate_candidate_hashes(root)
    manifest = validate_manifest(root)
    return {
        "authorization_id": AUTHORIZATION_ID,
        "manifest": MANIFEST_PATH.as_posix(),
        "publication_id": PUBLICATION_ID,
        "repository": REPOSITORY,
        "state": "READY_FOR_SEPARATE_EXTERNAL_DISPATCH",
        "source_head": manifest["source_head"],
    }


def require_execution_inputs(args: argparse.Namespace) -> None:
    if args.publication_id != PUBLICATION_ID:
        fail("DISPATCH_PUBLICATION_ID_MISMATCH")
    if args.authorization_id != AUTHORIZATION_ID:
        fail("DISPATCH_AUTHORIZATION_ID_MISMATCH")
    if args.confirm != CONFIRMATION:
        fail("DISPATCH_CONFIRMATION_MISMATCH")
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        fail("DISPATCH_REPOSITORY_MISMATCH")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        fail("DISPATCH_NOT_ON_AUTHORITY_MAIN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--publication-id")
    parser.add_argument("--authorization-id")
    parser.add_argument("--confirm")
    args = parser.parse_args(argv)
    root = pathlib.Path.cwd().resolve()
    try:
        result = preflight(root)
        if args.check:
            print(json.dumps(result, sort_keys=True))
            return 0
        require_execution_inputs(args)
        evidence = publisher.publish(root / MANIFEST_PATH, root)
        print(
            json.dumps(
                {
                    "doi": evidence["doi"],
                    "publication_id": PUBLICATION_ID,
                    "record_id": evidence["record_id"],
                    "state": "PUBLIC_VERIFIED",
                },
                sort_keys=True,
            )
        )
        return 0
    except BoundaryError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
