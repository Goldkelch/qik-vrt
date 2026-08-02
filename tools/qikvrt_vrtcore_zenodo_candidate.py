#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministically materialize the VRTCore Zenodo proof candidate.

The first stage turns an immutable, exact-head GitHub Actions payload into a
full claim matrix, a kernel receipt and a boundary report.  It deliberately
binds the verified predecessor rather than pretending that a receipt can bind
the commit which first contains that receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
from collections import Counter
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION_REL = pathlib.PurePosixPath(
    "docs/publications/2026-08-02-causality-is-relation-vrtcore"
)
PUBLICATION = ROOT.joinpath(*PUBLICATION_REL.parts)
PUBLICATION_ID = "qikvrt-causality-is-relation-vrtcore-v1"
H1_HEAD = "7de3bd9e5fff9b8aedf0d6385c0904646d99b2ac"
H1_TREE = "513c33f91d4226bfd3f735994bf15cb143d46ff4"
H0_MATRIX_NAME = "VRTCore_CLAIM_MATRIX_H0_RETURNED.json"
H1_OVERLAY_NAME = "VRTCore_CLAIM_MATRIX_H1_KERNEL_VERIFIED.json"
CI_EVIDENCE_NAME = "CI_KERNEL_EVIDENCE_H1_EXACT_HEAD.json"
CLAIM_MATRIX_NAME = "CLAIM_MATRIX.json"
KERNEL_RECEIPT_NAME = "KERNEL_RECEIPT.json"
BOUNDARY_REPORT_NAME = "BOUNDARY_TEST_REPORT.json"
CI_EVIDENCE_SHA256 = (
    "ea25ab8ddcbe34b33d14309d25a944e05bfd6899cb832cb1280c2aa7e121f0f1"
)
CI_ARCHIVE_SHA256 = (
    "5f1bf2d0b1cc9547d64487e05aa50d4eba872442a7a297cf247bc4560661d3c4"
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


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
    ).strip()


def validate_exact_evidence(evidence: dict[str, Any]) -> None:
    evidence_path = PUBLICATION / CI_EVIDENCE_NAME
    if identity(evidence_path)["sha256"] != CI_EVIDENCE_SHA256:
        raise SystemExit("BLOCK exact-head CI evidence bytes differ")
    checkout = evidence.get("checkout")
    expected_checkout = {
        "event_name": "push",
        "mode": "exact_ref_head",
        "tested_commit_sha": H1_HEAD,
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
        or evidence.get("github_sha") != H1_HEAD
        or evidence.get("github_run_id") != "30733039956"
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
        source_blob = git("rev-parse", f"{H1_HEAD}:{value['path']}")
        if source_blob != value["git_blob_sha1"]:
            raise SystemExit(f"BLOCK H1 source blob differs: {value['path']}")
    if git("show", "-s", "--format=%T", H1_HEAD) != H1_TREE:
        raise SystemExit("BLOCK exact-head source tree differs")


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
            prefix + "VERIFICATION_ADDENDUM_DE.md#" + source_ids[0]
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
        "schema": "qikvrt_vrtcore_kernel_receipt_v1",
        "publication_id": PUBLICATION_ID,
        "scope_id": PUBLICATION_ID,
        "state": "KERNEL_VERIFIED",
        "receipt_stage": {
            "stage": "H2_SUCCESSOR_MATERIALIZATION",
            "predecessor_head": H1_HEAD,
            "predecessor_tree": H1_TREE,
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
            "run_id": 30733039956,
            "run_attempt": 1,
            "job_id": 91456613018,
            "job_name": "source-claim-and-kernel-gates",
            "sha": H1_HEAD,
            "branch": "agent/vrtcore-causality-publication",
            "started_at": "2026-08-02T04:49:45Z",
            "completed_at": "2026-08-02T04:50:54Z",
            "url": "https://github.com/Goldkelch/qik-vrt/actions/runs/30733039956",
        },
        "source_verification": {
            "verified_candidate": {
                "repository": "Goldkelch/qik-vrt",
                "branch": "agent/vrtcore-causality-publication",
                "head": H1_HEAD,
                "tree": H1_TREE,
                "pull_request": 320,
            },
            "artifact": {
                "id": 8828591925,
                "name": "qikvrt-vrtcore-relational-causality-kernel-evidence",
                "archive_size_bytes": 2267,
                "archive_digest": "sha256:" + CI_ARCHIVE_SHA256,
                "created_at": "2026-08-02T04:50:20Z",
                "expires_at": "2026-09-01T04:50:19Z",
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
    candidate_names = [
        "QIK-VRT_Kausalitaet_ist_Relation_Fachartikel_DE_2026-08-02.md",
        "QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_DE_2026-08-02.md",
        "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.tex",
        "QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf",
        "VERIFICATION_ADDENDUM_DE.md",
        "QIK-VRT_Kausalitaet_ist_Relation_WhatsApp_Verifikationsnachtrag_DE_2026-08-02.md",
    ]
    candidates = [identity(PUBLICATION / name) for name in candidate_names]
    for item in candidates:
        source_blob = git("rev-parse", f"{H1_HEAD}:{item['path']}")
        if source_blob != item["git_blob_sha1"]:
            raise SystemExit(f"BLOCK owner-facing candidate changed: {item['path']}")
    return {
        "_license": {
            **LICENSE,
            "classification": "machine_readable_boundary_test_report",
        },
        "schema": "qikvrt_vrtcore_boundary_test_report_v1",
        "publication_id": PUBLICATION_ID,
        "tested_at": "2026-08-02T04:55:00Z",
        "stage": "H2_SUCCESSOR_MATERIALIZATION",
        "result": "PASS",
        "checks": [
            {
                "id": "EXACT_HEAD_KERNEL_EVIDENCE",
                "result": "PASS",
                "head": H1_HEAD,
                "tree": H1_TREE,
                "run_id": 30733039956,
                "artifact_id": 8828591925,
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
                "unchanged_from_exact_head": True,
            },
            {
                "id": "H2_SELF_INCLUSION_BOUNDARY",
                "result": "PASS",
                **receipt["receipt_stage"],
            },
        ],
        "model_boundaries": receipt["epistemic_boundary"],
        "external_effects": {
            "github_h1_persisted": True,
            "github_h1_exact_head_ci_success": True,
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


def emit(path: pathlib.Path, value: dict[str, Any], check: bool) -> None:
    expected = json_bytes(value)
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
        f"PASS {action} VRTCore H2: {matrix['claim_count']} claims, "
        f"{receipt['theorem_count']} kernel-verified theorems"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Materialize the VRTCore exact-head Zenodo candidate"
    )
    parser.add_argument("stage", choices=("kernel",))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.stage == "kernel":
        materialize_kernel(args.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
