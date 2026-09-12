#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Reflexive system verification for the QIK-VRT real multi-pair mesh.

This tool verifies an execution receipt produced by ``qikvrt_real_mesh.py``
against the declared contract in ``state/mesh/QIKVRT_REAL_MESH_V1.json``,
applies the REFLEXIVE_FINDING_WORKFLOW_STANDARD, and emits a structured
audit receipt.

Receipt, topology, route, protocol and independently read ledger bytes must bind
an externally supplied exact source. Hashes establish integrity, not producer
authenticity or public/platform liveness. Runtime claims remain scoped to the
bound loopback execution; no receipt-only check proves an external effect.

Usage::

    python3 -B tools/qikvrt_real_mesh_system_verification.py verify \\
        --receipt path/to/EXECUTION_RECEIPT.json

    python3 -B tools/qikvrt_real_mesh_system_verification.py run \\
        --source-head <sha1> --source-tree <sha1>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import os
import stat
import subprocess
import copy
import re
import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_PATH = ROOT / "state" / "mesh" / "QIKVRT_REAL_MESH_V1.json"
REFLEXIVE_STANDARD_PATH = ROOT / "REFLEXIVE_FINDING_WORKFLOW_STANDARD.json"

VERIFICATION_RECEIPT_SCHEMA = "qikvrt_real_mesh_system_verification_v1"
AUDIT_SCHEMA = "qikvrt_real_mesh_system_audit_v1"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


