#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Two-phase, fail-closed Zenodo publication client for GitHub Actions.

The client deliberately has no command-line token option.  It reads the bearer
token only from ``ZENODO_ACCESS_TOKEN``, never serializes it, never places it in
a URL, and never follows redirects.  ``reserve`` creates the two editable
depositions and records their server-assigned identifiers/DOIs.  ``finalize``
reconciles both drafts to an exact, hash-bound manifest before publishing the
paper first and the software second.

This module uses only the Python standard library so that the release workflow
does not need to execute code obtained from a package index.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import hmac
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any


DEFAULT_BASE_URL = "https://zenodo.org/api"
TOKEN_ENVIRONMENT_VARIABLE = "ZENODO_ACCESS_TOKEN"
ALLOWED_ORIGINS = frozenset(
    {"https://zenodo.org", "https://sandbox.zenodo.org"}
)
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_UPLOAD_BYTES = 512 * 1024 * 1024
USER_AGENT = "qik-vrt-effect-ack-zenodo-actions/1"
EXPECTED_RELEASE_ID = "2026-07-22-effect-ack-universality-1.0.0"
EXPECTED_REPOSITORIES = ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt")
EXPECTED_TAG = "v2026.07.22-effect-ack-universality-1.0.0"
EXPECTED_SOFTWARE_SOURCE_RECORD_ID = 21488116
EXPECTED_SOFTWARE_CONCEPT_RECORD_ID = 21488115
SOFTWARE_ARCHIVE_SENTINEL = "DO_NOT_UPLOAD__GENERATED_SOFTWARE_ARCHIVE_REQUIRED.txt"
SAFE_RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_TAG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
HEX_32 = re.compile(r"^[0-9a-f]{32}$")
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
DOI = re.compile(r"^10\.[0-9]{4,9}/[-._;()/:A-Za-z0-9]+$")


class ZenodoError(RuntimeError):
    """A safe-to-report, fail-closed publication error."""


class SafeArgumentParser(argparse.ArgumentParser):
    """Reject malformed CLI input without reflecting possible secret values."""

    def error(self, message: str) -> None:
        del message
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: invalid arguments\n")


