#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize the exact retrospective-proof-corpus Zenodo controls.

This is an offline control constructor, not a publisher.  It accepts one
explicit, strict-JSON ``OWNER_AUTHORIZATION_EVENT`` from the process
environment and otherwise fails before creating a control directory or file.
The event supplies the already-frozen single-use nonce; this tool neither
generates nor replaces owner authorization.

All 65 upload path/name pairs come, in order, from the frozen claim matrix's
``upload_contract``.  Each pair is resolved by exact path to one and only one
candidate, proof-artifact or proof-bundle identity.  Basename inference is
deliberately absent.
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import os
import pathlib
import re
import stat
import subprocess
import sys
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # ``python -I -S`` intentionally omits the repository root.  Add only the
    # exact root containing this controller so its reviewed local modules can
    # be loaded without consulting user or site packages.
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_retrospective_proof_corpus_zenodo_candidate as candidate
from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_machine_proof as machine_proof
from tools import qikvrt_zenodo_publish as publish


SOURCE_HEAD = "035642a660583113ec739d90577193ccb5a08889"
REPOSITORY = "Goldkelch/qik-vrt"
PUBLICATION_ID = "qikvrt-retrospective-proof-corpus-2026-07-28-v3"
AUTHORIZATION_ID = (
    "qikvrt-retrospective-proof-corpus-v3-rebuild-20260803t094446z"
)
OWNER_AUTHORIZATION_EVENT_ENV = "OWNER_AUTHORIZATION_EVENT"

RETURN_SHA256 = (
    "46c57378a6708df379768f943a99905cde3da4c4a11220f9a177e9bc968d3968"
)
METADATA_SHA256 = (
    "4bb6abea1f226f3950337ee3585abd1ba5d52f731a93f25fabfc2722f5b170de"
)
MACHINE_PROOF_SHA256 = (
    "cfe9ae60e3da81a6427c96399bd70299c74f12999dc4371809b879f5a5630be1"
)
PREPUBLICATION_RETURNED_AT = "2026-08-03T09:44:46Z"
UPLOAD_CONTRACT_SHA256 = (
    "3965b4167094ff47de60fc32023ac74ea1598148ab381885be8da3db4c427609"
)
EXPECTED_UPLOADS = 65
MAX_EVENT_BYTES = 16 * 1024
HEX64 = re.compile(r"^[0-9a-f]{64}$")

CONTROL_REL = pathlib.PurePosixPath(
    "release/zenodo-corpus-proof-publication-2026-08-03"
)
AUTHORIZATION_BASENAME = "OWNER_ZENODO_AUTHORIZATION.json"
MANIFEST_BASENAME = "publish-request.json"
EVIDENCE_BASENAME = "zenodo-publication.json"

PRINCIPAL = {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}
LICENSE = {
    "classification": "owner_effect_authorization",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}
EVENT_SCHEMA = "qikvrt_repository_recorded_owner_authorization_event_v1"
EVENT_KEYS = {
    "schema",
    "authorization_id",
    "publication_id",
    "decision",
    "exact_statement",
    "return_sha256",
    "metadata_sha256",
    "machine_proof_sha256",
    "authorized_at",
    "repository_recorded_conversation_assertion",
    "independent_external_proof",
    "nonce",
}


class CorpusPublicationControlError(RuntimeError):
    """Fail-closed publication-control construction error."""


def fail(message: str) -> NoReturn:
    raise CorpusPublicationControlError(message)


def exact_statement(
    authorization_id: str = AUTHORIZATION_ID,
    publication_id: str = PUBLICATION_ID,
    return_sha256: str = RETURN_SHA256,
    metadata_sha256: str = METADATA_SHA256,
    machine_proof_sha256: str = MACHINE_PROOF_SHA256,
) -> str:
    return publish._canonical_authorization_statement(
        authorization_id,
        publication_id,
        return_sha256,
        metadata_sha256,
        machine_proof_sha256,
    )


