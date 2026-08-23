#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Lossless Terminal Pattern, portable Pattern Capsules and M68000 decisions.

The canonical receipt is the state. Audience projections are deterministic
views of that receipt and never replace it. Every finite four-state decision
is executed through the existing proof-bound Motorola 68000 Spark kernel.
No network, Git mutation, platform publication or authority grant occurs here.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from tools import qikvrt_spark_branch as spark
except ModuleNotFoundError:  # direct execution from tools/
    import qikvrt_spark_branch as spark  # type: ignore[no-redef]

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "MESH_AUTONOMY_TERMINAL_PUBLICATION_V1.json"
SCHEMA_RECEIPT = "qikvrt_terminal_pattern_receipt_v1"
SCHEMA_PROJECTION = "qikvrt_terminal_pattern_projection_v1"
SCHEMA_CAPSULE = "qikvrt_pattern_capsule_v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
AUDIENCES = ("WATCHDOG_FULL", "OPERATOR", "OWNER", "PUBLIC")
DECISION_NAMES = {
    0: "NOOP_COMPLETE",
    1: "HOLD",
    2: "REOBSERVE",
    3: "REQUEST_AUTHORITY",
}


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy(path: Path = POLICY) -> dict[str, Any]:
    value = read_json(path)
    if value.get("schema") != "qikvrt_mesh_autonomy_terminal_publication_policy_v1":
        raise ValueError("terminal/publication policy schema mismatch")
    if value.get("status") != "ACTIVE":
        raise ValueError("terminal/publication policy is not active")
    return value


def safe_relpath(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    candidate = path if path.is_absolute() else resolved_root / path
    try:
        relative = candidate.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {path}") from exc
    return relative.as_posix()


def _payload_record(root: Path, path: Path) -> dict[str, Any]:
    relative = safe_relpath(root, path)
    absolute = root / relative
    data = absolute.read_bytes()
    return {
        "path": relative,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "raw_base64": base64.b64encode(data).decode("ascii"),
    }


def decode_payload(record: Mapping[str, Any]) -> bytes:
    required = {"path", "bytes", "sha256", "raw_base64"}
    if set(record) != required:
        raise ValueError("terminal payload record keys mismatch")
    raw = base64.b64decode(record["raw_base64"], validate=True)
    if len(raw) != record["bytes"]:
        raise ValueError("terminal payload byte length mismatch")
    if sha256_bytes(raw) != record["sha256"]:
        raise ValueError("terminal payload digest mismatch")
    return raw


def machine_decision(
    *,
    implemented: bool,
    verified: bool,
    persisted: bool,
    reobserved: bool,
    stale: bool = False,
    authority_required: bool = False,
    authority_present: bool = False,
    unclassified_remainder: bool = False,
    witness: int = 0,
) -> dict[str, Any]:
    """Execute one exact finite decision through the M68000 Spark kernel."""
    flags = (
        (1 if implemented else 0)
        | ((1 if verified else 0) << 1)
        | ((1 if persisted else 0) << 2)
        | ((1 if reobserved else 0) << 3)
        | ((1 if stale else 0) << 4)
        | ((1 if authority_required else 0) << 5)
        | ((1 if authority_present else 0) << 6)
        | ((1 if unclassified_remainder else 0) << 7)
    )
    d3 = witness & 0xFF
    d0, d1, d2, d3_out, instructions = spark.execute(spark.MACHINE, flags, d3)
    if d3_out != d3:
        raise AssertionError("M68000 pattern kernel mutated D3")
    return {
        "schema": "qikvrt_m68000_pattern_decision_v1",
        "kernel_id": "lean_spark_branch_pass_v1",
        "kernel_sha256": sha256_bytes(spark.MACHINE),
        "machine_bytes": len(spark.MACHINE),
        "control_flags": flags,
        "control_flags_hex": f"{flags:02x}",
        "decision_code": d0,
        "decision": DECISION_NAMES[d0],
        "completion_witness": d1,
        "machine_owned_active": d2,
        "d3_before": d3,
        "d3_after": d3_out,
        "dynamic_instructions": instructions,
        "virtual_m68000_execution_observed": True,
        "physical_m68000_execution_observed": False,
        "sun_sparc_execution_observed": False,
        "git_or_platform_effect_applied": False,
    }


def _first_blocker(status: Mapping[str, Any]) -> str | None:
    for key in (
        "first_blocker",
        "disposition_reason",
        "blocker",
        "fallback_error",
    ):
        value = status.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _next_action(status: Mapping[str, Any]) -> str | None:
    for key in ("next_action", "required_next_action"):
        value = status.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _effect_class(status: Mapping[str, Any]) -> str:
    publication_state = str(status.get("publication_state") or "").upper()
    if publication_state == "PUBLIC_VERIFIED":
        return "PLATFORM_PUBLICATION_PUBLICLY_REOBSERVED"
    if publication_state == "READY":
        return "PLATFORM_PUBLICATION_READY_NOT_EXECUTED"
    if status.get("status") == "DONE":
        return "REPOSITORY_WORK_PRODUCT_DONE"
    if status.get("status") == "BLOCK":
        return "NO_NEW_EFFECT_BLOCKED"
    return "REPOSITORY_ACTIVITY_NO_TERMINAL_EFFECT"


def _summary(status: Mapping[str, Any]) -> dict[str, Any]:
    owner_required = bool(status.get("owner_decision_required", False))
    machine_remaining = bool(
        status.get("machine_owned_work_remaining", status.get("status") == "CONTINUE")
    )
    return {
        "status": status.get("status"),
        "effect_class": _effect_class(status),
        "publication_required": bool(status.get("publication_required", False)),
        "publication_state": status.get("publication_state", "NOT_REQUESTED"),
        "first_blocker": _first_blocker(status),
        "next_action": _next_action(status),
        "machine_owned_work_remaining": machine_remaining,
        "owner_decision_required": owner_required,
        "pass_claimed": False,
        "final_pass_claimed": False,
        "effect_ack_done_claimed": bool(
            status.get("effect_ack_done", False)
            and status.get("publication_state") == "PUBLIC_VERIFIED"
        ),
    }


def _public_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": summary["status"],
        "effect_class": summary["effect_class"],
        "publication_state": summary["publication_state"],
        "machine_owned_work_remaining": summary["machine_owned_work_remaining"],
        "owner_decision_required": summary["owner_decision_required"],
        "pass_claimed": False,
        "final_pass_claimed": False,
        "effect_ack_done_claimed": summary["effect_ack_done_claimed"],
    }


