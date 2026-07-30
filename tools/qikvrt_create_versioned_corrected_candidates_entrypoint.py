#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed entrypoint for historical bindings whose targets are absent.

A historical archive may contain a manifest or checksum inventory naming a file
that is not part of that exact archive.  Such a target cannot be rehashed.  The
versioned candidate therefore replaces only that unresolvable assertion with an
explicit TARGET_ABSENT_FROM_CANDIDATE_SCOPE boundary before the normal builder
regenerates and verifies every remaining active binding.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Mapping

from tools import qikvrt_create_versioned_corrected_candidates as builder

ABSENT = "TARGET_ABSENT_FROM_CANDIDATE_SCOPE"


def scrub_json(
    value: Any,
    *,
    source: str,
    entries: Mapping[str, Any],
    pointer: str = "",
) -> list[dict[str, Any]]:
    exclusions: list[dict[str, Any]] = []
    if isinstance(value, dict):
        raw_path = value.get("path")
        raw_hash = value.get("sha256")
        if (
            isinstance(raw_path, str)
            and isinstance(raw_hash, str)
            and builder.SHA256.fullmatch(raw_hash)
            and builder.resolve_target(entries, source, raw_path) is None
        ):
            value["sha256"] = None
            value["sha256_binding_status"] = ABSENT
            exclusions.append(
                {
                    "kind": "json",
                    "source": source,
                    "target_expression": raw_path,
                    "historical_sha256": raw_hash.lower(),
                    "locator": f"{pointer}/sha256" or "/sha256",
                    "status": ABSENT,
                }
            )
        for key in sorted(value):
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            exclusions.extend(
                scrub_json(
                    value[key],
                    source=source,
                    entries=entries,
                    pointer=f"{pointer}/{escaped}",
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            exclusions.extend(
                scrub_json(
                    item,
                    source=source,
                    entries=entries,
                    pointer=f"{pointer}/{index}",
                )
            )
    return exclusions


def exclude_absent_targets(node: dict[str, Any]) -> list[dict[str, Any]]:
    exclusions: list[dict[str, Any]] = []
    entries = node["entries"]
    for path in sorted(entries):
        entry = entries[path]
        if entry["is_directory"] or entry.get("nested") is not None:
            continue
        suffix = pathlib.PurePosixPath(path).suffix.lower()
        name = pathlib.PurePosixPath(path).name.lower()
        if suffix == ".json":
            text, _encoding = builder.decode_text(entry["data"])
            if text is None:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                continue
            local = scrub_json(value, source=path, entries=entries)
            if local:
                entry["data"] = builder.pretty(value).encode("utf-8")
                exclusions.extend(local)
        elif name in builder.CHECKSUM_NAMES or suffix == ".sha256":
            text, _encoding = builder.decode_text(entry["data"])
            if text is None:
                continue
            lines = text.splitlines()
            changed = False
            for index, line in enumerate(lines):
                match = builder.CHECKSUM.match(line)
                if not match:
                    continue
                target_expression = match.group(4)
                if builder.resolve_target(entries, path, target_expression) is not None:
                    continue
                lines[index] = (
                    f"# QIKVRT_CORRECTION {ABSENT} {target_expression} "
                    f"HISTORICAL_SHA256={match.group(2).lower()}"
                )
                changed = True
                exclusions.append(
                    {
                        "kind": "checksum",
                        "source": path,
                        "target_expression": target_expression,
                        "historical_sha256": match.group(2).lower(),
                        "locator": index + 1,
                        "status": ABSENT,
                    }
                )
            if changed:
                entry["data"] = ("\n".join(lines) + "\n").encode("utf-8")
    return exclusions


_original_regenerate = builder.regenerate_bindings
_original_notice = builder.add_correction_notice


def regenerate_with_absent_boundary(node: dict[str, Any]) -> dict[str, Any]:
    exclusions = exclude_absent_targets(node)
    report = _original_regenerate(node)
    report["excluded_absent_target_binding_count"] = len(exclusions)
    report["excluded_absent_target_bindings"] = exclusions
    return report


def notice_with_absent_boundary(
    root: dict[str, Any],
    subject_id: str,
    source_observations: list[dict[str, Any]],
    decision: Mapping[str, Any],
    changes: list[dict[str, Any]],
    binding_reports: list[dict[str, Any]],
) -> None:
    _original_notice(
        root,
        subject_id,
        source_observations,
        decision,
        changes,
        binding_reports,
    )
    notice_entry = root["entries"]["QIKVRT_RETROSPECTIVE_CORRECTION_NOTICE_v1.json"]
    notice = json.loads(notice_entry["data"].decode("utf-8"))
    notice["candidate_repairs"]["absent_target_hash_bindings_explicitly_excluded"] = sum(
        int(report.get("excluded_absent_target_binding_count", 0))
        for report in binding_reports
    )
    notice_entry["data"] = builder.pretty(notice).encode("utf-8")


builder.regenerate_bindings = regenerate_with_absent_boundary
builder.add_correction_notice = notice_with_absent_boundary


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--materialize", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = builder.materialize() if args.materialize else builder.check()
    print(builder.pretty(result), end="")
    print("PASS=false")
    print("FINAL_PASS=false")
    print("EFFECT_ACK_DONE=false")
    print("ZENODO_MUTATION=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except builder.CorrectionError as exc:
        print(f"BLOCK: {exc}")
        raise SystemExit(2)
