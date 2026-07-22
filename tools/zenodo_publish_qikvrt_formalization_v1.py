#!/usr/bin/env python3
"""Fail-closed one-shot publisher for QIK-VRT Formalization v1.0.0.

The access token is read only from ZENODO_ACCESS_TOKEN and is transmitted only
as an HTTPS Authorization header to zenodo.org. It is never printed, written to
disk, placed in a URL, or copied into the non-secret publication receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "formalization/QIKVRT_Formalization_v1.0"
METADATA_PATH = PROJECT / "zenodo_deposition_metadata_v1.0.0.json"
RECEIPT_PATH = ROOT / "zenodo-formalization-publication-receipt.json"
API_BASE = "https://zenodo.org/api"
EXPECTED_TITLE = "QIK-VRT: Vollständige maschinenprüfbare Formalisierung des formal entscheidbaren Kerns"
MAX_RESPONSE = 16 * 1024 * 1024

EXPECTED_FILES = {
    "QIKVRT_Formalization_v1.0_2026-07-22.zip": {
        "path": PROJECT / "release/QIKVRT_Formalization_v1.0_2026-07-22.zip",
        "size": 697667,
        "sha256": "d1a7ebc3abbfa0bb107f82ac24d4c740940944ee7f381961e51d7f617c9e46a5",
        "md5": "f457de92d4c77b3aa348d4cb7fe67f33",
    },
    "README.md": {
        "path": PROJECT / "README.md",
        "size": 4258,
        "sha256": "ebab3bf5da6839e212fe7f47135d3da5a97e4df0cb68e25f188e3e9123c47633",
        "md5": "f5b74e3f085814358e803a896f86b30d",
    },
    "FORMALIZATION_BOUNDARY.md": {
        "path": PROJECT / "FORMALIZATION_BOUNDARY.md",
        "size": 4100,
        "sha256": "a4889f49a5aa7ee7bfbfe8dfece81c07925483c3e13384695afa0901189889bb",
        "md5": "561af9cce42b7f4b8d92270c3b2cf2e6",
    },
    "SHA256SUMS": {
        "path": PROJECT / "SHA256SUMS",
        "size": 3778,
        "sha256": "08c753071e1e9bbd42e0d76320206514824f5274bd8134b3d3e539c4a0873f26",
        "md5": "b7bb71fd66747d502fa77fcae32fa62b",
    },
    "CITATION.cff": {
        "path": PROJECT / "CITATION.cff",
        "size": 824,
        "sha256": "849b3f97be1c038848254201972ecc33fbaf32baba0e39ca9cdce635ccd8a9c0",
        "md5": "d7d840ab394deeca8367d009b930a431",
    },
    "lean-verification.json": {
        "path": PROJECT / "build/lean-verification.json",
        "size": 457,
        "sha256": "3c0e1b741544cce11fff9e6f5f58ea124af584ac7b6d37d3cb389f09b9afc35f",
        "md5": "04972a586159bc28063c1ac4f7a2bb8b",
    },
    "gate20-report.json": {
        "path": PROJECT / "build/gate20-report.json",
        "size": 3197,
        "sha256": "5b31d109a78a846aec3ad2bcb6169d7bbdebcb7e414e766b8c4bbe5f602847e3",
        "md5": "cb24567ea0aeded4341db70f37870a25",
    },
    "gate20-python-report.json": {
        "path": PROJECT / "build/gate20-python-report.json",
        "size": 2472,
        "sha256": "02fa34f43d34b32bdaccd2da186a734af1dd896eb7d49b6077c3951c26d81668",
        "md5": "60d7e74eef09192c310e0d593711878b",
    },
}


class Blocked(RuntimeError):
    pass


def digest(path: Path, algorithm: str) -> str:
    value = hashlib.md5(usedforsecurity=False) if algorithm == "md5" else hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def local_facts() -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for name, expected in EXPECTED_FILES.items():
        path = expected["path"]
        if not path.is_file() or path.is_symlink():
            raise Blocked(f"missing regular publication file: {name}")
        actual = {
            "name": name,
            "path": path,
            "size": path.stat().st_size,
            "sha256": digest(path, "sha256"),
            "md5": digest(path, "md5"),
        }
        for key in ("size", "sha256", "md5"):
            if actual[key] != expected[key]:
                raise Blocked(f"local {key} verification failed: {name}")
        facts.append(actual)
    return facts


def load_payload() -> dict[str, Any]:
    try:
        payload = json.loads(METADATA_PATH.read_text("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise Blocked("cannot load Zenodo metadata") from None
    metadata = payload.get("metadata") if isinstance(payload, dict) else None
    if not isinstance(metadata, dict):
        raise Blocked("invalid Zenodo metadata shape")
    required = {
        "title": EXPECTED_TITLE,
        "upload_type": "software",
        "publication_date": "2026-07-22",
        "version": "1.0.0",
        "language": "deu",
        "access_right": "open",
        "license": "other-open",
        "prereserve_doi": True,
    }
    for key, value in required.items():
        if metadata.get(key) != value:
            raise Blocked(f"Zenodo metadata mismatch: {key}")
    creators = metadata.get("creators")
    if not isinstance(creators, list) or not creators or creators[0].get("name") != "Lohmann, Ingolf":
        raise Blocked("approved creator metadata missing")
    related = metadata.get("related_identifiers")
    expected_relation = {
        "identifier": "10.5281/zenodo.21482023",
        "relation": "isSupplementTo",
        "scheme": "doi",
        "resource_type": "publication-workingpaper",
    }
    if not isinstance(related, list) or expected_relation not in related:
        raise Blocked("source DOI relationship missing")
    if "d1a7ebc3abbfa0bb107f82ac24d4c740940944ee7f381961e51d7f617c9e46a5" not in metadata.get("description", ""):
        raise Blocked("approved release hash missing from description")
    return payload


def access_token() -> str:
    value = os.environ.get("ZENODO_ACCESS_TOKEN", "")
    if not value or value.strip() != value or len(value) < 20:
        raise Blocked("ZENODO_ACCESS_TOKEN is missing or malformed")
    return value


def checked_url(url: str, *, api: bool = True) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "zenodo.org":
        raise Blocked("refusing non-Zenodo or non-HTTPS URL")
    if api and not parsed.path.startswith("/api/"):
        raise Blocked("refusing unexpected Zenodo API path")
    return url


def json_request(method: str, url: str, token: str | None, body: Any = None,
                 expected: tuple[int, ...] = (200,)) -> dict[str, Any]:
    checked_url(url)
    raw = None
    headers = {"Accept": "application/json", "User-Agent": "QIK-VRT-Formalization-Zenodo/1.0.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=raw, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120, context=ssl.create_default_context()) as response:
            data = response.read(MAX_RESPONSE + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        raise Blocked(f"Zenodo API returned HTTP {exc.code} for {method}") from None
    except (urllib.error.URLError, TimeoutError):
        raise Blocked(f"Zenodo API connection failed for {method}") from None
    if status not in expected or len(data) > MAX_RESPONSE:
        raise Blocked(f"unexpected Zenodo response for {method}")
    if not data:
        return {}
    try:
        result = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise Blocked("Zenodo returned invalid JSON") from None
    if not isinstance(result, dict):
        raise Blocked("Zenodo returned unexpected JSON shape")
    return result


def upload_file(bucket_url: str, fact: dict[str, Any], token: str) -> None:
    target = checked_url(bucket_url.rstrip("/") + "/" + urllib.parse.quote(fact["name"], safe=""))
    request = urllib.request.Request(
        target,
        data=Path(fact["path"]).read_bytes(),
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/octet-stream",
            "User-Agent": "QIK-VRT-Formalization-Zenodo/1.0.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=240, context=ssl.create_default_context()) as response:
            response.read(MAX_RESPONSE + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        raise Blocked(f"Zenodo upload returned HTTP {exc.code}: {fact['name']}") from None
    except (urllib.error.URLError, TimeoutError):
        raise Blocked(f"Zenodo upload failed: {fact['name']}") from None
    if status not in (200, 201):
        raise Blocked(f"unexpected upload status: {fact['name']}")


def file_entries(value: dict[str, Any]) -> list[dict[str, Any]]:
    files = value.get("files")
    if isinstance(files, list):
        return [item for item in files if isinstance(item, dict)]
    if isinstance(files, dict):
        entries = files.get("entries")
        if isinstance(entries, list):
            return [item for item in entries if isinstance(item, dict)]
    return []


def verify_listing(value: dict[str, Any], facts: list[dict[str, Any]]) -> None:
    by_name: dict[str, dict[str, Any]] = {}
    for entry in file_entries(value):
        name = entry.get("filename") or entry.get("key")
        if isinstance(name, str):
            by_name[name] = entry
    expected_names = {fact["name"] for fact in facts}
    if set(by_name) != expected_names:
        raise Blocked("remote file set differs from approved release")
    for fact in facts:
        entry = by_name[fact["name"]]
        size = entry.get("filesize", entry.get("size", -1))
        if int(size) != fact["size"]:
            raise Blocked(f"remote size mismatch: {fact['name']}")
        checksum = entry.get("checksum")
        if isinstance(checksum, str) and checksum.split(":", 1)[-1].lower() != fact["md5"]:
            raise Blocked(f"remote checksum mismatch: {fact['name']}")


def reserved_doi(value: dict[str, Any]) -> str:
    metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
    pre = metadata.get("prereserve_doi") if isinstance(metadata, dict) else None
    if isinstance(pre, dict) and isinstance(pre.get("doi"), str):
        return pre["doi"]
    doi = value.get("doi")
    if isinstance(doi, str) and doi.startswith("10.5281/zenodo."):
        return doi
    raise Blocked("Zenodo did not expose a reserved DOI")


def prepare() -> dict[str, Any]:
    facts = local_facts()
    metadata = load_payload()["metadata"]
    return {
        "status": "PREPARED_NOT_PUBLISHED",
        "title": metadata["title"],
        "version": metadata["version"],
        "files": [{k: f[k] for k in ("name", "size", "sha256", "md5")} for f in facts],
    }


def publish() -> dict[str, Any]:
    facts = local_facts()
    payload = load_payload()
    token = access_token()
    created = json_request("POST", f"{API_BASE}/deposit/depositions", token, payload, (201,))
    record_id = created.get("id")
    if not isinstance(record_id, int) or record_id <= 0:
        raise Blocked("Zenodo returned invalid deposition id")
    links = created.get("links") if isinstance(created.get("links"), dict) else {}
    bucket = links.get("bucket")
    if not isinstance(bucket, str):
        raise Blocked("Zenodo did not return upload bucket")
    doi = reserved_doi(created)

    draft_receipt = {
        "status": "DRAFT_CREATED_NOT_YET_PUBLISHED",
        "record_id": record_id,
        "reserved_doi": doi,
        "draft_url": f"https://zenodo.org/uploads/{record_id}",
        "source_commit": os.environ.get("GITHUB_SHA"),
        "files": [{k: f[k] for k in ("name", "size", "sha256", "md5")} for f in facts],
    }
    RECEIPT_PATH.write_text(json.dumps(draft_receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")

    for fact in facts:
        upload_file(bucket, fact, token)
    draft = json_request("GET", f"{API_BASE}/deposit/depositions/{record_id}", token)
    verify_listing(draft, facts)
    if reserved_doi(draft) != doi:
        raise Blocked("reserved DOI changed before publication")

    published = json_request(
        "POST", f"{API_BASE}/deposit/depositions/{record_id}/actions/publish", token, expected=(202,)
    )
    if isinstance(published.get("doi"), str) and published["doi"] != doi:
        raise Blocked("published DOI differs from reservation")

    public: dict[str, Any] | None = None
    for _ in range(30):
        try:
            candidate = json_request("GET", f"{API_BASE}/records/{record_id}", None)
            metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
            if candidate.get("doi") == doi and metadata.get("title") == EXPECTED_TITLE:
                verify_listing(candidate, facts)
                public = candidate
                break
        except Blocked:
            pass
        time.sleep(3)
    if public is None:
        raise Blocked("record was published but public verification did not complete")

    receipt = {
        "status": "PUBLISHED_AND_PUBLICLY_VERIFIED",
        "record_id": record_id,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}",
        "record_url": f"https://zenodo.org/records/{record_id}",
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository": os.environ.get("GITHUB_REPOSITORY"),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "files": [{k: f[k] for k in ("name", "size", "sha256", "md5")} for f in facts],
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare() if args.prepare else publish()
    except Blocked as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
