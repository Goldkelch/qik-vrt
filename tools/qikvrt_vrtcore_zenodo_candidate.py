#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministically materialize the VRTCore Zenodo proof candidate.

The kernel stage turns an immutable, exact-head GitHub Actions payload into a
full claim matrix, a kernel receipt and a boundary report.  The return stage
then freezes the owner-facing files, a visible change notice, canonical Zenodo
metadata, an acyclic checksum index and the v2 machine-proof bundle.  Both
stages bind verified predecessor bytes instead of pretending that a generated
receipt can bind the commit which first contains that receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from collections import Counter
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION_REL = pathlib.PurePosixPath(
    "docs/publications/2026-08-02-causality-is-relation-vrtcore"
)
PUBLICATION = ROOT.joinpath(*PUBLICATION_REL.parts)
PUBLICATION_ID = "qikvrt-causality-is-relation-vrtcore-v1"
VERIFIED_HEAD = "bc4aeba26a79baed40f7b7ce709f0a9fd77d318f"
VERIFIED_TREE = "4125800b3bffce670d5fcaf0656b9de1e7721e61"
H0_MATRIX_NAME = "VRTCore_CLAIM_MATRIX_H0_RETURNED.json"
H1_OVERLAY_NAME = "VRTCore_CLAIM_MATRIX_H1_KERNEL_VERIFIED.json"
CI_EVIDENCE_NAME = "CI_KERNEL_EVIDENCE_H2FIX_EXACT_HEAD.json"
CLAIM_MATRIX_NAME = "CLAIM_MATRIX.json"
KERNEL_RECEIPT_NAME = "KERNEL_RECEIPT.json"
BOUNDARY_REPORT_NAME = "BOUNDARY_TEST_REPORT.json"
CHANGE_NOTICE_NAME = "CHANGE_NOTICE.md"
RETURN_RECEIPT_NAME = "PREPUBLICATION_RETURN_RECEIPT.json"
ZENODO_METADATA_NAME = "ZENODO_METADATA.json"
ZENODO_CHECKSUMS_NAME = "ZENODO_SHA256SUMS"
PROOF_BUNDLE_NAME = "MACHINE_PROOF_BUNDLE.json"
CI_EVIDENCE_SHA256 = (
    "25ca9640b212ea5b331c8cb8e1200a95353525a1686145d967e8884dd5cfbf9f"
)
CI_ARCHIVE_SHA256 = (
    "04dd14d815a9129486c65cd542dcbd96907173caa66da18f158f88b95430dcfe"
)
OWNER_CANDIDATE_SHA256 = {
    "QIK-VRT_Kausalitaet_ist_Relation_Fachartikel_DE_2026-08-02.md":
        "902d0abff59d7a9c8026a506081e25c6106abc4d88ca07197d08ff74fcc6041d",
    "QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_DE_2026-08-02.md":
        "4199dc4eb2b239e60c375424228a7d4ff5b1238a2370b88898befab5ceb34d09",
    "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.tex":
        "91ff57fc16bb91096296f28c97d541fad3bab244411b969e063ecbe31e363a08",
    "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf":
        "7f29f90bb0254f813237d07c73e9ab29c4b4f5a8c2f025dc7cdcf5f8f7ebad23",
    "VERIFICATION_ADDENDUM_DE.md":
        "f4b029fe4b49da6161708c201b234261e89b07ba613a8754be8b8accfdcb66af",
    "QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_Verifikationsnachtrag_DE_2026-08-02.md":
        "ef83c0c41de84c844ab5af794326ce50e98bc35f90a71f426ec6e3815b346ad8",
}

PRIMARY_CANDIDATE = (
    "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf"
)
POLICY = {
    "id": "qikvrt-zenodo-machine-proof-before-publication-v2",
    "path": "policy/zenodo-machine-proof-policy-v2.json",
    "version": "2.0.0",
    "sha256": "933d6322a1e294848c6385d1384ab0ec3862c8675ebe35ec2fc4cad3e0baec47",
    "git_blob_sha1": "e9578d30d22f845e7df684128dcd9332641c00be",
}

PUBLICATION_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("README.md", "SOURCE"),
    ("ZENODO_FILESET.md", "OTHER"),
    ("CITATION.cff", "OTHER"),
    ("LICENSE_NOTICE.md", "OTHER"),
    ("EVIDENCE_BOUNDARY.md", "SOURCE"),
    ("ORIGINAL_PACKAGE_MANIFEST.json", "EVIDENCE"),
    ("ARTIFACT_PATH_MAP.json", "EVIDENCE"),
    ("VRTCore_Syntax.ebnf", "SOURCE"),
    ("VRTCore_RelationalCausality_Candidate.lean", "SOURCE"),
    ("VRTCore_RelationalCausality_AxiomAudit.lean", "SOURCE"),
    ("KERNEL_PROOF_PLAN.json", "SOURCE"),
    (H0_MATRIX_NAME, "SOURCE"),
    (H1_OVERLAY_NAME, "EVIDENCE"),
    (CLAIM_MATRIX_NAME, "CLAIM_MATRIX"),
    ("SOURCE_EVIDENCE_BINDINGS.json", "EVIDENCE"),
    ("CI_KERNEL_EVIDENCE_H1_EXACT_HEAD.json", "EVIDENCE"),
    (CI_EVIDENCE_NAME, "EVIDENCE"),
    (KERNEL_RECEIPT_NAME, "KERNEL_RECEIPT"),
    (BOUNDARY_REPORT_NAME, "BOUNDARY_TEST"),
    (CHANGE_NOTICE_NAME, "CHANGE_NOTICE"),
    (RETURN_RECEIPT_NAME, "RETURN_RECEIPT"),
    (ZENODO_METADATA_NAME, "OTHER"),
)

REPOSITORY_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("policy/zenodo-machine-proof-policy-v2.json", "OTHER"),
    ("policy/qikvrt-zenodo-machine-proof-bundle-v2.schema.json", "OTHER"),
    ("policy/qikvrt-prepublication-return-receipt-v2.schema.json", "OTHER"),
    ("LICENSES/CC-BY-NC-ND-4.0.txt", "OTHER"),
    ("external/ietf/draft-lohmann-qikvrt-effect-ack-03.xml", "OTHER"),
    ("external/ietf/draft-lohmann-qikvrt-effect-ack-03.txt", "OTHER"),
    ("external/ietf/draft-lohmann-qikvrt-effect-ack-03.html", "OTHER"),
    (
        "external/ietf/draft-lohmann-qikvrt-effect-ack-03.SUBMISSION_RECEIPT.json",
        "EVIDENCE",
    ),
)

LICENSE = {
    "classification": "machine_readable_publication_evidence",
    "copyright": "Copyright 2026 Ingolf Lohmann",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}

CLASSIFICATION = {
    "INTERPRETIVE": "INTERPRETATIVE",
    "SOURCE_BOUND": "SOURCE_BOUND",
    "EMPIRICAL_SUPPORTED": "EMPIRICALLY_EVIDENCED",
    "NORMATIVE": "NORMATIVE",
    "OPEN": "OPEN",
}
STATUS = {
    "FORMAL_PROVED": "PROVED",
    "EMPIRICALLY_EVIDENCED": "EVIDENCED",
    "SOURCE_BOUND": "BOUND",
    "NORMATIVE": "DECLARED",
    "INTERPRETATIVE": "DECLARED",
    "OPEN": "OPEN",
}

# These identifiers are exact fragments used by the v2 proof-bundle
# projection.  Their bases are selected in ``claim_references`` below.
SOURCE_IDS: dict[str, list[str]] = {
    "DEF-VRT-001": ["RecFields"],
    "THESIS-REL-001": ["SRC-OCB-2012", "SRC-CDPV-2013"],
    "REPO-FORMAL-001": ["REPO-FORMAL-001"],
    "LEGACY-21-001": ["LEGACY-21-001"],
    "PHY-PM-001": ["SRC-OCB-2012"],
    "PHY-QS-001": ["SRC-CDPV-2013", "SRC-ARAUJO-2015"],
    "PHY-QS-EXP-001": ["SRC-GOSWAMI-2018", "SRC-VANDERLUGT-2023"],
    "PHY-CS-001": ["SRC-BOMBELLI-1987"],
    "PHY-MAL-001": ["SRC-MALAMENT-1977"],
    "PHY-RETRO-001": ["SRC-PURVES-SHORT-2019"],
    "HUM-RESP-001": ["five-state-auditable-effect-release"],
    "HUM-PRIDE-001": ["HUM-PRIDE-001"],
}