def build_terminal_receipt(
    *,
    root: Path,
    status_path: Path,
    detail_paths: Iterable[Path] = (),
    repository: str,
    ref: str,
    head: str,
    tree: str,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    policy = load_policy()
    root = root.resolve()
    status_relative = safe_relpath(root, status_path)
    status_record = _payload_record(root, root / status_relative)
    status_raw = decode_payload(status_record)
    status = json.loads(status_raw.decode("utf-8"))
    if not isinstance(status, dict):
        raise ValueError("STATUS.json must contain one JSON object")

    detail_records: list[dict[str, Any]] = []
    seen = {status_relative}
    for item in detail_paths:
        relative = safe_relpath(root, item)
        if relative in seen:
            continue
        seen.add(relative)
        detail_records.append(_payload_record(root, root / relative))

    binding_complete = all(
        isinstance(item, str) and bool(item)
        for item in (repository, ref, head, tree)
    )
    summary = _summary(status)
    decision = machine_decision(
        implemented=True,
        verified=status.get("no_false_pass") is True,
        persisted=True,
        reobserved=binding_complete,
        stale=bool(status.get("stale_evidence", False)),
        authority_required=summary["owner_decision_required"],
        authority_present=bool(status.get("owner_decision_present", False)),
        unclassified_remainder=(
            status.get("status") != "DONE"
            and summary["first_blocker"] is None
            and summary["next_action"] is None
        ),
        witness=int(status_record["sha256"][:2], 16),
    )

    body = {
        "schema": SCHEMA_RECEIPT,
        "policy_id": policy["policy_id"],
        "binding": {
            "repository": repository,
            "ref": ref,
            "head": head,
            "tree": tree,
        },
        "canonical_state": {
            "status_payload": status_record,
            "detail_payloads": detail_records,
        },
        "parsed_status": status,
        "summary": summary,
        "m68000_decision": decision,
        "audiences": list(AUDIENCES),
        "boundaries": policy["mandatory_boundaries"],
    }
    receipt_sha256 = sha256_bytes(canonical_bytes(body))
    receipt = {**body, "receipt_sha256": receipt_sha256}

    common = {
        "schema": SCHEMA_PROJECTION,
        "receipt_sha256": receipt_sha256,
        "binding": body["binding"],
        "m68000_decision": decision,
    }
    projections = {
        "WATCHDOG_FULL": {
            **common,
            "audience": "WATCHDOG_FULL",
            "lossless": True,
            "canonical_receipt": receipt,
        },
        "OPERATOR": {
            **common,
            "audience": "OPERATOR",
            "lossless": False,
            "view": {
                **summary,
                "head": head,
                "tree": tree,
            },
        },
        "OWNER": {
            **common,
            "audience": "OWNER",
            "lossless": False,
            "view": {
                "effect_class": summary["effect_class"],
                "status": summary["status"],
                "first_blocker": summary["first_blocker"],
                "next_action": summary["next_action"],
                "machine_owned_work_remaining": summary[
                    "machine_owned_work_remaining"
                ],
                "owner_decision_required": summary["owner_decision_required"],
                "publication_state": summary["publication_state"],
            },
        },
        "PUBLIC": {
            **common,
            "audience": "PUBLIC",
            "lossless": False,
            "view": _public_summary(summary),
        },
    }
    return receipt, projections


def verify_terminal_receipt(receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema") != SCHEMA_RECEIPT:
        raise ValueError("terminal receipt schema mismatch")
    expected = receipt.get("receipt_sha256")
    if not isinstance(expected, str) or HEX64.fullmatch(expected) is None:
        raise ValueError("terminal receipt digest missing")
    body = dict(receipt)
    del body["receipt_sha256"]
    if sha256_bytes(canonical_bytes(body)) != expected:
        raise ValueError("terminal receipt digest mismatch")
    state = receipt.get("canonical_state")
    if not isinstance(state, dict):
        raise ValueError("terminal canonical state missing")
    decode_payload(state["status_payload"])
    for item in state.get("detail_payloads", []):
        decode_payload(item)
    machine = receipt.get("m68000_decision")
    if not isinstance(machine, dict) or machine.get("d3_before") != machine.get(
        "d3_after"
    ):
        raise ValueError("terminal M68000 decision receipt invalid")


def build_pattern_capsule(receipt: Mapping[str, Any]) -> dict[str, Any]:
    verify_terminal_receipt(receipt)
    policy = load_policy()
    receipt_sha = str(receipt["receipt_sha256"])
    capsule_body = {
        "schema": SCHEMA_CAPSULE,
        "policy_id": policy["policy_id"],
        "pattern_id": "qikvrt-pattern-" + receipt_sha[:24],
        "source_receipt_sha256": receipt_sha,
        "source_binding": receipt["binding"],
        "finite_control": {
            "abi": "QIKVRT_FOUR_STATE_D0_D1_D2_D3_V1",
            "kernel": receipt["m68000_decision"],
            "decision_table": policy["m68000_compilation"][
                "canonical_four_state_decisions"
            ],
        },
        "portable_intelligence": {
            "terminal_projection_contract": "TERMINAL_PATTERN_V1",
            "preconditions": policy["terminal_pattern"]["preconditions"],
            "invariants": policy["terminal_pattern"]["invariants"],
            "effect_adapter_contract": policy["publication_handoff"][
                "effect_adapter_contract"
            ],
            "reobservation_required": True,
        },
        "clone_contract": policy["pattern_capsule"],
        "nonportable_authority": policy["pattern_capsule"][
            "nonportable_authority"
        ],
        "boundaries": policy["mandatory_boundaries"],
    }
    return {
        **capsule_body,
        "capsule_sha256": sha256_bytes(canonical_bytes(capsule_body)),
    }


def verify_pattern_capsule(capsule: Mapping[str, Any]) -> None:
    if capsule.get("schema") != SCHEMA_CAPSULE:
        raise ValueError("pattern capsule schema mismatch")
    expected = capsule.get("capsule_sha256")
    if not isinstance(expected, str) or HEX64.fullmatch(expected) is None:
        raise ValueError("pattern capsule digest missing")
    body = dict(capsule)
    del body["capsule_sha256"]
    if sha256_bytes(canonical_bytes(body)) != expected:
        raise ValueError("pattern capsule digest mismatch")
    forbidden = canonical_bytes(capsule)
    for marker in (b"ZENODO_ACCESS_TOKEN=", b"GITHUB_TOKEN=", b"PRIVATE KEY"):
        if marker in forbidden:
            raise ValueError("pattern capsule contains credential material")


def materialize_terminal(
    *,
    root: Path,
    status_path: Path,
    output_dir: Path,
    detail_paths: Iterable[Path] = (),
    repository: str,
    ref: str,
    head: str,
    tree: str,
) -> dict[str, Any]:
    receipt, projections = build_terminal_receipt(
        root=root,
        status_path=status_path,
        detail_paths=detail_paths,
        repository=repository,
        ref=ref,
        head=head,
        tree=tree,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "TERMINAL_RECEIPT.json", receipt)
    for audience, projection in projections.items():
        write_json(output_dir / f"{audience}.json", projection)
    capsule = build_pattern_capsule(receipt)
    write_json(output_dir / "PATTERN_CAPSULE.json", capsule)
    return {
        "receipt": receipt,
        "projections": projections,
        "capsule": capsule,
    }


def verify_policy_and_kernel() -> dict[str, Any]:
    policy = load_policy()
    report = spark.verify_exhaustive()
    if report.get("input_pairs_verified") != 65536:
        raise ValueError("M68000 Spark kernel exhaustive space mismatch")
    if report.get("d3_preserved") is not True:
        raise ValueError("M68000 Spark kernel does not preserve D3")
    return {
        "schema": "qikvrt_mesh_pattern_verification_v1",
        "policy_id": policy["policy_id"],
        "kernel_report": report,
        "qikvrt_spark_is_sun_sparc": False,
        "physical_m68000_execution_observed": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def _parse_detail_paths(values: list[str]) -> list[Path]:
    return [Path(value) for value in values]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    terminal = sub.add_parser("terminal")
    terminal.add_argument("--root", default=".")
    terminal.add_argument("--status", required=True)
    terminal.add_argument("--detail", action="append", default=[])
    terminal.add_argument("--output-dir", required=True)
    terminal.add_argument("--repository", required=True)
    terminal.add_argument("--ref", required=True)
    terminal.add_argument("--head", required=True)
    terminal.add_argument("--tree", required=True)

    verify_receipt = sub.add_parser("verify-receipt")
    verify_receipt.add_argument("path")

    capsule = sub.add_parser("capsule")
    capsule.add_argument("--receipt", required=True)
    capsule.add_argument("--output", required=True)

    verify_capsule = sub.add_parser("verify-capsule")
    verify_capsule.add_argument("path")

    verify = sub.add_parser("verify")
    verify.add_argument("--output")

    args = parser.parse_args(argv)
    if args.command == "terminal":
        root = Path(args.root).resolve()
        materialize_terminal(
            root=root,
            status_path=Path(args.status),
            detail_paths=_parse_detail_paths(args.detail),
            output_dir=Path(args.output_dir),
            repository=args.repository,
            ref=args.ref,
            head=args.head,
            tree=args.tree,
        )
    elif args.command == "verify-receipt":
        verify_terminal_receipt(read_json(Path(args.path)))
    elif args.command == "capsule":
        value = build_pattern_capsule(read_json(Path(args.receipt)))
        write_json(Path(args.output), value)
    elif args.command == "verify-capsule":
        verify_pattern_capsule(read_json(Path(args.path)))
    else:
        value = verify_policy_and_kernel()
        if args.output:
            write_json(Path(args.output), value)
        else:
            print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
