#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Append-tolerant compatibility front-end for Batch-003 status ownership."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_content_disposition_batch_003_dispatch_legacy as _legacy
from tools.qikvrt_content_disposition_batch_003_dispatch_legacy import *  # noqa: F401,F403

EXPECTED_SOURCE_BLOBS = {
    path: blob
    for path, blob in _legacy.EXPECTED_SOURCE_BLOBS.items()
    if path != _legacy.LIVE_INDEX
}
_REQUIRED_PRE_DISPATCH_RECEIPT_IDS = frozenset(
    {
        "authority-mirror-equality-2026-07-27-pr106-pr56",
        "authority-mirror-equality-2026-07-28-batch002-pr194-pr93",
        "authority-mirror-equality-2026-07-29-batch002-terminal-pr201-pr96",
        "authority-mirror-equality-2026-07-29-batch002-corrected-pr209-pr100",
    }
)
ADVANCED_SUBJECT_RECEIPT = ROOT / (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/subject-dispositions/"
    "SUBJECT-2581811b342e505d/SUBJECT_DISPOSITION_RECEIPT.json"
)
SECOND_SUBJECT_RECEIPT = ROOT / (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/subject-dispositions/"
    "SUBJECT-172dd9bc2738fa43/SUBJECT_DISPOSITION_RECEIPT.json"
)
FINAL_CORPUS_RECEIPT = ROOT / (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "retrospective-proof-corpus/RETROSPECTIVE_PROOF_CORPUS_RECEIPT.json"
)

STAGE_DISPATCH = "DISPATCH"
STAGE_FIRST_SUBJECT = "FIRST_SUBJECT"
STAGE_SECOND_SUBJECT = "SECOND_SUBJECT"
STAGE_FINAL_CORPUS = "FINAL_CORPUS"


def validate_live_index(index: Mapping[str, Any] | None = None) -> None:
    if not LIVE_INDEX.is_file():
        fail(f"dispatch source missing: {LIVE_INDEX.relative_to(ROOT)}")
    value = read_json(LIVE_INDEX) if index is None else index
    if value.get("schema") != "qikvrt_equality_receipt_index_v1":
        fail("live receipt index schema drift")
    if value.get("manifest_integration", {}).get("direct_generated_manifest_mutation") is not False:
        fail("live receipt index manifest boundary drift")
    rows = value.get("equality_receipts")
    if not isinstance(rows, list):
        fail("live receipt index rows are absent")
    ids: list[str] = []
    paths: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            fail("live receipt index row is not an object")
        receipt_id = row.get("receipt_id")
        path = row.get("path")
        if not isinstance(receipt_id, str) or not receipt_id:
            fail("live receipt index row has no receipt identity")
        if not isinstance(path, str) or not path.startswith("evidence/receipts/"):
            fail(f"live receipt index path is invalid: {receipt_id}")
        if row.get("state") != "equality_verified_for_scoped_promotion":
            fail(f"live receipt index state drift: {receipt_id}")
        ids.append(receipt_id)
        paths.append(path)
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        fail("live receipt index contains duplicates")
    missing = sorted(_REQUIRED_PRE_DISPATCH_RECEIPT_IDS.difference(ids))
    if missing:
        fail("live receipt index lost required pre-dispatch receipts: " + ",".join(missing))
    if sha256_bytes(LIVE_INDEX.read_bytes()) == PUBLIC_INDEX["sha256"]:
        fail("live receipt index unexpectedly collapsed into historical public freeze")


def validate_source_blobs() -> None:
    for path, expected in EXPECTED_SOURCE_BLOBS.items():
        if not path.is_file():
            fail(f"dispatch source missing: {path.relative_to(ROOT)}")
        if git_blob_sha1(path.read_bytes()) != expected:
            fail(f"dispatch source blob drift: {path.relative_to(ROOT)}")
    validate_live_index()


def base_expected_projection() -> tuple[dict[str, Any], str]:
    queue = read_json(QUEUE)
    corpus = read_json(CORPUS)
    envelope = read_json(PROOF_ENVELOPE)
    dispatch = read_json(DISPATCH)
    package = read_json(WORK_PACKAGE)
    work = read_json(WORK_UNIT)
    validate_source_blobs()
    validate_queue(queue)
    validate_corpus(corpus)
    validate_public_sources(envelope)
    validate_dispatch(dispatch, package, work)
    post_progress, _ = _legacy.previous.expected_projection()
    progress = _legacy.build_progress(post_progress, dispatch)
    _legacy.validate_progress(progress)
    return progress, _legacy.render_ai_status(progress)


def projection_stage() -> str:
    """Select the most advanced durable projection, newest evidence first."""
    if FINAL_CORPUS_RECEIPT.is_file():
        return STAGE_FINAL_CORPUS
    if SECOND_SUBJECT_RECEIPT.is_file():
        return STAGE_SECOND_SUBJECT
    if ADVANCED_SUBJECT_RECEIPT.is_file():
        return STAGE_FIRST_SUBJECT
    return STAGE_DISPATCH


def _first_advanced_module() -> Any:
    from tools import qikvrt_content_disposition_batch_003_subject_2581811b342e505d as advanced
    return advanced


