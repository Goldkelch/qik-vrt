#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize the exact, truth-bounded global QIK-VRT completion inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from collections import Counter
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "policy" / "GLOBAL_COMPLETION_SCOPE.json"
INVENTORY_PATH = ROOT / "GLOBAL_CLAIM_INVENTORY.json"
TRACEABILITY_PATH = ROOT / "GLOBAL_TRACEABILITY.json"
KERNEL_RECEIPTS_PATH = ROOT / "GLOBAL_KERNEL_RECEIPTS.json"
COMPLETION_RECEIPT_PATH = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"

MANUSCRIPT_GRAPH_PATH = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "claims" / "CLAIM_GRAPH.json"
APPENDIX_MATRIX_PATH = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "claims" / "APPENDIX_MATRIX.json"
EFFECT_MATRIX_PATH = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "effect_ack" / "DRAFT01_CLAIM_MATRIX.json"
PROOF_MANIFEST_PATH = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "proofs" / "PROOF_OBJECT_MANIFEST.json"
FORMALIZATION_README_PATH = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "README.md"
COMPLETION_PLAN_PATH = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "COMPLETION_PLAN.md"
PROOF_MAP_PATH = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "MANUSCRIPT_PROOF_MAP.md"
AI_PROGRESS_PATH = ROOT / "AI_PROGRESS.json"

