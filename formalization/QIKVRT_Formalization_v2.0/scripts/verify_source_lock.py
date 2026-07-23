#!/usr/bin/env python3
"""Verify the immutable manuscript source lock from raw file bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVENANCE = PROJECT_ROOT / "source" / "SOURCE_PROVENANCE.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pdf_page_count(path: Path) -> int | None:
    """Return the physical page count when the standard pdfinfo tool exists."""
    executable = shutil.which("pdfinfo")
    if executable is None:
        return None
    result = subprocess.run(
        [executable, str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return None


def verify_source_lock(provenance_path: Path) -> list[str]:
    """Return every source-lock violation; an empty list means success."""
    provenance_path = provenance_path.resolve()
    try:
        data: dict[str, Any] = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read provenance {provenance_path}: {exc}"]

    errors: list[str] = []
    source_files = data.get("sourceFiles")
    if not isinstance(source_files, dict) or not source_files:
        return ["sourceFiles must be a non-empty object"]

    for key, record in source_files.items():
        if not isinstance(record, dict):
            errors.append(f"sourceFiles.{key} must be an object")
            continue
        relative_path = record.get("path")
        expected_hash = record.get("sha256")
        if not isinstance(relative_path, str) or not relative_path:
            errors.append(f"sourceFiles.{key}.path must be a non-empty string")
            continue
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            errors.append(f"sourceFiles.{key}.sha256 must be a 64-character digest")
            continue

        source_path = (provenance_path.parent / relative_path).resolve()
        if not source_path.is_file():
            errors.append(f"sourceFiles.{key} missing: {source_path}")
            continue
        actual_hash = sha256_file(source_path)
        if actual_hash != expected_hash:
            errors.append(
                f"sourceFiles.{key} sha256 mismatch: expected {expected_hash}, "
                f"got {actual_hash}"
            )

        if key == "tex" and "lineCount" in record:
            actual_lines = len(source_path.read_bytes().splitlines())
            if actual_lines != record["lineCount"]:
                errors.append(
                    f"sourceFiles.tex lineCount mismatch: expected "
                    f"{record['lineCount']}, got {actual_lines}"
                )

        if key == "pdf" and "physicalPages" in record:
            actual_pages = _pdf_page_count(source_path)
            if actual_pages is not None and actual_pages != record["physicalPages"]:
                errors.append(
                    f"sourceFiles.pdf physicalPages mismatch: expected "
                    f"{record['physicalPages']}, got {actual_pages}"
                )

    policy = data.get("policy", {})
    if policy.get("sourceBytesImmutable") is not True:
        errors.append("policy.sourceBytesImmutable must be true")
    if policy.get("lineSpanHashesAreNormative") is not True:
        errors.append("policy.lineSpanHashesAreNormative must be true")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provenance",
        type=Path,
        default=DEFAULT_PROVENANCE,
        help="path to SOURCE_PROVENANCE.json",
    )
    args = parser.parse_args(argv)
    errors = verify_source_lock(args.provenance)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"PASS source lock: {args.provenance.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
