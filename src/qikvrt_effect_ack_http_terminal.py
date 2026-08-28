#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Loopback-only reference backend for the QIKVRT Firefox terminal.

Experimental HTTP-profile demonstrator. V1 preserves the original in-memory
loopback reference. Opt-in V2 adds a private node-local hash-linked ledger for
sessionless two-peer HTTP prepare/commit/replay testing. Neither profile grants
repository, publication, deployment, browser-runtime, TLS/mTLS, or other
external-effect capability.
"""
from __future__ import annotations

import argparse
import base64
import errno
try:
    import fcntl
except ImportError:  # pragma: no cover - the durable local profile is POSIX-only.
    fcntl = None  # type: ignore[assignment]
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import stat
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

MAX_BODY = 2 * 1024 * 1024
MAX_MEDIA_BYTES = 512 * 1024
MAX_SAFE_JSON_INTEGER = (1 << 53) - 1
MAX_CANONICAL_DEPTH = 16
MAX_CANONICAL_COLLECTION_ITEMS = 64
TOKEN_TTL_SECONDS = 120
HOST = "127.0.0.1"
DEFAULT_PORT = 8771
SF_KEY = re.compile(r"^[a-z*][a-z0-9_.*-]*$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._=-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_MILLIS_UTC_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{3})?Z$"
)
MEDIA_CONTENT_TYPE_RE = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}$"
)
CANONICAL_BASE64_RE = re.compile(
    r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"
)
LEDGER_SCHEMA = "qikvrt_effect_ack_http_terminal_ledger_v2"
NODE_SCHEMA = "qikvrt_effect_ack_http_terminal_node_v2"
PEER_POLICY_ID = "QIKVRT_HTTP_TERMINAL_PEER_V2"
PEER_POLICY_PROJECTION = {
    "policy_id": PEER_POLICY_ID,
    "policy_version": 2,
    "wire_version": 2,
    "commit_bindings": [
        "effective_method",
        "effective_target",
        "request_content_sha256",
        "policy_sha256",
        "responsibility_owner",
        "record_hash",
        "expires_at",
        "source_node_id",
        "target_node_id",
        "target_endpoint_id",
        "request_id",
    ],
    "terminal_input_schema": "qikvrt_terminal_input_v2",
    "serialization_profile": "QIKVRT_CLOSED_JSON_V2",
    "terminal_input_forbidden": [
        "floating_point",
        "array",
        "untyped_object",
        "duplicate_json_member",
        "noncanonical_base64",
        "invalid_utf8",
    ],
    "media_descriptor_schema": "qikvrt_terminal_media_descriptor_v1",
    "external_effect": "NONE",
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utf8_text(value: Any, field: str, *, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value) or len(value) > maximum:
        raise ValueError(f"{field} is outside bounded UTF-8 text")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} is not valid UTF-8 text") from exc
    return value


def _validate_closed_json_v2(value: Any, *, path: str = "value", depth: int = 0) -> None:
    """Accept the finite JSON domain used by V2 hashes and tokens.

    Floating point is excluded because independent JSON stacks need not emit an
    identical decimal spelling.  Every integer is constrained to the exact
    IEEE-754 safe range so a normal browser JSON implementation preserves it.
    Terminal-input shape validation below further prohibits arrays and arbitrary
    objects; this helper also protects internal V2 receipts before hashing.
    """

    if depth > MAX_CANONICAL_DEPTH:
        raise ValueError(f"{path} exceeds canonical JSON nesting depth")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if not -MAX_SAFE_JSON_INTEGER <= value <= MAX_SAFE_JSON_INTEGER:
            raise ValueError(f"{path} is outside the canonical JSON integer range")
        return
    if type(value) is str:
        _utf8_text(value, path, maximum=MAX_BODY, allow_empty=True)
        return
    if type(value) is list:
        if len(value) > MAX_CANONICAL_COLLECTION_ITEMS:
            raise ValueError(f"{path} has too many canonical JSON array items")
        for index, member in enumerate(value):
            _validate_closed_json_v2(member, path=f"{path}[{index}]", depth=depth + 1)
        return
    if type(value) is dict:
        if len(value) > MAX_CANONICAL_COLLECTION_ITEMS:
            raise ValueError(f"{path} has too many canonical JSON object fields")
        for key, member in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} has a non-string canonical JSON key")
            _utf8_text(key, f"{path} key", maximum=MAX_BODY, allow_empty=True)
            _validate_closed_json_v2(member, path=f"{path}.{key}", depth=depth + 1)
        return
    raise ValueError(f"{path} is not in the closed canonical JSON domain")


def canonical_json_v2(value: Any) -> bytes:
    """Serialize the closed V2 JSON domain with an explicit byte algorithm.

    The procedure intentionally does not delegate string escaping or integer
    spelling to a host JSON library: object keys are Unicode-scalar sorted,
    strings are UTF-8 with a fixed escape table, and the domain contains no
    floating point.  A conforming implementation in another language can
    therefore reproduce these bytes rather than merely hoping its local JSON
    serializer happens to agree with Python's defaults.
    """

    _validate_closed_json_v2(value)

    def encode_string(text: str) -> str:
        output = ['"']
        for character in text:
            codepoint = ord(character)
            if character == '"':
                output.append('\\"')
            elif character == "\\":
                output.append("\\\\")
            elif character == "\b":
                output.append("\\b")
            elif character == "\f":
                output.append("\\f")
            elif character == "\n":
                output.append("\\n")
            elif character == "\r":
                output.append("\\r")
            elif character == "\t":
                output.append("\\t")
            elif codepoint <= 0x1F:
                output.append(f"\\u{codepoint:04x}")
            else:
                output.append(character)
        output.append('"')
        return "".join(output)

    def encode(member: Any) -> str:
        if member is None:
            return "null"
        if type(member) is bool:
            return "true" if member else "false"
        if type(member) is int:
            return str(member)
        if type(member) is str:
            return encode_string(member)
        if type(member) is list:
            return "[" + ",".join(encode(item) for item in member) + "]"
        if type(member) is dict:
            return "{" + ",".join(
                encode_string(key) + ":" + encode(member[key]) for key in sorted(member)
            ) + "}"
        raise AssertionError("closed JSON validation must precede canonical serialization")

    return encode(value).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


PEER_POLICY_SHA256 = "sha256:" + sha256(canonical_json_v2(PEER_POLICY_PROJECTION))


def _identifier(value: Any, field: str, *, request_id: bool = False) -> str:
    expression = REQUEST_ID_RE if request_id else IDENTIFIER_RE
    if not isinstance(value, str) or not expression.fullmatch(value):
        raise ValueError(f"{field} must be a bounded identifier")
    return value


def _private_state_path(path: pathlib.Path) -> pathlib.Path:
    """Return a lexical absolute state path, rejecting every symlink component.

    ``Path.resolve()`` is deliberately not used here: resolving first would hide
    the fact that an operator supplied a symlink.  The durable profile accepts
    only a directly addressed private directory so its identity, secret and
    ledger cannot silently be redirected through another path.
    """

    raw = pathlib.Path(os.path.abspath(os.fspath(path)))
    current = pathlib.Path(raw.anchor)
    for component in raw.parts[1:]:
        current = current / component
        try:
            observed = os.lstat(current)
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(observed.st_mode):
            raise ValueError("terminal state path may not contain a symbolic link")
    return raw


def _private_regular_or_absent(path: pathlib.Path, description: str) -> None:
    """Fail closed if a durable state file is not a normal private file."""

    try:
        observed = os.lstat(path)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(observed.st_mode):
        raise ValueError(f"{description} may not be a symbolic link")
    if not stat.S_ISREG(observed.st_mode):
        raise ValueError(f"{description} must be a regular file")


def _header_values(headers: Mapping[str, Any], name: str) -> list[Any]:
    """Return all occurrences of one HTTP field without collapsing duplicates."""

    getter = getattr(headers, "get_all", None)
    if callable(getter):
        values = getter(name)
        return [] if values is None else list(values)
    expected = name.lower()
    return [value for key, value in headers.items() if isinstance(key, str) and key.lower() == expected]


def _singleton_header(headers: Mapping[str, Any], name: str, *, required: bool = False) -> str | None:
    """Read one unambiguous HTTP field, rejecting duplicate framing/binding data."""

    values = _header_values(headers, name)
    if not values:
        if required:
            raise ValueError(f"{name} header required")
        return None
    if len(values) != 1:
        raise ValueError(f"{name} header must occur exactly once")
    value = values[0]
    if not isinstance(value, str) or "\r" in value or "\n" in value:
        raise ValueError(f"{name} header is malformed")
    return value


def _json_object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build one JSON object only if every on-wire member name is unique."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON object contains a duplicate member name")
        result[key] = value
    return result


def _reject_nonfinite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value is forbidden: {value}")


def _atomic_write(path: pathlib.Path, data: bytes, *, mode: int = 0o600) -> None:
    """Write one private node-local state file atomically without a repo write."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("terminal state path may not be a symbolic link")
    fd, raw_temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = pathlib.Path(raw_temp)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def parse_sf_bytes(value: str) -> bytes:
    if len(value) < 2 or not (value.startswith(":") and value.endswith(":")):
        raise ValueError("Structured Field Byte Sequence required")
    try:
        return base64.b64decode(value[1:-1], validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("malformed Structured Field Byte Sequence") from exc


def parse_effect_ack_request(raw: str | None) -> dict[str, Any]:
    if raw is None or not raw.strip():
        raise ValueError("Effect-Ack-Request required")
    members: dict[str, str] = {}
    for item in raw.split(","):
        if "=" not in item:
            raise ValueError("malformed Effect-Ack-Request dictionary")
        key, value = item.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not SF_KEY.fullmatch(key) or key in members:
            raise ValueError("invalid or duplicate Effect-Ack-Request member")
        members[key] = value
    if set(members) - {"v", "mode", "token", "hash"}:
        raise ValueError("unknown Effect-Ack-Request member")
    try:
        version = int(members.get("v", ""))
    except ValueError as exc:
        raise ValueError("Effect-Ack-Request v must be an integer") from exc
    if version not in {1, 2}:
        raise ValueError("unsupported Effect-Ack-Request version")
    mode = members.get("mode")
    if mode not in {"prepare", "commit"}:
        raise ValueError("Effect-Ack-Request mode must be prepare or commit")
    if mode == "prepare":
        if set(members) != {"v", "mode"}:
            raise ValueError("prepare must not carry token or hash")
        return {"v": version, "mode": "prepare"}
    if set(members) != {"v", "mode", "token", "hash"}:
        raise ValueError("commit requires token and hash")
    token_bytes = parse_sf_bytes(members["token"])
    try:
        token = token_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("commit token must be ASCII") from exc
    hash_bytes = parse_sf_bytes(members["hash"])
    if len(hash_bytes) != 32:
        raise ValueError("commit hash must contain exactly 32 octets")
    return {"v": version, "mode": "commit", "token": token, "hash": hash_bytes.hex()}


def git_read(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
    except (OSError, subprocess.SubprocessError):
        return None


@dataclass
class Prepared:
    token: str
    input_hash: str
    record_hash: str
    expires_at: float
    used: bool = False
    request_id: str | None = None
    request_fingerprint: str | None = None
    binding: dict[str, Any] | None = None


class State:
    def __init__(self) -> None:
        self.secret = secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.prepared: dict[str, Prepared] = {}
        self.records: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []

    def record(
        self,
        *,
        state: str,
        input_hash: str,
        ordinary_release: bool,
        reason: str,
        wire_version: int = 1,
        policy_id: str = "QIKVRT_LOOPBACK_TERMINAL_V1",
        policy_version: int = 1,
        responsibility_owner: str = "LOCAL_INTERACTIVE_USER",
        request_id: str | None = None,
        request_fingerprint: str | None = None,
        node_binding: Mapping[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        if wire_version not in {1, 2}:
            raise ValueError("terminal record wire version is unsupported")
        body = {
            "schema": f"qikvrt_effect_ack_http_terminal_record_v{wire_version}",
            "wire_version": wire_version,
            "message_type": "effect-ack-record",
            "state": state,
            "input_hash": "sha256:" + input_hash,
            "policy_id": policy_id,
            "policy_version": policy_version,
            "policy_allows_release": ordinary_release,
            "ordinary_release": ordinary_release,
            "responsibility_owner": responsibility_owner,
            "reason": reason,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "external_effect": "NONE",
        }
        if wire_version == 2:
            if request_id is None or request_fingerprint is None or node_binding is None:
                raise ValueError("peer terminal record requires request and node bindings")
            body.update({
                "request_id": _identifier(request_id, "request_id", request_id=True),
                "request_fingerprint": "sha256:" + request_fingerprint,
                "node_binding": dict(node_binding),
            })
        encoder = canonical_json_v2 if wire_version == 2 else canonical_json
        digest = sha256(encoder(body))
        body["record_hash"] = "sha256:" + digest
        self.records[digest] = body
        return digest, body

    def make_token(self, input_hash: str, record_hash: str) -> str:
        nonce = secrets.token_bytes(24)
        expires = int(time.time()) + TOKEN_TTL_SECONDS
        payload = nonce + expires.to_bytes(8, "big") + bytes.fromhex(input_hash) + bytes.fromhex(record_hash)
        mac = hmac.new(self.secret, payload, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(payload + mac).decode("ascii").rstrip("=")
        self.prepared[token] = Prepared(token, input_hash, record_hash, float(expires))
        return token


class DurableState(State):
    """Node-local append-only terminal ledger used by the V2 peer profile.

    The HTTP exchange remains sessionless.  The only retained application
    state is the explicit, hash-linked prepare/commit/replay record required to
    prevent a duplicate effect after a daemon restart.
    """

    def __init__(self, state_dir: pathlib.Path, *, node_id: str, endpoint_id: str) -> None:
        super().__init__()
        self.state_dir = _private_state_path(state_dir)
        self.node_id = _identifier(node_id, "node_id")
        self.endpoint_id = _identifier(endpoint_id, "endpoint_id")
        self.ledger_path = self.state_dir / "terminal-ledger.jsonl"
        self.sequence = 0
        self.previous_record_hash: str | None = None
        self.peer_prepared_by_request: dict[str, str] = {}
        self.committed: dict[str, dict[str, Any]] = {}
        self._state_lock_fd: int | None = None
        try:
            self._initialize()
        except Exception:
            self.close()
            raise

    @property
    def persistent(self) -> bool:
        return True

    def _initialize(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        observed_dir = os.lstat(self.state_dir)
        if stat.S_ISLNK(observed_dir.st_mode) or not stat.S_ISDIR(observed_dir.st_mode):
            raise ValueError("terminal state path must be a directory without symbolic links")
        self._acquire_state_lock()
        identity_path = self.state_dir / "node.json"
        identity = {
            "schema": NODE_SCHEMA,
            "node_id": self.node_id,
            "endpoint_id": self.endpoint_id,
            "peer_policy_id": PEER_POLICY_ID,
            "peer_policy_sha256": PEER_POLICY_SHA256,
            "external_effect": "NONE",
        }
        _private_regular_or_absent(identity_path, "terminal node identity")
        if identity_path.exists():
            try:
                observed = json.loads(identity_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("terminal node identity is unreadable") from exc
            if observed != identity:
                raise ValueError("terminal state directory belongs to another node/profile")
        else:
            _atomic_write(identity_path, canonical_json_v2(identity) + b"\n")
        secret_path = self.state_dir / "node-secret.b64"
        _private_regular_or_absent(secret_path, "terminal node secret")
        if secret_path.exists():
            raw = secret_path.read_text(encoding="ascii").strip()
            try:
                secret = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
            except (ValueError, base64.binascii.Error) as exc:
                raise ValueError("terminal node secret is malformed") from exc
            canonical = base64.urlsafe_b64encode(secret).rstrip(b"=").decode("ascii")
            if len(secret) != 32 or not hmac.compare_digest(raw, canonical):
                raise ValueError("terminal node secret is non-canonical")
            self.secret = secret
        else:
            self.secret = secrets.token_bytes(32)
            encoded = base64.urlsafe_b64encode(self.secret).rstrip(b"=") + b"\n"
            _atomic_write(secret_path, encoded)
        self._load_ledger()

    def _acquire_state_lock(self) -> None:
        """Hold one non-blocking exclusive lock for the durable node lifetime."""

        if fcntl is None:
            raise ValueError("terminal durable state locking is unavailable on this platform")
        lock_path = self.state_dir / ".qikvrt-terminal-v2.lock"
        _private_regular_or_absent(lock_path, "terminal state lock")
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(lock_path, flags, 0o600)
        try:
            os.fchmod(fd, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in {errno.EACCES, errno.EAGAIN}:
                    raise ValueError("terminal state directory is already locked by a running daemon") from exc
                raise
        except Exception:
            os.close(fd)
            raise
        self._state_lock_fd = fd

    def close(self) -> None:
        """Release the durable state lock; normal process exit also releases it."""

        fd = self._state_lock_fd
        if fd is None:
            return
        self._state_lock_fd = None
        try:
            if fcntl is not None:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def __del__(self) -> None:  # pragma: no cover - explicit close owns normal lifecycle.
        try:
            self.close()
        except Exception:
            pass

    def _append(self, event: str, **payload: Any) -> None:
        _private_regular_or_absent(self.ledger_path, "terminal ledger")
        projection = {
            "schema": LEDGER_SCHEMA,
            "node_id": self.node_id,
            "endpoint_id": self.endpoint_id,
            "sequence": self.sequence + 1,
            "previous_record_sha256": self.previous_record_hash,
            "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            **payload,
        }
        record = {**projection, "record_sha256": sha256(canonical_json_v2(projection))}
        encoded = canonical_json_v2(record) + b"\n"
        created = not self.ledger_path.exists()
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.ledger_path, flags, 0o600)
        try:
            view = memoryview(encoded)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("terminal ledger append made no forward progress")
                view = view[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        if created:
            directory_fd = os.open(self.state_dir, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        self._apply(record)
        self.sequence = int(record["sequence"])
        self.previous_record_hash = str(record["record_sha256"])

    def _load_ledger(self) -> None:
        _private_regular_or_absent(self.ledger_path, "terminal ledger")
        if not self.ledger_path.exists():
            return
        try:
            raw = self.ledger_path.read_bytes()
            if raw and not raw.endswith(b"\n"):
                raise ValueError("terminal ledger has an unterminated final record")
            lines = raw.decode("utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError("terminal ledger is unreadable") from exc
        previous: str | None = None
        for expected_sequence, line in enumerate(lines, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("terminal ledger contains invalid JSON") from exc
            if not isinstance(record, dict):
                raise ValueError("terminal ledger record must be an object")
            stored_hash = record.get("record_sha256")
            projection = {key: value for key, value in record.items() if key != "record_sha256"}
            if (
                record.get("schema") != LEDGER_SCHEMA
                or record.get("node_id") != self.node_id
                or record.get("endpoint_id") != self.endpoint_id
                or record.get("sequence") != expected_sequence
                or record.get("previous_record_sha256") != previous
                or not isinstance(stored_hash, str)
                or not SHA256_RE.fullmatch(stored_hash)
                or sha256(canonical_json_v2(projection)) != stored_hash
            ):
                raise ValueError("terminal ledger integrity mismatch")
            self._apply(record)
            self.sequence = expected_sequence
            self.previous_record_hash = stored_hash
            previous = stored_hash

    def _apply(self, record: Mapping[str, Any]) -> None:
        event = record.get("event")
        if event == "RECORD":
            body = record.get("body")
            digest = record.get("record_digest")
            if not isinstance(body, dict) or not isinstance(digest, str):
                raise ValueError("terminal record ledger entry is malformed")
            if body.get("record_hash") != "sha256:" + digest:
                raise ValueError("terminal record self-binding mismatch")
            self.records[digest] = dict(body)
            return
        if event == "PREPARED":
            value = record.get("prepared")
            if not isinstance(value, dict):
                raise ValueError("terminal prepared ledger entry is malformed")
            required = {
                "token", "input_hash", "record_hash", "expires_at", "request_id",
                "request_fingerprint", "binding",
            }
            if set(value) != required:
                raise ValueError("terminal prepared ledger fields differ")
            token = value.get("token")
            input_hash = value.get("input_hash")
            record_hash = value.get("record_hash")
            request_id = value.get("request_id")
            fingerprint = value.get("request_fingerprint")
            expires_at = value.get("expires_at")
            binding = value.get("binding")
            if (
                not isinstance(token, str)
                or not isinstance(input_hash, str) or not SHA256_RE.fullmatch(input_hash)
                or not isinstance(record_hash, str) or not SHA256_RE.fullmatch(record_hash)
                or not isinstance(expires_at, int)
                or not isinstance(binding, dict)
            ):
                raise ValueError("terminal prepared ledger value is invalid")
            _identifier(request_id, "prepared request_id", request_id=True)
            if not isinstance(fingerprint, str) or not SHA256_RE.fullmatch(fingerprint):
                raise ValueError("terminal prepared request fingerprint is invalid")
            prepared = Prepared(
                token, input_hash, record_hash, float(expires_at), False,
                request_id, fingerprint, dict(binding),
            )
            prior = self.peer_prepared_by_request.get(request_id)
            if prior is not None and prior != token:
                raise ValueError("terminal request id has conflicting prepared tokens")
            self.prepared[token] = prepared
            self.peer_prepared_by_request[request_id] = token
            return
        if event == "COMMITTED":
            request_id = _identifier(record.get("request_id"), "committed request_id", request_id=True)
            fingerprint = record.get("request_fingerprint")
            token = record.get("token")
            response = record.get("response")
            if (
                not isinstance(fingerprint, str) or not SHA256_RE.fullmatch(fingerprint)
                or not isinstance(token, str) or not isinstance(response, dict)
            ):
                raise ValueError("terminal committed ledger entry is malformed")
            prepared = self.prepared.get(token)
            if prepared is None:
                raise ValueError("terminal committed entry has no prepared token")
            prepared.used = True
            committed = {"request_fingerprint": fingerprint, "token": token, "response": dict(response)}
            prior = self.committed.get(request_id)
            if prior is not None and prior != committed:
                raise ValueError("terminal request id has conflicting committed result")
            self.committed[request_id] = committed
            event_value = response.get("post_effect")
            if isinstance(event_value, dict):
                self.events.append(dict(event_value))
            return
        raise ValueError("terminal ledger event is unsupported")

    def record(self, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        digest, body = super().record(**kwargs)
        self._append("RECORD", record_digest=digest, body=body)
        return digest, body

    def prepare_peer(
        self,
        *,
        input_hash: str,
        record_hash: str,
        request_id: str,
        request_fingerprint: str,
        binding: Mapping[str, Any],
    ) -> Prepared:
        expires_at = int(time.time()) + TOKEN_TTL_SECONDS
        token_binding = {
            **dict(binding),
            "record_hash": "sha256:" + record_hash,
            "expires_at": expires_at,
        }
        token = base64.urlsafe_b64encode(
            hmac.new(self.secret, canonical_json_v2(token_binding), hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        prepared = Prepared(
            token, input_hash, record_hash, float(expires_at), False,
            request_id, request_fingerprint, token_binding,
        )
        self.prepared[token] = prepared
        self.peer_prepared_by_request[request_id] = token
        self._append(
            "PREPARED",
            prepared={
                "token": token,
                "input_hash": input_hash,
                "record_hash": record_hash,
                "expires_at": expires_at,
                "request_id": request_id,
                "request_fingerprint": request_fingerprint,
                "binding": token_binding,
            },
        )
        return prepared

    def token_matches(self, prepared: Prepared, token: str) -> bool:
        if prepared.binding is None:
            return False
        expected = base64.urlsafe_b64encode(
            hmac.new(self.secret, canonical_json_v2(prepared.binding), hashlib.sha256).digest()
        ).decode("ascii").rstrip("=")
        return hmac.compare_digest(expected, token) and hmac.compare_digest(prepared.token, token)

    def commit_peer(
        self,
        *,
        prepared: Prepared,
        request_id: str,
        request_fingerprint: str,
        response: Mapping[str, Any],
    ) -> None:
        if prepared.used:
            raise ValueError("prepared token is already used")
        self._append(
            "COMMITTED",
            request_id=request_id,
            request_fingerprint=request_fingerprint,
            token=prepared.token,
            response=dict(response),
        )


def validate_terminal_media_descriptor_v1(value: Any, *, expected_kind: str) -> dict[str, Any]:
    """Validate one closed media descriptor before it can enter a V2 hash."""

    required = {"schema", "kind", "content_type", "byte_length", "sha256", "base64"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("peer terminal media descriptor fields differ")
    if value.get("schema") != "qikvrt_terminal_media_descriptor_v1":
        raise ValueError("peer terminal media descriptor schema is unsupported")
    if value.get("kind") != expected_kind:
        raise ValueError("peer terminal media descriptor kind differs from its field")
    content_type = value.get("content_type")
    if not isinstance(content_type, str) or not MEDIA_CONTENT_TYPE_RE.fullmatch(content_type):
        raise ValueError("peer terminal media content type is non-canonical")
    if expected_kind == "audio" and not content_type.startswith("audio/"):
        raise ValueError("peer terminal audio descriptor requires an audio content type")
    if expected_kind == "video_snapshot" and not (
        content_type.startswith("image/") or content_type.startswith("video/")
    ):
        raise ValueError("peer terminal video snapshot descriptor requires an image or video content type")
    byte_length = value.get("byte_length")
    if type(byte_length) is not int or not 0 <= byte_length <= MAX_MEDIA_BYTES:
        raise ValueError("peer terminal media byte length is outside the closed integer range")
    digest = value.get("sha256")
    if not isinstance(digest, str) or not digest.startswith("sha256:") or not SHA256_RE.fullmatch(digest[7:]):
        raise ValueError("peer terminal media SHA-256 is malformed")
    encoded = value.get("base64")
    if not isinstance(encoded, str) or not CANONICAL_BASE64_RE.fullmatch(encoded):
        raise ValueError("peer terminal media base64 is non-canonical")
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("peer terminal media base64 is malformed") from exc
    if base64.b64encode(decoded).decode("ascii") != encoded:
        raise ValueError("peer terminal media base64 is not the canonical spelling")
    if len(decoded) != byte_length or sha256(decoded) != digest[7:]:
        raise ValueError("peer terminal media bytes do not match their exact descriptor")
    return dict(value)


def validate_terminal_input_v2(value: Any) -> dict[str, Any]:
    """Accept the V2 closed terminal-input JSON domain.

    V1 remains deliberately permissive for compatibility.  V2 instead permits
    only bounded UTF-8 strings, null media or a typed media descriptor whose
    length, canonical base64 spelling and SHA-256 exactly agree.  Floats,
    arrays and arbitrary nested objects cannot enter the canonical input hash.
    """

    required = {"schema", "submitted_at", "page", "text", "audio", "video"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("peer terminal input fields differ from the closed v2 frame")
    if value.get("schema") != "qikvrt_terminal_input_v2":
        raise ValueError("peer terminal input schema is unsupported")
    submitted_at = _utf8_text(value.get("submitted_at"), "peer terminal input submitted_at", maximum=24)
    if not RFC3339_MILLIS_UTC_RE.fullmatch(submitted_at):
        raise ValueError("peer terminal input submitted_at must be canonical UTC RFC3339 milliseconds")
    _utf8_text(value.get("page"), "peer terminal input page", maximum=2048)
    _utf8_text(value.get("text"), "peer terminal input text", maximum=4096)
    for field, expected_kind in (("audio", "audio"), ("video", "video_snapshot")):
        media = value.get(field)
        if media is not None:
            validate_terminal_media_descriptor_v1(media, expected_kind=expected_kind)
    result = dict(value)
    canonical_json_v2(result)
    return result


def parse_peer_envelope(
    body: Any,
    headers: Mapping[str, Any],
    state: DurableState,
    *,
    request_path: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Parse an exact V2 peer frame and return its stable commit intent.

    The delivery path is checked independently.  The intent is always bound to
    ``POST /terminal/commit`` so a successful prepare cannot be replayed at a
    different protected target or method.
    """

    required = {
        "schema", "request_id", "source_node_id", "target_node_id",
        "target_endpoint_id", "effective_method", "effective_target",
        "policy_id", "policy_sha256", "responsibility_owner", "terminal_input",
    }
    if not isinstance(body, dict) or set(body) != required:
        raise ValueError("peer terminal envelope fields differ")
    if body.get("schema") != "qikvrt_terminal_peer_request_v2":
        raise ValueError("peer terminal envelope schema is unsupported")
    request_id = _identifier(body.get("request_id"), "request_id", request_id=True)
    source_node_id = _identifier(body.get("source_node_id"), "source_node_id")
    target_node_id = _identifier(body.get("target_node_id"), "target_node_id")
    target_endpoint_id = _identifier(body.get("target_endpoint_id"), "target_endpoint_id")
    if source_node_id == target_node_id:
        raise ValueError("peer terminal source and target nodes must differ")
    if target_node_id != state.node_id or target_endpoint_id != state.endpoint_id:
        raise ValueError("peer terminal target is not this node endpoint")
    if body.get("effective_method") != "POST" or body.get("effective_target") != request_path:
        raise ValueError("peer terminal effective HTTP target does not match delivery")
    if body.get("policy_id") != PEER_POLICY_ID or body.get("policy_sha256") != PEER_POLICY_SHA256:
        raise ValueError("peer terminal policy binding differs")
    responsibility_owner = _utf8_text(
        body.get("responsibility_owner"), "peer terminal responsibility owner", maximum=256
    )
    header_bindings = {
        "Idempotency-Key": request_id,
        "X-QIKVRT-Source-Node": source_node_id,
        "X-QIKVRT-Target-Node": target_node_id,
        "X-QIKVRT-Target-Endpoint": target_endpoint_id,
    }
    for name, expected in header_bindings.items():
        if _singleton_header(headers, name, required=True) != expected:
            raise ValueError(f"peer terminal {name} header is absent or differs")
    terminal_input = validate_terminal_input_v2(body.get("terminal_input"))
    input_hash = sha256(canonical_json_v2(terminal_input))
    intent = {
        "request_id": request_id,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "target_endpoint_id": target_endpoint_id,
        "effective_method": "POST",
        "effective_target": "/terminal/commit",
        "request_content_sha256": "sha256:" + input_hash,
        "policy_id": PEER_POLICY_ID,
        "policy_sha256": PEER_POLICY_SHA256,
        "responsibility_owner": responsibility_owner,
    }
    return terminal_input, intent, sha256(canonical_json_v2(intent))


STATE = State()


class Handler(BaseHTTPRequestHandler):
    server_version = "QIKVRTEffectAckTerminal/2.0"

    @property
    def state(self) -> State:
        """Use an explicit server-local state instance; retain V1's global fallback."""

        return getattr(self.server, "qikvrt_state", STATE)

    def _json(
        self,
        code: int,
        body: dict[str, Any],
        *,
        state: str | None = None,
        record_hash: str | None = None,
        commit_token: str | None = None,
        wire_version: int = 1,
    ) -> None:
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "https://github.com")
        self.send_header("Access-Control-Expose-Headers", "Effect-Ack, Link")
        self.send_header("Link", "</.well-known/effect-ack>; rel=\"effect-ack\"; type=\"application/json\"")
        if state and record_hash:
            state_token = {
                "EFFECT_NACK": "nack",
                "EFFECT_ACK_CONTINUE": "continue",
                "EFFECT_ACK_DONE": "done",
                "EFFECT_ACK_ISOLATE": "isolate",
                "EFFECT_ACK_BLOCK": "block",
            }[state]
            value = f"v={wire_version}, state={state_token}, hash={sf_bytes(bytes.fromhex(record_hash))}"
            if commit_token is not None:
                value += f", token={sf_bytes(commit_token.encode('ascii'))}"
            self.send_header("Effect-Ack", value)
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self, *, closed_v2_json: bool = False) -> dict[str, Any]:
        if _header_values(self.headers, "Transfer-Encoding"):
            raise ValueError("Transfer-Encoding unsupported")
        raw_length = _singleton_header(self.headers, "Content-Length", required=True)
        assert raw_length is not None
        if not re.fullmatch(r"[0-9]+", raw_length):
            raise ValueError("Content-Length must be an unsigned decimal integer")
        length = int(raw_length)
        if length < 1 or length > MAX_BODY:
            raise ValueError("body outside bounded size")
        content_type = _singleton_header(self.headers, "Content-Type") or ""
        if content_type.split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("application/json required")
        raw_body = self.rfile.read(length).decode("utf-8")
        if closed_v2_json:
            value = json.loads(
                raw_body,
                object_pairs_hook=_json_object_without_duplicate_keys,
                parse_constant=_reject_nonfinite_json_constant,
            )
        else:
            value = json.loads(raw_body)
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "https://github.com")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Effect-Ack-Request, Idempotency-Key, X-QIKVRT-Source-Node, "
            "X-QIKVRT-Target-Node, X-QIKVRT-Target-Endpoint",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/.well-known/effect-ack":
            durable = isinstance(self.state, DurableState)
            body = {
                "schema": "qikvrt_effect_ack_http_capability_v1",
                "versions": [1, 2] if durable else [1],
                "modes": ["prepare", "commit"],
                "protected_effects": ["terminal_input"],
                "external_effects": "NONE",
                "record_template": "/effect-ack/records/{sha256}",
            }
            if durable:
                body["peer_profile"] = {
                    "schema": "qikvrt_terminal_peer_profile_v2",
                    "policy_id": PEER_POLICY_ID,
                    "policy_sha256": PEER_POLICY_SHA256,
                    "node_id": self.state.node_id,
                    "endpoint_id": self.state.endpoint_id,
                    "idempotency_header": "Idempotency-Key",
                    "transport_scope": "LOOPBACK_HTTP_ONLY",
                    "tls_mtls": "OPEN",
                    "external_effect": "NONE",
                }
            self._json(200, body)
            return
        if self.path == "/terminal/state":
            head = git_read("rev-parse", "HEAD")
            tree = git_read("rev-parse", "HEAD^{tree}")
            with self.state.lock:
                body = {
                    "schema": "qikvrt_terminal_backend_state_v1",
                    "events": len(self.state.events),
                    "last_event": self.state.events[-1] if self.state.events else None,
                    "repository_head": head,
                    "repository_tree": tree,
                    "external_effects": "NONE",
                    "persistence": "DURABLE_NODE_LOCAL_LEDGER" if isinstance(self.state, DurableState) else "PROCESS_MEMORY_ONLY",
                }
                if isinstance(self.state, DurableState):
                    body["node_id"] = self.state.node_id
                    body["endpoint_id"] = self.state.endpoint_id
                    body["ledger_sequence"] = self.state.sequence
            self._json(200, body)
            return
        prefix = "/effect-ack/records/"
        if self.path.startswith(prefix):
            digest = self.path[len(prefix):]
            with self.state.lock:
                body = self.state.records.get(digest)
            if body is None:
                self._json(404, {"state": "HOLD", "reason": "record not found"})
            else:
                self._json(
                    200,
                    body,
                    state=body["state"],
                    record_hash=digest,
                    wire_version=int(body.get("wire_version", 1)),
                )
            return
        self._json(404, {"state": "HOLD", "reason": "not found"})

    def do_POST(self) -> None:
        try:
            request_binding = parse_effect_ack_request(
                _singleton_header(self.headers, "Effect-Ack-Request", required=True)
            )
            body = self._read_body(closed_v2_json=request_binding["v"] == 2)
            if self.path == "/terminal/prepare":
                if request_binding["mode"] != "prepare":
                    raise ValueError("prepare endpoint requires mode=prepare")
                self._prepare(body, request_binding)
                return
            if self.path == "/terminal/commit":
                if request_binding["mode"] != "commit":
                    raise ValueError("commit endpoint requires mode=commit")
                self._commit(body, request_binding)
                return
            self._json(404, {"state": "HOLD", "reason": "not found"})
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self._json(400, {"state": "HOLD", "ordinary_release": False, "reason": str(exc)})

    def _prepare(self, body: dict[str, Any], binding: dict[str, Any]) -> None:
        if binding["v"] == 2:
            self._prepare_peer_v2(body)
            return
        if body.get("schema") != "qikvrt_terminal_input_v1":
            digest, record = self.state.record(
                state="EFFECT_ACK_BLOCK",
                input_hash=sha256(canonical_json(body)),
                ordinary_release=False,
                reason="unsupported terminal schema",
            )
            self._json(422, {"record": record, "record_hash": digest}, state=record["state"], record_hash=digest)
            return
        input_hash = sha256(canonical_json(body))
        with self.state.lock:
            digest, record = self.state.record(
                state="EFFECT_ACK_DONE",
                input_hash=input_hash,
                ordinary_release=True,
                reason="loopback terminal input satisfies bounded local policy",
            )
            token = self.state.make_token(input_hash, digest)
        response = {
            "state": "EFFECT_ACK_DONE",
            "ordinary_release": False,
            "commit_token": token,
            "record_hash": digest,
            "record_url": f"/effect-ack/records/{digest}",
            "expires_in_seconds": TOKEN_TTL_SECONDS,
            "external_effect": "NONE",
        }
        self._json(200, response, state="EFFECT_ACK_DONE", record_hash=digest, commit_token=token)

    def _peer_conflict(self, reason: str) -> None:
        self._json(
            409,
            {
                "schema": "qikvrt_terminal_peer_result_v2",
                "state": "HOLD",
                "ordinary_release": False,
                "reason": reason,
                "external_effect": "NONE",
            },
        )

    def _peer_prepare_response(
        self,
        *,
        prepared: Prepared,
        request_id: str,
        request_fingerprint: str,
    ) -> dict[str, Any]:
        return {
            "schema": "qikvrt_terminal_prepare_v2",
            "wire_version": 2,
            "state": "EFFECT_ACK_DONE",
            "ordinary_release": False,
            "idempotency_key": request_id,
            "request_fingerprint": "sha256:" + request_fingerprint,
            "commit_token": prepared.token,
            "record_hash": prepared.record_hash,
            "record_url": f"/effect-ack/records/{prepared.record_hash}",
            "expires_at_unix": int(prepared.expires_at),
            "external_effect": "NONE",
        }

    def _prepare_peer_v2(self, body: dict[str, Any]) -> None:
        if not isinstance(self.state, DurableState):
            self._peer_conflict("peer profile requires durable node-local state")
            return
        terminal_input, intent, fingerprint = parse_peer_envelope(
            body, self.headers, self.state, request_path="/terminal/prepare"
        )
        request_id = intent["request_id"]
        input_hash = sha256(canonical_json_v2(terminal_input))
        with self.state.lock:
            committed = self.state.committed.get(request_id)
            if committed is not None:
                if not hmac.compare_digest(committed["request_fingerprint"], fingerprint):
                    self._peer_conflict("Idempotency-Key is already bound to different peer input")
                else:
                    self._peer_conflict("Idempotency-Key is already committed; replay commit to reobserve")
                return
            existing_token = self.state.peer_prepared_by_request.get(request_id)
            if existing_token is not None:
                prepared = self.state.prepared.get(existing_token)
                if prepared is None:
                    self._peer_conflict("persisted prepare binding is unavailable")
                    return
                if not hmac.compare_digest(prepared.request_fingerprint or "", fingerprint):
                    self._peer_conflict("Idempotency-Key is already bound to different peer input")
                    return
                if prepared.expires_at < time.time():
                    self._peer_conflict("persisted prepare token expired; use a new Idempotency-Key")
                    return
            else:
                digest, _ = self.state.record(
                    state="EFFECT_ACK_DONE",
                    input_hash=input_hash,
                    ordinary_release=True,
                    reason="durable peer prepare satisfies bounded local policy; commit remains required",
                    wire_version=2,
                    policy_id=PEER_POLICY_ID,
                    policy_version=2,
                    responsibility_owner=intent["responsibility_owner"],
                    request_id=request_id,
                    request_fingerprint=fingerprint,
                    node_binding=intent,
                )
                prepared = self.state.prepare_peer(
                    input_hash=input_hash,
                    record_hash=digest,
                    request_id=request_id,
                    request_fingerprint=fingerprint,
                    binding=intent,
                )
            response = self._peer_prepare_response(
                prepared=prepared,
                request_id=request_id,
                request_fingerprint=fingerprint,
            )
        self._json(
            200,
            response,
            state="EFFECT_ACK_DONE",
            record_hash=prepared.record_hash,
            commit_token=prepared.token,
            wire_version=2,
        )

    def _commit(self, body: dict[str, Any], binding: dict[str, Any]) -> None:
        if binding["v"] == 2:
            self._commit_peer_v2(body, binding)
            return
        token = binding["token"]
        record_hash = binding["hash"]
        commit_input_hash = sha256(canonical_json(body))
        with self.state.lock:
            prepared = self.state.prepared.get(token)
            if prepared is None or prepared.used or prepared.expires_at < time.time() or not hmac.compare_digest(prepared.record_hash, record_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "invalid stale used or mismatched token"})
                return
            if not hmac.compare_digest(prepared.input_hash, commit_input_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "commit payload differs from exact prepared payload"})
                return
            prepared.used = True
            event = {
                "event_id": len(self.state.events) + 1,
                "kind": "TERMINAL_INPUT_ACCEPTED",
                "record_hash": record_hash,
                "input_hash": commit_input_hash,
                "text": str(body.get("text", ""))[:4096],
                "audio_present": body.get("audio") is not None,
                "video_present": body.get("video") is not None,
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "external_effect": "NONE",
            }
            self.state.events.append(event)
            digest, record = self.state.record(
                state="EFFECT_ACK_DONE",
                input_hash=prepared.input_hash,
                ordinary_release=True,
                reason="single-use exact-bound loopback commit executed",
            )
        self._json(
            200,
            {"state": "EFFECT_ACK_DONE", "ordinary_release": True, "post_effect": event, "successor_record": record},
            state="EFFECT_ACK_DONE",
            record_hash=digest,
        )

    def _commit_peer_v2(self, body: dict[str, Any], binding: dict[str, Any]) -> None:
        if not isinstance(self.state, DurableState):
            self._peer_conflict("peer profile requires durable node-local state")
            return
        terminal_input, intent, fingerprint = parse_peer_envelope(
            body, self.headers, self.state, request_path="/terminal/commit"
        )
        request_id = intent["request_id"]
        token = binding["token"]
        record_hash = binding["hash"]
        commit_input_hash = sha256(canonical_json_v2(terminal_input))
        with self.state.lock:
            committed = self.state.committed.get(request_id)
            if committed is not None:
                if not hmac.compare_digest(committed["request_fingerprint"], fingerprint):
                    self._peer_conflict("Idempotency-Key is already bound to different peer input")
                    return
                if not hmac.compare_digest(committed["token"], token):
                    self._peer_conflict("Idempotency-Key replay token differs from committed token")
                    return
                response = {**committed["response"], "replayed": True}
                successor = response.get("successor_record")
                if not isinstance(successor, dict) or not isinstance(successor.get("record_hash"), str):
                    self._peer_conflict("persisted commit receipt is malformed")
                    return
                successor_hash = successor["record_hash"].removeprefix("sha256:")
                if not SHA256_RE.fullmatch(successor_hash):
                    self._peer_conflict("persisted commit receipt hash is malformed")
                    return
                self._json(
                    200,
                    response,
                    state="EFFECT_ACK_DONE",
                    record_hash=successor_hash,
                    wire_version=2,
                )
                return
            prepared = self.state.prepared.get(token)
            if prepared is None or prepared.used:
                self._peer_conflict("invalid stale or used peer commit token")
                return
            if prepared.expires_at < time.time():
                self._peer_conflict("peer commit token expired")
                return
            if not hmac.compare_digest(prepared.record_hash, record_hash):
                self._peer_conflict("peer commit record hash differs from prepared binding")
                return
            if not hmac.compare_digest(prepared.input_hash, commit_input_hash):
                self._peer_conflict("peer commit payload differs from exact prepared payload")
                return
            if (
                not hmac.compare_digest(prepared.request_id or "", request_id)
                or not hmac.compare_digest(prepared.request_fingerprint or "", fingerprint)
            ):
                self._peer_conflict("peer commit request binding differs from prepare")
                return
            expected_binding = {
                **intent,
                "record_hash": "sha256:" + record_hash,
                "expires_at": int(prepared.expires_at),
            }
            if prepared.binding != expected_binding or not self.state.token_matches(prepared, token):
                self._peer_conflict("peer commit token is not bound to this method target policy and node")
                return
            event = {
                "event_id": len(self.state.events) + 1,
                "kind": "TERMINAL_INPUT_ACCEPTED",
                "idempotency_key": request_id,
                "source_node_id": intent["source_node_id"],
                "target_node_id": intent["target_node_id"],
                "target_endpoint_id": intent["target_endpoint_id"],
                "record_hash": record_hash,
                "input_hash": commit_input_hash,
                "text": terminal_input["text"],
                "audio_present": terminal_input["audio"] is not None,
                "video_present": terminal_input["video"] is not None,
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "external_effect": "NONE",
            }
            digest, record = self.state.record(
                state="EFFECT_ACK_DONE",
                input_hash=prepared.input_hash,
                ordinary_release=True,
                reason="single-use exact-bound durable local peer commit recorded",
                wire_version=2,
                policy_id=PEER_POLICY_ID,
                policy_version=2,
                responsibility_owner=intent["responsibility_owner"],
                request_id=request_id,
                request_fingerprint=fingerprint,
                node_binding=intent,
            )
            response = {
                "schema": "qikvrt_terminal_peer_result_v2",
                "wire_version": 2,
                "state": "EFFECT_ACK_DONE",
                "ordinary_release": True,
                "idempotency_key": request_id,
                "request_fingerprint": "sha256:" + fingerprint,
                "node_binding": intent,
                "post_effect": event,
                "successor_record": record,
                "external_effect": "NONE",
            }
            self.state.commit_peer(
                prepared=prepared,
                request_id=request_id,
                request_fingerprint=fingerprint,
                response=response,
            )
        self._json(
            200,
            response,
            state="EFFECT_ACK_DONE",
            record_hash=digest,
            wire_version=2,
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--state-dir",
        type=pathlib.Path,
        help="private node-local durable ledger directory; enables the V2 peer profile",
    )
    parser.add_argument("--node-id", default="qikvrt-loopback-node")
    parser.add_argument("--endpoint-id", default="qikvrt-loopback-endpoint")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: reference terminal bridge is loopback-only")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    if args.state_dir is not None:
        server.qikvrt_state = DurableState(
            args.state_dir,
            node_id=args.node_id,
            endpoint_id=args.endpoint_id,
        )
    else:
        server.qikvrt_state = State()
    state = server.qikvrt_state
    print(
        json.dumps(
            {
                "state": "READY",
                "host": args.host,
                "port": args.port,
                "persistence": "DURABLE_NODE_LOCAL_LEDGER" if isinstance(state, DurableState) else "PROCESS_MEMORY_ONLY",
                "node_id": state.node_id if isinstance(state, DurableState) else None,
                "endpoint_id": state.endpoint_id if isinstance(state, DurableState) else None,
                "external_effects": "NONE",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if isinstance(state, DurableState):
            state.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
