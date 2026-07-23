#!/usr/bin/env python3
"""Validate Draft-01 bytes and the Lean claim/evidence boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
PROVENANCE = ROOT / "effect_ack" / "DRAFT01_SOURCE_PROVENANCE.json"
MATRIX = ROOT / "effect_ack" / "DRAFT01_CLAIM_MATRIX.json"
PROOF_REPORT = (
    REPOSITORY
    / "docs/publications/2026-07-22-effect-ack-universal-effect-control"
    / "proof-report.json"
)
CLAIMS_SOURCE = ROOT / "QIKVRTEffectAck" / "Claims.lean"

ALLOWED_STATUSES = {
    "KERNEL_PROVED",
    "KERNEL_PROVED_CONDITIONAL",
    "OPEN",
    "EMPIRICAL_OPEN",
}
KERNEL_STATUSES = {
    "KERNEL_PROVED",
    "KERNEL_PROVED_CONDITIONAL",
}
ALLOWED_DRAFT_RELATIONSHIPS = {
    "NORMATIVE_MODEL",
    "CONDITIONAL_EXTENSION",
    "ANALYTIC_EXTENSION",
    "SCOPE_BOUNDARY",
}
EXPECTED_STATES = [
    "EFFECT_NACK",
    "EFFECT_ACK_CONTINUE",
    "EFFECT_ACK_DONE",
    "EFFECT_ACK_ISOLATE",
    "EFFECT_ACK_BLOCK",
]
EXPECTED_CONNECTION_DECISIONS = [
    "UNDECIDED",
    "CONTINUE",
    "RELEASE",
    "ISOLATE",
    "BLOCK",
]
EXPECTED_PRIORITY_ANCHORS = [
    "predecessor_invalid",
    "deadline_exceeded",
    "not effect_checkable_reception",
    "integrity_failure",
    "connection_decision == BLOCK",
    "connection_decision == ISOLATE",
    "connection_decision == RELEASE",
    "state = EFFECT_ACK_CONTINUE",
    "ordinary_release = (state == EFFECT_ACK_DONE)",
]
REQUIRED_TEXT_ANCHORS = (
    "draft-lohmann-qikvrt-effect-ack-01",
    "ordinary_release(record) is true",
    "record.state == EFFECT_ACK_DONE",
    "r.transport_ack",
    "and set(r.required_evidence_refs) <= set(r.evidence_refs)",
    "ordinary_release = (state == EFFECT_ACK_DONE)",
    "A proof of the software model is not, by itself, a proof that a",
    "physical effect is safe.",
    "does not solve the halting problem",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"BLOCK EFFECT_ACK_CLAIM_MATRIX_INVALID: {message}")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.name}: top level must be an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sources(provenance: dict[str, Any]) -> str:
    require(
        provenance.get("schema")
        == "qikvrt_effect_ack_draft01_source_provenance_v1",
        "unsupported source-provenance schema",
    )
    require(
        provenance.get("draft") == "draft-lohmann-qikvrt-effect-ack-01",
        "wrong draft revision",
    )
    archive = provenance.get("archive")
    require(isinstance(archive, dict), "archive must be an object")
    source_text = ""
    for kind in ("txt", "xml"):
        entry = archive.get(kind)
        require(isinstance(entry, dict), f"archive.{kind} missing")
        path = REPOSITORY / str(entry.get("repository_path", ""))
        require(path.is_file(), f"archive.{kind} path missing")
        require(path.stat().st_size == entry.get("size"), f"archive.{kind} size")
        require(sha256(path) == entry.get("sha256"), f"archive.{kind} sha256")
        if kind == "txt":
            source_text = path.read_text(encoding="utf-8")
    normalized_text = " ".join(source_text.split())
    for anchor in REQUIRED_TEXT_ANCHORS:
        require(
            anchor in normalized_text,
            f"Draft-01 text anchor missing: {anchor}",
        )
    return source_text


def validate_existing_structural_report(provenance: dict[str, Any]) -> None:
    report = load_object(PROOF_REPORT)
    checks = report.get("checks")
    require(isinstance(checks, list), "proof report checks missing")
    spec = next(
        (item for item in checks if isinstance(item, dict) and item.get("id") == "SPEC-001"),
        None,
    )
    require(isinstance(spec, dict) and spec.get("status") == "PASS", "SPEC-001")
    inspection = spec.get("inspection")
    require(isinstance(inspection, dict), "SPEC-001 inspection missing")
    xml = provenance["archive"]["xml"]
    require(inspection.get("sha256") == xml["sha256"], "SPEC-001 XML hash")
    require(inspection.get("wireFields") == 35, "SPEC-001 wire fields")
    require(inspection.get("coreDoneConjuncts") == 17, "SPEC-001 CoreDone")
    require(inspection.get("states") == EXPECTED_STATES, "SPEC-001 states")
    require(
        inspection.get("connectionDecisions") == EXPECTED_CONNECTION_DECISIONS,
        "SPEC-001 decisions",
    )
    require(
        inspection.get("priorityAnchors") == EXPECTED_PRIORITY_ANCHORS,
        "SPEC-001 priority anchors",
    )


def validate_matrix(matrix: dict[str, Any]) -> dict[str, int]:
    require(
        matrix.get("schema") == "qikvrt_effect_ack_draft01_claim_matrix_v1",
        "unsupported claim-matrix schema",
    )
    model = matrix.get("model")
    require(isinstance(model, dict), "model missing")
    require(model.get("boolean_snapshot_fields") == 19, "model Boolean count")
    require(model.get("connection_decisions") == 5, "model decision count")
    require(model.get("states") == 5, "model state count")
    require(model.get("core_done_conjuncts") == 17, "model CoreDone count")

    claims = matrix.get("claims")
    require(isinstance(claims, list) and len(claims) == 15, "expected 15 claims")
    ids: set[str] = set()
    proof_count = 0
    registry_count = 0
    registry_source = CLAIMS_SOURCE.read_text(encoding="utf-8")
    for index, claim in enumerate(claims):
        require(isinstance(claim, dict), f"claim {index} must be an object")
        claim_id = claim.get("id")
        require(isinstance(claim_id, str) and claim_id, f"claim {index} id")
        require(claim_id not in ids, f"duplicate claim id {claim_id}")
        ids.add(claim_id)
        status = claim.get("status")
        require(status in ALLOWED_STATUSES, f"{claim_id}: status")
        relationship = claim.get("draft_relationship")
        require(
            relationship in ALLOWED_DRAFT_RELATIONSHIPS,
            f"{claim_id}: draft relationship",
        )
        sections = claim.get("source_sections")
        require(
            isinstance(sections, list)
            and all(isinstance(item, str) and item for item in sections),
            f"{claim_id}: source sections",
        )
        if relationship in {"NORMATIVE_MODEL", "CONDITIONAL_EXTENSION"}:
            require(sections, f"{claim_id}: Draft-derived claim needs sections")
        if relationship == "ANALYTIC_EXTENSION":
            require(not sections, f"{claim_id}: analytic theorem is not Draft normative")
            related = claim.get("related_sections")
            require(
                isinstance(related, list)
                and related
                and all(isinstance(item, str) and item for item in related),
                f"{claim_id}: related sections",
            )
        proof_constants = claim.get("proof_constants")
        require(isinstance(proof_constants, list), f"{claim_id}: proof constants")
        source_path = claim.get("source_path")
        if status in KERNEL_STATUSES:
            require(proof_constants, f"{claim_id}: proof constants missing")
            require(isinstance(source_path, str), f"{claim_id}: source path")
        if proof_constants:
            require(isinstance(source_path, str), f"{claim_id}: source path")
            source = ROOT / source_path
            require(source.is_file(), f"{claim_id}: source file missing")
            source_text = source.read_text(encoding="utf-8")
            for constant in proof_constants:
                require(isinstance(constant, str) and constant, f"{claim_id}: constant")
                require(
                    constant.rsplit(".", 1)[-1] in source_text,
                    f"{claim_id}: {constant} not found in {source_path}",
                )
                proof_count += 1
        registry = claim.get("registry_constant")
        if registry is not None:
            require(isinstance(registry, str) and registry, f"{claim_id}: registry")
            require(
                registry.rsplit(".", 1)[-1] in registry_source,
                f"{claim_id}: registry constant not found",
            )
            registry_count += 1
    require(registry_count == 8, "expected eight proposition-indexed claims")
    return {
        "claims": len(claims),
        "proof_constants": proof_count,
        "registry_claims": registry_count,
    }


def main() -> None:
    provenance = load_object(PROVENANCE)
    validate_sources(provenance)
    validate_existing_structural_report(provenance)
    counts = validate_matrix(load_object(MATRIX))
    print(
        "PASS EFFECT_ACK Draft-01 source/structure/proof-reference validation: "
        f"{counts['claims']} claims, {counts['proof_constants']} proof constants, "
        f"{counts['registry_claims']} proposition-indexed registry claims"
    )


if __name__ == "__main__":
    main()
