#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Validate and project the owner return of six versioned corpus corrections."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_content_disposition_batch_003_remaining_archives_legacy as base

CORRECTION_ROOT = (
    ROOT
    / "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
      "content-disposition-batch-003/corrected-candidates"
)
POLICY = CORRECTION_ROOT / "CORRECTION_POLICY.json"
INDEX = CORRECTION_ROOT / "CORRECTED_CANDIDATE_INDEX.json"
OWNER_PACKAGE = CORRECTION_ROOT / "OWNER_RETURN_PACKAGE.md"
OWNER_RECEIPT = CORRECTION_ROOT / "OWNER_RETURN_RECEIPT.json"
SOURCE_WORK_UNIT = ROOT / "work-units/CREATE_VERSIONED_CORRECTED_CANDIDATES_REMAINING_CORPUS_SUBJECTS.json"
REVIEW_WORK_UNIT = ROOT / "work-units/OWNER_REVIEW_VERSIONED_CORRECTED_CANDIDATES_REMAINING_CORPUS_SUBJECTS.json"
AI_PROGRESS = ROOT / "AI_PROGRESS.json"
AI_STATUS = ROOT / "AI_STATUS.md"
TOOL_REL = "tools/qikvrt_remaining_corpus_corrected_candidates_owner_return.py"
NEXT_EFFECT = "OWNER_ACCEPT_OR_REJECT_VERSIONED_CORRECTED_CANDIDATES_REMAINING_CORPUS_SUBJECTS"
NEXT_SUBJECT_ID = "NONE"
RETURNED_AT = "2026-07-30T06:14:51Z"
SOURCE_EVIDENCE_HEAD = "f60810b56a35f6e3434f1cacaca05a83e494aba2"
POLICY_BLOB = "ebcbd80cb2d942c696c9235ad077e9779852f804"
INDEX_BLOB = "713150777d5b3d23571da3c3bca39d9dc4a2b3f5"

EXPECTED = {
    "SUBJECT-172dd9bc2738fa43": {
        "blob": "dc2a79f76d9ce5f025859f30c137527d59ae37e7",
        "decision_blob": "7a69dbaeb2c49189cdf08ab360512e7bd657bce5",
        "claims": 175,
        "mismatches": 18,
        "records": [20712301],
    },
    "SUBJECT-780b9bf86425cee3": {
        "blob": "11a020d055238492fd47c7acfa58b7a68a8ee81f",
        "decision_blob": "f2a88369d2adea0b2924d07aab3efd97c328d0b7",
        "claims": 176,
        "mismatches": 18,
        "records": [21266670],
    },
    "SUBJECT-7956d8acdc473825": {
        "blob": "6c882f051cd0fcfc712e1d9587f12fffb7c87b16",
        "decision_blob": "9ae808599a63a8a5129a2cd0b9504f6d81027485",
        "claims": 276,
        "mismatches": 6,
        "records": [21252415],
    },
    "SUBJECT-7fdb36aa7c07c07d": {
        "blob": "2270ee8ffac3b36b4db1918a4413eb90affc174d",
        "decision_blob": "cd544f9371a281813f1234fdea1dec507fe7f901",
        "claims": 209,
        "mismatches": 23,
        "records": [21267021],
    },
    "SUBJECT-b4849e1a2d6b2270": {
        "blob": "648e51025424076a3251afce78cd478b5a0991f9",
        "decision_blob": "ad1814c59bfb2146af24aa2335f229688e3c8fae",
        "claims": 100,
        "mismatches": 18,
        "records": [21244412, 21245282, 21245951, 21247297, 21247388],
    },
    "SUBJECT-ce2390f18618ad0c": {
        "blob": "2b9d921ba65bdc3b2c7dfc2bc75c02f7805578b6",
        "decision_blob": "ee6b72bea68d7ec23d2e48987de2f9af3a0c12ee",
        "claims": 276,
        "mismatches": 6,
        "records": [21252649],
    },
}

DispositionError = base.DispositionError
SubjectDispositionError = DispositionError
pretty = base.pretty


def fail(reason: str) -> None:
    raise DispositionError(reason)


