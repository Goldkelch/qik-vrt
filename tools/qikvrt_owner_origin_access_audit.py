#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed owner-origin, access, provenance and license-evidence audit."""
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
ARTIFACT_SCHEMA = "qikvrt_owner_access_artifact_manifest_v1"
EVIDENCE_SCHEMA = "qikvrt_license_evidence_observation_v1"
WORK_UNIT_SCHEMA = "qikvrt_po_receipt_251_owner_origin_access_audit_v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ROLES = {"AUTHORITY", "MIRROR", "MESH_NODE", "CHATGPT_PROFILE_EXPORT", "EXTERNAL_TOOL_OUTPUT"}


class AuditError(ValueError):
    """Raised when the contract cannot be verified without assumption."""


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def policy_path() -> pathlib.Path:
    return repository_root() / "policy" / "OWNER_ORIGIN_ACCESS_AUDIT_AND_ENFORCEMENT_V1.json"


def work_unit_path() -> pathlib.Path:
    return repository_root() / "state" / "work_units" / "PO_RECEIPT_251_OWNER_ORIGIN_ACCESS_AUDIT_V1.json"


def load_json(path: pathlib.Path | str) -> dict[str, Any]:
    value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AuditError(f"{path} root must be an object")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AuditError(f"{name} must be an object")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise AuditError(f"{name} must be an array")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditError(f"{name} must be non-empty text")
    return value


def _sha256(value: Any, name: str) -> str:
    text = _text(value, name)
    if not SHA256_RE.fullmatch(text):
        raise AuditError(f"{name} must be lowercase SHA-256")
    return text


def validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    if policy.get("schema") != POLICY_SCHEMA:
        raise AuditError(f"policy schema must be {POLICY_SCHEMA}")
    origin = _mapping(policy.get("origin_principal"), "origin_principal")
    if origin.get("stable_id") != "Ingolf Lohmann":
        raise AuditError("origin principal must remain Ingolf Lohmann")
    roles = set(_sequence(origin.get("roles"), "origin_principal.roles"))
    if roles != {"HUMAN_ORIGIN_PRINCIPAL", "PRODUCT_OWNER"}:
        raise AuditError("origin roles changed")
    if origin.get("tool_assistance_erases_human_provenance") is not False:
        raise AuditError("tool assistance may not erase human provenance")
    if origin.get("statutory_copyright_status") != "ARTIFACT_AND_JURISDICTION_SPECIFIC":
        raise AuditError("copyright status must remain artifact- and jurisdiction-specific")

    orientation = _mapping(policy.get("normative_orientation"), "normative_orientation")
    if orientation.get("owner_declared_natural_language_count") != 47:
        raise AuditError("owner-declared natural-language count must remain 47")
    for key in (
        "natural_language_support_verified_by_this_policy",
        "translation_creates_jurisdictional_legal_effect",
        "translation_eliminates_legal_defences",
        "legal_compliance_inferred",
        "legal_advice",
    ):
        if orientation.get(key) is not False:
            raise AuditError(f"normative_orientation.{key} must remain false")

    hierarchy = _mapping(policy.get("mesh_role_hierarchy"), "mesh_role_hierarchy")
    if hierarchy.get("authority_mirror_and_node_roles_are_interchangeable") is not False:
        raise AuditError("mesh roles may not collapse")
    if hierarchy.get("role_identity_must_not_collapse") is not True:
        raise AuditError("role-local identity must remain explicit")

    access = _mapping(policy.get("owner_access_invariant"), "owner_access_invariant")
    required = set(_sequence(access.get("required_artifact_fields"), "required_artifact_fields"))
    expected = {
        "artifact_id", "work_unit_id", "origin_principal", "authority_repository",
        "repository_role", "source_sha256", "output_sha256", "open_representation",
        "access_paths", "provenance", "license",
    }
    if required != expected:
        raise AuditError("required artifact field set changed")
    for key in (
        "single_ephemeral_ui_only",
        "single_expiring_actions_artifact_only",
        "undocumented_proprietary_format_only",
        "closed_pull_request_as_only_locator",
        "bot_commit_may_erase_origin_principal",
        "third_party_platform_perpetual_availability_guaranteed",
        "access_failure_transfers_rights",
        "access_failure_erases_provenance",
        "access_failure_requires_content_recreation",
    ):
        if access.get(key) is not False:
            raise AuditError(f"owner_access_invariant.{key} must remain false")

    automated = _mapping(policy.get("automated_actions"), "automated_actions")
    forbidden = set(_sequence(automated.get("forbidden_without_separate_exact_authority"), "forbidden actions"))
    required_forbidden = {
        "PUBLIC_ACCUSATION", "CEASE_AND_DESIST_NOTICE", "PAYMENT_DEMAND", "INVOICE",
        "DAMAGES_CALCULATION_AS_FACT", "REGULATORY_COMPLAINT", "COURT_FILING",
        "RIGHTS_TRANSFER", "LICENSE_CHANGE", "DISCLOSURE_OF_CREDENTIALS_OR_PRIVATE_DATA",
    }
    if not required_forbidden.issubset(forbidden):
        raise AuditError("external legal and rights-changing actions are not fully blocked")

    gate = _mapping(policy.get("legal_action_gate"), "legal_action_gate")
    if gate.get("external_legal_action_authorized_by_this_policy") is not False:
        raise AuditError("policy must not authorize external legal action")

    claims = _mapping(policy.get("release_claims"), "release_claims")
    if any(value is not False for value in claims.values()):
        raise AuditError("release claims must remain false")
    return {
        "schema": POLICY_SCHEMA,
        "origin_principal": "Ingolf Lohmann",
        "owner_access_invariant": "BOUND",
        "role_local_hierarchy": "BOUND",
        "automated_external_legal_action": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def validate_artifact_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if manifest.get("schema") != ARTIFACT_SCHEMA:
        raise AuditError(f"artifact schema must be {ARTIFACT_SCHEMA}")
    for key in (
        "artifact_id", "work_unit_id", "origin_principal", "authority_repository",
        "repository_role", "source_sha256", "output_sha256", "open_representation",
        "access_paths", "provenance", "license",
    ):
        if key not in manifest:
            raise AuditError(f"artifact manifest missing {key}")
    if manifest.get("origin_principal") != "Ingolf Lohmann":
        raise AuditError("artifact origin principal changed")
    if manifest.get("authority_repository") != "Goldkelch/qik-vrt":
        raise AuditError("authority repository changed")
    role = _text(manifest.get("repository_role"), "repository_role")
    if role not in ROLES:
        raise AuditError("unsupported repository role")
    if role == "MIRROR" and manifest.get("canonical_authority_claimed") is not False:
        raise AuditError("Mirror may not claim canonical Authority")
    _sha256(manifest.get("source_sha256"), "source_sha256")
    _sha256(manifest.get("output_sha256"), "output_sha256")

    representation = _mapping(manifest.get("open_representation"), "open_representation")
    for key in ("format", "stable_locator"):
        _text(representation.get(key), f"open_representation.{key}")
    for key in ("owner_openable", "exportable", "reconstructable", "decoder_documented"):
        if representation.get(key) is not True:
            raise AuditError(f"open_representation.{key} must be true")

    access_paths = _sequence(manifest.get("access_paths"), "access_paths")
    if not access_paths:
        raise AuditError("at least one access path is required")
    owner_paths = []
    durable_paths = []
    for index, item in enumerate(access_paths):
        path = _mapping(item, f"access_paths[{index}]")
        _text(path.get("locator"), f"access_paths[{index}].locator")
        if path.get("owner_accessible") is True:
            owner_paths.append(path)
        if path.get("expiring") is False:
            durable_paths.append(path)
    if not owner_paths:
        raise AuditError("no owner-accessible path")
    if not durable_paths:
        raise AuditError("only expiring access paths are present")

    provenance = _mapping(manifest.get("provenance"), "provenance")
    if provenance.get("human_origin_principal") != "Ingolf Lohmann":
        raise AuditError("human origin is absent from provenance")
    tools = _sequence(provenance.get("tool_contributions"), "provenance.tool_contributions")
    if not tools:
        raise AuditError("tool contributions must be separately declared")
    if provenance.get("human_and_tool_contributions_separable") is not True:
        raise AuditError("human and tool contributions are not separable")

    license_info = _mapping(manifest.get("license"), "license")
    _text(license_info.get("id"), "license.id")
    _text(license_info.get("source"), "license.source")
    if license_info.get("legal_compliance_inferred") is not False:
        raise AuditError("artifact manifest may not infer legal compliance")

    return {
        "schema": "qikvrt_owner_access_artifact_audit_receipt_v1",
        "artifact_id": manifest["artifact_id"],
        "access_state": "OWNER_ACCESS_CONTRACT_SATISFIED",
        "repository_role": role,
        "owner_accessible_path_count": len(owner_paths),
        "durable_path_count": len(durable_paths),
        "legal_violation_asserted": False,
        "external_effect": False,
    }


def classify_license_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if evidence.get("schema") != EVIDENCE_SCHEMA:
        raise AuditError(f"evidence schema must be {EVIDENCE_SCHEMA}")
    state: str
    if evidence.get("artifact_bytes_verified") is not True:
        state = "NO_BYTE_IDENTITY"
    elif evidence.get("provenance_verified") is not True:
        state = "PROVENANCE_UNVERIFIED"
    elif evidence.get("license_text_bound") is not True:
        state = "LICENSE_SCOPE_UNBOUND"
    else:
        authorization = evidence.get("authorization_status")
        if authorization == "AUTHORIZED":
            state = "LICENSE_COMPATIBLE"
        elif authorization == "UNKNOWN":
            state = "POTENTIAL_VIOLATION_UNVERIFIED"
        elif authorization == "NOT_AUTHORIZED":
            exact = all(
                evidence.get(key) is True
                for key in (
                    "actor_identity_verified",
                    "conduct_verified",
                    "jurisdiction_bound",
                    "exact_license_version_bound",
                    "authorization_status_evidenced",
                )
            )
            state = "EVIDENCED_BREACH_CANDIDATE_INTERNAL_ONLY" if exact else "POTENTIAL_VIOLATION_UNVERIFIED"
        else:
            raise AuditError("authorization_status must be AUTHORIZED, UNKNOWN or NOT_AUTHORIZED")
    return {
        "schema": "qikvrt_license_evidence_classification_receipt_v1",
        "state": state,
        "legal_violation_asserted": False,
        "public_accusation_permitted": False,
        "external_notice_permitted": False,
        "damages_claim_permitted": False,
        "court_or_regulatory_filing_permitted": False,
        "owner_or_authorized_counsel_decision_required": state == "EVIDENCED_BREACH_CANDIDATE_INTERNAL_ONLY",
        "external_effect": False,
    }


def validate_work_unit(work_unit: Mapping[str, Any]) -> dict[str, Any]:
    if work_unit.get("schema") != WORK_UNIT_SCHEMA:
        raise AuditError(f"work-unit schema must be {WORK_UNIT_SCHEMA}")
    if work_unit.get("predecessor_evidence_transfer") is not False:
        raise AuditError("predecessor evidence may not transfer")
    sources = _sequence(work_unit.get("source_audio"), "source_audio")
    expected = {
        "AUDIO-2026-08-22-14-50-33.m4a": (1231890, 149.312, "9cf22fbea288975486c8bad0c6f60d0bd2c807512061e3313a1c7f52bb0a5892"),
        "AUDIO-2026-08-22-14-52-57.m4a": (884909, 105.024, "f0fa35219b40243b5dba23d30c0d3b37097f796055a06e0bda2875177dbab69f"),
    }
    observed = {}
    for item in sources:
        source = _mapping(item, "source_audio item")
        name = _text(source.get("file_name"), "source_audio.file_name")
        observed[name] = (source.get("bytes"), source.get("duration_seconds"), _sha256(source.get("sha256"), "source_audio.sha256"))
    if observed != expected:
        raise AuditError("source audio binding changed")
    transcription = _mapping(work_unit.get("transcription"), "transcription")
    if transcription.get("raw_audio_committed") is not False:
        raise AuditError("raw owner audio must not be committed")
    if transcription.get("verbatim_transcript_published") is not False:
        raise AuditError("verbatim owner transcript must not be published")
    if transcription.get("asr_output_is_not_verbatim_proof") is not True:
        raise AuditError("ASR boundary changed")
    semantic = set(_sequence(work_unit.get("semantic_bindings"), "semantic_bindings"))
    if "AUTOMATED_PUBLIC_ACCUSATION_NOTICE_DEMAND_OR_LAWSUIT_IS_NOT_AUTHORIZED" not in semantic:
        raise AuditError("external legal action boundary is absent")
    effects = _mapping(work_unit.get("external_effects"), "external_effects")
    if any(value is not False for value in effects.values()):
        raise AuditError("work unit must have no external effect")
    return {
        "schema": WORK_UNIT_SCHEMA,
        "source_count": len(sources),
        "source_hashes_bound": True,
        "raw_audio_committed": False,
        "verbatim_transcript_published": False,
        "external_effect": False,
    }


def self_check() -> dict[str, Any]:
    policy = validate_policy(load_json(policy_path()))
    work_unit = validate_work_unit(load_json(work_unit_path()))
    return {
        "schema": "qikvrt_owner_origin_access_audit_self_check_v1",
        "policy": policy,
        "work_unit": work_unit,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-check", action="store_true")
    group.add_argument("--artifact-manifest", type=pathlib.Path)
    group.add_argument("--license-evidence", type=pathlib.Path)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_check:
        result = self_check()
    elif args.artifact_manifest is not None:
        result = validate_artifact_manifest(load_json(args.artifact_manifest))
    else:
        result = classify_license_evidence(load_json(args.license_evidence))
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
