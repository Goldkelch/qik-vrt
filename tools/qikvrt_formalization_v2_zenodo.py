#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Reserve and finalize exactly QIK-VRT Formalization v2 alpha.2.

The client is intentionally release-specific.  It can create one new version
from published source record 21501365 in concept 21488115, or reconcile the
one draft named by a token-authenticated reservation.  It cannot edit the
published source, create a standalone deposition, or mutate any other draft.

The bearer token is accepted only through ``ZENODO_ACCESS_TOKEN``.  Local
preflight can validate manifests and payload hashes without a token; all live
reserve/finalize operations are intended to run in the bound GitHub Actions
workflows.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import re
import sys
import urllib.parse
from collections.abc import Mapping, Sequence
from typing import Any

try:
    from tools import qikvrt_zenodo_actions as shared
except ModuleNotFoundError:  # Direct ``python tools/<script>.py`` execution.
    import qikvrt_zenodo_actions as shared  # type: ignore[no-redef]


MANIFEST_SCHEMA = "qikvrt_formalization_v2_alpha2_zenodo_manifest_v1"
RESERVATION_KIND = "qikvrt-formalization-v2-alpha2"
RESULT_SCHEMA = "qikvrt_formalization_v2_alpha2_zenodo_result_v1"
RELEASE_ID = "2026-07-23-formalization-v2.0-alpha.2"
TARGET_VERSION = "2.0.0-alpha.2"
SOURCE_RECORD_ID = 21501365
SOURCE_VERSION_DOI = "10.5281/zenodo.21501365"
SOURCE_VERSION = "2.0.0-alpha.1"
CONCEPT_RECORD_ID = 21488115
SOURCE_EVIDENCE_SCHEMA = (
    "qikvrt_formalization_v2_zenodo_independent_verification_v1"
)
PROTECTED_ZENODO_IDS = frozenset(
    {
        CONCEPT_RECORD_ID,
        21488116,
        21498773,
        21498774,
        SOURCE_RECORD_ID,
    }
)
MAX_RELEASE_FILES = 100
MAX_RELEASE_BYTES = shared.MAX_UPLOAD_BYTES

REQUIRED_METADATA_KEYS = frozenset(
    {"title", "upload_type", "description", "creators", "version"}
)
ALLOWED_METADATA_KEYS = frozenset(
    {
        "title",
        "upload_type",
        "description",
        "creators",
        "version",
        "publication_date",
        "access_right",
        "license",
        "language",
        "keywords",
        "related_identifiers",
        "notes",
    }
)

ZenodoError = shared.ZenodoError


