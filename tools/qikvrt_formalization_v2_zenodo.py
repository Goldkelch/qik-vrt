#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed one-version Zenodo publisher for QIK-VRT formalization v2.

The only authorized lineage is current source record ``21498774`` in concept
``21488115``.  Earlier record ``21488116`` remains a historical version of
that concept but is never used as the ``newversion`` action target.  Before
any remote mutation, this client validates an exact
single-software-release manifest and reads every payload through the hardened
file/hash helpers in :mod:`tools.qikvrt_zenodo_actions`.

An interrupted run may resume only the source record's server-provided
``links.latest_draft`` or the one exact, read-only-audited recovery draft
created by the hash-bound publication run recorded in
``release/formalization-v2-draft-recovery.json``.  The client never accepts a
caller-provided deposition identifier.  Inherited draft files are deleted,
exact manifest bytes are uploaded and downloaded again for MD5/SHA-256
verification, exact client-controlled metadata values are gated, and only
then is the draft published.  The resulting public record is independently
gated afterward.

There is intentionally no command-line token option.  The bearer token is read
only from ``ZENODO_ACCESS_TOKEN`` by the shared transport.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any

try:
    from tools import qikvrt_zenodo_actions as zenodo
except ModuleNotFoundError:  # Direct ``python tools/<script>.py`` execution.
    import qikvrt_zenodo_actions as zenodo  # type: ignore[no-redef]


MANIFEST_SCHEMA = "qikvrt_formalization_v2_zenodo_manifest_v1"
RESULT_SCHEMA = "qikvrt_formalization_v2_zenodo_result_v1"
SOURCE_RECORD_ID = 21498774
CONCEPT_RECORD_ID = 21488115
SOURCE_VERSION_DOI = "10.5281/zenodo.21498774"
PRIOR_VERSION_RECORD_ID = 21488116
RECOVERY_DRAFT_RECORD_ID = 21501365
RECOVERY_DRAFT_DOI = "10.5281/zenodo.21501365"
RECOVERY_DRAFT_CREATED = "2026-07-23T00:33:37.286596+00:00"
RECOVERY_DRAFT_METADATA_SHA256 = (
    "dbd3cc9fb13448bab03c5b7c37dc3024eca1812aad3f0e11dea8da434b0662ea"
)
RECOVERY_DRAFT_FILE_FINGERPRINT = (
    (
        "qik-vrt-effect-ack-source-export-provenance.json",
        1082,
        "898967a157d5b54c4959037d4a4bb876",
    ),
    (
        "qik-vrt-v2026.07.22-effect-ack-universality-1.0.0-source.tar.gz",
        102094416,
        "645eb72d099a303da91ce37ceb3e95bf",
    ),
    (
        "qik-vrt-v2026.07.22-effect-ack-universality-1.0.0-source.tar.gz.sha256",
        130,
        "e786e1e10f859d1960519930438532e9",
    ),
)
MAX_RELEASE_FILES = 100
MAX_RELEASE_BYTES = zenodo.MAX_UPLOAD_BYTES

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


