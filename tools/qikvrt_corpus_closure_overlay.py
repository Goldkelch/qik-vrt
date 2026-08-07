#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize the effective corpus-closure state from temporally ordered evidence.

Historical AI_PROGRESS remains untouched: it is evidence of what the earlier
projection concluded.  This overlay binds that projection to the later exact-head
Temporal Precedence receipt and removes only those correction blockers whose
workflow obligations are independently proven resolved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROGRESS = ROOT / "AI_PROGRESS.json"
PRECEDENCE = ROOT / "evidence/receipts/corpus-correction-temporal-precedence-current.json"
OUT = ROOT / "evidence/receipts/corpus-closure-effective-current.json"
CORRECTION_CLASS = "CORPUS_SUBJECT_VERSIONED_CORRECTION_REQUIRED"
ZENODO_CLASS = "ZENODO_RETROSPECTIVE_PROOF_CORPUS_MUTATION_NOT_AUTHORIZED"


def read(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    progress = read(PROGRESS)
    precedence = read(PRECEDENCE)

    if precedence.get("state") != "CORRECTION_WORKFLOW_RESOLVED_BY_LATER_ACCEPTANCE_PROMOTION_EQUALITY":
        raise SystemExit("BLOCK temporal-precedence receipt is not terminal")
    unresolved = precedence.get("current_unresolved_correction_subject_ids")
    if unresolved != []:
        raise SystemExit(f"BLOCK temporal-precedence receipt still has unresolved subjects: {unresolved!r}")

    historical = sorted(precedence.get("historical_correction_required_subject_ids") or [])
    stale_rows = [b for b in progress.get("blockers", []) if b.get("failure_class") == CORRECTION_CLASS]
    stale_subjects = sorted(b.get("affected_subject") for b in stale_rows)
    if stale_subjects != historical:
        raise SystemExit(f"BLOCK historical/root correction subject mismatch: {stale_subjects!r} != {historical!r}")

    surviving = [b for b in progress.get("blockers", []) if b.get("failure_class") != CORRECTION_CLASS]
    unexpected = [b for b in surviving if b.get("failure_class") != ZENODO_CLASS]
    if unexpected:
        raise SystemExit(f"BLOCK unexpected non-correction blockers remain: {unexpected!r}")

    claim_count = None
    open_claim_count = None
    scope = (progress.get("scopes") or {}).get("qikvrt-zenodo-canonical-union-2026-07-28-v1") or {}
    corpus = scope.get("retrospective_proof_corpus") or {}
    claim_count = corpus.get("claims")
    open_claim_count = corpus.get("explicit_open_claims")

    return {
        "schema": "qikvrt_corpus_closure_effective_v1",
        "state": "CORPUS_CORRECTION_WORKFLOW_CLOSED_PUBLICATION_EFFECT_STILL_UNAUTHORIZED",
        "temporal_rule": "LATER_ACCEPTANCE_PROMOTION_EQUALITY_EVIDENCE_SUPERSEDES_EARLIER_WORKFLOW_OBLIGATION_WITHOUT_REWRITING_HISTORY",
        "historical_root_projection_preserved": True,
        "historical_correction_required_subject_ids": historical,
        "current_unresolved_correction_subject_ids": [],
        "effective_blockers": surviving,
        "corpus_counts": {
            "claims": claim_count,
            "explicit_open_claims": open_claim_count,
        },
        "evidence": {
            "historical_root_projection": {"path": str(PROGRESS.relative_to(ROOT)), "sha256": digest(PROGRESS)},
            "temporal_precedence_receipt": {"path": str(PRECEDENCE.relative_to(ROOT)), "sha256": digest(PRECEDENCE)},
        },
        "next_deterministic_effect": "FREEZE_FINAL_ROUND_TRIP_PUBLICATION_BYTES",
        "boundaries": {
            "historical_claim_classifications_rewritten": False,
            "historical_public_bytes_rewritten": False,
            "zenodo_mutation_authorized": False,
            "zenodo_publication_complete": False,
            "physical_correspondence": "NOT_INFERRED",
            "empirical_confirmation": "NOT_INFERRED",
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def render(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = render(build())
    if args.materialize:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(text, encoding="utf-8", newline="\n")
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != text:
            raise SystemExit("BLOCK effective corpus-closure receipt missing or stale")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