def _event_timestamp(value: Any) -> str:
    if not isinstance(value, str) or candidate.UTC_TIMESTAMP.fullmatch(value) is None:
        fail("authorization event authorized_at must use UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        fail("authorization event authorized_at is not a real UTC timestamp")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        fail("authorization event authorized_at is not canonical")
    return value


def parse_authorization_event(raw_text: str | None) -> dict[str, Any]:
    """Parse and validate the explicit external event before any filesystem write."""
    if raw_text is None or raw_text == "":
        fail(
            "explicit strict JSON OWNER_AUTHORIZATION_EVENT is required; "
            "owner authorization has not been assumed"
        )
    if not isinstance(raw_text, str):
        fail("OWNER_AUTHORIZATION_EVENT must be text")
    try:
        raw = raw_text.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        fail(f"OWNER_AUTHORIZATION_EVENT is not strict UTF-8 text: {exc}")
    if len(raw) > MAX_EVENT_BYTES:
        fail(f"OWNER_AUTHORIZATION_EVENT exceeds {MAX_EVENT_BYTES} bytes")
    try:
        value = candidate.parse_json_bytes(raw, OWNER_AUTHORIZATION_EVENT_ENV)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))
    if set(value) != EVENT_KEYS:
        fail("OWNER_AUTHORIZATION_EVENT keys differ from the exact event contract")
    expected_statement = exact_statement()
    expected = {
        "schema": EVENT_SCHEMA,
        "authorization_id": AUTHORIZATION_ID,
        "publication_id": PUBLICATION_ID,
        "decision": "AUTHORIZE_EXACT_UPLOAD",
        "exact_statement": expected_statement,
        "return_sha256": RETURN_SHA256,
        "metadata_sha256": METADATA_SHA256,
        "machine_proof_sha256": MACHINE_PROOF_SHA256,
        "repository_recorded_conversation_assertion": True,
        "independent_external_proof": False,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            fail(f"OWNER_AUTHORIZATION_EVENT {key} differs from the frozen candidate")
    authorized_at = _event_timestamp(value.get("authorized_at"))
    if authorized_at < PREPUBLICATION_RETURNED_AT:
        fail("OWNER_AUTHORIZATION_EVENT authorized_at predates candidate return")
    nonce = value.get("nonce")
    if (
        not isinstance(nonce, str)
        or HEX64.fullmatch(nonce) is None
        or nonce == "0" * 64
    ):
        fail("OWNER_AUTHORIZATION_EVENT nonce must be a fresh non-zero lowercase 256-bit value")
    return {**value, "authorized_at": authorized_at, "nonce": nonce}


def _run_git(arguments: Sequence[str]) -> str:
    environment = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"cannot execute read-only Git source gate: {exc}")
    if completed.returncode != 0:
        fail("read-only Git source gate rejected " + " ".join(arguments[:2]))
    try:
        return completed.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeError:
        fail("read-only Git source gate returned non-UTF-8 output")


def verify_source_blob(relative: str, observed_blob: str) -> None:
    safe = candidate.normalize_repo_relative(relative, "source-head upload path")
    source_blob = _run_git(["rev-parse", "--verify", f"{SOURCE_HEAD}:{safe}"])
    if source_blob != observed_blob:
        fail("source-head Git blob differs for " + safe)


def verify_source_head() -> None:
    resolved = _run_git(["rev-parse", "--verify", f"{SOURCE_HEAD}^{{commit}}"])
    if resolved != SOURCE_HEAD:
        fail("SOURCE_HEAD does not resolve to the exact frozen candidate commit")


def _strict_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        return candidate.load_json(path, label)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))


def _identity(path: pathlib.Path) -> dict[str, Any]:
    try:
        return candidate.identity(path)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))


def _generic_identity(observed: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": observed["path"],
        "bytes": observed["bytes"],
        "sha256": observed["sha256"],
        "git_blob_sha": observed["git_blob_sha1"],
    }


def _exact_identity_match(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
    *,
    require_bytes: bool,
    label: str,
) -> None:
    keys = ["path", "sha256", "git_blob_sha1"]
    if require_bytes:
        keys.insert(1, "bytes")
    if any(expected.get(key) != observed.get(key) for key in keys):
        fail(label + " identity differs from current repository bytes")


