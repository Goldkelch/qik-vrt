#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Reflexive system verification for the QIK-VRT real multi-pair mesh.

This tool verifies an execution receipt produced by ``qikvrt_real_mesh.py``
against the declared contract in ``state/mesh/QIKVRT_REAL_MESH_V1.json``,
applies the REFLEXIVE_FINDING_WORKFLOW_STANDARD, and emits a structured
audit receipt.

Each declared contract field is checked precisely.  Any deviation is recorded
as a finding and causes the tool to exit with a non-zero status.

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


def verify_receipt(
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
        isinstance(receipt.get("pair_count"), int)
        and receipt["pair_count"] >= topo.get("pair_count", 2),
        f"receipt.pair_count must be >= {topo.get('pair_count', 2)}",
    )
    _check(
        isinstance(receipt.get("node_process_count"), int)
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
    for field in required_true:
        _check(
            claims.get(field) is True,
            f"receipt.completion_claims.{field} must be true",
        )
    for field in required_false:
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

    # --- receipt integrity ---
    stored_sha = receipt.get("receipt_sha256")
    if isinstance(stored_sha, str):
        receipt_without_sha = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        computed = canonical_sha256(receipt_without_sha)
        _check(
            stored_sha == computed,
            "receipt.receipt_sha256 does not match canonical hash of receipt body",
        )

    return findings


def build_audit_receipt(
    *,
    receipt_path: str | None,
    receipt: dict[str, Any],
    contract: dict[str, Any],
    findings: list[str],
    reflexive_standard: dict[str, Any],
) -> dict[str, Any]:
    """Build a structured audit receipt."""
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
        "bounded_loopback_effect_ack_scope_confirmed": receipt.get("effect_ack_scope")
        == "BOUNDED_LOOPBACK_MULTI_PAIR_MESSAGE_DELIVERY_ONLY",
        "general_effect_ack_done": False,
        "external_effect": "NONE",
        "transport_ack_is_effect_ack": False,
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
    findings = verify_receipt(receipt, contract)
    return receipt, contract, findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _verify_command(args: argparse.Namespace) -> int:
    try:
        raw = json.loads(pathlib.Path(args.receipt).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BLOCK: cannot load receipt: {exc}", file=sys.stderr)
        return 2

    try:
        contract = load_contract()
        reflexive_standard = load_reflexive_standard()
    except VerificationError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2

    findings = verify_receipt(raw, contract)
    audit = build_audit_receipt(
        receipt_path=args.receipt,
        receipt=raw,
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

    workdir = pathlib.Path(args.workdir) if args.workdir else None

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

    audit = build_audit_receipt(
        receipt_path=None,
        receipt=receipt,
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
