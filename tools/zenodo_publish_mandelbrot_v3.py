#!/usr/bin/env python3
"""Fail-closed one-shot publisher for the QIK-VRT Mandelbrot V3 working paper.

The Zenodo token is read only from ``ZENODO_ACCESS_TOKEN`` and is sent only
as an HTTPS Authorization header to zenodo.org.  The token is never printed,
written to disk, embedded in a URL, or included in the publication receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_DIR = ROOT / "docs/publications/2026-07-21-mandelbrot-retrocausality"
METADATA_PATH = PUBLICATION_DIR / "zenodo_deposition_metadata_v3.0.json"
RECEIPT_PATH = ROOT / "zenodo-publication-receipt.json"
API_BASE = "https://zenodo.org/api"
EXPECTED_FILES = {
    "Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf": {
        "size": 601860,
        "sha256": "b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f",
    },
    "Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.tex": {
        "size": 154356,
        "sha256": "c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf",
    },
    "Mandelbrot_Komplement_Modelluniversum_Entscheidender_Unterschied_2026-07-21.bib": {
        "size": 21269,
        "sha256": "1994e495af8c3f85e9e85fb77346539855abec16ce8ec6d68a3d3ebe9b5957b8",
    },
    "README.md": {
        "size": 3695,
        "sha256": "e14d9d32ca585ee8ad0565908a69214a2f4b77e26675ae69605af07b72f54adb",
    },
    "SHA256SUMS": {
        "size": 428,
        "sha256": "995a13edf56ff5fe40845d34804300897d4b4017078ab1b6b5493bce2996b2c1",
    },
}
EXPECTED_TITLE = (
    "Mandelbrot-Menge, Anschlussordnung und physikalisches Modelluniversum – "
    "Komplementbeweis, rekursive Wirkungsklassifikation, dimensionsrichtige "
    "Raumzeitbrücke, Retrokausalität und der entscheidende Unterschied zur "
    "empirischen Quantengravitation"
)
MAX_RESPONSE = 16 * 1024 * 1024


class Blocked(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_facts() -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for name, expected in EXPECTED_FILES.items():
        path = PUBLICATION_DIR / name
        if not path.is_file() or path.is_symlink():
            raise Blocked(f"missing regular publication file: {name}")
        size = path.stat().st_size
        sha256 = sha256_file(path)
        if size != expected["size"] or sha256 != expected["sha256"]:
            raise Blocked(f"local file verification failed: {name}")
        facts.append({
            "name": name,
            "path": path,
            "size": size,
            "sha256": sha256,
            "md5": md5_file(path),
        })
    return facts


def load_payload() -> dict[str, Any]:
    try:
        payload = json.loads(METADATA_PATH.read_text("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Blocked(f"cannot load Zenodo metadata: {type(exc).__name__}") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("metadata"), dict):
        raise Blocked("Zenodo metadata payload has an invalid shape")
    metadata = payload["metadata"]
    if metadata.get("title") != EXPECTED_TITLE:
        raise Blocked("Zenodo title does not match the approved publication")
    required = {
        "upload_type": "publication",
        "publication_type": "workingpaper",
        "publication_date": "2026-07-21",
        "version": "3.0",
        "access_right": "open",
        "license": "cc-by-nc-nd-4.0",
        "language": "deu",
        "prereserve_doi": True,
    }
    for key, value in required.items():
        if metadata.get(key) != value:
            raise Blocked(f"Zenodo metadata mismatch: {key}")
    creators = metadata.get("creators")
    if not isinstance(creators, list) or not creators or creators[0].get("name") != "Lohmann, Ingolf":
        raise Blocked("approved creator metadata missing")
    encoded = json.dumps(payload, ensure_ascii=False)
    if "<" in encoded or ">" in encoded:
        raise Blocked("unresolved placeholder in Zenodo metadata")
    return payload


def token() -> str:
    value = os.environ.get("ZENODO_ACCESS_TOKEN", "")
    if not value or value.strip() != value or len(value) < 20:
        raise Blocked("ZENODO_ACCESS_TOKEN is missing or malformed")
    return value


def checked_url(url: str, *, api: bool) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "zenodo.org":
        raise Blocked("refusing a non-Zenodo or non-HTTPS URL")
    if api and not parsed.path.startswith("/api/"):
        raise Blocked("refusing an unexpected Zenodo API path")
    return url


def json_request(
    method: str,
    url: str,
    auth_token: str,
    body: Any = None,
    expected: tuple[int, ...] = (200,),
) -> dict[str, Any]:
    checked_url(url, api=True)
    raw = None
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Accept": "application/json",
        "User-Agent": "QIK-VRT-Zenodo-One-Shot/3.0",
    }
    if body is not None:
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=raw, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90, context=ssl.create_default_context()) as response:
            data = response.read(MAX_RESPONSE + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        raise Blocked(f"Zenodo API returned HTTP {exc.code} for {method}") from None
    except (urllib.error.URLError, TimeoutError):
        raise Blocked(f"Zenodo API connection failed for {method}") from None
    if status not in expected:
        raise Blocked(f"unexpected Zenodo HTTP status {status} for {method}")
    if len(data) > MAX_RESPONSE:
        raise Blocked("Zenodo response exceeded the safety limit")
    if not data:
        return {}
    try:
        result = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise Blocked("Zenodo returned invalid JSON") from None
    if not isinstance(result, dict):
        raise Blocked("Zenodo returned an unexpected response shape")
    return result


def upload_file(bucket_url: str, fact: dict[str, Any], auth_token: str) -> None:
    checked_url(bucket_url, api=True)
    target = bucket_url.rstrip("/") + "/" + urllib.parse.quote(fact["name"], safe="")
    checked_url(target, api=True)
    data = Path(fact["path"]).read_bytes()
    request = urllib.request.Request(
        target,
        data=data,
        method="PUT",
        headers={
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json",
            "Content-Type": "application/octet-stream",
            "User-Agent": "QIK-VRT-Zenodo-One-Shot/3.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180, context=ssl.create_default_context()) as response:
            response.read(MAX_RESPONSE + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        raise Blocked(f"Zenodo upload returned HTTP {exc.code}: {fact['name']}") from None
    except (urllib.error.URLError, TimeoutError):
        raise Blocked(f"Zenodo upload connection failed: {fact['name']}") from None
    if status not in (200, 201):
        raise Blocked(f"unexpected upload status {status}: {fact['name']}")


def normalize_checksum(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.split(":", 1)[-1].lower()


def deposition_files(value: dict[str, Any]) -> list[dict[str, Any]]:
    files = value.get("files")
    if isinstance(files, list):
        return [item for item in files if isinstance(item, dict)]
    if isinstance(files, dict) and isinstance(files.get("entries"), list):
        return [item for item in files["entries"] if isinstance(item, dict)]
    return []


def verify_remote_listing(value: dict[str, Any], facts: list[dict[str, Any]]) -> None:
    entries = deposition_files(value)
    by_name: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = entry.get("filename") or entry.get("key")
        if isinstance(name, str):
            by_name[name] = entry
    if set(by_name) != {fact["name"] for fact in facts}:
        raise Blocked("remote Zenodo file set differs from the approved five files")
    for fact in facts:
        entry = by_name[fact["name"]]
        if int(entry.get("filesize", entry.get("size", -1))) != fact["size"]:
            raise Blocked(f"remote file size mismatch: {fact['name']}")
        checksum = normalize_checksum(entry.get("checksum"))
        if checksum is not None and checksum != fact["md5"]:
            raise Blocked(f"remote MD5 mismatch: {fact['name']}")


def extract_prereserved_doi(value: dict[str, Any]) -> str:
    metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
    pre = metadata.get("prereserve_doi") if isinstance(metadata, dict) else None
    if isinstance(pre, dict) and isinstance(pre.get("doi"), str):
        return pre["doi"]
    doi = value.get("doi")
    if isinstance(doi, str) and doi.startswith("10.5281/zenodo."):
        return doi
    raise Blocked("Zenodo draft did not expose a reserved DOI")


def record_url(record_id: int) -> str:
    return f"https://zenodo.org/records/{record_id}"


def publish() -> dict[str, Any]:
    facts = local_facts()
    payload = load_payload()
    auth_token = token()

    created = json_request(
        "POST", f"{API_BASE}/deposit/depositions", auth_token, payload, expected=(201,)
    )
    record_id = created.get("id")
    if not isinstance(record_id, int) or record_id <= 0:
        raise Blocked("Zenodo did not return a valid deposition id")
    links = created.get("links") if isinstance(created.get("links"), dict) else {}
    bucket = links.get("bucket")
    if not isinstance(bucket, str):
        raise Blocked("Zenodo did not return an upload bucket")
    doi = extract_prereserved_doi(created)

    draft_receipt = {
        "status": "DRAFT_CREATED_NOT_YET_PUBLISHED",
        "record_id": record_id,
        "reserved_doi": doi,
        "draft_url": f"https://zenodo.org/uploads/{record_id}",
        "source_commit": os.environ.get("GITHUB_SHA"),
        "files": [{key: fact[key] for key in ("name", "size", "sha256", "md5")} for fact in facts],
    }
    RECEIPT_PATH.write_text(json.dumps(draft_receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")

    for fact in facts:
        upload_file(bucket, fact, auth_token)

    draft = json_request(
        "GET", f"{API_BASE}/deposit/depositions/{record_id}", auth_token, expected=(200,)
    )
    verify_remote_listing(draft, facts)
    if extract_prereserved_doi(draft) != doi:
        raise Blocked("reserved DOI changed before publication")

    published = json_request(
        "POST",
        f"{API_BASE}/deposit/depositions/{record_id}/actions/publish",
        auth_token,
        expected=(202,),
    )
    published_doi = published.get("doi")
    if isinstance(published_doi, str) and published_doi != doi:
        raise Blocked("published DOI differs from the reserved DOI")

    public: dict[str, Any] | None = None
    for _ in range(20):
        try:
            candidate = json_request(
                "GET", f"{API_BASE}/records/{record_id}", auth_token, expected=(200,)
            )
        except Blocked:
            time.sleep(5)
            continue
        live_doi = candidate.get("doi")
        live_metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else {}
        if live_doi == doi and live_metadata.get("title") == EXPECTED_TITLE:
            public = candidate
            break
        time.sleep(5)
    if public is None:
        raise Blocked(
            "publication was accepted but public verification did not finish; "
            f"inspect record {record_id} and do not repeat the upload"
        )
    verify_remote_listing(public, facts)

    receipt = {
        "status": "PUBLISHED_AND_PUBLICLY_VERIFIED",
        "record_id": record_id,
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}",
        "record_url": record_url(record_id),
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository": os.environ.get("GITHUB_REPOSITORY"),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "files": [{key: fact[key] for key in ("name", "size", "sha256", "md5")} for fact in facts],
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    if args.prepare == args.publish:
        raise Blocked("select exactly one of --prepare or --publish")
    facts = local_facts()
    load_payload()
    if args.prepare:
        print(json.dumps({
            "status": "READY",
            "network_performed": False,
            "files": [{key: fact[key] for key in ("name", "size", "sha256", "md5")} for fact in facts],
        }, ensure_ascii=False, indent=2))
        return 0
    receipt = publish()
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Blocked as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
