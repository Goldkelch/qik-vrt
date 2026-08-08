#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Focused compatibility smoke for the pypdf APIs consumed by xml2rfc 3.34.0."""
from __future__ import annotations
import importlib.metadata as metadata
from pathlib import Path
import sys
import tempfile
import types
import pypdf
from pypdf.generic import ContentStream

# xml2rfc 3.34.0 declares dict2xml only in its tests extra, while walkpdf
# imports it at module load. This smoke exercises only walkpdf.pyobj's pypdf
# surface, so keep the renderer lock unchanged and fail closed if the unrelated
# XML-serialization helper is ever reached by this path.
dict2xml_shim = types.ModuleType("dict2xml")
def _unexpected_dict2xml(*args: object, **kwargs: object) -> object:
    raise RuntimeError("dict2xml test shim must not be used by walkpdf.pyobj")
dict2xml_shim.dict2xml = _unexpected_dict2xml
sys.modules.setdefault("dict2xml", dict2xml_shim)

from xml2rfc import walkpdf

def main() -> int:
    if metadata.version("pypdf") != "6.15.0":
        raise SystemExit("FAIL: pypdf metadata is not exactly 6.15.0")
    md = metadata.metadata("pypdf")
    expression = md.get("License-Expression") or md.get("License") or ""
    if "BSD-3-Clause" not in expression:
        raise SystemExit(f"FAIL: unexpected pypdf license metadata: {expression!r}")
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=72, height=72)
    # walkpdf.pyobj exercises layout-mode text extraction, which requires a
    # real /Contents entry. Keep the fixture semantically blank while attaching
    # an empty content stream through pypdf's page API rather than weakening the
    # compatibility check or adding a runtime dependency.
    page.replace_contents(ContentStream(None, writer))
    with tempfile.TemporaryDirectory(prefix="qikvrt-pypdf-compat-") as temporary:
        pdf = Path(temporary) / "smoke.pdf"
        with pdf.open("wb") as handle:
            writer.write(handle)
        document = walkpdf.pyobj(filename=str(pdf))
    pages = document.get("Page")
    if not isinstance(pages, list) or len(pages) != 1:
        raise SystemExit("FAIL: xml2rfc.walkpdf did not inspect exactly one page")
    print("PASS: pypdf 6.15.0 metadata/license and xml2rfc 3.34.0 walkpdf.pyobj compatibility surface verified")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
