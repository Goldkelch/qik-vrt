#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Classify which expensive repository evidence generators are causally affected."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Iterable, Sequence
from typing import Any

CONTROL_PATHS = {
    ".github/workflows/qikvrt_batch04_integrity.yml",
    ".github/workflows/qikvrt_batch003_remaining_disposition.yml",
    "tools/qikvrt_materialization_scope.py",
    "tests/test_qikvrt_materialization_scope.py",
}
FORMALIZATION_PREFIXES = (
    "formalization/QIKVRT_Formalization_v2.0/",
    "release/formalization-v2/",
)
FORMALIZATION_PATHS = {
    "release/formalization-v2-alpha2-zenodo.json",
    "tests/test_formalization_v2_release_workflow.py",
}
CONTENT_PREFIXES = (
    "tools/qikvrt_content_disposition_",
    "tools/qikvrt_batch003_",
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/",
    "tests/test_content_disposition_batch_003_",
)
CONTENT_PATHS = {
    "AI_PROGRESS.json",
    "AI_STATUS.md",
}
APHORISM_PREFIXES = (
    "tools/qikvrt_aphorism_corpus_v2",
    "docs/publications/2026-08-04-aphorism-corpus-scientific-assessment/",
)
APHORISM_PATHS = {
    "docs/publications/index.json",
    "docs/publications/index.html",
    "tests/test_aphorism_corpus_v2.py",
    "work-units/MATERIALIZE_APHORISM_CORPUS_SCIENTIFIC_ASSESSMENT_V2.json",
}


def _unsafe(path: str) -> bool:
    value = pathlib.PurePosixPath(path)
    return (
        not path
        or "\x00" in path
        or path.startswith("/")
        or "\\" in path
        or ".." in value.parts
    )


def _starts(path: str, prefixes: Iterable[str]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def _content_work_unit(path: str) -> bool:
    if not path.startswith("work-units/"):
        return False
    upper = path.upper()
    return "BATCH_003" in upper or "RETROSPECTIVE_PROOF_CORPUS" in upper


def classify(paths: Sequence[str], *, force_full: bool = False) -> dict[str, Any]:
    normalized = sorted(set(path.strip() for path in paths if path.strip()))
    unsafe = sorted(path for path in normalized if _unsafe(path))
    control = sorted(path for path in normalized if path in CONTROL_PATHS)
    full = force_full or bool(unsafe) or bool(control)

    formalization = full or any(
        path in FORMALIZATION_PATHS or _starts(path, FORMALIZATION_PREFIXES)
        for path in normalized
    )
    content_disposition = full or any(
        path in CONTENT_PATHS
        or _starts(path, CONTENT_PREFIXES)
        or _content_work_unit(path)
        for path in normalized
    )
    aphorism = full or any(
        path in APHORISM_PATHS or _starts(path, APHORISM_PREFIXES)
        for path in normalized
    )

    return {
        "schema": "qikvrt_materialization_scope_v1",
        "full": full,
        "formalization": formalization,
        "content_disposition": content_disposition,
        "aphorism": aphorism,
        "integrity": True,
        "complete_repository_gates": True,
        "changed_path_count": len(normalized),
        "changed_paths": normalized,
        "full_reasons": {
            "explicit": force_full,
            "control_paths": control,
            "unsafe_paths": unsafe,
        },
        "claims": {
            "M68000_EXECUTED": False,
            "WORKFLOW_ACCELERATED_BY_M68000": False,
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def read_paths(path: pathlib.Path) -> list[str]:
    raw = path.read_bytes()
    if b"\x00" in raw:
        values = raw.split(b"\x00")
    else:
        values = raw.splitlines()
    return [value.decode("utf-8", errors="surrogateescape") for value in values if value]


def write_github_output(path: pathlib.Path, result: dict[str, Any]) -> None:
    keys = (
        "full",
        "formalization",
        "content_disposition",
        "aphorism",
        "integrity",
        "complete_repository_gates",
    )
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key in keys:
            handle.write(f"{key}={'true' if result[key] else 'false'}\n")
        handle.write(f"changed_path_count={result['changed_path_count']}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths-file", required=True, type=pathlib.Path)
    parser.add_argument("--github-output", type=pathlib.Path)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args(argv)

    try:
        paths = read_paths(args.paths_file)
        result = classify(paths, force_full=args.full)
        if args.github_output is not None:
            write_github_output(args.github_output, result)
    except (OSError, UnicodeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "schema": "qikvrt_materialization_scope_v1",
                    "state": "BLOCK",
                    "detail": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
