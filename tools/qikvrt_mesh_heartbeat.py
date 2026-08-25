#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Event-driven QIK-VRT Mesh heartbeat and bounded audit system test.

One pulse per second proves liveness and lease freshness only. Heartbeats never
select work, trigger semantic work, poll domain state or blind-retry failures.
Semantic work begins only from one locally constructed content-bound event and
follows the exact local lifecycle:

0 -> 1 -> ARBEIT -> ERGEBNIS -> REOBSERVATION -> AUTHORITY_EFFEKT -> 0

The bounded system test uses four independent emitter processes and real
loopback TCP. Its authority effect is local-test-ledger-only; repository
Authority effects remain the responsibility of the separate trusted writer.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import pathlib
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

HEARTBEAT_SCHEMA = "qikvrt_mesh_heartbeat_v1"
AUDIT_SCHEMA = "qikvrt_mesh_heartbeat_execution_receipt_v1"
WORK_EVENT_SCHEMA = "qikvrt_mesh_work_event_v1"
WORK_RECEIPT_SCHEMA = "qikvrt_mesh_work_receipt_v1"
AUTHORITY_LEDGER_SCHEMA = "qikvrt_mesh_local_authority_ledger_v1"
NETWORK_SCOPE = "LOOPBACK_TCP_ONLY"
HEARTBEAT_ROLE = "LIVENESS_AND_LEASE_FRESHNESS_ONLY"
AUTHORITY_EFFECT_SCOPE = "LOCAL_TEST_LEDGER_ONLY"
EXTERNAL_EFFECT = "NONE"
HEARTBEAT_HZ = 1
HEARTBEAT_INTERVAL_NS = 1_000_000_000
MAX_SEND_LATENESS_NS = 750_000_000
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
LIFECYCLE = ["0", "1", "ARBEIT", "ERGEBNIS", "REOBSERVATION", "AUTHORITY_EFFEKT", "0"]
NODE_SPECS = (
    ("authority-a", "pair-a", "AUTHORITY"),
    ("mirror-a", "pair-a", "MIRROR"),
    ("authority-b", "pair-b", "AUTHORITY"),
    ("mirror-b", "pair-b", "MIRROR"),
)


class HeartbeatContractError(ValueError):
    """Fail-closed contract violation."""


class HeartbeatTransportError(RuntimeError):
    """Bounded loopback transport failure."""


def canonical_json_bytes(value: Any) -> bytes:
    def normalize(item: Any) -> Any:
        if item is None or isinstance(item, (bool, int, str)):
            return item
        if isinstance(item, float):
            raise HeartbeatContractError("floating-point values are not canonical")
        if isinstance(item, Mapping):
            result: dict[str, Any] = {}
            for key, child in item.items():
                if not isinstance(key, str) or key in result:
                    raise HeartbeatContractError("invalid canonical object key")
                result[key] = normalize(child)
            return result
        if isinstance(item, (list, tuple)):
            return [normalize(child) for child in item]
        raise HeartbeatContractError("unsupported canonical value")

    return json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def sha256_ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_ref(canonical_json_bytes(value))


