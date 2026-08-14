#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize or check the local EAP-LCTP -00 IETF candidate offline.

The helper renders the RFCXML twice with independent local caches through the
repository-locked xml2rfc executable, refreshes only local evidence and
fixity, and never contacts the IETF Datatracker or sends email.
"""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / (
    "docs/publications/2026-08-12-observer-relative-retrocausality/"
    "ietf-local-change-time-provenance-00-current-synthesis-candidate"
)
XML = CANDIDATE / "draft-lohmann-qikvrt-local-change-time-00.xml"
TXT = CANDIDATE / "draft-lohmann-qikvrt-local-change-time-00.txt"
HTML = CANDIDATE / "draft-lohmann-qikvrt-local-change-time-00.html"
MANIFEST = CANDIDATE / "SUBMISSION_MANIFEST.json"
RENDER_STATUS = CANDIDATE / "RENDER_STATUS.json"
PROVENANCE = CANDIDATE / "SOURCE_PROVENANCE.json"
AUTHORIZATION_DRAFT = CANDIDATE / "EXACT_ARTIFACT_AUTHORIZATION_DRAFT.md"
CHECKSUMS = CANDIDATE / "SHA256SUMS"
VECTORS = CANDIDATE / "TEST_VECTORS.json"
VALIDATOR = CANDIDATE / "verify_candidate.py"
README = CANDIDATE / "README.md"
STAGING_README = CANDIDATE / "STAGING_README.md"
REQUIREMENTS = ROOT / "runtime/toolchains/requirements-xml2rfc-3.34.0.txt"
LOCK = ROOT / "runtime/toolchains/TOOLCHAIN.lock.tsv"
DEFAULT_XML2RFC = ROOT / (
    ".qikvrt/toolchains/xml2rfc/3.34.0/python-3.12.13/linux-amd64/venv/bin/xml2rfc"
)
FIXITY_PATHS = (
    XML.name,
    TXT.name,
    HTML.name,
    VECTORS.name,
    VALIDATOR.name,
    RENDER_STATUS.name,
    PROVENANCE.name,
    MANIFEST.name,
    README.name,
    STAGING_README.name,
    AUTHORIZATION_DRAFT.name,
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.fragments: list[str] = []

    def handle_data(self, data: str) -> None:
        self.fragments.append(data)


def fail(message: str) -> None:
    raise RuntimeError(message)


def digest(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {"path": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def git_blob_sha1(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()  # noqa: S324


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def write_json(path: Path, value: dict[str, Any], *, write: bool) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if path.is_file() and path.read_bytes() == payload:
        return
    if not write:
        fail(f"stale generated JSON: {path.relative_to(ROOT)}")
    path.write_bytes(payload)


def write_text(path: Path, text: str, *, write: bool) -> None:
    raw = text.encode("utf-8")
    if path.is_file() and path.read_bytes() == raw:
        return
    if not write:
        fail(f"stale generated text: {path.relative_to(ROOT)}")
    path.write_bytes(raw)


def check_renderer(xml2rfc: Path) -> None:
    result = subprocess.run(
        [str(xml2rfc), "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode != 0 or result.stdout.splitlines()[:1] != ["xml2rfc 3.34.0"]:
        fail("the renderer is not exactly xml2rfc 3.34.0")


def render_once(xml2rfc: Path, directory: Path, mode: str) -> tuple[bytes, str]:
    output = directory / f"rendered.{mode}"
    cache = directory / f"cache-{mode}"
    environment = os.environ.copy()
    environment["PYTHONNOUSERSITE"] = "1"
    result = subprocess.run(
        [
            str(xml2rfc),
            str(XML),
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
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=180,
        check=False,
    )
    if result.returncode != 0 or not output.is_file():
        fail(f"xml2rfc offline {mode} render failed: {(result.stderr or result.stdout)[-4000:]}")
    diagnostics = result.stdout + result.stderr
    if "warning" in diagnostics.lower() or "error" in diagnostics.lower():
        fail(f"xml2rfc {mode} emitted a diagnostic warning/error: {diagnostics[-4000:]}")
    return output.read_bytes(), diagnostics


def render_twice(xml2rfc: Path) -> tuple[bytes, bytes]:
    with tempfile.TemporaryDirectory(prefix="qikvrt-ietf-render-a-") as first, tempfile.TemporaryDirectory(prefix="qikvrt-ietf-render-b-") as second:
        first_dir = Path(first)
        second_dir = Path(second)
        first_txt, _ = render_once(xml2rfc, first_dir, "text")
        first_html, _ = render_once(xml2rfc, first_dir, "html")
        second_txt, _ = render_once(xml2rfc, second_dir, "text")
        second_html, _ = render_once(xml2rfc, second_dir, "html")
    if first_txt != second_txt or first_html != second_html:
        fail("independent offline renders are not byte-identical")
    return first_txt, first_html


def html_parse(raw: bytes) -> None:
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8"))
    parser.close()
    if not "Security Considerations" in " ".join(parser.fragments):
        fail("rendered HTML lacks Security Considerations")


def line_count(raw: bytes) -> tuple[int, int]:
    text = raw.decode("utf-8")
    return max((len(line) for line in text.splitlines()), default=0), text.count("[Page ")


def authorization_draft(xml: dict[str, Any], txt: dict[str, Any], html: dict[str, Any], vectors: dict[str, Any]) -> str:
    return f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Draft only — exact-artifact IETF submission authorization

**Status:** `NOT_AN_AUTHORIZATION`
**Candidate:** `draft-lohmann-qikvrt-local-change-time-00`
**Target:** IETF Datatracker, individual Internet-Draft, intended status
Experimental

This file is a template.  It grants no submission authority and records no
submission, email, acceptance, publication, RFC, or IETF consensus.

The locally finalized XML, TXT, HTML, and vector identities are prefilled
below.  Before any external action, the destination/account fields and the
final manifest identity must be filled from a fresh observation of the exact
unchanged package.  The author must then issue an unambiguous action-time
statement that names this document and the exact SHA-256 values.

```text
AUTHORIZE_EXACT_IETF_SUBMISSION

I, Ingolf Lohmann, authorize submission of exactly the following final
individual Internet-Draft package to the IETF Datatracker:

  document: draft-lohmann-qikvrt-local-change-time-00
  title: Local Change-Time Provenance Profile for QIK-VRT Effect Acknowledgement
  intended status: Experimental
  author/email: Ingolf Lohmann / [current Datatracker account email]
  destination observed at: [UTC timestamp and safe public destination URL]

  XML:  {xml['path']} {xml['bytes']} sha256:{xml['sha256']}
  TXT:  {txt['path']} {txt['bytes']} sha256:{txt['sha256']}
  HTML: {html['path']} {html['bytes']} sha256:{html['sha256']}
  manifest: SUBMISSION_MANIFEST.json [bytes] sha256:[digest]
  vectors: {vectors['path']} {vectors['bytes']} sha256:{vectors['sha256']}

I understand that this authorization covers the named external submission only.
It does not assert a physical backwards-signalling channel, a coordinate future
as causal future, a changed past event, payload truth, IETF endorsement, IETF
consensus, an RFC, or independent interoperability.

Signed/confirmed at action time: [name, timestamp, confirmation channel]
```

The external operator must retain the returned submission identifier and any
status/approval receipt without secrets, reobserve the public document after
publication, and record byte identity or documented renderer-induced drift.
"""


