#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Persist and validate explicit local effect authorization for the launcher."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_runtime_logger as qlog
from tools.qikvrt_subprocess import run_bounded

STATE_DIR = ROOT / ".qikvrt" / "runtime"
ACCEPTANCE_FILE = STATE_DIR / "launcher_acceptance_record.json"
LOG_FILE = qlog.LOG_FILE
DEFAULT_OPERATIONS = ("master-gate", "cicd-publish")
DEFAULT_TTL_SECONDS = 24 * 60 * 60
MAX_CONTEXT_FILE_BYTES = 256 * 1024 * 1024
ACCEPTANCE_SCHEMA = "qikvrt_bound_launcher_effect_authorization_v4"
CONTEXT_FILES = (
    "qikvrt.py",
    "tools/qikvrt_runtime_logger.py",
    "tools/qikvrt_subprocess.py",
    "tools/qikvrt_initial_acceptance_gate.py",
    "tools/qikvrt_integrity.py",
    "tools/qikvrt_master_acceptance_gate.py",
    "tools/qikvrt_cicd_publish.py",
    "tools/qikvrt_github_publish_runtime.py",
)
REQUIRED_FIELDS = {
    "effect_authorized",
    "operator_effect_authorization",
    "accepted_by",
    "accepted_utc",
    "authorization_scope",
    "repository_context",
    "launcher_sha256",
    "repository_content_tree_sha256",
    "command_surface_sha256",
    "repository_manifest_sha256",
    "accepted_operations",
    "expires_utc",
}
EFFECTFUL_EVENTS = {
    "command_start",
    "runtime_missing",
    "dependency_resolution_start",
    "target_process_result",
    "download_start",
    "repair_start",
    "release_start",
    "master_gate_start",
}
ALLOWED_BEFORE_ACCEPTANCE = {"run_start", "acceptance_required", "run_end"}


def json_safe_path(path: str | pathlib.Path) -> str:
    return qlog.json_safe_path(path)


def append_event(event: str, **fields: Any) -> dict[str, Any]:
    """Write through the shared logger so all launcher evidence is one stream."""
    return qlog.write_event(event, **fields)


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"effect-authorization context is not a regular file: {path}")
        if before.st_size > MAX_CONTEXT_FILE_BYTES:
            raise ValueError(f"effect-authorization context exceeds its size bound: {path}")
        remaining = MAX_CONTEXT_FILE_BYTES + 1
        total = 0
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            total += len(chunk)
            remaining -= len(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
        if total > MAX_CONTEXT_FILE_BYTES or total != before.st_size:
            raise ValueError(f"effect-authorization context changed size while hashing: {path}")
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            raise ValueError(f"effect-authorization context changed while hashing: {path}")
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _strict_json_loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_unique_json_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON value: {value}")
        ),
    )


def _read_regular_text(path: pathlib.Path, limit: int = 1024 * 1024) -> str:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError(f"effect-authorization record is not a bounded regular file: {path}")
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(descriptor)
        if len(data) > limit or len(data) != before.st_size:
            raise ValueError(f"effect-authorization record exceeds its bounded size: {path}")
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            raise ValueError(f"effect-authorization record changed while reading: {path}")
        return data.decode("utf-8")
    finally:
        os.close(descriptor)


def _acceptance_file_is_tracked() -> bool:
    try:
        relative = ACCEPTANCE_FILE.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return True
    try:
        process = run_bounded(
            ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", relative],
            cwd=ROOT,
            timeout=3,
            max_output_bytes=64 * 1024,
        )
    except (OSError, RuntimeError, ValueError):
        return True
    if process.timed_out or process.output_limit_exceeded:
        return True
    # Exit 1 is the documented no-match result.  Every other outcome is either
    # tracked (0) or indeterminate and must fail closed.
    return process.returncode != 1


def _acceptance_path_is_inside_repository(path: pathlib.Path) -> bool:
    try:
        path.parent.resolve().relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return False
    return True


