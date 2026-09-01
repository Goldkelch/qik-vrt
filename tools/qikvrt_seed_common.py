#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed Seed registry and mesh operations.

The original Seed shell scripts used textual searches to parse JSON and TSV
records.  This module is their shared, typed implementation.  It deliberately
uses only the Python standard library so the workflows do not need to install
dependencies before validating untrusted registry or remote data.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import datetime as dt
import hashlib
import html
import json
import os
import re
import ssl
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

try:
    from tools import qikvrt_workflow_executor as workflow_executor
except ModuleNotFoundError:  # Script execution keeps tools/ as sys.path[0].
    import qikvrt_workflow_executor as workflow_executor


MAX_INPUT_BYTES = 1_048_576
MAX_NODE_ROWS = 10_000
DEFAULT_SEED_REPOSITORY = "Goldkelch/qik-vrt"
REPOSITORY_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
BRANCH_RE = re.compile(r"[A-Za-z0-9._~/-]+\Z")
RUN_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
POLICY_STATES = frozenset({"ACTIVE", "SUSPENDED", "REVOKED"})
EFFECTIVE_STATES = frozenset({"ACTIVE", "STALE", "SUSPENDED", "REVOKED", "UNKNOWN"})
BOUNDARY_KEYS = (
    "no_global_scanning",
    "no_self_propagation",
    "no_remote_mutation_without_authorization",
)


class SeedError(RuntimeError):
    """A validation or execution error that must stop the Seed operation."""


@dataclasses.dataclass(frozen=True)
class NodeRecord:
    guid: str
    source_repository: str
    seed_repository: str
    request_url: str
    node_branch: str
    node_state_ref: str
    heartbeat_ttl_minutes: int
    lifecycle_policy: str
    source_path: str
    source_line: int


@dataclasses.dataclass(frozen=True)
class PolicyRecord:
    guid: str
    status: str
    reason: str


@dataclasses.dataclass(frozen=True)
class FetchedJson:
    value: dict[str, Any]
    sha256: str


