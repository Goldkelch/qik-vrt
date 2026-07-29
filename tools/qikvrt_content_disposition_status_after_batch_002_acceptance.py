#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Project the verified post-acceptance Batch-002 state without rewriting history."""

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

from tools import qikvrt_content_disposition_batch_002_terminal as terminal

BASE = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
QUEUE = BASE / "CONTENT_CLAIM_DISPOSITION_QUEUE.json"
INDEX = BASE / "CONTENT_CLAIM_DISPOSITION_INDEX.json"
UNION_RECEIPT = BASE / "CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json"
POST = BASE / (
    "content-disposition-batch-002/post-acceptance/"
    "POST_ACCEPTANCE_STATUS_PROJECTION.json"
)
OWNER_ACCEPTANCE = BASE / (
    "content-disposition-batch-002/corrected-candidate/"
    "SUBJECT-43c59da1cfd26267/OWNER_ACCEPTANCE_RECEIPT.json"
)
EQUALITY_RECEIPT = ROOT / (
    "evidence/receipts/"
    "authority-mirror-equality-2026-07-29-batch002-corrected-pr209-pr100.json"
)
AI_PROGRESS = ROOT / "AI_PROGRESS.json"
AI_STATUS = ROOT / "AI_STATUS.md"

NEXT_EFFECT = "EXECUTE_CONTENT_DISPOSITION_BATCH_003"
UPDATED_AT = "2026-07-29T22:16:38Z"
POST_REL = POST.relative_to(ROOT).as_posix()
OWNER_REL = OWNER_ACCEPTANCE.relative_to(ROOT).as_posix()
EQUALITY_REL = EQUALITY_RECEIPT.relative_to(ROOT).as_posix()

HISTORICAL_BLOBS = {
    QUEUE.relative_to(ROOT).as_posix():
        "3e5fd48c314fe02574ee67f1b22cbb4ba04003d7",
    INDEX.relative_to(ROOT).as_posix():
        "b72bccce7dcd13e2364bde30e31e482c754d8e18",
    UNION_RECEIPT.relative_to(ROOT).as_posix():
        "4769d622e59e99ece17e95c76b828b1c8aa72839",
}
OWNER_BLOB = "afe07dcbecd285917533f284287e560eaf7e29f7"
OWNER_SHA256 = "2de79451450e42af5e2e33f892ea5fbaa1a69ca8683ce34e79f145352a06e23e"
EQUALITY_BLOB = "fe9f2deac6eb935842829b21bd9625cb93a00269"
EQUALITY_SHA256 = "ba5267f60417f39ceb21efe271d191d0ba40d65dddbc6d17d47c72e672348658"
OPEN_SUBJECT_IDS = (
    "SUBJECT-2581811b342e505d",
    "SUBJECT-172dd9bc2738fa43",
    "SUBJECT-b4849e1a2d6b2270",
    "SUBJECT-7956d8acdc473825",
    "SUBJECT-ce2390f18618ad0c",
    "SUBJECT-780b9bf86425cee3",
    "SUBJECT-7fdb36aa7c07c07d",
)


class E(RuntimeError):
    """Fail-closed projection validation error."""


def fail(message: str) -> None:
    raise E(message)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"JSON root is not an object: {path.relative_to(ROOT)}")
    return value


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    framed = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(framed).hexdigest()


def historical_projection() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    source_queue, source_index, source_union = terminal.source_projection_inputs()
    receipt_path = terminal.OUT / "CONTENT_DISPOSITION_BATCH_002_RECEIPT.json"
    receipt_rel = receipt_path.relative_to(ROOT).as_posix()
    receipt = json.loads(terminal.source_capsule().files[receipt_rel])
    receipt.update({
        "work_unit_id": terminal.WORK_UNIT_ID,
        "observed_at": terminal.OBSERVED_AT,
        "union_id": source_index["union_id"],
    })
    terminal.validate_terminal_receipt(receipt, source_index)
    queue, index, union = terminal.project_status(
        source_queue,
        source_index,
        source_union,
        receipt["subjects"],
        int(receipt["claim_count"]),
        int(receipt["content_change_required_count"]),
    )
    receipt["next_deterministic_effect"] = queue["next_deterministic_effect"]
    terminal.validate_terminal_receipt(receipt, index)
    progress = terminal.build_ai_progress(queue, index, union, receipt)
    return queue, index, union, receipt, progress


