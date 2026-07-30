#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Recover, verify and terminally disposition Batch-003 subject 2581811b342e505d.

The two public Zenodo source files are immutable inputs.  The historical public
receipt index is stored under a dedicated public-freeze path and must never be
substituted with the append-only live receipt index.  This executor verifies the
record read-only, extracts every explicit claim or negative claim boundary,
materializes total source-to-claim traceability, and advances only this subject.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE_REL = (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/subject-dispositions/SUBJECT-2581811b342e505d"
)
BASE = ROOT / BASE_REL
PUBLIC_FREEZE = BASE / "public-freeze"
PUBLIC_RECEIPT_NAME = "authority-mirror-equality-2026-07-27-pr106-pr56.json"
PUBLIC_INDEX_NAME = "equality-receipts-index.json"
PUBLIC_RECEIPT = PUBLIC_FREEZE / PUBLIC_RECEIPT_NAME
PUBLIC_INDEX = PUBLIC_FREEZE / PUBLIC_INDEX_NAME
RECOVERY_RECEIPT = BASE / "PUBLIC_FREEZE_RECOVERY_RECEIPT.json"
CLAIM_MATRIX = BASE / "CLAIM_MATRIX.json"
TRACEABILITY = BASE / "SOURCE_TO_CLAIM_TRACEABILITY.json"
ASSERTION_COVERAGE = BASE / "ASSERTION_NODE_COVERAGE.json"
CONTENT_DECISION = BASE / "CONTENT_CHANGE_DECISION.json"
SUBJECT_RECEIPT = BASE / "SUBJECT_DISPOSITION_RECEIPT.json"
NEXT_WORK_UNIT = (
    ROOT
    / "work-units"
    / "EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_BATCH_003_SUBJECT_172DD9BC2738FA43.json"
)
WORK_UNIT = (
    ROOT
    / "work-units"
    / "RECOVER_EXACT_PUBLIC_INDEX_BYTES_AND_EXTRACT_CLASSIFY_BATCH_003_SUBJECT_2581811B342E505D.json"
)
LIVE_INDEX = ROOT / "evidence/receipts/index.json"
PUBLICATION_EVIDENCE = ROOT / "release/authority-mirror-equality-2026-07-27/zenodo-publication.json"
WORK_PACKAGE = (
    ROOT
    / "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-003/dispatch/subjects/SUBJECT-2581811b342e505d/"
    "CLAIM_EXTRACTION_WORK_PACKAGE.json"
)

SUBJECT_ID = "SUBJECT-2581811b342e505d"
NEXT_SUBJECT_ID = "SUBJECT-172dd9bc2738fa43"
BATCH_ID = "CONTENT-DISPOSITION-BATCH-003"
RECORD_ID = 21633411
DOI = "10.5281/zenodo.21633411"
CONCEPT_DOI = "10.5281/zenodo.21633410"
OBSERVED_AT = "2026-07-30T00:58:50Z"
NEXT_EFFECT = (
    "EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_"
    "BATCH_003_SUBJECT_172DD9BC2738FA43"
)
TOOL_REL = "tools/qikvrt_content_disposition_batch_003_subject_2581811b342e505d.py"
CHECK_COMMAND = f"python3 -B {TOOL_REL} --check"

EXPECTED_PUBLIC = {
    PUBLIC_RECEIPT_NAME: {
        "bytes": 5189,
        "md5": "8792385e000502fae63fa1b4e48e4723",
        "sha256": "2372fae39499febbb005d771cb2ce62bde7967a79cdd5e3b159a3591fc80ac98",
        "git_blob_sha1": "83c80c53d330eb929defb3739ecc9184e6754639",
    },
    PUBLIC_INDEX_NAME: {
        "bytes": 1487,
        "md5": "aa033aeacb744efd8cb89ac8fcd66733",
        "sha256": "47c5d7107098c0527c80aa0d65deeeb6a15ce1496588fda3fda087d4d18d5ff4",
        "git_blob_sha1": "24ed0bf0736b444d51e6773c66b57301cb6b9727",
    },
}

LICENSE = {
    "classification": "machine_readable_retrospective_claim_disposition",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "rights_holder": "Ingolf Lohmann",
}


class SubjectDispositionError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise SubjectDispositionError(message)


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    framed = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(framed).hexdigest()


def verify_exact_bytes(name: str, data: bytes) -> None:
    expected = EXPECTED_PUBLIC.get(name)
    if expected is None:
        fail(f"unexpected public file: {name}")
    observed = {
        "bytes": len(data),
        "md5": md5_bytes(data),
        "sha256": sha256_bytes(data),
        "git_blob_sha1": git_blob_sha1(data),
    }
    if observed != expected:
        fail(f"exact public byte mismatch for {name}: {observed}")


def parse_exact_json(name: str, data: bytes) -> Mapping[str, Any]:
    verify_exact_bytes(name, data)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SubjectDispositionError(f"invalid exact public JSON {name}: {exc}") from exc
    if not isinstance(value, Mapping):
        fail(f"public source is not an object: {name}")
    return value


def load_committed_public_freeze() -> dict[str, bytes]:
    values: dict[str, bytes] = {}
    for name, path in ((PUBLIC_RECEIPT_NAME, PUBLIC_RECEIPT), (PUBLIC_INDEX_NAME, PUBLIC_INDEX)):
        try:
            data = path.read_bytes()
        except FileNotFoundError as exc:
            raise SubjectDispositionError(
                f"missing recovered public freeze: {path.relative_to(ROOT)}"
            ) from exc
        verify_exact_bytes(name, data)
        values[name] = data
    if LIVE_INDEX.is_file() and sha256_bytes(LIVE_INDEX.read_bytes()) == EXPECTED_PUBLIC[PUBLIC_INDEX_NAME]["sha256"]:
        fail("live append-only receipt index was incorrectly replaced by the historical public freeze")
    return values


