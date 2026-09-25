#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed QIK-VRT API handler with an EFFECT_ACK haltpoint.

The handler deliberately separates technical receipt from permission to cause
an ordinary downstream effect.  Every operation is evaluated by the five-state
EFFECT_ACK engine.  Ordinary output/effect files are written only after
``EFFECT_ACK_DONE`` and, for non-dry-run mutations, explicit scoped acceptance
and an idempotency key.  Protective audit, protocol and recovery evidence is
written for every state, including dry-run, NACK, CONTINUE, ISOLATE and BLOCK.
"""
from __future__ import annotations

import base64
import contextlib
import fcntl
import hmac
import hashlib
import json
import os
import re
import tempfile
import threading
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from qikvrt_effect_ack import (
    ConnectionDecision,
    EffectAckEngine,
    EffectAckRequest,
    EffectAckResult,
    EffectState,
    ResponsibilityProtocol,
    RiskLevel,
    canonical_json,
    sha256_identifier,
    verify_protocol,
)

SAFE_ID = re.compile(r"^[A-Za-z0-9_.=-]{1,128}$")
WORK_ORDER_PATH = re.compile(r"^[A-Za-z0-9._/-]{1,512}$")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
BASE64URL_SECRET = re.compile(r"^[A-Za-z0-9_-]+$")
UTC_SECONDS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
AUDIT_SCHEMA = "qikvrt_api_audit_chain_v1"
RECEIPT_SCHEMA = "qikvrt_api_idempotency_receipt_v1"
TRANSACTION_SCHEMA = "qikvrt_api_recovery_transaction_v1"
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_BASE64_CHARS = 4 * ((MAX_PAYLOAD_BYTES + 2) // 3)
MIN_SECRET_BYTES = 32
MAX_SECRET_BYTES = 128
_HANDLER_LOCK = threading.RLock()


class IntegrityIsolationError(RuntimeError):
    """An unsafe path, replay conflict, or broken evidence chain."""


class PolicyBlockError(RuntimeError):
    """A protective policy halt with a responsible continuation path."""


@dataclass(frozen=True, slots=True)
class HandlerConfig:
    root: Path
    operation: str
    artifact_id: str
    payload_b64: str
    expected_sha256: str
    dry_run: bool
    repository: str = "local/qik-vrt"
    run_id: str = "local-run"
    request_id: str = ""
    effect_accepted: bool = False
    responsibility_owner: str = ""
    origin_authenticated: bool = False
    remote_evidence_b64: str = ""
    trusted_attestation_secret: str = ""
    trusted_attestation_signer: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return canonical_json(value).encode("utf-8")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


def _strict_json_loads(data: bytes | str) -> Any:
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    return json.loads(
        text,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
    )


def safe_id(raw: str, *, field: str = "artifact_id") -> str:
    if not raw or not SAFE_ID.fullmatch(raw):
        raise ValueError(f"unsafe or missing {field}")
    return raw


def require_sha(raw: str) -> str:
    if not raw or not SHA256_HEX.fullmatch(raw):
        raise ValueError("expected_sha256 must be 64 hex chars")
    return raw.lower()


def decode_secret_material(raw: str, *, field: str) -> bytes:
    """Decode one canonical, unpadded base64url secret of 32--128 bytes.

    The explicit ``b64url:`` prefix and the round-trip check avoid ambiguous
    text-to-key conversions.  Callers must never use the encoded text itself
    as HMAC key material.
    """

    if not isinstance(raw, str) or not raw.startswith("b64url:"):
        raise ValueError(f"{field} must use canonical b64url:<unpadded-value> encoding")
    encoded = raw.removeprefix("b64url:")
    if not encoded or not BASE64URL_SECRET.fullmatch(encoded):
        raise ValueError(f"{field} is not canonical unpadded base64url")
    # A 128-byte secret needs at most 171 unpadded base64url characters.
    # Reject oversized configuration before decoding so this boundary remains
    # allocation-bounded even when called outside the HTTP adapter.
    if len(encoded) > 171:
        raise ValueError(f"{field} exceeds the canonical 128-byte limit")
    try:
        material = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError(f"{field} is not valid base64url") from exc
    canonical = base64.urlsafe_b64encode(material).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(encoded, canonical):
        raise ValueError(f"{field} is not canonical unpadded base64url")
    if not MIN_SECRET_BYTES <= len(material) <= MAX_SECRET_BYTES:
        raise ValueError(
            f"{field} must decode to between {MIN_SECRET_BYTES} and {MAX_SECRET_BYTES} bytes"
        )
    return material


def _reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise IntegrityIsolationError(f"symlink path is not permitted: {path}")


def _safe_root(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _reject_symlink(root)
    return root.resolve()


def dirs(root: Path) -> dict[str, Path]:
    root = _safe_root(root)
    qikvrt_root = root / ".qikvrt"
    _reject_symlink(qikvrt_root)
    qikvrt_root.mkdir(exist_ok=True)
    _reject_symlink(qikvrt_root)
    state = qikvrt_root / "api"
    result = {
        "state": state,
        "inbox": state / "inbox",
        "audit": state / "audit",
        "out": state / "out",
        "replay": state / "replay",
        "protocol": state / "protocol",
        "transactions": state / "transactions",
        "provenance": state / "provenance",
        "stage": state / "out" / "stage",
        "work_orders": state / "out" / "work_orders",
    }
    for path in result.values():
        _reject_symlink(path)
        path.mkdir(parents=True, exist_ok=True)
        _reject_symlink(path)
    return result


def _assert_safe_target(path: Path) -> None:
    current = path
    while True:
        _reject_symlink(current)
        if current == current.parent:
            break
        current = current.parent
    if not path.parent.is_dir():
        raise IntegrityIsolationError(f"target parent is not a directory: {path.parent}")


def secure_read_bytes(path: Path, *, max_bytes: int | None = None) -> bytes:
    """Read one regular file through a single no-follow descriptor."""

    _assert_safe_target(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise IntegrityIsolationError(f"not a regular file: {path}")
        if max_bytes is not None and before.st_size > max_bytes:
            raise IntegrityIsolationError(f"file exceeds allowed size: {path}")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                raise IntegrityIsolationError(f"file exceeds allowed size: {path}")
            chunks.append(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise IntegrityIsolationError(f"file changed while being read: {path}")
        return b"".join(chunks)
    finally:
        os.close(fd)


@contextlib.contextmanager
def process_lock(root: Path):
    """Serialize handler effects across processes sharing the same root."""

    lock_path = dirs(root)["state"] / "handler.lock"
    _assert_safe_target(lock_path)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(lock_path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def atomic_write_bytes(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    """Durably replace one regular file without following a target symlink."""

    _assert_safe_target(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temporary)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _assert_safe_target(path)
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    atomic_write_text(path, _json_text(data))


def _json_text(data: Mapping[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _audit_hash(record_without_hash: Mapping[str, Any]) -> str:
    return sha256_identifier(_canonical_bytes(record_without_hash))


def validate_audit_chain(path: Path) -> dict[str, Any]:
    """Validate and return the last chained record, or an empty-chain marker."""

    _assert_safe_target(path)
    if not path.exists():
        return {"sequence": 0, "event_hash": None}
    previous_hash: str | None = None
    expected_sequence = 1
    last: dict[str, Any] = {"sequence": 0, "event_hash": None}
    try:
        lines = secure_read_bytes(path, max_bytes=64 * 1024 * 1024).decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError as exc:
        raise IntegrityIsolationError("audit chain is not UTF-8") from exc
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            raise IntegrityIsolationError(f"blank audit record at line {line_number}")
        try:
            record = _strict_json_loads(line)
        except ValueError as exc:
            raise IntegrityIsolationError(f"malformed audit JSON at line {line_number}") from exc
        if not isinstance(record, dict):
            raise IntegrityIsolationError(f"audit record {line_number} is not an object")
        event_hash = record.get("event_hash")
        projection = {key: value for key, value in record.items() if key != "event_hash"}
        if record.get("schema") != AUDIT_SCHEMA:
            raise IntegrityIsolationError(f"unsupported audit schema at line {line_number}")
        if record.get("sequence") != expected_sequence:
            raise IntegrityIsolationError(f"audit sequence gap at line {line_number}")
        if record.get("previous_event_hash") != previous_hash:
            raise IntegrityIsolationError(f"audit predecessor mismatch at line {line_number}")
        if event_hash != _audit_hash(projection):
            raise IntegrityIsolationError(f"audit hash mismatch at line {line_number}")
        previous_hash = event_hash
        expected_sequence += 1
        last = record
    return last


def append_audit(root: Path, event: Mapping[str, Any]) -> dict[str, Any]:
    """Append one fsynced, hash-linked audit event under the handler lock."""

    path = dirs(root)["audit"] / "events.jsonl"
    with _HANDLER_LOCK:
        last = validate_audit_chain(path)
        record: dict[str, Any] = {
            "schema": AUDIT_SCHEMA,
            "sequence": int(last.get("sequence", 0)) + 1,
            "previous_event_hash": last.get("event_hash"),
            "time": utc_now(),
            **dict(event),
        }
        record["event_hash"] = _audit_hash(record)
        encoded = (canonical_json(record) + "\n").encode("utf-8")
        _assert_safe_target(path)
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("audit append made no forward progress")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        return record


def _legacy_status(state: EffectState) -> str:
    return {
        EffectState.EFFECT_NACK: "NACK",
        EffectState.EFFECT_ACK_CONTINUE: "CONTINUE",
        EffectState.EFFECT_ACK_DONE: "PASS",
        EffectState.EFFECT_ACK_ISOLATE: "ISOLATE",
        EffectState.EFFECT_ACK_BLOCK: "BLOCK",
    }[state]


def _effect_request(
    cfg: HandlerConfig,
    *,
    payload: bytes | None,
    declared_hash: str | None,
    decision: ConnectionDecision,
    policy_allows_release: bool,
    reasons: tuple[str, ...],
    evidence_refs: tuple[str, ...] = (),
    required_evidence_refs: tuple[str, ...] = (),
    open_questions: tuple[str, ...] = (),
    next_checks: tuple[str, ...] = (),
    risk_level: RiskLevel = RiskLevel.LOW,
    checks_complete: bool = True,
) -> EffectAckResult:
    supplied_owner = cfg.responsibility_owner.strip()
    owner = supplied_owner or "unassigned-pending-review"
    responsibility_assigned = bool(supplied_owner) and (cfg.dry_run or cfg.effect_accepted)
    input_id = cfg.request_id.strip() or f"{cfg.run_id}:{cfg.operation}:{cfg.artifact_id}"
    if len(input_id) > 240:
        input_id = "sha256:" + sha256_bytes(input_id.encode("utf-8"))
    root_material = f"{cfg.repository}:{input_id}".encode("utf-8")
    request = EffectAckRequest(
        protocol_root_id=f"qikvrt:api:{sha256_bytes(root_material)}",
        input_id=input_id,
        payload=payload,
        transport_ack=payload is not None,
        declared_input_hash=(f"sha256:{declared_hash}" if declared_hash else None),
        origin_checked=cfg.origin_authenticated,
        context_checked=checks_complete,
        semantics_reconstructed=checks_complete,
        effect_anticipated=checks_complete,
        risk_classified=checks_complete,
        risk_level=risk_level,
        responsibility_assigned=responsibility_assigned,
        responsibility_owner=owner,
        connection_decision=decision,
        policy_allows_release=policy_allows_release,
        reasons=reasons,
        evidence_refs=evidence_refs,
        required_evidence_refs=required_evidence_refs,
        open_questions=open_questions,
        next_required_checks=next_checks,
    )
    return EffectAckEngine().evaluate(request)


def _haltpoint(state: EffectState, *, reason: str, error_class: str, cfg: HandlerConfig) -> dict[str, Any]:
    return {
        "blocking_gate": "QIKVRT_EFFECT_ACK_HALTPOINT",
        "error_class": error_class,
        "human_readable_reason": reason,
        "machine_readable_reason": error_class,
        "continue_path": "Correct the named precondition, preserve evidence, and rerun with a new request_id.",
        "repair_hint": "Inspect effect_ack.responsibility_protocol.reasons and next_required_checks.",
        "next_responsible_action": "RESPONSIBLE_OPERATOR_REVIEW_AND_RETRY",
        "required_consent": "effect_accepted=true plus responsibility_owner for non-dry-run mutation",
        "license_or_rights_context": "PolyForm-Noncommercial-1.0.0 source; commercial use requires separate written permission",
        "provenance_requirement": "authenticated origin, SHA-256 binding, request_id, and chained audit evidence",
        "retry_or_rebuild_path": "repair -> choose a fresh request_id -> rerun -> verify audit chain",
        "logfile": ".qikvrt/api/audit/events.jsonl",
        "evidence_file": ".qikvrt/api/audit/last_result.json",
        "exit_code": 20 if state is EffectState.EFFECT_ACK_CONTINUE else 1,
        "operation": cfg.operation,
        "artifact_id": cfg.artifact_id,
    }


def _with_effect(
    result: Mapping[str, Any],
    ack: EffectAckResult,
    *,
    cfg: HandlerConfig,
    reason: str = "",
    error_class: str = "",
) -> dict[str, Any]:
    merged = dict(result)
    merged.update(
        {
            "status": _legacy_status(ack.state),
            "effect_state": ack.state.value,
            "ordinary_release": ack.ordinary_release,
            "effect_ack": ack.to_dict(),
        }
    )
    if not ack.ordinary_release:
        merged["haltpoint"] = _haltpoint(
            ack.state,
            reason=reason or "; ".join(ack.protocol.reasons),
            error_class=(error_class or ack.protocol.reasons[0]) if ack.protocol.reasons else (error_class or "EFFECT_NOT_RELEASED"),
            cfg=cfg,
        )
    return merged


def _request_preconditions(cfg: HandlerConfig) -> None:
    try:
        safe_id(cfg.request_id.strip(), field="request_id")
    except ValueError as exc:
        raise PolicyBlockError(str(exc)) from exc
    attestation_secret_configured = bool(cfg.trusted_attestation_secret)
    attestation_signer_configured = bool(cfg.trusted_attestation_signer.strip())
    if attestation_secret_configured != attestation_signer_configured:
        raise PolicyBlockError(
            "remote attestation secret and trusted signer must be configured together"
        )
    if attestation_secret_configured:
        if len(cfg.trusted_attestation_signer.strip()) > 256:
            raise PolicyBlockError("trusted remote attestation signer is oversized")
        try:
            decode_secret_material(
                cfg.trusted_attestation_secret,
                field="QIKVRT_REMOTE_ATTESTATION_SECRET",
            )
        except ValueError as exc:
            raise PolicyBlockError(str(exc)) from exc


def _mutation_preconditions(cfg: HandlerConfig) -> None:
    _request_preconditions(cfg)
    if not cfg.effect_accepted:
        raise PolicyBlockError("explicit effect acceptance is required")
    if not cfg.responsibility_owner.strip():
        raise PolicyBlockError("responsibility_owner is required")
    if not cfg.origin_authenticated:
        raise PolicyBlockError("authenticated origin is required")


def _request_fingerprint(cfg: HandlerConfig) -> str:
    projection = {
        "operation": cfg.operation,
        "artifact_id": cfg.artifact_id,
        "payload_b64_sha256": sha256_bytes(cfg.payload_b64.encode("utf-8")),
        "expected_sha256": cfg.expected_sha256.lower(),
        "dry_run": cfg.dry_run,
        "repository": cfg.repository,
        "request_id": cfg.request_id,
        "effect_accepted": cfg.effect_accepted,
        "responsibility_owner": cfg.responsibility_owner,
        "origin_authenticated": cfg.origin_authenticated,
        "remote_evidence_b64_sha256": sha256_bytes(cfg.remote_evidence_b64.encode("utf-8")),
        "trusted_attestation_signer": cfg.trusted_attestation_signer,
    }
    return sha256_identifier(_canonical_bytes(projection))


def _load_receipt(cfg: HandlerConfig) -> dict[str, Any] | None:
    if not cfg.request_id:
        return None
    request_id = safe_id(cfg.request_id, field="request_id")
    path = dirs(cfg.root)["replay"] / f"{request_id}.json"
    _assert_safe_target(path)
    if not path.exists():
        return None
    try:
        receipt = _strict_json_loads(secure_read_bytes(path, max_bytes=4 * 1024 * 1024))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise IntegrityIsolationError("idempotency receipt is unreadable") from exc
    if not isinstance(receipt, dict):
        raise IntegrityIsolationError("idempotency receipt is not an object")
    if set(receipt) != {
        "schema", "request_id", "request_fingerprint", "result_sha256", "result",
    }:
        raise IntegrityIsolationError("idempotency receipt fields are incomplete or unknown")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise IntegrityIsolationError("idempotency receipt schema mismatch")
    if receipt.get("request_id") != safe_id(cfg.request_id, field="request_id"):
        raise IntegrityIsolationError("idempotency receipt request_id mismatch")
    if receipt.get("request_fingerprint") != _request_fingerprint(cfg):
        raise IntegrityIsolationError("request_id replayed with different content")
    result = receipt.get("result")
    if not isinstance(result, dict):
        raise IntegrityIsolationError("idempotency receipt result is malformed")
    result_sha256 = sha256_identifier(_canonical_bytes(result))
    if receipt.get("result_sha256") != result_sha256:
        raise IntegrityIsolationError("idempotency receipt result hash mismatch")
    if result.get("effect_state") != EffectState.EFFECT_ACK_DONE.value or result.get("ordinary_release") is not True:
        raise IntegrityIsolationError("idempotency receipt does not contain a DONE result")
    if result.get("operation") != cfg.operation:
        raise IntegrityIsolationError("idempotency receipt operation binding mismatch")
    effect_ack = result.get("effect_ack")
    if not isinstance(effect_ack, dict) or set(effect_ack) != {
        "state", "ordinary_release", "responsibility_protocol",
    }:
        raise IntegrityIsolationError("idempotency receipt EFFECT_ACK envelope is malformed")
    if (
        effect_ack.get("state") != EffectState.EFFECT_ACK_DONE.value
        or effect_ack.get("ordinary_release") is not True
    ):
        raise IntegrityIsolationError("idempotency receipt EFFECT_ACK envelope is not DONE")
    protocol_raw = effect_ack.get("responsibility_protocol")
    if not isinstance(protocol_raw, dict):
        raise IntegrityIsolationError("idempotency receipt lacks a responsibility protocol")
    try:
        protocol = ResponsibilityProtocol.from_dict(protocol_raw)
        verify_protocol(protocol)
    except Exception as exc:
        raise IntegrityIsolationError("idempotency responsibility protocol is invalid") from exc
    expected_protocol_root = (
        f"qikvrt:api:{sha256_bytes(f'{cfg.repository}:{cfg.request_id}'.encode('utf-8'))}"
    )
    if (
        protocol.input_id != cfg.request_id
        or protocol.protocol_root_id != expected_protocol_root
        or protocol.protocol_version != 1
        or protocol.previous_protocol_id is not None
        or protocol.previous_protocol_hash is not None
        or protocol.state is not EffectState.EFFECT_ACK_DONE
        or protocol.responsibility_owner != cfg.responsibility_owner.strip()
        or protocol.connection_decision is not ConnectionDecision.RELEASE
        or not protocol.policy_allows_release
        or not protocol.ordinary_release
    ):
        raise IntegrityIsolationError("idempotency responsibility protocol binding mismatch")
    if cfg.operation == "ingest":
        expected = require_sha(cfg.expected_sha256)
        if (
            result.get("artifact_id") != safe_id(cfg.artifact_id)
            or result.get("sha256") != expected
            or protocol.input_hash != f"sha256:{expected}"
        ):
            raise IntegrityIsolationError("idempotency ingest result binding mismatch")
    elif cfg.operation == "stage":
        stage_content_sha256 = result.get("stage_content_sha256")
        if (
            not isinstance(stage_content_sha256, str)
            or not SHA256_HEX.fullmatch(stage_content_sha256)
            or protocol.input_hash != f"sha256:{stage_content_sha256}"
        ):
            raise IntegrityIsolationError("idempotency stage result binding mismatch")
    elif cfg.operation == "work_order":
        expected = require_sha(cfg.expected_sha256)
        if (
            result.get("artifact_id") != safe_id(cfg.artifact_id)
            or result.get("source_sha256") != expected
            or protocol.input_hash != f"sha256:{expected}"
        ):
            raise IntegrityIsolationError("idempotency work-order result binding mismatch")
    else:
        raise IntegrityIsolationError("operation is not permitted to consume a persisted receipt")
    _verify_transaction_effects(cfg)
    transaction = _read_transaction(cfg)
    if transaction is None:
        raise IntegrityIsolationError("idempotency receipt has no recovery transaction")
    if (
        transaction.get("state") == "COMMITTED"
        and transaction.get("result_sha256") != result_sha256
    ):
        raise IntegrityIsolationError("committed recovery transaction result hash mismatch")
    return result


def _persist_receipt(cfg: HandlerConfig, result: Mapping[str, Any]) -> None:
    if not cfg.request_id or cfg.dry_run:
        return
    request_id = safe_id(cfg.request_id, field="request_id")
    path = dirs(cfg.root)["replay"] / f"{request_id}.json"
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "request_id": request_id,
        "request_fingerprint": _request_fingerprint(cfg),
        "result_sha256": sha256_identifier(_canonical_bytes(result)),
        "result": dict(result),
    }
    if path.exists():
        try:
            existing = _strict_json_loads(secure_read_bytes(path, max_bytes=4 * 1024 * 1024))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise IntegrityIsolationError("existing idempotency receipt is unreadable") from exc
        if existing != receipt:
            raise IntegrityIsolationError("idempotency receipt is append-only and already differs")
        return
    write_json(path, receipt)


def _persist_protocol(cfg: HandlerConfig, result: Mapping[str, Any]) -> None:
    protocol = result.get("effect_ack", {}).get("responsibility_protocol")
    if not isinstance(protocol, dict):
        return
    protocol_hash = str(protocol.get("protocol_hash", ""))
    if not protocol_hash.startswith("sha256:") or not SHA256_HEX.fullmatch(protocol_hash[7:]):
        raise IntegrityIsolationError("responsibility protocol has no canonical content hash")
    path = dirs(cfg.root)["protocol"] / f"{protocol_hash[7:]}.json"
    deterministic_protocol = {
        key: value for key, value in protocol.items() if key not in ("created_utc", "protocol_hash")
    }
    persisted = {
        "schema": "qikvrt_content_addressed_responsibility_protocol_v1",
        "protocol_hash": protocol_hash,
        "hash_projection": deterministic_protocol,
        "volatile_fields_excluded": ["created_utc"],
    }
    encoded = _json_text(persisted)
    if path.exists():
        if secure_read_bytes(path) != encoded.encode("utf-8"):
            raise IntegrityIsolationError("content-addressed protocol collision")
        return
    atomic_write_text(path, encoded)


def _transaction_path(cfg: HandlerConfig) -> Path | None:
    if cfg.dry_run or not cfg.request_id:
        return None
    request_id = safe_id(cfg.request_id, field="request_id")
    return dirs(cfg.root)["transactions"] / f"{request_id}.json"


def _read_transaction(cfg: HandlerConfig) -> dict[str, Any] | None:
    path = _transaction_path(cfg)
    if path is None or not path.exists():
        return None
    try:
        record = _strict_json_loads(secure_read_bytes(path, max_bytes=4 * 1024 * 1024))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise IntegrityIsolationError("recovery transaction is unreadable") from exc
    if not isinstance(record, dict):
        raise IntegrityIsolationError("recovery transaction is not an object")
    state = record.get("state")
    expected_keys = {
        "schema", "request_id", "request_fingerprint", "state", "effects",
        "history", "recovery_rule",
    }
    if state == "COMMITTED":
        expected_keys.add("result_sha256")
    if set(record) != expected_keys:
        raise IntegrityIsolationError("recovery transaction fields are incomplete or unknown")
    if record.get("schema") != TRANSACTION_SCHEMA:
        raise IntegrityIsolationError("recovery transaction schema mismatch")
    if record.get("request_id") != safe_id(cfg.request_id, field="request_id"):
        raise IntegrityIsolationError("recovery transaction request_id mismatch")
    if record.get("request_fingerprint") != _request_fingerprint(cfg):
        raise IntegrityIsolationError("recovery transaction is bound to different request facts")
    state_order = ("PREPARED", "APPLIED", "COMMITTED")
    if state not in state_order:
        raise IntegrityIsolationError("recovery transaction state is invalid")
    history = record.get("history")
    expected_history = list(state_order[: state_order.index(state) + 1])
    if (
        not isinstance(history, list)
        or [item.get("state") if isinstance(item, dict) else None for item in history]
        != expected_history
    ):
        raise IntegrityIsolationError("recovery transaction history is not contiguous")
    for item in history:
        if (
            not isinstance(item, dict)
            or set(item) != {"state", "time"}
            or not isinstance(item.get("time"), str)
            or not UTC_SECONDS.fullmatch(str(item["time"]))
        ):
            raise IntegrityIsolationError("recovery transaction history event is malformed")
    if record.get("recovery_rule") != (
        "Never claim rollback; inspect effects and safely replay the same authenticated request."
    ):
        raise IntegrityIsolationError("recovery transaction recovery rule differs")
    effects = record.get("effects")
    if not isinstance(effects, list) or not effects:
        raise IntegrityIsolationError("recovery transaction contains no declared effects")
    for effect in effects:
        if not isinstance(effect, dict) or set(effect) != {"path", "sha256", "size"}:
            raise IntegrityIsolationError("recovery transaction effect is malformed")
        if (
            not isinstance(effect.get("path"), str)
            or not effect["path"]
            or not isinstance(effect.get("sha256"), str)
            or not SHA256_HEX.fullmatch(str(effect.get("sha256", "")))
            or type(effect.get("size")) is not int
            or effect["size"] < 0
        ):
            raise IntegrityIsolationError("recovery transaction effect fields are invalid")
    if state == "COMMITTED":
        result_sha256 = record.get("result_sha256")
        if (
            not isinstance(result_sha256, str)
            or not result_sha256.startswith("sha256:")
            or not SHA256_HEX.fullmatch(result_sha256[7:])
        ):
            raise IntegrityIsolationError("recovery transaction result hash is invalid")
    return record


def _verify_transaction_effects(cfg: HandlerConfig) -> None:
    record = _read_transaction(cfg)
    if record is None:
        raise IntegrityIsolationError("idempotency receipt has no recovery transaction")
    if record.get("state") not in ("APPLIED", "COMMITTED"):
        raise IntegrityIsolationError("transaction effects were not fully applied")
    effects = record.get("effects")
    if not isinstance(effects, list) or not effects:
        raise IntegrityIsolationError("transaction contains no declared effects")
    root = cfg.root.resolve()
    for effect in effects:
        if not isinstance(effect, dict):
            raise IntegrityIsolationError("transaction effect is malformed")
        relative = Path(str(effect.get("path", "")))
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise IntegrityIsolationError("transaction effect path escapes repository root")
        path = root / relative
        _assert_safe_target(path)
        if not path.exists():
            raise IntegrityIsolationError(f"declared transaction effect is missing: {relative}")
        data = secure_read_bytes(path, max_bytes=MAX_PAYLOAD_BYTES + 1024 * 1024)
        if effect.get("size") != len(data) or effect.get("sha256") != sha256_bytes(data):
            raise IntegrityIsolationError(f"declared transaction effect changed: {relative}")


def _advance_transaction(
    cfg: HandlerConfig,
    state: str,
    *,
    effects: list[dict[str, Any]] | None = None,
    result: Mapping[str, Any] | None = None,
) -> None:
    """Persist PREPARED -> APPLIED -> COMMITTED recovery state."""

    path = _transaction_path(cfg)
    if path is None:
        return
    order = {"PREPARED": 1, "APPLIED": 2, "COMMITTED": 3}
    if state not in order:
        raise ValueError("unknown transaction state")
    previous = _read_transaction(cfg)
    if previous is None:
        if state != "PREPARED" or effects is None:
            raise IntegrityIsolationError("transaction must start in PREPARED")
        history: list[dict[str, Any]] = []
        bound_effects = effects
    else:
        previous_state = str(previous.get("state", ""))
        if previous_state not in order:
            raise IntegrityIsolationError("invalid recovery transaction state transition")
        history = list(previous.get("history", []))
        bound_effects = list(previous.get("effects", []))
        if effects is not None and effects != bound_effects:
            raise IntegrityIsolationError("recovery transaction effects changed")
        if order[state] <= order[previous_state]:
            if state == "COMMITTED" and result is not None:
                expected_result_sha256 = sha256_identifier(_canonical_bytes(result))
                if previous.get("result_sha256") != expected_result_sha256:
                    raise IntegrityIsolationError(
                        "committed recovery transaction is bound to a different result"
                    )
            return
    event = {"state": state, "time": utc_now()}
    history.append(event)
    record: dict[str, Any] = {
        "schema": TRANSACTION_SCHEMA,
        "request_id": cfg.request_id,
        "request_fingerprint": _request_fingerprint(cfg),
        "state": state,
        "effects": bound_effects,
        "history": history,
        "recovery_rule": "Never claim rollback; inspect effects and safely replay the same authenticated request.",
    }
    if result is not None:
        record["result_sha256"] = sha256_identifier(_canonical_bytes(result))
    write_json(path, record)


def _transaction_recovery_context(cfg: HandlerConfig) -> dict[str, Any]:
    try:
        record = _read_transaction(cfg)
    except Exception as exc:
        return {"recovery_required": True, "recovery_state": "UNREADABLE", "recovery_reason": str(exc)}
    if not record or record.get("state") == "COMMITTED":
        return {"recovery_required": False}
    path = _transaction_path(cfg)
    return {
        "recovery_required": True,
        "recovery_state": record.get("state"),
        "recovery_file": str(path.relative_to(cfg.root.resolve())) if path else None,
        "recovery_action": "Re-authorize and replay the identical request_id; inspect every declared effect before retry.",
    }


def op_ingest(cfg: HandlerConfig) -> dict[str, Any]:
    artifact_id = safe_id(cfg.artifact_id)
    expected = require_sha(cfg.expected_sha256)
    if len(cfg.payload_b64) > MAX_BASE64_CHARS:
        raise ValueError("base64 payload exceeds the 16 MiB decoded limit")
    try:
        payload = base64.b64decode(cfg.payload_b64.encode("utf-8"), validate=True)
    except Exception as exc:
        raise ValueError("invalid base64 payload") from exc
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ValueError("decoded payload exceeds the 16 MiB limit")
    actual = sha256_bytes(payload)
    if actual != expected:
        evidence = (f"sha256:{actual}",)
        ack = _effect_request(
            cfg,
            payload=payload,
            declared_hash=expected,
            decision=ConnectionDecision.BLOCK,
            policy_allows_release=False,
            reasons=("SHA256_MISMATCH",),
            evidence_refs=evidence,
            required_evidence_refs=evidence,
            next_checks=("REPAIR_AND_REVERIFY_INPUT_HASH_BINDING",),
            risk_level=RiskLevel.HIGH,
        )
        return _with_effect(
            {
                "operation": "ingest",
                "artifact_id": artifact_id,
                "actual_sha256": actual,
                "expected_sha256": expected,
                "sha256_match": False,
            },
            ack,
            cfg=cfg,
            reason=f"sha256 mismatch actual={actual} expected={expected}",
            error_class="SHA256_MISMATCH",
        )

    if not cfg.dry_run:
        _mutation_preconditions(cfg)
    evidence = (f"sha256:{actual}",)
    ack = _effect_request(
        cfg,
        payload=payload,
        declared_hash=expected,
        decision=ConnectionDecision.RELEASE,
        policy_allows_release=True,
        reasons=(
            "INGEST_VALIDATED",
            "EFFECT_SCOPE_OPAQUE_BYTE_STORAGE_ONLY",
            "PAYLOAD_CONTENT_NOT_EXECUTED_OR_SEMANTICALLY_RELEASED",
            "SCOPED_EFFECT_ACCEPTED" if not cfg.dry_run else "DRY_RUN_AUDIT_ONLY",
        ),
        evidence_refs=evidence,
        required_evidence_refs=evidence,
        risk_level=RiskLevel.MEDIUM if not cfg.dry_run else RiskLevel.LOW,
    )
    if not ack.ordinary_release:
        return _with_effect({"operation": "ingest", "artifact_id": artifact_id}, ack, cfg=cfg)

    d = dirs(cfg.root)
    target = d["inbox"] / f"{artifact_id}.bin"
    sidecar = d["inbox"] / f"{artifact_id}.bin.sha256"
    meta = d["provenance"] / f"{artifact_id}.{cfg.request_id}.json"
    for path in (target, sidecar, meta):
        _assert_safe_target(path)
    write_status = "DRY_RUN"
    if not cfg.dry_run:
        sidecar_text = f"{actual}  {target.name}\n"
        meta_data = {
            "schema": "qikvrt_ingest_provenance_v1",
            "artifact_id": artifact_id,
            "sha256": actual,
            "size": len(payload),
            "effect_scope": "opaque-byte-storage-only",
            "status": "INGESTED",
            "repository": cfg.repository,
            "request_id": cfg.request_id,
            "responsibility_owner": cfg.responsibility_owner,
        }
        meta_text = _json_text(meta_data)
        effects = [
            {"path": str(target.relative_to(cfg.root.resolve())), "sha256": actual, "size": len(payload)},
            {"path": str(sidecar.relative_to(cfg.root.resolve())), "sha256": sha256_bytes(sidecar_text.encode("utf-8")), "size": len(sidecar_text.encode("utf-8"))},
            {"path": str(meta.relative_to(cfg.root.resolve())), "sha256": sha256_bytes(meta_text.encode("utf-8")), "size": len(meta_text.encode("utf-8"))},
        ]
        _advance_transaction(cfg, "PREPARED", effects=effects)
        if target.exists():
            existing = sha256_bytes(secure_read_bytes(target, max_bytes=MAX_PAYLOAD_BYTES))
            if existing != actual:
                raise IntegrityIsolationError("artifact_id already binds different bytes")
            write_status = "ALREADY_PRESENT"
        else:
            atomic_write_bytes(target, payload)
            write_status = "WRITTEN"
        if sidecar.exists():
            if secure_read_bytes(sidecar, max_bytes=1024) != sidecar_text.encode("utf-8"):
                raise IntegrityIsolationError("artifact sidecar already binds different evidence")
        else:
            atomic_write_text(sidecar, sidecar_text)
        if meta.exists():
            if secure_read_bytes(meta, max_bytes=1024 * 1024) != meta_text.encode("utf-8"):
                raise IntegrityIsolationError("append-only ingest provenance already differs")
        else:
            atomic_write_text(meta, meta_text)
        _advance_transaction(cfg, "APPLIED")
    return _with_effect(
        {
            "operation": "ingest",
            "artifact_id": artifact_id,
            "sha256": actual,
            "size": len(payload),
            "effect_scope": "opaque-byte-storage-only",
            "write_status": write_status,
            "repository_persistence": "WORKFLOW_ARTIFACT_STORE_REQUIRED",
            "git_invoked": False,
        },
        ack,
        cfg=cfg,
    )


def op_verify(cfg: HandlerConfig) -> dict[str, Any]:
    artifact_id = safe_id(cfg.artifact_id)
    expected = require_sha(cfg.expected_sha256)
    target = dirs(cfg.root)["inbox"] / f"{artifact_id}.bin"
    _assert_safe_target(target)
    if not target.exists():
        ack = _effect_request(
            cfg,
            payload=None,
            declared_hash=None,
            decision=ConnectionDecision.UNDECIDED,
            policy_allows_release=False,
            reasons=("ARTIFACT_NOT_FOUND",),
            next_checks=("INGEST_OR_LOCATE_ARTIFACT",),
            checks_complete=False,
        )
        return _with_effect(
            {"operation": "verify", "artifact_id": artifact_id, "sha256_match": False},
            ack,
            cfg=cfg,
            reason="artifact not found",
            error_class="ARTIFACT_NOT_FOUND",
        )
    payload = secure_read_bytes(target, max_bytes=MAX_PAYLOAD_BYTES)
    actual = sha256_bytes(payload)
    decision = ConnectionDecision.RELEASE if actual == expected else ConnectionDecision.BLOCK
    evidence = (f"sha256:{actual}",)
    ack = _effect_request(
        cfg,
        payload=payload,
        declared_hash=expected,
        decision=decision,
        policy_allows_release=actual == expected,
        reasons=(("SHA256_MATCH", "EFFECT_SCOPE_BYTE_HASH_COMPARISON_ONLY") if actual == expected else ("SHA256_MISMATCH", "EFFECT_SCOPE_BYTE_HASH_COMPARISON_ONLY")),
        evidence_refs=evidence,
        required_evidence_refs=evidence,
    )
    return _with_effect(
        {
            "operation": "verify",
            "artifact_id": artifact_id,
            "actual_sha256": actual,
            "expected_sha256": expected,
            "sha256_match": actual == expected,
            "effect_scope": "byte-hash-comparison-only",
        },
        ack,
        cfg=cfg,
        reason="stored artifact hash does not match" if actual != expected else "",
        error_class="SHA256_MISMATCH" if actual != expected else "",
    )


def _secure_json(path: Path, *, max_bytes: int = 4 * 1024 * 1024) -> dict[str, Any]:
    return _json_object_from_bytes(
        secure_read_bytes(path, max_bytes=max_bytes),
        evidence_name=path.name,
    )


def _json_object_from_bytes(data: bytes, *, evidence_name: str) -> dict[str, Any]:
    try:
        value = _strict_json_loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise IntegrityIsolationError(f"JSON evidence is unreadable: {evidence_name}") from exc
    if not isinstance(value, dict):
        raise IntegrityIsolationError(f"JSON evidence is not an object: {evidence_name}")
    return value


def _verify_ingest_provenance(
    cfg: HandlerConfig,
    *,
    artifact_id: str,
    payload_path: Path,
    sidecar_path: Path,
    metadata_path: Path,
    payload: bytes,
    sidecar_bytes: bytes,
) -> dict[str, Any]:
    root = cfg.root.resolve()
    metadata_bytes = secure_read_bytes(metadata_path, max_bytes=1024 * 1024)
    metadata = _json_object_from_bytes(metadata_bytes, evidence_name=metadata_path.name)
    expected_keys = {
        "schema", "artifact_id", "sha256", "size", "effect_scope", "status",
        "repository", "request_id", "responsibility_owner",
    }
    if set(metadata) != expected_keys:
        raise IntegrityIsolationError(f"ingest provenance fields differ: {metadata_path.name}")
    actual = sha256_bytes(payload)
    expected_values = {
        "schema": "qikvrt_ingest_provenance_v1",
        "artifact_id": artifact_id,
        "sha256": actual,
        "size": len(payload),
        "effect_scope": "opaque-byte-storage-only",
        "status": "INGESTED",
        "repository": cfg.repository,
    }
    for key, value in expected_values.items():
        if metadata.get(key) != value:
            raise IntegrityIsolationError(f"ingest provenance {key} mismatch: {artifact_id}")
    request_id = safe_id(str(metadata.get("request_id", "")), field="ingest request_id")
    if metadata_path.name != f"{artifact_id}.{request_id}.json":
        raise IntegrityIsolationError("ingest provenance filename and request_id differ")
    owner = str(metadata.get("responsibility_owner", "")).strip()
    if not owner or len(owner) > 256:
        raise IntegrityIsolationError("ingest provenance responsibility owner is invalid")

    transaction_path = dirs(cfg.root)["transactions"] / f"{request_id}.json"
    receipt_path = dirs(cfg.root)["replay"] / f"{request_id}.json"
    for evidence_path in (transaction_path, receipt_path):
        _assert_safe_target(evidence_path)
        if not evidence_path.exists():
            raise IntegrityIsolationError(f"ingest provenance evidence missing: {evidence_path.name}")
    transaction_bytes = secure_read_bytes(transaction_path, max_bytes=4 * 1024 * 1024)
    receipt_bytes = secure_read_bytes(receipt_path, max_bytes=4 * 1024 * 1024)
    transaction = _json_object_from_bytes(transaction_bytes, evidence_name=transaction_path.name)
    receipt = _json_object_from_bytes(receipt_bytes, evidence_name=receipt_path.name)
    expected_transaction_keys = {
        "schema", "request_id", "request_fingerprint", "state", "effects",
        "history", "recovery_rule", "result_sha256",
    }
    expected_receipt_keys = {
        "schema", "request_id", "request_fingerprint", "result_sha256", "result",
    }
    if set(transaction) != expected_transaction_keys:
        raise IntegrityIsolationError("ingest recovery transaction fields are incomplete or unknown")
    if set(receipt) != expected_receipt_keys:
        raise IntegrityIsolationError("ingest idempotency receipt fields are incomplete or unknown")
    if transaction.get("schema") != TRANSACTION_SCHEMA or transaction.get("state") != "COMMITTED":
        raise IntegrityIsolationError("ingest recovery transaction is not committed")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise IntegrityIsolationError("ingest idempotency receipt schema mismatch")
    if transaction.get("request_id") != request_id or receipt.get("request_id") != request_id:
        raise IntegrityIsolationError("ingest request_id binding mismatch")
    request_fingerprint = transaction.get("request_fingerprint")
    if (
        not isinstance(request_fingerprint, str)
        or not request_fingerprint.startswith("sha256:")
        or not SHA256_HEX.fullmatch(request_fingerprint[7:])
        or request_fingerprint != receipt.get("request_fingerprint")
    ):
        raise IntegrityIsolationError("ingest receipt and transaction binding mismatch")
    result = receipt.get("result")
    if not isinstance(result, dict):
        raise IntegrityIsolationError("ingest receipt result is malformed")
    result_sha256 = sha256_identifier(_canonical_bytes(result))
    if (
        receipt.get("result_sha256") != result_sha256
        or transaction.get("result_sha256") != result_sha256
    ):
        raise IntegrityIsolationError("ingest receipt result hash mismatch")
    expected_result_keys = {
        "operation", "artifact_id", "sha256", "size", "effect_scope",
        "write_status", "repository_persistence", "git_invoked", "status",
        "effect_state", "ordinary_release", "effect_ack",
    }
    if set(result) != expected_result_keys:
        raise IntegrityIsolationError("ingest receipt result fields are incomplete or unknown")
    if (
        result.get("operation") != "ingest"
        or result.get("artifact_id") != artifact_id
        or result.get("sha256") != actual
        or result.get("size") != len(payload)
        or result.get("effect_scope") != "opaque-byte-storage-only"
        or result.get("write_status") not in ("WRITTEN", "ALREADY_PRESENT")
        or result.get("repository_persistence") != "WORKFLOW_ARTIFACT_STORE_REQUIRED"
        or result.get("git_invoked") is not False
        or result.get("status") != "PASS"
        or result.get("effect_state") != EffectState.EFFECT_ACK_DONE.value
        or result.get("ordinary_release") is not True
    ):
        raise IntegrityIsolationError("ingest receipt does not authorize this staged artifact")
    effect_ack = result.get("effect_ack")
    if not isinstance(effect_ack, dict) or set(effect_ack) != {
        "state", "ordinary_release", "responsibility_protocol",
    }:
        raise IntegrityIsolationError("ingest receipt EFFECT_ACK envelope is malformed")
    if (
        effect_ack.get("state") != EffectState.EFFECT_ACK_DONE.value
        or effect_ack.get("ordinary_release") is not True
    ):
        raise IntegrityIsolationError("ingest receipt EFFECT_ACK envelope is not DONE")
    protocol_raw = effect_ack.get("responsibility_protocol")
    if not isinstance(protocol_raw, dict):
        raise IntegrityIsolationError("ingest receipt responsibility protocol missing")
    try:
        protocol = ResponsibilityProtocol.from_dict(protocol_raw)
        verify_protocol(protocol)
    except Exception as exc:
        raise IntegrityIsolationError("ingest receipt responsibility protocol invalid") from exc
    expected_protocol_root = f"qikvrt:api:{sha256_bytes(f'{cfg.repository}:{request_id}'.encode('utf-8'))}"
    expected_evidence = (f"sha256:{actual}",)
    expected_reasons = {
        "ALL_RELEASE_GATES_SATISFIED",
        "EFFECT_SCOPE_OPAQUE_BYTE_STORAGE_ONLY",
        "INGEST_VALIDATED",
        "PAYLOAD_CONTENT_NOT_EXECUTED_OR_SEMANTICALLY_RELEASED",
        "SCOPED_EFFECT_ACCEPTED",
    }
    if (
        protocol.input_id != request_id
        or protocol.input_hash != f"sha256:{actual}"
        or protocol.protocol_root_id != expected_protocol_root
        or protocol.protocol_version != 1
        or protocol.previous_protocol_id is not None
        or protocol.previous_protocol_hash is not None
        or protocol.state is not EffectState.EFFECT_ACK_DONE
        or not protocol.transport_ack
        or not protocol.origin_checked
        or not protocol.context_checked
        or not protocol.semantics_reconstructed
        or not protocol.effect_anticipated
        or not protocol.risk_classified
        or protocol.risk_level is not RiskLevel.MEDIUM
        or not protocol.responsibility_assigned
        or protocol.responsibility_owner != owner
        or not protocol.connection_decided
        or protocol.connection_decision is not ConnectionDecision.RELEASE
        or not protocol.policy_allows_release
        or not protocol.ordinary_release
        or protocol.evidence_refs != expected_evidence
        or protocol.required_evidence_refs != expected_evidence
        or protocol.open_questions
        or protocol.next_required_checks
        or set(protocol.reasons) != expected_reasons
    ):
        raise IntegrityIsolationError("ingest responsibility protocol is not exactly bound to the artifact")

    history = transaction.get("history")
    if transaction.get("recovery_rule") != (
        "Never claim rollback; inspect effects and safely replay the same authenticated request."
    ):
        raise IntegrityIsolationError("ingest transaction recovery rule differs")
    if not isinstance(history, list) or [item.get("state") if isinstance(item, dict) else None for item in history] != [
        "PREPARED", "APPLIED", "COMMITTED",
    ]:
        raise IntegrityIsolationError("ingest transaction history is not PREPARED -> APPLIED -> COMMITTED")
    for item in history:
        if (
            not isinstance(item, dict)
            or set(item) != {"state", "time"}
            or not isinstance(item.get("time"), str)
            or not UTC_SECONDS.fullmatch(str(item["time"]))
        ):
            raise IntegrityIsolationError("ingest transaction history event is malformed")

    current_effects = {
        str(payload_path.relative_to(root)): payload,
        str(sidecar_path.relative_to(root)): sidecar_bytes,
        str(metadata_path.relative_to(root)): metadata_bytes,
    }
    expected_effects = [
        {"path": relative, "sha256": sha256_bytes(data), "size": len(data)}
        for relative, data in current_effects.items()
    ]
    if transaction.get("effects") != expected_effects:
        raise IntegrityIsolationError("ingest transaction effect set is not exactly bound")
    return {
        "path": str(metadata_path.relative_to(root)),
        "sha256": sha256_bytes(metadata_bytes),
        "request_id": request_id,
        "responsibility_owner": owner,
        "receipt_sha256": sha256_bytes(receipt_bytes),
        "protocol_hash": protocol.protocol_hash,
    }


def _verified_inbox_entries(cfg: HandlerConfig) -> list[dict[str, Any]]:
    """Bind payload, sidecar and append-only ingest provenance."""

    d = dirs(cfg.root)
    entries: list[dict[str, Any]] = []
    for path in sorted(d["inbox"].glob("*.bin")):
        _assert_safe_target(path)
        artifact_id = safe_id(path.name.removesuffix(".bin"))
        payload = secure_read_bytes(path, max_bytes=MAX_PAYLOAD_BYTES)
        actual = sha256_bytes(payload)
        sidecar = d["inbox"] / f"{artifact_id}.bin.sha256"
        _assert_safe_target(sidecar)
        if not sidecar.exists():
            raise IntegrityIsolationError(f"required staging sidecar missing: {sidecar.name}")
        sidecar_bytes = secure_read_bytes(sidecar, max_bytes=1024)
        expected_sidecar = f"{actual}  {path.name}\n".encode("utf-8")
        if sidecar_bytes != expected_sidecar:
            raise IntegrityIsolationError(f"sidecar does not bind staged payload: {artifact_id}")
        provenance_paths = sorted(d["provenance"].glob(f"{artifact_id}.*.json"))
        if not provenance_paths:
            raise IntegrityIsolationError(f"append-only ingest provenance missing: {artifact_id}")
        provenance = [
            _verify_ingest_provenance(
                cfg,
                artifact_id=artifact_id,
                payload_path=path,
                sidecar_path=sidecar,
                metadata_path=meta,
                payload=payload,
                sidecar_bytes=sidecar_bytes,
            )
            for meta in provenance_paths
        ]
        entries.append(
            {
                "artifact_id": artifact_id,
                "path": str(path.relative_to(cfg.root.resolve())),
                "size": len(payload),
                "sha256": actual,
                "sidecar": str(sidecar.relative_to(cfg.root.resolve())),
                "sidecar_sha256": sha256_bytes(sidecar_bytes),
                "provenance": provenance,
            }
        )
    return entries


def op_stage(cfg: HandlerConfig) -> dict[str, Any]:
    d = dirs(cfg.root)
    entries = _verified_inbox_entries(cfg)
    if not entries:
        descriptor = _canonical_bytes({"entries": [], "count": 0})
        ack = _effect_request(
            cfg,
            payload=descriptor,
            declared_hash=sha256_bytes(descriptor),
            decision=ConnectionDecision.CONTINUE,
            policy_allows_release=False,
            reasons=("NO_STAGED_ARTIFACTS",),
            next_checks=("INGEST_AND_VERIFY_AT_LEAST_ONE_ARTIFACT",),
        )
        return _with_effect(
            {"operation": "stage", "count": 0, "write_status": "NOT_WRITTEN"},
            ack,
            cfg=cfg,
            reason="no verified artifact is available for staging",
            error_class="NO_STAGED_ARTIFACTS",
        )
    if not cfg.dry_run:
        _mutation_preconditions(cfg)
    deterministic = {"schema": "qikvrt_stage_manifest_v1", "entries": entries, "count": len(entries)}
    descriptor = _canonical_bytes(deterministic)
    descriptor_hash = sha256_bytes(descriptor)
    evidence_set: set[str] = set()
    for entry in entries:
        evidence_set.add(f"sha256:{entry['sha256']}")
        evidence_set.add(f"sha256:{entry['sidecar_sha256']}")
        for provenance in entry["provenance"]:
            evidence_set.add(f"sha256:{provenance['sha256']}")
            evidence_set.add(f"sha256:{provenance['receipt_sha256']}")
            evidence_set.add(str(provenance["protocol_hash"]))
    evidence = tuple(sorted(evidence_set))
    ack = _effect_request(
        cfg,
        payload=descriptor,
        declared_hash=descriptor_hash,
        decision=ConnectionDecision.RELEASE,
        policy_allows_release=True,
        reasons=("STAGE_INPUTS_HASHED", "EFFECT_SCOPE_CONTENT_ADDRESSED_MANIFEST_ONLY"),
        evidence_refs=evidence,
        required_evidence_refs=evidence,
        risk_level=RiskLevel.MEDIUM if not cfg.dry_run else RiskLevel.LOW,
    )
    manifest_data = {
        **deterministic,
        "content_sha256": descriptor_hash,
        "request_id": cfg.request_id,
        "responsibility_owner": cfg.responsibility_owner,
    }
    manifest_text = _json_text(manifest_data)
    manifest_sha256 = sha256_bytes(manifest_text.encode("utf-8"))
    stage_manifest = d["stage"] / f"{manifest_sha256}.json"
    if not cfg.dry_run and ack.ordinary_release:
        effects = [
            {
                "path": str(stage_manifest.relative_to(cfg.root.resolve())),
                "sha256": manifest_sha256,
                "size": len(manifest_text.encode("utf-8")),
            }
        ]
        _advance_transaction(cfg, "PREPARED", effects=effects)
        if stage_manifest.exists():
            if secure_read_bytes(stage_manifest, max_bytes=16 * 1024 * 1024) != manifest_text.encode("utf-8"):
                raise IntegrityIsolationError("content-addressed stage manifest collision")
        else:
            atomic_write_text(stage_manifest, manifest_text)
        _advance_transaction(cfg, "APPLIED")
    return _with_effect(
        {
            "operation": "stage",
            "count": len(entries),
            "stage_manifest": str(stage_manifest.relative_to(cfg.root.resolve())),
            "stage_content_sha256": descriptor_hash,
            "stage_manifest_sha256": manifest_sha256,
            "effect_scope": "content-addressed-manifest-only",
            "write_status": "DRY_RUN" if cfg.dry_run else "WRITTEN",
        },
        ack,
        cfg=cfg,
    )


def op_work_order(cfg: HandlerConfig) -> dict[str, Any]:
    artifact_id = safe_id(cfg.artifact_id)
    expected = require_sha(cfg.expected_sha256)
    if len(cfg.payload_b64) > MAX_BASE64_CHARS:
        raise ValueError("base64 work order exceeds the 16 MiB decoded limit")
    try:
        payload = base64.b64decode(cfg.payload_b64.encode("utf-8"), validate=True)
    except Exception as exc:
        raise ValueError("invalid base64 work order") from exc
    if len(payload) > 256 * 1024:
        raise ValueError("work order exceeds the 256 KiB limit")
    actual = sha256_bytes(payload)
    if actual != expected:
        evidence = (f"sha256:{actual}",)
        ack = _effect_request(
            cfg,
            payload=payload,
            declared_hash=expected,
            decision=ConnectionDecision.BLOCK,
            policy_allows_release=False,
            reasons=("WORK_ORDER_SHA256_MISMATCH",),
            evidence_refs=evidence,
            required_evidence_refs=evidence,
            next_checks=("REPAIR_AND_REVERIFY_WORK_ORDER_HASH",),
            risk_level=RiskLevel.HIGH,
        )
        return _with_effect(
            {
                "operation": "work_order",
                "artifact_id": artifact_id,
                "actual_sha256": actual,
                "expected_sha256": expected,
                "work_order_accepted": False,
            },
            ack,
            cfg=cfg,
            reason=f"work-order sha256 mismatch actual={actual} expected={expected}",
            error_class="WORK_ORDER_SHA256_MISMATCH",
        )
    try:
        value = _strict_json_loads(payload)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("work order must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("work order must be a JSON object")
    allowed = {"schema", "task_type", "output_path", "requirements", "acceptance", "notes"}
    required = {"schema", "task_type", "output_path", "requirements"}
    if set(value) - allowed or required - set(value):
        raise ValueError("work-order fields are incomplete or unknown")
    if value.get("schema") != "qikvrt_work_order_v1":
        raise ValueError("unsupported work-order schema")
    if value.get("task_type") not in {"implement_artifact", "modify_artifact"}:
        raise ValueError("unsupported work-order task_type")
    output_path = value.get("output_path")
    if (
        not isinstance(output_path, str)
        or not WORK_ORDER_PATH.fullmatch(output_path)
        or output_path.startswith("/")
        or "//" in output_path
        or any(part in {"", ".", ".."} for part in output_path.split("/"))
    ):
        raise ValueError("unsafe work-order output_path")
    requirements = value.get("requirements")
    if not isinstance(requirements, dict) or len(requirements) > 64:
        raise ValueError("work-order requirements must be an object with at most 64 properties")
    acceptance = value.get("acceptance", {})
    if not isinstance(acceptance, dict) or len(acceptance) > 64:
        raise ValueError("work-order acceptance must be an object with at most 64 properties")
    notes = value.get("notes", "")
    if not isinstance(notes, str) or len(notes) > 8192:
        raise ValueError("work-order notes must be a string of at most 8192 characters")
    if not cfg.dry_run:
        _mutation_preconditions(cfg)

    normalized = {
        "schema": "qikvrt_work_order_v1",
        "task_type": value["task_type"],
        "output_path": output_path,
        "requirements": requirements,
        "acceptance": acceptance,
        "notes": notes,
    }
    normalized_bytes = _canonical_bytes(normalized)
    normalized_sha256 = sha256_bytes(normalized_bytes)
    evidence = (f"sha256:{actual}", f"sha256:{normalized_sha256}")
    ack = _effect_request(
        cfg,
        payload=payload,
        declared_hash=expected,
        decision=ConnectionDecision.RELEASE,
        policy_allows_release=True,
        reasons=(
            "WORK_ORDER_SCHEMA_VALIDATED",
            "WORK_ORDER_HASH_BOUND",
            "EFFECT_SCOPE_WORK_ORDER_REGISTRATION_ONLY",
            "TASK_EXECUTION_NOT_IMPLIED",
            "SCOPED_EFFECT_ACCEPTED" if not cfg.dry_run else "DRY_RUN_AUDIT_ONLY",
        ),
        evidence_refs=evidence,
        required_evidence_refs=evidence,
        risk_level=RiskLevel.MEDIUM if not cfg.dry_run else RiskLevel.LOW,
    )

    registration = {
        "schema": "qikvrt_work_order_registration_v1",
        "artifact_id": artifact_id,
        "request_id": cfg.request_id,
        "repository": cfg.repository,
        "responsibility_owner": cfg.responsibility_owner,
        "source_sha256": actual,
        "normalized_work_order_sha256": normalized_sha256,
        "work_order": normalized,
    }
    registration_text = _json_text(registration)
    registration_sha256 = sha256_bytes(registration_text.encode("utf-8"))
    target = dirs(cfg.root)["work_orders"] / f"{registration_sha256}.json"
    write_status = "DRY_RUN"
    if not cfg.dry_run and ack.ordinary_release:
        effects = [{
            "path": str(target.relative_to(cfg.root.resolve())),
            "sha256": registration_sha256,
            "size": len(registration_text.encode("utf-8")),
        }]
        _advance_transaction(cfg, "PREPARED", effects=effects)
        if target.exists():
            if secure_read_bytes(target, max_bytes=512 * 1024) != registration_text.encode("utf-8"):
                raise IntegrityIsolationError("content-addressed work-order registration collision")
            write_status = "ALREADY_PRESENT"
        else:
            atomic_write_text(target, registration_text)
            write_status = "WRITTEN"
        _advance_transaction(cfg, "APPLIED")

    return _with_effect(
        {
            "operation": "work_order",
            "artifact_id": artifact_id,
            "source_sha256": actual,
            "normalized_work_order_sha256": normalized_sha256,
            "work_order_accepted": True,
            "task_execution": "NOT_EXECUTED",
            "effect_scope": "work-order-registration-only",
            "registration_path": str(target.relative_to(cfg.root.resolve())),
            "registration_sha256": registration_sha256,
            "write_status": write_status,
        },
        ack,
        cfg=cfg,
    )


def op_release_status(cfg: HandlerConfig) -> dict[str, Any]:
    descriptor = _canonical_bytes({"repository": cfg.repository, "run_id": cfg.run_id})
    if cfg.remote_evidence_b64 or cfg.payload_b64 or cfg.expected_sha256:
        if not (cfg.remote_evidence_b64 and cfg.payload_b64 and cfg.expected_sha256):
            raise PolicyBlockError("remote evidence, asset bytes, and expected_sha256 must be supplied together")
        if not cfg.trusted_attestation_secret or not cfg.trusted_attestation_signer:
            raise PolicyBlockError("trusted remote attestation verifier is not configured")
        try:
            attestation_key = decode_secret_material(
                cfg.trusted_attestation_secret,
                field="QIKVRT_REMOTE_ATTESTATION_SECRET",
            )
        except ValueError as exc:
            raise PolicyBlockError(str(exc)) from exc
        if len(cfg.remote_evidence_b64) > 256 * 1024:
            raise PolicyBlockError("remote attestation exceeds the bounded evidence limit")
        if len(cfg.payload_b64) > MAX_BASE64_CHARS:
            raise PolicyBlockError("remote asset exceeds the bounded payload limit")
        try:
            attestation_bytes = base64.b64decode(cfg.remote_evidence_b64.encode("utf-8"), validate=True)
            asset = base64.b64decode(cfg.payload_b64.encode("utf-8"), validate=True)
            attestation = _strict_json_loads(attestation_bytes)
        except (ValueError, UnicodeDecodeError) as exc:
            raise PolicyBlockError("remote release evidence is not canonical base64 JSON") from exc
        if not isinstance(attestation, dict):
            raise PolicyBlockError("remote release attestation must be an object")
        required = {
            "schema", "repository", "release_run_id", "asset_name", "asset_sha256",
            "asset_size", "source_uri", "immutable_source_id", "signer", "signature",
        }
        if set(attestation) != required:
            raise PolicyBlockError("remote release attestation fields are incomplete or unknown")
        expected = require_sha(cfg.expected_sha256)
        actual = sha256_bytes(asset)
        if attestation.get("schema") != "qikvrt_remote_release_attestation_v1":
            raise PolicyBlockError("unsupported remote release attestation schema")
        if attestation.get("repository") != cfg.repository:
            raise IntegrityIsolationError("remote attestation repository binding mismatch")
        if attestation.get("signer") != cfg.trusted_attestation_signer:
            raise IntegrityIsolationError("remote attestation signer is not trusted")
        if not isinstance(attestation.get("release_run_id"), str) or not str(attestation["release_run_id"]).strip():
            raise PolicyBlockError("remote attestation release_run_id is missing")
        if not isinstance(attestation.get("asset_name"), str) or not SAFE_ID.fullmatch(str(attestation["asset_name"])):
            raise PolicyBlockError("remote attestation asset_name is unsafe")
        if type(attestation.get("asset_size")) is not int or attestation["asset_size"] != len(asset):
            raise IntegrityIsolationError("remote attestation asset size mismatch")
        if attestation.get("asset_sha256") != expected:
            raise IntegrityIsolationError("remote attestation expected hash mismatch")
        if not isinstance(attestation.get("source_uri"), str) or not str(attestation["source_uri"]).startswith("https://"):
            raise PolicyBlockError("remote attestation requires an HTTPS source URI")
        immutable_source_id = str(attestation.get("immutable_source_id", ""))
        if not immutable_source_id or len(immutable_source_id) > 256:
            raise PolicyBlockError("remote attestation immutable_source_id is missing or oversized")
        signature = str(attestation.get("signature", ""))
        if not SHA256_HEX.fullmatch(signature):
            raise IntegrityIsolationError("remote attestation signature is malformed")
        signed_projection = {key: value for key, value in attestation.items() if key != "signature"}
        expected_signature = hmac.new(
            attestation_key,
            _canonical_bytes(signed_projection),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature.lower(), expected_signature):
            raise IntegrityIsolationError("remote attestation signature verification failed")
        evidence = (f"sha256:{actual}", sha256_identifier(_canonical_bytes(signed_projection)))
        ack = _effect_request(
            cfg,
            payload=asset,
            declared_hash=expected,
            decision=ConnectionDecision.RELEASE,
            policy_allows_release=actual == expected,
            reasons=("REMOTE_ASSET_BYTES_VERIFIED", "SIGNED_IMMUTABLE_SOURCE_ATTESTATION_VERIFIED", "EFFECT_SCOPE_RELEASE_STATUS_ATTESTATION_ONLY"),
            evidence_refs=evidence,
            required_evidence_refs=evidence,
            risk_level=RiskLevel.LOW,
        )
        return _with_effect(
            {
                "operation": "release_status",
                "repository": cfg.repository,
                "run_id": cfg.run_id,
                "release_run_id": attestation["release_run_id"],
                "asset_name": attestation["asset_name"],
                "remote_visibility": "ATTESTED_IMMUTABLE_SOURCE",
                "remote_byte_exact_asset_hash": actual if actual == expected else "MISMATCH",
                "remote_source_uri": attestation["source_uri"],
                "immutable_source_id": immutable_source_id,
                "effect_scope": "release-status-attestation-only",
            },
            ack,
            cfg=cfg,
            reason="remote asset bytes do not match the attested digest" if actual != expected else "",
            error_class="REMOTE_ASSET_HASH_MISMATCH" if actual != expected else "",
        )
    ack = _effect_request(
        cfg,
        payload=descriptor,
        declared_hash=sha256_bytes(descriptor),
        decision=ConnectionDecision.CONTINUE,
        policy_allows_release=False,
        reasons=("REMOTE_BYTE_EXACT_ASSET_HASH_NOT_CONFIRMED",),
        open_questions=("REMOTE_RELEASE_EVIDENCE_REQUIRED",),
        next_checks=("FETCH_REMOTE_RELEASE_EVIDENCE_AND_VERIFY_BYTE_EXACT_HASH",),
        checks_complete=True,
        risk_level=RiskLevel.MEDIUM,
    )
    return _with_effect(
        {
            "operation": "release_status",
            "repository": cfg.repository,
            "run_id": cfg.run_id,
            "github_rest_api_entrypoint": "workflow_dispatch/repository_dispatch",
            "remote_visibility": "NOT_CONFIRMED",
            "remote_byte_exact_asset_hash": "NOT_CONFIRMED",
            "effect_scope": "release-status-attestation-only",
        },
        ack,
        cfg=cfg,
        reason="remote byte-exact release evidence has not been supplied",
        error_class="REMOTE_RELEASE_NOT_CONFIRMED",
    )


def _exception_result(cfg: HandlerConfig, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, IntegrityIsolationError):
        decision = ConnectionDecision.ISOLATE
        error_class = "INTEGRITY_OR_REPLAY_CONFLICT"
    elif isinstance(exc, PolicyBlockError):
        decision = ConnectionDecision.BLOCK
        error_class = "EFFECT_ACCEPTANCE_REQUIRED"
    else:
        decision = ConnectionDecision.UNDECIDED
        error_class = "INVALID_OR_INCOMPLETE_REQUEST"
    payload = str(exc).encode("utf-8") if not isinstance(exc, ValueError) else None
    ack = _effect_request(
        cfg,
        payload=payload,
        declared_hash=sha256_bytes(payload) if payload is not None else None,
        decision=decision,
        policy_allows_release=False,
        reasons=(error_class, str(exc)),
        next_checks=("REPAIR_REQUEST_AND_RETRY_WITH_FRESH_REQUEST_ID",),
        checks_complete=not isinstance(exc, ValueError),
        risk_level=RiskLevel.HIGH,
    )
    return _with_effect(
        {"operation": cfg.operation, "artifact_id": cfg.artifact_id, "reason": str(exc)},
        ack,
        cfg=cfg,
        reason=str(exc),
        error_class=error_class,
    )


def run_handler(cfg: HandlerConfig) -> dict[str, Any]:
    """Run one serialized, audited and idempotent handler operation."""

    with _HANDLER_LOCK:
        with process_lock(cfg.root):
            try:
                _request_preconditions(cfg)
                if not cfg.dry_run:
                    # Replays are authorized again; an old receipt is never an
                    # authentication or acceptance credential.
                    _mutation_preconditions(cfg)
                fingerprint = _request_fingerprint(cfg)
                append_audit(
                    cfg.root,
                    {
                        "event": "request_received",
                        "operation": cfg.operation,
                        "artifact_id": cfg.artifact_id,
                        "request_id": cfg.request_id,
                        "request_fingerprint": fingerprint,
                        "responsibility_owner": cfg.responsibility_owner,
                        "origin_authenticated": cfg.origin_authenticated,
                        "dry_run": cfg.dry_run,
                    },
                )
                replayed = _load_receipt(cfg)
                was_replay = replayed is not None
                if replayed is not None:
                    receipt_result = dict(replayed)
                    result = dict(receipt_result)
                    result["replayed"] = True
                elif cfg.operation == "ingest":
                    result = op_ingest(cfg)
                elif cfg.operation == "verify":
                    result = op_verify(cfg)
                elif cfg.operation == "stage":
                    result = op_stage(cfg)
                elif cfg.operation == "work_order":
                    result = op_work_order(cfg)
                elif cfg.operation == "release_status":
                    result = op_release_status(cfg)
                else:
                    raise ValueError("unknown operation")

                audit_record = append_audit(
                    cfg.root,
                    {
                        "event": "request_result",
                        "operation": cfg.operation,
                        "artifact_id": cfg.artifact_id,
                        "request_id": cfg.request_id,
                        "request_fingerprint": fingerprint,
                        "effect_state": result.get("effect_state"),
                        "ordinary_release": result.get("ordinary_release", False),
                        "result_sha256": sha256_identifier(_canonical_bytes(result)),
                    },
                )
                write_json(
                    dirs(cfg.root)["audit"] / "anchor.json",
                    {
                        "schema": "qikvrt_local_detached_audit_anchor_v1",
                        "sequence": audit_record["sequence"],
                        "event_hash": audit_record["event_hash"],
                        "trust_boundary": "LOCAL_ONLY; publish to an independent trusted store for rewrite detection",
                    },
                )
                write_json(dirs(cfg.root)["audit"] / "last_result.json", result)
                _persist_protocol(cfg, result)
                if result.get("effect_state") == EffectState.EFFECT_ACK_DONE.value:
                    if was_replay:
                        transaction = _read_transaction(cfg)
                        if transaction is not None and transaction.get("state") == "APPLIED":
                            _advance_transaction(cfg, "COMMITTED", result=receipt_result)
                    elif cfg.operation in ("ingest", "stage", "work_order") and not cfg.dry_run:
                        _persist_receipt(cfg, result)
                        _advance_transaction(cfg, "COMMITTED", result=result)
                return result
            except Exception as exc:
                result = _exception_result(cfg, exc)
                result.update(_transaction_recovery_context(cfg))
                try:
                    append_audit(
                        cfg.root,
                        {
                            "event": "request_exception",
                            "operation": cfg.operation or "UNKNOWN",
                            "artifact_id": cfg.artifact_id,
                            "request_id": cfg.request_id,
                            "effect_state": result.get("effect_state"),
                            "reason": str(exc),
                            "recovery_required": result.get("recovery_required", False),
                        },
                    )
                    write_json(dirs(cfg.root)["audit"] / "last_result.json", result)
                    _persist_protocol(cfg, result)
                except Exception as audit_exc:
                    result["audit_status"] = "ISOLATED_UNTRUSTED"
                    result["audit_reason"] = str(audit_exc)
                    result["status"] = "ISOLATE"
                    result["effect_state"] = EffectState.EFFECT_ACK_ISOLATE.value
                    result["ordinary_release"] = False
                return result


def config_from_env(root: Path | None = None) -> HandlerConfig:
    return HandlerConfig(
        root=root or Path.cwd(),
        operation=os.environ.get("QIKVRT_OPERATION", "").strip(),
        artifact_id=os.environ.get("QIKVRT_ARTIFACT_ID", "").strip() or "status",
        payload_b64=os.environ.get("QIKVRT_PAYLOAD_B64", ""),
        expected_sha256=os.environ.get("QIKVRT_EXPECTED_SHA256", ""),
        dry_run=os.environ.get("QIKVRT_DRY_RUN", "true").lower() != "false",
        repository=os.environ.get("GITHUB_REPOSITORY", "local/qik-vrt"),
        run_id=os.environ.get("GITHUB_RUN_ID", "local-run"),
        request_id=os.environ.get("QIKVRT_REQUEST_ID", "").strip(),
        effect_accepted=os.environ.get("QIKVRT_EFFECT_ACCEPTED", "false").lower() == "true",
        responsibility_owner=os.environ.get("QIKVRT_RESPONSIBILITY_OWNER", "").strip(),
        origin_authenticated=os.environ.get("QIKVRT_ORIGIN_AUTHENTICATED", "false").lower() == "true",
        remote_evidence_b64=os.environ.get("QIKVRT_REMOTE_EVIDENCE_B64", ""),
        trusted_attestation_secret=os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", ""),
        trusted_attestation_signer=os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip(),
    )


def main() -> int:
    result = run_handler(config_from_env())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("effect_state") == EffectState.EFFECT_ACK_DONE.value:
        return 0
    if result.get("effect_state") == EffectState.EFFECT_ACK_CONTINUE.value:
        return 20
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