def validate_historical_files(
    queue: Mapping[str, Any],
    index: Mapping[str, Any],
    union: Mapping[str, Any],
) -> tuple[str, ...]:
    expected_queue, expected_index, expected_union, _, _ = historical_projection()
    for path, expected_blob in HISTORICAL_BLOBS.items():
        raw = (ROOT / path).read_bytes()
        if git_blob_sha1(raw) != expected_blob:
            fail(f"historical projection blob drift: {path}")
    if queue != expected_queue or index != expected_index or union != expected_union:
        fail("historical terminal projection was rewritten instead of overlaid")

    active = queue.get("active_batch")
    if not isinstance(active, Mapping):
        fail("historical active batch missing")
    active_ids = tuple(
        str(row.get("subject_id"))
        for row in active.get("subjects", [])
        if isinstance(row, Mapping)
    )
    remaining_ids = tuple(str(value) for value in queue.get("remaining_subject_ids", []))
    open_ids = active_ids + remaining_ids
    if (
        active.get("batch_id") != "CONTENT-DISPOSITION-BATCH-003"
        or active.get("state") != "READY"
        or active.get("subject_count") != 6
        or queue.get("remaining_subject_count") != 1
        or open_ids != OPEN_SUBJECT_IDS
    ):
        fail("seven-subject Batch-003 partition drift")
    pending = [
        row for row in index.get("claim_subjects", [])
        if isinstance(row, Mapping) and row.get("claim_disposition_complete") is not True
    ]
    complete = [
        row for row in index.get("claim_subjects", [])
        if isinstance(row, Mapping) and row.get("claim_disposition_complete") is True
    ]
    if (
        len(index.get("claim_subjects", [])) != 19
        or len(complete) != 12
        or len(pending) != 7
        or sum(int(row["claim_count"]) for row in complete) != 1747
    ):
        fail("corpus counts drift")
    return open_ids


def validate_owner_acceptance(owner: Mapping[str, Any]) -> None:
    raw = OWNER_ACCEPTANCE.read_bytes()
    if git_blob_sha1(raw) != OWNER_BLOB or sha256_bytes(raw) != OWNER_SHA256:
        fail("owner-acceptance receipt byte binding drift")
    binding = owner.get("candidate_binding", {})
    completion = owner.get("completion_claims", {})
    if (
        owner.get("schema") != "qikvrt_owner_acceptance_receipt_v1"
        or owner.get("state") != "ACCEPTED"
        or owner.get("decision") != "ACCEPT"
        or owner.get("accepted_by", {}).get("name") != "Ingolf Lohmann"
        or binding.get("pull_request") != 209
        or binding.get("accepted_head")
        != "0c4d8654b16c0d36daf105c22b678a55ee938cb6"
        or owner.get("decision_evidence", {}).get("id") != 5122279522
        or completion.get("candidate_returned_to_owner") is not True
        or completion.get("owner_acceptance_recorded") is not True
        or completion.get("content_correction_review_complete") is not True
        or completion.get("zenodo_mutation_authorized") is not False
    ):
        fail("owner-acceptance semantics drift")
    for key in ("pass", "final_pass", "effect_ack_done"):
        if completion.get(key) is not False:
            fail(f"owner-acceptance release inflation: {key}")


