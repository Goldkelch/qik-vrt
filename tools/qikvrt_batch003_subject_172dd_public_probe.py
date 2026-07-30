#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only byte-exact probe for Batch-003 subject 172dd9bc2738fa43.

This bootstrap does not mutate Zenodo and does not claim PASS, FINAL_PASS,
EFFECT_ACK_DONE, publication completion, or subject completion. It retrieves the
already public record, verifies the complete file set and exact bytes, applies a
fail-closed ZIP safety policy, and emits a deterministic archive-content report
for the subsequent terminal claim-disposition executor.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Any, Callable, Mapping

RECORD_ID = 20712301
DOI = "10.5281/zenodo.20712301"
ARCHIVE_NAME = "QIKVRT_V8_33_REPOSITORY_AND_ANTICIPATORY_ZENODO_415_CONTENTTYPE_FIX.zip"
SIDECAR_NAME = ARCHIVE_NAME + ".sha256"
EXPECTED = {
    ARCHIVE_NAME: {
        "bytes": 148269,
        "md5": "48b1f4cb1ddaf017b874e55cdefd5dbb",
        "sha256": "a446a0c5b9fac78e47c3b51bc88ac81a6eaa7d15add089804d46c4f294fbd2f7",
    },
    SIDECAR_NAME: {
        "bytes": 138,
        "md5": "e380ad2aa0b0b7034df9c91146e1c04a",
        "sha256": "7dbc20f4a33d727d5df9a8857e631cb29991a73f4ae38ee37243d064d29a5594",
    },
}
MAX_RECORD_BYTES = 8 * 1024 * 1024
MAX_PUBLIC_FILE_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 4096
MAX_ENTRY_BYTES = 16 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1000.0
TEXT_EXTENSIONS = {
    ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".py", ".ps1", ".sh",
    ".bat", ".cmd", ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".csv", ".tsv", ".xml", ".html",
    ".htm", ".css", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".tex", ".bib", ".lean", ".lake", ".sha256", ".sha512", ".sum",
    ".license", ".notice", ".gitignore", ".gitattributes",
}
TEXT_BASENAMES = {
    "readme", "license", "notice", "copying", "copyright", "makefile",
    "dockerfile", "ai", "authors", "changelog", "changes",
}


class ProbeError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ProbeError(message)


def digest(data: bytes) -> dict[str, Any]:
    return {
        "bytes": len(data),
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            f"blob {len(data)}\0".encode("ascii") + data
        ).hexdigest(),
    }


def verify_exact(name: str, data: bytes) -> dict[str, Any]:
    if name not in EXPECTED:
        fail(f"unexpected public file: {name}")
    observed = digest(data)
    expected = EXPECTED[name]
    for key in ("bytes", "md5", "sha256"):
        if observed[key] != expected[key]:
            fail(
                f"exact public byte mismatch for {name}: "
                f"{key} expected={expected[key]} observed={observed[key]}"
            )
    return observed


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
                "User-Agent": "qikvrt-batch003-subject-172dd-public-probe/1.0",
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
                    fail(f"response exceeded byte bound {max_bytes}: {url}")
                return data
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise ProbeError(f"unable to read {url}: {last}")


def record_files(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = record.get("files")
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, Mapping)]
    if isinstance(raw, Mapping):
        entries = raw.get("entries") if isinstance(raw.get("entries"), Mapping) else raw
        if isinstance(entries, Mapping):
            result: list[dict[str, Any]] = []
            for key, value in entries.items():
                if isinstance(value, Mapping):
                    row = dict(value)
                    row.setdefault("key", key)
                    result.append(row)
            return result
    return []


