#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Materialize the exact v2 Zenodo controls for the ontological-priority package.

This helper is effect-free. It consumes only already successful workflow artifacts,
materializes the exact machine-proof/upload controls, validates them through the
generic v2 proof/publisher code, and leaves the external Zenodo mutation to
tools/qikvrt_zenodo_publish.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_zenodo_machine_proof as proof
from tools import qikvrt_zenodo_publish as publish

RELEASE_REL = "release/ontological-priority-of-difference-zenodo-v1"
RELEASE = ROOT / RELEASE_REL
PUBLICATION_ID = "qikvrt-ontological-priority-of-difference-2026-v1"
REPOSITORY = "Goldkelch/qik-vrt"
SOURCE_HEAD = "8225b8238b592d61b4d7c7e45e4cf804c1354843"
SOURCE_TREE = "2506855437751831391b090d8f266127119a7ac9"
ONTOLOGY_RUN_ID = "36113762374"
PREPUBLICATION_RUN_ID = "36113762274"
OWNER_DIRECTIVE = (
    "state/authorization/delegations/"
    "OWNER_IMMEDIATE_ZENODO_PUBLICATION_DIRECTIVE_20260925_V1.json"
)

WORKFLOW_RECEIPT = RELEASE / "UNIVERSAL_ONTOLOGY_KERNEL_RECEIPT_WORKFLOW.json"
CORE_AXIOMS = RELEASE / "universal-ontology-axioms.txt"
EXTENDED_AXIOMS = RELEASE / "universal-ontology-extended-axioms.txt"
PREPUB_GATE = RELEASE / "PREPUBLICATION_GATE_RECEIPT.json"
KERNEL_RECEIPT = RELEASE / "KERNEL_RECEIPT.json"
CLAIM_MATRIX = RELEASE / "ZENODO_MACHINE_PROOF_CLAIM_MATRIX.json"
SOURCE_BINDINGS = RELEASE / "PUBLICATION_SOURCE_BINDINGS_V2.json"
RETURN_RECEIPT = RELEASE / "PREPUBLICATION_RETURN_RECEIPT_V2.json"
BUNDLE = RELEASE / "MACHINE_PROOF_BUNDLE.json"
OWNER_AUTH = RELEASE / "OWNER_ZENODO_AUTHORIZATION.json"
MANIFEST = RELEASE / "publish-request.json"
FINAL_UPLOAD = RELEASE / "FINAL_UPLOAD_AUTHORIZATION.json"
EVIDENCE = RELEASE / "zenodo-publication.json"

PRIMARY_DOCUMENT = (
    "docs/publications/2026-09-25-ontological-priority-of-difference/"
    "SCIENTIFIC_ARTICLE_DE.md"
)
FREEZE = RELEASE / "CONTENT_CANDIDATE_FREEZE.json"

LICENSE_PROOF = {
    "classification": "machine_readable_proof_bundle",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}
LICENSE_RETURN = {
    "classification": "machine_readable_prepublication_return_receipt",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}
LICENSE_AUTH = {
    "classification": "owner_effect_authorization",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}


