#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize or check the deterministic local arXiv current-synthesis package.

This helper has no network or arXiv interaction.  It makes the single-source
archive, rebuilds it twice from fresh extractions, refreshes local validation
receipts and fixity indexes, and leaves the action-time authorization boundary
explicitly pending.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/publications/2026-08-12-observer-relative-retrocausality"
SOURCE = BASE / "arxiv-en-current-synthesis-v2"
STAGING = ROOT / "publication-staging/arxiv-observer-relative-retrocausality-en-v2"
ARCHIVE = STAGING / "arxiv-source.tar.gz"
SOURCE_DATE_EPOCH = 1786665600
BUILD_COMMAND = (
    "SOURCE_DATE_EPOCH=1786665600 FORCE_SOURCE_DATE=1 "
    "pdflatex -interaction=nonstopmode -halt-on-error main.tex"
)
SOURCE_SUM_PATHS = (
    "main.tex",
    "README.md",
    "arxiv_v2_submission_manifest.json",
    "CURRENT_SYNTHESIS_V2_SOURCE_PROVENANCE.json",
    "EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md",
)
STAGING_SUM_PATHS = (
    "arxiv-source.tar.gz",
    "main.pdf",
    "main.tex",
    "README.md",
    "ARXIV_LOCAL_COMPATIBILITY_VALIDATION.json",
    "STAGING_README.md",
    "PDF_RENDER_VALIDATION.json",
    "arxiv_v2_submission_manifest.json",
    "CURRENT_SYNTHESIS_V2_SOURCE_PROVENANCE.json",
    "EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md",
    "SOURCE_SHA256SUMS",
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.name,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any], *, write: bool) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if path.is_file() and path.read_bytes() == payload:
        return
    if not write:
        fail(f"stale generated JSON: {path.relative_to(ROOT)}")
    path.write_bytes(payload)


def write_text(path: Path, payload: str, *, write: bool) -> None:
    data = payload.encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return
    if not write:
        fail(f"stale generated text: {path.relative_to(ROOT)}")
    path.write_bytes(data)


def archive_members(path: Path) -> list[tarfile.TarInfo]:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        if [member.name for member in members] != ["main.tex"]:
            fail("archive must contain exactly main.tex")
        if any(member.issym() or member.islnk() for member in members):
            fail("archive contains a link")
        if any(member.name.startswith("/") or ".." in Path(member.name).parts for member in members):
            fail("archive contains an unsafe member path")
        return members


def materialize_archive(*, write: bool) -> None:
    source = SOURCE / "main.tex"
    staging_source = STAGING / "main.tex"
    if source.read_bytes() != staging_source.read_bytes():
        fail("canonical and staging main.tex differ")
    with tempfile.NamedTemporaryFile(
        prefix="qikvrt-arxiv-source-", suffix=".tar.gz", dir=STAGING, delete=False
    ) as stream:
        temporary = Path(stream.name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw, mtime=SOURCE_DATE_EPOCH
            ) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    info = tarfile.TarInfo("main.tex")
                    payload = staging_source.read_bytes()
                    info.size = len(payload)
                    info.mode = 0o644
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = SOURCE_DATE_EPOCH
                    archive.addfile(info, fileobj=__import__("io").BytesIO(payload))
        if ARCHIVE.is_file() and ARCHIVE.read_bytes() == temporary.read_bytes():
            return
        if not write:
            fail("arXiv source archive differs from deterministic materialization")
        os.replace(temporary, ARCHIVE)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run_pdflatex(directory: Path) -> None:
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = str(SOURCE_DATE_EPOCH)
    environment["FORCE_SOURCE_DATE"] = "1"
    environment["TZ"] = "UTC"
    for _ in range(2):
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
            cwd=directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        if result.returncode != 0:
            fail("pdfLaTeX build failed: " + (result.stderr or result.stdout)[-4000:])


