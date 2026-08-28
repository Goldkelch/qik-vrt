#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize immutable text inputs from the published Alpha-2 source archive.

The historical Alpha-2 ZIP must remain reproducible after live status,
entrypoint, or proof-workflow files advance. Only the explicitly named text
paths are projected from the already hash-bound archive; all other archive
inputs still come directly from the current repository paths used by the
Alpha-2 packaging contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "release/formalization-v2/QIKVRT_Formalization_v2.0-alpha.2.zip"
ARCHIVE_SHA256 = "500087f6aeee41787959cfc8902852503e2182019ae4f3e88f115e94a1f5e689"
PREFIX = "QIKVRT_Formalization_v2.0-alpha.2/"
FREEZE_ROOT = ROOT / "release/formalization-v2/alpha2-frozen"
PATHS = (
    ".github/workflows/qikvrt_manuscript_proof.yml",
    "docs/publications/2026-07-22-effect-ack-universal-effect-control/"
    "proof-report.json",
    "formalization/QIKVRT_Formalization_v2.0/README.md",
    "formalization/QIKVRT_Formalization_v2.0/COMPLETION_PLAN.md",
    "formalization/QIKVRT_Formalization_v2.0/scripts/package_release.py",
    "formalization/QIKVRT_Formalization_v2.0/scripts/audit_lean_axioms.py",
    "formalization/QIKVRT_Formalization_v2.0/lakefile.toml",
    "formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization.lean",
    "formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Claims/AxiomAuditAll.lean",
    "formalization/QIKVRT_Formalization_v2.0/QIKVRTEffectAck.lean",
)
MANIFEST = FREEZE_ROOT / "FREEZE_MANIFEST.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load() -> tuple[dict[str, bytes], dict[str, object]]:
    raw = ARCHIVE.read_bytes()
    if _sha256(raw) != ARCHIVE_SHA256:
        raise ValueError("Alpha-2 archive SHA-256 differs from the fixed tagged release")
    projected: dict[str, bytes] = {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Alpha-2 archive contains duplicate names")
        for path in PATHS:
            name = PREFIX + path
            try:
                info = archive.getinfo(name)
            except KeyError as exc:
                raise ValueError(f"Alpha-2 archive lacks frozen input: {path}") from exc
            mode = info.external_attr >> 16
            if mode and not stat.S_ISREG(mode):
                raise ValueError(f"Alpha-2 frozen input is not regular: {path}")
            data = archive.read(info)
            data.decode("utf-8")
            projected[path] = data
    manifest: dict[str, object] = {
        "_license": {
            "classification": "historical_release_freeze_manifest",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "rights_holder": "Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
        },
        "schema": "qikvrt_alpha2_status_freeze_v1",
        "archive": {
            "path": ARCHIVE.relative_to(ROOT).as_posix(),
            "sha256": ARCHIVE_SHA256,
            "prefix": PREFIX,
            "authority_tag_commit": "42389236ea638f5cd40c13a486b70b1e1bf03055",
        },
        "files": [
            {
                "archive_path": path,
                "frozen_path": (FREEZE_ROOT / path).relative_to(ROOT).as_posix(),
                "bytes": len(projected[path]),
                "sha256": _sha256(projected[path]),
            }
            for path in PATHS
        ],
        "purpose": (
            "Preserve the tagged and published Alpha-2 archive bytes while live "
            "workflow, proof report, entrypoints, axiom-audit sources, README, "
            "completion-plan and package implementation status advance."
        ),
    }
    return projected, manifest


def _expected() -> dict[pathlib.Path, bytes]:
    projected, manifest = _load()
    values = {FREEZE_ROOT / path: data for path, data in projected.items()}
    values[MANIFEST] = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    return values


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("generate", "check"), nargs="?", default="generate")
    args = parser.parse_args(argv)
    try:
        expected = _expected()
        for path, data in expected.items():
            if args.action == "check":
                if not path.is_file() or path.is_symlink() or path.read_bytes() != data:
                    raise ValueError(
                        f"frozen Alpha-2 input differs: {path.relative_to(ROOT).as_posix()}"
                    )
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists() or path.read_bytes() != data:
                    path.write_bytes(data)
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile) as exc:
        print(f"BLOCK Alpha-2 status freeze: {exc}", file=sys.stderr)
        return 1
    print(
        f"PASS {'verified' if args.action == 'check' else 'materialized'} "
        f"{len(PATHS)} frozen Alpha-2 text inputs from {ARCHIVE_SHA256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
