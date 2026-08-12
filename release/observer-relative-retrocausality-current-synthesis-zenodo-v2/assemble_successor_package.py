#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize or verify the non-effect Zenodo successor preparation.

This helper deliberately produces only draft artifacts.  It freezes the
current public candidate and records the remaining policy gates, but it does
not call Zenodo, inspect credentials, create a Git ref, or construct an
executable qikvrt_zenodo_publication_manifest_v2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[2]
RELEASE = pathlib.Path(__file__).resolve().parent
RELEASE_REL = RELEASE.relative_to(ROOT).as_posix()
PUBLICATION_ID = "qikvrt-observer-relative-retrocausality-current-synthesis-v2"
DIRECTIVE = "Zenodo, arXiv und IETF, Veröffentlichung freigegeben."

# The frozen candidate is the public data plane only.  The package directory
# also contains the private-to-the-publication-chain control plane: draft
# metadata, return/authorization drafts, gate reports and the materializer
# itself.  Those files are evidence for preparation, not research content, and
# must never be silently carried into the exact Zenodo upload set.
BASE = "docs/publications/2026-08-12-observer-relative-retrocausality"
NON_UPLOAD_CONTROL_PATHS = frozenset(
    {
        f"{BASE}/PDF_RENDER_VALIDATION.json",
        f"{BASE}/SHA256SUMS",
        "state/work_units/OBSERVER_RELATIVE_RETROCAUSALITY_CURRENT_SYNTHESIS_V2.json",
        f"{RELEASE_REL}/BOUNDARY_TEST_REPORT.json",
        f"{RELEASE_REL}/FINALIZATION_CHECKLIST.md",
        f"{RELEASE_REL}/FROZEN_UPLOAD_CANDIDATE.json",
        f"{RELEASE_REL}/MACHINE_PROOF_BUNDLE_DRAFT.json",
        f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION_DRAFT.json",
        f"{RELEASE_REL}/PREPUBLICATION_RETURN_RECEIPT_DRAFT.json",
        f"{RELEASE_REL}/PRODUCTION_GATE_STATUS.json",
        f"{RELEASE_REL}/PUBLISH_REQUEST_DRAFT.json",
        f"{RELEASE_REL}/RETURN_TO_OWNER_MESSAGE.md",
        f"{RELEASE_REL}/SHA256SUMS",
        f"{RELEASE_REL}/WORKFLOW_DISPATCH_PLAN.md",
        f"{RELEASE_REL}/ZENODO_FILESET.md",
        f"{RELEASE_REL}/ZENODO_METADATA_DRAFT.json",
        f"{RELEASE_REL}/assemble_successor_package.py",
        "policy/zenodo-machine-proof-policy-v2.json",
        "policy/qikvrt-zenodo-machine-proof-bundle-v2.schema.json",
        "policy/qikvrt-prepublication-return-receipt-v2.schema.json",
    }
)
CONTROL_NAME_MARKERS = ("_DRAFT", "FINALIZATION", "GATE_STATUS", "FILESET")


def _raw(path: pathlib.Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"required regular file is missing: {path.relative_to(ROOT)}")
    return path.read_bytes()


def _identity(path: pathlib.Path) -> dict[str, Any]:
    raw = _raw(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": hashlib.sha1(  # noqa: S324 - Git object identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
    }


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write(path: pathlib.Path, value: object, *, write: bool) -> None:
    payload = _json_bytes(value)
    if path.exists() and path.read_bytes() == payload:
        return
    if write:
        path.write_bytes(payload)
        return
    raise RuntimeError(f"generated content differs: {path.relative_to(ROOT)}")


