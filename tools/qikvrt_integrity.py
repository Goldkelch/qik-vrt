#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Deterministic QIK-VRT repository integrity generator and verifier."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
from dataclasses import dataclass
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools.qikvrt_subprocess import run_bounded

MANIFEST_NAME = "REPOSITORY_FILE_MANIFEST.json"
INDEX_NAME = "SHA256SUMS.txt"
DETACHED_NAME = "REPOSITORY_FILE_MANIFEST.json.sha256"
LOCK_NAME = ".qikvrt-integrity.lock"
SCHEMA = "qikvrt_repository_integrity_manifest_v3"
GENERATOR_VERSION = "3.1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
INTEGRITY_PATHS = {MANIFEST_NAME, INDEX_NAME, DETACHED_NAME}
LEGACY_GLOBAL_INVENTORIES = (
    {
        "path": "MANIFEST.json",
        "status": "LEGACY_SCOPED_PACKAGE_V2_7_NOT_CURRENT_GLOBAL_AUTHORITY",
    },
    {
        "path": "FILE_INVENTORY.json",
        "status": "LEGACY_REST_TCPIP_SNAPSHOT_NOT_CURRENT_GLOBAL_AUTHORITY",
    },
    {
        "path": "SHA256SUMS",
        "status": "LEGACY_V45_20_DOCUMENT_INDEX_NOT_CURRENT_GLOBAL_AUTHORITY",
    },
)
TRACKED_RUNTIME_STATE = {
    "release/effect-ack-universality-request.json",
    "state/launcher_acceptance_record.json",
    "runtime/DEPENDENCIES.json",
    "runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json",
    "runtime/RUNTIME_DEPENDENCY_MANIFEST.json",
}
TRANSIENT_PREFIXES = (
    "logs/",
    "unit_state/",
    "e2e_state/",
    ".qikvrt/runtime/",
    ".qikvrt/evidence/",
    ".qikvrt/api/",
    ".qikvrt/toolchains/",
    ".qikvrt/cache/",
    ".qikvrt/release/",
)
MAX_IMMUTABLE_FILE_BYTES = 256 * 1024 * 1024
MAX_INTEGRITY_METADATA_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class Verification:
    ok: bool
    message: str


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _regular_file_bytes(
    root: pathlib.Path,
    relative: str,
    *,
    max_bytes: int = MAX_IMMUTABLE_FILE_BYTES,
) -> bytes:
    """Read one stable in-tree regular file without following symlinks."""
    safe_relative = _safe_path(relative)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"repository root must be a real directory: {root}")
    parts = pathlib.PurePosixPath(safe_relative).parts
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow
    directory_descriptor = os.open(root, directory_flags)
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(part, directory_flags, dir_fd=directory_descriptor)
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=directory_descriptor)
    except OSError as exc:
        raise RuntimeError(
            f"immutable repository path must not be a symlink or unsafe component: {safe_relative}"
        ) from exc
    finally:
        os.close(directory_descriptor)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"repository path is not a regular file: {safe_relative}")
        if before.st_size > max_bytes:
            raise RuntimeError(
                f"repository path exceeds the {max_bytes}-byte integrity bound: {safe_relative}"
            )
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(data) > max_bytes or len(data) != before.st_size:
            raise RuntimeError(f"repository path changed size while hashing: {safe_relative}")
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise RuntimeError(f"repository path changed while hashing: {safe_relative}")
        return data
    finally:
        os.close(descriptor)


def _safe_path(raw: str) -> str:
    if not raw or "\\" in raw or any(ord(character) < 32 for character in raw):
        raise ValueError(f"non-portable repository path: {raw!r}")
    path = pathlib.PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"unsafe repository path: {raw!r}")
    return path.as_posix()


