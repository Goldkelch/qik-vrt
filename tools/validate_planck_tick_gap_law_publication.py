#!/usr/bin/env python3
"""Fail-closed local validation for the Planck-tick gap-law publication source.

This closes the gap that allowed a successful pdfLaTeX exit status to stand in
for publication/render validation. It rejects TeX warnings that can correspond
to clipped output and checks the frozen low-energy remainder across the human
and machine-readable representations.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TEX = ROOT / "docs/research/2026-09-03-planck-tick-gap-law/QIKVRT_Planck_Tick_Gap_Law_2026-09-03.tex"
CONTRACT = ROOT / "physics/planck_tick_gap_law_v1.json"
FORBIDDEN_LOG = (
    "Overfull \\hbox",
    "Overfull \\vbox",
    "LaTeX Warning: There were undefined references",
    "LaTeX Warning: There were undefined citations",
    "Package fancyhdr Warning: \\headheight is too small",
)
EXPECTED_MACHINE_REMAINDER = "O(DeltaE^5/(hbar*EP^4))"
EXPECTED_TEX_REMAINDER = r"O\!\left(\frac{\dE^5}{\hbar\EP^4}\right)"


def fail(message: str) -> None:
    raise SystemExit("PLANCK_TICK_PUBLICATION_VALIDATION_FAILED: " + message)


def main() -> None:
    if shutil.which("pdflatex") is None:
        fail("pdflatex is required; render validation may not be skipped")
    source = TEX.read_text(encoding="utf-8")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if EXPECTED_TEX_REMAINDER not in source:
        fail("human manuscript does not contain the dimensional fifth-order remainder")
    if EXPECTED_MACHINE_REMAINDER not in contract["derived_prediction"]["low_energy_expansion"]:
        fail("machine contract does not contain the dimensional fifth-order remainder")

    with tempfile.TemporaryDirectory(prefix="qikvrt-planck-tick-render-") as tmp:
        directory = Path(tmp)
        target = directory / TEX.name
        target.write_bytes(TEX.read_bytes())
        for _ in range(2):
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", target.name],
                cwd=directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
                check=False,
            )
            if result.returncode != 0:
                fail("pdfLaTeX returned non-zero")
        log = target.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
        for marker in FORBIDDEN_LOG:
            if marker in log:
                fail(f"forbidden TeX diagnostic: {marker}")
        if re.search(r"Overfull \\hbox", log):
            fail("overfull horizontal box detected")
        pdf = target.with_suffix(".pdf")
        if not pdf.is_file() or pdf.stat().st_size == 0:
            fail("non-empty PDF was not produced")
    print("PLANCK_TICK_PUBLICATION_VALIDATION=PASS_LOCAL_RENDER_AND_CROSS_ARTIFACT")


if __name__ == "__main__":
    main()
