#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Hardened front end for the retrospective Zenodo corpus proof inventory.

Zenodo file keys may contain safe relative POSIX path segments.  The original
inventory correctly rejected traversal, but was over-restrictive because it
accepted only a basename.  This front end preserves the established inventory
and proof-envelope implementation while replacing only the public-key parser
and adding an explicit public-record state gate.
"""
from __future__ import annotations

import pathlib
import sys
import urllib.parse
from collections.abc import Mapping, Sequence
from typing import Any, NoReturn

try:
    from tools import qikvrt_zenodo_corpus_proof as base
except ModuleNotFoundError:
    import qikvrt_zenodo_corpus_proof as base  # type: ignore[no-redef]


class PublicKeyError(base.CorpusProofError):
    """Unsafe or ambiguous public Zenodo file key."""


def fail(message: str) -> NoReturn:
    raise PublicKeyError(message)


def safe_public_key(raw: Any, record_id: int) -> str:
    """Return an exact safe relative POSIX key or fail closed.

    Safe nested keys such as ``source/article.pdf`` are preserved exactly.
    Absolute paths, empty or dot segments, traversal, Windows separators, NUL,
    DEL and C0 control characters are rejected.
    """
    if not isinstance(raw, str) or not raw:
        fail(f"record {record_id} contains an empty public file key")
    if "\x00" in raw or "\\" in raw:
        fail(f"record {record_id} contains an unsafe public file key")
    if any(ord(character) < 32 or ord(character) == 127 for character in raw):
        fail(f"record {record_id} contains a control character in a public file key")
    path = pathlib.PurePosixPath(raw)
    if path.is_absolute() or raw.startswith("/"):
        fail(f"record {record_id} contains an absolute public file key")
    if any(part in {"", ".", ".."} for part in path.parts):
        fail(f"record {record_id} contains traversal in a public file key")
    normalized = path.as_posix()
    if normalized != raw:
        fail(f"record {record_id} contains a non-canonical public file key")
    return raw


def public_files(record: Mapping[str, Any], record_id: int) -> list[dict[str, Any]]:
    """Normalize Zenodo list- and mapping-shaped public file metadata."""
    raw = record.get("files")
    values: list[dict[str, Any]] = []
    if isinstance(raw, list):
        values = [dict(item) for item in raw if isinstance(item, dict)]
    elif isinstance(raw, dict):
        entries = raw.get("entries")
        source = entries if isinstance(entries, dict) else raw
        for key, item in source.items():
            if isinstance(item, dict):
                normalized = dict(item)
                normalized.setdefault("key", key)
                values.append(normalized)

    result: list[dict[str, Any]] = []
    for value in values:
        key = safe_public_key(
            value.get("key") or value.get("filename") or value.get("name"),
            record_id,
        )
        links = value.get("links") if isinstance(value.get("links"), dict) else {}
        url = links.get("content") or links.get("download") or links.get("self")
        if not isinstance(url, str) or not url:
            quoted = urllib.parse.quote(key, safe="")
            url = f"{base.ZENODO_ORIGIN}/api/records/{record_id}/files/{quoted}/content"
        result.append(
            {
                "name": key,
                "declared_size": value.get("size", value.get("filesize")),
                "declared_checksum": value.get("checksum", value.get("md5")),
                "download_url": url,
            }
        )
    if not result:
        fail(f"published record {record_id} exposes no public files")
    keys = [item["name"] for item in result]
    if len(keys) != len(set(keys)):
        fail(f"published record {record_id} exposes duplicate public file keys")
    return sorted(result, key=lambda item: item["name"])


def public_record_is_published(record: Mapping[str, Any]) -> bool:
    return (
        record.get("is_published") is True
        or record.get("submitted") is True
        or str(record.get("status", "")).lower() in {"published", "done"}
        or str(record.get("state", "")).lower() in {"published", "done"}
    )


_original_build_envelope = base.build_envelope


def build_envelope(*, public_record: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    if not public_record_is_published(public_record):
        record_id = base.positive_int(public_record.get("id"))
        fail(f"public record {record_id or 'unknown'} does not expose a published state")
    return _original_build_envelope(public_record=public_record, **kwargs)


# Replace only the two functions used dynamically by base.inventory().
base.public_files = public_files
base.build_envelope = build_envelope


def main(argv: Sequence[str] | None = None) -> int:
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