def _sha1(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA1_RE.fullmatch(value):
        raise HeartbeatContractError(f"{label} must be a lowercase Git SHA-1")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise HeartbeatContractError(f"{label} must be a canonical sha256 reference")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise HeartbeatContractError(f"{label} must be a bounded identifier")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise HeartbeatContractError(f"{label} must be a non-negative integer")
    return value


def heartbeat_digest(value: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(value))


def build_heartbeat(
    *, node_id: str, pair_id: str, role: str, sequence: int,
    scheduled_monotonic_ns: int, sent_monotonic_ns: int,
    previous_heartbeat_sha256: str, source_head: str, source_tree: str,
) -> dict[str, Any]:
    value = {
        "schema": HEARTBEAT_SCHEMA,
        "node_id": node_id,
        "pair_id": pair_id,
        "role": role,
        "sequence": sequence,
        "scheduled_monotonic_ns": scheduled_monotonic_ns,
        "sent_monotonic_ns": sent_monotonic_ns,
        "lease_expires_monotonic_ns": scheduled_monotonic_ns + 2 * HEARTBEAT_INTERVAL_NS,
        "previous_heartbeat_sha256": previous_heartbeat_sha256,
        "source_head": source_head,
        "source_tree": source_tree,
        "heartbeat_hz": HEARTBEAT_HZ,
        "heartbeat_role": HEARTBEAT_ROLE,
        "semantic_work_triggered": False,
        "polling": False,
        "blind_retry": False,
        "external_effect": EXTERNAL_EFFECT,
    }
    return normalize_heartbeat(value)


def normalize_heartbeat(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HeartbeatContractError("heartbeat must be an object")
    required = {
        "schema", "node_id", "pair_id", "role", "sequence",
        "scheduled_monotonic_ns", "sent_monotonic_ns",
        "lease_expires_monotonic_ns", "previous_heartbeat_sha256",
        "source_head", "source_tree", "heartbeat_hz", "heartbeat_role",
        "semantic_work_triggered", "polling", "blind_retry", "external_effect",
    }
    if set(value) != required:
        raise HeartbeatContractError("heartbeat fields are not exact")
    sequence = _integer(value["sequence"], "sequence")
    scheduled = _integer(value["scheduled_monotonic_ns"], "scheduled_monotonic_ns")
    sent = _integer(value["sent_monotonic_ns"], "sent_monotonic_ns")
    lease = _integer(value["lease_expires_monotonic_ns"], "lease_expires_monotonic_ns")
    if value["schema"] != HEARTBEAT_SCHEMA or value["heartbeat_hz"] != 1:
        raise HeartbeatContractError("heartbeat schema or rate mismatch")
    if value["role"] not in {"AUTHORITY", "MIRROR"}:
        raise HeartbeatContractError("heartbeat role mismatch")
    if lease != scheduled + 2 * HEARTBEAT_INTERVAL_NS:
        raise HeartbeatContractError("heartbeat lease interval is not exact")
    if value["heartbeat_role"] != HEARTBEAT_ROLE:
        raise HeartbeatContractError("heartbeat role is not liveness-only")
    if value["semantic_work_triggered"] is not False:
        raise HeartbeatContractError("heartbeat may not trigger semantic work")
    if value["polling"] is not False:
        raise HeartbeatContractError("heartbeat may not poll")
    if value["blind_retry"] is not False:
        raise HeartbeatContractError("heartbeat may not blind-retry")
    if value["external_effect"] != EXTERNAL_EFFECT:
        raise HeartbeatContractError("heartbeat external effect must remain NONE")
    previous = value["previous_heartbeat_sha256"]
    if sequence == 0:
        if previous != "GENESIS":
            raise HeartbeatContractError("first heartbeat must bind GENESIS")
    else:
        _sha256(previous, "previous heartbeat")
    return {
        **dict(value),
        "node_id": _identifier(value["node_id"], "node_id"),
        "pair_id": _identifier(value["pair_id"], "pair_id"),
        "source_head": _sha1(value["source_head"], "source_head"),
        "source_tree": _sha1(value["source_tree"], "source_tree"),
        "sequence": sequence,
        "scheduled_monotonic_ns": scheduled,
        "sent_monotonic_ns": sent,
        "lease_expires_monotonic_ns": lease,
    }


def build_work_event(*, source_head: str, source_tree: str) -> dict[str, Any]:
    payload = {
        "operation": "HASH_BOUND_MESH_AUDIT",
        "nonce": "heartbeat-work-0001",
        "external_effect": EXTERNAL_EFFECT,
    }
    return {
        "schema": WORK_EVENT_SCHEMA,
        "event_id": "mesh-work-0001",
        "payload": payload,
        "payload_sha256": canonical_sha256(payload),
        "source_head": _sha1(source_head, "source_head"),
        "source_tree": _sha1(source_tree, "source_tree"),
        "authority_scope": AUTHORITY_EFFECT_SCOPE,
        "construction_scope": "LOCAL_SYSTEM_TEST",
        "external_ingress_authentication_observed": False,
    }


def normalize_work_event(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HeartbeatContractError("work event must be an object")
    required = {
        "schema", "event_id", "payload", "payload_sha256",
        "source_head", "source_tree", "authority_scope",
        "construction_scope", "external_ingress_authentication_observed",
    }
    if set(value) != required or value["schema"] != WORK_EVENT_SCHEMA:
        raise HeartbeatContractError("work event fields are not exact")
    if value["payload_sha256"] != canonical_sha256(value["payload"]):
        raise HeartbeatContractError("work event payload digest mismatch")
    if value["authority_scope"] != AUTHORITY_EFFECT_SCOPE:
        raise HeartbeatContractError("work event authority scope mismatch")
    if value["construction_scope"] != "LOCAL_SYSTEM_TEST":
        raise HeartbeatContractError("work event construction scope mismatch")
    if value["external_ingress_authentication_observed"] is not False:
        raise HeartbeatContractError(
            "work event may not manufacture external ingress authentication"
        )
    return {
        **copy.deepcopy(dict(value)),
        "event_id": _identifier(value["event_id"], "event_id"),
        "payload_sha256": _sha256(value["payload_sha256"], "payload_sha256"),
        "source_head": _sha1(value["source_head"], "source_head"),
        "source_tree": _sha1(value["source_tree"], "source_tree"),
    }


@dataclass
class WorkRing:
    state: str = "0"
    latest_lease_by_node: dict[str, int] = field(default_factory=dict)
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    payloads: dict[str, str] = field(default_factory=dict)
    authority_ledger: list[dict[str, Any]] = field(default_factory=list)
    heartbeat_semantic_work_count: int = 0
    polling_count: int = 0
    blind_retry_count: int = 0

    def observe_heartbeat(self, value: Any) -> None:
        heartbeat = normalize_heartbeat(value)
        before = self.state
        self.latest_lease_by_node[heartbeat["node_id"]] = heartbeat["lease_expires_monotonic_ns"]
        if self.state != before or self.state != "0":
            self.heartbeat_semantic_work_count += 1
            raise HeartbeatContractError("heartbeat changed semantic work state")

    def execute(self, value: Any) -> dict[str, Any]:
        event = normalize_work_event(value)
        event_id = event["event_id"]
        digest = event["payload_sha256"]
        if event_id in self.payloads:
            if self.payloads[event_id] != digest:
                raise HeartbeatContractError("event_id reuse with different payload is forbidden")
            return copy.deepcopy(self.receipts[event_id])
        if self.state != "0":
            raise HeartbeatContractError("work ring is not quiescent")
        transitions = ["0"]
        self.state = "1"; transitions.append(self.state)
        self.state = "ARBEIT"; transitions.append(self.state)
        result_sha = canonical_sha256({
            "event_id": event_id, "payload_sha256": digest,
            "source_head": event["source_head"], "source_tree": event["source_tree"],
        })
        self.state = "ERGEBNIS"; transitions.append(self.state)
        if result_sha != canonical_sha256({
            "event_id": event_id, "payload_sha256": digest,
            "source_head": event["source_head"], "source_tree": event["source_tree"],
        }):
            raise HeartbeatContractError("result reobservation mismatch")
        self.state = "REOBSERVATION"; transitions.append(self.state)
        previous = self.authority_ledger[-1]["record_sha256"] if self.authority_ledger else "GENESIS"
        record = {
            "schema": AUTHORITY_LEDGER_SCHEMA,
            "index": len(self.authority_ledger),
            "event_id": event_id,
            "result_sha256": result_sha,
            "previous_record_sha256": previous,
            "authority_scope": AUTHORITY_EFFECT_SCOPE,
            "external_effect": EXTERNAL_EFFECT,
        }
        record["record_sha256"] = canonical_sha256(record)
        self.authority_ledger.append(record)
        self.state = "AUTHORITY_EFFEKT"; transitions.append(self.state)
        self.state = "0"; transitions.append(self.state)
        if transitions != LIFECYCLE:
            raise HeartbeatContractError("work lifecycle mismatch")
        receipt = {
            "schema": WORK_RECEIPT_SCHEMA,
            "event_id": event_id,
            "payload_sha256": digest,
            "result_sha256": result_sha,
            "lifecycle": transitions,
            "local_authority_effect_reobserved": True,
            "repository_authority_effect_observed": False,
            "authority_effect_scope": AUTHORITY_EFFECT_SCOPE,
            "external_effect": EXTERNAL_EFFECT,
            "general_effect_ack_done": False,
        }
        receipt["receipt_sha256"] = canonical_sha256(receipt)
        self.payloads[event_id] = digest
        self.receipts[event_id] = copy.deepcopy(receipt)
        return receipt


@dataclass
class Collector:
    expected_total: int
    source_head: str
    source_tree: str
    events: list[dict[str, Any]] = field(default_factory=list)
    done: asyncio.Event = field(default_factory=asyncio.Event)
    failure: BaseException | None = None

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while len(self.events) < self.expected_total:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                if not line:
                    break
                heartbeat = normalize_heartbeat(json.loads(line.decode("utf-8")))
                if heartbeat["source_head"] != self.source_head or heartbeat["source_tree"] != self.source_tree:
                    raise HeartbeatContractError("collector source binding mismatch")
                digest = heartbeat_digest(heartbeat)
                self.events.append({
                    "heartbeat": heartbeat,
                    "heartbeat_sha256": digest,
                    "arrival_monotonic_ns": time.monotonic_ns(),
                })
                ack = {
                    "node_id": heartbeat["node_id"],
                    "sequence": heartbeat["sequence"],
                    "heartbeat_sha256": digest,
                    "semantic_work_triggered": False,
                    "external_effect": EXTERNAL_EFFECT,
                }
                writer.write(canonical_json_bytes(ack) + b"\n")
                await writer.drain()
                if len(self.events) == self.expected_total:
                    self.done.set()
        except BaseException as exc:
            self.failure = self.failure or exc
            self.done.set()
        finally:
            writer.close()
            await writer.wait_closed()


async def emit_heartbeats(
    *, host: str, port: int, node_id: str, pair_id: str, role: str,
    source_head: str, source_tree: str, start_monotonic_ns: int, count: int,
) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    previous = "GENESIS"
    try:
        for sequence in range(count):
            scheduled = start_monotonic_ns + sequence * HEARTBEAT_INTERVAL_NS
            await asyncio.sleep(max(0.0, (scheduled - time.monotonic_ns()) / 1_000_000_000))
            heartbeat = build_heartbeat(
                node_id=node_id, pair_id=pair_id, role=role, sequence=sequence,
                scheduled_monotonic_ns=scheduled, sent_monotonic_ns=time.monotonic_ns(),
                previous_heartbeat_sha256=previous,
                source_head=source_head, source_tree=source_tree,
            )
            digest = heartbeat_digest(heartbeat)
            writer.write(canonical_json_bytes(heartbeat) + b"\n")
            await writer.drain()
            ack = json.loads((await asyncio.wait_for(reader.readline(), timeout=3.0)).decode("utf-8"))
            if ack != {
                "node_id": node_id,
                "sequence": sequence,
                "heartbeat_sha256": digest,
                "semantic_work_triggered": False,
                "external_effect": EXTERNAL_EFFECT,
            }:
                raise HeartbeatContractError("heartbeat acknowledgement mismatch")
            previous = digest
    finally:
        writer.close()
        await writer.wait_closed()


def verify_history(events: Sequence[Mapping[str, Any]], count_per_node: int) -> dict[str, int | bool]:
    by_node = {node_id: [] for node_id, _, _ in NODE_SPECS}
    for record in events:
        heartbeat = normalize_heartbeat(record["heartbeat"])
        if heartbeat["node_id"] not in by_node or record["heartbeat_sha256"] != heartbeat_digest(heartbeat):
            raise HeartbeatContractError("unexpected heartbeat history")
        by_node[heartbeat["node_id"]].append(record)
    max_lateness = 0
    max_gap = 0
    for node_id, records in by_node.items():
        records.sort(key=lambda item: item["heartbeat"]["sequence"])
        if len(records) != count_per_node:
            raise HeartbeatContractError(f"heartbeat count mismatch for {node_id}")
        previous = "GENESIS"
        scheduled: int | None = None
        arrival: int | None = None
        for sequence, record in enumerate(records):
            heartbeat = record["heartbeat"]
            if heartbeat["sequence"] != sequence or heartbeat["previous_heartbeat_sha256"] != previous:
                raise HeartbeatContractError("heartbeat chain is not contiguous")
            if scheduled is not None and heartbeat["scheduled_monotonic_ns"] - scheduled != HEARTBEAT_INTERVAL_NS:
                raise HeartbeatContractError("heartbeat schedule is not exactly 1/s")
            lateness = max(0, heartbeat["sent_monotonic_ns"] - heartbeat["scheduled_monotonic_ns"])
            if lateness > MAX_SEND_LATENESS_NS:
                raise HeartbeatContractError("heartbeat lateness exceeds bound")
            max_lateness = max(max_lateness, lateness)
            if arrival is not None:
                max_gap = max(max_gap, record["arrival_monotonic_ns"] - arrival)
            previous = record["heartbeat_sha256"]
            scheduled = heartbeat["scheduled_monotonic_ns"]
            arrival = record["arrival_monotonic_ns"]
    return {
        "node_count": len(NODE_SPECS),
        "pair_count": 2,
        "total_heartbeats": len(events),
        "max_send_lateness_ns": max_lateness,
        "max_arrival_gap_ns": max_gap,
        "heartbeat_chain_verified": True,
        "scheduled_one_hertz_verified": True,
    }


async def run_demo(
    *, source_head: str, source_tree: str, output_dir: pathlib.Path,
    heartbeat_count: int, event_name: str, run_id: int,
) -> dict[str, Any]:
    _sha1(source_head, "source_head"); _sha1(source_tree, "source_tree")
    if heartbeat_count not in range(2, 11):
        raise HeartbeatContractError("heartbeat_count must be in 2..10")
    if event_name not in {"pull_request", "push", "workflow_dispatch", "local"}:
        raise HeartbeatContractError("unexpected event name")
    collector = Collector(len(NODE_SPECS) * heartbeat_count, source_head, source_tree)
    server = await asyncio.start_server(collector.handle, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    start_ns = time.monotonic_ns() + 250_000_000
    processes: list[asyncio.subprocess.Process] = []
    try:
        for node_id, pair_id, role in NODE_SPECS:
            processes.append(await asyncio.create_subprocess_exec(
                sys.executable, "-B", str(pathlib.Path(__file__).resolve()), "emit",
                "--host", host, "--port", str(port), "--node-id", node_id,
                "--pair-id", pair_id, "--role", role, "--source-head", source_head,
                "--source-tree", source_tree, "--start-monotonic-ns", str(start_ns),
                "--count", str(heartbeat_count),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            ))
        await asyncio.wait_for(collector.done.wait(), timeout=heartbeat_count + 6.0)
        if collector.failure:
            raise collector.failure
        for process in processes:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3.0)
            if process.returncode:
                raise HeartbeatTransportError((stderr + stdout).decode("utf-8", errors="replace"))
    finally:
        server.close(); await server.wait_closed()
        for process in processes:
            if process.returncode is None:
                process.terminate(); await process.wait()

    metrics = verify_history(collector.events, heartbeat_count)
    ring = WorkRing()
    for record in collector.events:
        ring.observe_heartbeat(record["heartbeat"])
    event = build_work_event(source_head=source_head, source_tree=source_tree)
    work_receipt = ring.execute(event)
    replay_identical = canonical_json_bytes(ring.execute(event)) == canonical_json_bytes(work_receipt)
    tampered = copy.deepcopy(event)
    tampered["payload"]["nonce"] = "heartbeat-work-tampered"
    tampered["payload_sha256"] = canonical_sha256(tampered["payload"])
    tamper_blocked = False
    try:
        ring.execute(tampered)
    except HeartbeatContractError:
        tamper_blocked = True
    if not replay_identical or not tamper_blocked or len(ring.authority_ledger) != 1:
        raise HeartbeatContractError("work-ring replay or tamper contract failed")

    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "heartbeats": output_dir / "heartbeats.jsonl",
        "work": output_dir / "work-receipt.json",
        "ledger": output_dir / "authority-ledger.json",
    }
    files["heartbeats"].write_bytes(b"".join(canonical_json_bytes(x) + b"\n" for x in collector.events))
    files["work"].write_bytes(canonical_json_bytes(work_receipt) + b"\n")
    files["ledger"].write_bytes(canonical_json_bytes(ring.authority_ledger) + b"\n")
    audit = {
        "schema": AUDIT_SCHEMA,
        "repository": os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"),
        "event": event_name,
        "run_id": run_id,
        "source_head": source_head,
        "source_tree": source_tree,
        "network_scope": NETWORK_SCOPE,
        "heartbeat_hz": HEARTBEAT_HZ,
        "heartbeat_role": HEARTBEAT_ROLE,
        "node_process_count": metrics["node_count"],
        "pair_count": metrics["pair_count"],
        "heartbeats_per_node": heartbeat_count,
        "total_heartbeats": metrics["total_heartbeats"],
        "heartbeat_chain_verified": True,
        "scheduled_one_hertz_verified": True,
        "scheduled_interval_ns": HEARTBEAT_INTERVAL_NS,
        "max_send_lateness_ns": metrics["max_send_lateness_ns"],
        "max_arrival_gap_ns": metrics["max_arrival_gap_ns"],
        "heartbeat_semantic_work_count": ring.heartbeat_semantic_work_count,
        "polling_count": ring.polling_count,
        "blind_retry_count": ring.blind_retry_count,
        "locally_constructed_content_bound_work_event_count": 1,
        "external_ingress_authentication_observed": False,
        "work_lifecycle": work_receipt["lifecycle"],
        "duplicate_event_replay_byte_identical": replay_identical,
        "event_id_payload_rebinding_blocked": tamper_blocked,
        "local_authority_effect_reobserved": True,
        "repository_authority_effect_observed": False,
        "authority_effect_scope": AUTHORITY_EFFECT_SCOPE,
        "external_effect": EXTERNAL_EFFECT,
        "general_effect_ack_done": False,
        "physical_hardware_execution_observed": False,
        "publication_observed": False,
        "deployment_observed": False,
        "pass": False,
        "final_pass": False,
        "heartbeats_sha256": sha256_ref(files["heartbeats"].read_bytes()),
        "work_receipt_sha256": sha256_ref(files["work"].read_bytes()),
        "authority_ledger_sha256": sha256_ref(files["ledger"].read_bytes()),
    }
    verify_audit(audit, source_head=source_head, source_tree=source_tree)
    (output_dir / "execution-receipt.json").write_bytes(canonical_json_bytes(audit) + b"\n")
    return audit


def verify_audit(value: Any, *, source_head: str, source_tree: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != AUDIT_SCHEMA:
        raise HeartbeatContractError("unexpected audit schema")
    if value.get("source_head") != _sha1(source_head, "source_head") or value.get("source_tree") != _sha1(source_tree, "source_tree"):
        raise HeartbeatContractError("audit source binding mismatch")
    if value.get("network_scope") != NETWORK_SCOPE or value.get("heartbeat_hz") != 1 or value.get("heartbeat_role") != HEARTBEAT_ROLE:
        raise HeartbeatContractError("audit heartbeat contract mismatch")
    if value.get("node_process_count") != 4 or value.get("pair_count") != 2:
        raise HeartbeatContractError("audit topology mismatch")
    if value.get("total_heartbeats") != 4 * value.get("heartbeats_per_node", -1):
        raise HeartbeatContractError("audit heartbeat total mismatch")
    for key in (
        "heartbeat_chain_verified", "scheduled_one_hertz_verified",
        "duplicate_event_replay_byte_identical", "event_id_payload_rebinding_blocked",
        "local_authority_effect_reobserved",
    ):
        if value.get(key) is not True:
            raise HeartbeatContractError(f"audit {key} must be true")
    if value.get("scheduled_interval_ns") != HEARTBEAT_INTERVAL_NS or value.get("work_lifecycle") != LIFECYCLE:
        raise HeartbeatContractError("audit schedule or lifecycle mismatch")
    if value.get("locally_constructed_content_bound_work_event_count") != 1:
        raise HeartbeatContractError("audit must execute exactly one work event")
    for key in ("heartbeat_semantic_work_count", "polling_count", "blind_retry_count"):
        if value.get(key) != 0:
            raise HeartbeatContractError(f"audit {key} must be zero")
    if value.get("repository_authority_effect_observed") is not False:
        raise HeartbeatContractError("audit may not manufacture repository authority effect")
    if value.get("external_ingress_authentication_observed") is not False:
        raise HeartbeatContractError(
            "audit may not manufacture external ingress authentication"
        )
    if value.get("authority_effect_scope") != AUTHORITY_EFFECT_SCOPE or value.get("external_effect") != EXTERNAL_EFFECT:
        raise HeartbeatContractError("audit authority or external effect mismatch")
    for key in (
        "general_effect_ack_done", "physical_hardware_execution_observed",
        "publication_observed", "deployment_observed", "pass", "final_pass",
    ):
        if value.get(key) is not False:
            raise HeartbeatContractError(f"audit {key} must remain false")
    for key in ("heartbeats_sha256", "work_receipt_sha256", "authority_ledger_sha256"):
        _sha256(value.get(key), key)
    return dict(value)


LEDGER_PROTECTION_SCHEMA = "qikvrt_mesh_heartbeat_ledger_protection_v1"
LEDGER_PROTECTION_COMPLETION_CLAIMS = {
    "PASS": False,
    "FINAL_PASS": False,
    "EFFECT_ACK_DONE": False,
    "MERGE": False,
    "APPROVAL": False,
    "DEPLOYMENT": False,
}


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def _effective_rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise HeartbeatContractError("effective rules response must be a paginated list")
    rules: list[dict[str, Any]] = []
    for page in value:
        if isinstance(page, list):
            items = page
        elif isinstance(page, dict):
            items = [page]
        else:
            raise HeartbeatContractError("effective rules page must be an array")
        if not all(isinstance(item, dict) for item in items):
            raise HeartbeatContractError("effective rule must be an object")
        rules.extend(items)
    return sorted(rules, key=canonical_json_bytes)


def _ruleset_details(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        value = value.get("rulesets")
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise HeartbeatContractError("ruleset details must be an object list")
    return sorted((dict(item) for item in value), key=canonical_json_bytes)


def _protection_receipt(
    *,
    repository: str,
    ledger_ref: str,
    source_head: str,
    source_run_id: str,
    phase: str,
    transition: str,
    classification: str,
    d0: int,
    reason: str,
    snapshot: dict[str, Any] | None,
    baseline_digest: str | None = None,
    observed_digest: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": LEDGER_PROTECTION_SCHEMA,
        "repository": repository,
        "ledger_ref": ledger_ref,
        "source_head": source_head,
        "source_run_id": source_run_id,
        "phase": phase,
        "ledger_transition": transition,
        "classification": classification,
        "d0": d0,
        "reason": reason,
        "protection_snapshot": snapshot,
        "protection_snapshot_sha256": canonical_sha256(snapshot) if snapshot is not None else None,
        "baseline_protection_snapshot_sha256": baseline_digest,
        "observed_protection_snapshot_sha256": observed_digest,
        "completion_claims": LEDGER_PROTECTION_COMPLETION_CLAIMS,
    }


def qualify_ledger_ref_protection(
    *,
    repository: str,
    ledger_ref: str,
    source_head: str,
    source_run_id: str,
    effective_rules: Any,
    ruleset_details: Any,
    phase: str,
    transition: str,
) -> dict[str, Any]:
    """Classify a read-only, platform-effective exact-ref protection observation."""
    try:
        rules = _effective_rules(effective_rules)
        details = _ruleset_details(ruleset_details)
    except HeartbeatContractError:
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REOBSERVE", d0=2,
            reason="RULESET_OBSERVATION_UNVERIFIABLE", snapshot=None,
        )

    groups: dict[tuple[str, str, int], set[str]] = {}
    try:
        for rule in rules:
            source_type = rule["ruleset_source_type"]
            source = rule["ruleset_source"]
            identifier = rule["ruleset_id"]
            rule_type = rule["type"]
            if (
                not isinstance(source_type, str) or not source_type
                or not isinstance(source, str) or not source
                or not _positive_int(identifier)
                or not isinstance(rule_type, str)
            ):
                raise HeartbeatContractError("effective ruleset identity is malformed")
            groups.setdefault((source_type, source, identifier), set()).add(rule_type)
    except (HeartbeatContractError, KeyError):
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REOBSERVE", d0=2,
            reason="RULESET_IDENTITY_UNVERIFIABLE", snapshot=None,
        )

    qualifying_groups = [
        group for group, rule_types in groups.items()
        if {"deletion", "non_fast_forward"}.issubset(rule_types)
    ]
    if len(qualifying_groups) != 1:
        snapshot = {
            "repository": repository, "ledger_ref": ledger_ref,
            "effective_rules": rules,
            "effective_rule_groups": [
                {"source_type": key[0], "source": key[1], "id": key[2],
                 "rule_types": sorted(value)}
                for key, value in sorted(groups.items())
            ],
            "ruleset_details": details,
        }
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REQUEST_AUTHORITY", d0=3,
            reason="EXACTLY_ONE_ACTIVE_PROTECTING_RULESET_REQUIRED", snapshot=snapshot,
        )

    source_type, source, identifier = qualifying_groups[0]
    matching_details = [detail for detail in details if detail.get("id") == identifier]
    if len(matching_details) != 1:
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REOBSERVE", d0=2,
            reason="RULESET_DETAIL_UNVERIFIABLE", snapshot=None,
        )
    detail = matching_details[0]
    conditions = detail.get("conditions")
    ref_name = conditions.get("ref_name") if isinstance(conditions, Mapping) else None
    include = _string_list(ref_name.get("include")) if isinstance(ref_name, Mapping) else None
    exclude = _string_list(ref_name.get("exclude")) if isinstance(ref_name, Mapping) else None
    snapshot = {
        "repository": repository, "ledger_ref": ledger_ref,
        "effective_rules_endpoint": (
            "GET /repos/{repository}/rules/branches/{ledger_ref_urlencoded}"
        ),
        "effective_rules": rules,
        "selected_ruleset": {
            "source_type": source_type, "source": source, "id": identifier,
            "effective_rule_types": sorted(groups[qualifying_groups[0]]),
        },
        "ruleset_detail": detail,
        "include": include,
        "exclude": exclude,
        "bypass_actors_present": "bypass_actors" in detail,
        "bypass_actors": detail.get("bypass_actors"),
        "current_user_can_bypass": detail.get("current_user_can_bypass"),
    }
    if (
        detail.get("source_type") != source_type
        or detail.get("source") != source
        or detail.get("target") != "branch"
        or detail.get("enforcement") != "active"
        or include is None
        or exclude is None
    ):
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REOBSERVE", d0=2,
            reason="RULESET_DETAIL_UNVERIFIABLE", snapshot=snapshot,
        )
    if "bypass_actors" not in detail or not isinstance(detail["bypass_actors"], list):
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REOBSERVE", d0=2,
            reason="BYPASS_VISIBILITY_UNVERIFIABLE", snapshot=snapshot,
        )
    if not isinstance(detail.get("current_user_can_bypass"), str):
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REOBSERVE", d0=2,
            reason="WRITER_BYPASS_VISIBILITY_UNVERIFIABLE", snapshot=snapshot,
        )
    if detail["bypass_actors"] or detail["current_user_can_bypass"] != "never":
        return _protection_receipt(
            repository=repository, ledger_ref=ledger_ref, source_head=source_head,
            source_run_id=source_run_id, phase=phase, transition=transition,
            classification="REQUEST_AUTHORITY", d0=3,
            reason="BYPASSABLE_LEDGER_PROTECTION", snapshot=snapshot,
        )
    return _protection_receipt(
        repository=repository, ledger_ref=ledger_ref, source_head=source_head,
        source_run_id=source_run_id, phase=phase, transition=transition,
        classification="QUALIFIED", d0=0,
        reason="EXACT_LEDGER_REF_PROTECTION_QUALIFIED", snapshot=snapshot,
    )


