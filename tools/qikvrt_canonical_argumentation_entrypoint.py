#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate QIK-VRT's canonical, evidence-bound argumentation entrypoint.

The checker is deliberately read-only.  It verifies the contract's own source
bindings, exact claim-class dispositions, no-transfer invariant, and the /AI
navigation anchors.  A successful result means only that this contract is
internally intact; it never grants a repository-wide completion or effect state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json"

EXPECTED_SCHEMA = "qikvrt_canonical_argumentation_entrypoint_v1"
EXPECTED_CONTRACT_ID = "QIKVRT-CANONICAL-ARGUMENTATION-ENTRYPOINT-V1"
EXPECTED_CLASSES = {
    "FORMAL_PROVED": ("PROVED", "ESTABLISHED_WITHIN_SCOPE"),
    "EMPIRICALLY_EVIDENCED": ("EVIDENCED", "EMPIRICALLY_SUPPORTED"),
    "SOURCE_BOUND": ("BOUND", "SOURCE_ATTRIBUTED"),
    "NORMATIVE": ("DECLARED", "NORMATIVE_DECLARATION"),
    "INTERPRETATIVE": ("DECLARED", "INTERPRETATIVE_DECLARATION"),
    "OPEN": ("OPEN", "EXPLICITLY_OPEN"),
}
REQUIRED_DYNAMIC_BINDING_KEY = {
    "repository",
    "ref_or_pull_request",
    "base",
    "head",
    "tree",
    "scope_sha256",
    "source_blob_set_sha256",
    "workflow_definition_sha256",
    "workflow_run_id",
    "workflow_job_id",
    "literal_checkout_head",
    "literal_checkout_tree",
    "review_routing_binding",
}
REQUIRED_DISTINCTIONS = {
    "CAUSALITY != SEQUENCE",
    "LATER != BETTER",
    "ACTIVITY != EFFECT",
    "TRANSPORT_ACK != EFFECT_ACK",
    "OWNER_ASSERTED_REALITY_CORRESPONDENCE != INDEPENDENT_EMPIRICAL_CONFIRMATION != SCIENTIFIC_CONSENSUS",
    "FORMAL_PROOF != EMPIRICAL_CONFIRMATION",
    "ZENODO_FIXITY != PEER_REVIEW_OR_EMPIRICAL_CONFIRMATION",
}
REQUIRED_ARGUMENT_FIELDS = {
    "claim_id",
    "classification",
    "status",
    "publication_wording",
    "statement",
    "scope",
    "assumptions",
    "guarded_inferences",
    "proof_refs",
    "evidence_refs",
    "source_refs",
    "argument_kinds",
    "evidence_bindings",
    "binding",
}
CLAIM_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{2,127}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ARGUMENT_KINDS = {
    "CAUSAL_CLAIM",
    "RECONSTRUCTION_CLAIM",
    "RETROSPECTIVE_DETERMINISM_CLAIM",
    "OWNER_ASSERTION",
    "SPACETIME_DIMENSIONAL_CLAIM",
    "EMPIRICAL_PHYSICAL_CLAIM",
}
SOURCE_EVIDENCE_KIND = "SOURCE_FILE"
FORMAL_THEOREM_EVIDENCE_KIND = "FORMAL_THEOREM"
CAUSAL_EVIDENCE_KINDS = {
    FORMAL_THEOREM_EVIDENCE_KIND,
    "INTERVENTION_RECORD",
    "COUNTERFACTUAL_RECORD",
    "EQUIVALENT_CAUSAL_JUSTIFICATION_RECORD",
}
EVIDENCE_RECORD_KINDS = {
    SOURCE_EVIDENCE_KIND,
    FORMAL_THEOREM_EVIDENCE_KIND,
    "MEASUREMENT_RECORD",
    "INTERVENTION_RECORD",
    "COUNTERFACTUAL_RECORD",
    "EQUIVALENT_CAUSAL_JUSTIFICATION_RECORD",
}


