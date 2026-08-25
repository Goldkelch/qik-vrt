#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed wrapper for autonomous repository work before external effects."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections.abc import Sequence
from typing import Any

from tools import qikvrt_autonomous_self_heal as self_heal

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "state/autonomy/AUTONOMOUS_PRE_EFFECT_POLICY_V1.json"
CANONICAL_UPSTREAM_POLICY = ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
EXPECTED_PRECONDITIONS = [
    "CURRENT_MAIN_REOBSERVED",
    "EXACT_HEAD_BOUND",
    "NO_COMPETING_WRITER",
    "DETERMINISTIC_STATE",
    "REPOSITORY_NATIVE_EVIDENCE",
]
IRREVERSIBLE_EFFECTS = {
    "ZENODO_PUBLICATION",
    "IETF_SUBMISSION",
    "DOI_CREATION",
    "PUBLIC_RELEASE",
    "EXTERNAL_CREDENTIAL_CONSUMPTION",
    "OTHER_NON_REVERSIBLE_EXTERNAL_STATE_CHANGE",
}
PROHIBITED_CLAIMS = {
    "SCIENTIFIC_CONFIRMATION",
    "PHYSICAL_CORRESPONDENCE",
    "PASS",
    "FINAL_PASS",
    "EFFECT_ACK_DONE",
}
REQUIRED_AUTONOMOUS_CAPABILITIES = {
    "REOBSERVE",
    "CLASSIFY",
    "SELF_HEAL",
    "DISPATCH_ALLOWLISTED_EXACT_HEAD_GATE",
    "GENERATE_RECEIPTS",
}
REQUIRED_EVIDENCE_PATHS = (
    "AI",
    "AI_CONTEXT.json",
    "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json",
    "policy/CANONICAL_UPSTREAM_REMOTE_V1.json",
    "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json",
    "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json",
    "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json",
    "tools/qikvrt_workflow_executor.py",
    ".github/workflows/qikvrt_workflow_executor.yml",
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)
SHA1 = re.compile(r"^[0-9a-f]{40}$")
REMOTE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class PreEffectBlock(RuntimeError):
    pass


