#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Append-tolerant compatibility front-end for the Batch-003 dispatcher.

The immutable dispatch inputs remain exact-blob-bound.  The live reciprocal
receipt index is an append-only registry owned by the equality-receipt
subsystem and must therefore be validated semantically rather than frozen to
the blob that existed at dispatch time.
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


# The delegated projection and CLI resolve this name in the legacy module.
_legacy.EXPECTED_SOURCE_BLOBS = EXPECTED_SOURCE_BLOBS
_legacy.validate_source_blobs = validate_source_blobs


if __name__ == "__main__":
    raise SystemExit(_legacy.main())
