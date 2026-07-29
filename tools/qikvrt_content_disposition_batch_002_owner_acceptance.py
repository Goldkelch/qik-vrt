#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Verify the explicit owner acceptance for the Batch-002 corrected candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
BATCH_ID = "CONTENT-DISPOSITION-BATCH-002"
SUBJECT_ID = "SUBJECT-43c59da1cfd26267"
RECORD_ID = 21582781
DOI = "10.5281/zenodo.21582781"
PR_NUMBER = 209
ACCEPTED_HEAD = "0c4d8654b16c0d36daf105c22b678a55ee938cb6"
AUTHORITY_BASE = "6a1555cd5ad418d9b243e2514d3271fb6c3a1585"
COMMENT_ID = 5122279522
COMMENT_CREATED_AT = "2026-07-29T19:00:40Z"
NEXT_EFFECT = "VERIFY_AND_PROMOTE_ACCEPTED_CORRECTED_CANDIDATE_TO_AUTHORITY"

CANDIDATE_ROOT = ROOT / (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-002/corrected-candidate/"
    "SUBJECT-43c59da1cfd26267"
)
ACCEPTANCE = CANDIDATE_ROOT / "OWNER_ACCEPTANCE_RECEIPT.json"
RETURN_RECEIPT = CANDIDATE_ROOT / "OWNER_RETURN_RECEIPT.json"
DISPOSITION = CANDIDATE_ROOT / "CORRECTED_CLAIM_DISPOSITION.json"
PUBLICATION_CORRECTION = (
    ROOT
    / "publications/ontology-des-unterschieds-reverse-engineering/"
      "corrections/v2/PUBLICATION_CORRECTION.json"
)
WORK_UNIT = ROOT / "work-units/OWNER_REVIEW_CORRECTED_CANDIDATE_FOR_BATCH_002.json"


class E(RuntimeError):
    """Fail-closed validation error."""


def fail(message: str) -> None:
    raise E(message)


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    framed = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(framed).hexdigest()


def validate_pending_source_history(
    owner_return: Mapping[str, Any],
    disposition: Mapping[str, Any],
    publication: Mapping[str, Any],
) -> None:
    """Require the pre-acceptance records to remain immutable event history."""
    if owner_return.get("state") != "RETURNED_FOR_OWNER_ACCEPTANCE":
        fail("owner-return history was rewritten")
    if owner_return.get("owner_decision", {}).get("state") != "PENDING":
        fail("pending owner-return event was mutated")
    if disposition.get("regenerated_disposition", {}).get("owner_acceptance") != "PENDING":
        fail("candidate event history was mutated")
    if publication.get("correction", {}).get("owner_acceptance") != "PENDING":
        fail("publication-correction event history was mutated")