class ContractError(RuntimeError):
    """Raised when an argumentation-contract invariant fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"CONTRACT_UNREADABLE: {path}: {exc}") from exc
    require(isinstance(value, dict), f"CONTRACT_NOT_OBJECT: {path}")
    return value


def raw_git_blob_sha1(raw: bytes) -> str:
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def unique_string_list(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    require(isinstance(value, list), f"{label} must be a list")
    require(all(isinstance(item, str) and item for item in value), f"{label} contains an empty value")
    require(len(value) == len(set(value)), f"{label} contains duplicates")
    if nonempty:
        require(bool(value), f"{label} must not be empty")
    return value


def verify_class_projection(contract: Mapping[str, Any]) -> None:
    projection = contract.get("epistemic_projection")
    require(isinstance(projection, dict), "EPISTEMIC_PROJECTION_MISSING")
    reuse = projection.get("reuse_source")
    require(isinstance(reuse, dict), "EPISTEMIC_REUSE_SOURCE_MISSING")
    require(
        reuse.get("path") == "tools/qikvrt_round_trip_zenodo_bundle_freeze.py",
        "EPISTEMIC_REUSE_SOURCE_DRIFT",
    )
    require(reuse.get("function") == "verify_claim_matrix", "EPISTEMIC_REUSE_FUNCTION_DRIFT")
    classes = projection.get("classes")
    require(isinstance(classes, list), "EPISTEMIC_CLASSES_MISSING")
    observed: dict[str, tuple[Any, Any]] = {}
    for index, item in enumerate(classes):
        require(isinstance(item, dict), f"EPISTEMIC_CLASS_{index}_MALFORMED")
        classification = item.get("classification")
        observed[str(classification)] = (item.get("status"), item.get("publication_wording"))
        unique_string_list(item.get("minimum_binding"), f"EPISTEMIC_CLASS_{index}_MINIMUM_BINDING", nonempty=True)
    require(observed == EXPECTED_CLASSES, "EPISTEMIC_CLASS_PROJECTION_DRIFT")
    rule = projection.get("projection_boundary")
    require(
        isinstance(rule, str) and "evidence class" in rule.lower() and "label alone" in rule.lower(),
        "EPISTEMIC_PROJECTION_BOUNDARY_MISSING",
    )


def verify_authority_snapshot(contract: Mapping[str, Any], root: Path, *, verify_git: bool) -> None:
    authority = contract.get("authority_snapshot")
    require(isinstance(authority, dict), "AUTHORITY_SNAPSHOT_MISSING")
    require(authority.get("repository") == "Goldkelch/qik-vrt", "AUTHORITY_REPOSITORY_DRIFT")
    require(authority.get("ref") == "refs/heads/main", "AUTHORITY_REF_DRIFT")
    commit = authority.get("commit")
    tree = authority.get("tree")
    require(isinstance(commit, str) and HEX40_RE.fullmatch(commit) is not None, "AUTHORITY_COMMIT_INVALID")
    require(isinstance(tree, str) and HEX40_RE.fullmatch(tree) is not None, "AUTHORITY_TREE_INVALID")
    require(
        authority.get("role") == "SOURCE_SNAPSHOT_FOR_THE_BOUND_ARTIFACTS_LISTED_HERE",
        "AUTHORITY_SNAPSHOT_ROLE_DRIFT",
    )
    require(
        authority.get("current_state_rule") == "This snapshot identifies the cited source bytes. It is historical source evidence after a ref/head/tree drift and must never be used as a current-state or successor-gate receipt.",
        "AUTHORITY_STALENESS_RULE_DRIFT",
    )
    if not verify_git:
        return
    completed = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{tree}}"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    require(completed.returncode == 0, "AUTHORITY_SNAPSHOT_UNAVAILABLE")
    require(completed.stdout.strip() == tree, "AUTHORITY_SNAPSHOT_TREE_MISMATCH")


def repository_relative_path(path_value: str, label: str) -> Path:
    """Validate one repository-relative path without resolving it in the worktree."""

    relative = Path(path_value)
    require(
        bool(path_value)
        and not relative.is_absolute()
        and all(part not in {"", ".", ".."} for part in relative.parts),
        f"{label}_PATH_INVALID",
    )
    return relative


def repository_file(root: Path, path_value: str, label: str) -> Path:
    """Return one non-symlinked current-worktree file below *root*."""

    relative = repository_relative_path(path_value, label)
    candidate = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"{label}_SYMLINK_FORBIDDEN")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ContractError(f"{label}_PATH_OUTSIDE_REPOSITORY") from exc
    require(candidate.is_file(), f"{label}_NOT_FILE")
    return candidate


def snapshot_blob_at(root: Path, commit: str, path: str) -> str:
    repository_relative_path(path, "SOURCE_SNAPSHOT")
    completed = subprocess.run(
        ["git", "ls-tree", commit, "--", path],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    require(completed.returncode == 0, f"SOURCE_SNAPSHOT_LOOKUP_FAILED: {path}")
    line = completed.stdout.strip()
    require(line, f"SOURCE_SNAPSHOT_PATH_MISSING: {path}")
    match = re.fullmatch(r"[0-7]{6} blob ([0-9a-f]{40})\t" + re.escape(path), line)
    require(match is not None, f"SOURCE_SNAPSHOT_ENTRY_INVALID: {path}")
    return str(match.group(1))


def snapshot_bytes_at(root: Path, commit: str, path: str) -> bytes:
    """Read immutable bytes from the declared source snapshot, never current drift."""

    repository_relative_path(path, "SOURCE_SNAPSHOT")
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    require(completed.returncode == 0, f"SOURCE_SNAPSHOT_BYTES_UNAVAILABLE: {path}")
    return bytes(completed.stdout)


def verify_source_bindings(contract: Mapping[str, Any], root: Path, *, verify_snapshot: bool) -> int:
    bindings = contract.get("source_bindings")
    require(isinstance(bindings, list) and bindings, "SOURCE_BINDINGS_MISSING")
    seen_paths: set[str] = set()
    for index, item in enumerate(bindings):
        require(isinstance(item, dict), f"SOURCE_BINDING_{index}_MALFORMED")
        path_value = item.get("path")
        require(isinstance(path_value, str), f"SOURCE_BINDING_{index}_PATH_INVALID")
        require(path_value not in seen_paths, f"SOURCE_BINDING_{index}_PATH_DUPLICATE")
        seen_paths.add(path_value)
        blob = item.get("git_blob_sha1")
        digest = item.get("sha256")
        role = item.get("role")
        require(isinstance(blob, str) and HEX40_RE.fullmatch(blob) is not None, f"SOURCE_BINDING_{index}_BLOB_INVALID")
        require(isinstance(digest, str) and HEX64_RE.fullmatch(digest) is not None, f"SOURCE_BINDING_{index}_SHA256_INVALID")
        require(isinstance(role, str) and role, f"SOURCE_BINDING_{index}_ROLE_INVALID")
        repository_relative_path(path_value, f"SOURCE_BINDING_{index}")
        if verify_snapshot:
            authority = contract["authority_snapshot"]
            require(
                snapshot_blob_at(root, str(authority["commit"]), path_value) == blob,
                f"SOURCE_BINDING_{index}_SNAPSHOT_BLOB_MISMATCH",
            )
            raw = snapshot_bytes_at(root, str(authority["commit"]), path_value)
            require(hashlib.sha256(raw).hexdigest() == digest, f"SOURCE_BINDING_{index}_SNAPSHOT_SHA256_MISMATCH")
            require(raw_git_blob_sha1(raw) == blob, f"SOURCE_BINDING_{index}_SNAPSHOT_BLOB_BYTES_MISMATCH")
    return len(bindings)


def verify_dynamic_non_transfer(contract: Mapping[str, Any]) -> None:
    key = unique_string_list(contract.get("dynamic_binding_key"), "DYNAMIC_BINDING_KEY", nonempty=True)
    require(set(key) == REQUIRED_DYNAMIC_BINDING_KEY, "DYNAMIC_BINDING_KEY_DRIFT")
    invariant = contract.get("non_transfer_invariant")
    require(isinstance(invariant, dict), "NON_TRANSFER_INVARIANT_MISSING")
    on_change = invariant.get("on_any_dynamic_binding_change")
    require(isinstance(on_change, dict), "NON_TRANSFER_ON_CHANGE_MISSING")
    require(on_change.get("predecessor") == "STALE_HISTORICAL_SOURCE_ONLY", "PREDECESSOR_STALENESS_RULE_DRIFT")
    require(on_change.get("successor") == "REOBSERVATION_REQUIRED", "SUCCESSOR_REOBSERVATION_RULE_DRIFT")
    prohibited = set(unique_string_list(invariant.get("prohibited_transfers"), "PROHIBITED_TRANSFERS", nonempty=True))
    required = {
        "predecessor_head_or_tree_receipt_to_successor_head_or_tree",
        "synthetic_merge_checkout_to_literal_head_execution",
        "workflow_transport_or_activity_to_external_effect",
        "transport_ack_to_effect_ack",
        "zenodo_fixity_to_peer_review_consensus_or_measurement_confirmation",
        "formal_model_theorem_to_unbound_empirical_or_physical_conclusion",
        "owner_assertion_to_independent_empirical_confirmation_or_scientific_consensus",
    }
    require(required.issubset(prohibited), "NON_TRANSFER_PROHIBITIONS_INCOMPLETE")


def verify_argument_requirements(contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    requirements = contract.get("argument_requirements")
    require(isinstance(requirements, dict), "ARGUMENT_REQUIREMENTS_MISSING")
    fields = set(unique_string_list(requirements.get("required_fields"), "ARGUMENT_REQUIRED_FIELDS", nonempty=True))
    require(fields == REQUIRED_ARGUMENT_FIELDS, "ARGUMENT_REQUIRED_FIELDS_DRIFT")
    causal = requirements.get("causal_claim")
    require(isinstance(causal, dict), "CAUSAL_REQUIREMENTS_MISSING")
    require(causal.get("forbidden_substitute") == "sequence_or_timestamp_alone", "CAUSAL_SEQUENCE_BOUNDARY_DRIFT")
    require(causal.get("failure_code") == "CAUSALITY_ONLY_SEQUENCE", "CAUSAL_FAILURE_CODE_DRIFT")
    unique_string_list(causal.get("requires_one_of"), "CAUSAL_JUSTIFICATION_SET", nonempty=True)
    reconstruction = requirements.get("reconstruction_claim")
    require(isinstance(reconstruction, dict), "RECONSTRUCTION_REQUIREMENTS_MISSING")
    required_reconstruction = {"complete_manifest", "content_hashes", "explicit_semantic_dependency_order", "conflict_rule"}
    require(required_reconstruction == set(unique_string_list(reconstruction.get("requires"), "RECONSTRUCTION_REQUIREMENTS", nonempty=True)), "RECONSTRUCTION_REQUIREMENTS_DRIFT")
    retrospective = requirements.get("retrospective_determinism")
    require(isinstance(retrospective, dict), "RETROSPECTIVE_REQUIREMENTS_MISSING")
    require(retrospective.get("on_information_loss_or_noninjectivity") == "OPEN_OR_AMBIGUOUS", "RETROSPECTIVE_LOSS_BOUNDARY_DRIFT")
    physical = requirements.get("spacetime_or_physical_claim")
    require(isinstance(physical, dict), "PHYSICAL_REQUIREMENTS_MISSING")
    required_physical = {"dimension_model", "coordinate_or_unit_mapping", "calibration", "observable_prediction", "measurement_protocol", "uncertainty", "controls_or_replication"}
    require(required_physical == set(unique_string_list(physical.get("requires_for_empirical_class"), "PHYSICAL_EMPIRICAL_REQUIREMENTS", nonempty=True)), "PHYSICAL_EMPIRICAL_REQUIREMENTS_DRIFT")
    kind_rules = requirements.get("claim_kinds")
    require(isinstance(kind_rules, list) and kind_rules, "ARGUMENT_KIND_REQUIREMENTS_MISSING")
    rules_by_kind: dict[str, Mapping[str, Any]] = {}
    for index, rule in enumerate(kind_rules):
        require(isinstance(rule, dict), f"ARGUMENT_KIND_REQUIREMENT_{index}_MALFORMED")
        kind = rule.get("kind")
        require(isinstance(kind, str) and kind in ARGUMENT_KINDS, f"ARGUMENT_KIND_REQUIREMENT_{index}_INVALID")
        require(kind not in rules_by_kind, f"ARGUMENT_KIND_REQUIREMENT_{kind}_DUPLICATE")
        classifications = set(
            unique_string_list(
                rule.get("allowed_classifications"),
                f"ARGUMENT_KIND_REQUIREMENT_{kind}_CLASSIFICATIONS",
                nonempty=True,
            )
        )
        require(classifications.issubset(EXPECTED_CLASSES), f"ARGUMENT_KIND_REQUIREMENT_{kind}_CLASSIFICATION_INVALID")
        evidence_binding = rule.get("evidence_binding")
        require(isinstance(evidence_binding, str) and evidence_binding, f"ARGUMENT_KIND_REQUIREMENT_{kind}_BINDING_INVALID")
        rules_by_kind[kind] = rule
    require(set(rules_by_kind) == ARGUMENT_KINDS, "ARGUMENT_KIND_REQUIREMENTS_INCOMPLETE")
    require(rules_by_kind["OWNER_ASSERTION"].get("allowed_classifications") == ["SOURCE_BOUND"], "OWNER_ASSERTION_CLASSIFICATION_DRIFT")
    require(rules_by_kind["EMPIRICAL_PHYSICAL_CLAIM"].get("allowed_classifications") == ["EMPIRICALLY_EVIDENCED"], "EMPIRICAL_PHYSICAL_CLASSIFICATION_DRIFT")
    require(
        set(unique_string_list(
            rules_by_kind["EMPIRICAL_PHYSICAL_CLAIM"].get("required_measurement_fields"),
            "EMPIRICAL_PHYSICAL_TYPED_FIELDS",
            nonempty=True,
        )) == required_physical,
        "EMPIRICAL_PHYSICAL_TYPED_FIELDS_DRIFT",
    )
    return rules_by_kind


def source_binding_index(contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    bindings = contract.get("source_bindings")
    require(isinstance(bindings, list), "SOURCE_BINDINGS_MISSING")
    return {str(binding["path"]): binding for binding in bindings if isinstance(binding, dict) and "path" in binding}


def verify_evidence_catalog(
    contract: Mapping[str, Any],
    source_bindings: Mapping[str, Mapping[str, Any]],
    root: Path,
    *,
    verify_source_bytes: bool,
) -> dict[str, Mapping[str, Any]]:
    catalog = contract.get("evidence_catalog")
    require(isinstance(catalog, list) and catalog, "EVIDENCE_CATALOG_MISSING")
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, item in enumerate(catalog):
        require(isinstance(item, dict), f"EVIDENCE_CATALOG_{index}_MALFORMED")
        evidence_id = item.get("evidence_id")
        require(isinstance(evidence_id, str) and CLAIM_ID_RE.fullmatch(evidence_id) is not None, f"EVIDENCE_CATALOG_{index}_ID_INVALID")
        require(evidence_id not in by_id, f"EVIDENCE_CATALOG_{evidence_id}_DUPLICATE")
        kind = item.get("kind")
        require(kind in EVIDENCE_RECORD_KINDS, f"EVIDENCE_CATALOG_{evidence_id}_KIND_INVALID")
        if kind == SOURCE_EVIDENCE_KIND:
            source_path = item.get("source_binding_path")
            require(isinstance(source_path, str) and source_path in source_bindings, f"EVIDENCE_CATALOG_{evidence_id}_SOURCE_UNBOUND")
            require(isinstance(item.get("role"), str) and item["role"], f"EVIDENCE_CATALOG_{evidence_id}_ROLE_INVALID")
        else:
            unique_string_list(item.get("source_refs"), f"EVIDENCE_CATALOG_{evidence_id}_SOURCE_REFS", nonempty=True)
            require(isinstance(item.get("role"), str) and item["role"], f"EVIDENCE_CATALOG_{evidence_id}_ROLE_INVALID")
            require(isinstance(item.get("causal_bridge"), bool), f"EVIDENCE_CATALOG_{evidence_id}_CAUSAL_BRIDGE_INVALID")
            if kind == FORMAL_THEOREM_EVIDENCE_KIND:
                require(isinstance(item.get("theorem"), str) and item["theorem"], f"EVIDENCE_CATALOG_{evidence_id}_THEOREM_INVALID")
        by_id[evidence_id] = item
    for evidence_id, item in by_id.items():
        if item["kind"] == SOURCE_EVIDENCE_KIND:
            continue
        source_refs = unique_string_list(item["source_refs"], f"EVIDENCE_CATALOG_{evidence_id}_SOURCE_REFS", nonempty=True)
        require(all(ref in by_id and by_id[ref]["kind"] == SOURCE_EVIDENCE_KIND for ref in source_refs), f"EVIDENCE_CATALOG_{evidence_id}_SOURCE_REF_UNRESOLVED")
        if item["kind"] != FORMAL_THEOREM_EVIDENCE_KIND:
            continue
        receipt_refs = [ref for ref in source_refs if by_id[ref].get("role") == "FORMAL_KERNEL_RECEIPT"]
        require(len(receipt_refs) == 1, f"EVIDENCE_CATALOG_{evidence_id}_KERNEL_RECEIPT_MISSING")
        lean_refs = [ref for ref in source_refs if by_id[ref].get("role") == "FORMAL_CAUSALITY_SOURCE"]
        require(len(lean_refs) == 1, f"EVIDENCE_CATALOG_{evidence_id}_LEAN_SOURCE_MISSING")
        if verify_source_bytes:
            receipt_path = str(by_id[receipt_refs[0]]["source_binding_path"])
            authority = contract["authority_snapshot"]
            try:
                receipt = json.loads(
                    snapshot_bytes_at(root, str(authority["commit"]), receipt_path).decode("utf-8")
                )
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ContractError(f"EVIDENCE_CATALOG_{evidence_id}_RECEIPT_UNREADABLE") from exc
            require(isinstance(receipt, dict), f"EVIDENCE_CATALOG_{evidence_id}_RECEIPT_NOT_OBJECT")
            require(receipt.get("state") == "KERNEL_VERIFIED", f"EVIDENCE_CATALOG_{evidence_id}_KERNEL_NOT_VERIFIED")
            require(item["theorem"] in receipt.get("theorems", []), f"EVIDENCE_CATALOG_{evidence_id}_THEOREM_NOT_IN_RECEIPT")
            source = receipt.get("source_verification", {}).get("source", {})
            lean_path = str(by_id[lean_refs[0]]["source_binding_path"])
            require(source.get("git_blob_sha1") == source_bindings[lean_path].get("git_blob_sha1"), f"EVIDENCE_CATALOG_{evidence_id}_LEAN_BLOB_RECEIPT_MISMATCH")
            require(receipt.get("source_verification", {}).get("source_exit_code") == 0, f"EVIDENCE_CATALOG_{evidence_id}_SOURCE_EXIT_NONZERO")
            require(receipt.get("source_verification", {}).get("axiom_audit_exit_code") == 0, f"EVIDENCE_CATALOG_{evidence_id}_AXIOM_AUDIT_EXIT_NONZERO")
            require(receipt.get("project_axioms") == [], f"EVIDENCE_CATALOG_{evidence_id}_PROJECT_AXIOMS_PRESENT")
            axioms = receipt.get("axioms_by_theorem", {}).get(item["theorem"], [])
            allowed_axioms = set(receipt.get("allowed_foundational_axioms", []))
            require(isinstance(axioms, list) and set(axioms).issubset(allowed_axioms), f"EVIDENCE_CATALOG_{evidence_id}_AXIOM_POLICY_VIOLATION")
    return by_id


def resolve_evidence_refs(
    value: Any,
    label: str,
    catalog: Mapping[str, Mapping[str, Any]],
    *,
    allowed_kinds: set[str] | None = None,
    nonempty: bool = False,
) -> list[str]:
    refs = unique_string_list(value, label, nonempty=nonempty)
    for reference in refs:
        require(reference in catalog, f"{label}_UNRESOLVED: {reference}")
        if allowed_kinds is not None:
            require(catalog[reference].get("kind") in allowed_kinds, f"{label}_KIND_INVALID: {reference}")
    return refs


def resolve_source_ref(value: Any, label: str, catalog: Mapping[str, Mapping[str, Any]]) -> str:
    require(isinstance(value, str) and value, f"{label}_MISSING")
    require(value in catalog, f"{label}_UNRESOLVED")
    require(catalog[value].get("kind") == SOURCE_EVIDENCE_KIND, f"{label}_KIND_INVALID")
    return value


def verify_claim_kind_bindings(
    claim: Mapping[str, Any],
    catalog: Mapping[str, Mapping[str, Any]],
    kind_rules: Mapping[str, Mapping[str, Any]],
) -> set[str]:
    claim_id = str(claim["claim_id"])
    kinds = set(unique_string_list(claim.get("argument_kinds"), f"CLAIM_{claim_id}_ARGUMENT_KINDS", nonempty=True))
    require(kinds.issubset(ARGUMENT_KINDS), f"CLAIM_{claim_id}_ARGUMENT_KIND_INVALID")
    evidence_bindings = claim.get("evidence_bindings")
    require(isinstance(evidence_bindings, dict), f"CLAIM_{claim_id}_EVIDENCE_BINDINGS_MISSING")
    classification = str(claim["classification"])
    for kind in kinds:
        rule = kind_rules[kind]
        require(classification in rule["allowed_classifications"], f"CLAIM_{claim_id}_{kind}_CLASSIFICATION_INVALID")
        binding_name = str(rule["evidence_binding"])
        require(binding_name in evidence_bindings, f"CLAIM_{claim_id}_{kind}_EVIDENCE_MISSING")
        if kind == "CAUSAL_CLAIM":
            refs = resolve_evidence_refs(
                evidence_bindings[binding_name],
                f"CLAIM_{claim_id}_CAUSAL_JUSTIFICATION",
                catalog,
                allowed_kinds=CAUSAL_EVIDENCE_KINDS,
                nonempty=True,
            )
            require(any(catalog[ref].get("causal_bridge") is True for ref in refs), f"CAUSALITY_ONLY_SEQUENCE: {claim_id}")
        elif kind == "RECONSTRUCTION_CLAIM":
            requirements = evidence_bindings[binding_name]
            require(isinstance(requirements, dict), f"CLAIM_{claim_id}_RECONSTRUCTION_EVIDENCE_INVALID")
            expected = {"complete_manifest_source", "content_hashes_source", "semantic_dependency_order_source", "conflict_rule_source"}
            require(set(requirements) == expected, f"CLAIM_{claim_id}_RECONSTRUCTION_EVIDENCE_INCOMPLETE")
            for field, reference in requirements.items():
                resolve_source_ref(reference, f"CLAIM_{claim_id}_{field.upper()}", catalog)
        elif kind == "RETROSPECTIVE_DETERMINISM_CLAIM":
            requirements = evidence_bindings[binding_name]
            require(isinstance(requirements, dict), f"CLAIM_{claim_id}_RETROSPECTIVE_EVIDENCE_INVALID")
            expected = {"complete_immutable_provenance_source", "inverse_or_injectivity_source", "on_information_loss_or_noninjectivity"}
            require(set(requirements) == expected, f"CLAIM_{claim_id}_RETROSPECTIVE_EVIDENCE_INCOMPLETE")
            resolve_source_ref(requirements["complete_immutable_provenance_source"], f"CLAIM_{claim_id}_PROVENANCE_SOURCE", catalog)
            resolve_source_ref(requirements["inverse_or_injectivity_source"], f"CLAIM_{claim_id}_INJECTIVITY_SOURCE", catalog)
            require(requirements["on_information_loss_or_noninjectivity"] == "OPEN_OR_AMBIGUOUS", f"CLAIM_{claim_id}_RETROSPECTIVE_LOSS_BOUNDARY_DRIFT")
        elif kind == "OWNER_ASSERTION":
            attribution = evidence_bindings[binding_name]
            require(isinstance(attribution, dict), f"CLAIM_{claim_id}_OWNER_ATTRIBUTION_INVALID")
            require(attribution.get("actor") == "Ingolf Lohmann", f"CLAIM_{claim_id}_OWNER_ATTRIBUTION_DRIFT")
            resolve_evidence_refs(
                attribution.get("attribution_source_refs"),
                f"CLAIM_{claim_id}_OWNER_ATTRIBUTION_SOURCES",
                catalog,
                allowed_kinds={SOURCE_EVIDENCE_KIND},
                nonempty=True,
            )
            require(attribution.get("independent_empirical_confirmation_inferred") is False, f"CLAIM_{claim_id}_OWNER_CONFIRMATION_INFERRED")
            require(attribution.get("scientific_consensus_inferred") is False, f"CLAIM_{claim_id}_OWNER_CONSENSUS_INFERRED")
        elif kind == "SPACETIME_DIMENSIONAL_CLAIM":
            dimensional = evidence_bindings[binding_name]
            require(isinstance(dimensional, dict), f"CLAIM_{claim_id}_DIMENSIONAL_EVIDENCE_INVALID")
            expected = {"dimension_model_source", "coordinate_or_unit_mapping_source", "empirical_physical_effect_asserted"}
            require(set(dimensional) == expected, f"CLAIM_{claim_id}_DIMENSIONAL_EVIDENCE_INCOMPLETE")
            resolve_source_ref(dimensional["dimension_model_source"], f"CLAIM_{claim_id}_DIMENSION_SOURCE", catalog)
            resolve_source_ref(dimensional["coordinate_or_unit_mapping_source"], f"CLAIM_{claim_id}_COORDINATE_SOURCE", catalog)
            require(dimensional["empirical_physical_effect_asserted"] is False, f"CLAIM_{claim_id}_DIMENSIONAL_EFFECT_INFERRED")
        elif kind == "EMPIRICAL_PHYSICAL_CLAIM":
            measurement = evidence_bindings[binding_name]
            require(isinstance(measurement, dict), f"CLAIM_{claim_id}_PHYSICAL_EVIDENCE_INVALID")
            expected = set(unique_string_list(contract_physical_fields(kind_rules), "PHYSICAL_EMPIRICAL_REQUIREMENTS", nonempty=True))
            require(set(measurement) == expected, f"CLAIM_{claim_id}_PHYSICAL_EVIDENCE_INCOMPLETE")
            for field, references in measurement.items():
                resolve_evidence_refs(references, f"CLAIM_{claim_id}_{field.upper()}", catalog, nonempty=True)
    return kinds


def contract_physical_fields(kind_rules: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Return the physical-evidence fields carried by the typed rule itself."""

    rule = kind_rules["EMPIRICAL_PHYSICAL_CLAIM"]
    return list(rule.get("required_measurement_fields", []))