def _read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(_raw(path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {path.relative_to(ROOT)}")
    return value


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
        (f"{RELEASE_REL}/ZENODO_LICENSE_NOTICE.md", "ZENODO_LICENSE_NOTICE.md", "SUPPLEMENT"),
        (f"{RELEASE_REL}/CITATION.cff", "CITATION.cff", "SUPPLEMENT"),
        (f"{RELEASE_REL}/CLAIM_MATRIX_V2.json", "CLAIM_MATRIX_V2.json", "SUPPLEMENT"),
        (f"{RELEASE_REL}/SOURCE_EVIDENCE_BINDINGS.json", "SOURCE_EVIDENCE_BINDINGS.json", "SUPPLEMENT"),
        ("LICENSES/CC-BY-NC-ND-4.0.txt", "CC-BY-NC-ND-4.0.txt", "SUPPLEMENT"),
        ("LICENSES/PolyForm-Noncommercial-1.0.0.txt", "PolyForm-Noncommercial-1.0.0.txt", "SUPPLEMENT"),
    ]


def _candidate_upload_boundary() -> dict[str, object]:
    return {
        "scope": "PUBLIC_CONTENT_AND_EVIDENCE_ONLY",
        "excluded_categories": [
            "preparation",
            "publication-control",
            "authorization",
            "execution-status",
            "draft",
            "repository-internal validation",
            "policy and schema source",
        ],
        "excluded_paths": sorted(NON_UPLOAD_CONTROL_PATHS),
        "rule": "The frozen upload set contains public research content, its public evidence bindings and required license material only. Preparation, control and draft artifacts remain repository-resident and are not Zenodo upload candidates.",
    }


def _candidate_files() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    names: set[str] = set()
    for relative, name, role in _candidate_specs():
        if relative in NON_UPLOAD_CONTROL_PATHS:
            raise RuntimeError(f"control artifact entered public upload set: {relative}")
        if any(marker in relative.upper() or marker in name.upper() for marker in CONTROL_NAME_MARKERS):
            raise RuntimeError(f"draft or control name entered public upload set: {relative}")
        if name in names:
            raise RuntimeError(f"duplicate upload name: {name}")
        names.add(name)
        item = _identity(ROOT / relative)
        item["name"] = name
        item["role"] = role
        values.append(item)
    if not any(item["path"] == f"{BASE}/HISTORICAL_ARTIFACTS.json" for item in values):
        raise RuntimeError("public candidate must retain the historical-artifact binding")
    if not any(item["path"] == f"{BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json" for item in values):
        raise RuntimeError("public candidate must retain the executable-witness report")
    return values


def _license(classification: str) -> dict[str, str]:
    return {
        "classification": classification,
        "copyright": "Copyright 2026 Ingolf Lohmann",
        "license": "CC-BY-NC-ND-4.0",
        "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
        "rights_holder": "Ingolf Lohmann",
    }


def _source_bindings() -> dict[str, Any]:
    base = "docs/publications/2026-08-12-observer-relative-retrocausality"
    bindings = [
        ("SRC-PAPER-DEFINITION", f"{base}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex", "Operational definition of observer-local change time / Eigenzeit and negative information direction.", ["ORRZ-001"]),
        ("SRC-EXECUTABLE-WITNESS", f"{base}/verify_observer_relative_retrocausality.py", "Finite checker that evaluates the declared witness without network or external-system effects.", ["ORRZ-002"]),
        ("SRC-WITNESS-REPORT", f"{base}/QIKVRT_RETROCAUSALITY_WITNESS.json", "Canonical output of the finite witness checker.", ["ORRZ-002", "ORRZ-004"]),
        ("SRC-PAPER-EXISTENCE", f"{base}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex", "Documented conditional finite existence argument and its declared assumptions.", ["ORRZ-003"]),
        ("SRC-PAPER-PHYSICAL", f"{base}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex", "Positive-latency physical realization section and its stated boundary.", ["ORRZ-004"]),
        ("SRC-PAPER-QUANTUM-CONTEXT", f"{base}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex", "Primary-literature citations and bounded delayed-choice / quantum-eraser bridge.", ["ORRZ-005"]),
        ("SRC-AUTHOR-CORRESPONDENCE", f"{base}/CLAIM_MATRIX.json", "Owner-asserted reality-correspondence thesis and its separate status boundary.", ["ORRZ-006"]),
        ("SRC-HUMAN-DECLARATION", f"{base}/AN_VON_UND_FUER_ALLE_MENSCHEN_DE.md", "Public normative declaration on responsibility, evidence and future agency.", ["ORRZ-007", "ORRZ-010"]),
        ("SRC-HISTORICAL-BINDINGS", f"{base}/HISTORICAL_ARTIFACTS.json", "Byte-exact bindings for the retained historical intermediate PDFs.", ["ORRZ-008"]),
        ("SRC-CURRENT-CLAIM-BOUNDARY", f"{base}/CLAIM_MATRIX.json", "Declared scope boundaries, including absence of a new Lean kernel receipt and unestablished independent confirmation.", ["ORRZ-009"]),
    ]
    rows: list[dict[str, Any]] = []
    for source_id, path, description, claim_ids in bindings:
        item = _identity(ROOT / path)
        item.update({"source_id": source_id, "description": description, "claim_ids": claim_ids})
        rows.append(item)
    return {
        "_license": _license("machine_readable_source_evidence_bindings"),
        "schema": "qikvrt_observer_relative_retrocausality_source_evidence_bindings_v2",
        "publication_id": PUBLICATION_ID,
        "binding_count": len(rows),
        "bindings": rows,
        "boundary": "Bindings identify supplied repository documents and executable outputs. They do not substitute for an external Zenodo effect, independent empirical confirmation or scientific consensus.",
    }


def _claims() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "ORRZ-001",
            "statement": "QIK-VRT defines observer-relative retrocausality as a negative information direction: a receiver's local change time increases while the authenticated comparable source-order markers of successive information-bearing records decrease.",
            "classification": "INTERPRETATIVE",
            "status": "DECLARED",
            "boundary": "This is the authorial operational definition used by the work. A metric relativistic proper-time calibration needs an additional physical worldline binding.",
            "proof_refs": [],
            "sources": ["SRC-PAPER-DEFINITION"],
        },
        {
            "claim_id": "ORRZ-002",
            "statement": "The bundled finite checker and its checked-in report evaluate the declared two-record witness and report all declared predicates as verified for that finite operational model.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "This is a bound executable-witness statement, not a Lean kernel receipt, a universal theorem or a measurement of the whole universe.",
            "proof_refs": [],
            "sources": ["SRC-EXECUTABLE-WITNESS", "SRC-WITNESS-REPORT"],
        },
        {
            "claim_id": "ORRZ-003",
            "statement": "The primary document presents a conditional finite existence argument for negative comparative information-reference direction under its declared host-order, authenticity, source-order and monotonic-local-chain assumptions.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "The argument is published as a source-bound mathematical presentation in this package; no new Lean kernel receipt for it is included here.",
            "proof_refs": [],
            "sources": ["SRC-PAPER-EXISTENCE"],
        },
        {
            "claim_id": "ORRZ-004",
            "statement": "The declared finite construction uses two positive future-directed path delays so that the later-source record arrives before the earlier-source record for the receiver.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "The construction demonstrates the stated operational ordering only; it does not assert superluminal propagation, reception before emission or past-directed transport.",
            "proof_refs": [],
            "sources": ["SRC-PAPER-PHYSICAL", "SRC-WITNESS-REPORT"],
        },
        {
            "claim_id": "ORRZ-005",
            "statement": "The paper cites delayed-choice and quantum-eraser experiments as a bounded empirical bridge for context-dependent classification of registered records with no selectable backward signal in the unconditioned local marginal.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "The citation-bound bridge does not uniquely select QIK-VRT among quantum interpretations or establish a controllable physical signal into the past.",
            "proof_refs": [],
            "sources": ["SRC-PAPER-QUANTUM-CONTEXT"],
        },
        {
            "claim_id": "ORRZ-006",
            "statement": "Ingolf Lohmann asserts that QIK-VRT describes reality within its claimed model scope.",
            "classification": "INTERPRETATIVE",
            "status": "DECLARED",
            "boundary": "This owner-authored correspondence thesis is distinct from the finite witness, independent empirical confirmation and scientific consensus.",
            "proof_refs": [],
            "sources": ["SRC-AUTHOR-CORRESPONDENCE"],
        },
        {
            "claim_id": "ORRZ-007",
            "statement": "Vergrößere die Menge des Jetzt: present responsibility should include more affected people, consequences, evidence and correction possibilities.",
            "classification": "NORMATIVE",
            "status": "DECLARED",
            "boundary": "This is a normative imperative of the public declaration, not a mathematical theorem or a compulsory moral law derived from physics.",
            "proof_refs": [],
            "sources": ["SRC-HUMAN-DECLARATION"],
        },
        {
            "claim_id": "ORRZ-008",
            "statement": "The two retained historical PDFs are bound as byte-exact intermediate states and are not overwritten by this current synthesis.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "The historical bindings preserve former bytes and former scope wording; they do not automatically turn later additions into historical evidence.",
            "proof_refs": [],
            "sources": ["SRC-HISTORICAL-BINDINGS"],
        },
        {
            "claim_id": "ORRZ-009",
            "statement": "A new Lean kernel receipt for the current observer-relative existence argument, independent empirical confirmation and scientific consensus remain open.",
            "classification": "OPEN",
            "status": "OPEN",
            "boundary": "Closing these questions would require the respectively appropriate formalization, independently reproducible empirical work and scientific evaluation; no completion is inferred from this candidate.",
            "proof_refs": [],
            "sources": [],
        },
        {
            "claim_id": "ORRZ-010",
            "statement": "Responsibility means preserving future agency and refusing to reduce persons to exploitable material, risk, file, target group or enemy image.",
            "classification": "NORMATIVE",
            "status": "DECLARED",
            "boundary": "This is the ethical position of the public declaration; it is not a conclusion mechanically compelled by software, mathematics or physics alone.",
            "proof_refs": [],
            "sources": ["SRC-HUMAN-DECLARATION"],
        },
    ]