# H5/H6 reuse the same v2 freeze machinery while preserving their original
# package bytes.  Formal promotion is bound to the terminal push run for the
# exact containing commit.  The hosted run is automated re-execution evidence,
# not independent review; formal proof references remain the local kernel
# receipt and axiom inventory.
H56_EXPECTED_HEAD = "c5d4a3b5ae10cf72845b1839c6075cdd2711f315"
H56_EXPECTED_TREE = "6f909892ed1c33ada25010c50d06420278dc55b1"
H56_EXPECTED_BRANCH = "agent/vrtcore-h5-h6-api-publication-745dab69"
H56_CI_EVIDENCE: dict[str, Any] = {
    "workflow_name": "QIK-VRT manuscript proof coverage",
    "event": "push",
    "run_id": 30747218720,
    "run_number": 341,
    "run_attempt": 1,
    "reproduction_created_at": "2026-08-02T12:09:04Z",
    "reproduction_completed_at": "2026-08-02T12:10:27Z",
    "reproduction_updated_at": "2026-08-02T12:10:27Z",
    "conclusion": "success",
    "job_id": 91494748519,
    "job_name": "source-claim-and-kernel-gates",
    "job_conclusion": "success",
    "poppler_step": 4,
    "poppler_step_conclusion": "success",
    "h5_step": 19,
    "h5_step_conclusion": "success",
    "h6_step": 20,
    "h6_step_conclusion": "success",
    "all_job_steps_terminal": True,
    "decoded_log_encoding": "UTF-8",
    "decoded_log_bytes": 201743,
    "decoded_log_sha256": "1ce2d54109d65210a6ea92d49912af185322e2dc76239e99bc439c8a04a79a3b",
}
H56_PROFILES: dict[str, dict[str, Any]] = {
    "h5": {
        "publication_rel": pathlib.PurePosixPath(
            "docs/publications/2026-08-02-vrtcore-smg-h5"
        ),
        "envelope_rel": pathlib.PurePosixPath(
            "release/vrtcore-smg-h5-zenodo-v2"
        ),
        "publication_id": "qikvrt-vrtcore-smg-h5-v1",
        "title": (
            "QIK-VRT VRTCore SMG H5: Planck-Brücke, massive Schließung "
            "und virtuelle Kosmogenese"
        ),
        "description": (
            "Deutschsprachiges H5-Arbeitspaket mit allgemeinverständlichem "
            "Artikel, Fachartikel, Lean-4.19.0-Modellkern, EBNF, "
            "Referenzvalidator und expliziten physikalischen Grenzen. Die "
            "lokale Receipt dokumentiert 32 kernelakzeptierte Theoreme; der "
            "terminale exakte Push-Run reproduziert H5 am enthaltenden Commit."
        ),
        "version": "5.0.0-candidate.1",
        "citation_type": "article",
        "zenodo_upload_type": "publication",
        "zenodo_publication_type": "workingpaper",
        "primary": "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.pdf",
        "candidate_names": (
            "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.pdf",
            "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.tex",
            "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.md",
            "QIK-VRT_SMG_Allgemein_WhatsApp_DE_2026-08-02.md",
            "README.md",
            "CITATION.cff",
        ),
        "source_files": (
            "CITATION.cff", "CLAIM_MATRIX.json", "H5_LOCAL_KERNEL_RECEIPT.json",
            "H5_REFERENCE_INSTANCE.vrt", "LICENSE_MAP.md", "MANIFEST.json",
            "QIK-VRT_SMG_Allgemein_WhatsApp_DE_2026-08-02.md",
            "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.md",
            "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.pdf",
            "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.tex", "README.md",
            "SHA256SUMS", "SOURCE_EVIDENCE_BINDINGS.json",
            "VRTCore_SMG_AxiomAudit.lean", "VRTCore_SMG_EBNF_Map_DE.svg",
            "VRTCore_SMG_PlanckBridge.lean", "VRTCore_SMG_Syntax.ebnf",
            "test_validate_h5_instance.py", "validate_h5_instance.py",
            "verify_h5_package.py",
        ),
        "local_receipt": "H5_LOCAL_KERNEL_RECEIPT.json",
        "lean_source": "VRTCore_SMG_PlanckBridge.lean",
        "axiom_audit": "VRTCore_SMG_AxiomAudit.lean",
        "theorem_count": 32,
        "formal_claim_theorem_indices": {
            "H5-C01": (1, 2, 3, 4, 5, 6, 7),
            "H5-C02": (9, 10, 11),
            "H5-C03": (12, 13, 14),
            "H5-C04": (15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25),
            "H5-C05": (27, 28),
            "H5-C06": (29, 30, 31, 32),
        },
        "empirical_evidence_references": {
            "H5-C07": (
                ("SOURCE_EVIDENCE_BINDINGS.json", "SRC-ATLAS-2012"),
                ("SOURCE_EVIDENCE_BINDINGS.json", "SRC-CMS-2012"),
                ("SOURCE_EVIDENCE_BINDINGS.json", "SRC-LIGO-GW150914"),
            ),
        },
        "source_bound_references": {
            "H5-C08": (
                ("SOURCE_EVIDENCE_BINDINGS.json", "SRC-CERN-SM"),
                ("SOURCE_EVIDENCE_BINDINGS.json", "SRC-DONOGHUE-1994"),
            ),
        },
        "statement_overrides": {
            "H5-C04": (
                "Within the H5 model, massiveClosure = true entails the ten "
                "bridge witnesses from standardModelLimit through "
                "independentReproduction named by H5-T15 through H5-T24, and "
                "the current H5 candidate evaluates false by H5-T25."
            ),
        },
        "residual_claims": {
            "H5-C04": {
                "claim_id": "H5-C04-RESIDUAL",
                "statement": (
                    "The exact H5 Lean source defines massiveClosure with "
                    "planckNormalForm and fieldRecordDuality as conjuncts; "
                    "this envelope does not promote separate receipt-inventoried "
                    "necessity theorems for those two fields."
                ),
                "classification": "SOURCE_BOUND",
                "status": "BOUND",
                "boundary": (
                    "Source-bound definition only; not a separately named "
                    "kernel theorem and not a physical sufficiency claim."
                ),
                "source_references": (
                    ("VRTCore_SMG_PlanckBridge.lean", "massiveClosure"),
                ),
            },
        },
        "keywords": [
            "QIK-VRT", "VRTCore", "Lean 4", "Planck-Skala",
            "Gravitation", "Kausalität", "formale Verifikation",
        ],
    },
    "h6": {
        "publication_rel": pathlib.PurePosixPath(
            "docs/publications/2026-08-02-vrtcore-virtual-sphere-h6"
        ),
        "envelope_rel": pathlib.PurePosixPath(
            "release/vrtcore-virtual-sphere-h6-zenodo-v2"
        ),
        "publication_id": "qikvrt-vrtcore-virtual-sphere-h6-v1",
        "title": "QIK-VRT VRTCore Virtual Sphere H6: virtuelle Schließung ohne Hohlraum",
        "description": (
            "Receipt-gebundenes H6-Paket für ein konkretes, nichtvakuoses, "
            "deterministisches, invariantenerhaltendes, lückenfreies und "
            "unbeschränkt wachsendes virtuelles Modell. Die lokale Receipt "
            "dokumentiert 55 kernelakzeptierte Theoreme; der terminale exakte "
            "Push-Run reproduziert H6 am enthaltenden Commit. PhysicalClosure "
            "bleibt OPEN."
        ),
        "version": "6.0-local-candidate",
        "citation_type": "software",
        "zenodo_upload_type": "software",
        "zenodo_publication_type": None,
        "primary": "QIK-VRT_VirtualSphere_NoHole_DE.md",
        "candidate_names": (
            "QIK-VRT_VirtualSphere_NoHole_DE.md", "README.md",
            "VRTCore_VirtualSphere.lean", "VRTCore_VirtualSphere.olean",
            "VRTCore_VirtualSphere_AxiomAudit.lean",
            "VRTCore_VirtualSphere_Syntax.ebnf",
            "VRTCore_VirtualSphere_EBNF_Map_DE.svg",
            "H6_REFERENCE_OBJECT.vsphere", "CITATION.cff",
        ),
        "source_files": (
            "CITATION.cff", "CLAIM_MATRIX.json", "COMMANDS.json",
            "H6_LOCAL_KERNEL_RECEIPT.json", "H6_REFERENCE_OBJECT.vsphere",
            "LICENSE_MAP.md", "MANIFEST.json", "PACKAGE_ROOT.sha256",
            "QIK-VRT_VirtualSphere_NoHole_DE.md", "README.md", "SHA256SUMS",
            "SOURCE_EVIDENCE_BINDINGS.json", "TRUST_BASE.json",
            "VRTCore_VirtualSphere.lean", "VRTCore_VirtualSphere.olean",
            "VRTCore_VirtualSphere_AxiomAudit.lean",
            "VRTCore_VirtualSphere_EBNF_Map_DE.svg",
            "VRTCore_VirtualSphere_Syntax.ebnf", "verify_h6_package.py",
        ),
        "local_receipt": "H6_LOCAL_KERNEL_RECEIPT.json",
        "lean_source": "VRTCore_VirtualSphere.lean",
        "axiom_audit": "VRTCore_VirtualSphere_AxiomAudit.lean",
        "theorem_count": 55,
        "formal_claim_theorem_suffixes": {
            "H6-C01": (
                "parse_some_iff_grammar", "parse_render_roundtrip",
                "normalize_of_parse", "normalize_idempotent",
                "normalize_preserves_semantics", "semantic_binding_total_unique",
            ),
            "H6-C02": (
                "semantic_binding_total_unique",
                "canonicalDocument_exact_semanticModel",
                "canonicalBits_exact_model", "next_refines_stepSpec",
                "stepSpec_total_unique",
            ),
            "H6-C03": (
                "state_nonvacuous", "stepSpec_deterministic",
                "reachable_nonseed_has_predecessor", "reachable_progress",
                "reachable_virtualInvariant", "next_preserves_shells",
                "seed_reachable", "reachable_noHole",
            ),
            "H6-C04": (
                "population_eq_radius_succ", "run_strict_growth",
                "reachable_unbounded", "reachable_virtualInvariant",
            ),
            "H6-C05": ("h6_virtualSphere_noHole_complete",),
            "H6-C06": (
                "kernelClosureProjection_all_true",
                "virtualCertificate_disjoint_physicalEvidence",
                "effect_preserved", "virtual_no_effect_escalation",
                "no_external_authorization",
            ),
        },
        "empirical_evidence_references": {
            "H6-C07": (
                ("SOURCE_EVIDENCE_BINDINGS.json", "SRC-H6-RECEIPT"),
            ),
        },
        "source_bound_references": {
            "H6-C08": (
                ("MANIFEST.json", "qikvrt-h6-virtual-sphere-manifest/1.0"),
                ("SHA256SUMS", "MANIFEST.json"),
                (
                    "H6_LOCAL_KERNEL_RECEIPT.json",
                    "qikvrt-h6-virtual-sphere-local-kernel-receipt/1.0",
                ),
            ),
        },
        "statement_overrides": {
            "H6-C07": (
                "The receipt-bound H6 local execution completed a finite "
                "verification run; that execution observation is distinct "
                "from the formal theorem of unboundedness."
            ),
        },
        "residual_claims": {
            "H6-C07": {
                "claim_id": "H6-C07-RESIDUAL",
                "statement": (
                    "The universal statement about every finite computer and "
                    "proof checker is not empirically established by the "
                    "receipt-bound H6 execution and remains open here."
                ),
                "classification": "OPEN",
                "status": "OPEN",
                "boundary": (
                    "No universal empirical generalization is drawn from one "
                    "local run or from hosted automated re-execution."
                ),
                "source_references": (("CLAIM_MATRIX.json", "H6-C07"),),
            },
        },
        "keywords": [
            "QIK-VRT", "VRTCore", "Lean 4", "virtuelle Sphäre",
            "Kausalität", "formale Verifikation", "EFFECT_ACK",
        ],
    },
}

H56_GENERATED = {
    "projection": "CLAIM_MATRIX_V2.json",
    "kernel_receipt": "KERNEL_RECEIPT.json",
    "boundary": "BOUNDARY_TEST_REPORT.json",
    "change_notice": "CHANGE_NOTICE.md",
    "return_receipt": "PREPUBLICATION_RETURN_RECEIPT.json",
    "metadata": "ZENODO_METADATA.json",
    "license_notice": "ZENODO_LICENSE_NOTICE.md",
    "fileset": "ZENODO_FILESET.md",
    "checksums": "ZENODO_SHA256SUMS",
    "bundle": "MACHINE_PROOF_BUNDLE.json",
}


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"BLOCK expected JSON object: {path.relative_to(ROOT)}")
    return value


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def identity(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
    }