def verify_claims(
    contract: Mapping[str, Any],
    catalog: Mapping[str, Mapping[str, Any]],
    kind_rules: Mapping[str, Mapping[str, Any]],
) -> int:
    claims = contract.get("claims")
    require(isinstance(claims, list) and claims, "CANONICAL_CLAIMS_MISSING")
    claim_ids: set[str] = set()
    expected_owner_claim = False
    expected_causal_claim = False
    for index, claim in enumerate(claims):
        require(isinstance(claim, dict), f"CLAIM_{index}_MALFORMED")
        require(REQUIRED_ARGUMENT_FIELDS.issubset(claim), f"CLAIM_{index}_FIELDS_MISSING")
        claim_id = claim.get("claim_id")
        require(isinstance(claim_id, str) and CLAIM_ID_RE.fullmatch(claim_id) is not None, f"CLAIM_{index}_ID_INVALID")
        require(claim_id not in claim_ids, f"CLAIM_{index}_ID_DUPLICATE")
        claim_ids.add(claim_id)
        classification = claim.get("classification")
        require(classification in EXPECTED_CLASSES, f"CLAIM_{claim_id}_CLASSIFICATION_INVALID")
        require((claim.get("status"), claim.get("publication_wording")) == EXPECTED_CLASSES[classification], f"CLAIM_{claim_id}_DISPOSITION_DRIFT")
        for field in ("statement", "scope"):
            require(isinstance(claim.get(field), str) and len(claim[field].strip()) >= 12, f"CLAIM_{claim_id}_{field.upper()}_INVALID")
        for field in ("assumptions", "guarded_inferences"):
            unique_string_list(claim.get(field), f"CLAIM_{claim_id}_{field.upper()}")
        proof_refs = resolve_evidence_refs(
            claim.get("proof_refs"),
            f"CLAIM_{claim_id}_PROOF_REFS",
            catalog,
            allowed_kinds={FORMAL_THEOREM_EVIDENCE_KIND},
        )
        resolve_evidence_refs(claim.get("evidence_refs"), f"CLAIM_{claim_id}_EVIDENCE_REFS", catalog)
        source_refs = resolve_evidence_refs(
            claim.get("source_refs"),
            f"CLAIM_{claim_id}_SOURCE_REFS",
            catalog,
            allowed_kinds={SOURCE_EVIDENCE_KIND},
            nonempty=classification in {"FORMAL_PROVED", "EMPIRICALLY_EVIDENCED", "SOURCE_BOUND"},
        )
        binding = claim.get("binding")
        require(isinstance(binding, dict), f"CLAIM_{claim_id}_BINDING_MISSING")
        require(binding.get("kind") == "SOURCE_SNAPSHOT", f"CLAIM_{claim_id}_BINDING_KIND_DRIFT")
        require(isinstance(binding.get("requires_current_reobservation_for_dynamic_use"), bool), f"CLAIM_{claim_id}_REOBSERVATION_FLAG_INVALID")
        if classification == "FORMAL_PROVED":
            require(bool(proof_refs), f"FORMAL_PROOF_UNBOUND: {claim_id}")
            proof_sources = {
                source_ref
                for proof_ref in proof_refs
                for source_ref in catalog[proof_ref].get("source_refs", [])
            }
            require(proof_sources.issubset(set(source_refs)), f"FORMAL_PROOF_SOURCE_UNBOUND: {claim_id}")
        if classification == "SOURCE_BOUND":
            require(bool(source_refs), f"SOURCE_BINDING_MISSING: {claim_id}")
        kinds = verify_claim_kind_bindings(claim, catalog, kind_rules)
        if claim_id == "QIKVRT-CAUSALITY-BRIDGE-V1":
            expected_causal_claim = classification == "FORMAL_PROVED" and bool(proof_refs) and "CAUSAL_CLAIM" in kinds
        if claim_id == "QIKVRT-OWNER-REALITY-CORRESPONDENCE-V1":
            expected_owner_claim = (
                classification == "SOURCE_BOUND"
                and claim.get("status") == "BOUND"
                and "OWNER_ASSERTION" in kinds
                and "Product Owner Ingolf Lohmann explicitly asserts" in claim.get("statement", "")
            )
    require(expected_causal_claim, "CANONICAL_CAUSALITY_CLAIM_MISSING")
    require(expected_owner_claim, "OWNER_ASSERTED_REALITY_CORRESPONDENCE_MISSING_OR_RECLASSIFIED")
    return len(claims)