def _reject_constant(value: str) -> None:
    raise SeedError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SeedError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if not raw:
        raise SeedError(f"{label}: empty JSON document")
    if len(raw) > MAX_INPUT_BYTES:
        raise SeedError(f"{label}: JSON document exceeds {MAX_INPUT_BYTES} bytes")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SeedError(f"{label}: invalid UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except SeedError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise SeedError(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SeedError(f"{label}: top-level JSON value must be an object")
    return value


def read_json(path: Path, label: str | None = None) -> dict[str, Any]:
    try:
        raw = _read_bytes_limited(path)
    except OSError as exc:
        raise SeedError(f"cannot read {path}: {exc}") from exc
    return parse_json_bytes(raw, label or str(path))


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    _reject_symlink_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_symlink_path(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o644)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _reject_symlink_path(path)
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            temporary_path.unlink()
        raise


def write_json(path: Path, value: Any) -> None:
    _atomic_write(path, canonical_json_bytes(value))


def write_text(path: Path, value: str) -> None:
    _atomic_write(path, value.encode("utf-8"))


def _require_regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise SeedError(f"required regular file is missing or unsafe: {path}")


def _reject_symlink_path(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise SeedError(f"symlink path is forbidden: {current}")
        if current == current.parent:
            break
        current = current.parent


def _read_bytes_limited(path: Path, max_bytes: int = MAX_INPUT_BYTES) -> bytes:
    _reject_symlink_path(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SeedError(f"cannot open required regular file {path}: {exc}") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SeedError(f"required path is not a regular file: {path}")
        if before.st_size > max_bytes:
            raise SeedError(f"input file exceeds {max_bytes} bytes: {path}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise SeedError(f"input file exceeds {max_bytes} bytes: {path}")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise SeedError(f"input file changed while being read: {path}")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_text_limited(path: Path) -> str:
    try:
        return _read_bytes_limited(path).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SeedError(f"invalid UTF-8 in {path}") from exc


def _validate_run_id(run_id: str) -> str:
    if not RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
        raise SeedError("run id must be 1-128 safe filename characters")
    return run_id


def _validate_repository(value: str, label: str) -> str:
    if not REPOSITORY_RE.fullmatch(value):
        raise SeedError(f"{label}: invalid owner/repository value")
    owner, repository = value.split("/", 1)
    if owner in {".", ".."} or repository in {".", ".."}:
        raise SeedError(f"{label}: dot path components are forbidden")
    return value


def _validate_branch(value: str) -> str:
    if (
        not value
        or len(value) > 255
        or not BRANCH_RE.fullmatch(value)
        or value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or any(part in {".", ".."} for part in value.split("/"))
    ):
        raise SeedError("invalid node branch")
    return value


def _validate_guid(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise SeedError(f"invalid node GUID: {value!r}") from exc
    canonical = str(parsed)
    if value != canonical:
        raise SeedError(f"node GUID must use canonical lower-case form: {value!r}")
    return value


def validate_raw_request_url(url: str, source_repository: str) -> str:
    if any(ord(character) < 0x20 for character in url) or "\\" in url:
        raise SeedError("request URL contains a control character or backslash")
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError as exc:
        raise SeedError("request URL cannot be parsed") from exc
    try:
        hostname = parsed.hostname
        port = parsed.port
        username = parsed.username
        password = parsed.password
    except ValueError as exc:
        raise SeedError("request URL authority is invalid") from exc
    if (
        parsed.scheme != "https"
        or hostname != "raw.githubusercontent.com"
        or port not in {None, 443}
        or username is not None
        or password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SeedError("request URL must be an unqualified raw.githubusercontent.com HTTPS URL")
    if "%" in parsed.path or urllib.parse.unquote(parsed.path) != parsed.path:
        raise SeedError("percent-encoded request URL paths are forbidden")
    owner, repository = source_repository.split("/", 1)
    prefix = f"/{owner}/{repository}/"
    suffix = "/qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json"
    if not parsed.path.startswith(prefix) or not parsed.path.endswith(suffix):
        raise SeedError("request URL is not bound to the declared source repository and request path")
    middle = parsed.path[len(prefix) : -len(suffix)]
    if not middle or any(part in {"", ".", ".."} for part in middle.split("/")):
        raise SeedError("request URL has an invalid revision component")
    return url


def _parse_tsv(path: Path, expected_columns: int) -> list[tuple[int, list[str]]]:
    rows: list[tuple[int, list[str]]] = []
    for line_number, raw_line in enumerate(_read_text_limited(path).splitlines(), 1):
        if not raw_line or raw_line.startswith("#"):
            continue
        fields = raw_line.split("\t")
        if len(fields) != expected_columns:
            raise SeedError(
                f"{path}:{line_number}: expected exactly {expected_columns} tab-separated fields, got {len(fields)}"
            )
        if any(not field or field != field.strip() for field in fields):
            raise SeedError(f"{path}:{line_number}: empty or whitespace-padded TSV field")
        if any(any(ord(character) < 0x20 for character in field) for field in fields):
            raise SeedError(f"{path}:{line_number}: control character in TSV field")
        rows.append((line_number, fields))
        if len(rows) > MAX_NODE_ROWS:
            raise SeedError(f"{path}: more than {MAX_NODE_ROWS} records")
    return rows


def load_policies(root: Path) -> dict[str, PolicyRecord]:
    path = root / "registry/NODE_POLICY.tsv"
    policies: dict[str, PolicyRecord] = {}
    for line_number, fields in _parse_tsv(path, 3):
        guid, status, reason = fields
        _validate_guid(guid)
        if status not in POLICY_STATES:
            raise SeedError(f"{path}:{line_number}: invalid policy state {status!r}")
        if guid in policies:
            raise SeedError(f"{path}:{line_number}: duplicate policy GUID {guid}")
        policies[guid] = PolicyRecord(guid=guid, status=status, reason=reason)
    return policies


def _registry_tsv_paths(root: Path) -> list[Path]:
    known = root / "registry/KNOWN_NODE_REQUESTS.tsv"
    _require_regular_file(known)
    queue = root / "registry/node_request_queue"
    result = [known]
    if queue.exists():
        if queue.is_symlink() or not queue.is_dir():
            raise SeedError(f"unsafe queue directory: {queue}")
        result.extend(sorted(path for path in queue.glob("*.tsv") if path.is_file() and not path.is_symlink()))
    return result


def load_nodes(root: Path, seed_repository: str) -> tuple[list[NodeRecord], dict[str, PolicyRecord]]:
    _validate_repository(seed_repository, "configured seed repository")
    policies = load_policies(root)
    nodes: list[NodeRecord] = []
    seen: set[str] = set()
    for path in _registry_tsv_paths(root):
        relative_path = path.relative_to(root).as_posix()
        for line_number, fields in _parse_tsv(path, 8):
            guid, source, seed, request_url, branch, state_ref, ttl_text, lifecycle = fields
            _validate_guid(guid)
            _validate_repository(source, f"{path}:{line_number} source repository")
            _validate_repository(seed, f"{path}:{line_number} seed repository")
            if seed != seed_repository:
                raise SeedError(f"{path}:{line_number}: seed repository is outside the configured allowlist")
            validate_raw_request_url(request_url, source)
            _validate_branch(branch)
            _validate_branch(state_ref)
            try:
                ttl = int(ttl_text, 10)
            except ValueError as exc:
                raise SeedError(f"{path}:{line_number}: heartbeat TTL is not an integer") from exc
            if not 1 <= ttl <= 10_080:
                raise SeedError(f"{path}:{line_number}: heartbeat TTL must be between 1 and 10080 minutes")
            if lifecycle not in POLICY_STATES:
                raise SeedError(f"{path}:{line_number}: invalid lifecycle policy {lifecycle!r}")
            if guid in seen:
                raise SeedError(f"{path}:{line_number}: duplicate node GUID {guid}")
            policy = policies.get(guid)
            if policy is None:
                raise SeedError(f"{path}:{line_number}: node has no explicit allowlist policy")
            if policy.status != lifecycle:
                raise SeedError(
                    f"{path}:{line_number}: lifecycle policy {lifecycle} disagrees with NODE_POLICY state {policy.status}"
                )
            seen.add(guid)
            nodes.append(
                NodeRecord(
                    guid=guid,
                    source_repository=source,
                    seed_repository=seed,
                    request_url=request_url,
                    node_branch=branch,
                    node_state_ref=state_ref,
                    heartbeat_ttl_minutes=ttl,
                    lifecycle_policy=lifecycle,
                    source_path=relative_path,
                    source_line=line_number,
                )
            )
    if not nodes:
        raise SeedError("node registry is empty")
    orphaned = sorted(set(policies) - seen)
    if orphaned:
        raise SeedError(f"NODE_POLICY contains entries outside the node registry: {', '.join(orphaned)}")
    return sorted(nodes, key=lambda node: (node.guid, node.source_repository)), policies


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class HttpJsonFetcher:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 60:
            raise SeedError("HTTP timeout must be in the interval (0, 60]")
        self.timeout_seconds = timeout_seconds
        context = ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            _NoRedirect(),
            urllib.request.HTTPSHandler(context=context),
        )

    def __call__(self, url: str) -> FetchedJson:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json, text/plain;q=0.9",
                "User-Agent": "qikvrt-seed-validator/2",
            },
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise SeedError(f"HTTP status {response.status} for {url}")
                if response.geturl() != url:
                    raise SeedError(f"redirected response is forbidden for {url}")
                raw = response.read(MAX_INPUT_BYTES + 1)
        except SeedError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            raise SeedError(f"network fetch failed for {url}: {exc}") from exc
        value = parse_json_bytes(raw, url)
        return FetchedJson(value=value, sha256=hashlib.sha256(raw).hexdigest())


def _require_exact(value: Mapping[str, Any], key: str, expected: Any, label: str) -> None:
    if key not in value or type(value[key]) is not type(expected) or value[key] != expected:
        raise SeedError(f"{label}: {key} must equal {expected!r}")


def _validate_boundaries(value: Mapping[str, Any], label: str) -> None:
    for key in BOUNDARY_KEYS:
        _require_exact(value, key, True, label)


def validate_registration_request(document: Mapping[str, Any], node: NodeRecord) -> str | None:
    label = f"registration request for {node.guid}"
    _require_exact(document, "event", "QIKVRT_NODE_ONBOARDING_REQUEST", label)
    _require_exact(document, "role", "node", label)
    _require_exact(document, "repository_guid", node.guid, label)
    _require_exact(document, "source_repository", node.source_repository, label)
    _require_exact(document, "seed_repository", node.seed_repository, label)
    _require_exact(document, "seed_url", f"https://github.com/{node.seed_repository}", label)
    _require_exact(document, "automatic_after_setup", True, label)
    _require_exact(document, "no_further_human_machine_interaction_after_setup", True, label)
    _require_exact(document, "authorized_manifest_graph_only", True, label)
    _validate_boundaries(document, label)
    if node.source_path.startswith("registry/node_request_queue/"):
        return workflow_executor.validate_node_continuity_declaration(
            document,
            node.source_repository,
            node.node_branch,
        )
    return None


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _parse_utc(value: Any, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SeedError(f"{label}: expected RFC3339 UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise SeedError(f"{label}: invalid RFC3339 timestamp") from exc
    if parsed.tzinfo != dt.timezone.utc:
        raise SeedError(f"{label}: timestamp is not UTC")
    return parsed


def _format_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_metadata(run_id: str, now: dt.datetime) -> tuple[str, str]:
    return _validate_run_id(run_id), _format_utc(now)


def _write_latest_and_run(root: Path, directory: str, run_id: str, value: Any) -> None:
    run_path = root / directory / "runs" / f"{run_id}.json"
    latest_path = root / directory / "LATEST.json"
    write_json(run_path, value)
    write_json(latest_path, value)


def run_acceptance(
    root: Path,
    run_id: str,
    fetch: Callable[[str], FetchedJson],
    *,
    now: dt.datetime | None = None,
    seed_repository: str = DEFAULT_SEED_REPOSITORY,
) -> dict[str, Any]:
    now = now or _utc_now()
    run_id, utc = _run_metadata(run_id, now)
    nodes, policies = load_nodes(root, seed_repository)
    prepared: list[tuple[NodeRecord, PolicyRecord, str, str | None, str | None, str | None]] = []
    errors: list[dict[str, str]] = []
    for node in nodes:
        policy = policies[node.guid]
        if policy.status == "ACTIVE":
            try:
                fetched = fetch(node.request_url)
                receipt_url = validate_registration_request(fetched.value, node)
                receipt_sha256 = None
                if receipt_url is not None:
                    receipt = fetch(receipt_url)
                    workflow_executor.validate_node_receipt(
                        receipt.value,
                        node.source_repository,
                        node.node_branch,
                    )
                    receipt_sha256 = receipt.sha256
                prepared.append(
                    (node, policy, "ACCEPTED", fetched.sha256, receipt_url, receipt_sha256)
                )
            except SeedError as exc:
                errors.append({"guid": node.guid, "error": str(exc)})
            except workflow_executor.ExecutorBlock as exc:
                errors.append({"guid": node.guid, "error": str(exc)})
        else:
            prepared.append((node, policy, policy.status, None, None, None))

    summary = {
        "schema": "qikvrt_seed_acceptance_run_v2",
        "qikvrt_event": "AUTONOMOUS_SEED_ACCEPTANCE_EVIDENCE",
        "generated_utc": utc,
        "run_id": run_id,
        "status": "BLOCK" if errors else "PASS",
        "seed_repository": seed_repository,
        "node_count": len(nodes),
        "accepted_count": sum(status == "ACCEPTED" for _, _, status, _, _, _ in prepared),
        "suspended_count": sum(status == "SUSPENDED" for _, _, status, _, _, _ in prepared),
        "revoked_count": sum(status == "REVOKED" for _, _, status, _, _, _ in prepared),
        "fail_count": len(errors),
        "errors": errors,
        "results": [
            {
                "guid": node.guid,
                "repository": node.source_repository,
                "policy_status": policy.status,
                "result_status": status,
                "request_sha256": digest,
                "workflow_executor_receipt_url": receipt_url,
                "workflow_executor_receipt_sha256": receipt_digest,
            }
            for node, policy, status, digest, receipt_url, receipt_digest in prepared
        ],
    }
    if errors:
        _write_latest_and_run(root, "evidence/seed_acceptance", run_id, summary)
        return summary

    ledger_path = root / "ledger/NODE_REGISTRATION_LEDGER.jsonl"
    existing = b""
    if ledger_path.exists():
        existing = _read_bytes_limited(ledger_path, max_bytes=16 * MAX_INPUT_BYTES)
        for line_number, line in enumerate(existing.splitlines(), 1):
            parse_json_bytes(line, f"{ledger_path}:{line_number}")

    for node, policy, status, request_digest, receipt_url, receipt_digest in prepared:
        entry = {
            "schema": "qikvrt_seed_registry_entry_v2",
            "qikvrt_event": "AUTONOMOUS_SEED_ACCEPTANCE",
            "guid": node.guid,
            "repository": node.source_repository,
            "seed_repository": node.seed_repository,
            "node_branch": node.node_branch,
            "node_state_ref": node.node_state_ref,
            "heartbeat_ttl_minutes": node.heartbeat_ttl_minutes,
            "node_request_url": node.request_url,
            "node_request_sha256": request_digest,
            "status": status,
            "policy_status": policy.status,
            "policy_reason": policy.reason,
            "acceptance_mode": "FAIL_CLOSED_SEED_REGISTRY_V2",
            "accepted_utc": utc,
            "last_acceptance_run_id": run_id,
            "source_registry_path": node.source_path,
            "source_registry_line": node.source_line,
            "lifecycle": {
                "heartbeat_required": True,
                "reaccept_supported": True,
                "renewal_supported": True,
                "revoke_supported": True,
                "suspend_supported": True,
            },
            "boundaries": {
                "authorized_manifest_graph_only": True,
                "no_global_scanning": True,
                "no_remote_mutation_without_authorization": True,
                "no_self_propagation": True,
                "seed_writes_only_to_seed_repository": True,
            },
        }
        if receipt_url is not None and receipt_digest is not None:
            entry["workflow_executor_continuity"] = {
                "receipt_url": receipt_url,
                "receipt_sha256": receipt_digest,
                "validation": "STRUCTURAL_ACCEPTANCE_ONLY",
            }
        write_json(root / "registry/nodes" / f"{node.guid}.json", entry)
        evidence = {
            "schema": "qikvrt_seed_acceptance_node_evidence_v2",
            "qikvrt_event": "AUTONOMOUS_SEED_ACCEPTANCE_EVIDENCE",
            "created_utc": utc,
            "guid": node.guid,
            "repository": node.source_repository,
            "seed_repository": node.seed_repository,
            "node_request_url": node.request_url,
            "node_request_sha256": request_digest,
            "policy_status": policy.status,
            "result_status": status,
            "run_id": run_id,
            "status": "PASS",
        }
        if receipt_url is not None and receipt_digest is not None:
            evidence["workflow_executor_continuity"] = {
                "receipt_url": receipt_url,
                "receipt_sha256": receipt_digest,
                "validation": "STRUCTURAL_ACCEPTANCE_ONLY",
            }
        write_json(root / "evidence/seed_acceptance" / f"{node.guid}.json", evidence)

    additions = b"".join(
        json.dumps(
            {
                "event": "AUTONOMOUS_SEED_ACCEPTANCE_V2",
                "guid": node.guid,
                "policy_status": policy.status,
                "repository": node.source_repository,
                "request_sha256": digest,
                "workflow_executor_receipt_url": receipt_url,
                "workflow_executor_receipt_sha256": receipt_digest,
                "result_status": status,
                "run_id": run_id,
                "seed_repository": node.seed_repository,
                "utc": utc,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
        for node, policy, status, digest, receipt_url, receipt_digest in prepared
    )
    _atomic_write(ledger_path, existing + additions)
    _write_latest_and_run(root, "evidence/seed_acceptance", run_id, summary)
    return summary


def _raw_node_url(node: NodeRecord, filename: str) -> str:
    branch = urllib.parse.quote(node.node_state_ref, safe="/-._~")
    return (
        f"https://raw.githubusercontent.com/{node.source_repository}/{branch}"
        f"/qikvrt/runtime/onboarding/{filename}"
    )


def _validate_health(document: Mapping[str, Any], node: NodeRecord, now: dt.datetime) -> tuple[str, str, str]:
    label = f"health record for {node.guid}"
    _require_exact(document, "qikvrt_event", "NODE_HEALTH_HEARTBEAT", label)
    _require_exact(document, "guid", node.guid, label)
    _require_exact(document, "repository", node.source_repository, label)
    _require_exact(document, "seed_repository", node.seed_repository, label)
    _require_exact(document, "node_branch", node.node_branch, label)
    _require_exact(document, "node_state_ref", node.node_state_ref, label)
    _require_exact(document, "status", "ACTIVE", label)
    boundaries = document.get("boundaries")
    if not isinstance(boundaries, dict):
        raise SeedError(f"{label}: boundaries must be an object")
    _validate_boundaries(boundaries, label)
    heartbeat = _parse_utc(document.get("heartbeat_utc"), f"{label}.heartbeat_utc")
    if heartbeat > now + dt.timedelta(minutes=5):
        raise SeedError(f"{label}: heartbeat is too far in the future")
    ttl_expiry = heartbeat + dt.timedelta(minutes=node.heartbeat_ttl_minutes)
    claimed_expiry_value = document.get("expires_utc")
    if claimed_expiry_value is None:
        effective_expiry = ttl_expiry
    else:
        claimed_expiry = _parse_utc(claimed_expiry_value, f"{label}.expires_utc")
        if claimed_expiry < heartbeat:
            raise SeedError(f"{label}: expiry precedes heartbeat")
        effective_expiry = min(claimed_expiry, ttl_expiry)
    freshness = "FRESH" if now <= effective_expiry else "STALE"
    return freshness, _format_utc(heartbeat), _format_utc(effective_expiry)


def _validate_ack(document: Mapping[str, Any], node: NodeRecord) -> None:
    label = f"seed acknowledgement for {node.guid}"
    _require_exact(document, "qikvrt_event", "NODE_ACK_OF_SEED_ACCEPTANCE", label)
    _require_exact(document, "guid", node.guid, label)
    _require_exact(document, "repository", node.source_repository, label)
    _require_exact(document, "seed_repository", node.seed_repository, label)
    _require_exact(document, "node_branch", node.node_branch, label)
    _require_exact(document, "node_state_ref", node.node_state_ref, label)
    _require_exact(document, "status", "ACCEPTED_BY_SEED", label)


def _validate_renewal(document: Mapping[str, Any], node: NodeRecord) -> None:
    label = f"registration renewal for {node.guid}"
    event = document.get("qikvrt_event", document.get("event"))
    if event not in {"NODE_REGISTRATION_RENEWAL", "QIKVRT_NODE_REGISTRATION_RENEWAL"}:
        raise SeedError(f"{label}: unsupported renewal event")
    guid = document.get("guid", document.get("repository_guid"))
    if guid != node.guid:
        raise SeedError(f"{label}: GUID does not match")
    repository = document.get("repository", document.get("source_repository"))
    if repository != node.source_repository:
        raise SeedError(f"{label}: repository does not match")
    _require_exact(document, "seed_repository", node.seed_repository, label)
    _require_exact(document, "node_branch", node.node_branch, label)
    _require_exact(document, "node_state_ref", node.node_state_ref, label)


def _validated_registry_entry(root: Path, node: NodeRecord, policy: PolicyRecord) -> tuple[str, str | None]:
    path = root / "registry/nodes" / f"{node.guid}.json"
    if not path.exists():
        return "UNKNOWN", "accepted registry entry is missing"
    try:
        entry = read_json(path)
        _require_exact(entry, "guid", node.guid, str(path))
        _require_exact(entry, "repository", node.source_repository, str(path))
        _require_exact(entry, "seed_repository", node.seed_repository, str(path))
        _require_exact(entry, "node_branch", node.node_branch, str(path))
        _require_exact(entry, "node_state_ref", node.node_state_ref, str(path))
        _require_exact(entry, "policy_status", policy.status, str(path))
        status = entry.get("status")
        expected = "ACCEPTED" if policy.status == "ACTIVE" else policy.status
        if status != expected:
            raise SeedError(f"{path}: status must be {expected!r}")
        return str(status), None
    except SeedError as exc:
        return "UNKNOWN", str(exc)


def run_maintenance(
    root: Path,
    run_id: str,
    fetch: Callable[[str], FetchedJson],
    *,
    now: dt.datetime | None = None,
    seed_repository: str = DEFAULT_SEED_REPOSITORY,
) -> dict[str, Any]:
    now = now or _utc_now()
    run_id, utc = _run_metadata(run_id, now)
    nodes, policies = load_nodes(root, seed_repository)
    index_nodes: list[dict[str, Any]] = []
    status_nodes: list[dict[str, Any]] = []
    error_count = 0
    for node in nodes:
        policy = policies[node.guid]
        registry_status, registry_error = _validated_registry_entry(root, node, policy)
        errors: list[dict[str, str]] = []
        if registry_error:
            errors.append({"source": "registry", "error": registry_error})
        health_visible = False
        ack_visible = False
        renewal_visible = False
        heartbeat_status = "MISSING"
        heartbeat_utc = ""
        expires_utc = ""
        evidence: dict[str, str | None] = {
            "health_sha256": None,
            "ack_sha256": None,
            "renewal_sha256": None,
        }
        health_url = _raw_node_url(node, "NODE_HEALTH.json")
        ack_url = _raw_node_url(node, "SEED_ACCEPTANCE_STATUS.json")
        renewal_url = _raw_node_url(node, "NODE_REGISTRATION_RENEWAL.json")
        if policy.status == "ACTIVE" and registry_status == "ACCEPTED":
            try:
                health = fetch(health_url)
                heartbeat_status, heartbeat_utc, expires_utc = _validate_health(health.value, node, now)
                health_visible = True
                evidence["health_sha256"] = health.sha256
            except SeedError as exc:
                errors.append({"source": "health", "error": str(exc)})
            try:
                acknowledgement = fetch(ack_url)
                _validate_ack(acknowledgement.value, node)
                ack_visible = True
                evidence["ack_sha256"] = acknowledgement.sha256
            except SeedError as exc:
                errors.append({"source": "ack", "error": str(exc)})
            try:
                renewal = fetch(renewal_url)
                _validate_renewal(renewal.value, node)
                renewal_visible = True
                evidence["renewal_sha256"] = renewal.sha256
            except SeedError as exc:
                errors.append({"source": "renewal", "error": str(exc)})

        if policy.status == "SUSPENDED":
            effective_status = "SUSPENDED"
        elif policy.status == "REVOKED":
            effective_status = "REVOKED"
        elif registry_status == "ACCEPTED":
            effective_status = (
                "ACTIVE"
                if health_visible and ack_visible and heartbeat_status == "FRESH"
                else "STALE"
            )
        else:
            effective_status = "UNKNOWN"
        error_count += len(errors)
        common = {
            "guid": node.guid,
            "repository": node.source_repository,
            "node_branch": node.node_branch,
            "node_state_ref": node.node_state_ref,
            "registry_status": registry_status,
            "policy_status": policy.status,
            "effective_status": effective_status,
            "heartbeat_ttl_minutes": node.heartbeat_ttl_minutes,
            "errors": errors,
        }
        index_nodes.append(
            {
                **common,
                "registry_path": f"registry/nodes/{node.guid}.json",
                "node_request_url": node.request_url,
                "node_health_url": health_url,
                "node_ack_url": ack_url,
                "node_renewal_url": renewal_url,
                "remote_evidence": evidence,
            }
        )
        status_nodes.append(
            {
                **common,
                "node_health_visible": health_visible,
                "node_ack_visible": ack_visible,
                "node_renewal_visible": renewal_visible,
                "heartbeat_status": heartbeat_status,
                "heartbeat_utc": heartbeat_utc,
                "effective_expires_utc": expires_utc,
                "remote_evidence": evidence,
            }
        )

    counts = {state.lower() + "_count": 0 for state in EFFECTIVE_STATES}
    for node_status in status_nodes:
        counts[str(node_status["effective_status"]).lower() + "_count"] += 1
    operation_status = "PASS" if error_count == 0 else "CONTINUE"
    base = {
        "generated_utc": utc,
        "run_id": run_id,
        "seed_repository": seed_repository,
        "fixed_node_count": False,
        "node_count": len(status_nodes),
        **counts,
        "error_count": error_count,
        "status": operation_status,
    }
    index = {
        "schema": "qikvrt_nodemesh_index_v2",
        "qikvrt_event": "NODEMESH_INDEX_AGGREGATE_OPEN_REGISTRY",
        **base,
        "nodes": index_nodes,
        "discovery_scope": [
            "registry/KNOWN_NODE_REQUESTS.tsv",
            "registry/node_request_queue/*.tsv",
        ],
        "boundaries": {
            "no_global_scanning": True,
            "no_remote_mutation_without_authorization": True,
            "no_self_propagation": True,
            "seed_index_only_reads_authorized_known_nodes_and_queue": True,
            "seed_writes_only_to_seed_repository": True,
        },
    }
    status = {
        "schema": "qikvrt_nodemesh_status_v2",
        "qikvrt_event": "NODEMESH_STATUS_AGGREGATE_OPEN_REGISTRY",
        **base,
        "nodes": status_nodes,
    }
    write_json(root / "registry/NODEMESH_INDEX.json", index)
    write_json(root / "registry/NODEMESH_STATUS.json", status)
    evidence = {
        "schema": "qikvrt_seed_mesh_maintenance_evidence_v2",
        "qikvrt_event": "SEED_MESH_MAINTENANCE_EVIDENCE",
        **base,
        "index_path": "registry/NODEMESH_INDEX.json",
        "status_path": "registry/NODEMESH_STATUS.json",
    }
    _write_latest_and_run(root, "evidence/seed_mesh_maintenance", run_id, evidence)
    return status


def _int_field(value: Mapping[str, Any], key: str, label: str) -> int:
    result = value.get(key)
    if type(result) is not int or result < 0:
        raise SeedError(f"{label}: {key} must be a non-negative integer")
    return result


def validate_aggregate_pair(root: Path, seed_repository: str = DEFAULT_SEED_REPOSITORY) -> tuple[dict[str, Any], dict[str, Any]]:
    index = read_json(root / "registry/NODEMESH_INDEX.json")
    status = read_json(root / "registry/NODEMESH_STATUS.json")
    for document, schema, label in (
        (index, "qikvrt_nodemesh_index_v2", "mesh index"),
        (status, "qikvrt_nodemesh_status_v2", "mesh status"),
    ):
        _require_exact(document, "schema", schema, label)
        _require_exact(document, "seed_repository", seed_repository, label)
        _require_exact(document, "fixed_node_count", False, label)
        if document.get("status") not in {"PASS", "CONTINUE"}:
            raise SeedError(f"{label}: invalid operation status")
        if not isinstance(document.get("nodes"), list):
            raise SeedError(f"{label}: nodes must be an array")
        if _int_field(document, "node_count", label) != len(document["nodes"]):
            raise SeedError(f"{label}: node_count does not match nodes array")
        _int_field(document, "error_count", label)
        for state in EFFECTIVE_STATES:
            _int_field(document, state.lower() + "_count", label)
    if index["run_id"] != status["run_id"] or index["generated_utc"] != status["generated_utc"]:
        raise SeedError("mesh index and status were not produced by the same run")
    index_by_guid: dict[str, Mapping[str, Any]] = {}
    status_by_guid: dict[str, Mapping[str, Any]] = {}
    for collection, target, label in (
        (index["nodes"], index_by_guid, "mesh index"),
        (status["nodes"], status_by_guid, "mesh status"),
    ):
        for entry in collection:
            if not isinstance(entry, dict):
                raise SeedError(f"{label}: node entry must be an object")
            guid = entry.get("guid")
            if not isinstance(guid, str):
                raise SeedError(f"{label}: node GUID must be a string")
            _validate_guid(guid)
            if guid in target:
                raise SeedError(f"{label}: duplicate node GUID {guid}")
            if entry.get("effective_status") not in EFFECTIVE_STATES:
                raise SeedError(f"{label}: invalid effective status for {guid}")
            if entry.get("policy_status") not in POLICY_STATES:
                raise SeedError(f"{label}: invalid policy status for {guid}")
            if not isinstance(entry.get("errors"), list):
                raise SeedError(f"{label}: errors must be an array for {guid}")
            target[guid] = entry
    if set(index_by_guid) != set(status_by_guid):
        raise SeedError("mesh index and status contain different node sets")
    for guid in sorted(status_by_guid):
        left = index_by_guid[guid]
        right = status_by_guid[guid]
        for key in (
            "repository",
            "node_branch",
            "node_state_ref",
            "registry_status",
            "policy_status",
            "effective_status",
        ):
            if left.get(key) != right.get(key):
                raise SeedError(f"mesh index/status mismatch for {guid}: {key}")
    actual_counts = {state.lower() + "_count": 0 for state in EFFECTIVE_STATES}
    actual_errors = 0
    for entry in status_by_guid.values():
        actual_counts[str(entry["effective_status"]).lower() + "_count"] += 1
        actual_errors += len(entry["errors"])
    for document, label in ((index, "mesh index"), (status, "mesh status")):
        for key, expected in actual_counts.items():
            if document[key] != expected:
                raise SeedError(f"{label}: {key} does not match node data")
        if document["error_count"] != actual_errors:
            raise SeedError(f"{label}: error_count does not match node data")
        expected_status = "PASS" if actual_errors == 0 else "CONTINUE"
        if document["status"] != expected_status:
            raise SeedError(f"{label}: status is inconsistent with errors")
    return index, status


def run_revalidation(
    root: Path,
    run_id: str,
    *,
    now: dt.datetime | None = None,
    seed_repository: str = DEFAULT_SEED_REPOSITORY,
) -> dict[str, Any]:
    now = now or _utc_now()
    run_id, utc = _run_metadata(run_id, now)
    index, source_status = validate_aggregate_pair(root, seed_repository)
    nodes = source_status["nodes"]
    accepted_count = sum(node.get("registry_status") == "ACCEPTED" for node in nodes)
    stale = source_status["stale_count"]
    unknown = source_status["unknown_count"]
    if not nodes:
        status = "BLOCK"
    elif source_status["status"] != "PASS" or stale or unknown:
        status = "CONTINUE"
    else:
        status = "PASS"
    result = {
        "schema": "qikvrt_nodemesh_revalidation_v2",
        "qikvrt_event": "NODEMESH_OPEN_MULTI_NODE_REVALIDATION",
        "generated_utc": utc,
        "run_id": run_id,
        "status": status,
        "seed_repository": seed_repository,
        "source_status_run_id": source_status["run_id"],
        "source_index_run_id": index["run_id"],
        "fixed_node_count": False,
        "node_count": source_status["node_count"],
        "accepted_count": accepted_count,
        "active_count": source_status["active_count"],
        "stale_count": stale,
        "suspended_count": source_status["suspended_count"],
        "revoked_count": source_status["revoked_count"],
        "unknown_count": unknown,
        "error_count": source_status["error_count"],
        "lifecycle_states": sorted(EFFECTIVE_STATES),
        "source_status_path": "registry/NODEMESH_STATUS.json",
        "source_index_path": "registry/NODEMESH_INDEX.json",
        "node_addition_method": "append a valid, explicitly policy-authorized TSV row",
        "boundaries": {
            "known_or_queued_nodes_only": True,
            "no_global_scanning": True,
            "no_remote_mutation_without_authorization": True,
            "no_self_propagation": True,
            "node_revalidation_does_not_write_to_node_repositories": True,
            "seed_writes_only_to_seed_repository": True,
        },
    }
    write_json(root / "registry/NODEMESH_REVALIDATION.json", result)
    _write_latest_and_run(root, "evidence/seed_node_revalidation", run_id, result)
    return result


def validate_revalidation(root: Path, source_status: Mapping[str, Any], seed_repository: str) -> dict[str, Any]:
    result = read_json(root / "registry/NODEMESH_REVALIDATION.json")
    _require_exact(result, "schema", "qikvrt_nodemesh_revalidation_v2", "mesh revalidation")
    _require_exact(result, "seed_repository", seed_repository, "mesh revalidation")
    _require_exact(result, "source_status_run_id", source_status["run_id"], "mesh revalidation")
    for key in (
        "node_count",
        "active_count",
        "stale_count",
        "suspended_count",
        "revoked_count",
        "unknown_count",
        "error_count",
    ):
        if result.get(key) != source_status.get(key):
            raise SeedError(f"mesh revalidation: {key} disagrees with source status")
    if result.get("status") != "PASS":
        raise SeedError("mesh revalidation is not PASS")
    return result


def run_dashboard(
    root: Path,
    run_id: str,
    *,
    now: dt.datetime | None = None,
    seed_repository: str = DEFAULT_SEED_REPOSITORY,
) -> dict[str, Any]:
    now = now or _utc_now()
    run_id, utc = _run_metadata(run_id, now)
    _, status = validate_aggregate_pair(root, seed_repository)
    revalidation = validate_revalidation(root, status, seed_repository)
    safe = {key: html.escape(str(value), quote=True) for key, value in {
        "utc": utc,
        "run_id": run_id,
        "seed": seed_repository,
        "nodes": status["node_count"],
        "active": status["active_count"],
        "stale": status["stale_count"],
    }.items()}
    dashboard_html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>QIK-VRT Mesh Dashboard</title>
<style>body{{font-family:Arial,sans-serif;margin:2rem;line-height:1.45}}code{{background:#eee;padding:.1rem .25rem}}.card{{border:1px solid #ccc;padding:1rem;margin:1rem 0;border-radius:.5rem}}</style></head>
<body>
<h1>QIK-VRT Mesh Dashboard</h1>
<div class="card"><strong>Generated UTC:</strong> {safe['utc']}<br><strong>Run ID:</strong> {safe['run_id']}<br><strong>Seed:</strong> {safe['seed']}</div>
<div class="card"><strong>Nodes:</strong> {safe['nodes']}<br><strong>Active:</strong> {safe['active']}<br><strong>Stale:</strong> {safe['stale']}</div>
<h2>Evidence</h2>
<ul><li><code>registry/NODEMESH_INDEX.json</code></li><li><code>registry/NODEMESH_STATUS.json</code></li><li><code>registry/NODEMESH_REVALIDATION.json</code></li><li><code>audit/QIKVRT_MESH_AUDIT_REPORT.md</code></li></ul>
<p>Boundary: authorized known nodes only, seed writes only to seed repository, no global scanning, no self propagation, no remote mutation without authorization.</p>
</body></html>
"""
    dashboard_md = f"""# QIK-VRT Mesh Dashboard

generated_utc: {utc}<br>
run_id: {run_id}<br>
seed_repository: {seed_repository}<br>
node_count: {status['node_count']}<br>
active_count: {status['active_count']}<br>
stale_count: {status['stale_count']}<br>
source_status_run_id: {status['run_id']}<br>
source_revalidation_run_id: {revalidation['run_id']}

HTML dashboard: docs/qikvrt_mesh_dashboard.html
"""
    write_text(root / "docs/qikvrt_mesh_dashboard.html", dashboard_html)
    write_text(root / "docs/QIKVRT_MESH_DASHBOARD.md", dashboard_md)
    evidence = {
        "schema": "qikvrt_seed_dashboard_publish_v2",
        "qikvrt_event": "SEED_DASHBOARD_PUBLISH",
        "generated_utc": utc,
        "run_id": run_id,
        "status": "PASS",
        "source_status_run_id": status["run_id"],
        "source_revalidation_run_id": revalidation["run_id"],
        "dashboard_html": "docs/qikvrt_mesh_dashboard.html",
        "dashboard_md": "docs/QIKVRT_MESH_DASHBOARD.md",
    }
    _write_latest_and_run(root, "evidence/seed_dashboard", run_id, evidence)
    return evidence


def run_audit_export(
    root: Path,
    run_id: str,
    *,
    now: dt.datetime | None = None,
    seed_repository: str = DEFAULT_SEED_REPOSITORY,
) -> dict[str, Any]:
    now = now or _utc_now()
    run_id, utc = _run_metadata(run_id, now)
    _, status = validate_aggregate_pair(root, seed_repository)
    revalidation = validate_revalidation(root, status, seed_repository)
    report_path = "audit/QIKVRT_MESH_AUDIT_REPORT.md"
    report = f"""# QIK-VRT Mesh Audit Report

- generated_utc: {utc}
- run_id: {run_id}
- seed_repository: {seed_repository}
- source_status_run_id: {status['run_id']}
- source_revalidation_run_id: {revalidation['run_id']}
- node_count: {status['node_count']}
- active_count: {status['active_count']}
- stale_count: {status['stale_count']}
- error_count: {status['error_count']}

## Evidence paths

- registry/NODEMESH_INDEX.json
- registry/NODEMESH_STATUS.json
- registry/NODEMESH_REVALIDATION.json
- evidence/seed_mesh_maintenance/LATEST.json
- evidence/seed_node_revalidation/LATEST.json

## Boundary statement

The Seed reads only explicitly policy-authorized Node entries. The Seed writes only to the local Seed working tree. Nodes write only to their own Node repository. This audit operation performs no global scanning, no self propagation, and no remote mutation.
"""
    write_text(root / report_path, report)
    write_text(root / "docs/QIKVRT_AUDIT_EXPORT.md", report)
    summary = {
        "schema": "qikvrt_seed_mesh_audit_export_v2",
        "qikvrt_event": "SEED_MESH_AUDIT_EXPORT",
        "generated_utc": utc,
        "run_id": run_id,
        "status": "PASS",
        "seed_repository": seed_repository,
        "source_status_run_id": status["run_id"],
        "source_revalidation_run_id": revalidation["run_id"],
        "node_count": status["node_count"],
        "active_count": status["active_count"],
        "stale_count": status["stale_count"],
        "error_count": status["error_count"],
        "report_path": report_path,
        "revalidation_path": "registry/NODEMESH_REVALIDATION.json",
        "doc_report_path": "docs/QIKVRT_AUDIT_EXPORT.md",
    }
    write_json(root / "audit/QIKVRT_MESH_AUDIT_SUMMARY.json", summary)
    _write_latest_and_run(root, "evidence/seed_mesh_audit", run_id, summary)
    return summary


def _result_exit_code(result: Mapping[str, Any]) -> int:
    return 0 if result.get("status") == "PASS" else 10


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("acceptance", "maintenance", "revalidate", "dashboard", "audit-export"),
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--run-id", default=os.environ.get("QIKVRT_RUN_ID", ""))
    parser.add_argument(
        "--seed-repository",
        default=os.environ.get("QIKVRT_SEED_REPOSITORY", DEFAULT_SEED_REPOSITORY),
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=float(os.environ.get("QIKVRT_SEED_HTTP_TIMEOUT_SECONDS", "15")),
    )
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    root = arguments.root.resolve()
    if not arguments.run_id:
        arguments.run_id = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    try:
        if arguments.operation == "acceptance":
            result = run_acceptance(
                root,
                arguments.run_id,
                HttpJsonFetcher(arguments.timeout_seconds),
                seed_repository=arguments.seed_repository,
            )
        elif arguments.operation == "maintenance":
            result = run_maintenance(
                root,
                arguments.run_id,
                HttpJsonFetcher(arguments.timeout_seconds),
                seed_repository=arguments.seed_repository,
            )
        elif arguments.operation == "revalidate":
            result = run_revalidation(
                root,
                arguments.run_id,
                seed_repository=arguments.seed_repository,
            )
        elif arguments.operation == "dashboard":
            result = run_dashboard(
                root,
                arguments.run_id,
                seed_repository=arguments.seed_repository,
            )
        else:
            result = run_audit_export(
                root,
                arguments.run_id,
                seed_repository=arguments.seed_repository,
            )
    except (SeedError, OSError) as exc:
        print(f"BLOCK QIKVRT_SEED_{arguments.operation.upper().replace('-', '_')} {exc}", file=sys.stderr)
        return 2
    print(
        f"QIKVRT_SEED_{arguments.operation.upper().replace('-', '_')} "
        f"{result.get('status')} run_id={arguments.run_id}"
    )
    return _result_exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
