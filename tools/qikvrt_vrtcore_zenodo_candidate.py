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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize the VRTCore exact-head Zenodo candidate"
    )
    parser.add_argument("stage", choices=("kernel", "return"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.stage == "kernel":
        materialize_kernel(args.check)
    elif args.stage == "return":
        materialize_return(args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