def verify_entrypoint_navigation(contract: Mapping[str, Any], root: Path) -> None:
    entrypoint = contract.get("canonical_entrypoint")
    require(isinstance(entrypoint, dict), "CANONICAL_ENTRYPOINT_MISSING")
    require(entrypoint.get("repository_path") == "AI", "CANONICAL_ENTRYPOINT_PATH_DRIFT")
    require(entrypoint.get("machine_contract") == "policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json", "CANONICAL_MACHINE_CONTRACT_DRIFT")
    require(entrypoint.get("human_contract") == "docs/CANONICAL_ARGUMENTATION_ENTRYPOINT.md", "CANONICAL_HUMAN_CONTRACT_DRIFT")
    require(entrypoint.get("claim_registry") == "policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json#/claims", "CANONICAL_CLAIM_REGISTRY_DRIFT")
    require(entrypoint.get("unregistered_argument_state") == "BLOCKED_UNTIL_REGISTERED_CLASSIFIED_AND_BOUND", "CANONICAL_UNREGISTERED_ARGUMENT_BOUNDARY_DRIFT")
    require(entrypoint.get("validator_command") == "python3 -B tools/qikvrt_canonical_argumentation_entrypoint.py check", "CANONICAL_VALIDATOR_COMMAND_DRIFT")
    require(entrypoint.get("mandatory_before_new_argument") is True, "CANONICAL_ENTRYPOINT_NOT_MANDATORY")

    for relative, fragments in {
        "AI": ["CANONICAL ARGUMENTATION ENTRYPOINT", "policy/CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json", "tools/qikvrt_canonical_argumentation_entrypoint.py check", "BLOCKED_UNTIL_REGISTERED_CLASSIFIED_AND_BOUND"],
        "README.md": ["Canonical argumentation entrypoint", "docs/CANONICAL_ARGUMENTATION_ENTRYPOINT.md"],
        "docs/CURRENT_AUTHORITY.md": ["Canonical argumentation entrypoint", "CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json"],
        "docs/AI_BOOTSTRAP_KNOWLEDGE_CORPUS.md": ["Canonical argumentation entrypoint", "CANONICAL_ARGUMENTATION_ENTRYPOINT_V1.json"],
    }.items():
        text = (root / relative).read_text(encoding="utf-8")
        for fragment in fragments:
            require(fragment in text, f"ENTRYPOINT_NAVIGATION_MISSING: {relative}: {fragment}")

    context = load_json_object(root / "AI_CONTEXT.json")
    context_entrypoint = context.get("canonical_argumentation_entrypoint")
    require(isinstance(context_entrypoint, dict), "AI_CONTEXT_ARGUMENTATION_ENTRYPOINT_MISSING")
    require(context_entrypoint.get("machine_contract") == entrypoint["machine_contract"], "AI_CONTEXT_ARGUMENTATION_CONTRACT_DRIFT")
    require(context_entrypoint.get("validator") == "tools/qikvrt_canonical_argumentation_entrypoint.py", "AI_CONTEXT_ARGUMENTATION_VALIDATOR_DRIFT")
    required_order = context.get("required_read_order")
    require(isinstance(required_order, list), "AI_CONTEXT_REQUIRED_READ_ORDER_MISSING")
    for path in (entrypoint["human_contract"], entrypoint["machine_contract"]):
        require(path in required_order, f"AI_CONTEXT_ARGUMENTATION_READ_ORDER_MISSING: {path}")
    boot = context.get("runtime_bootloader")
    require(isinstance(boot, dict), "AI_CONTEXT_BOOTLOADER_MISSING")
    require("tools/qikvrt_canonical_argumentation_entrypoint.py" in boot.get("reused_authorities", []), "AI_CONTEXT_ARGUMENTATION_GATE_UNBOUND")


