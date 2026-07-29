#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Build a retrospective, public-byte-verified Zenodo corpus proof registry.

The tool performs read-only Zenodo operations.  It enumerates every published
deposition visible to the connected account and attributable to Ingolf Lohmann,
re-fetches each public record, downloads every public file, verifies transport
checksums and builds one exact proof envelope per record.  It also discovers
repository provenance and existing claim/proof/evidence artifacts.

A proof envelope proves publication identity, public bytes and observed
provenance.  It never converts missing content-level claim analysis into a false
formal proof; such records are explicitly classified for retrospective content
review and possible versioned correction.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, NoReturn

TOKEN_ENV = "ZENODO_ACCESS_TOKEN"
ZENODO_ORIGIN = "https://zenodo.org"
MAX_JSON = 32 * 1024 * 1024
MAX_FILE = 512 * 1024 * 1024
MAX_PAGES = 100
PAGE_SIZE = 100
HEX32 = re.compile(r"^[0-9a-f]{32}$")
DOI_RE = re.compile(r"^10\.5281/zenodo\.([1-9][0-9]*)$")


class CorpusProofError(RuntimeError):
    pass


def fail(message: str) -> NoReturn:
    raise CorpusProofError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def write_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def safe_regular(path: pathlib.Path, limit: int = MAX_FILE) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        fail(f"cannot open regular file {path}: {exc.strerror}")
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            fail(f"not a regular file: {path}")
        if before.st_size > limit:
            fail(f"file exceeds size bound: {path}")
        data = bytearray()
        while True:
            chunk = os.read(fd, min(1024 * 1024, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > limit:
                fail(f"file exceeds size bound: {path}")
        after = os.fstat(fd)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            fail(f"file changed while being read: {path}")
        return bytes(data)
    finally:
        os.close(fd)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> None:
        return None


class ZenodoReadClient:
    def __init__(self, token: str) -> None:
        if not token or len(token) < 20 or any(character.isspace() for character in token):
            fail("ZENODO_ACCESS_TOKEN is missing or malformed")
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    @staticmethod
    def _validate_url(url: str, *, allow_query: bool) -> str:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or host != "zenodo.org"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or parsed.fragment
            or (parsed.query and not allow_query)
        ):
            fail("Zenodo URL escaped the approved HTTPS origin")
        return urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")
        )

    def json_get(self, url: str, *, authenticated: bool, allow_query: bool) -> Any:
        safe = self._validate_url(url, allow_query=allow_query)
        headers = {
            "Accept": "application/json",
            "User-Agent": "qikvrt-zenodo-corpus-proof/1.0",
        }
        if authenticated:
            headers["Authorization"] = "Bearer " + self.token
        request = urllib.request.Request(safe, headers=headers, method="GET")
        try:
            response = self.opener.open(request, timeout=60)
        except Exception as exc:  # urllib emits multiple transport subclasses
            fail(f"Zenodo JSON GET failed: {type(exc).__name__}")
        with response:
            final = self._validate_url(response.geturl(), allow_query=allow_query)
            if final != safe:
                fail("Zenodo JSON GET unexpectedly redirected")
            raw = response.read(MAX_JSON + 1)
        if len(raw) > MAX_JSON:
            fail("Zenodo JSON response exceeded its size bound")
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            fail("Zenodo returned invalid JSON")

    def public_bytes(self, url: str) -> bytes:
        safe = self._validate_url(url, allow_query=False)
        request = urllib.request.Request(
            safe,
            headers={
                "Accept": "application/octet-stream, */*;q=0.1",
                "User-Agent": "qikvrt-zenodo-corpus-proof/1.0",
            },
            method="GET",
        )
        # Public downloads may redirect within the exact Zenodo origin.  No token
        # is attached, and the final origin is checked before any bytes are used.
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                final = urllib.parse.urlsplit(response.geturl())
                if final.scheme != "https" or (final.hostname or "").lower() != "zenodo.org":
                    fail("public file redirect escaped Zenodo")
                data = response.read(MAX_FILE + 1)
        except CorpusProofError:
            raise
        except Exception as exc:
            fail(f"Zenodo public file download failed: {type(exc).__name__}")
        if len(data) > MAX_FILE:
            fail("Zenodo public file exceeded its size bound")
        return data

    def published_depositions(self) -> list[dict[str, Any]]:
        observed: dict[int, dict[str, Any]] = {}
        for page in range(1, MAX_PAGES + 1):
            query = urllib.parse.urlencode(
                {
                    "size": PAGE_SIZE,
                    "sort": "mostrecent",
                    "page": page,
                }
            )
            url = f"{ZENODO_ORIGIN}/api/deposit/depositions?{query}"
            value = self.json_get(url, authenticated=True, allow_query=True)
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                fail("Zenodo deposition inventory has an invalid shape")
            new_count = 0
            for item in value:
                raw_id = item.get("record_id", item.get("id"))
                try:
                    record_id = int(raw_id)
                except (TypeError, ValueError):
                    continue
                state = str(item.get("state", "")).lower()
                submitted = item.get("submitted") is True
                if not submitted and state not in {"done", "published"}:
                    continue
                if record_id not in observed:
                    observed[record_id] = dict(item)
                    new_count += 1
            if len(value) < PAGE_SIZE or new_count == 0:
                break
        else:
            fail("Zenodo deposition inventory exceeded the pagination bound")
        return [observed[key] for key in sorted(observed)]


