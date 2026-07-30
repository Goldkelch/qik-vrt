#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Append-tolerant compatibility front-end for the Batch-003 dispatcher.

The immutable dispatch inputs remain exact-blob-bound. The live reciprocal
receipt index is an append-only registry owned by the equality-receipt
subsystem and must therefore be validated semantically rather than frozen to
the blob that existed at dispatch time. Once the first subject disposition is
materialized, this compatibility layer preserves and validates the historical
dispatch while delegating the root status projection to the more advanced
subject projector. It never mutates the imported legacy module namespace.
"""

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

ADVANCED_SUBJECT_RECEIPT = (
    ROOT
    / "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/subject-dispositions/"
    "SUBJECT-2581811b342e505d/SUBJECT_DISPOSITION_RECEIPT.json"
)


def validate_live_index(index: Mapping[str, Any] | None = None) -> None:
    """Require a valid append-only live index without freezing its current blob."""
    if not LIVE_INDEX.is_file():
        fail(f"dispatch source missing: {LIVE_INDEX.relative_to(ROOT)}")
    value = read_json(LIVE_INDEX) if index is None else index
    if value.get("schema") != "qikvrt_equality_receipt_index_v1":
        fail("live receipt index schema drift")
    integration = value.get("manifest_integration", {})
    if integration.get("direct_generated_manifest_mutation") is not False:
        fail("live receipt index manifest boundary drift")
    rows = value.get("equality_receipts")
    if not isinstance(rows, list):
        fail("live receipt index rows are absent")

    receipt_ids: list[str] = []
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
        receipt_ids.append(receipt_id)
        paths.append(path)

    if len(receipt_ids) != len(set(receipt_ids)):
        fail("live receipt index contains duplicate receipt identities")
    if len(paths) != len(set(paths)):
        fail("live receipt index contains duplicate receipt paths")
    missing = sorted(_REQUIRED_PRE_DISPATCH_RECEIPT_IDS.difference(receipt_ids))
    if missing:
        fail("live receipt index lost required pre-dispatch receipts: " + ",".join(missing))
    if sha256_bytes(LIVE_INDEX.read_bytes()) == PUBLIC_INDEX["sha256"]:
        fail("live receipt index unexpectedly collapsed into historical public freeze")


def validate_source_blobs() -> None:
    for path, expected in EXPECTED_SOURCE_BLOBS.items():
        if not path.is_file():
            fail(f"dispatch source missing: {path.relative_to(ROOT)}")
        actual = git_blob_sha1(path.read_bytes())
        if actual != expected:
            fail(f"dispatch source blob drift: {path.relative_to(ROOT)}")
    validate_live_index()


def base_expected_projection() -> tuple[dict[str, Any], str]:
    """Build the immutable dispatch projection without touching root status files."""
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


def _advanced_module() -> Any:
    from tools import (  # type: ignore
        qikvrt_content_disposition_batch_003_subject_2581811b342e505d as advanced,
    )

    return advanced


def expected_projection() -> tuple[dict[str, Any], str]:
    if ADVANCED_SUBJECT_RECEIPT.is_file():
        return _advanced_module().build_progress_projection()
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
    if not ADVANCED_SUBJECT_RECEIPT.is_file():
        return _verify_base_root()

    base_expected_projection()
    advanced = _advanced_module()
    advanced_result = advanced.verify_materialized()
    return {
        "schema": "qikvrt_batch_003_dispatch_verification_v1",
        "state": "BATCH_003_DISPATCH_PRESERVED_ADVANCED_PROJECTION_CURRENT",
        "batch_id": BATCH_ID,
        "active_subject": advanced.NEXT_SUBJECT_ID,
        "active_subject_count": 5,
        "open_subject_count": 6,
        "next_deterministic_effect": advanced.NEXT_EFFECT,
        "claim_extraction_complete": True,
        "advanced_subject_state": advanced_result["state"],
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def materialize() -> None:
    if ADVANCED_SUBJECT_RECEIPT.is_file():
        _advanced_module().verify_materialized()
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
        payload = {
            "state": "BLOCK",
            "failure_class": "BATCH_003_DISPATCH_STATUS_PROJECTION_INVALID",
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
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
