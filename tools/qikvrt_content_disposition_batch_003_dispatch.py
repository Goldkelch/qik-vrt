#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Append-tolerant current-state front-end for the Batch-003 dispatcher.

The immutable dispatch inputs remain exact-blob-bound. The live reciprocal
receipt index is an append-only registry and is validated semantically. Once a
subject-disposition receipt is present, status materialization delegates to the
subject-specific fail-closed projector without rewriting the historical
dispatch layer.
"""

from __future__ import annotations

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

SUBJECT_DISPOSITION_REL = (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/subjects/SUBJECT-2581811b342e505d/"
    "SUBJECT_DISPOSITION_RECEIPT.json"
)
SUBJECT_DISPOSITION = ROOT / SUBJECT_DISPOSITION_REL
SECOND_SUBJECT_ID = "SUBJECT-172dd9bc2738fa43"
NEXT_EFFECT = (
    "EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_"
    "BATCH_003_SUBJECT_172DD9BC2738FA43"
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


# The delegated historical projection resolves this name in the legacy module.
_legacy.EXPECTED_SOURCE_BLOBS = EXPECTED_SOURCE_BLOBS
_legacy.validate_source_blobs = validate_source_blobs


def _active_module():
    if SUBJECT_DISPOSITION.is_file():
        from tools import (
            qikvrt_content_disposition_batch_003_subject_2581811b342e505d
            as subject,
        )

        return subject
    return _legacy


def expected_projection():
    return _active_module().expected_projection()


def verify():
    return _active_module().verify()


def materialize() -> None:
    _active_module().materialize()


def validate_progress(progress: Mapping[str, Any]) -> None:
    _active_module().validate_progress(progress)


def render_ai_status(progress: Mapping[str, Any]) -> str:
    return _active_module().render_ai_status(progress)


def main(argv: list[str] | None = None) -> int:
    return _active_module().main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