def load_upload_contract() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, str]]
]:
    """Resolve the 65 ordered matrix mappings to exact bundle roles/identities."""
    verify_source_head()
    matrix = _strict_json(candidate.CLAIM_MATRIX_PATH, "corpus claim matrix")
    metadata = _strict_json(candidate.METADATA_PATH, "canonical Zenodo metadata")
    bundle = _strict_json(candidate.PROOF_BUNDLE_PATH, "machine-proof bundle")
    return_receipt = _strict_json(
        candidate.RETURN_RECEIPT_PATH,
        "prepublication return receipt",
    )

    if matrix.get("publication_id") != PUBLICATION_ID:
        fail("corpus claim matrix publication_id differs")
    if bundle.get("publication_id") != PUBLICATION_ID:
        fail("machine-proof bundle publication_id differs")
    return_identity = _identity(candidate.RETURN_RECEIPT_PATH)
    bundle_identity = _identity(candidate.PROOF_BUNDLE_PATH)
    if return_identity["sha256"] != RETURN_SHA256:
        fail("prepublication return receipt SHA-256 differs from the owner statement")
    if candidate.canonical_json_sha256(metadata) != METADATA_SHA256:
        fail("canonical metadata SHA-256 differs from the owner statement")
    if bundle_identity["sha256"] != MACHINE_PROOF_SHA256:
        fail("machine-proof SHA-256 differs from the owner statement")

    contract = matrix.get("upload_contract")
    if not isinstance(contract, dict) or set(contract) != {
        "entry_count",
        "ordered_entries",
        "ordered_entries_canonical_sha256",
    }:
        fail("matrix upload_contract keys differ")
    entries = contract.get("ordered_entries")
    if (
        contract.get("entry_count") != EXPECTED_UPLOADS
        or not isinstance(entries, list)
        or len(entries) != EXPECTED_UPLOADS
        or contract.get("ordered_entries_canonical_sha256")
        != UPLOAD_CONTRACT_SHA256
        or candidate.canonical_json_sha256(entries) != UPLOAD_CONTRACT_SHA256
    ):
        fail("matrix upload_contract is not the exact frozen 65-entry contract")

    raw_candidates = bundle.get("candidate", {}).get("files")
    raw_artifacts = bundle.get("artifacts")
    if not isinstance(raw_candidates, list) or not isinstance(raw_artifacts, list):
        fail("machine-proof bundle upload role inventories are invalid")
    candidate_by_path: dict[str, Mapping[str, Any]] = {}
    artifact_by_path: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(raw_candidates):
        if not isinstance(item, dict):
            fail(f"machine-proof candidate {index} is not an object")
        path = candidate.normalize_repo_relative(
            item.get("path"), f"machine-proof candidate {index} path"
        )
        if path in candidate_by_path:
            fail("machine-proof candidate paths are not unique")
        candidate_by_path[path] = item
    for index, item in enumerate(raw_artifacts):
        if not isinstance(item, dict):
            fail(f"machine-proof artifact {index} is not an object")
        path = candidate.normalize_repo_relative(
            item.get("path"), f"machine-proof artifact {index} path"
        )
        if path in artifact_by_path:
            fail("machine-proof artifact paths are not unique")
        artifact_by_path[path] = item
    if set(candidate_by_path) & set(artifact_by_path):
        fail("candidate and artifact upload roles overlap")

    bundle_path = candidate.relative(candidate.PROOF_BUNDLE_PATH)
    expected_paths = [*candidate_by_path, *artifact_by_path, bundle_path]
    files: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    seen_names: set[str] = set()
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict) or set(raw_entry) != {"path", "name", "role"}:
            fail(f"matrix upload_contract entry {index} keys differ")
        path = candidate.normalize_repo_relative(
            raw_entry.get("path"), f"matrix upload_contract entry {index} path"
        )
        name = candidate.safe_upload_name(
            raw_entry.get("name"), f"matrix upload_contract entry {index} name"
        )
        role = raw_entry.get("role")
        if path in candidate_by_path:
            expected = candidate_by_path[path]
            if role != expected.get("role") or name != expected.get("name"):
                fail(f"matrix candidate mapping {index} differs from its exact bundle role")
            require_bytes = True
            label = "candidate " + path
        elif path in artifact_by_path:
            expected = artifact_by_path[path]
            if role != "PROOF_ARTIFACT":
                fail(f"matrix artifact mapping {index} has the wrong role")
            require_bytes = False
            label = "artifact " + path
        elif path == bundle_path:
            expected = bundle_identity
            if role != "PROOF_BUNDLE":
                fail("matrix proof-bundle mapping has the wrong role")
            require_bytes = True
            label = "proof bundle"
        else:
            fail(f"matrix upload_contract entry {index} has no exact bundle identity")
        if path in seen_paths or name in seen_names:
            fail("matrix upload_contract contains duplicate paths or names")
        seen_paths.add(path)
        seen_names.add(name)
        observed = _identity(ROOT.joinpath(*pathlib.PurePosixPath(path).parts))
        _exact_identity_match(
            expected,
            observed,
            require_bytes=require_bytes,
            label=label,
        )
        verify_source_blob(path, observed["git_blob_sha1"])
        files.append(
            {"path": path, "name": name, "git_blob_sha": observed["git_blob_sha1"]}
        )

    if [item["path"] for item in files] != expected_paths:
        fail("matrix upload_contract order differs from candidate/artifact/bundle order")
    if len(files) != EXPECTED_UPLOADS:
        fail("resolved upload count differs from 65")
    if return_receipt.get("publication_id") != PUBLICATION_ID:
        fail("prepublication return receipt publication_id differs")

    try:
        # Reuse the candidate's source-pinned validator loader so the bytes
        # executed here are the same reviewed bytes bound by the freeze.
        receipt = candidate.verify_machine_bundle(bundle)
    except candidate.CorpusCandidateError as exc:
        fail("machine-proof read-only gate rejected candidate: " + str(exc))
    if (
        receipt.get("sha256") != MACHINE_PROOF_SHA256
        or receipt.get("publication_id") != PUBLICATION_ID
    ):
        fail("machine-proof read-only gate returned a different candidate identity")
    return matrix, metadata, bundle, files