def normalized_person(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def attributed_to_ingolf(metadata: Mapping[str, Any]) -> bool:
    creators = metadata.get("creators")
    if not isinstance(creators, list):
        return False
    for creator in creators:
        if not isinstance(creator, dict):
            continue
        name = creator.get("name")
        if not isinstance(name, str):
            continue
        normalized = normalized_person(name)
        if "ingolf" in normalized.split() and "lohmann" in normalized.split():
            return True
    return False


def positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def doi_from_record(record: Mapping[str, Any], record_id: int) -> str:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    pids = record.get("pids") if isinstance(record.get("pids"), dict) else {}
    candidate = record.get("doi") or metadata.get("doi")
    if not candidate and isinstance(pids.get("doi"), dict):
        candidate = pids["doi"].get("identifier")
    if not isinstance(candidate, str) or DOI_RE.fullmatch(candidate) is None:
        candidate = f"10.5281/zenodo.{record_id}"
    return candidate


def concept_doi_from_record(record: Mapping[str, Any]) -> str | None:
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    candidate = record.get("conceptdoi") or metadata.get("conceptdoi")
    parent = record.get("parent") if isinstance(record.get("parent"), dict) else {}
    pids = parent.get("pids") if isinstance(parent.get("pids"), dict) else {}
    if not candidate and isinstance(pids.get("doi"), dict):
        candidate = pids["doi"].get("identifier")
    if not candidate:
        concept = positive_int(record.get("conceptrecid"))
        if concept is not None:
            candidate = f"10.5281/zenodo.{concept}"
    if isinstance(candidate, str) and DOI_RE.fullmatch(candidate):
        return candidate
    return None


def public_files(record: Mapping[str, Any], record_id: int) -> list[dict[str, Any]]:
    raw = record.get("files")
    values: list[dict[str, Any]] = []
    if isinstance(raw, list):
        values = [dict(item) for item in raw if isinstance(item, dict)]
    elif isinstance(raw, dict):
        entries = raw.get("entries")
        source = entries if isinstance(entries, dict) else raw
        for key, item in source.items():
            if isinstance(item, dict):
                normalized = dict(item)
                normalized.setdefault("key", key)
                values.append(normalized)
    result: list[dict[str, Any]] = []
    for value in values:
        name = value.get("key") or value.get("filename") or value.get("name")
        if not isinstance(name, str) or pathlib.PurePosixPath(name).name != name:
            fail(f"record {record_id} contains an unsafe public file name")
        links = value.get("links") if isinstance(value.get("links"), dict) else {}
        url = links.get("content") or links.get("download") or links.get("self")
        if not isinstance(url, str) or not url:
            quoted = urllib.parse.quote(name, safe="")
            url = f"{ZENODO_ORIGIN}/api/records/{record_id}/files/{quoted}/content"
        result.append(
            {
                "name": name,
                "declared_size": value.get("size", value.get("filesize")),
                "declared_checksum": value.get("checksum", value.get("md5")),
                "download_url": url,
            }
        )
    if not result:
        fail(f"published record {record_id} exposes no public files")
    names = [item["name"] for item in result]
    if len(names) != len(set(names)):
        fail(f"published record {record_id} exposes duplicate file names")
    return sorted(result, key=lambda item: item["name"])


def verify_public_file(
    client: ZenodoReadClient, record_id: int, item: Mapping[str, Any]
) -> dict[str, Any]:
    data = client.public_bytes(str(item["download_url"]))
    md5 = hashlib.md5(data).hexdigest()  # noqa: S324 - Zenodo transport checksum
    sha256 = hashlib.sha256(data).hexdigest()
    declared_size = item.get("declared_size")
    if isinstance(declared_size, int) and declared_size != len(data):
        fail(f"public size mismatch for record {record_id} file {item['name']}")
    declared_checksum = item.get("declared_checksum")
    if isinstance(declared_checksum, str):
        expected = declared_checksum.split(":", 1)[-1].lower()
        if HEX32.fullmatch(expected) and expected != md5:
            fail(f"public MD5 mismatch for record {record_id} file {item['name']}")
    return {
        "name": item["name"],
        "bytes": len(data),
        "md5": md5,
        "sha256": sha256,
        "public_byte_redownload_verified": True,
    }


def tracked_files(root: pathlib.Path) -> list[pathlib.Path]:
    raw = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--", "."], cwd=root
    )
    result: list[pathlib.Path] = []
    for value in raw.split(b"\0"):
        if not value:
            continue
        relative = value.decode("utf-8")
        path = root / relative
        if path.is_file() and not path.is_symlink():
            result.append(path)
    return sorted(result, key=lambda path: path.relative_to(root).as_posix())


