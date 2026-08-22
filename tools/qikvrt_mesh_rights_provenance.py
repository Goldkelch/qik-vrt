#!/usr/bin/env python3
"""Fail-closed QIK-VRT Mesh provenance, notice and rights-boundary verifier.

This module verifies technical byte identity, repository role and declared
license-notice bindings. It deliberately does not adjudicate authorship,
copying, legal infringement, damages, standing, jurisdiction or remedies.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "policy" / "MESH_RIGHTS_PROVENANCE_AUDIT_V1.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    """Raised when a policy or evidence envelope is structurally invalid."""


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain a JSON object")
    return value


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    policy = load_json(path)
    validate_policy(policy)
    return policy


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be a list")
    return value


def _require_exact_set(actual: Any, expected: set[str], label: str) -> None:
    values = _require_list(actual, label)
    if set(values) != expected or len(values) != len(expected):
        raise ContractError(f"{label} differs from the required exact set")


def validate_policy(policy: Mapping[str, Any]) -> None:
    if policy.get("schema") != "QIKVRT_MESH_RIGHTS_PROVENANCE_AUDIT_V1":
        raise ContractError("unexpected policy schema")
    if policy.get("version") != "1.0.0":
        raise ContractError("unexpected policy version")
    if policy.get("status") != "HOLD_UNVERIFIED":
        raise ContractError("candidate policy must remain HOLD_UNVERIFIED")

    principles = _require_mapping(policy.get("principles"), "principles")
    if principles.get("categorical_imperative_role") != (
        "OWNER_ETHICAL_HEURISTIC_NOT_LEGAL_SUBSTITUTE"
    ):
        raise ContractError("categorical imperative must not replace applicable law")
    if principles.get("law_and_rights_override_automation") is not True:
        raise ContractError("law-and-rights override must be enabled")
    if principles.get("technical_role_hierarchy_is_not_human_hierarchy") is not True:
        raise ContractError("technical role hierarchy must not imply human hierarchy")

    roles = _require_mapping(policy.get("mesh_roles"), "mesh_roles")
    authority = _require_mapping(roles.get("authority"), "mesh_roles.authority")
    mirror = _require_mapping(roles.get("mirror"), "mesh_roles.mirror")
    if authority.get("repository") != "Goldkelch/qik-vrt":
        raise ContractError("authority repository is not canonical")
    if authority.get("role") != "AUTHORITY":
        raise ContractError("authority role mismatch")
    if authority.get("normative_policy_precedence") is not True:
        raise ContractError("authority normative precedence must remain explicit")
    if authority.get("human_superiority_inferred") is not False:
        raise ContractError("authority must not imply human superiority")
    if mirror.get("repository") != "ingolf-lohmann/qik-vrt":
        raise ContractError("mirror repository mismatch")
    if mirror.get("role") != "MIRROR":
        raise ContractError("mirror role mismatch")
    if mirror.get("may_override_authority_policy") is not False:
        raise ContractError("mirror must not override Authority policy")
    if mirror.get("must_bind_authority_source") is not True:
        raise ContractError("mirror must bind its Authority source")
    if mirror.get("human_subordination_inferred") is not False:
        raise ContractError("mirror role must not imply fewer human rights")

    evidence = _require_mapping(policy.get("artifact_evidence"), "artifact_evidence")
    required_fields = {
        "repository",
        "authority_source_repository",
        "head_sha",
        "tree_sha",
        "manifest_sha256",
        "license_map_sha256",
        "artifact_sha256",
        "path",
    }
    _require_exact_set(
        evidence.get("required_observed_fields"),
        required_fields,
        "artifact_evidence.required_observed_fields",
    )
    _require_exact_set(
        evidence.get("required_expected_fields"),
        required_fields,
        "artifact_evidence.required_expected_fields",
    )
    if evidence.get("accepted_license_resolution") != "EXACT_NOTICE_MATCH":
        raise ContractError("accepted license resolution must remain exact")
    _require_exact_set(
        evidence.get("accepted_requested_effects"),
        {"READ_ONLY_VERIFY", "EVIDENCE_BOUND_ALERT", "HOLD_FOR_REVIEW"},
        "artifact_evidence.accepted_requested_effects",
    )

    data = _require_mapping(policy.get("data_protection"), "data_protection")
    _require_exact_set(
        data.get("when_personal_data_present_require"),
        {
            "lawful_basis_bound",
            "purpose_bound",
            "data_minimized",
            "retention_bound",
            "access_controlled",
            "data_subject_rights_path_bound",
        },
        "data_protection.when_personal_data_present_require",
    )
    if data.get("raw_owner_audio_in_repository") is not False:
        raise ContractError("raw owner audio must not be ordinary repository content")
    if data.get("verbatim_owner_transcript_in_repository") is not False:
        raise ContractError("verbatim owner transcript must not be repository content")

    legal = _require_mapping(policy.get("legal_effect_boundary"), "legal_effect_boundary")
    forbidden = {
        "ASSERT_COPYING",
        "ASSERT_AUTHORSHIP",
        "ASSERT_LEGAL_INFRINGEMENT",
        "ASSERT_DAMAGES",
        "SEND_LEGAL_DEMAND",
        "REQUEST_TAKEDOWN",
        "FILE_LEGAL_CLAIM",
        "PUBLICLY_ACCUSING_A_PERSON_OR_ENTITY",
    }
    _require_exact_set(
        legal.get("forbidden_automatic_conclusions_or_effects"),
        forbidden,
        "legal_effect_boundary.forbidden_automatic_conclusions_or_effects",
    )

    language = _require_mapping(
        policy.get("language_and_jurisdiction_boundary"),
        "language_and_jurisdiction_boundary",
    )
    if language.get("owner_spoken_number") != 47:
        raise ContractError("owner-spoken number must remain exactly 47")
    if language.get("status") != "UNRESOLVED_DO_NOT_NORMALIZE_SILENTLY":
        raise ContractError("47-language/country scope must remain unresolved")

    non_equivalences = set(
        _require_list(policy.get("non_equivalences"), "non_equivalences")
    )
    mandatory = {
        "PROVENANCE_MATCH != AUTHORSHIP_PROOF",
        "LICENSE_MISMATCH != LEGAL_INFRINGEMENT",
        "REPOSITORY_RECEIPT != COURT_FINDING",
        "ETHICAL_HEURISTIC != APPLICABLE_LAW",
    }
    if not mandatory.issubset(non_equivalences):
        raise ContractError("mandatory legal and evidence boundaries are missing")

    closure = _require_mapping(policy.get("closure"), "closure")
    for key in ("pass", "final_pass", "merge_claimed", "effect_ack_done"):
        if closure.get(key) is not False:
            raise ContractError(f"closure.{key} must remain false")
    if closure.get("external_effect") != "NONE":
        raise ContractError("candidate policy cannot claim an external effect")


def _is_safe_path(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute():
        return False
    return all(part not in {"", ".", ".."} for part in path.parts)


def _valid_binding(field: str, value: Any) -> bool:
    if field in {"head_sha", "tree_sha"}:
        return isinstance(value, str) and HEX40.fullmatch(value) is not None
    if field in {"manifest_sha256", "license_map_sha256", "artifact_sha256"}:
        return isinstance(value, str) and HEX64.fullmatch(value) is not None
    if field == "path":
        return _is_safe_path(value)
    return isinstance(value, str) and bool(value)


def _role_for_repository(repository: str, policy: Mapping[str, Any]) -> str | None:
    roles = _require_mapping(policy["mesh_roles"], "mesh_roles")
    for item in (roles["authority"], roles["mirror"]):
        if repository == item["repository"]:
            return str(item["role"])
    return None


def _result(
    decision: str,
    *,
    role: str | None,
    mismatches: list[str] | None = None,
    missing_or_invalid: list[str] | None = None,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    verified = decision == "PROVENANCE_AND_NOTICE_MATCH_VERIFIED"
    return {
        "schema": "qikvrt_mesh_rights_provenance_receipt_v1",
        "decision": decision,
        "repository_role": role or "UNTRUSTED_OR_UNKNOWN",
        "technical_provenance_verified": verified,
        "declared_license_notice_match": verified,
        "normative_authority": role == "AUTHORITY",
        "technical_role_hierarchy_inferred": role in {"AUTHORITY", "MIRROR"},
        "human_hierarchy_inferred": False,
        "authorship_proven": False,
        "copying_determined": False,
        "legal_infringement_determined": False,
        "damages_determined": False,
        "rights_chain_judicially_proven": False,
        "court_finding": False,
        "external_effect": "NONE",
        "mismatches": sorted(mismatches or []),
        "missing_or_invalid": sorted(missing_or_invalid or []),
        "blockers": sorted(blockers or []),
    }


def evaluate(evidence: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one technical evidence envelope under the fail-closed policy."""

    validate_policy(policy)
    if evidence.get("schema") != "qikvrt_mesh_artifact_evidence_v1":
        return _result(
            "HOLD_PROVENANCE_UNVERIFIED",
            role=None,
            missing_or_invalid=["schema"],
        )

    observed = evidence.get("observed")
    expected = evidence.get("expected")
    if not isinstance(observed, Mapping) or not isinstance(expected, Mapping):
        return _result(
            "HOLD_PROVENANCE_UNVERIFIED",
            role=None,
            missing_or_invalid=["observed_or_expected"],
        )

    config = _require_mapping(policy["artifact_evidence"], "artifact_evidence")
    required_observed = list(config["required_observed_fields"])
    required_expected = list(config["required_expected_fields"])
    missing_or_invalid: list[str] = []
    for namespace, values, fields in (
        ("observed", observed, required_observed),
        ("expected", expected, required_expected),
    ):
        for field in fields:
            if field not in values or not _valid_binding(field, values.get(field)):
                missing_or_invalid.append(f"{namespace}.{field}")

    repository = observed.get("repository") if isinstance(observed.get("repository"), str) else ""
    role = _role_for_repository(repository, policy)

    claims = evidence.get("claims", {})
    if not isinstance(claims, Mapping):
        claims = {"invalid": True}
    legal_claim_requested = any(
        claims.get(key) is True
        for key in (
            "authorship",
            "copying",
            "legal_infringement",
            "damages",
            "court_finding",
        )
    )
    requested_effect = evidence.get("requested_effect")
    accepted_effects = set(config["accepted_requested_effects"])
    if legal_claim_requested or requested_effect not in accepted_effects:
        blockers = []
        if legal_claim_requested:
            blockers.append("AUTOMATED_LEGAL_CONCLUSION_FORBIDDEN")
        if requested_effect not in accepted_effects:
            blockers.append("REQUESTED_EFFECT_OUTSIDE_AUTOMATED_SCOPE")
        return _result(
            "HOLD_LEGAL_AUTHORITY_REQUIRED",
            role=role,
            blockers=blockers,
            missing_or_invalid=missing_or_invalid,
        )

    if missing_or_invalid:
        return _result(
            "HOLD_PROVENANCE_UNVERIFIED",
            role=role,
            missing_or_invalid=missing_or_invalid,
        )

    if role is None:
        return _result(
            "HOLD_PROVENANCE_MISMATCH",
            role=role,
            blockers=["REPOSITORY_NOT_IN_BOUND_MESH_ROLE_REGISTRY"],
        )

    mismatches = [
        field for field in required_observed if observed.get(field) != expected.get(field)
    ]
    authority_repository = policy["mesh_roles"]["authority"]["repository"]
    if observed.get("authority_source_repository") != authority_repository:
        mismatches.append("authority_source_repository")
    if role == "AUTHORITY" and repository != authority_repository:
        mismatches.append("authority_repository")
    if role == "MIRROR" and expected.get("authority_source_repository") != authority_repository:
        mismatches.append("mirror_authority_source_repository")

    if mismatches:
        return _result(
            "HOLD_PROVENANCE_MISMATCH",
            role=role,
            mismatches=mismatches,
        )

    data = evidence.get("data_protection")
    if not isinstance(data, Mapping):
        return _result(
            "HOLD_DATA_PROTECTION_REVIEW",
            role=role,
            blockers=["DATA_PROTECTION_ENVELOPE_MISSING"],
        )
    if data.get("personal_data_present") is True:
        required_guards = policy["data_protection"][
            "when_personal_data_present_require"
        ]
        missing_guards = [name for name in required_guards if data.get(name) is not True]
        if missing_guards:
            return _result(
                "HOLD_DATA_PROTECTION_REVIEW",
                role=role,
                blockers=[f"MISSING_DATA_GUARD:{name}" for name in missing_guards],
            )
    elif data.get("personal_data_present") is not False:
        return _result(
            "HOLD_DATA_PROTECTION_REVIEW",
            role=role,
            blockers=["PERSONAL_DATA_PRESENCE_UNRESOLVED"],
        )

    license_binding = evidence.get("license")
    if not isinstance(license_binding, Mapping):
        return _result(
            "HOLD_LICENSE_REVIEW",
            role=role,
            blockers=["LICENSE_ENVELOPE_MISSING"],
        )
    if license_binding.get("resolution") != config["accepted_license_resolution"]:
        return _result(
            "HOLD_LICENSE_REVIEW",
            role=role,
            blockers=["DECLARED_LICENSE_NOTICE_NOT_EXACTLY_RESOLVED"],
        )

    return _result("PROVENANCE_AND_NOTICE_MATCH_VERIFIED", role=role)


