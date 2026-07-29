#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Verify the additive Batch-002 corrected candidate and owner-return package."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
BATCH_ID = "CONTENT-DISPOSITION-BATCH-002"
SUBJECT_ID = "SUBJECT-43c59da1cfd26267"
RECORD_ID = 21582781
DOI = "10.5281/zenodo.21582781"
AUTHORITY_BASE = "6a1555cd5ad418d9b243e2514d3271fb6c3a1585"

MATRIX = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/terminal-disposition/subjects/SUBJECT-43c59da1cfd26267/CLAIM_MATRIX.json"
DECISIONS = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/terminal-disposition/CONTENT_CHANGE_DECISIONS.json"
BOUNDARY = ROOT / "publications/ontology-des-unterschieds-reverse-engineering/corrections/v2/CLAIM_BOUNDARY.md"
PUBLICATION_CORRECTION = ROOT / "publications/ontology-des-unterschieds-reverse-engineering/corrections/v2/PUBLICATION_CORRECTION.json"
CORRECTION_README = ROOT / "publications/ontology-des-unterschieds-reverse-engineering/corrections/v2/README.md"
DENK = ROOT / "docs/axiome/denk_mengenlehre_corrected_candidate_v2.md"
DISPOSITION = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/corrected-candidate/SUBJECT-43c59da1cfd26267/CORRECTED_CLAIM_DISPOSITION.json"
OWNER_PACKAGE = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/corrected-candidate/SUBJECT-43c59da1cfd26267/OWNER_RETURN_PACKAGE.md"
OWNER_RECEIPT = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-002/corrected-candidate/SUBJECT-43c59da1cfd26267/OWNER_RETURN_RECEIPT.json"
WORK_UNIT = ROOT / "work-units/CREATE_CORRECTED_CANDIDATE_FOR_BATCH_002.json"

FROZEN_PUBLIC_FILES = {
    "META_REVIEW.md":
        "855687ec791c5d054ea235ad0388217954fdc0dc2d3e053684820a46289ac629",
    "ORIGINAL_ARTICLE.md":
        "0cc8077b032d805406f5cafe599dfa91f90e28a5bfa68292aaf4aaa232058589",
    "PUBLICATION.json":
        "a58c0f7fbe5ef0bf0e3fca1bcd379fedcf99e1a0b6bdf507d48682d50ac703dc",
    "README.md":
        "ed923d53022888f67ac49da271ae12bdaf9cf725b3986699b075a42cba0bae15",
}
REPOSITORY_SOURCE_FILES = {
    "META_REVIEW.md":
        "855687ec791c5d054ea235ad0388217954fdc0dc2d3e053684820a46289ac629",
    "ORIGINAL_ARTICLE.md":
        "0cc8077b032d805406f5cafe599dfa91f90e28a5bfa68292aaf4aaa232058589",
    "PUBLICATION.json":
        "adfcc0457baad9c120c054aa5acea3c575eaba135597a4002ab26eb2d92c6c27",
    "README.md":
        "ed923d53022888f67ac49da271ae12bdaf9cf725b3986699b075a42cba0bae15",
}
SOURCE_FILES = {
    ROOT / "publications/ontology-des-unterschieds-reverse-engineering" / name:
        digest
    for name, digest in REPOSITORY_SOURCE_FILES.items()
}

EXPECTED_OVERCLAIM_IDS = (
    "21582781-META-REVIEW-md-0002",
    "21582781-ORIGINAL-ARTICLE-md-0001",
    "21582781-ORIGINAL-ARTICLE-md-0067",
    "21582781-ORIGINAL-ARTICLE-md-0211",
)
OVERCLAIM = re.compile(
    r"\b(alles|allumfassend|absolut|universal(?:e|er|es)?|"
    r"vollständig bewiesen|endgültig bewiesen|unzweifelhaft|"
    r"gesamte wirklichkeit|gesamte natur)\b",
    re.IGNORECASE,
)


class E(RuntimeError):
    """Fail-closed validation error."""


def fail(message: str) -> None:
    raise E(message)