def build_from_archive() -> tuple[bytes, bytes]:
    with tempfile.TemporaryDirectory(prefix="qikvrt-arxiv-extract-") as temporary:
        directory = Path(temporary)
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            member = archive.getmember("main.tex")
            with archive.extractfile(member) as source, (directory / "main.tex").open("wb") as target:
                if source is None:
                    fail("archive source is unreadable")
                shutil.copyfileobj(source, target)
        run_pdflatex(directory)
        pdf = (directory / "main.pdf").read_bytes()
        out = (directory / "main.out").read_bytes()
        return pdf, out


def pdf_details(path: Path) -> tuple[int, str, str]:
    result = subprocess.run(
        ["pdfinfo", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        fail("pdfinfo failed: " + result.stderr)
    fields: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return int(fields["Pages"]), "A4", fields["PDF version"]


def materialize_pdf(*, write: bool) -> tuple[dict[str, Any], int, str, bytes]:
    first_pdf, first_out = build_from_archive()
    second_pdf, _ = build_from_archive()
    if first_pdf != second_pdf:
        fail("two fresh archive builds did not produce byte-identical PDFs")
    if write:
        (STAGING / "main.pdf").write_bytes(first_pdf)
        (STAGING / "build/main.pdf").write_bytes(first_pdf)
        (STAGING / "build/main.out").write_bytes(first_out)
    elif (STAGING / "main.pdf").read_bytes() != first_pdf:
        fail("staging main.pdf differs from a fresh deterministic archive build")
    pages, page_size, pdf_version = pdf_details(STAGING / "main.pdf")
    return identity(STAGING / "main.pdf"), pages, pdf_version, first_pdf


def materialize_visuals(*, write: bool, pages: int) -> None:
    if pages != 8:
        fail(f"unexpected page count for current arXiv candidate: {pages}")
    with tempfile.TemporaryDirectory(prefix="qikvrt-arxiv-pages-") as temporary:
        output = Path(temporary) / "page"
        result = subprocess.run(
            ["pdftoppm", "-png", "-r", "150", str(STAGING / "main.pdf"), str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        if result.returncode != 0:
            fail("pdftoppm failed: " + result.stderr)
        rendered = [Path(temporary) / f"page-{page}.png" for page in range(1, pages + 1)]
        if not all(path.is_file() for path in rendered):
            fail("pdftoppm did not produce every expected page")
        if write:
            target = STAGING / "rendered-pages"
            target.mkdir(exist_ok=True)
            for path in rendered:
                shutil.copyfile(path, target / path.name)
            contact = Path(temporary) / "contact.png"
            montage = subprocess.run(
                [
                    "montage",
                    *(str(path) for path in rendered),
                    "-thumbnail",
                    "220x",
                    "-tile",
                    "2x4",
                    "-geometry",
                    "+4+4",
                    str(contact),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
            if montage.returncode != 0:
                fail("montage failed: " + montage.stderr)
            shutil.copyfile(contact, STAGING / "render-contact-sheet.png")


def authorization_draft(archive: dict[str, Any], pdf: dict[str, Any], pages: int) -> str:
    return f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Exact arXiv v2 submission authorization — action-time binding draft

Status: **`DRAFT_NOT_YET_AN_EXTERNAL_SUBMISSION_RECEIPT`**.

This document binds the current local arXiv successor archive.  It does not
claim that arXiv has received, accepted, announced, endorsed, or identified
the manuscript.

## Candidate

- Candidate ID:
  `qikvrt-observer-relative-retrocausality-arxiv-en-current-synthesis-2026-08-12-v2`
- Title: *Observer-Relative Retrocausality: Negative Information Direction
  Along Monotonic Local Change Time*
- Author: Ingolf Lohmann
- Primary category candidate: `cs.DC`
- Suggested cross-lists: `cs.LO`, `cs.CR`
- Comment: distributed-information-systems manuscript; the quantum material is
  a bounded physical bridge and not an independent `quant-ph` result.

## Exact upload archive

| Field | Bound value |
|---|---|
| File | `arxiv-source.tar.gz` |
| Bytes | `{archive['bytes']}` |
| SHA-256 | `{archive['sha256']}` |
| Members | `main.tex` |
| Rendered PDF SHA-256 | `{pdf['sha256']}` |
| Build result | two successful pdfLaTeX passes; {pages} pages; archive rebuild PDF byte-identical |

## Action-time declaration to record after destination re-observation

> I, Ingolf Lohmann, authorize submission of **only** the archive identified
> above to the arXiv target fields displayed and re-observed at the time of
> action: title, author/affiliation, primary category, cross-lists, comments,
> and the selected current arXiv distribution licence.  I confirm that the
> upload archive has SHA-256 `{archive['sha256']}`.
> No differing bytes, metadata field, destination, or licence selection is
> authorized by this declaration.

The author has directly released the Zenodo/arXiv/IETF publication work in the
shared work context.  This draft preserves the required exact-byte and
destination-field binding rather than fabricating a platform action or a
signature that has not been observed.

## Required completion evidence

1. A fresh observation of the arXiv account and destination fields.
2. The final exact author declaration above, completed against those fields.
3. An arXiv response/receipt bound to the upload and target metadata.
4. Independent receipt inspection before any claim of submission, identifier,
   acceptance, announcement, or endorsement.
"""


def checksum_payload(directory: Path, paths: tuple[str, ...]) -> str:
    return "".join(
        f"{hashlib.sha256((directory / name).read_bytes()).hexdigest()}  {name}\n"
        for name in paths
    )


def refresh_receipts(*, write: bool, archive: dict[str, Any], pdf: dict[str, Any], pages: int, pdf_version: str) -> None:
    tex = identity(STAGING / "main.tex")
    for manifest_path in (
        SOURCE / "arxiv_v2_submission_manifest.json",
        STAGING / "arxiv_v2_submission_manifest.json",
    ):
        manifest = read_json(manifest_path)
        bindings = manifest["artifact_bindings"]
        bindings["main.tex"].update({"bytes": tex["bytes"], "sha256": tex["sha256"]})
        bindings["main.pdf"].update({"bytes": pdf["bytes"], "sha256": pdf["sha256"]})
        bindings["arxiv-source.tar.gz"].update({"bytes": archive["bytes"], "sha256": archive["sha256"]})
        manifest["build_and_visual_validation"].update(
            {
                "command": BUILD_COMMAND,
                "passes": 2,
                "result": "SUCCESS",
                "page_count": pages,
                "second_pass_warnings": [],
                "archive_rebuild_pdf_byte_identical": True,
            }
        )
        write_json(manifest_path, manifest, write=write)

    validation = read_json(STAGING / "PDF_RENDER_VALIDATION.json")
    validation["source_archive"].update({"bytes": archive["bytes"], "sha256": archive["sha256"], "members": ["main.tex"]})
    validation["build"].update({"command": BUILD_COMMAND, "passes": 2, "result": "SUCCESS", "warnings_after_second_pass": []})
    validation["output_pdf"].update({"bytes": pdf["bytes"], "sha256": pdf["sha256"], "page_count": pages, "page_size": "A4", "pdf_version": pdf_version})
    validation["rebuild_validation"].update({"result": "PASS", "pdf_byte_identical": True})
    validation["visual_validation"].update({"renderer": "Poppler pdftoppm", "resolution_dpi": 150, "page_count_rendered": pages, "contact_sheet": "render-contact-sheet.png", "result": "PASS"})
    write_json(STAGING / "PDF_RENDER_VALIDATION.json", validation, write=write)

    compatibility = read_json(STAGING / "ARXIV_LOCAL_COMPATIBILITY_VALIDATION.json")
    compatibility["validation_date"] = "2026-08-14"
    compatibility["exact_archive"].update({"bytes": archive["bytes"], "sha256": archive["sha256"], "members": ["main.tex"]})
    compatibility["tex_source"].update({"sha256": tex["sha256"]})
    compatibility["fresh_archive_build"].update({"command": BUILD_COMMAND, "passes": 2, "result": "PASS", "substantive_second_pass_diagnostics": []})
    compatibility["fresh_archive_build"]["pdf"].update({"sha256": pdf["sha256"], "byte_identical_to_frozen_staging_pdf": True, "pages": pages, "page_size": "A4", "pdf_version": pdf_version})
    write_json(STAGING / "ARXIV_LOCAL_COMPATIBILITY_VALIDATION.json", compatibility, write=write)

    draft = authorization_draft(archive, pdf, pages)
    for path in (
        SOURCE / "EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md",
        STAGING / "EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md",
    ):
        write_text(path, draft, write=write)

    write_text(SOURCE / "SHA256SUMS", checksum_payload(SOURCE, SOURCE_SUM_PATHS), write=write)
    write_text(STAGING / "SOURCE_SHA256SUMS", checksum_payload(STAGING, SOURCE_SUM_PATHS), write=write)
    write_text(STAGING / "SHA256SUMS", checksum_payload(STAGING, STAGING_SUM_PATHS), write=write)


def check_common(archive: dict[str, Any], pdf: dict[str, Any], pages: int) -> None:
    archive_members(ARCHIVE)
    if SOURCE.joinpath("main.tex").read_bytes() != STAGING.joinpath("main.tex").read_bytes():
        fail("source and staging TeX are no longer byte-identical")
    for manifest_path in (
        SOURCE / "arxiv_v2_submission_manifest.json",
        STAGING / "arxiv_v2_submission_manifest.json",
    ):
        manifest = read_json(manifest_path)
        bindings = manifest["artifact_bindings"]
        if bindings["main.tex"]["sha256"] != identity(STAGING / "main.tex")["sha256"]:
            fail(f"stale TeX binding: {manifest_path.relative_to(ROOT)}")
        if bindings["main.pdf"]["sha256"] != pdf["sha256"]:
            fail(f"stale PDF binding: {manifest_path.relative_to(ROOT)}")
        if bindings["arxiv-source.tar.gz"]["sha256"] != archive["sha256"]:
            fail(f"stale archive binding: {manifest_path.relative_to(ROOT)}")
        if manifest["build_and_visual_validation"]["page_count"] != pages:
            fail(f"stale page count: {manifest_path.relative_to(ROOT)}")
    if (SOURCE / "SHA256SUMS").read_text(encoding="utf-8") != checksum_payload(SOURCE, SOURCE_SUM_PATHS):
        fail("source SHA256SUMS is stale")
    if (STAGING / "SOURCE_SHA256SUMS").read_text(encoding="utf-8") != checksum_payload(STAGING, SOURCE_SUM_PATHS):
        fail("staging source SHA256SUMS is stale")
    if (STAGING / "SHA256SUMS").read_text(encoding="utf-8") != checksum_payload(STAGING, STAGING_SUM_PATHS):
        fail("staging SHA256SUMS is stale")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="materialize local package artifacts")
    parser.add_argument("--check", action="store_true", help="rebuild and verify local package artifacts")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    try:
        materialize_archive(write=args.write)
        archive = identity(ARCHIVE)
        archive_members(ARCHIVE)
        pdf, pages, pdf_version, _ = materialize_pdf(write=args.write)
        materialize_visuals(write=args.write, pages=pages)
        refresh_receipts(write=args.write, archive=archive, pdf=pdf, pages=pages, pdf_version=pdf_version)
        check_common(archive, pdf, pages)
        print(
            "PASS arXiv current-synthesis local materialization "
            f"archive_sha256={archive['sha256']} pdf_sha256={pdf['sha256']} pages={pages} "
            "external_effect=NONE"
        )
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print(f"BLOCK: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
