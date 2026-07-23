#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the deterministic QIK-VRT Formalization v2 alpha.2 source archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import stat
import zipfile


REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[3]
FORMALIZATION_ROOT = (
    REPOSITORY_ROOT / "formalization/QIKVRT_Formalization_v2.0"
)
OUTPUT_NAME = "QIKVRT_Formalization_v2.0-alpha.2.zip"
ARCHIVE_PREFIX = "QIKVRT_Formalization_v2.0-alpha.2/"
ZIP_TIMESTAMP = (2026, 7, 23, 0, 0, 0)

EXCLUDED_PARTS = {
    ".lake",
    "__pycache__",
    "build",
    "release",
    "release_authorization",
}
EXACT_INPUTS = (
    ".github/workflows/qikvrt_manuscript_proof.yml",
    "LICENSES/CC-BY-NC-ND-4.0.txt",
    "docs/publications/2026-07-23-effect-ack-lean-status/"
    "CITATION.cff",
    "docs/publications/2026-07-23-effect-ack-lean-status/"
    "EVIDENCE_BOUNDARY.md",
    "docs/publications/2026-07-23-effect-ack-lean-status/"
    "LICENSE_NOTICE.md",
    "docs/publications/2026-07-23-effect-ack-lean-status/"
    "README.md",
    "docs/publications/2026-07-23-effect-ack-lean-status/"
    "STATUSERKLAERUNG_WHATSAPP_DE.md",
    "docs/publications/2026-07-23-effect-ack-lean-status/"
    "ZENODO_FILESET.md",
    "formalization/QIKVRT_Formalization_v1.0/source/"
    "Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf",
    "formalization/QIKVRT_Formalization_v1.0/source/"
    "Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.bib",
    "formalization/QIKVRT_Formalization_v1.0/source/"
    "Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex",
    "docs/publications/2026-07-22-effect-ack-universal-effect-control/"
    "proof-report.json",
    "docs/publications/2026-07-22-effect-ack-universal-effect-control/inputs/"
    "draft-lohmann-qikvrt-effect-ack-01.txt",
    "docs/publications/2026-07-22-effect-ack-universal-effect-control/inputs/"
    "draft-lohmann-qikvrt-effect-ack-01.xml",
)
ZENODO_UPLOAD_INPUTS = (
    ("README.md", "docs/publications/2026-07-23-effect-ack-lean-status/README.md"),
    (
        "FORMALIZATION_SCOPE.md",
        "formalization/QIKVRT_Formalization_v2.0/FORMALIZATION_SCOPE.md",
    ),
    (
        "VERIFICATION_REPORT.md",
        "formalization/QIKVRT_Formalization_v2.0/VERIFICATION_REPORT.md",
    ),
    (
        "STATUSERKLAERUNG_WHATSAPP_DE.md",
        "docs/publications/2026-07-23-effect-ack-lean-status/"
        "STATUSERKLAERUNG_WHATSAPP_DE.md",
    ),
    (
        "EVIDENCE_BOUNDARY.md",
        "docs/publications/2026-07-23-effect-ack-lean-status/EVIDENCE_BOUNDARY.md",
    ),
    (
        "MANUSCRIPT_PROOF_MAP.md",
        "formalization/QIKVRT_Formalization_v2.0/MANUSCRIPT_PROOF_MAP.md",
    ),
    (
        "CLAIM_GRAPH.json",
        "formalization/QIKVRT_Formalization_v2.0/claims/CLAIM_GRAPH.json",
    ),
    (
        "DRAFT01_SOURCE_PROVENANCE.json",
        "formalization/QIKVRT_Formalization_v2.0/effect_ack/"
        "DRAFT01_SOURCE_PROVENANCE.json",
    ),
    (
        "DRAFT01_CLAIM_MATRIX.json",
        "formalization/QIKVRT_Formalization_v2.0/effect_ack/"
        "DRAFT01_CLAIM_MATRIX.json",
    ),
    (
        "CITATION.cff",
        "docs/publications/2026-07-23-effect-ack-lean-status/CITATION.cff",
    ),
    (
        "ZENODO_FILESET.md",
        "docs/publications/2026-07-23-effect-ack-lean-status/ZENODO_FILESET.md",
    ),
    (
        "LICENSE_NOTICE.md",
        "docs/publications/2026-07-23-effect-ack-lean-status/LICENSE_NOTICE.md",
    ),
    (
        "LICENSE-CODE",
        "formalization/QIKVRT_Formalization_v2.0/LICENSE-CODE",
    ),
    ("CC-BY-NC-ND-4.0.txt", "LICENSES/CC-BY-NC-ND-4.0.txt"),
    (
        "ALPHA2_INPUT.json",
        "formalization/QIKVRT_Formalization_v2.0/release_authorization/"
        "ALPHA2_INPUT.json",
    ),
    (
        "ALPHA2_EFFECT_ACK_DONE.json",
        "formalization/QIKVRT_Formalization_v2.0/release_authorization/"
        "ALPHA2_EFFECT_ACK_DONE.json",
    ),
)