def compare_ledger_ref_protection(
    initial: Any, observed: Any, *, phase: str, transition: str
) -> dict[str, Any]:
    """Compare two sealed D0=0 observations without trusting their declarations."""
    def valid(value: Any, expected_phase: str) -> bool:
        if not isinstance(value, Mapping) or value.get("schema") != LEDGER_PROTECTION_SCHEMA:
            return False
        if value.get("phase") != expected_phase or value.get("classification") != "QUALIFIED" or value.get("d0") != 0:
            return False
        snapshot = value.get("protection_snapshot")
        return (
            isinstance(snapshot, Mapping)
            and value.get("protection_snapshot_sha256") == canonical_sha256(snapshot)
            and value.get("completion_claims") == LEDGER_PROTECTION_COMPLETION_CLAIMS
        )

    if not valid(initial, "INITIAL") or not valid(observed, phase):
        context = initial if isinstance(initial, Mapping) else observed
        return _protection_receipt(
            repository=str(context.get("repository", "")) if isinstance(context, Mapping) else "",
            ledger_ref=str(context.get("ledger_ref", "")) if isinstance(context, Mapping) else "",
            source_head=str(context.get("source_head", "")) if isinstance(context, Mapping) else "",
            source_run_id=str(context.get("source_run_id", "")) if isinstance(context, Mapping) else "",
            phase=phase, transition=transition, classification="REOBSERVE", d0=2,
            reason="LEDGER_REF_CONTROL_RECEIPT_UNVERIFIABLE", snapshot=None,
        )
    initial_digest = initial["protection_snapshot_sha256"]
    observed_digest = observed["protection_snapshot_sha256"]
    same_binding = all(
        initial.get(key) == observed.get(key)
        for key in ("repository", "ledger_ref", "source_head", "source_run_id")
    )
    if not same_binding or initial_digest != observed_digest:
        return _protection_receipt(
            repository=observed["repository"], ledger_ref=observed["ledger_ref"],
            source_head=observed["source_head"], source_run_id=observed["source_run_id"],
            phase=phase, transition=transition, classification="REOBSERVE", d0=2,
            reason="LEDGER_REF_CONTROL_SNAPSHOT_DRIFT",
            snapshot=dict(observed["protection_snapshot"]),
            baseline_digest=initial_digest, observed_digest=observed_digest,
        )
    return _protection_receipt(
        repository=observed["repository"], ledger_ref=observed["ledger_ref"],
        source_head=observed["source_head"], source_run_id=observed["source_run_id"],
        phase=phase, transition=transition, classification="QUALIFIED", d0=0,
        reason="LEDGER_REF_CONTROL_SNAPSHOT_STABLE",
        snapshot=dict(observed["protection_snapshot"]),
    )