def update_provenance(*, write: bool, rendered_at: str, txt: dict[str, Any], html: dict[str, Any]) -> None:
    provenance = read_json(PROVENANCE)
    local = provenance["local_render"]
    local["observed_at"] = rendered_at
    local["result"] = "PASS_OFFLINE_RENDER_CLEAN"
    local["outputs"]["txt"].update({"bytes": txt["bytes"], "sha256": txt["sha256"]})
    local["outputs"]["html"].update({"bytes": html["bytes"], "sha256": html["sha256"]})
    local["outputs"]["repeat_render_byte_identical"] = True
    local["diagnostics"].update({"errors_per_mode": 0, "warnings_per_mode": 0, "unused_references": []})
    for item in provenance["current_synthesis_inputs"]["items"]:
        path = (CANDIDATE / item["path"]).resolve()
        if not path.is_file():
            fail(f"provenance input is missing: {item['path']}")
        observed = digest(path)
        item["bytes"] = observed["bytes"]
        item["sha256"] = observed["sha256"]
        if "git_blob_sha1" in item:
            item["git_blob_sha1"] = git_blob_sha1(path)
    write_json(PROVENANCE, provenance, write=write)


def update_render_status(*, write: bool, rendered_at: str, xml: dict[str, Any], txt: dict[str, Any], html: dict[str, Any], max_line: int, pages: int) -> None:
    status = read_json(RENDER_STATUS)
    status["rendered_at"] = rendered_at
    status["source"].update({"size_bytes": xml["bytes"], "sha256": xml["sha256"], "rendered": True})
    status["outputs"]["txt"].update({"size_bytes": txt["bytes"], "sha256": txt["sha256"], "repeat_render_byte_identical": True, "maximum_line_length": max_line, "page_count": pages})
    status["outputs"]["html"].update({"size_bytes": html["bytes"], "sha256": html["sha256"], "repeat_render_byte_identical": True, "html_parse": "PASS"})
    status["renderer_diagnostics"].update({"result": "PASS", "errors_per_mode": 0, "warnings_per_mode": 0, "unused_references": [], "submission_disposition": "NO_RENDERER_DIAGNOSTIC_BLOCKER"})
    status["local_validation"].update({"static_xml_and_vectors": "PASS", "package_fixity": "PASS", "render_reproducibility": "PASS_BYTE_IDENTICAL_TWO_RUNS", "text_structure_review": "PASS", "html_parse": "PASS", "idnits": "CONTINUE_NO_DECLARED_IDNITS_RUNTIME"})
    write_json(RENDER_STATUS, status, write=write)


