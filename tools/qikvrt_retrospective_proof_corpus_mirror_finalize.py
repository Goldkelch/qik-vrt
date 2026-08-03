#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Finalize the retrospective proof corpus on Authority and Mirror.

This capability is deliberately narrower than a repository synchronizer.  It
operates only on three dedicated, create-only/non-force refs for one frozen
publication.  It never reads a Zenodo credential and the only credential it
accepts is ``QIKVRT_MESH_TOKEN``.

The transaction starts and ends with a credential-free, proxy-disabled HTTPS
gate over the public Zenodo record and all 65 exact file bytes.  Before every
remote Git mutation, the already-gated Authority public, publication,
recovery and authorization-consumption refs plus the manifest and
``public_verified`` evidence are read back anonymously.  Exact existing refs
are immutable resume anchors; divergent refs always block.  The same derived
commit carrying the same reciprocal receipt is then created in both public
repositories.  ``EFFECT_ACK_DONE`` is returned only after anonymous readback
proves all three ref pairs and the equality commits, trees and receipt bytes
identical.  The
state is restricted to the named publication and refs; it is not a claim about
``main`` or repository-wide equality.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import math
import os
import pathlib
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_retrospective_proof_corpus_zenodo_candidate as candidate
from tools import qikvrt_retrospective_proof_corpus_zenodo_publication_controls as controls
from tools import qikvrt_retrospective_proof_corpus_zenodo_recovery as recovery
from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_publish as publish


AUTHORITY = "Goldkelch/qik-vrt"
MIRROR = "ingolf-lohmann/qik-vrt"
PUBLIC_REF = "refs/heads/evidence/retrospective-proof-corpus-public-verified-v3"
OVERVIEW_REF = "refs/heads/evidence/retrospective-proof-corpus-overview-v3"
EQUALITY_REF = "refs/heads/evidence/retrospective-proof-corpus-reciprocal-equality-v3"
PUBLICATION_REF = recovery.PUBLICATION_REF
CONTROL_REL = pathlib.PurePosixPath(
    "release/zenodo-corpus-proof-publication-2026-08-03"
)
MANIFEST_REL = (CONTROL_REL / controls.MANIFEST_BASENAME).as_posix()
EVIDENCE_REL = (CONTROL_REL / controls.EVIDENCE_BASENAME).as_posix()
RECEIPT_REL = (
    "evidence/receipts/retrospective-proof-corpus-reciprocal-equality-v3.json"
)
MESH_TOKEN_ENV = "QIKVRT_MESH_TOKEN"
EXPECTED_UPLOADS = 65
EXPECTED_TOTAL_BYTES = 221_808_115
ZERO40 = "0" * 40
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_JSON = 8 * 1024 * 1024
MAX_TOKEN_BYTES = 4096
MAX_ANONYMOUS_GITHUB_REST_REQUESTS = 8
GITHUB_API = "https://api.github.com"
ZENODO_ORIGIN = "https://zenodo.org"
RECEIPT_SCHEMA = "qikvrt_retrospective_proof_corpus_reciprocal_equality_receipt_v1"
RECEIPT_ID = "retrospective-proof-corpus-reciprocal-equality-v3"
INTEGRITY_PATHS = (
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)
EXECUTION_DELTA_STATUSES = {
    ".github/workflows/qikvrt_retrospective_proof_corpus_mirror_finalize.yml": "A",
    ".github/workflows/qikvrt_retrospective_proof_corpus_zenodo_publish.yml": "A",
    "REPOSITORY_FILE_MANIFEST.json": "M",
    "REPOSITORY_FILE_MANIFEST.json.sha256": "M",
    "SHA256SUMS.txt": "M",
    (CONTROL_REL / controls.AUTHORIZATION_BASENAME).as_posix(): "A",
    MANIFEST_REL: "A",
    "tests/test_retrospective_proof_corpus_mirror_finalize.py": "A",
    "tests/test_retrospective_proof_corpus_zenodo_recovery.py": "A",
    "tests/test_retrospective_proof_corpus_zenodo_workflow.py": "A",
    "tools/qikvrt_retrospective_proof_corpus_mirror_finalize.py": "A",
    "tools/qikvrt_retrospective_proof_corpus_zenodo_recovery.py": "A",
}
EXECUTION_DELTA_PATHS = frozenset(EXECUTION_DELTA_STATUSES)
FINAL_DELTA_STATUSES = {
    "REPOSITORY_FILE_MANIFEST.json": "M",
    "REPOSITORY_FILE_MANIFEST.json.sha256": "M",
    "SHA256SUMS.txt": "M",
    EVIDENCE_REL: "A",
}
FINAL_DELTA_PATHS = frozenset(FINAL_DELTA_STATUSES)
FINAL_CUMULATIVE_STATUSES = {
    "REPOSITORY_FILE_MANIFEST.json": "M",
    "REPOSITORY_FILE_MANIFEST.json.sha256": "M",
    "SHA256SUMS.txt": "M",
    recovery.RECOVERY_RELATIVE: "A",
    EVIDENCE_REL: "A",
}
FINAL_CUMULATIVE_PATHS = frozenset(FINAL_CUMULATIVE_STATUSES)


class MirrorFinalizeError(RuntimeError):
    """Safe-to-report fail-closed finalization error."""


def fail(message: str) -> NoReturn:
    raise MirrorFinalizeError(message)


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8") + b"\n"


def parse_json(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or len(raw) > MAX_JSON:
        fail(label + " exceeds its strict JSON byte bound")

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                fail(label + " contains a duplicate JSON object key")
            result[key] = item
        return result

    def reject_constant(value: str) -> NoReturn:
        fail(label + " contains a non-finite JSON number: " + value)

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail(label + " is not strict UTF-8 JSON")
    if not isinstance(value, dict):
        fail(label + " is not a JSON object")

    def validate_unicode(item: Any) -> None:
        if isinstance(item, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                fail(label + " contains a non-scalar Unicode value")
        elif isinstance(item, float) and not math.isfinite(item):
            fail(label + " contains a non-finite JSON number")
        elif isinstance(item, list):
            for child in item:
                validate_unicode(child)
        elif isinstance(item, dict):
            for key, child in item.items():
                validate_unicode(key)
                validate_unicode(child)

    validate_unicode(value)
    return value


def git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()  # noqa: S324 - Git identity


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        fail(label + " keys differ from the closed contract")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class AnonymousHTTPS:
    """Verified-TLS HTTPS with no proxy, redirect, cookie or credential state."""

    def __init__(self, opener: Any | None = None) -> None:
        self.github_rest_requests = 0
        self.opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            NoRedirect(),
        )

    @staticmethod
    def _validate_url(url: str) -> str:
        if not isinstance(url, str):
            fail("anonymous URL is not text")
        parts = urllib.parse.urlsplit(url)
        try:
            port = parts.port
        except ValueError:
            fail("anonymous URL has an invalid port")
        origin = f"{parts.scheme}://{parts.hostname or ''}"
        if (
            parts.scheme != "https"
            or origin not in {GITHUB_API, ZENODO_ORIGIN}
            or parts.username is not None
            or parts.password is not None
            or port not in (None, 443)
            or parts.fragment
        ):
            fail("anonymous URL escaped the GitHub/Zenodo allowlist")
        if origin == GITHUB_API and not parts.path.startswith("/repos/"):
            fail("anonymous GitHub URL escaped the repository API")
        if origin == ZENODO_ORIGIN and not parts.path.startswith("/api/records/"):
            fail("anonymous Zenodo URL escaped the public records API")
        if origin == ZENODO_ORIGIN and parts.query:
            fail("anonymous Zenodo URL may not contain a query")
        if origin == GITHUB_API:
            if parts.path.startswith("/repos/") and "/contents/" in parts.path:
                try:
                    query = urllib.parse.parse_qsl(
                        parts.query, keep_blank_values=True, strict_parsing=True
                    )
                except ValueError:
                    fail("anonymous GitHub contents URL has an invalid query")
                if (
                    len(query) != 1
                    or query[0][0] != "ref"
                    or HEX40.fullmatch(query[0][1]) is None
                ):
                    fail("anonymous GitHub contents URL has an invalid query")
            elif parts.query:
                fail("anonymous GitHub URL may not contain a query")
        return urllib.parse.urlunsplit(
            (parts.scheme, parts.netloc, parts.path, parts.query, "")
        )

    def request(
        self,
        url: str,
        *,
        maximum: int,
        accept: tuple[int, ...] = (200,),
    ) -> tuple[int, bytes]:
        safe = self._validate_url(url)
        if urllib.parse.urlsplit(safe).hostname == "api.github.com":
            self.github_rest_requests += 1
            if self.github_rest_requests > MAX_ANONYMOUS_GITHUB_REST_REQUESTS:
                fail("anonymous GitHub REST request budget exceeded")
        if maximum < 0 or maximum > zenodo.MAX_UPLOAD_BYTES:
            fail("anonymous response bound is invalid")
        request = urllib.request.Request(
            safe,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json, application/json",
                "Accept-Encoding": "identity",
                "User-Agent": "qikvrt-retrospective-corpus-mirror-finalizer/1",
            },
        )
        if any(key.casefold() == "authorization" for key in request.headers):
            fail("anonymous request unexpectedly contains authorization")
        try:
            response = self.opener.open(request, timeout=60)
        except urllib.error.HTTPError as exc:
            if int(exc.code) not in accept:
                fail(f"anonymous GET failed with HTTP {int(exc.code)}")
            raw = exc.read(maximum + 1)
            if len(raw) > maximum:
                fail("anonymous error response exceeded its byte bound")
            return int(exc.code), raw
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            fail("anonymous HTTPS transport failed: " + type(exc).__name__)
        with response:
            if response.geturl() != safe:
                fail("anonymous GET followed a redirect")
            raw = response.read(maximum + 1)
            if len(raw) > maximum:
                fail("anonymous response exceeded its byte bound")
            status = int(response.status)
            if status not in accept:
                fail(f"anonymous GET failed with HTTP {status}")
            return status, raw

    def json(self, url: str, *, maximum: int = MAX_JSON) -> dict[str, Any]:
        status, raw = self.request(url, maximum=maximum)
        if status != 200:
            fail("anonymous JSON GET did not return HTTP 200")
        return parse_json(raw, "anonymous response")