def _write_control_receipt(path: pathlib.Path, receipt: Mapping[str, Any]) -> None:
    path.write_bytes(canonical_json_bytes(receipt) + b"\n")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--source-head", required=True); demo.add_argument("--source-tree", required=True)
    demo.add_argument("--output-dir", type=pathlib.Path, required=True)
    demo.add_argument("--heartbeat-count", type=int, default=4)
    demo.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", "local"))
    demo.add_argument("--run-id", type=int, default=int(os.environ.get("GITHUB_RUN_ID", "0")))
    emit = sub.add_parser("emit", help=argparse.SUPPRESS)
    for name in ("host", "node-id", "pair-id", "role", "source-head", "source-tree"):
        emit.add_argument("--" + name, required=True)
    emit.add_argument("--port", type=int, required=True)
    emit.add_argument("--start-monotonic-ns", type=int, required=True)
    emit.add_argument("--count", type=int, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--receipt", type=pathlib.Path, required=True)
    verify.add_argument("--source-head", required=True); verify.add_argument("--source-tree", required=True)
    qualify = sub.add_parser("qualify-ledger-ref-protection")
    qualify.add_argument("--repository", required=True)
    qualify.add_argument("--ledger-ref", required=True)
    qualify.add_argument("--source-head", required=True)
    qualify.add_argument("--source-run-id", required=True)
    qualify.add_argument("--phase", choices=("INITIAL", "PRE_PUSH", "POST_READBACK"), required=True)
    qualify.add_argument("--ledger-transition", required=True)
    qualify.add_argument("--effective-rules", type=pathlib.Path, required=True)
    qualify.add_argument("--ruleset-details", type=pathlib.Path, required=True)
    qualify.add_argument("--out", type=pathlib.Path, required=True)
    compare = sub.add_parser("compare-ledger-ref-protection")
    compare.add_argument("--initial", type=pathlib.Path, required=True)
    compare.add_argument("--observed", type=pathlib.Path, required=True)
    compare.add_argument("--phase", choices=("PRE_PUSH", "POST_READBACK"), required=True)
    compare.add_argument("--ledger-transition", required=True)
    compare.add_argument("--out", type=pathlib.Path, required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "qualify-ledger-ref-protection":
        try:
            receipt = qualify_ledger_ref_protection(
                repository=args.repository, ledger_ref=args.ledger_ref,
                source_head=args.source_head, source_run_id=args.source_run_id,
                effective_rules=json.loads(args.effective_rules.read_text(encoding="utf-8")),
                ruleset_details=json.loads(args.ruleset_details.read_text(encoding="utf-8")),
                phase=args.phase, transition=args.ledger_transition,
            )
        except (OSError, json.JSONDecodeError):
            receipt = _protection_receipt(
                repository=args.repository, ledger_ref=args.ledger_ref,
                source_head=args.source_head, source_run_id=args.source_run_id,
                phase=args.phase, transition=args.ledger_transition,
                classification="REOBSERVE", d0=2,
                reason="RULESET_OBSERVATION_UNAVAILABLE", snapshot=None,
            )
        _write_control_receipt(args.out, receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0 if receipt["d0"] == 0 else 2
    if args.command == "compare-ledger-ref-protection":
        try:
            receipt = compare_ledger_ref_protection(
                json.loads(args.initial.read_text(encoding="utf-8")),
                json.loads(args.observed.read_text(encoding="utf-8")),
                phase=args.phase, transition=args.ledger_transition,
            )
        except (OSError, json.JSONDecodeError):
            receipt = _protection_receipt(
                repository="", ledger_ref="", source_head="", source_run_id="",
                phase=args.phase, transition=args.ledger_transition,
                classification="REOBSERVE", d0=2,
                reason="LEDGER_REF_CONTROL_RECEIPT_UNAVAILABLE", snapshot=None,
            )
        _write_control_receipt(args.out, receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0 if receipt["d0"] == 0 else 2
    if args.command == "emit":
        asyncio.run(emit_heartbeats(
            host=args.host, port=args.port, node_id=args.node_id, pair_id=args.pair_id,
            role=args.role, source_head=args.source_head, source_tree=args.source_tree,
            start_monotonic_ns=args.start_monotonic_ns, count=args.count,
        ))
        return 0
    if args.command == "demo":
        value = asyncio.run(run_demo(
            source_head=args.source_head, source_tree=args.source_tree,
            output_dir=args.output_dir, heartbeat_count=args.heartbeat_count,
            event_name=args.event, run_id=args.run_id,
        ))
    else:
        value = verify_audit(
            json.loads(args.receipt.read_text(encoding="utf-8")),
            source_head=args.source_head, source_tree=args.source_tree,
        )
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
