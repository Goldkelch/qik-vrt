#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Validate and project the fail-closed Batch-003 dispatch state."""

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

from tools import qikvrt_content_disposition_status_after_batch_002_acceptance_compat as previous

E = previous.E
fail = previous.fail
read_json = previous.read_json
pretty = previous.pretty

AI_PROGRESS = previous.AI_PROGRESS
AI_STATUS = previous.AI_STATUS
QUEUE = previous.QUEUE
INDEX = previous.INDEX
UNION_RECEIPT = previous.UNION_RECEIPT
POST = previous.POST
OWNER_ACCEPTANCE = previous.OWNER_ACCEPTANCE
EQUALITY_RECEIPT = previous.EQUALITY_RECEIPT
OPEN_SUBJECT_IDS = previous.OPEN_SUBJECT_IDS
TERMINAL_RECEIPT_REL = previous.TERMINAL_RECEIPT_REL
TERMINAL_RECEIPT_SHA256 = previous.TERMINAL_RECEIPT_SHA256
POST_ACCEPTANCE_STATE = previous.POST_ACCEPTANCE_STATE
validate_historical_files = previous.validate_historical_files
validate_owner_acceptance = previous.validate_owner_acceptance
validate_equality_receipt = previous.validate_equality_receipt
validate_post_projection = previous.validate_post_projection
historical_projection = previous.historical_projection

BATCH_ID = "CONTENT-DISPOSITION-BATCH-003"
FIRST_SUBJECT_ID = "SUBJECT-2581811b342e505d"
AUTHORITY_BASE = "191bee0e50cc0cbb1f71423289224c1de8cba7f2"
STATUS_EXACT_HEAD = "bc61da06a932c8884e296e247aa428d6451e7e0f"
OBSERVED_AT = "2026-07-29T23:05:40Z"
NEXT_EFFECT = (
    "RECOVER_EXACT_PUBLIC_INDEX_BYTES_AND_EXTRACT_CLASSIFY_"
    "BATCH_003_SUBJECT_2581811B342E505D"
)

DISPATCH_REL = (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/dispatch/BATCH_003_DISPATCH_RECEIPT.json"
)
WORK_PACKAGE_REL = (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/dispatch/subjects/"
    "SUBJECT-2581811b342e505d/CLAIM_EXTRACTION_WORK_PACKAGE.json"
)
WORK_UNIT_REL = "work-units/ADVANCE_CANONICAL_STATUS_AND_DISPATCH_BATCH_003.json"
PROOF_ENVELOPE_REL = (
    "release/zenodo-corpus-proof-2026-07-28/proof-envelopes/"
    "zenodo-21633411.json"
)
CORPUS_REL = (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "CANONICAL_UNION_CORPUS.json"
)
HISTORICAL_RECEIPT_REL = (
    "evidence/receipts/authority-mirror-equality-2026-07-27-pr106-pr56.json"
)
LIVE_INDEX_REL = "evidence/receipts/index.json"

DISPATCH = ROOT / DISPATCH_REL
WORK_PACKAGE = ROOT / WORK_PACKAGE_REL
WORK_UNIT = ROOT / WORK_UNIT_REL
PROOF_ENVELOPE = ROOT / PROOF_ENVELOPE_REL
CORPUS = ROOT / CORPUS_REL
HISTORICAL_RECEIPT = ROOT / HISTORICAL_RECEIPT_REL
LIVE_INDEX = ROOT / LIVE_INDEX_REL

TOOL_REL = "tools/qikvrt_content_disposition_batch_003_dispatch.py"
CHECK_COMMAND = f"python3 -B {TOOL_REL} --check-status-projection"

EXPECTED_SOURCE_BLOBS = {
    QUEUE: "3e5fd48c314fe02574ee67f1b22cbb4ba04003d7",
    CORPUS: "bcfe6bdfb7aa2a9add8b55651d28235a3da341f6",
    POST: "106dcab562f8c0d9d0295b103b40275b34fcbb1b",
    PROOF_ENVELOPE: "2ccc06b2205106eb1cd65b96161321c4df3bbc5c",
    HISTORICAL_RECEIPT: "83c80c53d330eb929defb3739ecc9184e6754639",
}

ACTIVE_SUBJECT_IDS = (
    "SUBJECT-2581811b342e505d",
    "SUBJECT-172dd9bc2738fa43",
    "SUBJECT-b4849e1a2d6b2270",
    "SUBJECT-7956d8acdc473825",
    "SUBJECT-ce2390f18618ad0c",
    "SUBJECT-780b9bf86425cee3",
)
OUTSIDE_SUBJECT_IDS = ("SUBJECT-7fdb36aa7c07c07d",)