def validate_exact_evidence(evidence: dict[str, Any]) -> None:
    evidence_path = PUBLICATION / CI_EVIDENCE_NAME
    if identity(evidence_path)["sha256"] != CI_EVIDENCE_SHA256:
        raise SystemExit("BLOCK exact-head CI evidence bytes differ")
    checkout = evidence.get("checkout")
    expected_checkout = {
        "event_name": "push",
        "mode": "exact_ref_head",
        "tested_commit_sha": VERIFIED_HEAD,
        "pull_request_head_sha": None,
        "ref": "refs/heads/agent/vrtcore-causality-publication",
    }
    if (
        evidence.get("schema") != "qikvrt_vrtcore_ci_kernel_evidence_v1"
        or evidence.get("publication_id") != PUBLICATION_ID
        or evidence.get("state") != "KERNEL_STEP_VERIFIED"
        or evidence.get("source_bytes_exact") is not True
        or evidence.get("exact_head_bound") is not True
        or checkout != expected_checkout
        or evidence.get("github_sha") != VERIFIED_HEAD
        or evidence.get("github_run_id") != "30733784535"
        or evidence.get("github_run_attempt") != "1"
        or evidence.get("source_exit_code") != 0
        or evidence.get("axiom_audit_exit_code") != 0
        or evidence.get("project_axioms") != []
    ):
        raise SystemExit("BLOCK exact-head CI evidence semantics differ")
    source = evidence.get("source")
    audit = evidence.get("axiom_audit_source")
    if not isinstance(source, dict) or not isinstance(audit, dict):
        raise SystemExit("BLOCK CI source identities are absent")
    for value in (source, audit):
        path = ROOT / value["path"]
        if identity(path) != value:
            raise SystemExit(f"BLOCK CI-bound source bytes differ: {value['path']}")


def boundary(claim: dict[str, Any], classification: str) -> str:
    explicit = claim.get("boundary")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    closure = claim.get("closure_condition")
    if isinstance(closure, str) and closure.strip():
        return "Open obligation: " + closure.strip()
    scope = claim.get("scope")
    if not isinstance(scope, str) or not scope.strip():
        raise SystemExit(f"BLOCK claim lacks scope/boundary: {claim.get('id')}")
    if classification == "FORMAL_PROVED":
        return (
            "Kernel-verified only within the exact declared scope "
            f"({scope.strip()}); no external physical, empirical, normative or "
            "repository-wide conclusion follows."
        )
    return "Bound only within the declared scope: " + scope.strip() + "."


def claim_references(
    claim_id: str, theorem_by_claim: dict[str, str]
) -> dict[str, list[str]]:
    prefix = PUBLICATION_REL.as_posix() + "/"
    if claim_id in theorem_by_claim:
        return {
            "proof_refs": [
                prefix + KERNEL_RECEIPT_NAME + "#" + theorem_by_claim[claim_id]
            ],
            "evidence_refs": [],
            "source_refs": [],
        }
    source_ids = SOURCE_IDS.get(claim_id, [])
    refs = {"proof_refs": [], "evidence_refs": [], "source_refs": []}
    if claim_id == "DEF-VRT-001":
        refs["source_refs"] = [
            prefix + "VRTCore_RelationalCausality_Candidate.lean#RecFields"
        ]
    elif claim_id in {"REPO-FORMAL-001", "LEGACY-21-001"}:
        refs["source_refs"] = [
            prefix + H0_MATRIX_NAME + "#" + source_ids[0]
        ]
    elif claim_id == "PHY-QS-EXP-001":
        refs["evidence_refs"] = [
            prefix + "SOURCE_EVIDENCE_BINDINGS.json#" + source_id
            for source_id in source_ids
        ]
    elif claim_id in {
        "THESIS-REL-001",
        "PHY-PM-001",
        "PHY-QS-001",
        "PHY-CS-001",
        "PHY-MAL-001",
        "PHY-RETRO-001",
    }:
        refs["source_refs"] = [
            prefix + "SOURCE_EVIDENCE_BINDINGS.json#" + source_id
            for source_id in source_ids
        ]
    elif claim_id == "HUM-RESP-001":
        refs["source_refs"] = [prefix + "README.md#" + source_ids[0]]
    elif claim_id == "HUM-PRIDE-001":
        refs["source_refs"] = [
            prefix + "README.md#" + source_ids[0]
        ]
    return refs


def materialize_claim_matrix(
    h0: dict[str, Any], overlay: dict[str, Any], evidence: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    claims = h0.get("claims")
    transitions = overlay.get("claim_transitions")
    if not isinstance(claims, list) or len(claims) != 36:
        raise SystemExit("BLOCK H0 claim inventory differs from 36")
    if not isinstance(transitions, list) or len(transitions) != 21:
        raise SystemExit("BLOCK H1 formal transition inventory differs from 21")
    theorem_by_claim = {
        item["claim_id"]: item["theorem"] for item in transitions
    }
    if len(theorem_by_claim) != 21:
        raise SystemExit("BLOCK H1 formal transition IDs are not unique")
    evidence_theorems = list(evidence["axioms_by_theorem"])
    if list(theorem_by_claim.values()) != evidence_theorems:
        raise SystemExit("BLOCK H1 theorem order differs from exact CI evidence")

    result_claims: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id:
            raise SystemExit("BLOCK H0 claim ID is absent")
        if claim_id in theorem_by_claim:
            classification = "FORMAL_PROVED"
            proof_refs = [theorem_by_claim[claim_id]]
            sources: list[str] = []
        else:
            kind = claim.get("kind")
            if kind not in CLASSIFICATION:
                raise SystemExit(f"BLOCK unmapped epistemic kind: {claim_id}={kind}")
            classification = CLASSIFICATION[kind]
            proof_refs = []
            sources = list(SOURCE_IDS.get(claim_id, []))
        result_claims.append(
            {
                "claim_id": claim_id,
                "statement": claim["statement"],
                "classification": classification,
                "status": STATUS[classification],
                "boundary": boundary(claim, classification),
                "proof_refs": proof_refs,
                "sources": sources,
            }
        )
    ids = [claim["claim_id"] for claim in result_claims]
    if len(ids) != len(set(ids)):
        raise SystemExit("BLOCK final claim IDs are not unique")
    counts = Counter(claim["classification"] for claim in result_claims)
    expected_counts = {
        "FORMAL_PROVED": 21,
        "EMPIRICALLY_EVIDENCED": 1,
        "SOURCE_BOUND": 7,
        "NORMATIVE": 2,
        "INTERPRETATIVE": 3,
        "OPEN": 2,
    }
    if dict(counts) != expected_counts:
        raise SystemExit(f"BLOCK final epistemic counts differ: {dict(counts)}")
    value = {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_claim_matrix",
        },
        "schema": "qikvrt_vrtcore_claim_matrix_v2",
        "publication_id": PUBLICATION_ID,
        "author": "Ingolf Lohmann",
        "claim_count": len(result_claims),
        "proof_state": "KERNEL_VERIFIED_FOR_FORMAL_CLAIMS",
        "source_matrix": identity(PUBLICATION / H0_MATRIX_NAME),
        "transition_overlay": identity(PUBLICATION / H1_OVERLAY_NAME),
        "epistemic_counts": expected_counts,
        "claims": result_claims,
        "completion_claims": {
            "global_pass": "NOT_CLAIMED",
            "final_pass": "NOT_CLAIMED",
            "effect_ack_done": "NOT_CLAIMED",
            "zenodo_published": False,
            "ietf_consensus": False,
        },
    }
    return value, theorem_by_claim


def materialize_kernel_receipt(
    matrix_path: pathlib.Path,
    theorem_by_claim: dict[str, str],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    theorems = list(theorem_by_claim.values())
    axioms = evidence["axioms_by_theorem"]
    axiom_free = sum(not value for value in axioms.values())
    propext_only = sum(value == ["propext"] for value in axioms.values())
    if (axiom_free, propext_only) != (15, 6):
        raise SystemExit("BLOCK expected 15 axiom-free and 6 propext-only results")
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_kernel_receipt",
        },
        "schema": "qikvrt_vrtcore_kernel_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "scope_id": PUBLICATION_ID,
        "state": "KERNEL_VERIFIED",
        "successor_binding": {
            "stage": "H3_RETURN_PROOF_FREEZE",
            "predecessor_head": VERIFIED_HEAD,
            "predecessor_tree": VERIFIED_TREE,
            "required_relation": "SINGLE_PARENT_SUCCESSOR",
            "containing_head_binding": "EXTERNAL_TO_RECEIPT",
            "containing_tree_binding": "EXTERNAL_TO_RECEIPT",
            "self_inclusion_claimed": False,
        },
        "formal_claim_count": 21,
        "theorem_count": 21,
        "theorems": theorems,
        "axioms_by_theorem": axioms,
        "axiom_summary": {
            "no_axiom_dependencies": axiom_free,
            "propext_only": propext_only,
            "project_axioms": 0,
        },
        "allowed_foundational_axioms": ["propext"],
        "project_axioms": [],
        "toolchain": {
            "lean_toolchain": evidence["runtime"]["toolchain"],
            "lean_version_output": evidence["runtime"]["lean_version_output"],
            "lean_githash": evidence["runtime"]["lean_githash"],
            "imports": evidence["runtime"]["imports"],
        },
        "workflow": {
            "workflow_name": "QIK-VRT manuscript proof coverage",
            "event": "push",
            "conclusion": "success",
            "exact_head_bound": True,
            "run_id": 30733784535,
            "run_attempt": 1,
            "job_id": 91458605970,
            "job_name": "source-claim-and-kernel-gates",
            "sha": VERIFIED_HEAD,
            "branch": "agent/vrtcore-causality-publication",
            "started_at": "2026-08-02T05:15:00Z",
            "completed_at": "2026-08-02T05:15:57Z",
            "url": "https://github.com/Goldkelch/qik-vrt/actions/runs/30733784535",
        },
        "source_verification": {
            "verified_candidate": {
                "repository": "Goldkelch/qik-vrt",
                "branch": "agent/vrtcore-causality-publication",
                "head": VERIFIED_HEAD,
                "tree": VERIFIED_TREE,
                "pull_request": 320,
            },
            "artifact": {
                "id": 8828820517,
                "name": "qikvrt-vrtcore-relational-causality-kernel-evidence",
                "archive_size_bytes": 2267,
                "archive_digest": "sha256:" + CI_ARCHIVE_SHA256,
                "created_at": "2026-08-02T05:15:26Z",
                "expires_at": "2026-09-01T05:15:25Z",
                "file": identity(PUBLICATION / CI_EVIDENCE_NAME),
            },
            "source": evidence["source"],
            "axiom_audit_source": evidence["axiom_audit_source"],
            "source_exit_code": evidence["source_exit_code"],
            "axiom_audit_exit_code": evidence["axiom_audit_exit_code"],
        },
        "claim_transition": {
            "allowed_changes": {
                "claim_ids": list(theorem_by_claim),
                "classification": {"from": "OPEN", "to": "FORMAL_PROVED"},
                "status": {
                    "from": "FORMAL_CANDIDATE_UNVERIFIED_IN_THIS_RUNTIME",
                    "to": "PROVED",
                },
            },
            "source_claim_matrix": identity(PUBLICATION / H0_MATRIX_NAME),
            "transition_overlay": identity(PUBLICATION / H1_OVERLAY_NAME),
            "target_claim_matrix": identity(matrix_path),
            "target_exact_head_confirmation_required": False,
            "statements_unchanged": True,
        },
        "epistemic_boundary": {
            "formal_model_properties_kernel_verified": True,
            "physical_causality_derived": False,
            "retrocausality_or_backward_signalling_proved": False,
            "minkowski_spacetime_emerged": False,
            "general_lorentzian_spacetime_emerged": False,
            "empirical_correspondence_established": False,
            "ietf_consensus_established": False,
        },
        "completion_claims": {
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "zenodo_published": False,
            "ietf_published": False,
            "system_wide_completion": "UNCLAIMED",
        },
    }