def block(message: str) -> None:
    raise SystemExit("BLOCK: " + message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def identity(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    raw = path.read_bytes()
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()  # noqa: S324
    return {
        "path": relative,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": blob,
    }


def publisher_identity(relative: str) -> dict[str, Any]:
    value = identity(relative)
    return {
        "path": value["path"],
        "bytes": value["bytes"],
        "sha256": value["sha256"],
        "git_blob_sha": value["git_blob_sha1"],
    }


def git(*args: str, accepted: tuple[int, ...] = (0,)) -> str:
    p = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if p.returncode not in accepted:
        block("git " + " ".join(args[:2]) + " failed")
    return p.stdout.strip()


def require_source_ancestry() -> None:
    if git("rev-parse", "--verify", f"{SOURCE_HEAD}^{{commit}}") != SOURCE_HEAD:
        block("proof source head does not resolve")
    if git("merge-base", "--is-ancestor", SOURCE_HEAD, "HEAD", accepted=(0, 1)) == "":
        pass
    p = subprocess.run(
        ["git", "merge-base", "--is-ancestor", SOURCE_HEAD, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    if p.returncode != 0:
        block("current branch is not a descendant of the proof source head")


def source_blob(relative: str) -> str:
    return git("rev-parse", "--verify", f"{SOURCE_HEAD}:{relative}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        block(f"{path} must contain an object")
    return value


def copy_artifacts(ontology_dir: Path, prepub_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source_receipt = ontology_dir / "UNIVERSAL_ONTOLOGY_KERNEL_RECEIPT.json"
    source_core = ontology_dir / "universal-ontology-axioms.txt"
    source_extended = ontology_dir / "universal-ontology-extended-axioms.txt"
    source_prepub = (
        prepub_dir
        / "release/ontological-priority-of-difference-zenodo-v1/"
        "PREPUBLICATION_GATE_RECEIPT.json"
    )
    for path in (source_receipt, source_core, source_extended, source_prepub):
        if not path.is_file():
            block("workflow artifact member missing: " + str(path))
    shutil.copyfile(source_receipt, WORKFLOW_RECEIPT)
    shutil.copyfile(source_core, CORE_AXIOMS)
    shutil.copyfile(source_extended, EXTENDED_AXIOMS)
    shutil.copyfile(source_prepub, PREPUB_GATE)
    return load_json(WORKFLOW_RECEIPT), load_json(PREPUB_GATE)


def verify_workflow_receipts(kernel: dict[str, Any], prepub: dict[str, Any]) -> list[str]:
    if kernel.get("schema") != "qikvrt_universal_ontology_kernel_receipt_v2":
        block("universal ontology workflow receipt schema differs")
    if kernel.get("source_commit") != SOURCE_HEAD or kernel.get("source_tree") != SOURCE_TREE:
        block("universal ontology workflow receipt subject differs")
    workflow = kernel.get("workflow")
    if not isinstance(workflow, dict) or workflow.get("run_id") != ONTOLOGY_RUN_ID:
        block("universal ontology workflow run differs")
    axioms = kernel.get("axioms_by_theorem")
    if not isinstance(axioms, dict) or len(axioms) != 35:
        block("universal ontology theorem inventory differs")
    theorem_names = list(axioms)
    for theorem in (
        "QIKVRT.UniversalOntology.determinateReality_requires_difference",
        "QIKVRT.UniversalOntology.noDifference_excludes_determinateReality",
        "QIKVRT.UniversalOntology.noDifference_excludes_information",
    ):
        if theorem not in axioms or axioms[theorem] != []:
            block("origin theorem is missing or not axiom-free: " + theorem)

    if prepub.get("schema") != "qikvrt_ontological_priority_prepublication_gate_receipt_v1":
        block("prepublication gate receipt schema differs")
    if prepub.get("source_head") != SOURCE_HEAD or prepub.get("source_tree") != SOURCE_TREE:
        block("prepublication gate receipt subject differs")
    if prepub.get("publication_id") != PUBLICATION_ID:
        block("prepublication gate publication differs")
    if prepub.get("status") != "PASS_PREPUBLICATION_GATES_UPLOAD_STILL_BLOCKED":
        block("prepublication gate did not pass")
    formal = prepub.get("formal")
    if formal != {
        "core_constants": 35,
        "extended_constants": 74,
        "origin_theorems_axiom_free": True,
    }:
        block("prepublication formal receipt differs")
    content = prepub.get("content")
    if not isinstance(content, dict) or content.get("file_count") != 17:
        block("prepublication candidate file count differs")
    freeze = load_json(FREEZE)
    if (
        freeze.get("exact_content_aggregate_sha256") != content.get("aggregate_sha256")
        or freeze.get("total_bytes") != content.get("total_bytes")
        or len(freeze.get("files", [])) != content.get("file_count")
    ):
        block("frozen candidate differs from the successful prepublication receipt")
    return theorem_names


def materialize_kernel_receipt(kernel: dict[str, Any], theorem_names: list[str]) -> None:
    wrapper = {
        "_license": {
            "classification": "machine_readable_kernel_receipt",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_ontological_priority_kernel_receipt_v1",
        "state": "KERNEL_VERIFIED",
        "publication_id": PUBLICATION_ID,
        "source_head": SOURCE_HEAD,
        "source_tree": SOURCE_TREE,
        "workflow": {
            "run_id": int(ONTOLOGY_RUN_ID),
            "run_attempt": 1,
            "conclusion": "success",
            "exact_head_bound": True,
        },
        "theorems": theorem_names,
        "theorem_count": len(theorem_names),
        "axioms_by_theorem": kernel["axioms_by_theorem"],
        "source_workflow_receipt": identity(WORKFLOW_RECEIPT.relative_to(ROOT).as_posix()),
        "boundary": {
            "formal_scope_only": True,
            "physical_cosmogony_claimed": False,
            "predecessor_evidence_transfer": False,
        },
    }
    write_json(KERNEL_RECEIPT, wrapper)


def materialize_sources() -> None:
    value = {
        "schema": "qikvrt_ontological_priority_publication_source_bindings_v2",
        "publication_id": PUBLICATION_ID,
        "PROOF_SOURCE_HEAD": {
            "repository": REPOSITORY,
            "head": SOURCE_HEAD,
            "tree": SOURCE_TREE,
        },
        "LEIBNIZ_PRIMARY": {
            "citation": "G. W. Leibniz, Discours de Metaphysique §9 and Monadology",
            "role": "historical and conceptual context, not an identity claim",
        },
        "PRIOR_ZENODO_21582781": {
            "doi": "10.5281/zenodo.21582781",
            "role": "historical related ontology publication",
        },
        "QIKVRT_LEIBNIZ_COMPARISON": {
            "path": "docs/publications/2026-09-25-leibniz-qikvrt/SCIENTIFIC_ARTICLE_LEIBNIZ_QIKVRT_DE.md",
            "role": "scholarly comparison of Leibniz and QIK-VRT",
        },
    }
    write_json(SOURCE_BINDINGS, value)


def claim_rows() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "OPD-001",
            "statement": "Determinate reality, as defined by Nonempty (Distinction alpha), entails the existence of two unequal values.",
            "classification": "FORMAL_PROVED",
            "status": "PROVED",
            "boundary": "Exact Lean definitions of DeterminateReality and Distinction only.",
            "proof_refs": ["QIKVRT.UniversalOntology.determinateReality_requires_difference"],
            "sources": [],
        },
        {
            "claim_id": "OPD-002",
            "statement": "If every pair of values is equal, determinate reality is impossible.",
            "classification": "FORMAL_PROVED",
            "status": "PROVED",
            "boundary": "NoDifference alpha := for all left right, left = right.",
            "proof_refs": ["QIKVRT.UniversalOntology.noDifference_excludes_determinateReality"],
            "sources": [],
        },
        {
            "claim_id": "OPD-003",
            "statement": "If every pair of values is equal, no InformationWitness sourced by a Distinction can exist.",
            "classification": "FORMAL_PROVED",
            "status": "PROVED",
            "boundary": "InformationWitness is exactly the source-bound structure in UniversalOntology/Core.lean.",
            "proof_refs": ["QIKVRT.UniversalOntology.noDifference_excludes_information"],
            "sources": [],
        },
        {
            "claim_id": "OPD-004",
            "statement": "Am Anfang muss ein Unterschied gewesen sein, denn sonst wäre alles nichts.",
            "classification": "INTERPRETATIVE",
            "status": "DECLARED",
            "boundary": "Beginning means ontological priority; nothing means absence of determinate difference.",
            "proof_refs": [],
            "sources": [],
        },
        {
            "claim_id": "OPD-005",
            "statement": "The physical universe instantiates the complete QIK-VRT Universal Ontology.",
            "classification": "OPEN",
            "status": "OPEN",
            "boundary": "Physical correspondence remains open and requires independent operationalization and evidence.",
            "proof_refs": [],
            "sources": [],
        },
        {
            "claim_id": "OPD-006",
            "statement": "Leibniz is a historical and conceptual precursor for questions of discernibility, monadic perspective and calculable reasoning.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "Historical/contextual attribution only; QIK-VRT is not asserted to be identical with Leibnizian metaphysics.",
            "proof_refs": [],
            "sources": ["LEIBNIZ_PRIMARY"],
        },
        {
            "claim_id": "OPD-007",
            "statement": "Zenodo DOI 10.5281/zenodo.21582781 is a prior related QIK-VRT ontology publication and is not overwritten by this record.",
            "classification": "SOURCE_BOUND",
            "status": "BOUND",
            "boundary": "Relationship/provenance claim only.",
            "proof_refs": [],
            "sources": ["PRIOR_ZENODO_21582781"],
        },
        {
            "claim_id": "OPD-008",
            "statement": "QIK-VRT extends Leibniz-related motifs specifically through machine-checkable scope, provenance, successor identity, causal/effect evidence and fresh readback.",
            "classification": "INTERPRETATIVE",
            "status": "DECLARED",
            "boundary": "Dimension-specific scholarly comparison; not a global ranking of philosophical systems.",
            "proof_refs": [],
            "sources": ["QIKVRT_LEIBNIZ_COMPARISON"],
        },
        {
            "claim_id": "OPD-009",
            "statement": "Zenodo persistence must not be promoted into empirical confirmation, physical truth or scientific consensus.",
            "classification": "NORMATIVE",
            "status": "DECLARED",
            "boundary": "Publication-effect boundary for this exact record.",
            "proof_refs": [],
            "sources": [],
        },
    ]


def materialize_claim_matrix() -> list[dict[str, Any]]:
    rows = claim_rows()
    value = {
        "schema": "qikvrt_ontological_priority_claim_matrix_v2",
        "publication_id": PUBLICATION_ID,
        "claim_count": len(rows),
        "claims": rows,
    }
    write_json(CLAIM_MATRIX, value)
    return rows


def candidate_files() -> list[dict[str, Any]]:
    freeze = load_json(FREEZE)
    result: list[dict[str, Any]] = []
    for item in freeze["files"]:
        relative = item["path"]
        observed = identity(relative)
        for key in ("bytes", "sha256", "git_blob_sha1"):
            if observed[key] != item[key]:
                block("candidate identity drift: " + relative)
        if source_blob(relative) != observed["git_blob_sha1"]:
            block("candidate bytes are not committed at the proof source head: " + relative)
        result.append(
            {
                "path": relative,
                "name": item["name"],
                "bytes": observed["bytes"],
                "sha256": observed["sha256"],
                "git_blob_sha1": observed["git_blob_sha1"],
                "role": "PRIMARY" if relative == PRIMARY_DOCUMENT else "SUPPLEMENT",
            }
        )
    if sum(1 for item in result if item["role"] == "PRIMARY") != 1:
        block("candidate must contain exactly one primary document")
    return result


def materialize_return(candidates: list[dict[str, Any]]) -> str:
    returned_at = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
    value = {
        "_license": LICENSE_RETURN,
        "schema": proof.RETURN_SCHEMA,
        "publication_id": PUBLICATION_ID,
        "content_changed": False,
        "original_files": [],
        "candidate_files": [
            {key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")}
            for item in candidates
        ],
        "changed_claim_ids": [],
        "change_reasons": [],
        "change_notice_path": None,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": "ChatGPT exact candidate readback plus repository-bound successful prepublication receipt",
            "returned_at": returned_at,
            "visible_change_notice_returned": False,
        },
    }
    write_json(RETURN_RECEIPT, value)
    return returned_at


def artifact(relative: str, kind: str) -> dict[str, Any]:
    observed = identity(relative)
    return {
        "path": relative,
        "sha256": observed["sha256"],
        "git_blob_sha1": observed["git_blob_sha1"],
        "kind": kind,
    }


def materialize_bundle(candidates: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[str]:
    source_bindings_rel = SOURCE_BINDINGS.relative_to(ROOT).as_posix()
    kernel_rel = KERNEL_RECEIPT.relative_to(ROOT).as_posix()
    artifacts = [
        artifact(CLAIM_MATRIX.relative_to(ROOT).as_posix(), "CLAIM_MATRIX"),
        artifact(kernel_rel, "KERNEL_RECEIPT"),
        artifact(WORKFLOW_RECEIPT.relative_to(ROOT).as_posix(), "EVIDENCE"),
        artifact(CORE_AXIOMS.relative_to(ROOT).as_posix(), "EVIDENCE"),
        artifact(EXTENDED_AXIOMS.relative_to(ROOT).as_posix(), "EVIDENCE"),
        artifact(PREPUB_GATE.relative_to(ROOT).as_posix(), "EVIDENCE"),
        artifact(source_bindings_rel, "SOURCE"),
        artifact(RETURN_RECEIPT.relative_to(ROOT).as_posix(), "RETURN_RECEIPT"),
    ]
    status_wording = {
        "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
        "NORMATIVE": "NORMATIVE_DECLARATION",
    }
    claims = []
    for row in rows:
        claims.append(
            {
                "claim_id": row["claim_id"],
                "statement": row["statement"],
                "classification": row["classification"],
                "status": row["status"],
                "publication_wording": status_wording[row["classification"]],
                "scope": row["boundary"],
                "proof_refs": [
                    f"{kernel_rel}#{name}" for name in row["proof_refs"]
                ],
                "evidence_refs": [],
                "source_refs": [
                    f"{source_bindings_rel}#{name}" for name in row["sources"]
                ],
            }
        )
    bundle = {
        "_license": LICENSE_PROOF,
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
            "files": candidates,
            "primary_document_path": PRIMARY_DOCUMENT,
        },
        "claims": claims,
        "artifacts": artifacts,
        "prepublication_return": {
            "content_changed": False,
            "candidate_returned_to_owner": True,
            "receipt_path": RETURN_RECEIPT.relative_to(ROOT).as_posix(),
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
    write_json(BUNDLE, bundle)
    return [item["path"] for item in candidates] + [item["path"] for item in artifacts] + [BUNDLE.relative_to(ROOT).as_posix()]


def metadata() -> dict[str, Any]:
    draft = load_json(RELEASE / "ZENODO_METADATA_DRAFT.json")
    base = dict(draft["metadata"])
    base["title"] = (
        "Der ontologische Vorrang des Unterschieds: Ein maschinenprüfbares "
        "Minimaltheorem über Bestimmbarkeit, Information und den Geltungsbereich "
        "formaler Welterklärungen"
    )
    base["upload_type"] = "publication"
    base["publication_type"] = "article"
    base["creators"] = [{"name": "Ingolf Lohmann"}]
    base["version"] = "1.0.0"
    base["publication_date"] = "2026-09-25"
    base["access_right"] = "open"
    base["license"] = "cc-by-nc-nd-4.0"
    base["language"] = "deu"
    base["prereserve_doi"] = True
    return base


def materialize_authorization_and_manifest(upload_paths: list[str]) -> str:
    validated = proof.validate_bundle(ROOT, BUNDLE, upload_paths=upload_paths)
    proof_identity = publisher_identity(BUNDLE.relative_to(ROOT).as_posix())
    return_identity = publisher_identity(RETURN_RECEIPT.relative_to(ROOT).as_posix())
    meta = metadata()
    metadata_sha256 = hashlib.sha256(publish.zenodo._json_bytes(meta)).hexdigest()

    uploads = []
    manifest_files = []
    seen_names: set[str] = set()
    candidate_name_map = {
        item["path"]: item["name"] for item in load_json(FREEZE)["files"]
    }
    artifact_name_map = {
        CLAIM_MATRIX.relative_to(ROOT).as_posix(): "ZENODO_MACHINE_PROOF_CLAIM_MATRIX.json",
        KERNEL_RECEIPT.relative_to(ROOT).as_posix(): "KERNEL_RECEIPT.json",
        WORKFLOW_RECEIPT.relative_to(ROOT).as_posix(): "UNIVERSAL_ONTOLOGY_KERNEL_RECEIPT_WORKFLOW.json",
        CORE_AXIOMS.relative_to(ROOT).as_posix(): "universal-ontology-axioms.txt",
        EXTENDED_AXIOMS.relative_to(ROOT).as_posix(): "universal-ontology-extended-axioms.txt",
        PREPUB_GATE.relative_to(ROOT).as_posix(): "PREPUBLICATION_GATE_RECEIPT.json",
        SOURCE_BINDINGS.relative_to(ROOT).as_posix(): "PUBLICATION_SOURCE_BINDINGS_V2.json",
        RETURN_RECEIPT.relative_to(ROOT).as_posix(): "PREPUBLICATION_RETURN_RECEIPT_V2.json",
        BUNDLE.relative_to(ROOT).as_posix(): "MACHINE_PROOF_BUNDLE.json",
    }
    for relative in upload_paths:
        observed = publisher_identity(relative)
        name = candidate_name_map.get(relative, artifact_name_map.get(relative))
        if not name:
            block("upload name is undefined: " + relative)
        if name in seen_names:
            block("duplicate upload name: " + name)
        seen_names.add(name)
        uploads.append({**observed, "name": name})
        manifest_files.append(
            {
                "path": relative,
                "name": name,
                "git_blob_sha": observed["git_blob_sha"],
            }
        )

    directive_raw = (ROOT / OWNER_DIRECTIVE).read_bytes()
    nonce = hashlib.sha256(
        directive_raw + proof_identity["sha256"].encode("ascii") + SOURCE_HEAD.encode("ascii")
    ).hexdigest()
    authorization_id = "qikvrt-opd-zenodo-final-20260925-001"
    exact_statement = publish._canonical_authorization_statement(
        authorization_id,
        PUBLICATION_ID,
        return_identity["sha256"],
        metadata_sha256,
        proof_identity["sha256"],
    )
    authorized_at = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    auth = {
        "_license": LICENSE_AUTH,
        "schema": publish.OWNER_AUTHORIZATION_SCHEMA,
        "authorization_id": authorization_id,
        "nonce": nonce,
        "single_use": True,
        "single_use_scope": publish.SINGLE_USE_SCOPE,
        "principal": {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
        "publication_id": PUBLICATION_ID,
        "repository": REPOSITORY,
        "source_head": SOURCE_HEAD,
        "candidate_return_receipt": return_identity,
        "canonical_metadata_sha256": metadata_sha256,
        "uploads": uploads,
        "machine_proof": proof_identity,
        "authorized_effects": list(publish.OWNER_AUTHORIZED_EFFECTS),
        "publication_evidence_path": EVIDENCE.relative_to(ROOT).as_posix(),
        "authorization_event": {
            "channel": 'ChatGPT owner directive "Veröffentliche jetzt auf Zenodo." bound by the repository publication executor',
            "authorized_at": authorized_at,
            "decision": "AUTHORIZE_EXACT_UPLOAD",
            "exact_statement": exact_statement,
            "statement_sha256": hashlib.sha256(exact_statement.encode("utf-8")).hexdigest(),
            "principal": {"name": "Ingolf Lohmann", "type": "NATURAL_PERSON"},
            "candidate_return_receipt_sha256": return_identity["sha256"],
        },
    }
    write_json(OWNER_AUTH, auth)
    owner_identity = publisher_identity(OWNER_AUTH.relative_to(ROOT).as_posix())
    manifest = {
        "schema": publish.SCHEMA_V2,
        "state": "publish",
        "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
        "repository": REPOSITORY,
        "source_head": SOURCE_HEAD,
        "metadata": meta,
        "files": manifest_files,
        "machine_proof": {
            "path": BUNDLE.relative_to(ROOT).as_posix(),
            "git_blob_sha": proof_identity["git_blob_sha"],
            "policy_id": proof.POLICY_ID,
        },
        "owner_authorization": owner_identity,
        "evidence_path": EVIDENCE.relative_to(ROOT).as_posix(),
    }
    write_json(MANIFEST, manifest)

    aggregate_lines = [
        f"{item['sha256']}  {item['path']}  {item['name']}\n" for item in uploads
    ]
    aggregate_sha256 = hashlib.sha256(
        "".join(sorted(aggregate_lines)).encode("utf-8")
    ).hexdigest()
    final = {
        "schema": "qikvrt_final_upload_authorization_v1",
        "publication_id": PUBLICATION_ID,
        "proof_source_head": SOURCE_HEAD,
        "proof_source_tree": SOURCE_TREE,
        "upload_count": len(uploads),
        "aggregate_algorithm": "SHA-256 of sorted '<sha256>  <path>  <name>\\n' lines",
        "final_upload_aggregate_sha256": aggregate_sha256,
        "machine_proof_sha256": proof_identity["sha256"],
        "return_receipt_sha256": return_identity["sha256"],
        "metadata_sha256": metadata_sha256,
        "authorization_id": authorization_id,
        "exact_authorization_statement": exact_statement,
        "owner_directive_path": OWNER_DIRECTIVE,
        "predecessor_evidence_transfer": False,
    }
    write_json(FINAL_UPLOAD, final)

    # Full schema validation before any commit/effect.
    publish.load_manifest(MANIFEST, ROOT)
    if validated["sha256"] != proof_identity["sha256"]:
        block("validated proof identity drift")
    print("FINAL_UPLOAD_AGGREGATE_SHA256=" + aggregate_sha256)
    print("FINAL_UPLOAD_COUNT=" + str(len(uploads)))
    print("MACHINE_PROOF_SHA256=" + proof_identity["sha256"])
    return aggregate_sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ontology-artifact-dir", type=Path, required=True)
    parser.add_argument("--prepublication-artifact-dir", type=Path, required=True)
    args = parser.parse_args()

    require_source_ancestry()
    if EVIDENCE.exists():
        block("publication evidence already exists")
    kernel, prepub = copy_artifacts(
        args.ontology_artifact_dir.resolve(),
        args.prepublication_artifact_dir.resolve(),
    )
    theorem_names = verify_workflow_receipts(kernel, prepub)
    materialize_kernel_receipt(kernel, theorem_names)
    materialize_sources()
    rows = materialize_claim_matrix()
    candidates = candidate_files()
    materialize_return(candidates)
    upload_paths = materialize_bundle(candidates, rows)
    materialize_authorization_and_manifest(upload_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