class VerificationError(ValueError):
    """A contract violation discovered during reflexive verification."""


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return a canonical SHA-256 identifier in ``sha256:<hex>`` format.

    This matches the format produced by ``qikvrt_real_mesh.canonical_sha256``
    and stored in execution receipts.
    """
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_contract() -> dict[str, Any]:
    """Load and lightly validate the declared mesh contract."""
    try:
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"cannot load contract {CONTRACT_PATH}: {exc}"
        ) from exc
    if raw.get("schema") != "qikvrt_real_mesh_contract_v1":
        raise VerificationError("contract schema mismatch")
    if raw.get("mesh_id") != "QIKVRT_REAL_MULTI_PAIR_MESH_V1":
        raise VerificationError("contract mesh_id mismatch")
    return raw


def load_reflexive_standard() -> dict[str, Any]:
    """Load the REFLEXIVE_FINDING_WORKFLOW_STANDARD."""
    try:
        return json.loads(REFLEXIVE_STANDARD_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"cannot load reflexive standard {REFLEXIVE_STANDARD_PATH}: {exc}"
        ) from exc


def _verify_declared_fields(
    receipt: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    """Return a list of findings.  An empty list means the receipt is conformant."""
    findings: list[str] = []

    def _check(condition: bool, finding: str) -> None:
        if not condition:
            findings.append(finding)

    # --- schema and identity ---
    _check(
        receipt.get("schema") == "qikvrt_real_mesh_execution_receipt_v1",
        "receipt.schema must be qikvrt_real_mesh_execution_receipt_v1",
    )
    _check(
        receipt.get("mesh_id") == contract["mesh_id"],
        f"receipt.mesh_id must be {contract['mesh_id']}",
    )

    # --- minimum_topology ---
    topo = contract.get("minimum_topology", {})
    _check(
        type(receipt.get("pair_count")) is int
        and receipt["pair_count"] >= topo.get("pair_count", 2),
        f"receipt.pair_count must be >= {topo.get('pair_count', 2)}",
    )
    _check(
        type(receipt.get("node_process_count")) is int
        and receipt["node_process_count"] >= topo.get("node_process_count", 4),
        f"receipt.node_process_count must be >= {topo.get('node_process_count', 4)}",
    )
    _check(
        receipt.get("redundant_path_observed") is True,
        "receipt.redundant_path_observed must be true (contract requires redundant_routes_required)",
    )

    # --- transport ---
    transport = contract.get("transport", {})
    _check(
        receipt.get("network_scope") == transport.get("network_scope"),
        f"receipt.network_scope must be {transport.get('network_scope')}",
    )
    _check(
        receipt.get("event_model") == transport.get("event_model"),
        f"receipt.event_model must be {transport.get('event_model')}",
    )

    # --- restart replay ---
    replay = receipt.get("restart_replay", {})
    _check(
        replay.get("same_terminal_receipt") is True,
        "receipt.restart_replay.same_terminal_receipt must be true"
        " (contract: idempotent_exact_replay)",
    )
    _check(
        replay.get("ledger_record_count_unchanged") is True,
        "receipt.restart_replay.ledger_record_count_unchanged must be true"
        " (contract: append_only_hash_linked_ledger + restart_reconstruction)",
    )

    # --- completion_claims ---
    claims = receipt.get("completion_claims", {})
    required_true = {
        "real_multi_pair_mesh_runtime_executed",
        "independent_tcp_node_processes_observed",
        "multi_hop_delivery_reobserved",
        "acknowledgement_return_path_observed",
        "append_only_restart_persistence_observed",
        "bounded_loopback_effect_ack_done",
    }
    required_false = {
        "general_effect_ack_done",
        "general_internet_reachability",
        "production_deployment",
        "physical_hardware_execution",
        "authority_mirror_synchronization",
        "authority_mirror_equality_claimed",
        "merge",
        "PASS",
        "FINAL_PASS",
    }
    for field in sorted(required_true):
        _check(
            claims.get(field) is True,
            f"receipt.completion_claims.{field} must be true",
        )
    for field in sorted(required_false):
        _check(
            claims.get(field) is False,
            f"receipt.completion_claims.{field} must be false"
            " (effect boundary violation)",
        )

    # --- effect boundary ---
    eb = contract.get("effect_boundary", {})
    _check(
        receipt.get("external_effect") == "NONE",
        "receipt.external_effect must be NONE",
    )
    for eb_field in (
        "general_effect_ack_done",
        "general_internet_reachability",
        "production_deployment",
        "physical_hardware_execution",
        "authority_mirror_synchronization",
        "authority_mirror_equality_claimed",
        "merge",
        "PASS",
        "FINAL_PASS",
    ):
        declared = eb.get(eb_field)
        if declared is False:
            _check(
                claims.get(eb_field) is False,
                f"effect_boundary.{eb_field} is false in contract"
                f" but receipt claims it true",
            )

    # --- effect_ack ---
    eff = contract.get("effect_ack", {})
    _check(
        receipt.get("effect_ack_scope") == eff.get("completion_scope"),
        f"receipt.effect_ack_scope must be {eff.get('completion_scope')}",
    )
    # all hop ledgers must be reobserved
    routes = receipt.get("routes", [])
    _check(
        len(routes) >= 2,
        "receipt must contain at least two route observations",
    )
    for i, route in enumerate(routes):
        obs = route.get("observation", {})
        path = obs.get("path") or obs.get("hops") or []
        _check(
            isinstance(path, list) and len(path) >= 2,
            f"route[{i}].observation.path must contain at least two entries",
        )

    return findings


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise VerificationError(reason)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        _require(key not in value, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _decode(raw: bytes) -> Any:
    def reject_number(value: str) -> None:
        raise VerificationError(f"non-finite JSON value: {value}")
    return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=reject_number)


def _read_regular(path: pathlib.Path) -> bytes:
    # Read-only and bounded. Neither a missing directory nor ledger is created.
    for part in (path, *path.parents):
        _require(not part.is_symlink(), f"symlink evidence path forbidden: {part}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        before = os.fstat(handle.fileno())
        _require(stat.S_ISREG(before.st_mode), "evidence must be a regular file")
        raw = handle.read(16 * 1024 * 1024 + 1)
        after = os.fstat(handle.fileno())
        _require(len(raw) <= 16 * 1024 * 1024, "evidence size bound exceeded")
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        _require(all(getattr(before, k) == getattr(after, k) for k in fields),
                 "evidence changed while reading")
    return raw


def _ledger_records(path: pathlib.Path, node_id: str) -> list[dict[str, Any]]:
    from tools import qikvrt_real_mesh as mesh
    raw = _read_regular(path)
    _require(bool(raw) and raw.endswith(b"\n"), "ledger is empty or truncated")
    lines = raw.splitlines()
    _require(len(lines) <= 4096, "ledger record bound exceeded")
    records = []
    previous = None
    seen: set[tuple[str, str]] = set()
    for sequence, line in enumerate(lines, 1):
        record = _decode(line)
        _require(isinstance(record, dict), "ledger record must be an object")
        _require(record["schema"] == mesh.LEDGER_RECORD_SCHEMA and record["node_id"] == node_id,
                 "ledger identity mismatch")
        _require(type(record["sequence"]) is int and record["sequence"] == sequence,
                 "ledger sequence mismatch")
        _require(record["previous_record_sha256"] == previous, "ledger predecessor mismatch")
        _require(record["record_sha256"] == mesh.canonical_sha256(
            {k: v for k, v in record.items() if k != "record_sha256"}), "ledger hash mismatch")
        event, message_id = record["event"], mesh._identifier(record["message_id"], "ledger.message_id")
        _require(event in {"ACCEPTED", "COMPLETED"}, "nonterminal/HELD ledger cannot prove completion")
        _require((event, message_id) not in seen, "duplicate ledger effect record")
        if event == "COMPLETED":
            _require(("ACCEPTED", message_id) in seen, "completion precedes acceptance")
        seen.add((event, message_id))
        records.append(record)
        previous = record["record_sha256"]
    return records


def _verify_witnesses(receipt: dict[str, Any], contract: dict[str, Any], *,
                      expected_head: str | None, expected_tree: str | None,
                      ledger_dir: pathlib.Path | None) -> None:
    from tools import qikvrt_real_mesh as mesh
    from src.qikvrt_effect_ack import ResponsibilityProtocol, EffectState

    _require(contract.get("schema") == "qikvrt_real_mesh_contract_v1"
             and contract.get("mesh_id") == mesh.MESH_ID, "contract identity mismatch")
    for field, expected in (("source_head", expected_head), ("source_tree", expected_tree)):
        mesh._sha1(expected, f"independent expected {field}")
        mesh._sha1(receipt.get(field), f"receipt.{field}")
        _require(receipt[field] == expected, f"receipt.{field} differs from independent expected subject")
    mesh._sha256(receipt.get("receipt_sha256"), "receipt.receipt_sha256")
    _require(receipt["receipt_sha256"] == mesh.canonical_sha256(
        {k: v for k, v in receipt.items() if k != "receipt_sha256"}), "receipt.receipt_sha256 mismatch")
    topology = mesh.normalize_topology(receipt["topology"])
    _require(receipt["topology"] == topology, "topology is not canonical")
    _require(receipt["topology_sha256"] == mesh.canonical_sha256(topology), "topology hash mismatch")
    nodes = {node["node_id"]: node for node in topology["nodes"]}
    _require(len({node["instance_id"] for node in nodes.values()}) == len(nodes), "duplicate node instance")
    _require(receipt["node_process_count"] == len(nodes), "node_process_count contradicts topology")
    _require(receipt["pair_count"] == len({n["pair_id"] for n in nodes.values()}), "pair_count contradicts topology")
    _require(receipt["pair_states"] == mesh._pair_divergence(topology), "pair_states contradict topology")
    _require(receipt["transport"] == "TCP", "transport must be TCP")
    for node in nodes.values():
        if node["role"] == "AUTHORITY":
            _require(node["root_tree_sha"] == expected_tree, "Authority node tree differs from source tree")
    _require(ledger_dir is not None, "independent node ledger directory is required")
    records = {nid: _ledger_records(pathlib.Path(ledger_dir) / f"{nid}.jsonl", nid) for nid in nodes}
    routes = receipt["routes"]
    _require(isinstance(routes, list) and 2 <= len(routes) <= mesh.MAX_NODES, "route count outside bound")
    paths, messages, terminal_hashes, covered = set(), set(), {}, {nid: set() for nid in nodes}
    prefix_counts = {}
    for route in routes:
        msg = mesh.normalize_message(route["message"])
        _require(msg == route["message"] and msg["hop_index"] == 0 and msg["receipt_chain"] == [],
                 "route must carry canonical origin message")
        _require(msg["topology"] == topology, "route topology mismatch")
        _require(msg["payload"]["input_binding"] == {
            "source_head": expected_head, "source_tree": expected_tree, "external_effect": "NONE"},
            "message source binding mismatch (predecessor evidence forbidden)")
        path, mid = tuple(msg["route"]), msg["message_id"]
        _require(path not in paths and mid not in messages, "duplicate route or message identity")
        paths.add(path); messages.add(mid)
        obs = route["observation"]
        _require(obs["complete_route_reobserved"] is True, "route readback incomplete")
        for key, expected in (("path", list(path)), ("message_id", mid),
                              ("route_id", msg["route_id"]), ("payload_sha256", msg["payload_sha256"])):
            _require(obs[key] == expected, f"route observation {key} mismatch")
        chain, observations = obs["hop_receipt_sha256s"], obs["node_observations"]
        _require(isinstance(chain, list) and isinstance(observations, list)
                 and len(chain) == len(path) == len(observations), "missing hop readbacks")
        terminal = None
        for i, (nid, observation) in enumerate(zip(path, observations)):
            mesh._sha256(chain[i], "hop hash")
            node = nodes[nid]
            for key in ("node_id", "pair_id", "role", "root_tree_sha"):
                _require(observation[key] == node[key], f"hop observation {key} mismatch")
            _require(observation["accepted_and_completed_reobserved"] is True, "hop not reobserved")
            _require(observation["hop_receipt_sha256"] == chain[i], "observed hop hash mismatch")
            count = observation["ledger_record_count"]
            _require(type(count) is int and 2 <= count <= len(records[nid]), "ledger prefix count invalid")
            prefix = records[nid][:count]
            _require(prefix[-1]["record_sha256"] == observation["ledger_tip_sha256"], "ledger prefix tip mismatch")
            accepted = [r for r in prefix if r["event"] == "ACCEPTED" and r["message_id"] == mid]
            completed = [r for r in prefix if r["event"] == "COMPLETED" and r["message_id"] == mid]
            _require(len(accepted) == len(completed) == 1, "hop accepted/completed witness absent")
            inbound = copy.deepcopy(msg); inbound["hop_index"] = i; inbound["receipt_chain"] = chain[:i]
            inbound_hash = mesh.canonical_sha256(mesh.normalize_message(inbound))
            accepted = accepted[0]["accepted"]
            hop = accepted["hop_receipt"]
            _require(accepted["message_sha256"] == inbound_hash, "ledger inbound message mismatch")
            _require(accepted["hop_receipt_sha256"] == chain[i] == mesh.canonical_sha256(hop), "ledger hop hash mismatch")
            expected_hop = {**{k: node[k] for k in ("node_id", "pair_id", "role", "repository", "instance_id", "root_tree_sha")},
                "schema": mesh.HOP_RECEIPT_SCHEMA, "mesh_id": mesh.MESH_ID, "message_id": mid,
                "route_id": msg["route_id"], "hop_index": i, "inbound_message_sha256": inbound_hash,
                "predecessor_hop_receipt_sha256": chain[i-1] if i else None,
                "payload_sha256": msg["payload_sha256"], "observed_effect": "MESH_MESSAGE_ACCEPTED_AND_LEDGERED",
                "network_scope": mesh.NETWORK_SCOPE, "external_effect": "NONE"}
            _require(type(hop["hop_index"]) is int and all(hop.get(k) == v for k,v in expected_hop.items()),
                     "ledger hop identity/causal binding mismatch")
            response = completed[0]["response"]
            expected_terminal = {"schema": mesh.TERMINAL_RECEIPT_SCHEMA, "mesh_id": mesh.MESH_ID,
                "message_id": mid, "route_id": msg["route_id"], "payload_sha256": msg["payload_sha256"],
                "hop_receipt_sha256s": chain, "path": list(path), "final_node_id": path[-1],
                "network_scope": mesh.NETWORK_SCOPE, "external_effect": "NONE",
                "effect_state": "EFFECT_ACK_CONTINUE",
                "next_required_check": "REOBSERVE_ALL_NODE_LEDGERS_AND_FINALIZE_BOUND_EFFECT_ACK"}
            _require(all(response.get(k) == v for k,v in expected_terminal.items())
                and response.get("transport_ack") is True and response.get("ordinary_release") is False
                and response.get("authority_mirror_synchronization") is False
                and response.get("general_internet_reachability") is False, "terminal transport/effect boundary mismatch")
            _require(terminal is None or terminal == response, "inconsistent terminal across hop ledgers")
            terminal = response
            covered[nid].add(mid); prefix_counts[(nid,mid)] = count
        terminal_hashes[mid] = mesh.canonical_sha256(terminal)
        ack = route["bounded_effect_ack"]
        _require(ack["state"] == "EFFECT_ACK_DONE" and ack["ordinary_release"] is True, "bounded effect ack not DONE")
        protocol = ResponsibilityProtocol.from_dict(ack["responsibility_protocol"])
        _require(protocol.state is EffectState.EFFECT_ACK_DONE and protocol.ordinary_release is True,
                 "responsibility protocol not DONE")
        _require(protocol.input_id == mid and protocol.input_hash == msg["payload_sha256"]
                 and protocol.responsibility_owner == mesh.MESH_ID, "protocol input/owner mismatch")
        _require(set(protocol.evidence_refs) == set(protocol.required_evidence_refs) == set(chain)
                 and len(protocol.evidence_refs) == len(protocol.required_evidence_refs) == len(chain),
                 "protocol does not bind exactly all hop evidence")
    for nid in nodes:
        _require({r["message_id"] for r in records[nid]} == covered[nid]
                 and len(records[nid]) == 2 * len(covered[nid]) and bool(covered[nid]),
                 "unaccounted/missing node ledger effects")
    replay = receipt["restart_replay"]
    _require(replay["observed"] is True, "restart not observed")
    mid, nid = replay["message_id"], replay["node_id"]
    _require(mid in messages and (nid,mid) in prefix_counts, "restart subject not observed")
    _require(type(replay["record_count_before"]) is int and type(replay["record_count_after"]) is int
             and replay["record_count_before"] == replay["record_count_after"] == prefix_counts[(nid,mid)],
             "restart ledger counts contradict unchanged-record claim")
    _require(replay["terminal_sha256_before"] == replay["terminal_sha256_after"] == terminal_hashes[mid],
             "restart terminal bytes differ")
    before, after = replay["processes_before"], replay["processes_after"]
    for processes in (before,after):
        _require(isinstance(processes,dict) and set(processes) == set(nodes), "process inventory incomplete")
        _require(all(type(pid) is int and pid > 0 for pid in processes.values())
                 and len(set(processes.values())) == len(nodes), "process identities not independent")
    _require(before[nid] != after[nid] and all(before[k] == after[k] for k in nodes if k != nid),
             "restart process transition not witnessed")


def verify_receipt(receipt: Any, contract: dict[str, Any], *,
                   expected_head: str | None = None, expected_tree: str | None = None,
                   ledger_dir: pathlib.Path | None = None) -> list[str]:
    """Fail closed without independent subject binding and actual ledger readback.

    Unit callers may supply synthetic subjects explicitly. Platform users must
    bind these expectations from authoritative Git observations, not the receipt.
    """
    findings: list[str] = []
    try:
        _require(isinstance(receipt,dict), "receipt must be an object")
        findings.extend(_verify_declared_fields(receipt,contract))
        _verify_witnesses(receipt,contract,expected_head=expected_head,
                          expected_tree=expected_tree,ledger_dir=ledger_dir)
    except (ValueError, TypeError, KeyError, AttributeError, OSError, IndexError, RecursionError) as exc:
        findings.append(f"INVALID_OR_INCOMPLETE_MESH_EVIDENCE: {type(exc).__name__}: {exc}")
    return findings


def build_audit_receipt(
    *,
    receipt_path: str | None,
    receipt: dict[str, Any],
    contract: dict[str, Any],
    findings: list[str],
    reflexive_standard: dict[str, Any],
    expected_head: str | None = None,
    expected_tree: str | None = None,
    ledger_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Reverify before emitting an audit; caller-provided [] is not evidence."""
    findings = list(dict.fromkeys([*findings, *verify_receipt(
        receipt, contract, expected_head=expected_head,
        expected_tree=expected_tree, ledger_dir=ledger_dir)]))
    receipt = receipt if isinstance(receipt, dict) else {}
    status = "PASS" if not findings else "BLOCK"
    audit: dict[str, Any] = {
        "schema": AUDIT_SCHEMA,
        "mesh_id": contract.get("mesh_id"),
        "verified_at": _utc_now(),
        "receipt_source": receipt_path or "in-memory",
        "source_head": receipt.get("source_head"),
        "source_tree": receipt.get("source_tree"),
        "contract_path": str(CONTRACT_PATH.relative_to(ROOT)),
        "contract_schema": contract.get("schema"),
        "reflexive_standard_id": reflexive_standard.get("id"),
        "reflexive_standard_status": reflexive_standard.get("status"),
        "finding_count": len(findings),
        "findings": findings,
        "status": status,
        "effect_boundary_preserved": not any(
            "effect boundary" in f or "must be false" in f for f in findings
        ),
        "bounded_loopback_effect_ack_scope_confirmed": not findings and receipt.get("effect_ack_scope")
        == "BOUNDED_LOOPBACK_MULTI_PAIR_MESSAGE_DELIVERY_ONLY",
        "general_effect_ack_done": False,
        "external_effect": "NONE",
        "transport_ack_is_effect_ack": False,
        "verification_scope": "EXACT_SOURCE_RECEIPT_AND_NODE_LEDGER_BYTES_ONLY",
        "producer_authenticity_independently_proven": False,
        "live_platform_and_repository_mesh_verified": False,
        "expected_head": expected_head,
        "expected_tree": expected_tree,
    }
    audit["audit_sha256"] = canonical_sha256(audit)
    return audit