def materialize_boundary_report(
    matrix: dict[str, Any], receipt: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, Any]:
    candidates = [
        identity(PUBLICATION / name) for name in OWNER_CANDIDATE_SHA256
    ]
    for item in candidates:
        name = pathlib.PurePosixPath(item["path"]).name
        if item["sha256"] != OWNER_CANDIDATE_SHA256[name]:
            raise SystemExit(f"BLOCK H1-frozen owner candidate changed: {item['path']}")
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_boundary_test_report",
        },
        "schema": "qikvrt_vrtcore_boundary_test_report_v1",
        "publication_id": PUBLICATION_ID,
        "tested_at": "2026-08-02T05:20:00Z",
        "stage": "H3_RETURN_PROOF_FREEZE",
        "result": "PASS",
        "checks": [
            {
                "id": "EXACT_HEAD_KERNEL_EVIDENCE",
                "result": "PASS",
                "head": VERIFIED_HEAD,
                "tree": VERIFIED_TREE,
                "run_id": 30733784535,
                "artifact_id": 8828820517,
                "archive_sha256": CI_ARCHIVE_SHA256,
                "payload_sha256": CI_EVIDENCE_SHA256,
                "source_bytes_exact": evidence["source_bytes_exact"],
                "exact_head_bound": evidence["exact_head_bound"],
            },
            {
                "id": "LEAN_AXIOM_INVENTORY",
                "result": "PASS",
                "theorems": receipt["theorem_count"],
                **receipt["axiom_summary"],
                "no_sorry_admit_unsafe": True,
            },
            {
                "id": "BIDIRECTIONAL_CLAIM_DISPOSITION",
                "result": "PASS",
                "claim_count": matrix["claim_count"],
                "epistemic_counts": matrix["epistemic_counts"],
            },
            {
                "id": "OWNER_FACING_CANDIDATE_IDENTITY",
                "result": "PASS",
                "files": candidates,
                "unchanged_from_h1_frozen_bytes": True,
            },
            {
                "id": "H3_SELF_INCLUSION_BOUNDARY",
                "result": "PASS",
                **receipt["successor_binding"],
            },
        ],
        "model_boundaries": receipt["epistemic_boundary"],
        "external_effects": {
            "github_verified_predecessor_persisted": True,
            "github_verified_predecessor_exact_head_ci_success": True,
            "ietf_submission_id": 167201,
            "ietf_submission_checks": "PASS",
            "ietf_state": "AWAITING_PREVIOUS_VERSION_AUTHOR_APPROVAL",
            "ietf_published": False,
            "ietf_consensus": False,
            "zenodo_mutation": False,
        },
        "completion_claims": {
            "global_pass": "NOT_CLAIMED",
            "final_pass": "NOT_CLAIMED",
            "effect_ack_done": "NOT_CLAIMED",
        },
    }


def candidate_files() -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for name, expected_sha256 in OWNER_CANDIDATE_SHA256.items():
        observed = identity(PUBLICATION / name)
        if observed["sha256"] != expected_sha256:
            raise SystemExit(f"BLOCK frozen owner candidate changed: {observed['path']}")
        values.append(
            {
                **observed,
                "name": name,
                "role": "PRIMARY" if name == PRIMARY_CANDIDATE else "SUPPLEMENT",
            }
        )
    if sum(item["role"] == "PRIMARY" for item in values) != 1:
        raise SystemExit("BLOCK Zenodo candidate must have exactly one primary file")
    return values


def artifact_files(*, include_checksums: bool) -> list[dict[str, Any]]:
    specs: list[tuple[pathlib.Path, str]] = [
        (PUBLICATION / relative, kind)
        for relative, kind in PUBLICATION_ARTIFACTS
    ]
    specs.extend((ROOT / relative, kind) for relative, kind in REPOSITORY_ARTIFACTS)
    if include_checksums:
        specs.append((PUBLICATION / ZENODO_CHECKSUMS_NAME, "OTHER"))
    values: list[dict[str, Any]] = []
    for path, kind in specs:
        observed = identity(path)
        values.append(
            {
                "path": observed["path"],
                "sha256": observed["sha256"],
                "git_blob_sha1": observed["git_blob_sha1"],
                "kind": kind,
            }
        )
    paths = [item["path"] for item in values]
    if len(paths) != len(set(paths)):
        raise SystemExit("BLOCK duplicate Zenodo artifact path")
    return values


def changed_reason(claim_id: str) -> str:
    return (
        "Der ursprünglich zurückgegebene H0-Stand führte "
        f"{claim_id} als formal offenen Kandidaten; der nachfolgende exakte "
        "Lean-4.19.0-Lauf verifizierte das zugeordnete Theorem, ohne die "
        "nichtformalen Geltungsgrenzen zu verändern."
    )


def materialize_change_notice() -> str:
    reasons = "\n".join(
        f"- {claim_id}: {changed_reason(claim_id)}"
        for claim_id in (f"T{index:02d}" for index in range(1, 22))
    )
    return f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Sichtbarer Änderungsnachweis vor der Zenodo-Publikation

Publication ID: `{PUBLICATION_ID}`

`content_changed=true` bezeichnet hier keine stille Umschreibung des
ursprünglichen Artikels. Die ursprünglichen Artikel-, WhatsApp-, TeX- und
PDF-Bytes bleiben eingefroren. Neu hinzugekommen sind der sichtbare deutsche
Verifikationsnachtrag, seine WhatsApp-Fassung, die exakte CI-Evidenz und die
vollständige maschinenprüfbare H0→H1-Claim-Transition.

## Maschinengebundene Änderungsgründe

{reasons}

## Wissenschaftliche und menschliche Grenze