def repository_index(root: pathlib.Path) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    by_sha256: dict[str, list[str]] = {}
    searchable: list[tuple[str, str]] = []
    for path in tracked_files(root):
        relative = path.relative_to(root).as_posix()
        data = safe_regular(path)
        by_sha256.setdefault(sha256_bytes(data), []).append(relative)
        if len(data) <= 16 * 1024 * 1024 and b"\x00" not in data:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            searchable.append((relative, text))
    return by_sha256, searchable


def classify_repository_ref(path: str) -> str:
    upper = path.upper()
    if pathlib.PurePosixPath(path).name.lower() == "zenodo-publication.json":
        return "EVIDENCE"
    if "CLAIM_MATRIX" in upper or "CLAIM_GRAPH" in upper or "CLAIM_INVENTORY" in upper:
        return "CLAIM_DISPOSITION"
    if "KERNEL_RECEIPT" in upper or "PROOF_OBJECT" in upper or upper.endswith(".LEAN"):
        return "FORMAL_PROOF"
    if "EVIDENCE" in upper or "RECEIPT" in upper or "VERIFICATION" in upper:
        return "EVIDENCE"
    if "SOURCE" in upper or "ARTICLE" in upper or upper.endswith((".PDF", ".TEX", ".MD", ".TXT")):
        return "SOURCE_OR_CONTENT"
    return "OTHER"


def refs_for_record(
    searchable: Iterable[tuple[str, str]], record_id: int, doi: str, conceptdoi: str | None
) -> list[dict[str, str]]:
    needles = {str(record_id), doi}
    if conceptdoi:
        needles.add(conceptdoi)
    results: list[dict[str, str]] = []
    for path, text in searchable:
        if any(needle in text for needle in needles):
            results.append({"path": path, "kind": classify_repository_ref(path)})
    return sorted(results, key=lambda item: (item["kind"], item["path"]))


