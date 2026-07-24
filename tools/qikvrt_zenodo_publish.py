#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Generic fail-closed Zenodo publication capability.

The implementation contains no document-, release-, record- or DOI-specific
constants. Effect-bearing identity is supplied by a repository-controlled JSON
manifest. Each file is bound to its Git blob SHA-1; byte size, MD5 and SHA-256
are derived locally and then independently verified by the hardened shared
Zenodo transport before and after publication.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import sys
from collections.abc import Mapping
from typing import Any, NoReturn

try:
    from tools import qikvrt_zenodo_actions as zenodo
except ModuleNotFoundError:
    import qikvrt_zenodo_actions as zenodo  # type: ignore[no-redef]

SCHEMA = "qikvrt_zenodo_publication_manifest_v1"
EVIDENCE_SCHEMA = "qikvrt_zenodo_publication_evidence_v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
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


def _safe_relative(
    root: pathlib.Path, raw: Any, where: str, *, must_exist: bool
) -> pathlib.Path:
    if not isinstance(raw, str) or not raw:
        _fail(f"{where} must be a non-empty repository-relative path")
    try:
        return zenodo._relative_path(root, raw, must_exist=must_exist)
    except zenodo.ZenodoError as exc:
        _fail(f"{where}: {exc}")


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


def load_manifest(path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    value, raw = zenodo._load_json_file(path)
    zenodo._check_exact_keys(
        value,
        {"schema", "state", "confirm", "repository", "metadata", "files", "evidence_path"},
        "manifest",
    )
    if value["schema"] != SCHEMA:
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
    return {
        "schema": SCHEMA,
        "repository": repository,
        "metadata": metadata,
        "files": files,
        "evidence_path": evidence_path,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def verify_files(
    manifest: Mapping[str, Any], root: pathlib.Path, token: str
) -> dict[tuple[str, str], bytes]:
    verified: dict[tuple[str, str], bytes] = {}
    for entry in manifest["files"]:
        shared_entry = {key: entry[key] for key in ("path", "name", "size", "md5", "sha256")}
        verified[("publication", entry["name"])] = zenodo._file_bytes(
            root, shared_entry, token
        )
    return verified


def _shared_entries(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: entry[key] for key in ("path", "name", "size", "md5", "sha256")}
        for entry in files
    ]


def publish(manifest_path: pathlib.Path, root: pathlib.Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path, root)
    evidence_path = manifest["evidence_path"]
    if evidence_path.exists():
        _fail("publication evidence already exists; refusing duplicate remote mutation")
    token = os.environ.get(zenodo.TOKEN_ENVIRONMENT_VARIABLE, "")
    client = zenodo.ZenodoClient(
        token,
        os.environ.get("ZENODO_API_BASE", zenodo.DEFAULT_BASE_URL),
    )
    verified = verify_files(manifest, root, token)
    metadata = manifest["metadata"]
    entries = _shared_entries(manifest["files"])
    draft = client.create_paper(metadata)
    record_id = zenodo._record_id(draft, "generic publication deposition")
    doi = zenodo._doi_from_deposition(draft, "generic publication deposition")
    client.prepare_draft("publication", record_id, metadata, entries, verified, doi)
    published = client.publish_and_poll(record_id, metadata, entries, doi, False)
    links = published.get("links") if isinstance(published.get("links"), dict) else {}
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "state": "published",
        "record_id": record_id,
        "doi": doi,
        "conceptdoi": published.get("conceptdoi")
        or published.get("metadata", {}).get("conceptdoi"),
        "title": metadata["title"],
        "version": metadata["version"],
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": manifest["manifest_sha256"],
        "files": manifest["files"],
        "record_url": links.get("html") or f"https://zenodo.org/records/{record_id}",
        "repository": manifest["repository"],
        "repository_commit": os.environ.get("GITHUB_SHA", "unavailable"),
    }
    zenodo._atomic_json(evidence_path, evidence, token)
    return evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish a Git-blob-bound repository manifest to Zenodo"
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
