#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Publish exactly QIK-VRT Formalization v2 alpha.3 from public alpha.2.

This module reuses the audited alpha.2 Zenodo implementation and changes only
its release identity, source record and source-evidence contract. All network,
mutation, file, metadata, HMAC, polling and public-verification gates remain in
the existing implementation. The resulting client can create one new version
from published record 21518464 in concept 21488115 and can mutate only the one
draft bound by its token-authenticated reservation.
"""
from __future__ import annotations

import contextlib
import pathlib
import re
import sys
from collections.abc import Mapping
from typing import Any, TextIO

import qikvrt_formalization_v2_zenodo as implementation
import qikvrt_zenodo_actions as shared


implementation.MANIFEST_SCHEMA = "qikvrt_formalization_v2_alpha3_zenodo_manifest_v1"
implementation.RESERVATION_KIND = "qikvrt-formalization-v2-alpha3"
implementation.RESULT_SCHEMA = "qikvrt_formalization_v2_alpha3_zenodo_result_v1"
implementation.RELEASE_ID = "2026-07-24-formalization-v2.0-alpha.3"
implementation.TARGET_VERSION = "2.0.0-alpha.3"
implementation.SOURCE_RECORD_ID = 21518464
implementation.SOURCE_VERSION_DOI = "10.5281/zenodo.21518464"
implementation.SOURCE_VERSION = "2.0.0-alpha.2"
implementation.CONCEPT_RECORD_ID = 21488115
implementation.SOURCE_EVIDENCE_SCHEMA = (
    "qikvrt_formalization_v2_alpha2_public_source_evidence_v1"
)
implementation.PROTECTED_ZENODO_IDS = frozenset(
    {21488115, 21488116, 21498773, 21498774, 21501365, 21518464}
)

UTC_SECOND = re.compile(
    r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z$"
)


class _Tee:
    def __init__(self, *targets: TextIO) -> None:
        self.targets = targets

    def write(self, value: str) -> int:
        for target in self.targets:
            target.write(value)
            target.flush()
        return len(value)

    def flush(self) -> None:
        for target in self.targets:
            target.flush()


def validate_source_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the anonymous byte verification of published alpha.2."""
    required = {
        "anonymous",
        "concept_record_id",
        "doi",
        "files",
        "public_record_verified",
        "published_record_id",
        "schema",
        "source_latest_verified",
        "source_record_id",
        "verified_at_utc",
        "version",
        "workflow_artifact_id",
        "workflow_artifact_sha256",
        "workflow_run_id",
    }
    shared._check_exact_keys(value, required, "alpha.2 public source evidence")
    if (
        value["schema"] != implementation.SOURCE_EVIDENCE_SCHEMA
        or value["source_record_id"] != implementation.SOURCE_RECORD_ID
        or value["published_record_id"] != implementation.SOURCE_RECORD_ID
        or value["concept_record_id"] != implementation.CONCEPT_RECORD_ID
        or value["doi"] != implementation.SOURCE_VERSION_DOI
        or value["version"] != implementation.SOURCE_VERSION
        or value["anonymous"] is not True
        or value["public_record_verified"] is not True
        or value["source_latest_verified"] is not True
    ):
        raise implementation.ZenodoError(
            "source evidence does not identify verified public alpha.2 record 21518464"
        )
    if (
        not isinstance(value["verified_at_utc"], str)
        or UTC_SECOND.fullmatch(value["verified_at_utc"]) is None
        or isinstance(value["workflow_run_id"], bool)
        or not isinstance(value["workflow_run_id"], int)
        or value["workflow_run_id"] <= 0
        or isinstance(value["workflow_artifact_id"], bool)
        or not isinstance(value["workflow_artifact_id"], int)
        or value["workflow_artifact_id"] <= 0
        or not isinstance(value["workflow_artifact_sha256"], str)
        or shared.HEX_64.fullmatch(value["workflow_artifact_sha256"]) is None
    ):
        raise implementation.ZenodoError("source evidence provenance is malformed")

    files = value["files"]
    if (
        not isinstance(files, list)
        or len(files) != 19
        or not all(isinstance(item, dict) for item in files)
    ):
        raise implementation.ZenodoError(
            "alpha.2 source evidence must contain exactly 19 public file receipts"
        )
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        shared._check_exact_keys(
            item, {"name", "size", "md5", "sha256"}, f"source files[{index}]"
        )
        name = item["name"]
        size = item["size"]
        md5 = item["md5"]
        sha256 = item["sha256"]
        if (
            not isinstance(name, str)
            or not name
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(md5, str)
            or shared.HEX_32.fullmatch(md5) is None
            or not isinstance(sha256, str)
            or shared.HEX_64.fullmatch(sha256) is None
        ):
            raise implementation.ZenodoError(f"source files[{index}] is malformed")
        normalized.append(
            {"name": name, "size": size, "md5": md5, "sha256": sha256}
        )
    if len({item["name"] for item in normalized}) != len(normalized):
        raise implementation.ZenodoError("source evidence contains duplicate file names")
    result = dict(value)
    result["files"] = sorted(normalized, key=lambda item: item["name"])
    return result


implementation.validate_source_evidence = validate_source_evidence


def main() -> int:
    log = pathlib.Path(
        ".qikvrt/release/formalization-v2-alpha3/zenodo-client-stderr.log"
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        with contextlib.redirect_stderr(_Tee(sys.stderr, handle)):
            return implementation.main()


if __name__ == "__main__":
    raise SystemExit(main())