OUTPUTS = (INVENTORY_PATH, TRACEABILITY_PATH, KERNEL_RECEIPTS_PATH, COMPLETION_RECEIPT_PATH)
KERNEL_DISPOSITIONS = {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"}
TERMINAL_DISPOSITIONS = {
    "KERNEL_PROVED",
    "KERNEL_PROVED_CONDITIONAL",
    "EMPIRICAL_EVIDENCE_BOUND",
    "INTERPRETIVE",
    "NORMATIVE",
    "OPEN",
    "OUT_OF_SCOPE",
}

LICENSE = {
    "classification": "machine_readable_completion_evidence",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}


class CompletionError(RuntimeError):
    """Fail-closed materialization error."""


def _load(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CompletionError(f"cannot load {path.relative_to(ROOT)}: {exc}") from None
    if not isinstance(value, dict):
        raise CompletionError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()  # noqa: S324


def _duplicates(values: Iterable[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _scope_source(scope: dict[str, Any], source_id: str) -> dict[str, Any]:
    matches = [item for item in scope.get("claim_sources", []) if item.get("id") == source_id]
    if len(matches) != 1:
        raise CompletionError(f"scope must contain exactly one source {source_id}")
    return matches[0]


def _validate_source_blob(scope: dict[str, Any], source_id: str, path: pathlib.Path) -> None:
    source = _scope_source(scope, source_id)
    raw = path.read_bytes()
    actual = _git_blob_sha1(raw)
    expected = source.get("git_blob_sha1")
    if actual != expected:
        raise CompletionError(
            f"{path.relative_to(ROOT)} Git blob changed: expected {expected}, got {actual}"
        )


def _validate_exact_tag(scope: dict[str, Any], paths: Iterable[pathlib.Path]) -> None:
    tag = scope["baseline"]["tag"]
    expected_commit = scope["baseline"]["authority_commit"]
    try:
        actual_commit = subprocess.check_output(
            ["git", "rev-parse", f"{tag}^{{commit}}"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CompletionError(f"exact tag {tag} is unavailable: {exc}") from None
    if actual_commit != expected_commit:
        raise CompletionError(
            f"exact tag {tag} resolves to {actual_commit}, expected {expected_commit}"
        )
    for path in sorted(set(paths)):
        relative = path.relative_to(ROOT).as_posix()
        try:
            tagged = subprocess.check_output(
                ["git", "show", f"{tag}^{{commit}}:{relative}"], cwd=ROOT
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise CompletionError(f"cannot read {relative} from exact tag {tag}: {exc}") from None
        current = path.read_bytes()
        if tagged != current:
            raise CompletionError(f"current {relative} differs from exact tag {tag}")


def _manuscript_disposition(node: dict[str, Any]) -> str:
    status = node.get("formalizationStatus")
    category = node.get("epistemicCategory")
    binding = node.get("formalBinding")
    if status == "PENDING":
        return "OPEN"
    if isinstance(binding, dict):
        if status == "CONDITIONAL_CHECKED" or category == "CONDITIONAL":
            return "KERNEL_PROVED_CONDITIONAL"
        return "KERNEL_PROVED"
    return {
        "EMPIRICAL": "EMPIRICAL_EVIDENCE_BOUND",
        "INTERPRETIVE": "INTERPRETIVE",
        "NORMATIVE": "NORMATIVE",
        "SOURCE": "OUT_OF_SCOPE",
        "BACKGROUND": "OUT_OF_SCOPE",
    }.get(str(category), "OPEN")


def _appendix_disposition(row: dict[str, Any], manuscript: dict[str, dict[str, Any]]) -> str:
    category = row.get("epistemicCategory")
    if category == "EMPIRICAL":
        return "EMPIRICAL_EVIDENCE_BOUND"
    if category == "INTERPRETIVE":
        return "INTERPRETIVE"
    if category == "NORMATIVE":
        return "NORMATIVE"
    if category in {"BACKGROUND", "SOURCE"}:
        return "OUT_OF_SCOPE"
    related = row.get("relatedClaimIds", [])
    if not isinstance(related, list) or not related:
        return "OPEN"
    related_dispositions = []
    for claim_id in related:
        node = manuscript.get(str(claim_id))
        if node is None:
            return "OPEN"
        related_dispositions.append(_manuscript_disposition(node))
    if not all(item in KERNEL_DISPOSITIONS for item in related_dispositions):
        return "OPEN"
    if category == "CONDITIONAL" or "KERNEL_PROVED_CONDITIONAL" in related_dispositions:
        return "KERNEL_PROVED_CONDITIONAL"
    return "KERNEL_PROVED"


def _effect_disposition(claim: dict[str, Any]) -> str:
    status = claim.get("status")
    if status == "KERNEL_PROVED":
        return "KERNEL_PROVED"
    if status == "KERNEL_PROVED_CONDITIONAL":
        return "KERNEL_PROVED_CONDITIONAL"
    return "OPEN"


def _source_span(value: dict[str, Any]) -> dict[str, Any] | None:
    span = value.get("sourceSpan")
    if not isinstance(span, dict):
        return None
    return {
        key: span[key]
        for key in ("id", "startLine", "endLine", "sha256", "physicalPdfPage")
        if key in span
    }


def _build() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[pathlib.Path]]:
    scope = _load(SCOPE_PATH)
    allowed = set(scope.get("allowed_terminal_dispositions", []))
    if allowed != TERMINAL_DISPOSITIONS:
        raise CompletionError("scope terminal dispositions differ from the closed seven-state contract")

    _validate_source_blob(scope, "locked-manuscript-claim-graph", MANUSCRIPT_GRAPH_PATH)
    _validate_source_blob(scope, "locked-manuscript-appendix-matrix", APPENDIX_MATRIX_PATH)
    _validate_source_blob(scope, "effect-ack-draft01-claim-matrix", EFFECT_MATRIX_PATH)

    graph = _load(MANUSCRIPT_GRAPH_PATH)
    appendix = _load(APPENDIX_MATRIX_PATH)
    effect = _load(EFFECT_MATRIX_PATH)
    proof_manifest = _load(PROOF_MANIFEST_PATH)

    nodes = graph.get("nodes", [])
    rows = appendix.get("rows", [])
    effect_claims = effect.get("claims", [])
    if not all(isinstance(items, list) for items in (nodes, rows, effect_claims)):
        raise CompletionError("one or more authoritative claim arrays are malformed")

    expected = {
        "locked-manuscript-claim-graph": len(nodes),
        "locked-manuscript-appendix-matrix": len(rows),
        "effect-ack-draft01-claim-matrix": len(effect_claims),
    }
    for source_id, actual in expected.items():
        scoped = int(_scope_source(scope, source_id).get("expected_entries", -1))
        if actual != scoped:
            raise CompletionError(f"{source_id}: expected {scoped} entries, got {actual}")

    manuscript_by_id = {
        str(node["id"]): node
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    if len(manuscript_by_id) != len(nodes):
        raise CompletionError("manuscript graph contains malformed or duplicate IDs")

    manifest_objects = {
        str(item.get("claimId")): item
        for item in proof_manifest.get("objects", [])
        if isinstance(item, dict) and isinstance(item.get("claimId"), str)
    }
    manifest_effect = {
        str(item.get("claimId")): item
        for item in proof_manifest.get("effectAck", {}).get("claims", [])
        if isinstance(item, dict) and isinstance(item.get("claimId"), str)
    }

    entries: list[dict[str, Any]] = []
    trace_entries: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    exact_tag_paths: list[pathlib.Path] = [
        MANUSCRIPT_GRAPH_PATH,
        APPENDIX_MATRIX_PATH,
        EFFECT_MATRIX_PATH,
        PROOF_MANIFEST_PATH,
    ]
    baseline = scope["baseline"]

    for node in nodes:
        claim_id = str(node["id"])
        global_id = f"MANUSCRIPT::{claim_id}"
        disposition = _manuscript_disposition(node)
        binding = node.get("formalBinding") if isinstance(node.get("formalBinding"), dict) else None
        kernel_eligible = binding is not None
        entry = {
            "id": global_id,
            "native_id": claim_id,
            "source_registry": "locked-manuscript-claim-graph",
            "statement": node.get("statement"),
            "epistemic_category": node.get("epistemicCategory"),
            "terminal_disposition": disposition,
            "kernel_eligible": kernel_eligible,
            "direct_kernel_binding": kernel_eligible,
            "dependencies": node.get("dependencies", []),
            "source_span_ids": node.get("sourceSpanIds", []),
            "environment_ids": node.get("environmentIds", []),
        }
        entries.append(entry)
        trace_entries.append(
            {
                "claim_id": global_id,
                "source": {
                    "path": MANUSCRIPT_GRAPH_PATH.relative_to(ROOT).as_posix(),
                    "registry_entry_id": claim_id,
                    "source_span_ids": node.get("sourceSpanIds", []),
                    "environment_ids": node.get("environmentIds", []),
                },
                "terminal_disposition": disposition,
                "disposition_evidence": (
                    [binding.get("proofConstant"), binding.get("registryConstant")]
                    if binding
                    else [str(node.get("formalizationStatus"))]
                ),
            }
        )
        if binding:
            persistent_manifest_entry = manifest_objects.get(claim_id)
            source_path = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / str(binding["sourcePath"])
            registry_path = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / str(binding["registrySourcePath"])
            if not source_path.is_file() or not registry_path.is_file():
                raise CompletionError(f"Lean source or registry missing for {claim_id}")
            exact_tag_paths.extend((source_path, registry_path))
            receipts.append(
                {
                    "claim_id": global_id,
                    "native_id": claim_id,
                    "terminal_disposition": disposition,
                    "proof_system": "Lean4",
                    "exact_tag": baseline["tag"],
                    "tag_authority_commit": baseline["authority_commit"],
                    "tag_mirror_commit": baseline["mirror_commit"],
                    "statement_constant": binding.get("statementConstant"),
                    "proof_constants": [binding.get("proofConstant")],
                    "registry_constant": binding.get("registryConstant"),
                    "source_path": source_path.relative_to(ROOT).as_posix(),
                    "source_sha256": _sha256(source_path.read_bytes()),
                    "source_git_blob_sha1": _git_blob_sha1(source_path.read_bytes()),
                    "registry_path": registry_path.relative_to(ROOT).as_posix(),
                    "registry_sha256": _sha256(registry_path.read_bytes()),
                    "registry_git_blob_sha1": _git_blob_sha1(registry_path.read_bytes()),
                    "assumption_policy": binding.get("assumptionPolicy"),
                    "proof_object_manifest_entry": (
                        claim_id if persistent_manifest_entry is not None else None
                    ),
                    "proof_object_coverage": (
                        "PERSISTENT_ENTRY"
                        if persistent_manifest_entry is not None
                        else "DIRECT_SOURCE_REGISTRY_AND_WORKFLOW_AUDIT"
                    ),
                    "verification_contract": ".github/workflows/qikvrt_manuscript_proof.yml",
                }
            )

    for row in rows:
        native_id = str(row.get("id"))
        global_id = f"APPENDIX::{native_id}"
        disposition = _appendix_disposition(row, manuscript_by_id)
        related = [str(item) for item in row.get("relatedClaimIds", [])]
        entry = {
            "id": global_id,
            "native_id": native_id,
            "source_registry": "locked-manuscript-appendix-matrix",
            "statement": row.get("statementTex"),
            "epistemic_category": row.get("epistemicCategory"),
            "terminal_disposition": disposition,
            "kernel_eligible": False,
            "direct_kernel_binding": False,
            "derived_from_claim_ids": related,
            "truth_disposition": row.get("truthDisposition"),
            "source_span": _source_span(row),
        }
        entries.append(entry)
        trace_entries.append(
            {
                "claim_id": global_id,
                "source": {
                    "path": APPENDIX_MATRIX_PATH.relative_to(ROOT).as_posix(),
                    "registry_entry_id": native_id,
                    "source_span": _source_span(row),
                },
                "terminal_disposition": disposition,
                "disposition_evidence": [f"MANUSCRIPT::{item}" for item in related]
                or [str(row.get("truthDisposition"))],
                "binding_mode": "DERIVED_FROM_RELATED_REGISTERED_CLAIMS" if related else "CLASSIFIED_ONLY",
            }
        )

    for claim in effect_claims:
        native_id = str(claim.get("id"))
        global_id = f"EFFECT_ACK::{native_id}"
        disposition = _effect_disposition(claim)
        proof_constants = [str(value) for value in claim.get("proof_constants", [])]
        kernel_eligible = bool(proof_constants)
        entry = {
            "id": global_id,
            "native_id": native_id,
            "source_registry": "effect-ack-draft01-claim-matrix",
            "statement": claim.get("statement"),
            "epistemic_category": claim.get("classification"),
            "terminal_disposition": disposition,
            "kernel_eligible": kernel_eligible,
            "direct_kernel_binding": kernel_eligible,
            "source_sections": claim.get("source_sections", []),
            "related_sections": claim.get("related_sections", []),
        }
        entries.append(entry)
        trace_entries.append(
            {
                "claim_id": global_id,
                "source": {
                    "path": EFFECT_MATRIX_PATH.relative_to(ROOT).as_posix(),
                    "registry_entry_id": native_id,
                    "source_sections": claim.get("source_sections", []),
                    "related_sections": claim.get("related_sections", []),
                },
                "terminal_disposition": disposition,
                "disposition_evidence": proof_constants or [str(claim.get("status"))],
            }
        )
        if kernel_eligible:
            if native_id not in manifest_effect:
                raise CompletionError(f"proof-object manifest lacks {native_id}")
            source_path = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / str(claim["source_path"])
            if not source_path.is_file():
                raise CompletionError(f"EFFECT_ACK Lean source missing for {native_id}")
            exact_tag_paths.append(source_path)
            receipts.append(
                {
                    "claim_id": global_id,
                    "native_id": native_id,
                    "terminal_disposition": disposition,
                    "proof_system": "Lean4",
                    "exact_tag": baseline["tag"],
                    "tag_authority_commit": baseline["authority_commit"],
                    "tag_mirror_commit": baseline["mirror_commit"],
                    "proof_constants": proof_constants,
                    "registry_constant": claim.get("registry_constant"),
                    "source_path": source_path.relative_to(ROOT).as_posix(),
                    "source_sha256": _sha256(source_path.read_bytes()),
                    "source_git_blob_sha1": _git_blob_sha1(source_path.read_bytes()),
                    "proof_object_manifest_entry": native_id,
                    "verification_contract": ".github/workflows/qikvrt_manuscript_proof.yml",
                }
            )

    operational = scope.get("operational_claims", [])
    if not isinstance(operational, list) or len(operational) != 4:
        raise CompletionError("scope must contain exactly four operational claims")
    for claim in operational:
        native_id = str(claim.get("id"))
        global_id = f"OPERATIONAL::{native_id}"
        disposition = str(claim.get("disposition"))
        entries.append(
            {
                "id": global_id,
                "native_id": native_id,
                "source_registry": "global-completion-scope",
                "statement": claim.get("statement"),
                "epistemic_category": "OPERATIONAL_EVIDENCE",
                "terminal_disposition": disposition,
                "kernel_eligible": False,
                "direct_kernel_binding": False,
                "evidence": claim.get("evidence", []),
            }
        )
        trace_entries.append(
            {
                "claim_id": global_id,
                "source": {
                    "path": SCOPE_PATH.relative_to(ROOT).as_posix(),
                    "registry_entry_id": native_id,
                },
                "terminal_disposition": disposition,
                "disposition_evidence": claim.get("evidence", []),
            }
        )

    entries.sort(key=lambda item: item["id"])
    trace_entries.sort(key=lambda item: item["claim_id"])
    receipts.sort(key=lambda item: item["claim_id"])
    ids = [str(item["id"]) for item in entries]
    duplicates = _duplicates(ids)
    if duplicates:
        raise CompletionError(f"duplicate global claim IDs: {duplicates}")
    expected_total = sum(int(item["expected_entries"]) for item in scope["claim_sources"]) + len(operational)
    if len(entries) != expected_total:
        raise CompletionError(f"expected {expected_total} global claims, got {len(entries)}")
    bad_dispositions = sorted(
        {str(item["terminal_disposition"]) for item in entries} - TERMINAL_DISPOSITIONS
    )
    if bad_dispositions:
        raise CompletionError(f"unknown terminal dispositions: {bad_dispositions}")
    eligible_ids = {str(item["id"]) for item in entries if item["kernel_eligible"] is True}
    receipt_ids = {str(item["claim_id"]) for item in receipts}
    if eligible_ids != receipt_ids:
        raise CompletionError(
            f"kernel receipt coverage mismatch: missing={sorted(eligible_ids - receipt_ids)}, "
            f"extra={sorted(receipt_ids - eligible_ids)}"
        )

    disposition_counts = dict(sorted(Counter(item["terminal_disposition"] for item in entries).items()))
    open_ids = sorted(item["id"] for item in entries if item["terminal_disposition"] == "OPEN")

    inventory = {
        "_license": LICENSE,
        "schema": "qikvrt_global_claim_inventory_v1",
        "scope_id": scope["scope_id"],
        "baseline_tag": baseline["tag"],
        "counts": {
            "claims": len(entries),
            "kernel_eligible": len(eligible_ids),
            "terminal_dispositions": disposition_counts,
            "open": len(open_ids),
        },
        "claims": entries,
    }
    traceability = {
        "_license": LICENSE,
        "schema": "qikvrt_global_source_claim_disposition_traceability_v1",
        "scope_id": scope["scope_id"],
        "inventory_sha256": _sha256(_json_bytes(inventory)),
        "counts": {
            "claims": len(trace_entries),
            "source_bound": len(trace_entries),
            "terminally_classified": len(trace_entries),
        },
        "entries": trace_entries,
    }
    kernel_receipts = {
        "_license": LICENSE,
        "schema": "qikvrt_exact_tag_kernel_receipt_index_v1",
        "scope_id": scope["scope_id"],
        "exact_tag": baseline["tag"],
        "tag_authority_commit": baseline["authority_commit"],
        "tag_mirror_commit": baseline["mirror_commit"],
        "shared_tag_tree_sha1": baseline["shared_git_tree_sha1"],
        "verification_model": "Exact-tag source and registry bytes are required to equal the bytes kernel-checked by the mandatory manuscript proof workflow on the candidate head. Runtime run and artifact identities are attached by the promotion receipt; cache cannot replace kernel verification.",
        "counts": {
            "kernel_eligible_claims": len(eligible_ids),
            "receipts": len(receipts),
            "coverage_gap": 0,
        },
        "receipts": receipts,
    }
    completion = {
        "_license": LICENSE,
        "schema": "qikvrt_global_completion_receipt_v1",
        "scope_id": scope["scope_id"],
        "state": "COMPLETE_INVENTORY_WITH_OPEN_BOUNDARIES" if open_ids else "CANDIDATE_READY_FOR_GLOBAL_GATES",
        "baseline_tag": baseline["tag"],
        "artifact_hashes": {
            "global_claim_inventory_sha256": _sha256(_json_bytes(inventory)),
            "global_traceability_sha256": _sha256(_json_bytes(traceability)),
            "global_kernel_receipts_sha256": _sha256(_json_bytes(kernel_receipts)),
        },
        "claims": {
            "complete_claim_inventory": True,
            "complete_source_claim_disposition_traceability": True,
            "complete_exact_tag_kernel_receipt_coverage_for_kernel_eligible_claims": True,
            "green_global_gates_on_exact_candidate": False,
            "authority_mirror_equality_for_exact_candidate": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "fully_kernel_verified_overall_completion": False,
        },
        "open_claim_ids": open_ids,
        "non_claims": [
            "unqualified PASS",
            "FINAL_PASS",
            "repository-wide timeless EFFECT_ACK_DONE",
            "truth of empirical or interpretive claims",
            "fully kernel-verified overall completion",
        ],
        "next_required_effect": (
            "Run all mandatory gates on one exact materialized candidate, promote to Authority, "
            "synchronize Mirror, and issue a final pair-bound completion receipt. OPEN entries "
            "remain explicit blockers for FINAL_PASS."
        ),
    }
    return inventory, traceability, kernel_receipts, completion, exact_tag_paths


def _validate_status_projections() -> None:
    readme = FORMALIZATION_README_PATH.read_text(encoding="utf-8")
    plan = COMPLETION_PLAN_PATH.read_text(encoding="utf-8")
    proof_map = PROOF_MAP_PATH.read_text(encoding="utf-8")
    progress = _load(AI_PROGRESS_PATH)
    required_readme = (
        "formal-environment coverage complete",
        "42 strong source-bound Lean bindings",
        "six conditional bindings",
        "GLOBAL_CLAIM_INVENTORY.json",
    )
    for needle in required_readme:
        if needle not in readme:
            raise CompletionError(f"formalization README lacks current status marker: {needle}")
    if "Status: COMPLETED_FOR_LOCKED_MANUSCRIPT" not in plan:
        raise CompletionError("COMPLETION_PLAN.md is not marked completed for the locked manuscript")
    for needle in (
        "| Formal LaTeX environments inventoried | 40 / 40 |",
        "| Definitions source-bound and kernel-checked | 20 / 20 |",
        "| Theorem-like environments formally closed | 20 / 20 |",
        "| Open theorem/conditional nodes | 0 |",
    ):
        if needle not in proof_map:
            raise CompletionError(f"proof map lacks canonical completion row: {needle}")
    if progress.get("operation_id") != "global-completion-v1-2026-07-28":
        raise CompletionError("AI_PROGRESS.json does not project the global completion operation")
    if progress.get("state") != "EVIDENCE_COMPLETE_WITH_OPEN_BOUNDARIES":
        raise CompletionError("AI_PROGRESS.json has a stale or overclaiming state")


def _write_or_check(path: pathlib.Path, value: dict[str, Any], check: bool) -> None:
    expected = _json_bytes(value)
    if check:
        if not path.is_file():
            raise CompletionError(f"generated file is missing: {path.relative_to(ROOT)}")
        actual = path.read_bytes()
        if actual != expected:
            raise CompletionError(f"generated file is stale: {path.relative_to(ROOT)}")
    else:
        path.write_bytes(expected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("generate", "check"))
    parser.add_argument("--require-tag", action="store_true")
    args = parser.parse_args(argv)
    try:
        inventory, traceability, kernel_receipts, completion, tag_paths = _build()
        if args.require_tag:
            _validate_exact_tag(_load(SCOPE_PATH), tag_paths)
        for path, value in zip(
            OUTPUTS,
            (inventory, traceability, kernel_receipts, completion),
            strict=True,
        ):
            _write_or_check(path, value, args.action == "check")
        _validate_status_projections()
    except (CompletionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"BLOCK global completion: {exc}", file=sys.stderr)
        return 1
    print(
        "PASS global completion inventory: "
        f"{inventory['counts']['claims']} claims, "
        f"{inventory['counts']['kernel_eligible']} exact-tag kernel receipts, "
        f"{inventory['counts']['open']} OPEN boundaries; FINAL_PASS remains fail-closed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