def verify_effect_boundary(contract: Mapping[str, Any]) -> None:
    distinctions = set(unique_string_list(contract.get("protected_distinctions"), "PROTECTED_DISTINCTIONS", nonempty=True))
    require(REQUIRED_DISTINCTIONS.issubset(distinctions), "PROTECTED_DISTINCTIONS_INCOMPLETE")
    boundary = contract.get("effect_boundary")
    require(isinstance(boundary, dict), "EFFECT_BOUNDARY_MISSING")
    for name in ("transport_ack_is_effect_ack", "repository_test_is_external_effect", "zenodo_record_is_peer_review", "independent_empirical_confirmation_inferred", "scientific_consensus_inferred", "PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
        require(boundary.get(name) is False, f"EFFECT_BOUNDARY_DRIFT: {name}")


def validate_contract(
    contract: Mapping[str, Any],
    root: Path = ROOT,
    *,
    verify_source_bytes: bool = True,
    verify_git_snapshot: bool = True,
    verify_navigation: bool = True,
) -> dict[str, Any]:
    """Validate a loaded contract and return only contract-scope facts.

    The keyword switches exist for focused negative unit tests; the command-line
    checker always verifies every source, snapshot, and navigation binding.
    """

    require(contract.get("schema") == EXPECTED_SCHEMA, "CONTRACT_SCHEMA_DRIFT")
    require(contract.get("contract_id") == EXPECTED_CONTRACT_ID, "CONTRACT_ID_DRIFT")
    require(contract.get("version") == "1.0.0", "CONTRACT_VERSION_DRIFT")
    verify_class_projection(contract)
    verify_authority_snapshot(contract, root, verify_git=verify_git_snapshot)
    verify_dynamic_non_transfer(contract)
    source_count = (
        verify_source_bindings(contract, root, verify_snapshot=verify_git_snapshot)
        if verify_source_bytes
        else 0
    )
    source_bindings = source_binding_index(contract)
    catalog = verify_evidence_catalog(
        contract,
        source_bindings,
        root,
        verify_source_bytes=verify_source_bytes,
    )
    kind_rules = verify_argument_requirements(contract)
    claim_count = verify_claims(contract, catalog, kind_rules)
    if verify_navigation:
        verify_entrypoint_navigation(contract, root)
    verify_effect_boundary(contract)
    enforcement = contract.get("enforcement")
    require(isinstance(enforcement, dict) and enforcement.get("fail_closed") is True, "ENFORCEMENT_NOT_FAIL_CLOSED")
    require(enforcement.get("validator") == "tools/qikvrt_canonical_argumentation_entrypoint.py", "ENFORCEMENT_VALIDATOR_DRIFT")
    require(enforcement.get("bootstrap_gate") == "tools/ai_runtime_bootloader.py", "ENFORCEMENT_BOOTSTRAP_GATE_DRIFT")
    return {
        "state": "ARGUMENTATION_CONTRACT_VALID",
        "contract_id": contract["contract_id"],
        "version": contract["version"],
        "source_binding_count": source_count,
        "claim_count": claim_count,
        "effect_boundary": deepcopy(contract["effect_boundary"]),
        "scope": "CANONICAL_ARGUMENTATION_CONTRACT_ONLY",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check",), help="read-only validation command")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT, help="contract JSON path")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable result")
    args = parser.parse_args(argv)
    contract_path = args.contract if args.contract.is_absolute() else ROOT / args.contract
    try:
        result = validate_contract(load_json_object(contract_path), ROOT)
    except (ContractError, OSError, subprocess.SubprocessError) as exc:
        result = {
            "state": "ARGUMENTATION_CONTRACT_BLOCKED",
            "scope": "CANONICAL_ARGUMENTATION_CONTRACT_ONLY",
            "blocker": str(exc),
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        }
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"STATE={result['state']}")
            print(f"BLOCKER={result['blocker']}")
        return 2
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"STATE={result['state']}")
        print(f"CONTRACT_ID={result['contract_id']}")
        print(f"SOURCE_BINDINGS={result['source_binding_count']}")
        print(f"CLAIMS={result['claim_count']}")
        print("PASS=NOT_CLAIMED")
        print("FINAL_PASS=NOT_CLAIMED")
        print("EFFECT_ACK_DONE=NOT_CLAIMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
