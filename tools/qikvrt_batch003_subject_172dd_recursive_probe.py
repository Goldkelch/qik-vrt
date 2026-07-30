#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Recursively inspect exact public ZIP content for Batch-003 subject 172dd.

The public Zenodo record is read-only. Nested ZIP archives are recursively
verified with the same fail-closed path, symlink, duplicate, encryption, CRC,
size and decompression-ratio policy. Every decodable text source is retained as
UTF-8 base64 in the deterministic report for terminal claim classification.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import pathlib
import stat
import zipfile
from typing import Any

from tools import qikvrt_batch003_subject_172dd_public_probe as base

MAX_DEPTH = 4
MAX_RECURSIVE_ENTRIES = 8192
MAX_RECURSIVE_UNCOMPRESSED_BYTES = 128 * 1024 * 1024


class RecursiveProbeError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise RecursiveProbeError(message)


def inspect_zip(
    data: bytes,
    *,
    archive_label: str,
    depth: int,
    state: dict[str, int],
) -> dict[str, Any]:
    if depth > MAX_DEPTH:
        fail(f"nested ZIP depth exceeds {MAX_DEPTH}: {archive_label}")
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_casefold: set[str] = set()
    local_total = 0
    try:
        zf_context = zipfile.ZipFile(io.BytesIO(data), "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise RecursiveProbeError(f"invalid ZIP archive {archive_label}: {exc}") from exc
    with zf_context as zf:
        infos = zf.infolist()
        state["entries"] += len(infos)
        if state["entries"] > MAX_RECURSIVE_ENTRIES:
            fail(f"recursive ZIP entry count exceeds {MAX_RECURSIVE_ENTRIES}")
        bad = zf.testzip()
        if bad is not None:
            fail(f"ZIP CRC failure in {archive_label}: {bad}")
        for info in infos:
            try:
                path = base.normalized_zip_path(info.filename)
            except base.ProbeError as exc:
                raise RecursiveProbeError(str(exc)) from exc
            normalized = path.as_posix().rstrip("/")
            folded = normalized.casefold()
            if normalized in seen or folded in seen_casefold:
                fail(f"duplicate or case-colliding ZIP path in {archive_label}: {normalized}")
            seen.add(normalized)
            seen_casefold.add(folded)

            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                fail(f"ZIP symlink rejected in {archive_label}: {normalized}")
            if info.flag_bits & 0x1:
                fail(f"encrypted ZIP entry rejected in {archive_label}: {normalized}")
            if info.file_size > base.MAX_ENTRY_BYTES:
                fail(f"ZIP entry exceeds size bound in {archive_label}: {normalized}")
            local_total += info.file_size
            state["bytes"] += info.file_size
            if local_total > base.MAX_TOTAL_UNCOMPRESSED_BYTES:
                fail(f"ZIP local uncompressed size exceeds bound: {archive_label}")
            if state["bytes"] > MAX_RECURSIVE_UNCOMPRESSED_BYTES:
                fail("recursive ZIP uncompressed size exceeds bound")
            ratio = (
                1.0 if info.file_size == 0 else float("inf")
            ) if info.compress_size == 0 else info.file_size / info.compress_size
            if ratio > base.MAX_COMPRESSION_RATIO:
                fail(
                    f"ZIP compression ratio exceeds bound in {archive_label}: "
                    f"{normalized} ratio={ratio:.2f}"
                )

            qualified = f"{archive_label}!/{normalized}"
            row: dict[str, Any] = {
                "path": normalized,
                "qualified_path": qualified,
                "archive_depth": depth,
                "is_directory": info.is_dir(),
                "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size,
                "compression_method": info.compress_type,
                "crc32": f"{info.CRC:08x}",
                "unix_mode": f"{mode:o}" if mode else None,
            }
            if not info.is_dir():
                payload = zf.read(info)
                row.update(base.digest(payload))
                is_nested_zip = path.suffix.lower() == ".zip" or payload.startswith(b"PK\x03\x04")
                if is_nested_zip:
                    if not zipfile.is_zipfile(io.BytesIO(payload)):
                        fail(f"ZIP-labelled entry is not a valid ZIP: {qualified}")
                    row["content_class"] = "NESTED_ZIP"
                    row["nested_archive"] = inspect_zip(
                        payload,
                        archive_label=qualified,
                        depth=depth + 1,
                        state=state,
                    )
                else:
                    text, encoding = base.decode_text(payload) if base.is_text_candidate(path) else (None, None)
                    if text is not None:
                        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
                        row["content_class"] = "TEXT"
                        row["text_encoding"] = encoding
                        row["text_line_count"] = len(normalized_text.splitlines())
                        row["text_utf8_sha256"] = hashlib.sha256(
                            normalized_text.encode("utf-8")
                        ).hexdigest()
                        row["text_content_base64_utf8"] = base64.b64encode(
                            normalized_text.encode("utf-8")
                        ).decode("ascii")
                    else:
                        row["content_class"] = "BINARY_OR_UNDECODED"
                        row["text_encoding"] = None
            entries.append(row)
    return {
        "archive_format": "ZIP",
        "archive_label": archive_label,
        "archive_depth": depth,
        "entry_count": len(entries),
        "file_count": sum(not row["is_directory"] for row in entries),
        "directory_count": sum(row["is_directory"] for row in entries),
        "total_uncompressed_bytes": local_total,
        "entries": entries,
    }


def flatten_entries(archive: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in archive["entries"]:
        row = {key: value for key, value in entry.items() if key != "nested_archive"}
        rows.append(row)
        nested = entry.get("nested_archive")
        if isinstance(nested, dict):
            rows.extend(flatten_entries(nested))
    return rows


def build_report() -> dict[str, Any]:
    try:
        record, files, observations = base.fetch_public_record()
        sidecar = base.verify_sidecar(files[base.SIDECAR_NAME])
    except base.ProbeError as exc:
        raise RecursiveProbeError(str(exc)) from exc
    archive_bytes = files[base.ARCHIVE_NAME]
    state = {"entries": 0, "bytes": 0}
    archive = inspect_zip(
        archive_bytes,
        archive_label=base.ARCHIVE_NAME,
        depth=0,
        state=state,
    )
    rows = flatten_entries(archive)
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    published = record.get("is_published")
    if published is None:
        published = record.get("status") == "published"
    text_rows = [row for row in rows if row.get("content_class") == "TEXT"]
    nested_rows = [row for row in rows if row.get("content_class") == "NESTED_ZIP"]
    return {
        "_license": {
            "classification": "machine_readable_recursive_read_only_public_archive_probe",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_batch003_recursive_public_archive_probe_v1",
        "subject_id": "SUBJECT-172dd9bc2738fa43",
        "record": {
            "record_id": base.RECORD_ID,
            "doi": base.DOI,
            "title": metadata.get("title"),
            "version": metadata.get("version"),
            "published_state_observed": bool(published),
            "public_file_set_exact": True,
            "public_file_observations": observations,
        },
        "sidecar_verification": sidecar,
        "public_archive": {
            "name": base.ARCHIVE_NAME,
            **base.digest(archive_bytes),
            **archive,
        },
        "recursive_summary": {
            "maximum_allowed_depth": MAX_DEPTH,
            "observed_maximum_depth": max((row["archive_depth"] for row in rows), default=0),
            "total_entry_count": len(rows),
            "total_text_file_count": len(text_rows),
            "total_nested_zip_count": len(nested_rows),
            "total_recursive_uncompressed_bytes": state["bytes"],
            "all_text_sources_retained_for_claim_extraction": True,
            "qualified_text_paths": [row["qualified_path"] for row in text_rows],
            "nested_zip_paths": [row["qualified_path"] for row in nested_rows],
        },
        "flat_entries": rows,
        "safety_policy": {
            "absolute_paths_rejected": True,
            "backslashes_rejected": True,
            "casefold_collisions_rejected": True,
            "crc_verified": True,
            "decompression_bomb_bounds_enforced": True,
            "duplicates_rejected": True,
            "encrypted_entries_rejected": True,
            "nested_archives_recursively_checked": True,
            "symlinks_rejected": True,
            "traversal_rejected": True,
        },
        "completion_claims": {
            "archive_bytes_recovered": True,
            "archive_safety_verified": True,
            "nested_archive_content_extracted": True,
            "all_text_sources_retained_for_claim_extraction": True,
            "claim_disposition_complete": False,
            "effect_ack_done": False,
            "final_pass": False,
            "pass": False,
            "proof_corpus_published_on_zenodo": False,
            "zenodo_mutation_authorized": False,
        },
        "next_deterministic_effect": (
            "EXTRACT_AND_TERMINALLY_CLASSIFY_EVERY_CONTENT_CLAIM_"
            "BATCH_003_SUBJECT_172DD9BC2738FA43"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = build_report()
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print("QIKVRT_RECURSIVE_ARCHIVE_PROBE_REPORT_BEGIN")
    print(encoded, end="")
    print("QIKVRT_RECURSIVE_ARCHIVE_PROBE_REPORT_END")
    print("PASS=false")
    print("FINAL_PASS=false")
    print("EFFECT_ACK_DONE=false")
    print("ZENODO_MUTATION=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RecursiveProbeError as exc:
        print(f"BLOCK: {exc}")
        raise SystemExit(2)
