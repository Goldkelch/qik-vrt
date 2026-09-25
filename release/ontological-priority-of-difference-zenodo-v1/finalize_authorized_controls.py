#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Finalize the exact ontological-priority Zenodo v2 controls.

This helper is deterministic and local-only. It consumes the already successful
Universal Ontology and prepublication workflow artifacts, writes the final
machine-proof/authorization/manifest controls, and validates them through the
generic QIK-VRT v2 proof and publication loaders. It performs no network effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_machine_proof as proof
from tools import qikvrt_zenodo_publish as publish

RELEASE_REL = "release/ontological-priority-of-difference-zenodo-v1"
RELEASE = ROOT / RELEASE_REL
PUBLICATION_ID = "qikvrt-ontological-priority-of-difference-2026-v1"
SOURCE_HEAD = "8225b8238b592d61b4d7c7e45e4cf804c1354843"
SOURCE_TREE = "2506855437751831391b090d8f266127119a7ac9"
KERNEL_RUN_ID = 36113762374
PREPUBLICATION_RUN_ID = 36113762274
KERNEL_ARTIFACT_ID = 10854405579
PREPUBLICATION_ARTIFACT_ID = 10853874569
EXPECTED_CONTENT_AGGREGATE = "0549cff6cb8883fd3f75abc3002d0fe7917c5d6139adac2252bf1febd45cd1e1"
AUTHORIZED_AT = "2026-09-25T08:50:00Z"
AUTHORIZATION_ID = "qikvrt-ontology-difference-zenodo-20260925-v1"

PATHS = {
    "freeze": f"{RELEASE_REL}/CONTENT_CANDIDATE_FREEZE.json",
    "metadata_draft": f"{RELEASE_REL}/ZENODO_METADATA_DRAFT.json",
    "raw_kernel": f"{RELEASE_REL}/UNIVERSAL_ONTOLOGY_KERNEL_RECEIPT.json",
    "prepub_gate": f"{RELEASE_REL}/PREPUBLICATION_GATE_RECEIPT.json",
    "kernel": f"{RELEASE_REL}/KERNEL_RECEIPT.json",
    "claim_matrix": f"{RELEASE_REL}/CLAIM_MATRIX_V2.json",
    "source_evidence": f"{RELEASE_REL}/SOURCE_EVIDENCE_BINDINGS_V2.json",
    "return": f"{RELEASE_REL}/PREPUBLICATION_RETURN_RECEIPT_V2.json",
    "bundle": f"{RELEASE_REL}/MACHINE_PROOF_BUNDLE.json",
    "auth": f"{RELEASE_REL}/OWNER_ZENODO_AUTHORIZATION.json",
    "manifest": f"{RELEASE_REL}/publish-request.json",
    "evidence": f"{RELEASE_REL}/zenodo-publication.json",
}

LICENSE_TEXT_REF = "LICENSES/CC-BY-NC-ND-4.0.txt"


