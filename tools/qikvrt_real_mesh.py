#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Execute a bounded event-driven QIK-VRT multi-pair mesh over real TCP sockets.

The runtime is deliberately smaller than a production deployment, but it is
not a static topology projection: four independent node processes bind four
loopback TCP listeners, relay exact canonical envelopes across two distinct
Authority/Mirror pairs, return the acknowledgement through the route, persist
hash-linked node-local ledgers, survive a node restart, and reobserve every
hop before a bounded Effect-Acknowledgement may be emitted.

The network boundary is loopback-only. Diverged repository trees remain an
observed state and never authorize synchronization, merge, publication, or any
other external effect.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import pathlib
import queue
import re
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.qikvrt_effect_ack import (  # noqa: E402
    ConnectionDecision,
    EffectAckEngine,
    EffectAckRequest,
    EffectState,
    RiskLevel,
    sha256_identifier,
)
from src.qikvrt_deterministic_admission import (  # noqa: E402
    DeterministicDisposition,
    deterministic_disposition,
)

MESH_ID = "QIKVRT_REAL_MULTI_PAIR_MESH_V1"
TOPOLOGY_SCHEMA = "qikvrt_real_mesh_topology_v1"
MESSAGE_SCHEMA = "qikvrt_real_mesh_message_v1"
HOP_RECEIPT_SCHEMA = "qikvrt_real_mesh_hop_receipt_v1"
TERMINAL_RECEIPT_SCHEMA = "qikvrt_real_mesh_terminal_receipt_v1"
HOLD_SCHEMA = "qikvrt_real_mesh_hold_v1"
LEDGER_RECORD_SCHEMA = "qikvrt_real_mesh_ledger_record_v1"
EXECUTION_RECEIPT_SCHEMA = "qikvrt_real_mesh_execution_receipt_v1"
NETWORK_SCOPE = "LOOPBACK_TCP_ONLY"
EFFECT_ACK_SCOPE = "BOUNDED_LOOPBACK_MULTI_PAIR_MESSAGE_DELIVERY_ONLY"
MAX_FRAME_BYTES = 1024 * 1024
MAX_NODES = 16
MIN_PAIR_COUNT = 2
SOCKET_TIMEOUT_SECONDS = 3.0
PROCESS_READY_TIMEOUT_SECONDS = 10.0
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class MeshRuntimeError(ValueError):
    """A fail-closed mesh contract violation."""