def validate_equality_receipt(receipt: Mapping[str, Any]) -> None:
    raw = EQUALITY_RECEIPT.read_bytes()
    if git_blob_sha1(raw) != EQUALITY_BLOB or sha256_bytes(raw) != EQUALITY_SHA256:
        fail("reciprocal equality receipt byte binding drift")
    claims = receipt.get("claims", {})
    equality = receipt.get("equality", {})
    authority = receipt.get("authority", {})
    mirror = receipt.get("mirror", {})
    reciprocal = receipt.get("reciprocal_repository_binding", {})
    if (
        receipt.get("receipt_id")
        != "authority-mirror-equality-2026-07-29-batch002-corrected-pr209-pr100"
        or receipt.get("state") != "equality_verified_for_scoped_promotion"
        or authority.get("main") != "524fabd51f3492aa99da1430557f4f515074450e"
        or authority.get("promotion_pull_request") != 209
        or mirror.get("main") != "a8b85fbf3222da1e528505a760c184d48e112329"
        or mirror.get("synchronization_pull_request") != 100
        or equality.get("shared_git_tree_sha1")
        != "e38a9890826e71ce971234f64f5f35e651a00800"
        or equality.get("repository_content_tree_sha256")
        != "6ac38cf4b33b638dcc57ac415eb2bee626ade900998f72c2e2a542890535d113"
        or reciprocal.get("binding_payload_sha256")
        != "7a3b9bb21cbabc124c2f79b7975ab3f83d64b2ea9e6f0a5da2c5328b2434c1da"
        or claims.get("authority_mirror_equality_verified") is not True
        or claims.get("corrected_candidate_owner_accepted") is not True
        or claims.get("content_correction_review_complete") is not True
        or claims.get("scoped_promotion_chain_complete") is not True
        or claims.get("zenodo_mutation_authorized") is not False
    ):
        fail("reciprocal equality semantics drift")
    for key in (
        "all_content_claims_dispositioned",
        "pass",
        "final_pass",
        "effect_ack_done",
        "proof_corpus_published_on_zenodo",
        "zenodo_corpus_complete",
    ):
        if claims.get(key) is not False:
            fail(f"reciprocal receipt release inflation: {key}")


def validate_post_projection(
    post: Mapping[str, Any],
    open_ids: tuple[str, ...],
) -> None:
    base = post.get("base_projection", {})
    evidence = post.get("evidence", {})
    owner = evidence.get("owner_acceptance", {})
    promotions = evidence.get("promotion_chain", {})
    reciprocal = evidence.get("reciprocal_receipt", {})
    corpus = post.get("preserved_corpus", {})
    projection = post.get("projection", {})
    completion = post.get("completion_claims", {})
    if (
        post.get("schema")
        != "qikvrt_content_disposition_post_acceptance_status_projection_v1"
        or post.get("observed_at") != UPDATED_AT
        or base.get("queue_git_blob_sha1") != HISTORICAL_BLOBS[QUEUE.relative_to(ROOT).as_posix()]
        or base.get("index_git_blob_sha1") != HISTORICAL_BLOBS[INDEX.relative_to(ROOT).as_posix()]
        or base.get("union_receipt_git_blob_sha1")
        != HISTORICAL_BLOBS[UNION_RECEIPT.relative_to(ROOT).as_posix()]
        or base.get("terminal_projection_preserved") is not True
        or owner.get("path") != OWNER_REL
        or owner.get("git_blob_sha1") != OWNER_BLOB
        or owner.get("sha256") != OWNER_SHA256
        or owner.get("decision") != "ACCEPT"
        or reciprocal.get("path") != EQUALITY_REL
        or reciprocal.get("git_blob_sha1") != EQUALITY_BLOB
        or reciprocal.get("sha256") != EQUALITY_SHA256
        or reciprocal.get("authority", {}).get("pull_request") != 213
        or reciprocal.get("authority", {}).get("merge_commit")
        != "10b5a86e967e554aca698fa36817e92ad4e1887d"
        or reciprocal.get("mirror", {}).get("pull_request") != 101
        or reciprocal.get("mirror", {}).get("merge_commit")
        != "c0bbf85881c996cca5fff32be91847b7e537a493"
        or promotions.get("authority", {}).get("promotion_pull_request") != 209
        or promotions.get("mirror", {}).get("promotion_pull_request") != 100
        or corpus.get("subject_count") != 19
        or corpus.get("dispositioned_subject_count") != 12
        or corpus.get("open_subject_count") != 7
        or tuple(corpus.get("open_subject_ids", [])) != open_ids
        or corpus.get("active_batch", {}).get("batch_id")
        != "CONTENT-DISPOSITION-BATCH-003"
        or corpus.get("active_batch", {}).get("state") != "READY"
        or corpus.get("active_batch", {}).get("subject_count") != 6
        or corpus.get("queued_after_active") != 1
        or projection.get("batch_002_state")
        != "CORRECTION_ACCEPTED_PROMOTED_AND_RECIPROCALLY_BOUND"
        or projection.get("next_deterministic_effect") != NEXT_EFFECT
        or projection.get("active_batch") != "CONTENT-DISPOSITION-BATCH-003"
    ):
        fail("post-acceptance status projection drift")

    for key in (
        "corrected_candidate_created",
        "candidate_returned_to_owner",
        "owner_acceptance_recorded",
        "content_correction_review_complete",
        "authority_promotion_complete",
        "mirror_synchronized",
        "reciprocal_equality_receipt_complete",
    ):
        if completion.get(key) is not True:
            fail(f"post-acceptance completion missing: {key}")
    for key in (
        "all_content_claims_dispositioned",
        "proof_corpus_published_on_zenodo",
        "zenodo_mutation_authorized",
        "pass",
        "final_pass",
        "effect_ack_done",
    ):
        if completion.get(key) is not False:
            fail(f"post-acceptance false completion: {key}")