def fail(message: str) -> None:
    raise SystemExit("BLOCK: " + message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def identity_bytes(path: str, raw: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha": hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
    }


def artifact_identity(path: str, raw: bytes, kind: str) -> dict[str, Any]:
    value = identity_bytes(path, raw)
    return {
        "path": path,
        "sha256": value["sha256"],
        "git_blob_sha1": value["git_blob_sha"],
        "kind": kind,
    }


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def write_once(relative: str, raw: bytes) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        fail("final artifact already exists: " + relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def license_block(classification: str) -> dict[str, str]:
    return {
        "classification": classification,
        "copyright": "Copyright 2026 Ingolf Lohmann",
        "license": "CC-BY-NC-ND-4.0",
        "license_text_ref": LICENSE_TEXT_REF,
        "rights_holder": "Ingolf Lohmann",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--prepublication-artifact", required=True, type=pathlib.Path)
    args = parser.parse_args()

    if any((ROOT / PATHS[key]).exists() for key in (
        "raw_kernel", "prepub_gate", "kernel", "claim_matrix", "source_evidence",
        "return", "bundle", "auth", "manifest", "evidence",
    )):
        fail("one or more final publication artifacts already exist")

    freeze = load_json(ROOT / PATHS["freeze"])
    files = freeze.get("files")
    if (
        freeze.get("publication_id") != PUBLICATION_ID
        or not isinstance(files, list)
        or len(files) != 17
        or freeze.get("total_bytes") != 201710
        or freeze.get("exact_content_aggregate_sha256") != EXPECTED_CONTENT_AGGREGATE
    ):
        fail("frozen candidate differs from the returned 17-file subject")

    candidate: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            fail(f"candidate {index} is not an object")
        required = {"path", "name", "git_blob_sha1", "bytes", "sha256", "role"}
        if not required.issubset(item):
            fail(f"candidate {index} lacks required identity fields")
        if item["name"] in names:
            fail("candidate upload names are not unique")
        names.add(item["name"])
        candidate.append(dict(item))

    universal_raw = args.kernel_artifact.read_bytes()
    universal = json.loads(universal_raw.decode("utf-8"))
    prepub_raw = args.prepublication_artifact.read_bytes()
    prepub = json.loads(prepub_raw.decode("utf-8"))

    if (
        universal.get("schema") != "qikvrt_universal_ontology_kernel_receipt_v2"
        or universal.get("state") != "KERNEL_VERIFIED_FINITE_AND_RELATIONAL_MODELS"
        or universal.get("source_commit") != SOURCE_HEAD
        or universal.get("source_tree") != SOURCE_TREE
        or universal.get("theorem_count") != 35
        or universal.get("workflow", {}).get("run_id") != str(KERNEL_RUN_ID)
        or universal.get("project_axioms") != []
    ):
        fail("fresh Universal Ontology receipt differs")

    if (
        prepub.get("schema") != "qikvrt_ontological_priority_prepublication_gate_receipt_v1"
        or prepub.get("status") != "PASS_PREPUBLICATION_GATES_UPLOAD_STILL_BLOCKED"
        or prepub.get("source_head") != SOURCE_HEAD
        or prepub.get("source_tree") != SOURCE_TREE
        or prepub.get("content", {}).get("aggregate_sha256") != EXPECTED_CONTENT_AGGREGATE
        or prepub.get("content", {}).get("file_count") != 17
        or prepub.get("content", {}).get("total_bytes") != 201710
        or prepub.get("formal", {}).get("core_constants") != 35
        or prepub.get("formal", {}).get("extended_constants") != 74
        or prepub.get("formal", {}).get("origin_theorems_axiom_free") is not True
    ):
        fail("fresh prepublication receipt differs")

    write_once(PATHS["raw_kernel"], universal_raw)
    write_once(PATHS["prepub_gate"], prepub_raw)

    theorem_inventory = list(universal["axioms_by_theorem"])
    origin_theorems = [
        "QIKVRT.UniversalOntology.determinateReality_requires_difference",
        "QIKVRT.UniversalOntology.noDifference_excludes_determinateReality",
        "QIKVRT.UniversalOntology.noDifference_excludes_information",
    ]
    if not set(origin_theorems).issubset(theorem_inventory):
        fail("origin theorem inventory is incomplete")

    kernel = {
        "_license": license_block("machine_readable_kernel_receipt"),
        "schema": "qikvrt_ontological_priority_kernel_receipt_v1",
        "state": "KERNEL_VERIFIED",
        "publication_id": PUBLICATION_ID,
        "scope_id": PUBLICATION_ID,
        "source_head": SOURCE_HEAD,
        "source_tree": SOURCE_TREE,
        "workflow": {
            "run_id": KERNEL_RUN_ID,
            "run_attempt": 1,
            "conclusion": "success",
            "exact_head_bound": True,
        },
        "theorems": theorem_inventory,
        "theorem_count": len(theorem_inventory),
        "axioms_by_theorem": universal["axioms_by_theorem"],
        "project_axioms": universal["project_axioms"],
        "upstream_receipt": {
            "path": PATHS["raw_kernel"],
            "workflow_artifact_id": KERNEL_ARTIFACT_ID,
            "sha256": hashlib.sha256(universal_raw).hexdigest(),
            "git_blob_sha1": identity_bytes(PATHS["raw_kernel"], universal_raw)["git_blob_sha"],
        },
        "prepublication_gate": {
            "path": PATHS["prepub_gate"],
            "workflow_artifact_id": PREPUBLICATION_ARTIFACT_ID,
            "sha256": hashlib.sha256(prepub_raw).hexdigest(),
            "git_blob_sha1": identity_bytes(PATHS["prepub_gate"], prepub_raw)["git_blob_sha"],
            "content_aggregate_sha256": EXPECTED_CONTENT_AGGREGATE,
        },
        "scope_boundary": universal["scope_boundary"],
    }
    kernel_raw = json_bytes(kernel)
    write_once(PATHS["kernel"], kernel_raw)

    source_evidence = {
        "_license": license_block("machine_readable_source_evidence"),
        "schema": "qikvrt_ontological_priority_source_evidence_v2",
        "publication_id": PUBLICATION_ID,
        "sources": {
            "SRC-LEIBNIZ-PROSE": {
                "path": "docs/publications/2026-09-25-leibniz-qikvrt/PROSA_VOM_UNTERSCHIED_ZU_QIKVRT_DE.md",
                "sha256": "c569016aaa95354b5ab6f78019ea14ba5e0bfcc8ff1f6698f81b42cfd7da183c",
                "git_blob_sha1": "958ca375d4189d3a178500f300c9ae155f2dbcc3",
            },
            "SRC-LEIBNIZ-PDF": {
                "path": "docs/publications/2026-09-25-leibniz-qikvrt/Leibniz_QIK-VRT_Monaden_und_evidenzgebundener_Unterschied.pdf",
                "sha256": "f5623f13e0dbacb899bdf296567068fa5fd5a9504d9b857ad2899a05833c003a",
                "git_blob_sha1": "5ee4b7c8bcb11c58c203a3c99c685ffecc57ad54",
            },
        },
        "boundary": {
            "historical_parallel_is_not_identity": True,
            "formal_proof_is_not_empirical_confirmation": True,
            "zenodo_persistence_is_not_scientific_consensus": True,
        },
    }
    source_evidence_raw = json_bytes(source_evidence)
    write_once(PATHS["source_evidence"], source_evidence_raw)

    specs = [
        ("OPD-001", "Determinate reality, as defined by Nonempty (Distinction α), entails the existence of two unequal values.", "FORMAL_PROVED", "PROVED", "ESTABLISHED_WITHIN_SCOPE", "Exact Lean definition of DeterminateReality and Distinction only.", origin_theorems[0], None),
        ("OPD-002", "If every pair of values is equal, determinate reality is impossible.", "FORMAL_PROVED", "PROVED", "ESTABLISHED_WITHIN_SCOPE", "NoDifference α := ∀ left right : α, left = right.", origin_theorems[1], None),
        ("OPD-003", "If every pair of values is equal, no InformationWitness sourced by a Distinction can exist.", "FORMAL_PROVED", "PROVED", "ESTABLISHED_WITHIN_SCOPE", "InformationWitness is the exact source-bound structure in UniversalOntology/Core.lean.", origin_theorems[2], None),
        ("OPD-004", "Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.", "INTERPRETATIVE", "DECLARED", "INTERPRETATIVE_DECLARATION", "Beginning means ontological priority; nothing means absence of determinate difference.", None, None),
        ("OPD-005", "The theorem proves a first physical instant or empirical cosmogenesis.", "INTERPRETATIVE", "DECLARED", "INTERPRETATIVE_DECLARATION", "Explicit negative boundary: no first-time, cosmogenesis, quantum-vacuum, or creation-from-nothing conclusion follows from the Lean theorems.", None, None),
        ("OPD-006", "The physical universe instantiates the complete QIK-VRT Universal Ontology.", "OPEN", "OPEN", "EXPLICITLY_OPEN", "Requires independent reference binding, operationalization, evidence, known-limit recovery, prediction and validation.", None, None),
        ("OPD-007", "The formal theorem is identical to Leibniz's Principle of the Identity of Indiscernibles.", "INTERPRETATIVE", "DECLARED", "INTERPRETATIVE_DECLARATION", "Leibniz is a historical and conceptual reference; the QIK-VRT theorem is a distinct and weaker formal statement.", None, None),
        ("OPD-008", "Zenodo publication by itself establishes scientific consensus or physical truth.", "INTERPRETATIVE", "DECLARED", "INTERPRETATIVE_DECLARATION", "Explicit boundary: Zenodo establishes persistence/identity/availability of deposited bytes, not scientific consensus or physical truth.", None, None),
        ("OPD-009", "The public prose article traces a historical/conceptual line from the ontology of difference through Leibniz and later formal/technical developments to QIK-VRT.", "SOURCE_BOUND", "BOUND", "SOURCE_ATTRIBUTED", "Explanatory historical synthesis; it is not a claim that every cited predecessor already contained QIK-VRT.", None, "SRC-LEIBNIZ-PROSE"),
        ("OPD-010", "The Leibniz/QIK-VRT scientific PDF records a scholarly comparison and the dimensions in which QIK-VRT adds machine-checkable scope, provenance, successor semantics and effect evidence.", "SOURCE_BOUND", "BOUND", "SOURCE_ATTRIBUTED", "Scholarly comparison artifact; the PDF itself does not establish empirical physical correspondence or scientific consensus.", None, "SRC-LEIBNIZ-PDF"),
    ]
    matrix_claims = []
    bundle_claims = []
    for claim_id, statement, classification, status, wording, boundary, theorem, source in specs:
        matrix_claims.append({
            "claim_id": claim_id,
            "statement": statement,
            "classification": classification,
            "status": status,
            "boundary": boundary,
            "proof_refs": [theorem] if theorem else [],
            "sources": [source] if source else [],
        })
        bundle_claims.append({
            "claim_id": claim_id,
            "statement": statement,
            "classification": classification,
            "status": status,
            "publication_wording": wording,
            "scope": boundary,
            "proof_refs": [f"{PATHS['kernel']}#{theorem}"] if theorem else [],
            "evidence_refs": [],
            "source_refs": [f"{PATHS['source_evidence']}#{source}"] if source else [],
        })

    claim_matrix = {
        "schema": "qikvrt_ontological_priority_claim_matrix_v2",
        "publication_id": PUBLICATION_ID,
        "claim_count": len(matrix_claims),
        "claims": matrix_claims,
    }
    claim_matrix_raw = json_bytes(claim_matrix)
    write_once(PATHS["claim_matrix"], claim_matrix_raw)

    return_receipt = {
        "_license": license_block("machine_readable_prepublication_return_receipt"),
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": False,
        "original_files": [],
        "candidate_files": [
            {
                "path": item["path"],
                "bytes": item["bytes"],
                "sha256": item["sha256"],
                "git_blob_sha1": item["git_blob_sha1"],
            }
            for item in candidate
        ],
        "changed_claim_ids": [],
        "change_reasons": [],
        "change_notice_path": None,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": "ChatGPT and GitHub pull request #1215 exact candidate return",
            "returned_at": "2026-09-25T08:00:11Z",
            "visible_change_notice_returned": False,
        },
    }
    return_raw = json_bytes(return_receipt)
    write_once(PATHS["return"], return_raw)

    artifact_raw = {
        PATHS["claim_matrix"]: claim_matrix_raw,
        PATHS["kernel"]: kernel_raw,
        PATHS["raw_kernel"]: universal_raw,
        PATHS["prepub_gate"]: prepub_raw,
        PATHS["source_evidence"]: source_evidence_raw,
        PATHS["return"]: return_raw,
    }
    artifact_kind = {
        PATHS["claim_matrix"]: "CLAIM_MATRIX",
        PATHS["kernel"]: "KERNEL_RECEIPT",
        PATHS["raw_kernel"]: "EVIDENCE",
        PATHS["prepub_gate"]: "EVIDENCE",
        PATHS["source_evidence"]: "EVIDENCE",
        PATHS["return"]: "RETURN_RECEIPT",
    }
    artifacts = [
        artifact_identity(path, raw, artifact_kind[path])
        for path, raw in artifact_raw.items()
    ]

    candidate_files = []
    for item in candidate:
        candidate_files.append({
            "path": item["path"],
            "name": item["name"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
            "git_blob_sha1": item["git_blob_sha1"],
            "role": (
                "PRIMARY"
                if item["path"].endswith(
                    "/2026-09-25-ontological-priority-of-difference/SCIENTIFIC_ARTICLE_DE.md"
                )
                else "SUPPLEMENT"
            ),
        })

    bundle = {
        "_license": license_block("machine_readable_proof_bundle"),
        "schema": proof.BUNDLE_SCHEMA,
        "policy": {
            "id": proof.POLICY_ID,
            "path": proof.POLICY_PATH,
            "version": proof.POLICY_VERSION,
            "sha256": proof.POLICY_SHA256,
            "git_blob_sha1": proof.POLICY_GIT_BLOB_SHA1,
        },
        "publication_id": PUBLICATION_ID,
        "candidate": {
            "files": candidate_files,
            "primary_document_path": "docs/publications/2026-09-25-ontological-priority-of-difference/SCIENTIFIC_ARTICLE_DE.md",
        },
        "claims": bundle_claims,
        "artifacts": artifacts,
        "prepublication_return": {
            "content_changed": False,
            "candidate_returned_to_owner": True,
            "receipt_path": PATHS["return"],
            "change_notice_path": None,
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
    bundle_raw = json_bytes(bundle)
    write_once(PATHS["bundle"], bundle_raw)

    metadata_draft = load_json(ROOT / PATHS["metadata_draft"])
    metadata = dict(metadata_draft["metadata"])
    metadata["version"] = "1.0.0"
    metadata["prereserve_doi"] = True
    metadata_sha256 = hashlib.sha256(zenodo._json_bytes(metadata)).hexdigest()

    uploads: list[dict[str, Any]] = []
    for item in candidate:
        uploads.append({
            "path": item["path"],
            "name": item["name"],
            "bytes": item["bytes"],
            "sha256": item["sha256"],
            "git_blob_sha": item["git_blob_sha1"],
        })
    for path, raw in artifact_raw.items():
        ident = identity_bytes(path, raw)
        uploads.append({
            "path": path,
            "name": pathlib.PurePosixPath(path).name,
            "bytes": ident["bytes"],
            "sha256": ident["sha256"],
            "git_blob_sha": ident["git_blob_sha"],
        })
    bundle_ident = identity_bytes(PATHS["bundle"], bundle_raw)
    uploads.append({
        "path": PATHS["bundle"],
        "name": "MACHINE_PROOF_BUNDLE.json",
        "bytes": bundle_ident["bytes"],
        "sha256": bundle_ident["sha256"],
        "git_blob_sha": bundle_ident["git_blob_sha"],
    })
    if len(uploads) != 24 or len({item["name"] for item in uploads}) != 24:
        fail("final upload inventory must contain 24 unique names")

    return_ident = identity_bytes(PATHS["return"], return_raw)
    exact_statement = publish._canonical_authorization_statement(
        AUTHORIZATION_ID,
        PUBLICATION_ID,
        return_ident["sha256"],
        metadata_sha256,
        bundle_ident["sha256"],
    )
    nonce = hashlib.sha256(
        ("Veröffentliche jetzt auf Zenodo.|" + SOURCE_HEAD).encode("utf-8")
    ).hexdigest()

    authorization = {
        "_license": license_block("owner_effect_authorization"),
        "schema": publish.OWNER_AUTHORIZATION_SCHEMA,
        "authorization_id": AUTHORIZATION_ID,
        "nonce": nonce,
        "single_use": True,
        "single_use_scope": publish.SINGLE_USE_SCOPE,
        "principal": {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
        "publication_id": PUBLICATION_ID,
        "repository": "Goldkelch/qik-vrt",
        "source_head": SOURCE_HEAD,
        "candidate_return_receipt": return_ident,
        "canonical_metadata_sha256": metadata_sha256,
        "uploads": uploads,
        "machine_proof": bundle_ident,
        "authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS),
        "publication_evidence_path": PATHS["evidence"],
        "authorization_event": {
            "channel": "ChatGPT exact owner instruction: Veröffentliche jetzt auf Zenodo.",
            "authorized_at": AUTHORIZED_AT,
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": exact_statement,
            "statement_sha256": hashlib.sha256(
                exact_statement.encode("utf-8")
            ).hexdigest(),
            "principal": {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
            "candidate_return_receipt_sha256": return_ident["sha256"],
        },
    }
    authorization_raw = json_bytes(authorization)
    write_once(PATHS["auth"], authorization_raw)
    authorization_ident = identity_bytes(PATHS["auth"], authorization_raw)

    manifest = {
        "schema": publish.SCHEMA_V2,
        "state": "publish",
        "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
        "repository": "Goldkelch/qik-vrt",
        "source_head": SOURCE_HEAD,
        "metadata": metadata,
        "files": [
            {
                "path": item["path"],
                "name": item["name"],
                "git_blob_sha": item["git_blob_sha"],
            }
            for item in uploads
        ],
        "machine_proof": {
            "path": PATHS["bundle"],
            "git_blob_sha": bundle_ident["git_blob_sha"],
            "policy_id": proof.POLICY_ID,
        },
        "owner_authorization": authorization_ident,
        "evidence_path": PATHS["evidence"],
    }
    manifest_raw = json_bytes(manifest)
    write_once(PATHS["manifest"], manifest_raw)

    upload_paths = [item["path"] for item in uploads]
    proof_receipt = proof.validate_bundle(
        ROOT,
        ROOT / PATHS["bundle"],
        upload_paths=upload_paths,
    )
    normalized = publish.load_manifest(ROOT / PATHS["manifest"], ROOT)
    if (
        proof_receipt["machine_proof_complete"] is not True
        or proof_receipt["zenodo_upload_authorized"] is not True
        or len(normalized["files"]) != 24
        or normalized["source_head"] != SOURCE_HEAD
    ):
        fail("generic v2 publication validation differs")

    print(json.dumps({
        "schema": "qikvrt_ontological_priority_final_controls_receipt_v1",
        "source_head": SOURCE_HEAD,
        "source_tree": SOURCE_TREE,
        "upload_count": 24,
        "content_aggregate_sha256": EXPECTED_CONTENT_AGGREGATE,
        "return_sha256": return_ident["sha256"],
        "metadata_sha256": metadata_sha256,
        "machine_proof_sha256": bundle_ident["sha256"],
        "machine_proof_git_blob_sha1": bundle_ident["git_blob_sha"],
        "authorization_statement": exact_statement,
        "authorization_sha256": authorization_ident["sha256"],
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "state": "FINAL_CONTROLS_VALIDATED_READY_FOR_EXECUTION_COMMIT",
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
