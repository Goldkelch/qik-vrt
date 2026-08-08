#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Focused compatibility smoke for the pypdf APIs consumed by xml2rfc 3.34.0."""
from __future__ import annotations
import importlib.metadata as metadata
from pathlib import Path
import tempfile
import pypdf
from xml2rfc import walkpdf

def main() -> int:
    if metadata.version("pypdf") != "6.15.0":
        raise SystemExit("FAIL: pypdf metadata is not exactly 6.15.0")
    md = metadata.metadata("pypdf")
    expression = md.get("License-Expression") or md.get("License") or ""
    if "BSD-3-Clause" not in expression:
        raise SystemExit(f"FAIL: unexpected pypdf license metadata: {expression!r}")
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with tempfile.TemporaryDirectory(prefix="qikvrt-pypdf-compat-") as temporary:
        pdf = Path(temporary) / "smoke.pdf"
        with pdf.open("wb") as handle:
            writer.write(handle)
        document = walkpdf.pyobj(filename=str(pdf))
    pages = document.get("Page")
    if not isinstance(pages, list) or len(pages) != 1:
        raise SystemExit("FAIL: xml2rfc.walkpdf did not inspect exactly one page")
    print("PASS: pypdf 6.15.0 metadata/license and xml2rfc 3.34.0 walkpdf compatibility surface verified")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
