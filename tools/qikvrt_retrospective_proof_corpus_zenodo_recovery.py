#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed recovery state machine for the frozen proof-corpus publication.

The state machine is transport-testable through small protocols.  Its
``--execute`` command wires those protocols to pinned GitHub Git-Data and
production Zenodo adapters.  Every effect intent is remotely durable before
the effect; every effect has one mutation call followed by one exact readback.
A restored mutation intent is always reconciled read-only and can never issue
the mutation again.

The generic ``zenodo-publication.json`` v2 receipt remains the final public
authority.  Fine-grained upload intents live in the separate
``zenodo-recovery.json`` journal so the generic evidence schema is not widened.
"""

from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime
import hashlib
import json
import math
import os
import pathlib
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any, NoReturn, Protocol

from tools import qikvrt_retrospective_proof_corpus_zenodo_candidate as candidate
from tools import (
    qikvrt_retrospective_proof_corpus_zenodo_publication_controls as controls,
)
from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_publish as publish
from tools import qikvrt_integrity as integrity


ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY = controls.REPOSITORY
PUBLICATION_ID = controls.PUBLICATION_ID
AUTHORIZATION_ID = controls.AUTHORIZATION_ID
SOURCE_HEAD = controls.SOURCE_HEAD
CONTROL_BASE_HEAD = "c556382c89d32faf7bdd193d8e58c4a190ebc3cc"
EXPECTED_UPLOADS = controls.EXPECTED_UPLOADS
EXPECTED_UPLOAD_BYTES = 221_808_115
UPLOAD_CONTRACT_SHA256 = controls.UPLOAD_CONTRACT_SHA256
METADATA_SHA256 = controls.METADATA_SHA256
STATEMENT_SHA256 = hashlib.sha256(
    controls.exact_statement().encode("utf-8")
).hexdigest()

CONTROL_REL = controls.CONTROL_REL
MANIFEST_RELATIVE = (CONTROL_REL / controls.MANIFEST_BASENAME).as_posix()
RECOVERY_RELATIVE = (CONTROL_REL / "zenodo-recovery.json").as_posix()
EVIDENCE_RELATIVE = (CONTROL_REL / controls.EVIDENCE_BASENAME).as_posix()
PUBLICATION_REF = "refs/heads/publication/retrospective-proof-corpus-v3"
RECOVERY_REF_PREFIX = (
    "refs/heads/qikvrt-recovery/retrospective-proof-corpus-v3/"
)

JOURNAL_SCHEMA = "qikvrt_retrospective_proof_corpus_zenodo_recovery_v1"
GENERIC_EVIDENCE_SCHEMA = publish.EVIDENCE_SCHEMA_V2
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DOI = re.compile(r"^10\.5281/zenodo\.[1-9][0-9]*$")
PHASES = (
    "authorization_consumed",
    "create_requested",
    "record_created",
    "prepared",
    "publish_requested",
    "public_verified",
)
RECOVERY_PHASES = PHASES[:-1]
MAX_RECOVERY_CHECKPOINTS = 135
GITHUB_TOKEN_ENVIRONMENT_VARIABLE = "GITHUB_TOKEN"
ZENODO_TOKEN_ENVIRONMENT_VARIABLE = zenodo.TOKEN_ENVIRONMENT_VARIABLE
GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPOSITORY_API = "/repos/Goldkelch/qik-vrt"
MAX_GITHUB_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_PUBLIC_JSON_BYTES = 8 * 1024 * 1024
RECOVERY_COMMIT_SUBJECT = "zenodo: persist retrospective proof corpus recovery"
PUBLICATION_COMMIT_SUBJECT = (
    "zenodo: persist retrospective proof corpus publication"
)
RECEIPT_AUTHOR = {
    "name": "qik-vrt-zenodo-publication[bot]",
    "email": "qik-vrt-zenodo-publication[bot]@users.noreply.github.com",
}
INTEGRITY_PATHS = (
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)


class CorpusRecoveryError(RuntimeError):
    """A fail-closed contract or recovery-state violation."""


class RemoteMutationError(RuntimeError):
    """A one-shot remote mutation failed or returned an ambiguous outcome."""


class AmbiguousMutation(RemoteMutationError):
    """The one permitted mutation may or may not have reached its remote."""


def fail(message: str) -> NoReturn:
    raise CorpusRecoveryError(message)


def _validate_unicode_scalars(value: Any, label: str) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            fail(f"{label} contains a Unicode surrogate")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            fail(f"{label} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_unicode_scalars(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_unicode_scalars(key, f"{label} key")
            _validate_unicode_scalars(item, f"{label}.{key}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail("strict recovery JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    fail("strict recovery JSON contains a non-finite number: " + value)


def strict_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw or len(raw) > 8 * 1024 * 1024:
        fail(f"{label} bytes are absent or exceed the bound")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f"{label} is not strict UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        fail(f"{label} must contain one JSON object")
    _validate_unicode_scalars(value, label)
    return value


def canonical_json_bytes(value: Any) -> bytes:
    _validate_unicode_scalars(value, "canonical recovery value")
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        fail(f"recovery value is not canonical JSON: {exc}")


def journal_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


@dataclasses.dataclass(frozen=True)
class UploadIdentity:
    index: int
    path: str
    name: str
    size: int
    md5: str
    sha256: str
    git_blob_sha: str

    def server_identity(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "size": self.size,
            "md5": self.md5,
            "sha256": self.sha256,
        }

    def generic_file(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "size": self.size,
            "md5": self.md5,
            "sha256": self.sha256,
            "git_blob_sha": self.git_blob_sha,
        }


@dataclasses.dataclass(frozen=True)
class FrozenUploadContract:
    entries: tuple[UploadIdentity, ...]
    canonical_sha256: str
    fileset_sha256: str
    total_bytes: int
    metadata_sha256: str
    title: str
    version: str


def validate_frozen_contract(contract: FrozenUploadContract) -> None:
    if (
        len(contract.entries) != EXPECTED_UPLOADS
        or contract.canonical_sha256 != UPLOAD_CONTRACT_SHA256
        or contract.total_bytes != EXPECTED_UPLOAD_BYTES
        or contract.metadata_sha256 != METADATA_SHA256
        or not contract.title
        or not contract.version
    ):
        fail("frozen upload contract summary differs")
    names: set[str] = set()
    paths: set[str] = set()
    expected_files: list[dict[str, Any]] = []
    total = 0
    for index, entry in enumerate(contract.entries):
        if (
            entry.index != index
            or not entry.path
            or not entry.name
            or pathlib.PurePosixPath(entry.name).name != entry.name
            or entry.path in paths
            or entry.name in names
            or entry.size < 0
            or re.fullmatch(r"[0-9a-f]{32}", entry.md5) is None
            or HEX64.fullmatch(entry.sha256) is None
            or HEX40.fullmatch(entry.git_blob_sha) is None
        ):
            fail(f"frozen upload entry {index} differs")
        paths.add(entry.path)
        names.add(entry.name)
        total += entry.size
        expected_files.append(entry.generic_file())
    if total != contract.total_bytes:
        fail("frozen upload byte sum differs")
    if hashlib.sha256(canonical_json_bytes(expected_files)).hexdigest() != (
        contract.fileset_sha256
    ):
        fail("frozen upload fileset digest differs")


def load_frozen_contract() -> FrozenUploadContract:
    """Resolve and hash the exact 65 source-head-bound upload mappings."""
    _matrix, metadata, _bundle, files = controls.load_upload_contract()
    entries: list[UploadIdentity] = []
    for index, item in enumerate(files):
        raw_path = item["path"]
        path = ROOT.joinpath(*pathlib.PurePosixPath(raw_path).parts)
        raw = zenodo.read_regular_file(path, zenodo.MAX_UPLOAD_BYTES)
        observed_blob = git_blob_sha1(raw)
        if observed_blob != item["git_blob_sha"]:
            fail("control upload Git blob differs for " + raw_path)
        entries.append(
            UploadIdentity(
                index=index,
                path=raw_path,
                name=item["name"],
                size=len(raw),
                md5=hashlib.md5(raw).hexdigest(),  # noqa: S324 - Zenodo checksum
                sha256=hashlib.sha256(raw).hexdigest(),
                git_blob_sha=observed_blob,
            )
        )
    fileset = [entry.generic_file() for entry in entries]
    contract = FrozenUploadContract(
        entries=tuple(entries),
        canonical_sha256=UPLOAD_CONTRACT_SHA256,
        fileset_sha256=hashlib.sha256(canonical_json_bytes(fileset)).hexdigest(),
        total_bytes=sum(entry.size for entry in entries),
        metadata_sha256=candidate.canonical_json_sha256(metadata),
        title=str(metadata.get("title", "")),
        version=str(metadata.get("version", "")),
    )
    validate_frozen_contract(contract)
    return contract


@dataclasses.dataclass(frozen=True)
class ConsumptionIdentity:
    key: str
    ref: str
    tag_object: str
    execution_head: str
    acquisition: str = "CREATE_ONLY_NONFORCE_READBACK_VERIFIED"


@dataclasses.dataclass(frozen=True)
class RecordIdentity:
    record_id: int
    doi: str


@dataclasses.dataclass(frozen=True)
class ServerFile:
    name: str
    size: int
    md5: str
    sha256: str


@dataclasses.dataclass(frozen=True)
class DraftSnapshot:
    record: RecordIdentity
    metadata_sha256: str
    files: tuple[ServerFile, ...]
    editable: bool = True


@dataclasses.dataclass(frozen=True)
class PublicTransportAttestation:
    anonymous: bool = True
    proxy_handler: str = "DISABLED"
    redirects: str = "REJECTED"
    tls: str = "VERIFIED_DEFAULT_CONTEXT"
    authorization_header: bool = False
    cookie_header: bool = False
    readback_count: int = 1


@dataclasses.dataclass(frozen=True)
class PublicSnapshot:
    record: RecordIdentity
    conceptdoi: str
    metadata_sha256: str
    files: tuple[ServerFile, ...]
    transport: PublicTransportAttestation


@dataclasses.dataclass(frozen=True)
class RecoveryContext:
    execution_head: str
    manifest_sha256: str
    consumption: ConsumptionIdentity
    recovery_ref: str
    publication_ref: str = PUBLICATION_REF


def make_context(
    execution_head: str,
    manifest_sha256: str,
    consumption_key: str,
    tag_object: str,
) -> RecoveryContext:
    if HEX40.fullmatch(execution_head) is None:
        fail("execution head is not an exact Git commit")
    if HEX64.fullmatch(manifest_sha256) is None:
        fail("manifest digest is invalid")
    expected_key = publish._authorization_consumption_key(
        REPOSITORY,
        AUTHORIZATION_ID,
        PUBLICATION_ID,
        STATEMENT_SHA256,
    )["value"]
    if consumption_key != expected_key:
        fail("consumption key differs from the exact authorization statement")
    if HEX40.fullmatch(tag_object) is None:
        fail("consumption tag object is invalid")
    tag_ref = publish._remote_consumption_ref(consumption_key)
    recovery_ref = RECOVERY_REF_PREFIX + consumption_key
    consumption = ConsumptionIdentity(
        key=consumption_key,
        ref=tag_ref,
        tag_object=tag_object,
        execution_head=execution_head,
    )
    context = RecoveryContext(
        execution_head=execution_head,
        manifest_sha256=manifest_sha256,
        consumption=consumption,
        recovery_ref=recovery_ref,
    )
    validate_context(context)
    return context


def validate_context(context: RecoveryContext) -> None:
    consumption = context.consumption
    if (
        HEX40.fullmatch(context.execution_head) is None
        or HEX64.fullmatch(context.manifest_sha256) is None
        or HEX64.fullmatch(consumption.key) is None
        or consumption.ref != publish._remote_consumption_ref(consumption.key)
        or HEX40.fullmatch(consumption.tag_object) is None
        or consumption.execution_head != context.execution_head
        or consumption.acquisition != "CREATE_ONLY_NONFORCE_READBACK_VERIFIED"
        or context.recovery_ref != RECOVERY_REF_PREFIX + consumption.key
        or context.publication_ref != PUBLICATION_REF
    ):
        fail("recovery context differs from its exact refs or authorization")


def _context_value(context: RecoveryContext) -> dict[str, Any]:
    return {
        "repository": REPOSITORY,
        "publication_id": PUBLICATION_ID,
        "authorization_id": AUTHORIZATION_ID,
        "source_head": SOURCE_HEAD,
        "execution_head": context.execution_head,
        "manifest_path": MANIFEST_RELATIVE,
        "manifest_sha256": context.manifest_sha256,
        "authorization_statement_sha256": STATEMENT_SHA256,
    }


def _consumption_value(context: RecoveryContext) -> dict[str, Any]:
    value = dataclasses.asdict(context.consumption)
    return {
        "key": value["key"],
        "ref": value["ref"],
        "tag_object": value["tag_object"],
        "execution_head": value["execution_head"],
        "acquisition": value["acquisition"],
    }


def _contract_value(contract: FrozenUploadContract) -> dict[str, Any]:
    return {
        "entry_count": len(contract.entries),
        "total_bytes": contract.total_bytes,
        "ordered_entries_canonical_sha256": contract.canonical_sha256,
        "fileset_sha256": contract.fileset_sha256,
        "metadata_sha256": contract.metadata_sha256,
    }


def _effect_value() -> dict[str, Any]:
    return {
        "state": "EFFECT_ACK_CONTINUE",
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
        "mirror_persisted": False,
        "reciprocal_equality_verified": False,
    }


def observed_preparation(prefix_count: int) -> dict[str, Any]:
    return {
        "state": "OBSERVED_PREFIX",
        "verified_prefix_count": prefix_count,
        "pending_upload": None,
    }


def upload_intent(entry: UploadIdentity, prefix_count: int) -> dict[str, Any]:
    return {
        "state": "UPLOAD_INTENT",
        "verified_prefix_count": prefix_count,
        "pending_upload": {
            "index": entry.index,
            "name": entry.name,
            "size": entry.size,
            "sha256": entry.sha256,
        },
    }


def make_journal(
    contract: FrozenUploadContract,
    context: RecoveryContext,
    *,
    phase: str,
    sequence: int,
    record: RecordIdentity | None = None,
    preparation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    value = {
        "schema": JOURNAL_SCHEMA,
        "phase": phase,
        "sequence": sequence,
        "context": _context_value(context),
        "upload_contract": _contract_value(contract),
        "consumption": _consumption_value(context),
        "refs": {
            "recovery": context.recovery_ref,
            "publication": context.publication_ref,
        },
        "record": (
            None
            if record is None
            else {"record_id": record.record_id, "doi": record.doi}
        ),
        "preparation": None if preparation is None else dict(preparation),
        "effect": _effect_value(),
    }
    validate_journal(value, contract, context)
    return value


def _record_from_value(value: Any) -> RecordIdentity | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"record_id", "doi"}:
        fail("recovery record identity keys differ")
    record_id = value["record_id"]
    doi = value["doi"]
    if (
        isinstance(record_id, bool)
        or not isinstance(record_id, int)
        or record_id <= 0
        or not isinstance(doi, str)
        or DOI.fullmatch(doi) is None
        or doi != f"10.5281/zenodo.{record_id}"
    ):
        fail("recovery record identity differs")
    return RecordIdentity(record_id, doi)


def _validate_preparation(
    value: Any,
    contract: FrozenUploadContract,
) -> tuple[str, int, Mapping[str, Any] | None]:
    if not isinstance(value, dict) or set(value) != {
        "state",
        "verified_prefix_count",
        "pending_upload",
    }:
        fail("recovery preparation keys differ")
    state = value["state"]
    count = value["verified_prefix_count"]
    pending = value["pending_upload"]
    if (
        state not in {"OBSERVED_PREFIX", "UPLOAD_INTENT"}
        or isinstance(count, bool)
        or not isinstance(count, int)
        or not 0 <= count <= EXPECTED_UPLOADS
    ):
        fail("recovery preparation state or prefix differs")
    if state == "OBSERVED_PREFIX":
        if pending is not None:
            fail("observed prefix may not retain an upload intent")
        return state, count, None
    if count >= EXPECTED_UPLOADS:
        fail("complete prefix may not create another upload intent")
    entry = contract.entries[count]
    expected = {
        "index": count,
        "name": entry.name,
        "size": entry.size,
        "sha256": entry.sha256,
    }
    if pending != expected:
        fail("pending upload differs from the next exact contract entry")
    return state, count, pending


def validate_journal(
    value: Mapping[str, Any],
    contract: FrozenUploadContract,
    context: RecoveryContext,
) -> dict[str, Any]:
    validate_frozen_contract(contract)
    validate_context(context)
    if set(value) != {
        "schema",
        "phase",
        "sequence",
        "context",
        "upload_contract",
        "consumption",
        "refs",
        "record",
        "preparation",
        "effect",
    }:
        fail("recovery journal top-level keys differ")
    phase = value.get("phase")
    sequence = value.get("sequence")
    if (
        value.get("schema") != JOURNAL_SCHEMA
        or phase not in RECOVERY_PHASES
        or isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or not 0 <= sequence < MAX_RECOVERY_CHECKPOINTS
        or value.get("context") != _context_value(context)
        or value.get("upload_contract") != _contract_value(contract)
        or value.get("consumption") != _consumption_value(context)
        or value.get("refs")
        != {"recovery": context.recovery_ref, "publication": context.publication_ref}
        or value.get("effect") != _effect_value()
    ):
        fail("recovery journal binding differs")
    record = _record_from_value(value.get("record"))
    preparation = value.get("preparation")
    if phase in {"authorization_consumed", "create_requested"}:
        if record is not None or preparation is not None:
            fail("pre-record phase may not carry record or preparation state")
    else:
        if record is None or preparation is None:
            fail("record-bearing phase lacks record or preparation state")
        state, count, _pending = _validate_preparation(preparation, contract)
        if phase in {"prepared", "publish_requested"} and (
            state != "OBSERVED_PREFIX" or count != EXPECTED_UPLOADS
        ):
            fail("prepared/publish phase lacks the complete exact prefix")
    return dict(value)


def journal_from_bytes(
    raw: bytes,
    contract: FrozenUploadContract,
    context: RecoveryContext,
) -> dict[str, Any]:
    value = strict_json_bytes(raw, "recovery journal")
    validated = validate_journal(value, contract, context)
    if raw != journal_bytes(validated):
        fail("recovery journal bytes are not the canonical persisted form")
    return validated


def _record_for_journal(value: Mapping[str, Any]) -> RecordIdentity | None:
    return _record_from_value(value.get("record"))


def _transition(
    prior: Mapping[str, Any],
    current: Mapping[str, Any],
    contract: FrozenUploadContract,
) -> None:
    if current["sequence"] != prior["sequence"] + 1:
        fail("recovery checkpoint sequence is not contiguous")
    for key in ("context", "upload_contract", "consumption", "refs", "effect"):
        if current[key] != prior[key]:
            fail("recovery checkpoint binding changed at " + key)
    prior_record = _record_for_journal(prior)
    current_record = _record_for_journal(current)
    if prior_record is not None and current_record != prior_record:
        fail("recovery record identity changed")
    left = prior["phase"]
    right = current["phase"]
    if left == "authorization_consumed":
        if right != "create_requested":
            fail("authorization_consumed must advance to create_requested")
        return
    if left == "create_requested":
        if (
            right != "record_created"
            or current_record is None
            or current["preparation"] != observed_preparation(0)
        ):
            fail("create_requested must resolve one exact empty draft")
        return
    if left == "record_created":
        prior_state, prior_count, _ = _validate_preparation(
            prior["preparation"], contract
        )
        if prior_state == "OBSERVED_PREFIX":
            if prior_count == EXPECTED_UPLOADS:
                if (
                    right != "prepared"
                    or current["preparation"]
                    != observed_preparation(EXPECTED_UPLOADS)
                ):
                    fail("complete prefix must advance to prepared")
                return
            expected = upload_intent(contract.entries[prior_count], prior_count)
            if right != "record_created" or current["preparation"] != expected:
                fail("observed prefix must persist the exact next upload intent")
            return
        expected = observed_preparation(prior_count + 1)
        if right != "record_created" or current["preparation"] != expected:
            fail("upload intent must advance by exactly one verified file")
        return
    if left == "prepared":
        if (
            right != "publish_requested"
            or current["preparation"] != observed_preparation(EXPECTED_UPLOADS)
        ):
            fail("prepared must advance to publish_requested")
        return
    fail("publish_requested is terminal on the recovery ref")


@dataclasses.dataclass(frozen=True)
class CheckpointCandidate:
    commit_sha: str
    parent_sha: str
    relative_path: str
    evidence_bytes: bytes


class CheckpointPort(Protocol):
    """Remote-ref persistence adapter; implementations must not retry."""

    def prepare_commit(
        self,
        parent_sha: str,
        relative_path: str,
        evidence_bytes: bytes,
    ) -> CheckpointCandidate: ...

    def mutate_ref_once(
        self,
        ref: str,
        expected_old_sha: str | None,
        candidate_value: CheckpointCandidate,
    ) -> None: ...

    def read_ref_once(self, ref: str) -> CheckpointCandidate | None: ...


class ConsumptionRefPort(Protocol):
    def create_once(self, expected: ConsumptionIdentity) -> None: ...

    def read_once(self, ref: str) -> ConsumptionIdentity | None: ...


def consume_authorization_once(
    port: ConsumptionRefPort,
    expected: ConsumptionIdentity,
) -> ConsumptionIdentity:
    """Perform one create-only consumption mutation and one exact readback."""
    try:
        port.create_once(expected)
    except RemoteMutationError:
        pass
    observed = port.read_once(expected.ref)
    if observed != expected:
        fail("authorization consumption has no exact post-mutation readback")
    return expected


@dataclasses.dataclass(frozen=True)
class PersistedCheckpoint:
    commit_sha: str
    parent_sha: str
    relative_path: str
    evidence_bytes: bytes


def _candidate_to_persisted(value: CheckpointCandidate) -> PersistedCheckpoint:
    return PersistedCheckpoint(
        value.commit_sha,
        value.parent_sha,
        value.relative_path,
        value.evidence_bytes,
    )


def validate_recovery_chain(
    history: Sequence[PersistedCheckpoint],
    contract: FrozenUploadContract,
    context: RecoveryContext,
) -> list[dict[str, Any]]:
    if len(history) > MAX_RECOVERY_CHECKPOINTS:
        fail("recovery checkpoint chain exceeds its exact bound")
    values: list[dict[str, Any]] = []
    parent = context.execution_head
    for index, checkpoint in enumerate(history):
        if (
            HEX40.fullmatch(checkpoint.commit_sha) is None
            or checkpoint.parent_sha != parent
            or checkpoint.relative_path != RECOVERY_RELATIVE
        ):
            fail("recovery checkpoint commit/ref path differs")
        value = journal_from_bytes(checkpoint.evidence_bytes, contract, context)
        if value["sequence"] != index:
            fail("recovery journal sequence differs from its chain position")
        if index == 0:
            if value["phase"] != "authorization_consumed":
                fail("recovery chain must begin with authorization_consumed")
        else:
            _transition(values[-1], value, contract)
        values.append(value)
        parent = checkpoint.commit_sha
    return values


def validate_ref_state(
    history: Sequence[PersistedCheckpoint],
    context: RecoveryContext,
    recovery_head: str | None,
    publication_head: str,
    final_checkpoint: PersistedCheckpoint | None = None,
) -> None:
    expected_recovery = history[-1].commit_sha if history else None
    if recovery_head != expected_recovery:
        fail("recovery ref head differs from its checkpoint chain")
    if final_checkpoint is None:
        if publication_head != context.execution_head:
            fail("unfinalized publication ref moved from the execution head")
        return
    if not history:
        fail("final publication lacks a recovery parent")
    parent_journal = strict_json_bytes(
        history[-1].evidence_bytes,
        "final publication recovery parent",
    )
    if parent_journal.get("phase") != "publish_requested":
        fail("final publication parent is not publish_requested")
    if (
        final_checkpoint.parent_sha != history[-1].commit_sha
        or final_checkpoint.relative_path != EVIDENCE_RELATIVE
        or publication_head != final_checkpoint.commit_sha
    ):
        fail("final publication ref differs from its publish_requested parent")


class CreatePort(Protocol):
    def create_once(self, metadata_sha256: str) -> Any: ...

    def read_create_once(self, hint: Any | None) -> Sequence[DraftSnapshot]: ...


class UploadPort(Protocol):
    def upload_once(self, record: RecordIdentity, entry: UploadIdentity) -> None: ...

    def read_draft_once(self, record: RecordIdentity) -> DraftSnapshot: ...


class PublishPort(Protocol):
    def publish_once(self, record: RecordIdentity) -> None: ...


class AnonymousPublicPort(Protocol):
    def read_public_once(self, record: RecordIdentity) -> PublicSnapshot | None: ...


def _server_file_map(files: Sequence[ServerFile]) -> dict[str, ServerFile]:
    result: dict[str, ServerFile] = {}
    for item in files:
        if item.name in result:
            fail("remote file inventory contains a duplicate name")
        result[item.name] = item
    return result


def exact_prefix_count(
    snapshot: DraftSnapshot,
    contract: FrozenUploadContract,
    record: RecordIdentity,
) -> int:
    if (
        snapshot.record != record
        or snapshot.metadata_sha256 != contract.metadata_sha256
        or snapshot.editable is not True
    ):
        fail("editable draft identity or metadata differs")
    observed = _server_file_map(snapshot.files)
    count = len(observed)
    if count > EXPECTED_UPLOADS:
        fail("editable draft contains more than 65 files")
    expected_names = {entry.name for entry in contract.entries[:count]}
    if set(observed) != expected_names:
        fail("editable draft file set is not an exact ordered-contract prefix")
    for entry in contract.entries[:count]:
        if dataclasses.asdict(observed[entry.name]) != entry.server_identity():
            fail("editable draft prefix bytes differ for " + entry.name)
    return count


def validate_public_snapshot(
    snapshot: PublicSnapshot,
    contract: FrozenUploadContract,
    record: RecordIdentity,
) -> None:
    if (
        snapshot.record != record
        or DOI.fullmatch(snapshot.conceptdoi) is None
        or snapshot.metadata_sha256 != contract.metadata_sha256
        or snapshot.transport != PublicTransportAttestation()
    ):
        fail("anonymous public record identity or transport boundary differs")
    observed = _server_file_map(snapshot.files)
    if set(observed) != {entry.name for entry in contract.entries}:
        fail("anonymous public fileset is not exactly the frozen 65 uploads")
    total = 0
    for entry in contract.entries:
        if dataclasses.asdict(observed[entry.name]) != entry.server_identity():
            fail("anonymous public redownload differs for " + entry.name)
        total += observed[entry.name].size
    if total != contract.total_bytes:
        fail("anonymous public redownload byte total differs")


def validate_generic_public_evidence(
    value: Mapping[str, Any],
    contract: FrozenUploadContract,
    context: RecoveryContext,
    public_snapshot: PublicSnapshot,
) -> dict[str, Any]:
    """Validate the generic v2 final receipt without creating an auth file."""
    expected_keys = {
        "schema",
        "state",
        "phase",
        "manifest_path",
        "manifest_sha256",
        "machine_proof",
        "owner_authorization",
        "remote_consumption",
        "repository",
        "repository_commit",
        "source_head",
        "binding",
        "governance_boundaries",
        "recovery",
        "record_id",
        "doi",
        "title",
        "version",
        "files",
        "conceptdoi",
        "record_url",
    }
    if set(value) != expected_keys:
        fail("generic public evidence keys differ")
    record = public_snapshot.record
    expected_files = [entry.generic_file() for entry in contract.entries]
    if (
        value.get("schema") != GENERIC_EVIDENCE_SCHEMA
        or value.get("state") != "published"
        or value.get("phase") != "public_verified"
        or value.get("manifest_path") != MANIFEST_RELATIVE
        or value.get("manifest_sha256") != context.manifest_sha256
        or value.get("repository") != REPOSITORY
        or value.get("repository_commit") != context.execution_head
        or value.get("source_head") != SOURCE_HEAD
        or value.get("record_id") != record.record_id
        or value.get("doi") != record.doi
        or value.get("conceptdoi") != public_snapshot.conceptdoi
        or value.get("title") != contract.title
        or value.get("version") != contract.version
        or value.get("files") != expected_files
        or value.get("recovery") != publish._recovery_flags("public_verified")
        or value.get("governance_boundaries")
        != list(publish.GOVERNANCE_BOUNDARIES)
    ):
        fail("generic public evidence differs from the exact corpus publication")
    if not isinstance(value.get("machine_proof"), dict) or not isinstance(
        value.get("owner_authorization"), dict
    ):
        fail("generic public evidence lacks its proof/authorization bindings")
    remote = value.get("remote_consumption")
    if (
        not isinstance(remote, dict)
        or remote.get("ref") != context.consumption.ref
        or remote.get("tag_object") != context.consumption.tag_object
        or remote.get("execution_head") != context.execution_head
        or remote.get("repository") != REPOSITORY
    ):
        fail("generic public evidence remote consumption differs")
    binding = value.get("binding")
    if (
        not isinstance(binding, dict)
        or binding.get("repository") != REPOSITORY
        or binding.get("authorization_id") != AUTHORIZATION_ID
        or binding.get("publication_id") != PUBLICATION_ID
        or binding.get("statement_sha256") != STATEMENT_SHA256
        or binding.get("manifest_sha256") != context.manifest_sha256
        or binding.get("source_head") != SOURCE_HEAD
        or binding.get("execution_head") != context.execution_head
        or binding.get("consumption_key", {}).get("value")
        != context.consumption.key
    ):
        fail("generic public evidence authorization binding differs")
    record_url = value.get("record_url")
    expected_url = f"https://zenodo.org/records/{record.record_id}"
    if record_url != expected_url:
        fail("generic public evidence record URL differs")
    validate_public_snapshot(public_snapshot, contract, record)
    return dict(value)


class _RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


def build_anonymous_public_opener() -> urllib.request.OpenerDirector:
    """Build a default-CA HTTPS opener with proxies and redirects disabled."""
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _RejectRedirects(),
        urllib.request.HTTPSHandler(context=context),
    )


def build_anonymous_public_request(url: str) -> urllib.request.Request:
    parts = urllib.parse.urlsplit(url)
    try:
        port = parts.port
    except ValueError:
        fail("anonymous public URL port is invalid")
    if (
        parts.scheme != "https"
        or parts.hostname != "zenodo.org"
        or parts.username is not None
        or parts.password is not None
        or port not in {None, 443}
        or parts.query
        or parts.fragment
        or not (
            re.fullmatch(r"/api/records/[1-9][0-9]*", parts.path)
            or re.fullmatch(
                r"/api/records/[1-9][0-9]*/files/[^/]+/content", parts.path
            )
        )
    ):
        fail("anonymous public URL escaped the exact Zenodo read allowlist")
    is_content = parts.path.endswith("/content")
    return urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/octet-stream" if is_content else "application/json",
            "User-Agent": "qik-vrt-corpus-public-verify/1",
        },
    )


class RecoveryController:
    """One exact recovery transaction reconstructed from durable checkpoints."""

    def __init__(
        self,
        contract: FrozenUploadContract,
        context: RecoveryContext,
        checkpoint_port: CheckpointPort,
        *,
        history: Sequence[PersistedCheckpoint] = (),
        recovery_head: str | None = None,
        publication_head: str | None = None,
        final_checkpoint: PersistedCheckpoint | None = None,
    ) -> None:
        validate_frozen_contract(contract)
        validate_context(context)
        self.contract = contract
        self.context = context
        self.port = checkpoint_port
        self.history = list(history)
        self.values = validate_recovery_chain(self.history, contract, context)
        self.recovery_head = (
            recovery_head
            if recovery_head is not None
            else (self.history[-1].commit_sha if self.history else None)
        )
        self.publication_head = publication_head or context.execution_head
        self.final_checkpoint = final_checkpoint
        validate_ref_state(
            self.history,
            context,
            self.recovery_head,
            self.publication_head,
            final_checkpoint,
        )

    @property
    def phase(self) -> str | None:
        if self.final_checkpoint is not None:
            return "public_verified"
        return self.values[-1]["phase"] if self.values else None

    @property
    def current_record(self) -> RecordIdentity | None:
        return _record_for_journal(self.values[-1]) if self.values else None

    def _persist(
        self,
        value: Mapping[str, Any],
        *,
        final: bool = False,
    ) -> PersistedCheckpoint:
        raw = (
            journal_bytes(value)
            if not final
            else json.dumps(
                dict(value), ensure_ascii=False, indent=2, sort_keys=True
            ).encode("utf-8")
            + b"\n"
        )
        parent = self.history[-1].commit_sha if self.history else self.context.execution_head
        relative = EVIDENCE_RELATIVE if final else RECOVERY_RELATIVE
        candidate_value = self.port.prepare_commit(parent, relative, raw)
        if (
            HEX40.fullmatch(candidate_value.commit_sha) is None
            or candidate_value.parent_sha != parent
            or candidate_value.relative_path != relative
            or candidate_value.evidence_bytes != raw
        ):
            fail("prepared checkpoint commit differs from the exact candidate")
        target_ref = self.context.publication_ref if final else self.context.recovery_ref
        expected_old = self.context.execution_head if final else self.recovery_head
        try:
            self.port.mutate_ref_once(target_ref, expected_old, candidate_value)
        except RemoteMutationError:
            pass
        observed = self.port.read_ref_once(target_ref)
        if observed != candidate_value:
            fail("checkpoint ref mutation has no exact one-shot readback")
        persisted = _candidate_to_persisted(candidate_value)
        if final:
            self.final_checkpoint = persisted
            self.publication_head = persisted.commit_sha
        else:
            self.history.append(persisted)
            self.values = validate_recovery_chain(
                self.history, self.contract, self.context
            )
            self.recovery_head = persisted.commit_sha
        validate_ref_state(
            self.history,
            self.context,
            self.recovery_head,
            self.publication_head,
            self.final_checkpoint,
        )
        return persisted

    def bootstrap_authorization_consumed(self) -> PersistedCheckpoint:
        if self.history or self.final_checkpoint is not None:
            fail("authorization bootstrap requires an empty recovery chain")
        value = make_journal(
            self.contract,
            self.context,
            phase="authorization_consumed",
            sequence=0,
        )
        return self._persist(value)

    def _resolve_create_readback(
        self,
        snapshots: Sequence[DraftSnapshot],
    ) -> PersistedCheckpoint:
        if len(snapshots) != 1:
            fail(
                "create readback requires exactly one matching empty draft; "
                f"observed {len(snapshots)}"
            )
        snapshot = snapshots[0]
        if exact_prefix_count(snapshot, self.contract, snapshot.record) != 0:
            fail("created record is not the exact empty draft")
        value = make_journal(
            self.contract,
            self.context,
            phase="record_created",
            sequence=len(self.history),
            record=snapshot.record,
            preparation=observed_preparation(0),
        )
        return self._persist(value)

    def create_record(
        self,
        remote: CreatePort,
        *,
        after_intent: Callable[[], None] | None = None,
    ) -> PersistedCheckpoint:
        if self.phase != "authorization_consumed":
            fail("fresh create requires authorization_consumed")
        intent = make_journal(
            self.contract,
            self.context,
            phase="create_requested",
            sequence=len(self.history),
        )
        self._persist(intent)
        if after_intent is not None:
            after_intent()
        hint: Any | None = None
        try:
            hint = remote.create_once(self.contract.metadata_sha256)
        except RemoteMutationError:
            hint = None
        snapshots = remote.read_create_once(hint)
        return self._resolve_create_readback(snapshots)

    def reconcile_create_requested(
        self,
        remote: CreatePort,
    ) -> PersistedCheckpoint:
        """GET-only recovery; this method has no create call."""
        if self.phase != "create_requested":
            fail("create reconciliation requires restored create_requested")
        return self._resolve_create_readback(remote.read_create_once(None))

    def _resolve_upload_readback(
        self,
        remote: UploadPort,
        record: RecordIdentity,
        expected_count: int,
    ) -> PersistedCheckpoint:
        snapshot = remote.read_draft_once(record)
        count = exact_prefix_count(snapshot, self.contract, record)
        if count != expected_count:
            fail(
                "one-shot upload readback did not advance exactly one prefix entry"
            )
        value = make_journal(
            self.contract,
            self.context,
            phase="record_created",
            sequence=len(self.history),
            record=record,
            preparation=observed_preparation(count),
        )
        return self._persist(value)

    def upload_next(
        self,
        remote: UploadPort,
        *,
        after_intent: Callable[[], None] | None = None,
    ) -> PersistedCheckpoint:
        if self.phase != "record_created":
            fail("fresh upload requires record_created")
        current = self.values[-1]
        state, count, _pending = _validate_preparation(
            current["preparation"], self.contract
        )
        record = self.current_record
        if state != "OBSERVED_PREFIX" or count >= EXPECTED_UPLOADS or record is None:
            fail("fresh upload requires an incomplete observed prefix")
        entry = self.contract.entries[count]
        intent = make_journal(
            self.contract,
            self.context,
            phase="record_created",
            sequence=len(self.history),
            record=record,
            preparation=upload_intent(entry, count),
        )
        self._persist(intent)
        if after_intent is not None:
            after_intent()
        try:
            remote.upload_once(record, entry)
        except RemoteMutationError:
            pass
        return self._resolve_upload_readback(remote, record, count + 1)

    def reconcile_upload_intent(
        self,
        remote: UploadPort,
    ) -> PersistedCheckpoint:
        """GET-only recovery; a persisted upload intent is never replayed."""
        if self.phase != "record_created":
            fail("upload reconciliation requires record_created")
        current = self.values[-1]
        state, count, _pending = _validate_preparation(
            current["preparation"], self.contract
        )
        record = self.current_record
        if state != "UPLOAD_INTENT" or record is None:
            fail("upload reconciliation requires a restored upload intent")
        return self._resolve_upload_readback(remote, record, count + 1)

    def mark_prepared(self) -> PersistedCheckpoint:
        if self.phase != "record_created":
            fail("prepared transition requires record_created")
        current = self.values[-1]
        state, count, _pending = _validate_preparation(
            current["preparation"], self.contract
        )
        record = self.current_record
        if state != "OBSERVED_PREFIX" or count != EXPECTED_UPLOADS or record is None:
            fail("prepared transition requires the exact complete prefix")
        value = make_journal(
            self.contract,
            self.context,
            phase="prepared",
            sequence=len(self.history),
            record=record,
            preparation=observed_preparation(EXPECTED_UPLOADS),
        )
        return self._persist(value)

    def _resolve_public_readback(
        self,
        snapshot: PublicSnapshot | None,
        generic_evidence: Mapping[str, Any] | None,
        generic_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
    ) -> PersistedCheckpoint:
        record = self.current_record
        if snapshot is None or record is None:
            fail("publish readback did not return the exact public record")
        validate_public_snapshot(snapshot, self.contract, record)
        if generic_evidence is None or generic_validator is None:
            fail("public_verified requires a full generic publisher validator")
        normalized = dict(generic_validator(generic_evidence))
        if normalized != dict(generic_evidence):
            fail("generic publisher validator changed the final evidence")
        validated = validate_generic_public_evidence(
            normalized,
            self.contract,
            self.context,
            snapshot,
        )
        return self._persist(validated, final=True)

    def publish_once(
        self,
        remote: PublishPort,
        public: AnonymousPublicPort,
        generic_evidence_factory: Callable[[PublicSnapshot], Mapping[str, Any]],
        generic_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        *,
        after_intent: Callable[[], None] | None = None,
    ) -> PersistedCheckpoint:
        if self.phase != "prepared":
            fail("fresh publish requires prepared")
        record = self.current_record
        if record is None:
            fail("fresh publish lacks its record identity")
        value = make_journal(
            self.contract,
            self.context,
            phase="publish_requested",
            sequence=len(self.history),
            record=record,
            preparation=observed_preparation(EXPECTED_UPLOADS),
        )
        self._persist(value)
        if after_intent is not None:
            after_intent()
        try:
            remote.publish_once(record)
        except RemoteMutationError:
            pass
        snapshot = public.read_public_once(record)
        evidence = None if snapshot is None else generic_evidence_factory(snapshot)
        return self._resolve_public_readback(snapshot, evidence, generic_validator)

    def reconcile_publish_requested(
        self,
        public: AnonymousPublicPort,
        generic_evidence_factory: Callable[[PublicSnapshot], Mapping[str, Any]],
        generic_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    ) -> PersistedCheckpoint:
        """Anonymous GET-only recovery; publish POST is intentionally absent."""
        if self.phase != "publish_requested":
            fail("publish reconciliation requires restored publish_requested")
        record = self.current_record
        if record is None:
            fail("publish reconciliation lacks its record identity")
        snapshot = public.read_public_once(record)
        evidence = None if snapshot is None else generic_evidence_factory(snapshot)
        return self._resolve_public_readback(snapshot, evidence, generic_validator)


def _git_text(*arguments: str) -> str:
    environment = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"cannot execute repository Git gate: {type(exc).__name__}")
    if completed.returncode != 0:
        fail("repository Git gate rejected " + " ".join(arguments[:2]))
    try:
        return completed.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError:
        fail("repository Git gate returned non-UTF-8 output")


def _git_bytes(*arguments: str) -> bytes:
    environment = {
        key: value
        for key in ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "SYSTEMROOT")
        if (value := os.environ.get(key)) is not None
    }
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"})
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"cannot execute repository Git gate: {type(exc).__name__}")
    if completed.returncode != 0:
        fail("repository Git gate rejected " + " ".join(arguments[:2]))
    return completed.stdout


def _exact_execution_head() -> str:
    observed = _git_text("rev-parse", "--verify", "HEAD^{commit}")
    ancestry = _git_text("rev-list", "--parents", "-n", "1", observed).split()
    supplied = os.environ.get("GITHUB_SHA")
    expected_ref_name = PUBLICATION_REF.removeprefix("refs/heads/")
    if (
        HEX40.fullmatch(observed) is None
        or supplied != observed
        or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != PUBLICATION_REF
        or os.environ.get("GITHUB_REF_NAME") != expected_ref_name
        or ancestry != [observed, CONTROL_BASE_HEAD]
    ):
        fail("workflow ref/repository/parent differs from the exact execution HEAD")
    return observed


def _load_production_manifest(
    contract: FrozenUploadContract,
) -> tuple[pathlib.Path, dict[str, Any]]:
    manifest_path = ROOT.joinpath(*pathlib.PurePosixPath(MANIFEST_RELATIVE).parts)
    try:
        manifest = publish.load_manifest(manifest_path, ROOT)
    except zenodo.ZenodoError as exc:
        fail("generic manifest gate rejected the corpus controls: " + str(exc))
    expected_files = [entry.generic_file() for entry in contract.entries]
    if (
        manifest_path != ROOT / CONTROL_REL / controls.MANIFEST_BASENAME
        or manifest.get("schema") != publish.SCHEMA_V2
        or manifest.get("repository") != REPOSITORY
        or manifest.get("source_head") != SOURCE_HEAD
        or manifest.get("files") != expected_files
        or candidate.canonical_json_sha256(manifest.get("metadata"))
        != contract.metadata_sha256
        or manifest.get("owner_authorization", {}).get("authorization_id")
        != AUTHORIZATION_ID
        or manifest.get("owner_authorization", {}).get("publication_id")
        != PUBLICATION_ID
        or manifest.get("evidence_path")
        != ROOT.joinpath(*pathlib.PurePosixPath(EVIDENCE_RELATIVE).parts)
    ):
        fail("normalized production manifest differs from the frozen contract")
    return manifest_path, manifest


class _NoCredentialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> None:
        return None


class GitHubReceiptAPI:
    """Pinned, bounded GitHub transport; mutation calls are never retried."""

    def __init__(self, token: str) -> None:
        if len(token) < 20 or any(character.isspace() for character in token):
            fail("GITHUB_TOKEN is missing or structurally invalid")
        self.token = token
        self.opener = urllib.request.build_opener(_NoCredentialRedirect())

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        accept: tuple[int, ...] = (200,),
        ambiguous_mutation: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        if (
            method not in {"GET", "POST", "PATCH"}
            or not path.startswith(GITHUB_REPOSITORY_API + "/")
            or any(character in path for character in ("\x00", "\r", "\n", "#"))
        ):
            fail("GitHub receipt request escaped its exact repository allowlist")
        body = None if payload is None else canonical_json_bytes(dict(payload))
        url = GITHUB_API_BASE + path
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self.token,
                "User-Agent": "qik-vrt-corpus-recovery/1",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        response: Any
        try:
            response = self.opener.open(request, timeout=60)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            if ambiguous_mutation and method in {"POST", "PATCH"}:
                raise AmbiguousMutation(type(exc).__name__) from None
            fail("GitHub receipt transport failed: " + type(exc).__name__)
        try:
            status = int(response.status)
            if response.geturl() != url:
                fail("GitHub receipt response URL changed")
            raw = response.read(MAX_GITHUB_RESPONSE_BYTES + 1)
        finally:
            response.close()
        if len(raw) > MAX_GITHUB_RESPONSE_BYTES:
            fail("GitHub receipt response exceeded its byte bound")
        if self.token.encode("utf-8") in raw:
            fail("GitHub receipt response contained its bearer credential")
        if status not in accept:
            if ambiguous_mutation and method in {"POST", "PATCH"} and status >= 500:
                raise AmbiguousMutation(f"HTTP {status}")
            fail(f"GitHub receipt API rejected {method} (HTTP {status})")
        if not raw:
            return status, {}
        return status, strict_json_bytes(raw, "GitHub receipt response")


def _head_ref_path(ref: str, *, plural: bool) -> str:
    if not ref.startswith("refs/heads/") or any(
        character in ref for character in ("\x00", "\r", "\n")
    ):
        fail("receipt ref is not a safe branch ref")
    suffix = urllib.parse.quote(ref.removeprefix("refs/"), safe="/")
    marker = "/git/refs/" if plural else "/git/ref/"
    return GITHUB_REPOSITORY_API + marker + suffix


def _ref_sha(value: Mapping[str, Any], ref: str) -> str:
    target = value.get("object")
    sha = target.get("sha") if isinstance(target, dict) else None
    if (
        value.get("ref") != ref
        or not isinstance(sha, str)
        or HEX40.fullmatch(sha) is None
        or target.get("type") != "commit"
    ):
        fail("GitHub receipt ref response differs")
    return sha


@dataclasses.dataclass(frozen=True)
class _GitHubCandidatePlan:
    candidate: CheckpointCandidate
    tree_sha: str
    subject: str
    changes: tuple[tuple[str, bytes], ...]


def _integrity_entry(path: str, raw: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "classification": "repository_content",
        "immutable": True,
        "excluded_from_sha256_index": False,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "file_type": "regular",
    }


def _expected_final_integrity(
    execution_head: str,
    recovery_raw: bytes,
    evidence_raw: bytes,
) -> dict[str, bytes]:
    base_raw = _git_bytes(
        "show", f"{execution_head}:REPOSITORY_FILE_MANIFEST.json"
    )
    base = strict_json_bytes(base_raw, "execution integrity manifest")
    entries = base.get("files")
    if not isinstance(entries, list) or any(
        not isinstance(entry, dict) for entry in entries
    ):
        fail("execution integrity manifest files differ")
    receipt_paths = {RECOVERY_RELATIVE, EVIDENCE_RELATIVE}
    if any(entry.get("path") in receipt_paths for entry in entries):
        fail("execution integrity manifest already contains recovery receipt paths")
    expected_entries = sorted(
        [
            *entries,
            _integrity_entry(RECOVERY_RELATIVE, recovery_raw),
            _integrity_entry(EVIDENCE_RELATIVE, evidence_raw),
        ],
        key=lambda entry: entry["path"],
    )
    expected_manifest = dict(base)
    expected_manifest["files"] = expected_entries
    expected_manifest["file_count"] = len(expected_entries)
    expected_manifest["immutable_file_count"] = sum(
        entry.get("immutable") is True for entry in expected_entries
    )
    expected_manifest["excluded_file_count"] = (
        len(expected_entries) - expected_manifest["immutable_file_count"]
    )
    expected_manifest["repository_content_tree_sha256"] = (
        integrity._content_tree_sha256(expected_entries)
    )
    manifest_raw = (
        json.dumps(
            expected_manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    index_raw = "".join(
        f"{entry['sha256']}  {entry['path']}\n"
        for entry in expected_entries
        if entry.get("immutable") is True
    ).encode("utf-8")
    detached_raw = (
        hashlib.sha256(manifest_raw).hexdigest()
        + "  REPOSITORY_FILE_MANIFEST.json\n"
    ).encode("ascii")
    return {
        "REPOSITORY_FILE_MANIFEST.json": manifest_raw,
        "REPOSITORY_FILE_MANIFEST.json.sha256": detached_raw,
        "SHA256SUMS.txt": index_raw,
    }


class GitHubCheckpointPort:
    """Content-addressed remote receipt store for the exact recovery refs."""

    def __init__(
        self,
        api: GitHubReceiptAPI,
        execution_head: str,
        commit_date: str,
    ) -> None:
        if HEX40.fullmatch(execution_head) is None:
            fail("receipt store execution head differs")
        try:
            parsed = datetime.datetime.fromisoformat(commit_date.replace("Z", "+00:00"))
        except ValueError:
            fail("receipt commit date is invalid")
        if parsed.tzinfo is None:
            fail("receipt commit date lacks a timezone")
        self.api = api
        self.execution_head = execution_head
        self.commit_date = commit_date
        self.plans: dict[str, _GitHubCandidatePlan] = {}
        self.ref_heads: dict[str, str | None] = {}

    def _read_ref_sha(self, ref: str, *, allow_absent: bool) -> str | None:
        status, value = self.api.request(
            "GET",
            _head_ref_path(ref, plural=False),
            accept=(200, 404) if allow_absent else (200,),
        )
        if status == 404:
            return None
        return _ref_sha(value, ref)

    def _read_blob(self, sha: str) -> bytes:
        if HEX40.fullmatch(sha) is None:
            fail("receipt blob identity is invalid")
        _status, value = self.api.request(
            "GET", GITHUB_REPOSITORY_API + "/git/blobs/" + sha
        )
        if value.get("sha") != sha or value.get("encoding") != "base64":
            fail("GitHub receipt blob response differs")
        content = value.get("content")
        if not isinstance(content, str):
            fail("GitHub receipt blob lacks base64 content")
        try:
            raw = base64.b64decode(content, validate=False)
        except (ValueError, TypeError):
            fail("GitHub receipt blob base64 differs")
        if git_blob_sha1(raw) != sha:
            fail("GitHub receipt blob content identity differs")
        return raw

    def _load_plan(
        self,
        commit_sha: str,
        relative_path: str,
    ) -> _GitHubCandidatePlan:
        expected_subject = (
            PUBLICATION_COMMIT_SUBJECT
            if relative_path == EVIDENCE_RELATIVE
            else RECOVERY_COMMIT_SUBJECT
        )
        _status, commit = self.api.request(
            "GET", GITHUB_REPOSITORY_API + "/git/commits/" + commit_sha
        )
        parents = commit.get("parents")
        parent_sha = (
            parents[0].get("sha")
            if isinstance(parents, list)
            and len(parents) == 1
            and isinstance(parents[0], dict)
            else None
        )
        tree = commit.get("tree")
        tree_sha = tree.get("sha") if isinstance(tree, dict) else None
        if (
            commit.get("sha") != commit_sha
            or not isinstance(parent_sha, str)
            or HEX40.fullmatch(parent_sha) is None
            or not isinstance(tree_sha, str)
            or HEX40.fullmatch(tree_sha) is None
            or commit.get("message") != expected_subject
        ):
            fail("GitHub receipt commit identity differs")
        for identity in (commit.get("author"), commit.get("committer")):
            if (
                not isinstance(identity, dict)
                or identity.get("name") != RECEIPT_AUTHOR["name"]
                or identity.get("email") != RECEIPT_AUTHOR["email"]
                or identity.get("date") != self.commit_date
            ):
                fail("GitHub receipt commit provenance differs")
        _status, detail = self.api.request(
            "GET", GITHUB_REPOSITORY_API + "/commits/" + commit_sha
        )
        files = detail.get("files")
        expected_paths = (
            {EVIDENCE_RELATIVE, *INTEGRITY_PATHS}
            if relative_path == EVIDENCE_RELATIVE
            else {RECOVERY_RELATIVE}
        )
        if (
            not isinstance(files, list)
            or len(files) != len(expected_paths)
            or not all(isinstance(item, dict) for item in files)
            or {item.get("filename") for item in files} != expected_paths
            or any(item.get("status") not in {"added", "modified"} for item in files)
        ):
            fail("GitHub receipt commit delta differs")
        changes: list[tuple[str, bytes]] = []
        for item in files:
            sha = item.get("sha")
            path = item.get("filename")
            if not isinstance(sha, str) or not isinstance(path, str):
                fail("GitHub receipt changed-file identity differs")
            changes.append((path, self._read_blob(sha)))
        by_path = dict(changes)
        evidence_raw = by_path[relative_path]
        if relative_path == EVIDENCE_RELATIVE:
            recovery_plan = self._load_plan(parent_sha, RECOVERY_RELATIVE)
            expected_integrity = _expected_final_integrity(
                self.execution_head,
                recovery_plan.candidate.evidence_bytes,
                evidence_raw,
            )
            if any(by_path.get(path) != raw for path, raw in expected_integrity.items()):
                fail("final receipt deterministic integrity trio differs")
        candidate_value = CheckpointCandidate(
            commit_sha,
            parent_sha,
            relative_path,
            evidence_raw,
        )
        plan = _GitHubCandidatePlan(
            candidate_value,
            tree_sha,
            expected_subject,
            tuple(sorted(changes)),
        )
        self.plans[commit_sha] = plan
        return plan

    def _create_object(
        self,
        endpoint: str,
        payload: Mapping[str, Any],
        label: str,
    ) -> str:
        _status, value = self.api.request(
            "POST",
            GITHUB_REPOSITORY_API + endpoint,
            payload=payload,
            accept=(201,),
            ambiguous_mutation=True,
        )
        sha = value.get("sha")
        if not isinstance(sha, str) or HEX40.fullmatch(sha) is None:
            fail("GitHub receipt " + label + " identity differs")
        return sha

    def prepare_commit(
        self,
        parent_sha: str,
        relative_path: str,
        evidence_bytes: bytes,
    ) -> CheckpointCandidate:
        if relative_path not in {RECOVERY_RELATIVE, EVIDENCE_RELATIVE}:
            fail("receipt candidate path escaped its exact allowlist")
        _status, parent = self.api.request(
            "GET", GITHUB_REPOSITORY_API + "/git/commits/" + parent_sha
        )
        parent_tree = parent.get("tree")
        base_tree = parent_tree.get("sha") if isinstance(parent_tree, dict) else None
        if not isinstance(base_tree, str) or HEX40.fullmatch(base_tree) is None:
            fail("receipt candidate parent tree differs")
        changes: dict[str, bytes] = {relative_path: evidence_bytes}
        if relative_path == EVIDENCE_RELATIVE:
            recovery_plan = self.plans.get(parent_sha) or self._load_plan(
                parent_sha, RECOVERY_RELATIVE
            )
            changes.update(
                _expected_final_integrity(
                    self.execution_head,
                    recovery_plan.candidate.evidence_bytes,
                    evidence_bytes,
                )
            )
        tree_entries: list[dict[str, str]] = []
        for path, raw in sorted(changes.items()):
            blob_sha = self._create_object(
                "/git/blobs",
                {
                    "content": base64.b64encode(raw).decode("ascii"),
                    "encoding": "base64",
                },
                "blob",
            )
            if blob_sha != git_blob_sha1(raw):
                fail("GitHub receipt blob creation returned a different identity")
            tree_entries.append(
                {"path": path, "mode": "100644", "type": "blob", "sha": blob_sha}
            )
        tree_sha = self._create_object(
            "/git/trees",
            {"base_tree": base_tree, "tree": tree_entries},
            "tree",
        )
        subject = (
            PUBLICATION_COMMIT_SUBJECT
            if relative_path == EVIDENCE_RELATIVE
            else RECOVERY_COMMIT_SUBJECT
        )
        identity = {**RECEIPT_AUTHOR, "date": self.commit_date}
        commit_sha = self._create_object(
            "/git/commits",
            {
                "message": subject,
                "tree": tree_sha,
                "parents": [parent_sha],
                "author": identity,
                "committer": identity,
            },
            "commit",
        )
        candidate_value = CheckpointCandidate(
            commit_sha,
            parent_sha,
            relative_path,
            evidence_bytes,
        )
        self.plans[commit_sha] = _GitHubCandidatePlan(
            candidate_value,
            tree_sha,
            subject,
            tuple(sorted(changes.items())),
        )
        return candidate_value

    def mutate_ref_once(
        self,
        ref: str,
        expected_old_sha: str | None,
        candidate_value: CheckpointCandidate,
    ) -> None:
        if ref not in self.ref_heads:
            fail("receipt ref mutation was not preceded by restoration")
        observed = self.ref_heads[ref]
        if ref == PUBLICATION_REF and observed is None:
            fail("absent publication ref may not be created")
        if observed != expected_old_sha:
            fail("receipt ref changed since restoration")
        try:
            if observed is None:
                status, value = self.api.request(
                    "POST",
                    GITHUB_REPOSITORY_API + "/git/refs",
                    payload={"ref": ref, "sha": candidate_value.commit_sha},
                    accept=(201, 409, 422),
                    ambiguous_mutation=True,
                )
                if status == 201:
                    _ref_sha(value, ref)
                    return
            else:
                status, value = self.api.request(
                    "PATCH",
                    _head_ref_path(ref, plural=True),
                    payload={"sha": candidate_value.commit_sha, "force": False},
                    accept=(200, 409, 422),
                    ambiguous_mutation=True,
                )
                if status == 200:
                    _ref_sha(value, ref)
                    return
        except AmbiguousMutation:
            raise
        raise RemoteMutationError("receipt ref mutation was rejected")

    def read_ref_once(self, ref: str) -> CheckpointCandidate | None:
        sha = self._read_ref_sha(ref, allow_absent=True)
        self.ref_heads[ref] = sha
        if sha is None:
            return None
        plan = self.plans.get(sha)
        relative = EVIDENCE_RELATIVE if ref == PUBLICATION_REF else RECOVERY_RELATIVE
        loaded = self._load_plan(sha, relative)
        if plan is not None and loaded != plan:
            fail("GitHub receipt readback differs from its prepared candidate")
        return loaded.candidate

    def restore(
        self,
        contract: FrozenUploadContract,
        context: RecoveryContext,
    ) -> tuple[list[PersistedCheckpoint], str | None, str, PersistedCheckpoint | None]:
        recovery_head = self._read_ref_sha(context.recovery_ref, allow_absent=True)
        publication_remote = self._read_ref_sha(
            context.publication_ref, allow_absent=True
        )
        if publication_remote is None:
            fail("remote publication ref is absent and may not be recreated")
        self.ref_heads[context.recovery_ref] = recovery_head
        self.ref_heads[context.publication_ref] = publication_remote
        history_reverse: list[PersistedCheckpoint] = []
        cursor = recovery_head
        visited: set[str] = set()
        while cursor is not None and cursor != context.execution_head:
            if cursor in visited or len(visited) >= MAX_RECOVERY_CHECKPOINTS:
                fail("remote recovery receipt chain is cyclic or unbounded")
            visited.add(cursor)
            plan = self._load_plan(cursor, RECOVERY_RELATIVE)
            history_reverse.append(_candidate_to_persisted(plan.candidate))
            cursor = plan.candidate.parent_sha
        if cursor != context.execution_head and recovery_head is not None:
            fail("remote recovery receipt chain escaped the execution head")
        history = list(reversed(history_reverse))
        validate_recovery_chain(history, contract, context)
        final: PersistedCheckpoint | None = None
        publication_head = publication_remote
        if publication_remote != context.execution_head:
            plan = self._load_plan(publication_remote, EVIDENCE_RELATIVE)
            final = _candidate_to_persisted(plan.candidate)
        if final is not None and final.parent_sha != recovery_head:
            fail("remote final receipt parent differs from the recovery ref")
        return history, recovery_head, publication_head, final


class ProductionZenodoAdapter(CreatePort, UploadPort, PublishPort):
    """One-shot authenticated mutations with exact draft GET reconciliation."""

    def __init__(
        self,
        client: zenodo.ZenodoClient,
        token: str,
        contract: FrozenUploadContract,
        metadata: Mapping[str, Any],
        forbidden_secrets: Sequence[str] = (),
    ) -> None:
        self.client = client
        self.token = token
        self.contract = contract
        self.metadata = dict(metadata)
        self.forbidden_secrets = tuple(
            secret.encode("utf-8") for secret in forbidden_secrets if secret
        )
        # A newly restored process must establish SHA-256 knowledge for every
        # existing prefix member.  Within that process, immutable prefix
        # members are downloaded only once and each later upload adds exactly
        # one previously unseen name to this set.
        self._verified_prefix_names: set[str] = set()

    def _draft_snapshot(
        self,
        value: Mapping[str, Any],
        *,
        verify_unseen_prefix: bool,
    ) -> DraftSnapshot:
        record_id = zenodo._record_id(value, "corpus recovery draft")
        doi = zenodo._doi_from_deposition(value, "corpus recovery draft")
        record = RecordIdentity(record_id, doi)
        expected_metadata = dict(self.metadata)
        expected_metadata.pop("prereserve_doi", None)
        if not zenodo._metadata_matches(value.get("metadata"), expected_metadata):
            fail("editable corpus draft metadata differs from the frozen metadata")
        if value.get("submitted") is True or value.get("state") == "done":
            return DraftSnapshot(
                record, self.contract.metadata_sha256, (), editable=False
            )
        raw_files = self.client._server_files(value)
        by_name: dict[str, Mapping[str, Any]] = {}
        for item in raw_files:
            name = self.client._server_file_name(item)
            if name in by_name:
                fail("editable corpus draft contains duplicate file names")
            by_name[name] = item
        count = len(by_name)
        if count > EXPECTED_UPLOADS:
            fail("editable corpus draft contains more than 65 files")
        expected_prefix = self.contract.entries[:count]
        if set(by_name) != {entry.name for entry in expected_prefix}:
            fail("editable corpus draft is not an exact ordered-contract prefix")
        current_names = set(by_name)
        if not self._verified_prefix_names.issubset(current_names):
            fail("editable corpus draft regressed after prefix verification")
        snapshots: list[ServerFile] = []
        for entry in expected_prefix:
            item = by_name[entry.name]
            size = item.get("filesize", item.get("size"))
            if isinstance(size, str) and size.isdecimal():
                size = int(size)
            checksum = item.get("checksum")
            if size != entry.size or checksum not in {entry.md5, "md5:" + entry.md5}:
                fail("editable corpus draft server identity differs for " + entry.name)
            observed_sha = entry.sha256
            if verify_unseen_prefix and entry.name not in self._verified_prefix_names:
                links = item.get("links")
                if not isinstance(links, dict):
                    fail("editable corpus draft file lacks a download link")
                download: str | None = None
                for link in (links.get("download"), links.get("self")):
                    if not isinstance(link, str):
                        continue
                    try:
                        download = zenodo.validate_response_url(
                            link, self.client.base_url
                        )
                    except zenodo.ZenodoError:
                        continue
                    break
                if download is None:
                    fail("editable corpus draft file escaped its download origin")
                response, _unused = self.client.request(
                    "GET",
                    download,
                    accept=(200,),
                    parse_json=False,
                    max_response_bytes=entry.size,
                )
                raw = response.body
                if (
                    len(raw) != entry.size
                    or hashlib.md5(raw).hexdigest() != entry.md5  # noqa: S324
                    or hashlib.sha256(raw).hexdigest() != entry.sha256
                ):
                    fail("editable corpus draft redownload differs for " + entry.name)
                observed_sha = hashlib.sha256(raw).hexdigest()
                self._verified_prefix_names.add(entry.name)
            snapshots.append(ServerFile(entry.name, int(size), entry.md5, observed_sha))
        return DraftSnapshot(
            record,
            self.contract.metadata_sha256,
            tuple(reversed(snapshots)),
            editable=True,
        )

    def create_once(self, metadata_sha256: str) -> Any:
        if metadata_sha256 != self.contract.metadata_sha256:
            fail("create mutation metadata identity differs")
        try:
            _response, value = self.client.request(
                "POST",
                "/api/deposit/depositions",
                payload={"metadata": self.metadata},
                accept=(200, 201, 202),
            )
        except zenodo.ZenodoError as exc:
            raise RemoteMutationError(type(exc).__name__) from None
        try:
            record_id = zenodo._record_id(value, "corpus create response")
            doi = zenodo._doi_from_deposition(value, "corpus create response")
        except zenodo.ZenodoError:
            return None
        return RecordIdentity(record_id, doi)

    def read_create_once(self, hint: Any | None) -> Sequence[DraftSnapshot]:
        del hint
        try:
            inventory = publish._list_all_owned_depositions(self.client, self.token)
        except zenodo.ZenodoError as exc:
            fail("create reconciliation inventory failed: " + str(exc))
        snapshots: list[DraftSnapshot] = []
        for item in inventory:
            if not publish._inventory_publication_identity_candidate(
                item, self.metadata
            ):
                continue
            record_id = zenodo._record_id(item, "corpus create inventory")
            state, current = self.client.get_deposition_or_record(record_id)
            if state == "published":
                doi = zenodo._doi_from_deposition(current, "published create candidate")
                snapshots.append(
                    DraftSnapshot(
                        RecordIdentity(record_id, doi),
                        self.contract.metadata_sha256,
                        (),
                        editable=False,
                    )
                )
                continue
            snapshots.append(
                self._draft_snapshot(current, verify_unseen_prefix=False)
            )
        return tuple(snapshots)

    def upload_once(self, record: RecordIdentity, entry: UploadIdentity) -> None:
        try:
            state, current = self.client.get_deposition_or_record(record.record_id)
            if state != "draft":
                fail("upload target is no longer an editable draft")
            before = self._draft_snapshot(current, verify_unseen_prefix=True)
            if before.record != record or len(before.files) != entry.index:
                fail("upload target prefix changed before the one-shot PUT")
            links = current.get("links")
            bucket_raw = links.get("bucket") if isinstance(links, dict) else None
            if not isinstance(bucket_raw, str):
                fail("upload target lacks its exact bucket link")
            bucket = zenodo.validate_response_url(
                bucket_raw, self.client.base_url
            ).rstrip("/")
            raw = zenodo.read_regular_file(
                ROOT.joinpath(*pathlib.PurePosixPath(entry.path).parts),
                zenodo.MAX_UPLOAD_BYTES,
            )
            if (
                len(raw) != entry.size
                or hashlib.md5(raw).hexdigest() != entry.md5  # noqa: S324
                or hashlib.sha256(raw).hexdigest() != entry.sha256
                or git_blob_sha1(raw) != entry.git_blob_sha
                or any(secret in raw for secret in self.forbidden_secrets)
            ):
                fail("one-shot upload bytes differ for " + entry.name)
            self.client.request(
                "PUT",
                bucket + "/" + urllib.parse.quote(entry.name, safe=""),
                data=raw,
                content_type="application/octet-stream",
                accept=(200, 201, 202),
            )
        except zenodo.ZenodoError as exc:
            raise RemoteMutationError(type(exc).__name__) from None

    def read_draft_once(self, record: RecordIdentity) -> DraftSnapshot:
        try:
            state, current = self.client.get_deposition_or_record(record.record_id)
        except zenodo.ZenodoError as exc:
            fail("draft reconciliation GET failed: " + str(exc))
        if state != "draft":
            fail("draft reconciliation observed a published record")
        snapshot = self._draft_snapshot(current, verify_unseen_prefix=True)
        if snapshot.record != record:
            fail("draft reconciliation record identity changed")
        return snapshot

    def publish_once(self, record: RecordIdentity) -> None:
        try:
            self.client.request(
                "POST",
                f"/api/deposit/depositions/{record.record_id}/actions/publish",
                accept=(200, 201, 202),
            )
        except zenodo.ZenodoError as exc:
            raise RemoteMutationError(type(exc).__name__) from None


def _anonymous_open(
    opener: urllib.request.OpenerDirector,
    request: urllib.request.Request,
    maximum: int,
    *,
    accept_missing: bool = False,
) -> tuple[int, bytes]:
    response: Any
    try:
        response = opener.open(request, timeout=120)
    except urllib.error.HTTPError as exc:
        response = exc
    except (OSError, TimeoutError, urllib.error.URLError) as exc:
        fail("anonymous public transport failed: " + type(exc).__name__)
    try:
        status = int(response.status)
        if response.geturl() != request.full_url:
            fail("anonymous public response URL changed")
        raw = response.read(maximum + 1)
    finally:
        response.close()
    if len(raw) > maximum:
        fail("anonymous public response exceeded its exact byte bound")
    if status == 404 and accept_missing:
        return status, raw
    if status != 200:
        fail(f"anonymous public GET was rejected (HTTP {status})")
    return status, raw


class AnonymousZenodoPublicAdapter:
    """Credential-free, proxy-free, redirect-free final record gate."""

    def __init__(
        self,
        contract: FrozenUploadContract,
        metadata: Mapping[str, Any],
    ) -> None:
        self.contract = contract
        self.metadata = dict(metadata)
        self.opener = build_anonymous_public_opener()

    def read_public_once(self, record: RecordIdentity) -> PublicSnapshot | None:
        url = f"https://zenodo.org/api/records/{record.record_id}"
        status, raw = _anonymous_open(
            self.opener,
            build_anonymous_public_request(url),
            MAX_PUBLIC_JSON_BYTES,
            accept_missing=True,
        )
        if status == 404:
            return None
        value = strict_json_bytes(raw, "anonymous public record")
        if (
            zenodo._record_id(value, "anonymous public record") != record.record_id
            or zenodo._doi_from_deposition(value, "anonymous public record")
            != record.doi
            or not zenodo._published_metadata_matches(
                value.get("metadata"), self.metadata
            )
        ):
            fail("anonymous public record identity or metadata differs")
        metadata = value.get("metadata")
        conceptdoi = value.get("conceptdoi") or (
            metadata.get("conceptdoi") if isinstance(metadata, dict) else None
        )
        if not isinstance(conceptdoi, str) or DOI.fullmatch(conceptdoi) is None:
            fail("anonymous public record concept DOI differs")
        raw_files = value.get("files")
        if not isinstance(raw_files, list) or not all(
            isinstance(item, dict) for item in raw_files
        ):
            fail("anonymous public record files differ")
        by_name: dict[str, Mapping[str, Any]] = {}
        for item in raw_files:
            name = item.get("key", item.get("filename"))
            if not isinstance(name, str) or not name or name in by_name:
                fail("anonymous public record contains an invalid/duplicate file")
            by_name[name] = item
        if set(by_name) != {entry.name for entry in self.contract.entries}:
            fail("anonymous public files are not the exact frozen 65 uploads")
        files: list[ServerFile] = []
        for entry in self.contract.entries:
            item = by_name[entry.name]
            size = item.get("size", item.get("filesize"))
            if isinstance(size, str) and size.isdecimal():
                size = int(size)
            checksum = item.get("checksum")
            if size != entry.size or checksum not in {entry.md5, "md5:" + entry.md5}:
                fail("anonymous public server identity differs for " + entry.name)
            content_url = (
                f"https://zenodo.org/api/records/{record.record_id}/files/"
                + urllib.parse.quote(entry.name, safe="")
                + "/content"
            )
            _status, content = _anonymous_open(
                self.opener,
                build_anonymous_public_request(content_url),
                entry.size,
            )
            if (
                len(content) != entry.size
                or hashlib.md5(content).hexdigest() != entry.md5  # noqa: S324
                or hashlib.sha256(content).hexdigest() != entry.sha256
            ):
                fail("anonymous public redownload differs for " + entry.name)
            files.append(
                ServerFile(entry.name, entry.size, entry.md5, entry.sha256)
            )
        return PublicSnapshot(
            record,
            conceptdoi,
            self.contract.metadata_sha256,
            tuple(reversed(files)),
            PublicTransportAttestation(),
        )


def _canonical_remote_consumption(
    manifest: Mapping[str, Any],
    execution_head: str,
    github_token: str,
) -> dict[str, Any]:
    try:
        observed = publish._acquire_remote_consumption_lock(
            ROOT, manifest, execution_head, github_token
        )
    except zenodo.ZenodoError as exc:
        fail("authorization consumption failed: " + str(exc))
    expected_ref = manifest["owner_authorization"]["remote_consumption_ref"]
    expected_keys = {
        "remote",
        "api_origin",
        "repository",
        "ref",
        "tag_object",
        "object_type",
        "execution_head",
        "acquisition",
        "recovery_mode",
    }
    recovery_mode = observed.get("recovery_mode")
    tag_object = observed.get("tag_object")
    if (
        set(observed) != expected_keys
        or observed.get("remote") != "github_git_data_api"
        or observed.get("api_origin") != GITHUB_API_BASE
        or observed.get("repository") != REPOSITORY
        or observed.get("ref") != expected_ref
        or not isinstance(tag_object, str)
        or HEX40.fullmatch(tag_object) is None
        or observed.get("object_type") != "tag"
        or observed.get("execution_head") != execution_head
        or observed.get("acquisition") != "GITHUB_GIT_DATA_REST_CREATE_ONLY"
        or recovery_mode
        not in {"NEWLY_CREATED_REF", "EXISTING_EXACT_REF_NO_CREATE"}
    ):
        fail("authorization consumption identity differs")
    if recovery_mode == "NEWLY_CREATED_REF":
        try:
            status, tag_value = publish._github_api_request(
                "GET",
                "/repos/Goldkelch/qik-vrt/git/tags/" + tag_object,
                github_token,
                accept=(200, 404),
            )
            if status != 200:
                fail("new authorization consumption ref lacks its tag object")
            publish._validate_github_tag_response(
                tag_value,
                publish._expected_consumption_tag(manifest, execution_head),
                tag_object,
            )
        except zenodo.ZenodoError as exc:
            fail("new authorization consumption tag readback failed: " + str(exc))
    return {
        "remote": "github_git_data_api",
        "api_origin": GITHUB_API_BASE,
        "repository": REPOSITORY,
        "ref": expected_ref,
        "tag_object": tag_object,
        "object_type": "tag",
        "execution_head": execution_head,
        "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
        "recovery_mode": recovery_mode,
    }


def _generic_evidence_callbacks(
    manifest_path: pathlib.Path,
    manifest: Mapping[str, Any],
    execution_head: str,
    remote_consumption: Mapping[str, Any],
) -> tuple[
    Callable[[PublicSnapshot], Mapping[str, Any]],
    Callable[[Mapping[str, Any]], Mapping[str, Any]],
]:
    def factory(snapshot: PublicSnapshot) -> Mapping[str, Any]:
        return publish._phase_evidence(
            manifest_path,
            ROOT,
            manifest,
            execution_head,
            remote_consumption,
            "public_verified",
            record_id=snapshot.record.record_id,
            doi=snapshot.record.doi,
            published={
                "id": snapshot.record.record_id,
                "doi": snapshot.record.doi,
                "conceptdoi": snapshot.conceptdoi,
                "links": {
                    "html": f"https://zenodo.org/records/{snapshot.record.record_id}"
                },
            },
        )

    def validator(value: Mapping[str, Any]) -> Mapping[str, Any]:
        return publish._validate_recovery_evidence(
            value,
            manifest_path,
            ROOT,
            manifest,
            execution_head,
        )

    return factory, validator


def _verify_final_controller(
    controller: RecoveryController,
    public: AnonymousZenodoPublicAdapter,
    factory: Callable[[PublicSnapshot], Mapping[str, Any]],
    validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    final = controller.final_checkpoint
    record = controller.current_record
    if final is None or record is None:
        fail("final receipt lacks its durable record identity")
    snapshot = public.read_public_once(record)
    if snapshot is None:
        fail("final receipt public record is no longer anonymously visible")
    evidence = strict_json_bytes(final.evidence_bytes, "final publication receipt")
    normalized = dict(validator(evidence))
    regenerated = dict(factory(snapshot))
    regenerated_remote = regenerated.get("remote_consumption")
    persisted_remote = evidence.get("remote_consumption")
    if isinstance(regenerated_remote, dict) and isinstance(persisted_remote, dict):
        # A final receipt records what happened in the run that created it.
        # A later GET-only rerun necessarily observes the same consumption ref
        # as pre-existing.  Preserve the validated historical mode while
        # requiring every other freshly regenerated field to remain exact.
        regenerated_remote = dict(regenerated_remote)
        regenerated_remote["recovery_mode"] = persisted_remote.get(
            "recovery_mode"
        )
        regenerated["remote_consumption"] = regenerated_remote
    if normalized != evidence or regenerated != evidence:
        fail("final receipt differs from the fresh anonymous public record")
    return validate_generic_public_evidence(
        evidence, controller.contract, controller.context, snapshot
    )


def _verify_complete_draft_prefix(
    controller: RecoveryController,
    remote: UploadPort,
) -> None:
    """Require a fresh exact 65-file GET gate before prepare/publish effects."""
    record = controller.current_record
    if record is None:
        fail("complete draft verification lacks its durable record identity")
    snapshot = remote.read_draft_once(record)
    if exact_prefix_count(snapshot, controller.contract, record) != EXPECTED_UPLOADS:
        fail("complete draft verification differs from the exact 65-file prefix")


def execute_production(contract: FrozenUploadContract) -> tuple[dict[str, Any], str]:
    manifest_path, manifest = _load_production_manifest(contract)
    execution_head = _exact_execution_head()
    try:
        publish._validate_repository_source_head(ROOT, manifest_path, manifest)
        publish._validate_origin_repository(ROOT, REPOSITORY)
        secrets = publish._validated_network_secrets()
        publish._reject_owner_authorization_replay(
            ROOT,
            manifest["owner_authorization"],
            secrets,
        )
    except zenodo.ZenodoError as exc:
        fail("generic production boundary rejected execution: " + str(exc))
    github_token = secrets[GITHUB_TOKEN_ENVIRONMENT_VARIABLE]
    zenodo_token = secrets[ZENODO_TOKEN_ENVIRONMENT_VARIABLE]
    remote_consumption = _canonical_remote_consumption(
        manifest, execution_head, github_token
    )
    context = make_context(
        execution_head,
        manifest["manifest_sha256"],
        manifest["owner_authorization"]["consumption_key"]["value"],
        remote_consumption["tag_object"],
    )
    raw_date = _git_text("show", "-s", "--format=%cI", execution_head)
    parsed_date = datetime.datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    commit_date = (
        parsed_date.astimezone(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    receipt_api = GitHubReceiptAPI(github_token)
    checkpoint_port = GitHubCheckpointPort(
        receipt_api, execution_head, commit_date
    )
    history, recovery_head, publication_head, final = checkpoint_port.restore(
        contract, context
    )
    controller = RecoveryController(
        contract,
        context,
        checkpoint_port,
        history=history,
        recovery_head=recovery_head,
        publication_head=publication_head,
        final_checkpoint=final,
    )
    base_url = zenodo.validate_base_url(
        os.environ.get("ZENODO_API_BASE", zenodo.DEFAULT_BASE_URL)
    )
    if base_url != zenodo.DEFAULT_BASE_URL:
        fail("corpus recovery permits only the production Zenodo API origin")
    client = zenodo.ZenodoClient(zenodo_token, base_url, poll_attempts=1)
    remote = ProductionZenodoAdapter(
        client,
        zenodo_token,
        contract,
        manifest["metadata"],
        tuple(secrets.values()),
    )
    public = AnonymousZenodoPublicAdapter(contract, manifest["metadata"])
    factory, validator = _generic_evidence_callbacks(
        manifest_path,
        manifest,
        execution_head,
        remote_consumption,
    )
    if controller.phase == "public_verified":
        evidence = _verify_final_controller(
            controller, public, factory, validator
        )
        assert controller.final_checkpoint is not None
        return evidence, controller.final_checkpoint.commit_sha
    while controller.phase != "public_verified":
        phase = controller.phase
        if phase is None:
            controller.bootstrap_authorization_consumed()
        elif phase == "authorization_consumed":
            if remote.read_create_once(None):
                fail("pre-create inventory is not empty for the exact corpus identity")
            controller.create_record(remote)
        elif phase == "create_requested":
            controller.reconcile_create_requested(remote)
        elif phase == "record_created":
            state, count, _pending = _validate_preparation(
                controller.values[-1]["preparation"], contract
            )
            if state == "UPLOAD_INTENT":
                controller.reconcile_upload_intent(remote)
            elif count < EXPECTED_UPLOADS:
                controller.upload_next(remote)
            else:
                _verify_complete_draft_prefix(controller, remote)
                controller.mark_prepared()
        elif phase == "prepared":
            _verify_complete_draft_prefix(controller, remote)
            controller.publish_once(remote, public, factory, validator)
        elif phase == "publish_requested":
            controller.reconcile_publish_requested(public, factory, validator)
        else:
            fail("restored recovery phase is unsupported")
    if controller.final_checkpoint is None:
        fail("public_verified transition lacks its final receipt")
    evidence = strict_json_bytes(
        controller.final_checkpoint.evidence_bytes,
        "new final publication receipt",
    )
    assert controller.final_checkpoint is not None
    return evidence, controller.final_checkpoint.commit_sha


def _write_github_outputs(path: pathlib.Path | None, values: Mapping[str, Any]) -> None:
    if path is None:
        return
    lines: list[str] = []
    for key, raw in values.items():
        value = str(raw).lower() if isinstance(raw, bool) else str(raw)
        if (
            re.fullmatch(r"[a-z][a-z0-9_]*", key) is None
            or not value
            or "\n" in value
            or "\r" in value
        ):
            fail("unsafe GitHub output value")
        lines.append(f"{key}={value}\n")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
        try:
            raw = "".join(lines).encode("utf-8")
            offset = 0
            while offset < len(raw):
                written = os.write(descriptor, raw[offset:])
                if written <= 0:
                    fail("GitHub output write made no progress")
                offset += written
        finally:
            os.close(descriptor)
    except OSError as exc:
        fail("cannot write GitHub output: " + str(exc))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument(
        "--verify-contract",
        action="store_true",
        help="verify only the frozen local 65-file upload contract",
    )
    operations.add_argument(
        "--check",
        action="store_true",
        help="read-only verification of the exact contract and production manifest",
    )
    operations.add_argument(
        "--execute",
        action="store_true",
        help="restore and execute the dedicated production recovery transaction",
    )
    parser.add_argument("--github-output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        contract = load_frozen_contract()
        if args.verify_contract:
            print(
                "PASS verified retrospective proof corpus recovery contract: "
                f"uploads={len(contract.entries)} bytes={contract.total_bytes} "
                f"contract={contract.canonical_sha256}"
            )
            return 0
        if args.check:
            _manifest_path_value, manifest = _load_production_manifest(contract)
            print(
                "PASS checked retrospective proof corpus recovery controls: "
                f"uploads={len(contract.entries)} manifest={manifest['manifest_sha256']}"
            )
            return 0
        evidence, commit_sha = execute_production(contract)
        if (
            evidence.get("state") != "published"
            or evidence.get("phase") != "public_verified"
            or HEX40.fullmatch(commit_sha) is None
        ):
            fail("execute returned without exact public_verified evidence")
        outputs = {
            "state": "published",
            "phase": "public_verified",
            "finalized": True,
            "receipt_commit": commit_sha,
            "record_id": evidence["record_id"],
            "doi": evidence["doi"],
        }
        _write_github_outputs(args.github_output, outputs)
        print("CORPUS_RECOVERY_STATE=published")
        print("CORPUS_RECOVERY_PHASE=public_verified")
        print("CORPUS_RECOVERY_FINALIZED=true")
        print("CORPUS_RECOVERY_RECEIPT_COMMIT=" + commit_sha)
        print("ZENODO_RECORD_ID=" + str(evidence["record_id"]))
        print("ZENODO_DOI=" + str(evidence["doi"]))
        return 0
    except (
        CorpusRecoveryError,
        controls.CorpusPublicationControlError,
        zenodo.ZenodoError,
        RemoteMutationError,
    ) as exc:
        print("BLOCK: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
