#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Derive the final Zenodo manifest from an exact Git source tree.

The checked-in release manifest contains a reserve-only sentinel instead of a
software archive.  This avoids asking a tagged tree to contain the digest of an
archive that contains that same tree.  Immediately before finalization this
tool reads every blob from the authorized Git tree, creates a normalized
deterministic source export outside the tree, and replaces the sentinel in a
transient client manifest.  No Git history, ref, credential, or untracked file
is included in the archive.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tarfile
from typing import Any, Sequence


REPOSITORY_MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_MODULE_ROOT))

from tools.qikvrt_zenodo_actions import ZenodoError, validate_manifest


RELEASE_ID = "2026-07-22-effect-ack-universality-1.0.0"
TAG = "v2026.07.22-effect-ack-universality-1.0.0"
SENTINEL_NAME = "DO_NOT_UPLOAD__GENERATED_SOFTWARE_ARCHIVE_REQUIRED.txt"
ARCHIVE_NAME = f"qik-vrt-{TAG}-source.tar.gz"
CHECKSUM_NAME = ARCHIVE_NAME + ".sha256"
PROVENANCE_NAME = "qik-vrt-effect-ack-source-export-provenance.json"
FIXED_MTIME = 1784678400  # 2026-07-22T00:00:00Z
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
DOI = re.compile(r"10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+\Z")
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_BLOB_BYTES = 256 * 1024 * 1024


class BuildError(RuntimeError):
    """A safe, fail-closed source-export error."""


def _run_git(root: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:]
        raise BuildError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _relative(root: Path, raw: str, *, must_exist: bool = False) -> Path:
    if not raw or "\x00" in raw:
        raise BuildError("path must be a non-empty string")
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(root)
        except ValueError:
            raise BuildError("path must stay inside the repository root") from None
    pure = PurePosixPath(candidate.as_posix())
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise BuildError(f"unsafe repository-relative path: {raw}")
    cursor = root
    for part in pure.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise BuildError(f"path contains a symbolic link: {raw}")
    resolved = cursor.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise BuildError(f"path escapes the repository root: {raw}") from None
    if must_exist and (not resolved.is_file() or resolved.is_symlink()):
        raise BuildError(f"required regular file is absent: {raw}")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > 4 * 1024 * 1024:
        raise BuildError("template exceeds the JSON size bound")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"invalid JSON template: {exc}") from None
    if not isinstance(value, dict):
        raise BuildError("template must contain a JSON object")
    return value


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise BuildError(f"refusing to replace an existing output: {path.name}")
    temporary = path.parent / ("." + path.name + f".{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("output write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)


def _parse_tree(root: Path, commit: str) -> list[tuple[str, str, str, str]]:
    raw = _run_git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries: list[tuple[str, str, str, str]] = []
    previous = ""
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            raise BuildError("Git tree contains an unsupported entry") from None
        pure = PurePosixPath(path)
        if (
            pure.is_absolute()
            or any(part in ("", ".", "..") for part in pure.parts)
            or "\\" in path
            or any(ord(character) < 32 for character in path)
        ):
            raise BuildError(f"Git tree contains an unsafe path: {path!r}")
        if previous and path <= previous:
            raise BuildError("Git tree paths are not strictly ordered")
        previous = path
        if object_type != "blob" or mode not in {"100644", "100755", "120000"}:
            raise BuildError(f"unsupported Git tree entry {mode} {object_type}: {path}")
        if not SHA1.fullmatch(object_id):
            raise BuildError("Git tree contains an invalid object identifier")
        entries.append((mode, object_type, object_id, path))
    if not entries:
        raise BuildError("authorized Git tree is empty")
    return entries