def _tracked_authorization_paths() -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            env={
                key: value
                for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ")
                if (value := os.environ.get(key)) is not None
            }
            | {"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"cannot inspect existing owner-authorization nonces: {exc}")
    if completed.returncode != 0:
        fail("cannot inspect existing owner-authorization nonces")
    try:
        values = completed.stdout.decode("utf-8", errors="strict").split("\0")
    except UnicodeError:
        fail("tracked path inventory is not UTF-8")
    return sorted(
        path
        for path in values
        if path and pathlib.PurePosixPath(path).name == AUTHORIZATION_BASENAME
    )


def require_fresh_nonce(nonce: str, target_relative: str) -> None:
    """Reject reuse while permitting deterministic revalidation of this control."""
    for relative in _tracked_authorization_paths():
        if relative == target_relative:
            continue
        path = ROOT.joinpath(*pathlib.PurePosixPath(relative).parts)
        value = _strict_json(path, "existing owner authorization")
        if value.get("nonce") == nonce:
            fail("OWNER_AUTHORIZATION_EVENT nonce is already used by another authorization")


def build_controls(
    event: Mapping[str, Any],
    control_rel: pathlib.PurePosixPath = CONTROL_REL,
) -> tuple[pathlib.Path, pathlib.Path, bytes, bytes, list[dict[str, str]]]:
    safe_control = candidate.normalize_repo_relative(
        control_rel.as_posix(), "publication control directory"
    )
    authorization_relative = (
        pathlib.PurePosixPath(safe_control) / AUTHORIZATION_BASENAME
    ).as_posix()
    manifest_relative = (
        pathlib.PurePosixPath(safe_control) / MANIFEST_BASENAME
    ).as_posix()
    evidence_relative = (
        pathlib.PurePosixPath(safe_control) / EVIDENCE_BASENAME
    ).as_posix()
    require_fresh_nonce(str(event["nonce"]), authorization_relative)
    _matrix, metadata, _bundle, files = load_upload_contract()
    upload_paths = {item["path"] for item in files}
    if {authorization_relative, manifest_relative, evidence_relative} & upload_paths:
        fail("authorization, manifest and evidence controls must not be uploaded")

    return_identity = _identity(candidate.RETURN_RECEIPT_PATH)
    bundle_identity = _identity(candidate.PROOF_BUNDLE_PATH)
    uploads: list[dict[str, Any]] = []
    for item in files:
        observed = _identity(
            ROOT.joinpath(*pathlib.PurePosixPath(item["path"]).parts)
        )
        uploads.append(
            {
                "path": item["path"],
                "name": item["name"],
                "bytes": observed["bytes"],
                "sha256": observed["sha256"],
                "git_blob_sha": observed["git_blob_sha1"],
            }
        )
    statement = exact_statement()
    authorization = {
        "_license": LICENSE,
        "schema": publish.OWNER_AUTHORIZATION_SCHEMA,
        "authorization_id": AUTHORIZATION_ID,
        "nonce": event["nonce"],
        "single_use": True,
        "single_use_scope": publish.SINGLE_USE_SCOPE,
        "principal": PRINCIPAL,
        "publication_id": PUBLICATION_ID,
        "repository": REPOSITORY,
        "source_head": SOURCE_HEAD,
        "candidate_return_receipt": _generic_identity(return_identity),
        "canonical_metadata_sha256": METADATA_SHA256,
        "uploads": uploads,
        "machine_proof": _generic_identity(bundle_identity),
        "authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS),
        "publication_evidence_path": evidence_relative,
        "authorization_event": {
            "channel": (
                "Repository-recorded ChatGPT conversation exact hash-bound owner "
                "authorization; independent external proof: false"
            ),
            "authorized_at": event["authorized_at"],
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": statement,
            "statement_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
            "principal": PRINCIPAL,
            "candidate_return_receipt_sha256": RETURN_SHA256,
        },
    }
    try:
        authorization_raw = candidate.json_bytes(authorization)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))
    authorization_identity = {
        "path": authorization_relative,
        "bytes": len(authorization_raw),
        "sha256": hashlib.sha256(authorization_raw).hexdigest(),
        "git_blob_sha": candidate.git_blob_sha1(authorization_raw),
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
            "path": candidate.relative(candidate.PROOF_BUNDLE_PATH),
            "git_blob_sha": bundle_identity["git_blob_sha1"],
            "policy_id": machine_proof.POLICY_ID,
        },
        "owner_authorization": authorization_identity,
        "evidence_path": evidence_relative,
    }
    try:
        manifest_raw = candidate.json_bytes(manifest)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))
    return (
        ROOT.joinpath(*pathlib.PurePosixPath(authorization_relative).parts),
        ROOT.joinpath(*pathlib.PurePosixPath(manifest_relative).parts),
        authorization_raw,
        manifest_raw,
        files,
    )


