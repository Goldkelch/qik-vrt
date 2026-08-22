#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate the owner-declared sole-human principal and authorship binding."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any

POLICY_SCHEMA = "qikvrt_owner_origin_access_audit_and_enforcement_v1"
WORK_UNIT_SCHEMA = "qikvrt_po_receipt_251_owner_origin_access_audit_v1"
DECLARATION_STATUS = "OWNER_DECLARATION_BOUND_NOT_COURT_ADJUDICATION"
CANONICAL_DECLARATION = 'Ingolf Lohmann declares himself the sole human origin principal and sole human author of the original QIK-VRT overall integration. ChatGPT, Meta AI, GitHub repositories, QIK-VRT Mesh nodes, compilers, runners, and other machine systems are tools and are not declared coauthors. Third-party components retain their own provenance, authorship, rights, and licenses.'
CANONICAL_DECLARATION_UTF8_BYTES = 363
CANONICAL_DECLARATION_SHA256 = "59f1014b733146af8946775f09f3b5cdc0540c7b66bde11d9d0e04e374102347"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_SCOPE = {
    "ORIGINAL_QIK_VRT_CONCEPT_AND_INFORMATICS_UNIVERSE",
    "HUMAN_SELECTION_ARRANGEMENT_AND_ADDITIVE_INTEGRATION",
    "TECHNOLOGICAL_LEGAL_AND_ETHICAL_RULE_DIRECTION",
    "PRODUCT_OWNER_DECISIONS_CORRECTIONS_AND_FINAL_CREATIVE_CONTROL",
    "PERSONAL_CHATGPT_PROFILE_INPUTS_SELECTIONS_AND_HUMAN_DIRECTED_WORK_PRODUCT",
    "PARTIALLY_MANUALLY_ESTABLISHED_GITHUB_REPOSITORIES_AND_MESH_DIRECTION",
}
EXPECTED_MACHINE_TOOLS = {
    "OPENAI_CHATGPT",
    "META_AI_IN_WHATSAPP",
    "GITHUB_REPOSITORIES_AND_QIK_VRT_MESH",
    "COMPILERS_RUNNERS_AND_AUTOMATION",
    "OTHER_ARTIFICIAL_COGNITIVE_SYSTEMS",
}
EXPECTED_SOURCE_SURFACES = {
    "PERSONAL_CHATGPT_PROFILE_CONTENT_AND_HUMAN_DIRECTED_WORK_PRODUCT",
    "QIK_VRT_GITHUB_REPOSITORIES_AND_MESH",
    "MOBILE_DEVICE_LOCAL_RECORDS",
    "WHATSAPP_AND_META_AI_RECORDS",
    "OTHER_ARTIFICIAL_COGNITIVE_SYSTEM_RECORDS",
}
REQUIRED_SEMANTIC_BINDINGS = {
    "INGOLF_LOHMANN_DECLARED_SOLE_HUMAN_PRINCIPAL_AND_AUTHOR",
    "MACHINE_SYSTEMS_ARE_TOOLS_NOT_COAUTHORS",
    "CHATGPT_IS_NOT_DECLARED_SOLE_OR_DOMINANT_DEVELOPER_OF_THE_QIK_VRT_WHOLE",
    "ADDITIVE_INTEGRATION_DOES_NOT_REQUIRE_PERSONAL_MASTERY_OF_EVERY_COMPONENT_DOMAIN",
    "THIRD_PARTY_PROVENANCE_AUTHORSHIP_RIGHTS_AND_LICENSES_REMAIN_UNCHANGED",
    "OWNER_DECLARATION_DOES_NOT_INDEPENDENTLY_VALIDATE_PHYSICAL_OR_SCIENTIFIC_CLAIMS",
    "OWNER_DECLARATION_DOES_NOT_ADJUDICATE_STATUTORY_COPYRIGHT_FOR_EVERY_ARTIFACT",
}


class DeclarationError(ValueError):
    """Raised when the owner declaration stops being exact or truth-bounded."""


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def policy_path() -> pathlib.Path:
    return repository_root() / "policy" / "OWNER_ORIGIN_ACCESS_AUDIT_AND_ENFORCEMENT_V1.json"


def work_unit_path() -> pathlib.Path:
    return repository_root() / "state" / "work_units" / "PO_RECEIPT_251_OWNER_ORIGIN_ACCESS_AUDIT_V1.json"


