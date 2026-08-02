#!/usr/bin/env python3
"""Materialize the three exact VRTCore Zenodo-v2 publication controls.

This module never contacts Zenodo and never exposes authorization nonces.  It
turns the natural-person decisions returned in the ChatGPT conversation into
repository-bound owner authorization and publication-manifest objects, then
passes every object through the active generic publisher's read-only gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
from typing import Any

from tools import qikvrt_zenodo_publish as publish
from tools import qikvrt_zenodo_machine_proof as machine_proof


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE_HEAD = "4d00723c7f6f52f1b2b279fd91f902647e0547cc"
REPOSITORY = "Goldkelch/qik-vrt"
PRINCIPAL = {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}
LICENSE = {
    "classification": "owner_effect_authorization",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}


PROFILES: dict[str, dict[str, str | int]] = {
    "h3": {
        "authorization_id": "qikvrt-vrtcore-zenodo-v1-8b3f8cdc",
        "publication_id": "qikvrt-causality-is-relation-vrtcore-v1",
        "return_sha256": "3c964218535908de94cd54decf7cb8d46706f910040ea520985cdc76cfa78098",
        "metadata_sha256": "2e81fd54ba4ee37db8461bab6f0f09e49bad2a0cd9a5102ad6747f16c8a2f202",
        "machine_proof_sha256": "ccdc516209ea4b3106976470c244c7c1e1b965a30be16f7a832d3d95e03b1a06",
        "bundle": "docs/publications/2026-08-02-causality-is-relation-vrtcore/MACHINE_PROOF_BUNDLE.json",
        "metadata": "docs/publications/2026-08-02-causality-is-relation-vrtcore/ZENODO_METADATA.json",
        "control": "release/vrtcore-relational-h3-publication-2026-08-02",
        "upload_count": 38,
    },
    "h5": {
        "authorization_id": "qikvrt-vrtcore-smg-h5-zenodo-v1-8d97a4c0",
        "publication_id": "qikvrt-vrtcore-smg-h5-v1",
        "return_sha256": "4004d5edfbd9a782af146276bdf6e4c86a646184bb2e05f04229a4a2cda10a5b",
        "metadata_sha256": "b6648a3626e9c28df3bf79e4bd5b06db43b87ac0342f591a8ce314cbba8c68b6",
        "machine_proof_sha256": "8d97a4c0fbdad7766dde70da6c54723dda0c5169329acb08ab1c83c2feef6503",
        "bundle": "release/vrtcore-smg-h5-zenodo-v2/MACHINE_PROOF_BUNDLE.json",
        "metadata": "release/vrtcore-smg-h5-zenodo-v2/ZENODO_METADATA.json",
        "control": "release/vrtcore-smg-h5-publication-2026-08-02",
        "upload_count": 35,
    },
    "h6": {
        "authorization_id": "qikvrt-vrtcore-virtual-sphere-h6-zenodo-v1-d033d6b2",
        "publication_id": "qikvrt-vrtcore-virtual-sphere-h6-v1",
        "return_sha256": "03fb1cb2debc036593baadc2a6797944d7bb01ddfc1d6f9b8f6c162d0a023fc2",
        "metadata_sha256": "07b2896f9da6f6765cc1760c03fbc89670e4d3a21a2dc86141921a7e3802b1a6",
        "machine_proof_sha256": "d033d6b25f6ad7cc3a64177b1ec6ab46fb26d2ec2366b3ebdb03dc04b3fc0aa3",
        "bundle": "release/vrtcore-virtual-sphere-h6-zenodo-v2/MACHINE_PROOF_BUNDLE.json",
        "metadata": "release/vrtcore-virtual-sphere-h6-zenodo-v2/ZENODO_METADATA.json",
        "control": "release/vrtcore-virtual-sphere-h6-publication-2026-08-02",
        "upload_count": 34,
    },
}


def block(message: str) -> None:
    raise SystemExit("BLOCK: " + message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw: bytes) -> str:
    prefix = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(prefix + raw).hexdigest()  # noqa: S324 - Git identity


def identity(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        block("required regular file is absent: " + relative)
    raw = path.read_bytes()
    return {
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha": git_blob_sha1(raw),
    }


def load_json(relative: str) -> dict[str, Any]:
    try:
        value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        block(f"cannot read {relative}: {exc}")
    if not isinstance(value, dict):
        block(relative + " must contain a JSON object")
    return value


def git_source_blob(relative: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{SOURCE_HEAD}:{relative}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        block("source head lacks " + relative)
    return completed.stdout.strip()


def upload_files(profile: dict[str, str | int], bundle: dict[str, Any]) -> list[dict[str, str]]:
    raw_entries = [
        *bundle["candidate"]["files"],
        *bundle["artifacts"],
        {
            "path": profile["bundle"],
            "name": pathlib.PurePosixPath(str(profile["bundle"])).name,
        },
    ]
    files: list[dict[str, str]] = []
    names: set[str] = set()
    paths: set[str] = set()
    for raw_entry in raw_entries:
        relative = raw_entry["path"]
        name = raw_entry.get("name", pathlib.PurePosixPath(relative).name)
        observed = identity(relative)
        listed_sha256 = raw_entry.get("sha256")
        listed_blob = raw_entry.get("git_blob_sha1")
        if listed_sha256 is not None and listed_sha256 != observed["sha256"]:
            block("bundle SHA-256 differs for " + relative)
        if listed_blob is not None and listed_blob != observed["git_blob_sha"]:
            block("bundle Git blob differs for " + relative)
        if git_source_blob(relative) != observed["git_blob_sha"]:
            block("source-head Git blob differs for " + relative)
        if name in names or relative in paths:
            block("duplicate upload name or path: " + relative)
        names.add(name)
        paths.add(relative)
        files.append(
            {
                "path": relative,
                "name": name,
                "git_blob_sha": observed["git_blob_sha"],
            }
        )
    if len(files) != profile["upload_count"]:
        block("upload count differs for " + str(profile["publication_id"]))
    return files


def exact_statement(profile: dict[str, str | int]) -> str:
    return publish._canonical_authorization_statement(
        str(profile["authorization_id"]),
        str(profile["publication_id"]),
        str(profile["return_sha256"]),
        str(profile["metadata_sha256"]),
        str(profile["machine_proof_sha256"]),
    )


def read_preserved_event(auth_path: pathlib.Path) -> tuple[str, str]:
    if not auth_path.is_file() or auth_path.is_symlink():
        block(
            "owner authorization must already exist; "
            "replacement nonce generation is forbidden"
        )
    value = json.loads(auth_path.read_text(encoding="utf-8"))
    return value["nonce"], value["authorization_event"]["authorized_at"]


def build_profile(name: str, profile: dict[str, str | int]) -> tuple[pathlib.Path, pathlib.Path, bytes, bytes]:
    bundle_path = str(profile["bundle"])
    metadata_path = str(profile["metadata"])
    bundle = load_json(bundle_path)
    metadata = load_json(metadata_path)
    if bundle.get("publication_id") != profile["publication_id"]:
        block(name + " publication ID differs in machine proof")
    bundle_identity = identity(bundle_path)
    if bundle_identity["sha256"] != profile["machine_proof_sha256"]:
        block(name + " machine-proof SHA-256 differs from owner statement")
    if canonical_json_sha256(metadata) != profile["metadata_sha256"]:
        block(name + " canonical metadata SHA-256 differs from owner statement")
    return_path = bundle["prepublication_return"]["receipt_path"]
    return_identity = identity(return_path)
    if return_identity["sha256"] != profile["return_sha256"]:
        block(name + " return SHA-256 differs from owner statement")

    files = upload_files(profile, bundle)
    control = ROOT / str(profile["control"])
    auth_path = control / "OWNER_ZENODO_AUTHORIZATION.json"
    manifest_path = control / "publish-request.json"
    evidence_relative = (pathlib.PurePosixPath(str(profile["control"])) / "zenodo-publication.json").as_posix()
    nonce, authorized_at = read_preserved_event(auth_path)
    if len(nonce) != 64 or nonce == "0" * 64:
        block(name + " nonce is structurally invalid")
    statement = exact_statement(profile)
    normalized_files = []
    for entry in files:
        observed = identity(entry["path"])
        normalized_files.append(
            {
                "path": entry["path"],
                "name": entry["name"],
                "bytes": observed["bytes"],
                "sha256": observed["sha256"],
                "git_blob_sha": observed["git_blob_sha"],
            }
        )
    authorization = {
        "_license": LICENSE,
        "schema": publish.OWNER_AUTHORIZATION_SCHEMA,
        "authorization_id": profile["authorization_id"],
        "nonce": nonce,
        "single_use": True,
        "single_use_scope": publish.SINGLE_USE_SCOPE,
        "principal": PRINCIPAL,
        "publication_id": profile["publication_id"],
        "repository": REPOSITORY,
        "source_head": SOURCE_HEAD,
        "candidate_return_receipt": return_identity,
        "canonical_metadata_sha256": profile["metadata_sha256"],
        "uploads": normalized_files,
        "machine_proof": bundle_identity,
        "authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS),
        "publication_evidence_path": evidence_relative,
        "authorization_event": {
            "channel": "ChatGPT conversation exact hash-bound owner authorization",
            "authorized_at": authorized_at,
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": statement,
            "statement_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
            "principal": PRINCIPAL,
            "candidate_return_receipt_sha256": profile["return_sha256"],
        },
    }
    authorization_raw = json_bytes(authorization)
    authorization_identity = {
        "path": auth_path.relative_to(ROOT).as_posix(),
        "bytes": len(authorization_raw),
        "sha256": hashlib.sha256(authorization_raw).hexdigest(),
        "git_blob_sha": git_blob_sha1(authorization_raw),
    }
    manifest = {
        "schema": publish.SCHEMA_V2,
        "state": "publish",
        "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
        "repository": REPOSITORY,
        "source_head": SOURCE_HEAD,
        "metadata": metadata,
        "files": files,
        "machine_proof": {
            "path": bundle_path,
            "git_blob_sha": bundle_identity["git_blob_sha"],
            "policy_id": machine_proof.POLICY_ID,
        },
        "owner_authorization": authorization_identity,
        "evidence_path": evidence_relative,
    }
    return auth_path, manifest_path, authorization_raw, json_bytes(manifest)


def emit(path: pathlib.Path, expected: bytes, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_bytes() != expected:
            block("generated control differs: " + path.relative_to(ROOT).as_posix())
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != expected:
        block("refusing to overwrite changed control: " + path.relative_to(ROOT).as_posix())
    path.write_bytes(expected)


def materialize(check: bool) -> None:
    seen_ids: set[str] = set()
    for name, profile in PROFILES.items():
        authorization_id = str(profile["authorization_id"])
        if authorization_id in seen_ids:
            block("duplicate authorization ID")
        seen_ids.add(authorization_id)
        auth_path, manifest_path, auth_raw, manifest_raw = build_profile(name, profile)
        emit(auth_path, auth_raw, check)
        emit(manifest_path, manifest_raw, check)
        normalized = publish.load_manifest(manifest_path, ROOT)
        if normalized["source_head"] != SOURCE_HEAD:
            block(name + " normalized source head differs")
        if normalized["owner_authorization"]["authorization_id"] != authorization_id:
            block(name + " normalized authorization ID differs")
        print(
            "PASS "
            + ("verified" if check else "materialized")
            + f" {name.upper()} controls: uploads={len(normalized['files'])} "
            + f"source_head={SOURCE_HEAD} authorization_id={authorization_id}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    materialize(args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
