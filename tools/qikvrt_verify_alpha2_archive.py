#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Rebuild the Alpha-2 archive and report exact entry-level differences."""
from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "formalization/QIKVRT_Formalization_v2.0/scripts/package_release.py"
ARCHIVE = ROOT / "release/formalization-v2/QIKVRT_Formalization_v2.0-alpha.2.zip"
SUMS = ROOT / "release/formalization-v2/ZENODO_SHA256SUMS-alpha.2"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_package_module():
    spec = importlib.util.spec_from_file_location("qikvrt_alpha2_package", SCRIPT)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load Alpha-2 package implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive_map(path: pathlib.Path) -> tuple[list[str], dict[str, tuple[bytes, tuple]]]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        values = {
            info.filename: (
                archive.read(info),
                (
                    info.date_time,
                    info.compress_type,
                    info.create_system,
                    info.external_attr,
                    info.flag_bits,
                ),
            )
            for info in archive.infolist()
        }
    return names, values


def main() -> int:
    try:
        package = load_package_module()
        with tempfile.TemporaryDirectory(prefix="qikvrt-alpha2-diff-") as raw:
            temporary = pathlib.Path(raw)
            output = temporary / package.OUTPUT_NAME
            checksum = temporary / (package.OUTPUT_NAME + ".sha256")
            zenodo = temporary / "ZENODO_SHA256SUMS"
            result = package.main(
                [
                    "--repository-root",
                    str(ROOT),
                    "--output",
                    str(output),
                    "--checksum",
                    str(checksum),
                    "--zenodo-checksums",
                    str(zenodo),
                ]
            )
            if result != 0:
                raise ValueError(f"package builder returned {result}")
            expected_names, expected = archive_map(ARCHIVE)
            actual_names, actual = archive_map(output)
            errors: list[str] = []
            if expected_names != actual_names:
                errors.append("archive entry order differs")
            missing = sorted(set(expected) - set(actual))
            added = sorted(set(actual) - set(expected))
            if missing:
                errors.append(f"missing entries: {missing}")
            if added:
                errors.append(f"added entries: {added}")
            for name in sorted(set(expected) & set(actual)):
                left, left_meta = expected[name]
                right, right_meta = actual[name]
                if left != right:
                    errors.append(
                        f"content differs: {name}: expected {sha(left)} "
                        f"({len(left)} bytes), got {sha(right)} ({len(right)} bytes)"
                    )
                if left_meta != right_meta:
                    errors.append(
                        f"ZIP metadata differs: {name}: expected {left_meta}, got {right_meta}"
                    )
            if output.read_bytes() != ARCHIVE.read_bytes() and not errors:
                errors.append(
                    "raw ZIP differs despite equal entry bytes and selected metadata; "
                    f"expected {sha(ARCHIVE.read_bytes())}, got {sha(output.read_bytes())}"
                )
            if checksum.read_text(encoding="ascii") != pathlib.Path(
                str(ARCHIVE) + ".sha256"
            ).read_text(encoding="ascii"):
                errors.append("archive checksum sidecar differs")
            if zenodo.read_bytes() != SUMS.read_bytes():
                errors.append("Zenodo checksum list differs")
            if errors:
                for error in errors:
                    print(f"BLOCK Alpha-2 archive: {error}", file=sys.stderr)
                return 1
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"BLOCK Alpha-2 archive verification: {exc}", file=sys.stderr)
        return 1
    print(
        "PASS Alpha-2 archive reproduced byte-exactly: "
        "1fc6edc074aa001680f6c244e4411ca44af036debc81f083a4665143f4c820bf"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