def _acceptance_path_has_symlink_component(path: pathlib.Path) -> bool:
    """Reject redirection through any existing component below the root."""
    root = ROOT.resolve()
    current = path
    while True:
        if current.is_symlink():
            return True
        if current == ROOT or current == root:
            return False
        parent = current.parent
        if parent == current:
            return True
        current = parent


def _context() -> dict[str, str]:
    context_paths = [ROOT / relative for relative in CONTEXT_FILES]
    context_paths.append(ROOT / "REPOSITORY_FILE_MANIFEST.json")
    if any(_acceptance_path_has_symlink_component(path) for path in context_paths):
        raise ValueError("effect-authorization context contains a symlink component")
    launcher_sha256 = _sha256(ROOT / "qikvrt.py")
    command_hashes = [f"{relative}:{_sha256(ROOT / relative)}" for relative in CONTEXT_FILES]
    command_surface_sha256 = hashlib.sha256("\n".join(command_hashes).encode("utf-8")).hexdigest()
    repository_manifest_path = ROOT / "REPOSITORY_FILE_MANIFEST.json"
    repository_manifest_sha256 = _sha256(repository_manifest_path)
    manifest = _strict_json_loads(_read_regular_text(repository_manifest_path, 64 * 1024 * 1024))
    if not isinstance(manifest, dict):
        raise ValueError("repository manifest must be a JSON object")
    repository_content_tree_sha256 = manifest.get("repository_content_tree_sha256")
    if not isinstance(repository_content_tree_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", repository_content_tree_sha256
    ):
        raise ValueError("repository manifest has no canonical content-tree digest")
    material = "\n".join(
        (
            str(ROOT.resolve()),
            repository_content_tree_sha256,
            launcher_sha256,
            command_surface_sha256,
            repository_manifest_sha256,
        )
    ).encode("utf-8")
    return {
        "repository_context": hashlib.sha256(material).hexdigest(),
        "launcher_sha256": launcher_sha256,
        "repository_content_tree_sha256": repository_content_tree_sha256,
        "command_surface_sha256": command_surface_sha256,
        "repository_manifest_sha256": repository_manifest_sha256,
    }


def _parse_utc(value: str) -> dt.datetime | None:
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=dt.timezone.utc)


def _valid_record(data: Any, operation: str | None = None) -> bool:
    if not isinstance(data, dict) or not REQUIRED_FIELDS.issubset(data):
        return False
    if data.get("schema") != ACCEPTANCE_SCHEMA:
        return False
    if data.get("authorization_kind") != "local_operator_declaration_not_identity_authentication":
        return False
    if data.get("effect_authorized") is not True or data.get("operator_effect_authorization") is not True:
        return False
    string_fields = REQUIRED_FIELDS - {
        "effect_authorized", "operator_effect_authorization", "accepted_operations"
    }
    for field in string_fields:
        if not isinstance(data.get(field), str) or not data[field].strip():
            return False
    operations = data.get("accepted_operations")
    if not isinstance(operations, list) or not operations or not all(
        isinstance(item, str) and item in DEFAULT_OPERATIONS for item in operations
    ):
        return False
    if operation is not None and operation not in operations:
        return False
    accepted = _parse_utc(data.get("accepted_utc"))
    expires = _parse_utc(data.get("expires_utc"))
    now = dt.datetime.now(dt.timezone.utc)
    if (
        accepted is None
        or expires is None
        or accepted > now + dt.timedelta(minutes=5)
        or expires <= now
        or expires <= accepted
        or expires - accepted > dt.timedelta(seconds=DEFAULT_TTL_SECONDS)
    ):
        return False
    try:
        context = _context()
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError):
        return False
    if any(data.get(key) != value for key, value in context.items()):
        return False
    return True


