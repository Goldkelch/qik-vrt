#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Project the newest durable corpus-correction evidence without rewriting history.

The historical proof-corpus index correctly records which frozen public subjects
required versioned correction. Later owner acceptance, Authority promotion and
reciprocal Authority/Mirror equality resolve the *workflow obligation* without
changing that historical diagnosis. This projector therefore preserves the
historical correction_requirements and derives the current action from newer,
independently persisted evidence.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROOF = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union/retrospective-proof-corpus"
OWNER = ROOT / "work-units/OWNER_DECISION_VERSIONED_CORRECTED_CANDIDATES.json"
PROMOTION = ROOT / "work-units/VERIFY_AND_PROMOTE_ACCEPTED_VERSIONED_CORRECTED_CANDIDATES_TO_AUTHORITY.json"
EQUALITY = ROOT / "evidence/receipts/authority-mirror-equality-2026-07-30-six-corrected-candidates-pr249-pr147.json"
OUT = ROOT / "evidence/receipts/corpus-correction-temporal-precedence-current.json"


def read(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    index_path = PROOF / "RETROSPECTIVE_PROOF_CORPUS_INDEX.json"
    index = read(index_path)
    owner = read(OWNER)
    promotion = read(PROMOTION)
    equality = read(EQUALITY)

    historical = sorted(x["subject_id"] for x in index["correction_requirements"])
    accepted = sorted(x["subject_id"] for x in promotion["accepted_candidates"])
    if historical != accepted:
        raise SystemExit(f"BLOCK correction/acceptance subject drift: {historical!r} != {accepted!r}")
    if owner.get("state") != "ACCEPTED_ALL_SIX":
        raise SystemExit("BLOCK owner acceptance is not terminal")
    claims = owner.get("completion_claims", {})
    if claims.get("all_owner_decisions_received") is not True or claims.get("candidate_promotion_authorized") is not True:
        raise SystemExit("BLOCK owner acceptance completion binding missing")

    # Equality receipt is the durable post-promotion evidence: require the exact
    # six-subject scope and a shared promoted pair, but do not infer repository-wide
    # equality or any Zenodo effect from it.
    eq_text = EQUALITY.read_text(encoding="utf-8")
    for subject in historical:
        if subject not in eq_text:
            raise SystemExit(f"BLOCK equality receipt omits accepted subject {subject}")
    if "7d87a6003135a6e3efbca34b2d898967d7f66018" not in eq_text:
        raise SystemExit("BLOCK expected Authority PR249 promotion not bound by equality receipt")

    return {
        "schema": "qikvrt_corpus_correction_temporal_precedence_v1",
        "state": "CORRECTION_WORKFLOW_RESOLVED_BY_LATER_ACCEPTANCE_PROMOTION_EQUALITY",
        "historical_diagnosis_preserved": True,
        "historical_correction_required_subject_ids": historical,
        "current_unresolved_correction_subject_ids": [],
        "evidence": {
            "historical_proof_corpus_index": {"path": str(index_path.relative_to(ROOT)), "sha256": sha256(index_path)},
            "owner_acceptance": {"path": str(OWNER.relative_to(ROOT)), "sha256": sha256(OWNER)},
            "authority_promotion_work_unit": {"path": str(PROMOTION.relative_to(ROOT)), "sha256": sha256(PROMOTION)},
            "reciprocal_equality_receipt": {"path": str(EQUALITY.relative_to(ROOT)), "sha256": sha256(EQUALITY)},
        },
        "next_deterministic_effect": "REOBSERVE_CORPUS_CLOSURE_THEN_FREEZE_FINAL_ROUND_TRIP_PUBLICATION_BYTES",
        "boundaries": {
            "historical_public_bytes_rewritten": False,
            "zenodo_mutation_authorized": False,
            "zenodo_publication_complete": False,
            "repository_wide_pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def main() -> int:
    value = build()
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if "--materialize" in __import__("sys").argv:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(rendered, encoding="utf-8", newline="\n")
    if "--check" in __import__("sys").argv:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("BLOCK temporal-precedence receipt missing or stale")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