def _canonical_upstream_contract() -> dict[str, str]:
    try:
        policy = json.loads(CANONICAL_UPSTREAM_POLICY.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PreEffectBlock("canonical upstream policy cannot be loaded") from exc
    if policy.get("schema") != "qikvrt_canonical_upstream_remote_v1":
        raise PreEffectBlock("canonical upstream policy schema mismatch")
    if policy.get("status") != "NORMATIVE":
        raise PreEffectBlock("canonical upstream policy is not normative")
    canonical = policy.get("canonical_upstream", {})
    repository = canonical.get("repository")
    role = canonical.get("role")
    remote_name = canonical.get("canonical_remote_name")
    remote_url = canonical.get("canonical_https_url")
    default_branch = canonical.get("default_branch")
    if (
        not isinstance(repository, str)
        or not repository
        or role != "AUTHORITY"
        or not isinstance(remote_name, str)
        or REMOTE_NAME.fullmatch(remote_name) is None
        or not isinstance(remote_url, str)
        or not remote_url
        or not isinstance(default_branch, str)
        or not default_branch
    ):
        raise PreEffectBlock("canonical upstream contract mismatch")
    expected_url = f"https://github.com/{repository}.git"
    if remote_url != expected_url:
        raise PreEffectBlock("canonical upstream URL/repository mismatch")
    selection = policy.get("selection_rule", {})
    if selection.get("source_of_truth") != "canonical_upstream.repository":
        raise PreEffectBlock("canonical upstream selection rule mismatch")
    if (
        selection.get("policy_over_local_git_config") is not True
        or selection.get("policy_over_remote_name_heuristics") is not True
        or selection.get("policy_over_personal_origin") is not True
        or selection.get("ambiguous_or_missing_binding") != "HOLD"
    ):
        raise PreEffectBlock("canonical upstream precedence weakened")
    return {
        "repository": repository,
        "remote_name": remote_name,
        "remote_url": remote_url,
        "default_branch": default_branch,
    }


def load_policy() -> dict[str, Any]:
    value = json.loads(POLICY.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt_autonomous_pre_effect_policy_v1":
        raise PreEffectBlock("pre-effect policy schema mismatch")
    if value.get("mission") != "AUTONOMOUS_UNTIL_FIRST_IRREVERSIBLE_EXTERNAL_EFFECT":
        raise PreEffectBlock("pre-effect mission mismatch")
    if value.get("preconditions") != EXPECTED_PRECONDITIONS:
        raise PreEffectBlock("pre-effect preconditions differ")
    if value.get("fail_closed") != {
        "when": "ANY_PRECONDITION_MISSING",
        "state": "HOLD",
        "repair_forbidden": True,
    }:
        raise PreEffectBlock("fail-closed policy differs")
    if set(value.get("first_irreversible_external_effect", [])) != IRREVERSIBLE_EFFECTS:
        raise PreEffectBlock("irreversible-effect boundary differs")
    prohibited = set(value.get("prohibited_autonomous_effects", []))
    if not PROHIBITED_CLAIMS.issubset(prohibited):
        raise PreEffectBlock("epistemic or completion boundary weakened")
    capabilities = set(value.get("autonomous_capabilities", []))
    if not REQUIRED_AUTONOMOUS_CAPABILITIES.issubset(capabilities):
        raise PreEffectBlock("required repository-native autonomous capability absent")
    owner = value.get("owner_authorization", {})
    if owner.get("state") != "ACTIVE" or owner.get("role") != "Product Owner":
        raise PreEffectBlock("Product Owner implementation authorization absent")
    _canonical_upstream_contract()
    self_heal.load_contract()
    self_heal.load_delegation()
    return value


def _canonical_source_remote() -> str:
    contract = _canonical_upstream_contract()
    expected_name = contract["remote_name"]
    expected_url = contract["remote_url"]

    remotes_result = self_heal.run(("git", "remote"), timeout=60)
    if remotes_result.returncode:
        raise PreEffectBlock("cannot enumerate Git remotes")
    remotes = set(remotes_result.stdout.split())
    if expected_name not in remotes:
        raise PreEffectBlock("canonical source remote is absent")
    url_result = self_heal.run(
        ("git", "remote", "get-url", expected_name),
        timeout=60,
    )
    if url_result.returncode or url_result.stdout.strip() != expected_url:
        raise PreEffectBlock("canonical source remote URL mismatch")
    return expected_name


def _remote_main_revision() -> str | None:
    contract = _canonical_upstream_contract()
    remote = _canonical_source_remote()
    branch = contract["default_branch"]
    ref = f"refs/heads/{branch}"
    result = self_heal.run((
        "git", "ls-remote", "--heads", remote, ref,
    ), timeout=60)
    if result.returncode:
        return None
    fields = result.stdout.split()
    if len(fields) != 2 or not SHA1.fullmatch(fields[0]) or fields[1] != ref:
        return None
    return fields[0]


def observe_preconditions() -> dict[str, bool]:
    head = self_heal.observed_base_revision()
    remote_main = _remote_main_revision()
    evidence_present = all((ROOT / path).is_file() for path in REQUIRED_EVIDENCE_PATHS)
    deterministic_state = True
    try:
        load_policy()
    except (OSError, ValueError, json.JSONDecodeError, self_heal.SelfHealBlock, PreEffectBlock):
        deterministic_state = False
    return {
        "CURRENT_MAIN_REOBSERVED": remote_main is not None and remote_main == head,
        "EXACT_HEAD_BOUND": SHA1.fullmatch(head) is not None,
        "NO_COMPETING_WRITER": remote_main is not None and remote_main == head,
        "DETERMINISTIC_STATE": deterministic_state,
        "REPOSITORY_NATIVE_EVIDENCE": evidence_present,
    }


def classify(preconditions: dict[str, bool], requested_effect: str | None) -> str:
    if requested_effect is not None:
        if requested_effect not in IRREVERSIBLE_EFFECTS:
            raise PreEffectBlock("unknown external effect")
        return "REQUIRE_EXACT_PRODUCT_OWNER_AUTHORIZATION"
    if set(preconditions) != set(EXPECTED_PRECONDITIONS):
        raise PreEffectBlock("precondition set differs")
    if not all(preconditions[name] is True for name in EXPECTED_PRECONDITIONS):
        return "HOLD"
    return "AUTONOMOUS_EXECUTION_ALLOWED"


def execute(command: str, requested_effect: str | None = None) -> dict[str, Any]:
    load_policy()
    preconditions = observe_preconditions()
    decision = classify(preconditions, requested_effect)
    if decision != "AUTONOMOUS_EXECUTION_ALLOWED":
        return {
            "schema": "qikvrt_autonomous_pre_effect_result_v1",
            "state": decision,
            "preconditions": preconditions,
            "external_effect": requested_effect or "NONE",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }
    result = self_heal.execute(command == "apply")
    result["schema"] = "qikvrt_autonomous_pre_effect_result_v1"
    result["pre_effect_policy"] = "AUTONOMOUS-PRE-EFFECT-POLICY-V1"
    result["preconditions"] = preconditions
    result["decision"] = decision
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "apply"))
    parser.add_argument("--requested-effect", choices=sorted(IRREVERSIBLE_EFFECTS))
    args = parser.parse_args(argv)
    try:
        result = execute(args.command, args.requested_effect)
    except (OSError, ValueError, json.JSONDecodeError, self_heal.SelfHealBlock, PreEffectBlock) as exc:
        print(json.dumps({
            "state": "HOLD",
            "failure_class": "AUTONOMOUS_PRE_EFFECT_BLOCKED",
            "detail": str(exc),
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
