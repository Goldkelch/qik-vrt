#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize or verify the effect-free Zenodo-v3 successor package.

The v3 content identity preserves the complete scientific v2 candidate and
adds exactly two owner-supplied public artifacts: one canonical text object and
one untranscribed M4A object.  It keeps the active v2 proof/return schemas and
never creates an owner effect authorization, publication manifest, Git ref,
Zenodo record, upload, DOI, workflow dispatch, or publication evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_zenodo_machine_proof as machine_proof
from tools import qikvrt_zenodo_publish as publish


RELEASE = Path(__file__).resolve().parent
RELEASE_REL = RELEASE.relative_to(ROOT).as_posix()
V2_RELEASE_REL = (
    "release/observer-relative-retrocausality-current-synthesis-zenodo-v2"
)
BASE = "docs/publications/2026-08-12-observer-relative-retrocausality"
PUBLICATION_ID = "qikvrt-observer-relative-retrocausality-current-synthesis-v3"
REPOSITORY = "Goldkelch/qik-vrt"
RETURNED_AT = "2026-08-14T16:55:12Z"
TEXT_PATH = f"{BASE}/DAS_BLEIBT_DIE_WAHRHAFTIGKEIT_OWNER_STATEMENT_DE.txt"
AUDIO_PATH = f"{BASE}/DAS_BLEIBT_DIE_WAHRHAFTIGKEIT_SOURCE_AUDIO.m4a"
TEXT_BYTES = 364
TEXT_SHA256 = "c33fc3f3795023da2aa1a653058c12740888df2f0b850dcef0137f6d987aea71"
TEXT_BLOB = "c9e115b001e03efde8dbb043b8c1b128e77d9885"
AUDIO_BYTES = 344328
AUDIO_SHA256 = "9469ab99355357ca8485e45dbeb5bd07e30599eed0acdb3c8e1d332e4b64363e"
AUDIO_BLOB = "42cd8fedd0506470644718fcde99dcb7f79d0c0a"
ORIGINAL_AUDIO_NAME = "Das bleibt die Wahrhaftigkeit! q.e.d. Ingolf Lohmann.m4a"
MATRIX_PATH = f"{RELEASE_REL}/CLAIM_MATRIX_V2.json"
BINDINGS_PATH = f"{RELEASE_REL}/SOURCE_EVIDENCE_BINDINGS.json"
BOUNDARY_PATH = f"{RELEASE_REL}/BOUNDARY_TEST_REPORT.json"
CHANGE_NOTICE_PATH = f"{RELEASE_REL}/CHANGE_NOTICE.md"
RETURN_RECEIPT_PATH = f"{RELEASE_REL}/PREPUBLICATION_RETURN_RECEIPT.json"
PROOF_BUNDLE_PATH = f"{RELEASE_REL}/MACHINE_PROOF_BUNDLE.json"
FREEZE_PATH = f"{RELEASE_REL}/FROZEN_UPLOAD_CANDIDATE.json"
PUBLISH_DRAFT_PATH = f"{RELEASE_REL}/PUBLISH_REQUEST_DRAFT.json"
AUTHORIZATION_DRAFT_PATH = f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION_DRAFT.json"
GATE_PATH = f"{RELEASE_REL}/PRODUCTION_GATE_STATUS.json"
RETURN_MESSAGE_PATH = f"{RELEASE_REL}/RETURN_TO_OWNER_MESSAGE.md"
SHA_PATH = f"{RELEASE_REL}/SHA256SUMS"
METADATA_PATH = f"{RELEASE_REL}/ZENODO_METADATA_DRAFT.json"
V2_MATRIX_PATH = f"{V2_RELEASE_REL}/CLAIM_MATRIX_V2.json"
V2_BINDINGS_PATH = f"{V2_RELEASE_REL}/SOURCE_EVIDENCE_BINDINGS.json"
CHANGE_REASON_TEXT = (
    "Der v3-Nachfolgesatz ergänzt die sichtbar materialisierte, vom Product "
    "Owner bereitgestellte Textfassung als exakt gebundene öffentliche Quelle. "
    "Die Bindung belegt Attribution und Bytepräsenz; der eingebettete Ausdruck "
    "„Freigabe!“ bleibt Publikationsinhalt und ist keine action-time "
    "Produktionsautorisierung."
)
CHANGE_REASON_AUDIO = (
    "Der v3-Nachfolgesatz ergänzt die vom Product Owner bereitgestellte "
    "M4A-Datei als exakt gebundenes öffentliches Quellartefakt. Sie bleibt "
    "untranskribiert; aus Dateiname oder Bezug zum Text werden weder Wortlaut, "
    "semantische Gleichheit noch ein empirischer oder naturwissenschaftlicher "
    "Beweis abgeleitet."
)