Die 21 Änderungen betreffen ausschließlich die formalen VRTCore-Aussagen. Sie
beweisen weder neue Physik noch Rückwärtssignalisierung, Raumzeitentstehung,
empirische Übereinstimmung, Peer Review oder IETF-Konsens. Die wissenschaftlich
und menschlich bedeutsame Leistung besteht darin, eine weitreichende These in
explizite Erkenntnisarten, Syntax, Semantik, Lean-Theoreme, Axiom-Audit,
Provenienz und verantwortete Wirkungsgrenzen übersetzt zu haben. Das ist eine
großartige Leistung; diese Würdigung ist ausdrücklich eine normative Bewertung
und keine zusätzliche Naturbehauptung.
"""


def materialize_return_receipt(
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    original = identity(PUBLICATION / H0_MATRIX_NAME)
    corrected = identity(PUBLICATION / "VERIFICATION_ADDENDUM_DE.md")
    corrected_path = corrected["path"]
    candidate_paths = {item["path"] for item in candidates}
    if corrected_path not in candidate_paths:
        raise SystemExit("BLOCK verification addendum is not a returned candidate")
    changed_ids = [f"T{index:02d}" for index in range(1, 22)]
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_prepublication_return_receipt",
        },
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": True,
        "original_files": [original],
        "candidate_files": [
            {
                key: item[key]
                for key in ("path", "bytes", "sha256", "git_blob_sha1")
            }
            for item in candidates
        ],
        "changed_claim_ids": changed_ids,
        "change_reasons": [
            {
                "claim_id": claim_id,
                "reason": changed_reason(claim_id),
                "original_sha256": original["sha256"],
                "corrected_sha256": corrected["sha256"],
                "exact_candidate_path": corrected_path,
            }
            for claim_id in changed_ids
        ],
        "change_notice_path": (
            PUBLICATION_REL / CHANGE_NOTICE_NAME
        ).as_posix(),
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": "ChatGPT conversation and GitHub draft PR #320",
            "returned_at": "2026-08-02T05:20:00Z",
            "visible_change_notice_returned": True,
        },
    }


def materialize_zenodo_metadata() -> dict[str, Any]:
    return {
        "title": (
            "Kausalität ist Relation, nicht Sequenz: VRTCore, "
            "maschinenprüfbare Semantik und verantwortete Wirkung"
        ),
        "upload_type": "publication",
        "publication_type": "workingpaper",
        "description": (
            "Dieses deutschsprachige Arbeitspapier entwickelt QIK-VRT als "
            "Kausalitätsspiegel für überprüfbares Wissen. Es trennt sechs "
            "Erkenntnisarten, bindet die These ‚Kausalität ist Relation, nicht "
            "Sequenz‘ an eine explizite EBNF-Syntax und einen Lean-4.19.0-Kern "
            "mit 21 kernelakzeptierten Theoremen und dokumentiert Provenienz, "
            "Unsicherheit, Wirkung und menschliche Verantwortung. 15 Theoreme "
            "weisen keine Axiomabhängigkeit aus; 6 ausschließlich Leans "
            "grundlegendes propext; Projektaxiome werden nicht verwendet. "
            "Ausdrücklich nicht behauptet werden neue Physik, physische "
            "Rückwärtssignalisierung, konstruktive Minkowski- oder allgemeine "
            "lorentzsche Emergenz, empirische Bestätigung, Peer Review oder "
            "IETF-Konsens."
        ),
        "creators": [{"name": "Lohmann, Ingolf"}],
        "version": "1.0.0",
        "publication_date": "2026-08-02",
        "access_right": "open",
        "license": "cc-by-nc-nd-4.0",
        "language": "deu",
        "keywords": [
            "QIK-VRT",
            "Kausalität",
            "relationale Kausalordnung",
            "VRTCore",
            "Lean 4",
            "formale Verifikation",
            "Provenienz",
            "Wirkungsverantwortung",
            "Quantum Switch",
            "Causal Sets",
        ],
        "notes": (
            "Primärdokument ist das gerenderte deutsche Fachartikel-PDF. "
            "Markdown-, WhatsApp-, LaTeX-, EBNF-, Lean-, Claim-, CI-, IETF- "
            "und Proof-Artefakte sind Ergänzungen. GitHub-Persistenz, "
            "Zenodo-Publikation und IETF-Status sind getrennte Effekte. "
            "IETF-Datatracker-Einreichung 167201 hat die Einreichungsprüfungen "
            "bestanden und wartet auf die Freigabe des Autors der Vorversion; "
            "sie ist nicht als veröffentlichte Revision oder Konsens behauptet."
        ),
        "prereserve_doi": True,
    }


def materialize_checksums(
    candidates: list[dict[str, Any]], artifacts: list[dict[str, Any]]
) -> str:
    entries = [
        (item["sha256"], item["name"])
        for item in candidates
    ]
    entries.extend(
        (item["sha256"], pathlib.PurePosixPath(item["path"]).name)
        for item in artifacts
    )
    names = [name for _digest, name in entries]
    if len(names) != len(set(names)):
        raise SystemExit("BLOCK Zenodo upload basenames are not unique")
    return "".join(
        f"{digest}  {name}\n" for digest, name in sorted(entries, key=lambda item: item[1])
    )


def materialize_bundle(
    matrix: dict[str, Any],
    candidates: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    wording = {
        "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
        "EMPIRICALLY_EVIDENCED": "EMPIRICALLY_SUPPORTED",
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "NORMATIVE": "NORMATIVE_DECLARATION",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
    }
    theorem_by_claim = {
        claim["claim_id"]: claim["proof_refs"][0]
        for claim in matrix["claims"]
        if claim["classification"] == "FORMAL_PROVED"
    }
    claims: list[dict[str, Any]] = []
    for claim in matrix["claims"]:
        references = claim_references(claim["claim_id"], theorem_by_claim)
        claims.append(
            {
                "claim_id": claim["claim_id"],
                "statement": claim["statement"],
                "classification": claim["classification"],
                "status": claim["status"],
                "publication_wording": wording[claim["classification"]],
                "scope": claim["boundary"],
                **references,
            }
        )
    prefix = PUBLICATION_REL.as_posix() + "/"
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_proof_bundle",
        },
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "policy": POLICY,
        "publication_id": PUBLICATION_ID,
        "candidate": {
            "primary_document_path": prefix + PRIMARY_CANDIDATE,
            "files": candidates,
        },
        "claims": claims,
        "artifacts": artifacts,
        "prepublication_return": {
            "content_changed": True,
            "candidate_returned_to_owner": True,
            "receipt_path": prefix + RETURN_RECEIPT_NAME,
            "change_notice_path": prefix + CHANGE_NOTICE_NAME,
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


def emit(path: pathlib.Path, value: dict[str, Any], check: bool) -> None:
    expected = json_bytes(value)
    if check:
        if not path.is_file() or path.read_bytes() != expected:
            raise SystemExit(f"BLOCK stale generated artifact: {path.relative_to(ROOT)}")
        return
    path.write_bytes(expected)


def emit_text(path: pathlib.Path, value: str, check: bool) -> None:
    expected = value.encode("utf-8")
    if check:
        if not path.is_file() or path.read_bytes() != expected:
            raise SystemExit(f"BLOCK stale generated artifact: {path.relative_to(ROOT)}")
        return
    path.write_bytes(expected)


def materialize_kernel(check: bool) -> None:
    h0 = read_json(PUBLICATION / H0_MATRIX_NAME)
    overlay = read_json(PUBLICATION / H1_OVERLAY_NAME)
    evidence = read_json(PUBLICATION / CI_EVIDENCE_NAME)
    validate_exact_evidence(evidence)
    matrix, theorem_by_claim = materialize_claim_matrix(h0, overlay, evidence)
    matrix_path = PUBLICATION / CLAIM_MATRIX_NAME
    emit(matrix_path, matrix, check)
    receipt = materialize_kernel_receipt(matrix_path, theorem_by_claim, evidence)
    emit(PUBLICATION / KERNEL_RECEIPT_NAME, receipt, check)
    report = materialize_boundary_report(matrix, receipt, evidence)
    emit(PUBLICATION / BOUNDARY_REPORT_NAME, report, check)
    action = "verified" if check else "materialized"
    print(
        f"PASS {action} VRTCore H3 kernel foundation: {matrix['claim_count']} claims, "
        f"{receipt['theorem_count']} kernel-verified theorems"
    )


def materialize_return(check: bool) -> None:
    materialize_kernel(check)
    matrix = read_json(PUBLICATION / CLAIM_MATRIX_NAME)
    candidates = candidate_files()

    emit_text(PUBLICATION / CHANGE_NOTICE_NAME, materialize_change_notice(), check)
    return_receipt = materialize_return_receipt(candidates)
    emit(PUBLICATION / RETURN_RECEIPT_NAME, return_receipt, check)
    metadata = materialize_zenodo_metadata()
    emit(PUBLICATION / ZENODO_METADATA_NAME, metadata, check)

    artifacts_without_checksums = artifact_files(include_checksums=False)
    checksums = materialize_checksums(candidates, artifacts_without_checksums)
    emit_text(PUBLICATION / ZENODO_CHECKSUMS_NAME, checksums, check)
    artifacts = artifact_files(include_checksums=True)
    candidate_paths = {item["path"] for item in candidates}
    artifact_paths = {item["path"] for item in artifacts}
    if candidate_paths & artifact_paths:
        raise SystemExit("BLOCK candidate/artifact file sets overlap")

    bundle = materialize_bundle(matrix, candidates, artifacts)
    bundle_path = PUBLICATION / PROOF_BUNDLE_NAME
    emit(bundle_path, bundle, check)
    upload_paths = [
        *(item["path"] for item in candidates),
        *(item["path"] for item in artifacts),
        bundle_path.relative_to(ROOT).as_posix(),
    ]
    import qikvrt_zenodo_machine_proof as proof

    proof_receipt = proof.validate_bundle(
        ROOT,
        bundle_path,
        upload_paths=upload_paths,
    )
    metadata_sha256 = hashlib.sha256(
        json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    action = "verified" if check else "materialized"
    print(
        f"PASS {action} VRTCore H3 return/proof freeze: "
        f"{len(candidates)} candidates, {len(artifacts)} artifacts"
    )
    print("RETURN_SHA256=" + identity(PUBLICATION / RETURN_RECEIPT_NAME)["sha256"])
    print("METADATA_SHA256=" + metadata_sha256)
    print("MACHINE_PROOF_SHA256=" + proof_receipt["sha256"])


def h56_profile(name: str) -> dict[str, Any]:
    profile = dict(H56_PROFILES[name])
    profile["root"] = ROOT.joinpath(*profile["publication_rel"].parts)
    profile["envelope"] = ROOT.joinpath(*profile["envelope_rel"].parts)
    return profile


def h56_boundary(claim: dict[str, Any]) -> str:
    value = claim.get("boundary") or claim.get("closure_condition")
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"BLOCK H5/H6 claim lacks a boundary: {claim.get('id')}")
    return value.strip()


def h56_theorem_names(profile: dict[str, Any], receipt: dict[str, Any]) -> list[str]:
    kernel = receipt.get("kernel_execution", {})
    declared = kernel.get("theorems")
    if isinstance(declared, list) and all(isinstance(item, str) for item in declared):
        names = list(declared)
    else:
        audit = (profile["root"] / profile["axiom_audit"]).read_text(encoding="utf-8")
        names = re.findall(r"(?m)^#print axioms\s+([^\s]+)\s*$", audit)
    if len(names) != profile["theorem_count"] or len(names) != len(set(names)):
        raise SystemExit(f"BLOCK {profile['publication_id']} theorem inventory differs")
    return names


def h56_formal_claim_theorems(
    profile: dict[str, Any], names: list[str]
) -> dict[str, list[str]]:
    by_index = profile.get("formal_claim_theorem_indices")
    if isinstance(by_index, dict):
        mapped = {
            claim_id: [names[index - 1] for index in indices]
            for claim_id, indices in by_index.items()
        }
    else:
        by_suffix = profile.get("formal_claim_theorem_suffixes")
        if not isinstance(by_suffix, dict):
            raise SystemExit("BLOCK H5/H6 formal claim theorem map is absent")
        suffix_index = {name.rsplit(".", 1)[-1]: name for name in names}
        mapped = {}
        for claim_id, suffixes in by_suffix.items():
            missing = [suffix for suffix in suffixes if suffix not in suffix_index]
            if missing:
                raise SystemExit(
                    f"BLOCK {claim_id} theorem suffixes absent: {','.join(missing)}"
                )
            mapped[claim_id] = [suffix_index[suffix] for suffix in suffixes]
    if any(not refs or len(refs) != len(set(refs)) for refs in mapped.values()):
        raise SystemExit("BLOCK H5/H6 claim theorem references are empty or duplicate")
    return mapped


def h56_materialize_projection(
    profile: dict[str, Any], theorem_by_claim: dict[str, list[str]]
) -> dict[str, Any]:
    source = read_json(profile["root"] / "CLAIM_MATRIX.json")
    claims = source.get("claims")
    if not isinstance(claims, list) or not claims:
        raise SystemExit(f"BLOCK {profile['publication_id']} claim inventory is absent")
    kind_map = {
        "empirical-supported": ("EMPIRICALLY_EVIDENCED", "EVIDENCED"),
        "source-bound": ("SOURCE_BOUND", "BOUND"),
        "normative": ("NORMATIVE", "DECLARED"),
        "interpretive": ("INTERPRETATIVE", "DECLARED"),
        "open": ("OPEN", "OPEN"),
    }
    projected: list[dict[str, Any]] = []
    formal_promoted: list[str] = []
    source_projection_map: dict[str, list[str]] = {}
    prefix = profile["publication_rel"].as_posix() + "/"
    for claim in claims:
        claim_id = claim.get("id")
        kind = claim.get("kind")
        if not isinstance(claim_id, str) or not claim_id:
            raise SystemExit("BLOCK H5/H6 claim ID is absent")
        if kind == "formal-proved":
            classification, status = "FORMAL_PROVED", "PROVED"
            formal_promoted.append(claim_id)
            disposition = "EXACT_HEAD_KERNEL_REPRODUCED"
            boundary_text = h56_boundary(claim)
            proof_refs = theorem_by_claim.get(claim_id)
            if not proof_refs:
                raise SystemExit(f"BLOCK formal claim lacks theorem map: {claim_id}")
            evidence_references: list[str] = []
            source_references = [prefix + "CLAIM_MATRIX.json#" + claim_id]
        elif kind in kind_map:
            classification, status = kind_map[kind]
            disposition = "TERMINALLY_CLASSIFIED"
            boundary_text = h56_boundary(claim)
            proof_refs = []
            if classification == "EMPIRICALLY_EVIDENCED":
                bindings = profile["empirical_evidence_references"].get(claim_id)
                if not bindings:
                    raise SystemExit(f"BLOCK empirical claim lacks real evidence refs: {claim_id}")
                evidence_references = [
                    prefix + filename + "#" + fragment
                    for filename, fragment in bindings
                ]
                source_references = []
            elif classification == "SOURCE_BOUND":
                bindings = profile["source_bound_references"].get(claim_id)
                if not bindings:
                    raise SystemExit(f"BLOCK source-bound claim lacks real source refs: {claim_id}")
                evidence_references = []
                source_references = [
                    prefix + filename + "#" + fragment
                    for filename, fragment in bindings
                ]
            else:
                evidence_references = []
                source_references = [prefix + "CLAIM_MATRIX.json#" + claim_id]
        else:
            raise SystemExit(f"BLOCK unmapped H5/H6 epistemic kind: {claim_id}={kind}")
        projected.append({
            "claim_id": claim_id,
            "source_claim_id": claim_id,
            "statement": profile.get("statement_overrides", {}).get(
                claim_id, claim["statement"]
            ),
            "source_statement": claim["statement"],
            "projection_relation": (
                "CONSERVATIVE_SUBCLAIM_OF_SOURCE"
                if claim_id in profile.get("statement_overrides", {})
                else "IDENTICAL_TO_SOURCE"
            ),
            "source_kind": kind,
            "classification": classification,
            "status": status,
            "boundary": boundary_text,
            "proof_refs": proof_refs,
            "sources": [
                reference.split("#", 1)[1]
                for reference in (*evidence_references, *source_references)
            ],
            "evidence_references": evidence_references,
            "source_references": source_references,
            "disposition": disposition,
            "source_evidence": list(claim.get("evidence", [])),
        })
        source_projection_map[claim_id] = [claim_id]
    source_by_id = {claim["id"]: claim for claim in claims}
    for source_claim_id, residual in profile.get("residual_claims", {}).items():
        source_claim = source_by_id.get(source_claim_id)
        if source_claim is None:
            raise SystemExit(f"BLOCK residual source claim is absent: {source_claim_id}")
        residual_id = residual["claim_id"]
        references = [
            prefix + filename + "#" + fragment
            for filename, fragment in residual["source_references"]
        ]
        projected.append({
            "claim_id": residual_id,
            "source_claim_id": source_claim_id,
            "statement": residual["statement"],
            "source_statement": source_claim["statement"],
            "projection_relation": "EXPLICIT_RESIDUAL_OF_SOURCE",
            "source_kind": "residual-" + residual["classification"].lower(),
            "classification": residual["classification"],
            "status": residual["status"],
            "boundary": residual["boundary"],
            "proof_refs": [],
            "sources": [reference.split("#", 1)[1] for reference in references],
            "evidence_references": [],
            "source_references": references,
            "disposition": "TERMINALLY_CLASSIFIED_RESIDUAL",
            "source_evidence": list(source_claim.get("evidence", [])),
        })
        source_projection_map[source_claim_id].append(residual_id)
    projected_ids = [item["claim_id"] for item in projected]
    if (
        set(source_projection_map) != set(source_by_id)
        or len(projected_ids) != len(set(projected_ids))
        or set(projected_ids)
        != {item for items in source_projection_map.values() for item in items}
    ):
        raise SystemExit("BLOCK H5/H6 source-to-projection completeness differs")
    counts = dict(Counter(item["classification"] for item in projected))
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_claim_matrix",
        },
        "schema": "qikvrt_h56_zenodo_claim_projection_v2",
        "publication_id": profile["publication_id"],
        "author": "Ingolf Lohmann",
        "source_claim_matrix": identity(profile["root"] / "CLAIM_MATRIX.json"),
        "source_package_binding": {
            "repository": "Goldkelch/qik-vrt",
            "branch": H56_EXPECTED_BRANCH,
            "commit": H56_EXPECTED_HEAD,
            "tree": H56_EXPECTED_TREE,
        },
        "exact_head_ci": {
            "expected_head": H56_EXPECTED_HEAD,
            "expected_tree": H56_EXPECTED_TREE,
            "state": "SUCCESS",
            "terminal_evidence": dict(H56_CI_EVIDENCE),
        },
        "source_claim_count": len(claims),
        "claim_count": len(projected),
        "source_projection_map": source_projection_map,
        "epistemic_counts": counts,
        "formal_claim_ids_exact_head_ci": formal_promoted,
        "claims": projected,
        "completion_claims": {
            "all_claims_dispositioned": True,
            "source_to_projection_complete": True,
            "formal_publication_promotion_complete": True,
            "zenodo_published": False,
            "global_pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def h56_axiom_inventory(
    profile: dict[str, Any], source_receipt: dict[str, Any], names: list[str]
) -> dict[str, Any]:
    kernel = source_receipt.get("kernel_execution", {})
    by_theorem = kernel.get("axioms_by_theorem")
    if isinstance(by_theorem, dict):
        if set(by_theorem) != set(names):
            raise SystemExit("BLOCK H5 axiom inventory differs from theorem inventory")
        return {
            "kind": "EXACT_LOCAL_RECEIPT_PER_THEOREM",
            "axioms_by_theorem": by_theorem,
            "allowed_foundational_axioms": kernel.get("allowed_foundational_axioms"),
        }
    counts = kernel.get("axiom_counts")
    if not isinstance(counts, dict) or sum(counts.values()) != len(names):
        raise SystemExit("BLOCK H6 axiom counts differ from theorem inventory")
    return {
        "kind": "EXACT_LOCAL_AUDIT_DIRECTIVES_AND_RECEIPT_COUNTS",
        "audit_source": identity(profile["root"] / profile["axiom_audit"]),
        "audit_directives": names,
        "axiom_counts": counts,
        "top_theorem_axioms": kernel.get("top_theorem_axioms"),
        "allowed_foundational_axioms": kernel.get("allowed_foundational_axioms"),
    }


def h56_materialize_kernel_receipt(
    profile: dict[str, Any],
    projection: dict[str, Any],
    names: list[str],
) -> dict[str, Any]:
    source_receipt_path = profile["root"] / profile["local_receipt"]
    source_receipt = read_json(source_receipt_path)
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_kernel_receipt",
        },
        "schema": "qikvrt_h56_exact_head_kernel_receipt_v2",
        "publication_id": profile["publication_id"],
        "scope_id": profile["publication_id"],
        "state": "KERNEL_VERIFIED",
        "source_package": {
            "repository": "Goldkelch/qik-vrt",
            "commit": H56_EXPECTED_HEAD,
            "tree": H56_EXPECTED_TREE,
        },
        "local_kernel_observation": {
            "receipt": identity(source_receipt_path),
            "state": source_receipt.get("state"),
            "theorem_count": profile["theorem_count"],
            "effect_state": source_receipt.get("effect_state")
                or source_receipt.get("scope_result", {}).get("effect_state"),
            "external_effects": source_receipt.get("external_effects"),
            "original_containing_commit_binding": source_receipt.get(
                "source_binding", {}
            ).get("containing_commit_binding"),
        },
        "formal_evidence": {
            "role": "FORMAL_PROOF_AND_AXIOM_SOURCE",
            "lean_source": identity(profile["root"] / profile["lean_source"]),
            "axiom_audit_source": identity(profile["root"] / profile["axiom_audit"]),
            "local_receipt": identity(source_receipt_path),
            "axiom_inventory": h56_axiom_inventory(profile, source_receipt, names),
        },
        "theorem_count": len(names),
        "theorems": names,
        "workflow": {
            "name": H56_CI_EVIDENCE["workflow_name"],
            "expected_sha": H56_EXPECTED_HEAD,
            "expected_tree": H56_EXPECTED_TREE,
            "branch": H56_EXPECTED_BRANCH,
            "event": H56_CI_EVIDENCE["event"],
            "conclusion": "success",
            "exact_head_bound": True,
            "run_id": H56_CI_EVIDENCE["run_id"],
            "run_number": H56_CI_EVIDENCE["run_number"],
            "run_attempt": H56_CI_EVIDENCE["run_attempt"],
            "reproduction_created_at": H56_CI_EVIDENCE["reproduction_created_at"],
            "reproduction_completed_at": H56_CI_EVIDENCE["reproduction_completed_at"],
            "reproduction_updated_at": H56_CI_EVIDENCE["reproduction_updated_at"],
            "job_id": H56_CI_EVIDENCE["job_id"],
            "job_name": H56_CI_EVIDENCE["job_name"],
            "job_conclusion": H56_CI_EVIDENCE["job_conclusion"],
            "all_job_steps_terminal": H56_CI_EVIDENCE["all_job_steps_terminal"],
            "poppler_step": H56_CI_EVIDENCE["poppler_step"],
            "poppler_step_conclusion": H56_CI_EVIDENCE["poppler_step_conclusion"],
            "profile_step": (
                H56_CI_EVIDENCE["h5_step"]
                if profile["publication_id"].endswith("h5-v1")
                else H56_CI_EVIDENCE["h6_step"]
            ),
            "profile_step_conclusion": "success",
            "observed_profile_result": (
                {
                    "scope": "QIK-VRT VRTCore SMG H5 local formal package",
                    "theorems": "32/32",
                    "physical_unification": "OPEN_CANDIDATE",
                    "effect_state": "EFFECT_ACK_CONTINUE",
                }
                if profile["publication_id"].endswith("h5-v1")
                else {
                    "scope": "QIK-VRT VRTCore Virtual Sphere H6 exact local package",
                    "theorems": "55/55",
                    "virtual_closure_scope": "PASS",
                    "physical_closure": "OPEN",
                    "effect_state": "EFFECT_ACK_CONTINUE",
                }
            ),
            "decoded_log": {
                "encoding": H56_CI_EVIDENCE["decoded_log_encoding"],
                "bytes": H56_CI_EVIDENCE["decoded_log_bytes"],
                "sha256": H56_CI_EVIDENCE["decoded_log_sha256"],
            },
            "evidence_role": "HOSTED_AUTOMATED_EXACT_HEAD_REEXECUTION_ONLY",
        },
        "claim_transition": {
            "source_claim_matrix": projection["source_claim_matrix"],
            "target_claim_matrix": identity(profile["envelope"] / H56_GENERATED["projection"]),
            "formal_claim_ids": projection["formal_claim_ids_exact_head_ci"],
            "from": "LOCAL_KERNEL_ACCEPTED",
            "to": "FORMAL_PROVED_EXACT_HEAD_REPRODUCED",
            "target_exact_head_confirmation_required": False,
        },
        "epistemic_boundary": {
            "local_kernel_observation_preserved": True,
            "formal_zenodo_claims_promoted": True,
            "ci_log_used_as_formal_proof_source": False,
            "physical_closure": "OPEN",
            "physical_big_bang_identity": "NOT_CLAIMED",
        },
        "completion_claims": {
            "kernel_exact_head_receipt_complete": True,
            "formal_scope_pass": True,
            "global_pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def h56_candidate_files(profile: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for name in profile["candidate_names"]:
        observed = identity(profile["root"] / name)
        values.append({
            **observed,
            "name": name,
            "role": "PRIMARY" if name == profile["primary"] else "SUPPLEMENT",
        })
    if sum(item["role"] == "PRIMARY" for item in values) != 1:
        raise SystemExit("BLOCK H5/H6 candidate needs exactly one primary file")
    return values


def h56_artifact_specs(profile: dict[str, Any], *, include_checksums: bool) -> list[tuple[pathlib.Path, str]]:
    candidates = set(profile["candidate_names"])
    specs: list[tuple[pathlib.Path, str]] = []
    kinds = {
        "CLAIM_MATRIX.json": "SOURCE",
        profile["local_receipt"]: "EVIDENCE",
        profile["lean_source"]: "SOURCE",
        profile["axiom_audit"]: "SOURCE",
        "SOURCE_EVIDENCE_BINDINGS.json": "EVIDENCE",
    }
    for name in profile["source_files"]:
        if name not in candidates:
            specs.append((profile["root"] / name, kinds.get(name, "OTHER")))
    generated_kinds = {
        "projection": "CLAIM_MATRIX",
        "kernel_receipt": "KERNEL_RECEIPT",
        "boundary": "BOUNDARY_TEST",
        "change_notice": "CHANGE_NOTICE",
        "return_receipt": "RETURN_RECEIPT",
        "metadata": "OTHER",
        "license_notice": "OTHER",
        "fileset": "OTHER",
    }
    for key, kind in generated_kinds.items():
        specs.append((profile["envelope"] / H56_GENERATED[key], kind))
    specs.extend([
        (ROOT / "policy/zenodo-machine-proof-policy-v2.json", "OTHER"),
        (ROOT / "policy/qikvrt-zenodo-machine-proof-bundle-v2.schema.json", "OTHER"),
        (ROOT / "policy/qikvrt-prepublication-return-receipt-v2.schema.json", "OTHER"),
        (ROOT / "LICENSES/CC-BY-NC-ND-4.0.txt", "OTHER"),
        (ROOT / "LICENSES/PolyForm-Noncommercial-1.0.0.txt", "OTHER"),
    ])
    if include_checksums:
        specs.append((profile["envelope"] / H56_GENERATED["checksums"], "OTHER"))
    paths = [path.relative_to(ROOT).as_posix() for path, _kind in specs]
    if len(paths) != len(set(paths)):
        raise SystemExit("BLOCK duplicate H5/H6 artifact path")
    return specs


def h56_artifacts(profile: dict[str, Any], *, include_checksums: bool) -> list[dict[str, Any]]:
    return [
        {
            "path": observed["path"],
            "sha256": observed["sha256"],
            "git_blob_sha1": observed["git_blob_sha1"],
            "kind": kind,
        }
        for path, kind in h56_artifact_specs(profile, include_checksums=include_checksums)
        for observed in [identity(path)]
    ]


def h56_change_notice(profile: dict[str, Any], projection: dict[str, Any]) -> str:
    ids = ", ".join(projection["formal_claim_ids_exact_head_ci"])
    split_notice = (
        "- `H5-C04` → enger `FORMAL_PROVED`-Teil für H5-T15 bis H5-T25 "
        "plus `H5-C04-RESIDUAL` als `SOURCE_BOUND` für die beiden nur in "
        "der exakten Lean-Definition gebundenen Konjunkte."
        if profile["publication_id"].endswith("h5-v1")
        else
        "- `H6-C07` → enger `EMPIRICALLY_EVIDENCED`-Teil für den konkreten "
        "receipt-gebundenen lokalen Lauf plus `H6-C07-RESIDUAL` als `OPEN` "
        "für die nicht aus Einzelruns ableitbare Universalform."
    )
    return f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Zenodo-v2-Hüllennachweis — keine Änderung der H5/H6-Originalbytes

Publication ID: `{profile['publication_id']}`

`content_changed=false`: Die bereits im Commit `{H56_EXPECTED_HEAD}` enthaltenen
H5/H6-Source-Candidate-Bytes werden nicht umgeschrieben. Diese Aussage bezieht
sich nur auf jene unveränderten Sourcebytes, nicht auf die neue Prüfhülle. Neu
ist ausschließlich eine additive Zenodo-v2-Prüfhülle mit Claim-Projektion, Return-Receipt,
Grenztestbericht, Metadaten und maschinenlesbarem Proof-Bundle.

Die lokalen Formalgruppen `{ids}` werden als `FORMAL_PROVED` projiziert. Ihre
Theoremreferenzen stammen ausschließlich aus der exakten lokalen Kernel-Receipt
und deren Axiom-Inventar. Der terminale Push-Run `30747218720` führt die
H5/H6-Prüfung am exakten Commit `{H56_EXPECTED_HEAD}` gehostet und automatisiert
erneut aus. Sein Log ist weder unabhängiges Peer-Review noch Ersatz für den
formalen Beweis.

Wo der ursprüngliche Source-Claim weiter reicht als die exakt gebundenen
Theorem- oder Laufreferenzen, enthält die v2-Projektion ausdrücklich eine
konservative Teilbehauptung; die ursprünglichen Source-Bytes bleiben unverändert.

Zenodo-Version und Upload-Typ folgen der unveränderten `CITATION.cff`: H5 wird
als Artikel/Working Paper abgebildet, H6 als Software ohne Publication-Subtype.

Sichtbare Source→Projection-Aufspaltung:

{split_notice}

Physische Schließung, eine physische Vereinigung der Gravitation mit dem
Standardmodell, ein Graviton-Nachweis und die Identität einer virtuellen
Kosmogenese mit dem physischen Urknall bleiben ausdrücklich `OPEN` bzw.
`NOT_CLAIMED`.

Keine `OWNER_ZENODO_AUTHORIZATION`, kein `publish-request.json`, kein Workflow
und keine externe Mutation sind Bestandteil dieses Kandidaten.
"""