def build_progress(
    historical_progress: Mapping[str, Any],
    post: Mapping[str, Any],
) -> dict[str, Any]:
    progress = copy.deepcopy(dict(historical_progress))
    corpus_id = str(progress["percent_scope"])
    corpus = progress["scopes"][corpus_id]
    batch = corpus["batch_002"]

    progress["updated_at"] = UPDATED_AT
    progress["current_action"] = "No live operation owns this stable post-acceptance handoff snapshot."
    progress["completed_steps"] = [
        "Build the canonical 24-record Zenodo union with 19 byte-distinct claim subjects",
        "Terminally disposition Batch 001 with six subjects",
        "Terminally disposition Batch 002 with 6 subjects and 1489 claims",
        "Stage Batch 003 deterministically with six subjects and one subject beyond the active batch",
        "Create the required corrected Batch-002 candidate and return it to Ingolf Lohmann",
        "Record Ingolf Lohmann's explicit ACCEPT decision for the exact corrected candidate",
        "Promote the accepted corrected candidate through Authority PR #209 and Mirror PR #100",
        "Persist the independently gated reciprocal equality receipt through Authority PR #213 and Mirror PR #101",
    ]
    progress["pending_steps"] = [
        "Terminally disposition the seven remaining Zenodo claim subjects beginning with Batch 003",
        "Build and verify the retrospective proof corpus before any publication effect",
        "Require separate authorization and byte verification for every later Zenodo mutation",
    ]
    progress["next_action"] = NEXT_EFFECT
    progress["source_semantics"] = (
        "Historical terminal-disposition source capsule preserved unchanged; "
        "the current post-acceptance state is an additive evidence overlay bound "
        f"by {POST_REL}."
    )
    progress["projection_owner"] = {
        "tool": "tools/qikvrt_content_disposition_status_after_batch_002_acceptance.py",
        "check_command": (
            "python3 -B tools/"
            "qikvrt_content_disposition_status_after_batch_002_acceptance.py "
            "--check-status-projection"
        ),
    }
    progress["union_receipt_state"] = post["projection"]["union_receipt_state"]
    progress["repository_effects"]["scope"] = (
        "The compatibility fields remain NOT_EVALUATED; exact current Authority, "
        "Mirror and reciprocal-receipt evidence is bound inside the Zenodo corpus "
        f"scope by {POST_REL}."
    )

    batch.update({
        "state": "CORRECTION_ACCEPTED_PROMOTED_AND_RECIPROCALLY_BOUND",
        "corrected_candidate_count": 1,
        "corrected_candidate_required_count": 1,
        "owner_return_complete": True,
        "owner_acceptance_recorded": True,
        "content_correction_review_complete": True,
        "authority_promotion_complete": True,
        "mirror_promotion_complete": True,
        "reciprocal_equality_receipt_complete": True,
        "evidence": {
            "terminal_disposition": {
                "path": (
                    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
                    "content-disposition-batch-002/terminal-disposition/"
                    "CONTENT_DISPOSITION_BATCH_002_RECEIPT.json"
                ),
                "sha256": "e656e54e5d15733a3930a280e5933f36c6c91e5b1827534d662983cb640bcadc",
            },
            "post_acceptance_projection": POST_REL,
            "owner_acceptance": {
                "path": OWNER_REL,
                "sha256": OWNER_SHA256,
                "git_blob_sha1": OWNER_BLOB,
            },
            "reciprocal_equality": {
                "path": EQUALITY_REL,
                "sha256": EQUALITY_SHA256,
                "git_blob_sha1": EQUALITY_BLOB,
            },
        },
    })
    corpus["active_batch"] = {
        "batch_id": "CONTENT-DISPOSITION-BATCH-003",
        "state": "READY",
        "subjects": 6,
    }
    corpus["queued_after_active"] = 1
    corpus["evidence"] = POST_REL
    corpus["boundary"] = (
        "Batch-002 correction creation, owner return, owner acceptance, Authority "
        "promotion, Mirror promotion and reciprocal equality are complete for the "
        "bound scope. Seven claim subjects, the retrospective proof corpus and any "
        "Zenodo mutation remain open."
    )
    corpus["next_action"] = NEXT_EFFECT
    return progress