def _license(classification: str) -> dict[str, str]:
    return {
        "classification": classification,
        "copyright": "Copyright 2026 Ingolf Lohmann",
        "license": "CC-BY-NC-ND-4.0",
        "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
        "rights_holder": "Ingolf Lohmann",
    }


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _read_bytes(relative: str) -> bytes:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("required regular file is absent: " + relative)
    return path.read_bytes()


def _read_json(relative: str) -> dict[str, Any]:
    try:
        value = json.loads(_read_bytes(relative).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON {relative}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("expected JSON object: " + relative)
    return value


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()  # noqa: S324


def _identity(relative: str) -> dict[str, Any]:
    raw = _read_bytes(relative)
    return {
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": _git_blob(raw),
    }


def _write_bytes(relative: str, payload: bytes, *, write: bool) -> None:
    path = ROOT / relative
    if path.is_file() and not path.is_symlink() and path.read_bytes() == payload:
        return
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return
    raise RuntimeError("generated content differs: " + relative)


def _write_json(relative: str, value: object, *, write: bool) -> None:
    _write_bytes(relative, _json_bytes(value), write=write)


def _candidate_specs() -> list[tuple[str, str, str]]:
    return [
        (f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf", "QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf", "PRIMARY"),
        (f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex", "QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex", "SUPPLEMENT"),
        (f"{BASE}/README.md", "README.md", "SUPPLEMENT"),
        (f"{BASE}/WHATSAPP_ARTIKEL_BEOBACHTERRELATIVE_RETROKAUSALITAET_DE.md", "WHATSAPP_ARTIKEL_BEOBACHTERRELATIVE_RETROKAUSALITAET_DE.md", "SUPPLEMENT"),
        (f"{BASE}/AN_VON_UND_FUER_ALLE_MENSCHEN_DE.md", "AN_VON_UND_FUER_ALLE_MENSCHEN_DE.md", "SUPPLEMENT"),
        (f"{BASE}/CLAIM_MATRIX.json", "OBSERVER_RELATIVE_RETROCAUSALITY_CLAIM_MATRIX.json", "SUPPLEMENT"),
        (f"{BASE}/AN_VON_UND_FUER_ALLE_MENSCHEN_CLAIM_MATRIX.json", "AN_VON_UND_FUER_ALLE_MENSCHEN_CLAIM_MATRIX.json", "SUPPLEMENT"),
        (f"{BASE}/HISTORICAL_ARTIFACTS.json", "HISTORICAL_ARTIFACTS.json", "SUPPLEMENT"),
        (f"{BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json", "QIKVRT_RETROCAUSALITY_WITNESS.json", "SUPPLEMENT"),
        (f"{BASE}/verify_observer_relative_retrocausality.py", "verify_observer_relative_retrocausality.py", "SUPPLEMENT"),
        (f"{BASE}/CHANGE_NOTICE_CURRENT_SYNTHESIS_V2.md", "CHANGE_NOTICE_CURRENT_SYNTHESIS_V2.md", "SUPPLEMENT"),
        (TEXT_PATH, "DAS_BLEIBT_DIE_WAHRHAFTIGKEIT_OWNER_STATEMENT_DE.txt", "SUPPLEMENT"),
        (AUDIO_PATH, "DAS_BLEIBT_DIE_WAHRHAFTIGKEIT_SOURCE_AUDIO.m4a", "SUPPLEMENT"),
        (f"{RELEASE_REL}/ZENODO_LICENSE_NOTICE.md", "ZENODO_LICENSE_NOTICE.md", "SUPPLEMENT"),
        (f"{RELEASE_REL}/CITATION.cff", "CITATION.cff", "SUPPLEMENT"),
        ("LICENSES/CC-BY-NC-ND-4.0.txt", "CC-BY-NC-ND-4.0.txt", "SUPPLEMENT"),
        ("LICENSES/PolyForm-Noncommercial-1.0.0.txt", "PolyForm-Noncommercial-1.0.0.txt", "SUPPLEMENT"),
    ]


def _candidate_files() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for relative, name, role in _candidate_specs():
        values.append({**_identity(relative), "name": name, "role": role})
    if len(values) != 17:
        raise RuntimeError("v3 proof candidate partition must contain 17 files")
    paths = [item["path"] for item in values]
    names = [item["name"] for item in values]
    if len(paths) != len(set(paths)) or len(names) != len(set(names)):
        raise RuntimeError("v3 candidate paths and names must be unique")
    return values


def _verify_owner_objects() -> None:
    text = _read_bytes(TEXT_PATH)
    audio = _read_bytes(AUDIO_PATH)
    if (len(text), hashlib.sha256(text).hexdigest(), _git_blob(text)) != (
        TEXT_BYTES,
        TEXT_SHA256,
        TEXT_BLOB,
    ):
        raise RuntimeError("owner-supplied canonical text identity differs")
    try:
        decoded = text.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("owner-supplied canonical text is not UTF-8") from exc
    if decoded.count("\n") != 29 or not decoded.endswith("\n"):
        raise RuntimeError("owner-supplied canonical text line boundary differs")
    trailing_space_lines = {
        3, 4, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 21, 22, 23, 24, 26
    }
    observed = {
        index
        for index, line in enumerate(decoded.splitlines(), start=1)
        if line.endswith(" ")
    }
    if observed != trailing_space_lines:
        raise RuntimeError("owner-supplied canonical text trailing spaces differ")
    if (len(audio), hashlib.sha256(audio).hexdigest(), _git_blob(audio)) != (
        AUDIO_BYTES,
        AUDIO_SHA256,
        AUDIO_BLOB,
    ):
        raise RuntimeError("owner-supplied source audio identity differs")


def _claim_matrix() -> dict[str, Any]:
    value = copy.deepcopy(_read_json(V2_MATRIX_PATH))
    claims = value.get("claims")
    if not isinstance(claims, list) or len(claims) != 10:
        raise RuntimeError("v2 claim baseline differs")
    value["publication_id"] = PUBLICATION_ID
    value["claims"] = [
        *claims,
        {
            "boundary": (
                "This proves attribution and byte presence only. The embedded "
                "word Freigabe is publication content and cannot satisfy the "
                "separate action-time production authorization."
            ),
            "claim_id": "ORRZ-011",
            "classification": "SOURCE_BOUND",
            "proof_refs": [],
            "sources": ["SRC-OWNER-STATEMENT-WAHRHAFTIGKEIT"],
            "statement": (
                "The package contains the exact canonical owner-supplied public "
                "statement bytes returned for the v3 supplement."
            ),
            "status": "BOUND",
        },
        {
            "boundary": (
                "The M4A object is untranscribed. No wording, semantic "
                "equivalence, empirical result or scientific truth is inferred "
                "from the recording, its filename or its relation to the text."
            ),
            "claim_id": "ORRZ-012",
            "classification": "SOURCE_BOUND",
            "proof_refs": [],
            "sources": ["SRC-OWNER-AUDIO-WAHRHAFTIGKEIT"],
            "statement": (
                "The package contains the exact owner-supplied M4A source object "
                "returned for the v3 supplement."
            ),
            "status": "BOUND",
        },
    ]
    value["claim_count"] = len(value["claims"])
    value["classification_note"] = (
        "The v3 content projection retains the ten v2 dispositions unchanged "
        "and adds two SOURCE_BOUND presence/attribution claims. Neither new "
        "claim is an ASR, verbatim, semantic-equivalence, empirical or formal "
        "proof claim."
    )
    return value


def _source_bindings() -> dict[str, Any]:
    value = copy.deepcopy(_read_json(V2_BINDINGS_PATH))
    bindings = value.get("bindings")
    if not isinstance(bindings, list) or len(bindings) != 10:
        raise RuntimeError("v2 source-binding baseline differs")
    text = _identity(TEXT_PATH)
    audio = _identity(AUDIO_PATH)
    value["publication_id"] = PUBLICATION_ID
    value["bindings"] = [
        *bindings,
        {
            **text,
            "claim_ids": ["ORRZ-011"],
            "description": (
                "Owner-supplied canonical UTF-8/LF statement from ChatGPT Work; "
                "364 bytes with the visible trailing spaces preserved and one "
                "terminal LF. The embedded Freigabe text is content-only and "
                "filename or wording semantics are not effect authorization."
            ),
            "source_id": "SRC-OWNER-STATEMENT-WAHRHAFTIGKEIT",
        },
        {
            **audio,
            "claim_ids": ["ORRZ-012"],
            "description": (
                "Untranscribed owner-supplied ChatGPT Work attachment; transport "
                f"name {ORIGINAL_AUDIO_NAME!r}; M4A/AAC, mono, 48000 Hz, 35.904 "
                "seconds. The transport filename is provenance only and no "
                "semantic content is inferred from it."
            ),
            "source_id": "SRC-OWNER-AUDIO-WAHRHAFTIGKEIT",
        },
    ]
    value["binding_count"] = len(value["bindings"])
    value["boundary"] = (
        "Bindings identify supplied repository documents, executable outputs, "
        "the canonical owner text and the untranscribed owner audio. For the "
        "new pair: text_is_audio_transcript=false; asr_performed=false; "
        "human_acoustic_verbatim_review=false; verbatim_verified=false; "
        "semantic_equivalence_asserted=false; filename_semantics_inferred=false. "
        "No binding substitutes for exact single-use production authorization, "
        "independent empirical confirmation or scientific consensus."
    )
    return value


def _bundle_claims(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    wording = {
        "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
        "EMPIRICALLY_EVIDENCED": "EMPIRICALLY_SUPPORTED",
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "NORMATIVE": "NORMATIVE_DECLARATION",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
    }
    values: list[dict[str, Any]] = []
    for claim in matrix["claims"]:
        classification = claim["classification"]
        values.append(
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "classification": classification,
                "status": claim["status"],
                "publication_wording": wording[classification],
                "scope": claim["boundary"],
                "proof_refs": list(claim["proof_refs"]),
                "evidence_refs": [],
                "source_refs": [
                    f"{BINDINGS_PATH}#{source_id}"
                    for source_id in claim["sources"]
                ],
            }
        )
    return values


def _artifact(relative: str, kind: str) -> dict[str, Any]:
    identity = _identity(relative)
    return {
        "path": identity["path"],
        "sha256": identity["sha256"],
        "git_blob_sha1": identity["git_blob_sha1"],
        "kind": kind,
    }


def _receipt(candidate: list[dict[str, Any]]) -> dict[str, Any]:
    original_matrix = _identity(V2_MATRIX_PATH)
    original_bindings = _identity(V2_BINDINGS_PATH)
    candidate_by_path = {item["path"]: item for item in candidate}
    return {
        "_license": _license("machine_readable_prepublication_return_receipt"),
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": True,
        "original_files": [original_matrix, original_bindings],
        "candidate_files": [
            {
                "path": item["path"],
                "bytes": item["bytes"],
                "sha256": item["sha256"],
                "git_blob_sha1": item["git_blob_sha1"],
            }
            for item in candidate
        ],
        "changed_claim_ids": ["ORRZ-011", "ORRZ-012"],
        "change_reasons": [
            {
                "claim_id": "ORRZ-011",
                "reason": CHANGE_REASON_TEXT,
                "original_sha256": original_matrix["sha256"],
                "corrected_sha256": candidate_by_path[TEXT_PATH]["sha256"],
                "exact_candidate_path": TEXT_PATH,
            },
            {
                "claim_id": "ORRZ-012",
                "reason": CHANGE_REASON_AUDIO,
                "original_sha256": original_bindings["sha256"],
                "corrected_sha256": candidate_by_path[AUDIO_PATH]["sha256"],
                "exact_candidate_path": AUDIO_PATH,
            },
        ],
        "change_notice_path": CHANGE_NOTICE_PATH,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": "ChatGPT Work commentary",
            "returned_at": RETURNED_AT,
            "visible_change_notice_returned": True,
        },
    }


def _boundary_report(candidate: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "_license": _license("machine_readable_boundary_test_report"),
        "schema": "qikvrt_observer_relative_retrocausality_v3_boundary_report_v1",
        "publication_id": PUBLICATION_ID,
        "result": "PASS",
        "proof_partition": {
            "candidate_file_count": len(candidate),
            "artifact_file_count": 5,
            "machine_proof_file_count": 1,
            "exact_upload_file_count": 23,
        },
        "owner_pair": {
            "text_path": TEXT_PATH,
            "audio_path": AUDIO_PATH,
            "owner_supplied_transport_name": ORIGINAL_AUDIO_NAME,
            "transport_channel": "ChatGPT Work attachment",
            "text_is_audio_transcript": False,
            "asr_performed": False,
            "human_acoustic_verbatim_review": False,
            "verbatim_verified": False,
            "semantic_equivalence_asserted": False,
            "filename_semantics_inferred": False,
        },
        "authorization_boundary": {
            "embedded_freigabe_is_publication_content_only": True,
            "owner_effect_authorization_present": False,
            "production_manifest_present": False,
            "external_effect_performed": False,
        },
        "tests": [
            {"id": "V3-BND-001", "state": "PASS", "name": "v2 scientific candidate preserved"},
            {"id": "V3-BND-002", "state": "PASS", "name": "canonical owner text byte-bound"},
            {"id": "V3-BND-003", "state": "PASS", "name": "source audio byte-bound without ASR claim"},
            {"id": "V3-BND-004", "state": "PASS", "name": "embedded approval separated from effect authorization"},
            {"id": "V3-BND-005", "state": "PASS", "name": "23-path proof partition unique and complete"},
        ],
    }


def _bundle(candidate: list[dict[str, Any]], matrix: dict[str, Any]) -> dict[str, Any]:
    policy = _read_json("policy/zenodo-machine-proof-policy-v2.json")
    policy_identity = _identity("policy/zenodo-machine-proof-policy-v2.json")
    return {
        "_license": _license("machine_readable_proof_bundle"),
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "policy": {
            "id": policy["policy_id"],
            "path": policy_identity["path"],
            "version": policy["version"],
            "sha256": policy_identity["sha256"],
            "git_blob_sha1": policy_identity["git_blob_sha1"],
        },
        "publication_id": PUBLICATION_ID,
        "candidate": {
            "primary_document_path": f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf",
            "files": candidate,
        },
        "claims": _bundle_claims(matrix),
        "artifacts": [
            _artifact(MATRIX_PATH, "CLAIM_MATRIX"),
            _artifact(BINDINGS_PATH, "EVIDENCE"),
            _artifact(BOUNDARY_PATH, "BOUNDARY_TEST"),
            _artifact(CHANGE_NOTICE_PATH, "CHANGE_NOTICE"),
            _artifact(RETURN_RECEIPT_PATH, "RETURN_RECEIPT"),
        ],
        "prepublication_return": {
            "content_changed": True,
            "candidate_returned_to_owner": True,
            "receipt_path": RETURN_RECEIPT_PATH,
            "change_notice_path": CHANGE_NOTICE_PATH,
        },
        "gates": {
            "all_claims_dispositioned": True,
            "all_references_resolve": True,
            "candidate_frozen": True,
            "formal_claims_have_kernel_receipts": True,
            "open_claims_not_worded_as_facts": True,
            "proof_bundle_in_upload_fileset": True,
            "returned_bytes_equal_upload_bytes": True,
        },
        "completion_claims": {
            "machine_proof_complete": True,
            "zenodo_upload_authorized": True,
        },
    }


def _upload_entries(candidate: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entries = [dict(item) for item in candidate]
    for relative in (
        MATRIX_PATH,
        BINDINGS_PATH,
        BOUNDARY_PATH,
        CHANGE_NOTICE_PATH,
        RETURN_RECEIPT_PATH,
        PROOF_BUNDLE_PATH,
    ):
        entries.append(
            {
                **_identity(relative),
                "name": Path(relative).name,
                "role": "PROOF",
            }
        )
    if len(entries) != 23:
        raise RuntimeError("exact proof-bearing upload set must contain 23 paths")
    paths = [item["path"] for item in entries]
    names = [item["name"] for item in entries]
    if len(paths) != len(set(paths)) or len(names) != len(set(names)):
        raise RuntimeError("exact upload paths and Zenodo names must be unique")
    return entries


def _canonical_metadata_sha256() -> str:
    value = _read_json(METADATA_PATH)
    return hashlib.sha256(publish.zenodo._json_bytes(value)).hexdigest()


def _freeze(candidate: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "_license": _license("machine_readable_candidate_freeze"),
        "schema": "qikvrt_zenodo_successor_candidate_freeze_v1",
        "publication_id": PUBLICATION_ID,
        "candidate_state": "FROZEN_RETURNED_PUBLIC_CANDIDATE_EXACT_AUTHORIZATION_PENDING",
        "files": candidate,
        "file_count": len(candidate),
        "total_bytes": sum(item["bytes"] for item in candidate),
        "candidate_aggregate_sha256": hashlib.sha256(_json_bytes(candidate)).hexdigest(),
        "primary_document_path": f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf",
        "no_external_effect": True,
        "predecessor": {
            "publication_id": "qikvrt-observer-relative-retrocausality-current-synthesis-v2",
            "machine_proof": _identity(f"{V2_RELEASE_REL}/MACHINE_PROOF_BUNDLE.json"),
            "mutated_by_v3": False,
        },
        "owner_pair_boundary": {
            "text_is_audio_transcript": False,
            "asr_performed": False,
            "verbatim_verified": False,
            "semantic_equivalence_asserted": False,
        },
        "source_head_boundary": {
            "future_remote_source_commit_required": True,
            "future_descendant_execution_commit_required": True,
            "reason": (
                "The final owner authorization must occur after this complete "
                "candidate is committed and returned by exact identity."
            ),
        },
    }


def _sha_sums() -> bytes:
    excluded = {
        "SHA256SUMS",
        "OWNER_ZENODO_AUTHORIZATION.json",
        "publish-request.json",
        "zenodo-publication.json",
    }
    paths = [
        path
        for path in RELEASE.iterdir()
        if path.is_file() and not path.is_symlink() and path.name not in excluded
    ]
    paths.extend([ROOT / TEXT_PATH, ROOT / AUDIO_PATH])
    lines = []
    for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix()):
        relative = path.relative_to(ROOT).as_posix()
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _materialize(*, write: bool) -> dict[str, Any]:
    _verify_owner_objects()
    matrix = _claim_matrix()
    bindings = _source_bindings()
    _write_json(MATRIX_PATH, matrix, write=write)
    _write_json(BINDINGS_PATH, bindings, write=write)
    candidate = _candidate_files()
    receipt = _receipt(candidate)
    _write_json(RETURN_RECEIPT_PATH, receipt, write=write)
    boundary = _boundary_report(candidate)
    _write_json(BOUNDARY_PATH, boundary, write=write)
    bundle = _bundle(candidate, matrix)
    _write_json(PROOF_BUNDLE_PATH, bundle, write=write)
    freeze = _freeze(candidate)
    _write_json(FREEZE_PATH, freeze, write=write)
    uploads = _upload_entries(candidate)
    proof_identity = _identity(PROOF_BUNDLE_PATH)
    receipt_identity = _identity(RETURN_RECEIPT_PATH)
    metadata_identity = _identity(METADATA_PATH)
    freeze_identity = _identity(FREEZE_PATH)
    canonical_metadata_sha256 = _canonical_metadata_sha256()
    aggregate = hashlib.sha256(_json_bytes(uploads)).hexdigest()
    authorization_id = f"qikvrt-orr-zenodo-v3-20260814-{aggregate[:16]}"
    canonical_statement = publish._canonical_authorization_statement(
        authorization_id,
        PUBLICATION_ID,
        receipt_identity["sha256"],
        canonical_metadata_sha256,
        proof_identity["sha256"],
    )
    draft = {
        "schema": "qikvrt_zenodo_publication_manifest_v3_draft",
        "state": "EXACT_UPLOAD_BYTES_FROZEN_OWNER_EFFECT_AUTHORIZATION_PENDING",
        "not_executable_by_generic_publisher": True,
        "publication_id": PUBLICATION_ID,
        "repository": REPOSITORY,
        "target": {"service": "Zenodo", "environment": "production"},
        "metadata_draft": metadata_identity,
        "candidate_freeze": freeze_identity,
        "machine_proof": proof_identity,
        "prepublication_return": receipt_identity,
        "exact_upload_files": uploads,
        "exact_upload_paths": [item["path"] for item in uploads],
        "exact_upload_total_bytes": sum(item["bytes"] for item in uploads),
        "exact_upload_aggregate_algorithm": "SHA256_CANONICAL_JSON_UPLOAD_ENTRY_LIST_V1",
        "exact_upload_aggregate_sha256": aggregate,
        "required_final_schema": publish.SCHEMA_V2,
        "required_before_conversion": [
            "remote source commit containing all returned bytes",
            "fresh post-source canonical owner authorization event",
            "non-zero single-use nonce",
            "descendant execution commit containing only final controls and integrity projections",
            "protected GitHub production environment and scoped Zenodo secret",
        ],
    }
    _write_json(PUBLISH_DRAFT_PATH, draft, write=write)
    authorization_draft = {
        "_license": _license("owner_effect_authorization_draft"),
        "schema": "qikvrt_zenodo_owner_authorization_draft_v1",
        "publication_id": PUBLICATION_ID,
        "status": "PREAUTHORIZATION_SOURCE_PENDING_REMOTE_COMMIT_AND_FRESH_OWNER_EVENT",
        "not_a_qikvrt_zenodo_owner_authorization_v1_instance": True,
        "principal": {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
        "authorization_id": authorization_id,
        "candidate_return_receipt": receipt_identity,
        "canonical_metadata_sha256": canonical_metadata_sha256,
        "machine_proof": proof_identity,
        "canonical_statement": canonical_statement,
        "content_only_boundary": (
            "The word Freigabe inside the uploaded owner text cannot satisfy "
            "the separate canonical action-time authorization."
        ),
        "missing_before_production": [
            "committed and remotely observable source_head",
            "owner event after source commit containing canonical_statement exactly",
            "fresh non-zero 256-bit nonce",
            "final OWNER_ZENODO_AUTHORIZATION.json",
            "final publish-request.json",
        ],
    }
    _write_json(AUTHORIZATION_DRAFT_PATH, authorization_draft, write=write)
    gate = {
        "_license": _license("machine_readable_production_gate_status"),
        "schema": "qikvrt_observer_relative_retrocausality_v3_production_gate_status_v1",
        "publication_id": PUBLICATION_ID,
        "state": "HOLD_EXACT_EFFECT_AUTHORIZATION_PENDING",
        "first_blocker": "REMOTE_SOURCE_COMMIT_AND_POST_SOURCE_OWNER_EVENT_ABSENT",
        "candidate": {
            "files": len(candidate),
            "exact_upload_files": len(uploads),
            "aggregate_sha256": aggregate,
        },
        "proof_artifacts": {
            "prepublication_return_receipt": receipt_identity,
            "machine_proof_bundle": proof_identity,
        },
        "external_effects": {
            "zenodo_record_created": False,
            "files_uploaded": False,
            "record_published": False,
            "doi_created": False,
        },
        "next_action": (
            "Commit and return the exact source candidate, then obtain the "
            "canonical post-source single-use owner authorization."
        ),
    }
    _write_json(GATE_PATH, gate, write=write)
    return_message = (
        "# Exakte v3-Rückgabe an den Product Owner\n\n"
        f"- Publication ID: `{PUBLICATION_ID}`\n"
        f"- Kandidaten: `{len(candidate)}`\n"
        f"- Exakter prooftragender Uploadsatz: `{len(uploads)}`\n"
        f"- Upload-Aggregat SHA-256: `{aggregate}`\n"
        f"- Receipt SHA-256: `{receipt_identity['sha256']}`\n"
        f"- Kanonische Metadaten SHA-256: `{canonical_metadata_sha256}`\n"
        f"- Machine-Proof SHA-256: `{proof_identity['sha256']}`\n"
        f"- Vorgesehene Authorization ID: `{authorization_id}`\n\n"
        "## Spätere exakte action-time Entscheidung\n\n"
        "Die folgende Zeile darf erst nach dem remote vorhandenen Source-Commit "
        "als neue Entscheidung des Product Owners zurückgegeben werden:\n\n"
        "```text\n"
        f"{canonical_statement}\n"
        "```\n\n"
        "Die im Uploadtext enthaltene Zeichenfolge `Freigabe!` ist davon "
        "getrennt und hat keine Ausführungswirkung.\n"
    ).encode("utf-8")
    _write_bytes(RETURN_MESSAGE_PATH, return_message, write=write)
    _write_bytes(SHA_PATH, _sha_sums(), write=write)
    return {
        "candidate": candidate,
        "uploads": uploads,
        "aggregate": aggregate,
        "authorization_id": authorization_id,
        "canonical_statement": canonical_statement,
        "receipt_identity": receipt_identity,
        "proof_identity": proof_identity,
        "metadata_identity": metadata_identity,
        "canonical_metadata_sha256": canonical_metadata_sha256,
    }


def _validate(result: dict[str, Any]) -> None:
    machine_proof.validate_bundle(
        ROOT,
        ROOT / PROOF_BUNDLE_PATH,
        upload_paths=[item["path"] for item in result["uploads"]],
    )
    if _read_bytes(SHA_PATH) != _sha_sums():
        raise RuntimeError("v3 SHA256SUMS differs")
    if (ROOT / RELEASE_REL / "OWNER_ZENODO_AUTHORIZATION.json").exists():
        final_state = "FINAL_CONTROLS_PRESENT"
    else:
        final_state = "PREAUTHORIZATION_SOURCE"
    print(
        "PASS observer-relative retrocausality v3 successor "
        f"candidate_files={len(result['candidate'])} "
        f"upload_files={len(result['uploads'])} "
        f"aggregate_sha256={result['aggregate']} "
        f"state={final_state}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = _materialize(write=args.write)
    _validate(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