def api_url(repository: str, suffix: str) -> str:
    if repository not in {AUTHORITY, MIRROR} or not suffix.startswith("/"):
        fail("GitHub API target escaped the two-repository scope")
    return GITHUB_API + "/repos/" + repository + suffix


def encoded_ref(ref: str) -> str:
    if not ref.startswith("refs/heads/"):
        fail("finalization ref is not a branch ref")
    return urllib.parse.quote(ref.removeprefix("refs/"), safe="/")


def read_ref(
    transport: AnonymousHTTPS,
    repository: str,
    ref: str,
    *,
    missing_ok: bool = False,
) -> str | None:
    status, raw = transport.request(
        api_url(repository, "/git/ref/" + encoded_ref(ref)),
        maximum=MAX_JSON,
        accept=(200, 404) if missing_ok else (200,),
    )
    if status == 404:
        return None
    value = parse_json(raw, repository + " ref")
    target = value.get("object")
    sha = target.get("sha") if isinstance(target, dict) else None
    if (
        value.get("ref") != ref
        or not isinstance(sha, str)
        or HEX40.fullmatch(sha) is None
        or target.get("type") != "commit"
    ):
        fail(repository + " ref response differs from the exact branch contract")
    return sha


def read_commit(
    transport: AnonymousHTTPS, repository: str, commit: str
) -> dict[str, Any]:
    if HEX40.fullmatch(commit) is None:
        fail("commit identity is invalid")
    value = transport.json(api_url(repository, "/git/commits/" + commit))
    tree = value.get("tree")
    parents = value.get("parents")
    if (
        value.get("sha") != commit
        or not isinstance(tree, dict)
        or not isinstance(tree.get("sha"), str)
        or HEX40.fullmatch(tree["sha"]) is None
        or not isinstance(parents, list)
        or not all(
            isinstance(item, dict)
            and isinstance(item.get("sha"), str)
            and HEX40.fullmatch(item["sha"]) is not None
            for item in parents
        )
    ):
        fail(repository + " commit response is incomplete")
    return {
        "commit": commit,
        "tree": tree["sha"],
        "parents": [item["sha"] for item in parents],
    }


def read_content(
    transport: AnonymousHTTPS,
    repository: str,
    path: str,
    ref: str,
) -> bytes:
    safe_path = candidate.normalize_repo_relative(path, "remote content path")
    query = urllib.parse.urlencode({"ref": ref})
    value = transport.json(
        api_url(
            repository,
            "/contents/" + urllib.parse.quote(safe_path, safe="/") + "?" + query,
        )
    )
    exact_keys(
        value,
        {"name", "path", "sha", "size", "url", "html_url", "git_url", "download_url", "type", "content", "encoding", "_links"},
        repository + " content response",
    )
    if value.get("path") != safe_path or value.get("type") != "file":
        fail(repository + " content path/type differs")
    if value.get("encoding") != "base64" or not isinstance(value.get("content"), str):
        fail(repository + " content response is not Base64")
    encoded = value["content"]
    if any(character.isspace() and character not in "\r\n" for character in encoded):
        fail(repository + " content response has unsupported Base64 whitespace")
    try:
        raw = base64.b64decode(
            encoded.replace("\r", "").replace("\n", ""), validate=True
        )
    except (ValueError, TypeError):
        fail(repository + " content response has invalid Base64")
    if value.get("size") != len(raw) or value.get("sha") != git_blob_sha1(raw):
        fail(repository + " content byte/Git binding differs")
    return raw


def validate_public_evidence(
    value: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    required = {
        "schema", "state", "phase", "manifest_path", "manifest_sha256",
        "machine_proof", "owner_authorization", "remote_consumption",
        "repository", "repository_commit", "source_head", "binding",
        "governance_boundaries", "recovery", "record_id", "doi", "title",
        "version", "files", "conceptdoi", "record_url",
    }
    exact_keys(value, required, "publication evidence")
    if (
        value.get("schema") != publish.EVIDENCE_SCHEMA_V2
        or value.get("state") != "published"
        or value.get("phase") != "public_verified"
        or value.get("manifest_path") != MANIFEST_REL
        or value.get("manifest_sha256") != manifest.get("manifest_sha256")
        or value.get("machine_proof") != manifest.get("machine_proof")
        or value.get("owner_authorization") != manifest.get("owner_authorization")
        or value.get("repository") != AUTHORITY
        or value.get("source_head") != controls.SOURCE_HEAD
        or value.get("files") != manifest.get("files")
        or value.get("title") != manifest.get("metadata", {}).get("title")
        or value.get("version") != manifest.get("metadata", {}).get("version")
        or value.get("recovery") != publish._recovery_flags("public_verified")
    ):
        fail("publication evidence is not the exact Authority public_verified state")
    repository_commit = value.get("repository_commit")
    record_id = value.get("record_id")
    doi = value.get("doi")
    conceptdoi = value.get("conceptdoi")
    record_url = value.get("record_url")
    if not isinstance(repository_commit, str) or HEX40.fullmatch(repository_commit) is None:
        fail("publication evidence repository_commit is invalid")
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
        fail("publication evidence record_id is invalid")
    if not isinstance(doi, str) or publish.ZENODO_DOI.fullmatch(doi) is None:
        fail("publication evidence DOI is invalid")
    if not isinstance(conceptdoi, str) or publish.ZENODO_DOI.fullmatch(conceptdoi) is None:
        fail("publication evidence concept DOI is invalid")
    if record_url != f"https://zenodo.org/records/{record_id}":
        fail("publication evidence record URL differs")
    files = value.get("files")
    if not isinstance(files, list) or len(files) != EXPECTED_UPLOADS:
        fail("publication evidence does not bind 65 files")
    return dict(value)


def validate_server_files(
    record: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]
) -> list[tuple[Mapping[str, Any], Mapping[str, Any], str]]:
    raw_files = record.get("files")
    if not isinstance(raw_files, list) or not all(isinstance(item, dict) for item in raw_files):
        fail("public Zenodo record has an invalid file list")
    by_name: dict[str, Mapping[str, Any]] = {}
    for item in raw_files:
        name = item.get("key", item.get("filename"))
        if not isinstance(name, str) or name in by_name:
            fail("public Zenodo record has an invalid/duplicate filename")
        by_name[name] = item
    expected_names = [str(entry["name"]) for entry in entries]
    if set(by_name) != set(expected_names) or len(by_name) != EXPECTED_UPLOADS:
        fail("public Zenodo fileset differs from the exact 65-file manifest")
    result: list[tuple[Mapping[str, Any], Mapping[str, Any], str]] = []
    for entry in entries:
        item = by_name[str(entry["name"])]
        size = item.get("size", item.get("filesize"))
        if isinstance(size, str) and size.isdecimal():
            size = int(size)
        checksum = item.get("checksum")
        if size != entry["size"] or checksum not in {entry["md5"], "md5:" + entry["md5"]}:
            fail("public Zenodo file metadata differs for " + str(entry["name"]))
        links = item.get("links")
        if not isinstance(links, dict):
            fail("public Zenodo file lacks download links")
        url = links.get("content", links.get("download", links.get("self")))
        if not isinstance(url, str):
            fail("public Zenodo file lacks a download URL")
        AnonymousHTTPS._validate_url(url)
        result.append((entry, item, url))
    return result