def fetch_public_record() -> tuple[Mapping[str, Any], dict[str, bytes], dict[str, Any]]:
    api_url = f"https://zenodo.org/api/records/{RECORD_ID}"
    raw_record = request_bytes(api_url, accept="application/json", max_bytes=MAX_RECORD_BYTES)
    try:
        record = json.loads(raw_record.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProbeError(f"invalid Zenodo record JSON: {exc}") from exc
    if not isinstance(record, Mapping):
        fail("Zenodo record is not a JSON object")
    if int(record.get("id") or 0) != RECORD_ID:
        fail("Zenodo record identity mismatch")
    observed_doi = record.get("doi")
    if not observed_doi and isinstance(record.get("pids"), Mapping):
        doi_row = record["pids"].get("doi")
        if isinstance(doi_row, Mapping):
            observed_doi = doi_row.get("identifier")
    if observed_doi not in (None, DOI):
        fail(f"Zenodo DOI drift: {observed_doi}")

    rows = record_files(record)
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        name = row.get("key") or row.get("filename") or row.get("name")
        if isinstance(name, str):
            if name in by_name:
                fail(f"duplicate public filename in record metadata: {name}")
            by_name[name] = row
    if set(by_name) != set(EXPECTED):
        fail(
            "Zenodo public file-set drift: "
            f"expected={sorted(EXPECTED)} observed={sorted(by_name)}"
        )

    files: dict[str, bytes] = {}
    observations: dict[str, Any] = {}
    for name in sorted(EXPECTED):
        row = by_name[name]
        expected = EXPECTED[name]
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
        data = request_bytes(
            url,
            accept="application/octet-stream, */*;q=0.1",
            max_bytes=MAX_PUBLIC_FILE_BYTES,
        )
        observations[name] = verify_exact(name, data)
        files[name] = data
    return record, files, observations


def decode_text(data: bytes) -> tuple[str | None, str | None]:
    if b"\x00" in data[:4096] and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return None, None
    encodings = []
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.append("utf-16")
    if data.startswith(b"\xef\xbb\xbf"):
        encodings.append("utf-8-sig")
    encodings.extend(["utf-8", "cp1252"])
    tried: set[str] = set()
    for encoding in encodings:
        if encoding in tried:
            continue
        tried.add(encoding)
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" in text:
            continue
        return text, encoding
    return None, None


def is_text_candidate(path: pathlib.PurePosixPath) -> bool:
    suffix = path.suffix.lower()
    name = path.name.lower()
    return suffix in TEXT_EXTENSIONS or name in TEXT_BASENAMES


def normalized_zip_path(name: str) -> pathlib.PurePosixPath:
    if not name or "\\" in name or "\x00" in name:
        fail(f"unsafe ZIP pathname encoding: {name!r}")
    path = pathlib.PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        fail(f"unsafe ZIP path: {name}")
    if len(path.as_posix()) > 512:
        fail(f"ZIP path too long: {name}")
    return path


def inspect_archive(archive: bytes) -> dict[str, Any]:
    import io

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_casefold: set[str] = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(archive), "r") as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ARCHIVE_ENTRIES:
            fail(f"ZIP entry count exceeds {MAX_ARCHIVE_ENTRIES}")
        bad = zf.testzip()
        if bad is not None:
            fail(f"ZIP CRC failure: {bad}")
        for info in infos:
            path = normalized_zip_path(info.filename)
            normalized = path.as_posix().rstrip("/")
            folded = normalized.casefold()
            if normalized in seen or folded in seen_casefold:
                fail(f"duplicate or case-colliding ZIP path: {normalized}")
            seen.add(normalized)
            seen_casefold.add(folded)

            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                fail(f"ZIP symlink rejected: {normalized}")
            if info.flag_bits & 0x1:
                fail(f"encrypted ZIP entry rejected: {normalized}")
            if info.file_size > MAX_ENTRY_BYTES:
                fail(f"ZIP entry exceeds size bound: {normalized}")
            total += info.file_size
            if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
                fail("ZIP total uncompressed size exceeds bound")
            if info.compress_size == 0:
                ratio = 1.0 if info.file_size == 0 else float("inf")
            else:
                ratio = info.file_size / info.compress_size
            if ratio > MAX_COMPRESSION_RATIO:
                fail(f"ZIP compression ratio exceeds bound: {normalized} ratio={ratio:.2f}")

            row: dict[str, Any] = {
                "path": normalized,
                "is_directory": info.is_dir(),
                "compressed_bytes": info.compress_size,
                "uncompressed_bytes": info.file_size,
                "compression_method": info.compress_type,
                "crc32": f"{info.CRC:08x}",
                "unix_mode": f"{mode:o}" if mode else None,
            }
            if not info.is_dir():
                data = zf.read(info)
                row.update(digest(data))
                text, encoding = decode_text(data) if is_text_candidate(path) else (None, None)
                if text is not None:
                    row["content_class"] = "TEXT"
                    row["text_encoding"] = encoding
                    row["text_line_count"] = len(text.splitlines())
                    row["text_utf8_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    row["text_content_base64_utf8"] = base64.b64encode(
                        text.encode("utf-8")
                    ).decode("ascii")
                else:
                    row["content_class"] = "BINARY_OR_UNDECODED"
                    row["text_encoding"] = None
            entries.append(row)
    return {
        "archive_format": "ZIP",
        "entry_count": len(entries),
        "file_count": sum(not row["is_directory"] for row in entries),
        "directory_count": sum(row["is_directory"] for row in entries),
        "total_uncompressed_bytes": total,
        "safety_policy": {
            "absolute_paths_rejected": True,
            "backslashes_rejected": True,
            "casefold_collisions_rejected": True,
            "decompression_bomb_bounds_enforced": True,
            "duplicates_rejected": True,
            "encrypted_entries_rejected": True,
            "symlinks_rejected": True,
            "traversal_rejected": True,
        },
        "entries": entries,
    }


