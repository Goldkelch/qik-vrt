#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify one public Zenodo software record against a local hash manifest.

The verifier is anonymous and read-only.  It checks record/concept/DOI/version,
selected stable metadata fields, the exact file-name set, API sizes and MD5s,
and independently downloads every file to recompute MD5 and SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat
import urllib.parse
import urllib.request
from typing import Any

MAX_JSON_BYTES = 16 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024


def _zenodo_host(host: str | None) -> bool:
    return host == "zenodo.org" or (
        isinstance(host, str) and host.endswith(".zenodo.org")
    )


def _regular(path: pathlib.Path) -> pathlib.Path:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise SystemExit(f"BLOCK: path is not a regular file: {path}")
    return path


def _safe_output(root: pathlib.Path, raw: str) -> pathlib.Path:
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError:
        raise SystemExit("BLOCK: result path escapes repository root") from None
    return resolved


def _get_json(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not _zenodo_host(parsed.hostname):
        raise SystemExit("BLOCK: public record URL is not an allowlisted Zenodo URL")
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "qikvrt-public-manifest-verifier/1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        final = urllib.parse.urlsplit(response.geturl())
        raw = response.read(MAX_JSON_BYTES + 1)
    if final.scheme != "https" or not _zenodo_host(final.hostname):
        raise SystemExit("BLOCK: public record redirect escaped Zenodo")
    if len(raw) > MAX_JSON_BYTES:
        raise SystemExit("BLOCK: public record response exceeded its bound")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("BLOCK: public record response is not an object")
    return value


def _download(url: str, expected_name: str) -> tuple[int, str, str]:
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or not _zenodo_host(parsed.hostname)
        or parsed.query
        or parsed.fragment
    ):
        raise SystemExit(f"BLOCK: public file URL escaped Zenodo: {expected_name}")
    request = urllib.request.Request(
        url, method="GET", headers={"User-Agent": "qikvrt-public-manifest-verifier/1"}
    )
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=180) as response:
        final = urllib.parse.urlsplit(response.geturl())
        if final.scheme != "https" or not _zenodo_host(final.hostname):
            raise SystemExit(
                f"BLOCK: public file redirect escaped Zenodo: {expected_name}"
            )
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise SystemExit(f"BLOCK: public file exceeded its bound: {expected_name}")
            md5.update(chunk)
            sha256.update(chunk)
    return size, md5.hexdigest(), sha256.hexdigest()


def verify(
    manifest_path: pathlib.Path,
    record_id: int,
    doi: str,
) -> dict[str, Any]:
    manifest_raw = _regular(manifest_path).read_bytes()
    manifest = json.loads(manifest_raw.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise SystemExit("BLOCK: manifest is not an object")
    software = manifest.get("software")
    if not isinstance(software, dict):
        raise SystemExit("BLOCK: manifest software object is missing")
    concept_id = software.get("concept_record_id")
    expected_metadata = software.get("metadata")
    expected_files = software.get("files")
    if (
        isinstance(concept_id, bool)
        or not isinstance(concept_id, int)
        or concept_id <= 0
        or not isinstance(expected_metadata, dict)
        or not isinstance(expected_files, list)
    ):
        raise SystemExit("BLOCK: manifest identity, metadata or files are malformed")

    record = _get_json(f"https://zenodo.org/api/records/{record_id}")
    metadata = record.get("metadata")
    public_files = record.get("files")
    if not isinstance(metadata, dict) or not isinstance(public_files, list):
        raise SystemExit("BLOCK: public metadata or files are malformed")
    observed_identity = {
        "record_id": int(record.get("id")),
        "concept_record_id": int(record.get("conceptrecid")),
        "doi": metadata.get("doi"),
        "version": metadata.get("version"),
    }
    expected_identity = {
        "record_id": record_id,
        "concept_record_id": concept_id,
        "doi": doi,
        "version": expected_metadata.get("version"),
    }
    if observed_identity != expected_identity:
        raise SystemExit(
            f"BLOCK: public record identity differs: {observed_identity!r}"
        )

    metadata_comparison = {}
    for key in ("title", "description", "creators", "version"):
        expected = expected_metadata.get(key)
        observed = metadata.get(key)
        metadata_comparison[key] = observed == expected
    if not all(metadata_comparison.values()):
        raise SystemExit(
            "BLOCK: stable public metadata differs: "
            + ",".join(key for key, value in metadata_comparison.items() if not value)
        )

    expected_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(expected_files):
        if not isinstance(item, dict):
            raise SystemExit(f"BLOCK: manifest files[{index}] is not an object")
        name = item.get("name")
        if not isinstance(name, str) or not name or name in expected_by_name:
            raise SystemExit("BLOCK: manifest file names are invalid")
        expected_by_name[name] = item

    public_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(public_files):
        if not isinstance(item, dict):
            raise SystemExit(f"BLOCK: public files[{index}] is not an object")
        name = item.get("key", item.get("filename"))
        if not isinstance(name, str) or not name or name in public_by_name:
            raise SystemExit("BLOCK: public file names are invalid")
        public_by_name[name] = item
    if set(expected_by_name) != set(public_by_name):
        raise SystemExit(
            "BLOCK: public file-name set differs; missing="
            + repr(sorted(set(expected_by_name) - set(public_by_name)))
            + "; extra="
            + repr(sorted(set(public_by_name) - set(expected_by_name)))
        )

    receipts = []
    total = 0
    for name in sorted(expected_by_name):
        expected = expected_by_name[name]
        public = public_by_name[name]
        expected_size = expected.get("size")
        expected_md5 = expected.get("md5")
        expected_sha256 = expected.get("sha256")
        public_size = public.get("size")
        public_checksum = public.get("checksum")
        links = public.get("links")
        url = None
        if isinstance(links, dict):
            for key in ("self", "download", "content"):
                if isinstance(links.get(key), str):
                    url = links[key]
                    break
        if (
            isinstance(expected_size, bool)
            or not isinstance(expected_size, int)
            or expected_size < 0
            or not isinstance(expected_md5, str)
            or len(expected_md5) != 32
            or not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or public_size != expected_size
            or public_checksum != "md5:" + expected_md5
            or not isinstance(url, str)
        ):
            raise SystemExit(f"BLOCK: public file metadata differs: {name}")
        size, md5, sha256 = _download(url, name)
        total += size
        if total > MAX_TOTAL_BYTES:
            raise SystemExit("BLOCK: aggregate public download exceeded its bound")
        if size != expected_size or md5 != expected_md5 or sha256 != expected_sha256:
            raise SystemExit(f"BLOCK: public file bytes differ: {name}")
        receipts.append(
            {"name": name, "size": size, "md5": md5, "sha256": sha256}
        )

    return {
        "schema": "qikvrt_public_zenodo_manifest_verification_v1",
        "status": "PASS",
        "record_id": record_id,
        "concept_record_id": concept_id,
        "doi": doi,
        "version": expected_metadata.get("version"),
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "metadata_matches": metadata_comparison,
        "file_count": len(receipts),
        "files": receipts,
        "public_record_verified": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--record-id", required=True, type=int)
    parser.add_argument("--doi", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--repository-root", default=".")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = pathlib.Path(args.repository_root).resolve(strict=True)
    manifest_path = pathlib.Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    result_path = _safe_output(root, args.result)
    result = verify(manifest_path.resolve(strict=True), args.record_id, args.doi)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "record_id": result["record_id"],
                "file_count": result["file_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