def read(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def verify_underlying_corpus() -> tuple[dict[str, Any], dict[str, Any]]:
    for subject_id in base.ORDER:
        base.verify_subject(subject_id)
    batch_receipt = base.B3 / "CONTENT_DISPOSITION_BATCH_003_RECEIPT.json"
    if not batch_receipt.is_file():
        fail("Batch-003 terminal receipt missing beneath owner return")
    proof_index = read(base.PROOF / "RETROSPECTIVE_PROOF_CORPUS_INDEX.json")
    proof_receipt = read(base.PROOF / "RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json")
    if proof_index.get("subject_count") != 19 or len(proof_index.get("subjects", [])) != 19:
        fail("proof corpus subject count drift beneath owner return")
    for row in proof_index["subjects"]:
        path = ROOT / row["claim_matrix"]["path"]
        raw = path.read_bytes()
        binding = row["claim_matrix"]
        if (
            len(raw) != binding["bytes"]
            or base.sha(raw) != binding["sha256"]
            or base.blob(raw) != binding["git_blob_sha1"]
        ):
            fail(f"proof corpus matrix binding drift: {row['subject_id']}")
    completion = proof_receipt.get("completion_claims", {})
    if (
        proof_receipt.get("state") != "BUILT_AND_VERIFIED_PUBLICATION_NOT_AUTHORIZED"
        or completion.get("retrospective_proof_corpus_published_on_zenodo") is not False
        or completion.get("zenodo_mutation_authorized") is not False
    ):
        fail("proof corpus truth boundary drift beneath owner return")
    return proof_index, proof_receipt


def validate_return_evidence() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = (POLICY, INDEX, OWNER_PACKAGE, OWNER_RECEIPT, SOURCE_WORK_UNIT, REVIEW_WORK_UNIT)
    for path in required:
        if not path.is_file():
            fail(f"owner-return artifact missing: {path.relative_to(ROOT)}")
    if git_blob_sha1(POLICY.read_bytes()) != POLICY_BLOB:
        fail("correction policy blob drift")
    if git_blob_sha1(INDEX.read_bytes()) != INDEX_BLOB:
        fail("corrected candidate index blob drift")

    policy = read(POLICY)
    index = read(INDEX)
    receipt = read(OWNER_RECEIPT)
    source_work = read(SOURCE_WORK_UNIT)
    review_work = read(REVIEW_WORK_UNIT)

    if (
        policy.get("schema") != "qikvrt_versioned_correction_policy_v1"
        or policy.get("source_evidence_head") != SOURCE_EVIDENCE_HEAD
        or policy.get("historical_source_bytes", {}).get("rewrite_permitted") is not False
        or policy.get("mandatory_candidate_boundary", {}).get("owner_decision") != "PENDING"
    ):
        fail("correction policy boundary drift")
    if (
        index.get("schema") != "qikvrt_versioned_corrected_candidate_index_v1"
        or index.get("source_evidence_head") != SOURCE_EVIDENCE_HEAD
        or index.get("candidate_count") != 6
        or index.get("selected_correction_claim_count") != 1212
        or index.get("observed_internal_hash_mismatch_count") != 89
        or index.get("next_deterministic_effect") != NEXT_EFFECT
    ):
        fail("corrected candidate index identity drift")

    rows = index.get("candidates", [])
    by_subject = {row.get("subject_id"): row for row in rows if isinstance(row, Mapping)}
    if set(by_subject) != set(EXPECTED) or len(rows) != len(by_subject):
        fail("corrected candidate subject set drift")
    for subject_id, expected in EXPECTED.items():
        row = by_subject[subject_id]
        path = ROOT / row["path"]
        if not path.is_file() or git_blob_sha1(path.read_bytes()) != expected["blob"]:
            fail(f"corrected candidate blob drift: {subject_id}")
        candidate = read(path)
        source = candidate.get("source_evidence", {})
        truth = candidate.get("truth_boundary", {})
        if (
            candidate.get("schema") != "qikvrt_versioned_corrected_candidate_v1"
            or candidate.get("subject_id") != subject_id
            or candidate.get("candidate_state") != "READY_FOR_OWNER_REVIEW"
            or candidate.get("owner_review", {}).get("decision") != "PENDING"
            or candidate.get("record_ids") != expected["records"]
            or candidate.get("claim_selector", {}).get("selected_claim_count") != expected["claims"]
            or source.get("content_change_decision", {}).get("git_blob_sha1") != expected["decision_blob"]
            or source.get("internal_hash_binding_audit", {}).get("mismatch_count") != expected["mismatches"]
            or truth.get("historical_public_bytes_changed") is not False
            or any(truth.get(key) is not False for key in ("pass", "final_pass", "effect_ack_done", "upload_executed", "publication_executed", "zenodo_mutation_authorized"))
        ):
            fail(f"corrected candidate boundary drift: {subject_id}")
        decision_path = ROOT / source["content_change_decision"]["path"]
        if git_blob_sha1(decision_path.read_bytes()) != expected["decision_blob"]:
            fail(f"source content decision drift: {subject_id}")

    if (
        receipt.get("schema") != "qikvrt_owner_return_receipt_v1"
        or receipt.get("state") != "RETURNED_TO_OWNER_DECISION_PENDING"
        or receipt.get("owner", {}).get("name") != "Ingolf Lohmann"
        or receipt.get("owner", {}).get("type") != "NATURAL_PERSON"
        or receipt.get("owner", {}).get("decision") != "PENDING"
        or receipt.get("candidate_index", {}).get("git_blob_sha1") != INDEX_BLOB
        or receipt.get("return_channel", {}).get("repository") != "Goldkelch/qik-vrt"
        or receipt.get("return_channel", {}).get("branch") != "agent/remaining-corpus-corrected-candidates-owner-return-v1"
        or receipt.get("return_channel", {}).get("pull_request") != 231
    ):
        fail("owner return receipt identity drift")
    if (
        source_work.get("state") != "RETURNED_TO_OWNER_DECISION_PENDING"
        or source_work.get("next_deterministic_effect") != NEXT_EFFECT
        or review_work.get("state") != "WAITING_FOR_OWNER_DECISION"
        or review_work.get("decision") != "PENDING"
        or review_work.get("next_deterministic_effect") != NEXT_EFFECT
    ):
        fail("owner review work-unit state drift")
    for value in (index.get("truth_boundary", {}), receipt.get("completion_claims", {}), source_work.get("truth_boundary", {}), review_work.get("truth_boundary", {})):
        if any(value.get(key) is not False for key in ("pass", "final_pass", "effect_ack_done", "zenodo_mutation_authorized")):
            fail("owner return completion inflation")
    return index, receipt, review_work


def build_progress_projection() -> tuple[dict[str, Any], str]:
    proof_index, proof_receipt = verify_underlying_corpus()
    candidate_index, owner_receipt, _ = validate_return_evidence()
    progress, _ = base.build_progress_projection()
    progress = copy.deepcopy(progress)
    progress.update(
        state="WORKING",
        effect_state="EFFECT_ACK_CONTINUE",
        percent=100,
        current_action=(
            "Six versioned corrected candidates covering exactly 1,212 correction claims "
            "have been returned to Ingolf Lohmann; explicit ACCEPT or REJECT is pending."
        ),
        pending_steps=[
            "Record Ingolf Lohmann's explicit ACCEPT or REJECT decision for the exact indexed candidate set",
            "Run all mandatory exact-head gates and promote only owner-accepted candidates",
            "Require a separate explicit Zenodo mutation authorization before any upload or proof-corpus publication",
        ],
        next_action=NEXT_EFFECT,
        updated_at=owner_receipt.get("returned_at", RETURNED_AT),
        union_receipt_state="ALL_SUBJECTS_DISPOSITIONED_CORRECTED_CANDIDATES_RETURNED_OWNER_DECISION_PENDING",
    )
    progress["blockers"] = [
        {
            "failure_class": "OWNER_DECISION_PENDING_FOR_REMAINING_CORPUS_CORRECTED_CANDIDATES",
            "affected_artifacts": [
                INDEX.relative_to(ROOT).as_posix(),
                OWNER_RECEIPT.relative_to(ROOT).as_posix(),
                REVIEW_WORK_UNIT.relative_to(ROOT).as_posix(),
            ],
            "smallest_repair": "Ingolf Lohmann records ACCEPT or REJECT for the exact indexed six-candidate set.",
        },
        {
            "failure_class": "ZENODO_RETROSPECTIVE_PROOF_CORPUS_MUTATION_NOT_AUTHORIZED",
            "affected_artifacts": [
                "work-units/REQUEST_SEPARATE_ZENODO_MUTATION_AUTHORIZATION_RETROSPECTIVE_PROOF_CORPUS.json",
                proof_receipt["proof_corpus_index"]["path"],
            ],
            "smallest_repair": "After accepted corrections are promoted, separately authorize exact proof-corpus bytes and mutation scope.",
        },
    ]
    step = "Create six versioned corrected candidates and return the exact indexed set to Ingolf Lohmann"
    if step not in progress["completed_steps"]:
        progress["completed_steps"].append(step)
    scope = progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
    scope.update(
        state="CONTENT_DISPOSITION_COMPLETE_CORRECTIONS_RETURNED_OWNER_DECISION_PENDING",
        effect_state="EFFECT_ACK_CONTINUE",
        boundary=(
            "All 19 subjects are terminally classified and the retrospective proof corpus is built. "
            "Six versioned corrections are returned to the owner; no upload, publication or Zenodo mutation is authorized."
        ),
        next_action=NEXT_EFFECT,
        corrected_candidates={
            "state": "RETURNED_TO_OWNER_DECISION_PENDING",
            "candidate_count": candidate_index["candidate_count"],
            "selected_correction_claim_count": candidate_index["selected_correction_claim_count"],
            "observed_internal_hash_mismatch_count": candidate_index["observed_internal_hash_mismatch_count"],
            "candidate_index": INDEX.relative_to(ROOT).as_posix(),
            "owner_return_receipt": OWNER_RECEIPT.relative_to(ROOT).as_posix(),
            "owner": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "owner_decision": "PENDING",
            "zenodo_mutation_authorized": False,
        },
    )
    progress["projection_owner"] = {
        "check_command": f"python3 -B {TOOL_REL} --check",
        "tool": TOOL_REL,
    }
    validate_progress_projection(progress)
    status = f"""# QIK-VRT Work Status

Repository: `Goldkelch/qik-vrt`

Updated at: `{owner_receipt.get('returned_at', RETURNED_AT)}`

Snapshot state: **`WORKING`**. Overall effect state: **`EFFECT_ACK_CONTINUE`**. No repository-wide `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, Zenodo publication, deployment, merge or current Authority/Mirror symmetry is claimed.

`[███████████████████] 100%` — Zenodo-Subject-Disposition (19/19)

- ✓ All 19 canonical claim subjects terminally classified or explicitly `OPEN`
- ✓ {proof_index['claim_count']} claims indexed; {proof_index['explicit_open_claim_count']} explicitly `OPEN`; zero unclassified
- ✓ Retrospective proof corpus built and byte-verified
- ✓ Six versioned corrected candidates materialized for exactly 1,212 selected correction claims
- ✓ Historical public Zenodo bytes remain unchanged
- ▶ Owner decision pending: Ingolf Lohmann (`ACCEPT` or `REJECT`)
- ⛔ No upload, publication or Zenodo mutation is authorized

## BLOCK

`OWNER_DECISION_PENDING_FOR_REMAINING_CORPUS_CORRECTED_CANDIDATES`

Smallest repair: Ingolf Lohmann records `ACCEPT` or `REJECT` for the exact indexed candidate set.

## NEXT

`{NEXT_EFFECT}`
"""
    return progress, status


def validate_progress_projection(progress: Mapping[str, Any]) -> None:
    base.validate_progress_projection(progress)
    scope = progress.get("scopes", {}).get("qikvrt-zenodo-canonical-union-2026-07-28-v1", {})
    candidates = scope.get("corrected_candidates", {})
    if (
        progress.get("next_action") != NEXT_EFFECT
        or progress.get("union_receipt_state") != "ALL_SUBJECTS_DISPOSITIONED_CORRECTED_CANDIDATES_RETURNED_OWNER_DECISION_PENDING"
        or candidates.get("state") != "RETURNED_TO_OWNER_DECISION_PENDING"
        or candidates.get("candidate_count") != 6
        or candidates.get("selected_correction_claim_count") != 1212
        or candidates.get("observed_internal_hash_mismatch_count") != 89
        or candidates.get("owner_decision") != "PENDING"
        or candidates.get("zenodo_mutation_authorized") is not False
    ):
        fail("owner-return progress projection drift")


def verify_materialized() -> dict[str, Any]:
    proof_index, _ = verify_underlying_corpus()
    candidate_index, _, _ = validate_return_evidence()
    progress, status = build_progress_projection()
    if read(AI_PROGRESS) != progress:
        fail("materialized owner-return output drift: AI_PROGRESS.json")
    if AI_STATUS.read_text(encoding="utf-8") != status:
        fail("materialized owner-return output drift: AI_STATUS.md")
    return {
        "schema": "qikvrt_remaining_corpus_corrected_candidates_owner_return_verification_v1",
        "state": "CORRECTED_CANDIDATES_RETURNED_TO_OWNER_DECISION_PENDING",
        "subject_count": 19,
        "claim_count": proof_index["claim_count"],
        "candidate_count": candidate_index["candidate_count"],
        "selected_correction_claim_count": candidate_index["selected_correction_claim_count"],
        "observed_internal_hash_mismatch_count": candidate_index["observed_internal_hash_mismatch_count"],
        "next_deterministic_effect": NEXT_EFFECT,
        "owner_decision": "PENDING",
        "historical_public_bytes_changed": False,
        "zenodo_mutation_authorized": False,
        "proof_corpus_published_on_zenodo": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def materialize() -> None:
    progress, status = build_progress_projection()
    AI_PROGRESS.write_text(pretty(progress), encoding="utf-8", newline="\n")
    AI_STATUS.write_text(status, encoding="utf-8", newline="\n")
    verify_materialized()


def compat_main() -> int:
    try:
        if "--materialize" in sys.argv:
            materialize()
        result = verify_materialized()
    except (DispositionError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "state": "BLOCK",
            "failure_class": "REMAINING_CORPUS_CORRECTED_CANDIDATES_OWNER_RETURN_INVALID",
            "reason": str(exc),
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "zenodo_mutation_authorized": False,
        }, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if "--json" in sys.argv else None, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.materialize:
            materialize()
        result = verify_materialized()
    except (DispositionError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "state": "BLOCK",
            "failure_class": "REMAINING_CORPUS_CORRECTED_CANDIDATES_OWNER_RETURN_INVALID",
            "reason": str(exc),
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "zenodo_mutation_authorized": False,
        }, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