def validate_progress(progress: Mapping[str, Any], post: Mapping[str, Any]) -> None:
    corpus = progress.get("scopes", {}).get(
        "qikvrt-zenodo-canonical-union-2026-07-28-v1", {}
    )
    batch = corpus.get("batch_002", {})
    effects = progress.get("repository_effects", {})
    if (
        progress.get("schema") != "qikvrt-ai-progress/3.1"
        or progress.get("state") != "IDLE"
        or progress.get("effect_state") != "EFFECT_ACK_CONTINUE"
        or progress.get("percent") != 63
        or progress.get("next_action") != NEXT_EFFECT
        or progress.get("updated_at") != UPDATED_AT
        or progress.get("projection_owner", {}).get("tool")
        != "tools/qikvrt_content_disposition_status_after_batch_002_acceptance.py"
        or progress.get("union_receipt_state")
        != post.get("projection", {}).get("union_receipt_state")
        or corpus.get("counts", {}).get("subjects") != 19
        or corpus.get("counts", {}).get("dispositioned_subjects") != 12
        or corpus.get("counts", {}).get("open_subjects") != 7
        or corpus.get("next_action") != NEXT_EFFECT
        or batch.get("state")
        != "CORRECTION_ACCEPTED_PROMOTED_AND_RECIPROCALLY_BOUND"
        or batch.get("owner_acceptance_recorded") is not True
        or batch.get("reciprocal_equality_receipt_complete") is not True
        or set(effects) != {
            "scope",
            "authority_promotion",
            "mirror_synchronization",
            "reciprocal_equality_receipt",
            "proof_corpus_publication",
        }
        or any(
            value != "NOT_EVALUATED"
            for key, value in effects.items()
            if key != "scope"
        )
    ):
        fail("AI_PROGRESS post-acceptance projection drift")
    claims = progress.get("claims", {})
    scope_claims = corpus.get("claims", {})
    for mapping, label in ((claims, "top-level"), (scope_claims, "corpus")):
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            if mapping.get(key) is not False:
                fail(f"{label} release inflation: {key}")


