#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Derive candidate-specific Zenodo v2 controls under the standing I/O delegation.

Input is a repository-bound candidate control JSON. This command performs no
network access and no publication. It may materialize an exact natural-person
single-use authorization and the corresponding v2 manifest only after machine
proof and prepublication-return bytes are already present and validated.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import secrets
import subprocess
import sys
from typing import Any

from tools import qikvrt_zenodo_machine_proof as machine_proof
from tools import qikvrt_zenodo_publish as publish

ROOT = pathlib.Path(__file__).resolve().parents[1]
DELEGATION = ROOT / "state/authorization/delegations/OWNER_AI_IO_ROUND_TRIP_AUTOPUBLISH_V1.json"
SCHEMA = "qikvrt_io_zenodo_candidate_control_v1"
PRINCIPAL = {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}
LICENSE = {
    "classification": "owner_effect_authorization",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}


class AuthorizationBlock(RuntimeError):
    pass


def load(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuthorizationBlock(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuthorizationBlock(f"{path} must contain a JSON object")
    return value


def git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise AuthorizationBlock("cannot resolve Git HEAD")
    return result.stdout.strip()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()  # noqa: S324


def identity(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise AuthorizationBlock("required regular file absent: " + relative)
    raw = path.read_bytes()
    return {"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "git_blob_sha": git_blob(raw)}


def safe_relative(raw: str) -> pathlib.Path:
    value = pathlib.PurePosixPath(raw)
    if value.is_absolute() or ".." in value.parts or not value.parts:
        raise AuthorizationBlock("unsafe repository-relative path")
    return ROOT / value


def derive(candidate_path: pathlib.Path, check: bool) -> dict[str, Any]:
    delegation = load(DELEGATION)
    if delegation.get("schema") != "qikvrt_owner_ai_io_round_trip_autopublish_v1" or delegation.get("state") != "ACTIVE":
        raise AuthorizationBlock("standing I/O publication delegation is not active")
    candidate = load(candidate_path)
    if candidate.get("schema") != SCHEMA:
        raise AuthorizationBlock("candidate control schema mismatch")
    if candidate.get("repository") != "Goldkelch/qik-vrt":
        raise AuthorizationBlock("candidate repository differs from Authority")
    if candidate.get("principal") != PRINCIPAL:
        raise AuthorizationBlock("candidate principal differs from standing natural-person principal")

    source_head = candidate.get("source_head")
    if not isinstance(source_head, str) or len(source_head) != 40:
        raise AuthorizationBlock("candidate source_head is invalid")
    publication_id = candidate.get("publication_id")
    if not isinstance(publication_id, str) or not publication_id:
        raise AuthorizationBlock("publication_id is missing")

    metadata = publish._validate_metadata(candidate.get("metadata"))
    raw_files = candidate.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise AuthorizationBlock("candidate files must be non-empty")
    files = [publish._materialize_file(value, ROOT, f"candidate.files[{index}]") for index, value in enumerate(raw_files)]

    proof_raw = candidate.get("machine_proof")
    proof = publish._validate_machine_proof(proof_raw, ROOT, files)
    if proof["publication_id"] != publication_id:
        raise AuthorizationBlock("machine proof publication_id differs")
    return_receipt = proof["candidate_return_receipt"]
    if not isinstance(return_receipt, dict) or not return_receipt.get("sha256"):
        raise AuthorizationBlock("prepublication return receipt missing")

    evidence_relative = candidate.get("evidence_path")
    if not isinstance(evidence_relative, str) or pathlib.PurePosixPath(evidence_relative).name != "zenodo-publication.json":
        raise AuthorizationBlock("evidence_path must end in zenodo-publication.json")
    authorization_relative = candidate.get("authorization_path")
    manifest_relative = candidate.get("manifest_path")
    if not isinstance(authorization_relative, str) or not isinstance(manifest_relative, str):
        raise AuthorizationBlock("authorization_path and manifest_path are required")
    auth_path = safe_relative(authorization_relative)
    manifest_path = safe_relative(manifest_relative)

    canonical_metadata_sha256 = hashlib.sha256(publish.zenodo._json_bytes(metadata)).hexdigest()
    proof_identity = {key: proof[key] for key in ("path", "bytes", "sha256", "git_blob_sha")}
    authorization_id = "qikvrt-auto-" + hashlib.sha256((publication_id + ":" + proof_identity["sha256"]).encode("utf-8")).hexdigest()[:32]
    statement = publish._canonical_authorization_statement(
        authorization_id,
        publication_id,
        return_receipt["sha256"],
        canonical_metadata_sha256,
        proof_identity["sha256"],
    )

    preserved: dict[str, Any] | None = None
    if auth_path.is_file():
        preserved = load(auth_path)
        if preserved.get("authorization_id") != authorization_id:
            raise AuthorizationBlock("existing authorization belongs to a different exact candidate")
    nonce = preserved.get("nonce") if preserved else secrets.token_hex(32)
    authorized_at = preserved.get("authorization_event", {}).get("authorized_at") if preserved else None
    if not isinstance(authorized_at, str):
        authorized_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    uploads = [
        {"path": entry["path"], "name": entry["name"], "bytes": entry["size"], "sha256": entry["sha256"], "git_blob_sha": entry["git_blob_sha"]}
        for entry in files
    ]
    authorization = {
        "_license": LICENSE,
        "schema": publish.OWNER_AUTHORIZATION_SCHEMA,
        "authorization_id": authorization_id,
        "nonce": nonce,
        "single_use": True,
        "single_use_scope": publish.SINGLE_USE_SCOPE,
        "principal": PRINCIPAL,
        "publication_id": publication_id,
        "repository": "Goldkelch/qik-vrt",
        "source_head": source_head,
        "candidate_return_receipt": return_receipt,
        "canonical_metadata_sha256": canonical_metadata_sha256,
        "uploads": uploads,
        "machine_proof": proof_identity,
        "authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS),
        "publication_evidence_path": evidence_relative,
        "authorization_event": {
            "channel": "Repository-bound Product Owner standing delegation OWNER-AI-IO-ROUND-TRIP-AUTOPUBLISH-V1",
            "authorized_at": authorized_at,
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": statement,
            "statement_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
            "principal": PRINCIPAL,
            "candidate_return_receipt_sha256": return_receipt["sha256"]
        }
    }
    auth_raw = json_bytes(authorization)
    auth_identity = {"path": authorization_relative, "bytes": len(auth_raw), "sha256": hashlib.sha256(auth_raw).hexdigest(), "git_blob_sha": git_blob(auth_raw)}
    manifest = {
        "schema": publish.SCHEMA_V2,
        "state": "publish",
        "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
        "repository": "Goldkelch/qik-vrt",
        "source_head": source_head,
        "metadata": metadata,
        "files": [{"path": entry["path"], "name": entry["name"], "git_blob_sha": entry["git_blob_sha"]} for entry in files],
        "machine_proof": proof_raw,
        "owner_authorization": auth_identity,
        "evidence_path": evidence_relative
    }
    manifest_raw = json_bytes(manifest)

    for path, expected in ((auth_path, auth_raw), (manifest_path, manifest_raw)):
        if check:
            if not path.is_file() or path.read_bytes() != expected:
                raise AuthorizationBlock("derived control differs: " + path.relative_to(ROOT).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != expected:
                raise AuthorizationBlock("refusing to overwrite changed exact control: " + path.relative_to(ROOT).as_posix())
            path.write_bytes(expected)
    return {
        "state": "EXACT_SINGLE_USE_AUTHORIZATION_READY",
        "publication_id": publication_id,
        "source_head": source_head,
        "authorization_path": authorization_relative,
        "manifest_path": manifest_relative,
        "authorization_id": authorization_id,
        "machine_proof_sha256": proof_identity["sha256"],
        "candidate_return_receipt_sha256": return_receipt["sha256"],
        "network_effect": False
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        path = safe_relative(args.candidate)
        result = derive(path, args.check)
    except (AuthorizationBlock, OSError, ValueError, publish.zenodo.ZenodoError, machine_proof.ProofGateError) as exc:
        print(json.dumps({"state": "BLOCK", "detail": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
