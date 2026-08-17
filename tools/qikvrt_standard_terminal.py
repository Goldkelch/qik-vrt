#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Canonical QIK-VRT terminal projection for mesh and node boundaries.

This controller is read-only.  It turns exact-head watchdog evidence or explicit
terminal facts into one deterministic semantic event projected in two coupled
forms: an outward audit reflection and an inward reflexive admission signal.
The inward signal never promotes semantic/scientific truth; it only constrains
what the runtime may admit next.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/STANDARD_TERMINAL_PATTERN_V1.json"
SHA1 = re.compile(r"^[0-9a-f]{40}$")


class TerminalBlock(RuntimeError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TerminalBlock(f"{label} must be an object")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA1.fullmatch(value) is None:
        raise TerminalBlock(f"{label} must be a lowercase forty-character Git SHA")
    return value


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    try:
        value = json.loads((root / CONTRACT.relative_to(ROOT)).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TerminalBlock(f"cannot load terminal contract: {exc}") from exc
    contract = dict(_mapping(value, "terminal contract"))
    if contract.get("schema") != "qikvrt_standard_terminal_pattern_v1":
        raise TerminalBlock("terminal contract schema mismatch")
    loci = contract.get("architectural_loci")
    if not isinstance(loci, list) or len(loci) < 8:
        raise TerminalBlock("terminal contract does not cover enough architectural loci")
    pairs = []
    for raw in loci:
        item = _mapping(raw, "terminal locus")
        scope, phase = item.get("scope"), item.get("phase")
        if not isinstance(scope, str) or not scope or not isinstance(phase, str) or not phase:
            raise TerminalBlock("terminal locus is malformed")
        pairs.append((scope, phase))
    if len(set(pairs)) != len(pairs):
        raise TerminalBlock("terminal loci must be unique")
    if not {"MESH_BOUNDARY", "MESH_NODE_BOUNDARY", "MESH_NODE_INTERNAL"}.issubset({scope for scope, _ in pairs}):
        raise TerminalBlock("mesh, node-boundary, and node-internal coverage is mandatory")
    inward = _mapping(contract.get("inward_reflexivity"), "inward reflexivity")
    if inward.get("must_share_event_ids_with_outward") is not True or inward.get("semantic_promotion_forbidden") is not True:
        raise TerminalBlock("inward reflexive safety boundary is weakened")
    admission = _mapping(contract.get("admission"), "terminal admission")
    if admission.get("fail_closed_without_fresh_exact_head_inward_projection") is not True:
        raise TerminalBlock("terminal admission must fail closed")
    return contract


def classify(facts: Mapping[str, Any]) -> str:
    ordered = (
        ("exact_head_mismatch", "EXACT_HEAD_MISMATCH"),
        ("stale_writer_or_lease", "STALE_WRITER_OR_LEASE"),
        ("integrity_projection_defect", "INTEGRITY_PROJECTION_DEFECT"),
        ("platform_pre_job_barrier", "PLATFORM_PRE_JOB_BARRIER"),
        ("executed_workflow_failure", "EXECUTED_WORKFLOW_FAILURE"),
        ("expected_semantic_hold", "EXPECTED_SEMANTIC_HOLD"),
        ("observed_exact_head_success", "OBSERVED_EXACT_HEAD_SUCCESS"),
    )
    for fact, classification in ordered:
        if facts.get(fact) is True:
            return classification
    return "OBSERVE"


def _admission(classification: str, source: Mapping[str, Any]) -> dict[str, Any]:
    blocked = classification not in {"OBSERVE", "OBSERVED_EXACT_HEAD_SUCCESS"}
    requires_human = classification == "PLATFORM_PRE_JOB_BARRIER"
    retryable = classification in {"PLATFORM_PRE_JOB_BARRIER", "EXECUTED_WORKFLOW_FAILURE", "STALE_WRITER_OR_LEASE"}
    next_action = {
        "EXACT_HEAD_MISMATCH": "REOBSERVE_EXACT_HEAD_AND_TREE",
        "STALE_WRITER_OR_LEASE": "REOBSERVE_STALE_WRITER_AND_PRESERVE_SINGLE_WRITER",
        "INTEGRITY_PROJECTION_DEFECT": "REGENERATE_DETERMINISTIC_INTEGRITY_PROJECTIONS_HISTORY_PRESERVINGLY",
        "PLATFORM_PRE_JOB_BARRIER": "OBTAIN_TRUSTED_PLATFORM_APPROVAL_OR_TRUSTED_EXACT_HEAD_EXECUTION",
        "EXECUTED_WORKFLOW_FAILURE": "REPAIR_OR_REOBSERVE_FIRST_DETERMINISTIC_EXECUTED_FAILURE",
        "EXPECTED_SEMANTIC_HOLD": "PRESERVE_HOLD_UNTIL_REQUIRED_EVIDENCE_EXISTS",
        "OBSERVED_EXACT_HEAD_SUCCESS": "CONTINUE_WITH_NEXT_SEPARATELY_AUTHORIZED_BOUNDARY",
        "OBSERVE": source.get("productive_edge") or "CONTINUE_REFLEXIVE_OBSERVATION",
    }[classification]
    return {
        "blocks_productive_progress": blocked,
        "admit_productive_writer": not blocked,
        "admit_observer": True,
        "requires_human": requires_human,
        "retryable": retryable,
        "next_action": next_action,
        "semantic_promotion": False,
    }


def watchdog_facts(receipt: Mapping[str, Any]) -> dict[str, bool]:
    observations = _mapping(receipt.get("observations", {}), "watchdog observations")
    gatewatch = _mapping(receipt.get("gatewatch", {}), "watchdog gatewatch")
    untrusted = observations.get("untrusted_terminal_runs", [])
    failures = gatewatch.get("executed_failures", [])
    state = receipt.get("state")
    blocker = receipt.get("first_blocker")
    return {
        "expected_semantic_hold": state in {"PREEMPTIVE_HOLD_NODE_LIVENESS"},
        "integrity_projection_defect": blocker in {"REPOSITORY_MANIFEST_DIFFERS_FROM_DETERMINISTIC_REGENERATION", "INTEGRITY_PROJECTION_MISMATCH"},
        "exact_head_mismatch": blocker in {"EXACT_HEAD_MISMATCH", "AUTHORITY_HEAD_MISMATCH"},
        "stale_writer_or_lease": state in {"PREEMPTIVE_HOLD_STALE_WRITER_LEASE", "PREEMPTIVE_HOLD_COMPETING_WRITERS"},
        "platform_pre_job_barrier": bool(untrusted),
        "executed_workflow_failure": bool(failures),
        "observed_exact_head_success": receipt.get("disposition") == "OBSERVE" and not untrusted and not failures,
    }


def _previous_relation(previous: Mapping[str, Any] | None, *, head: str, tree: str, source_fingerprint: str) -> str:
    if previous is None:
        return "REFLEXIVE_BOOTSTRAP"
    if previous.get("head_sha") != head or previous.get("tree_sha") != tree:
        return "REFLEXIVE_TRANSITION"
    return "REFLEXIVE_STABLE" if previous.get("source_semantic_fingerprint") == source_fingerprint else "REFLEXIVE_TRANSITION"


def project_watchdog(receipt: Mapping[str, Any], previous: Mapping[str, Any] | None = None, *, root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = load_contract(root)
    repository = receipt.get("repository")
    if not isinstance(repository, str) or not repository:
        raise TerminalBlock("watchdog receipt repository is missing")
    head = _sha(receipt.get("head_sha"), "watchdog head")
    tree = _sha(receipt.get("tree_sha"), "watchdog tree")
    source_fingerprint = receipt.get("semantic_fingerprint")
    if not isinstance(source_fingerprint, str) or len(source_fingerprint) != 64:
        raise TerminalBlock("watchdog semantic fingerprint is missing")
    facts = watchdog_facts(receipt)
    classification = classify(facts)
    relation = _previous_relation(previous, head=head, tree=tree, source_fingerprint=source_fingerprint)
    outward_events = []
    inward_events = []
    for locus in contract["architectural_loci"]:
        identity = {
            "repository": repository,
            "head_sha": head,
            "tree_sha": tree,
            "scope": locus["scope"],
            "phase": locus["phase"],
            "classification": classification,
            "source_semantic_fingerprint": source_fingerprint,
        }
        event_id = digest(identity)
        outward_events.append({
            "event_id": event_id,
            **identity,
            "state": receipt.get("state"),
            "disposition": receipt.get("disposition"),
            "first_blocker": receipt.get("first_blocker"),
            "reflection_only": True,
            "semantic_truth_authority": False,
        })
        inward_events.append({
            "event_id": event_id,
            **identity,
            **_admission(classification, receipt),
        })
    outward = {
        "schema": "qikvrt_standard_terminal_outward_v1",
        "repository": repository,
        "head_sha": head,
        "tree_sha": tree,
        "source_semantic_fingerprint": source_fingerprint,
        "reflexive_relation": relation,
        "events": outward_events,
        "completion_claims": dict(contract["completion_claims"]),
    }
    inward = {
        "schema": "qikvrt_standard_terminal_inward_v1",
        "repository": repository,
        "head_sha": head,
        "tree_sha": tree,
        "source_semantic_fingerprint": source_fingerprint,
        "reflexive_relation": relation,
        "events": inward_events,
        "aggregate": {
            "blocks_productive_progress": any(event["blocks_productive_progress"] for event in inward_events),
            "admit_productive_writer": all(event["admit_productive_writer"] for event in inward_events),
            "admit_observer": all(event["admit_observer"] for event in inward_events),
            "requires_human": any(event["requires_human"] for event in inward_events),
            "classification": classification,
            "next_actions": sorted({event["next_action"] for event in inward_events}),
        },
        "completion_claims": dict(contract["completion_claims"]),
    }
    if [event["event_id"] for event in outward_events] != [event["event_id"] for event in inward_events]:
        raise TerminalBlock("outward and inward event identities diverged")
    return outward, inward


def verify_inward(inward: Mapping[str, Any], *, expected_head: str, expected_tree: str, observer: bool) -> dict[str, Any]:
    load_contract()
    head, tree = _sha(expected_head, "expected head"), _sha(expected_tree, "expected tree")
    if inward.get("schema") != "qikvrt_standard_terminal_inward_v1":
        raise TerminalBlock("inward terminal schema mismatch")
    if inward.get("head_sha") != head or inward.get("tree_sha") != tree:
        raise TerminalBlock("inward terminal projection is not bound to the exact head/tree")
    aggregate = _mapping(inward.get("aggregate"), "inward aggregate")
    allowed = aggregate.get("admit_observer") if observer else aggregate.get("admit_productive_writer")
    return {
        "schema": "qikvrt_standard_terminal_admission_v1",
        "head_sha": head,
        "tree_sha": tree,
        "mode": "OBSERVER" if observer else "PRODUCTIVE_WRITER",
        "state": "ADMIT" if allowed is True else "HOLD",
        "classification": aggregate.get("classification"),
        "next_actions": aggregate.get("next_actions", []),
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def _read(path: Path) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), path.as_posix())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TerminalBlock(f"cannot read {path}: {exc}") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-contract")
    check.add_argument("--json", action="store_true")
    project = sub.add_parser("project-watchdog")
    project.add_argument("--receipt", type=Path, required=True)
    project.add_argument("--previous-inward", type=Path)
    project.add_argument("--out-dir", type=Path, required=True)
    admit = sub.add_parser("admit")
    admit.add_argument("--inward", type=Path, required=True)
    admit.add_argument("--expect-head", required=True)
    admit.add_argument("--expect-tree", required=True)
    admit.add_argument("--mode", choices=("observer", "productive-writer"), required=True)
    admit.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "check-contract":
            contract = load_contract()
            result = {"schema": "qikvrt_standard_terminal_contract_check_v1", "state": "CONTRACT_BOUND", "locus_count": len(contract["architectural_loci"])}
        elif args.command == "project-watchdog":
            receipt = _read(args.receipt)
            previous = _read(args.previous_inward) if args.previous_inward and args.previous_inward.is_file() else None
            outward, inward = project_watchdog(receipt, previous)
            args.out_dir.mkdir(parents=True, exist_ok=True)
            (args.out_dir / "terminal-outward.json").write_bytes(canonical_json_bytes(outward))
            (args.out_dir / "terminal-inward.json").write_bytes(canonical_json_bytes(inward))
            result = inward["aggregate"]
        else:
            result = verify_inward(_read(args.inward), expected_head=args.expect_head, expected_tree=args.expect_tree, observer=args.mode == "observer")
        print(canonical_json_bytes(result).decode("utf-8"), end="")
        return 0
    except TerminalBlock as exc:
        print(json.dumps({"state": "HOLD", "failure_class": "STANDARD_TERMINAL_BLOCKED", "detail": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