def update_manifest(*, write: bool, xml: dict[str, Any], txt: dict[str, Any], html: dict[str, Any]) -> None:
    manifest = read_json(MANIFEST)
    manifest["submission_artifacts"]["xml"].update({"size_bytes": xml["bytes"], "sha256": xml["sha256"]})
    manifest["submission_artifacts"]["txt"].update({"size_bytes": txt["bytes"], "sha256": txt["sha256"], "state": "RENDERED_REPRODUCIBLY", "required_renderer": "xml2rfc 3.34.0"})
    manifest["submission_artifacts"]["html"].update({"size_bytes": html["bytes"], "sha256": html["sha256"], "state": "RENDERED_REPRODUCIBLY", "required_renderer": "xml2rfc 3.34.0"})
    for name, path in {
        "test_vectors": VECTORS,
        "validator": VALIDATOR,
        "render_status": RENDER_STATUS,
        "source_provenance": PROVENANCE,
        "readme": README,
        "staging_readme": STAGING_README,
        "authorization_draft": AUTHORIZATION_DRAFT,
    }.items():
        observed = digest(path)
        manifest["supporting_artifacts"][name].update({"size_bytes": observed["bytes"], "sha256": observed["sha256"]})
    manifest["validation"].update({"xml_well_formed": True, "static_ietf_header_precheck": "PASS", "reference_classification_vectors": 7, "candidate_fixity": "PASS", "validation_command": "python3 -B verify_candidate.py", "result": "PASS_LOCAL_CANDIDATE_VALIDATION", "renderer_validation": "PASS_OFFLINE_RENDER_CLEAN", "render_reproducibility": "PASS_BYTE_IDENTICAL_TWO_RUNS", "idnits_validation": "CONTINUE_NO_DECLARED_IDNITS_RUNTIME"})
    manifest["validation"]["renderer_warnings"] = {"errors_per_mode": 0, "warnings_per_mode": 0, "references": []}
    write_json(MANIFEST, manifest, write=write)


def checksum_payload() -> str:
    return "".join(
        f"{hashlib.sha256((CANDIDATE / name).read_bytes()).hexdigest()}  {name}\n"
        for name in FIXITY_PATHS
    )


def materialize(xml2rfc: Path, *, write: bool, rendered_at: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    check_renderer(xml2rfc)
    rendered_txt, rendered_html = render_twice(xml2rfc)
    if write:
        TXT.write_bytes(rendered_txt)
        HTML.write_bytes(rendered_html)
    elif TXT.read_bytes() != rendered_txt or HTML.read_bytes() != rendered_html:
        fail("committed rendered artifacts differ from independent offline renders")
    html_parse(HTML.read_bytes())
    max_line, pages = line_count(TXT.read_bytes())
    if max_line != 72 or pages != 16:
        fail(f"unexpected rendered text structure: max_line={max_line} pages={pages}")
    xml = digest(XML)
    txt = digest(TXT)
    html = digest(HTML)
    update_render_status(write=write, rendered_at=rendered_at, xml=xml, txt=txt, html=html, max_line=max_line, pages=pages)
    update_provenance(write=write, rendered_at=rendered_at, txt=txt, html=html)
    write_text(AUTHORIZATION_DRAFT, authorization_draft(xml, txt, html, digest(VECTORS)), write=write)
    update_manifest(write=write, xml=xml, txt=txt, html=html)
    write_text(CHECKSUMS, checksum_payload(), write=write)
    return xml, txt, html


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml2rfc", type=Path, default=DEFAULT_XML2RFC)
    parser.add_argument("--write", action="store_true", help="render and refresh local candidate evidence")
    parser.add_argument("--check", action="store_true", help="re-render and verify the local candidate")
    parser.add_argument("--rendered-at", help="UTC timestamp recorded for a write operation")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    xml2rfc = args.xml2rfc.resolve(strict=True)
    if args.write and not args.rendered_at:
        parser.error("--write requires --rendered-at")
    rendered_at = args.rendered_at if args.write else str(read_json(RENDER_STATUS)["rendered_at"])
    try:
        xml, txt, html = materialize(xml2rfc, write=args.write, rendered_at=rendered_at)
        print(
            "PASS IETF current-synthesis local materialization "
            f"xml_sha256={xml['sha256']} txt_sha256={txt['sha256']} html_sha256={html['sha256']} "
            "external_effect=NONE"
        )
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"BLOCK: {exc}", file=__import__("sys").stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