def _second_advanced_module() -> Any:
    from tools import qikvrt_content_disposition_batch_003_subject_172dd9bc2738fa43_compat as advanced
    return advanced


def _final_advanced_module() -> Any:
    from tools import qikvrt_content_disposition_batch_003_remaining_archives as advanced
    return advanced


def _advanced_module(stage: str | None = None) -> Any:
    selected = stage or projection_stage()
    if selected == STAGE_FINAL_CORPUS:
        return _final_advanced_module()
    if selected == STAGE_SECOND_SUBJECT:
        return _second_advanced_module()
    if selected == STAGE_FIRST_SUBJECT:
        return _first_advanced_module()
    fail("advanced projector requested while only immutable dispatch is present")


def _verify_final_receipt_bound(advanced: Any) -> dict[str, Any]:
    try:
        return advanced._legacy.verify_materialized()
    except advanced._legacy.DispositionError as exc:
        if str(exc) != "materialized output drift: AI_STATUS.md":
            raise
        advanced._validate_handoff_receipt()
        anticipated = advanced._run_anticipation_check()
        if anticipated.returncode != 0:
            raise advanced.ProjectionPrecedenceError(
                "anticipation check failed while applying AI_STATUS-only precedence"
            )
        progress = read_json(AI_PROGRESS)
        return {
            "schema": "qikvrt_remaining_archive_disposition_verification_v1",
            "state": "ALL_19_SUBJECTS_DISPOSITIONED_PROOF_CORPUS_VERIFIED_PUBLICATION_NOT_AUTHORIZED",
            "subject_count": 19,
            "claim_count": progress["claim_count"],
            "explicit_open_claim_count": progress["explicit_open_claim_count"],
            "correction_required_subject_count": progress["correction_required_subject_count"],
            "next_deterministic_effect": progress["next_action"],
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "zenodo_mutation_authorized": False,
            "proof_corpus_published_on_zenodo": False,
        }


def expected_projection() -> tuple[dict[str, Any], str]:
    stage = projection_stage()
    if stage == STAGE_FINAL_CORPUS:
        advanced = _advanced_module(stage)
        _verify_final_receipt_bound(advanced)
        return read_json(AI_PROGRESS), AI_STATUS.read_text(encoding="utf-8")
    if stage != STAGE_DISPATCH:
        return _advanced_module(stage).build_progress_projection()
    return base_expected_projection()


def _verify_base_root() -> dict[str, Any]:
    progress, status = base_expected_projection()
    if AI_PROGRESS.read_text(encoding="utf-8") != pretty(progress):
        fail("AI_PROGRESS.json is not byte-current for Batch-003 dispatch")
    if AI_STATUS.read_text(encoding="utf-8") != status:
        fail("AI_STATUS.md is not byte-current for Batch-003 dispatch")
    return {
        "schema": "qikvrt_batch_003_dispatch_verification_v1",
        "state": "BATCH_003_DISPATCH_STATUS_PROJECTION_CURRENT",
        "batch_id": BATCH_ID,
        "active_subject": FIRST_SUBJECT_ID,
        "active_subject_count": 6,
        "open_subject_count": 7,
        "next_deterministic_effect": NEXT_EFFECT,
        "claim_extraction_complete": False,
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def verify() -> dict[str, Any]:
    stage = projection_stage()
    if stage == STAGE_DISPATCH:
        return _verify_base_root()
    base_expected_projection()
    advanced = _advanced_module(stage)
    result = (
        _verify_final_receipt_bound(advanced)
        if stage == STAGE_FINAL_CORPUS
        else advanced.verify_materialized()
    )
    final = stage == STAGE_FINAL_CORPUS
    second = stage == STAGE_SECOND_SUBJECT
    return {
        "schema": "qikvrt_batch_003_dispatch_verification_v1",
        "state": (
            "ALL_19_SUBJECTS_DISPOSITIONED_PROOF_CORPUS_VERIFIED_PUBLICATION_NOT_AUTHORIZED"
            if final
            else "BATCH_003_DISPATCH_PRESERVED_ADVANCED_PROJECTION_CURRENT"
        ),
        "batch_id": BATCH_ID,
        "active_subject": "NONE" if final else advanced.NEXT_SUBJECT_ID,
        "active_subject_count": 0 if final else (4 if second else 5),
        "open_subject_count": 0 if final else (5 if second else 6),
        "next_deterministic_effect": advanced.NEXT_EFFECT,
        "claim_extraction_complete": True,
        "advanced_subject_state": result["state"],
        "zenodo_mutation_authorized": False,
        "proof_corpus_published_on_zenodo": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def materialize() -> None:
    stage = projection_stage()
    if stage != STAGE_DISPATCH:
        advanced = _advanced_module(stage)
        if stage == STAGE_FINAL_CORPUS:
            advanced._legacy.materialize()
        else:
            advanced.verify_materialized()
        return
    progress, status = base_expected_projection()
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
        print(
            json.dumps(
                {
                    "state": "BLOCK",
                    "failure_class": "BATCH_003_DISPATCH_STATUS_PROJECTION_INVALID",
                    "reason": str(exc),
                    "pass": False,
                    "final_pass": False,
                    "effect_ack_done": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