def request_bytes(
    url: str,
    *,
    accept: str,
    max_bytes: int,
    attempts: int = 4,
    opener: Callable[[urllib.request.Request, float], Any] | None = None,
) -> bytes:
    last: Exception | None = None
    open_call = opener or (lambda request, timeout: urllib.request.urlopen(request, timeout=timeout))
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": "qikvrt-batch003-subject-2581811b342e505d/1.0",
            },
        )
        try:
            with open_call(request, 120.0) as response:
                final_url = response.geturl()
                parsed = urllib.parse.urlsplit(final_url)
                host = (parsed.hostname or "").lower()
                if parsed.scheme != "https" or not (
                    host == "zenodo.org" or host.endswith(".zenodo.org")
                ):
                    fail(f"Zenodo redirect escaped approved domain: {final_url}")
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    fail(f"response exceeded {max_bytes} byte bound: {url}")
                return data
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise SubjectDispositionError(f"unable to read {url}: {last}")


def record_files(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = record.get("files")
    values: list[dict[str, Any]] = []
    if isinstance(raw, list):
        values = [dict(item) for item in raw if isinstance(item, Mapping)]
    elif isinstance(raw, Mapping):
        entries = raw.get("entries") if isinstance(raw.get("entries"), Mapping) else raw
        if isinstance(entries, Mapping):
            for key, value in entries.items():
                if isinstance(value, Mapping):
                    item = dict(value)
                    item.setdefault("key", key)
                    values.append(item)
    return values


def fetch_public_record(
    *,
    request: Callable[..., bytes] = request_bytes,
) -> dict[str, bytes]:
    api_url = f"https://zenodo.org/api/records/{RECORD_ID}"
    raw_record = request(api_url, accept="application/json", max_bytes=8 * 1024 * 1024)
    try:
        record = json.loads(raw_record.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SubjectDispositionError(f"invalid Zenodo record JSON: {exc}") from exc
    if not isinstance(record, Mapping) or int(record.get("id") or 0) != RECORD_ID:
        fail("Zenodo record identity mismatch")
    observed_doi = record.get("doi") or record.get("pids", {}).get("doi", {}).get("identifier")
    if observed_doi not in {None, DOI}:
        fail(f"Zenodo DOI drift: {observed_doi}")

    rows = record_files(record)
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        name = row.get("key") or row.get("filename") or row.get("name")
        if isinstance(name, str):
            by_name[name] = row
    if set(by_name) != set(EXPECTED_PUBLIC):
        fail(
            "Zenodo public file-set drift: "
            f"expected {sorted(EXPECTED_PUBLIC)}, observed {sorted(by_name)}"
        )

    result: dict[str, bytes] = {}
    for name in sorted(EXPECTED_PUBLIC):
        row = by_name[name]
        expected = EXPECTED_PUBLIC[name]
        size = row.get("size")
        if size is not None and int(size) != expected["bytes"]:
            fail(f"Zenodo metadata byte-count drift: {name}")
        checksum = row.get("checksum")
        if isinstance(checksum, str):
            checksum = checksum.removeprefix("md5:")
            if checksum != expected["md5"]:
                fail(f"Zenodo metadata MD5 drift: {name}")
        links = row.get("links") if isinstance(row.get("links"), Mapping) else {}
        url = links.get("content") or links.get("download") or links.get("self")
        if not isinstance(url, str):
            quoted = urllib.parse.quote(name, safe="")
            url = f"https://zenodo.org/api/records/{RECORD_ID}/files/{quoted}/content"
        data = request(
            url,
            accept="application/octet-stream, */*;q=0.1",
            max_bytes=16 * 1024 * 1024,
        )
        verify_exact_bytes(name, data)
        result[name] = data
    return result


def verify_public_record_against_committed_freeze() -> dict[str, Any]:
    committed = load_committed_public_freeze()
    remote = fetch_public_record()
    for name in sorted(EXPECTED_PUBLIC):
        if remote[name] != committed[name]:
            fail(f"Zenodo byte reobservation differs from committed public freeze: {name}")
    return {
        "record_id": RECORD_ID,
        "doi": DOI,
        "file_count": 2,
        "remote_public_record_reverified": True,
        "verified_names": sorted(remote),
    }


def source_ref(name: str, pointer: str) -> str:
    return f"{name}#{pointer}"


def claim_row(
    claim_id: str,
    statement: str,
    *,
    source_file: str,
    source_pointers: Sequence[str],
    epistemic_class: str,
    status: str,
    terminal_disposition: str,
    boundary: str,
    source_value: Any = None,
) -> dict[str, Any]:
    return {
        "boundary": boundary,
        "claim_id": claim_id,
        "epistemic_class": epistemic_class,
        "proof_refs": [],
        "publication_language_status": "COMPATIBLE_WITH_DISPOSITION",
        "source_file": source_file,
        "source_pointers": list(source_pointers),
        "source_refs": [source_ref(source_file, pointer) for pointer in source_pointers],
        "source_value": source_value,
        "statement": statement,
        "status": status,
        "terminal_disposition": terminal_disposition,
    }


def build_claims(receipt: Mapping[str, Any], index: Mapping[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    number = 1

    def add(statement: str, **kwargs: Any) -> None:
        nonlocal number
        claims.append(claim_row(f"B3S258-{number:03d}", statement, **kwargs))
        number += 1

    explicit_statements = {
        "authority_mirror_equality_verified": "Authority/Mirror equality is verified for the receipt's scoped promotion.",
        "effect_ack_done": "EFFECT_ACK_DONE is established for the overall repository scope.",
        "final_pass": "FINAL_PASS is established for the overall repository scope.",
        "fully_kernel_verified_overall_completion": "Fully kernel-verified overall completion is established.",
        "pass": "PASS is established for the overall repository scope.",
        "scoped_promotion_chain_complete": "The scoped promotion chain bound by the receipt is complete.",
    }
    explicit = receipt.get("claims")
    if not isinstance(explicit, Mapping) or tuple(explicit) != tuple(explicit_statements):
        fail("explicit receipt claim set drift")
    for key, statement in explicit_statements.items():
        value = explicit[key]
        if not isinstance(value, bool):
            fail(f"explicit receipt claim is not Boolean: {key}")
        positive = value is True
        add(
            statement,
            source_file=PUBLIC_RECEIPT_NAME,
            source_pointers=[f"/claims/{key}"],
            epistemic_class="EMPIRICALLY_EVIDENCED" if positive else "SOURCE_BOUND",
            status="SUPPORTED" if positive else "NOT_ESTABLISHED",
            terminal_disposition="EMPIRICAL_EVIDENCE_BOUND" if positive else "NEGATIVE_BOUNDARY",
            boundary=(
                "Valid only for the exact scoped Authority/Mirror promotion named by this historical receipt."
                if positive
                else "A false value is an explicit non-completion boundary, not an OPEN positive proof obligation."
            ),
            source_value=value,
        )

    reobs = receipt.get("reobservation")
    if not isinstance(reobs, Mapping):
        fail("receipt reobservation object missing")
    for key, value in reobs.items():
        if key == "observed_at":
            continue
        if not isinstance(value, bool):
            fail(f"reobservation claim is not Boolean: {key}")
        add(
            f"The receipt reobservation records {key.replace('_', ' ')} as {str(value).lower()}.",
            source_file=PUBLIC_RECEIPT_NAME,
            source_pointers=[f"/reobservation/{key}"],
            epistemic_class="EMPIRICALLY_EVIDENCED",
            status="SUPPORTED" if value else "CONTRADICTED",
            terminal_disposition="EMPIRICAL_EVIDENCE_BOUND",
            boundary="This classifies the recorded repository observation; it is not a timeless theorem.",
            source_value=value,
        )

    state = receipt.get("state")
    if state != "equality_verified_for_scoped_promotion":
        fail("receipt state drift")
    add(
        "The historical receipt state is equality_verified_for_scoped_promotion.",
        source_file=PUBLIC_RECEIPT_NAME,
        source_pointers=["/state", "/scope", "/receipt_id"],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="The state applies only to the receipt_id and scope encoded in the same immutable file.",
        source_value=state,
    )

    workflow = receipt.get("workflow_evidence")
    if not isinstance(workflow, Mapping):
        fail("workflow evidence object missing")
    for side in ("authority_exact_head", "mirror_exact_head"):
        rows = workflow.get(side)
        if not isinstance(rows, list) or len(rows) != 5:
            fail(f"workflow evidence set drift: {side}")
        for idx, row in enumerate(rows):
            if not isinstance(row, Mapping):
                fail(f"workflow evidence row invalid: {side}/{idx}")
            conclusion = row.get("conclusion")
            name = row.get("name")
            if conclusion not in {"success", "skipped"} or not isinstance(name, str):
                fail(f"workflow evidence conclusion drift: {side}/{idx}")
            pointers = [
                f"/workflow_evidence/{side}/{idx}/name",
                f"/workflow_evidence/{side}/{idx}/run_id",
                f"/workflow_evidence/{side}/{idx}/conclusion",
            ]
            reason = row.get("reason")
            if reason is not None:
                pointers.append(f"/workflow_evidence/{side}/{idx}/reason")
            add(
                f"{side.replace('_', ' ')} workflow '{name}' concluded {conclusion}"
                + (f" with reason {reason}." if reason else "."),
                source_file=PUBLIC_RECEIPT_NAME,
                source_pointers=pointers,
                epistemic_class="EMPIRICALLY_EVIDENCED",
                status="SUPPORTED",
                terminal_disposition="EMPIRICAL_EVIDENCE_BOUND",
                boundary="The claim reports the named historical workflow run only.",
                source_value={"conclusion": conclusion, "name": name, "run_id": row.get("run_id")},
            )

    non_claims = receipt.get("non_claims")
    if not isinstance(non_claims, list) or len(non_claims) != 7:
        fail("receipt non-claim boundary set drift")
    for idx, text in enumerate(non_claims):
        if not isinstance(text, str) or not text:
            fail(f"invalid non-claim boundary: {idx}")
        add(
            f"The receipt explicitly does not claim {text}.",
            source_file=PUBLIC_RECEIPT_NAME,
            source_pointers=[f"/non_claims/{idx}"],
            epistemic_class="SOURCE_BOUND",
            status="EXPLICITLY_NOT_CLAIMED",
            terminal_disposition="OUT_OF_SCOPE",
            boundary="This is a terminal negative scope boundary; it does not prove or disprove the excluded proposition.",
            source_value=text,
        )

    rows = index.get("equality_receipts")
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], Mapping):
        fail("historical public index receipt set drift")
    row = rows[0]
    add(
        "The historical public equality-receipt index contains exactly one receipt entry.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=["/equality_receipts"],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="This concerns only the immutable public index freeze, not the later append-only live index.",
        source_value=1,
    )
    add(
        "The indexed receipt state is equality_verified_for_scoped_promotion.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=["/equality_receipts/0/state"],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="The state is scoped by the same index row.",
        source_value=row.get("state"),
    )
    add(
        "The index binds the receipt file to its exact SHA-256 and Git blob identities.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=["/equality_receipts/0/file_sha256", "/equality_receipts/0/git_blob_sha1", "/equality_receipts/0/path"],
        epistemic_class="EMPIRICALLY_EVIDENCED",
        status="SUPPORTED",
        terminal_disposition="EMPIRICAL_EVIDENCE_BOUND",
        boundary="The binding is verified against the exact recovered public receipt bytes.",
        source_value={"file_sha256": row.get("file_sha256"), "git_blob_sha1": row.get("git_blob_sha1")},
    )
    add(
        "The index binds Authority main and PR #106 to Mirror main and PR #56.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=[
            "/equality_receipts/0/authority/main",
            "/equality_receipts/0/authority/pull_request",
            "/equality_receipts/0/authority/repository",
            "/equality_receipts/0/mirror/main",
            "/equality_receipts/0/mirror/pull_request",
            "/equality_receipts/0/mirror/repository",
        ],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="This is an identity binding, not a fresh reobservation of current repository mains.",
        source_value={"authority": row.get("authority"), "mirror": row.get("mirror")},
    )
    add(
        "The index row identifies the historical receipt and its scoped promotion.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=["/equality_receipts/0/receipt_id", "/equality_receipts/0/scope"],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="The identity is exact and historical.",
        source_value={"receipt_id": row.get("receipt_id"), "scope": row.get("scope")},
    )
    add(
        "The index records the canonical source receipt payload SHA-256.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=["/equality_receipts/0/source_receipt_payload_sha256"],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="The source payload hash is recorded, not recomputed from truncated transport comments.",
        source_value=row.get("source_receipt_payload_sha256"),
    )
    integration = index.get("manifest_integration")
    if not isinstance(integration, Mapping):
        fail("historical index manifest integration missing")
    add(
        "The historical index declares that generated repository manifests were not mutated directly.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=["/manifest_integration/direct_generated_manifest_mutation"],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="This reports the declared integration method for this index.",
        source_value=integration.get("direct_generated_manifest_mutation"),
    )
    add(
        "The deterministic integrity generator includes the index and referenced receipts as immutable files.",
        source_file=PUBLIC_INDEX_NAME,
        source_pointers=["/manifest_integration/method"],
        epistemic_class="SOURCE_BOUND",
        status="SUPPORTED",
        terminal_disposition="SOURCE_BOUND",
        boundary="This is a repository process statement, not a kernel theorem.",
        source_value=integration.get("method"),
    )

    if len(claims) != 39:
        fail(f"claim extraction count drift: {len(claims)}")
    if len({row["claim_id"] for row in claims}) != len(claims):
        fail("duplicate claim identity")
    return claims


def source_files_metadata() -> list[dict[str, Any]]:
    rows = []
    for name, path in ((PUBLIC_RECEIPT_NAME, PUBLIC_RECEIPT), (PUBLIC_INDEX_NAME, PUBLIC_INDEX)):
        data = path.read_bytes()
        rows.append(
            {
                "bytes": len(data),
                "git_blob_sha1": git_blob_sha1(data),
                "md5": md5_bytes(data),
                "name": name,
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_bytes(data),
            }
        )
    return rows


def build_claim_matrix(claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(row["terminal_disposition"]) for row in claims)
    open_count = sum(1 for row in claims if row["terminal_disposition"] == "OPEN")
    return {
        "_license": LICENSE,
        "batch_id": BATCH_ID,
        "claim_count": len(claims),
        "claims": list(claims),
        "classification_counts": dict(sorted(counts.items())),
        "extraction_scope": {
            "explicit_receipt_claims": True,
            "negative_claim_boundaries": True,
            "receipt_reobservations": True,
            "workflow_run_conclusions": True,
            "historical_index_assertions": True,
            "non_claim_metadata_classified_separately": True,
        },
        "open_claim_count": open_count,
        "record_ids": [RECORD_ID],
        "schema": "qikvrt_retrospective_claim_matrix_v1",
        "source_artifacts": source_files_metadata(),
        "subject_id": SUBJECT_ID,
        "terminal_claim_count": len(claims) - open_count,
    }


def build_traceability(claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    files = {row["name"]: row for row in source_files_metadata()}
    entries = []
    for claim in claims:
        name = str(claim["source_file"])
        entries.append(
            {
                "claim_id": claim["claim_id"],
                "source_file": name,
                "source_file_git_blob_sha1": files[name]["git_blob_sha1"],
                "source_file_sha256": files[name]["sha256"],
                "source_pointers": claim["source_pointers"],
                "status": claim["status"],
                "terminal_disposition": claim["terminal_disposition"],
            }
        )
    return {
        "_license": LICENSE,
        "batch_id": BATCH_ID,
        "claim_count": len(entries),
        "entries": entries,
        "schema": "qikvrt_source_to_claim_traceability_v1",
        "source_files": list(files.values()),
        "subject_id": SUBJECT_ID,
        "untraced_claim_count": 0,
    }


def escape_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def leaf_nodes(value: Any, pointer: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        if not value:
            yield pointer or "/", value
        for key, child in value.items():
            yield from leaf_nodes(child, f"{pointer}/{escape_pointer_token(str(key))}")
    elif isinstance(value, list):
        if not value:
            yield pointer or "/", value
        for idx, child in enumerate(value):
            yield from leaf_nodes(child, f"{pointer}/{idx}")
    else:
        yield pointer or "/", value


def role_for_pointer(file_name: str, pointer: str, claim_ids: Sequence[str]) -> str:
    if claim_ids:
        return "CLAIM_SOURCE"
    if pointer.startswith("/_license/"):
        return "LICENSE_METADATA"
    if pointer in {"/schema", "/updated_at", "/materialized_at"} or pointer.endswith("/observed_at"):
        return "TEMPORAL_OR_SCHEMA_METADATA"
    if pointer.startswith("/authority/") or pointer.startswith("/mirror/"):
        return "REPOSITORY_IDENTITY_EVIDENCE"
    if pointer.startswith("/equality/"):
        return "HASH_OR_TREE_EVIDENCE"
    if pointer.startswith("/reciprocal_github_receipts/"):
        return "RECIPROCAL_RECEIPT_EVIDENCE"
    if pointer.startswith("/workflow_evidence/"):
        return "WORKFLOW_EVIDENCE"
    if pointer.startswith("/equality_receipts/"):
        return "INDEX_PROVENANCE_EVIDENCE"
    if pointer.startswith("/manifest_integration/"):
        return "INTEGRITY_PROCESS_EVIDENCE"
    if pointer in {"/receipt_id", "/scope", "/state"}:
        return "RECEIPT_IDENTITY_EVIDENCE"
    if pointer.startswith("/claims/") or pointer.startswith("/reobservation/") or pointer.startswith("/non_claims/"):
        return "CLAIM_SOURCE"
    return "SOURCE_METADATA"


def build_assertion_coverage(
    receipt: Mapping[str, Any],
    index: Mapping[str, Any],
    claims: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    pointer_claims: dict[tuple[str, str], list[str]] = {}
    for claim in claims:
        name = str(claim["source_file"])
        for pointer in claim["source_pointers"]:
            pointer_claims.setdefault((name, str(pointer)), []).append(str(claim["claim_id"]))

    rows = []
    for name, value in ((PUBLIC_RECEIPT_NAME, receipt), (PUBLIC_INDEX_NAME, index)):
        for pointer, leaf in leaf_nodes(value):
            direct = pointer_claims.get((name, pointer), [])
            aggregate = []
            for (candidate_name, candidate_pointer), ids in pointer_claims.items():
                if candidate_name == name and candidate_pointer == "/equality_receipts" and pointer.startswith("/equality_receipts/"):
                    aggregate.extend(ids)
            claim_ids = sorted(set(direct + aggregate))
            rows.append(
                {
                    "claim_ids": claim_ids,
                    "file": name,
                    "pointer": pointer,
                    "role": role_for_pointer(name, pointer, claim_ids),
                    "value_sha256": sha256_bytes(
                        json.dumps(leaf, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    ),
                }
            )
    if any(row["role"] == "UNCLASSIFIED" for row in rows):
        fail("unclassified source assertion node")
    return {
        "_license": LICENSE,
        "claim_source_node_count": sum(1 for row in rows if row["claim_ids"]),
        "covered_leaf_count": len(rows),
        "nodes": rows,
        "schema": "qikvrt_assertion_node_coverage_v1",
        "source_file_count": 2,
        "subject_id": SUBJECT_ID,
        "unclassified_leaf_count": 0,
    }


def build_content_decision(claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    open_count = sum(1 for row in claims if row["terminal_disposition"] == "OPEN")
    if open_count:
        fail("content decision cannot be terminal while OPEN claims remain")
    return {
        "_license": LICENSE,
        "batch_id": BATCH_ID,
        "decision": {
            "public_bytes_must_remain_unchanged": True,
            "reason": (
                "The two published historical evidence files are byte-exact, internally scoped, "
                "and explicitly keep PASS, FINAL_PASS, EFFECT_ACK_DONE and overall kernel completion false. "
                "The extracted claims require repository-side disposition evidence, not a mutation of the public record."
            ),
            "repository_evidence_addition_required": True,
            "required": False,
            "state": "NO_CONTENT_CHANGE_REQUIRED",
            "zenodo_mutation_authorized": False,
        },
        "schema": "qikvrt_content_change_decision_v1",
        "subject_id": SUBJECT_ID,
    }


def build_recovery_receipt(remote_verified: bool) -> dict[str, Any]:
    return {
        "_license": LICENSE,
        "batch_id": BATCH_ID,
        "files": source_files_metadata(),
        "observed_at": OBSERVED_AT,
        "record": {"conceptdoi": CONCEPT_DOI, "doi": DOI, "record_id": RECORD_ID},
        "recovery": {
            "live_index_substitution_rejected": True,
            "method": "READ_ONLY_ZENODO_REOBSERVATION_PLUS_EXACT_PUBLIC_GIT_BLOB_REHYDRATION",
            "public_record_file_set_exact": remote_verified,
            "remote_public_record_reverified": remote_verified,
            "source_publication_evidence": PUBLICATION_EVIDENCE.relative_to(ROOT).as_posix(),
            "sources_rewritten": False,
        },
        "schema": "qikvrt_public_freeze_recovery_receipt_v1",
        "state": "EXACT_PUBLIC_FREEZE_RECOVERED_AND_VERIFIED" if remote_verified else "EXACT_PUBLIC_FREEZE_RECOVERED_REMOTE_REOBSERVATION_PENDING",
        "subject_id": SUBJECT_ID,
    }


def build_subject_receipt(claims: Sequence[Mapping[str, Any]], remote_verified: bool) -> dict[str, Any]:
    if not remote_verified:
        fail("subject receipt cannot be materialized without remote public-record reobservation")
    open_count = sum(1 for row in claims if row["terminal_disposition"] == "OPEN")
    if open_count:
        fail("subject receipt cannot be terminal while OPEN claims remain")
    return {
        "_license": LICENSE,
        "artifacts": {
            "assertion_node_coverage": ASSERTION_COVERAGE.relative_to(ROOT).as_posix(),
            "claim_matrix": CLAIM_MATRIX.relative_to(ROOT).as_posix(),
            "content_change_decision": CONTENT_DECISION.relative_to(ROOT).as_posix(),
            "public_freeze_recovery_receipt": RECOVERY_RECEIPT.relative_to(ROOT).as_posix(),
            "source_to_claim_traceability": TRACEABILITY.relative_to(ROOT).as_posix(),
        },
        "batch_id": BATCH_ID,
        "claim_counts": {"open": open_count, "terminal": len(claims), "total": len(claims)},
        "completion_claims": {
            "all_content_claims_dispositioned": False,
            "batch_003_terminal": False,
            "effect_ack_done": False,
            "final_pass": False,
            "first_subject_claim_extraction_complete": True,
            "pass": False,
            "proof_corpus_published_on_zenodo": False,
            "subject_terminally_dispositioned": True,
            "zenodo_mutation_authorized": False,
        },
        "content_change_decision": "NO_CONTENT_CHANGE_REQUIRED",
        "next_deterministic_effect": NEXT_EFFECT,
        "observed_at": OBSERVED_AT,
        "preserved_corpus": {
            "dispositioned_subject_count": 13,
            "open_subject_count": 6,
            "subject_count": 19,
        },
        "record_id": RECORD_ID,
        "schema": "qikvrt_content_disposition_subject_receipt_v1",
        "state": "TERMINALLY_DISPOSITIONED_NO_CONTENT_CHANGE",
        "subject_id": SUBJECT_ID,
    }


def build_next_work_unit() -> dict[str, Any]:
    return {
        "_license": {
            "classification": "machine_readable_work_unit",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "batch_id": BATCH_ID,
        "dependencies": {
            "first_subject_receipt": SUBJECT_RECEIPT.relative_to(ROOT).as_posix(),
            "first_subject_state": "TERMINALLY_DISPOSITIONED_NO_CONTENT_CHANGE",
        },
        "next_deterministic_effect": NEXT_EFFECT,
        "operation": "EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS",
        "representative_record_id": 20712301,
        "requirements": [
            "retrieve the exact public archive bytes read-only",
            "verify every file identity before archive extraction",
            "reject unsafe paths, symlinks, traversal, duplicates and decompression bombs",
            "extract and classify every content claim terminally or explicitly OPEN",
            "preserve PASS, FINAL_PASS, EFFECT_ACK_DONE and Zenodo mutation as false",
        ],
        "schema": "qikvrt_work_unit_v1",
        "state": "READY",
        "subject_id": NEXT_SUBJECT_ID,
        "work_unit_id": "EXTRACT-ARCHIVE-CONTENT-THEN-DISPOSITION-CLAIMS-BATCH-003-SUBJECT-172DD9BC2738FA43-20260730",
    }


def validate_repository_bindings() -> None:
    try:
        publication = json.loads(PUBLICATION_EVIDENCE.read_text(encoding="utf-8"))
        package = json.loads(WORK_PACKAGE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise SubjectDispositionError(f"invalid public-source repository binding: {exc}") from exc

    if (
        publication.get("schema") != "qikvrt_zenodo_publication_evidence_v1"
        or publication.get("state") != "published"
        or publication.get("record_id") != RECORD_ID
        or publication.get("doi") != DOI
        or publication.get("conceptdoi") != CONCEPT_DOI
    ):
        fail("Zenodo publication-evidence identity drift")
    published = {row.get("name"): row for row in publication.get("files", []) if isinstance(row, Mapping)}
    if set(published) != set(EXPECTED_PUBLIC):
        fail("Zenodo publication-evidence file-set drift")
    for name, expected in EXPECTED_PUBLIC.items():
        row = published[name]
        for source_key, expected_key in (("size", "bytes"), ("md5", "md5"), ("sha256", "sha256"), ("git_blob_sha", "git_blob_sha1")):
            if row.get(source_key) != expected[expected_key]:
                fail(f"Zenodo publication-evidence binding drift: {name}:{source_key}")

    if (
        package.get("schema") != "qikvrt_content_claim_extraction_work_package_v1"
        or package.get("state") != "DISPATCHED_PUBLIC_FREEZE_RECOVERY_REQUIRED"
        or package.get("batch_id") != BATCH_ID
        or package.get("subject_id") != SUBJECT_ID
        or package.get("record", {}).get("record_id") != RECORD_ID
    ):
        fail("first-subject claim-extraction work-package drift")
    packaged = {row.get("name"): row for row in package.get("public_source_files", []) if isinstance(row, Mapping)}
    if set(packaged) != set(EXPECTED_PUBLIC):
        fail("claim-extraction work-package public file-set drift")
    for name, expected in EXPECTED_PUBLIC.items():
        row = packaged[name]
        for key in ("bytes", "md5", "sha256"):
            if row.get(key) != expected[key]:
                fail(f"claim-extraction work-package binding drift: {name}:{key}")


def validate_work_unit() -> None:
    try:
        work = json.loads(WORK_UNIT.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise SubjectDispositionError(f"invalid recovery work unit: {exc}") from exc
    if (
        work.get("schema") != "qikvrt_work_unit_v1"
        or work.get("operation") != "RECOVER_EXACT_PUBLIC_INDEX_BYTES_AND_EXTRACT_CLASSIFY_BATCH_003_SUBJECT_2581811B342E505D"
        or work.get("state") != "AUTHORIZED"
        or work.get("subject_id") != SUBJECT_ID
        or work.get("record_id") != RECORD_ID
    ):
        fail("recovery work-unit binding drift")


def expected_subject_artifacts(remote_verified: bool) -> dict[pathlib.Path, Any]:
    validate_work_unit()
    validate_repository_bindings()
    raw = load_committed_public_freeze()
    receipt = parse_exact_json(PUBLIC_RECEIPT_NAME, raw[PUBLIC_RECEIPT_NAME])
    index = parse_exact_json(PUBLIC_INDEX_NAME, raw[PUBLIC_INDEX_NAME])
    claims = build_claims(receipt, index)
    matrix = build_claim_matrix(claims)
    traceability = build_traceability(claims)
    coverage = build_assertion_coverage(receipt, index, claims)
    decision = build_content_decision(claims)
    recovery = build_recovery_receipt(remote_verified)
    subject = build_subject_receipt(claims, remote_verified)
    next_work = build_next_work_unit()
    return {
        RECOVERY_RECEIPT: recovery,
        CLAIM_MATRIX: matrix,
        TRACEABILITY: traceability,
        ASSERTION_COVERAGE: coverage,
        CONTENT_DECISION: decision,
        SUBJECT_RECEIPT: subject,
        NEXT_WORK_UNIT: next_work,
    }


def load_dispatch_module() -> Any:
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from tools import qikvrt_content_disposition_batch_003_dispatch as dispatch  # type: ignore

    return dispatch


def build_progress_projection() -> tuple[dict[str, Any], str]:
    dispatch = load_dispatch_module()
    base_builder = getattr(dispatch, "base_expected_projection", dispatch.expected_projection)
    progress, _ = base_builder()
    progress = copy.deepcopy(progress)
    corpus = progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
    counts = corpus["counts"]

    progress["state"] = "WORKING"
    progress["current_action"] = (
        "SUBJECT-2581811b342e505d is terminally dispositioned with exact public-byte recovery, "
        "39 classified claims, total traceability and no content change. The next owned work unit "
        "is archive extraction for SUBJECT-172dd9bc2738fa43."
    )
    progress["next_action"] = NEXT_EFFECT
    progress["updated_at"] = OBSERVED_AT
    progress["union_receipt_state"] = "CONTENT_DISPOSITION_BATCH_003_FIRST_SUBJECT_TERMINAL_NEXT_SUBJECT_READY"
    progress["percent"] = 68
    progress["projection_owner"] = {"check_command": CHECK_COMMAND, "tool": TOOL_REL}
    completed = (
        "Recover exact public index bytes and terminally disposition "
        "SUBJECT-2581811b342e505d with complete claim traceability"
    )
    if completed not in progress["completed_steps"]:
        progress["completed_steps"].append(completed)
    progress["pending_steps"] = [
        "Extract the exact public archive for SUBJECT-172dd9bc2738fa43 and disposition its claims",
        "Process the four later Batch-003 archive subjects and the final queued subject",
        "Build and verify the retrospective proof corpus before any publication effect",
    ]

    counts["dispositioned_subjects"] = 13
    counts["open_subjects"] = 6
    corpus["percent"] = 68
    corpus["next_action"] = NEXT_EFFECT
    corpus["active_batch"] = {
        "active_subject": NEXT_SUBJECT_ID,
        "active_work_package": NEXT_WORK_UNIT.relative_to(ROOT).as_posix(),
        "batch_id": BATCH_ID,
        "dispositioned_subjects": 1,
        "open_subjects": 5,
        "state": "IN_PROGRESS",
        "subjects": 6,
    }
    corpus["batch_003"] = {
        "active_subject": NEXT_SUBJECT_ID,
        "active_work_package": NEXT_WORK_UNIT.relative_to(ROOT).as_posix(),
        "claim_extraction_complete": False,
        "dispositioned_subjects": 1,
        "first_subject_claim_extraction_complete": True,
        "first_subject_receipt": SUBJECT_RECEIPT.relative_to(ROOT).as_posix(),
        "next_action": NEXT_EFFECT,
        "open_subjects": 5,
        "state": "FIRST_SUBJECT_TERMINAL_NEXT_SUBJECT_READY",
        "subjects": 6,
        "terminal": False,
    }

    for mapping in (progress["claims"], corpus["claims"]):
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            mapping[key] = False

    global_counts = progress["scopes"]["qikvrt-global-claim-scope-v1"]["counts"]
    bar = "█" * 13 + "░" * 6
    status = f"""# QIK-VRT Work Status

Repository: `Goldkelch/qik-vrt`

Batch-003 first-subject receipt: `{SUBJECT_RECEIPT.relative_to(ROOT).as_posix()}`

Updated at: `{OBSERVED_AT}`

Snapshot state: **`WORKING`**. Overall effect state: **`EFFECT_ACK_CONTINUE`**.
No unqualified repository-wide `PASS`, `FINAL_PASS`, Zenodo publication or corpus completion is claimed.

`[{bar}] 68%` — Zenodo-Subject-Disposition (13/19)

- ✓ Canonical 24-record union and 19 claim subjects bound
- ✓ Batch 001 terminally dispositioned
- ✓ Batch 002 correction accepted, promoted and reciprocally bound
- ✓ Batch 003 dispatched with six subjects
- ✓ Exact public `equality-receipts-index.json` freeze recovered and verified
- ✓ `{SUBJECT_ID}`: 39/39 claims terminally classified, zero OPEN
- ✓ Source→Claim traceability and `NO_CONTENT_CHANGE_REQUIRED` decision materialized
- ▶ Next work unit ready: `{NEXT_SUBJECT_ID}`
- □ Five Batch-003 archive subjects and one later subject remain disposition-incomplete
- □ Retrospective proof corpus and any later publication effect

## Bounded global claim scope

`qikvrt-global-claim-scope-v1`: **`FINAL_PASS`**, 100% inside its declared finite boundary
({global_counts['claims']} claims, {global_counts['primary_kernel_receipts']} primary kernel receipts,
{global_counts['open_claims']} claims retained `OPEN`). This bounded historical scope does not establish
completion of the Zenodo corpus or any unregistered statement.

## Zenodo canonical-union corpus

`qikvrt-zenodo-canonical-union-2026-07-28-v1`: **`CONTINUE`**, 13/19 subjects
dispositioned (68%), 6 open.

- Batch 003: `FIRST_SUBJECT_TERMINAL_NEXT_SUBJECT_READY` with six subjects.
- First subject: `{SUBJECT_ID}` — terminal, no public content change required.
- Active subject: `{NEXT_SUBJECT_ID}`.
- Active work unit: `{NEXT_WORK_UNIT.relative_to(ROOT).as_posix()}`.
- Corpus `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE`, Zenodo mutation and proof-corpus publication: **not established**.

## NEXT

`{NEXT_EFFECT}`
"""
    validate_progress_projection(progress)
    return progress, status


def validate_progress_projection(progress: Mapping[str, Any]) -> None:
    corpus = progress.get("scopes", {}).get("qikvrt-zenodo-canonical-union-2026-07-28-v1", {})
    counts = corpus.get("counts", {})
    batch = corpus.get("batch_003", {})
    if (
        progress.get("state") != "WORKING"
        or progress.get("effect_state") != "EFFECT_ACK_CONTINUE"
        or progress.get("percent") != 68
        or progress.get("next_action") != NEXT_EFFECT
        or progress.get("projection_owner") != {"check_command": CHECK_COMMAND, "tool": TOOL_REL}
        or counts.get("subjects") != 19
        or counts.get("dispositioned_subjects") != 13
        or counts.get("open_subjects") != 6
        or corpus.get("percent") != 68
        or batch.get("state") != "FIRST_SUBJECT_TERMINAL_NEXT_SUBJECT_READY"
        or batch.get("first_subject_claim_extraction_complete") is not True
        or batch.get("terminal") is not False
        or batch.get("active_subject") != NEXT_SUBJECT_ID
    ):
        fail("Batch-003 first-subject status projection drift")
    for mapping in (progress.get("claims", {}), corpus.get("claims", {})):
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            if mapping.get(key) is not False:
                fail(f"completion inflation in status projection: {key}")


def write_or_check(path: pathlib.Path, text: str, *, check: bool) -> None:
    if check:
        try:
            current = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise SubjectDispositionError(f"missing materialized output: {path.relative_to(ROOT)}") from exc
        if current != text:
            fail(f"materialized output drift: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def materialize(*, remote_verified: bool, check: bool) -> None:
    artifacts = expected_subject_artifacts(remote_verified)
    for path, value in artifacts.items():
        write_or_check(path, pretty(value), check=check)
    progress, status = build_progress_projection()
    dispatch = load_dispatch_module()
    write_or_check(dispatch.AI_PROGRESS, pretty(progress), check=check)
    write_or_check(dispatch.AI_STATUS, status, check=check)


def verify_materialized() -> dict[str, Any]:
    materialize(remote_verified=True, check=True)
    matrix = json.loads(CLAIM_MATRIX.read_text(encoding="utf-8"))
    trace = json.loads(TRACEABILITY.read_text(encoding="utf-8"))
    coverage = json.loads(ASSERTION_COVERAGE.read_text(encoding="utf-8"))
    decision = json.loads(CONTENT_DECISION.read_text(encoding="utf-8"))
    if (
        matrix.get("claim_count") != 39
        or matrix.get("terminal_claim_count") != 39
        or matrix.get("open_claim_count") != 0
        or trace.get("untraced_claim_count") != 0
        or coverage.get("unclassified_leaf_count") != 0
        or decision.get("decision", {}).get("state") != "NO_CONTENT_CHANGE_REQUIRED"
        or decision.get("decision", {}).get("zenodo_mutation_authorized") is not False
    ):
        fail("materialized first-subject terminal disposition contract mismatch")
    return {
        "schema": "qikvrt_batch_003_first_subject_verification_v1",
        "state": "FIRST_SUBJECT_TERMINALLY_DISPOSITIONED_NEXT_SUBJECT_READY",
        "batch_id": BATCH_ID,
        "subject_id": SUBJECT_ID,
        "claim_count": 39,
        "terminal_claim_count": 39,
        "open_claim_count": 0,
        "content_change_required": False,
        "next_deterministic_effect": NEXT_EFFECT,
        "batch_003_terminal": False,
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-public-record", action="store_true")
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        remote_verified = False
        if args.verify_public_record:
            verify_public_record_against_committed_freeze()
            remote_verified = True
        if args.materialize:
            if not remote_verified:
                fail("--materialize requires --verify-public-record")
            materialize(remote_verified=True, check=False)
        if args.check:
            result = verify_materialized()
        elif args.materialize:
            result = verify_materialized()
        else:
            raw = load_committed_public_freeze()
            receipt = parse_exact_json(PUBLIC_RECEIPT_NAME, raw[PUBLIC_RECEIPT_NAME])
            index = parse_exact_json(PUBLIC_INDEX_NAME, raw[PUBLIC_INDEX_NAME])
            claims = build_claims(receipt, index)
            result = {
                "schema": "qikvrt_batch_003_first_subject_preflight_v1",
                "state": "EXACT_PUBLIC_BYTES_PARSED_CLAIMS_CLASSIFIED",
                "claim_count": len(claims),
                "open_claim_count": sum(1 for row in claims if row["terminal_disposition"] == "OPEN"),
                "remote_public_record_reverified": remote_verified,
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False,
            }
    except (SubjectDispositionError, OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {
            "state": "BLOCK",
            "failure_class": "BATCH_003_FIRST_SUBJECT_PUBLIC_FREEZE_OR_CLAIM_DISPOSITION_INVALID",
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