def _claim_matrix() -> dict[str, Any]:
    claims = _claims()
    return {
        "_license": _license("machine_readable_claim_matrix"),
        "schema": "qikvrt_zenodo_v2_claim_matrix_v1",
        "publication_id": PUBLICATION_ID,
        "claim_count": len(claims),
        "claims": claims,
        "classification_note": "The Zenodo-v2 projection uses only the active policy's claim classes. Source-bound presentation and executable-witness results are not silently reclassified as Lean kernel theorems.",
    }


def _run_witness() -> dict[str, Any]:
    script = ROOT / "docs/publications/2026-08-12-observer-relative-retrocausality/verify_observer_relative_retrocausality.py"
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
        raise RuntimeError("finite witness output is not JSON") from exc
    stored = _read_json(ROOT / "docs/publications/2026-08-12-observer-relative-retrocausality/QIKVRT_RETROCAUSALITY_WITNESS.json")
    if output != stored:
        raise RuntimeError("finite witness output differs from its checked-in canonical report")
    return {
        "exit_code": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "canonical_report_byte_identical": True,
        "report_schema": stored.get("schema"),
        "report_result": stored.get("result"),
    }


def _path_identity(relative: str) -> dict[str, Any]:
    return _identity(ROOT / relative)


def _build_generated(*, write: bool) -> dict[str, object]:
    bindings_path = f"{RELEASE_REL}/SOURCE_EVIDENCE_BINDINGS.json"
    matrix_path = f"{RELEASE_REL}/CLAIM_MATRIX_V2.json"
    boundary_path = f"{RELEASE_REL}/BOUNDARY_TEST_REPORT.json"
    gate_status_path = f"{RELEASE_REL}/PRODUCTION_GATE_STATUS.json"
    freeze_path = f"{RELEASE_REL}/FROZEN_UPLOAD_CANDIDATE.json"
    return_draft_path = f"{RELEASE_REL}/PREPUBLICATION_RETURN_RECEIPT_DRAFT.json"
    proof_draft_path = f"{RELEASE_REL}/MACHINE_PROOF_BUNDLE_DRAFT.json"
    authorization_draft_path = f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION_DRAFT.json"
    manifest_draft_path = f"{RELEASE_REL}/PUBLISH_REQUEST_DRAFT.json"
    owner_message_path = RELEASE / "RETURN_TO_OWNER_MESSAGE.md"

    _write(ROOT / bindings_path, _source_bindings(), write=write)
    _write(ROOT / matrix_path, _claim_matrix(), write=write)

    witness = _run_witness()
    gates = {
        "candidate_bytes_frozen": True,
        "claim_inventory_classified": True,
        "source_evidence_bindings_present": True,
        "finite_witness_reexecuted": True,
        "historical_record_21888130_preserved": True,
        "existing_metadata_edit_package_preserved": True,
        "candidate_upload_set_excludes_preparation_control_and_draft_files": True,
        "canonical_prepublication_return_receipt": False,
        "canonical_machine_proof_bundle": False,
        "canonical_exact_upload_authorization": False,
        "remote_source_head_binding": False,
        "github_token_observed_in_execution_context": False,
        "zenodo_token_observed_in_execution_context": False,
        "production_upload_executed": False,
        "public_byte_redownload_verified": False,
    }
    boundary = {
        "_license": _license("machine_readable_boundary_test_report"),
        "schema": "qikvrt_observer_relative_retrocausality_zenodo_successor_boundary_test_v1",
        "publication_id": PUBLICATION_ID,
        "witness_execution": witness,
        "tests": [
            {
                "id": "BND-001",
                "name": "current finite witness reproduces the stored canonical report",
                "state": "PASS",
            },
            {
                "id": "BND-002",
                "name": "historical Zenodo record is modeled as preserved rather than replaced",
                "state": "PASS",
            },
            {
                "id": "BND-003",
                "name": "no draft artifact is accepted as a production manifest or exact authorization",
                "state": "PASS",
            },
            {
                "id": "BND-004",
                "name": "new Lean kernel proof for this exact current claim set is not represented as present",
                "state": "PASS",
            },
            {
                "id": "BND-005",
                "name": "candidate upload set contains public content and evidence only, excluding preparation, control and draft artifacts",
                "state": "PASS",
            },
        ],
        "production_gates": gates,
        "result": "PREPARATION_BOUNDARY_PASS_PRODUCTION_GATES_REMAIN_BLOCKED",
    }
    _write(ROOT / boundary_path, boundary, write=write)
    gate_status = {
        "_license": _license("machine_readable_production_gate_status"),
        "schema": "qikvrt_zenodo_successor_production_gate_status_v1",
        "publication_id": PUBLICATION_ID,
        "state": "PREPUBLICATION_PACKAGE_PREPARED_NOT_EXECUTABLE",
        "gates": gates,
        "first_blocker": "NO_CANDIDATE_SPECIFIC_PREPUBLICATION_RETURN_RECEIPT_OR_CANONICAL_EXACT_UPLOAD_AUTHORIZATION",
        "next_action": "Return the frozen candidate and visible change notice to Ingolf Lohmann, then bind his canonical AUTHORIZE_EXACT_UPLOAD decision to final receipt, metadata and machine-proof hashes.",
        "external_effects": {
            "existing_record_21888130_changed": False,
            "new_zenodo_record_created": False,
            "zenodo_upload_performed": False,
            "doi_registered_by_this_package": False,
        },
    }
    _write(ROOT / gate_status_path, gate_status, write=write)

    candidate = _candidate_files()
    candidate_aggregate_sha256 = hashlib.sha256(_json_bytes(candidate)).hexdigest()
    freeze = {
        "_license": _license("machine_readable_candidate_freeze"),
        "schema": "qikvrt_zenodo_successor_candidate_freeze_v1",
        "publication_id": PUBLICATION_ID,
        "candidate_state": "FROZEN_LOCAL_CANDIDATE_PENDING_RETURN_AND_EXACT_AUTHORIZATION",
        "primary_document_path": "docs/publications/2026-08-12-observer-relative-retrocausality/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf",
        "files": candidate,
        "file_count": len(candidate),
        "total_bytes": sum(item["bytes"] for item in candidate),
        "candidate_aggregate_sha256": candidate_aggregate_sha256,
        "upload_boundary": _candidate_upload_boundary(),
        "preserved_predecessor": {
            "record_id": "21888130",
            "doi": "10.5281/zenodo.21888130",
            "mutation_by_this_package": False,
        },
        "source_head_boundary": {
            "local_preparation_head": "a2716dd994f282036cfeef3ab0bc2bf6e723be07",
            "local_preparation_tree": "089da93574b5b649b4a8d43ef450253db86e4e9d",
            "future_remote_execution_head_required": True,
            "reason": "The final v2 manifest must bind a committed and remotely observable source head after all final proof and authorization bytes are fixed.",
        },
        "no_external_effect": True,
    }
    _write(ROOT / freeze_path, freeze, write=write)
    freeze_identity = _path_identity(freeze_path)
    matrix_identity = _path_identity(matrix_path)
    bindings_identity = _path_identity(bindings_path)
    boundary_identity = _path_identity(boundary_path)
    gate_status_identity = _path_identity(gate_status_path)
    metadata_identity = _path_identity(f"{RELEASE_REL}/ZENODO_METADATA_DRAFT.json")
    change_identity = _path_identity(f"{RELEASE_REL}/CHANGE_NOTICE.md")
    policy_identity = _path_identity("policy/zenodo-machine-proof-policy-v2.json")

    return_draft = {
        "_license": _license("machine_readable_prepublication_return_receipt_draft"),
        "schema": "qikvrt_prepublication_return_receipt_draft_v1",
        "publication_id": PUBLICATION_ID,
        "status": "NOT_RETURNED_TO_OWNER",
        "candidate_freeze": freeze_identity,
        "candidate_files": [{key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")} for item in candidate],
        "visible_change_notice": change_identity,
        "direct_owner_instruction": {
            "date": "2026-08-12",
            "channel": "CURRENT_CHAT_SESSION",
            "statement": DIRECTIVE,
            "interpretation": "Broad destination authorization recorded; not a candidate-specific AUTHORIZE_EXACT_UPLOAD statement.",
        },
        "required_before_final_receipt": [
            "visible delivery of all frozen candidate paths and hashes to Ingolf Lohmann",
            "actual return timestamp and return channel",
            "candidate_returned_to_owner: true in the v2 schema instance",
            "visible change notice confirmed as returned",
        ],
        "candidate_returned_to_owner": False,
        "not_a_v2_receipt": True,
    }
    _write(ROOT / return_draft_path, return_draft, write=write)
    return_draft_identity = _path_identity(return_draft_path)

    bundle_claims: list[dict[str, Any]] = []
    for claim in _claims():
        classification = claim["classification"]
        wording = {
            "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
            "EMPIRICALLY_EVIDENCED": "EMPIRICALLY_SUPPORTED",
            "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
            "NORMATIVE": "NORMATIVE_DECLARATION",
            "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
            "OPEN": "EXPLICITLY_OPEN",
        }[classification]
        source_refs = [f"{bindings_path}#{source_id}" for source_id in claim["sources"]]
        bundle_claims.append(
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "classification": classification,
                "status": claim["status"],
                "publication_wording": wording,
                "scope": claim["boundary"],
                "proof_refs": [],
                "evidence_refs": [],
                "source_refs": source_refs,
            }
        )
    proof_draft = {
        "_license": _license("machine_readable_proof_bundle_draft"),
        "schema": "qikvrt_zenodo_machine_proof_bundle_draft_v1",
        "publication_id": PUBLICATION_ID,
        "status": "NOT_A_PRODUCTION_V2_PROOF_BUNDLE",
        "active_policy": policy_identity,
        "candidate": {
            "primary_document_path": freeze["primary_document_path"],
            "files": candidate,
            "freeze": freeze_identity,
        },
        "claim_matrix": matrix_identity,
        "claims": bundle_claims,
        "formal_claim_count": 0,
        "formal_claim_boundary": "No claim in this successor projection is labelled FORMAL_PROVED because the current package contains no new exact-head Lean kernel receipt for its observer-relative theorem presentation. The explicit executable witness and mathematical exposition remain separately source-bound.",
        "artifacts_available_for_final_bundle": [
            {**matrix_identity, "kind": "CLAIM_MATRIX"},
            {**bindings_identity, "kind": "EVIDENCE"},
            {**boundary_identity, "kind": "BOUNDARY_TEST"},
            {**gate_status_identity, "kind": "OTHER"},
            {**change_identity, "kind": "CHANGE_NOTICE"},
        ],
        "return_receipt_draft": return_draft_identity,
        "gates": {
            "all_claims_dispositioned": True,
            "all_references_resolve": True,
            "candidate_frozen": True,
            "formal_claims_have_kernel_receipts": True,
            "open_claims_not_worded_as_facts": True,
            "proof_bundle_in_upload_fileset": False,
            "returned_bytes_equal_upload_bytes": False,
            "candidate_returned_to_owner": False,
            "canonical_v2_schema_instance": False,
            "exact_upload_authorization": False,
        },
        "finalization_required": [
            "materialize a qikvrt_zenodo_machine_proof_bundle_v2 instance after actual candidate return",
            "add the final bundle to the exact upload fileset",
            "validate with tools/qikvrt_zenodo_machine_proof.py",
            "bind the final bundle digest to the canonical owner authorization",
        ],
        "not_authorizing": True,
    }
    _write(ROOT / proof_draft_path, proof_draft, write=write)
    proof_draft_identity = _path_identity(proof_draft_path)

    authorization_draft = {
        "_license": _license("owner_effect_authorization_draft"),
        "schema": "qikvrt_zenodo_owner_authorization_draft_v1",
        "publication_id": PUBLICATION_ID,
        "status": "BROAD_DIRECTIVE_RECORDED_EXACT_UPLOAD_AUTHORIZATION_PENDING",
        "principal": {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
        "direct_owner_instruction": {
            "date": "2026-08-12",
            "channel": "CURRENT_CHAT_SESSION",
            "statement": DIRECTIVE,
            "scope": ["Zenodo", "arXiv", "IETF"],
        },
        "bound_drafts": {
            "candidate_freeze": freeze_identity,
            "metadata": metadata_identity,
            "machine_proof_draft": proof_draft_identity,
            "prepublication_return_draft": return_draft_identity,
        },
        "canonical_statement_template": "AUTHORIZE_EXACT_UPLOAD authorization_id=<new-single-use-id> publication_id=qikvrt-observer-relative-retrocausality-current-synthesis-v2 return_sha256=<final-v2-return-receipt-sha256> metadata_sha256=<final-metadata-sha256> machine_proof_sha256=<final-v2-machine-proof-sha256>",
        "missing_before_production": [
            "final candidate-specific v2 prepublication return receipt",
            "final v2 machine proof bundle",
            "canonical exact statement from Ingolf Lohmann after the candidate return",
            "current remote source_head and a matching committed manifest",
            "single-use remote consumption ref acquisition",
            "execution-context GitHub and Zenodo credentials",
        ],
        "authorized_effects": [],
        "not_a_qikvrt_zenodo_owner_authorization_v1_instance": True,
    }
    _write(ROOT / authorization_draft_path, authorization_draft, write=write)
    authorization_draft_identity = _path_identity(authorization_draft_path)

    manifest_draft = {
        "schema": "qikvrt_zenodo_publication_manifest_draft_v2",
        "publication_id": PUBLICATION_ID,
        "state": "BLOCKED_BEFORE_CANONICAL_AUTHORIZATION",
        "repository": "Goldkelch/qik-vrt",
        "target": "CREATE_NEW_ZENODO_RECORD_PRESERVE_21888130",
        "metadata_draft": metadata_identity,
        "candidate_freeze": freeze_identity,
        "machine_proof_draft": proof_draft_identity,
        "prepublication_return_draft": return_draft_identity,
        "owner_authorization_draft": authorization_draft_identity,
        "required_final_schema": "qikvrt_zenodo_publication_manifest_v2",
        "not_executable_by_generic_publisher": True,
        "required_before_conversion": [
            "all final proof and return bytes materialized",
            "exact canonical owner decision recorded",
            "source_head updated to the remote final execution commit",
            "generic publisher validation succeeds before any remote mutation",
        ],
    }
    _write(ROOT / manifest_draft_path, manifest_draft, write=write)

    table_lines = [
        "<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->",
        "# Rückgabe an Ingolf Lohmann vor der Zenodo-Produktionsmutation",
        "",
        "Diese Kandidatenbytes sind eingefroren, aber noch nicht als Zenodo-Record hochgeladen.",
        "Die hier sichtbare Liste ist die Voraussetzung für die anschließend mögliche exakte Hash-Freigabe.",
        "",
        "| Datei | Bytes | SHA-256 | Git-Blob-ID |",
        "|---|---:|---|---|",
    ]
    for item in candidate:
        table_lines.append(f"| `{item['path']}` | {item['bytes']} | `{item['sha256']}` | `{item['git_blob_sha1']}` |")
    table_lines.extend(
        [
            "",
            "Der sichtbare Änderungsvermerk ist `CHANGE_NOTICE.md`. Der genaue Status und die noch fehlenden Voraussetzungen sind in `PRODUCTION_GATE_STATUS.json` und `FINALIZATION_CHECKLIST.md` dokumentiert.",
            "",
            "Die direkte Freigabe vom 12. August 2026 wird als breite Veröffentlichungsfreigabe respektiert. Eine Zenodo-v2-Produktion benötigt zusätzlich die kanonische, hashgebundene `AUTHORIZE_EXACT_UPLOAD`-Zeile nach dieser Rückgabe.",
            "",
        ]
    )
    owner_message = ("\n".join(table_lines)).encode("utf-8")
    if owner_message_path.exists() and owner_message_path.read_bytes() == owner_message:
        pass
    elif write:
        owner_message_path.write_bytes(owner_message)
    else:
        raise RuntimeError(
            "generated content differs: " + owner_message_path.relative_to(ROOT).as_posix()
        )

    return {
        "candidate": candidate,
        "freeze_path": freeze_path,
        "generated_paths": [
            bindings_path,
            matrix_path,
            boundary_path,
            gate_status_path,
            freeze_path,
            return_draft_path,
            proof_draft_path,
            authorization_draft_path,
            manifest_draft_path,
            owner_message_path.relative_to(ROOT).as_posix(),
        ],
    }


def _sha_sums() -> str:
    entries: list[tuple[str, str]] = []
    for path in sorted(RELEASE.iterdir()):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        entries.append(
            (
                hashlib.sha256(path.read_bytes()).hexdigest(),
                f"{RELEASE_REL}/{path.name}",
            )
        )
    return "".join(f"{digest}  {name}\n" for digest, name in entries)


def _materialize() -> None:
    _build_generated(write=True)
    (RELEASE / "SHA256SUMS").write_text(_sha_sums(), encoding="utf-8")


def _check() -> None:
    expected = _build_generated(write=False)
    for relative in expected["generated_paths"]:
        if not (ROOT / relative).is_file():
            raise RuntimeError(f"generated path missing: {relative}")
    expected_sums = _sha_sums()
    actual_sums = _raw(RELEASE / "SHA256SUMS").decode("utf-8")
    if actual_sums != expected_sums:
        raise RuntimeError("SHA256SUMS differs from deterministic regeneration")
    status = _read_json(RELEASE / "PRODUCTION_GATE_STATUS.json")
    if status.get("state") != "PREPUBLICATION_PACKAGE_PREPARED_NOT_EXECUTABLE":
        raise RuntimeError("production gate status boundary drifted")
    for name in (
        "candidate_upload_set_excludes_preparation_control_and_draft_files",
    ):
        if status.get("gates", {}).get(name) is not True:
            raise RuntimeError(f"candidate-boundary gate must remain true: {name}")
    for name in (
        "canonical_prepublication_return_receipt",
        "canonical_machine_proof_bundle",
        "canonical_exact_upload_authorization",
        "production_upload_executed",
    ):
        if status.get("gates", {}).get(name) is not False:
            raise RuntimeError(f"production gate must remain false: {name}")
    print(
        "PASS successor preparation verified "
        f"candidate_files={len(expected['candidate'])} "
        "state=PREPUBLICATION_PACKAGE_PREPARED_NOT_EXECUTABLE"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="materialize deterministic draft artifacts")
    parser.add_argument("--check", action="store_true", help="verify deterministic draft artifacts")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    try:
        if args.write:
            _materialize()
            print("PREPARATION_MATERIALIZED_NO_EXTERNAL_EFFECT")
        else:
            _check()
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