PUBLIC_RECEIPT = {
    "name": "authority-mirror-equality-2026-07-27-pr106-pr56.json",
    "bytes": 5189,
    "md5": "8792385e000502fae63fa1b4e48e4723",
    "sha256": "2372fae39499febbb005d771cb2ce62bde7967a79cdd5e3b159a3591fc80ac98",
}
PUBLIC_INDEX = {
    "name": "equality-receipts-index.json",
    "bytes": 1487,
    "md5": "aa033aeacb744efd8cb89ac8fcd66733",
    "sha256": "47c5d7107098c0527c80aa0d65deeeb6a15ce1496588fda3fda087d4d18d5ff4",
}

LIVE_INDEX_BASE_ENTRY_COUNT = 4
LIVE_INDEX_BASE_PREFIX_SHA256 = (
    "724a6c7c20f5c5e404fac69a7fabfef8f299e92e8a43a192ecaf1f9477c0467b"
)
LIVE_INDEX_BASE_UPDATED_AT = "2026-07-29T22:08:06Z"
LIVE_INDEX_LICENSE = {
    "classification": "machine_readable_equality_evidence_index",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}
LIVE_INDEX_MANIFEST_INTEGRATION = {
    "direct_generated_manifest_mutation": False,
    "method": (
        "The deterministic integrity generator includes this index and every "
        "referenced receipt as immutable files in REPOSITORY_FILE_MANIFEST.json."
    ),
}
LIVE_INDEX_KEYS = {
    "_license",
    "equality_receipts",
    "manifest_integration",
    "schema",
    "updated_at",
}
LIVE_INDEX_ENTRY_KEYS = {
    "authority",
    "file_sha256",
    "git_blob_sha1",
    "mirror",
    "path",
    "receipt_id",
    "scope",
    "source_receipt_payload_sha256",
    "state",
}
LIVE_INDEX_SIDE_KEYS = {"main", "pull_request", "repository"}


