#!/usr/bin/env python3
"""Fail-closed EFFECT_ACK live serialization and loopback REST adapter."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import threading
from collections.abc import Mapping, Sequence
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

PROTOCOL_VERSION = "effect-ack-v1"
PROFILE_VERSION = "qikvrt-repository-live-v1"
EFFECT_STATES = {
    "REQUEST_RECEIVED", "AUTHORIZATION_CHECKED", "WORK_STARTED",
    "EFFECT_ACK_CONTINUE", "BLOCK", "STALL",
    "COMPLETION_CANDIDATE", "PAIR_ACKNOWLEDGED",
}
GATE_STATES = {
    "pending", "running", "success", "failure", "action_required",
    "cancelled", "skipped", "not_applicable",
}
COMPLETION_STATES = {"COMPLETION_CANDIDATE", "PAIR_ACKNOWLEDGED"}
BLOCKING_STATES = {"BLOCK", "STALL"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:=-]{1,128}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_BODY_BYTES = 1024 * 1024


class ProtocolError(ValueError):
    pass


class CausalConflict(ProtocolError):
    pass


class NotFound(ProtocolError):
    pass


class RestError(RuntimeError):
    def __init__(self, status: int, payload: Mapping[str, Any]):
        super().__init__(f"HTTP {status}: {payload}")
        self.status = status
        self.payload = dict(payload)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProtocolError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ProtocolError(f"{label} must be a non-empty string")
    if identifier and IDENTIFIER.fullmatch(value) is None:
        raise ProtocolError(f"{label} is not a bounded identifier")
    return value


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ProtocolError(f"{label} must be an array")
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        text = _string(item, f"{label}[{index}]")
        if text in seen:
            raise ProtocolError(f"{label} contains duplicate {text!r}")
        seen.add(text)
        result.append(text)
    return result


def active_remainder(requirements: Sequence[str], closed_verified: Sequence[str]) -> list[str]:
    """Return the order-preserving complement requirements minus closed_verified."""
    closed = set(closed_verified)
    return [item for item in requirements if item not in closed]


def _validate_node(value: Any, label: str) -> dict[str, str]:
    node = _object(value, label)
    if set(node) != {"repository", "head", "tree"}:
        raise ProtocolError(f"{label} must contain exactly repository/head/tree")
    repository = _string(node["repository"], f"{label}.repository")
    head = _string(node["head"], f"{label}.head")
    tree = _string(node["tree"], f"{label}.tree")
    if REPOSITORY.fullmatch(repository) is None:
        raise ProtocolError(f"{label}.repository is invalid")
    if HEX40.fullmatch(head) is None or HEX40.fullmatch(tree) is None:
        raise ProtocolError(f"{label} head/tree must be lowercase 40-hex Git identities")
    return {"repository": repository, "head": head, "tree": tree}


def _validate_causal(value: Any) -> dict[str, str | None]:
    causal = _object(value, "causal")
    expected = {"transaction_id", "observation_id", "predecessor_id"}
    if set(causal) != expected:
        raise ProtocolError("causal must contain exactly transaction_id/observation_id/predecessor_id")
    transaction = _string(causal["transaction_id"], "causal.transaction_id", identifier=True)
    observation = _string(causal["observation_id"], "causal.observation_id", identifier=True)
    predecessor = causal["predecessor_id"]
    if predecessor is not None:
        predecessor = _string(predecessor, "causal.predecessor_id", identifier=True)
        if predecessor == observation:
            raise ProtocolError("an observation cannot name itself as predecessor")
    return {"transaction_id": transaction, "observation_id": observation, "predecessor_id": predecessor}


def _validate_gates(value: Any) -> dict[str, str]:
    gates = _object(value, "mandatory_gates")
    result: dict[str, str] = {}
    for raw_name, raw_state in gates.items():
        name = _string(raw_name, "mandatory_gates key")
        state = _string(raw_state, f"mandatory_gates[{name!r}]")
        if state not in GATE_STATES:
            raise ProtocolError(f"mandatory_gates[{name!r}] has unknown state {state!r}")
        result[name] = state
    return result


def _validate_closure(value: Any) -> dict[str, list[str]]:
    closure = _object(value, "closure")
    expected_keys = {"requirements", "closed_verified", "active_remainder"}
    if set(closure) != expected_keys:
        raise ProtocolError("closure must contain exactly requirements/closed_verified/active_remainder")
    requirements = _unique_strings(closure["requirements"], "closure.requirements")
    closed = _unique_strings(closure["closed_verified"], "closure.closed_verified")
    unknown = [item for item in closed if item not in requirements]
    if unknown:
        raise ProtocolError(f"closed_verified is not a subset of requirements: {unknown}")
    observed = _unique_strings(closure["active_remainder"], "closure.active_remainder")
    expected = active_remainder(requirements, closed)
    if observed != expected:
        raise ProtocolError("closure.active_remainder is not the exact order-preserving complement")
    return {"requirements": requirements, "closed_verified": closed, "active_remainder": observed}


def validate_frame(raw: Mapping[str, Any]) -> dict[str, Any]:
    frame = _object(raw, "frame")
    expected = {
        "protocol_version", "profile_version", "sequence", "authority", "mirror",
        "candidate", "effect_state", "causal", "mandatory_gates", "evidence_refs",
        "reason_codes", "next_possible_step", "observed_at", "closure",
    }
    if set(frame) != expected:
        raise ProtocolError(
            f"frame keys differ; missing={sorted(expected-set(frame))}, extra={sorted(set(frame)-expected)}"
        )
    if frame["protocol_version"] != PROTOCOL_VERSION:
        raise ProtocolError("unsupported protocol_version")
    if frame["profile_version"] != PROFILE_VERSION:
        raise ProtocolError("unsupported profile_version")
    sequence = frame["sequence"]
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise ProtocolError("sequence must be a non-negative integer")
    authority = _validate_node(frame["authority"], "authority")
    mirror = None if frame["mirror"] is None else _validate_node(frame["mirror"], "mirror")
    candidate = _validate_node(frame["candidate"], "candidate")
    effect_state = _string(frame["effect_state"], "effect_state")
    if effect_state not in EFFECT_STATES:
        raise ProtocolError(f"unknown effect_state {effect_state!r}")
    causal = _validate_causal(frame["causal"])
    gates = _validate_gates(frame["mandatory_gates"])
    evidence = _unique_strings(frame["evidence_refs"], "evidence_refs")
    reasons = _unique_strings(frame["reason_codes"], "reason_codes")
    next_step = _string(frame["next_possible_step"], "next_possible_step")
    observed_at = _string(frame["observed_at"], "observed_at")
    closure = _validate_closure(frame["closure"])
    if effect_state in COMPLETION_STATES and closure["active_remainder"]:
        raise ProtocolError("completion state is forbidden while active_remainder is non-empty")
    if effect_state in BLOCKING_STATES and not reasons:
        raise ProtocolError("BLOCK/STALL requires at least one reason_code")
    return {
        "protocol_version": PROTOCOL_VERSION,
        "profile_version": PROFILE_VERSION,
        "sequence": sequence,
        "authority": authority,
        "mirror": mirror,
        "candidate": candidate,
        "effect_state": effect_state,
        "causal": causal,
        "mandatory_gates": gates,
        "evidence_refs": evidence,
        "reason_codes": reasons,
        "next_possible_step": next_step,
        "observed_at": observed_at,
        "closure": closure,
    }


def encode_frame(snapshot: Mapping[str, Any], sequence: int) -> dict[str, Any]:
    source = _object(snapshot, "snapshot")
    closure = _object(source.get("closure"), "closure")
    requirements = _unique_strings(closure.get("requirements"), "closure.requirements")
    closed = _unique_strings(closure.get("closed_verified"), "closure.closed_verified")
    wire = dict(source)
    wire["protocol_version"] = PROTOCOL_VERSION
    wire["profile_version"] = PROFILE_VERSION
    wire["sequence"] = sequence
    wire["closure"] = {
        "requirements": requirements,
        "closed_verified": closed,
        "active_remainder": active_remainder(requirements, closed),
    }
    return validate_frame(wire)


def decode_frame(frame: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_frame(frame)
    snapshot = dict(normalized)
    snapshot.pop("protocol_version")
    snapshot.pop("profile_version")
    snapshot.pop("sequence")
    closure = dict(snapshot["closure"])
    closure.pop("active_remainder")
    snapshot["closure"] = closure
    return snapshot


def canonical_bytes(frame: Mapping[str, Any]) -> bytes:
    return json.dumps(validate_frame(frame), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def snapshot_sha256(frame: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(frame)).hexdigest()


def build_delta(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    left = validate_frame(previous)
    right = validate_frame(current)
    lcausal, rcausal = left["causal"], right["causal"]
    if lcausal["transaction_id"] != rcausal["transaction_id"]:
        raise CausalConflict("observations belong to different transactions")
    if rcausal["predecessor_id"] != lcausal["observation_id"]:
        raise CausalConflict("current frame is not causally linked to previous observation")
    lsnapshot, rsnapshot = decode_frame(left), decode_frame(right)
    changed = sorted(key for key in rsnapshot if lsnapshot.get(key) != rsnapshot.get(key))
    return {
        "protocol_version": PROTOCOL_VERSION,
        "profile_version": PROFILE_VERSION,
        "transaction_id": rcausal["transaction_id"],
        "previous_observation_id": lcausal["observation_id"],
        "observation_id": rcausal["observation_id"],
        "causal_predecessor_valid": True,
        "changed_fields": changed,
        "effect_state": right["effect_state"],
        "active_remainder": list(right["closure"]["active_remainder"]),
        "current_snapshot_sha256": snapshot_sha256(right),
    }


class LiveStore:
    def __init__(self) -> None:
        self._history: dict[str, list[dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def accept(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        frame = validate_frame(raw)
        causal = frame["causal"]
        transaction, observation = causal["transaction_id"], causal["observation_id"]
        with self._lock:
            history = self._history.setdefault(transaction, [])
            for existing in history:
                if existing["causal"]["observation_id"] == observation:
                    if canonical_bytes(existing) != canonical_bytes(frame):
                        raise CausalConflict("observation_id replayed with different bytes")
                    return self._receipt(existing, True)
            if not history and causal["predecessor_id"] is not None:
                raise CausalConflict("first observation must have predecessor_id=null")
            if history:
                expected = history[-1]["causal"]["observation_id"]
                if causal["predecessor_id"] != expected:
                    raise CausalConflict(f"predecessor mismatch: expected {expected!r}")
            history.append(frame)
            return self._receipt(frame, False)

    @staticmethod
    def _receipt(frame: Mapping[str, Any], idempotent: bool) -> dict[str, Any]:
        causal = frame["causal"]
        return {
            "transport_ack": True,
            "completion_inferred": False,
            "effect_state": frame["effect_state"],
            "transaction_id": causal["transaction_id"],
            "observation_id": causal["observation_id"],
            "snapshot_sha256": snapshot_sha256(frame),
            "active_remainder": list(frame["closure"]["active_remainder"]),
            "idempotent": idempotent,
        }

    def current(self, transaction: str) -> dict[str, Any]:
        with self._lock:
            history = self._history.get(transaction)
            if not history:
                raise NotFound(f"unknown transaction {transaction!r}")
            return copy.deepcopy(history[-1])

    def delta(self, transaction: str, after: str) -> dict[str, Any]:
        with self._lock:
            history = self._history.get(transaction)
            if not history:
                raise NotFound(f"unknown transaction {transaction!r}")
            for index, frame in enumerate(history):
                if frame["causal"]["observation_id"] == after:
                    if index + 1 >= len(history):
                        raise NotFound(f"no successor after observation {after!r}")
                    return build_delta(frame, history[index + 1])
            raise NotFound(f"unknown observation {after!r}")


class _Handler(BaseHTTPRequestHandler):
    store: LiveStore

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send(self, status: int, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, code: str, detail: str) -> None:
        self._send(status, {"error": code, "detail": detail})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/effect-ack/v1/observations":
            self._error(404, "NOT_FOUND", "unknown endpoint")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValueError("invalid Content-Length")
            payload = json.loads(self.rfile.read(length).decode())
            receipt = self.store.accept(_object(payload, "request body"))
        except CausalConflict as exc:
            self._error(409, "CAUSAL_CONFLICT", str(exc)); return
        except ProtocolError as exc:
            self._error(422, "FRAME_REJECTED", str(exc)); return
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._error(400, "MALFORMED_REQUEST", str(exc)); return
        self._send(202, receipt)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(200, {"status": "ALIVE", "protocol_version": PROTOCOL_VERSION, "profile_version": PROFILE_VERSION})
            return
        match = re.fullmatch(r"/effect-ack/v1/snapshots/([A-Za-z0-9_.:=-]{1,128})(/delta)?", parsed.path)
        if match is None:
            self._error(404, "NOT_FOUND", "unknown endpoint"); return
        transaction = match.group(1)
        try:
            if match.group(2):
                values = parse_qs(parsed.query).get("after", [])
                if len(values) != 1 or IDENTIFIER.fullmatch(values[0]) is None:
                    raise ProtocolError("delta requires one bounded after observation id")
                payload = self.store.delta(transaction, values[0])
            else:
                payload = self.store.current(transaction)
        except NotFound as exc:
            self._error(404, "NOT_FOUND", str(exc)); return
        except CausalConflict as exc:
            self._error(409, "CAUSAL_CONFLICT", str(exc)); return
        except ProtocolError as exc:
            self._error(422, "REQUEST_REJECTED", str(exc)); return
        self._send(200, payload)


def make_server(host: str = "127.0.0.1", port: int = 8767, store: LiveStore | None = None) -> ThreadingHTTPServer:
    if host != "127.0.0.1":
        raise ProtocolError("reference adapter is loopback-only")
    bound_store = store or LiveStore()

    class Handler(_Handler):
        pass

    Handler.store = bound_store
    return ThreadingHTTPServer((host, port), Handler)


class EffectAckClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base_url + path, data=body, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return _object(json.loads(response.read().decode()), "response")
        except HTTPError as exc:
            try:
                error_payload = _object(json.loads(exc.read().decode()), "error response")
            except Exception:
                error_payload = {"error": "HTTP_ERROR", "detail": str(exc)}
            raise RestError(exc.code, error_payload) from exc

    def post_observation(self, frame: Mapping[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/effect-ack/v1/observations", frame)

    def get_snapshot(self, transaction: str) -> dict[str, Any]:
        _string(transaction, "transaction", identifier=True)
        return self._request("GET", f"/effect-ack/v1/snapshots/{quote(transaction)}")

    def get_delta(self, transaction: str, after: str) -> dict[str, Any]:
        _string(transaction, "transaction", identifier=True)
        _string(after, "after", identifier=True)
        return self._request("GET", f"/effect-ack/v1/snapshots/{quote(transaction)}/delta?after={quote(after)}")


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8767)
    validate = sub.add_parser("validate")
    validate.add_argument("frame", type=Path)
    args = parser.parse_args(argv)
    if args.command == "serve":
        server = make_server(args.host, args.port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    payload = json.loads(args.frame.read_text(encoding="utf-8"))
    print(json.dumps(validate_frame(_object(payload, "frame")), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