def validate_acceptance(
    receipt: Mapping[str, Any],
    owner_return: Mapping[str, Any],
    disposition: Mapping[str, Any],
    publication: Mapping[str, Any],
) -> None:
    if receipt.get("schema") != "qikvrt_owner_acceptance_receipt_v1":
        fail("acceptance schema mismatch")
    if receipt.get("state") != "ACCEPTED" or receipt.get("decision") != "ACCEPT":
        fail("owner acceptance decision mismatch")
    if receipt.get("recorded_at") != COMMENT_CREATED_AT:
        fail("owner acceptance timestamp mismatch")

    owner = receipt.get("accepted_by", {})
    if (
        owner.get("type") != "NATURAL_PERSON"
        or owner.get("name") != "Ingolf Lohmann"
        or owner.get("github_login") != "ingolf-lohmann"
    ):
        fail("responsible owner identity mismatch")

    binding = receipt.get("candidate_binding", {})
    if binding.get("repository") != "Goldkelch/qik-vrt":
        fail("acceptance repository mismatch")
    if binding.get("pull_request") != PR_NUMBER:
        fail("acceptance PR mismatch")
    if binding.get("accepted_head") != ACCEPTED_HEAD:
        fail("accepted candidate head mismatch")
    if binding.get("authority_base") != AUTHORITY_BASE:
        fail("acceptance Authority base mismatch")
    if binding.get("owner_return_receipt_git_blob_sha1") != git_blob_sha1(
        RETURN_RECEIPT.read_bytes()
    ):
        fail("owner-return receipt blob binding mismatch")

    subject = receipt.get("subject_binding", {})
    if subject != {
        "batch_id": BATCH_ID,
        "doi": DOI,
        "record_id": RECORD_ID,
        "subject_id": SUBJECT_ID,
    }:
        fail("acceptance subject binding mismatch")

    evidence = receipt.get("decision_evidence", {})
    if evidence.get("type") != "GITHUB_PR_COMMENT":
        fail("owner decision evidence type mismatch")
    if evidence.get("id") != COMMENT_ID:
        fail("owner decision comment mismatch")
    if evidence.get("created_at") != COMMENT_CREATED_AT:
        fail("owner decision comment timestamp mismatch")
    body = evidence.get("body_binding", {})
    if body != {
        "accepted_candidate_head": ACCEPTED_HEAD,
        "decision": "ACCEPT",
        "operation": "OWNER_REVIEW_CORRECTED_CANDIDATE_FOR_BATCH_002",
        "responsible_owner": "Ingolf Lohmann",
    }:
        fail("owner decision body binding mismatch")

    if receipt.get("accepted_artifacts") != owner_return.get("artifacts"):
        fail("accepted artifact set differs from owner-return package")

    expected_superseded = {
        RETURN_RECEIPT.relative_to(ROOT).as_posix(): git_blob_sha1(
            RETURN_RECEIPT.read_bytes()
        ),
        DISPOSITION.relative_to(ROOT).as_posix(): git_blob_sha1(
            DISPOSITION.read_bytes()
        ),
        PUBLICATION_CORRECTION.relative_to(ROOT).as_posix(): git_blob_sha1(
            PUBLICATION_CORRECTION.read_bytes()
        ),
    }
    actual_superseded = {
        row.get("path"): row.get("git_blob_sha1")
        for row in receipt.get("supersedes_pending_owner_state_in", [])
        if isinstance(row, dict)
    }
    if actual_superseded != expected_superseded:
        fail("superseded pending-state binding mismatch")

    completion = receipt.get("completion_claims", {})
    for key in (
        "candidate_returned_to_owner",
        "content_correction_review_complete",
        "corrected_candidate_accepted",
        "owner_acceptance_recorded",
    ):
        if completion.get(key) is not True:
            fail(f"missing owner-acceptance completion: {key}")
    for key in (
        "all_content_claims_dispositioned",
        "authority_promotion_complete",
        "effect_ack_done",
        "final_pass",
        "mirror_synchronized",
        "pass",
        "proof_corpus_published_on_zenodo",
        "zenodo_mutation_authorized",
    ):
        if completion.get(key) is not False:
            fail(f"false completion or authorization: {key}")
    if receipt.get("next_deterministic_effect") != NEXT_EFFECT:
        fail("acceptance next effect mismatch")


def validate_work_unit(work: Mapping[str, Any]) -> None:
    if work.get("work_unit_id") != (
        "OWNER-REVIEW-CORRECTED-CANDIDATE-FOR-"
        "CONTENT-DISPOSITION-BATCH-002-20260729"
    ):
        fail("owner-review work-unit identity mismatch")
    if work.get("state") != "OWNER_ACCEPTANCE_RECORDED":
        fail("owner-review work-unit state mismatch")
    if work.get("decision") != "ACCEPT":
        fail("owner-review work-unit decision mismatch")
    if work.get("accepted_candidate_head") != ACCEPTED_HEAD:
        fail("owner-review accepted head mismatch")
    if work.get("next_deterministic_effect") != NEXT_EFFECT:
        fail("owner-review next effect mismatch")
    completion = work.get("completion_claims", {})
    for key in (
        "content_correction_review_complete",
        "corrected_candidate_accepted",
        "owner_acceptance_recorded",
    ):
        if completion.get(key) is not True:
            fail(f"work-unit acceptance completion missing: {key}")
    for key in (
        "zenodo_mutation_authorized",
        "pass",
        "final_pass",
        "effect_ack_done",
    ):
        if completion.get(key) is not False:
            fail(f"work-unit false completion or authorization: {key}")


def verify() -> dict[str, Any]:
    owner_return = read_json(RETURN_RECEIPT)
    disposition = read_json(DISPOSITION)
    publication = read_json(PUBLICATION_CORRECTION)
    acceptance = read_json(ACCEPTANCE)
    work = read_json(WORK_UNIT)

    validate_pending_source_history(owner_return, disposition, publication)
    validate_acceptance(acceptance, owner_return, disposition, publication)
    validate_work_unit(work)

    return {
        "schema": "qikvrt_owner_acceptance_verification_result_v1",
        "state": "OWNER_ACCEPTANCE_VERIFIED_FOR_BATCH_002",
        "decision": "ACCEPT",
        "accepted_candidate_head": ACCEPTED_HEAD,
        "batch_id": BATCH_ID,
        "subject_id": SUBJECT_ID,
        "record_id": RECORD_ID,
        "owner": "Ingolf Lohmann",
        "owner_acceptance_recorded": True,
        "zenodo_mutation_authorized": False,
        "next_deterministic_effect": NEXT_EFFECT,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify()
    except (E, OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {
            "state": "BLOCK",
            "failure_class": "BATCH002_OWNER_ACCEPTANCE_VALIDATION_FAILED",
            "reason": str(exc),
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(result["state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