def _positive_id(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise zenodo.ZenodoError(f"{where} must be a positive integer")
    return value


def _validate_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not zenodo._is_json_value(value):
        raise zenodo.ZenodoError("software.metadata must be a JSON object")
    unknown = set(value) - ALLOWED_METADATA_KEYS
    missing = REQUIRED_METADATA_KEYS - set(value)
    if unknown or missing:
        detail: list[str] = []
        if missing:
            detail.append("missing=" + ",".join(sorted(missing)))
        if unknown:
            detail.append("unknown=" + ",".join(sorted(unknown)))
        raise zenodo.ZenodoError(
            "invalid software.metadata keys (" + "; ".join(detail) + ")"
        )
    zenodo._metadata_identity(value, "software")
    if value["upload_type"] != "software":
        raise zenodo.ZenodoError("software.metadata.upload_type must equal software")
    if not isinstance(value["description"], str) or not value["description"].strip():
        raise zenodo.ZenodoError(
            "software.metadata.description must be a non-empty string"
        )
    if "access_right" in value and value["access_right"] != "open":
        raise zenodo.ZenodoError(
            "software.metadata.access_right, when present, must equal open"
        )
    if "license" in value and (
        not isinstance(value["license"], str) or not value["license"].strip()
    ):
        raise zenodo.ZenodoError(
            "software.metadata.license must be a non-empty string"
        )
    if "language" in value and (
        not isinstance(value["language"], str)
        or re.fullmatch(r"[a-z]{3}", value["language"]) is None
    ):
        raise zenodo.ZenodoError(
            "software.metadata.language must be a lowercase ISO 639-3 code"
        )
    keywords = value.get("keywords")
    if keywords is not None and (
        not isinstance(keywords, list)
        or not keywords
        or not all(isinstance(item, str) and item.strip() for item in keywords)
        or len(keywords) != len(set(keywords))
    ):
        raise zenodo.ZenodoError(
            "software.metadata.keywords must be unique non-empty strings"
        )
    return dict(value)


def validate_manifest(value: dict[str, Any], root: pathlib.Path) -> dict[str, Any]:
    """Validate and normalize one exact software-release manifest."""
    zenodo._check_exact_keys(value, {"schema", "software"}, "manifest")
    if value["schema"] != MANIFEST_SCHEMA:
        raise zenodo.ZenodoError("manifest.schema is unsupported")
    software = value["software"]
    if not isinstance(software, dict):
        raise zenodo.ZenodoError("manifest.software must be one object")
    zenodo._check_exact_keys(
        software,
        {"source_record_id", "concept_record_id", "metadata", "files"},
        "software",
    )
    source = _positive_id(software["source_record_id"], "software.source_record_id")
    concept = _positive_id(
        software["concept_record_id"], "software.concept_record_id"
    )
    if source != SOURCE_RECORD_ID or concept != CONCEPT_RECORD_ID:
        raise zenodo.ZenodoError(
            "manifest lineage is not the authorized formalization source/concept"
        )
    metadata = _validate_metadata(software["metadata"])
    raw_files = software["files"]
    if (
        not isinstance(raw_files, list)
        or not 1 <= len(raw_files) <= MAX_RELEASE_FILES
    ):
        raise zenodo.ZenodoError(
            f"software.files must contain between 1 and {MAX_RELEASE_FILES} files"
        )
    files = [
        zenodo._validate_file_entry(item, root, f"software.files[{index}]")
        for index, item in enumerate(raw_files)
    ]
    if len({entry["name"] for entry in files}) != len(files):
        raise zenodo.ZenodoError("software.files contains duplicate upload names")
    if len({entry["path"] for entry in files}) != len(files):
        raise zenodo.ZenodoError("software.files contains duplicate repository paths")
    total_size = sum(entry["size"] for entry in files)
    if total_size > MAX_RELEASE_BYTES:
        raise zenodo.ZenodoError("software release exceeds the total upload size limit")
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
    """Read and hash-gate all bytes before the first Zenodo mutation."""
    verified: dict[tuple[str, str], bytes] = {}
    for entry in manifest["software"]["files"]:
        verified[("software", entry["name"])] = zenodo._file_bytes(
            root, entry, token
        )
    return verified


def _latest_draft_url(value: Mapping[str, Any], client: zenodo.ZenodoClient) -> str | None:
    links = value.get("links")
    candidate = links.get("latest_draft") if isinstance(links, dict) else None
    if candidate is None:
        return None
    if not isinstance(candidate, str):
        raise zenodo.ZenodoError("source links.latest_draft is not a URL")
    return zenodo.validate_response_url(candidate, client.base_url)


def _new_version_draft_url(
    value: Mapping[str, Any],
    client: zenodo.ZenodoClient,
    *,
    source_owner_view: bool = False,
) -> str | None:
    """Return only a ``latest_draft`` link for a distinct new version.

    Zenodo's legacy owner view can expose the already-published source
    deposition itself as ``links.latest_draft``.  That self-link is not an
    editable new-version draft.  It is therefore treated as absence, but only
    a demonstrably published source owner view may use that representation.
    """
    latest_draft_url = _latest_draft_url(value, client)
    if latest_draft_url is None:
        return None
    linked_id = zenodo._id_from_api_url(
        latest_draft_url, client.base_url, "/api/deposit/depositions"
    )
    if linked_id != SOURCE_RECORD_ID:
        return latest_draft_url
    if source_owner_view and not (
        value.get("submitted") is True or value.get("state") == "done"
    ):
        raise zenodo.ZenodoError(
            "source self latest_draft is not a completed published deposition"
        )
    return None


def _validate_editable_draft(
    draft: Mapping[str, Any],
    latest_draft_url: str,
    client: zenodo.ZenodoClient,
) -> dict[str, Any]:
    linked_id = zenodo._id_from_api_url(
        latest_draft_url, client.base_url, "/api/deposit/depositions"
    )
    draft_id = zenodo._record_id(draft, "formalization latest_draft")
    if draft_id != linked_id or draft_id == SOURCE_RECORD_ID:
        raise zenodo.ZenodoError(
            "source latest_draft URL and returned draft do not identify one new version"
        )
    if zenodo._concept_id(draft, "formalization latest_draft") != CONCEPT_RECORD_ID:
        raise zenodo.ZenodoError("source latest_draft changed formalization concept")
    if draft.get("submitted") is True or draft.get("state") == "done":
        raise zenodo.ZenodoError("source latest_draft is not editable")
    return dict(draft)


def _get_linked_draft(
    client: zenodo.ZenodoClient, latest_draft_url: str
) -> dict[str, Any]:
    _, draft = client.get(latest_draft_url)
    return _validate_editable_draft(draft, latest_draft_url, client)


def _require_existing_draft_identity(
    draft: Mapping[str, Any], target_metadata: Mapping[str, Any]
) -> None:
    actual_metadata = draft.get("metadata")
    if not isinstance(actual_metadata, dict):
        raise zenodo.ZenodoError(
            "existing source latest_draft has no metadata object"
        )
    # A resumable draft is one that a prior run already initialized for this
    # exact release.  Zenodo adds the DOI reservation object; every other key
    # must be present in the closed client-controlled manifest.  In
    # particular, an unrelated draft that merely shares title/version/creator
    # fields must never be overwritten.
    unknown = set(actual_metadata) - set(target_metadata) - {"prereserve_doi"}
    if unknown:
        raise zenodo.ZenodoError(
            "existing source latest_draft contains metadata outside this exact release"
        )
    if not zenodo._metadata_matches(actual_metadata, target_metadata):
        raise zenodo.ZenodoError(
            "existing source latest_draft metadata does not match this exact release"
        )
    if actual_metadata.get("upload_type") != "software":
        raise zenodo.ZenodoError(
            "existing source latest_draft is not an identifiable software release"
        )


def _recovery_draft_url(client: zenodo.ZenodoClient) -> str:
    return zenodo.validate_response_url(
        f"{client.base_url}/deposit/depositions/{RECOVERY_DRAFT_RECORD_ID}",
        client.base_url,
    )


def _require_recovery_draft_invariants(draft: Mapping[str, Any]) -> None:
    """Require the audited identity/state in every recovery phase."""
    metadata = draft.get("metadata")
    reserved = metadata.get("prereserve_doi") if isinstance(metadata, dict) else None
    if (
        zenodo._record_id(draft, "formalization recovery draft")
        != RECOVERY_DRAFT_RECORD_ID
        or zenodo._concept_id(draft, "formalization recovery draft")
        != CONCEPT_RECORD_ID
        or draft.get("created") != RECOVERY_DRAFT_CREATED
        or draft.get("submitted") is not False
        or draft.get("state") != "unsubmitted"
        or not isinstance(reserved, dict)
        or reserved.get("doi") != RECOVERY_DRAFT_DOI
    ):
        raise zenodo.ZenodoError(
            "audited formalization recovery draft changed identity or state"
        )


def _require_exact_recovery_draft_identity(draft: Mapping[str, Any]) -> None:
    """Accept only the immutable fingerprint from the GET-only recovery audit."""
    _require_recovery_draft_invariants(draft)
    metadata = draft.get("metadata")
    metadata_sha256 = (
        hashlib.sha256(zenodo._json_bytes(metadata)).hexdigest()
        if isinstance(metadata, dict)
        else None
    )
    files = draft.get("files")
    fingerprint: list[tuple[str, int, str]] = []
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                fingerprint = []
                break
            name = item.get("filename", item.get("key"))
            size = item.get("filesize", item.get("size"))
            checksum = item.get("checksum")
            if isinstance(size, str) and size.isdecimal():
                size = int(size)
            if isinstance(checksum, str) and checksum.startswith("md5:"):
                checksum = checksum[4:]
            if (
                not isinstance(name, str)
                or not isinstance(size, int)
                or isinstance(size, bool)
                or not isinstance(checksum, str)
                or zenodo.HEX_32.fullmatch(checksum) is None
            ):
                fingerprint = []
                break
            fingerprint.append((name, size, checksum))
    if (
        metadata_sha256 != RECOVERY_DRAFT_METADATA_SHA256
        or tuple(sorted(fingerprint)) != RECOVERY_DRAFT_FILE_FINGERPRINT
    ):
        raise zenodo.ZenodoError(
            "audited formalization recovery draft changed identity or state"
        )


def _require_resumable_draft_identity(
    draft: Mapping[str, Any], target_metadata: Mapping[str, Any]
) -> None:
    _require_recovery_draft_invariants(draft)
    try:
        _require_existing_draft_identity(draft, target_metadata)
        return
    except zenodo.ZenodoError:
        pass
    _require_exact_recovery_draft_identity(draft)


def _recover_exact_audited_draft(
    client: zenodo.ZenodoClient,
    target_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    recovery_url = _recovery_draft_url(client)
    status, candidate = client.get(recovery_url, accept=(200, 403, 404))
    if status == 404:
        raise zenodo.ZenodoError("audited formalization recovery draft is missing")
    if status != 200:
        raise zenodo.ZenodoError("audited formalization recovery draft is unreadable")
    draft = _validate_editable_draft(candidate, recovery_url, client)
    _require_resumable_draft_identity(draft, target_metadata)
    return draft, recovery_url


def resolve_or_create_source_latest_draft(
    client: zenodo.ZenodoClient,
    target_metadata: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    """Resume only ``21498774``'s release-identified latest draft."""
    client.check_live_software_source(SOURCE_RECORD_ID, CONCEPT_RECORD_ID)
    status, source_owner_view = client.get(
        f"/api/deposit/depositions/{SOURCE_RECORD_ID}",
        accept=(200, 403, 404),
    )
    if status == 200:
        if (
            zenodo._record_id(source_owner_view, "source owner view")
            != SOURCE_RECORD_ID
            or zenodo._concept_id(source_owner_view, "source owner view")
            != CONCEPT_RECORD_ID
        ):
            raise zenodo.ZenodoError("source owner view changed lineage")
        latest_draft_url = _new_version_draft_url(
            source_owner_view, client, source_owner_view=True
        )
        if latest_draft_url is not None:
            draft = _get_linked_draft(client, latest_draft_url)
            _require_resumable_draft_identity(draft, target_metadata)
            return draft, latest_draft_url

    recovered = _recover_exact_audited_draft(client, target_metadata)
    # The public latest pointer was checked above; repeat it immediately before
    # returning the only draft this recovery release is permitted to mutate.
    client.check_live_software_source(SOURCE_RECORD_ID, CONCEPT_RECORD_ID)
    return recovered


def _reserved_new_version_doi(draft: Mapping[str, Any]) -> str:
    metadata = draft.get("metadata")
    reserved = metadata.get("prereserve_doi") if isinstance(metadata, dict) else None
    doi = reserved.get("doi") if isinstance(reserved, dict) else None
    if not isinstance(doi, str) or not zenodo.DOI.fullmatch(doi):
        raise zenodo.ZenodoError(
            "formalization latest_draft has no authoritative prereserved DOI"
        )
    if doi == SOURCE_VERSION_DOI:
        raise zenodo.ZenodoError("formalization latest_draft reused the source version DOI")
    draft_id = zenodo._record_id(draft, "formalization latest_draft")
    if doi != f"10.5281/zenodo.{draft_id}":
        raise zenodo.ZenodoError(
            "formalization latest_draft DOI is not bound to its record ID"
        )
    return doi


def _assert_still_source_latest_draft(
    client: zenodo.ZenodoClient,
    expected_url: str,
    expected_id: int,
    metadata: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
    expected_doi: str,
) -> None:
    # Re-resolve the public latest pointer immediately before the irreversible
    # action.  It must still identify the exact published source version.
    client.check_live_software_source(SOURCE_RECORD_ID, CONCEPT_RECORD_ID)
    status, source = client.get(
        f"/api/deposit/depositions/{SOURCE_RECORD_ID}", accept=(200, 202)
    )
    if (
        status != 200
        or zenodo._record_id(source, "source owner view") != SOURCE_RECORD_ID
        or zenodo._concept_id(source, "source owner view") != CONCEPT_RECORD_ID
    ):
        raise zenodo.ZenodoError("source owner view is unavailable before publication")
    actual_url = _new_version_draft_url(source, client, source_owner_view=True)
    if actual_url is not None and zenodo._id_from_api_url(
        actual_url, client.base_url, "/api/deposit/depositions"
    ) != expected_id:
        raise zenodo.ZenodoError("source latest_draft ID changed before publication")
    expected_url_id = zenodo._id_from_api_url(
        expected_url, client.base_url, "/api/deposit/depositions"
    )
    if expected_url_id != expected_id:
        raise zenodo.ZenodoError("authorized draft URL changed before publication")
    # When the owner source remains self-linked, the directly bound draft must
    # still be readable, editable, and in the same concept immediately before
    # the irreversible publish action.
    directly_bound = _get_linked_draft(client, expected_url)
    _require_recovery_draft_invariants(directly_bound)
    fully_gated = client.wait_for_gated_record(
        expected_id,
        metadata,
        entries,
        expected_doi,
        published=False,
    )
    _require_recovery_draft_invariants(fully_gated)


def _verify_public_lineage(
    client: zenodo.ZenodoClient,
    published: Mapping[str, Any],
    published_id: int,
) -> None:
    if zenodo._concept_id(published, "published formalization") != CONCEPT_RECORD_ID:
        raise zenodo.ZenodoError("published formalization changed concept")
    if published_id == SOURCE_RECORD_ID:
        raise zenodo.ZenodoError("publication did not create a new formalization version")
    for attempt in range(client.poll_attempts):
        status, source = client.get(
            f"/api/records/{SOURCE_RECORD_ID}", accept=(200, 202, 404)
        )
        if status == 200:
            if zenodo._record_id(source, "public source") != SOURCE_RECORD_ID:
                raise zenodo.ZenodoError("public source record ID changed")
            if zenodo._concept_id(source, "public source") != CONCEPT_RECORD_ID:
                raise zenodo.ZenodoError("public source concept changed")
            links = source.get("links")
            latest_url = links.get("latest") if isinstance(links, dict) else None
            if not isinstance(latest_url, str):
                raise zenodo.ZenodoError("public source has no latest-version link")
            try:
                latest = client.get_with_validated_redirects(latest_url)
            except zenodo.ZenodoError:
                latest = {}
            if latest and (
                zenodo._record_id(latest, "public latest formalization")
                == published_id
                and zenodo._concept_id(latest, "public latest formalization")
                == CONCEPT_RECORD_ID
            ):
                return
        if attempt + 1 < client.poll_attempts:
            client.sleeper(client.poll_interval)
    raise zenodo.ZenodoError(
        "published formalization did not become the source record's public latest version"
    )


def _current_public_latest(client: zenodo.ZenodoClient) -> dict[str, Any]:
    _, source = client.get(f"/api/records/{SOURCE_RECORD_ID}")
    if zenodo._record_id(source, "public source") != SOURCE_RECORD_ID:
        raise zenodo.ZenodoError("public source record ID changed")
    if zenodo._concept_id(source, "public source") != CONCEPT_RECORD_ID:
        raise zenodo.ZenodoError("public source concept changed")
    links = source.get("links")
    latest_url = links.get("latest") if isinstance(links, dict) else None
    if not isinstance(latest_url, str):
        raise zenodo.ZenodoError("public source has no latest-version link")
    latest = client.get_with_validated_redirects(latest_url)
    if zenodo._concept_id(latest, "public latest formalization") != CONCEPT_RECORD_ID:
        raise zenodo.ZenodoError("public latest formalization changed concept")
    return latest


def _result(
    manifest_sha256: str,
    metadata: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
    published_id: int,
    doi: str,
    *,
    published_by_this_run: bool,
) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "manifest_sha256": manifest_sha256,
        "source_record_id": SOURCE_RECORD_ID,
        "concept_record_id": CONCEPT_RECORD_ID,
        "published_record_id": published_id,
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


def publish_release(
    client: zenodo.ZenodoClient,
    manifest: Mapping[str, Any],
    root: pathlib.Path,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Reconcile, publish, and verify exactly one formalization version."""
    if (
        not isinstance(manifest_sha256, str)
        or zenodo.HEX_64.fullmatch(manifest_sha256) is None
    ):
        raise zenodo.ZenodoError("manifest SHA-256 must be lowercase hexadecimal")
    normalized = validate_manifest(dict(manifest), root)
    serialized = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    if client.token and client.token in serialized:
        raise zenodo.ZenodoError("manifest contains the Zenodo access token")
    verified = verify_manifest_files(normalized, root, client.token)
    software = normalized["software"]
    metadata = software["metadata"]
    entries = software["files"]

    # Completed-run idempotency: after publication the authorized source is no
    # longer the concept's latest record.  Reconcile only that server-resolved
    # public latest record and accept it only if every manifest-controlled
    # metadata value and every exact file hash pass the public-record gate.
    current_latest = _current_public_latest(client)
    current_latest_id = zenodo._record_id(
        current_latest, "public latest formalization"
    )
    if current_latest_id != SOURCE_RECORD_ID:
        current_doi = zenodo._doi_from_deposition(
            current_latest, "public latest formalization"
        )
        if current_doi != f"10.5281/zenodo.{current_latest_id}":
            raise zenodo.ZenodoError(
                "public latest formalization DOI is not bound to its record ID"
            )
        client.wait_for_gated_record(
            current_latest_id,
            metadata,
            entries,
            current_doi,
            published=True,
            initial=current_latest,
        )
        return _result(
            manifest_sha256,
            metadata,
            entries,
            current_latest_id,
            current_doi,
            published_by_this_run=False,
        )

    draft, latest_draft_url = resolve_or_create_source_latest_draft(
        client, metadata
    )
    draft_id = zenodo._record_id(draft, "formalization latest_draft")
    expected_doi = _reserved_new_version_doi(draft)

    # Metadata and files are fully reconciled while the record is editable.
    client.request(
        "PUT",
        f"/api/deposit/depositions/{draft_id}",
        payload={"metadata": metadata},
        accept=(200, 202),
    )
    editable = client.wait_for_editable_metadata(draft_id, metadata)
    client.delete_all_files(draft_id, editable)
    client.upload_files(editable, entries, verified, "software")
    client.wait_for_gated_record(
        draft_id,
        metadata,
        entries,
        expected_doi,
        published=False,
    )

    # Revalidate provenance after all uploads and immediately before publish.
    _assert_still_source_latest_draft(
        client,
        latest_draft_url,
        draft_id,
        metadata,
        entries,
        expected_doi,
    )
    public = client.publish_and_poll(
        draft_id,
        metadata,
        entries,
        expected_doi,
        already_published=False,
    )
    _verify_public_lineage(client, public, draft_id)

    return _result(
        manifest_sha256,
        metadata,
        entries,
        draft_id,
        expected_doi,
        published_by_this_run=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = zenodo.SafeArgumentParser(
        description="Publish one hash-bound QIK-VRT formalization v2 Zenodo version."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--poll-attempts", type=int, default=30)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument(
        "--base-url", default=zenodo.DEFAULT_BASE_URL, help=argparse.SUPPRESS
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    token = os.environ.get(zenodo.TOKEN_ENVIRONMENT_VARIABLE, "")
    try:
        args = build_parser().parse_args(argv)
        root = pathlib.Path(args.repository_root).resolve(strict=True)
        if not root.is_dir():
            raise zenodo.ZenodoError("repository-root must identify a directory")
        manifest_path = zenodo._external_path_in_root(
            root, args.manifest, must_exist=True
        )
        result_path = zenodo._external_path_in_root(
            root, args.result, must_exist=False
        )
        manifest_value, manifest_raw = zenodo._load_json_file(manifest_path, token)
        normalized = validate_manifest(manifest_value, root)
        manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
        client = zenodo.ZenodoClient(
            token,
            args.base_url,
            poll_attempts=args.poll_attempts,
            poll_interval=args.poll_interval,
        )
        result = publish_release(client, normalized, root, manifest_sha256)
        zenodo._atomic_json(result_path, result, token)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "record_id": result["published_record_id"],
                    "doi": result["doi"],
                },
                sort_keys=True,
            )
        )
        return 0
    except zenodo.ZenodoError as exc:
        print("BLOCK " + zenodo.redact(str(exc), token), file=sys.stderr)
        return 1
    except Exception:
        print("BLOCK internal Zenodo client failure", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