def _read_batch_blob(process: subprocess.Popen[bytes], object_id: str) -> bytes:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(object_id.encode("ascii") + b"\n")
    process.stdin.flush()
    header = process.stdout.readline()
    parts = header.rstrip(b"\n").split(b" ")
    if len(parts) != 3 or parts[0] != object_id.encode("ascii") or parts[1] != b"blob":
        raise BuildError("git cat-file returned an unexpected object header")
    try:
        size = int(parts[2])
    except ValueError:
        raise BuildError("git cat-file returned an invalid blob size") from None
    if size < 0 or size > MAX_BLOB_BYTES:
        raise BuildError("Git blob exceeds the source-export size bound")
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = process.stdout.read(min(1024 * 1024, remaining))
        if not chunk:
            raise BuildError("git cat-file ended before the blob was complete")
        chunks.append(chunk)
        remaining -= len(chunk)
    if process.stdout.read(1) != b"\n":
        raise BuildError("git cat-file blob framing is invalid")
    return b"".join(chunks)


def _build_archive(root: Path, commit: str, destination: Path) -> tuple[int, int]:
    entries = _parse_tree(root, commit)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        raise BuildError("refusing to replace an existing source archive")
    temporary = destination.parent / ("." + destination.name + f".{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    blob_bytes = 0
    process = subprocess.Popen(
        ["git", "-C", str(root), "cat-file", "--batch"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as raw_output:
            descriptor = -1
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_output, compresslevel=9, mtime=0
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
                ) as archive:
                    for mode, _object_type, object_id, path in entries:
                        payload = _read_batch_blob(process, object_id)
                        blob_bytes += len(payload)
                        info = tarfile.TarInfo(path)
                        info.mtime = FIXED_MTIME
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        info.pax_headers = {}
                        if mode == "120000":
                            try:
                                linkname = payload.decode("utf-8")
                            except UnicodeDecodeError:
                                raise BuildError(f"symlink target is not UTF-8: {path}") from None
                            if not linkname or "\x00" in linkname:
                                raise BuildError(f"unsafe symlink target in Git tree: {path}")
                            info.type = tarfile.SYMTYPE
                            info.mode = 0o777
                            info.linkname = linkname
                            info.size = 0
                            archive.addfile(info)
                        else:
                            info.type = tarfile.REGTYPE
                            info.mode = 0o755 if mode == "100755" else 0o644
                            info.size = len(payload)
                            archive.addfile(info, io.BytesIO(payload))
            raw_output.flush()
            os.fsync(raw_output.fileno())
        assert process.stdin is not None
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr is not None else b""
        if process.wait(timeout=30) != 0:
            raise BuildError(
                "git cat-file failed: " + stderr.decode("utf-8", errors="replace")[-1000:]
            )
        size = temporary.stat().st_size
        if size <= 0 or size > MAX_ARCHIVE_BYTES:
            raise BuildError("generated archive violates the upload size bound")
        os.replace(temporary, destination)
        return len(entries), blob_bytes
    except Exception:
        process.kill()
        process.wait()
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _hashes(path: Path) -> tuple[int, str, str]:
    md5 = hashlib.md5()  # noqa: S324 - Zenodo transport checksum
    sha256 = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            md5.update(chunk)
            sha256.update(chunk)
    return size, md5.hexdigest(), sha256.hexdigest()


def _entry(root: Path, path: Path, upload_name: str) -> dict[str, Any]:
    size, md5, sha256 = _hashes(path)
    return {
        "path": path.relative_to(root).as_posix(),
        "name": upload_name,
        "size": size,
        "md5": md5,
        "sha256": sha256,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repository_root).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise BuildError("repository root must be a real directory")
    template_path = _relative(root, args.template, must_exist=True)
    output_directory = _relative(root, args.output_directory)
    result_path = _relative(root, args.result)
    try:
        result_path.relative_to(output_directory)
    except ValueError:
        raise BuildError("result must be inside the output directory") from None
    if not SHA1.fullmatch(args.source_commit) or not SHA1.fullmatch(args.source_tree):
        raise BuildError("source commit/tree must be lowercase Git SHA-1 values")
    actual_tree = _run_git(root, "show", "-s", "--format=%T", args.source_commit).decode("ascii").strip()
    if actual_tree != args.source_tree:
        raise BuildError("source commit does not carry the authorized source tree")

    template = _read_json(template_path)
    if template.get("release_id") != RELEASE_ID:
        raise BuildError("template belongs to another release")
    authorization = template.get("authorization")
    if not isinstance(authorization, dict) or authorization.get("tag") != TAG:
        raise BuildError("template does not bind the exact release tag")
    reserved = template.get("reserved_dois")
    if (
        not isinstance(reserved, dict)
        or set(reserved) != {"paper", "software"}
        or not all(isinstance(value, str) and DOI.fullmatch(value) for value in reserved.values())
    ):
        raise BuildError("template does not bind both reserved DOIs")
    software = template.get("software")
    if not isinstance(software, dict) or not isinstance(software.get("files"), list):
        raise BuildError("template software files are invalid")
    if len(software["files"]) != 1 or software["files"][0].get("name") != SENTINEL_NAME:
        raise BuildError("template does not contain the exact reserve-only sentinel")
    reserve_shape = copy.deepcopy(template)
    reserve_shape.pop("reserved_dois")
    try:
        validate_manifest(reserve_shape, root, final=False)
    except ZenodoError as exc:
        raise BuildError(f"checked-in reserve manifest is invalid: {exc}") from None

    output_directory.mkdir(parents=True, exist_ok=True)
    archive_path = output_directory / ARCHIVE_NAME
    checksum_path = output_directory / CHECKSUM_NAME
    provenance_path = output_directory / PROVENANCE_NAME
    file_count, blob_bytes = _build_archive(root, args.source_commit, archive_path)
    archive_size, archive_md5, archive_sha256 = _hashes(archive_path)
    _write_atomic(
        checksum_path,
        f"{archive_sha256}  {ARCHIVE_NAME}\n".encode("ascii"),
    )
    provenance = {
        "schema": "qikvrt_effect_ack_source_export_provenance_v1",
        "release_id": RELEASE_ID,
        "tag": TAG,
        "authority_repository": "Goldkelch/qik-vrt",
        "source_commit": args.source_commit,
        "source_tree": args.source_tree,
        "git_tree_entries": file_count,
        "git_blob_bytes": blob_bytes,
        "archive": {
            "name": ARCHIVE_NAME,
            "size": archive_size,
            "md5": archive_md5,
            "sha256": archive_sha256,
        },
        "normalization": {
            "format": "PAX tar compressed with gzip level 9",
            "gzip_mtime": 0,
            "entry_mtime_utc": "2026-07-22T00:00:00Z",
            "uid": 0,
            "gid": 0,
            "regular_modes": ["0644", "0755"],
            "scope": "every blob path in the exact Git tree; no history, refs, credentials, or untracked files",
        },
        "github_release_object_created": False,
        "datatracker_submission_performed": False,
    }
    _write_atomic(
        provenance_path,
        (json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )

    final_manifest = copy.deepcopy(template)
    final_manifest["software"]["files"] = [
        _entry(root, archive_path, ARCHIVE_NAME),
        _entry(root, checksum_path, CHECKSUM_NAME),
        _entry(root, provenance_path, PROVENANCE_NAME),
    ]
    try:
        final_manifest = validate_manifest(final_manifest, root, final=True)
    except ZenodoError as exc:
        raise BuildError(f"derived final manifest is invalid: {exc}") from None
    payload = (
        json.dumps(final_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _write_atomic(result_path, payload)
    return {
        "result": result_path.relative_to(root).as_posix(),
        "archive": archive_path.relative_to(root).as_posix(),
        "archive_sha256": archive_sha256,
        "source_tree": args.source_tree,
        "git_tree_entries": file_count,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repository-root", default=".")
    value.add_argument("--template", required=True)
    value.add_argument("--source-commit", required=True)
    value.add_argument("--source-tree", required=True)
    value.add_argument("--output-directory", required=True)
    value.add_argument("--result", required=True)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    try:
        outcome = build(parser().parse_args(argv))
        print(json.dumps(outcome, sort_keys=True))
        return 0
    except (BuildError, OSError, subprocess.SubprocessError) as exc:
        print(f"BLOCK: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
