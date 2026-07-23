#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Publish the machine-verifiable-science charter through the hardened Zenodo client."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
from typing import Any

from tools import qikvrt_zenodo_actions as zenodo

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUEST = ROOT / "release/machine-verifiable-science/publish-request.json"
ARTIFACT = ROOT / "docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md"
EVIDENCE = ROOT / "release/machine-verifiable-science/zenodo-publication.json"
SCHEMA = "qikvrt_machine_verifiable_science_publish_request_v1"
TITLE = "Charta einer maschinenprüfbaren Wissenschaft"
VERSION = "1.0.0-2026-07-23"


def fail(message: str) -> "NoReturn":
    raise zenodo.ZenodoError(message)


def load_request() -> dict[str, Any]:
    value, _ = zenodo._load_json_file(REQUEST)
    if set(value) != {"schema", "state", "confirm", "artifact", "expected_repository"}:
        fail("publish request keys differ from the closed contract")
    if value["schema"] != SCHEMA:
        fail("unsupported publish request schema")
    if value["state"] != "publish" or value["confirm"] != "PUBLISH_TO_PRODUCTION_ZENODO":
        fail("production publication is not explicitly authorized")
    if value["artifact"] != ARTIFACT.relative_to(ROOT).as_posix():
        fail("publish request artifact differs from the fixed charter path")
    if value["expected_repository"] != "Goldkelch/qik-vrt":
        fail("publish request repository differs from the authority repository")
    return value


def entry_for(path: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    data = zenodo.read_regular_file(path, zenodo.MAX_UPLOAD_BYTES)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "name": path.name,
        "size": len(data),
        "md5": hashlib.md5(data).hexdigest(),  # noqa: S324 - Zenodo transport checksum
        "sha256": hashlib.sha256(data).hexdigest(),
    }, data


def metadata() -> dict[str, Any]:
    return {
        "title": TITLE,
        "upload_type": "publication",
        "publication_type": "technicalnote",
        "description": (
            "Charta und Architekturgrundprinzipien für eine transparente, "
            "maschinenlesbare, reproduzierbare und revisionsfähige wissenschaftliche Wissensbasis."
        ),
        "creators": [{"name": "Lohmann, Ingolf"}],
        "version": VERSION,
        "publication_date": "2026-07-23",
        "access_right": "open",
        "license": "cc-by-nc-nd-4.0",
        "language": "deu",
        "keywords": [
            "maschinenprüfbare Wissenschaft",
            "Reproduzierbarkeit",
            "Provenienz",
            "QIK-VRT",
            "wissenschaftliche Infrastruktur",
            "kollaborative Kognition"
        ],
        "related_identifiers": [
            {
                "identifier": "https://github.com/Goldkelch/qik-vrt/blob/main/AI",
                "relation": "isSupplementTo",
                "scheme": "url"
            },
            {
                "identifier": "https://github.com/Goldkelch/qik-vrt",
                "relation": "isDocumentedBy",
                "scheme": "url"
            }
        ],
        "prereserve_doi": True
    }


def find_existing(client: zenodo.ZenodoClient) -> dict[str, Any] | None:
    status, value = client.get("/api/deposit/depositions", accept=(200,))
    if status != 200:
        return None
    items = value if isinstance(value, list) else value.get("hits", {}).get("hits", [])
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata")
        if isinstance(meta, dict) and meta.get("title") == TITLE and meta.get("version") == VERSION:
            return item
    return None


def main() -> int:
    try:
        load_request()
        token = os.environ.get(zenodo.TOKEN_ENVIRONMENT_VARIABLE, "")
        client = zenodo.ZenodoClient(token, os.environ.get("ZENODO_API_BASE", zenodo.DEFAULT_BASE_URL))
        item, data = entry_for(ARTIFACT)
        meta = metadata()
        existing = find_existing(client)
        if existing is None:
            draft = client.create_paper(meta)
        else:
            draft = existing
        record_id = zenodo._record_id(draft, "charter deposition")
        doi = zenodo._doi_from_deposition(draft, "charter deposition")
        verified = {("paper", item["name"]): data}
        state = client.prepare_draft("paper", record_id, meta, [item], verified, doi)
        published = client.publish_and_poll(record_id, meta, [item], doi, state == "published")
        links = published.get("links") if isinstance(published.get("links"), dict) else {}
        evidence = {
            "schema": "qikvrt_machine_verifiable_science_zenodo_evidence_v1",
            "state": "published",
            "record_id": record_id,
            "doi": doi,
            "conceptdoi": published.get("conceptdoi") or published.get("metadata", {}).get("conceptdoi"),
            "artifact": item,
            "title": TITLE,
            "version": VERSION,
            "record_url": links.get("html") or f"https://zenodo.org/records/{record_id}",
            "repository_commit": os.environ.get("GITHUB_SHA", "unavailable")
        }
        zenodo._atomic_json(EVIDENCE, evidence, token)
        print(f"ZENODO_PUBLICATION_STATE=published")
        print(f"ZENODO_RECORD_ID={record_id}")
        print(f"ZENODO_DOI={doi}")
        return 0
    except zenodo.ZenodoError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
