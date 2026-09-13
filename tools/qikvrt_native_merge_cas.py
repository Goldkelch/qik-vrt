# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations


class NativeMergeCASBlock(ValueError):
    """Fail-closed blocker for native exact-base/head promotion."""


def require_native_strict_base_cas_ruleset(ruleset: dict) -> None:
    if ruleset.get("enforcement") != "active":
        raise NativeMergeCASBlock("RULESET_NOT_ACTIVE")
    conditions = ruleset.get("conditions") or {}
    ref_name = conditions.get("ref_name") or {}
    if "refs/heads/main" not in (ref_name.get("include") or []):
        raise NativeMergeCASBlock("MAIN_NOT_TARGETED")
    if ruleset.get("current_user_can_bypass") != "never":
        raise NativeMergeCASBlock("BYPASS_MUST_BE_NEVER")

    by_type = {item.get("type"): item for item in (ruleset.get("rules") or []) if isinstance(item, dict)}
    if "pull_request" not in by_type:
        raise NativeMergeCASBlock("PULL_REQUEST_RULE_REQUIRED")
    required = by_type.get("required_status_checks")
    if not isinstance(required, dict):
        raise NativeMergeCASBlock("REQUIRED_STATUS_CHECKS_RULE_REQUIRED")
    params = required.get("parameters") or {}
    if params.get("strict_required_status_checks_policy") is not True:
        raise NativeMergeCASBlock("STRICT_BASE_POLICY_REQUIRED")
    if not params.get("required_status_checks"):
        raise NativeMergeCASBlock("AT_LEAST_ONE_REQUIRED_STATUS_CHECK_REQUIRED")
    if "non_fast_forward" not in by_type:
        raise NativeMergeCASBlock("NON_FAST_FORWARD_RULE_REQUIRED")


def verify_native_merge_effect(
    *,
    expected_base: str,
    expected_head: str,
    merge_response: dict,
    pr_after: dict,
    main_after: dict,
    merge_commit: dict,
) -> None:
    merge_sha = merge_response.get("sha")
    if merge_response.get("merged") is not True or not isinstance(merge_sha, str) or len(merge_sha) != 40:
        raise NativeMergeCASBlock("NATIVE_MERGE_NOT_ACKNOWLEDGED")
    if pr_after.get("merged") is not True or pr_after.get("merge_commit_sha") != merge_sha:
        raise NativeMergeCASBlock("PR_MERGE_READBACK_MISMATCH")
    if main_after.get("sha") != merge_sha:
        raise NativeMergeCASBlock("MAIN_READBACK_MISMATCH")
    if merge_commit.get("sha") != merge_sha:
        raise NativeMergeCASBlock("MERGE_COMMIT_READBACK_MISMATCH")
    parents = merge_commit.get("parents") or []
    observed = [item.get("sha") for item in parents if isinstance(item, dict)]
    if observed != [expected_base, expected_head]:
        raise NativeMergeCASBlock("MERGE_PARENT_BINDING_MISMATCH")