@dataclasses.dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Make every redirect visible to the caller instead of forwarding auth."""

    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> None:
        return None


def _origin(parts: urllib.parse.SplitResult) -> str:
    host = parts.hostname or ""
    return f"{parts.scheme}://{host}"


def validate_base_url(raw: str) -> str:
    """Return a canonical, allowlisted Zenodo API base URL."""
    parts = urllib.parse.urlsplit(raw)
    if (
        parts.scheme != "https"
        or _origin(parts) not in ALLOWED_ORIGINS
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
        or parts.query
        or parts.fragment
        or parts.path.rstrip("/") != "/api"
    ):
        raise ZenodoError("base URL must be an allowlisted Zenodo HTTPS /api URL")
    return _origin(parts) + "/api"


def validate_response_url(raw: str, base_url: str) -> str:
    """Validate a server-provided API/file link before attaching credentials."""
    candidate = urllib.parse.urljoin(base_url.rstrip("/") + "/", raw)
    parts = urllib.parse.urlsplit(candidate)
    base = urllib.parse.urlsplit(base_url)
    if (
        parts.scheme != "https"
        or _origin(parts) != _origin(base)
        or parts.username is not None
        or parts.password is not None
        or parts.port not in (None, 443)
        or parts.query
        or parts.fragment
        or not (parts.path == "/api" or parts.path.startswith("/api/"))
    ):
        raise ZenodoError("server returned a non-allowlisted Zenodo API URL")
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, "", "")
    )


def redact(text: str, token: str) -> str:
    """Remove bearer/query credentials from diagnostics."""
    value = str(text)
    if token:
        value = value.replace(token, "[REDACTED]")
    value = re.sub(
        r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+",
        r"\1[REDACTED]",
        value,
    )
    value = re.sub(
        r"(?i)(access_token=)[^&\s]+", r"\1[REDACTED]", value
    )
    return value


class HttpTransport:
    """Bounded urllib transport that never follows redirects."""

    def __init__(self, token: str, base_url: str) -> None:
        self._token = token
        self._base_url = validate_base_url(base_url)
        self._opener = urllib.request.build_opener(NoRedirectHandler())

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> HttpResponse:
        if max_response_bytes < 0 or max_response_bytes > MAX_UPLOAD_BYTES:
            raise ZenodoError("invalid HTTP response size bound")
        safe_url = validate_response_url(url, self._base_url)
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self._token,
            "User-Agent": USER_AGENT,
        }
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(
            safe_url, data=body, headers=headers, method=method.upper()
        )
        try:
            response = self._opener.open(request, timeout=60)
        except urllib.error.HTTPError as exc:
            response_body = exc.read(min(max_response_bytes, MAX_RESPONSE_BYTES) + 1)
            if len(response_body) > MAX_RESPONSE_BYTES:
                raise ZenodoError("Zenodo error response exceeded the size limit")
            return HttpResponse(
                status=int(exc.code),
                headers=dict(exc.headers.items()) if exc.headers else {},
                body=response_body,
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            detail = redact(str(exc), self._token)[:500]
            raise ZenodoError(f"Zenodo transport failed: {detail}") from None
        with response:
            final_url = response.geturl()
            validate_response_url(final_url, self._base_url)
            response_body = response.read(max_response_bytes + 1)
            if len(response_body) > max_response_bytes:
                raise ZenodoError("Zenodo response exceeded the size limit")
            return HttpResponse(
                status=int(response.status),
                headers=dict(response.headers.items()),
                body=response_body,
            )


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _parse_json(response: HttpResponse, token: str) -> dict[str, Any]:
    if not response.body:
        return {}
    try:
        value = json.loads(response.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ZenodoError(
            f"Zenodo returned invalid JSON (HTTP {response.status})"
        ) from None
    if not isinstance(value, dict):
        raise ZenodoError("Zenodo returned a non-object JSON response")
    if token and token in json.dumps(value, ensure_ascii=False):
        raise ZenodoError("Zenodo response unexpectedly contained the access token")
    return value


def _response_detail(response: HttpResponse, token: str) -> str:
    try:
        parsed = _parse_json(response, token)
    except ZenodoError:
        return "response body omitted"
    candidate = parsed.get("message") or parsed.get("status") or "request rejected"
    return redact(str(candidate), token)[:500]


def _header(response: HttpResponse, name: str) -> str | None:
    lowered = name.lower()
    for key, value in response.headers.items():
        if key.lower() == lowered:
            return value
    return None


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int, float)):
        return not isinstance(value, float) or (
            value == value and value not in (float("inf"), float("-inf"))
        )
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in value.items()
        )
    return False


def _check_exact_keys(value: Mapping[str, Any], allowed: set[str], where: str) -> None:
    unknown = set(value) - allowed
    missing = allowed - set(value)
    if unknown or missing:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unknown=" + ",".join(sorted(unknown)))
        raise ZenodoError(f"invalid {where} keys ({'; '.join(details)})")


def _safe_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ZenodoError(f"{where} must be a positive integer")
    return value


def _relative_path(root: pathlib.Path, raw: str, *, must_exist: bool) -> pathlib.Path:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ZenodoError("manifest file path must be a non-empty string")
    relative = pathlib.PurePosixPath(raw)
    if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
        raise ZenodoError(f"unsafe repository-relative path: {raw}")
    lexical = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ZenodoError(f"path contains a symbolic link: {raw}")
    resolved_root = root.resolve()
    resolved = lexical.resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        raise ZenodoError(f"path escapes repository root: {raw}") from None
    if must_exist and not resolved.is_file():
        raise ZenodoError(f"manifest file is missing: {raw}")
    return resolved


def _external_path_in_root(
    root: pathlib.Path, raw: str, *, must_exist: bool
) -> pathlib.Path:
    candidate = pathlib.Path(raw)
    if candidate.is_absolute():
        try:
            relative = candidate.relative_to(root.resolve())
        except ValueError:
            raise ZenodoError("control/result path must stay inside repository root") from None
        raw = relative.as_posix()
    return _relative_path(root, raw, must_exist=must_exist)


def read_regular_file(path: pathlib.Path, max_bytes: int) -> bytes:
    """Read one non-symlink regular file through a single descriptor."""
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ZenodoError(f"cannot open regular file: {path.name}: {exc.strerror}") from None
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ZenodoError(f"not a regular file: {path.name}")
        if before.st_size > max_bytes:
            raise ZenodoError(f"file exceeds size limit: {path.name}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ZenodoError(f"file exceeds size limit: {path.name}")
        after = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if before_identity != after_identity or total != before.st_size:
            raise ZenodoError(f"file changed while being read: {path.name}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _load_json_file(path: pathlib.Path, token: str = "") -> tuple[dict[str, Any], bytes]:
    raw = read_regular_file(path, MAX_JSON_BYTES)
    if token and token.encode("utf-8") in raw:
        raise ZenodoError("control file contains the Zenodo access token")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ZenodoError(f"invalid JSON control file: {path.name}: {exc}") from None
    if not isinstance(value, dict):
        raise ZenodoError(f"JSON control file must contain an object: {path.name}")
    return value, raw


def _metadata_identity(metadata: Mapping[str, Any], where: str) -> dict[str, Any]:
    title = metadata.get("title")
    version = metadata.get("version")
    creators = metadata.get("creators")
    if not isinstance(title, str) or not title.strip():
        raise ZenodoError(f"{where}.metadata.title must be a non-empty string")
    if not isinstance(version, str) or not version.strip():
        raise ZenodoError(f"{where}.metadata.version must be a non-empty string")
    if not isinstance(creators, list) or not creators:
        raise ZenodoError(f"{where}.metadata.creators must be a non-empty list")
    if not all(
        isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and item["name"].strip()
        for item in creators
    ):
        raise ZenodoError(f"{where}.metadata.creators contains an invalid creator")
    return {"title": title, "version": version, "creators": creators}


def _validate_file_entry(
    value: Any, root: pathlib.Path, where: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ZenodoError(f"{where} must be an object")
    _check_exact_keys(
        value, {"path", "name", "size", "md5", "sha256"}, where
    )
    name = value["name"]
    if (
        not isinstance(name, str)
        or not name
        or pathlib.PurePosixPath(name).name != name
        or name in (".", "..")
        or any(ord(character) < 32 for character in name)
        or len(name.encode("utf-8")) > 255
    ):
        raise ZenodoError(f"{where}.name must be a safe basename")
    size = value["size"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ZenodoError(f"{where}.size must be a non-negative integer")
    md5 = value["md5"]
    sha256 = value["sha256"]
    if not isinstance(md5, str) or not HEX_32.fullmatch(md5):
        raise ZenodoError(f"{where}.md5 must be lowercase hexadecimal")
    if not isinstance(sha256, str) or not HEX_64.fullmatch(sha256):
        raise ZenodoError(f"{where}.sha256 must be lowercase hexadecimal")
    path = value["path"]
    _relative_path(root, path, must_exist=True)
    return {
        "path": path,
        "name": name,
        "size": size,
        "md5": md5,
        "sha256": sha256,
    }


def validate_manifest(
    value: dict[str, Any], root: pathlib.Path, *, final: bool
) -> dict[str, Any]:
    top_keys = {
        "schema_version",
        "release_id",
        "authorization",
        "paper",
        "software",
    }
    if final:
        top_keys.add("reserved_dois")
    _check_exact_keys(value, top_keys, "manifest")
    if value["schema_version"] != 1:
        raise ZenodoError("manifest.schema_version must equal 1")
    release_id = value["release_id"]
    if not isinstance(release_id, str) or not SAFE_RELEASE_ID.fullmatch(release_id):
        raise ZenodoError("manifest.release_id is unsafe")
    if release_id != EXPECTED_RELEASE_ID:
        raise ZenodoError("manifest.release_id is not the authorized EFFECT_ACK release")

    authorization = value["authorization"]
    if not isinstance(authorization, dict):
        raise ZenodoError("manifest.authorization must be an object")
    _check_exact_keys(authorization, {"repositories", "tag"}, "authorization")
    repositories = authorization["repositories"]
    tag = authorization["tag"]
    if (
        not isinstance(repositories, list)
        or not repositories
        or not all(
            isinstance(repository, str) and SAFE_REPOSITORY.fullmatch(repository)
            for repository in repositories
        )
        or len(repositories) != len(set(repositories))
    ):
        raise ZenodoError("authorization.repositories must be unique OWNER/REPO names")
    if not isinstance(tag, str) or not SAFE_TAG.fullmatch(tag):
        raise ZenodoError("authorization.tag is unsafe")
    if tuple(repositories) != EXPECTED_REPOSITORIES or tag != EXPECTED_TAG:
        raise ZenodoError("repository/tag authorization is outside the EFFECT_ACK release")

    normalized: dict[str, Any] = {
        "schema_version": 1,
        "release_id": release_id,
        "authorization": {"repositories": repositories, "tag": tag},
    }
    for kind in ("paper", "software"):
        section = value[kind]
        if not isinstance(section, dict):
            raise ZenodoError(f"manifest.{kind} must be an object")
        expected = {"metadata", "files"}
        if kind == "software":
            expected |= {"source_record_id", "concept_record_id"}
        _check_exact_keys(section, expected, kind)
        metadata = section["metadata"]
        if not isinstance(metadata, dict) or not _is_json_value(metadata):
            raise ZenodoError(f"{kind}.metadata must be a JSON object")
        _metadata_identity(metadata, kind)
        if kind == "paper" and metadata.get("prereserve_doi") is not True:
            raise ZenodoError("paper.metadata.prereserve_doi must equal true")
        raw_files = section["files"]
        if not isinstance(raw_files, list) or not (1 <= len(raw_files) <= 100):
            raise ZenodoError(f"{kind}.files must contain between 1 and 100 files")
        files = [
            _validate_file_entry(item, root, f"{kind}.files[{index}]")
            for index, item in enumerate(raw_files)
        ]
        if len({item["name"] for item in files}) != len(files):
            raise ZenodoError(f"{kind}.files contains duplicate upload names")
        if len({item["path"] for item in files}) != len(files):
            raise ZenodoError(f"{kind}.files contains duplicate repository paths")
        if (
            final
            and kind == "software"
            and any(item["name"] == SOFTWARE_ARCHIVE_SENTINEL for item in files)
        ):
            raise ZenodoError(
                "final software files still contain the generated-archive sentinel"
            )
        normalized[kind] = {"metadata": metadata, "files": files}
        if kind == "software":
            source = _safe_int(section["source_record_id"], "software.source_record_id")
            concept = _safe_int(
                section["concept_record_id"], "software.concept_record_id"
            )
            if source == concept:
                raise ZenodoError("software source and concept record IDs must differ")
            if (
                source != EXPECTED_SOFTWARE_SOURCE_RECORD_ID
                or concept != EXPECTED_SOFTWARE_CONCEPT_RECORD_ID
            ):
                raise ZenodoError("software source/concept IDs are not authorized")
            normalized[kind]["source_record_id"] = source
            normalized[kind]["concept_record_id"] = concept

    if final:
        dois = value["reserved_dois"]
        if not isinstance(dois, dict):
            raise ZenodoError("manifest.reserved_dois must be an object")
        _check_exact_keys(dois, {"paper", "software"}, "reserved_dois")
        for kind in ("paper", "software"):
            if not isinstance(dois[kind], str) or not DOI.fullmatch(dois[kind]):
                raise ZenodoError(f"reserved_dois.{kind} is not a valid DOI")
        normalized["reserved_dois"] = dict(dois)
    return normalized


def authorization_envelope(manifest: Mapping[str, Any]) -> dict[str, Any]:
    software = manifest["software"]
    return {
        "release_id": manifest["release_id"],
        "authorization": manifest["authorization"],
        "paper_identity": _metadata_identity(manifest["paper"]["metadata"], "paper"),
        "software_identity": _metadata_identity(software["metadata"], "software"),
        "software_source_record_id": software["source_record_id"],
        "software_concept_record_id": software["concept_record_id"],
    }


def _file_bytes(
    root: pathlib.Path, entry: Mapping[str, Any], token: str
) -> bytes:
    path = _relative_path(root, entry["path"], must_exist=True)
    data = read_regular_file(path, MAX_UPLOAD_BYTES)
    if token.encode("utf-8") in data:
        raise ZenodoError(f"upload file contains the Zenodo access token: {entry['name']}")
    if len(data) != entry["size"]:
        raise ZenodoError(f"size mismatch for upload file: {entry['name']}")
    if hashlib.md5(data).hexdigest() != entry["md5"]:  # noqa: S324 - transport checksum
        raise ZenodoError(f"MD5 mismatch for upload file: {entry['name']}")
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ZenodoError(f"SHA-256 mismatch for upload file: {entry['name']}")
    return data


def verify_manifest_files(
    manifest: Mapping[str, Any], root: pathlib.Path, token: str
) -> dict[tuple[str, str], bytes]:
    verified: dict[tuple[str, str], bytes] = {}
    for kind in ("paper", "software"):
        for entry in manifest[kind]["files"]:
            verified[(kind, entry["name"])] = _file_bytes(root, entry, token)
    return verified


def _doi_from_deposition(value: Mapping[str, Any], where: str) -> str:
    metadata = value.get("metadata")
    candidates: list[Any] = []
    if isinstance(metadata, dict):
        reserved = metadata.get("prereserve_doi")
        if isinstance(reserved, dict):
            candidates.append(reserved.get("doi"))
    # A new-version draft can still expose its predecessor's legacy ``doi``
    # alongside the authoritative newly-prereserved DOI.  Prefer the latter.
    candidates.append(value.get("doi"))
    if isinstance(metadata, dict):
        candidates.append(metadata.get("doi"))
    for candidate in candidates:
        if isinstance(candidate, str) and DOI.fullmatch(candidate):
            return candidate
    raise ZenodoError(f"{where} did not contain a server-reserved DOI")


def _record_id(value: Mapping[str, Any], where: str) -> int:
    raw = value.get("id")
    if isinstance(raw, str) and raw.isdecimal():
        raw = int(raw)
    return _safe_int(raw, f"{where}.id")


def _concept_id(value: Mapping[str, Any], where: str) -> int:
    raw = value.get("conceptrecid", value.get("concept_record_id"))
    if isinstance(raw, str) and raw.isdecimal():
        raw = int(raw)
    return _safe_int(raw, f"{where}.conceptrecid")


def _id_from_api_url(url: str, base_url: str, marker: str) -> int:
    safe = validate_response_url(url, base_url)
    path = urllib.parse.urlsplit(safe).path.rstrip("/")
    pattern = re.compile(re.escape(marker.rstrip("/")) + r"/([0-9]+)$")
    match = pattern.search(path)
    if not match:
        raise ZenodoError("Zenodo link did not identify the expected record type")
    return int(match.group(1))


def _metadata_matches(actual: Any, expected: Any) -> bool:
    """Compare every client-controlled value while allowing server-added keys."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _metadata_matches(actual[key], value)
            for key, value in expected.items()
        )
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _metadata_matches(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _published_metadata_matches(
    actual: Any, expected: Mapping[str, Any]
) -> bool:
    """Compare legacy deposit metadata to its public-record representation.

    Zenodo's public records API normalizes three legacy write fields and omits
    the DOI-reservation instruction.  All other client-controlled fields remain
    subject to the recursive exact-value comparison (server-added object keys
    are tolerated).
    """
    if not isinstance(actual, dict):
        return False
    resource_type = actual.get("resource_type")
    for key, expected_value in expected.items():
        if key == "prereserve_doi":
            continue
        if key == "license":
            license_value = actual.get("license")
            actual_value = (
                license_value.get("id")
                if isinstance(license_value, dict)
                else license_value
            )
        elif key == "upload_type":
            actual_value = (
                resource_type.get("type")
                if isinstance(resource_type, dict)
                else None
            )
        elif key == "publication_type":
            actual_value = (
                resource_type.get("subtype")
                if isinstance(resource_type, dict)
                else None
            )
        else:
            if key not in actual:
                return False
            actual_value = actual[key]
        if not _metadata_matches(actual_value, expected_value):
            return False
    return True


class ZenodoClient:
    def __init__(
        self,
        token: str,
        base_url: str,
        transport: Any | None = None,
        *,
        poll_attempts: int = 30,
        poll_interval: float = 2.0,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(token, str) or len(token) < 20 or any(c.isspace() for c in token):
            raise ZenodoError(
                f"{TOKEN_ENVIRONMENT_VARIABLE} is missing or structurally invalid"
            )
        if poll_attempts < 1 or poll_attempts > 300:
            raise ZenodoError("poll-attempts must be between 1 and 300")
        if poll_interval < 0 or poll_interval > 60:
            raise ZenodoError("poll-interval must be between 0 and 60 seconds")
        self.token = token
        self.base_url = validate_base_url(base_url)
        self.transport = transport or HttpTransport(token, self.base_url)
        self.poll_attempts = poll_attempts
        self.poll_interval = poll_interval
        self.sleeper = sleeper

    def url(self, path: str) -> str:
        return validate_response_url(path, self.base_url)

    def request(
        self,
        method: str,
        url: str,
        *,
        payload: Any | None = None,
        data: bytes | None = None,
        content_type: str | None = None,
        accept: Sequence[int] = (200,),
        parse_json: bool = True,
        max_response_bytes: int = MAX_RESPONSE_BYTES,
    ) -> tuple[HttpResponse, dict[str, Any]]:
        if payload is not None and data is not None:
            raise ZenodoError("internal request supplied two request bodies")
        if payload is not None:
            data = _json_bytes(payload)
            content_type = "application/json"
        safe_url = validate_response_url(url, self.base_url)
        response = self.transport.request(
            method,
            safe_url,
            body=data,
            content_type=content_type,
            max_response_bytes=max_response_bytes,
        )
        if response.status not in accept:
            detail = _response_detail(response, self.token)
            path = urllib.parse.urlsplit(safe_url).path
            raise ZenodoError(
                f"Zenodo request rejected: {method.upper()} {path} "
                f"HTTP {response.status}: {detail}"
            )
        return response, _parse_json(response, self.token) if parse_json else {}

    def get(self, path_or_url: str, accept: Sequence[int] = (200,)) -> tuple[int, dict[str, Any]]:
        response, value = self.request("GET", path_or_url, accept=accept)
        return response.status, value

    def get_with_validated_redirects(self, path_or_url: str) -> dict[str, Any]:
        """Follow a small same-origin API redirect chain without forwarding blindly."""
        current = validate_response_url(path_or_url, self.base_url)
        redirect_statuses = (301, 302, 303, 307, 308)
        for _ in range(4):
            response, value = self.request(
                "GET", current, accept=(200, *redirect_statuses)
            )
            if response.status == 200:
                return value
            location = _header(response, "Location")
            if not location:
                raise ZenodoError("Zenodo redirect omitted its Location header")
            # Validation happens before the next request is built, so the
            # bearer header can never be relayed to another origin or a URL
            # carrying query credentials.
            current = validate_response_url(location, self.base_url)
        raise ZenodoError("Zenodo returned too many redirects")

    def check_live_software_source(self, source: int, concept: int) -> dict[str, Any]:
        _, record = self.get(f"/api/records/{source}")
        if _record_id(record, "software source") != source:
            raise ZenodoError("live software source record ID changed")
        if _concept_id(record, "software source") != concept:
            raise ZenodoError("live software concept record ID changed")
        links = record.get("links")
        if not isinstance(links, dict) or not isinstance(links.get("latest"), str):
            raise ZenodoError("live software record has no latest-version link")
        latest_url = validate_response_url(links["latest"], self.base_url)
        latest_record = self.get_with_validated_redirects(latest_url)
        if _record_id(latest_record, "resolved latest software record") != source:
            raise ZenodoError("software source record is no longer the live latest version")
        if _concept_id(latest_record, "resolved latest software record") != concept:
            raise ZenodoError("resolved latest software record changed concept")
        relations = latest_record.get("metadata", {}).get("relations")
        if isinstance(relations, dict) and isinstance(relations.get("version"), list):
            versions = relations["version"]
            if versions and not any(
                isinstance(item, dict) and item.get("is_last") is True
                for item in versions
            ):
                raise ZenodoError("resolved software record is not marked as latest")
        return record

    def create_paper(self, metadata: Mapping[str, Any]) -> dict[str, Any]:
        response, deposition = self.request(
            "POST",
            "/api/deposit/depositions",
            payload={"metadata": metadata},
            accept=(200, 201, 202),
        )
        if "id" not in deposition:
            location = _header(response, "Location")
            if not location:
                raise ZenodoError("asynchronous paper creation returned no safe location")
            location = validate_response_url(location, self.base_url)
            for attempt in range(self.poll_attempts):
                status, candidate = self.get(location, accept=(200, 202, 404))
                if status == 200 and "id" in candidate:
                    deposition = candidate
                    break
                if attempt + 1 < self.poll_attempts:
                    self.sleeper(self.poll_interval)
        _record_id(deposition, "paper deposition")
        _doi_from_deposition(deposition, "paper deposition")
        return deposition

    def create_software_version(self, source: int) -> dict[str, Any]:
        response, value = self.request(
            "POST",
            f"/api/deposit/depositions/{source}/actions/newversion",
            accept=(200, 201, 202, 409),
        )
        links = value.get("links")
        latest_draft_raw = (
            links.get("latest_draft") if isinstance(links, dict) else None
        )
        if not isinstance(latest_draft_raw, str):
            for attempt in range(self.poll_attempts):
                status, candidate = self.get(
                    f"/api/deposit/depositions/{source}",
                    accept=(200, 202, 404),
                )
                candidate_links = candidate.get("links")
                if status == 200 and isinstance(candidate_links, dict):
                    latest_draft_raw = candidate_links.get("latest_draft")
                if isinstance(latest_draft_raw, str):
                    break
                if attempt + 1 < self.poll_attempts:
                    self.sleeper(self.poll_interval)
        if not isinstance(latest_draft_raw, str):
            raise ZenodoError("new-version response has no links.latest_draft")
        latest_draft = validate_response_url(latest_draft_raw, self.base_url)
        # The response object's id is deliberately ignored: latest_draft is the
        # legacy API's authoritative pointer for a newly-created version.
        _, draft = self.get(latest_draft)
        linked_id = _id_from_api_url(
            latest_draft, self.base_url, "/api/deposit/depositions"
        )
        if _record_id(draft, "software draft") != linked_id:
            raise ZenodoError("latest_draft URL and returned software draft disagree")
        _doi_from_deposition(draft, "software draft")
        return draft

    def get_deposition_or_record(self, record_id: int) -> tuple[str, dict[str, Any]]:
        status, value = self.get(
            f"/api/deposit/depositions/{record_id}", accept=(200, 403, 404)
        )
        if status == 200 and not (
            value.get("submitted") is True or value.get("state") == "done"
        ):
            return "draft", value
        # Published owner depositions can remain readable as ``submitted`` or
        # can disappear/return 403 from the editable-deposition namespace.
        # In all three cases, only an independently gated public record is
        # accepted as evidence of publication.
        for attempt in range(self.poll_attempts):
            status, value = self.get(
                f"/api/records/{record_id}", accept=(200, 202, 404)
            )
            if status == 200:
                return "published", value
            if attempt + 1 < self.poll_attempts:
                self.sleeper(self.poll_interval)
        raise ZenodoError(f"Zenodo record {record_id} is neither an editable draft nor published")

    @staticmethod
    def _server_files(value: Mapping[str, Any]) -> list[dict[str, Any]]:
        files = value.get("files")
        if files is None:
            return []
        if not isinstance(files, list) or not all(isinstance(item, dict) for item in files):
            raise ZenodoError("Zenodo returned an invalid file list")
        return files

    @staticmethod
    def _server_file_name(value: Mapping[str, Any]) -> str:
        name = value.get("filename", value.get("key"))
        if not isinstance(name, str) or not name:
            raise ZenodoError("Zenodo returned a file without a name")
        return name

    def delete_all_files(self, deposition_id: int, deposition: Mapping[str, Any]) -> None:
        deposition_links = deposition.get("links")
        bucket_path: str | None = None
        if isinstance(deposition_links, dict) and isinstance(
            deposition_links.get("bucket"), str
        ):
            bucket_path = urllib.parse.urlsplit(
                validate_response_url(deposition_links["bucket"], self.base_url)
            ).path.rstrip("/")
        legacy_prefix = f"/api/deposit/depositions/{deposition_id}/files/"
        for item in self._server_files(deposition):
            links = item.get("links")
            delete_url: str | None = None
            if isinstance(links, dict) and isinstance(links.get("self"), str):
                delete_url = links["self"]
            if delete_url is None:
                file_id = item.get("id")
                if isinstance(file_id, str) and file_id:
                    delete_url = f"/api/deposit/depositions/{deposition_id}/files/{file_id}"
            if delete_url is None:
                raise ZenodoError("inherited Zenodo file has no safe deletion endpoint")
            safe_delete_url = validate_response_url(delete_url, self.base_url)
            delete_path = urllib.parse.urlsplit(safe_delete_url).path
            if not (
                delete_path.startswith(legacy_prefix)
                or (bucket_path is not None and delete_path.startswith(bucket_path + "/"))
            ):
                raise ZenodoError("inherited file deletion endpoint escaped its deposition")
            self.request("DELETE", safe_delete_url, accept=(200, 202, 204, 404))
        for attempt in range(self.poll_attempts):
            status, value = self.get(
                f"/api/deposit/depositions/{deposition_id}", accept=(200, 202)
            )
            if status == 200 and not self._server_files(value):
                return
            if attempt + 1 < self.poll_attempts:
                self.sleeper(self.poll_interval)
        raise ZenodoError(
            f"timed out waiting for inherited files to be deleted from {deposition_id}"
        )

    def upload_files(
        self,
        deposition: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
        verified: Mapping[tuple[str, str], bytes],
        kind: str,
    ) -> None:
        links = deposition.get("links")
        if not isinstance(links, dict) or not isinstance(links.get("bucket"), str):
            raise ZenodoError(f"{kind} draft has no upload bucket link")
        bucket = validate_response_url(links["bucket"], self.base_url).rstrip("/")
        for entry in entries:
            encoded_name = urllib.parse.quote(entry["name"], safe="")
            upload_url = bucket + "/" + encoded_name
            self.request(
                "PUT",
                upload_url,
                data=verified[(kind, entry["name"])],
                content_type="application/octet-stream",
                accept=(200, 201, 202),
            )

    def gate_files(
        self,
        value: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
    ) -> None:
        server_files = self._server_files(value)
        by_name: dict[str, Mapping[str, Any]] = {}
        for item in server_files:
            name = self._server_file_name(item)
            if name in by_name:
                raise ZenodoError(f"Zenodo returned duplicate file name: {name}")
            by_name[name] = item
        expected_names = {entry["name"] for entry in entries}
        if set(by_name) != expected_names:
            raise ZenodoError("Zenodo file list does not exactly match the release manifest")
        for entry in entries:
            item = by_name[entry["name"]]
            raw_size = item.get("filesize", item.get("size"))
            if isinstance(raw_size, str) and raw_size.isdecimal():
                raw_size = int(raw_size)
            if raw_size != entry["size"]:
                raise ZenodoError(f"server size mismatch for {entry['name']}")
            checksum = item.get("checksum")
            if checksum not in (entry["md5"], "md5:" + entry["md5"]):
                raise ZenodoError(f"server MD5 mismatch for {entry['name']}")
            links = item.get("links")
            if not isinstance(links, dict):
                raise ZenodoError(f"server file has no download link: {entry['name']}")
            download: str | None = None
            for candidate in (links.get("download"), links.get("self")):
                if not isinstance(candidate, str):
                    continue
                try:
                    download = validate_response_url(candidate, self.base_url)
                except ZenodoError:
                    continue
                break
            if download is None:
                raise ZenodoError(f"server file has no download link: {entry['name']}")
            response, _ = self.request(
                "GET",
                download,
                accept=(200,),
                parse_json=False,
                max_response_bytes=entry["size"],
            )
            if len(response.body) != entry["size"]:
                raise ZenodoError(f"downloaded size mismatch for {entry['name']}")
            if hashlib.md5(response.body).hexdigest() != entry["md5"]:  # noqa: S324
                raise ZenodoError(f"downloaded MD5 mismatch for {entry['name']}")
            if hashlib.sha256(response.body).hexdigest() != entry["sha256"]:
                raise ZenodoError(f"downloaded SHA-256 mismatch for {entry['name']}")

    def gate_record(
        self,
        value: Mapping[str, Any],
        record_id: int,
        metadata: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
        expected_doi: str,
        *,
        published: bool,
    ) -> None:
        if _record_id(value, "gated record") != record_id:
            raise ZenodoError("gated Zenodo record ID changed")
        actual_metadata = value.get("metadata")
        if published:
            metadata_ok = _published_metadata_matches(actual_metadata, metadata)
        else:
            expected_metadata = dict(metadata)
            # ``prereserve_doi: true`` is a write-time instruction.  Zenodo
            # replaces it in GET responses with an object containing the DOI.
            expected_metadata.pop("prereserve_doi", None)
            metadata_ok = _metadata_matches(actual_metadata, expected_metadata)
        if not metadata_ok:
            raise ZenodoError("Zenodo metadata does not contain the exact manifest values")
        if _doi_from_deposition(value, "gated record") != expected_doi:
            raise ZenodoError("Zenodo DOI changed across the publication boundary")
        self.gate_files(value, entries)

    def wait_for_editable_metadata(
        self, record_id: int, metadata: Mapping[str, Any]
    ) -> dict[str, Any]:
        expected_metadata = dict(metadata)
        expected_metadata.pop("prereserve_doi", None)
        for attempt in range(self.poll_attempts):
            status, value = self.get(
                f"/api/deposit/depositions/{record_id}", accept=(200, 202)
            )
            links = value.get("links")
            if (
                status == 200
                and _metadata_matches(value.get("metadata"), expected_metadata)
                and isinstance(links, dict)
                and isinstance(links.get("bucket"), str)
            ):
                return value
            if attempt + 1 < self.poll_attempts:
                self.sleeper(self.poll_interval)
        raise ZenodoError(f"timed out waiting for editable Zenodo metadata {record_id}")

    def wait_for_gated_record(
        self,
        record_id: int,
        metadata: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
        expected_doi: str,
        *,
        published: bool,
        initial: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: ZenodoError | None = None
        for attempt in range(self.poll_attempts):
            if attempt == 0 and initial is not None:
                status, value = 200, dict(initial)
            else:
                path = (
                    f"/api/records/{record_id}"
                    if published
                    else f"/api/deposit/depositions/{record_id}"
                )
                status, value = self.get(path, accept=(200, 202, 404))
            if status == 200:
                try:
                    self.gate_record(
                        value,
                        record_id,
                        metadata,
                        entries,
                        expected_doi,
                        published=published,
                    )
                    return value
                except ZenodoError as exc:
                    last_error = exc
            if attempt + 1 < self.poll_attempts:
                self.sleeper(self.poll_interval)
        if last_error is not None:
            raise ZenodoError(
                f"Zenodo record {record_id} did not pass the final GET gate: {last_error}"
            )
        raise ZenodoError(f"timed out waiting for Zenodo record {record_id}")

    def prepare_draft(
        self,
        kind: str,
        record_id: int,
        metadata: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
        verified: Mapping[tuple[str, str], bytes],
        expected_doi: str,
    ) -> str:
        state, current = self.get_deposition_or_record(record_id)
        if state == "published":
            self.wait_for_gated_record(
                record_id,
                metadata,
                entries,
                expected_doi,
                published=True,
                initial=current,
            )
            return "published"
        if _record_id(current, f"{kind} draft") != record_id:
            raise ZenodoError(f"{kind} draft ID changed")
        self.request(
            "PUT",
            f"/api/deposit/depositions/{record_id}",
            payload={"metadata": metadata},
            accept=(200, 202),
        )
        updated = self.wait_for_editable_metadata(record_id, metadata)
        self.delete_all_files(record_id, updated)
        self.upload_files(updated, entries, verified, kind)
        self.wait_for_gated_record(
            record_id,
            metadata,
            entries,
            expected_doi,
            published=False,
        )
        return "draft"

    def publish_and_poll(
        self,
        record_id: int,
        metadata: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
        expected_doi: str,
        already_published: bool,
    ) -> dict[str, Any]:
        if not already_published:
            self.request(
                "POST",
                f"/api/deposit/depositions/{record_id}/actions/publish",
                accept=(200, 201, 202, 409),
            )
        return self.wait_for_gated_record(
            record_id,
            metadata,
            entries,
            expected_doi,
            published=True,
        )


def _atomic_json(path: pathlib.Path, value: Mapping[str, Any], token: str) -> None:
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n"
    if token and token in serialized:
        raise ZenodoError("refusing to write a result artifact containing the access token")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise ZenodoError("result path must not be a symbolic link")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="." + path.name + ".", suffix=".tmp", dir=path.parent
    )
    temporary = pathlib.Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _reservation_base(
    manifest: Mapping[str, Any], manifest_sha256: str, client: ZenodoClient
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "phase": "reserving",
        "api_origin": urllib.parse.urlsplit(client.base_url).hostname,
        "reservation_manifest_sha256": manifest_sha256,
        "authorization_envelope": authorization_envelope(manifest),
    }


def _sign_reservation(value: Mapping[str, Any], token: str) -> dict[str, Any]:
    signed = dict(value)
    signed.pop("authorization_mac", None)
    signed["authorization_mac"] = hmac.new(
        token.encode("utf-8"), _json_bytes(signed), hashlib.sha256
    ).hexdigest()
    return signed


def _validate_reservation(
    value: Mapping[str, Any], manifest: Mapping[str, Any], client: ZenodoClient
) -> None:
    required = {
        "schema_version",
        "phase",
        "api_origin",
        "reservation_manifest_sha256",
        "authorization_envelope",
        "authorization_mac",
        "paper",
    }
    if not required.issubset(value):
        raise ZenodoError("reservation artifact is incomplete")
    if value["schema_version"] != 1:
        raise ZenodoError("reservation artifact schema is unsupported")
    if value["api_origin"] != urllib.parse.urlsplit(client.base_url).hostname:
        raise ZenodoError("reservation artifact belongs to another Zenodo origin")
    if value["authorization_envelope"] != authorization_envelope(manifest):
        raise ZenodoError("final manifest changes the reserved authorization envelope")
    supplied_mac = value.get("authorization_mac")
    if not isinstance(supplied_mac, str) or not HEX_64.fullmatch(supplied_mac):
        raise ZenodoError("reservation artifact has no valid authorization MAC")
    unsigned = dict(value)
    unsigned.pop("authorization_mac", None)
    expected_mac = hmac.new(
        client.token.encode("utf-8"), _json_bytes(unsigned), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied_mac, expected_mac):
        raise ZenodoError("reservation artifact authorization MAC mismatch")
    for kind in ("paper", "software"):
        if kind not in value:
            if kind == "software" and value.get("phase") == "paper_reserved":
                continue
            raise ZenodoError("reservation artifact is missing a deposition")
        item = value[kind]
        if not isinstance(item, dict):
            raise ZenodoError(f"reservation {kind} entry is invalid")
        _safe_int(item.get("deposition_id"), f"reservation.{kind}.deposition_id")
        doi = item.get("doi")
        if not isinstance(doi, str) or not DOI.fullmatch(doi):
            raise ZenodoError(f"reservation.{kind}.doi is invalid")


def reserve(
    client: ZenodoClient,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    root: pathlib.Path,
    result_path: pathlib.Path,
) -> dict[str, Any]:
    # Reserve has no file upload, but it still authorizes identities and two
    # remote drafts.  Stale or fabricated file descriptors therefore block
    # before the first network request.
    verify_manifest_files(manifest, root, client.token)
    if result_path.exists():
        existing, _ = _load_json_file(result_path, client.token)
        _validate_reservation(existing, manifest, client)
        if existing.get("reservation_manifest_sha256") != manifest_sha256:
            raise ZenodoError("reserve rerun uses different pre-reservation manifest bytes")
        if existing.get("phase") == "reserved":
            return existing
        result: dict[str, Any] = dict(existing)
    else:
        result = _reservation_base(manifest, manifest_sha256, client)

    source = manifest["software"]["source_record_id"]
    concept = manifest["software"]["concept_record_id"]
    client.check_live_software_source(source, concept)

    if "paper" not in result:
        paper = client.create_paper(manifest["paper"]["metadata"])
        result["paper"] = {
            "deposition_id": _record_id(paper, "paper deposition"),
            "concept_record_id": _concept_id(paper, "paper deposition"),
            "doi": _doi_from_deposition(paper, "paper deposition"),
        }
        result["phase"] = "paper_reserved"
        result = _sign_reservation(result, client.token)
        _atomic_json(result_path, result, client.token)

    if "software" not in result:
        software = client.create_software_version(source)
        if _concept_id(software, "software draft") != concept:
            raise ZenodoError("software draft concept ID differs from authorized concept")
        result["software"] = {
            "deposition_id": _record_id(software, "software draft"),
            "concept_record_id": concept,
            "source_record_id": source,
            "doi": _doi_from_deposition(software, "software draft"),
        }
        result["phase"] = "reserved"
        result = _sign_reservation(result, client.token)
        _atomic_json(result_path, result, client.token)
    return result


def _validate_final_dois(
    manifest: Mapping[str, Any],
    reservation: Mapping[str, Any],
    verified: Mapping[tuple[str, str], bytes],
) -> None:
    expected = {
        kind: reservation[kind]["doi"] for kind in ("paper", "software")
    }
    if manifest["reserved_dois"] != expected:
        raise ZenodoError("final manifest does not bind the two reserved DOIs exactly")
    for kind, doi in expected.items():
        explicit_metadata_doi = manifest[kind]["metadata"].get("doi")
        if explicit_metadata_doi is not None and explicit_metadata_doi != doi:
            raise ZenodoError(f"final {kind} metadata contains a conflicting DOI")
        searchable = _json_bytes(manifest[kind]["metadata"]) + b"\n" + b"\n".join(
            data
            for (file_kind, _), data in verified.items()
            if file_kind == kind
        )
        if doi.encode("ascii") not in searchable:
            raise ZenodoError(
                f"reserved {kind} DOI is absent from its final metadata and deposited bytes"
            )


def finalize(
    client: ZenodoClient,
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    reservation: Mapping[str, Any],
    root: pathlib.Path,
    result_path: pathlib.Path,
) -> dict[str, Any]:
    _validate_reservation(reservation, manifest, client)
    if reservation.get("phase") != "reserved":
        raise ZenodoError("both Zenodo depositions must be reserved before finalize")
    verified = verify_manifest_files(manifest, root, client.token)
    _validate_final_dois(manifest, reservation, verified)

    preparation: dict[str, str] = {}
    for kind in ("paper", "software"):
        preparation[kind] = client.prepare_draft(
            kind,
            reservation[kind]["deposition_id"],
            manifest[kind]["metadata"],
            manifest[kind]["files"],
            verified,
            reservation[kind]["doi"],
        )

    published: dict[str, dict[str, Any]] = {}
    for kind in ("paper", "software"):
        record = client.publish_and_poll(
            reservation[kind]["deposition_id"],
            manifest[kind]["metadata"],
            manifest[kind]["files"],
            reservation[kind]["doi"],
            preparation[kind] == "published",
        )
        published[kind] = {
            "record_id": _record_id(record, f"published {kind}"),
            "concept_record_id": _concept_id(record, f"published {kind}"),
            "doi": _doi_from_deposition(record, f"published {kind}"),
        }

    result = {
        "schema_version": 1,
        "phase": "published",
        "release_id": manifest["release_id"],
        "tag": manifest["authorization"]["tag"],
        "repositories": manifest["authorization"]["repositories"],
        "final_manifest_sha256": manifest_sha256,
        "paper": published["paper"],
        "software": published["software"],
        "datatracker_submitted": False,
        "github_release_created": False,
    }
    _atomic_json(result_path, result, client.token)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = SafeArgumentParser(
        description="Reserve or finalize the two EFFECT_ACK Zenodo depositions."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=SafeArgumentParser
    )

    reserve_parser = subparsers.add_parser("reserve")
    reserve_parser.add_argument("--manifest", required=True)
    reserve_parser.add_argument("--result", required=True)

    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--manifest", required=True)
    finalize_parser.add_argument("--reservation", required=True)
    finalize_parser.add_argument("--result", required=True)
    for command_parser in (reserve_parser, finalize_parser):
        command_parser.add_argument(
            "--base-url", default=DEFAULT_BASE_URL, help=argparse.SUPPRESS
        )
        command_parser.add_argument("--repository-root", default=".")
        command_parser.add_argument("--poll-attempts", type=int, default=30)
        command_parser.add_argument("--poll-interval", type=float, default=2.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, "")
    try:
        args = build_parser().parse_args(argv)
        root = pathlib.Path(args.repository_root).resolve(strict=True)
        if not root.is_dir():
            raise ZenodoError("repository-root must identify a directory")
        manifest_path = _external_path_in_root(
            root, args.manifest, must_exist=True
        )
        result_path = _external_path_in_root(
            root, args.result, must_exist=False
        )
        manifest_value, manifest_raw = _load_json_file(manifest_path, token)
        manifest = validate_manifest(
            manifest_value, root, final=args.command == "finalize"
        )
        manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
        client = ZenodoClient(
            token,
            args.base_url,
            poll_attempts=args.poll_attempts,
            poll_interval=args.poll_interval,
        )
        if args.command == "reserve":
            outcome = reserve(
                client, manifest, manifest_sha256, root, result_path
            )
        else:
            reservation_path = _external_path_in_root(
                root, args.reservation, must_exist=True
            )
            reservation, _ = _load_json_file(reservation_path, token)
            outcome = finalize(
                client,
                manifest,
                manifest_sha256,
                reservation,
                root,
                result_path,
            )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "phase": outcome["phase"],
                },
                sort_keys=True,
            )
        )
        return 0
    except ZenodoError as exc:
        print("BLOCK " + redact(str(exc), token), file=sys.stderr)
        return 1
    except Exception:
        # Unexpected local/runtime failures remain blocking but are deliberately
        # not reflected: exception representations can contain request headers,
        # environment values, or attacker-controlled file names.
        print("BLOCK internal Zenodo client failure", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