def verify_public_record(
    transport: AnonymousHTTPS,
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    record_id = int(evidence["record_id"])
    record = transport.json(f"https://zenodo.org/api/records/{record_id}")
    if zenodo._record_id(record, "anonymous public record") != record_id:
        fail("anonymous public record ID differs")
    if zenodo._doi_from_deposition(record, "anonymous public record") != evidence["doi"]:
        fail("anonymous public DOI differs")
    metadata = record.get("metadata")
    if not zenodo._published_metadata_matches(metadata, manifest["metadata"]):
        fail("anonymous public metadata differs from the exact manifest")
    conceptdoi = record.get("conceptdoi")
    if conceptdoi is None and isinstance(metadata, dict):
        conceptdoi = metadata.get("conceptdoi")
    if conceptdoi != evidence["conceptdoi"]:
        fail("anonymous public concept DOI differs")
    entries = manifest["files"]
    pairs = validate_server_files(record, entries)
    total = 0
    for entry, _server, url in pairs:
        status, raw = transport.request(url, maximum=int(entry["size"]))
        if status != 200 or len(raw) != entry["size"]:
            fail("anonymous public byte count differs for " + str(entry["name"]))
        if hashlib.md5(raw).hexdigest() != entry["md5"]:  # noqa: S324 - transport
            fail("anonymous public MD5 differs for " + str(entry["name"]))
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            fail("anonymous public SHA-256 differs for " + str(entry["name"]))
        total += len(raw)
    if len(pairs) != EXPECTED_UPLOADS or total != EXPECTED_TOTAL_BYTES:
        fail("anonymous public fileset count/byte total differs")
    return {
        "record_id": record_id,
        "doi": evidence["doi"],
        "conceptdoi": evidence["conceptdoi"],
        "file_count": len(pairs),
        "total_bytes": total,
    }


def verify_authority_gate(
    transport: AnonymousHTTPS,
    manifest_raw: bytes,
    evidence_raw: bytes,
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
    expected_head: str,
) -> dict[str, Any]:
    binding = validate_publication_binding_anonymous(
        manifest_raw=manifest_raw,
        evidence_raw=evidence_raw,
        manifest=manifest,
        evidence=evidence,
        head=expected_head,
    )
    commit = local_commit(expected_head)
    if local_content(expected_head, MANIFEST_REL) != manifest_raw:
        fail("Authority public manifest differs from local exact bytes")
    if local_content(expected_head, EVIDENCE_REL) != evidence_raw:
        fail("Authority public_verified evidence differs from local exact bytes")
    verify_remote_integrity_anonymous(
        AUTHORITY,
        PUBLIC_REF,
        expected_head,
        expected_tree=str(commit["tree"]),
        expected_files={MANIFEST_REL: manifest_raw, EVIDENCE_REL: evidence_raw},
    )
    public = verify_public_record(transport, manifest, evidence)
    return {
        "authority_head": expected_head,
        "authority_tree": commit["tree"],
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "evidence_sha256": hashlib.sha256(evidence_raw).hexdigest(),
        **binding,
        **public,
    }


def verify_guard_unchanged(
    transport: AnonymousHTTPS,
    gate: Mapping[str, Any],
    manifest_raw: bytes,
    evidence_raw: bytes,
) -> None:
    del transport
    head = anonymous_git_ref(AUTHORITY, PUBLIC_REF)
    if head != gate["authority_head"]:
        fail("Authority public_verified ref moved before mutation")
    dynamic_refs = (
        PUBLICATION_REF,
        str(gate["recovery_ref"]),
        str(gate["consumption_ref"]),
    )
    live_publication = anonymous_git_ref(
        AUTHORITY, PUBLICATION_REF, additional_refs=dynamic_refs
    )
    live_recovery = anonymous_git_ref(
        AUTHORITY, str(gate["recovery_ref"]), additional_refs=dynamic_refs
    )
    live_consumption = anonymous_git_ref(
        AUTHORITY, str(gate["consumption_ref"]), additional_refs=dynamic_refs
    )
    if live_publication != gate["publication_head"]:
        fail("Authority publication ref moved before mutation")
    if live_recovery != gate["recovery_head"]:
        fail("Authority recovery ref moved before mutation")
    if live_consumption != gate["consumption_tag_object"]:
        fail("Authority consumption ref moved before mutation")
    commit = local_commit(str(head))
    if commit["tree"] != gate["authority_tree"]:
        fail("Authority public_verified tree moved before mutation")
    if local_content(str(head), MANIFEST_REL) != manifest_raw:
        fail("Authority manifest moved before mutation")
    if local_content(str(head), EVIDENCE_REL) != evidence_raw:
        fail("Authority public_verified evidence moved before mutation")


def require_mesh_token(environment: Mapping[str, str]) -> str:
    forbidden = sorted(
        key for key, value in environment.items()
        if value and (("ZENODO" in key.upper() and "TOKEN" in key.upper()) or key in {"GH_TOKEN", "GITHUB_TOKEN"})
    )
    if forbidden:
        fail("only QIKVRT_MESH_TOKEN is allowed; forbidden credential variable: " + forbidden[0])
    token = environment.get(MESH_TOKEN_ENV)
    if (
        not isinstance(token, str)
        or len(token.encode("utf-8")) < 20
        or len(token.encode("utf-8")) > MAX_TOKEN_BYTES
        or any(character.isspace() for character in token)
    ):
        fail("QIKVRT_MESH_TOKEN is missing or structurally invalid")
    return token


def verify_event(environment: Mapping[str, str], head: str) -> None:
    expected = {
        "GITHUB_REPOSITORY": AUTHORITY,
        "GITHUB_REF": PUBLIC_REF,
        "GITHUB_SHA": head,
        "QIKVRT_EVENT_CREATED": "true",
        "QIKVRT_EVENT_DELETED": "false",
        "QIKVRT_EVENT_FORCED": "false",
        "QIKVRT_EVENT_BEFORE": ZERO40,
        "QIKVRT_EVENT_AFTER": head,
    }
    for key, value in expected.items():
        if environment.get(key) != value:
            fail("workflow event is not the exact create-only/non-force Authority event: " + key)


def git_output(
    arguments: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    env: Mapping[str, str] | None = None,
    cwd: pathlib.Path | None = None,
) -> bytes:
    if cwd is None:
        cwd = ROOT
    process_env = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    process_env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0"})
    if env:
        process_env.update(env)
    try:
        completed = subprocess.run(
            ["git", *arguments], cwd=cwd, env=process_env,
            input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail("Git operation failed locally: " + type(exc).__name__)
    if completed.returncode != 0:
        fail("Git operation rejected: " + " ".join(arguments[:2]))
    return completed.stdout


def anonymous_git_ref(
    repository: str,
    ref: str,
    *,
    missing_ok: bool = False,
    additional_refs: Sequence[str] = (),
) -> str | None:
    """Read one exact public branch/tag without REST, credentials or proxy state."""
    fixed_refs = {
        PUBLIC_REF,
        OVERVIEW_REF,
        EQUALITY_REF,
    }
    dynamic_refs = set(additional_refs)
    structurally_valid_dynamic = (
        ref == PUBLICATION_REF
        or (
            ref.startswith(recovery.RECOVERY_REF_PREFIX)
            and HEX64.fullmatch(ref.removeprefix(recovery.RECOVERY_REF_PREFIX))
            is not None
        )
        or (
            ref.startswith(publish.CONSUMPTION_REF_PREFIX)
            and HEX64.fullmatch(ref.removeprefix(publish.CONSUMPTION_REF_PREFIX))
            is not None
        )
    )
    if (
        repository not in {AUTHORITY, MIRROR}
        or (
            ref not in fixed_refs
            and (ref not in dynamic_refs or not structurally_valid_dynamic)
        )
    ):
        fail("anonymous Git ref target escaped the finalization scope")
    temporary_base = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp"))
    if not temporary_base.is_dir():
        fail("anonymous Git reader lacks a safe temporary directory")
    with tempfile.TemporaryDirectory(
        prefix="qikvrt-corpus-ref-read-", dir=temporary_base
    ) as temporary:
        isolated = pathlib.Path(temporary)
        raw = git_output(
            [
                "-c", "credential.helper=",
                "-c", "http.extraHeader=",
                "-c", "http.https://github.com/.extraheader=",
                "-c", "http.proxy=",
                "-c", "https.proxy=",
                "ls-remote", "--refs",
                f"https://github.com/{repository}.git",
                ref,
            ],
            cwd=isolated,
            env={"GIT_CEILING_DIRECTORIES": str(isolated)},
        )
    try:
        output = raw.decode("ascii", errors="strict")
    except UnicodeDecodeError:
        fail("anonymous Git ref readback is not ASCII")
    lines = output.splitlines()
    if not lines:
        if missing_ok:
            return None
        fail(repository + " public ref is absent")
    if len(lines) != 1:
        fail(repository + " public ref readback is ambiguous")
    fields = lines[0].split("\t")
    if len(fields) != 2 or fields[1] != ref or HEX40.fullmatch(fields[0]) is None:
        fail(repository + " public ref readback differs from the exact contract")
    return fields[0]


def local_commit(commit: str) -> dict[str, Any]:
    if HEX40.fullmatch(commit) is None:
        fail("local immutable commit identity is invalid")
    raw = git_output(["show", "-s", "--format=%H%n%T%n%P%nEND", commit])
    try:
        lines = raw.decode("ascii", errors="strict").splitlines()
    except UnicodeDecodeError:
        fail("local immutable commit envelope is not ASCII")
    if (
        len(lines) != 4
        or lines[0] != commit
        or lines[3] != "END"
        or HEX40.fullmatch(lines[1]) is None
    ):
        fail("local immutable commit envelope differs")
    parents = [] if not lines[2] else lines[2].split(" ")
    if not all(HEX40.fullmatch(parent) is not None for parent in parents):
        fail("local immutable commit parents differ")
    return {"commit": commit, "tree": lines[1], "parents": parents}


def raw_commit_envelope(cwd: pathlib.Path, revision: str) -> dict[str, Any]:
    """Parse tree/parents from the raw object, unaffected by shallow grafts."""
    if not isinstance(revision, str) or not revision or any(
        character in revision for character in "\x00\r\n"
    ):
        fail("raw commit revision is invalid")
    object_type = git_output(["cat-file", "-t", revision], cwd=cwd)
    if object_type != b"commit\n":
        fail("anonymous Git object is not a commit")
    raw = git_output(["cat-file", "-p", revision], cwd=cwd)
    if len(raw) > MAX_JSON:
        fail("raw commit object exceeded its byte bound")
    header, separator, _message = raw.partition(b"\n\n")
    if not separator:
        fail("raw commit object lacks its header boundary")
    trees: list[str] = []
    parents: list[str] = []
    for line in header.splitlines():
        if line.startswith(b"tree "):
            try:
                trees.append(line.removeprefix(b"tree ").decode("ascii", errors="strict"))
            except UnicodeDecodeError:
                fail("raw commit tree is not ASCII")
        elif line.startswith(b"parent "):
            try:
                parents.append(line.removeprefix(b"parent ").decode("ascii", errors="strict"))
            except UnicodeDecodeError:
                fail("raw commit parent is not ASCII")
    if (
        len(trees) != 1
        or HEX40.fullmatch(trees[0]) is None
        or not all(HEX40.fullmatch(parent) is not None for parent in parents)
    ):
        fail("raw commit tree/parent envelope differs")
    return {"tree": trees[0], "parents": parents}


def local_content(commit: str, path: str, *, maximum: int = MAX_JSON) -> bytes:
    if HEX40.fullmatch(commit) is None or maximum < 0 or maximum > zenodo.MAX_UPLOAD_BYTES:
        fail("local immutable content target is invalid")
    safe = candidate.normalize_repo_relative(path, "immutable content path")
    raw = git_output(["show", f"{commit}:{safe}"])
    if len(raw) > maximum:
        fail("local immutable content exceeded its byte bound: " + safe)
    return raw


def local_head() -> str:
    value = git_output(["rev-parse", "--verify", "HEAD"]).decode("ascii").strip()
    if HEX40.fullmatch(value) is None:
        fail("local HEAD is invalid")
    return value


def local_commit_subject(commit: str) -> str:
    if HEX40.fullmatch(commit) is None:
        fail("local commit subject target is invalid")
    raw = git_output(["show", "-s", "--format=%s", commit])
    try:
        subject = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        fail("local commit subject is not UTF-8")
    if not subject.endswith("\n") or any(
        character in subject[:-1] for character in "\x00\r\n"
    ):
        fail("local commit subject envelope differs")
    return subject[:-1]


def local_changed_delta(older: str, newer: str) -> dict[str, str]:
    if HEX40.fullmatch(older) is None or HEX40.fullmatch(newer) is None:
        fail("local commit delta target is invalid")
    raw = git_output(
        ["diff", "--raw", "--no-abbrev", "--no-renames", "-z", older, newer, "--"]
    )
    if raw and not raw.endswith(b"\0"):
        fail("local commit delta lacks its NUL boundary")
    parts = raw[:-1].split(b"\0") if raw else []
    if len(parts) % 2 != 0:
        fail("local commit raw delta envelope differs")
    result: dict[str, str] = {}
    for index in range(0, len(parts), 2):
        metadata = parts[index]
        item = parts[index + 1]
        fields = metadata.split(b" ")
        if len(fields) != 5 or not fields[0].startswith(b":"):
            fail("local commit raw delta metadata differs")
        try:
            decoded = item.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            fail("local commit delta path is not UTF-8")
        path = candidate.normalize_repo_relative(decoded, "commit delta path")
        try:
            old_mode = fields[0][1:].decode("ascii", errors="strict")
            new_mode = fields[1].decode("ascii", errors="strict")
            old_sha = fields[2].decode("ascii", errors="strict")
            new_sha = fields[3].decode("ascii", errors="strict")
            status = fields[4].decode("ascii", errors="strict")
        except UnicodeDecodeError:
            fail("local commit raw delta metadata is not ASCII")
        expected_modes = (
            ("000000", "100644") if status == "A" else ("100644", "100644")
        )
        if (
            status not in {"A", "M"}
            or (old_mode, new_mode) != expected_modes
            or HEX40.fullmatch(old_sha) is None
            or HEX40.fullmatch(new_sha) is None
            or (status == "A" and old_sha != ZERO40)
            or (status == "M" and (old_sha == ZERO40 or new_sha == ZERO40))
            or path in result
        ):
            fail("local commit delta status/type/object identity differs")
        result[path] = status
    return result


def local_changed_paths(older: str, newer: str) -> frozenset[str]:
    return frozenset(local_changed_delta(older, newer))


def require_local_delta(
    older: str,
    newer: str,
    expected: Mapping[str, str],
    label: str,
) -> None:
    if local_changed_delta(older, newer) != dict(expected):
        fail(label + " status/path delta differs")


def validate_publication_binding_anonymous(
    *,
    manifest_raw: bytes,
    evidence_raw: bytes,
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
    head: str,
    require_public_ref: bool = True,
) -> dict[str, Any]:
    """Bind the mirror event to the complete immutable publication transaction."""
    validate_public_evidence(evidence, manifest)
    execution_head = evidence.get("repository_commit")
    authorization = manifest.get("owner_authorization")
    remote_consumption = evidence.get("remote_consumption")
    consumption_key = (
        authorization.get("consumption_key", {}).get("value")
        if isinstance(authorization, dict)
        and isinstance(authorization.get("consumption_key"), dict)
        else None
    )
    tag_object = (
        remote_consumption.get("tag_object")
        if isinstance(remote_consumption, dict)
        else None
    )
    consumption_ref = (
        remote_consumption.get("ref")
        if isinstance(remote_consumption, dict)
        else None
    )
    if (
        not isinstance(execution_head, str)
        or HEX40.fullmatch(execution_head) is None
        or not isinstance(consumption_key, str)
        or HEX64.fullmatch(consumption_key) is None
        or not isinstance(tag_object, str)
        or HEX40.fullmatch(tag_object) is None
        or not isinstance(consumption_ref, str)
        or consumption_ref != publish._remote_consumption_ref(consumption_key)
    ):
        fail("publication chain lacks its exact execution/consumption identity")

    try:
        contract = recovery.load_frozen_contract()
        context = recovery.make_context(
            execution_head,
            str(manifest.get("manifest_sha256")),
            consumption_key,
            tag_object,
        )
    except (recovery.CorpusRecoveryError, zenodo.ZenodoError) as exc:
        fail("publication recovery context rejected the mirror binding: " + str(exc))
    if (
        context.publication_ref != PUBLICATION_REF
        or context.consumption.ref != consumption_ref
        or context.consumption.tag_object != tag_object
    ):
        fail("publication recovery context refs differ from the public evidence")

    execution = local_commit(execution_head)
    if execution["parents"] != [recovery.CONTROL_BASE_HEAD]:
        fail("publication execution commit is not the sole child of the control base")
    require_local_delta(
        recovery.CONTROL_BASE_HEAD,
        execution_head,
        EXECUTION_DELTA_STATUSES,
        "publication execution commit exact 12-path",
    )
    if local_content(execution_head, MANIFEST_REL) != manifest_raw:
        fail("publication execution commit manifest bytes differ")

    final = local_commit(head)
    if (
        final["parents"] == []
        or len(final["parents"]) != 1
        or local_commit_subject(head) != recovery.PUBLICATION_COMMIT_SUBJECT
    ):
        fail("final publication commit subject/parent/4-path delta differs")
    require_local_delta(
        final["parents"][0],
        head,
        FINAL_DELTA_STATUSES,
        "final publication commit exact 4-path",
    )
    require_local_delta(
        execution_head,
        head,
        FINAL_CUMULATIVE_STATUSES,
        "publication execution-to-final cumulative 5-path",
    )
    if local_content(head, EVIDENCE_REL) != evidence_raw:
        fail("final publication commit evidence bytes differ")

    reverse_history: list[recovery.PersistedCheckpoint] = []
    cursor = final["parents"][0]
    visited: set[str] = set()
    while cursor != execution_head:
        if cursor in visited or len(reverse_history) >= recovery.MAX_RECOVERY_CHECKPOINTS:
            fail("publication recovery commit chain is cyclic or exceeds 135 checkpoints")
        visited.add(cursor)
        checkpoint = local_commit(cursor)
        if (
            len(checkpoint["parents"]) != 1
            or local_commit_subject(cursor) != recovery.RECOVERY_COMMIT_SUBJECT
        ):
            fail("publication recovery commit subject/parent/delta differs")
        require_local_delta(
            checkpoint["parents"][0],
            cursor,
            {
                recovery.RECOVERY_RELATIVE: (
                    "A"
                    if checkpoint["parents"][0] == execution_head
                    else "M"
                )
            },
            "publication recovery commit",
        )
        reverse_history.append(
            recovery.PersistedCheckpoint(
                cursor,
                checkpoint["parents"][0],
                recovery.RECOVERY_RELATIVE,
                local_content(cursor, recovery.RECOVERY_RELATIVE),
            )
        )
        cursor = checkpoint["parents"][0]
    history = list(reversed(reverse_history))
    try:
        values = recovery.validate_recovery_chain(history, contract, context)
    except recovery.CorpusRecoveryError as exc:
        fail("publication recovery chain rejected the mirror binding: " + str(exc))
    if not values or values[-1].get("phase") != "publish_requested":
        fail("publication recovery chain is not terminal publish_requested")

    dynamic_refs = (
        PUBLICATION_REF,
        context.recovery_ref,
        context.consumption.ref,
    )
    publication_head = anonymous_git_ref(
        AUTHORITY, PUBLICATION_REF, additional_refs=dynamic_refs
    )
    recovery_head = anonymous_git_ref(
        AUTHORITY, context.recovery_ref, additional_refs=dynamic_refs
    )
    observed_tag = anonymous_git_ref(
        AUTHORITY, context.consumption.ref, additional_refs=dynamic_refs
    )
    if publication_head != head:
        fail("live Authority publication ref differs from the event head")
    if recovery_head != final["parents"][0]:
        fail("live Authority recovery ref differs from the final parent")
    if observed_tag != context.consumption.tag_object:
        fail("live Authority consumption ref differs from the evidence tag object")
    final_checkpoint = recovery.PersistedCheckpoint(
        head,
        final["parents"][0],
        recovery.EVIDENCE_RELATIVE,
        evidence_raw,
    )
    try:
        recovery.validate_ref_state(
            history,
            context,
            str(recovery_head),
            str(publication_head),
            final_checkpoint,
        )
    except recovery.CorpusRecoveryError as exc:
        fail("publication recovery refs rejected the mirror binding: " + str(exc))

    public_head: str | None = None
    if require_public_ref:
        public_head = anonymous_git_ref(AUTHORITY, PUBLIC_REF)
        if public_head != head:
            fail("Authority public_verified ref differs from the publication event head")
    return {
        "execution_head": execution_head,
        "publication_head": publication_head,
        "recovery_ref": context.recovery_ref,
        "recovery_head": recovery_head,
        "consumption_ref": context.consumption.ref,
        "consumption_tag_object": observed_tag,
        "public_ref_head": public_head,
        "recovery_checkpoint_count": len(history),
        "terminal_recovery_phase": values[-1]["phase"],
    }


def push_create_only(repository: str, source: str, ref: str, token: str) -> None:
    if (
        repository not in {AUTHORITY, MIRROR}
        or HEX40.fullmatch(source) is None
        or ref not in {PUBLIC_REF, OVERVIEW_REF, EQUALITY_REF}
    ):
        fail("create-only push target is invalid")
    basic = base64.b64encode(("x-access-token:" + token).encode("utf-8")).decode("ascii")
    output = git_output(
        [
            "push",
            "--porcelain",
            "--force-with-lease=" + ref + ":",
            f"https://github.com/{repository}.git",
            f"{source}:{ref}",
        ],
        env={
            "GIT_CONFIG_COUNT": "3",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": "Authorization: Basic " + basic,
            "GIT_CONFIG_KEY_1": "credential.helper",
            "GIT_CONFIG_VALUE_1": "",
            "GIT_CONFIG_KEY_2": "core.hooksPath",
            "GIT_CONFIG_VALUE_2": "/dev/null",
        },
    ).decode("utf-8", errors="strict")
    if not any(line.startswith("*") and "[new " in line for line in output.splitlines()):
        fail("create-only push did not create a new non-force ref")


def ensure_create_only_ref(
    repository: str,
    ref: str,
    expected_commit: str,
    token: str,
) -> bool:
    """Create once, or resume only from the exact immutable expected ref."""
    observed = anonymous_git_ref(repository, ref, missing_ok=True)
    if observed is not None:
        if observed != expected_commit:
            fail(repository + " existing finalization ref is divergent: " + ref)
        return False
    mutation_failed = False
    try:
        push_create_only(repository, expected_commit, ref, token)
    except MirrorFinalizeError:
        mutation_failed = True
    readback = anonymous_git_ref(repository, ref, missing_ok=True)
    if readback == expected_commit:
        return True
    if readback is None:
        if mutation_failed:
            fail(repository + " create-only ref outcome remained absent after one mutation")
        fail(repository + " create-only ref disappeared after mutation")
    fail(repository + " create-only ref readback is divergent after one mutation")


def build_overview_files(
    manifest: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict[str, bytes]:
    """Create the three mandatory overview projections without touching the worktree."""
    paths = {
        "html": ROOT / "docs/publications/index.html",
        "json": ROOT / "docs/publications/index.json",
        "disclosure": ROOT / ".well-known/qik-vrt-self-disclosure.json",
    }
    try:
        html_raw = candidate.regular_bytes(paths["html"], zenodo.MAX_JSON_BYTES)
        overview_raw = candidate.regular_bytes(paths["json"], zenodo.MAX_JSON_BYTES)
        disclosure_raw = candidate.regular_bytes(paths["disclosure"], zenodo.MAX_JSON_BYTES)
    except candidate.CorpusCandidateError as exc:
        fail("publication overview source is unsafe: " + str(exc))
    overview = parse_json(overview_raw, "publication overview")
    disclosure = parse_json(disclosure_raw, "repository self-disclosure")
    records = overview.get("zenodo_records")
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        fail("publication overview zenodo_records is invalid")
    if any(
        item.get("id") == controls.PUBLICATION_ID
        or item.get("doi") == evidence["doi"]
        or item.get("receipt_path") == EVIDENCE_REL
        for item in records
    ):
        fail("retrospective proof corpus is already present in the publication overview")
    records.append(
        {
            "id": controls.PUBLICATION_ID,
            "title": manifest["metadata"]["title"],
            "doi": evidence["doi"],
            "doi_url": "https://doi.org/" + evidence["doi"],
            "concept_doi": evidence["conceptdoi"],
            "receipt_path": EVIDENCE_REL,
            "manifest_sha256": evidence["manifest_sha256"],
            "repository_commit": evidence["repository_commit"],
            "file_count": EXPECTED_UPLOADS,
            "state": "published_receipt",
            "boundary": (
                "Public byte-exact retrospective proof corpus; archival persistence "
                "does not establish peer review, empirical truth or repository-wide equality."
            ),
        }
    )
    overview_output = (
        json.dumps(overview, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

    try:
        html = html_raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("publication overview HTML is not UTF-8")
    start = html.find('<div class="record-grid">')
    if start < 0:
        fail("publication overview HTML lacks the Zenodo record grid")
    end = html.find("\n      </div>", start)
    if end < 0:
        fail("publication overview HTML record grid is not closed")
    doi_url = "https://doi.org/" + str(evidence["doi"])
    if doi_url in html:
        fail("retrospective proof corpus DOI is already present in overview HTML")
    title = str(manifest["metadata"]["title"])
    if any(character in title for character in "<>&\""):
        fail("publication title is unsafe for deterministic HTML insertion")
    card = (
        f'        <a class="record-card" href="{doi_url}"><span class="record-type">'
        f'Proof-Corpus</span><strong>{title}</strong><code>{evidence["doi"]}</code></a>'
    )
    html_output = (html[:end] + "\n" + card + html[end:]).encode("utf-8")

    bindings = disclosure.get("bindings")
    claims = disclosure.get("completion_claims")
    if not isinstance(bindings, dict) or not isinstance(claims, dict):
        fail("repository self-disclosure bindings/claims are invalid")
    if "retrospective_proof_corpus_publication" in bindings:
        fail("retrospective proof corpus disclosure binding already exists")
    if claims != {"pass": False, "final_pass": False, "effect_ack_done": False}:
        fail("repository-wide self-disclosure claims are not fail-closed")
    bindings["retrospective_proof_corpus_publication"] = {
        "publication_id": controls.PUBLICATION_ID,
        "doi": evidence["doi"],
        "concept_doi": evidence["conceptdoi"],
        "evidence_path": EVIDENCE_REL,
        "manifest_sha256": evidence["manifest_sha256"],
        "file_count": EXPECTED_UPLOADS,
        "authority_public_ref": PUBLIC_REF,
        "reciprocal_equality_ref": EQUALITY_REF,
        "scope_bound_only": True,
        "repository_wide_equality_claimed": False,
    }
    disclosure_output = (
        json.dumps(disclosure, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    return {
        "docs/publications/index.html": html_output,
        "docs/publications/index.json": overview_output,
        ".well-known/qik-vrt-self-disclosure.json": disclosure_output,
    }


def build_receipt(
    gate: Mapping[str, Any],
    overview_files: Mapping[str, bytes],
    overview_commit: str | None = None,
    overview_tree: str | None = None,
) -> bytes:
    overview_commit = overview_commit or ("0" * 40)
    overview_tree = overview_tree or ("0" * 40)
    value = {
        "_license": {
            "classification": "machine_readable_evidence",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": RECEIPT_SCHEMA,
        "receipt_id": RECEIPT_ID,
        "scope": {
            "publication_id": controls.PUBLICATION_ID,
            "authorization_id": controls.AUTHORIZATION_ID,
            "authority_repository": AUTHORITY,
            "mirror_repository": MIRROR,
            "authority_public_ref": PUBLIC_REF,
            "mirror_public_ref": PUBLIC_REF,
            "authority_overview_ref": OVERVIEW_REF,
            "mirror_overview_ref": OVERVIEW_REF,
            "authority_equality_ref": EQUALITY_REF,
            "mirror_equality_ref": EQUALITY_REF,
            "receipt_path": RECEIPT_REL,
            "main_equality_claimed": False,
            "repository_wide_equality_claimed": False,
        },
        "public_record": {
            "record_id": gate["record_id"],
            "doi": gate["doi"],
            "conceptdoi": gate["conceptdoi"],
            "manifest_sha256": gate["manifest_sha256"],
            "publication_evidence_sha256": gate["evidence_sha256"],
            "file_count": gate["file_count"],
            "total_bytes": gate["total_bytes"],
            "anonymous_byte_redownload_required": True,
        },
        "shared_public_source": {
            "commit": gate["authority_head"],
            "tree": gate["authority_tree"],
        },
        "git_ref_acquisition": {
            "mode": "GIT_CAS_CREATE_ONLY",
            "lease_contract": "EXPECTED_OLD_ABSENT",
            "force_update_allowed": False,
            "unbound_lease_allowed": False,
            "main_ref_allowed": False,
        },
        "publication_overview": {
            "same_finalization_commit_required": True,
            "shared_commit": overview_commit,
            "shared_tree": overview_tree,
            "files": [
                {
                    "path": path,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "git_blob_sha1": git_blob_sha1(raw),
                }
                for path, raw in sorted(overview_files.items())
            ],
        },
        "effect_boundary": {
            "embedded_state": "EFFECT_ACK_CONTINUE",
            "effect_ack_done": False,
            "ordinary_release": False,
            "done_only_after": [
                "both public refs resolve anonymously to the shared source commit/tree",
                "both overview refs resolve anonymously to one integrity-valid commit/tree",
                "both equality refs resolve anonymously to one derived commit/tree",
                "both repositories return this exact receipt bytes from that commit",
                "both equality commits pass anonymous-checkout repository integrity",
                "the final anonymous 65-file Zenodo redownload passes",
            ],
            "final_evaluation_is_live_and_scope_bound": True,
        },
    }
    return json_bytes(value)


def _write_stage_file(root: pathlib.Path, relative: str, raw: bytes) -> None:
    safe = candidate.normalize_repo_relative(relative, "derived finalization path")
    path = root.joinpath(*pathlib.PurePosixPath(safe).parts)
    current = root
    for part in pathlib.PurePosixPath(safe).parts[:-1]:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            fail("derived finalization parent is unsafe: " + safe)
    flags = os.O_WRONLY | os.O_TRUNC | getattr(os, "O_CLOEXEC", 0)
    if path.exists() or path.is_symlink():
        flags |= getattr(os, "O_NOFOLLOW", 0)
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o644)
    except OSError as exc:
        fail("cannot open derived finalization file safely: " + safe)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                fail("derived finalization write made no progress: " + safe)
            offset += written
        os.fsync(descriptor)
    except OSError:
        fail("cannot write derived finalization file: " + safe)
    finally:
        os.close(descriptor)


def _run_integrity(root: pathlib.Path, action: str) -> None:
    if action not in {"generate", "verify"}:
        fail("integrity action is invalid")
    environment = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-B", "tools/qikvrt_integrity.py", action],
            cwd=root, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=300, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail("derived integrity operation failed: " + type(exc).__name__)
    if completed.returncode != 0:
        fail("derived integrity " + action + " rejected the stage")


def _run_stage_overview_tests(root: pathlib.Path) -> None:
    environment = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                "tests/test_qikvrt_self_disclosure.py",
            ],
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail("derived publication overview test failed: " + type(exc).__name__)
    if completed.returncode != 0:
        fail("derived publication overview/self-disclosure test rejected the stage")


def create_verified_stage_commit(
    parent: str,
    outputs: Mapping[str, bytes],
    message: bytes,
) -> tuple[str, str]:
    """Derive one common commit while leaving the source worktree untouched."""
    if HEX40.fullmatch(parent) is None or not outputs:
        fail("derived stage parent/outputs are invalid")
    for relative, raw in outputs.items():
        candidate.normalize_repo_relative(relative, "derived finalization path")
        if not isinstance(raw, bytes):
            fail("derived finalization output is not bytes")
    temporary_base = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp"))
    with tempfile.TemporaryDirectory(
        prefix="qikvrt-corpus-finalize-", dir=temporary_base
    ) as temporary:
        stage = pathlib.Path(temporary) / "worktree"
        git_output(["worktree", "add", "--detach", str(stage), parent])
        try:
            for relative, raw in outputs.items():
                _write_stage_file(stage, relative, raw)
            _run_integrity(stage, "generate")
            _run_integrity(stage, "verify")
            _run_stage_overview_tests(stage)
            expected_paths = sorted([*outputs, *INTEGRITY_PATHS])
            git_output(["add", "--", *expected_paths], cwd=stage)
            changed = git_output(
                ["diff", "--cached", "--name-only", "-z"], cwd=stage
            ).decode("utf-8", errors="strict").split("\0")
            if sorted(path for path in changed if path) != expected_paths:
                fail("derived stage changed paths outside outputs and integrity trio")
            unstaged = git_output(["diff", "--name-only", "-z"], cwd=stage)
            untracked = git_output(
                ["ls-files", "--others", "--exclude-standard", "-z"], cwd=stage
            )
            if unstaged or untracked:
                fail("derived stage contains unstaged or untracked changes")
            tree = git_output(["write-tree"], cwd=stage).decode("ascii").strip()
        finally:
            git_output(["worktree", "remove", "--force", str(stage)])
    parent_value = git_output(["show", "-s", "--format=%cI", parent]).decode("utf-8").strip()
    try:
        parsed = datetime.datetime.fromisoformat(parent_value.replace("Z", "+00:00"))
    except ValueError:
        fail("source commit timestamp is invalid")
    date = parsed.isoformat()
    commit_env = {
        "GIT_AUTHOR_NAME": "QIK-VRT Corpus Equality Finalizer",
        "GIT_AUTHOR_EMAIL": "qik-vrt@users.noreply.github.com",
        "GIT_AUTHOR_DATE": date,
        "GIT_COMMITTER_NAME": "QIK-VRT Corpus Equality Finalizer",
        "GIT_COMMITTER_EMAIL": "qik-vrt@users.noreply.github.com",
        "GIT_COMMITTER_DATE": date,
    }
    commit = git_output(
        ["commit-tree", tree, "-p", parent],
        input_bytes=message,
        env=commit_env,
    ).decode("ascii").strip()
    if HEX40.fullmatch(commit) is None:
        fail("derived finalization commit identity is invalid")
    return commit, tree


def verify_pair(
    transport: AnonymousHTTPS,
    ref: str,
    expected_commit: str,
    *,
    expected_tree: str | None = None,
    expected_parent: str | None = None,
) -> dict[str, Any]:
    del transport
    commit = local_commit(expected_commit)
    for repository in (AUTHORITY, MIRROR):
        head = anonymous_git_ref(repository, ref)
        if head != expected_commit:
            fail(repository + " pair ref differs from the expected shared commit")
    if expected_tree is not None and commit["tree"] != expected_tree:
        fail("shared pair tree differs")
    if expected_parent is not None and commit["parents"] != [expected_parent]:
        fail("shared pair commit parent differs")
    return commit


def verify_remote_integrity_anonymous(
    repository: str,
    ref: str,
    expected_commit: str,
    *,
    expected_tree: str | None = None,
    expected_parent: str | None = None,
    expected_files: Mapping[str, bytes] | None = None,
) -> None:
    """Fetch one public ref without any credential/proxy and verify its tree."""
    if repository not in {AUTHORITY, MIRROR} or HEX40.fullmatch(expected_commit) is None:
        fail("anonymous integrity checkout target is invalid")
    temporary_base = pathlib.Path(os.environ.get("RUNNER_TEMP", "/tmp"))
    with tempfile.TemporaryDirectory(
        prefix="qikvrt-corpus-public-checkout-", dir=temporary_base
    ) as temporary:
        checkout = pathlib.Path(temporary)
        git_output(["init", "--quiet"], cwd=checkout)
        git_output(
            [
                "-c", "credential.helper=",
                "-c", "http.extraHeader=",
                "-c", "http.https://github.com/.extraheader=",
                "-c", "http.proxy=",
                "-c", "https.proxy=",
                "fetch", "--quiet", "--depth=1",
                f"https://github.com/{repository}.git", ref,
            ],
            cwd=checkout,
        )
        fetched = git_output(["rev-parse", "--verify", "FETCH_HEAD"], cwd=checkout).decode("ascii").strip()
        if fetched != expected_commit:
            fail(repository + " anonymous checkout commit differs")
        envelope = raw_commit_envelope(checkout, "FETCH_HEAD")
        if expected_tree is not None and envelope["tree"] != expected_tree:
            fail(repository + " anonymous checkout tree differs")
        if expected_parent is not None and envelope["parents"] != [expected_parent]:
            fail(repository + " anonymous checkout parent differs")
        git_output(["checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=checkout)
        _run_integrity(checkout, "verify")
        for relative, expected in (expected_files or {}).items():
            safe = candidate.normalize_repo_relative(
                relative, "anonymous checkout content path"
            )
            try:
                observed = candidate.regular_bytes(
                    checkout.joinpath(*pathlib.PurePosixPath(safe).parts),
                    max(len(expected), 1),
                )
            except candidate.CorpusCandidateError as exc:
                fail(repository + " anonymous checkout content is unsafe: " + str(exc))
            if observed != expected:
                fail(repository + " anonymous checkout bytes differ: " + safe)


def verify_pair_integrity_anonymous(
    ref: str,
    expected_commit: str,
    *,
    expected_tree: str | None = None,
    expected_parent: str | None = None,
    expected_files: Mapping[str, bytes] | None = None,
) -> None:
    for repository in (AUTHORITY, MIRROR):
        verify_remote_integrity_anonymous(
            repository,
            ref,
            expected_commit,
            expected_tree=expected_tree,
            expected_parent=expected_parent,
            expected_files=expected_files,
        )


def emit_frame(number: int, operation: str, percent: int, status: str, blocker: str, next_action: str) -> None:
    width = 20
    filled = percent * width // 100
    print(
        f"Repository: {AUTHORITY} <-> {MIRROR}\n"
        f"Branch: {PUBLIC_REF} / {EQUALITY_REF}\n"
        f"Commit: scope-bound\n"
        f"Operation: {operation}\n"
        f"Frame: {number} — transaction\n\n"
        f"[{'█' * filled}{'░' * (width - filled)}] {percent}%\n\n"
        f"BLOCKER: {blocker}\nNEXT: {next_action}\nSTATUS = {status}",
        flush=True,
    )


def finalize(
    *,
    transport: AnonymousHTTPS,
    environment: Mapping[str, str],
    manifest_raw: bytes,
    evidence_raw: bytes,
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
    head: str,
) -> dict[str, Any]:
    token = require_mesh_token(environment)
    verify_event(environment, head)
    validate_public_evidence(evidence, manifest)
    gate = verify_authority_gate(
        transport, manifest_raw, evidence_raw, manifest, evidence, head
    )

    verify_guard_unchanged(transport, gate, manifest_raw, evidence_raw)
    emit_frame(1, "ensure Mirror public_verified ref", 30, "RUNNING", "none", "anonymous pair readback")
    ensure_create_only_ref(MIRROR, PUBLIC_REF, head, token)
    verify_pair(transport, PUBLIC_REF, head, expected_tree=str(gate["authority_tree"]))
    verify_remote_integrity_anonymous(
        MIRROR,
        PUBLIC_REF,
        head,
        expected_tree=str(gate["authority_tree"]),
        expected_files={MANIFEST_REL: manifest_raw, EVIDENCE_REL: evidence_raw},
    )

    overview_files = build_overview_files(manifest, evidence)
    overview_commit, overview_tree = create_verified_stage_commit(
        head,
        overview_files,
        b"Add retrospective proof corpus to publication overview\n",
    )
    for number, repository in ((2, AUTHORITY), (3, MIRROR)):
        verify_guard_unchanged(transport, gate, manifest_raw, evidence_raw)
        verify_pair(transport, PUBLIC_REF, head, expected_tree=str(gate["authority_tree"]))
        emit_frame(number, "ensure publication overview in " + repository, 40 + number * 10, "RUNNING", "none", "next overview ref/readback")
        ensure_create_only_ref(
            repository, OVERVIEW_REF, overview_commit, token
        )

    verify_pair(
        transport, OVERVIEW_REF, overview_commit,
        expected_tree=overview_tree, expected_parent=head,
    )
    verify_pair_integrity_anonymous(
        OVERVIEW_REF,
        overview_commit,
        expected_tree=overview_tree,
        expected_parent=head,
        expected_files=overview_files,
    )

    receipt_raw = build_receipt(
        gate, overview_files, overview_commit, overview_tree
    )
    equality_commit, equality_tree = create_verified_stage_commit(
        overview_commit,
        {RECEIPT_REL: receipt_raw},
        b"Bind retrospective proof corpus reciprocal equality receipt\n",
    )
    for number, repository in ((4, AUTHORITY), (5, MIRROR)):
        verify_guard_unchanged(transport, gate, manifest_raw, evidence_raw)
        verify_pair(
            transport, OVERVIEW_REF, overview_commit,
            expected_tree=overview_tree, expected_parent=head,
        )
        emit_frame(number, "ensure reciprocal receipt in " + repository, 65 + number * 5, "RUNNING", "none", "next equality ref/readback")
        ensure_create_only_ref(
            repository, EQUALITY_REF, equality_commit, token
        )

    verify_pair(
        transport, EQUALITY_REF, equality_commit,
        expected_tree=equality_tree, expected_parent=overview_commit,
    )
    verify_pair_integrity_anonymous(
        EQUALITY_REF,
        equality_commit,
        expected_tree=equality_tree,
        expected_parent=overview_commit,
        expected_files={RECEIPT_REL: receipt_raw, **overview_files},
    )

    final_gate = verify_authority_gate(
        transport, manifest_raw, evidence_raw, manifest, evidence, head
    )
    if final_gate != gate:
        fail("final anonymous public gate differs from the pre-mutation gate")
    # The final evaluation is live: re-read all three ref pairs after the last
    # remote effect and the second complete Zenodo byte gate.  Immutable
    # commit/integrity evidence above remains reusable only while these live
    # refs still resolve to the exact objects it bound.
    verify_pair(
        transport,
        PUBLIC_REF,
        head,
        expected_tree=str(gate["authority_tree"]),
    )
    verify_pair(
        transport,
        OVERVIEW_REF,
        overview_commit,
        expected_tree=overview_tree,
        expected_parent=head,
    )
    verify_pair(
        transport,
        EQUALITY_REF,
        equality_commit,
        expected_tree=equality_tree,
        expected_parent=overview_commit,
    )
    report = {
        "schema": "qikvrt_retrospective_proof_corpus_mirror_finalization_v1",
        "scope": {
            "publication_id": controls.PUBLICATION_ID,
            "authority_repository": AUTHORITY,
            "mirror_repository": MIRROR,
            "public_ref": PUBLIC_REF,
            "overview_ref": OVERVIEW_REF,
            "equality_ref": EQUALITY_REF,
            "main_equality_claimed": False,
            "repository_wide_equality_claimed": False,
        },
        "public_source_commit": head,
        "public_source_tree": gate["authority_tree"],
        "overview_commit": overview_commit,
        "overview_tree": overview_tree,
        "equality_commit": equality_commit,
        "equality_tree": equality_tree,
        "receipt_path": RECEIPT_REL,
        "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "publication_overview_paths": sorted(overview_files),
        "publication_overview_same_commit_verified": True,
        "anonymous_public_gates": 2,
        "public_file_count": EXPECTED_UPLOADS,
        "public_total_bytes": EXPECTED_TOTAL_BYTES,
        "effect_state": "EFFECT_ACK_DONE",
        "ordinary_release": True,
        "effect_scope_bound": True,
    }
    emit_frame(6, "scope-bound reciprocal equality finalization", 100, "PASS", "none", "none")
    return report


def load_local_contract() -> tuple[bytes, bytes, dict[str, Any], dict[str, Any]]:
    manifest_path = ROOT.joinpath(*pathlib.PurePosixPath(MANIFEST_REL).parts)
    evidence_path = ROOT.joinpath(*pathlib.PurePosixPath(EVIDENCE_REL).parts)
    try:
        manifest_raw = candidate.regular_bytes(manifest_path, zenodo.MAX_JSON_BYTES)
        evidence_raw = candidate.regular_bytes(evidence_path, zenodo.MAX_JSON_BYTES)
    except candidate.CorpusCandidateError as exc:
        fail(str(exc))
    try:
        manifest = publish.load_manifest(manifest_path, ROOT)
    except zenodo.ZenodoError as exc:
        fail("publication manifest gate rejected finalization: " + str(exc))
    evidence = parse_json(evidence_raw, "publication evidence")
    validate_public_evidence(evidence, manifest)
    try:
        publish._validate_recovery_evidence(
            evidence,
            manifest_path,
            ROOT,
            manifest,
            str(evidence["repository_commit"]),
        )
    except zenodo.ZenodoError as exc:
        fail("generic public_verified recovery gate rejected finalization: " + str(exc))
    return manifest_raw, evidence_raw, manifest, evidence


def bootstrap_authority_public_ref(
    *,
    environment: Mapping[str, str],
    manifest_raw: bytes,
    evidence_raw: bytes,
    manifest: Mapping[str, Any],
    evidence: Mapping[str, Any],
    head: str,
) -> dict[str, Any]:
    """Create/resume the Authority trigger ref without claiming finalization."""
    token = require_mesh_token(environment)
    before = validate_publication_binding_anonymous(
        manifest_raw=manifest_raw,
        evidence_raw=evidence_raw,
        manifest=manifest,
        evidence=evidence,
        head=head,
        require_public_ref=False,
    )
    created = ensure_create_only_ref(AUTHORITY, PUBLIC_REF, head, token)
    after = validate_publication_binding_anonymous(
        manifest_raw=manifest_raw,
        evidence_raw=evidence_raw,
        manifest=manifest,
        evidence=evidence,
        head=head,
        require_public_ref=True,
    )
    stable_keys = {
        "execution_head",
        "publication_head",
        "recovery_ref",
        "recovery_head",
        "consumption_ref",
        "consumption_tag_object",
        "recovery_checkpoint_count",
        "terminal_recovery_phase",
    }
    if any(before.get(key) != after.get(key) for key in stable_keys):
        fail("publication binding changed across the Authority public-ref bootstrap")
    if after.get("public_ref_head") != head:
        fail("Authority public-ref bootstrap lacks its exact anonymous readback")
    return {
        "schema": "qikvrt_retrospective_proof_corpus_authority_public_ref_bootstrap_v1",
        "scope": {
            "repository": AUTHORITY,
            "publication_id": controls.PUBLICATION_ID,
            "public_ref": PUBLIC_REF,
            "publication_ref": PUBLICATION_REF,
        },
        "head": head,
        "created": created,
        "exact_existing_resume": not created,
        "recovery_checkpoint_count": after["recovery_checkpoint_count"],
        "terminal_recovery_phase": after["terminal_recovery_phase"],
        "anonymous_readback_verified": True,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "ordinary_release": False,
    }


def source_check() -> dict[str, Any]:
    if EXPECTED_UPLOADS != 65 or EXPECTED_TOTAL_BYTES != 221_808_115:
        fail("frozen corpus count/byte constants differ")
    if controls.PUBLICATION_ID != "qikvrt-retrospective-proof-corpus-2026-07-28-v3":
        fail("publication scope drift")
    refs = {PUBLIC_REF, OVERVIEW_REF, EQUALITY_REF}
    if len(refs) != 3 or not all(ref.startswith("refs/heads/evidence/") for ref in refs):
        fail("dedicated finalization refs are invalid")
    if (
        PUBLICATION_REF != recovery.PUBLICATION_REF
        or recovery.CONTROL_BASE_HEAD
        != "c556382c89d32faf7bdd193d8e58c4a190ebc3cc"
        or recovery.MAX_RECOVERY_CHECKPOINTS != 135
        or len(EXECUTION_DELTA_PATHS) != 12
        or len(FINAL_DELTA_PATHS) != 4
        or len(FINAL_CUMULATIVE_PATHS) != 5
    ):
        fail("publication/recovery cross-integration constants differ")
    return {
        "state": "SOURCE_CONTRACT_PASS",
        "network_effect": False,
        "git_effect": False,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "ordinary_release": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument("--check-source", action="store_true")
    operations.add_argument("--bootstrap-authority-public-ref", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_source:
            print(json.dumps(source_check(), sort_keys=True))
            return 0
        manifest_raw, evidence_raw, manifest, evidence = load_local_contract()
        head = local_head()
        if args.bootstrap_authority_public_ref:
            report = bootstrap_authority_public_ref(
                environment=os.environ,
                manifest_raw=manifest_raw,
                evidence_raw=evidence_raw,
                manifest=manifest,
                evidence=evidence,
                head=head,
            )
        else:
            report = finalize(
                transport=AnonymousHTTPS(), environment=os.environ,
                manifest_raw=manifest_raw, evidence_raw=evidence_raw,
                manifest=manifest, evidence=evidence, head=head,
            )
    except MirrorFinalizeError as exc:
        raise SystemExit("EFFECT_ACK_BLOCK " + str(exc)) from exc
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
