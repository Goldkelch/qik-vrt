#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded repository-native QIK-VRT self-healing controller."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
DELEGATION = (
    ROOT
    / "state/authorization/delegations/"
    "OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json"
)
PROMOTION_CONDITIONS = (
    "CURRENT_BASE_REOBSERVED",
    "HEAD_UNCHANGED",
    "DIFF_ALLOWLISTED",
    "NO_EXTERNAL_EFFECT",
    "ALL_APPLICABLE_GATES_TERMINAL_GREEN",
    "NO_COMPETING_WRITER",
)


class SelfHealBlock(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run(command: Sequence[str], timeout: int = 900) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(
        tuple(command),
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def _load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SelfHealBlock(f"{label} cannot be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise SelfHealBlock(f"{label} must be a JSON object")
    return value


def _validate_promotion_policy(
    policy: Any,
    *,
    proposal_workflow_may_merge: bool | None,
    standing_delegation: bool | None,
) -> Mapping[str, Any]:
    if not isinstance(policy, Mapping):
        raise SelfHealBlock("promotion policy is absent")
    if policy.get("unconditional_automatic_merge") != "FORBIDDEN":
        raise SelfHealBlock("unconditional automatic merge must remain forbidden")
    if policy.get("expected_head_bound_promotion") != "ALLOWED_ONLY_IF":
        raise SelfHealBlock("expected-head-bound promotion policy differs")
    if policy.get("conditions") != list(PROMOTION_CONDITIONS):
        raise SelfHealBlock("expected-head-bound promotion conditions differ")
    if policy.get("requires_existing_repository_bound_promotion_contract") is not True:
        raise SelfHealBlock("repository-bound promotion contract is required")
    if policy.get("general_auto_merge_authorization") is not False:
        raise SelfHealBlock("general automatic-merge authorization is forbidden")
    if (
        proposal_workflow_may_merge is not None
        and policy.get("proposal_workflow_may_merge")
        is not proposal_workflow_may_merge
    ):
        raise SelfHealBlock("proposal workflow promotion boundary differs")
    if (
        standing_delegation is not None
        and policy.get("standing_delegation") is not standing_delegation
    ):
        raise SelfHealBlock("standing promotion delegation differs")
    return policy


def load_delegation() -> dict[str, Any]:
    value = _load_json(DELEGATION, "autonomous continuation delegation")
    if value.get("schema") != "qikvrt_owner_autonomous_repository_continuation_v2":
        raise SelfHealBlock("delegation schema mismatch")
    if value.get("authorization_scope", {}).get("state") != "ACTIVE":
        raise SelfHealBlock("autonomous continuation delegation is not active")
    _validate_promotion_policy(
        value.get("promotion_policy"),
        proposal_workflow_may_merge=None,
        standing_delegation=True,
    )
    if "unconditional_automatic_merge_or_unbound_promotion" not in set(
        value.get("not_authorized", [])
    ):
        raise SelfHealBlock("delegation does not forbid unbound promotion")
    return value


def load_contract() -> dict[str, Any]:
    value = _load_json(CONTRACT, "autonomous self-healing contract")
    if value.get("schema") != "qikvrt_autonomous_self_healing_contract_v1":
        raise SelfHealBlock("contract schema mismatch")
    execution_model = value.get("execution_model", {})
    if execution_model.get("promotion") != "expected_head_bound_only":
        raise SelfHealBlock("promotion must remain expected-head-bound")
    contract_policy = _validate_promotion_policy(
        value.get("promotion_policy"),
        proposal_workflow_may_merge=False,
        standing_delegation=None,
    )
    delegation = load_delegation()
    delegation_policy = delegation["promotion_policy"]
    if contract_policy["conditions"] != delegation_policy["conditions"]:
        raise SelfHealBlock("contract and delegation promotion conditions differ")
    if value.get("promotion_gate_order") != [
        "NEW_CURRENT_MAIN_DRAFT",
        "REPOSITORY_NATIVE_INTEGRITY_MATERIALIZATION",
        "EXACT_HEAD_GATES",
        "EXPECTED_HEAD_BOUND_PROMOTION",
    ]:
        raise SelfHealBlock("promotion gate order differs")
    forbidden = set(value.get("forbidden_effects", []))
    if not {
        "unconditional_automatic_merge",
        "unbound_or_stale_head_promotion",
        "force_push",
        "zenodo_mutation",
        "ietf_mutation",
        "deployment",
    }.issubset(forbidden):
        raise SelfHealBlock("forbidden-effect boundary differs")
    candidate = value.get("candidate_contract", {})
    if (
        candidate.get("pull_request_mode") != "draft"
        or candidate.get("deduplicate_by")
        != "base_revision_and_semantic_fingerprint"
        or candidate.get("proposal_workflow_may_merge") is not False
    ):
        raise SelfHealBlock("candidate review boundary differs")
    return value


def allowed_paths(contract: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for handler in contract["allowlisted_handlers"]:
        result.update(handler["mutable_paths"])
    return result


def changed_paths() -> list[str]:
    result = run(("git", "diff", "--name-only", "--"), timeout=60)
    if result.returncode:
        raise SelfHealBlock(result.stderr.strip() or "git diff failed")
    return sorted(line for line in result.stdout.splitlines() if line)


def semantic_fingerprint(paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        payload = (ROOT / path).read_bytes()
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def candidate_identity(base_revision: str, fingerprint: str) -> str:
    if (
        len(base_revision) != 40
        or any(character not in "0123456789abcdef" for character in base_revision)
    ):
        raise SelfHealBlock("base revision is not a Git SHA-1")
    if (
        len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        raise SelfHealBlock("semantic fingerprint is not a SHA-256")
    payload = (
        base_revision.encode("ascii")
        + b"\0"
        + fingerprint.encode("ascii")
    )
    return hashlib.sha256(payload).hexdigest()


def observed_base_revision() -> str:
    result = run(("git", "rev-parse", "--verify", "HEAD^{commit}"), timeout=60)
    value = result.stdout.strip()
    if result.returncode or len(value) != 40:
        raise SelfHealBlock(result.stderr.strip() or "cannot bind current HEAD")
    return value


def repair_handler(handler: dict[str, Any]) -> dict[str, Any]:
    probe = run(tuple(handler["probe"]))
    if probe.returncode == 0:
        return {"failure_class": handler["failure_class"], "state": "NOOP"}
    combined = probe.stdout + "\n" + probe.stderr
    if (
        handler["failure_class"] == "ANTICIPATION_PROJECTION_DRIFT"
        and "projection drift:" not in combined
    ):
        raise SelfHealBlock(
            "anticipation failure is not an allowlisted projection drift"
        )
    repair = run(tuple(handler["repair"]))
    if repair.returncode:
        raise SelfHealBlock(
            f"repair failed for {handler['failure_class']}: "
            f"{repair.stderr.strip() or repair.stdout.strip()}"
        )
    return {"failure_class": handler["failure_class"], "state": "REPAIRED"}


def execute(apply: bool) -> dict[str, Any]:
    contract = load_contract()
    initial = run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        timeout=60,
    )
    if initial.returncode or initial.stdout.strip():
        raise SelfHealBlock("controller requires a clean repository")
    base_revision = observed_base_revision()
    boot = run(
        (
            "python3",
            "-B",
            "tools/ai_runtime_bootloader.py",
            "--profile",
            "all",
            "--json",
        )
    )
    if boot.returncode not in (0, 2):
        raise SelfHealBlock("AI runtime bootloader returned an unrecognized state")
    actions: list[dict[str, Any]] = []
    if apply:
        for handler in contract["allowlisted_handlers"]:
            actions.append(repair_handler(handler))
    paths = changed_paths()
    unexpected = sorted(set(paths) - allowed_paths(contract))
    if unexpected:
        raise SelfHealBlock(f"non-allowlisted mutation: {unexpected}")
    fingerprint = semantic_fingerprint(paths) if paths else None
    candidate_id = (
        candidate_identity(base_revision, fingerprint)
        if fingerprint is not None
        else None
    )
    state = "CANDIDATE_READY" if paths else "NOOP"
    return {
        "schema": "qikvrt_autonomous_self_heal_result_v1",
        "state": state,
        "observed_base_revision": base_revision,
        "semantic_fingerprint": fingerprint,
        "candidate_identity": candidate_id,
        "changed_paths": paths,
        "actions": actions,
        "external_effect": "NONE",
        "promotion_policy": {
            "unconditional_automatic_merge": "FORBIDDEN",
            "expected_head_bound_promotion": "ALLOWED_ONLY_IF",
            "conditions": list(PROMOTION_CONDITIONS),
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "FULL_SYNC": False,
            "SYMMETRIC_CANONICALITY": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "apply"))
    args = parser.parse_args(argv)
    try:
        result = execute(args.command == "apply")
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
        SelfHealBlock,
    ) as exc:
        print(
            json.dumps(
                {
                    "state": "BLOCK",
                    "failure_class": "AUTONOMOUS_SELF_HEAL_BLOCKED",
                    "detail": str(exc),
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