def read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def verify_source_files() -> None:
    for path, expected in SOURCE_FILES.items():
        if not path.is_file():
            fail(f"source file missing: {path.relative_to(ROOT)}")
        actual = sha256_bytes(path.read_bytes())
        if actual != expected:
            fail(f"repository source drift: {path.relative_to(ROOT)}")


def detected_overclaims(matrix: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for claim in matrix.get("claims", []):
        if not isinstance(claim, dict):
            fail("non-object claim")
        statement = claim.get("statement")
        claim_id = claim.get("claim_id")
        if not isinstance(statement, str) or not isinstance(claim_id, str):
            fail("claim identity missing")
        match = OVERCLAIM.search(statement)
        if not match:
            continue
        refs = claim.get("source_refs")
        if not isinstance(refs, list) or len(refs) != 1:
            fail(f"overclaim source binding not singular: {claim_id}")
        source = refs[0]
        rows.append({
            "claim_id": claim_id,
            "statement": statement,
            "statement_sha256": sha256_text(statement),
            "trigger": match.group(0),
            "source_file": source.get("file"),
        })
    return rows


def verify_exact_subject(matrix: Mapping[str, Any], decisions: Mapping[str, Any]) -> None:
    if matrix.get("batch_id") != BATCH_ID:
        fail("matrix batch mismatch")
    if matrix.get("subject_id") != SUBJECT_ID:
        fail("matrix subject mismatch")
    if matrix.get("record_ids") != [RECORD_ID]:
        fail("matrix record mismatch")
    if matrix.get("claim_count") != 248:
        fail("matrix claim count drift")
    content = matrix.get("content_change_decision", {})
    if content.get("required") is not True:
        fail("source correction no longer required")
    if content.get("state") != "VERSIONED_CORRECTION_REQUIRED":
        fail("source correction state drift")
    exact = [
        row for row in decisions.get("decisions", [])
        if row.get("subject_id") == SUBJECT_ID
    ]
    if len(exact) != 1:
        fail("exact content-change decision missing")
    if exact[0].get("required") is not True:
        fail("decision does not require correction")


def verify_boundary(text: str) -> None:
    required = (
        BATCH_ID,
        SUBJECT_ID,
        str(RECORD_ID),
        DOI,
        *EXPECTED_OVERCLAIM_IDS,
        "a universal solver for arbitrary problems",
        "Exact historical inversion requires",
        "interpretive hypothesis",
        "does not complete the correction until Ingolf Lohmann records",
    )
    for token in required:
        if token not in text:
            fail(f"boundary token missing: {token}")
    forbidden = (
        "FINAL_PASS = true",
        "EFFECT_ACK_DONE = true",
        "repository-wide PASS is established",
    )
    for token in forbidden:
        if token in text:
            fail(f"false completion in boundary: {token}")


def verify_candidate(
    candidate: Mapping[str, Any],
    matrix: Mapping[str, Any],
    boundary_text: str,
    publication_correction: Mapping[str, Any],
    denk_text: str,
) -> None:
    source = candidate.get("source_binding", {})
    if source.get("authority_base") != AUTHORITY_BASE:
        fail("authority base mismatch")
    if source.get("batch_id") != BATCH_ID:
        fail("candidate batch mismatch")
    if source.get("subject_id") != SUBJECT_ID:
        fail("candidate subject mismatch")
    if source.get("record_id") != RECORD_ID or source.get("doi") != DOI:
        fail("candidate record/DOI mismatch")
    if source.get("frozen_public_files") != FROZEN_PUBLIC_FILES:
        fail("frozen public-file binding mismatch")
    if source.get("repository_source_files") != REPOSITORY_SOURCE_FILES:
        fail("repository source-file binding mismatch")
    publication_source = publication_correction.get("source", {})
    if publication_source.get("frozen_public_files") != FROZEN_PUBLIC_FILES:
        fail("publication frozen-file binding mismatch")
    if publication_source.get("repository_source_files") != REPOSITORY_SOURCE_FILES:
        fail("publication repository-file binding mismatch")

    detected = detected_overclaims(matrix)
    if tuple(row["claim_id"] for row in detected) != EXPECTED_OVERCLAIM_IDS:
        fail("detected overclaim set drift")
    bound = candidate.get("detected_overclaim_bindings")
    if not isinstance(bound, list):
        fail("candidate overclaim bindings missing")
    if tuple(row.get("claim_id") for row in bound) != EXPECTED_OVERCLAIM_IDS:
        fail("candidate overclaim IDs mismatch")
    by_id = {row["claim_id"]: row for row in detected}
    for row in bound:
        expected = by_id[row["claim_id"]]
        for key in ("statement", "statement_sha256", "source_file"):
            if row.get(key) != expected[key]:
                fail(f"overclaim binding mismatch: {row['claim_id']}:{key}")

    regenerated = candidate.get("regenerated_disposition", {})
    if regenerated.get("historical_claim_matrix_mutated") is not False:
        fail("historical matrix mutation claimed")
    if regenerated.get("historical_public_bytes_mutated") is not False:
        fail("historical public bytes mutation claimed")
    if regenerated.get("candidate_state") != "READY_FOR_OWNER_ACCEPTANCE":
        fail("candidate state mismatch")
    if regenerated.get("owner_acceptance") != "PENDING":
        fail("owner acceptance was inferred")
    boundary_ref = regenerated.get("boundary_artifact", {})
    if boundary_ref.get("sha256") != sha256_text(boundary_text):
        fail("boundary digest mismatch")
    if publication_correction.get("correction", {}).get("owner_acceptance") != "PENDING":
        fail("publication correction owner gate mismatch")

    separation = candidate.get("scope_separation", {})
    if separation.get("content_disposition_scope") != BATCH_ID:
        fail("content-disposition scope mismatch")
    if separation.get("user_supplied_text_scope") != "DENK-MENGENLEHRE-BATCH-002":
        fail("Denk-Mengenlehre scope mismatch")
    if separation.get("scopes_equal") is not False:
        fail("distinct scopes collapsed")
    if separation.get("denk_candidate_resolves_zenodo_subject") is not False:
        fail("Denk candidate falsely resolves Zenodo subject")
    if separation.get("user_supplied_text_sha256") != sha256_text(denk_text):
        fail("Denk candidate digest mismatch")

    completion = candidate.get("completion_claims", {})
    required_false = (
        "owner_acceptance_recorded",
        "content_correction_review_complete",
        "all_content_claims_dispositioned",
        "proof_corpus_published_on_zenodo",
        "pass",
        "final_pass",
        "effect_ack_done",
    )
    for key in required_false:
        if completion.get(key) is not False:
            fail(f"false completion claim: {key}")
    if completion.get("corrected_candidate_created") is not True:
        fail("candidate creation not recorded")
    if completion.get("owner_return_package_created") is not True:
        fail("owner return not recorded")


def verify_denk_candidate(text: str) -> None:
    required = (
        "DENK-MENGENLEHRE-BATCH-002",
        "CONTENT-DISPOSITION-BATCH-002",
        r"\varnothing\subseteq G",
        r"\varnothing\in\mathcal T",
        r"\operatorname{cl}:\mathcal P(U)\to\mathcal T",
        r"R_{\mathrm{meta}}\subseteq\mathcal T_{\mathrm{meta}}\times\mathcal T",
        "KANDIDAT_IN_DIESEM_PR",
        "NICHT_DURCH_DIESEN_EFFEKT_AUSGEFÜHRT",
    )
    for token in required:
        if token not in text:
            fail(f"Denk candidate token missing: {token}")
    if "dieser Scope ist identisch" in text:
        fail("Denk scope collapsed into corpus scope")


def verify_owner_receipt(
    receipt: Mapping[str, Any],
    candidate_texts: Mapping[str, str],
) -> None:
    if receipt.get("state") != "RETURNED_FOR_OWNER_ACCEPTANCE":
        fail("owner-return state mismatch")
    owner = receipt.get("returned_to", {})
    if owner.get("type") != "NATURAL_PERSON" or owner.get("name") != "Ingolf Lohmann":
        fail("responsible owner mismatch")
    decision = receipt.get("owner_decision", {})
    if decision.get("state") != "PENDING":
        fail("owner decision was inferred")
    if decision.get("recorded_at") is not None or decision.get("evidence_ref") is not None:
        fail("owner decision evidence forged")
    artifacts = receipt.get("artifacts", {})
    for path, text in candidate_texts.items():
        if artifacts.get(path) != sha256_text(text):
            fail(f"owner-return artifact digest mismatch: {path}")
    completion = receipt.get("completion_claims", {})
    if completion.get("candidate_returned_to_owner") is not True:
        fail("return effect not recorded")
    for key in (
        "owner_acceptance_recorded",
        "content_correction_review_complete",
        "zenodo_mutation_authorized",
        "pass",
        "final_pass",
        "effect_ack_done",
    ):
        if completion.get(key) is not False:
            fail(f"false owner-return completion claim: {key}")


def verify(root: pathlib.Path = ROOT) -> dict[str, Any]:
    del root  # Paths are intentionally fixed to the repository root.
    verify_source_files()
    matrix = read_json(MATRIX)
    decisions = read_json(DECISIONS)
    candidate = read_json(DISPOSITION)
    publication_correction = read_json(PUBLICATION_CORRECTION)
    receipt = read_json(OWNER_RECEIPT)
    work = read_json(WORK_UNIT)
    boundary_text = BOUNDARY.read_text(encoding="utf-8")
    correction_readme = CORRECTION_README.read_text(encoding="utf-8")
    denk_text = DENK.read_text(encoding="utf-8")
    owner_package = OWNER_PACKAGE.read_text(encoding="utf-8")
    publication_text = PUBLICATION_CORRECTION.read_text(encoding="utf-8")
    disposition_text = DISPOSITION.read_text(encoding="utf-8")

    verify_exact_subject(matrix, decisions)
    verify_boundary(boundary_text)
    verify_denk_candidate(denk_text)
    verify_candidate(candidate, matrix, boundary_text, publication_correction, denk_text)
    verify_owner_receipt(
        receipt,
        {
            BOUNDARY.relative_to(ROOT).as_posix(): boundary_text,
            PUBLICATION_CORRECTION.relative_to(ROOT).as_posix(): publication_text,
            CORRECTION_README.relative_to(ROOT).as_posix(): correction_readme,
            DISPOSITION.relative_to(ROOT).as_posix(): disposition_text,
            DENK.relative_to(ROOT).as_posix(): denk_text,
            OWNER_PACKAGE.relative_to(ROOT).as_posix(): owner_package,
        },
    )
    if work.get("subject_id") != SUBJECT_ID:
        fail("work-unit subject mismatch")
    if work.get("next_deterministic_effect") != "OWNER_REVIEW_CORRECTED_CANDIDATE_FOR_BATCH_002":
        fail("work-unit next effect mismatch")
    for key in ("pass", "final_pass", "effect_ack_done"):
        if work.get("completion_claims", {}).get(key) is not False:
            fail(f"work-unit false completion claim: {key}")

    return {
        "schema": "qikvrt_corrected_candidate_verification_result_v1",
        "state": "CORRECTED_CANDIDATE_READY_FOR_OWNER_ACCEPTANCE",
        "authority_base": AUTHORITY_BASE,
        "batch_id": BATCH_ID,
        "subject_id": SUBJECT_ID,
        "record_id": RECORD_ID,
        "doi": DOI,
        "overclaim_claim_ids": list(EXPECTED_OVERCLAIM_IDS),
        "historical_bytes_mutated": False,
        "owner": "Ingolf Lohmann",
        "owner_acceptance": "PENDING",
        "next_deterministic_effect": "OWNER_REVIEW_CORRECTED_CANDIDATE_FOR_BATCH_002",
        "completion_claims": {
            "candidate_returned_to_owner": True,
            "owner_acceptance_recorded": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
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
            "failure_class": "BATCH002_CORRECTED_CANDIDATE_VALIDATION_FAILED",
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