def _regular_file(path: pathlib.Path) -> pathlib.Path:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode) or path.is_symlink():
        raise SystemExit(f"BLOCK: package input is not a regular file: {path}")
    return path


def release_inputs(root: pathlib.Path) -> list[pathlib.Path]:
    """Return the closed, sorted alpha.2 input set."""
    formalization = root / FORMALIZATION_ROOT.relative_to(REPOSITORY_ROOT)
    inputs: set[pathlib.Path] = set()
    for path in formalization.rglob("*"):
        relative = path.relative_to(formalization)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_file() and path.suffix != ".pyc":
            inputs.add(_regular_file(path))
    for relative in EXACT_INPUTS:
        inputs.add(_regular_file(root / relative))
    return sorted(inputs, key=lambda path: path.relative_to(root).as_posix())


def build_archive(root: pathlib.Path, output: pathlib.Path) -> str:
    files = release_inputs(root)
    payloads = [
        (path.relative_to(root).as_posix(), path.read_bytes())
        for path in files
    ]
    provenance = {
        "schema": "qikvrt_formalization_v2_alpha2_archive_provenance_v1",
        "version": "2.0.0-alpha.2",
        "archive_prefix": ARCHIVE_PREFIX,
        "entries": [
            {
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for relative, data in payloads
        ],
    }
    provenance_bytes = (
        json.dumps(
            provenance,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    payloads.append(("ARCHIVE_PROVENANCE.json", provenance_bytes))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for relative, data in sorted(payloads):
            info = zipfile.ZipInfo(ARCHIVE_PREFIX + relative, ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    return hashlib.sha256(output.read_bytes()).hexdigest()


def build_zenodo_checksums(
    root: pathlib.Path,
    archive: pathlib.Path,
    archive_checksum: pathlib.Path,
    output: pathlib.Path,
) -> None:
    """Bind every alpha.2 upload except the checksum list itself."""
    inputs = [
        (OUTPUT_NAME, _regular_file(archive)),
        (OUTPUT_NAME + ".sha256", _regular_file(archive_checksum)),
    ]
    inputs.extend(
        (name, _regular_file(root / relative))
        for name, relative in ZENODO_UPLOAD_INPUTS
    )
    names = [name for name, _path in inputs]
    if len(names) != 18 or len(names) != len(set(names)):
        raise SystemExit("BLOCK: Zenodo checksum input set is not exactly 18 files")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}\n"
            for name, path in inputs
        ),
        encoding="ascii",
        newline="\n",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository-root",
        type=pathlib.Path,
        default=REPOSITORY_ROOT,
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=(
            REPOSITORY_ROOT
            / "release/formalization-v2"
            / OUTPUT_NAME
        ),
    )
    parser.add_argument("--checksum", type=pathlib.Path)
    parser.add_argument("--zenodo-checksums", type=pathlib.Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.repository_root.resolve()
    output = args.output.resolve()
    checksum = (
        args.checksum.resolve()
        if args.checksum is not None
        else pathlib.Path(str(output) + ".sha256")
    )
    digest = build_archive(root, output)
    checksum.parent.mkdir(parents=True, exist_ok=True)
    checksum.write_text(
        f"{digest}  {OUTPUT_NAME}\n",
        encoding="ascii",
        newline="\n",
    )
    if args.zenodo_checksums is not None:
        build_zenodo_checksums(
            root,
            output,
            checksum,
            args.zenodo_checksums.resolve(),
        )
    print(output)
    print(checksum)
    if args.zenodo_checksums is not None:
        print(args.zenodo_checksums.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