def witness(repository: str = "Goldkelch/qik-vrt") -> dict[str, Any]:
    authority = "Goldkelch/qik-vrt"
    binding = {
        "repository": repository,
        "authority_source_repository": authority,
        "head_sha": "1" * 40,
        "tree_sha": "2" * 40,
        "manifest_sha256": "3" * 64,
        "license_map_sha256": "4" * 64,
        "artifact_sha256": "5" * 64,
        "path": "docs/example.md",
    }
    return {
        "schema": "qikvrt_mesh_artifact_evidence_v1",
        "observed": dict(binding),
        "expected": dict(binding),
        "license": {
            "resolution": "EXACT_NOTICE_MATCH",
            "rights_chain_status": "REPOSITORY_STATED_NOT_JUDICIALLY_PROVEN",
        },
        "data_protection": {"personal_data_present": False},
        "requested_effect": "READ_ONLY_VERIFY",
        "claims": {
            "authorship": False,
            "copying": False,
            "legal_infringement": False,
            "damages": False,
            "court_finding": False,
        },
    }


def self_check(policy: Mapping[str, Any]) -> dict[str, Any]:
    authority = evaluate(witness(), policy)
    mirror = evaluate(witness("ingolf-lohmann/qik-vrt"), policy)

    mismatch_evidence = copy.deepcopy(witness())
    mismatch_evidence["observed"]["artifact_sha256"] = "6" * 64
    mismatch = evaluate(mismatch_evidence, policy)

    license_evidence = copy.deepcopy(witness())
    license_evidence["license"]["resolution"] = "AMBIGUOUS"
    license_hold = evaluate(license_evidence, policy)

    privacy_evidence = copy.deepcopy(witness())
    privacy_evidence["data_protection"] = {
        "personal_data_present": True,
        "lawful_basis_bound": True,
        "purpose_bound": True,
        "data_minimized": False,
    }
    privacy_hold = evaluate(privacy_evidence, policy)

    legal_evidence = copy.deepcopy(witness())
    legal_evidence["claims"]["legal_infringement"] = True
    legal_hold = evaluate(legal_evidence, policy)

    expected = {
        "authority": "PROVENANCE_AND_NOTICE_MATCH_VERIFIED",
        "mirror": "PROVENANCE_AND_NOTICE_MATCH_VERIFIED",
        "mismatch": "HOLD_PROVENANCE_MISMATCH",
        "license": "HOLD_LICENSE_REVIEW",
        "privacy": "HOLD_DATA_PROTECTION_REVIEW",
        "legal": "HOLD_LEGAL_AUTHORITY_REQUIRED",
    }
    observed = {
        "authority": authority["decision"],
        "mirror": mirror["decision"],
        "mismatch": mismatch["decision"],
        "license": license_hold["decision"],
        "privacy": privacy_hold["decision"],
        "legal": legal_hold["decision"],
    }
    if observed != expected:
        raise ContractError(f"self-check decisions differ: {observed!r}")
    if authority["normative_authority"] is not True:
        raise ContractError("Authority witness lost normative role")
    if mirror["normative_authority"] is not False:
        raise ContractError("Mirror witness gained Authority role")
    if any(
        receipt[key]
        for receipt in (authority, mirror)
        for key in (
            "human_hierarchy_inferred",
            "authorship_proven",
            "copying_determined",
            "legal_infringement_determined",
            "damages_determined",
            "court_finding",
        )
    ):
        raise ContractError("technical verification crossed a prohibited boundary")

    return {
        "schema": "qikvrt_mesh_rights_provenance_self_check_v1",
        "decisions": observed,
        "authority_role_preserved": True,
        "mirror_role_preserved": True,
        "technical_hierarchy_not_human_hierarchy": True,
        "legal_effect": "NONE",
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    policy = load_policy(args.policy)
    if args.self_check:
        result = self_check(policy)
    elif args.evidence:
        result = evaluate(load_json(args.evidence), policy)
    else:
        raise ContractError("provide --self-check or --evidence")

    text = json.dumps(result, indent=2 if args.pretty else None, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(f"{text}\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, json.JSONDecodeError) as error:
        print(f"qikvrt_mesh_rights_provenance: {error}", file=sys.stderr)
        raise SystemExit(2)