def render_ai_status(progress: Mapping[str, Any]) -> str:
    corpus = progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
    global_scope = progress["scopes"]["qikvrt-global-claim-scope-v1"]
    counts = corpus["counts"]
    batch = corpus["batch_002"]
    active = corpus["active_batch"]
    global_counts = global_scope["counts"]
    bar = "█" * counts["dispositioned_subjects"] + "░" * counts["open_subjects"]
    equality = batch["evidence"]["reciprocal_equality"]
    return f"""# QIK-VRT Work Status

Repository: `Goldkelch/qik-vrt`

Historical projection input ref: `{progress['ref_name']}`

Historical projection source: `{progress['source_sha']}`

Post-acceptance overlay: `{POST_REL}`

Updated at: `{progress['updated_at']}`

Snapshot state: **`{progress['state']}`**. Overall effect state:
**`{progress['effect_state']}`**. No unqualified repository-wide
`PASS`, `FINAL_PASS`, Zenodo publication or corpus completion is claimed.

`[{bar}] {corpus['percent']}%` — Zenodo-Subject-Disposition
({counts['dispositioned_subjects']}/{counts['subjects']})

- ✓ Canonical 24-record union and 19 claim subjects bound
- ✓ Batch 001 terminally dispositioned
- ✓ Batch 002 terminally dispositioned
- ✓ Corrected Batch-002 candidate created and returned to Ingolf Lohmann
- ✓ Owner decision `ACCEPT` recorded
- ✓ Authority PR #209 and Mirror PR #100 promoted
- ✓ Reciprocal receipt Authority PR #213 / Mirror PR #101 promoted
- □ Seven remaining claim subjects
- □ Retrospective proof corpus and any later publication effect

## Bounded global claim scope

`qikvrt-global-claim-scope-v1`: **`FINAL_PASS`**, 100% inside its declared
finite boundary ({global_counts['claims']} claims,
{global_counts['primary_kernel_receipts']} primary kernel receipts,
{global_counts['open_claims']} claims retained `OPEN`). This bounded historical
scope does not establish completion of the Zenodo corpus or any unregistered
statement.

## Zenodo canonical-union corpus

`qikvrt-zenodo-canonical-union-2026-07-28-v1`: **`CONTINUE`**,
{counts['dispositioned_subjects']}/{counts['subjects']} subjects dispositioned
({corpus['percent']}%), {counts['open_subjects']} open.

- Batch 002: `{batch['state']}`, {batch['subjects']} subjects,
  {batch['claims']} claims, one accepted versioned correction.
- Owner return and content-correction review: complete.
- Authority promotion: PR #209, merge `524fabd51f3492aa99da1430557f4f515074450e`.
- Mirror promotion: PR #100, merge `a8b85fbf3222da1e528505a760c184d48e112329`.
- Reciprocal receipt: PR #213 / PR #101,
  SHA-256 `{equality['sha256']}`.
- Batch 003: `{active['state']}` with {active['subjects']} subjects;
  {corpus['queued_after_active']} further subject remains beyond the active batch.
- Corpus `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, Zenodo mutation and
  proof-corpus publication: **not established**.

## Repository evidence boundary

The historical terminal queue, index and union receipt remain immutable. The
post-acceptance overlay binds the Owner `ACCEPT` receipt, both promotions and
the independently gated reciprocal equality receipt. It advances only the
content-disposition next action; it does not rewrite the earlier event records.

## BLOCKER

No internal Batch-002 correction or owner-return blocker remains. Seven claim
subjects and the retrospective proof corpus remain incomplete.

## NEXT

`{progress['next_action']}`
"""


def expected_projection() -> tuple[dict[str, Any], str]:
    queue = read_json(QUEUE)
    index = read_json(INDEX)
    union = read_json(UNION_RECEIPT)
    owner = read_json(OWNER_ACCEPTANCE)
    equality = read_json(EQUALITY_RECEIPT)
    post = read_json(POST)

    open_ids = validate_historical_files(queue, index, union)
    validate_owner_acceptance(owner)
    validate_equality_receipt(equality)
    validate_post_projection(post, open_ids)
    _, _, _, _, historical_progress = historical_projection()
    progress = build_progress(historical_progress, post)
    validate_progress(progress, post)
    return progress, render_ai_status(progress)


def verify() -> dict[str, Any]:
    progress, status = expected_projection()
    if AI_PROGRESS.read_text(encoding="utf-8") != pretty(progress):
        fail("AI_PROGRESS.json is not byte-current")
    if AI_STATUS.read_text(encoding="utf-8") != status:
        fail("AI_STATUS.md is not byte-current")
    return {
        "schema": "qikvrt_post_acceptance_status_projection_verification_v1",
        "state": "BATCH_002_ACCEPTANCE_STATUS_PROJECTION_CURRENT",
        "next_deterministic_effect": NEXT_EFFECT,
        "batch_002_correction_and_owner_return_complete": True,
        "open_subject_count": 7,
        "active_batch": "CONTENT-DISPOSITION-BATCH-003",
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def materialize() -> None:
    progress, status = expected_projection()
    AI_PROGRESS.write_text(pretty(progress), encoding="utf-8", newline="\n")
    AI_STATUS.write_text(status, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--check-status-projection", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.materialize:
            materialize()
        result = verify()
    except (E, OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {
            "state": "BLOCK",
            "failure_class": (
                "POST_ACCEPTANCE_CONTENT_DISPOSITION_STATUS_PROJECTION_INVALID"
            ),
            "reason": str(exc),
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2
    if args.json or args.check_status_projection:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(result["state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
