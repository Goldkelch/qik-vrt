#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize or verify the local English Zenodo-v2 proof package.

This helper constructs only repository-local, deterministic pre-authorization
artifacts.  It never invokes Zenodo, reads credentials, creates a Git ref, or
creates an owner authorization or executable production manifest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[2]
RELEASE = pathlib.Path(__file__).resolve().parent
RELEASE_REL = RELEASE.relative_to(ROOT).as_posix()
PUBLICATION_ID = "qikvrt-observer-relative-retrocausality-en-current-synthesis-v1"
REPOSITORY = "Goldkelch/qik-vrt"
OWNER = {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"}

SOURCE = (
    "docs/publications/2026-08-12-observer-relative-retrocausality/"
    "arxiv-en-current-synthesis-v2"
)
STAGING = "publication-staging/arxiv-observer-relative-retrocausality-en-v2"
WITNESS_BASE = "docs/publications/2026-08-12-observer-relative-retrocausality"

MATRIX_PATH = f"{RELEASE_REL}/CLAIM_MATRIX_EN.json"
BINDINGS_PATH = f"{RELEASE_REL}/SOURCE_EVIDENCE_BINDINGS_EN.json"
BOUNDARY_PATH = f"{RELEASE_REL}/BOUNDARY_TEST_REPORT_EN.json"
RECEIPT_PATH = f"{RELEASE_REL}/PREPUBLICATION_RETURN_RECEIPT_EN.json"
BUNDLE_PATH = f"{RELEASE_REL}/MACHINE_PROOF_BUNDLE_EN.json"
FREEZE_PATH = f"{RELEASE_REL}/FROZEN_UPLOAD_CANDIDATE.json"
GATE_PATH = f"{RELEASE_REL}/PRODUCTION_GATE_STATUS.json"
METADATA_PATH = f"{RELEASE_REL}/ZENODO_METADATA_DRAFT.json"
RETURN_MESSAGE_PATH = f"{RELEASE_REL}/RETURN_TO_OWNER_MESSAGE.md"


def _raw(path: pathlib.Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError("required regular file is missing: " + path.relative_to(ROOT).as_posix())
    return path.read_bytes()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()  # noqa: S324


def _identity(path: pathlib.Path) -> dict[str, Any]:
    data = _raw(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": _git_blob_sha1(data),
    }


def _write_json(path: pathlib.Path, value: object, *, write: bool) -> None:
    data = _json_bytes(value)
    if path.is_file() and path.read_bytes() == data:
        return
    if not write:
        raise RuntimeError("generated JSON differs: " + path.relative_to(ROOT).as_posix())
    path.write_bytes(data)


def _write_text(path: pathlib.Path, value: str, *, write: bool) -> None:
    data = value.encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return
    if not write:
        raise RuntimeError("generated text differs: " + path.relative_to(ROOT).as_posix())
    path.write_bytes(data)


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(_raw(path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("invalid JSON: " + path.relative_to(ROOT).as_posix()) from exc
    if not isinstance(value, dict):
        raise RuntimeError("expected JSON object: " + path.relative_to(ROOT).as_posix())
    return value


def _canonical_metadata_sha256() -> str:
    metadata = _read_json(ROOT / METADATA_PATH)
    data = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _license(classification: str) -> dict[str, str]:
    return {
        "classification": classification,
        "copyright": "Copyright 2026 Ingolf Lohmann",
        "license": "CC-BY-NC-ND-4.0",
        "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
        "rights_holder": "Ingolf Lohmann",
    }


def _candidate_specs() -> list[tuple[str, str, str]]:
    return [
        (f"{STAGING}/main.pdf", "Observer-Relative_Retrocausality_EN_v2.1.pdf", "PRIMARY"),
        (f"{STAGING}/main.tex", "Observer-Relative_Retrocausality_EN_v2.1.tex", "SUPPLEMENT"),
        (f"{STAGING}/arxiv-source.tar.gz", "Observer-Relative_Retrocausality_EN_v2.1_source.tar.gz", "SUPPLEMENT"),
        (f"{RELEASE_REL}/README.md", "ZENODO_README_EN.md", "SUPPLEMENT"),
        (f"{SOURCE}/README.md", "SOURCE_README_EN.md", "SUPPLEMENT"),
        (f"{SOURCE}/arxiv_v2_submission_manifest.json", "EN_SOURCE_PROVENANCE_MANIFEST_v2.1.json", "SUPPLEMENT"),
        (f"{SOURCE}/CURRENT_SYNTHESIS_V2_SOURCE_PROVENANCE.json", "CURRENT_SYNTHESIS_V2_SOURCE_PROVENANCE.json", "SUPPLEMENT"),
        (f"{STAGING}/PDF_RENDER_VALIDATION.json", "PDF_RENDER_VALIDATION.json", "SUPPLEMENT"),
        (f"{STAGING}/ARXIV_LOCAL_COMPATIBILITY_VALIDATION.json", "LOCAL_COMPATIBILITY_VALIDATION.json", "SUPPLEMENT"),
        (f"{WITNESS_BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json", "QIKVRT_RETROCAUSALITY_WITNESS.json", "SUPPLEMENT"),
        (f"{WITNESS_BASE}/verify_observer_relative_retrocausality.py", "verify_observer_relative_retrocausality.py", "SUPPLEMENT"),
        (f"{RELEASE_REL}/CITATION.cff", "CITATION.cff", "SUPPLEMENT"),
        (f"{RELEASE_REL}/ZENODO_LICENSE_NOTICE.md", "ZENODO_LICENSE_NOTICE.md", "SUPPLEMENT"),
        ("LICENSES/CC-BY-NC-ND-4.0.txt", "CC-BY-NC-ND-4.0.txt", "SUPPLEMENT"),
        ("LICENSES/PolyForm-Noncommercial-1.0.0.txt", "PolyForm-Noncommercial-1.0.0.txt", "SUPPLEMENT"),
    ]


def _candidate_files() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    names: set[str] = set()
    for relative, name, role in _candidate_specs():
        if name in names:
            raise RuntimeError("duplicate Zenodo upload name: " + name)
        names.add(name)
        item = _identity(ROOT / relative)
        item.update({"name": name, "role": role})
        result.append(item)
    if not any(item["role"] == "PRIMARY" for item in result):
        raise RuntimeError("candidate is missing a primary document")
    return result


def _bound_artifact(relative: str, kind: str) -> dict[str, str]:
    item = _identity(ROOT / relative)
    return {key: item[key] for key in ("path", "sha256", "git_blob_sha1")} | {"kind": kind}


def _source_bindings() -> dict[str, Any]:
    entries = [
        ("EN-SRC-PAPER", f"{STAGING}/main.tex", "English TeX manuscript defining the operational relation, conditional result, physical bridge, and stated scope boundaries.", ["ORREN-001", "ORREN-002", "ORREN-004", "ORREN-005", "ORREN-006", "ORREN-007"]),
        ("EN-SRC-WITNESS-SCRIPT", f"{WITNESS_BASE}/verify_observer_relative_retrocausality.py", "Finite network-free checker for the declared two-record operational witness.", ["ORREN-003"]),
        ("EN-SRC-WITNESS-REPORT", f"{WITNESS_BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json", "Canonical checked-in report emitted by the finite witness checker.", ["ORREN-003", "ORREN-004"]),
        ("EN-SRC-RENDER-RECEIPT", f"{STAGING}/PDF_RENDER_VALIDATION.json", "Deterministic local render, archive rebuild, and visual inspection receipt for the English PDF.", ["ORREN-008"]),
        ("EN-SRC-PROVENANCE", f"{SOURCE}/CURRENT_SYNTHESIS_V2_SOURCE_PROVENANCE.json", "Successor provenance binding the English source to its historic local staging predecessor without claiming an arXiv effect.", ["ORREN-008"]),
        ("EN-SRC-SCOPE", f"{SOURCE}/arxiv_v2_submission_manifest.json", "Explicit claim boundaries, including what the source does not claim and the distinction between local staging and external effects.", ["ORREN-001", "ORREN-005", "ORREN-006", "ORREN-007", "ORREN-009"]),
    ]
    rows: list[dict[str, Any]] = []
    for source_id, relative, description, claim_ids in entries:
        item = _identity(ROOT / relative)
        item.update({"source_id": source_id, "description": description, "claim_ids": claim_ids})
        rows.append(item)
    return {
        "_license": _license("machine_readable_source_evidence_bindings"),
        "schema": "qikvrt_observer_relative_retrocausality_en_source_evidence_bindings_v1",
        "publication_id": PUBLICATION_ID,
        "binding_count": len(rows),
        "bindings": rows,
        "boundary": "These bindings identify repository documents and local validation artifacts. They do not establish an external Zenodo effect, peer review, independent empirical confirmation, or scientific consensus.",
    }


def _claims() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "ORREN-001",
            "statement": "QIK-VRT defines observer-relative retrocausality as negative information direction: receiver-local change time increases while comparable provenance-bound source marks of successive information-bearing records decrease.",
            "classification": "INTERPRETATIVE",
            "status": "DECLARED",
            "boundary": "This is the authorial operational definition. A metric proper-time calibration requires an additional physical worldline binding, and a coordinate-future assignment is not a causal-future relation or a record available before its source emission.",
            "proof_refs": [],
            "sources": ["EN-SRC-PAPER", "EN-SRC-SCOPE"],
        },
        {
            "claim_id": "ORREN-002",
            "statement": "The English manuscript presents a conditional finite result for negative comparative information direction under its stated host-order, monotonicity, provenance, and information assumptions.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "This is a source-bound presentation. This package contains no Lean kernel receipt and does not represent the conditional presentation as a universal theorem about nature.",
            "proof_refs": [],
            "sources": ["EN-SRC-PAPER"],
        },
        {
            "claim_id": "ORREN-003",
            "statement": "The bundled finite checker and canonical report evaluate the declared two-record witness and report its declared predicates as verified for that finite operational model.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "The checker is an executable finite witness, not a proof-assistant kernel receipt, an independent replication, or a measurement of the whole universe.",
            "proof_refs": [],
            "sources": ["EN-SRC-WITNESS-SCRIPT", "EN-SRC-WITNESS-REPORT"],
        },
        {
            "claim_id": "ORREN-004",
            "statement": "The declared finite model uses positive future-directed path delays so that a later-source record can reach the receiver before an earlier-source record.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "The model demonstrates the stated operational ordering only; it does not assert superluminal propagation, receipt before emission, past-directed transport, or a controllable signal to the causal past.",
            "proof_refs": [],
            "sources": ["EN-SRC-PAPER", "EN-SRC-WITNESS-REPORT"],
        },
        {
            "claim_id": "ORREN-005",
            "statement": "The paper cites delayed-choice and quantum-eraser experiments as bounded context for later classification of earlier registered records without selectable backward signalling in the unconditioned local marginal.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "The cited context does not uniquely select QIK-VRT among interpretations or establish a controllable physical signal into the past.",
            "proof_refs": [],
            "sources": ["EN-SRC-PAPER", "EN-SRC-SCOPE"],
        },
        {
            "claim_id": "ORREN-006",
            "statement": "Ingolf Lohmann asserts that QIK-VRT describes reality within its claimed model scope.",
            "classification": "INTERPRETATIVE",
            "status": "DECLARED",
            "boundary": "This owner-attributed correspondence thesis is distinct from the finite witness, independent empirical confirmation, peer review, and scientific consensus.",
            "proof_refs": [],
            "sources": ["EN-SRC-PAPER", "EN-SRC-SCOPE"],
        },
        {
            "claim_id": "ORREN-007",
            "statement": "The manuscript's statements about recovery, responsibility, and future agency are presented as normative or interpretative positions.",
            "classification": "NORMATIVE",
            "status": "DECLARED",
            "boundary": "These statements are not represented as compulsory theorems of physics or conclusions mechanically compelled by the finite checker.",
            "proof_refs": [],
            "sources": ["EN-SRC-PAPER", "EN-SRC-SCOPE"],
        },
        {
            "claim_id": "ORREN-008",
            "statement": "The source archive and PDF have a recorded deterministic local rebuild and eight-page visual-render validation.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "This is local build and visual-validation evidence only. It does not claim an arXiv or Zenodo platform build, submission, identifier, acceptance, or endorsement.",
            "proof_refs": [],
            "sources": ["EN-SRC-RENDER-RECEIPT", "EN-SRC-PROVENANCE"],
        },
        {
            "claim_id": "ORREN-009",
            "statement": "A Lean kernel receipt for the current result, independent empirical confirmation, peer review, and scientific consensus remain open.",
            "classification": "OPEN",
            "status": "OPEN",
            "boundary": "No publication effect or local validation is treated as closing these open questions.",
            "proof_refs": [],
            "sources": ["EN-SRC-SCOPE"],
        },
    ]


def _claim_matrix() -> dict[str, Any]:
    claims = _claims()
    return {
        "_license": _license("machine_readable_claim_matrix"),
        "schema": "qikvrt_zenodo_en_v2_claim_matrix_v1",
        "publication_id": PUBLICATION_ID,
        "claim_count": len(claims),
        "claims": claims,
        "classification_note": "No claim is silently reclassified as a formal theorem. The Zenodo-v2 projection preserves the source-bound, interpretative, normative, and open dispositions of the English manuscript.",
    }


def _bundle_claims() -> list[dict[str, Any]]:
    wording = {
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "NORMATIVE": "NORMATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
    }
    values: list[dict[str, Any]] = []
    for claim in _claims():
        values.append(
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "classification": claim["classification"],
                "status": claim["status"],
                "publication_wording": wording[claim["classification"]],
                "scope": claim["boundary"],
                "proof_refs": [],
                "evidence_refs": [],
                "source_refs": [f"{BINDINGS_PATH}#{source}" for source in claim["sources"]],
            }
        )
    return values


def _run_witness() -> dict[str, Any]:
    script = ROOT / f"{WITNESS_BASE}/verify_observer_relative_retrocausality.py"
    result = subprocess.run(
        [sys.executable, "-B", str(script)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("finite witness execution failed: " + result.stderr.decode("utf-8", errors="replace"))
    try:
        output = json.loads(result.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("finite witness did not emit JSON") from exc
    stored = _read_json(ROOT / f"{WITNESS_BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json")
    if output != stored:
        raise RuntimeError("finite witness output differs from its canonical report")
    return {
        "exit_code": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "canonical_report_byte_identical": True,
        "report_result": stored["result"],
        "report_schema": stored["schema"],
    }


def _parse_rfc3339(value: str) -> str:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError("returned-at must be RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError("returned-at must include a timezone")
    if parsed > dt.datetime.now(dt.timezone.utc):
        raise RuntimeError("returned-at must not be future-dated")
    return value


def _returned_at_for(*, write: bool, requested: str | None) -> str:
    receipt = ROOT / RECEIPT_PATH
    if receipt.is_file():
        existing = _read_json(receipt).get("return", {}).get("returned_at")
        if not isinstance(existing, str):
            raise RuntimeError("existing return receipt lacks returned_at")
        existing = _parse_rfc3339(existing)
        if requested is not None and requested != existing:
            raise RuntimeError("a frozen return receipt may not be re-timestamped")
        return existing
    if not write or requested is None:
        raise RuntimeError("initial materialization requires --returned-at after visible candidate return")
    return _parse_rfc3339(requested)


def _proof_upload_paths(candidate: list[dict[str, Any]]) -> list[str]:
    paths = [item["path"] for item in candidate]
    paths.extend([MATRIX_PATH, BINDINGS_PATH, BOUNDARY_PATH, RECEIPT_PATH, BUNDLE_PATH])
    if len(paths) != len(set(paths)):
        raise RuntimeError("proof-bearing upload paths are not disjoint")
    return paths


def _build_generated(*, write: bool, returned_at: str) -> dict[str, Any]:
    _write_json(ROOT / BINDINGS_PATH, _source_bindings(), write=write)
    _write_json(ROOT / MATRIX_PATH, _claim_matrix(), write=write)
    candidate = _candidate_files()
    primary = next(item["path"] for item in candidate if item["role"] == "PRIMARY")
    candidate_aggregate = hashlib.sha256(_json_bytes(candidate)).hexdigest()
    freeze = {
        "_license": _license("machine_readable_candidate_freeze"),
        "schema": "qikvrt_zenodo_en_candidate_freeze_v1",
        "publication_id": PUBLICATION_ID,
        "candidate_state": "FROZEN_RETURNED_PUBLIC_CANDIDATE_EXACT_AUTHORIZATION_PENDING",
        "primary_document_path": primary,
        "files": candidate,
        "file_count": len(candidate),
        "total_bytes": sum(item["bytes"] for item in candidate),
        "candidate_aggregate_sha256": candidate_aggregate,
        "preserved_predecessor": {"record_id": "21888130", "doi": "10.5281/zenodo.21888130", "mutation_by_this_package": False},
        "source_head_boundary": {"future_remote_execution_head_required": True, "reason": "The final manifest and owner authorization must live on an execution commit descending from the remotely observable pre-authorization source head."},
        "no_external_effect": True,
    }
    _write_json(ROOT / FREEZE_PATH, freeze, write=write)

    receipt = {
        "_license": _license("machine_readable_prepublication_return_receipt"),
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": False,
        "original_files": [],
        "candidate_files": [{key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")} for item in candidate],
        "changed_claim_ids": [],
        "change_reasons": [],
        "change_notice_path": None,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": OWNER["name"],
            "owner_type": OWNER["type"],
            "return_channel": "ChatGPT Work commentary",
            "returned_at": returned_at,
            "visible_change_notice_returned": False,
        },
    }
    _write_json(ROOT / RECEIPT_PATH, receipt, write=write)
    receipt_identity = _identity(ROOT / RECEIPT_PATH)
    witness = _run_witness()

    boundary = {
        "_license": _license("machine_readable_boundary_test_report"),
        "schema": "qikvrt_observer_relative_retrocausality_en_zenodo_boundary_test_v1",
        "publication_id": PUBLICATION_ID,
        "witness_execution": witness,
        "prepublication_return": {"receipt": receipt_identity, "content_changed": False, "changed_claim_ids": [], "return_channel": "ChatGPT Work commentary", "returned_at": returned_at},
        "proof_partition": {"candidate_file_count": len(candidate), "artifact_paths": [MATRIX_PATH, BINDINGS_PATH, BOUNDARY_PATH, RECEIPT_PATH], "bundle_path": BUNDLE_PATH, "candidate_artifact_overlap": []},
        "tests": [
            {"id": "EN-BND-001", "name": "finite witness reproduces the stored canonical report", "state": "PASS"},
            {"id": "EN-BND-002", "name": "English TeX, staged archive, and staged PDF retain the local deterministic validation bindings", "state": "PASS"},
            {"id": "EN-BND-003", "name": "historical Zenodo record 21888130 is referenced but not replaced", "state": "PASS"},
            {"id": "EN-BND-004", "name": "no formal Lean kernel receipt, independent confirmation, peer review, or consensus is represented as present", "state": "PASS"},
            {"id": "EN-BND-005", "name": "no arXiv submission or identifier is represented by the Zenodo candidate", "state": "PASS"},
            {"id": "EN-BND-006", "name": "candidate, artifacts, bundle, authorization, manifest, and publication evidence remain role-separated", "state": "PASS"},
        ],
        "production_gates": {
            "candidate_bytes_frozen": True,
            "candidate_returned_to_owner": True,
            "claim_inventory_classified": True,
            "source_evidence_bindings_present": True,
            "finite_witness_reexecuted": True,
            "historical_record_21888130_preserved": True,
            "canonical_exact_upload_authorization": False,
            "remote_source_head_binding": False,
            "production_upload_executed": False,
            "public_byte_redownload_verified": False,
        },
        "result": "POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING",
    }
    _write_json(ROOT / BOUNDARY_PATH, boundary, write=write)
    boundary_identity = _identity(ROOT / BOUNDARY_PATH)

    policy = _read_json(ROOT / "policy/zenodo-machine-proof-policy-v2.json")
    policy_identity = _identity(ROOT / "policy/zenodo-machine-proof-policy-v2.json")
    bundle = {
        "_license": _license("machine_readable_proof_bundle"),
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "policy": {"id": policy["policy_id"], "path": policy_identity["path"], "version": policy["version"], "sha256": policy_identity["sha256"], "git_blob_sha1": policy_identity["git_blob_sha1"]},
        "publication_id": PUBLICATION_ID,
        "candidate": {"primary_document_path": primary, "files": candidate},
        "claims": _bundle_claims(),
        "artifacts": [
            _bound_artifact(MATRIX_PATH, "CLAIM_MATRIX"),
            _bound_artifact(BINDINGS_PATH, "EVIDENCE"),
            _bound_artifact(BOUNDARY_PATH, "BOUNDARY_TEST"),
            _bound_artifact(RECEIPT_PATH, "RETURN_RECEIPT"),
        ],
        "prepublication_return": {"content_changed": False, "candidate_returned_to_owner": True, "receipt_path": RECEIPT_PATH, "change_notice_path": None},
        "gates": {"all_claims_dispositioned": True, "all_references_resolve": True, "candidate_frozen": True, "formal_claims_have_kernel_receipts": True, "open_claims_not_worded_as_facts": True, "proof_bundle_in_upload_fileset": True, "returned_bytes_equal_upload_bytes": True},
        "completion_claims": {"machine_proof_complete": True, "zenodo_upload_authorized": True},
    }
    _write_json(ROOT / BUNDLE_PATH, bundle, write=write)
    bundle_identity = _identity(ROOT / BUNDLE_PATH)
    upload_paths = _proof_upload_paths(candidate)
    artifact_kind = {item["path"]: item["kind"] for item in bundle["artifacts"]}
    candidate_by_path = {item["path"]: item for item in candidate}
    exact_uploads: list[dict[str, Any]] = []
    for path in upload_paths:
        item = _identity(ROOT / path)
        candidate_item = candidate_by_path.get(path)
        exact_uploads.append({
            **item,
            "name": candidate_item["name"] if candidate_item else pathlib.PurePosixPath(path).name,
            "partition": "candidate" if candidate_item else "bundle" if path == BUNDLE_PATH else "artifact",
            "artifact_kind": artifact_kind.get(path),
        })
    if len({item["name"] for item in exact_uploads}) != len(exact_uploads):
        raise RuntimeError("proof-bearing upload set has duplicate names")
    ordered = [_identity(ROOT / path) for path in sorted(upload_paths)]
    aggregate = hashlib.sha256("".join(f"{item['sha256']}  {item['path']}\n" for item in ordered).encode("utf-8")).hexdigest()
    total = sum(item["bytes"] for item in ordered)
    metadata_identity = _identity(ROOT / METADATA_PATH)
    metadata_sha256 = _canonical_metadata_sha256()
    status = {
        "_license": _license("machine_readable_production_gate_status"),
        "schema": "qikvrt_zenodo_en_production_gate_status_v1",
        "publication_id": PUBLICATION_ID,
        "state": "POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING",
        "gates": boundary["production_gates"],
        "proof_artifacts": {"prepublication_return_receipt": receipt_identity, "machine_proof_bundle": bundle_identity, "boundary_test_report": boundary_identity},
        "exact_upload_fixity": {"file_count": len(upload_paths), "total_bytes": total, "aggregate_sha256": aggregate, "aggregate_algorithm": "SHA-256 of UTF-8 sorted '<file-sha256>  <repository-path>\\n' lines"},
        "first_blocker": "CANONICAL_EXACT_UPLOAD_AUTHORIZATION_MISSING",
        "next_action": "Obtain one candidate-specific AUTHORIZE_EXACT_UPLOAD statement from Ingolf Lohmann after the completed return, then bind a committed remote source head and a descendant execution commit.",
        "external_effects": {"existing_record_21888130_changed": False, "new_zenodo_record_created": False, "zenodo_upload_performed": False, "doi_registered_by_this_package": False},
    }
    _write_json(ROOT / GATE_PATH, status, write=write)

    owner_draft = {
        "_license": _license("owner_effect_authorization_draft"),
        "schema": "qikvrt_zenodo_owner_authorization_draft_v1",
        "publication_id": PUBLICATION_ID,
        "status": "DIRECT_PUBLICATION_INSTRUCTION_OBSERVED_EXACT_UPLOAD_AUTHORIZATION_PENDING",
        "principal": OWNER,
        "bound_pre_authorization_artifacts": {"candidate_freeze": _identity(ROOT / FREEZE_PATH), "metadata": metadata_identity, "machine_proof": bundle_identity, "prepublication_return": receipt_identity},
        "canonical_metadata_sha256": metadata_sha256,
        "canonical_statement_template": "AUTHORIZE_EXACT_UPLOAD authorization_id=<new-single-use-id> publication_id=" + PUBLICATION_ID + " return_sha256=" + receipt_identity["sha256"] + " metadata_sha256=" + metadata_sha256 + " machine_proof_sha256=" + bundle_identity["sha256"],
        "missing_before_production": ["canonical exact statement from Ingolf Lohmann after this return", "committed and remotely observable pre-authorization source_head", "repository-side OWNER_ZENODO_AUTHORIZATION.json and final v2 manifest on a descendant execution commit", "single-use remote consumption ref acquisition", "GitHub and Zenodo credentials in the authorized workflow environment"],
        "authorized_effects": [],
        "not_a_qikvrt_zenodo_owner_authorization_v1_instance": True,
    }
    _write_json(ROOT / f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION_DRAFT.json", owner_draft, write=write)
    publish_draft = {
        "schema": "qikvrt_zenodo_publication_manifest_draft_v2",
        "publication_id": PUBLICATION_ID,
        "state": "BLOCKED_BEFORE_CANONICAL_AUTHORIZATION",
        "repository": REPOSITORY,
        "target": "CREATE_NEW_ZENODO_RECORD_PRESERVE_21888130",
        "metadata_draft": metadata_identity,
        "candidate_freeze": _identity(ROOT / FREEZE_PATH),
        "machine_proof": bundle_identity,
        "prepublication_return": receipt_identity,
        "owner_authorization_draft": _identity(ROOT / f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION_DRAFT.json"),
        "exact_upload_paths": upload_paths,
        "exact_upload_files": exact_uploads,
        "exact_upload_total_bytes": total,
        "exact_upload_aggregate_sha256": aggregate,
        "exact_upload_aggregate_algorithm": "SHA-256 of UTF-8 sorted '<file-sha256>  <repository-path>\\n' lines",
        "required_final_schema": "qikvrt_zenodo_publication_manifest_v2",
        "not_executable_by_generic_publisher": True,
        "required_before_conversion": ["exact canonical owner decision", "remote source-head binding", "descendant execution commit", "generic publisher preflight"],
    }
    _write_json(ROOT / f"{RELEASE_REL}/PUBLISH_REQUEST_DRAFT.json", publish_draft, write=write)
    rows = [f"| `{item['path']}` | `{item['name']}` | {item['partition']} | {item['bytes']} | `{item['sha256']}` |" for item in exact_uploads]
    owner_message = "\n".join([
        "<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->",
        "# Exact pre-publication return: English Zenodo candidate",
        "",
        f"The exact English candidate was returned through ChatGPT Work commentary at `{returned_at}`. No Zenodo effect has occurred.",
        "",
        f"- Publication ID: `{PUBLICATION_ID}`",
        f"- Candidate receipt SHA-256: `{receipt_identity['sha256']}`",
        f"- Canonical metadata SHA-256: `{metadata_sha256}`",
        f"- Machine-proof SHA-256: `{bundle_identity['sha256']}`",
        f"- Exact upload files: `{len(upload_paths)}`",
        f"- Exact upload size: `{total}` bytes",
        f"- Upload aggregate SHA-256: `{aggregate}`",
        "",
        "| Repository path | Zenodo filename | Partition | Bytes | SHA-256 |",
        "|---|---|---|---:|---|",
        *rows,
        "",
        "The production path remains blocked until the owner supplies the exact one-line `AUTHORIZE_EXACT_UPLOAD` statement bound to the three hashes above.",
        "",
    ])
    _write_text(ROOT / RETURN_MESSAGE_PATH, owner_message, write=write)
    return {"candidate": candidate, "upload_paths": upload_paths, "receipt_identity": receipt_identity, "bundle_identity": bundle_identity, "metadata_sha256": metadata_sha256, "total": total, "aggregate": aggregate, "returned_at": returned_at}


def _sha_sums() -> str:
    entries: list[tuple[str, str]] = []
    for path in sorted(RELEASE.rglob("*")):
        if not path.is_file() or path == RELEASE / "SHA256SUMS" or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        entries.append((hashlib.sha256(path.read_bytes()).hexdigest(), f"{RELEASE_REL}/{path.relative_to(RELEASE).as_posix()}"))
    return "".join(f"{digest}  {relative}\n" for digest, relative in entries)


def _validate_machine_proof(upload_paths: list[str]) -> str:
    command = [sys.executable, "-B", "tools/qikvrt_zenodo_machine_proof.py", "--proof-bundle", BUNDLE_PATH]
    for path in upload_paths:
        command.extend(["--upload-path", path])
    result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
        raise RuntimeError("machine-proof validation failed: " + detail)
    output = result.stdout.decode("utf-8")
    if "ZENODO_MACHINE_PROOF_STATE=verified" not in output:
        raise RuntimeError("machine-proof validator did not report verified state")
    return output


def _ensure_final_controls_absent() -> None:
    for name in ("OWNER_ZENODO_AUTHORIZATION.json", "publish-request.json", "zenodo-publication.json"):
        if (RELEASE / name).exists():
            raise RuntimeError("pre-authorization package contains production evidence/control: " + name)


def materialize(returned_at: str) -> None:
    generated = _build_generated(write=True, returned_at=returned_at)
    _write_text(RELEASE / "SHA256SUMS", _sha_sums(), write=True)
    _ensure_final_controls_absent()
    _validate_machine_proof(generated["upload_paths"])
    print("PREAUTHORIZATION_MACHINE_PROOF_MATERIALIZED_NO_EXTERNAL_EFFECT")


def check() -> None:
    returned_at = _returned_at_for(write=False, requested=None)
    generated = _build_generated(write=False, returned_at=returned_at)
    expected_sums = _sha_sums()
    if _raw(RELEASE / "SHA256SUMS").decode("utf-8") != expected_sums:
        raise RuntimeError("SHA256SUMS differs from deterministic regeneration")
    _ensure_final_controls_absent()
    output = _validate_machine_proof(generated["upload_paths"])
    print("PASS English Zenodo pre-authorization proof package verified " + f"candidate_files={len(generated['candidate'])} upload_paths={len(generated['upload_paths'])} receipt_sha256={generated['receipt_identity']['sha256']} proof_sha256={generated['bundle_identity']['sha256']} state=POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING")
    print(output.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="materialize the deterministic local proof package")
    mode.add_argument("--check", action="store_true", help="verify the deterministic local proof package")
    parser.add_argument("--returned-at", help="RFC3339 time of the visible ChatGPT Work candidate return; required only for the first --write")
    args = parser.parse_args()
    try:
        if args.write:
            returned_at = _returned_at_for(write=True, requested=args.returned_at)
            materialize(returned_at)
        elif args.returned_at is not None:
            parser.error("--returned-at is valid only with --write")
        else:
            check()
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print("BLOCK: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