def load_acceptance(operation: str | None = None) -> dict[str, Any] | None:
    """Return a valid persisted effect authorization, otherwise ``None``."""
    if (
        not ACCEPTANCE_FILE.is_file()
        or ACCEPTANCE_FILE.is_symlink()
        or _acceptance_path_has_symlink_component(ACCEPTANCE_FILE)
        or _acceptance_file_is_tracked()
    ):
        return None
    try:
        data = _strict_json_loads(_read_regular_text(ACCEPTANCE_FILE))
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError):
        return None
    return data if _valid_record(data, operation) else None


def _atomic_write_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    if not _acceptance_path_is_inside_repository(path):
        raise ValueError("effect-authorization path escapes the repository")
    if _acceptance_path_has_symlink_component(path):
        raise ValueError("effect-authorization path contains a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    if _acceptance_path_has_symlink_component(path):
        raise ValueError("effect-authorization path contains a symlink")
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            os.fchmod(descriptor, 0o600)
        except Exception:
            os.close(descriptor)
            raise
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if _acceptance_path_has_symlink_component(path):
            raise ValueError("effect-authorization path contains a symlink")
        temporary.replace(path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def persist_acceptance(
    accepted_by: str | None = None,
    accepted_scope: str = "QIK-VRT launcher execution",
    accepted_operations: tuple[str, ...] = DEFAULT_OPERATIONS,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> dict[str, Any]:
    """Persist the local operator's explicit effect authorization atomically."""
    actor = (accepted_by or os.environ.get("QIKVRT_ACCEPTED_BY") or "local operator").strip()
    scope = accepted_scope.strip()
    if not actor or not scope:
        raise ValueError("accepted_by and authorization scope must be non-empty")
    if len(actor) > 256 or len(scope) > 1024:
        raise ValueError("accepted_by or authorization scope exceeds its size bound")
    operations = tuple(dict.fromkeys(accepted_operations))
    if not operations or any(item not in DEFAULT_OPERATIONS for item in operations):
        raise ValueError("accepted_operations contains an unknown launcher operation")
    if not 60 <= int(ttl_seconds) <= DEFAULT_TTL_SECONDS:
        raise ValueError("ttl_seconds must be between 60 and 86400")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    expires = now + dt.timedelta(seconds=int(ttl_seconds))
    data = {
        "schema": ACCEPTANCE_SCHEMA,
        "effect_authorized": True,
        "operator_effect_authorization": True,
        "accepted_by": actor,
        "accepted_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_utc": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authorization_scope": scope,
        "accepted_operations": list(operations),
        "authorization_kind": "local_operator_declaration_not_identity_authentication",
        "license_acceptance_required": False,
        "license_information_reference": "LICENSE_NOTICE.md",
        **_context(),
    }
    _atomic_write_json(ACCEPTANCE_FILE, data)
    append_event(
        "acceptance_persisted",
        status="ACCEPTED",
        persisted=True,
        acceptance_record=json_safe_path(ACCEPTANCE_FILE),
        accepted_by=actor,
        authorization_scope=scope,
        accepted_operations=list(operations),
        expires_utc=data["expires_utc"],
    )
    return data


def require_acceptance(operation: str | None = None) -> bool:
    """Return true only for a complete, persisted effect authorization."""
    if operation is not None and operation not in DEFAULT_OPERATIONS:
        raise ValueError(f"unknown operation: {operation}")
    data = load_acceptance(operation)
    if data is not None:
        append_event(
            "acceptance_verified",
            status="ACCEPTED",
            persisted=True,
            acceptance_record=json_safe_path(ACCEPTANCE_FILE),
            accepted_by=data["accepted_by"],
            authorization_scope=data["authorization_scope"],
            accepted_operation=operation or "ANY_ACCEPTED_OPERATION",
            expires_utc=data["expires_utc"],
        )
        return True
    append_event(
        "acceptance_required",
        status="CONTINUE_ACCEPTANCE_REQUIRED",
        persisted=False,
        error_class="INITIAL_ACCEPTANCE_NOT_PERSISTED_BEFORE_EFFECT",
        continue_path="PERSIST_LAUNCHER_ACCEPTANCE_BEFORE_ANY_EFFECT",
        repair_hint="Run 'python qikvrt.py --accept' before an effectful command.",
        acceptance_record=json_safe_path(ACCEPTANCE_FILE),
        requested_operation=operation or "ANY_ACCEPTED_OPERATION",
    )
    return False


def validate_log_order(path: pathlib.Path | None = None) -> bool:
    """Verify that no effectful event precedes persisted acceptance."""
    log_path = path or qlog.LOG_FILE
    if log_path.is_symlink():
        raise ValueError("runtime log must not be a symlink")
    events = []
    for line in _read_regular_text(log_path, qlog.MAX_POINTER_LOG_BYTES).splitlines():
        if not line.strip():
            continue
        event = _strict_json_loads(line)
        if not isinstance(event, dict):
            raise ValueError("runtime log event must be a JSON object")
        events.append(event)
    accepted_index: int | None = None
    for index, event in enumerate(events):
        name = event.get("event")
        if name in {"acceptance_verified", "acceptance_persisted"} and event.get("persisted") is True:
            accepted_index = index
        if accepted_index is None and name not in ALLOWED_BEFORE_ACCEPTANCE:
            raise AssertionError(f"event before acceptance is not allowed: {name}")
        if name in EFFECTFUL_EVENTS and (accepted_index is None or accepted_index >= index):
            raise AssertionError("effectful event occurred before persisted acceptance")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QIK-VRT initial effect-authorization gate")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--accept", action="store_true", help="persist explicit local effect authorization")
    action.add_argument("--check", action="store_true", help="verify persisted effect authorization")
    action.add_argument("--validate-log", action="store_true", help="validate event ordering")
    parser.add_argument("--accepted-by", default=None)
    parser.add_argument("--scope", default="QIK-VRT launcher execution")
    parser.add_argument("--operation", action="append", choices=DEFAULT_OPERATIONS)
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)
    if args.validate_log:
        try:
            validate_log_order()
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError, AssertionError) as exc:
            print(f"BLOCK initial acceptance order: {exc}", file=sys.stderr)
            return 1
        print("PASS initial acceptance order")
        return 0

    log_managed_by_parent = os.environ.get("QIKVRT_LAUNCHED_BY_QIKVRT") == "1"
    if not log_managed_by_parent:
        qlog.reset_log("tools/qikvrt_initial_acceptance_gate.py")
    try:
        if args.accept:
            operations = tuple(args.operation) if args.operation else DEFAULT_OPERATIONS
            persist_acceptance(args.accepted_by, args.scope, operations, args.ttl_seconds)
            print("PASS launcher effect authorization persisted")
            code = 0
        else:
            if args.operation and len(args.operation) != 1:
                raise ValueError("--check accepts at most one --operation scope")
            operation = args.operation[0] if args.operation and len(args.operation) == 1 else None
            if require_acceptance(operation):
                print("PASS launcher effect authorization verified")
                code = 0
            else:
                print("CONTINUE launcher effect authorization required")
                code = 20
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"BLOCK launcher effect-authorization gate: {exc}", file=sys.stderr)
        qlog.log_check_result("launcher-acceptance-gate", "BLOCK", 1, error=str(exc))
        code = 1
    if not log_managed_by_parent:
        return qlog.finish(
            code,
            status="PASS" if code == 0 else ("CONTINUE" if code == 20 else "BLOCK"),
            error_class="NONE" if code == 0 else "LAUNCHER_ACCEPTANCE_NOT_COMPLETED",
            continue_path="NONE" if code == 0 else "REPAIR_OR_PERSIST_ACCEPTANCE_AND_RERUN",
            repair_hint="NONE" if code == 0 else "Inspect the acceptance record and repository context.",
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