def _positive_id(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ZenodoError(f"{where} must be a positive integer")
    return value


def _validate_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not shared._is_json_value(value):
        raise ZenodoError("software.metadata must be a JSON object")
    unknown = set(value) - ALLOWED_METADATA_KEYS
    missing = REQUIRED_METADATA_KEYS - set(value)
    if unknown or missing:
        details: list[str] = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            details.append("unknown=" + ",".join(sorted(unknown)))
        raise ZenodoError(
            "invalid software.metadata keys (" + "; ".join(details) + ")"
        )
    shared._metadata_identity(value, "software")
    if value["upload_type"] != "software":
        raise ZenodoError("software.metadata.upload_type must equal software")
    if value["version"] != TARGET_VERSION:
        raise ZenodoError(
            f"software.metadata.version must equal {TARGET_VERSION}"
        )
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise ZenodoError("software.metadata.description must be non-empty")
    if value.get("access_right", "open") != "open":
        raise ZenodoError("software.metadata.access_right must equal open")
    if "license" in value and (
        not isinstance(value["license"], str) or not value["license"].strip()
    ):
        raise ZenodoError("software.metadata.license must be non-empty")
    if "language" in value and (
        not isinstance(value["language"], str)
        or re.fullmatch(r"[a-z]{3}", value["language"]) is None
    ):
        raise ZenodoError(
            "software.metadata.language must be lowercase ISO 639-3"
        )
    keywords = value.get("keywords")
    if keywords is not None and (
        not isinstance(keywords, list)
        or not keywords
        or not all(isinstance(item, str) and item.strip() for item in keywords)
        or len(keywords) != len(set(keywords))
    ):
        raise ZenodoError(
            "software.metadata.keywords must be unique non-empty strings"
        )
    return dict(value)


def validate_manifest(value: dict[str, Any], root: pathlib.Path) -> dict[str, Any]:
    """Validate and normalize the one exact alpha.2 software manifest."""
    shared._check_exact_keys(value, {"schema", "software"}, "manifest")
    if value["schema"] != MANIFEST_SCHEMA:
        raise ZenodoError("manifest.schema is unsupported")
    software = value["software"]
    if not isinstance(software, dict):
        raise ZenodoError("manifest.software must be an object")
    shared._check_exact_keys(
        software,
        {"source_record_id", "concept_record_id", "metadata", "files"},
        "software",
    )
    source = _positive_id(software["source_record_id"], "source_record_id")
    concept = _positive_id(software["concept_record_id"], "concept_record_id")
    if source != SOURCE_RECORD_ID or concept != CONCEPT_RECORD_ID:
        raise ZenodoError(
            "manifest lineage is not the authorized alpha.2 source/concept"
        )
    metadata = _validate_metadata(software["metadata"])
    raw_files = software["files"]
    if (
        not isinstance(raw_files, list)
        or not 1 <= len(raw_files) <= MAX_RELEASE_FILES
    ):
        raise ZenodoError(
            f"software.files must contain 1..{MAX_RELEASE_FILES} files"
        )
    files = [
        shared._validate_file_entry(item, root, f"software.files[{index}]")
        for index, item in enumerate(raw_files)
    ]
    if len({entry["name"] for entry in files}) != len(files):
        raise ZenodoError("software.files contains duplicate upload names")
    if len({entry["path"] for entry in files}) != len(files):
        raise ZenodoError("software.files contains duplicate repository paths")
    if sum(entry["size"] for entry in files) > MAX_RELEASE_BYTES:
        raise ZenodoError("software release exceeds the upload size limit")
    return {
        "schema": MANIFEST_SCHEMA,
        "software": {
            "source_record_id": source,
            "concept_record_id": concept,
            "metadata": metadata,
            "files": files,
        },
    }


def verify_manifest_files(
    manifest: Mapping[str, Any], root: pathlib.Path, token: str
) -> dict[tuple[str, str], bytes]:
    verified: dict[tuple[str, str], bytes] = {}
    for entry in manifest["software"]["files"]:
        verified[("software", entry["name"])] = shared._file_bytes(
            root, entry, token
        )
    return verified


def validate_source_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the persisted anonymous proof for published source 21501365."""
    required = {
        "anonymous",
        "concept_record_id",
        "doi",
        "files",
        "manifest_sha256",
        "public_record_verified",
        "published_record_id",
        "schema",
        "source_latest_verified",
        "source_record_id",
        "verified_at_utc",
        "version",
    }
    shared._check_exact_keys(value, required, "source evidence")
    if (
        value["schema"] != SOURCE_EVIDENCE_SCHEMA
        or value["published_record_id"] != SOURCE_RECORD_ID
        or value["concept_record_id"] != CONCEPT_RECORD_ID
        or value["doi"] != SOURCE_VERSION_DOI
        or value["version"] != SOURCE_VERSION
        or value["anonymous"] is not True
        or value["public_record_verified"] is not True
        or value["source_latest_verified"] is not True
    ):
        raise ZenodoError("source evidence does not identify verified record 21501365")
    files = value["files"]
    if (
        not isinstance(files, list)
        or len(files) != 14
        or not all(isinstance(item, dict) for item in files)
    ):
        raise ZenodoError("source evidence must contain exactly 14 file entries")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        shared._check_exact_keys(
            item, {"name", "size", "md5", "sha256"}, f"source files[{index}]"
        )
        name = item["name"]
        size = item["size"]
        md5 = item["md5"]
        sha256 = item["sha256"]
        if (
            not isinstance(name, str)
            or not name
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(md5, str)
            or shared.HEX_32.fullmatch(md5) is None
            or not isinstance(sha256, str)
            or shared.HEX_64.fullmatch(sha256) is None
        ):
            raise ZenodoError(f"source files[{index}] is malformed")
        normalized.append(
            {"name": name, "size": size, "md5": md5, "sha256": sha256}
        )
    if len({item["name"] for item in normalized}) != len(normalized):
        raise ZenodoError("source evidence contains duplicate file names")
    result = dict(value)
    result["files"] = sorted(normalized, key=lambda item: item["name"])
    return result


def _manifest_hashes(manifest: Mapping[str, Any]) -> tuple[str, str]:
    software = manifest["software"]
    metadata_sha256 = hashlib.sha256(
        shared._json_bytes(software["metadata"])
    ).hexdigest()
    files_sha256 = hashlib.sha256(
        shared._json_bytes(software["files"])
    ).hexdigest()
    return metadata_sha256, files_sha256


def _draft_file_fingerprint(value: Mapping[str, Any]) -> list[dict[str, Any]]:
    files = value.get("files")
    if not isinstance(files, list) or not all(isinstance(item, dict) for item in files):
        raise ZenodoError("new-version draft has an invalid inherited file list")
    fingerprint: list[dict[str, Any]] = []
    for item in files:
        name = item.get("filename", item.get("key"))
        size = item.get("filesize", item.get("size"))
        checksum = item.get("checksum")
        if isinstance(size, str) and size.isdecimal():
            size = int(size)
        if isinstance(checksum, str) and checksum.startswith("md5:"):
            checksum = checksum[4:]
        if (
            not isinstance(name, str)
            or not name
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
            or not isinstance(checksum, str)
            or shared.HEX_32.fullmatch(checksum) is None
        ):
            raise ZenodoError("new-version draft inherited file is malformed")
        fingerprint.append({"name": name, "size": size, "md5": checksum})
    if len({item["name"] for item in fingerprint}) != len(fingerprint):
        raise ZenodoError("new-version draft inherited duplicate file names")
    return sorted(fingerprint, key=lambda item: item["name"])


def _expected_source_fingerprint(
    source_evidence: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        {"name": item["name"], "size": item["size"], "md5": item["md5"]}
        for item in source_evidence["files"]
    ]


class FormalizationVersionClient(shared.ZenodoClient):
    """Mutation-restricted client for one reserved alpha.2 draft."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._allow_newversion = False
        self._newversion_attempted = False
        self._authorized_draft_id: int | None = None
        self._authorized_bucket_path: str | None = None

    def _mutation_is_authorized(self, method: str, path: str) -> bool:
        source_action = (
            f"/api/deposit/depositions/{SOURCE_RECORD_ID}/actions/newversion"
        )
        if method == "POST" and path.rstrip("/") == source_action:
            return self._allow_newversion
        draft_id = self._authorized_draft_id
        if draft_id is None:
            return False
        deposition = f"/api/deposit/depositions/{draft_id}"
        if method == "PUT" and path.rstrip("/") == deposition:
            return True
        if method == "POST" and path.rstrip("/") == deposition + "/actions/publish":
            return True
        if method == "DELETE" and path.startswith(deposition + "/files/"):
            return True
        bucket = self._authorized_bucket_path
        return bool(
            bucket
            and path.startswith(bucket + "/")
            and method in {"PUT", "DELETE"}
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        payload: Any | None = None,
        data: bytes | None = None,
        content_type: str | None = None,
        accept: Sequence[int] = (200,),
        parse_json: bool = True,
        max_response_bytes: int = shared.MAX_RESPONSE_BYTES,
    ) -> tuple[shared.HttpResponse, dict[str, Any]]:
        safe_url = shared.validate_response_url(url, self.base_url)
        path = urllib.parse.urlsplit(safe_url).path
        method = method.upper()
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise ZenodoError("HTTP method is outside the alpha.2 policy")
        if method != "GET" and not self._mutation_is_authorized(method, path):
            raise ZenodoError("mutation is outside the reserved alpha.2 draft")
        return super().request(
            method,
            safe_url,
            payload=payload,
            data=data,
            content_type=content_type,
            accept=accept,
            parse_json=parse_json,
            max_response_bytes=max_response_bytes,
        )

    def authorize_draft(
        self,
        value: Mapping[str, Any],
        *,
        record_id: int,
        doi: str,
    ) -> None:
        if record_id in PROTECTED_ZENODO_IDS:
            raise ZenodoError("reserved alpha.2 draft reused a protected Zenodo ID")
        if shared._record_id(value, "alpha.2 draft") != record_id:
            raise ZenodoError("reserved alpha.2 draft ID changed")
        if shared._concept_id(value, "alpha.2 draft") != CONCEPT_RECORD_ID:
            raise ZenodoError("reserved alpha.2 draft changed concept")
        actual_doi = shared._doi_from_deposition(value, "alpha.2 draft")
        if actual_doi != doi or doi != f"10.5281/zenodo.{record_id}":
            raise ZenodoError("reserved alpha.2 DOI and draft ID disagree")
        if value.get("submitted") is True or value.get("state") == "done":
            raise ZenodoError("reserved alpha.2 draft is not editable")
        links = value.get("links")
        if not isinstance(links, dict):
            raise ZenodoError("reserved alpha.2 draft has no links")
        self_link = links.get("self")
        bucket_link = links.get("bucket")
        if not isinstance(self_link, str) or not isinstance(bucket_link, str):
            raise ZenodoError("reserved alpha.2 draft has no safe self/bucket links")
        self_path = urllib.parse.urlsplit(
            shared.validate_response_url(self_link, self.base_url)
        ).path.rstrip("/")
        if self_path != f"/api/deposit/depositions/{record_id}":
            raise ZenodoError("reserved alpha.2 self link changed identity")
        bucket_path = urllib.parse.urlsplit(
            shared.validate_response_url(bucket_link, self.base_url)
        ).path.rstrip("/")
        if not bucket_path.startswith("/api/files/"):
            raise ZenodoError("reserved alpha.2 bucket escaped the file API")
        if self._authorized_draft_id not in (None, record_id):
            raise ZenodoError("client is already bound to another draft")
        if self._authorized_bucket_path not in (None, bucket_path):
            raise ZenodoError("reserved alpha.2 bucket changed")
        self._authorized_draft_id = record_id
        self._authorized_bucket_path = bucket_path

    def create_version(self) -> dict[str, Any]:
        if self._newversion_attempted:
            raise ZenodoError("this client may attempt newversion only once")
        self._newversion_attempted = True
        self._allow_newversion = True
        try:
            return super().create_software_version(
                SOURCE_RECORD_ID, CONCEPT_RECORD_ID
            )
        finally:
            self._allow_newversion = False


def _require_pristine_source_snapshot(
    draft: Mapping[str, Any],
    source_public: Mapping[str, Any],
    source_evidence: Mapping[str, Any],
) -> tuple[int, str]:
    record_id = shared._record_id(draft, "new alpha.2 draft")
    if record_id in PROTECTED_ZENODO_IDS:
        raise ZenodoError("new alpha.2 draft reused a protected ID")
    if shared._concept_id(draft, "new alpha.2 draft") != CONCEPT_RECORD_ID:
        raise ZenodoError("new alpha.2 draft changed concept")
    if draft.get("submitted") is True or draft.get("state") == "done":
        raise ZenodoError("new alpha.2 draft is not editable")
    doi = shared._doi_from_deposition(draft, "new alpha.2 draft")
    if doi != f"10.5281/zenodo.{record_id}":
        raise ZenodoError("new alpha.2 draft DOI is not record-bound")
    if _draft_file_fingerprint(draft) != _expected_source_fingerprint(
        source_evidence
    ):
        raise ZenodoError("new alpha.2 draft did not inherit the exact source files")
    source_metadata = source_public.get("metadata")
    draft_metadata = draft.get("metadata")
    if not isinstance(source_metadata, dict) or not isinstance(draft_metadata, dict):
        raise ZenodoError("source or draft metadata is missing")
    if source_metadata.get("version") != SOURCE_VERSION:
        raise ZenodoError("published source metadata has an unexpected version")
    identity = {
        key: source_metadata[key]
        for key in ("title", "creators")
        if key in source_metadata
    }
    if set(identity) != {"title", "creators"} or not shared._metadata_matches(
        draft_metadata, identity
    ):
        raise ZenodoError("new alpha.2 draft did not inherit source title and creators")
    if (
        "version" in draft_metadata
        and draft_metadata["version"] != SOURCE_VERSION
    ):
        raise ZenodoError("new alpha.2 draft inherited an unexpected source version")
    return record_id, doi


def _sign_reservation(value: Mapping[str, Any], token: str) -> dict[str, Any]:
    signed = dict(value)
    signed.pop("authorization_mac", None)
    signed["authorization_mac"] = hmac.new(
        token.encode("utf-8"), shared._json_bytes(signed), hashlib.sha256
    ).hexdigest()
    return signed


def _validate_reservation(
    value: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_sha256: str,
    source_evidence_sha256: str,
    client: FormalizationVersionClient,
) -> dict[str, Any]:
    shared._check_exact_keys(
        value,
        {
            "schema_version",
            "kind",
            "phase",
            "api_base_url",
            "release_id",
            "manifest_sha256",
            "metadata_sha256",
            "files_sha256",
            "source_evidence_sha256",
            "source",
            "software",
            "authorization_mac",
        },
        "alpha.2 reservation",
    )
    if (
        value["schema_version"] != 2
        or value["kind"] != RESERVATION_KIND
        or value["phase"] != "reserved"
        or value["api_base_url"] != client.base_url
        or value["release_id"] != RELEASE_ID
        or value["manifest_sha256"] != manifest_sha256
        or value["source_evidence_sha256"] != source_evidence_sha256
    ):
        raise ZenodoError("alpha.2 reservation identity or hash binding changed")
    metadata_sha256, files_sha256 = _manifest_hashes(manifest)
    if (
        value["metadata_sha256"] != metadata_sha256
        or value["files_sha256"] != files_sha256
    ):
        raise ZenodoError("alpha.2 reservation manifest projection changed")
    if value["source"] != {
        "record_id": SOURCE_RECORD_ID,
        "concept_record_id": CONCEPT_RECORD_ID,
        "doi": SOURCE_VERSION_DOI,
    }:
        raise ZenodoError("alpha.2 reservation source changed")
    supplied_mac = value.get("authorization_mac")
    if not isinstance(supplied_mac, str) or shared.HEX_64.fullmatch(supplied_mac) is None:
        raise ZenodoError("alpha.2 reservation has no valid authorization MAC")
    unsigned = dict(value)
    unsigned.pop("authorization_mac", None)
    expected_mac = hmac.new(
        client.token.encode("utf-8"),
        shared._json_bytes(unsigned),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(supplied_mac, expected_mac):
        raise ZenodoError("alpha.2 reservation authorization MAC mismatch")
    software = value["software"]
    if not isinstance(software, dict):
        raise ZenodoError("alpha.2 reservation software entry is invalid")
    shared._check_exact_keys(
        software,
        {"deposition_id", "concept_record_id", "doi"},
        "alpha.2 reserved software",
    )
    record_id = _positive_id(software["deposition_id"], "reserved deposition_id")
    if record_id in PROTECTED_ZENODO_IDS:
        raise ZenodoError("alpha.2 reservation identifies a protected record")
    if software["concept_record_id"] != CONCEPT_RECORD_ID:
        raise ZenodoError("alpha.2 reservation changed concept")
    if software["doi"] != f"10.5281/zenodo.{record_id}":
        raise ZenodoError("alpha.2 reservation DOI and record ID disagree")
    return dict(software)


def _unknown_existing_concept_drafts(
    client: FormalizationVersionClient,
) -> list[int]:
    drafts: list[int] = []
    for item in client.list_owned_depositions():
        try:
            record_id = shared._record_id(item, "owner deposition inventory")
            concept_id = shared._concept_id(item, "owner deposition inventory")
        except ZenodoError:
            continue
        if (
            record_id != SOURCE_RECORD_ID
            and concept_id == CONCEPT_RECORD_ID
            and item.get("submitted") is not True
            and item.get("state") != "done"
        ):
            drafts.append(record_id)
    return sorted(set(drafts))


def reserve_release(
    client: FormalizationVersionClient,
    manifest: Mapping[str, Any],
    root: pathlib.Path,
    manifest_sha256: str,
    source_evidence: Mapping[str, Any],
    source_evidence_sha256: str,
    reservation_path: pathlib.Path,
) -> dict[str, Any]:
    """Reserve one alpha.2 draft without editing files or publishing it."""
    normalized = validate_manifest(dict(manifest), root)
    verified_evidence = validate_source_evidence(source_evidence)
    verify_manifest_files(normalized, root, client.token)
    if reservation_path.exists():
        existing, _ = shared._load_json_file(reservation_path, client.token)
        _validate_reservation(
            existing,
            normalized,
            manifest_sha256,
            source_evidence_sha256,
            client,
        )
        return existing
    source_public = client.check_live_software_source(
        SOURCE_RECORD_ID, CONCEPT_RECORD_ID
    )
    if _unknown_existing_concept_drafts(client):
        raise ZenodoError(
            "an unreserved editable draft already exists in the formalization concept"
        )
    draft = client.create_version()
    record_id, doi = _require_pristine_source_snapshot(
        draft, source_public, verified_evidence
    )
    client.authorize_draft(draft, record_id=record_id, doi=doi)
    client.check_live_software_source(SOURCE_RECORD_ID, CONCEPT_RECORD_ID)
    metadata_sha256, files_sha256 = _manifest_hashes(normalized)
    reservation = _sign_reservation(
        {
            "schema_version": 2,
            "kind": RESERVATION_KIND,
            "phase": "reserved",
            "api_base_url": client.base_url,
            "release_id": RELEASE_ID,
            "manifest_sha256": manifest_sha256,
            "metadata_sha256": metadata_sha256,
            "files_sha256": files_sha256,
            "source_evidence_sha256": source_evidence_sha256,
            "source": {
                "record_id": SOURCE_RECORD_ID,
                "concept_record_id": CONCEPT_RECORD_ID,
                "doi": SOURCE_VERSION_DOI,
            },
            "software": {
                "deposition_id": record_id,
                "concept_record_id": CONCEPT_RECORD_ID,
                "doi": doi,
            },
        },
        client.token,
    )
    shared._atomic_json(reservation_path, reservation, client.token)
    return reservation


def _result(
    manifest_sha256: str,
    source_evidence_sha256: str,
    metadata: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
    record_id: int,
    doi: str,
    *,
    published_by_this_run: bool,
) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "release_id": RELEASE_ID,
        "manifest_sha256": manifest_sha256,
        "source_evidence_sha256": source_evidence_sha256,
        "source_record_id": SOURCE_RECORD_ID,
        "concept_record_id": CONCEPT_RECORD_ID,
        "published_record_id": record_id,
        "doi": doi,
        "version": metadata["version"],
        "files": [
            {
                "name": entry["name"],
                "size": entry["size"],
                "md5": entry["md5"],
                "sha256": entry["sha256"],
            }
            for entry in entries
        ],
        "published_by_this_run": published_by_this_run,
        "public_record_verified": True,
    }


def _verify_public_lineage(
    client: FormalizationVersionClient,
    published: Mapping[str, Any],
    expected_record_id: int,
) -> None:
    if (
        shared._record_id(published, "published alpha.2") != expected_record_id
        or shared._concept_id(published, "published alpha.2")
        != CONCEPT_RECORD_ID
    ):
        raise ZenodoError("published alpha.2 identity or concept changed")
    _, source = client.get(f"/api/records/{SOURCE_RECORD_ID}")
    links = source.get("links")
    latest_url = links.get("latest") if isinstance(links, dict) else None
    if not isinstance(latest_url, str):
        raise ZenodoError("alpha.1 source has no public latest link")
    latest = client.get_with_validated_redirects(latest_url)
    if (
        shared._record_id(latest, "public latest alpha.2")
        != expected_record_id
        or shared._concept_id(latest, "public latest alpha.2")
        != CONCEPT_RECORD_ID
    ):
        raise ZenodoError("published alpha.2 did not become concept latest")


def finalize_release(
    client: FormalizationVersionClient,
    manifest: Mapping[str, Any],
    root: pathlib.Path,
    manifest_sha256: str,
    source_evidence: Mapping[str, Any],
    source_evidence_sha256: str,
    reservation: Mapping[str, Any],
    result_path: pathlib.Path,
) -> dict[str, Any]:
    """Reconcile, gate, publish, and verify only the reserved alpha.2 draft."""
    normalized = validate_manifest(dict(manifest), root)
    validate_source_evidence(source_evidence)
    software_reservation = _validate_reservation(
        reservation,
        normalized,
        manifest_sha256,
        source_evidence_sha256,
        client,
    )
    verified = verify_manifest_files(normalized, root, client.token)
    metadata = normalized["software"]["metadata"]
    entries = normalized["software"]["files"]
    record_id = software_reservation["deposition_id"]
    doi = software_reservation["doi"]
    state, current = client.get_deposition_or_record(record_id)
    if state == "published":
        public = client.wait_for_gated_record(
            record_id,
            metadata,
            entries,
            doi,
            published=True,
            initial=current,
        )
        _verify_public_lineage(client, public, record_id)
        result = _result(
            manifest_sha256,
            source_evidence_sha256,
            metadata,
            entries,
            record_id,
            doi,
            published_by_this_run=False,
        )
        shared._atomic_json(result_path, result, client.token)
        return result
    client.check_live_software_source(SOURCE_RECORD_ID, CONCEPT_RECORD_ID)
    client.authorize_draft(current, record_id=record_id, doi=doi)
    client.request(
        "PUT",
        f"/api/deposit/depositions/{record_id}",
        payload={"metadata": metadata},
        accept=(200, 202),
    )
    editable = client.wait_for_editable_metadata(record_id, metadata)
    client.authorize_draft(editable, record_id=record_id, doi=doi)
    client.delete_all_files(record_id, editable)
    client.upload_files(editable, entries, verified, "software")
    client.wait_for_gated_record(
        record_id, metadata, entries, doi, published=False
    )
    # Repeat every identity gate immediately before the irreversible action.
    client.check_live_software_source(SOURCE_RECORD_ID, CONCEPT_RECORD_ID)
    _, directly_bound = client.get(
        f"/api/deposit/depositions/{record_id}"
    )
    client.authorize_draft(directly_bound, record_id=record_id, doi=doi)
    client.wait_for_gated_record(
        record_id, metadata, entries, doi, published=False, initial=directly_bound
    )
    public = client.publish_and_poll(
        record_id, metadata, entries, doi, already_published=False
    )
    _verify_public_lineage(client, public, record_id)
    result = _result(
        manifest_sha256,
        source_evidence_sha256,
        metadata,
        entries,
        record_id,
        doi,
        published_by_this_run=True,
    )
    shared._atomic_json(result_path, result, client.token)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = shared.SafeArgumentParser(
        description="Reserve or finalize QIK-VRT Formalization v2 alpha.2."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=shared.SafeArgumentParser
    )
    reserve_parser = subparsers.add_parser("reserve")
    reserve_parser.add_argument("--manifest", required=True)
    reserve_parser.add_argument("--source-evidence", required=True)
    reserve_parser.add_argument("--reservation", required=True)
    finalize_parser = subparsers.add_parser("finalize")
    finalize_parser.add_argument("--manifest", required=True)
    finalize_parser.add_argument("--source-evidence", required=True)
    finalize_parser.add_argument("--reservation", required=True)
    finalize_parser.add_argument("--result", required=True)
    for command in subparsers.choices.values():
        command.add_argument(
            "--base-url", default=shared.DEFAULT_BASE_URL, help=argparse.SUPPRESS
        )
        command.add_argument("--repository-root", default=".")
        command.add_argument("--poll-attempts", type=int, default=30)
        command.add_argument("--poll-interval", type=float, default=2.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    token = os.environ.get(shared.TOKEN_ENVIRONMENT_VARIABLE, "")
    try:
        args = build_parser().parse_args(argv)
        root = pathlib.Path(args.repository_root).resolve(strict=True)
        if not root.is_dir():
            raise ZenodoError("repository-root must identify a directory")
        manifest_path = shared._external_path_in_root(
            root, args.manifest, must_exist=True
        )
        manifest_value, manifest_raw = shared._load_json_file(
            manifest_path, token
        )
        manifest = validate_manifest(manifest_value, root)
        manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
        evidence_path = shared._external_path_in_root(
            root, args.source_evidence, must_exist=True
        )
        evidence_value, evidence_raw = shared._load_json_file(
            evidence_path, token
        )
        source_evidence = validate_source_evidence(evidence_value)
        source_evidence_sha256 = hashlib.sha256(evidence_raw).hexdigest()
        client = FormalizationVersionClient(
            token,
            args.base_url,
            poll_attempts=args.poll_attempts,
            poll_interval=args.poll_interval,
        )
        reservation_path = shared._external_path_in_root(
            root, args.reservation, must_exist=args.command == "finalize"
        )
        if args.command == "reserve":
            outcome = reserve_release(
                client,
                manifest,
                root,
                manifest_sha256,
                source_evidence,
                source_evidence_sha256,
                reservation_path,
            )
            message = {
                "status": "ok",
                "phase": outcome["phase"],
                "record_id": outcome["software"]["deposition_id"],
                "doi": outcome["software"]["doi"],
            }
        else:
            reservation, _ = shared._load_json_file(reservation_path, token)
            result_path = shared._external_path_in_root(
                root, args.result, must_exist=False
            )
            outcome = finalize_release(
                client,
                manifest,
                root,
                manifest_sha256,
                source_evidence,
                source_evidence_sha256,
                reservation,
                result_path,
            )
            message = {
                "status": "ok",
                "phase": "published",
                "record_id": outcome["published_record_id"],
                "doi": outcome["doi"],
            }
        print(json.dumps(message, sort_keys=True))
        return 0
    except ZenodoError as exc:
        print("BLOCK " + shared.redact(str(exc), token), file=sys.stderr)
        return 1
    except Exception:
        print("BLOCK internal formalization alpha.2 Zenodo client failure", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