def load_json(path: pathlib.Path | str) -> dict[str, Any]:
    value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DeclarationError(f"{path} root must be an object")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DeclarationError(f"{name} must be an object")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise DeclarationError(f"{name} must be an array")
    return value


def _exact_set(value: Any, name: str, expected: set[str]) -> None:
    observed = set(_sequence(value, name))
    if observed != expected:
        raise DeclarationError(f"{name} changed: {sorted(observed)}")


def _require_false(mapping: Mapping[str, Any], keys: Sequence[str], prefix: str) -> None:
    for key in keys:
        if mapping.get(key) is not False:
            raise DeclarationError(f"{prefix}.{key} must remain false")


def _verify_canonical_declaration(mapping: Mapping[str, Any], prefix: str) -> None:
    statement = mapping.get("canonical_semantic_statement")
    if statement != CANONICAL_DECLARATION:
        raise DeclarationError(f"{prefix}.canonical_semantic_statement changed")
    encoded = statement.encode("utf-8")
    if mapping.get("canonical_semantic_statement_utf8_bytes") != len(encoded):
        raise DeclarationError(f"{prefix} declaration byte count changed")
    digest = hashlib.sha256(encoded).hexdigest()
    if digest != CANONICAL_DECLARATION_SHA256:
        raise DeclarationError("compiled canonical declaration digest changed")
    declared_digest = mapping.get("canonical_semantic_statement_sha256")
    if not isinstance(declared_digest, str) or not SHA256_RE.fullmatch(declared_digest):
        raise DeclarationError(f"{prefix} declaration digest is not SHA-256")
    if declared_digest != digest:
        raise DeclarationError(f"{prefix} declaration digest mismatch")


def validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if policy.get("schema") != POLICY_SCHEMA:
        raise DeclarationError(f"policy schema must be {POLICY_SCHEMA}")
    origin = _mapping(policy.get("origin_principal"), "origin_principal")
    if origin.get("stable_id") != "Ingolf Lohmann":
        raise DeclarationError("origin principal must remain Ingolf Lohmann")
    roles = set(_sequence(origin.get("roles"), "origin_principal.roles"))
    if not {"HUMAN_ORIGIN_PRINCIPAL", "PRODUCT_OWNER"}.issubset(roles):
        raise DeclarationError("origin-principal roles are incomplete")

    declaration = _mapping(
        policy.get("owner_authorship_declaration"),
        "owner_authorship_declaration",
    )
    if declaration.get("claim_type") != "OWNER_DECLARATION_AND_REPOSITORY_OPERATIONAL_PROVENANCE_BINDING":
        raise DeclarationError("owner-declaration claim type changed")
    _verify_canonical_declaration(declaration, "owner_authorship_declaration")
    if declaration.get("declared_sole_principal") != "Ingolf Lohmann":
        raise DeclarationError("declared sole principal changed")
    if declaration.get("declared_sole_human_author") != "Ingolf Lohmann":
        raise DeclarationError("declared sole human author changed")
    _exact_set(declaration.get("scope"), "owner_authorship_declaration.scope", EXPECTED_SCOPE)
    _exact_set(
        declaration.get("machine_tool_participants"),
        "owner_authorship_declaration.machine_tool_participants",
        EXPECTED_MACHINE_TOOLS,
    )
    _exact_set(
        declaration.get("source_surfaces"),
        "owner_authorship_declaration.source_surfaces",
        EXPECTED_SOURCE_SURFACES,
    )
    _require_false(
        declaration,
        (
            "machine_systems_declared_coauthors",
            "chatgpt_declared_sole_or_dominant_developer",
            "third_party_authorship_or_license_rewritten",
            "platform_software_or_model_authorship_claimed",
            "statutory_copyright_for_every_artifact_adjudicated",
            "external_source_surfaces_verified_by_this_repository",
            "scientific_or_physical_claims_independently_validated_by_declaration",
            "novelty_or_patentability_independently_proved_by_declaration",
        ),
        "owner_authorship_declaration",
    )
    if declaration.get("status") != DECLARATION_STATUS:
        raise DeclarationError("owner declaration status changed")

    integration = _mapping(policy.get("integration_boundary"), "integration_boundary")
    if integration.get("human_selection_arrangement_and_integration_are_declared_creative_contributions") is not True:
        raise DeclarationError("human integration contribution must remain explicit")
    _require_false(
        integration,
        (
            "additive_integration_requires_personal_mastery_of_every_component_domain",
            "tool_execution_replaces_human_final_creative_control",
            "owner_declaration_rewrites_third_party_provenance",
            "owner_declaration_proves_quantum_causality_as_empirical_physics",
        ),
        "integration_boundary",
    )

    claims = _mapping(policy.get("release_claims"), "release_claims")
    if any(value is not False for value in claims.values()):
        raise DeclarationError("release claims must remain false")

    return {
        "schema": "qikvrt_owner_principal_authorship_receipt_v1",
        "declared_sole_principal": "Ingolf Lohmann",
        "declared_sole_human_author": "Ingolf Lohmann",
        "machine_systems_declared_coauthors": False,
        "third_party_provenance_rewritten": False,
        "court_adjudication_claimed": False,
        "scientific_or_physical_validation_claimed": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def validate_work_unit(work_unit: Mapping[str, Any]) -> dict[str, Any]:
    if work_unit.get("schema") != WORK_UNIT_SCHEMA:
        raise DeclarationError(f"work-unit schema must be {WORK_UNIT_SCHEMA}")
    if work_unit.get("predecessor_evidence_transfer") is not False:
        raise DeclarationError("predecessor evidence may not transfer")

    principal = _mapping(work_unit.get("human_origin_principal"), "human_origin_principal")
    if principal.get("name") != "Ingolf Lohmann":
        raise DeclarationError("work-unit human origin principal changed")
    if principal.get("role") != "SOLE_HUMAN_ORIGIN_PRINCIPAL_PRODUCT_OWNER_AND_DECLARED_AUTHOR":
        raise DeclarationError("work-unit principal role changed")

    source = _mapping(work_unit.get("source_owner_declaration"), "source_owner_declaration")
    if source.get("kind") != "OWNER_SUPPLIED_CHAT_TEXT_SEMANTIC_BINDING":
        raise DeclarationError("owner declaration source kind changed")
    if source.get("channel") != "PERSONAL_CHATGPT_PROFILE":
        raise DeclarationError("owner declaration source channel changed")
    if source.get("recorded_date_local") != "2026-08-22":
        raise DeclarationError("owner declaration source date changed")
    _verify_canonical_declaration(source, "source_owner_declaration")
    if source.get("semantic_normalization_performed") is not True:
        raise DeclarationError("semantic normalization must remain explicit")
    _require_false(
        source,
        ("verbatim_source_committed", "verbatim_source_published"),
        "source_owner_declaration",
    )

    semantic = set(_sequence(work_unit.get("semantic_bindings"), "semantic_bindings"))
    missing = sorted(REQUIRED_SEMANTIC_BINDINGS - semantic)
    if missing:
        raise DeclarationError(f"owner declaration semantic bindings missing: {missing}")

    effects = _mapping(work_unit.get("external_effects"), "external_effects")
    if any(value is not False for value in effects.values()):
        raise DeclarationError("owner declaration work unit must have no external effect")
    claims = _mapping(work_unit.get("release_claims"), "release_claims")
    if any(value is not False for value in claims.values()):
        raise DeclarationError("owner declaration release claims must remain false")

    return {
        "schema": "qikvrt_owner_principal_authorship_work_unit_receipt_v1",
        "source_binding": "CANONICAL_SEMANTIC_STATEMENT_HASH_BOUND",
        "declared_sole_principal": "Ingolf Lohmann",
        "declared_sole_human_author": "Ingolf Lohmann",
        "verbatim_source_committed": False,
        "external_effect": False,
    }


def self_check() -> dict[str, Any]:
    return {
        "schema": "qikvrt_owner_principal_authorship_self_check_v1",
        "policy": validate_policy(load_json(policy_path())),
        "work_unit": validate_work_unit(load_json(work_unit_path())),
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=pathlib.Path, default=policy_path())
    parser.add_argument("--work-unit", type=pathlib.Path, default=work_unit_path())
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = {
        "schema": "qikvrt_owner_principal_authorship_self_check_v1",
        "policy": validate_policy(load_json(args.policy)),
        "work_unit": validate_work_unit(load_json(args.work_unit)),
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