class MeshTransportError(RuntimeError):
    """A bounded transport or process-liveness failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _normalize_json(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        raise MeshRuntimeError("floating-point values are not canonical mesh JSON")
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise MeshRuntimeError("mesh JSON object keys must be strings")
            if key in result:
                raise MeshRuntimeError("duplicate mesh JSON key")
            result[key] = _normalize_json(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item) for item in value]
    raise MeshRuntimeError(f"unsupported mesh JSON value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalize_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return sha256_identifier(canonical_json_bytes(value))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MeshRuntimeError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], required: set[str], label: str) -> None:
    if set(value) != required:
        raise MeshRuntimeError(f"{label} must contain exactly {sorted(required)}")


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER_RE.fullmatch(value):
        raise MeshRuntimeError(f"{label} must be a bounded identifier")
    return value


def _text(value: Any, label: str, *, max_chars: int = 1024) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > max_chars
        or any(ord(ch) < 32 for ch in value)
    ):
        raise MeshRuntimeError(f"{label} must be bounded non-control text")
    return value


def _sha1(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA1_RE.fullmatch(value):
        raise MeshRuntimeError(f"{label} must be a lowercase Git SHA-1")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise MeshRuntimeError(f"{label} must be a canonical sha256 reference")
    return value


def _port(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 65535:
        raise MeshRuntimeError(f"{label} must be an integer TCP port")
    return value


def normalize_node(value: Any, label: str = "node") -> dict[str, Any]:
    node = _mapping(value, label)
    _exact_keys(
        node,
        {
            "node_id",
            "pair_id",
            "role",
            "repository",
            "instance_id",
            "root_tree_sha",
            "host",
            "port",
        },
        label,
    )
    role = node["role"]
    if role not in {"AUTHORITY", "MIRROR"}:
        raise MeshRuntimeError(f"{label}.role must be AUTHORITY or MIRROR")
    repository = _text(node["repository"], f"{label}.repository", max_chars=256)
    if repository.count("/") != 1 or repository.startswith("/") or repository.endswith("/"):
        raise MeshRuntimeError(f"{label}.repository must be owner/name")
    host = node["host"]
    if host != "127.0.0.1":
        raise MeshRuntimeError(f"{label}.host must be 127.0.0.1")
    return {
        "node_id": _identifier(node["node_id"], f"{label}.node_id"),
        "pair_id": _identifier(node["pair_id"], f"{label}.pair_id"),
        "role": role,
        "repository": repository,
        "instance_id": _identifier(node["instance_id"], f"{label}.instance_id"),
        "root_tree_sha": _sha1(node["root_tree_sha"], f"{label}.root_tree_sha"),
        "host": host,
        "port": _port(node["port"], f"{label}.port"),
    }


def _normalize_link(value: Any, node_ids: set[str], label: str) -> tuple[str, str]:
    if not isinstance(value, list) or len(value) != 2:
        raise MeshRuntimeError(f"{label} must be a two-node list")
    left = _identifier(value[0], f"{label}[0]")
    right = _identifier(value[1], f"{label}[1]")
    if left == right:
        raise MeshRuntimeError(f"{label} cannot self-link")
    if left not in node_ids or right not in node_ids:
        raise MeshRuntimeError(f"{label} references an unknown node")
    return tuple(sorted((left, right)))


def normalize_topology(value: Any) -> dict[str, Any]:
    topology = _mapping(value, "topology")
    _exact_keys(
        topology,
        {"schema", "mesh_id", "network_scope", "nodes", "links"},
        "topology",
    )
    if topology["schema"] != TOPOLOGY_SCHEMA:
        raise MeshRuntimeError(f"topology.schema must be {TOPOLOGY_SCHEMA}")
    if topology["mesh_id"] != MESH_ID:
        raise MeshRuntimeError(f"topology.mesh_id must be {MESH_ID}")
    if topology["network_scope"] != NETWORK_SCOPE:
        raise MeshRuntimeError(f"topology.network_scope must be {NETWORK_SCOPE}")
    raw_nodes = topology["nodes"]
    if not isinstance(raw_nodes, list) or not 4 <= len(raw_nodes) <= MAX_NODES:
        raise MeshRuntimeError("topology must contain 4..16 nodes")
    nodes = [
        normalize_node(node, f"topology.nodes[{index}]")
        for index, node in enumerate(raw_nodes)
    ]
    node_ids = [node["node_id"] for node in nodes]
    if len(set(node_ids)) != len(node_ids):
        raise MeshRuntimeError("topology node_id values must be unique")
    endpoints = [(node["host"], node["port"]) for node in nodes]
    if len(set(endpoints)) != len(endpoints):
        raise MeshRuntimeError("topology TCP endpoints must be unique")

    pairs: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        pairs.setdefault(node["pair_id"], []).append(node)
    if len(pairs) < MIN_PAIR_COUNT:
        raise MeshRuntimeError(
            "REAL_MESH_REQUIRES_AT_LEAST_TWO_AUTHORITY_MIRROR_PAIRS"
        )
    for pair_id, pair_nodes in pairs.items():
        roles = sorted(node["role"] for node in pair_nodes)
        if len(pair_nodes) != 2 or roles != ["AUTHORITY", "MIRROR"]:
            raise MeshRuntimeError(
                f"pair {pair_id} must contain exactly AUTHORITY and MIRROR"
            )
        repositories = {node["repository"] for node in pair_nodes}
        if len(repositories) != 2:
            raise MeshRuntimeError(
                f"pair {pair_id} must bind distinct role repositories"
            )

    raw_links = topology["links"]
    if not isinstance(raw_links, list) or len(raw_links) < len(nodes):
        raise MeshRuntimeError("mesh topology needs enough links to contain a cycle")
    links = [
        _normalize_link(item, set(node_ids), f"topology.links[{index}]")
        for index, item in enumerate(raw_links)
    ]
    if len(set(links)) != len(links):
        raise MeshRuntimeError("topology links must be unique")

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for left, right in links:
        adjacency[left].add(right)
        adjacency[right].add(left)
    seen: set[str] = set()
    stack = [node_ids[0]]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(adjacency[current] - seen)
    if seen != set(node_ids):
        raise MeshRuntimeError("mesh topology must be connected")
    if any(len(adjacency[node_id]) < 2 for node_id in node_ids):
        raise MeshRuntimeError("every real-mesh node must have at least two peers")
    if len(links) < len(nodes):
        raise MeshRuntimeError("mesh topology must contain a cycle")

    return {
        "schema": TOPOLOGY_SCHEMA,
        "mesh_id": MESH_ID,
        "network_scope": NETWORK_SCOPE,
        "nodes": sorted(nodes, key=lambda item: item["node_id"]),
        "links": [list(link) for link in sorted(set(links))],
    }


def node_by_id(topology: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    for node in topology["nodes"]:
        if node["node_id"] == node_id:
            return dict(node)
    raise MeshRuntimeError(f"unknown route node {node_id}")


def topology_link_set(topology: Mapping[str, Any]) -> set[tuple[str, str]]:
    return {tuple(sorted(link)) for link in topology["links"]}


def normalize_payload(value: Any) -> dict[str, Any]:
    payload = _mapping(value, "payload")
    _exact_keys(payload, {"kind", "nonce", "input_binding"}, "payload")
    if payload["kind"] != "MESH_PROBE":
        raise MeshRuntimeError("payload.kind must be MESH_PROBE")
    binding = _mapping(payload["input_binding"], "payload.input_binding")
    _exact_keys(
        binding,
        {"source_head", "source_tree", "external_effect"},
        "payload.input_binding",
    )
    if binding["external_effect"] != "NONE":
        raise MeshRuntimeError("payload.external_effect must remain NONE")
    return {
        "kind": "MESH_PROBE",
        "nonce": _identifier(payload["nonce"], "payload.nonce"),
        "input_binding": {
            "source_head": _sha1(
                binding["source_head"], "payload.input_binding.source_head"
            ),
            "source_tree": _sha1(
                binding["source_tree"], "payload.input_binding.source_tree"
            ),
            "external_effect": "NONE",
        },
    }


def normalize_message(value: Any) -> dict[str, Any]:
    message = _mapping(value, "message")
    _exact_keys(
        message,
        {
            "schema",
            "mesh_id",
            "message_id",
            "route_id",
            "topology",
            "route",
            "hop_index",
            "receipt_chain",
            "payload",
            "payload_sha256",
            "ambiguity_present",
        },
        "message",
    )
    if message["schema"] != MESSAGE_SCHEMA:
        raise MeshRuntimeError(f"message.schema must be {MESSAGE_SCHEMA}")
    if message["mesh_id"] != MESH_ID:
        raise MeshRuntimeError(f"message.mesh_id must be {MESH_ID}")
    topology = normalize_topology(message["topology"])
    route = message["route"]
    if (
        not isinstance(route, list)
        or len(route) < 4
        or len(route) > len(topology["nodes"])
    ):
        raise MeshRuntimeError("route must traverse at least four topology nodes")
    normalized_route = [
        _identifier(item, f"route[{index}]") for index, item in enumerate(route)
    ]
    if len(set(normalized_route)) != len(normalized_route):
        raise MeshRuntimeError("route may not repeat a node")
    topology_ids = {node["node_id"] for node in topology["nodes"]}
    if not set(normalized_route).issubset(topology_ids):
        raise MeshRuntimeError("route references unknown topology node")
    links = topology_link_set(topology)
    for left, right in zip(normalized_route, normalized_route[1:]):
        if tuple(sorted((left, right))) not in links:
            raise MeshRuntimeError(
                f"route edge {left}->{right} is not a topology link"
            )
    route_pairs = {
        node_by_id(topology, node_id)["pair_id"] for node_id in normalized_route
    }
    if len(route_pairs) < MIN_PAIR_COUNT:
        raise MeshRuntimeError("route must cross at least two Authority/Mirror pairs")
    expected_route_id = canonical_sha256(
        {
            "mesh_id": MESH_ID,
            "topology_sha256": canonical_sha256(topology),
            "route": normalized_route,
        }
    )
    if message["route_id"] != expected_route_id:
        raise MeshRuntimeError("route_id mismatch")
    hop_index = message["hop_index"]
    if (
        isinstance(hop_index, bool)
        or not isinstance(hop_index, int)
        or not 0 <= hop_index < len(normalized_route)
    ):
        raise MeshRuntimeError("hop_index is outside the route")
    chain = message["receipt_chain"]
    if not isinstance(chain, list) or len(chain) != hop_index:
        raise MeshRuntimeError("receipt_chain length must equal hop_index")
    normalized_chain = [
        _sha256(item, f"receipt_chain[{index}]")
        for index, item in enumerate(chain)
    ]
    payload = normalize_payload(message["payload"])
    payload_hash = canonical_sha256(payload)
    if message["payload_sha256"] != payload_hash:
        raise MeshRuntimeError("payload_sha256 mismatch")
    if not isinstance(message["ambiguity_present"], bool):
        raise MeshRuntimeError("ambiguity_present must be a boolean")
    return {
        "schema": MESSAGE_SCHEMA,
        "mesh_id": MESH_ID,
        "message_id": _identifier(message["message_id"], "message.message_id"),
        "route_id": expected_route_id,
        "topology": topology,
        "route": normalized_route,
        "hop_index": hop_index,
        "receipt_chain": normalized_chain,
        "payload": payload,
        "payload_sha256": payload_hash,
        "ambiguity_present": message["ambiguity_present"],
    }


def build_message(
    topology: Mapping[str, Any],
    route: Sequence[str],
    *,
    message_id: str,
    nonce: str,
    source_head: str,
    source_tree: str,
    ambiguity_present: bool = False,
) -> dict[str, Any]:
    normalized_topology = normalize_topology(topology)
    normalized_route = [_identifier(node_id, "route node") for node_id in route]
    route_id = canonical_sha256(
        {
            "mesh_id": MESH_ID,
            "topology_sha256": canonical_sha256(normalized_topology),
            "route": normalized_route,
        }
    )
    payload = {
        "kind": "MESH_PROBE",
        "nonce": _identifier(nonce, "nonce"),
        "input_binding": {
            "source_head": _sha1(source_head, "source_head"),
            "source_tree": _sha1(source_tree, "source_tree"),
            "external_effect": "NONE",
        },
    }
    message = {
        "schema": MESSAGE_SCHEMA,
        "mesh_id": MESH_ID,
        "message_id": _identifier(message_id, "message_id"),
        "route_id": route_id,
        "topology": normalized_topology,
        "route": normalized_route,
        "hop_index": 0,
        "receipt_chain": [],
        "payload": payload,
        "payload_sha256": canonical_sha256(payload),
        "ambiguity_present": ambiguity_present,
    }
    return normalize_message(message)


def hold_response(
    *,
    message_id: str,
    node_id: str,
    state: EffectState,
    reason: str,
    retryable: bool,
) -> dict[str, Any]:
    if state not in {
        EffectState.EFFECT_ACK_CONTINUE,
        EffectState.EFFECT_ACK_BLOCK,
        EffectState.EFFECT_ACK_ISOLATE,
    }:
        raise MeshRuntimeError(
            "hold response requires CONTINUE, BLOCK, or ISOLATE"
        )
    return {
        "schema": HOLD_SCHEMA,
        "mesh_id": MESH_ID,
        "message_id": message_id,
        "node_id": node_id,
        "effect_state": state.value,
        "ordinary_release": False,
        "reason": reason,
        "retryable": retryable,
        "external_effect": "NONE",
    }


class AppendOnlyNodeLedger:
    """Hash-linked append-only JSONL ledger with restart reconstruction."""

    def __init__(self, path: pathlib.Path, node_id: str) -> None:
        self.path = path
        self.node_id = node_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.sequence = 0
        self.previous_record_sha256: str | None = None
        self.accepted: dict[str, dict[str, Any]] = {}
        self.completed: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        previous: str | None = None
        expected_sequence = 1
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, start=1):
                if not raw.endswith("\n"):
                    raise MeshRuntimeError(
                        f"ledger line {line_number} is not newline terminated"
                    )
                record = json.loads(raw)
                if not isinstance(record, dict):
                    raise MeshRuntimeError(
                        f"ledger line {line_number} is not an object"
                    )
                stored_hash = record.get("record_sha256")
                if not isinstance(stored_hash, str):
                    raise MeshRuntimeError(
                        f"ledger line {line_number} has no record hash"
                    )
                projection = dict(record)
                projection.pop("record_sha256", None)
                if canonical_sha256(projection) != stored_hash:
                    raise MeshRuntimeError(
                        f"ledger line {line_number} hash mismatch"
                    )
                if (
                    record.get("schema") != LEDGER_RECORD_SCHEMA
                    or record.get("node_id") != self.node_id
                ):
                    raise MeshRuntimeError(
                        f"ledger line {line_number} identity mismatch"
                    )
                if record.get("sequence") != expected_sequence:
                    raise MeshRuntimeError(
                        f"ledger line {line_number} sequence mismatch"
                    )
                if record.get("previous_record_sha256") != previous:
                    raise MeshRuntimeError(
                        f"ledger line {line_number} predecessor mismatch"
                    )
                self._apply_record(record)
                previous = stored_hash
                expected_sequence += 1
        self.sequence = expected_sequence - 1
        self.previous_record_sha256 = previous

    def _apply_record(self, record: Mapping[str, Any]) -> None:
        event = record.get("event")
        message_id = record.get("message_id")
        if not isinstance(message_id, str):
            raise MeshRuntimeError("ledger message_id missing")
        if event == "ACCEPTED":
            accepted = record.get("accepted")
            if not isinstance(accepted, dict):
                raise MeshRuntimeError("ledger ACCEPTED payload missing")
            existing = self.accepted.get(message_id)
            if existing is not None and existing != accepted:
                raise MeshRuntimeError(
                    "ledger contains conflicting ACCEPTED records"
                )
            self.accepted[message_id] = accepted
        elif event == "COMPLETED":
            response = record.get("response")
            if not isinstance(response, dict):
                raise MeshRuntimeError("ledger COMPLETED response missing")
            self.completed[message_id] = response
        elif event == "HELD":
            response = record.get("response")
            if not isinstance(response, dict):
                raise MeshRuntimeError("ledger HELD response missing")
        else:
            raise MeshRuntimeError(f"unsupported ledger event {event}")

    def append(
        self, event: str, message_id: str, **fields: Any
    ) -> dict[str, Any]:
        projection = {
            "schema": LEDGER_RECORD_SCHEMA,
            "node_id": self.node_id,
            "sequence": self.sequence + 1,
            "previous_record_sha256": self.previous_record_sha256,
            "recorded_utc": utc_now(),
            "event": event,
            "message_id": message_id,
            **fields,
        }
        record = {**projection, "record_sha256": canonical_sha256(projection)}
        encoded = canonical_json_bytes(record) + b"\n"
        descriptor = os.open(
            self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
        )
        try:
            os.write(descriptor, encoded)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self.sequence += 1
        self.previous_record_sha256 = record["record_sha256"]
        self._apply_record(record)
        return record


@dataclass(frozen=True)
class NodeIdentity:
    node_id: str
    pair_id: str
    role: str
    repository: str
    instance_id: str
    root_tree_sha: str

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "NodeIdentity":
        required = {
            "node_id",
            "pair_id",
            "role",
            "repository",
            "instance_id",
            "root_tree_sha",
        }
        _exact_keys(value, required, "node identity")
        synthetic = {**value, "host": "127.0.0.1", "port": 1}
        normalized = normalize_node(synthetic, "node identity")
        return cls(**{key: normalized[key] for key in required})

    def to_node(self, host: str, port: int) -> dict[str, Any]:
        return normalize_node(
            {
                "node_id": self.node_id,
                "pair_id": self.pair_id,
                "role": self.role,
                "repository": self.repository,
                "instance_id": self.instance_id,
                "root_tree_sha": self.root_tree_sha,
                "host": host,
                "port": port,
            }
        )


class NodeRuntime:
    def __init__(
        self, identity: NodeIdentity, ledger: AppendOnlyNodeLedger
    ) -> None:
        self.identity = identity
        self.ledger = ledger
        self._lock = asyncio.Lock()

    async def handle(self, raw_message: Any) -> dict[str, Any]:
        try:
            message = normalize_message(raw_message)
        except (MeshRuntimeError, TypeError, ValueError) as exc:
            message_id = (
                raw_message.get("message_id", "UNAVAILABLE")
                if isinstance(raw_message, dict)
                else "UNAVAILABLE"
            )
            return hold_response(
                message_id=str(message_id)[:128] or "UNAVAILABLE",
                node_id=self.identity.node_id,
                state=EffectState.EFFECT_ACK_BLOCK,
                reason=f"INVALID_MESH_MESSAGE:{str(exc)[:512]}",
                retryable=False,
            )
        async with self._lock:
            return await self._handle_valid(message)

    async def _handle_valid(self, message: dict[str, Any]) -> dict[str, Any]:
        message_id = message["message_id"]
        admission = deterministic_disposition(
            frame_complete=True,
            canonical_equal=True,
            ambiguity_present=message["ambiguity_present"],
        )
        if admission is DeterministicDisposition.HOLD:
            return hold_response(
                message_id=message_id,
                node_id=self.identity.node_id,
                state=EffectState.EFFECT_ACK_CONTINUE,
                reason="EXPLICIT_AMBIGUITY_HOLD",
                retryable=False,
            )
        if admission is not DeterministicDisposition.ACCEPT:
            return hold_response(
                message_id=message_id,
                node_id=self.identity.node_id,
                state=EffectState.EFFECT_ACK_BLOCK,
                reason="DETERMINISTIC_ADMISSION_NOT_ACCEPTED",
                retryable=False,
            )
        hop_index = message["hop_index"]
        expected_node_id = message["route"][hop_index]
        if expected_node_id != self.identity.node_id:
            return hold_response(
                message_id=message_id,
                node_id=self.identity.node_id,
                state=EffectState.EFFECT_ACK_BLOCK,
                reason="ROUTE_NODE_IDENTITY_MISMATCH",
                retryable=False,
            )
        topology_node = node_by_id(message["topology"], self.identity.node_id)
        identity_fields = (
            "node_id",
            "pair_id",
            "role",
            "repository",
            "instance_id",
            "root_tree_sha",
        )
        if any(
            topology_node[field] != getattr(self.identity, field)
            for field in identity_fields
        ):
            return hold_response(
                message_id=message_id,
                node_id=self.identity.node_id,
                state=EffectState.EFFECT_ACK_BLOCK,
                reason="TOPOLOGY_NODE_IDENTITY_MISMATCH",
                retryable=False,
            )

        message_sha256 = canonical_sha256(message)
        existing = self.ledger.accepted.get(message_id)
        if existing is not None:
            if existing.get("message_sha256") != message_sha256:
                return hold_response(
                    message_id=message_id,
                    node_id=self.identity.node_id,
                    state=EffectState.EFFECT_ACK_BLOCK,
                    reason="MESSAGE_ID_REBOUND_TO_DIFFERENT_BYTES",
                    retryable=False,
                )
            completed = self.ledger.completed.get(message_id)
            if completed is not None:
                return copy.deepcopy(completed)
            hop_receipt = existing["hop_receipt"]
            hop_receipt_sha256 = existing["hop_receipt_sha256"]
        else:
            predecessor = (
                message["receipt_chain"][-1]
                if message["receipt_chain"]
                else None
            )
            hop_receipt = {
                "schema": HOP_RECEIPT_SCHEMA,
                "mesh_id": MESH_ID,
                "message_id": message_id,
                "route_id": message["route_id"],
                "node_id": self.identity.node_id,
                "pair_id": self.identity.pair_id,
                "role": self.identity.role,
                "repository": self.identity.repository,
                "instance_id": self.identity.instance_id,
                "root_tree_sha": self.identity.root_tree_sha,
                "hop_index": hop_index,
                "inbound_message_sha256": message_sha256,
                "predecessor_hop_receipt_sha256": predecessor,
                "payload_sha256": message["payload_sha256"],
                "deterministic_admission": admission.value,
                "observed_effect": "MESH_MESSAGE_ACCEPTED_AND_LEDGERED",
                "network_scope": NETWORK_SCOPE,
                "external_effect": "NONE",
                "recorded_utc": utc_now(),
            }
            hop_receipt_sha256 = canonical_sha256(hop_receipt)
            self.ledger.append(
                "ACCEPTED",
                message_id,
                accepted={
                    "message_sha256": message_sha256,
                    "hop_receipt": hop_receipt,
                    "hop_receipt_sha256": hop_receipt_sha256,
                },
            )

        chain = [*message["receipt_chain"], hop_receipt_sha256]
        if hop_index == len(message["route"]) - 1:
            response = {
                "schema": TERMINAL_RECEIPT_SCHEMA,
                "mesh_id": MESH_ID,
                "message_id": message_id,
                "route_id": message["route_id"],
                "payload_sha256": message["payload_sha256"],
                "hop_receipt_sha256s": chain,
                "path": list(message["route"]),
                "final_node_id": self.identity.node_id,
                "transport_ack": True,
                "effect_state": EffectState.EFFECT_ACK_CONTINUE.value,
                "ordinary_release": False,
                "next_required_check": (
                    "REOBSERVE_ALL_NODE_LEDGERS_AND_FINALIZE_BOUND_EFFECT_ACK"
                ),
                "network_scope": NETWORK_SCOPE,
                "external_effect": "NONE",
                "general_internet_reachability": False,
                "authority_mirror_synchronization": False,
            }
            self.ledger.append("COMPLETED", message_id, response=response)
            return response

        next_id = message["route"][hop_index + 1]
        next_node = node_by_id(message["topology"], next_id)
        forwarded = copy.deepcopy(message)
        forwarded["hop_index"] = hop_index + 1
        forwarded["receipt_chain"] = chain
        try:
            response = await send_message_async(
                next_node["host"],
                next_node["port"],
                forwarded,
                timeout_seconds=SOCKET_TIMEOUT_SECONDS,
            )
        except (OSError, asyncio.TimeoutError, MeshTransportError) as exc:
            response = hold_response(
                message_id=message_id,
                node_id=self.identity.node_id,
                state=EffectState.EFFECT_ACK_CONTINUE,
                reason=(
                    f"NEXT_HOP_UNREACHABLE:{next_id}:{type(exc).__name__}"
                ),
                retryable=True,
            )
            self.ledger.append("HELD", message_id, response=response)
            return response

        if response.get("schema") == TERMINAL_RECEIPT_SCHEMA:
            downstream_chain = response.get("hop_receipt_sha256s")
            if (
                response.get("message_id") != message_id
                or response.get("route_id") != message["route_id"]
                or response.get("payload_sha256") != message["payload_sha256"]
                or not isinstance(downstream_chain, list)
                or len(downstream_chain) != len(message["route"])
                or downstream_chain[hop_index] != hop_receipt_sha256
            ):
                response = hold_response(
                    message_id=message_id,
                    node_id=self.identity.node_id,
                    state=EffectState.EFFECT_ACK_BLOCK,
                    reason="DOWNSTREAM_TERMINAL_RECEIPT_BINDING_MISMATCH",
                    retryable=False,
                )
                self.ledger.append("HELD", message_id, response=response)
                return response
            self.ledger.append("COMPLETED", message_id, response=response)
            return response
        if response.get("schema") == HOLD_SCHEMA:
            self.ledger.append("HELD", message_id, response=response)
            return response
        response = hold_response(
            message_id=message_id,
            node_id=self.identity.node_id,
            state=EffectState.EFFECT_ACK_BLOCK,
            reason="DOWNSTREAM_RESPONSE_SCHEMA_INVALID",
            retryable=False,
        )
        self.ledger.append("HELD", message_id, response=response)
        return response


async def send_message_async(
    host: str,
    port: int,
    message: Mapping[str, Any],
    *,
    timeout_seconds: float = SOCKET_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if host != "127.0.0.1":
        raise MeshTransportError("only loopback endpoints are admitted")
    encoded = canonical_json_bytes(message) + b"\n"
    if len(encoded) > MAX_FRAME_BYTES:
        raise MeshTransportError("mesh frame exceeds maximum size")
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port), timeout=timeout_seconds
    )
    try:
        writer.write(encoded)
        await asyncio.wait_for(writer.drain(), timeout=timeout_seconds)
        response_bytes = await asyncio.wait_for(
            reader.readline(), timeout=timeout_seconds
        )
        if not response_bytes or len(response_bytes) > MAX_FRAME_BYTES:
            raise MeshTransportError("mesh response missing or oversized")
        response = json.loads(response_bytes)
        if not isinstance(response, dict):
            raise MeshTransportError("mesh response is not an object")
        return response
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


def send_message(
    host: str, port: int, message: Mapping[str, Any]
) -> dict[str, Any]:
    return asyncio.run(send_message_async(host, port, message))


async def serve_node(
    identity: NodeIdentity,
    ledger_path: pathlib.Path,
    host: str,
    port: int,
) -> None:
    if host != "127.0.0.1":
        raise MeshRuntimeError("node listeners are loopback-only")
    ledger = AppendOnlyNodeLedger(ledger_path, identity.node_id)
    runtime = NodeRuntime(identity, ledger)

    async def handle_connection(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            raw = await asyncio.wait_for(
                reader.readline(), timeout=SOCKET_TIMEOUT_SECONDS
            )
            if not raw or len(raw) > MAX_FRAME_BYTES:
                response = hold_response(
                    message_id="UNAVAILABLE",
                    node_id=identity.node_id,
                    state=EffectState.EFFECT_ACK_BLOCK,
                    reason="FRAME_MISSING_OR_OVERSIZED",
                    retryable=False,
                )
            else:
                try:
                    decoded = json.loads(raw)
                except json.JSONDecodeError:
                    decoded = None
                response = await runtime.handle(decoded)
            writer.write(canonical_json_bytes(response) + b"\n")
            await asyncio.wait_for(
                writer.drain(), timeout=SOCKET_TIMEOUT_SECONDS
            )
        except (OSError, asyncio.TimeoutError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass

    server = await asyncio.start_server(
        handle_connection, host, port, limit=MAX_FRAME_BYTES + 1
    )
    bound = server.sockets[0].getsockname()
    print(
        json.dumps(
            {
                "event": "READY",
                "node_id": identity.node_id,
                "host": bound[0],
                "port": bound[1],
                "ledger": str(ledger_path),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    async with server:
        await server.serve_forever()


@dataclass
class NodeProcess:
    identity: NodeIdentity
    ledger_path: pathlib.Path
    process: subprocess.Popen[str] | None = None
    host: str = "127.0.0.1"
    port: int = 0

    def start(self, *, port: int = 0) -> None:
        if self.process is not None:
            raise MeshTransportError(
                f"node {self.identity.node_id} is already running"
            )
        config = {
            "node_id": self.identity.node_id,
            "pair_id": self.identity.pair_id,
            "role": self.identity.role,
            "repository": self.identity.repository,
            "instance_id": self.identity.instance_id,
            "root_tree_sha": self.identity.root_tree_sha,
        }
        command = [
            sys.executable,
            "-B",
            str(pathlib.Path(__file__).resolve()),
            "node",
            "--identity-json",
            json.dumps(config, sort_keys=True, separators=(",", ":")),
            "--ledger",
            str(self.ledger_path),
            "--host",
            self.host,
            "--port",
            str(port),
        ]
        self.process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert self.process.stdout is not None
        ready_queue: queue.Queue[str] = queue.Queue(maxsize=1)

        def reader() -> None:
            assert self.process is not None and self.process.stdout is not None
            ready_queue.put(self.process.stdout.readline())

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        try:
            line = ready_queue.get(timeout=PROCESS_READY_TIMEOUT_SECONDS)
        except queue.Empty as exc:
            diagnostics = self.stop()
            raise MeshTransportError(
                f"node {self.identity.node_id} did not become ready: {diagnostics}"
            ) from exc
        if not line:
            diagnostics = self.stop()
            raise MeshTransportError(
                f"node {self.identity.node_id} exited before READY: {diagnostics}"
            )
        ready = json.loads(line)
        if (
            ready.get("event") != "READY"
            or ready.get("node_id") != self.identity.node_id
        ):
            diagnostics = self.stop()
            raise MeshTransportError(
                f"node {self.identity.node_id} emitted invalid READY: "
                f"{ready}; {diagnostics}"
            )
        self.host = ready["host"]
        self.port = int(ready["port"])

    def stop(self) -> str:
        process = self.process
        if process is None:
            return ""
        self.process = None
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        stderr = ""
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            stderr = process.stderr.read()
            process.stderr.close()
        return stderr.strip()

    def restart(self) -> None:
        old_port = self.port
        diagnostics = self.stop()
        if diagnostics:
            raise MeshTransportError(
                f"node {self.identity.node_id} emitted stderr before restart: "
                f"{diagnostics}"
            )
        self.start(port=old_port)

    def topology_node(self) -> dict[str, Any]:
        return self.identity.to_node(self.host, self.port)


class MeshHarness:
    def __init__(self, workdir: pathlib.Path, source_tree: str) -> None:
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        authority_tree = _sha1(source_tree, "source_tree")
        mirror_tree = "bd421a2624d20804c74eef77647fc52fcdb1feec"
        identities = [
            NodeIdentity(
                node_id="pair-a-authority",
                pair_id="pair-a",
                role="AUTHORITY",
                repository="Goldkelch/qik-vrt",
                instance_id="authority-instance-a",
                root_tree_sha=authority_tree,
            ),
            NodeIdentity(
                node_id="pair-a-mirror",
                pair_id="pair-a",
                role="MIRROR",
                repository="ingolf-lohmann/qik-vrt",
                instance_id="mirror-instance-a",
                root_tree_sha=mirror_tree,
            ),
            NodeIdentity(
                node_id="pair-b-authority",
                pair_id="pair-b",
                role="AUTHORITY",
                repository="Goldkelch/qik-vrt",
                instance_id="authority-instance-b",
                root_tree_sha=authority_tree,
            ),
            NodeIdentity(
                node_id="pair-b-mirror",
                pair_id="pair-b",
                role="MIRROR",
                repository="ingolf-lohmann/qik-vrt",
                instance_id="mirror-instance-b",
                root_tree_sha=mirror_tree,
            ),
        ]
        self.nodes = {
            identity.node_id: NodeProcess(
                identity=identity,
                ledger_path=(
                    self.workdir
                    / "ledgers"
                    / f"{identity.node_id}.jsonl"
                ),
            )
            for identity in identities
        }
        self.topology: dict[str, Any] | None = None

    def __enter__(self) -> "MeshHarness":
        try:
            for node in self.nodes.values():
                node.start()
            self.topology = normalize_topology(
                {
                    "schema": TOPOLOGY_SCHEMA,
                    "mesh_id": MESH_ID,
                    "network_scope": NETWORK_SCOPE,
                    "nodes": [
                        node.topology_node() for node in self.nodes.values()
                    ],
                    "links": [
                        ["pair-a-authority", "pair-a-mirror"],
                        ["pair-a-authority", "pair-b-authority"],
                        ["pair-a-mirror", "pair-b-authority"],
                        ["pair-a-mirror", "pair-b-mirror"],
                        ["pair-b-authority", "pair-b-mirror"],
                    ],
                }
            )
            return self
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        diagnostics = []
        for node in reversed(list(self.nodes.values())):
            stderr = node.stop()
            if stderr:
                diagnostics.append(f"{node.identity.node_id}: {stderr}")
        if diagnostics and exc is None:
            raise MeshTransportError(
                "node diagnostics: " + " | ".join(diagnostics)
            )

    def route_message(self, message: Mapping[str, Any]) -> dict[str, Any]:
        normalized = normalize_message(message)
        first = node_by_id(
            normalized["topology"], normalized["route"][0]
        )
        return send_message(first["host"], first["port"], normalized)

    def restart(self, node_id: str) -> None:
        self.nodes[node_id].restart()
        assert self.topology is not None
        for node in self.topology["nodes"]:
            if node["node_id"] == node_id:
                node["port"] = self.nodes[node_id].port
                node["host"] = self.nodes[node_id].host
        self.topology = normalize_topology(self.topology)


def _read_ledger_records(path: pathlib.Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            records.append(json.loads(line))
    return records


def reobserve_route(
    harness: MeshHarness,
    message: Mapping[str, Any],
    terminal: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = normalize_message(message)
    if terminal.get("schema") != TERMINAL_RECEIPT_SCHEMA:
        raise MeshRuntimeError("terminal response is not a terminal receipt")
    expected_chain = terminal.get("hop_receipt_sha256s")
    if (
        not isinstance(expected_chain, list)
        or len(expected_chain) != len(normalized["route"])
    ):
        raise MeshRuntimeError("terminal receipt has incomplete hop chain")
    observations: list[dict[str, Any]] = []
    for hop_index, node_id in enumerate(normalized["route"]):
        process = harness.nodes[node_id]
        ledger = AppendOnlyNodeLedger(process.ledger_path, node_id)
        accepted = ledger.accepted.get(normalized["message_id"])
        completed = ledger.completed.get(normalized["message_id"])
        if accepted is None or completed is None:
            raise MeshRuntimeError(
                f"node {node_id} lacks accepted/completed receipt"
            )
        if accepted["hop_receipt_sha256"] != expected_chain[hop_index]:
            raise MeshRuntimeError(
                f"node {node_id} hop receipt hash mismatch"
            )
        if completed != terminal:
            raise MeshRuntimeError(
                f"node {node_id} terminal response mismatch"
            )
        observations.append(
            {
                "node_id": node_id,
                "pair_id": process.identity.pair_id,
                "role": process.identity.role,
                "root_tree_sha": process.identity.root_tree_sha,
                "ledger_record_count": ledger.sequence,
                "ledger_tip_sha256": ledger.previous_record_sha256,
                "hop_receipt_sha256": accepted["hop_receipt_sha256"],
                "accepted_and_completed_reobserved": True,
            }
        )
    return {
        "message_id": normalized["message_id"],
        "route_id": normalized["route_id"],
        "path": list(normalized["route"]),
        "payload_sha256": normalized["payload_sha256"],
        "hop_receipt_sha256s": list(expected_chain),
        "node_observations": observations,
        "complete_route_reobserved": True,
    }


def finalize_effect_ack(
    message: Mapping[str, Any], route_observation: Mapping[str, Any]
) -> dict[str, Any]:
    payload = canonical_json_bytes(normalize_payload(message["payload"]))
    evidence_refs = tuple(route_observation["hop_receipt_sha256s"])
    request = EffectAckRequest(
        protocol_root_id=f"qikvrt:real-mesh:{message['message_id']}",
        input_id=message["message_id"],
        payload=payload,
        transport_ack=True,
        declared_input_hash=sha256_identifier(payload),
        origin_checked=True,
        context_checked=True,
        semantics_reconstructed=True,
        effect_anticipated=True,
        risk_classified=True,
        risk_level=RiskLevel.LOW,
        responsibility_assigned=True,
        responsibility_owner=MESH_ID,
        connection_decision=ConnectionDecision.RELEASE,
        policy_allows_release=True,
        reasons=("BOUNDED_LOOPBACK_MULTI_PAIR_DELIVERY_REOBSERVED",),
        evidence_refs=evidence_refs,
        required_evidence_refs=evidence_refs,
        open_questions=(),
        next_required_checks=(),
    )
    result = EffectAckEngine(max_payload_bytes=MAX_FRAME_BYTES).evaluate(
        request
    )
    if result.state is not EffectState.EFFECT_ACK_DONE:
        raise MeshRuntimeError(
            "bounded mesh effect acknowledgement did not close: "
            f"{result.state.value}"
        )
    return result.to_dict()


def _pair_divergence(
    topology: Mapping[str, Any]
) -> list[dict[str, Any]]:
    pairs: dict[str, dict[str, str]] = {}
    for node in topology["nodes"]:
        pairs.setdefault(node["pair_id"], {})[
            node["role"]
        ] = node["root_tree_sha"]
    return [
        {
            "pair_id": pair_id,
            "authority_tree": values["AUTHORITY"],
            "mirror_tree": values["MIRROR"],
            "state": (
                "DIVERGED"
                if values["AUTHORITY"] != values["MIRROR"]
                else "TREE_EQUALITY_OBSERVED"
            ),
            "synchronization_authorized": False,
        }
        for pair_id, values in sorted(pairs.items())
    ]


def run_demo(
    workdir: pathlib.Path,
    *,
    source_head: str,
    source_tree: str,
) -> dict[str, Any]:
    source_head = _sha1(source_head, "source_head")
    source_tree = _sha1(source_tree, "source_tree")
    with MeshHarness(workdir, source_tree) as harness:
        assert harness.topology is not None
        route_a = [
            "pair-a-authority",
            "pair-a-mirror",
            "pair-b-mirror",
            "pair-b-authority",
        ]
        message_a = build_message(
            harness.topology,
            route_a,
            message_id="real-mesh-route-a-0001",
            nonce="QIKVRT-REAL-MESH-NONCE-A-0001",
            source_head=source_head,
            source_tree=source_tree,
        )
        terminal_a = harness.route_message(message_a)
        observation_a = reobserve_route(harness, message_a, terminal_a)
        ack_a = finalize_effect_ack(message_a, observation_a)

        source_node = harness.nodes[route_a[0]]
        before_restart_records = len(
            _read_ledger_records(source_node.ledger_path)
        )
        harness.restart(route_a[0])
        replay = harness.route_message(message_a)
        after_restart_records = len(
            _read_ledger_records(source_node.ledger_path)
        )
        if (
            replay != terminal_a
            or before_restart_records != after_restart_records
        ):
            raise MeshRuntimeError("restart replay was not idempotent")

        route_b = [
            "pair-a-authority",
            "pair-b-authority",
            "pair-b-mirror",
            "pair-a-mirror",
        ]
        message_b = build_message(
            harness.topology,
            route_b,
            message_id="real-mesh-route-b-0001",
            nonce="QIKVRT-REAL-MESH-NONCE-B-0001",
            source_head=source_head,
            source_tree=source_tree,
        )
        terminal_b = harness.route_message(message_b)
        observation_b = reobserve_route(harness, message_b, terminal_b)
        ack_b = finalize_effect_ack(message_b, observation_b)

        topology = normalize_topology(harness.topology)
        receipt = {
            "schema": EXECUTION_RECEIPT_SCHEMA,
            "mesh_id": MESH_ID,
            "source_head": source_head,
            "source_tree": source_tree,
            "topology_sha256": canonical_sha256(topology),
            "topology": topology,
            "pair_count": len(
                {node["pair_id"] for node in topology["nodes"]}
            ),
            "node_process_count": len(topology["nodes"]),
            "transport": "TCP",
            "network_scope": NETWORK_SCOPE,
            "event_model": "SOCKET_EVENT_DRIVEN_NO_DOMAIN_POLLING",
            "redundant_path_observed": route_a != route_b,
            "routes": [
                {
                    "observation": observation_a,
                    "bounded_effect_ack": ack_a,
                },
                {
                    "observation": observation_b,
                    "bounded_effect_ack": ack_b,
                },
            ],
            "restart_replay": {
                "node_id": route_a[0],
                "same_terminal_receipt": replay == terminal_a,
                "ledger_record_count_unchanged": (
                    before_restart_records == after_restart_records
                ),
                "observed": True,
            },
            "pair_states": _pair_divergence(topology),
            "completion_claims": {
                "real_multi_pair_mesh_runtime_executed": True,
                "independent_tcp_node_processes_observed": True,
                "multi_hop_delivery_reobserved": True,
                "acknowledgement_return_path_observed": True,
                "append_only_restart_persistence_observed": True,
                "bounded_loopback_effect_ack_done": True,
                "general_effect_ack_done": False,
                "general_internet_reachability": False,
                "production_deployment": False,
                "physical_hardware_execution": False,
                "authority_mirror_synchronization": False,
                "authority_mirror_equality_claimed": False,
                "merge": False,
                "PASS": False,
                "FINAL_PASS": False,
            },
            "effect_ack_scope": EFFECT_ACK_SCOPE,
            "external_effect": "NONE",
            "receipt_created_utc": utc_now(),
        }
        receipt["receipt_sha256"] = canonical_sha256(receipt)
        return receipt


def _node_command(args: argparse.Namespace) -> int:
    identity_raw = json.loads(args.identity_json)
    identity = NodeIdentity.from_json(
        _mapping(identity_raw, "identity")
    )
    try:
        asyncio.run(
            serve_node(identity, args.ledger, args.host, args.port)
        )
    except KeyboardInterrupt:
        return 0
    return 0


def _demo_command(args: argparse.Namespace) -> int:
    workdir = args.workdir or pathlib.Path(
        tempfile.mkdtemp(prefix="qikvrt-real-mesh-")
    )
    try:
        receipt = run_demo(
            workdir,
            source_head=args.source_head,
            source_tree=args.source_tree,
        )
        encoded = (
            json.dumps(
                receipt, ensure_ascii=False, sort_keys=True, indent=2
            )
            + "\n"
        )
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
    except (
        MeshRuntimeError,
        MeshTransportError,
        OSError,
        ValueError,
    ) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    node = subparsers.add_parser(
        "node", help="run one loopback node service"
    )
    node.add_argument("--identity-json", required=True)
    node.add_argument("--ledger", required=True, type=pathlib.Path)
    node.add_argument("--host", default="127.0.0.1")
    node.add_argument("--port", default=0, type=int)
    node.set_defaults(func=_node_command)

    demo = subparsers.add_parser(
        "demo", help="execute and reobserve a four-node real mesh"
    )
    demo.add_argument("--source-head", required=True)
    demo.add_argument("--source-tree", required=True)
    demo.add_argument("--workdir", type=pathlib.Path)
    demo.add_argument("--output", type=pathlib.Path)
    demo.set_defaults(func=_demo_command)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