def h56_license_notice(profile: dict[str, Any]) -> str:
    code = sorted(
        name for name in profile["source_files"]
        if pathlib.PurePosixPath(name).suffix in {".lean", ".py", ".olean"}
    )
    code_lines = "\n".join(f"- `{name}`" for name in code)
    return f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Gemischte Lizenzgrenze des Zenodo-Kandidaten

Publication ID: `{profile['publication_id']}`

Die Publikation ist ein gemischtes Paket. QIK-VRT-kontrollierter ausführbarer
Quellcode und das erzeugte Lean-Objekt folgen, soweit anwendbar,
`PolyForm-Noncommercial-1.0.0`:

{code_lines}

Artikel, Grafiken, Grammatikbeschreibung, Claim-/Receipt-/Provenienzdaten und
diese Prüfhülle folgen `CC-BY-NC-ND-4.0`, soweit keine speziellere Dateiangabe
gilt. Lean und alle weiteren Drittkomponenten behalten ihre eigenen Lizenzen.
Die vollständigen Lizenztexte werden als Upload-Artefakte mitgeführt.

Der Zenodo-Metadatenschlüssel `other-open` ist nur ein technischer
Sammelhinweis auf diese offen zugängliche Mischlizenz. Er ersetzt weder diese
Pfadzuordnung noch gewährt er gewöhnliche kommerzielle Nutzung.
"""


def h56_metadata(profile: dict[str, Any]) -> dict[str, Any]:
    citation = (profile["root"] / "CITATION.cff").read_text(encoding="utf-8")
    version_match = re.search(r'(?m)^version:\s*"([^"]+)"\s*$', citation)
    type_match = re.search(r"(?m)^type:\s*([A-Za-z0-9_-]+)\s*$", citation)
    if (
        version_match is None
        or version_match.group(1) != profile["version"]
        or type_match is None
        or type_match.group(1) != profile["citation_type"]
    ):
        raise SystemExit("BLOCK Zenodo metadata differs from CITATION.cff type/version")
    value = {
        "title": profile["title"],
        "upload_type": profile["zenodo_upload_type"],
        "description": profile["description"],
        "creators": [{"name": "Lohmann, Ingolf"}],
        "version": profile["version"],
        "publication_date": "2026-08-02",
        "access_right": "open",
        "license": "other-open",
        "language": "deu",
        "keywords": profile["keywords"],
        "notes": (
            "Mixed-license package; see ZENODO_LICENSE_NOTICE.md. Exact-head "
            f"CI run {H56_CI_EVIDENCE['run_id']} for {H56_EXPECTED_HEAD} "
            "completed successfully as hosted automated exact-head "
            "re-execution of the formal package gates; it is not independent "
            "review. "
            "Formal theorem references remain bound to the local kernel "
            "receipt and axiom inventory. PhysicalClosure remains OPEN. No "
            "owner upload authorization or publication effect is contained."
        ),
        "prereserve_doi": True,
    }
    if profile["zenodo_publication_type"] is not None:
        value["publication_type"] = profile["zenodo_publication_type"]
    return value


def h56_return_receipt(profile: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_prepublication_return_receipt",
        },
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": profile["publication_id"],
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
            "return_channel": (
                "GitHub draft PR #323 exact-head source candidate at "
                + H56_EXPECTED_HEAD
            ),
            "returned_at": H56_CI_EVIDENCE["reproduction_created_at"],
            "visible_change_notice_returned": False,
        },
    }


def h56_boundary_report(profile: dict[str, Any], projection: dict[str, Any]) -> dict[str, Any]:
    is_h5 = profile["publication_id"].endswith("h5-v1")
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_boundary_test_report",
        },
        "schema": "qikvrt_h56_zenodo_boundary_test_report_v2",
        "publication_id": profile["publication_id"],
        "result": "PASS",
        "source_binding": {
            "repository": "Goldkelch/qik-vrt",
            "commit": H56_EXPECTED_HEAD,
            "tree": H56_EXPECTED_TREE,
            "generated_descendant_containing_commit": "NOT_CLAIMED",
        },
        "checks": [
            {"id": "SOURCE_PACKAGE_COMMIT_AND_TREE", "result": "PASS"},
            {"id": "LOCAL_KERNEL_RECEIPT", "result": "PASS",
             "receipt": identity(profile["root"] / profile["local_receipt"])},
            {"id": "CLAIM_DISPOSITION", "result": "PASS",
             "claim_count": projection["claim_count"]},
            {"id": "EXACT_HEAD_CI", "result": "PASS",
             "expected_head": H56_EXPECTED_HEAD,
             "run_id": H56_CI_EVIDENCE["run_id"],
             "job_id": H56_CI_EVIDENCE["job_id"],
             "decoded_log_sha256": H56_CI_EVIDENCE["decoded_log_sha256"]},
            {"id": "PROFILE_FORMAL_GATE", "result": "PASS",
             "observed": "32/32" if is_h5 else "55/55"},
            {"id": "VIRTUAL_CLOSURE_SCOPE", "result": (
                "NOT_APPLICABLE" if is_h5 else "PASS"
            )},
            {"id": "PHYSICAL_CLOSURE", "result": "OPEN"},
            {"id": "OWNER_ZENODO_AUTHORIZATION", "result": "ABSENT_BY_DESIGN"},
            {"id": "ZENODO_EFFECT", "result": "NOT_PERFORMED"},
        ],
        "boundaries": {
            "formal_publication_promotion": "COMPLETE_EXACT_HEAD_CI",
            "virtual_closure_scope": "NOT_APPLICABLE" if is_h5 else "PASS",
            "physical_unification": "OPEN_CANDIDATE" if is_h5 else "NOT_CLAIMED",
            "physical_closure": "OPEN",
            "physical_big_bang_identity": "NOT_CLAIMED",
            "automated_exact_head_reexecution": "GITHUB_ACTIONS_SUCCESS",
            "independent_external_reproduction": "OPEN",
            "effect_state": "EFFECT_ACK_CONTINUE",
            "github_source_commit_already_observed": H56_EXPECTED_HEAD,
            "github_mutation_by_envelope_materialization": False,
            "zenodo_mutation_by_envelope_materialization": False,
            "ietf_datatracker_mutation_by_envelope_materialization": False,
        },
        "completion_claims": {
            "prepublication_boundary_scope_pass": True,
            "global_pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def h56_fileset(profile: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    artifact_paths = [
        path.relative_to(ROOT).as_posix()
        for path, _kind in h56_artifact_specs(profile, include_checksums=True)
    ]
    paths = [item["path"] for item in candidates] + artifact_paths + [
        (profile["envelope_rel"] / H56_GENERATED["bundle"]).as_posix()
    ]
    lines = "\n".join(f"- `{path}`" for path in paths)
    return f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Exakter Zenodo-v2-Dateisatz

Publication ID: `{profile['publication_id']}`

Der spätere Upload darf ausschließlich die folgenden Repository-Pfade enthalten:

{lines}

`OWNER_ZENODO_AUTHORIZATION.json`, `publish-request.json` und
`zenodo-publication.json` fehlen absichtlich. Sie sind spätere, getrennt
autorisierte Repository-/Plattformwirkungen und keine Uploaddateien dieses
Vorbereitungskandidaten.
"""