def _open_or_create_control_directory(relative: pathlib.PurePosixPath) -> int:
    safe = candidate.normalize_repo_relative(
        relative.as_posix(), "publication control directory"
    )
    parts = pathlib.PurePosixPath(safe).parts
    if not parts:
        fail("publication control directory is empty")
    parent_relative = pathlib.PurePosixPath(*parts[:-1]).as_posix()
    try:
        parent_descriptor = candidate.open_repo_directory(ROOT, parent_relative)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))
    try:
        try:
            os.mkdir(parts[-1], 0o755, dir_fd=parent_descriptor)
        except FileExistsError:
            pass
        except OSError as exc:
            fail(f"cannot create publication control directory: {exc.strerror}")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        try:
            descriptor = os.open(parts[-1], flags, dir_fd=parent_descriptor)
        except OSError as exc:
            fail(f"cannot open publication control directory safely: {exc.strerror}")
        status = os.fstat(descriptor)
        if not stat.S_ISDIR(status.st_mode):
            os.close(descriptor)
            fail("publication control path is not a directory")
        return descriptor
    finally:
        os.close(parent_descriptor)


def _directory_file_bytes(directory_descriptor: int, name: str) -> bytes | None:
    candidate.safe_upload_name(name, "control basename")
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_descriptor,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        fail(f"cannot inspect existing publication control {name}: {exc.strerror}")
    try:
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
            fail(f"publication control must be a single-link regular file: {name}")
        if status.st_size > zenodo.MAX_JSON_BYTES:
            fail(f"publication control exceeds size limit: {name}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, zenodo.MAX_JSON_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > zenodo.MAX_JSON_BYTES:
                fail(f"publication control exceeds size limit: {name}")
        if total != status.st_size:
            fail(f"publication control changed while being read: {name}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _verify_control_readback(path: pathlib.Path, expected: bytes) -> None:
    try:
        observed = candidate.regular_bytes(path, zenodo.MAX_JSON_BYTES)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))
    if observed != expected:
        fail("publication control readback differs: " + candidate.relative(path))


