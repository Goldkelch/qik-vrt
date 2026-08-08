#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize effective corpus closure from temporally ordered evidence.

Historical AI_PROGRESS remains untouched: it is evidence of what the earlier
projection concluded. This overlay binds that projection to the later exact-head
Temporal Precedence receipt and derives the next repository-internal edge from
the canonical promoted Round Trip prepublication-return work unit.
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
PUBLICATION = ROOT / "state/work_units/ROUND_TRIP_PREPUBLICATION_RETURN_V1.json"
OUT = ROOT / "evidence/receipts/corpus-closure-effective-current.json"
CORRECTION_CLASS = "CORPUS_SUBJECT_VERSIONED_CORRECTION_REQUIRED"
ZENODO_CLASS = "ZENODO_RETROSPECTIVE_PROOF_CORPUS_MUTATION_NOT_AUTHORIZED"
EXPECTED_NEXT = "FREEZE_EXACT_ZENODO_UPLOAD_BUNDLE_AND_METADATA_THEN_EVALUATE_SINGLE_USE_EXACT_ARTIFACT_AUTHORIZATION"


def read(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    progress = read(PROGRESS)
    precedence = read(PRECEDENCE)
    publication = read(PUBLICATION)

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

    publication_state = publication.get("publication_state") or {}
    if publication_state.get("primary_publication_bytes_frozen") is not True:
        raise SystemExit("BLOCK canonical primary publication bytes are not frozen")
    if publication_state.get("pre_effect_return_receipt_materialized") is not True:
        raise SystemExit("BLOCK canonical pre-effect return receipt is not materialized")
    if publication_state.get("zenodo_upload_bundle_frozen") is not False:
        raise SystemExit("BLOCK canonical Zenodo upload-bundle state changed; reobserve before continuing")
    if publication_state.get("exact_artifact_zenodo_authorization_established") is not False:
        raise SystemExit("BLOCK exact-artifact Zenodo authorization state changed; reobserve before continuing")
    if publication_state.get("zenodo_effect_executed") is not False:
        raise SystemExit("BLOCK Zenodo effect state changed; reobserve before continuing")
    next_required = publication.get("next_required_operation")
    if next_required != EXPECTED_NEXT:
        raise SystemExit(f"BLOCK canonical publication next edge changed: {next_required!r}")

    scope = (progress.get("scopes") or {}).get("qikvrt-zenodo-canonical-union-2026-07-28-v1") or {}
    corpus = scope.get("retrospective_proof_corpus") or {}

    return {
        "schema": "qikvrt_corpus_closure_effective_v1",
        "state": "CORPUS_CORRECTION_WORKFLOW_CLOSED_PUBLICATION_EFFECT_STILL_UNAUTHORIZED",
        "temporal_rule": "LATER_ACCEPTANCE_PROMOTION_EQUALITY_EVIDENCE_SUPERSEDES_EARLIER_WORKFLOW_OBLIGATION_WITHOUT_REWRITING_HISTORY",
        "historical_root_projection_preserved": True,
        "historical_correction_required_subject_ids": historical,
        "current_unresolved_correction_subject_ids": [],
        "effective_blockers": surviving,
        "corpus_counts": {
            "claims": corpus.get("claims"),
            "explicit_open_claims": corpus.get("explicit_open_claims"),
        },
        "evidence": {
            "historical_root_projection": {"path": str(PROGRESS.relative_to(ROOT)), "sha256": digest(PROGRESS)},
            "temporal_precedence_receipt": {"path": str(PRECEDENCE.relative_to(ROOT)), "sha256": digest(PRECEDENCE)},
            "canonical_prepublication_state": {"path": str(PUBLICATION.relative_to(ROOT)), "sha256": digest(PUBLICATION)},
        },
        "next_deterministic_effect": next_required,
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