def run_and_verify(
    *,
    source_head: str,
    source_tree: str,
    workdir: pathlib.Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Execute the real mesh demo and verify the resulting receipt."""
    from tools import qikvrt_real_mesh as mesh  # noqa: PLC0415

    resolved_workdir = workdir or pathlib.Path(
        tempfile.mkdtemp(prefix="qikvrt-real-mesh-sysverify-")
    )
    receipt = mesh.run_demo(
        resolved_workdir,
        source_head=source_head,
        source_tree=source_tree,
    )
    contract = load_contract()
    findings = verify_receipt(receipt, contract, expected_head=source_head,
        expected_tree=source_tree, ledger_dir=resolved_workdir / "ledgers")
    return receipt, contract, findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _verify_command(args: argparse.Namespace) -> int:
    try:
        raw = _decode(_read_regular(pathlib.Path(args.receipt)))
    except (OSError, ValueError, RecursionError) as exc:
        print(f"BLOCK: cannot load receipt: {exc}", file=sys.stderr)
        return 2

    try:
        contract = load_contract()
        reflexive_standard = load_reflexive_standard()
    except VerificationError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2

    findings = verify_receipt(raw, contract, expected_head=args.expected_head,
        expected_tree=args.expected_tree, ledger_dir=pathlib.Path(args.ledger_dir))
    audit = build_audit_receipt(
        receipt_path=args.receipt,
        receipt=raw,
        expected_head=args.expected_head, expected_tree=args.expected_tree,
        ledger_dir=pathlib.Path(args.ledger_dir),
        contract=contract,
        findings=findings,
        reflexive_standard=reflexive_standard,
    )

    encoded = json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")

    findings = audit["findings"]
    if findings:
        print(
            f"BLOCK: {len(findings)} finding(s) — reflexive correction required",
            file=sys.stderr,
        )
        for i, f in enumerate(findings, 1):
            print(f"  [{i}] {f}", file=sys.stderr)
        return 2

    print("PASS: all declared contract fields verified", file=sys.stderr)
    return 0


def _run_command(args: argparse.Namespace) -> int:
    if not SHA1_RE.fullmatch(args.source_head):
        print("BLOCK: --source-head must be a 40-char lowercase hex SHA-1", file=sys.stderr)
        return 2
    if not SHA1_RE.fullmatch(args.source_tree):
        print("BLOCK: --source-tree must be a 40-char lowercase hex SHA-1", file=sys.stderr)
        return 2

    # The executable CLI binds the actual checkout, not a caller's label.
    try:
        observed = subprocess.check_output(
            ["git", "rev-parse", "HEAD", "HEAD^{tree}"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL, timeout=10).splitlines()
        _require(observed == [args.source_head, args.source_tree], "checkout source mismatch")
        _require(not subprocess.check_output(["git", "status", "--porcelain"],
            cwd=ROOT, text=True, timeout=10).strip(), "checkout has uncommitted changes")
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    workdir = pathlib.Path(args.workdir) if args.workdir else pathlib.Path(
        tempfile.mkdtemp(prefix="qikvrt-real-mesh-sysverify-"))

    try:
        contract = load_contract()
        reflexive_standard = load_reflexive_standard()
    except VerificationError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2

    try:
        receipt, _contract, findings = run_and_verify(
            source_head=args.source_head,
            source_tree=args.source_tree,
            workdir=workdir,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"BLOCK: mesh execution failed: {exc}", file=sys.stderr)
        return 2

    (workdir / "EXECUTION_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    audit = build_audit_receipt(
        receipt_path=str(workdir / "EXECUTION_RECEIPT.json"),
        receipt=receipt,
        expected_head=args.source_head, expected_tree=args.source_tree,
        ledger_dir=workdir / "ledgers",
        contract=contract,
        findings=findings,
        reflexive_standard=reflexive_standard,
    )

    encoded = json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")

    findings = audit["findings"]
    if findings:
        print(
            f"BLOCK: {len(findings)} finding(s) — reflexive correction required",
            file=sys.stderr,
        )
        for i, f in enumerate(findings, 1):
            print(f"  [{i}] {f}", file=sys.stderr)
        return 2

    print("PASS: real mesh executed and all contract fields verified", file=sys.stderr)
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="verify an existing execution receipt")
    verify.add_argument("--receipt", required=True, help="path to execution receipt JSON")
    verify.add_argument("--expected-head", required=True)
    verify.add_argument("--expected-tree", required=True)
    verify.add_argument("--ledger-dir", required=True)
    verify.add_argument("--output", help="path to write audit receipt JSON")
    verify.set_defaults(func=_verify_command)

    run = sub.add_parser("run", help="execute real mesh and verify the receipt")
    run.add_argument("--source-head", required=True)
    run.add_argument("--source-tree", required=True)
    run.add_argument("--workdir")
    run.add_argument("--output", help="path to write audit receipt JSON")
    run.set_defaults(func=_run_command)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