def emit_controls(
    control_rel: pathlib.PurePosixPath,
    authorization_raw: bytes,
    manifest_raw: bytes,
    *,
    check: bool,
) -> tuple[pathlib.Path, pathlib.Path]:
    authorization_path = ROOT.joinpath(
        *control_rel.parts, AUTHORIZATION_BASENAME
    )
    manifest_path = ROOT.joinpath(*control_rel.parts, MANIFEST_BASENAME)
    if check:
        try:
            descriptor = candidate.open_repo_directory(ROOT, control_rel.as_posix())
        except candidate.CorpusCandidateError as exc:
            fail(str(exc))
    else:
        descriptor = _open_or_create_control_directory(control_rel)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("publication control directory is already locked by another run")
        except OSError as exc:
            fail(f"cannot lock publication control directory: {exc.strerror}")
        outputs = {
            AUTHORIZATION_BASENAME: authorization_raw,
            MANIFEST_BASENAME: manifest_raw,
        }
        observed = {
            name: _directory_file_bytes(descriptor, name) for name in outputs
        }
        for name, raw in observed.items():
            if raw is not None and raw != outputs[name]:
                action = "generated control differs" if check else "refusing to overwrite changed publication control"
                fail(action + ": " + name)
        if check and any(raw is None for raw in observed.values()):
            fail("generated publication control is absent")
        if not check and any(raw is None for raw in observed.values()):
            try:
                candidate.atomic_write_set(
                    descriptor,
                    outputs,
                    commit_marker=MANIFEST_BASENAME,
                )
            except candidate.CorpusCandidateError as exc:
                fail(str(exc))
        final = {
            name: _directory_file_bytes(descriptor, name) for name in outputs
        }
        if any(final[name] != outputs[name] for name in outputs):
            fail("publication control locked readback differs")
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(descriptor)
    _verify_control_readback(authorization_path, authorization_raw)
    _verify_control_readback(manifest_path, manifest_raw)
    return authorization_path, manifest_path


def materialize(
    *,
    check: bool,
    event_raw: str | None,
    control_rel: pathlib.PurePosixPath = CONTROL_REL,
) -> dict[str, Any]:
    event = parse_authorization_event(event_raw)
    (
        authorization_path,
        manifest_path,
        authorization_raw,
        manifest_raw,
        files,
    ) = build_controls(event, control_rel)
    emitted_authorization, emitted_manifest = emit_controls(
        control_rel,
        authorization_raw,
        manifest_raw,
        check=check,
    )
    if (
        emitted_authorization != authorization_path
        or emitted_manifest != manifest_path
    ):
        fail("publication control output paths differ")
    try:
        normalized = publish.load_manifest(manifest_path, ROOT)
    except zenodo.ZenodoError as exc:
        fail("generic publisher read-only manifest gate rejected controls: " + str(exc))
    contract_pairs = [(item["path"], item["name"]) for item in files]
    normalized_pairs = [(item["path"], item["name"]) for item in normalized["files"]]
    if (
        normalized.get("source_head") != SOURCE_HEAD
        or normalized.get("owner_authorization", {}).get("authorization_id")
        != AUTHORIZATION_ID
        or normalized_pairs != contract_pairs
        or len(normalized_pairs) != EXPECTED_UPLOADS
    ):
        fail("generic publisher normalized controls differ from the exact contract")
    return {
        "authorization_path": candidate.relative(authorization_path),
        "manifest_path": candidate.relative(manifest_path),
        "authorization_sha256": hashlib.sha256(authorization_raw).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "upload_count": len(files),
        "source_head": SOURCE_HEAD,
        "authorization_id": AUTHORIZATION_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = materialize(
            check=args.check,
            event_raw=os.environ.get(OWNER_AUTHORIZATION_EVENT_ENV),
        )
    except CorpusPublicationControlError as exc:
        raise SystemExit("BLOCK " + str(exc)) from exc
    print(
        "PASS "
        + ("verified" if args.check else "materialized")
        + " retrospective proof corpus publication controls: "
        + f"uploads={report['upload_count']} source_head={report['source_head']} "
        + f"authorization_id={report['authorization_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
