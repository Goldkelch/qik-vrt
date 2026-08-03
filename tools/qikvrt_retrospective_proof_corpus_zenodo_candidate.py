#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Freeze the retrospective proof corpus as one deterministic Zenodo v3 set.

The historical corpus inventory, the nineteen terminal claim matrices and the
six separately returned correction archives already exist in the repository.
This tool reuses those exact bytes.  It adds only the corpus-level claim
projection, v2 prepublication-return receipt, canonical Zenodo metadata and v2
machine-proof bundle required to describe one exact 65-file upload set.

The earlier owner statement is retained only as a byte oracle.  A rebuilt
candidate whose return, metadata or proof digest differs is *not* covered by
that statement and the tool reports the mismatch without silently widening
authorization.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import math
import os
import pathlib
import re
import stat
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, NoReturn


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION_REL = pathlib.PurePosixPath("release/zenodo-corpus-proof-2026-07-28")
PUBLICATION = ROOT.joinpath(*PUBLICATION_REL.parts)
UNION_REL = PUBLICATION_REL / "canonical-union"
UNION = ROOT.joinpath(*UNION_REL.parts)
RETROSPECTIVE_REL = UNION_REL / "retrospective-proof-corpus"
RETROSPECTIVE = ROOT.joinpath(*RETROSPECTIVE_REL.parts)
CORRECTIONS_REL = UNION_REL / "versioned-corrected-candidates"
CORRECTIONS = ROOT.joinpath(*CORRECTIONS_REL.parts)

PUBLICATION_ID = "qikvrt-retrospective-proof-corpus-2026-07-28-v3"
SUGGESTED_AUTHORIZATION_ID = (
    "qikvrt-retrospective-proof-corpus-v3-rebuild-20260803t094446z"
)

INDEX_PATH = RETROSPECTIVE / "RETROSPECTIVE_PROOF_CORPUS_INDEX.json"
CORPUS_RECEIPT_PATH = RETROSPECTIVE / "RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json"
OWNER_RETURN_PATH = CORRECTIONS / "OWNER_RETURN_PACKAGE.json"
OWNER_RETURN_NOTICE_PATH = CORRECTIONS / "OWNER_RETURN_PACKAGE.md"
OWNER_ACCEPTANCE_PATH = CORRECTIONS / "OWNER_ACCEPTANCE_RECEIPT.json"
EQUALITY_PATH = ROOT / (
    "evidence/receipts/"
    "authority-mirror-equality-2026-08-01-"
    "batch003-six-versioned-corrections-pr297-pr174.json"
)
EQUALITY_INDEX_PATH = ROOT / "evidence/receipts/index.json"

CLAIM_MATRIX_PATH = PUBLICATION / "CORPUS_CLAIM_MATRIX.json"
RETURN_RECEIPT_PATH = PUBLICATION / "PREPUBLICATION_RETURN_RECEIPT.json"
METADATA_PATH = PUBLICATION / "ZENODO_METADATA.json"
PROOF_BUNDLE_PATH = PUBLICATION / "MACHINE_PROOF_BUNDLE.json"

EXPECTED_SUBJECTS = 19
EXPECTED_SOURCE_CLAIMS = 70_439
EXPECTED_EXPLICIT_OPEN = 1_262
EXPECTED_CORRECTIONS = 6
EXPECTED_UPLOADS = 65
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_VALIDATOR_BYTES = 8 * 1024 * 1024
SUBJECT_ID = re.compile(r"^SUBJECT-[0-9a-f]{16}$")
UTC_TIMESTAMP = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)

VALIDATOR_REL = "tools/qikvrt_zenodo_machine_proof.py"
# These pins bind the exact source bytes compiled by verify_machine_bundle().
# Update them only together after intentional review of the shared validator.
VALIDATOR_SHA256 = (
    "da00bbd72a81f543eba7a9cc7eb67f80686ba4ca435e6eba5b78f1844ecd7f32"
)
VALIDATOR_GIT_BLOB_SHA1 = "e205b3c26a42a3911421d4a449dec8a8dec08d1c"

OUTPUT_PATHS = (
    CLAIM_MATRIX_PATH,
    METADATA_PATH,
    RETURN_RECEIPT_PATH,
    PROOF_BUNDLE_PATH,
)

ALLOWED_MATRIX_SCHEMAS = {
    "qikvrt_retrospective_claim_matrix_v1",
    "qikvrt_retrospective_claim_matrix_v2",
}
KNOWN_INDEX_DISCREPANCY_SUBJECT = "SUBJECT-2581811b342e505d"
KNOWN_INDEX_DISCREPANCY_SUMMARY = {
    "EMPIRICALLY_EVIDENCED": 0,
    "FORMAL_PROVED": 0,
    "INTERPRETATIVE": 0,
    "NORMATIVE": 0,
    "OPEN": 0,
    "SOURCE_BOUND": 8,
}
KNOWN_MATRIX_RECOMPUTED_SUMMARY = {
    "EMPIRICALLY_EVIDENCED": 20,
    "FORMAL_PROVED": 0,
    "INTERPRETATIVE": 0,
    "NORMATIVE": 0,
    "OPEN": 0,
    "SOURCE_BOUND": 19,
}

OLD_AUTHORIZED_RETURN_SHA256 = (
    "6a8a3fe211d086f34ae306d084a23304410f6ba9876cf1f0feb1be54fbd0fcad"
)
OLD_AUTHORIZED_METADATA_SHA256 = (
    "0d55ce8ffd5023f5666ad6a4ee656766613e879f9f726834692198c5b304b8c5"
)
OLD_AUTHORIZED_MACHINE_PROOF_SHA256 = (
    "cbeb6d818e38e91369b8730a0621b48059fdf60fe8d2fccfef0d79b79f20542c"
)

LICENSE = {
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}

STATUS = {
    "FORMAL_PROVED": "PROVED",
    "EMPIRICALLY_EVIDENCED": "EVIDENCED",
    "SOURCE_BOUND": "BOUND",
    "NORMATIVE": "DECLARED",
    "INTERPRETATIVE": "DECLARED",
    "OPEN": "OPEN",
}

ALLOWED_EPISTEMIC_CLASSES = frozenset(STATUS)

WORDING = {
    "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
    "EMPIRICALLY_EVIDENCED": "EMPIRICALLY_SUPPORTED",
    "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
    "NORMATIVE": "NORMATIVE_DECLARATION",
    "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
    "OPEN": "EXPLICITLY_OPEN",
}


class CorpusCandidateError(RuntimeError):
    """Fail-closed candidate-construction error."""


def fail(message: str) -> NoReturn:
    raise CorpusCandidateError(message)


def _validate_unicode_scalars(value: Any, label: str) -> None:
    """Require one finite JSON value containing only Unicode scalar strings."""
    pending: list[Any] = [value]
    while pending:
        item = pending.pop()
        if item is None or isinstance(item, (bool, int)):
            continue
        if isinstance(item, float):
            if not math.isfinite(item):
                fail(f"{label} contains a non-finite JSON number")
            continue
        if isinstance(item, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                fail(f"{label} contains a lone Unicode surrogate")
            continue
        if isinstance(item, list):
            pending.extend(item)
            continue
        if isinstance(item, Mapping):
            for key, child in item.items():
                if not isinstance(key, str):
                    fail(f"{label} contains a non-string JSON object key")
                pending.append(key)
                pending.append(child)
            continue
        fail(f"{label} contains a non-JSON value: {type(item).__name__}")


def json_bytes(value: Any) -> bytes:
    _validate_unicode_scalars(value, "generated JSON")
    try:
        return (
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        fail(f"cannot serialize strict generated JSON: {exc}")


def canonical_json_sha256(value: Any) -> str:
    _validate_unicode_scalars(value, "canonical JSON")
    try:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        fail(f"cannot serialize strict canonical JSON: {exc}")
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def normalize_repo_relative(raw: Any, label: str = "repository path") -> str:
    """Return one exact portable canonical repository-relative path."""
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        fail(f"{label} must be a non-empty repository-relative path")
    if "\\" in raw or any(ord(character) < 32 or ord(character) == 127 for character in raw):
        fail(f"{label} contains a non-portable path character")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in raw):
        fail(f"{label} contains a lone Unicode surrogate")
    parsed = pathlib.PurePosixPath(raw)
    normalized = parsed.as_posix()
    if (
        parsed.is_absolute()
        or not parsed.parts
        or ".." in parsed.parts
        or normalized != raw
    ):
        fail(f"{label} is not a canonical repository-relative path: {raw!r}")
    return normalized


def validate_subject_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or SUBJECT_ID.fullmatch(value) is None:
        fail(f"{label} must match SUBJECT-[0-9a-f]{{16}}")
    return value


def safe_upload_name(value: Any, label: str = "upload name") -> str:
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a non-empty safe basename")
    _validate_unicode_scalars(value, label)
    if (
        value in {".", ".."}
        or "/" in value
        or "\\" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or pathlib.PurePosixPath(value).name != value
        or len(value.encode("utf-8")) > 255
    ):
        fail(f"{label} must be a portable single-component basename")
    return value


def repo_relative(root: pathlib.Path, path: pathlib.Path, label: str) -> str:
    candidate = path if path.is_absolute() else root / path
    try:
        raw = candidate.relative_to(root).as_posix()
    except ValueError:
        fail(f"{label} is outside the repository: {path}")
    return normalize_repo_relative(raw, label)


def relative(path: pathlib.Path) -> str:
    return repo_relative(ROOT, path, "repository path")


def _directory_flags() -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        fail("platform lacks required nofollow directory-descriptor support")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)