def verify_sidecar(sidecar: bytes) -> dict[str, Any]:
    text, encoding = decode_text(sidecar)
    if text is None or encoding is None:
        fail("SHA-256 sidecar is not decodable text")
    tokens = text.replace("\r", " ").replace("\n", " ").split()
    expected_hash = EXPECTED[ARCHIVE_NAME]["sha256"]
    if expected_hash not in tokens:
        fail("SHA-256 sidecar does not bind the archive digest")
    if not any(ARCHIVE_NAME in token or "v833.zip" in token for token in tokens):
        fail("SHA-256 sidecar does not bind an archive filename")
    return {
        "encoding": encoding,
        "sha256_token_verified": True,
        "archive_name_token_verified": True,
        "normalized_text": text.replace("\r\n", "\n").replace("\r", "\n"),
    }


def build_report() -> dict[str, Any]:
    record, files, observations = fetch_public_record()
    archive = files[ARCHIVE_NAME]
    sidecar = files[SIDECAR_NAME]
    metadata = record.get("metadata") if isinstance(record.get("metadata"), Mapping) else {}
    title = metadata.get("title") if isinstance(metadata, Mapping) else None
    version = metadata.get("version") if isinstance(metadata, Mapping) else None
    published = record.get("is_published")
    if published is None:
        published = record.get("status") == "published"
    return {
        "_license": {
            "classification": "machine_readable_read_only_public_archive_probe",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_batch003_public_archive_probe_v1",
        "subject_id": "SUBJECT-172dd9bc2738fa43",
        "record": {
            "record_id": RECORD_ID,
            "doi": DOI,
            "title": title,
            "version": version,
            "published_state_observed": bool(published),
            "public_file_set_exact": True,
            "public_file_observations": observations,
        },
        "sidecar_verification": verify_sidecar(sidecar),
        "archive": {
            "name": ARCHIVE_NAME,
            **digest(archive),
            **inspect_archive(archive),
        },
        "completion_claims": {
            "archive_bytes_recovered": True,
            "archive_safety_verified": True,
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
    print("QIKVRT_ARCHIVE_PROBE_REPORT_BEGIN")
    print(encoded, end="")
    print("QIKVRT_ARCHIVE_PROBE_REPORT_END")
    print("PASS=false")
    print("FINAL_PASS=false")
    print("EFFECT_ACK_DONE=false")
    print("ZENODO_MUTATION=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeError as exc:
        print(f"BLOCK: {exc}")
        raise SystemExit(2)