def git_blob_sha1(data: bytes) -> str:
    framed = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(framed).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def is_hex(value: Any, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_live_index(index: Mapping[str, Any] | None = None) -> None:
    if index is None:
        index = read_json(LIVE_INDEX)
    if set(index) != LIVE_INDEX_KEYS:
        fail("live equality-receipt index key set drift")
    if index.get("_license") != LIVE_INDEX_LICENSE:
        fail("live equality-receipt index license drift")
    if index.get("schema") != "qikvrt_equality_receipt_index_v1":
        fail("live equality-receipt index schema drift")
    if index.get("manifest_integration") != LIVE_INDEX_MANIFEST_INTEGRATION:
        fail("live equality-receipt index manifest-integration drift")

    updated_at = index.get("updated_at")
    if (
        not isinstance(updated_at, str)
        or not updated_at.endswith("Z")
        or updated_at < LIVE_INDEX_BASE_UPDATED_AT
    ):
        fail("live equality-receipt index timestamp drift")

    rows = index.get("equality_receipts")
    if not isinstance(rows, list) or len(rows) < LIVE_INDEX_BASE_ENTRY_COUNT:
        fail("live equality-receipt index history was truncated")
    if (
        sha256_bytes(
            canonical_json_bytes(rows[:LIVE_INDEX_BASE_ENTRY_COUNT])
        )
        != LIVE_INDEX_BASE_PREFIX_SHA256
    ):
        fail("live equality-receipt index historical prefix drift")
    if len(rows) == LIVE_INDEX_BASE_ENTRY_COUNT:
        if updated_at != LIVE_INDEX_BASE_UPDATED_AT:
            fail("unchanged live equality-receipt index timestamp drift")
    elif updated_at <= LIVE_INDEX_BASE_UPDATED_AT:
        fail("appended live equality-receipt index lacks a later timestamp")

    receipt_ids: set[str] = set()
    paths: set[str] = set()
    for offset, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != LIVE_INDEX_ENTRY_KEYS:
            fail(f"live equality-receipt index entry key drift: {offset}")
        authority = row.get("authority")
        mirror = row.get("mirror")
        if (
            not isinstance(authority, Mapping)
            or set(authority) != LIVE_INDEX_SIDE_KEYS
            or not isinstance(mirror, Mapping)
            or set(mirror) != LIVE_INDEX_SIDE_KEYS
        ):
            fail(f"live equality-receipt index side binding drift: {offset}")
        if (
            authority.get("repository") != "Goldkelch/qik-vrt"
            or mirror.get("repository") != "ingolf-lohmann/qik-vrt"
            or not is_hex(authority.get("main"), 40)
            or not is_hex(mirror.get("main"), 40)
            or isinstance(authority.get("pull_request"), bool)
            or not isinstance(authority.get("pull_request"), int)
            or authority.get("pull_request", 0) <= 0
            or isinstance(mirror.get("pull_request"), bool)
            or not isinstance(mirror.get("pull_request"), int)
            or mirror.get("pull_request", 0) <= 0
        ):
            fail(f"live equality-receipt index repository binding drift: {offset}")

        receipt_id = row.get("receipt_id")
        scope = row.get("scope")
        relative = row.get("path")
        if (
            not isinstance(receipt_id, str)
            or not receipt_id
            or not isinstance(scope, str)
            or not scope
            or not isinstance(relative, str)
            or not relative
            or row.get("state") != "equality_verified_for_scoped_promotion"
            or not is_hex(row.get("file_sha256"), 64)
            or not is_hex(row.get("git_blob_sha1"), 40)
            or not is_hex(row.get("source_receipt_payload_sha256"), 64)
        ):
            fail(f"live equality-receipt index identity drift: {offset}")
        if receipt_id in receipt_ids or relative in paths:
            fail(f"live equality-receipt index duplicate entry: {offset}")
        receipt_ids.add(receipt_id)
        paths.add(relative)

        pure = pathlib.PurePosixPath(relative)
        if (
            pure.is_absolute()
            or any(part in {"", ".", ".."} for part in pure.parts)
            or pure.parts[:2] != ("evidence", "receipts")
            or pure.name == "index.json"
            or pure.suffix != ".json"
        ):
            fail(f"unsafe live equality-receipt index path: {offset}")
        receipt_path = ROOT.joinpath(*pure.parts)
        if not receipt_path.is_file() or receipt_path.is_symlink():
            fail(f"live equality-receipt index target missing: {relative}")
        raw = receipt_path.read_bytes()
        if (
            sha256_bytes(raw) != row.get("file_sha256")
            or git_blob_sha1(raw) != row.get("git_blob_sha1")
        ):
            fail(f"live equality-receipt index target identity drift: {relative}")


def validate_source_blobs() -> None:
    for path, expected in EXPECTED_SOURCE_BLOBS.items():
        if not path.is_file():
            fail(f"dispatch source missing: {path.relative_to(ROOT)}")
        actual = git_blob_sha1(path.read_bytes())
        if actual != expected:
            fail(f"dispatch source blob drift: {path.relative_to(ROOT)}")
    validate_live_index()


def validate_queue(queue: Mapping[str, Any]) -> None:
    active = queue.get("active_batch", {})
    rows = active.get("subjects", [])
    ids = tuple(row.get("subject_id") for row in rows if isinstance(row, dict))
    if (
        active.get("batch_id") != BATCH_ID
        or active.get("state") != "READY"
        or active.get("subject_count") != 6
        or ids != ACTIVE_SUBJECT_IDS
    ):
        fail("Batch-003 queue partition drift")
    first = rows[0]
    if (
        first.get("queue_priority") != 2
        or first.get("representative_record_id") != 21633411
        or first.get("required_action") != "EXTRACT_AND_CLASSIFY_CONTENT_CLAIMS"
        or first.get("payload_multiset_sha256")
        != "2581811b342e505d8ac807aa8fa8c33a4afdbf1f2bf663c277010dda28329799"
    ):
        fail("Batch-003 first-subject priority binding drift")
    remaining = tuple(queue.get("remaining_subject_ids", []))
    if remaining != OUTSIDE_SUBJECT_IDS or queue.get("remaining_subject_count") != 1:
        fail("subject beyond Batch 003 drift")


def validate_corpus(corpus: Mapping[str, Any]) -> None:
    clusters = {
        row.get("cluster_id"): row
        for row in corpus.get("payload_clusters", [])
        if isinstance(row, dict)
    }
    row = clusters.get("PAYLOAD-2581811b342e505d", {})
    if (
        corpus.get("payload_cluster_count") != 19
        or row.get("payload_multiset_sha256")
        != "2581811b342e505d8ac807aa8fa8c33a4afdbf1f2bf663c277010dda28329799"
        or row.get("record_ids") != [21633411]
    ):
        fail("canonical-union first-subject binding drift")


def validate_public_sources(envelope: Mapping[str, Any]) -> None:
    record = envelope.get("record", {})
    if (
        record.get("record_id") != 21633411
        or record.get("doi") != "10.5281/zenodo.21633411"
        or record.get("conceptdoi") != "10.5281/zenodo.21633410"
    ):
        fail("public record identity drift")
    files = {
        row.get("name"): row
        for row in envelope.get("public_files", [])
        if isinstance(row, dict)
    }
    for expected in (PUBLIC_RECEIPT, PUBLIC_INDEX):
        row = files.get(expected["name"], {})
        for key in ("bytes", "md5", "sha256"):
            if row.get(key) != expected[key]:
                fail(f"public file binding drift: {expected['name']}:{key}")
        if row.get("public_byte_redownload_verified") is not True:
            fail(f"public redownload is not verified: {expected['name']}")

    receipt = HISTORICAL_RECEIPT.read_bytes()
    if (
        len(receipt) != PUBLIC_RECEIPT["bytes"]
        or md5_bytes(receipt) != PUBLIC_RECEIPT["md5"]
        or sha256_bytes(receipt) != PUBLIC_RECEIPT["sha256"]
    ):
        fail("local historical receipt is not the exact public bytes")

    live_index = LIVE_INDEX.read_bytes()
    if sha256_bytes(live_index) == PUBLIC_INDEX["sha256"]:
        fail("live receipt index unexpectedly collapsed into historical public freeze")


def validate_work_package(package: Mapping[str, Any]) -> None:
    if (
        package.get("schema") != "qikvrt_content_claim_extraction_work_package_v1"
        or package.get("state") != "DISPATCHED_PUBLIC_FREEZE_RECOVERY_REQUIRED"
        or package.get("batch_id") != BATCH_ID
        or package.get("subject_id") != FIRST_SUBJECT_ID
        or package.get("next_deterministic_effect") != NEXT_EFFECT
    ):
        fail("first Batch-003 work-package identity drift")
    files = package.get("public_source_files", [])
    if len(files) != 2:
        fail("first Batch-003 public source set drift")
    by_name = {row.get("name"): row for row in files if isinstance(row, dict)}
    receipt = by_name.get(PUBLIC_RECEIPT["name"], {})
    index = by_name.get(PUBLIC_INDEX["name"], {})
    if (
        receipt.get("state") != "LOCAL_EXACT_PUBLIC_BYTES_AVAILABLE"
        or receipt.get("current_repository_binding", {}).get("repository_byte_match")
        is not True
        or index.get("state") != "PUBLIC_FREEZE_RECOVERY_REQUIRED_BEFORE_EXTRACTION"
        or index.get("current_repository_binding", {}).get(
            "current_repository_byte_match"
        )
        is not False
    ):
        fail("public-freeze recovery boundary drift")
    for row, expected in ((receipt, PUBLIC_RECEIPT), (index, PUBLIC_INDEX)):
        for key in ("name", "bytes", "md5", "sha256"):
            if row.get(key) != expected[key]:
                fail(f"work-package public binding drift: {expected['name']}:{key}")
    for key, value in package.get("truth_boundary", {}).items():
        if value is not False:
            fail(f"work-package completion inflation: {key}")


def validate_dispatch(
    dispatch: Mapping[str, Any],
    package: Mapping[str, Any],
    work: Mapping[str, Any],
) -> None:
    if (
        dispatch.get("schema")
        != "qikvrt_content_disposition_batch_dispatch_receipt_v1"
        or dispatch.get("state") != "BATCH_003_DISPATCHED_FIRST_SUBJECT_ACTIVE"
        or dispatch.get("work_unit_id")
        != "ADVANCE-CANONICAL-STATUS-AND-DISPATCH-BATCH-003-20260730"
        or dispatch.get("next_deterministic_effect") != NEXT_EFFECT
        or dispatch.get("observed_at") != OBSERVED_AT
    ):
        fail("Batch-003 dispatch receipt identity drift")
    authority = dispatch.get("authority_binding", {})
    if (
        authority.get("repository") != "Goldkelch/qik-vrt"
        or authority.get("main") != AUTHORITY_BASE
        or authority.get("post_acceptance_status_exact_head") != STATUS_EXACT_HEAD
        or authority.get("post_acceptance_status_pull_request") != 215
    ):
        fail("Batch-003 Authority dispatch binding drift")
    rows = dispatch.get("batch", {}).get("subjects", [])
    ids = tuple(row.get("subject_id") for row in rows if isinstance(row, dict))
    if (
        dispatch.get("batch", {}).get("batch_id") != BATCH_ID
        or dispatch.get("batch", {}).get("active_subject_count") != 6
        or ids != ACTIVE_SUBJECT_IDS
        or rows[0].get("state") != "ACTIVE_WORK_PACKAGE_MATERIALIZED"
        or any(row.get("state") != "QUEUED_WITHIN_BATCH" for row in rows[1:])
    ):
        fail("Batch-003 dispatch partition drift")
    if (
        dispatch.get("outside_active_batch", {}).get("subject_ids")
        != list(OUTSIDE_SUBJECT_IDS)
        or dispatch.get("preserved_corpus")
        != {
            "dispositioned_subject_count": 12,
            "open_subject_count": 7,
            "subject_count": 19,
        }
    ):
        fail("Batch-003 preserved corpus drift")
    completion = dispatch.get("completion_claims", {})
    if (
        completion.get("batch_003_dispatched") is not True
        or completion.get("first_subject_selected") is not True
    ):
        fail("Batch-003 dispatch completion missing")
    for key in (
        "all_content_claims_dispositioned",
        "batch_003_terminal",
        "effect_ack_done",
        "final_pass",
        "first_subject_claim_extraction_complete",
        "pass",
        "proof_corpus_published_on_zenodo",
        "zenodo_mutation_authorized",
    ):
        if completion.get(key) is not False:
            fail(f"Batch-003 dispatch completion inflation: {key}")

    validate_work_package(package)
    if (
        work.get("schema") != "qikvrt_work_unit_v1"
        or work.get("operation") != "ADVANCE_CANONICAL_STATUS_AND_DISPATCH_BATCH_003"
        or work.get("state") != "DISPATCHED"
        or work.get("authority_base") != AUTHORITY_BASE
        or work.get("batch_id") != BATCH_ID
        or work.get("first_subject_id") != FIRST_SUBJECT_ID
        or work.get("next_deterministic_effect") != NEXT_EFFECT
    ):
        fail("Batch-003 work-unit binding drift")


def build_progress(
    post_progress: Mapping[str, Any],
    dispatch: Mapping[str, Any],
) -> dict[str, Any]:
    progress = copy.deepcopy(post_progress)
    corpus = progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
    dispatch_path = DISPATCH_REL
    package_path = WORK_PACKAGE_REL

    progress["state"] = "WORKING"
    progress["current_action"] = (
        "Batch 003 is dispatched. The active work package owns "
        "SUBJECT-2581811b342e505d and is fail-closed on recovery of the exact "
        "published equality-receipts-index.json bytes."
    )
    progress["next_action"] = NEXT_EFFECT
    progress["updated_at"] = OBSERVED_AT
    progress["union_receipt_state"] = (
        "CONTENT_DISPOSITION_BATCH_003_DISPATCHED_FIRST_SUBJECT_ACTIVE"
    )
    step = (
        "Dispatch Batch 003 with six subjects and materialize the first "
        "claim-extraction work package"
    )
    if step not in progress["completed_steps"]:
        progress["completed_steps"].append(step)
    progress["pending_steps"] = [
        "Recover and hash-verify the exact public equality-receipts-index.json freeze",
        "Extract and terminally classify every claim for SUBJECT-2581811b342e505d",
        "Process the five remaining Batch-003 subjects and the final queued subject",
        "Build and verify the retrospective proof corpus before any publication effect",
    ]
    progress["projection_owner"] = {
        "tool": TOOL_REL,
        "check_command": CHECK_COMMAND,
    }

    corpus["active_batch"] = {
        "batch_id": BATCH_ID,
        "state": "DISPATCHED",
        "subjects": 6,
        "active_subject": FIRST_SUBJECT_ID,
        "active_work_package": package_path,
    }
    corpus["batch_003"] = {
        "state": "DISPATCHED_FIRST_SUBJECT_ACTIVE",
        "subjects": 6,
        "claim_extraction_complete": False,
        "terminal": False,
        "dispatch_receipt": dispatch_path,
        "active_subject": FIRST_SUBJECT_ID,
        "active_work_package": package_path,
        "next_action": NEXT_EFFECT,
    }
    corpus["next_action"] = NEXT_EFFECT
    return progress


def validate_progress(progress: Mapping[str, Any]) -> None:
    corpus = progress.get("scopes", {}).get(
        "qikvrt-zenodo-canonical-union-2026-07-28-v1", {}
    )
    active = corpus.get("active_batch", {})
    batch = corpus.get("batch_003", {})
    if (
        progress.get("schema") != "qikvrt-ai-progress/3.1"
        or progress.get("state") != "WORKING"
        or progress.get("effect_state") != "EFFECT_ACK_CONTINUE"
        or progress.get("percent") != 63
        or progress.get("next_action") != NEXT_EFFECT
        or progress.get("updated_at") != OBSERVED_AT
        or progress.get("projection_owner")
        != {"tool": TOOL_REL, "check_command": CHECK_COMMAND}
        or progress.get("union_receipt_state")
        != "CONTENT_DISPOSITION_BATCH_003_DISPATCHED_FIRST_SUBJECT_ACTIVE"
        or corpus.get("counts", {}).get("subjects") != 19
        or corpus.get("counts", {}).get("dispositioned_subjects") != 12
        or corpus.get("counts", {}).get("open_subjects") != 7
        or corpus.get("next_action") != NEXT_EFFECT
        or active.get("batch_id") != BATCH_ID
        or active.get("state") != "DISPATCHED"
        or active.get("subjects") != 6
        or active.get("active_subject") != FIRST_SUBJECT_ID
        or batch.get("state") != "DISPATCHED_FIRST_SUBJECT_ACTIVE"
        or batch.get("terminal") is not False
        or batch.get("claim_extraction_complete") is not False
        or batch.get("next_action") != NEXT_EFFECT
        or corpus.get("queued_after_active") != 1
    ):
        fail("Batch-003 current status projection drift")

    for mapping, label in (
        (progress.get("claims", {}), "top-level"),
        (corpus.get("claims", {}), "corpus"),
    ):
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            if mapping.get(key) is not False:
                fail(f"{label} release inflation: {key}")


def render_ai_status(progress: Mapping[str, Any]) -> str:
    corpus = progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
    global_scope = progress["scopes"]["qikvrt-global-claim-scope-v1"]
    counts = corpus["counts"]
    batch2 = corpus["batch_002"]
    batch3 = corpus["batch_003"]
    later = batch2["post_acceptance"]
    global_counts = global_scope["counts"]
    bar = "█" * counts["dispositioned_subjects"] + "░" * counts["open_subjects"]
    return f"""# QIK-VRT Work Status

Repository: `Goldkelch/qik-vrt`

Post-acceptance overlay: `{previous.POST_REL}`

Batch-003 dispatch receipt: `{DISPATCH_REL}`

Updated at: `{progress['updated_at']}`

Snapshot state: **`{progress['state']}`**. Overall effect state:
**`{progress['effect_state']}`**. No unqualified repository-wide
`PASS`, `FINAL_PASS`, Zenodo publication or corpus completion is claimed.

`[{bar}] {corpus['percent']}%` — Zenodo-Subject-Disposition
({counts['dispositioned_subjects']}/{counts['subjects']})

- ✓ Canonical 24-record union and 19 claim subjects bound
- ✓ Batch 001 terminally dispositioned
- ✓ Batch 002 correction accepted, promoted and reciprocally bound
- ✓ Batch 003 dispatched with six subjects
- ▶ First work package active: `{FIRST_SUBJECT_ID}`
- □ Exact public `equality-receipts-index.json` freeze recovery
- □ Six Batch-003 subjects and one later subject remain disposition-incomplete
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

- Batch 002: `{batch2['state']}`; post-acceptance chain `{later['state']}`.
- Batch 003: `{batch3['state']}` with {batch3['subjects']} subjects.
- Active subject: `{batch3['active_subject']}`.
- Active work package: `{batch3['active_work_package']}`.
- Claim extraction complete: `{str(batch3['claim_extraction_complete']).lower()}`.
- Corpus `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, Zenodo mutation and
  proof-corpus publication: **not established**.

## Active evidence boundary

The exact historical receipt bytes are already repository-bound. The live
`evidence/receipts/index.json` contains later receipts and therefore cannot
substitute for the published `equality-receipts-index.json` freeze. Recovery and
hash verification of that exact public freeze is the first active technical
effect.

## NEXT

`{progress['next_action']}`
"""


def expected_projection() -> tuple[dict[str, Any], str]:
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

    post_progress, _ = previous.expected_projection()
    progress = build_progress(post_progress, dispatch)
    validate_progress(progress)
    return progress, render_ai_status(progress)


def verify() -> dict[str, Any]:
    progress, status = expected_projection()
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
        print(result["state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