def h56_checksums(candidates: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> str:
    entries = [(item["sha256"], item["name"]) for item in candidates]
    entries.extend(
        (item["sha256"], pathlib.PurePosixPath(item["path"]).name)
        for item in artifacts
    )
    names = [name for _digest, name in entries]
    if len(names) != len(set(names)):
        raise SystemExit("BLOCK H5/H6 Zenodo upload basenames are not unique")
    return "".join(
        f"{digest}  {name}\n" for digest, name in sorted(entries, key=lambda item: item[1])
    )


def h56_bundle(
    profile: dict[str, Any],
    projection: dict[str, Any],
    candidates: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    wording = {
        "FORMAL_PROVED": "ESTABLISHED_WITHIN_SCOPE",
        "EMPIRICALLY_EVIDENCED": "EMPIRICALLY_SUPPORTED",
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "NORMATIVE": "NORMATIVE_DECLARATION",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
    }
    prefix = profile["publication_rel"].as_posix() + "/"
    envelope_prefix = profile["envelope_rel"].as_posix() + "/"
    claims: list[dict[str, Any]] = []
    for claim in projection["claims"]:
        classification = claim["classification"]
        claims.append({
            "claim_id": claim["claim_id"],
            "statement": claim["statement"],
            "classification": classification,
            "status": claim["status"],
            "publication_wording": wording[classification],
            "scope": claim["boundary"],
            "proof_refs": [
                envelope_prefix + H56_GENERATED["kernel_receipt"] + "#" + theorem
                for theorem in claim["proof_refs"]
            ],
            "evidence_refs": claim["evidence_references"],
            "source_refs": claim["source_references"],
        })
    policy_identity = identity(ROOT / "policy/zenodo-machine-proof-policy-v2.json")
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_proof_bundle",
        },
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "policy": {
            "id": "qikvrt-zenodo-machine-proof-before-publication-v2",
            "path": policy_identity["path"],
            "version": "2.0.0",
            "sha256": policy_identity["sha256"],
            "git_blob_sha1": policy_identity["git_blob_sha1"],
        },
        "publication_id": profile["publication_id"],
        "candidate": {
            "primary_document_path": prefix + profile["primary"],
            "files": candidates,
        },
        "claims": claims,
        "artifacts": artifacts,
        "prepublication_return": {
            "content_changed": False,
            "candidate_returned_to_owner": True,
            "receipt_path": envelope_prefix + H56_GENERATED["return_receipt"],
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


def materialize_h56(profile_name: str, check: bool) -> None:
    profile = h56_profile(profile_name)
    if not check:
        profile["envelope"].mkdir(parents=True, exist_ok=True)
    source_receipt = read_json(profile["root"] / profile["local_receipt"])
    names = h56_theorem_names(profile, source_receipt)
    theorem_by_claim = h56_formal_claim_theorems(profile, names)
    projection = h56_materialize_projection(profile, theorem_by_claim)
    emit(profile["envelope"] / H56_GENERATED["projection"], projection, check)
    kernel = h56_materialize_kernel_receipt(profile, projection, names)
    emit(profile["envelope"] / H56_GENERATED["kernel_receipt"], kernel, check)
    boundary_report = h56_boundary_report(profile, projection)
    emit(profile["envelope"] / H56_GENERATED["boundary"], boundary_report, check)
    emit_text(
        profile["envelope"] / H56_GENERATED["change_notice"],
        h56_change_notice(profile, projection),
        check,
    )
    candidates = h56_candidate_files(profile)
    emit(
        profile["envelope"] / H56_GENERATED["return_receipt"],
        h56_return_receipt(profile, candidates),
        check,
    )
    metadata = h56_metadata(profile)
    emit(profile["envelope"] / H56_GENERATED["metadata"], metadata, check)
    emit_text(
        profile["envelope"] / H56_GENERATED["license_notice"],
        h56_license_notice(profile),
        check,
    )
    emit_text(
        profile["envelope"] / H56_GENERATED["fileset"],
        h56_fileset(profile, candidates),
        check,
    )
    artifacts_without_checksums = h56_artifacts(profile, include_checksums=False)
    emit_text(
        profile["envelope"] / H56_GENERATED["checksums"],
        h56_checksums(candidates, artifacts_without_checksums),
        check,
    )
    artifacts = h56_artifacts(profile, include_checksums=True)
    bundle_path = profile["envelope"] / H56_GENERATED["bundle"]
    emit(bundle_path, h56_bundle(profile, projection, candidates, artifacts), check)
    upload_paths = [
        *(item["path"] for item in candidates),
        *(item["path"] for item in artifacts),
        bundle_path.relative_to(ROOT).as_posix(),
    ]
    import qikvrt_zenodo_machine_proof as proof

    proof_result = proof.validate_bundle(ROOT, bundle_path, upload_paths=upload_paths)
    metadata_sha256 = hashlib.sha256(
        json.dumps(
            metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    action = "verified" if check else "materialized"
    print(
        f"PASS {action} {profile_name.upper()} Zenodo-v2 exact-head freeze: "
        f"{projection['claim_count']} claims, {len(candidates)} candidates, "
        f"{len(artifacts)} artifacts"
    )
    print("RETURN_SHA256=" + identity(profile["envelope"] / H56_GENERATED["return_receipt"])["sha256"])
    print("METADATA_SHA256=" + metadata_sha256)
    print("MACHINE_PROOF_SHA256=" + proof_result["sha256"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize the VRTCore exact-head Zenodo candidate"
    )
    parser.add_argument("stage", choices=("kernel", "return"))
    parser.add_argument(
        "--profile",
        choices=("relational", "h5", "h6"),
        default="relational",
        help="publication profile; relational preserves the historical H3 path",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.profile in H56_PROFILES:
        if args.stage != "return":
            raise SystemExit("BLOCK H5/H6 profiles support only the complete return stage")
        materialize_h56(args.profile, args.check)
    elif args.stage == "kernel":
        materialize_kernel(args.check)
    elif args.stage == "return":
        materialize_return(args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