def build_envelope(
    *,
    observed_at: str,
    record: Mapping[str, Any],
    public_record: Mapping[str, Any],
    verified_files: list[dict[str, Any]],
    repository_sha_index: Mapping[str, list[str]],
    searchable: Iterable[tuple[str, str]],
) -> dict[str, Any]:
    record_id = positive_int(public_record.get("id")) or positive_int(
        record.get("record_id", record.get("id"))
    )
    if record_id is None:
        fail("published record lacks a positive record ID")
    metadata = public_record.get("metadata")
    if not isinstance(metadata, dict):
        fail(f"public record {record_id} lacks metadata")
    if not attributed_to_ingolf(metadata):
        fail(f"public record {record_id} is not attributable to Ingolf Lohmann")
    doi = doi_from_record(public_record, record_id)
    conceptdoi = concept_doi_from_record(public_record)
    refs = refs_for_record(searchable, record_id, doi, conceptdoi)
    hash_matches: list[dict[str, Any]] = []
    for item in verified_files:
        paths = repository_sha_index.get(item["sha256"], [])
        hash_matches.append(
            {
                "public_name": item["name"],
                "sha256": item["sha256"],
                "repository_paths": sorted(paths),
                "repository_byte_match": bool(paths),
            }
        )
    claim_refs = [item["path"] for item in refs if item["kind"] == "CLAIM_DISPOSITION"]
    formal_refs = [item["path"] for item in refs if item["kind"] == "FORMAL_PROOF"]
    evidence_refs = [item["path"] for item in refs if item["kind"] == "EVIDENCE"]
    repository_provenance = bool(refs) or any(
        item["repository_byte_match"] for item in hash_matches
    )
    claim_coverage = (
        "EXISTING_MACHINE_CLAIM_DISPOSITION_BOUND"
        if claim_refs
        else "RETROSPECTIVE_RECORD_LEVEL_ENVELOPE_ONLY"
    )
    required_action = (
        "VERIFY_EXISTING_CLAIM_GRAPH_AND_NO_CONTENT_CHANGE"
        if claim_refs
        else "CONTENT_CLAIM_EXTRACTION_REVIEW_AND_POSSIBLE_VERSIONED_CORRECTION"
    )
    title = metadata.get("title")
    version = metadata.get("version")
    return {
        "_license": {
            "classification": "machine_readable_retrospective_proof_envelope",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_zenodo_retrospective_record_proof_envelope_v1",
        "observed_at": observed_at,
        "record": {
            "record_id": record_id,
            "doi": doi,
            "conceptdoi": conceptdoi,
            "title": title,
            "version": version,
            "creators": metadata.get("creators"),
            "public_record_canonical_sha256": sha256_bytes(canonical_bytes(public_record)),
            "published_state_verified": True,
        },
        "public_files": verified_files,
        "repository_provenance": {
            "observed": repository_provenance,
            "textual_references": refs,
            "public_file_hash_matches": hash_matches,
        },
        "proof_artifacts": {
            "claim_disposition_refs": claim_refs,
            "formal_proof_refs": formal_refs,
            "evidence_refs": evidence_refs,
        },
        "claims": [
            {
                "claim_id": f"ZENODO-{record_id}-IDENTITY",
                "statement": "The public Zenodo record identity, DOI, metadata and published state were independently observed.",
                "classification": "SOURCE_BOUND",
                "status": "BOUND",
                "scope": "public Zenodo records API response",
            },
            {
                "claim_id": f"ZENODO-{record_id}-BYTES",
                "statement": "Every public file was redownloaded and bound by size, MD5 and SHA-256.",
                "classification": "EMPIRICALLY_EVIDENCED",
                "status": "EVIDENCED",
                "scope": "the exact public file set listed in this envelope",
            },
            {
                "claim_id": f"ZENODO-{record_id}-REPOSITORY-PROVENANCE",
                "statement": "Repository provenance is present exactly to the extent listed in this envelope.",
                "classification": "SOURCE_BOUND" if repository_provenance else "OPEN",
                "status": "BOUND" if repository_provenance else "OPEN",
                "scope": "current Authority repository tree",
            },
            {
                "claim_id": f"ZENODO-{record_id}-CONTENT-COVERAGE",
                "statement": "Content-level claim proof coverage is exactly the state declared by claim_coverage.",
                "classification": "SOURCE_BOUND",
                "status": "BOUND",
                "scope": "discovered machine-readable repository proof artifacts",
            },
        ],
        "coverage": {
            "publication_identity_complete": True,
            "public_file_integrity_complete": True,
            "repository_provenance_observed": repository_provenance,
            "claim_coverage": claim_coverage,
            "formal_proof_artifacts_observed": bool(formal_refs),
            "content_level_final_pass": False,
            "required_action": required_action,
        },
        "completion_claims": {
            "publication_integrity_proved": True,
            "all_natural_language_claims_formally_proved": False,
            "retrospective_content_review_complete": False,
            "final_pass": False,
        },
    }


def build_report(index: Mapping[str, Any]) -> str:
    lines = [
        "<!--",
        "SPDX-License-Identifier: CC-BY-NC-ND-4.0",
        "Copyright 2026 Ingolf Lohmann.",
        "-->",
        "",
        "# Retrospektiver maschineller Zenodo-Korpusbeweis",
        "",
        f"**Beobachtungszeitpunkt:** `{index['observed_at']}`  ",
        f"**Veröffentlichungen:** `{index['record_count']}`  ",
        f"**Öffentlich bytegenau rückgeprüft:** `{index['public_byte_verified_count']}`",
        "",
        "## Bewiesener Umfang",
        "",
        "Für jeden erfassten Record sind Identität, DOI, Concept-Bezug, öffentliche Metadaten, veröffentlichter Zustand und sämtliche öffentlich verfügbaren Dateien maschinell erfasst. Jede Datei wurde erneut von Zenodo heruntergeladen und durch Größe, MD5 und SHA-256 gebunden.",
        "",
        "## Wahrheitsgrenze",
        "",
        "Dieser Korpusbeweis erklärt keine natürliche Sprache pauschal zum mathematischen Theorem. Er weist für jeden Record den tatsächlichen Anspruchsdispositionsstand aus. Veröffentlichungen ohne bereits auffindbare Claim-Matrix erhalten keinen falschen Inhalts-PASS, sondern den Status `RETROSPECTIVE_RECORD_LEVEL_ENVELOPE_ONLY` und einen verpflichtenden inhaltlichen Review mit möglicher versionierter Korrektur.",
        "",
        "## Records",
        "",
        "| Record | DOI | Titel | Claim-Coverage | Erforderliche Aktion |",
        "|---:|---|---|---|---|",
    ]
    for item in index["records"]:
        title = str(item["title"] or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {item['record_id']} | `{item['doi']}` | {title} | `{item['claim_coverage']}` | `{item['required_action']}` |"
        )
    lines.extend(
        [
            "",
            "## Verbindlicher Folgegrundsatz",
            "",
            "```text",
            "NO_MACHINE_PROOF_NO_ZENODO_UPLOAD",
            "NO_PREPUBLICATION_RETURN_RECEIPT_NO_CHANGED_CONTENT_UPLOAD",
            "RETURNED_BYTES_MUST_EQUAL_UPLOADED_BYTES",
            "```",
            "",
            "Neue Veröffentlichungen werden erst nach vollständiger Claim-Disposition, notwendiger Korrektur, sichtbarer Rücklieferung der exakten Kandidatenfassung an Ingolf Lohmann und kandidatenspezifischer Rücklieferungsquittung auf Zenodo hochgeladen.",
            "",
            "**q.e.d.**  ",
            "**Ingolf Lohmann**",
            "",
        ]
    )
    return "\n".join(lines)


def inventory(root: pathlib.Path, output_dir: pathlib.Path, observed_at: str) -> dict[str, Any]:
    token = os.environ.get(TOKEN_ENV, "")
    client = ZenodoReadClient(token)
    repository_sha_index, searchable = repository_index(root)
    depositions = client.published_depositions()
    envelopes: list[dict[str, Any]] = []
    for deposition in depositions:
        metadata = deposition.get("metadata")
        if not isinstance(metadata, dict) or not attributed_to_ingolf(metadata):
            continue
        record_id = positive_int(deposition.get("record_id", deposition.get("id")))
        if record_id is None:
            fail("attributable published deposition lacks record ID")
        public = client.json_get(
            f"{ZENODO_ORIGIN}/api/records/{record_id}",
            authenticated=False,
            allow_query=False,
        )
        if not isinstance(public, dict):
            fail(f"public record {record_id} is not a JSON object")
        if positive_int(public.get("id")) != record_id:
            fail(f"public record identity mismatch for {record_id}")
        files = [
            verify_public_file(client, record_id, item)
            for item in public_files(public, record_id)
        ]
        envelope = build_envelope(
            observed_at=observed_at,
            record=deposition,
            public_record=public,
            verified_files=files,
            repository_sha_index=repository_sha_index,
            searchable=searchable,
        )
        envelopes.append(envelope)
        write_json(
            output_dir / "proof-envelopes" / f"zenodo-{record_id}.json",
            envelope,
        )
    if not envelopes:
        fail("authenticated inventory found no published Ingolf Lohmann records")
    envelopes.sort(key=lambda value: value["record"]["record_id"])
    records = [
        {
            "record_id": value["record"]["record_id"],
            "doi": value["record"]["doi"],
            "conceptdoi": value["record"]["conceptdoi"],
            "title": value["record"]["title"],
            "version": value["record"]["version"],
            "public_file_count": len(value["public_files"]),
            "claim_coverage": value["coverage"]["claim_coverage"],
            "required_action": value["coverage"]["required_action"],
            "envelope_path": (
                output_dir / "proof-envelopes" / f"zenodo-{value['record']['record_id']}.json"
            ).relative_to(root).as_posix(),
        }
        for value in envelopes
    ]
    index = {
        "_license": {
            "classification": "machine_readable_zenodo_corpus_proof_index",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_zenodo_corpus_proof_index_v1",
        "policy": "policy/zenodo-machine-proof-policy-v1.json",
        "observed_at": observed_at,
        "account_scope": "authenticated published depositions attributable to Ingolf Lohmann",
        "record_count": len(records),
        "public_byte_verified_count": len(records),
        "existing_claim_disposition_count": sum(
            item["claim_coverage"] == "EXISTING_MACHINE_CLAIM_DISPOSITION_BOUND"
            for item in records
        ),
        "retrospective_content_review_required_count": sum(
            item["claim_coverage"] != "EXISTING_MACHINE_CLAIM_DISPOSITION_BOUND"
            for item in records
        ),
        "records": records,
        "completion_claims": {
            "account_inventory_complete_within_authenticated_api_observation": True,
            "public_record_and_file_integrity_complete": True,
            "all_content_claims_final_pass": False,
            "proof_corpus_publication_executed": False,
            "final_pass": False,
        },
    }
    write_json(output_dir / "ZENODO_CORPUS_PROOF_INDEX.json", index)
    write_text(output_dir / "CORPUS_PROOF_REPORT_DE.md", build_report(index))
    inventory_value = {
        "schema": "qikvrt_zenodo_corpus_inventory_v1",
        "observed_at": observed_at,
        "records": [value["record"] for value in envelopes],
        "record_count": len(envelopes),
    }
    write_json(output_dir / "ZENODO_CORPUS_INVENTORY.json", inventory_value)
    return index


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a read-only Zenodo corpus proof registry")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args(argv)
    try:
        parsed = dt.datetime.fromisoformat(args.observed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            fail("--observed-at must include a timezone")
        root = pathlib.Path.cwd().resolve()
        output_dir = (root / args.output_dir).resolve()
        output_dir.relative_to(root)
        index = inventory(root, output_dir, args.observed_at)
    except (CorpusProofError, ValueError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    print("ZENODO_CORPUS_INVENTORY_STATE=verified")
    print("ZENODO_CORPUS_RECORD_COUNT=" + str(index["record_count"]))
    print("ZENODO_CORPUS_PUBLIC_BYTE_VERIFIED=" + str(index["public_byte_verified_count"]))
    print(
        "ZENODO_CORPUS_CONTENT_REVIEW_REQUIRED="
        + str(index["retrospective_content_review_required_count"])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