def open_repo_directory(root: pathlib.Path, relative_directory: str | None = None) -> int:
    """Open a real in-root directory by walking every component with openat."""
    parts: tuple[str, ...] = ()
    if relative_directory is not None:
        safe = normalize_repo_relative(relative_directory, "repository directory")
        parts = pathlib.PurePosixPath(safe).parts
    try:
        descriptor = os.open(root, _directory_flags())
    except OSError as exc:
        fail(f"cannot open repository root safely: {exc.strerror}")
    try:
        for part in parts:
            next_descriptor = os.open(part, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        status = os.fstat(descriptor)
        if not stat.S_ISDIR(status.st_mode):
            fail("repository directory descriptor is not a directory")
        return descriptor
    except CorpusCandidateError:
        os.close(descriptor)
        raise
    except OSError as exc:
        os.close(descriptor)
        fail(f"repository directory contains a symlink or unsafe component: {exc.strerror}")


def read_stable_regular(
    root: pathlib.Path,
    raw_relative: str,
    *,
    max_bytes: int = MAX_FILE_BYTES,
) -> bytes:
    """Read one bounded single-link regular file through nofollow descriptors."""
    safe = normalize_repo_relative(raw_relative, "repository file")
    parts = pathlib.PurePosixPath(safe).parts
    directory_descriptor = open_repo_directory(root)
    descriptor: int | None = None
    try:
        for part in parts[:-1]:
            next_descriptor = os.open(
                part,
                _directory_flags(),
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_descriptor,
        )
    except OSError as exc:
        fail(f"cannot open repository file safely {safe}: {exc.strerror}")
    finally:
        os.close(directory_descriptor)
    assert descriptor is not None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            fail(f"repository path is not a regular file: {safe}")
        if before.st_nlink != 1:
            fail(f"repository path must be a single-link regular file: {safe}")
        if before.st_size > max_bytes:
            fail(f"repository file exceeds {max_bytes} bytes: {safe}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                fail(f"repository file exceeds {max_bytes} bytes: {safe}")
        after = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_nlink,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_nlink,
        )
        if before_identity != after_identity or total != before.st_size:
            fail(f"repository file changed while being read: {safe}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def regular_bytes(path: pathlib.Path, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    return read_stable_regular(
        ROOT,
        repo_relative(ROOT, path, "repository file"),
        max_bytes=max_bytes,
    )


def identity_from_bytes(path: pathlib.Path, raw: bytes) -> dict[str, Any]:
    return {
        "path": relative(path),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
    }


def identity(path: pathlib.Path) -> dict[str, Any]:
    return identity_from_bytes(path, regular_bytes(path))


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            fail(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> NoReturn:
    fail(f"non-finite JSON number is forbidden: {value}")


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if not raw or len(raw) > MAX_JSON_BYTES:
        fail(f"{label} is empty or exceeds {MAX_JSON_BYTES} bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except CorpusCandidateError:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        fail(f"invalid {label}: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    _validate_unicode_scalars(value, label)
    return value


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    return parse_json_bytes(regular_bytes(path, MAX_JSON_BYTES), label)


def verify_binding(binding: Mapping[str, Any], label: str) -> pathlib.Path:
    required = {"path", "bytes", "sha256", "git_blob_sha1"}
    if not isinstance(binding, Mapping) or set(binding) != required:
        fail(f"{label} identity keys differ")
    raw_path = binding.get("path")
    safe_path = normalize_repo_relative(raw_path, f"{label} path")
    path = ROOT.joinpath(*pathlib.PurePosixPath(safe_path).parts)
    observed = identity(path)
    if dict(binding) != observed:
        fail(f"{label} identity differs from repository bytes")
    return path


def exact_epistemic_counts(value: Any, label: str) -> dict[str, int]:
    """Normalize one exact six-class summary without accepting bools/extras."""
    if not isinstance(value, dict) or set(value) != ALLOWED_EPISTEMIC_CLASSES:
        fail(f"{label} must contain exactly the allowed epistemic classes")
    counts: dict[str, int] = {}
    for classification in sorted(ALLOWED_EPISTEMIC_CLASSES):
        count = value[classification]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            fail(f"{label}.{classification} must be a non-negative integer")
        counts[classification] = count
    return counts


def inventory_matrix_claims(
    subject_id: str,
    matrix: Mapping[str, Any],
    label: str,
) -> dict[str, Any]:
    """Strictly inventory, but do not recursively revalidate, nested claims."""
    if matrix.get("schema") not in ALLOWED_MATRIX_SCHEMAS:
        fail(f"{label} schema is unsupported")
    if matrix.get("subject_id") != subject_id:
        fail(f"{label} subject binding differs")
    claims = matrix.get("claims")
    if not isinstance(claims, list):
        fail(f"{label} claims must be a list")

    claim_ids: set[str] = set()
    counts: Counter[str] = Counter()
    for index, item in enumerate(claims):
        where = f"{label} claims[{index}]"
        if not isinstance(item, dict):
            fail(f"{where} must be an object")
        claim_id = item.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            fail(f"{where} claim_id must be non-empty text")
        if claim_id in claim_ids:
            fail(f"{label} claim IDs are not unique")
        claim_ids.add(claim_id)
        classification = item.get("epistemic_class")
        if classification not in ALLOWED_EPISTEMIC_CLASSES:
            fail(f"{where} epistemic_class is unsupported")
        if "subject_id" in item and item["subject_id"] != subject_id:
            fail(f"{where} subject binding differs")
        counts[classification] += 1

    declared_count = matrix.get("claim_count")
    if (
        isinstance(declared_count, bool)
        or not isinstance(declared_count, int)
        or declared_count != len(claims)
    ):
        fail(f"{label} declared claim_count differs from claims")
    recomputed = {
        classification: counts[classification]
        for classification in sorted(ALLOWED_EPISTEMIC_CLASSES)
    }
    if "classification_summary" in matrix:
        declared_summary = exact_epistemic_counts(
            matrix["classification_summary"],
            f"{label} classification_summary",
        )
        if declared_summary != recomputed:
            fail(f"{label} classification_summary differs from claims")
    for count_key in ("terminal_claim_count", "terminally_classified_claim_count"):
        if count_key in matrix and matrix[count_key] != len(claims):
            fail(f"{label} {count_key} differs from claims")
    for open_key in ("epistemic_open_count", "open_claim_count"):
        if open_key in matrix and matrix[open_key] != recomputed["OPEN"]:
            fail(f"{label} {open_key} differs from claims")
    if "unclassified_claim_count" in matrix and matrix["unclassified_claim_count"] != 0:
        fail(f"{label} unclassified_claim_count must equal zero")
    return {
        "matrix_claim_count_recomputed": len(claims),
        "matrix_epistemic_counts_recomputed": recomputed,
        "claim_ids_unique_within_subject": True,
    }


def classify_index_matrix_discrepancy(
    subject_id: str,
    historical_index_claim_count: int,
    historical_index_counts: Mapping[str, int],
    matrix_claim_count: int,
    matrix_counts: Mapping[str, int],
) -> dict[str, Any] | None:
    """Accept only the one exact byte-frozen historical summary discrepancy."""
    if subject_id == KNOWN_INDEX_DISCREPANCY_SUBJECT:
        if (
            historical_index_claim_count != 39
            or matrix_claim_count != 39
            or dict(historical_index_counts) != KNOWN_INDEX_DISCREPANCY_SUMMARY
            or dict(matrix_counts) != KNOWN_MATRIX_RECOMPUTED_SUMMARY
        ):
            fail("known historical index discrepancy no longer matches its exact pin")
        return {
            "discrepancy_id": (
                "HISTORICAL-INDEX-CLASSIFICATION-SUMMARY-"
                "SUBJECT-2581811b342e505d"
            ),
            "subject_id": subject_id,
            "historical_index_claim_count": historical_index_claim_count,
            "historical_index_classification_summary": dict(historical_index_counts),
            "historical_index_summary_total": sum(historical_index_counts.values()),
            "matrix_claim_count_recomputed": matrix_claim_count,
            "matrix_epistemic_counts_recomputed": dict(matrix_counts),
            "matrix_summary_total_recomputed": sum(matrix_counts.values()),
            "claims_absent_from_historical_index_summary": (
                matrix_claim_count - sum(historical_index_counts.values())
            ),
            "historical_bytes_modified": False,
            "disposition": "DISCLOSED_NOT_REWRITTEN",
        }
    if dict(historical_index_counts) != dict(matrix_counts):
        fail(f"{subject_id} unrecognized index/matrix classification discrepancy")
    return None


def validate_owner_acceptance_boundary(value: Any) -> None:
    """Bind the owner-acceptance claims to their exact recorded scope."""
    if not isinstance(value, Mapping):
        fail("owner acceptance receipt must be an object")
    expected_principal = {
        "github_login": "ingolf-lohmann",
        "name": "Ingolf Lohmann",
        "role": "author_rights_holder_and_responsible_owner",
        "type": "NATURAL_PERSON",
    }
    if value.get("accepted_by") != expected_principal:
        fail("owner acceptance principal differs from the exact recorded owner")
    if (
        value.get("receipt_id")
        != "OWNER-ACCEPTANCE-SIX-VERSIONED-CORRECTED-CORPUS-CANDIDATES-20260730-V1"
        or value.get("scope_separation_verified") is not True
    ):
        fail("owner acceptance receipt identity or scope separation differs")
    non_authorizations = value.get("non_authorizations")
    if (
        not isinstance(non_authorizations, list)
        or non_authorizations.count("Zenodo upload, publication or record mutation")
        != 1
    ):
        fail("owner acceptance lacks the exact Zenodo non-authorization")
    completion = value.get("completion_claims")
    if (
        not isinstance(completion, Mapping)
        or completion.get("all_six_corrected_candidates_accepted") is not True
        or completion.get("zenodo_mutation_authorized") is not False
    ):
        fail("owner acceptance completion boundary differs")
    binding = value.get("candidate_binding")
    observed_return = identity(OWNER_RETURN_PATH)
    if (
        not isinstance(binding, Mapping)
        or binding.get("owner_return_package_path") != observed_return["path"]
        or binding.get("owner_return_package_sha256") != observed_return["sha256"]
        or binding.get("owner_return_package_git_blob_sha1")
        != observed_return["git_blob_sha1"]
        or binding.get("repository") != "Goldkelch/qik-vrt"
    ):
        fail("owner acceptance candidate binding differs from the current return package")


@contextlib.contextmanager
def output_directory_lock(
    root: pathlib.Path,
    relative_directory: str,
) -> Iterator[int]:
    """Serialize candidate verification/materialization on the real directory."""
    descriptor = open_repo_directory(root, relative_directory)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("candidate output directory is already locked by another run")
        except OSError as exc:
            fail(f"cannot lock candidate output directory: {exc.strerror}")
        yield descriptor
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _single_link_target_identity(
    directory_descriptor: int,
    name: str,
) -> tuple[int, int, int, int, int, int, int] | None:
    safe_upload_name(name, "generated output basename")
    try:
        status = os.stat(
            name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        fail(f"cannot inspect generated output {name}: {exc.strerror}")
    if not stat.S_ISREG(status.st_mode) or status.st_nlink != 1:
        fail(f"generated output must be a single-link regular file: {name}")
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_nlink,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _write_all(descriptor: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("atomic output write made no forward progress")
        view = view[written:]


def atomic_write_set(
    directory_descriptor: int,
    outputs: Mapping[str, bytes],
    *,
    commit_marker: str,
) -> None:
    """Atomically replace each prepared file; install the bundle marker last."""
    if commit_marker not in outputs:
        fail("atomic output set lacks its commit marker")
    names = list(outputs)
    if len(names) != len(set(names)):
        fail("atomic output basenames are not unique")
    for name, raw in outputs.items():
        safe_upload_name(name, "generated output basename")
        if not isinstance(raw, bytes):
            fail(f"generated output bytes are invalid: {name}")
    ordered_names = [name for name in names if name != commit_marker] + [commit_marker]
    initial = {
        name: _single_link_target_identity(directory_descriptor, name)
        for name in ordered_names
    }
    temporary: dict[str, str] = {}
    try:
        for name in ordered_names:
            temporary_name: str | None = None
            descriptor: int | None = None
            for _attempt in range(32):
                candidate = (
                    f".{name}.{os.getpid()}.{os.urandom(8).hex()}.qikvrt.tmp"
                )
                try:
                    descriptor = os.open(
                        candidate,
                        os.O_WRONLY
                        | os.O_CREAT
                        | os.O_EXCL
                        | os.O_NOFOLLOW
                        | getattr(os, "O_CLOEXEC", 0),
                        0o600,
                        dir_fd=directory_descriptor,
                    )
                except FileExistsError:
                    continue
                temporary_name = candidate
                break
            if descriptor is None or temporary_name is None:
                fail(f"cannot allocate atomic temporary output for {name}")
            temporary[name] = temporary_name
            try:
                opened = os.fstat(descriptor)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    fail(f"atomic temporary output is not single-link regular: {name}")
                os.fchmod(descriptor, 0o644)
                _write_all(descriptor, outputs[name])
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

        for name in ordered_names:
            if _single_link_target_identity(directory_descriptor, name) != initial[name]:
                fail(f"generated output changed during atomic materialization: {name}")
            os.replace(
                temporary[name],
                name,
                src_dir_fd=directory_descriptor,
                dst_dir_fd=directory_descriptor,
            )
            temporary.pop(name)
        os.fsync(directory_descriptor)
    except CorpusCandidateError:
        raise
    except OSError as exc:
        fail(f"atomic candidate output failed: {exc}")
    finally:
        for temporary_name in temporary.values():
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_name, dir_fd=directory_descriptor)


def verify_prepared_outputs(prepared: Mapping[str, bytes]) -> None:
    for raw_path, expected in prepared.items():
        safe = normalize_repo_relative(raw_path, "prepared output path")
        observed = read_stable_regular(ROOT, safe)
        if observed != expected:
            fail(f"stale or changed generated artifact: {safe}")


def index_and_candidates() -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
]:
    index = load_json(INDEX_PATH, "retrospective proof corpus index")
    if (
        index.get("schema") != "qikvrt_retrospective_proof_corpus_index_v1"
        or index.get("subject_count") != EXPECTED_SUBJECTS
        or index.get("claim_count") != EXPECTED_SOURCE_CLAIMS
        or index.get("explicit_open_claim_count") != EXPECTED_EXPLICIT_OPEN
    ):
        fail("retrospective proof corpus index boundary differs")
    subjects = index.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != EXPECTED_SUBJECTS:
        fail("retrospective proof corpus subject inventory differs")
    subject_ids = [
        validate_subject_id(item.get("subject_id"), "index subject_id")
        for item in subjects
        if isinstance(item, dict)
    ]
    if (
        len(subject_ids) != EXPECTED_SUBJECTS
        or len(set(subject_ids)) != EXPECTED_SUBJECTS
        or subject_ids != sorted(subject_ids)
    ):
        fail("retrospective proof corpus subject IDs are not unique and sorted")

    matrices: list[pathlib.Path] = []
    matrix_subjects: list[dict[str, Any]] = []
    recomputed_counts: Counter[str] = Counter()
    indexed_counts: Counter[str] = Counter()
    discrepancies: list[dict[str, Any]] = []
    for subject in subjects:
        subject_id = subject["subject_id"]
        matrix_path = verify_binding(
            subject.get("claim_matrix", {}),
            f"{subject_id} claim matrix",
        )
        matrix = load_json(matrix_path, f"{subject_id} claim matrix")
        inventory = inventory_matrix_claims(
            subject_id,
            matrix,
            f"{subject_id} claim matrix",
        )
        matrix_count = inventory["matrix_claim_count_recomputed"]
        matrix_counts = inventory["matrix_epistemic_counts_recomputed"]
        if subject.get("claim_count") != matrix_count:
            fail(f"{subject_id} claim count differs")
        index_counts = exact_epistemic_counts(
            subject.get("classification_summary"),
            f"{subject_id} index classification_summary",
        )
        discrepancy = classify_index_matrix_discrepancy(
            subject_id,
            subject["claim_count"],
            index_counts,
            matrix_count,
            matrix_counts,
        )
        if discrepancy is not None:
            discrepancies.append(discrepancy)
        recomputed_counts.update(matrix_counts)
        indexed_counts.update(index_counts)
        matrix_subjects.append(
            {
                "subject_id": subject_id,
                "claim_matrix": identity(matrix_path),
                "historical_index_claim_count": subject["claim_count"],
                "historical_index_classification_summary": index_counts,
                **inventory,
                "historical_index_discrepancy": (
                    subject_id == KNOWN_INDEX_DISCREPANCY_SUBJECT
                ),
            }
        )
        matrices.append(matrix_path)
    recomputed_claims = sum(recomputed_counts.values())
    recomputed_open = recomputed_counts["OPEN"]
    if (
        recomputed_claims != EXPECTED_SOURCE_CLAIMS
        or recomputed_open != EXPECTED_EXPLICIT_OPEN
    ):
        fail("retrospective proof corpus aggregate counts differ")
    historical_index_counts = exact_epistemic_counts(
        index.get("classification_summary"),
        "retrospective proof corpus index classification_summary",
    )
    normalized_indexed_counts = {
        classification: indexed_counts[classification]
        for classification in sorted(ALLOWED_EPISTEMIC_CLASSES)
    }
    if historical_index_counts != normalized_indexed_counts:
        fail("retrospective index aggregate classification summary differs from subjects")
    if len(discrepancies) != 1:
        fail("historical index discrepancy inventory is not exactly one")

    formal_subjects = sum(
        1
        for item in matrix_subjects
        if item["matrix_epistemic_counts_recomputed"]["FORMAL_PROVED"] > 0
    )
    source_inventory = {
        "inventory_method": (
            "Parse each of the 19 exact byte-bound matrix claims lists; require "
            "a unique non-empty claim_id within each subject, an allowed "
            "epistemic_class and the matrix subject_id binding; then count list "
            "entries without recursively revalidating their proofs or sources."
        ),
        "all_19_bound_matrices_parsed": True,
        "matrix_subject_count": len(matrix_subjects),
        "matrix_claim_count_recomputed": recomputed_claims,
        "matrix_explicit_open_claim_count_recomputed": recomputed_open,
        "matrix_epistemic_counts_recomputed": {
            classification: recomputed_counts[classification]
            for classification in sorted(ALLOWED_EPISTEMIC_CLASSES)
        },
        "matrix_subjects_with_formal_proved_labels_recomputed": formal_subjects,
        "historical_index_classification_summary": historical_index_counts,
        "historical_index_summary_total": sum(historical_index_counts.values()),
        "matrix_subjects": matrix_subjects,
        "historical_index_discrepancies": discrepancies,
        "historical_corpus_receipt_verification_claims_adopted": False,
        "historical_corpus_receipt_note": (
            "The byte-frozen historical receipt remains an uploaded artifact, but "
            "its all-counts/all-classification-counts recomputed assertions are not "
            "repeated or adopted because the pinned index summary discrepancy is "
            "visible in the exact historical bytes."
        ),
    }

    owner_return = load_json(OWNER_RETURN_PATH, "owner return package")
    owner_acceptance = load_json(OWNER_ACCEPTANCE_PATH, "owner acceptance receipt")
    validate_owner_acceptance_boundary(owner_acceptance)
    returned = owner_return.get("candidates")
    decisions = owner_acceptance.get("decisions")
    if (
        owner_return.get("schema")
        != "qikvrt_versioned_corrected_candidates_owner_return_v1"
        or not isinstance(returned, list)
        or len(returned) != EXPECTED_CORRECTIONS
        or owner_acceptance.get("state") != "ACCEPTED"
        or owner_acceptance.get("decision") != "ACCEPT"
        or not isinstance(decisions, list)
        or len(decisions) != EXPECTED_CORRECTIONS
    ):
        fail("six-candidate return/acceptance boundary differs")
    decision_by_subject = {
        validate_subject_id(item.get("subject_id"), "owner decision subject_id"): item
        for item in decisions
        if isinstance(item, dict)
    }
    if len(decision_by_subject) != EXPECTED_CORRECTIONS:
        fail("owner acceptance decision subjects are not unique and exact")
    archives: list[pathlib.Path] = []
    returned_by_subject: dict[str, dict[str, Any]] = {}
    for item in returned:
        if not isinstance(item, dict):
            fail("owner return candidate is invalid")
        subject_id = validate_subject_id(
            item.get("subject_id"),
            "owner return candidate subject_id",
        )
        archive_binding = item.get("candidate_archive", {})
        archive_path = verify_binding(archive_binding, f"{subject_id} candidate archive")
        decision = decision_by_subject.get(subject_id)
        if (
            not isinstance(decision, dict)
            or decision.get("decision") != "ACCEPT"
            or decision.get("candidate_archive_path") != archive_binding["path"]
            or decision.get("candidate_sha256") != archive_binding["sha256"]
        ):
            fail(f"{subject_id} exact owner acceptance differs")
        returned_by_subject[subject_id] = item
        archives.append(archive_path)
    if len(returned_by_subject) != EXPECTED_CORRECTIONS:
        fail("owner return subjects are not unique")

    candidates = [
        {**identity(INDEX_PATH), "name": INDEX_PATH.name, "role": "PRIMARY"},
        *[
            {
                **identity(path),
                "name": f"{subject['subject_id']}__CLAIM_MATRIX.json",
                "role": "SUPPLEMENT",
            }
            for subject, path in zip(subjects, matrices, strict=True)
        ],
        *[
            {
                **identity(path),
                "name": path.name,
                "role": "SUPPLEMENT",
            }
            for path in sorted(archives, key=lambda item: item.name)
        ],
    ]
    if len(candidates) != 1 + EXPECTED_SUBJECTS + EXPECTED_CORRECTIONS:
        fail("candidate file count differs")
    names = [item["name"] for item in candidates]
    paths = [item["path"] for item in candidates]
    for name_index, name in enumerate(names):
        safe_upload_name(name, f"candidate upload name {name_index}")
    if len(names) != len(set(names)) or len(paths) != len(set(paths)):
        fail("candidate upload names or paths are not unique")
    return index, owner_return, candidates, source_inventory


def corpus_auxiliary_paths(index: Mapping[str, Any]) -> list[tuple[pathlib.Path, str]]:
    values: list[tuple[pathlib.Path, str]] = []
    subjects = index["subjects"]
    for subject in subjects:
        receipt = subject.get("subject_receipt")
        if receipt is not None:
            values.append((verify_binding(receipt, f"{subject['subject_id']} receipt"), "EVIDENCE"))
    for correction in index.get("correction_requirements", []):
        if not isinstance(correction, dict):
            fail("correction requirement is invalid")
        validate_subject_id(
            correction.get("subject_id"),
            "correction requirement subject_id",
        )
        values.append(
            (
                verify_binding(
                    correction.get("decision", {}),
                    f"{correction.get('subject_id')} correction decision",
                ),
                "EVIDENCE",
            )
        )
    if len(values) != 13:
        fail("index-referenced auxiliary artifact count differs")
    return values


def correction_support_paths(owner_return: Mapping[str, Any]) -> list[tuple[pathlib.Path, str]]:
    values: list[tuple[pathlib.Path, str]] = [
        (CORPUS_RECEIPT_PATH, "EVIDENCE"),
        (OWNER_ACCEPTANCE_PATH, "EVIDENCE"),
        (OWNER_RETURN_PATH, "EVIDENCE"),
        (OWNER_RETURN_NOTICE_PATH, "CHANGE_NOTICE"),
    ]
    candidates = owner_return["candidates"]
    for item in sorted(candidates, key=lambda value: value["subject_id"]):
        subject_id = item["subject_id"]
        base = CORRECTIONS / subject_id
        receipt_path = base / "CANDIDATE_RECEIPT.json"
        review_path = base / "OWNER_REVIEW.md"
        receipt = load_json(receipt_path, f"{subject_id} candidate receipt")
        if (
            receipt.get("subject_id") != subject_id
            or receipt.get("candidate_archive") != item.get("candidate_archive")
        ):
            fail(f"{subject_id} candidate receipt differs from owner return")
        review = regular_bytes(review_path).decode("utf-8")
        archive = item["candidate_archive"]
        if archive["sha256"] not in review or archive["path"] not in review:
            fail(f"{subject_id} visible owner review lacks exact archive binding")
        values.extend(((receipt_path, "EVIDENCE"), (review_path, "CHANGE_NOTICE")))
    values.extend(
        (
            (EQUALITY_PATH, "EVIDENCE"),
            (EQUALITY_INDEX_PATH, "EVIDENCE"),
            (ROOT / "policy/zenodo-machine-proof-policy-v2.json", "OTHER"),
            (ROOT / "policy/qikvrt-zenodo-machine-proof-bundle-v2.schema.json", "OTHER"),
            (ROOT / "policy/qikvrt-prepublication-return-receipt-v2.schema.json", "OTHER"),
            (ROOT / "LICENSES/CC-BY-NC-ND-4.0.txt", "OTHER"),
        )
    )
    if len(values) != 22:
        fail("correction-support artifact count differs")

    equality = load_json(EQUALITY_PATH, "PR297/PR174 equality receipt")
    receipt_id = equality.get("receipt_id")
    equality_index = load_json(EQUALITY_INDEX_PATH, "equality receipt index")
    entries = equality_index.get("equality_receipts")
    matches = [
        item for item in entries or []
        if isinstance(item, dict) and item.get("receipt_id") == receipt_id
    ]
    if (
        equality.get("state") != "equality_verified_for_scoped_promotion"
        or len(matches) != 1
        or matches[0].get("path") != relative(EQUALITY_PATH)
        or matches[0].get("file_sha256") != identity(EQUALITY_PATH)["sha256"]
    ):
        fail("PR297/PR174 equality receipt is not exactly indexed")
    return values


def proof_artifact_specs(
    index: Mapping[str, Any], owner_return: Mapping[str, Any]
) -> list[tuple[pathlib.Path, str]]:
    specs = [
        *corpus_auxiliary_paths(index),
        *correction_support_paths(owner_return),
        (CLAIM_MATRIX_PATH, "CLAIM_MATRIX"),
        (RETURN_RECEIPT_PATH, "RETURN_RECEIPT"),
        (METADATA_PATH, "OTHER"),
    ]
    paths = [relative(path) for path, _kind in specs]
    if len(specs) != 38 or len(paths) != len(set(paths)):
        fail("proof artifact specification is not exactly 38 unique paths")
    return specs


def artifact_upload_name(path: pathlib.Path) -> str:
    relative_path = pathlib.PurePosixPath(relative(path))
    subject = next(
        (part for part in relative_path.parts if part.startswith("SUBJECT-")),
        None,
    )
    if subject and relative_path.name in {
        "SUBJECT_DISPOSITION_RECEIPT.json",
        "CONTENT_CHANGE_DECISION.json",
        "CANDIDATE_RECEIPT.json",
        "OWNER_REVIEW.md",
    }:
        return safe_upload_name(
            f"{validate_subject_id(subject, 'artifact subject')}__{relative_path.name}",
            "artifact upload name",
        )
    return safe_upload_name(relative_path.name, "artifact upload name")


def materialize_upload_contract(
    candidates: Sequence[Mapping[str, Any]],
    artifact_specs: Sequence[tuple[pathlib.Path, str]],
) -> dict[str, Any]:
    entries = [
        {
            "path": item["path"],
            "name": item["name"],
            "role": item["role"],
        }
        for item in candidates
    ]
    entries.extend(
        {
            "path": relative(path),
            "name": artifact_upload_name(path),
            "role": "PROOF_ARTIFACT",
        }
        for path, _kind in artifact_specs
    )
    entries.append(
        {
            "path": relative(PROOF_BUNDLE_PATH),
            "name": PROOF_BUNDLE_PATH.name,
            "role": "PROOF_BUNDLE",
        }
    )
    paths = [item["path"] for item in entries]
    names = [item["name"] for item in entries]
    for index, path in enumerate(paths):
        normalize_repo_relative(path, f"upload contract path {index}")
    for index, name in enumerate(names):
        safe_upload_name(name, f"upload contract name {index}")
    if (
        len(entries) != EXPECTED_UPLOADS
        or len(paths) != len(set(paths))
        or len(names) != len(set(names))
    ):
        fail("upload contract is not exactly 65 unique path/name mappings")
    return {
        "entry_count": len(entries),
        "ordered_entries": entries,
        "ordered_entries_canonical_sha256": canonical_json_sha256(entries),
    }


def validate_upload_contract(
    matrix: Mapping[str, Any], bundle: Mapping[str, Any]
) -> list[dict[str, str]]:
    contract = matrix.get("upload_contract")
    if not isinstance(contract, dict) or set(contract) != {
        "entry_count",
        "ordered_entries",
        "ordered_entries_canonical_sha256",
    }:
        fail("upload contract keys differ")
    entries = contract["ordered_entries"]
    if not isinstance(entries, list) or contract["entry_count"] != EXPECTED_UPLOADS:
        fail("upload contract entry count differs")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict) or set(item) != {"path", "name", "role"}:
            fail(f"upload contract entry {index} keys differ")
        if not all(isinstance(item[key], str) and item[key] for key in item):
            fail(f"upload contract entry {index} values must be non-empty text")
        normalize_repo_relative(item["path"], f"upload contract entry {index} path")
        safe_upload_name(item["name"], f"upload contract entry {index} name")
        if item["role"] not in {
            "PRIMARY",
            "SUPPLEMENT",
            "PROOF_ARTIFACT",
            "PROOF_BUNDLE",
        }:
            fail(f"upload contract entry {index} role is invalid")
        normalized.append(dict(item))
    if contract["ordered_entries_canonical_sha256"] != canonical_json_sha256(normalized):
        fail("upload contract canonical digest differs")
    paths = [item["path"] for item in normalized]
    names = [item["name"] for item in normalized]
    if (
        len(normalized) != EXPECTED_UPLOADS
        or len(paths) != len(set(paths))
        or len(names) != len(set(names))
    ):
        fail("upload contract path/name mappings are not unique")

    candidates = bundle["candidate"]["files"]
    artifacts = bundle["artifacts"]
    expected_paths = [
        *(item["path"] for item in candidates),
        *(item["path"] for item in artifacts),
        relative(PROOF_BUNDLE_PATH),
    ]
    expected_roles = [
        *(item["role"] for item in candidates),
        *("PROOF_ARTIFACT" for _item in artifacts),
        "PROOF_BUNDLE",
    ]
    if paths != expected_paths:
        fail("upload contract ordered paths differ from the machine-proof bundle")
    if [item["role"] for item in normalized] != expected_roles:
        fail("upload contract ordered roles differ from the machine-proof bundle")
    if names[: len(candidates)] != [item["name"] for item in candidates]:
        fail("upload contract candidate names differ from the machine-proof bundle")
    return normalized


def claim(
    claim_id: str,
    statement: str,
    classification: str,
    boundary: str,
    references: Sequence[tuple[str, pathlib.Path, str]],
) -> dict[str, Any]:
    if classification not in STATUS:
        fail(f"unsupported claim classification: {classification}")
    source_ids = [fragment for _kind, _path, fragment in references]
    if len(source_ids) != len(set(source_ids)):
        fail(f"claim {claim_id} source identifiers are not unique")
    return {
        "claim_id": claim_id,
        "statement": statement,
        "classification": classification,
        "status": STATUS[classification],
        "boundary": boundary,
        "proof_refs": [],
        "sources": source_ids,
        "source_references": [
            {
                "reference_kind": kind,
                "path": relative(path),
                "fragment": fragment,
            }
            for kind, path, fragment in references
        ],
    }


def materialize_claim_matrix(
    source_inventory: Mapping[str, Any],
    upload_contract: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = CORPUS_RECEIPT_PATH
    owner_return = OWNER_RETURN_PATH
    acceptance = OWNER_ACCEPTANCE_PATH
    equality = EQUALITY_PATH
    equality_index = EQUALITY_INDEX_PATH
    policy = ROOT / "policy/zenodo-machine-proof-policy-v2.json"
    claims = [
        claim(
            "CORPUS-SCOPE-001",
            "The retrospective corpus receipt binds one index containing 19 subjects.",
            "SOURCE_BOUND",
            "The claim is limited to the exact index and receipt bytes in this upload; it is not an assertion about every possible publication by the author.",
            (("source", receipt, "qikvrt_retrospective_proof_corpus_receipt_v1"),),
        ),
        claim(
            "CORPUS-CLAIMS-001",
            "A fresh inventory of the claims lists in the 19 exact byte-bound matrices contains 70,439 nested claim entries.",
            "SOURCE_BOUND",
            "The count is recomputed from list entries by this freeze; it is not inherited from the historical receipt and is not proof that every nested statement is true.",
            (("source", CLAIM_MATRIX_PATH, "matrix_claim_count_recomputed"),),
        ),
        claim(
            "CORPUS-OPEN-001",
            "The fresh matrix inventory observes 1,262 nested claims explicitly classified as OPEN.",
            "OPEN",
            "OPEN claims remain unresolved and may not be represented as established facts or mathematical theorems.",
            (
                (
                    "source",
                    CLAIM_MATRIX_PATH,
                    "matrix_explicit_open_claim_count_recomputed",
                ),
            ),
        ),
        claim(
            "CORPUS-MATRIX-BINDING-001",
            "Every one of the 19 byte-bound subject matrices was parsed and inventoried under the finite class and subject-binding checks declared by this freeze.",
            "SOURCE_BOUND",
            "This establishes exact byte identity and a fresh inventory; it does not claim that the historical index summaries are all consistent or that nested proofs were recursively revalidated.",
            (("source", CLAIM_MATRIX_PATH, "all_19_bound_matrices_parsed"),),
        ),
        claim(
            "CORPUS-INDEX-DISCREPANCY-001",
            "For SUBJECT-2581811b342e505d, the historical index declares 39 total claims but summarizes only 8 SOURCE_BOUND and zero in every other epistemic class; the bound matrix freshly inventories 20 EMPIRICALLY_EVIDENCED and 19 SOURCE_BOUND claims.",
            "SOURCE_BOUND",
            "This is the one exact recognized historical index/matrix classification-summary discrepancy. The historical index and receipt bytes are disclosed unchanged, and every other such discrepancy blocks the freeze.",
            (
                (
                    "source",
                    CLAIM_MATRIX_PATH,
                    "HISTORICAL-INDEX-CLASSIFICATION-SUMMARY-SUBJECT-2581811b342e505d",
                ),
            ),
        ),
        claim(
            "CORPUS-NESTED-VALIDATION-SCOPE-001",
            "The 70,439 nested matrix claims are historical dataset content and are not recursively revalidated or promoted by this corpus-level v2 bundle; in particular, its 160 observed FORMAL_PROVED labels across 7 subjects are not asserted here to have kernel-verified proof_refs.",
            "SOURCE_BOUND",
            "The v2 bundle gates apply only to the corpus-level claim projection in this generated matrix. There are zero corpus-level FORMAL_PROVED claims, so formal_claims_have_kernel_receipts does not attest the nested 160 labels.",
            (
                (
                    "source",
                    CLAIM_MATRIX_PATH,
                    "nested_formal_proved_labels_not_revalidated",
                ),
            ),
        ),
        claim(
            "CORPUS-HISTORY-001",
            "Building the proof corpus did not rewrite the observed historical public bytes.",
            "SOURCE_BOUND",
            "The later correction archives are new versioned candidates and do not alter old Zenodo records.",
            (("source", receipt, "historical_public_bytes_rewritten"),),
        ),
        claim(
            "CORPUS-CORRECTIONS-001",
            "Six exact versioned correction archives were returned for owner decision.",
            "SOURCE_BOUND",
            "The assertion concerns only the six archive identities in the owner return package.",
            (("source", owner_return, "qikvrt_versioned_corrected_candidates_owner_return_v1"),),
        ),
        claim(
            "CORPUS-CORRECTIONS-ACCEPTED-001",
            "Ingolf Lohmann accepted the six exact correction archive SHA-256 identities recorded in the owner acceptance receipt.",
            "SOURCE_BOUND",
            "The repository receipt records a platform-mediated owner decision; it is not biometric or cryptographic proof of natural-person identity.",
            (("source", acceptance, "OWNER-ACCEPTANCE-SIX-VERSIONED-CORRECTED-CORPUS-CANDIDATES-20260730-V1"),),
        ),
        claim(
            "CORPUS-ACCEPTANCE-BOUNDARY-001",
            "The correction acceptance did not authorize a Zenodo upload, publication, or record mutation.",
            "SOURCE_BOUND",
            "A separate exact byte-bound upload authorization is required after this corpus freeze is returned.",
            (("source", acceptance, "Zenodo upload, publication or record mutation"),),
        ),
        claim(
            "CORPUS-EQUALITY-001",
            "The PR297/PR174 receipt verifies Authority/Mirror equality for its scoped correction promotion.",
            "SOURCE_BOUND",
            "The equality claim is restricted to the receipt's named promotion scope and does not establish repository-wide current equality.",
            (("source", equality, "promotion_2026-08-01_batch003_six_versioned_corrections_pr297_pr174"),),
        ),
        claim(
            "CORPUS-EQUALITY-INDEX-001",
            "The PR297/PR174 equality receipt is registered by its exact receipt identifier in the repository evidence index.",
            "SOURCE_BOUND",
            "Index membership proves discoverability of that receipt, not a new external effect.",
            (("source", equality_index, "authority-mirror-equality-2026-08-01-batch003-six-versioned-corrections-pr297-pr174"),),
        ),
        claim(
            "CORPUS-POLICY-001",
            "This freeze uses the active v2 machine-proof-before-publication policy.",
            "NORMATIVE",
            "The policy governs this repository publication path and does not itself prove scientific source claims.",
            (("source", policy, "qikvrt-zenodo-machine-proof-before-publication-v2"),),
        ),
        claim(
            "CORPUS-EXACT-UPLOAD-001",
            "The intended production file set must contain exactly the proof-bearing paths and no extras.",
            "NORMATIVE",
            "This is an upload-control requirement; it is not evidence that the upload has occurred.",
            (("source", policy, "EXACT_UPLOAD_SET_ONLY_NO_EXTRAS"),),
        ),
        claim(
            "CORPUS-PUBLIC-VERIFY-001",
            "A future publication acknowledgement requires public byte-exact redownload verification.",
            "NORMATIVE",
            "Until the public record and every uploaded byte are reverified, the publication effect remains incomplete.",
            (("source", policy, "NO_PUBLIC_BYTE_EXACT_REDOWNLOAD_NO_ZENODO_ACK"),),
        ),
        claim(
            "CORPUS-PUBLICATION-OPEN-001",
            "Publication of this retrospective proof corpus on Zenodo is not established by the prepublication repository receipts.",
            "OPEN",
            "Only a public Zenodo record plus exact redownload evidence can close this claim.",
            (("source", receipt, "BUILT_AND_VERIFIED_PUBLICATION_NOT_AUTHORIZED"),),
        ),
        claim(
            "CORPUS-EPISTEMIC-BOUNDARY-001",
            "Archival fixity, source attribution and claim disposition do not by themselves establish peer review, empirical truth, field consensus or universal validity.",
            "INTERPRETATIVE",
            "Each nested claim keeps its own epistemic classification; this corpus-level boundary does not promote OPEN or interpretative statements.",
            (),
        ),
    ]
    counts = Counter(item["classification"] for item in claims)
    return {
        "_license": {**LICENSE, "classification": "machine_readable_claim_matrix"},
        "schema": "qikvrt_retrospective_proof_corpus_claim_matrix_v3",
        "publication_id": PUBLICATION_ID,
        "author": "Ingolf Lohmann",
        "source_corpus_receipt": identity(CORPUS_RECEIPT_PATH),
        "source_inventory_counts": {
            "subjects": EXPECTED_SUBJECTS,
            "claims": EXPECTED_SOURCE_CLAIMS,
            "explicit_open_claims": EXPECTED_EXPLICIT_OPEN,
            "accepted_correction_archives": EXPECTED_CORRECTIONS,
            "basis": "fresh_matrix_claim_list_inventory",
        },
        "source_inventory_recomputation": dict(source_inventory),
        "nested_claim_validation_scope": {
            "nested_claims_are_historical_dataset_content": True,
            "nested_matrix_claim_count_recomputed": source_inventory[
                "matrix_claim_count_recomputed"
            ],
            "nested_claims_recursively_revalidated_by_this_bundle": False,
            "nested_claims_promoted_by_this_bundle": False,
            "nested_formal_proved_labels_observed": source_inventory[
                "matrix_epistemic_counts_recomputed"
            ]["FORMAL_PROVED"],
            "nested_subjects_with_formal_proved_labels_observed": source_inventory[
                "matrix_subjects_with_formal_proved_labels_recomputed"
            ],
            "nested_formal_proved_labels_not_revalidated": True,
            "nested_formal_proved_proof_refs_kernel_verified_by_this_bundle": False,
            "corpus_level_formal_proved_claims": 0,
            "formal_claims_have_kernel_receipts_gate_scope": (
                "corpus_level_claim_projection_only"
            ),
        },
        "upload_contract": dict(upload_contract),
        "claim_count": len(claims),
        "epistemic_counts": dict(sorted(counts.items())),
        "claims": claims,
        "completion_claims": {
            "all_corpus_level_claims_dispositioned": True,
            "source_claims_promoted_to_formal_proofs": False,
            "nested_matrix_claims_recursively_revalidated": False,
            "nested_formal_proved_labels_kernel_revalidated": False,
            "historical_receipt_count_verification_adopted": False,
            "zenodo_published": False,
            "public_redownload_verified": False,
            "global_pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def materialize_metadata(source_inventory: Mapping[str, Any]) -> dict[str, Any]:
    recomputed = source_inventory["matrix_epistemic_counts_recomputed"]
    return {
        "title": (
            "QIK-VRT Retrospective Proof Corpus: 19 subjects and 70,439 "
            "machine-readable claim dispositions"
        ),
        "upload_type": "dataset",
        "description": (
            "Retrospective, machine-readable evidence corpus for 19 byte-distinct "
            "QIK-VRT Zenodo claim subjects. Fresh parsing of the nineteen exact "
            "byte-bound matrix claims lists yields 70,439 nested entries, including "
            "1,262 OPEN and 160 FORMAL_PROVED labels. The historical index has one "
            "explicitly disclosed discrepancy: SUBJECT-2581811b342e505d declares "
            "39 total claims but its classification summary contains only 8 "
            "SOURCE_BOUND and zero in all other classes, while the bound matrix "
            "recomputes to 20 EMPIRICALLY_EVIDENCED plus 19 SOURCE_BOUND. Those "
            "historical index and receipt bytes remain unchanged. The v2 bundle "
            "validates only its corpus-level claim projection; it does not "
            "recursively revalidate or promote the 70,439 nested claims and does "
            "not assert that the 160 FORMAL_PROVED labels across 7 subjects have "
            "kernel-verified proof_refs. Six separately returned and accepted "
            "versioned correction archives are also included."
        ),
        "creators": [{"name": "Lohmann, Ingolf"}],
        "version": "3.0.0",
        "publication_date": "2026-08-03",
        "access_right": "open",
        "license": "cc-by-nc-nd-4.0",
        "language": "eng",
        "keywords": [
            "QIK-VRT",
            "machine-verifiable science",
            "claim disposition",
            "proof corpus",
            "provenance",
            "EFFECT_ACK",
            "Zenodo",
        ],
        "notes": (
            "Dataset-level proof is bounded to exact repository bytes and a fresh "
            f"matrix inventory (EMPIRICALLY_EVIDENCED={recomputed['EMPIRICALLY_EVIDENCED']}, "
            f"FORMAL_PROVED={recomputed['FORMAL_PROVED']}, "
            f"INTERPRETATIVE={recomputed['INTERPRETATIVE']}, "
            f"NORMATIVE={recomputed['NORMATIVE']}, OPEN={recomputed['OPEN']}, "
            f"SOURCE_BOUND={recomputed['SOURCE_BOUND']}). The historical corpus "
            "receipt remains a byte-frozen artifact, but this freeze does not adopt "
            "its all-counts or all-classification-counts recomputed assertions. "
            "The six correction ZIPs are new versioned candidates; historical "
            "Zenodo records remain unchanged. Public publication and byte-exact "
            "redownload verification are separate effects."
        ),
        "prereserve_doi": True,
    }


def candidate_set_canonical_sha256(
    candidates: Sequence[Mapping[str, Any]],
) -> str:
    exact = [
        {key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")}
        for item in candidates
    ]
    return canonical_json_sha256(exact)


def validate_utc_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str) or UTC_TIMESTAMP.fullmatch(value) is None:
        fail(f"{label} must use exact UTC YYYY-MM-DDTHH:MM:SSZ form")
    try:
        parsed = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        fail(f"{label} must be a real UTC calendar timestamp")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        fail(f"{label} is not a canonical UTC timestamp")
    return value


def validate_return_event(
    event: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> dict[str, str]:
    required = {
        "_license",
        "schema",
        "publication_id",
        "candidate_set_canonical_sha256",
        "returned_at",
        "repository_recorded_conversation_handoff_assertion",
        "independent_external_proof",
    }
    if set(event) != required:
        fail("return event keys differ")
    if (
        event.get("_license")
        != {
            **LICENSE,
            "classification": "machine_readable_repository_recorded_return_event",
        }
        or event.get("schema") != "qikvrt_repository_recorded_return_event_v1"
        or event.get("publication_id") != PUBLICATION_ID
        or event.get("candidate_set_canonical_sha256")
        != candidate_set_canonical_sha256(candidates)
        or event.get("repository_recorded_conversation_handoff_assertion") is not True
        or event.get("independent_external_proof") is not False
    ):
        fail("return event does not exactly bind this repository-recorded handoff")
    returned_at = validate_utc_timestamp(
        event.get("returned_at"),
        "return event returned_at",
    )
    return {
        "returned_at": returned_at,
        "return_channel": (
            "Repository-recorded exact-candidate Codex conversation handoff "
            "assertion; this receipt is not independent external evidence of "
            "delivery or natural-person identity."
        ),
    }


def materialize_return_receipt(
    candidates: Sequence[Mapping[str, Any]],
    return_event: Mapping[str, Any],
) -> dict[str, Any]:
    validated_event = validate_return_event(return_event, candidates)
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_prepublication_return_receipt",
        },
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": False,
        "original_files": [],
        "candidate_files": [
            {key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")}
            for item in candidates
        ],
        "changed_claim_ids": [],
        "change_reasons": [],
        "change_notice_path": None,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": validated_event["return_channel"],
            "returned_at": validated_event["returned_at"],
            "visible_change_notice_returned": False,
        },
    }


def artifact_entry(
    path: pathlib.Path,
    kind: str,
    prepared: Mapping[str, bytes],
) -> dict[str, str]:
    raw_path = relative(path)
    observed = (
        identity_from_bytes(path, prepared[raw_path])
        if raw_path in prepared
        else identity(path)
    )
    return {
        "path": observed["path"],
        "sha256": observed["sha256"],
        "git_blob_sha1": observed["git_blob_sha1"],
        "kind": kind,
    }


def materialize_artifacts(
    specs: Sequence[tuple[pathlib.Path, str]],
    prepared: Mapping[str, bytes],
) -> list[dict[str, str]]:
    artifacts = [artifact_entry(path, kind, prepared) for path, kind in specs]
    artifact_paths = [item["path"] for item in artifacts]
    if len(artifacts) != 38 or len(artifact_paths) != len(set(artifact_paths)):
        fail("proof artifact set is not exactly 38 unique paths")
    return artifacts


def materialize_bundle(
    matrix: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    artifact_paths = {item["path"] for item in artifacts}
    bundle_claims: list[dict[str, Any]] = []
    for matrix_claim in matrix["claims"]:
        proof_refs: list[str] = []
        evidence_refs: list[str] = []
        source_refs: list[str] = []
        for reference in matrix_claim["source_references"]:
            target = f"{reference['path']}#{reference['fragment']}"
            if reference["path"] not in artifact_paths:
                fail(f"claim reference is not a proof artifact: {target}")
            if reference["reference_kind"] == "evidence":
                evidence_refs.append(target)
            elif reference["reference_kind"] == "source":
                source_refs.append(target)
            else:
                fail(f"unsupported claim reference kind: {target}")
        bundle_claims.append(
            {
                "claim_id": matrix_claim["claim_id"],
                "statement": matrix_claim["statement"],
                "classification": matrix_claim["classification"],
                "status": matrix_claim["status"],
                "publication_wording": WORDING[matrix_claim["classification"]],
                "scope": matrix_claim["boundary"],
                "proof_refs": proof_refs,
                "evidence_refs": evidence_refs,
                "source_refs": source_refs,
            }
        )
    policy_identity = identity(ROOT / "policy/zenodo-machine-proof-policy-v2.json")
    return {
        "_license": {**LICENSE, "classification": "machine_readable_proof_bundle"},
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "policy": {
            "id": "qikvrt-zenodo-machine-proof-before-publication-v2",
            "path": policy_identity["path"],
            "version": "2.0.0",
            "sha256": policy_identity["sha256"],
            "git_blob_sha1": policy_identity["git_blob_sha1"],
        },
        "publication_id": PUBLICATION_ID,
        "candidate": {
            "primary_document_path": relative(INDEX_PATH),
            "files": list(candidates),
        },
        "claims": bundle_claims,
        "artifacts": list(artifacts),
        "prepublication_return": {
            "content_changed": False,
            "candidate_returned_to_owner": True,
            "receipt_path": relative(RETURN_RECEIPT_PATH),
            "change_notice_path": None,
        },
        "gates": {
            "all_claims_dispositioned": True,
            "all_references_resolve": True,
            "candidate_frozen": True,
            "formal_claims_have_kernel_receipts": True,
            "open_claims_not_worded_as_facts": True,
            "proof_bundle_in_upload_fileset": True,
            "returned_bytes_equal_upload_bytes": True,
        },
        "completion_claims": {
            "machine_proof_complete": True,
            "zenodo_upload_authorized": True,
        },
    }


def upload_paths(bundle: Mapping[str, Any]) -> list[str]:
    paths = [
        *(item["path"] for item in bundle["candidate"]["files"]),
        *(item["path"] for item in bundle["artifacts"]),
        relative(PROOF_BUNDLE_PATH),
    ]
    if len(paths) != EXPECTED_UPLOADS or len(paths) != len(set(paths)):
        fail("exact upload path set is not 65 unique files")
    return paths


def upload_names(
    bundle: Mapping[str, Any], matrix: Mapping[str, Any]
) -> list[str]:
    return [
        item["name"] for item in validate_upload_contract(matrix, bundle)
    ]


def _validator_schema_contracts() -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}
    for key, raw_path in (
        (
            "machine_proof_bundle",
            "policy/qikvrt-zenodo-machine-proof-bundle-v2.schema.json",
        ),
        (
            "prepublication_return_receipt",
            "policy/qikvrt-prepublication-return-receipt-v2.schema.json",
        ),
    ):
        path = ROOT.joinpath(*pathlib.PurePosixPath(raw_path).parts)
        observed = identity(path)
        values[key] = {
            "path": observed["path"],
            "sha256": observed["sha256"],
            "git_blob_sha1": observed["git_blob_sha1"],
        }
    return values


def validate_validator_result(
    bundle: Mapping[str, Any],
    bundle_raw: bytes,
    result: Any,
) -> dict[str, Any]:
    """Require every field returned by the pinned validator to match locally."""
    expected_keys = {
        "schema",
        "publication_id",
        "path",
        "bytes",
        "sha256",
        "git_blob_sha1",
        "policy",
        "claim_count",
        "candidate_file_count",
        "artifact_count",
        "machine_proof_complete",
        "zenodo_upload_authorized",
    }
    if not isinstance(result, dict) or set(result) != expected_keys:
        fail("pinned machine-proof validator returned an inexact result shape")
    expected_policy = {
        **dict(bundle["policy"]),
        "schema_contracts": _validator_schema_contracts(),
    }
    expected = {
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "publication_id": PUBLICATION_ID,
        "path": relative(PROOF_BUNDLE_PATH),
        "bytes": len(bundle_raw),
        "sha256": hashlib.sha256(bundle_raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(bundle_raw),
        "policy": expected_policy,
        "claim_count": len(bundle["claims"]),
        "candidate_file_count": len(bundle["candidate"]["files"]),
        "artifact_count": len(bundle["artifacts"]),
        "machine_proof_complete": True,
        "zenodo_upload_authorized": True,
    }
    if result != expected:
        fail("pinned machine-proof validator result differs from exact local bytes")
    return dict(result)


def verify_machine_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    validator_raw = read_stable_regular(
        ROOT,
        VALIDATOR_REL,
        max_bytes=MAX_VALIDATOR_BYTES,
    )
    if (
        hashlib.sha256(validator_raw).hexdigest() != VALIDATOR_SHA256
        or git_blob_sha1(validator_raw) != VALIDATOR_GIT_BLOB_SHA1
    ):
        fail("exact v2 machine-proof validator source binding differs")
    namespace: dict[str, Any] = {
        "__name__": "qikvrt_zenodo_machine_proof_exact",
        "__file__": str(ROOT.joinpath(*pathlib.PurePosixPath(VALIDATOR_REL).parts)),
        "__package__": None,
    }
    try:
        code = compile(
            validator_raw,
            namespace["__file__"],
            "exec",
            dont_inherit=True,
            optimize=0,
        )
        exec(code, namespace)
        validate_bundle = namespace.get("validate_bundle")
        if not callable(validate_bundle):
            fail("pinned machine-proof validator lacks validate_bundle")
        result = validate_bundle(
            ROOT,
            PROOF_BUNDLE_PATH,
            upload_paths=upload_paths(bundle),
        )
    except KeyboardInterrupt:
        raise
    except CorpusCandidateError:
        raise
    except BaseException as exc:
        fail(f"pinned machine-proof validation blocked: {exc}")
    bundle_raw = regular_bytes(PROOF_BUNDLE_PATH, MAX_JSON_BYTES)
    expected_bundle_raw = json_bytes(bundle)
    if bundle_raw != expected_bundle_raw:
        fail("machine-proof bundle changed during pinned validation")
    return validate_validator_result(bundle, bundle_raw, result)


def validate_all_upload_json(
    matrix: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> None:
    """Reject ambiguous/non-strict JSON anywhere in the exact upload set."""
    for entry in validate_upload_contract(matrix, bundle):
        raw_path = normalize_repo_relative(entry["path"], "upload JSON path")
        if pathlib.PurePosixPath(raw_path).suffix.lower() == ".json":
            parse_json_bytes(
                read_stable_regular(ROOT, raw_path, max_bytes=MAX_JSON_BYTES),
                f"upload JSON {raw_path}",
            )


def verify_upload_identity_snapshot(
    bundle: Mapping[str, Any],
    validator_result: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Reobserve all 65 paths after validation and bind every current identity."""
    snapshot: dict[str, dict[str, Any]] = {}
    for role, entries in (
        ("candidate", bundle["candidate"]["files"]),
        ("artifact", bundle["artifacts"]),
    ):
        for index, expected in enumerate(entries):
            if not isinstance(expected, Mapping):
                fail(f"{role} upload identity {index} is not an object")
            raw_path = normalize_repo_relative(
                expected.get("path"),
                f"{role} upload identity {index} path",
            )
            if raw_path in snapshot:
                fail(f"duplicate post-validator upload path: {raw_path}")
            path = ROOT.joinpath(*pathlib.PurePosixPath(raw_path).parts)
            observed = identity(path)
            required_fields = ("sha256", "git_blob_sha1")
            if role == "candidate":
                required_fields = ("bytes", *required_fields)
            if observed["path"] != raw_path or any(
                expected.get(key) != observed[key] for key in required_fields
            ):
                fail(
                    f"{role} upload identity changed after pinned validation: "
                    f"{raw_path}"
                )
            snapshot[raw_path] = observed

    bundle_path = relative(PROOF_BUNDLE_PATH)
    if bundle_path in snapshot:
        fail("machine-proof bundle overlaps a bound upload identity")
    observed_bundle = identity(PROOF_BUNDLE_PATH)
    if (
        validator_result.get("path") != bundle_path
        or validator_result.get("bytes") != observed_bundle["bytes"]
        or validator_result.get("sha256") != observed_bundle["sha256"]
        or validator_result.get("git_blob_sha1") != observed_bundle["git_blob_sha1"]
    ):
        fail("machine-proof bundle identity changed after pinned validation")
    snapshot[bundle_path] = observed_bundle
    expected_paths = upload_paths(bundle)
    if list(snapshot) != expected_paths or len(snapshot) != EXPECTED_UPLOADS:
        fail("post-validator identity snapshot differs from the exact upload order")
    return snapshot


def digest_report(
    metadata: Mapping[str, Any],
    matrix: Mapping[str, Any],
    bundle: Mapping[str, Any],
    identity_snapshot: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    contract = validate_upload_contract(matrix, bundle)
    paths = [item["path"] for item in contract]
    names = upload_names(bundle, matrix)
    if list(identity_snapshot) != paths:
        fail("digest report identity snapshot order differs from upload contract")
    total_bytes = sum(identity_snapshot[path]["bytes"] for path in paths)
    metadata_identity = identity_snapshot[relative(METADATA_PATH)]
    return_identity = identity_snapshot[relative(RETURN_RECEIPT_PATH)]
    bundle_identity = identity_snapshot[relative(PROOF_BUNDLE_PATH)]
    report = {
        "publication_id": PUBLICATION_ID,
        "upload_count": len(paths),
        "upload_bytes": total_bytes,
        "return_sha256": return_identity["sha256"],
        "metadata_sha256": canonical_json_sha256(metadata),
        "metadata_file_sha256": metadata_identity["sha256"],
        "machine_proof_sha256": bundle_identity["sha256"],
        "upload_contract_sha256": matrix["upload_contract"][
            "ordered_entries_canonical_sha256"
        ],
        "upload_names_unique": len(names) == len(set(names)),
    }
    report["old_authorization_exact_match"] = (
        report["return_sha256"] == OLD_AUTHORIZED_RETURN_SHA256
        and report["metadata_sha256"] == OLD_AUTHORIZED_METADATA_SHA256
        and report["machine_proof_sha256"] == OLD_AUTHORIZED_MACHINE_PROOF_SHA256
    )
    return report


def materialize(
    check: bool,
    return_event: Mapping[str, Any] | None,
) -> dict[str, Any]:
    index, owner_return, candidates, source_inventory = index_and_candidates()
    if return_event is None:
        fail(
            "no frozen repository-recorded conversation return event was supplied; "
            "final hashes are not authorizable"
        )
    artifact_specs = proof_artifact_specs(index, owner_return)
    upload_contract = materialize_upload_contract(candidates, artifact_specs)
    matrix = materialize_claim_matrix(source_inventory, upload_contract)
    metadata = materialize_metadata(source_inventory)
    return_receipt = materialize_return_receipt(candidates, return_event)
    prepared = {
        relative(CLAIM_MATRIX_PATH): json_bytes(matrix),
        relative(METADATA_PATH): json_bytes(metadata),
        relative(RETURN_RECEIPT_PATH): json_bytes(return_receipt),
    }
    artifacts = materialize_artifacts(artifact_specs, prepared)
    candidate_paths = {item["path"] for item in candidates}
    artifact_paths = {item["path"] for item in artifacts}
    if candidate_paths & artifact_paths:
        fail("candidate and proof artifact roles overlap")
    bundle = materialize_bundle(matrix, candidates, artifacts)
    prepared[relative(PROOF_BUNDLE_PATH)] = json_bytes(bundle)
    expected_paths = [relative(path) for path in OUTPUT_PATHS]
    if list(prepared) != expected_paths:
        fail("prepared output order differs from the exact four-file contract")
    outputs = {
        pathlib.PurePosixPath(raw_path).name: prepared[raw_path]
        for raw_path in expected_paths
    }
    with output_directory_lock(ROOT, PUBLICATION_REL.as_posix()) as directory_descriptor:
        if not check:
            atomic_write_set(
                directory_descriptor,
                outputs,
                commit_marker=PROOF_BUNDLE_PATH.name,
            )
        verify_prepared_outputs(prepared)
        validate_all_upload_json(matrix, bundle)
        validator_result = verify_machine_bundle(bundle)
        # A pinned validator is still code; require a second exact readback after it.
        verify_prepared_outputs(prepared)
        identity_snapshot = verify_upload_identity_snapshot(bundle, validator_result)
        return digest_report(
            metadata,
            matrix,
            bundle,
            identity_snapshot,
        )


def print_report(report: Mapping[str, Any], check: bool) -> None:
    action = "verified" if check else "materialized"
    print(
        f"PASS {action} retrospective proof corpus v3: "
        f"{report['upload_count']} uploads, {report['upload_bytes']} bytes"
    )
    print("RETURN_SHA256=" + str(report["return_sha256"]))
    print("METADATA_SHA256=" + str(report["metadata_sha256"]))
    print("MACHINE_PROOF_SHA256=" + str(report["machine_proof_sha256"]))
    print("UPLOAD_CONTRACT_SHA256=" + str(report["upload_contract_sha256"]))
    if report["old_authorization_exact_match"]:
        print("OLD_AUTHORIZATION_ORACLE=EXACT_MATCH")
    else:
        print("OLD_AUTHORIZATION_ORACLE=MISMATCH_NEW_AUTHORIZATION_REQUIRED")
        print(
            "NEW_AUTHORIZATION_TEMPLATE=AUTHORIZE_EXACT_UPLOAD "
            f"authorization_id={SUGGESTED_AUTHORIZATION_ID} "
            f"publication_id={PUBLICATION_ID} "
            f"return_sha256={report['return_sha256']} "
            f"metadata_sha256={report['metadata_sha256']} "
            f"machine_proof_sha256={report['machine_proof_sha256']}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze the retrospective proof corpus Zenodo v3 candidate"
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--return-event",
        type=pathlib.Path,
        help=(
            "frozen JSON input recording the exact-candidate conversation handoff; "
            "without it no final authorization hashes are emitted"
        ),
    )
    parser.add_argument(
        "--require-old-authorization-match",
        action="store_true",
        help="fail unless all three rebuilt digests equal the old owner statement",
    )
    args = parser.parse_args(argv)
    try:
        return_event = (
            load_json(args.return_event, "repository-recorded return event")
            if args.return_event is not None
            else None
        )
        report = materialize(args.check, return_event)
    except CorpusCandidateError as exc:
        raise SystemExit("BLOCK " + str(exc)) from exc
    print_report(report, args.check)
    if args.require_old_authorization_match and not report["old_authorization_exact_match"]:
        raise SystemExit(
            "BLOCK rebuilt candidate differs from the exact old owner authorization"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
