#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Render Draft-01 offline and verify the documented TXT/HTML identities."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/publications/2026-07-22-effect-ack-universal-effect-control"
REPORT = BUNDLE / "IETF_RENDER_VALIDATION.json"
INPUTS = BUNDLE / "inputs"


def digest(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def run_renderer(xml2rfc: Path, source: Path, output: Path, cache: Path, mode: str) -> None:
    command = [
        str(xml2rfc),
        str(source),
        "--v3",
        f"--{mode}",
        "--no-network",
        "--skip-config-files",
        "--warn-bare-unicode",
        "--cache",
        str(cache),
        "--verbose",
        "--out",
        str(output),
    ]
    environment = os.environ.copy()
    environment["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=180,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "FAIL: xml2rfc offline render failed "
            f"for {mode} with exit {completed.returncode}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml2rfc", type=Path, required=True)
    args = parser.parse_args()

    xml2rfc = args.xml2rfc.resolve(strict=True)
    require(xml2rfc.is_file(), "--xml2rfc is not a regular file")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    require(report["result"] == "PASS", "render report is not PASS")
    require(
        report["draft"]["datatracker_submission_performed"] is False,
        "render report claims a Datatracker submission",
    )
    require(
        report["toolchain"]["network_access"] is False,
        "render report does not require offline operation",
    )
    require(
        report["validation"]["prepped_xml"]["digest_claimed"] is False,
        "timestamp-dependent prepped XML bytes are incorrectly claimed",
    )

    version = subprocess.run(
        [str(xml2rfc), "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    require(version.returncode == 0, "xml2rfc --version failed")
    require(
        version.stdout.splitlines()[:1] == ["xml2rfc 3.34.0"],
        "renderer is not exactly xml2rfc 3.34.0",
    )

    xml_record = report["artifacts"]["xml"]
    txt_record = report["artifacts"]["txt"]
    html_record = report["artifacts"]["html"]
    source = INPUTS / xml_record["filename"]
    committed_txt = INPUTS / txt_record["filename"]
    require(
        digest(source) == (xml_record["sha256"], xml_record["size_bytes"]),
        "Draft-01 XML identity differs from the validation report",
    )
    require(
        digest(committed_txt) == (txt_record["sha256"], txt_record["size_bytes"]),
        "committed Draft-01 TXT identity differs from the validation report",
    )

    with tempfile.TemporaryDirectory(prefix="qikvrt-ietf-offline-render-") as temporary:
        scratch = Path(temporary)
        cache = scratch / "cache"
        cache.mkdir()
        rendered_txt = scratch / txt_record["filename"]
        rendered_html = scratch / html_record["filename"]
        run_renderer(xml2rfc, source, rendered_txt, cache, "text")
        run_renderer(xml2rfc, source, rendered_html, cache, "html")

        require(
            digest(rendered_txt) == (txt_record["sha256"], txt_record["size_bytes"]),
            "fresh offline TXT render differs from the documented identity",
        )
        require(
            rendered_txt.read_bytes() == committed_txt.read_bytes(),
            "fresh offline TXT render is not byte-identical to the committed input",
        )
        require(
            digest(rendered_html)
            == (html_record["sha256"], html_record["size_bytes"]),
            "fresh offline HTML render differs from the documented clean identity",
        )

    print(
        "PASS: xml2rfc 3.34.0 offline TXT/HTML render matches documented SHA-256; "
        "no prepped-byte or Datatracker effect claimed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
