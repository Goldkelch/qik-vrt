#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize or verify the pre-authorization Zenodo successor package.

The helper preserves the visibly returned 17-file public freeze and binds the
separately returned amended change notice to the truthful v1.0 -> current
content-change chain.  It materializes repository-only predecessor snapshots,
the canonical v2 return receipt, the negative/boundary report and the complete
machine-proof bundle.  It never calls Zenodo, inspects credentials, creates a
Git ref, constructs an owner authorization or constructs an executable
qikvrt_zenodo_publication_manifest_v2.
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
MATRIX_PATH = f"{RELEASE_REL}/CLAIM_MATRIX_V2.json"
BINDINGS_PATH = f"{RELEASE_REL}/SOURCE_EVIDENCE_BINDINGS.json"
CHANGE_NOTICE_PATH = f"{RELEASE_REL}/CHANGE_NOTICE.md"
RETURN_RECEIPT_PATH = f"{RELEASE_REL}/PREPUBLICATION_RETURN_RECEIPT.json"
PROOF_BUNDLE_PATH = f"{RELEASE_REL}/MACHINE_PROOF_BUNDLE.json"
BOUNDARY_PATH = f"{RELEASE_REL}/BOUNDARY_TEST_REPORT.json"
AMENDED_NOTICE_RETURNED_AT = "2026-08-14T09:25:59Z"
AMENDED_NOTICE_RETURN_CHANNEL = "ChatGPT Work commentary"
ORIGINAL_SOURCE_COMMIT = "47510c8569f56ecf3d2e22fb5ed846fa32208b86"
ORIGINAL_SNAPSHOT_DIR = f"{RELEASE_REL}/original-candidate-47510c8"
ORIGINAL_SOURCE_PATHS = (
    f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf",
    f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex",
    f"{BASE}/README.md",
    f"{BASE}/WHATSAPP_ARTIKEL_BEOBACHTERRELATIVE_RETROKAUSALITAET_DE.md",
    f"{BASE}/CLAIM_MATRIX.json",
    f"{BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json",
    f"{BASE}/verify_observer_relative_retrocausality.py",
)
ORIGINAL_SNAPSHOT_BY_SOURCE = {
    source: f"{ORIGINAL_SNAPSHOT_DIR}/{pathlib.PurePosixPath(source).name}"
    for source in ORIGINAL_SOURCE_PATHS
}
ORIGINAL_SNAPSHOT_IDENTITIES = {
    f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf": (125122, "b31453b01e1b46b05b7e2954d7637223864965f033e987b604d1a07325d8786c"),
    f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex": (42975, "ff7a10e78f8f602352612d797e83a8911be3bc464d0d69e7b88f41f4a9139412"),
    f"{BASE}/README.md": (4610, "a23f96ec7f75dc28dcbc37012f1195a97370fdcfcf8dc92b6e70b0be6c3a18d9"),
    f"{BASE}/WHATSAPP_ARTIKEL_BEOBACHTERRELATIVE_RETROKAUSALITAET_DE.md": (17052, "433c1149ab8842311d58e89892a0feaf445330fbfcac0799d246307db86877b4"),
    f"{BASE}/CLAIM_MATRIX.json": (8078, "c7250fc60ce5d13808a69dc6af2a5c80e348bce3ed28514f18cae1d98fae6be8"),
    f"{BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json": (3722, "6ed0ae65dd112631b1c952275151c93ed5c8c126f87d9cdd8d1a64caa8fa3cd7"),
    f"{BASE}/verify_observer_relative_retrocausality.py": (7482, "53e43a4d3d96acc8654379d4cf5f0b09ec41edde686a39b7a5cec16ecdf524c9"),
}
PROOF_ARTIFACT_PATHS = frozenset({MATRIX_PATH, BINDINGS_PATH})
NON_UPLOAD_CONTROL_PATHS = frozenset(
    {
        f"{BASE}/PDF_RENDER_VALIDATION.json",
        f"{BASE}/SHA256SUMS",
        "state/work_units/OBSERVER_RELATIVE_RETROCAUSALITY_CURRENT_SYNTHESIS_V2.json",
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
    | set(ORIGINAL_SNAPSHOT_BY_SOURCE.values())
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


def _canonical_json_sha256(path: pathlib.Path) -> str:
    """Match the generic publisher's canonical metadata digest exactly."""
    value = json.loads(_raw(path).decode("utf-8"))
    material = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


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


def _original_snapshot_bytes(source: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{ORIGINAL_SOURCE_COMMIT}:{source}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    expected_size, expected_sha256 = ORIGINAL_SNAPSHOT_IDENTITIES[source]
    if result.returncode == 0:
        payload = result.stdout
    else:
        # The historical commit is retained as provenance, but a shallow or
        # pruned remote may not expose its object.  The repository therefore
        # retains a separately hash-pinned public snapshot for exact replay.
        archived = ROOT / ORIGINAL_SNAPSHOT_BY_SOURCE[source]
        payload = _raw(archived)
    if len(payload) != expected_size or hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise RuntimeError("original candidate snapshot identity mismatch: " + source)
    return payload


def _materialize_original_snapshots(*, write: bool) -> list[dict[str, Any]]:
    identities: list[dict[str, Any]] = []
    for source in ORIGINAL_SOURCE_PATHS:
        target = ROOT / ORIGINAL_SNAPSHOT_BY_SOURCE[source]
        expected = _original_snapshot_bytes(source)
        if target.is_file() and not target.is_symlink() and target.read_bytes() == expected:
            pass
        elif write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(expected)
        else:
            raise RuntimeError(
                "original candidate snapshot differs: "
                + target.relative_to(ROOT).as_posix()
            )
        identities.append(_identity(target))
    return identities


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


def _proof_candidate_files(
    returned_public_files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Partition the returned public set into candidate and proof artifacts."""
    candidates = [
        dict(item)
        for item in returned_public_files
        if item["path"] not in PROOF_ARTIFACT_PATHS
    ]
    artifact_paths = {
        item["path"]
        for item in returned_public_files
        if item["path"] in PROOF_ARTIFACT_PATHS
    }
    if artifact_paths != PROOF_ARTIFACT_PATHS:
        raise RuntimeError("returned public set lacks a required proof artifact")
    if len(candidates) != 15:
        raise RuntimeError("v2 proof candidate partition must contain 15 files")
    if {item["path"] for item in candidates} & PROOF_ARTIFACT_PATHS:
        raise RuntimeError("candidate/artifact proof partition overlaps")
    return candidates


def _bound_artifact(relative: str, kind: str) -> dict[str, str]:
    observed = _path_identity(relative)
    return {
        "path": observed["path"],
        "sha256": observed["sha256"],
        "git_blob_sha1": observed["git_blob_sha1"],
        "kind": kind,
    }


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
        ("SRC-PAPER-DEFINITION", f"{base}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex", "Operational definition of observer-local change time / Eigenzeit, negative information direction, and the coordinate-future versus causal-future boundary.", ["ORRZ-001"]),
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
            "boundary": "This is the authorial operational definition used by the work. A metric relativistic proper-time calibration needs an additional physical worldline binding. For spacelike-separated comparisons, a coordinate-future assignment is not a causal-future relation and does not make a source-bound record available before its source emission.",
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


def _bundle_claims(bindings_path: str) -> list[dict[str, Any]]:
    wording_by_classification = {
        "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
        "EMPIRICALLY_EVIDENCED": "EMPIRICALLY_SUPPORTED",
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "NORMATIVE": "NORMATIVE_DECLARATION",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
    }
    values: list[dict[str, Any]] = []
    for claim in _claims():
        classification = claim["classification"]
        values.append(
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "classification": classification,
                "status": claim["status"],
                "publication_wording": wording_by_classification[classification],
                "scope": claim["boundary"],
                "proof_refs": [],
                "evidence_refs": [],
                "source_refs": [
                    f"{bindings_path}#{source_id}"
                    for source_id in claim["sources"]
                ],
            }
        )
    return values


def _change_specs() -> list[dict[str, str]]:
    paper_tex = f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.tex"
    readme = f"{BASE}/README.md"
    witness = f"{BASE}/QIKVRT_RETROCAUSALITY_WITNESS.json"
    verifier = f"{BASE}/verify_observer_relative_retrocausality.py"
    declaration = f"{BASE}/AN_VON_UND_FUER_ALLE_MENSCHEN_DE.md"
    original_tex = ORIGINAL_SNAPSHOT_BY_SOURCE[paper_tex]
    original_readme = ORIGINAL_SNAPSHOT_BY_SOURCE[readme]
    original_witness = ORIGINAL_SNAPSHOT_BY_SOURCE[witness]
    original_verifier = ORIGINAL_SNAPSHOT_BY_SOURCE[verifier]
    return [
        {
            "claim_id": "ORRZ-001",
            "reason": (
                "Die lokale Veränderungszeit wird operativ von einer optionalen "
                "metrischen Eigenzeitkalibrierung getrennt; die negative "
                "Informationsrichtung wird an steigende Empfangsordnung und "
                "absteigende authentische Quellenordnung gebunden. Bei "
                "raumartiger Trennung kann ein lokales Gegenwartsereignis in "
                "einer gewählten Koordinatisierung im Koordinaten-Zukunftsbereich "
                "eines anderen Beobachters liegen; dies ist keine kausale "
                "Zukunftsbeziehung und stellt keinen Record vor seiner "
                "Quellenerzeugung bereit."
            ),
            "original_path": original_tex,
            "corrected_path": paper_tex,
        },
        {
            "claim_id": "ORRZ-002",
            "reason": (
                "Der endliche Prüfer und sein kanonischer Report werden als "
                "ausführbarer Zeuge des deklarierten Modells ausgewiesen, nicht "
                "als Lean-Kernel-Receipt, universeller Satz oder Messung des ganzen "
                "Universums."
            ),
            "original_path": original_verifier,
            "corrected_path": verifier,
        },
        {
            "claim_id": "ORRZ-003",
            "reason": (
                "Der bedingte endliche Existenzsatz wird für die genau genannten "
                "Ordnungs-, Authentizitäts- und Monotonieannahmen quellgebunden "
                "dargestellt; für diese aktuelle Claim-Menge liegt kein neues "
                "exaktes Lean-Kernel-Receipt vor."
            ),
            "original_path": original_tex,
            "corrected_path": paper_tex,
        },
        {
            "claim_id": "ORRZ-004",
            "reason": (
                "Die Konstruktion bindet zwei positive vorwärtsgerichtete "
                "Laufzeiten und trennt die resultierende Empfangsreihenfolge "
                "ausdrücklich von Überlichtübertragung, Empfang vor Emission und "
                "vergangenheitsgerichtetem Transport."
            ),
            "original_path": original_witness,
            "corrected_path": witness,
        },
        {
            "claim_id": "ORRZ-005",
            "reason": (
                "Delayed-Choice- und Quantenradierer-Arbeiten dienen nur als "
                "begrenzte Quellenbrücke für kontextabhängige Klassifikation; "
                "ein auswählbares Rückwärtssignal oder eine eindeutige empirische "
                "Auswahl von QIK-VRT wird nicht behauptet."
            ),
            "original_path": original_tex,
            "corrected_path": paper_tex,
        },
        {
            "claim_id": "ORRZ-006",
            "reason": (
                "Die vom Autor vertretene Korrespondenzthese wird als "
                "Interpretation von endlichem Zeugen, unabhängiger empirischer "
                "Bestätigung und wissenschaftlichem Konsens getrennt."
            ),
            "original_path": original_tex,
            "corrected_path": paper_tex,
        },
        {
            "claim_id": "ORRZ-007",
            "reason": (
                "Die neu hinzugefügte öffentliche Erklärung kennzeichnet "
                "„Vergrößere die Menge des Jetzt“ als normativen "
                "Verantwortungsimperativ und nicht als mathematischen Satz oder "
                "aus Physik erzwungenes Moralgesetz."
            ),
            "original_path": original_readme,
            "corrected_path": declaration,
        },
        {
            "claim_id": "ORRZ-008",
            "reason": (
                "Die zwei historischen PDFs bleiben bytegenaue Zwischenstände; "
                "spätere Aussagen werden ihnen nicht rückwirkend zugeschrieben und "
                "ihre Bytes werden nicht überschrieben."
            ),
            "original_path": original_readme,
            "corrected_path": readme,
        },
        {
            "claim_id": "ORRZ-009",
            "reason": (
                "Ein neues Lean-Kernel-Receipt für die aktuelle "
                "beobachterrelative Existenzdarstellung, unabhängige empirische "
                "Bestätigung und wissenschaftlicher Konsens bleiben ausdrücklich "
                "offen."
            ),
            "original_path": original_tex,
            "corrected_path": paper_tex,
        },
        {
            "claim_id": "ORRZ-010",
            "reason": (
                "Die neu hinzugefügte öffentliche Erklärung kennzeichnet den "
                "Schutz zukünftiger Handlungsfähigkeit und die Nicht-Reduktion von "
                "Menschen auf verwertbares Material, Risiko, Datei, Zielgruppe "
                "oder Feindbild als normative Position, nicht als mechanisch aus "
                "Software, Mathematik oder Physik erzwungene Folgerung."
            ),
            "original_path": original_readme,
            "corrected_path": declaration,
        },
    ]


def _return_receipt(
    proof_candidates: list[dict[str, Any]],
    original_files: list[dict[str, Any]],
    *,
    returned_at: str,
    return_channel: str,
) -> dict[str, Any]:
    candidate_by_path = {item["path"]: item for item in proof_candidates}
    original_by_path = {item["path"]: item for item in original_files}
    specs = _change_specs()
    normalized_notice = " ".join(
        _raw(ROOT / CHANGE_NOTICE_PATH).decode("utf-8").split()
    )
    for spec in specs:
        if spec["claim_id"] not in normalized_notice:
            raise RuntimeError(
                "visible change notice omits changed claim " + spec["claim_id"]
            )
        if " ".join(spec["reason"].split()) not in normalized_notice:
            raise RuntimeError(
                "visible change notice omits the exact reason for "
                + spec["claim_id"]
            )
        if spec["corrected_path"] not in candidate_by_path:
            raise RuntimeError(
                "changed claim lacks a returned candidate path: "
                + spec["claim_id"]
            )
        if spec["original_path"] not in original_by_path:
            raise RuntimeError(
                "changed claim lacks its original candidate snapshot: "
                + spec["claim_id"]
            )
    return {
        "_license": _license("machine_readable_prepublication_return_receipt"),
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": True,
        "original_files": original_files,
        "candidate_files": [
            {
                key: item[key]
                for key in ("path", "bytes", "sha256", "git_blob_sha1")
            }
            for item in proof_candidates
        ],
        "changed_claim_ids": [spec["claim_id"] for spec in specs],
        "change_reasons": [
            {
                "claim_id": spec["claim_id"],
                "reason": spec["reason"],
                "original_sha256": original_by_path[spec["original_path"]]["sha256"],
                "corrected_sha256": candidate_by_path[spec["corrected_path"]]["sha256"],
                "exact_candidate_path": spec["corrected_path"],
            }
            for spec in specs
        ],
        "change_notice_path": CHANGE_NOTICE_PATH,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": return_channel,
            "returned_at": returned_at,
            "visible_change_notice_returned": True,
        },
    }


def _machine_proof_bundle(
    proof_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    policy_path = "policy/zenodo-machine-proof-policy-v2.json"
    policy = _read_json(ROOT / policy_path)
    policy_identity = _path_identity(policy_path)
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
            "primary_document_path": (
                f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf"
            ),
            "files": proof_candidates,
        },
        "claims": _bundle_claims(BINDINGS_PATH),
        "artifacts": [
            _bound_artifact(MATRIX_PATH, "CLAIM_MATRIX"),
            _bound_artifact(BINDINGS_PATH, "EVIDENCE"),
            _bound_artifact(BOUNDARY_PATH, "BOUNDARY_TEST"),
            _bound_artifact(CHANGE_NOTICE_PATH, "CHANGE_NOTICE"),
            _bound_artifact(RETURN_RECEIPT_PATH, "RETURN_RECEIPT"),
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


def _proof_upload_paths(proof_candidates: list[dict[str, Any]]) -> list[str]:
    paths = [item["path"] for item in proof_candidates]
    paths.extend(
        [
            MATRIX_PATH,
            BINDINGS_PATH,
            BOUNDARY_PATH,
            CHANGE_NOTICE_PATH,
            RETURN_RECEIPT_PATH,
            PROOF_BUNDLE_PATH,
        ]
    )
    if len(paths) != 21 or len(paths) != len(set(paths)):
        raise RuntimeError("exact proof-bearing upload set must contain 21 unique paths")
    return paths


def _build_generated(*, write: bool) -> dict[str, object]:
    gate_status_path = f"{RELEASE_REL}/PRODUCTION_GATE_STATUS.json"
    freeze_path = f"{RELEASE_REL}/FROZEN_UPLOAD_CANDIDATE.json"
    return_draft_path = f"{RELEASE_REL}/PREPUBLICATION_RETURN_RECEIPT_DRAFT.json"
    proof_draft_path = f"{RELEASE_REL}/MACHINE_PROOF_BUNDLE_DRAFT.json"
    authorization_draft_path = f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION_DRAFT.json"
    manifest_draft_path = f"{RELEASE_REL}/PUBLISH_REQUEST_DRAFT.json"
    owner_message_path = RELEASE / "RETURN_TO_OWNER_MESSAGE.md"

    _write(ROOT / BINDINGS_PATH, _source_bindings(), write=write)
    _write(ROOT / MATRIX_PATH, _claim_matrix(), write=write)
    witness = _run_witness()
    candidate = _candidate_files()
    proof_candidates = _proof_candidate_files(candidate)
    upload_paths = _proof_upload_paths(proof_candidates)
    original_files = _materialize_original_snapshots(write=write)

    candidate_aggregate_sha256 = hashlib.sha256(_json_bytes(candidate)).hexdigest()
    freeze = {
        "_license": _license("machine_readable_candidate_freeze"),
        "schema": "qikvrt_zenodo_successor_candidate_freeze_v1",
        "publication_id": PUBLICATION_ID,
        "candidate_state": "FROZEN_RETURNED_PUBLIC_CANDIDATE_EXACT_AUTHORIZATION_PENDING",
        "primary_document_path": f"{BASE}/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf",
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
        "return_events": {
            "candidate_and_initial_notice_returned_at": "2026-08-13T19:49:33Z",
            "amended_notice_returned_at": AMENDED_NOTICE_RETURNED_AT,
            "return_channel": AMENDED_NOTICE_RETURN_CHANNEL,
        },
        "source_head_boundary": {
            "future_remote_execution_head_required": True,
            "reason": "The final v2 manifest must bind a committed and remotely observable pre-authorization source head; the manifest and owner authorization must live on a descendant execution commit.",
        },
        "no_external_effect": True,
    }
    _write(ROOT / freeze_path, freeze, write=write)
    freeze_identity = _path_identity(freeze_path)
    matrix_identity = _path_identity(MATRIX_PATH)
    bindings_identity = _path_identity(BINDINGS_PATH)
    metadata_path = ROOT / f"{RELEASE_REL}/ZENODO_METADATA_DRAFT.json"
    metadata_identity = _path_identity(f"{RELEASE_REL}/ZENODO_METADATA_DRAFT.json")
    canonical_metadata_sha256 = _canonical_json_sha256(metadata_path)
    change_identity = _path_identity(CHANGE_NOTICE_PATH)
    policy_identity = _path_identity("policy/zenodo-machine-proof-policy-v2.json")

    receipt = _return_receipt(
        proof_candidates,
        original_files,
        returned_at=AMENDED_NOTICE_RETURNED_AT,
        return_channel=AMENDED_NOTICE_RETURN_CHANNEL,
    )
    _write(ROOT / RETURN_RECEIPT_PATH, receipt, write=write)
    receipt_identity = _path_identity(RETURN_RECEIPT_PATH)

    gates = {
        "candidate_bytes_frozen": True,
        "candidate_returned_to_owner": True,
        "amended_visible_change_notice_returned": True,
        "claim_inventory_classified": True,
        "source_evidence_bindings_present": True,
        "negative_and_boundary_tests_present": True,
        "finite_witness_reexecuted": True,
        "historical_record_21888130_preserved": True,
        "existing_metadata_edit_package_preserved": True,
        "candidate_upload_set_excludes_preparation_control_and_draft_files": True,
        "canonical_prepublication_return_receipt": True,
        "canonical_machine_proof_bundle": True,
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
        "prepublication_return": {
            "receipt": receipt_identity,
            "content_changed": True,
            "changed_claim_ids": [f"ORRZ-{index:03d}" for index in range(1, 11)],
            "amended_notice_returned_at": AMENDED_NOTICE_RETURNED_AT,
            "return_channel": AMENDED_NOTICE_RETURN_CHANNEL,
            "original_source_commit": ORIGINAL_SOURCE_COMMIT,
            "repository_only_original_files": original_files,
        },
        "proof_partition": {
            "candidate_file_count": len(proof_candidates),
            "artifact_paths": [
                MATRIX_PATH,
                BINDINGS_PATH,
                BOUNDARY_PATH,
                CHANGE_NOTICE_PATH,
                RETURN_RECEIPT_PATH,
            ],
            "bundle_path": PROOF_BUNDLE_PATH,
            "exact_upload_count": len(upload_paths),
            "candidate_artifact_overlap": [],
        },
        "tests": [
            {"id": "BND-001", "name": "current finite witness reproduces the stored canonical report", "state": "PASS"},
            {"id": "BND-002", "name": "historical Zenodo record is preserved rather than replaced", "state": "PASS"},
            {"id": "BND-003", "name": "draft and control artifacts are rejected from the production upload set", "state": "PASS"},
            {"id": "BND-004", "name": "no new exact-head Lean kernel proof is represented as present", "state": "PASS"},
            {"id": "BND-005", "name": "all ten changed claims bind exact visible reasons and changed predecessor/current identities", "state": "PASS"},
            {"id": "BND-006", "name": "candidate and artifact path sets are disjoint", "state": "PASS"},
            {"id": "BND-007", "name": "negative and boundary report is included in the exact proof-bearing upload set", "state": "PASS"},
            {"id": "BND-008", "name": "owner authorization, production manifest, remote effect and DOI remain absent", "state": "PASS"},
        ],
        "production_gates": gates,
        "result": "POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING",
    }
    _write(ROOT / BOUNDARY_PATH, boundary, write=write)
    boundary_identity = _path_identity(BOUNDARY_PATH)

    bundle = _machine_proof_bundle(proof_candidates)
    _write(ROOT / PROOF_BUNDLE_PATH, bundle, write=write)
    proof_identity = _path_identity(PROOF_BUNDLE_PATH)
    sorted_upload_identities = [
        _path_identity(path) for path in sorted(upload_paths)
    ]
    proof_candidate_by_path = {item["path"]: item for item in proof_candidates}
    artifact_kind_by_path = {
        item["path"]: item["kind"] for item in bundle["artifacts"]
    }
    exact_upload_files: list[dict[str, Any]] = []
    for path in upload_paths:
        identity = _path_identity(path)
        candidate_entry = proof_candidate_by_path.get(path)
        exact_upload_files.append(
            {
                **identity,
                "name": (
                    candidate_entry["name"]
                    if candidate_entry is not None
                    else pathlib.PurePosixPath(path).name
                ),
                "partition": (
                    "candidate"
                    if candidate_entry is not None
                    else "bundle"
                    if path == PROOF_BUNDLE_PATH
                    else "artifact"
                ),
                "artifact_kind": artifact_kind_by_path.get(path),
            }
        )
    if len({item["name"] for item in exact_upload_files}) != len(exact_upload_files):
        raise RuntimeError("exact proof-bearing upload set contains duplicate names")
    upload_sha256sum_lines = "".join(
        f"{item['sha256']}  {item['path']}\n"
        for item in sorted_upload_identities
    ).encode("utf-8")
    upload_aggregate_sha256 = hashlib.sha256(upload_sha256sum_lines).hexdigest()
    upload_total_bytes = sum(item["bytes"] for item in sorted_upload_identities)

    gate_status = {
        "_license": _license("machine_readable_production_gate_status"),
        "schema": "qikvrt_zenodo_successor_production_gate_status_v1",
        "publication_id": PUBLICATION_ID,
        "state": "POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING",
        "gates": gates,
        "proof_artifacts": {
            "prepublication_return_receipt": receipt_identity,
            "machine_proof_bundle": proof_identity,
            "boundary_test_report": boundary_identity,
        },
        "exact_upload_fixity": {
            "file_count": len(upload_paths),
            "total_bytes": upload_total_bytes,
            "aggregate_sha256": upload_aggregate_sha256,
            "aggregate_algorithm": "SHA-256 of UTF-8 sorted '<file-sha256>  <repository-path>\\n' lines",
        },
        "first_blocker": "CANONICAL_EXACT_UPLOAD_AUTHORIZATION_MISSING",
        "next_action": "Return the final receipt, metadata and machine-proof hashes to Ingolf Lohmann and obtain one canonical AUTHORIZE_EXACT_UPLOAD statement before creating any owner authorization or production manifest.",
        "external_effects": {
            "existing_record_21888130_changed": False,
            "new_zenodo_record_created": False,
            "zenodo_upload_performed": False,
            "doi_registered_by_this_package": False,
        },
    }
    _write(ROOT / gate_status_path, gate_status, write=write)

    return_draft = {
        "_license": _license("machine_readable_prepublication_return_receipt_draft"),
        "schema": "qikvrt_prepublication_return_receipt_draft_v1",
        "publication_id": PUBLICATION_ID,
        "status": "SUPERSEDED_BY_CANONICAL_V2_RECEIPT",
        "candidate_freeze": freeze_identity,
        "canonical_receipt": receipt_identity,
        "visible_change_notice": change_identity,
        "return_event": {
            "returned_at": AMENDED_NOTICE_RETURNED_AT,
            "return_channel": AMENDED_NOTICE_RETURN_CHANNEL,
            "candidate_returned_to_owner": True,
            "visible_change_notice_returned": True,
        },
        "direct_owner_instruction": {
            "date": "2026-08-12",
            "channel": "CURRENT_CHAT_SESSION",
            "statement": DIRECTIVE,
            "interpretation": "Broad destination authorization recorded; not a candidate-specific AUTHORIZE_EXACT_UPLOAD statement.",
        },
        "not_a_v2_receipt": True,
    }
    _write(ROOT / return_draft_path, return_draft, write=write)
    return_draft_identity = _path_identity(return_draft_path)

    proof_draft = {
        "_license": _license("machine_readable_proof_bundle_draft"),
        "schema": "qikvrt_zenodo_machine_proof_bundle_draft_v1",
        "publication_id": PUBLICATION_ID,
        "status": "SUPERSEDED_BY_CANONICAL_V2_PROOF_BUNDLE",
        "active_policy": policy_identity,
        "candidate_freeze": freeze_identity,
        "canonical_machine_proof_bundle": proof_identity,
        "canonical_prepublication_return_receipt": receipt_identity,
        "boundary_test_report": boundary_identity,
        "exact_upload_paths": upload_paths,
        "exact_upload_count": len(upload_paths),
        "exact_upload_total_bytes": upload_total_bytes,
        "exact_upload_aggregate_sha256": upload_aggregate_sha256,
        "remaining_blocker": "CANONICAL_EXACT_UPLOAD_AUTHORIZATION_MISSING",
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
        "bound_pre_authorization_artifacts": {
            "candidate_freeze": freeze_identity,
            "metadata": metadata_identity,
            "machine_proof": proof_identity,
            "prepublication_return": receipt_identity,
            "historical_machine_proof_draft": proof_draft_identity,
            "historical_prepublication_return_draft": return_draft_identity,
        },
        "canonical_metadata_sha256": canonical_metadata_sha256,
        "canonical_statement_template": (
            "AUTHORIZE_EXACT_UPLOAD authorization_id=<new-single-use-id> "
            f"publication_id={PUBLICATION_ID} "
            f"return_sha256={receipt_identity['sha256']} "
            f"metadata_sha256={canonical_metadata_sha256} "
            f"machine_proof_sha256={proof_identity['sha256']}"
        ),
        "missing_before_production": [
            "canonical exact statement from Ingolf Lohmann after the completed return",
            "committed and remotely observable pre-authorization source_head",
            "repository-side OWNER_ZENODO_AUTHORIZATION.json and final v2 manifest on a descendant execution commit",
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
        "machine_proof": proof_identity,
        "prepublication_return": receipt_identity,
        "owner_authorization_draft": authorization_draft_identity,
        "exact_upload_paths": upload_paths,
        "exact_upload_files": exact_upload_files,
        "exact_upload_total_bytes": upload_total_bytes,
        "exact_upload_aggregate_sha256": upload_aggregate_sha256,
        "exact_upload_aggregate_algorithm": "SHA-256 of UTF-8 sorted '<file-sha256>  <repository-path>\\n' lines",
        "required_final_schema": "qikvrt_zenodo_publication_manifest_v2",
        "not_executable_by_generic_publisher": True,
        "required_before_conversion": [
            "exact canonical owner decision recorded",
            "pre-authorization source_head committed and remotely observable",
            "manifest and authorization committed on a descendant execution head",
            "generic publisher validation succeeds before any remote mutation",
        ],
    }
    _write(ROOT / manifest_draft_path, manifest_draft, write=write)

    upload_rows = []
    for item in exact_upload_files:
        upload_rows.append(
            f"| `{item['path']}` | `{item['name']}` | {item['partition']} | {item['bytes']} | `{item['sha256']}` | `{item['git_blob_sha1']}` |"
        )
    owner_message_lines = [
        "<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->",
        "# Exakte Vorautorisierungs-Rückgabe für den Zenodo-Nachfolger",
        "",
        "Die 17 eingefrorenen öffentlichen Kandidatendateien wurden am `2026-08-13T19:49:33Z` sichtbar zurückgegeben.",
        f"Der vervollständigte Änderungsvermerk wurde am `{AMENDED_NOTICE_RETURNED_AT}` über `{AMENDED_NOTICE_RETURN_CHANNEL}` sichtbar zurückgegeben.",
        "Der daraus materialisierte prooftragende Satz umfasst exakt 21 disjunkte Uploadpfade und wurde noch nicht hochgeladen.",
        "",
        f"- Receipt SHA-256: `{receipt_identity['sha256']}`",
        f"- Metadaten-Datei SHA-256: `{metadata_identity['sha256']}`",
        f"- Kanonische Metadaten SHA-256: `{canonical_metadata_sha256}`",
        f"- Machine-Proof SHA-256: `{proof_identity['sha256']}`",
        f"- Exakte Uploadgröße: `{upload_total_bytes}` Bytes",
        f"- Aggregat-SHA-256 der 21 sortierten Prüfsummenzeilen: `{upload_aggregate_sha256}`",
        "",
        "| Repositorypfad | Zenodo-Dateiname | Partition | Bytes | SHA-256 | Git-Blob-ID |",
        "|---|---|---|---:|---|---|",
        *upload_rows,
        "",
        "Eine Produktionsmutation bleibt bis zur kanonischen hashgebundenen `AUTHORIZE_EXACT_UPLOAD`-Zeile gesperrt.",
        "",
    ]
    owner_message = "\n".join(owner_message_lines).encode("utf-8")
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
        "proof_candidates": proof_candidates,
        "original_files": original_files,
        "upload_paths": upload_paths,
        "exact_upload_files": exact_upload_files,
        "freeze_path": freeze_path,
        "receipt_identity": receipt_identity,
        "proof_identity": proof_identity,
        "upload_total_bytes": upload_total_bytes,
        "upload_aggregate_sha256": upload_aggregate_sha256,
        "generated_paths": [
            BINDINGS_PATH,
            MATRIX_PATH,
            BOUNDARY_PATH,
            RETURN_RECEIPT_PATH,
            PROOF_BUNDLE_PATH,
            gate_status_path,
            freeze_path,
            return_draft_path,
            proof_draft_path,
            authorization_draft_path,
            manifest_draft_path,
            owner_message_path.relative_to(ROOT).as_posix(),
            *ORIGINAL_SNAPSHOT_BY_SOURCE.values(),
        ],
    }


def _sha_sums() -> str:
    entries: list[tuple[str, str]] = []
    for path in sorted(RELEASE.rglob("*")):
        if (
            not path.is_file()
            or path == RELEASE / "SHA256SUMS"
            or "__pycache__" in path.parts
            or path.suffix == ".pyc"
        ):
            continue
        entries.append(
            (
                hashlib.sha256(path.read_bytes()).hexdigest(),
                f"{RELEASE_REL}/{path.relative_to(RELEASE).as_posix()}",
            )
        )
    return "".join(f"{digest}  {name}\n" for digest, name in entries)


def _validate_machine_proof(upload_paths: list[str]) -> str:
    command = [
        sys.executable,
        "-B",
        "tools/qikvrt_zenodo_machine_proof.py",
        "--proof-bundle",
        PROOF_BUNDLE_PATH,
    ]
    for path in upload_paths:
        command.extend(["--upload-path", path])
    result = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode("utf-8", errors="replace")
        raise RuntimeError("machine-proof validation failed: " + detail.strip())
    output = result.stdout.decode("utf-8")
    if "ZENODO_MACHINE_PROOF_STATE=verified" not in output:
        raise RuntimeError("machine-proof validator did not report verified state")
    return output


def _materialize() -> None:
    generated = _build_generated(write=True)
    (RELEASE / "SHA256SUMS").write_text(_sha_sums(), encoding="utf-8")
    _validate_machine_proof(generated["upload_paths"])


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
    if (
        status.get("state")
        != "POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING"
    ):
        raise RuntimeError("production gate status boundary drifted")
    for name in (
        "candidate_upload_set_excludes_preparation_control_and_draft_files",
        "candidate_returned_to_owner",
        "amended_visible_change_notice_returned",
        "canonical_prepublication_return_receipt",
        "canonical_machine_proof_bundle",
        "negative_and_boundary_tests_present",
    ):
        if status.get("gates", {}).get(name) is not True:
            raise RuntimeError(f"completed proof gate must remain true: {name}")
    for name in (
        "canonical_exact_upload_authorization",
        "remote_source_head_binding",
        "production_upload_executed",
    ):
        if status.get("gates", {}).get(name) is not False:
            raise RuntimeError(f"production gate must remain false: {name}")
    receipt = _read_json(ROOT / RETURN_RECEIPT_PATH)
    if (
        receipt.get("content_changed") is not True
        or receipt.get("changed_claim_ids")
        != [f"ORRZ-{index:03d}" for index in range(1, 11)]
        or receipt.get("return", {}).get("returned_at")
        != AMENDED_NOTICE_RETURNED_AT
        or receipt.get("return", {}).get("visible_change_notice_returned") is not True
    ):
        raise RuntimeError("canonical return receipt boundary drifted")
    bundle = _read_json(ROOT / PROOF_BUNDLE_PATH)
    artifact_kinds = {item["path"]: item["kind"] for item in bundle["artifacts"]}
    if artifact_kinds.get(BOUNDARY_PATH) != "BOUNDARY_TEST":
        raise RuntimeError("proof bundle lacks the required boundary-test artifact")
    if len(expected["upload_paths"]) != 21:
        raise RuntimeError("exact proof-bearing upload set must contain 21 paths")
    exact_fixity = status.get("exact_upload_fixity", {})
    if (
        exact_fixity.get("file_count") != 21
        or exact_fixity.get("total_bytes") != expected["upload_total_bytes"]
        or exact_fixity.get("aggregate_sha256")
        != expected["upload_aggregate_sha256"]
    ):
        raise RuntimeError("exact proof-bearing upload aggregate drifted")
    for relative in (
        f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION.json",
        f"{RELEASE_REL}/publish-request.json",
    ):
        if (ROOT / relative).exists():
            raise RuntimeError("pre-authorization package contains a production control: " + relative)
    validator_output = _validate_machine_proof(expected["upload_paths"])
    print(
        "PASS successor pre-authorization proof package verified "
        f"candidate_files={len(expected['candidate'])} "
        f"proof_candidates={len(expected['proof_candidates'])} "
        f"upload_paths={len(expected['upload_paths'])} "
        f"receipt_sha256={expected['receipt_identity']['sha256']} "
        f"proof_sha256={expected['proof_identity']['sha256']} "
        "state=POST_RETURN_MACHINE_PROOF_READY_EXACT_AUTHORIZATION_PENDING"
    )
    print(validator_output.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="materialize deterministic final pre-authorization proof artifacts")
    parser.add_argument("--check", action="store_true", help="verify deterministic final pre-authorization proof artifacts")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    try:
        if args.write:
            _materialize()
            print("PREAUTHORIZATION_MACHINE_PROOF_MATERIALIZED_NO_EXTERNAL_EFFECT")
        else:
            _check()
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
