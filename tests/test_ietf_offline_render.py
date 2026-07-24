#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Render Draft-01 offline and verify the version-bound published identities."""

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
REQUIREMENTS = ROOT / "runtime/toolchains/requirements-xml2rfc-3.34.0.txt"


def digest(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


def digest_bytes(payload: bytes) -> tuple[str, int]:
    return hashlib.sha256(payload).hexdigest(), len(payload)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def locked_requirement_version(package: str) -> str:
    prefix = f"{package}=="
    versions: list[str] = []
    for raw in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith(prefix):
            continue
        versions.append(line[len(prefix) :].split()[0].rstrip("\\"))
    require(
        len(versions) == 1 and bool(versions[0]),
        f"requirements do not declare exactly one {package} version",
    )
    return versions[0]


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


def verify_html_identity(
    rendered_html: Path,
    html_record: dict[str, object],
    historical_pypdf: str,
    locked_pypdf: str,
) -> None:
    documented = (str(html_record["sha256"]), int(html_record["size_bytes"]))
    payload = rendered_html.read_bytes()
    if locked_pypdf == historical_pypdf:
        require(
            digest_bytes(payload) == documented,
            "fresh offline HTML render differs from the documented clean identity",
        )
        return

    current_line = f"    pypdf {locked_pypdf}\n".encode("utf-8")
    historical_line = f"    pypdf {historical_pypdf}\n".encode("utf-8")
    require(
        payload.count(current_line) == 1,
        "fresh HTML does not contain exactly one locked pypdf generator line",
    )
    require(
        payload.count(historical_line) == 0,
        "fresh HTML unexpectedly contains the historical pypdf generator line",
    )
    normalized = payload.replace(current_line, historical_line, 1)
    require(
        digest_bytes(normalized) == documented,
        "fresh HTML differs from the published identity beyond the exact pypdf generator-version line",
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

    historical_pypdf = str(report["toolchain"]["pypdf"])
    locked_pypdf = locked_requirement_version("pypdf")
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
        verify_html_identity(
            rendered_html,
            html_record,
            historical_pypdf,
            locked_pypdf,
        )

    print(
        "PASS: xml2rfc 3.34.0 offline TXT matches the published SHA-256; "
        f"HTML under locked pypdf {locked_pypdf} reconstructs the published "
        f"pypdf {historical_pypdf} identity after exact generator-line normalization; "
        "no prepped-byte or Datatracker effect claimed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
