#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Render a backward-compatible post-acceptance Batch-002 root projection."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_content_disposition_status_after_batch_002_acceptance as base

E = base.E
fail = base.fail
read_json = base.read_json
pretty = base.pretty
validate_historical_files = base.validate_historical_files
validate_owner_acceptance = base.validate_owner_acceptance
validate_equality_receipt = base.validate_equality_receipt
validate_post_projection = base.validate_post_projection
historical_projection = base.historical_projection

POST = base.POST
OWNER_ACCEPTANCE = base.OWNER_ACCEPTANCE
EQUALITY_RECEIPT = base.EQUALITY_RECEIPT
AI_PROGRESS = base.AI_PROGRESS
AI_STATUS = base.AI_STATUS
QUEUE = base.QUEUE
INDEX = base.INDEX
UNION_RECEIPT = base.UNION_RECEIPT
OPEN_SUBJECT_IDS = base.OPEN_SUBJECT_IDS
OWNER_BLOB = base.OWNER_BLOB
OWNER_SHA256 = base.OWNER_SHA256
EQUALITY_BLOB = base.EQUALITY_BLOB
EQUALITY_SHA256 = base.EQUALITY_SHA256
NEXT_EFFECT = base.NEXT_EFFECT
UPDATED_AT = base.UPDATED_AT
POST_REL = base.POST_REL
OWNER_REL = base.OWNER_REL
EQUALITY_REL = base.EQUALITY_REL

TOOL_REL = (
    "tools/"
    "qikvrt_content_disposition_status_after_batch_002_acceptance_compat.py"
)
CHECK_COMMAND = f"python3 -B {TOOL_REL} --check-status-projection"
TERMINAL_RECEIPT_REL = (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-002/terminal-disposition/"
    "CONTENT_DISPOSITION_BATCH_002_RECEIPT.json"
)
TERMINAL_RECEIPT_SHA256 = (
    "e656e54e5d15733a3930a280e5933f36c6c91e5b1827534d662983cb640bcadc"
)
POST_ACCEPTANCE_STATE = (
    "CORRECTION_ACCEPTED_PROMOTED_AND_RECIPROCALLY_BOUND"
)


def build_progress(
    historical_progress: Mapping[str, Any],
    post: Mapping[str, Any],
) -> dict[str, Any]:
    progress = base.build_progress(historical_progress, post)
    corpus = progress["scopes"][
        "qikvrt-zenodo-canonical-union-2026-07-28-v1"
    ]
    batch = corpus["batch_002"]
    generated_evidence = copy.deepcopy(batch["evidence"])

    batch["state"] = "TERMINALLY_DISPOSITIONED"
    batch["evidence"] = {
        "path": TERMINAL_RECEIPT_REL,
        "sha256": TERMINAL_RECEIPT_SHA256,
    }
    batch["post_acceptance"] = {
        "state": POST_ACCEPTANCE_STATE,
        "corrected_candidate_count": 1,
        "corrected_candidate_required_count": 1,
        "owner_return_complete": True,
        "owner_acceptance_recorded": True,
        "content_correction_review_complete": True,
        "authority_promotion_complete": True,
        "mirror_promotion_complete": True,
        "reciprocal_equality_receipt_complete": True,
        "evidence": generated_evidence,
    }
    progress["projection_owner"] = {
        "tool": TOOL_REL,
        "check_command": CHECK_COMMAND,
    }
    return progress


def validate_progress(
    progress: Mapping[str, Any],
    post: Mapping[str, Any],
) -> None:
    corpus = progress.get("scopes", {}).get(
        "qikvrt-zenodo-canonical-union-2026-07-28-v1", {}
    )
    batch = corpus.get("batch_002", {})
    later = batch.get("post_acceptance", {})
    evidence = later.get("evidence", {})
    effects = progress.get("repository_effects", {})
    if (
        progress.get("schema") != "qikvrt-ai-progress/3.1"
        or progress.get("state") != "IDLE"
        or progress.get("effect_state") != "EFFECT_ACK_CONTINUE"
        or progress.get("percent") != 63
        or progress.get("next_action") != NEXT_EFFECT
        or progress.get("updated_at") != UPDATED_AT
        or progress.get("projection_owner")
        != {"tool": TOOL_REL, "check_command": CHECK_COMMAND}
        or progress.get("union_receipt_state")
        != post.get("projection", {}).get("union_receipt_state")
        or corpus.get("counts", {}).get("subjects") != 19
        or corpus.get("counts", {}).get("dispositioned_subjects") != 12
        or corpus.get("counts", {}).get("open_subjects") != 7
        or corpus.get("next_action") != NEXT_EFFECT
        or corpus.get("active_batch", {}).get("batch_id")
        != "CONTENT-DISPOSITION-BATCH-003"
        or corpus.get("active_batch", {}).get("state") != "READY"
        or corpus.get("active_batch", {}).get("subjects") != 6
        or corpus.get("queued_after_active") != 1
        or batch.get("state") != "TERMINALLY_DISPOSITIONED"
        or batch.get("evidence")
        != {"path": TERMINAL_RECEIPT_REL, "sha256": TERMINAL_RECEIPT_SHA256}
        or later.get("state") != POST_ACCEPTANCE_STATE
        or later.get("owner_return_complete") is not True
        or later.get("owner_acceptance_recorded") is not True
        or later.get("content_correction_review_complete") is not True
        or later.get("authority_promotion_complete") is not True
        or later.get("mirror_promotion_complete") is not True
        or later.get("reciprocal_equality_receipt_complete") is not True
        or evidence.get("post_acceptance_projection") != POST_REL
        or evidence.get("owner_acceptance", {}).get("git_blob_sha1")
        != OWNER_BLOB
        or evidence.get("reciprocal_equality", {}).get("git_blob_sha1")
        != EQUALITY_BLOB
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
        fail("backward-compatible AI_PROGRESS projection drift")

    for mapping, label in (
        (progress.get("claims", {}), "top-level"),
        (corpus.get("claims", {}), "corpus"),
    ):
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            if mapping.get(key) is not False:
                fail(f"{label} release inflation: {key}")


def render_ai_status(progress: Mapping[str, Any]) -> str:
    corpus = progress["scopes"][
        "qikvrt-zenodo-canonical-union-2026-07-28-v1"
    ]
    global_scope = progress["scopes"]["qikvrt-global-claim-scope-v1"]
    counts = corpus["counts"]
    batch = corpus["batch_002"]
    later = batch["post_acceptance"]
    active = corpus["active_batch"]
    global_counts = global_scope["counts"]
    bar = "█" * counts["dispositioned_subjects"] + "░" * counts["open_subjects"]
    equality = later["evidence"]["reciprocal_equality"]
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

- Batch 002 claim disposition: `{batch['state']}`, {batch['subjects']} subjects,
  {batch['claims']} claims.
- Batch 002 correction chain: `{later['state']}`.
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