def _git(root: pathlib.Path, *arguments: str) -> bytes:
    try:
        process = run_bounded(
            ["git", "-C", str(root), *arguments],
            cwd=root,
            timeout=30,
            max_output_bytes=16 * 1024 * 1024,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise RuntimeError(f"git invocation failed: {exc}") from exc
    if process.timed_out:
        raise RuntimeError(f"git {' '.join(arguments)} timed out")
    if process.output_limit_exceeded:
        raise RuntimeError(f"git {' '.join(arguments)} exceeded the output bound")
    if process.returncode != 0:
        error = process.stderr.strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {error}")
    return process.stdout.encode("utf-8", errors="surrogateescape")


def is_transient(relative: str) -> bool:
    path = pathlib.PurePosixPath(relative)
    return (
        any(relative.startswith(prefix) for prefix in TRANSIENT_PREFIXES)
        or "__pycache__" in path.parts
        or path.suffix.lower() in {".pyc", ".pyo"}
        or relative == LOCK_NAME
        or relative.endswith(".qikvrt-integrity.tmp")
    )


def collect_paths(root: pathlib.Path = ROOT) -> list[str]:
    """Collect tracked plus deliberate untracked sources via git, never caches."""
    output = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", ".")
    deleted_output = _git(root, "ls-files", "-z", "--deleted", "--", ".")
    deleted = {os.fsdecode(item) for item in deleted_output.split(b"\0") if item}
    decoded = [os.fsdecode(item) for item in output.split(b"\0") if item]
    paths = sorted(
        {_safe_path(item) for item in decoded if item not in deleted and not is_transient(item)}
    )
    return paths


def classification(relative: str) -> tuple[str, bool, str]:
    """Return classification, immutable flag and exclusion reason."""
    if relative in INTEGRITY_PATHS:
        return "integrity_metadata", False, "cycle_prevention"
    if relative in TRACKED_RUNTIME_STATE or any(
        relative.startswith(prefix)
        for prefix in (
            "logs/",
            ".qikvrt/runtime/",
            ".qikvrt/evidence/",
            ".qikvrt/api/",
            ".qikvrt/toolchains/",
            ".qikvrt/cache/",
            ".qikvrt/release/",
        )
    ):
        legacy = relative == "state/launcher_acceptance_record.json"
        authorization = relative == "release/effect-ack-universality-request.json"
        return (
            (
                "legacy_runtime_state"
                if legacy
                else "release_authorization_state"
                if authorization
                else "runtime_state"
            ),
            False,
            (
                "authorization_marker_is_self_digest_bound_not_release_constant"
                if authorization
                else "runtime_state_is_not_release_constant"
            ),
        )
    if relative.startswith("tests/"):
        return "test_source", True, ""
    if relative.startswith(("tools/", "src/", "scripts/")) or pathlib.PurePosixPath(relative).suffix in {
        ".py", ".sh", ".ps1", ".cmd", ".bat", ".c",
    }:
        return "source_code", True, ""
    if relative.startswith("canonical/"):
        return "canonical_contract", True, ""
    if relative.startswith(("acceptance/", "policy/", "platform/", "cicd/")):
        return "policy_or_acceptance", True, ""
    if relative.startswith("payload/"):
        return "payload_snapshot", True, ""
    if relative.startswith(("dist/", "assets/", "documents/", "incoming/")):
        return "artifact", True, ""
    if relative.startswith(("audit/", "evidence/", "ledger/", "publication/")) or relative.startswith("LOGS/"):
        return "historical_evidence", True, ""
    if pathlib.PurePosixPath(relative).suffix.lower() in {".md", ".txt", ".tex", ".bib", ".html"}:
        return "documentation", True, ""
    return "repository_content", True, ""


def _content_tree_sha256(entries: list[dict[str, Any]]) -> str:
    """Hash the canonical immutable content tree, never Git history metadata.

    A commit id is not a content identity: an empty/rebased commit can change
    HEAD without changing a byte, and generating a commit that embeds its own
    id introduces an avoidable lifecycle cycle.  The records below contain
    exactly the stable properties needed to identify the immutable tree.  The
    three generated integrity outputs are classified non-immutable and are
    therefore excluded from this digest by construction.
    """
    records = [
        {
            "path": entry["path"],
            "file_type": entry["file_type"],
            "bytes": entry["bytes"],
            "sha256": entry["sha256"],
        }
        for entry in entries
        if entry.get("immutable") is True
    ]
    material = json.dumps(
        records,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(material)


def build_outputs(root: pathlib.Path = ROOT) -> tuple[bytes, bytes, bytes, dict[str, Any]]:
    paths = collect_paths(root)
    for required in INTEGRITY_PATHS:
        if required not in paths:
            paths.append(required)
    for required in {"tools/qikvrt_integrity.py", "LEGACY_INTEGRITY_INVENTORIES.md"}:
        if required not in paths:
            if (root / required).exists() and not is_transient(required):
                paths.append(required)
            else:
                raise RuntimeError(f"required integrity path is missing: {required}")
    paths = sorted(set(paths))
    entries: list[dict[str, Any]] = []
    immutable_digests: dict[str, str] = {}
    for relative in paths:
        kind, immutable, reason = classification(relative)
        entry: dict[str, Any] = {
            "path": relative,
            "classification": kind,
            "immutable": immutable,
            "excluded_from_sha256_index": not immutable,
        }
        if immutable:
            path = root / relative
            if path.is_symlink():
                raise RuntimeError(
                    f"immutable repository path must not be a symlink: {relative}"
                )
            if not path.is_file():
                raise RuntimeError(f"repository path is not a file: {relative}")
            data = _regular_file_bytes(root, relative)
            digest = _sha256_bytes(data)
            entry.update({
                "bytes": len(data),
                "sha256": digest,
                "file_type": "regular",
            })
            immutable_digests[relative] = digest
        else:
            entry["exclusion_reason"] = reason
        entries.append(entry)

    manifest: dict[str, Any] = {
        "_license": {
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "rights_holder": "Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "classification": "repository_integrity_manifest_json",
        },
        "schema": SCHEMA,
        "generator": "tools/qikvrt_integrity.py",
        "generator_version": GENERATOR_VERSION,
        "immutable_file_max_bytes": MAX_IMMUTABLE_FILE_BYTES,
        "integrity_metadata_max_bytes": MAX_INTEGRITY_METADATA_BYTES,
        "source_command": (
            "git ls-files -z --cached --others --exclude-standard -- .; "
            "subtract git ls-files -z --deleted -- ."
        ),
        "repository_content_tree_sha256": _content_tree_sha256(entries),
        "repository_content_tree_digest_specification": (
            "sha256(canonical-json-v1 immutable records: "
            "path,file_type,bytes,sha256; integrity outputs excluded)"
        ),
        "includes_deliberate_untracked_sources": True,
        "file_count": len(entries),
        "immutable_file_count": len(immutable_digests),
        "excluded_file_count": len(entries) - len(immutable_digests),
        "integrity_authority": {
            "manifest": MANIFEST_NAME,
            "sha256_index": INDEX_NAME,
            "detached_manifest_digest": DETACHED_NAME,
            "legacy_global_inventories": list(LEGACY_GLOBAL_INVENTORIES),
            "scoped_manifest_rule": "Other manifests apply only to the artifact they explicitly name.",
        },
        "transient_exclusion_rules": [
            *TRANSIENT_PREFIXES,
            "**/__pycache__/**",
            "*.py[cod]",
            LOCK_NAME,
            "*.qikvrt-integrity.tmp",
        ],
        "files": entries,
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    index_bytes = "".join(
        f"{digest}  {relative}\n"
        for relative, digest in sorted(immutable_digests.items())
    ).encode("utf-8")
    detached_bytes = f"{_sha256_bytes(manifest_bytes)}  {MANIFEST_NAME}\n".encode("ascii")
    return manifest_bytes, index_bytes, detached_bytes, manifest


def _fsync_directory(path: pathlib.Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextlib.contextmanager
def _exclusive_integrity_lock(root: pathlib.Path):
    """Serialize generation and verification of the integrity snapshot."""
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError(f"repository root must be a real directory: {root}")
    lock = root / LOCK_NAME
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(lock, flags, 0o600)
    except OSError as exc:
        raise RuntimeError("integrity lock cannot be opened safely") from exc
    try:
        lock_status = os.fstat(descriptor)
        if not stat.S_ISREG(lock_status.st_mode) or lock_status.st_nlink != 1:
            raise RuntimeError("integrity lock must be a single-link regular file")
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("integrity generation or verification is already active") from exc
        payload = f"{os.getpid()}\n".encode("ascii")
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("integrity lock write made no forward progress")
            view = view[written:]
        os.fsync(descriptor)
        _fsync_directory(root)
        yield descriptor
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _atomic_write_set(
    root: pathlib.Path,
    outputs: dict[str, bytes],
    lock_descriptor: int,
) -> None:
    lock = root / LOCK_NAME
    try:
        held = os.fstat(lock_descriptor)
        current = os.lstat(lock)
    except OSError as exc:
        raise RuntimeError("integrity output write lost its exclusive lock") from exc
    if (
        not stat.S_ISREG(held.st_mode)
        or held.st_nlink != 1
        or (held.st_dev, held.st_ino) != (current.st_dev, current.st_ino)
    ):
        raise RuntimeError("integrity output write lock identity changed")
    temporary: dict[str, pathlib.Path] = {}
    try:
        for name, data in outputs.items():
            path = root / name
            temp = root / f".{name}.{os.getpid()}.qikvrt-integrity.tmp"
            descriptor = os.open(
                temp,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                view = memoryview(data)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("integrity output write made no forward progress")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            temporary[name] = temp
        # Each replace is atomic. Manifest is the final commit marker.
        for name in (INDEX_NAME, DETACHED_NAME, MANIFEST_NAME):
            os.replace(temporary[name], root / name)
            temporary.pop(name)
        _fsync_directory(root)
    finally:
        for path in temporary.values():
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def generate(root: pathlib.Path = ROOT) -> Verification:
    with _exclusive_integrity_lock(root) as lock_descriptor:
        manifest_bytes, index_bytes, detached_bytes, manifest = build_outputs(root)
        _atomic_write_set(
            root,
            {
                MANIFEST_NAME: manifest_bytes,
                INDEX_NAME: index_bytes,
                DETACHED_NAME: detached_bytes,
            },
            lock_descriptor,
        )
    return Verification(
        True,
        f"generated {manifest['file_count']} classified entries and "
        f"{manifest['immutable_file_count']} immutable digests",
    )


def _parse_index(data: bytes, name: str) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{name} is not UTF-8: {exc}") from exc
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if len(line) < 67 or line[64:66] != "  " or not SHA256_RE.fullmatch(line[:64]):
            raise ValueError(f"invalid {name} line {number}")
        relative = _safe_path(line[66:])
        if relative in result:
            raise ValueError(f"duplicate {name} path: {relative}")
        result[relative] = line[:64]
    return result


def verify(root: pathlib.Path = ROOT) -> Verification:
    try:
        with _exclusive_integrity_lock(root):
            stored_manifest_bytes = _regular_file_bytes(
                root, MANIFEST_NAME, max_bytes=MAX_INTEGRITY_METADATA_BYTES
            )
            stored_index_bytes = _regular_file_bytes(
                root, INDEX_NAME, max_bytes=MAX_INTEGRITY_METADATA_BYTES
            )
            stored_detached_bytes = _regular_file_bytes(
                root, DETACHED_NAME, max_bytes=MAX_INTEGRITY_METADATA_BYTES
            )
            expected_manifest, expected_index, expected_detached, manifest = build_outputs(root)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return Verification(False, f"integrity input failure: {exc}")
    if stored_manifest_bytes != expected_manifest:
        return Verification(False, "repository manifest differs from deterministic regeneration")
    if stored_index_bytes != expected_index:
        return Verification(False, "SHA256SUMS.txt differs from deterministic regeneration")
    if stored_detached_bytes != expected_detached:
        return Verification(False, "detached manifest digest differs from deterministic regeneration")
    try:
        stored_manifest = json.loads(stored_manifest_bytes.decode("utf-8"))
        index = _parse_index(stored_index_bytes, INDEX_NAME)
        detached = _parse_index(stored_detached_bytes, DETACHED_NAME)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return Verification(False, f"stored integrity metadata is invalid: {exc}")
    if stored_manifest.get("schema") != SCHEMA or stored_manifest.get("files") != manifest.get("files"):
        return Verification(False, "stored manifest schema or entries are not canonical")
    if stored_manifest.get("repository_content_tree_sha256") != _content_tree_sha256(
        stored_manifest["files"]
    ):
        return Verification(False, "repository content-tree digest is not canonical")
    immutable = {
        entry["path"]: entry["sha256"]
        for entry in stored_manifest["files"]
        if entry.get("immutable") is True
    }
    if index != immutable:
        return Verification(False, "SHA256SUMS.txt is not exactly the immutable manifest set")
    if detached != {MANIFEST_NAME: _sha256_bytes(stored_manifest_bytes)}:
        return Verification(False, "detached digest does not authenticate the stored manifest")
    return Verification(
        True,
        f"verified {stored_manifest['file_count']} classified entries and "
        f"{stored_manifest['immutable_file_count']} immutable digests",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or verify QIK-VRT repository integrity metadata")
    parser.add_argument("action", choices=("generate", "verify"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = generate(ROOT) if args.action == "generate" else verify(ROOT)
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        result = Verification(False, f"integrity input failure: {exc}")
    print(("PASS " if result.ok else "BLOCK ") + result.message, file=sys.stdout if result.ok else sys.stderr)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
