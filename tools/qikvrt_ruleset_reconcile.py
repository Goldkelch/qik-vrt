#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Plan or apply the exact QIK-VRT main-ruleset projection."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy/GITHUB_MAIN_RULESET_V1.json"
SCHEMA = "qikvrt_github_main_ruleset_reconciliation_v1"
INCOMPLETE_VISIBILITY = "INCOMPLETE_VISIBILITY"
SOURCE_RUN_NONTERMINAL = "NONTERMINAL"
SOURCE_RUN_TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
SOURCE_RUN_DURABLE_INTENT = "DURABLE_INTENT_SOURCE"
SOURCE_BRIDGE_JOB_NAME = "QIKVRT ruleset reconciliation dispatch bridge"
SOURCE_INTENT_STEP_NAME = "Preserve exact ruleset dispatch intent"
SOURCE_TRANSPORT_STEP_NAME = "Enqueue exact ruleset intent without dispatching"
CONTINUATION_PATH = ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
RULESET_TRANSPORT_RECOVERY_JOB_NAME = (
    "Recover one exact ruleset reconcile transport"
)
RULESET_TRANSPORT_RECOVERY_INTENT_STEP_NAME = (
    "Preserve exact ruleset reconcile transport recovery intent"
)
RULESET_REVIEW_RESUME_JOB_NAME = (
    "Reobserve exact ruleset receipt and resume one blocked review"
)
RULESET_REVIEW_RESUME_INTENT_STEP_NAME = (
    "Preserve exact requested-review successor intent"
)
RULESET_REVIEW_RESUME_TRANSPORT_STEP_NAME = (
    "Reobserve and dispatch the exact secret-free requested-review successor"
)
RULESET_RECONCILER_RERUN_INTENT_STEP_NAME = (
    "Preserve exact transient reconciler rerun intent"
)
RULESET_RECONCILER_RERUN_TRANSPORT_STEP_NAME = (
    "Reobserve and rerun one exact transient reconciler attempt"
)
RULESET_REVIEW_RECOVERY_JOB_NAME = (
    "Recover one exact ruleset review-resume transport"
)
RULESET_REVIEW_RECOVERY_INTENT_STEP_NAME = (
    "Preserve exact ruleset review-resume transport recovery intent"
)
RULESET_RERUN_RECOVERY_JOB_NAME = (
    "Recover one exact ruleset reconciler-rerun transport"
)
RULESET_RECONCILER_PATH = ".github/workflows/qikvrt_ruleset_reconcile.yml"
REQUESTED_REVIEW_EXECUTOR_PATH = (
    ".github/workflows/qikvrt_requested_review_executor.yml"
)
REQUESTED_REVIEW_EXECUTOR_JOB_NAME = "review-one"
REVIEW_LEDGER_REF = "refs/heads/qikvrt/mesh-review-ledger-v1"
REQUIRED_REVIEW_GATE_PATH = ".github/workflows/qikvrt_required_review_gate.yml"
REQUIRED_REVIEW_GATE_JOB_NAME = "plan-native-account-review"
REVIEW_RESUME_BINDING_SCHEMA = "qikvrt_ruleset_review_resume_binding_v1"
ACTIVE_RUN_STATUSES = frozenset(
    {"queued", "in_progress", "waiting", "requested", "pending"}
)
RULESET_REVIEW_INTENT_PATTERN = re.compile(
    r"qikvrt-ruleset-review-resume-intent-([1-9][0-9]*)-([1-9][0-9]*)"
    r"(?:-reconciler-([1-9][0-9]*)-([1-9][0-9]*))?"
)
RULESET_RERUN_INTENT_PATTERN = re.compile(
    r"qikvrt-ruleset-reconciler-rerun-intent-([1-9][0-9]*)-([1-9][0-9]*)"
    r"(?:-target-([1-9][0-9]*))?"
)


class RulesetBlock(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_policy(path: pathlib.Path = POLICY_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt_github_main_ruleset_v1":
        raise RulesetBlock("ruleset policy schema mismatch")
    if value.get("repository") != "Goldkelch/qik-vrt":
        raise RulesetBlock("ruleset policy repository mismatch")
    if value.get("ruleset_id") != 19344903:
        raise RulesetBlock("ruleset policy id mismatch")
    authority = _mapping(value.get("authority"), "ruleset authority")
    external = _mapping(
        authority.get("required_external_readback"),
        "ruleset authority external readback",
    )
    forbidden_scopes = (
        "repository_scope_secret_names_absent",
        "organization_scope_secret_names_absent",
    )
    expected_owner = _mapping(
        external.get("repository_owner"),
        "ruleset authority repository owner",
    )
    if (
        authority.get("environment") != "qikvrt-ruleset-authority"
        or authority.get("credential") != "QIKVRT_ENV_RULESET_ADMIN_TOKEN"
        or authority.get("credential_scope") != "ENVIRONMENT_ONLY"
        or authority.get("external_configuration_verified") is not False
        or authority.get("external_configuration_hold")
        != "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED"
        or external.get("deployment_branch_policy") != "SELECTED_BRANCHES_ONLY"
        or external.get("selected_branch") != "main"
        or external.get("environment_protection_rules_required") is not True
        or external.get("environment_secret_present")
        != "QIKVRT_ENV_RULESET_ADMIN_TOKEN"
        or expected_owner
        != {"login": "Goldkelch", "id": 293941403, "type": "User"}
        or external.get("organization_scope_resolution")
        != "OWNER_TYPE_AWARE"
        or any(
            external.get(scope)
            != ["QIKVRT_ENV_RULESET_ADMIN_TOKEN", "QIKVRT_RULESET_ADMIN_TOKEN"]
            for scope in forbidden_scopes
        )
    ):
        raise RulesetBlock("ruleset Authority environment contract mismatch")
    effect = _mapping(value.get("effect_contract"), "effect contract")
    if effect.get("immediate_pre_effect_reobservation_required") is not True:
        raise RulesetBlock("ruleset policy must require immediate pre-effect reobservation")
    if effect.get("conditional_update_supported") is not False:
        raise RulesetBlock("ruleset policy must not claim unsupported conditional update")
    if (
        effect.get("conditional_update_used") is not False
        or effect.get("get_put_race_eliminated") is not False
        or effect.get("final_get_to_put_boundary")
        != "IRREDUCIBLE_NO_DOCUMENTED_CAS_LAST_WRITER_CONVERGENCE"
    ):
        raise RulesetBlock("ruleset policy final GET-to-PUT boundary mismatch")
    if effect.get("write_concurrency_model") != "LAST_WRITER_WINS":
        raise RulesetBlock("ruleset policy write-concurrency model mismatch")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RulesetBlock(f"{label} must be an object")
    return value


def _rules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise RulesetBlock("rules must be a list")
    result = []
    for raw in value:
        item = json.loads(json.dumps(dict(_mapping(raw, "rule"))))
        rule_type = item.get("type")
        if not isinstance(rule_type, str) or not rule_type:
            raise RulesetBlock("rule type is missing")
        parameters = item.get("parameters")
        if isinstance(parameters, dict):
            checks = parameters.get("required_status_checks")
            if isinstance(checks, list):
                parameters["required_status_checks"] = sorted(
                    checks,
                    key=lambda check: (
                        str(check.get("context", "")),
                        int(check.get("integration_id") or 0),
                    ),
                )
            reviewers = parameters.get("required_reviewers")
            if isinstance(reviewers, list):
                parameters["required_reviewers"] = sorted(
                    reviewers, key=lambda reviewer: json.dumps(reviewer, sort_keys=True)
                )
        result.append(item)
    return sorted(result, key=lambda item: item["type"])


def normalize(value: Mapping[str, Any]) -> dict[str, Any]:
    if "bypass_actors" not in value:
        raise RulesetBlock("ruleset observation omitted bypass_actors")
    bypass_actors = value["bypass_actors"]
    if not isinstance(bypass_actors, list):
        raise RulesetBlock("ruleset bypass_actors must be an explicit list")
    return {
        "name": value.get("name"),
        "target": value.get("target"),
        "enforcement": value.get("enforcement"),
        "conditions": value.get("conditions"),
        "bypass_actors": bypass_actors,
        "rules": _rules(value.get("rules")),
    }


def desired_payload(policy: Mapping[str, Any]) -> dict[str, Any]:
    return normalize(policy)


def evaluate(current: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    if current.get("id") != policy.get("ruleset_id"):
        raise RulesetBlock("observed ruleset id mismatch")
    if current.get("source") != policy.get("repository"):
        raise RulesetBlock("observed ruleset source mismatch")
    desired = desired_payload(policy)
    if "bypass_actors" not in current:
        incomplete = {
            "name": current.get("name"),
            "target": current.get("target"),
            "enforcement": current.get("enforcement"),
            "conditions": current.get("conditions"),
            "bypass_actors": {"visibility": "ABSENT"},
            "rules": _rules(current.get("rules")),
        }
        return {
            "schema": SCHEMA,
            "repository": policy["repository"],
            "ruleset_id": policy["ruleset_id"],
            "state": INCOMPLETE_VISIBILITY,
            "first_blocker": "RULESET_BYPASS_ACTORS_VISIBILITY_INCOMPLETE",
            "missing_fields": ["bypass_actors"],
            "changed_fields": [],
            "pre_state_sha256": digest(incomplete),
            "desired_state_sha256": digest(desired),
            "mutation": "NONE",
            "effect_observed": False,
        }
    before = normalize(current)
    changed = sorted(
        key for key in desired if before.get(key) != desired.get(key)
    )
    return {
        "schema": SCHEMA,
        "repository": policy["repository"],
        "ruleset_id": policy["ruleset_id"],
        "state": "CURRENT" if not changed else "DRIFT",
        "changed_fields": changed,
        "pre_state_sha256": digest(before),
        "desired_state_sha256": digest(desired),
        "mutation": "NONE",
        "effect_observed": False,
    }


def _request(
    method: str,
    url: str,
    token: str,
    *,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = canonical_bytes(payload) if payload is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RulesetBlock(f"GitHub API HTTP {exc.code}: {detail}") from exc
    if not isinstance(value, dict):
        raise RulesetBlock("GitHub API returned a non-object")
    return value


def github_get(url: str, token: str) -> dict[str, Any]:
    """Read one fixed GitHub API object through the repository HTTP layer."""
    if not token:
        raise RulesetBlock("GitHub API token is unavailable")
    if not url.startswith("https://api.github.com/"):
        raise RulesetBlock("GitHub API URL is outside api.github.com")
    return _request("GET", url, token)


def github_get_bytes(url: str, token: str) -> bytes:
    """Read one fixed GitHub API byte stream through the repository HTTP layer."""
    if not token:
        raise RulesetBlock("GitHub API token is unavailable")
    if not url.startswith("https://api.github.com/"):
        raise RulesetBlock("GitHub API URL is outside api.github.com")
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    class SafeArtifactRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
            if redirected is None:
                return None
            old = urllib.parse.urlsplit(req.full_url)
            new = urllib.parse.urlsplit(newurl)
            if new.scheme != "https":
                raise RulesetBlock("artifact redirect is not HTTPS")
            if old.netloc.lower() != new.netloc.lower():
                redirected.remove_header("Authorization")
                redirected.remove_unredirected_header("Authorization")
            return redirected

    opener = urllib.request.build_opener(SafeArtifactRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RulesetBlock(f"GitHub API HTTP {exc.code}: {detail}") from exc


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RulesetBlock(f"{label} must be a positive integer")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise RulesetBlock(f"{label} must be a lowercase 40-character SHA")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise RulesetBlock(f"{label} must be a lowercase SHA-256")
    return value


def _workflow_path(value: Any) -> Any:
    return value.split("@", 1)[0] if isinstance(value, str) else value


def _artifact_archive_digest(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise RulesetBlock("artifact digest must be an explicit SHA-256")
    return value


def _json_from_single_file_zip(
    archive: bytes, *, expected_name: str, expected_digest: str
) -> dict[str, Any]:
    observed_digest = f"sha256:{hashlib.sha256(archive).hexdigest()}"
    if observed_digest != _artifact_archive_digest(expected_digest):
        raise RulesetBlock("artifact archive digest mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            names = package.namelist()
            if names != [expected_name]:
                raise RulesetBlock("artifact archive does not contain the exact file")
            raw = package.read(expected_name)
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        raise RulesetBlock("artifact archive is invalid") from exc
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RulesetBlock("artifact JSON is invalid") from exc
    return dict(_mapping(value, "artifact JSON"))


def _json_files_from_zip(
    archive: bytes, *, expected_digest: str, required_names: Sequence[str]
) -> dict[str, dict[str, Any]]:
    observed_digest = f"sha256:{hashlib.sha256(archive).hexdigest()}"
    if observed_digest != _artifact_archive_digest(expected_digest):
        raise RulesetBlock("artifact archive digest mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            names = package.namelist()
            if len(names) != len(set(names)):
                raise RulesetBlock("artifact archive contains duplicate paths")
            for name in names:
                path = pathlib.PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts or not path.parts:
                    raise RulesetBlock("artifact archive contains an unsafe path")
            if any(name not in names for name in required_names):
                raise RulesetBlock("artifact archive omits a required file")
            raw_files = {name: package.read(name) for name in required_names}
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        raise RulesetBlock("artifact archive is invalid") from exc
    result: dict[str, dict[str, Any]] = {}
    for name, raw in raw_files.items():
        try:
            result[name] = dict(_mapping(json.loads(raw), f"artifact {name}"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RulesetBlock(f"artifact {name} is invalid JSON") from exc
    return result


def _artifact_files_from_zip(
    archive: bytes, *, expected_digest: str, required_names: Sequence[str]
) -> dict[str, bytes]:
    """Read exact artifact members as bytes after archive/path validation."""
    observed_digest = f"sha256:{hashlib.sha256(archive).hexdigest()}"
    if observed_digest != _artifact_archive_digest(expected_digest):
        raise RulesetBlock("artifact archive digest mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as package:
            names = package.namelist()
            if len(names) != len(set(names)):
                raise RulesetBlock("artifact archive contains duplicate paths")
            for name in names:
                path = pathlib.PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts or not path.parts:
                    raise RulesetBlock("artifact archive contains an unsafe path")
            if any(name not in names for name in required_names):
                raise RulesetBlock("artifact archive omits a required file")
            return {name: package.read(name) for name in required_names}
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        raise RulesetBlock("artifact archive is invalid") from exc


def classify_required_review_gate_run(
    value: Mapping[str, Any],
    *,
    repository: str,
    main_head_sha: str,
    run_attempt: int,
    workflow_id: int,
) -> dict[str, Any]:
    expected = {
        "path": REQUIRED_REVIEW_GATE_PATH,
        "workflow_id": _positive_int(workflow_id, "required-review workflow id"),
        "event": "workflow_run",
        "head_branch": "main",
        "head_sha": _sha(main_head_sha, "required-review main head"),
        "repository": repository,
        "run_attempt": _positive_int(run_attempt, "required-review run attempt"),
        "status": "completed",
        "conclusion": "success",
    }
    observed = {
        "path": _workflow_path(value.get("path")),
        "workflow_id": value.get("workflow_id"),
        "event": value.get("event"),
        "head_branch": value.get("head_branch"),
        "head_sha": value.get("head_sha"),
        "repository": _mapping(value.get("repository"), "gate repository").get(
            "full_name"
        ),
        "run_attempt": value.get("run_attempt"),
        "status": value.get("status"),
        "conclusion": value.get("conclusion"),
    }
    if observed != expected:
        raise RulesetBlock("required-review gate run identity mismatch")
    return observed


def classify_required_review_gate_jobs(
    value: Mapping[str, Any], *, run_attempt: int
) -> dict[str, Any]:
    attempt = _positive_int(run_attempt, "required-review run attempt")
    total_count = value.get("total_count")
    jobs = value.get("jobs")
    if not isinstance(total_count, int) or total_count < 0 or total_count > 100:
        raise RulesetBlock("required-review jobs total_count is invalid")
    if not isinstance(jobs, list) or len(jobs) != total_count:
        raise RulesetBlock("required-review jobs observation is incomplete")
    matches = [
        _mapping(job, "required-review job")
        for job in jobs
        if isinstance(job, Mapping) and job.get("name") == REQUIRED_REVIEW_GATE_JOB_NAME
    ]
    if len(matches) != 1:
        raise RulesetBlock("required-review publish job is not unique")
    job = matches[0]
    job_id = _positive_int(job.get("id"), "required-review publish job id")
    if (
        job.get("run_attempt") != attempt
        or job.get("status") != "completed"
        or job.get("conclusion") != "success"
    ):
        raise RulesetBlock("required-review publish job did not complete exactly")
    return {
        "id": job_id,
        "name": REQUIRED_REVIEW_GATE_JOB_NAME,
        "run_attempt": attempt,
        "status": "completed",
        "conclusion": "success",
    }


def classify_required_review_gate_artifact(
    value: Mapping[str, Any], *, run_id: int, run_attempt: int, main_head_sha: str
) -> dict[str, Any]:
    gate_run_id = _positive_int(run_id, "required-review run id")
    attempt = _positive_int(run_attempt, "required-review run attempt")
    total_count = value.get("total_count")
    artifacts = value.get("artifacts")
    if not isinstance(total_count, int) or total_count < 0 or total_count > 100:
        raise RulesetBlock("required-review artifact total_count is invalid")
    if not isinstance(artifacts, list) or len(artifacts) != total_count:
        raise RulesetBlock("required-review artifact observation is incomplete")
    expected_name = f"qikvrt-native-account-review-plan-{gate_run_id}-{attempt}"
    matches = [
        _mapping(item, "required-review artifact")
        for item in artifacts
        if isinstance(item, Mapping) and item.get("name") == expected_name
    ]
    if len(matches) != 1:
        raise RulesetBlock("required-review blocked-plan artifact is not unique")
    artifact = matches[0]
    artifact_id = _positive_int(artifact.get("id"), "required-review artifact id")
    if artifact.get("expired") is not False:
        raise RulesetBlock("required-review artifact is expired")
    producer = _mapping(artifact.get("workflow_run"), "artifact producer")
    if (
        producer.get("id") != gate_run_id
        or producer.get("head_sha") != _sha(main_head_sha, "artifact producer main head")
    ):
        raise RulesetBlock("required-review artifact producer mismatch")
    archive_digest = _artifact_archive_digest(artifact.get("digest"))
    return {
        "id": artifact_id,
        "name": expected_name,
        "digest": archive_digest,
    }


def _required_review_subject_from_plan(
    plan: Mapping[str, Any], selection: Mapping[str, Any], pr: Mapping[str, Any], commit: Mapping[str, Any]
) -> dict[str, Any]:
    from tools.qikvrt_native_account_review import (
        NO_EFFECT,
        NativeAccountReviewError,
        validate_plan,
    )

    try:
        sealed = validate_plan(plan)
    except NativeAccountReviewError as exc:
        raise RulesetBlock(f"required-review blocked plan is invalid: {exc}") from exc
    if (
        sealed.get("event") != NO_EFFECT
        or sealed.get("effect_permitted") is not False
        or sealed.get("first_blocker") != "CODE_OWNER_RULE_NOT_ENFORCED"
    ):
        raise RulesetBlock("required-review plan is not the exact ruleset blocker")
    number = _positive_int(sealed.get("pr_number"), "required-review pull request")
    expected_head = _sha(sealed.get("head_sha"), "blocked-plan head")
    expected_tree = _sha(sealed.get("tree_sha"), "blocked-plan tree")
    expected_base = _sha(sealed.get("base_sha"), "blocked-plan base")
    evidence_fingerprint = _sha256(
        sealed.get("evidence_fingerprint"), "blocked-plan evidence fingerprint"
    )
    if (
        selection.get("schema") != "qikvrt_native_account_review_event_v1"
        or selection.get("state") != "CANDIDATE"
        or selection.get("artifact_pr_number") != number
        or selection.get("artifact_head") != expected_head
        or selection.get("artifact_fingerprint") != evidence_fingerprint
        or not isinstance(selection.get("upstream_run_id"), int)
        or selection.get("upstream_run_id", 0) <= 0
        or not isinstance(selection.get("upstream_run_attempt"), int)
        or selection.get("upstream_run_attempt", 0) <= 0
    ):
        raise RulesetBlock("required-review selection and blocked plan differ")
    if pr.get("number") != number or pr.get("state") != "open":
        raise RulesetBlock("required-review pull request is not exact and open")
    head = _mapping(pr.get("head"), "pull request head")
    base = _mapping(pr.get("base"), "pull request base")
    head_repo = _mapping(head.get("repo"), "pull request head repository").get(
        "full_name"
    )
    base_repo = _mapping(base.get("repo"), "pull request base repository").get(
        "full_name"
    )
    if head_repo != "Goldkelch/qik-vrt" or base_repo != "Goldkelch/qik-vrt":
        raise RulesetBlock("required-review pull request is not role-local")
    head_sha = _sha(head.get("sha"), "pull request head")
    if head_sha != expected_head:
        raise RulesetBlock("required-review pull request head drifted")
    if base.get("ref") != "main":
        raise RulesetBlock("required-review pull request base is not main")
    tree_sha = _sha(
        _mapping(commit.get("tree"), "head commit tree").get("sha"),
        "pull request head tree",
    )
    if tree_sha != expected_tree:
        raise RulesetBlock("required-review pull request tree drifted")
    base_sha = _sha(base.get("sha"), "pull request base")
    if base_sha != expected_base:
        raise RulesetBlock("required-review pull request base drifted")
    return {
        "pull_request": number,
        "head_repository": head_repo,
        "head_ref": str(head.get("ref") or ""),
        "head_sha": head_sha,
        "head_tree_sha": tree_sha,
        "base_repository": base_repo,
        "base_ref": "main",
        "base_sha": base_sha,
        "evidence_fingerprint": evidence_fingerprint,
        "blocked_plan_sha256": _sha256(
            sealed.get("plan_sha256"), "blocked-plan seal"
        ),
    }


def _validate_review_resume_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    binding = json.loads(json.dumps(dict(value)))
    if binding.get("schema") != REVIEW_RESUME_BINDING_SCHEMA:
        raise RulesetBlock("review-resume binding schema mismatch")
    fingerprint = _sha256(binding.pop("fingerprint", None), "review-resume fingerprint")
    if digest(binding) != fingerprint:
        raise RulesetBlock("review-resume fingerprint mismatch")
    binding["fingerprint"] = fingerprint
    return binding


def materialize_review_resume_binding(
    token: str,
    *,
    repository: str,
    main_head_sha: str,
    run_id: int,
    run_attempt: int,
    workflow_id: int,
) -> dict[str, Any]:
    if repository != "Goldkelch/qik-vrt":
        raise RulesetBlock("review-resume repository mismatch")
    gate_run_id = _positive_int(run_id, "required-review run id")
    gate_run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{gate_run_id}", token
    )
    classify_required_review_gate_run(
        gate_run,
        repository=repository,
        main_head_sha=main_head_sha,
        run_attempt=run_attempt,
        workflow_id=workflow_id,
    )
    jobs = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{gate_run_id}/jobs?filter=latest&per_page=100",
        token,
    )
    gate_job = classify_required_review_gate_jobs(jobs, run_attempt=run_attempt)
    artifacts = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{gate_run_id}/artifacts?per_page=100",
        token,
    )
    artifact = classify_required_review_gate_artifact(
        artifacts,
        run_id=gate_run_id,
        run_attempt=run_attempt,
        main_head_sha=main_head_sha,
    )
    archive = github_get_bytes(
        f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact['id']}/zip",
        token,
    )
    files = _json_files_from_zip(
        archive,
        expected_digest=artifact["digest"],
        required_names=("plan.json", "selection.json"),
    )
    plan = files["plan.json"]
    selection = files["selection.json"]
    number = _positive_int(plan.get("pr_number"), "required-review pull request")
    pr = github_get(
        f"https://api.github.com/repos/{repository}/pulls/{number}", token
    )
    head_sha = _sha(
        _mapping(pr.get("head"), "pull request head").get("sha"),
        "pull request head",
    )
    commit = github_get(
        f"https://api.github.com/repos/{repository}/git/commits/{head_sha}", token
    )
    subject = _required_review_subject_from_plan(plan, selection, pr, commit)
    raw = {
        "schema": REVIEW_RESUME_BINDING_SCHEMA,
        "repository": repository,
        "gate": {
            "workflow_path": REQUIRED_REVIEW_GATE_PATH,
            "workflow_id": workflow_id,
            "run_id": gate_run_id,
            "run_attempt": run_attempt,
            "event": "workflow_run",
            "main_head_sha": main_head_sha,
            "job": gate_job,
            "artifact": {
                **artifact,
                "plan_sha256": _sha256(
                    plan.get("plan_sha256"), "blocked-plan seal"
                ),
                "selection_sha256": digest(selection),
            },
        },
        "subject": subject,
    }
    return {**raw, "fingerprint": digest(raw)}


def reobserve_review_resume_binding(
    token: str,
    *,
    repository: str,
    main_head_sha: str,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    expected = _validate_review_resume_binding(binding)
    gate = _mapping(expected.get("gate"), "review-resume gate")
    observed = materialize_review_resume_binding(
        token,
        repository=repository,
        main_head_sha=main_head_sha,
        run_id=_positive_int(gate.get("run_id"), "required-review run id"),
        run_attempt=_positive_int(
            gate.get("run_attempt"), "required-review run attempt"
        ),
        workflow_id=_positive_int(
            gate.get("workflow_id"), "required-review workflow id"
        ),
    )
    if observed != expected:
        raise RulesetBlock("review-resume binding drifted")
    live_main = github_get(
        f"https://api.github.com/repos/{repository}/git/ref/heads/main", token
    )
    if _mapping(live_main.get("object"), "live main object").get("sha") != main_head_sha:
        raise RulesetBlock("review-resume main head drifted")
    return observed


def reobserve_review_resume_binding_from_environment() -> dict[str, Any]:
    try:
        binding = json.loads(os.environ.get("REQUEST_REVIEW_JSON", ""))
    except json.JSONDecodeError as exc:
        raise RulesetBlock("review-resume dispatch binding is invalid") from exc
    return reobserve_review_resume_binding(
        os.environ.get("GH_TOKEN", ""),
        repository=os.environ.get("GITHUB_REPOSITORY", ""),
        main_head_sha=os.environ.get("REQUEST_MAIN_HEAD", ""),
        binding=_mapping(binding, "review-resume dispatch binding"),
    )


def classify_exact_run_artifact(
    value: Mapping[str, Any], *, run_id: int, expected_name: str
) -> dict[str, Any]:
    producer_run_id = _positive_int(run_id, "artifact producer run id")
    total_count = value.get("total_count")
    artifacts = value.get("artifacts")
    if not isinstance(total_count, int) or total_count < 0 or total_count > 100:
        raise RulesetBlock("artifact total_count is invalid")
    if not isinstance(artifacts, list) or len(artifacts) != total_count:
        raise RulesetBlock("artifact observation is incomplete")
    matches = [
        _mapping(item, "workflow artifact")
        for item in artifacts
        if isinstance(item, Mapping) and item.get("name") == expected_name
    ]
    if len(matches) != 1:
        raise RulesetBlock(f"exact artifact is not unique: {expected_name}")
    artifact = matches[0]
    if artifact.get("expired") is not False:
        raise RulesetBlock("exact artifact is expired")
    producer = _mapping(artifact.get("workflow_run"), "artifact producer")
    if producer.get("id") != producer_run_id:
        raise RulesetBlock("exact artifact producer mismatch")
    return {
        "id": _positive_int(artifact.get("id"), "artifact id"),
        "name": expected_name,
        "digest": _artifact_archive_digest(artifact.get("digest")),
    }


def parse_ruleset_reconciler_locator(display_title: Any) -> dict[str, Any]:
    if not isinstance(display_title, str):
        raise RulesetBlock("ruleset reconciler locator is missing")
    match = re.fullmatch(
        r"qikvrt-ruleset intent=([0-9a-f]{64}) "
        r"seq=([1-9][0-9]*) transport-attempt=(1)",
        display_title,
    )
    if match is None:
        raise RulesetBlock("ruleset reconciler locator is invalid")
    return {
        "intent_sha256": match.group(1),
        "sequence": int(match.group(2)),
        "transport_attempt": int(match.group(3)),
    }


def ruleset_reconciler_title(
    *, intent_sha256: str, sequence: int, transport_attempt: int
) -> str:
    """Return the deterministic locator for one already-validated intent.

    The title is only a scan locator.  Callers must still bind the matching run
    to the exact source artifact, stable workflow id/path, repository, main, and
    event before treating it as an accepted repository_dispatch.
    """
    title = (
        f"qikvrt-ruleset intent={_sha256(intent_sha256, 'ruleset intent')} "
        f"seq={_positive_int(sequence, 'ruleset sequence')} "
        f"transport-attempt={transport_attempt}"
    )
    if transport_attempt != 1 or len(title) >= 255:
        raise RulesetBlock("ruleset reconciler locator exceeds its exact ABI")
    parse_ruleset_reconciler_locator(title)
    return title


def split_ruleset_dispatch_transport(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate and remove the durable transport locator from an event.

    The source artifact seals the semantic repository-dispatch request before
    any transport exists.  The scheduled outbox consumer adds exactly one
    transport object.  Comparing the incoming event to the source artifact
    therefore requires an explicit, validated projection instead of either
    rejecting the valid locator or silently ignoring arbitrary extra fields.
    """
    payload = dict(_mapping(value, "ruleset repository-dispatch payload"))
    if set(payload) != {
        "schema",
        "repository",
        "source",
        "binding",
        "review",
        "causal",
        "transport",
    }:
        raise RulesetBlock("ruleset repository-dispatch payload key set is invalid")
    transport = dict(_mapping(payload.pop("transport"), "ruleset transport locator"))
    if (
        set(transport) != {"intent_sha256", "sequence", "attempt"}
        or re.fullmatch(r"[0-9a-f]{64}", str(transport.get("intent_sha256")))
        is None
        or isinstance(transport.get("sequence"), bool)
        or not isinstance(transport.get("sequence"), int)
        or transport.get("sequence", 0) < 1
        or transport.get("attempt") not in {1, 2}
    ):
        raise RulesetBlock("ruleset transport locator is invalid")
    return payload, transport


def requested_review_executor_title(plan: Mapping[str, Any]) -> str:
    if (
        plan.get("schema") != "qikvrt_ruleset_review_resume_plan_v1"
        or plan.get("action") != "DISPATCH_REQUESTED_REVIEW_EXECUTOR"
        or plan.get("d0") != 2
        or plan.get("productive_effect") is not False
    ):
        raise RulesetBlock("ruleset review-resume plan cannot locate a successor")
    evaluator_sha = _sha(plan.get("evaluator_sha"), "requested-review evaluator SHA")
    return (
        f"QIKVRT requested review admission-v2 evaluator-{evaluator_sha} "
        f"pr={_positive_int(plan.get('pull_request'), 'resume pull request')} "
        f"head={_sha(plan.get('head_sha'), 'resume head')} "
        f"fp={_sha256(plan.get('evidence_fingerprint'), 'resume fingerprint')}"
    )


def review_resume_transport_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    requested_review_executor_title(plan)
    keys = (
        "schema",
        "state",
        "d0",
        "action",
        "reconciler_run_id",
        "reconciler_run_attempt",
        "target_workflow_id",
        "evaluator_sha",
        "pull_request",
        "head_sha",
        "evidence_fingerprint",
        "resume_fingerprint",
        "source_artifact",
        "reconciler_artifact",
        "review_resume",
        "productive_effect",
    )
    result = {key: plan.get(key) for key in keys}
    if any(value is None for value in result.values()):
        raise RulesetBlock("review-resume transport projection is incomplete")
    return result


def reconciler_rerun_transport_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    if (
        plan.get("schema") != "qikvrt_ruleset_review_resume_plan_v1"
        or plan.get("action") != "RERUN_RECONCILER_ONCE"
        or plan.get("state") != "REOBSERVE"
        or plan.get("d0") != 2
        or plan.get("reconciler_run_attempt") != 1
        or plan.get("productive_effect") is not False
    ):
        raise RulesetBlock("ruleset rerun plan is not exact attempt 1")
    keys = (
        "schema",
        "state",
        "d0",
        "action",
        "reconciler_run_id",
        "reconciler_run_attempt",
        "source_artifact",
        "review_resume",
        "productive_effect",
    )
    result = {key: plan.get(key) for key in keys}
    if any(value is None for value in result.values()):
        raise RulesetBlock("ruleset rerun transport projection is incomplete")
    return result


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise RulesetBlock(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RulesetBlock(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise RulesetBlock(f"{label} lacks a timezone")
    return parsed.astimezone(timezone.utc)


def classify_bound_successor_scan(
    runs: Sequence[Mapping[str, Any]],
    *,
    scan_complete: bool,
    title: str,
    workflow_id: int,
    workflow_path: str,
    event: str,
    repository: str,
    main_head_sha: str,
    not_before: str,
) -> dict[str, Any]:
    """Classify an exact accepted transport without trusting a display title.

    A title match is merely a locator.  Any such locator with a different
    stable identity is an ambiguity and therefore cannot authorize replay.
    """
    expected_workflow_id = _positive_int(workflow_id, "successor workflow id")
    expected_head = _sha(main_head_sha, "successor main head")
    lower_bound = _timestamp(not_before, "successor scan lower bound")
    matches: list[dict[str, Any]] = []
    for raw in runs:
        run = _mapping(raw, "successor workflow run")
        if run.get("display_title") != title:
            continue
        observed = {
            "workflow_id": run.get("workflow_id"),
            "path": _workflow_path(run.get("path")),
            "event": run.get("event"),
            "head_branch": run.get("head_branch"),
            "head_sha": run.get("head_sha"),
            "repository": _mapping(
                run.get("repository"), "successor repository"
            ).get("full_name"),
        }
        expected = {
            "workflow_id": expected_workflow_id,
            "path": workflow_path,
            "event": event,
            "head_branch": "main",
            "head_sha": expected_head,
            "repository": repository,
        }
        if observed != expected:
            raise RulesetBlock("successor locator has conflicting stable identity")
        created = _timestamp(run.get("created_at"), "successor creation time")
        if created < lower_bound:
            # The same deterministic locator can have a bounded predecessor
            # transport.  Once attempt-2 intent is durable, only successors
            # created at or after that intent belong to the current ordinal.
            continue
        status = run.get("status")
        if status not in ACTIVE_RUN_STATUSES and status != "completed":
            raise RulesetBlock("successor locator has unknown status")
        matches.append(
            {
                "id": _positive_int(run.get("id"), "successor run id"),
                "run_attempt": _positive_int(
                    run.get("run_attempt"), "successor run attempt"
                ),
                "status": status,
                "conclusion": run.get("conclusion"),
            }
        )
    if len(matches) > 1:
        return {"state": "AMBIGUOUS_ACCEPTED_RUNS", "matches": matches}
    if len(matches) == 1:
        match = matches[0]
        return {
            "state": (
                "TRANSPORT_PENDING"
                if match["status"] in ACTIVE_RUN_STATUSES
                else "TRANSPORT_COMPLETED"
            ),
            "match": match,
        }
    if not scan_complete:
        return {"state": "SCAN_INCOMPLETE"}
    return {"state": "ORPHAN"}


def validate_completed_requested_review_successor(
    token: str,
    *,
    repository: str,
    main_head_sha: str,
    workflow_id: int,
    run_id: int,
    run_attempt: int,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Require an exact successful executor job, artifact, and ledger receipt."""
    from tools.qikvrt_native_account_review import (
        NativeAccountReviewError,
        trusted_executor_run_is_valid,
        verify_trusted_executor_producer_binding,
    )
    from tools.qikvrt_requested_review_executor import _canonical_sha256

    expected_main = _sha(main_head_sha, "requested-review successor main")
    expected_workflow_id = _positive_int(
        workflow_id, "requested-review successor workflow id"
    )
    expected_run_id = _positive_int(run_id, "requested-review successor run id")
    expected_attempt = _positive_int(
        run_attempt, "requested-review successor run attempt"
    )
    requested_review_executor_title(plan)
    workflow = github_get(
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        "qikvrt_requested_review_executor.yml",
        token,
    )
    if (
        workflow.get("id") != expected_workflow_id
        or workflow.get("path") != REQUESTED_REVIEW_EXECUTOR_PATH
    ):
        raise RulesetBlock("requested-review terminal workflow identity mismatch")
    run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{expected_run_id}",
        token,
    )
    if not trusted_executor_run_is_valid(
        run,
        workflow,
        repository,
        expected_main,
        expected_run_id,
        expected_attempt,
    ):
        raise RulesetBlock("requested-review successor is not exact terminal success")
    if run.get("display_title") != requested_review_executor_title(plan):
        raise RulesetBlock("requested-review successor locator drifted")
    live_main = github_get(
        f"https://api.github.com/repos/{repository}/git/ref/heads/main", token
    )
    if _mapping(live_main.get("object"), "requested-review live main").get(
        "sha"
    ) != expected_main:
        raise RulesetBlock("requested-review successor main drifted")

    jobs = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{expected_run_id}"
        "/jobs?filter=all&per_page=100",
        token,
    )
    total = jobs.get("total_count")
    values = jobs.get("jobs")
    if (
        not isinstance(total, int)
        or total < 0
        or total > 100
        or not isinstance(values, list)
        or len(values) != total
    ):
        raise RulesetBlock("requested-review successor jobs are incomplete")
    job_matches = [
        _mapping(raw, "requested-review successor job")
        for raw in values
        if isinstance(raw, Mapping)
        and raw.get("name") == REQUESTED_REVIEW_EXECUTOR_JOB_NAME
        and raw.get("run_attempt") == expected_attempt
    ]
    if len(job_matches) != 1:
        raise RulesetBlock("requested-review successor job is not unique")
    job = job_matches[0]
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        raise RulesetBlock("requested-review successor job is not successful")

    pr_number = _positive_int(plan.get("pull_request"), "requested-review pull request")
    head = _sha(plan.get("head_sha"), "requested-review head")
    fingerprint = _sha256(
        plan.get("evidence_fingerprint"), "requested-review fingerprint"
    )
    artifact_name = (
        f"qikvrt-mesh-review-pr-{pr_number}-{head}-{fingerprint}-"
        f"run-{expected_run_id}-attempt-{expected_attempt}"
    )
    artifacts = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{expected_run_id}"
        "/artifacts?per_page=100",
        token,
    )
    artifact = classify_exact_run_artifact(
        artifacts, run_id=expected_run_id, expected_name=artifact_name
    )
    archive = github_get_bytes(
        f"https://api.github.com/repos/{repository}/actions/artifacts/"
        f"{artifact['id']}/zip",
        token,
    )
    files = _artifact_files_from_zip(
        archive,
        expected_digest=artifact["digest"],
        required_names=(
            "review.json",
            "review.diff",
            "ledger-write.json",
            "review-transport.json",
            "producer-binding.json",
        ),
    )
    try:
        review = dict(_mapping(json.loads(files["review.json"]), "review receipt"))
        ledger = dict(
            _mapping(json.loads(files["ledger-write.json"]), "review ledger receipt")
        )
        producer = dict(
            _mapping(json.loads(files["producer-binding.json"]), "review producer binding")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RulesetBlock("requested-review successor artifact JSON is invalid") from exc
    try:
        verify_trusted_executor_producer_binding(
            producer,
            repository=repository,
            run_id=expected_run_id,
            run_attempt=expected_attempt,
            artifact_name=artifact_name,
            pr_number=pr_number,
            head_sha=head,
            evidence_fingerprint=fingerprint,
            files={
                name: files[name]
                for name in (
                    "review.json",
                    "review.diff",
                    "ledger-write.json",
                    "review-transport.json",
                )
            },
        )
    except NativeAccountReviewError as exc:
        raise RulesetBlock(str(exc)) from exc
    sealed_review = dict(review)
    claimed_receipt_digest = sealed_review.pop("receipt_payload_sha256", None)
    if (
        review.get("schema") != "qikvrt_mesh_repository_review_receipt_v1"
        or review.get("repository") != repository
        or review.get("pr_number") != pr_number
        or review.get("head_sha") != head
        or review.get("evidence_fingerprint") != fingerprint
        or claimed_receipt_digest != _canonical_sha256(sealed_review)
        or review.get("diff_sha256") != hashlib.sha256(files["review.diff"]).hexdigest()
    ):
        raise RulesetBlock("requested-review successor receipt binding mismatch")
    ledger_commit = _sha(ledger.get("ledger_commit"), "review ledger commit")
    ledger_path = review.get("ledger_path")
    if (
        ledger.get("schema") != "qikvrt_mesh_review_ledger_write_v1"
        or ledger.get("persisted") is not True
        or ledger.get("projection_current") is not True
        or ledger.get("first_blocker") is not None
        or not isinstance(ledger_path, str)
        or not ledger_path.startswith("state/mesh/reviews/")
    ):
        raise RulesetBlock("requested-review successor ledger receipt is not exact")
    ledger_ref = github_get(
        f"https://api.github.com/repos/{repository}/git/ref/heads/"
        "qikvrt/mesh-review-ledger-v1",
        token,
    )
    ledger_head = _sha(
        _mapping(ledger_ref.get("object"), "review ledger ref").get("sha"),
        "review ledger head",
    )
    comparison = github_get(
        f"https://api.github.com/repos/{repository}/compare/"
        f"{ledger_commit}...{ledger_head}",
        token,
    )
    if comparison.get("status") not in {"ahead", "identical"}:
        raise RulesetBlock("requested-review ledger commit is not on the live ledger")
    quoted_path = urllib.parse.quote(ledger_path, safe="/")
    content = github_get(
        f"https://api.github.com/repos/{repository}/contents/{quoted_path}"
        f"?ref={ledger_commit}",
        token,
    )
    blob = github_get(
        f"https://api.github.com/repos/{repository}/git/blobs/"
        f"{_sha(content.get('sha'), 'review ledger receipt blob')}",
        token,
    )
    if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
        raise RulesetBlock("requested-review ledger receipt blob is invalid")
    try:
        ledger_receipt_bytes = base64.b64decode(
            "".join(blob["content"].split()), validate=True
        )
    except (ValueError, TypeError) as exc:
        raise RulesetBlock("requested-review ledger receipt blob is not base64") from exc
    if ledger_receipt_bytes != files["review.json"]:
        raise RulesetBlock("requested-review artifact and ledger receipt differ")
    return {
        "schema": "qikvrt_ruleset_requested_review_terminal_v1",
        "state": "REOBSERVE",
        "d0": 2,
        "action": "NONE",
        "first_blocker": "REQUESTED_REVIEW_EXACT_LEDGER_CONTINUATION_OBSERVED",
        "run_id": expected_run_id,
        "run_attempt": expected_attempt,
        "job_id": _positive_int(job.get("id"), "requested-review successor job id"),
        "artifact": artifact,
        "ledger_commit": ledger_commit,
        "productive_effect": False,
    }


def _bounded_repository_artifacts(
    token: str,
    *,
    repository: str,
    name_pattern: re.Pattern[str],
    max_pages: int | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    """Return every retained matching artifact with complete pagination.

    Production callers do not pass a page cap: a fixed newest-artifact window
    can permanently starve an older retained outbox.  ``max_pages`` exists only
    for fail-closed tests/diagnostics; truncation is always reported explicitly.
    """
    if max_pages is not None and max_pages <= 0:
        raise RulesetBlock("artifact scan bound is invalid")
    matches: list[dict[str, Any]] = []
    complete = False
    page = 1
    while max_pages is None or page <= max_pages:
        value = github_get(
            f"https://api.github.com/repos/{repository}/actions/artifacts"
            f"?per_page=100&page={page}",
            token,
        )
        artifacts = value.get("artifacts")
        if not isinstance(artifacts, list) or len(artifacts) > 100:
            raise RulesetBlock("repository artifact page is invalid")
        for raw in artifacts:
            artifact = _mapping(raw, "repository artifact")
            name = artifact.get("name")
            if isinstance(name, str) and name_pattern.fullmatch(name):
                producer = _mapping(
                    artifact.get("workflow_run"), "repository artifact producer"
                )
                matches.append(
                    {
                        "id": _positive_int(artifact.get("id"), "artifact id"),
                        "name": name,
                        "digest": _artifact_archive_digest(artifact.get("digest")),
                        "expired": artifact.get("expired"),
                        "created_at": artifact.get("created_at"),
                        "producer_run_id": _positive_int(
                            producer.get("id"), "artifact producer run id"
                        ),
                    }
                )
        if len(artifacts) < 100:
            complete = True
            break
        page += 1
    matches.sort(
        key=lambda item: (
            _timestamp(item.get("created_at"), "artifact creation time"),
            item["id"],
        )
    )
    return matches, complete


def _current_ruleset_outbox_intent(
    token: str,
    *,
    repository: str,
    lane: str,
    main_head_sha: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Read one exact FIFO item without repository-wide artifact discovery."""
    from tools.qikvrt_ruleset_outbox import GitHubLedgerBackend, read_next

    item = read_next(GitHubLedgerBackend(repository, token), lane)
    if item.get("state") == "EMPTY":
        return None, None
    if item.get("state") != "PENDING":
        raise RulesetBlock("ruleset outbox next-state is invalid")
    intent = _mapping(item.get("intent"), "ruleset outbox intent")
    payload = _mapping(intent.get("payload"), "ruleset outbox payload")
    if (
        payload.get("repository") != repository
        or payload.get("lane") != lane
        or payload.get("main_head_sha") != main_head_sha
    ):
        raise RulesetBlock("ruleset outbox live binding mismatch")
    artifact = _mapping(intent.get("artifact"), "ruleset outbox artifact")
    producer = _mapping(payload.get("producer"), "ruleset outbox producer")
    candidate = {
        "id": _positive_int(artifact.get("id"), "ruleset outbox artifact id"),
        "name": artifact.get("name"),
        "digest": artifact.get("archive_sha256"),
        "expired": False,
        "producer_run_id": _positive_int(
            artifact.get("producer_run_id"), "ruleset outbox artifact producer"
        ),
        "producer_run_attempt": _positive_int(
            artifact.get("producer_run_attempt"),
            "ruleset outbox artifact producer attempt",
        ),
        "producer_workflow_id": _positive_int(
            artifact.get("producer_workflow_id"),
            "ruleset outbox artifact producer workflow",
        ),
        "payload_sha256": artifact.get("payload_sha256"),
    }
    if (
        not isinstance(candidate["name"], str)
        or not candidate["name"]
        or candidate["producer_run_id"] != producer.get("run_id")
        or candidate["producer_run_attempt"] != producer.get("run_attempt")
        or candidate["producer_workflow_id"] != producer.get("workflow_id")
    ):
        raise RulesetBlock("ruleset outbox artifact owner mismatch")
    return dict(item), candidate


def _bounded_workflow_runs_since(
    token: str,
    *,
    repository: str,
    workflow: str,
    event: str,
    not_before: str,
    max_pages: int | None = None,
) -> tuple[list[dict[str, Any]], bool]:
    if max_pages is not None and max_pages <= 0:
        raise RulesetBlock("workflow-run scan bound is invalid")
    lower_bound = _timestamp(not_before, "workflow-run scan lower bound")
    runs: list[dict[str, Any]] = []
    complete = False
    encoded_event = urllib.parse.quote(event, safe="")
    page = 1
    while max_pages is None or page <= max_pages:
        value = github_get(
            f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}"
            f"/runs?event={encoded_event}&branch=main&per_page=100&page={page}",
            token,
        )
        page_runs = value.get("workflow_runs")
        if not isinstance(page_runs, list) or len(page_runs) > 100:
            raise RulesetBlock("workflow-run scan page is invalid")
        mapped = [_mapping(raw, "workflow run scan item") for raw in page_runs]
        runs.extend(dict(raw) for raw in mapped)
        if len(mapped) < 100:
            complete = True
            break
        oldest = min(
            _timestamp(raw.get("created_at"), "workflow run creation time")
            for raw in mapped
        )
        if oldest < lower_bound:
            complete = True
            break
        page += 1
    return runs, complete


def _exact_repository_artifact(
    token: str, *, repository: str, name: str
) -> dict[str, Any] | None:
    encoded_name = urllib.parse.quote(name, safe="")
    value = github_get(
        f"https://api.github.com/repos/{repository}/actions/artifacts"
        f"?name={encoded_name}&per_page=100",
        token,
    )
    artifacts = value.get("artifacts")
    total = value.get("total_count")
    if (
        not isinstance(total, int)
        or total < 0
        or total > 100
        or not isinstance(artifacts, list)
        or len(artifacts) != total
    ):
        raise RulesetBlock("exact recovery artifact observation is incomplete")
    matches = [
        _mapping(raw, "exact recovery artifact")
        for raw in artifacts
        if isinstance(raw, Mapping) and raw.get("name") == name
    ]
    if len(matches) > 1:
        raise RulesetBlock("exact recovery artifact is not unique")
    if not matches:
        return None
    artifact = matches[0]
    if artifact.get("expired") is not False:
        raise RulesetBlock("exact recovery artifact is expired")
    producer = _mapping(artifact.get("workflow_run"), "exact recovery producer")
    return {
        "id": _positive_int(artifact.get("id"), "exact recovery artifact id"),
        "name": name,
        "digest": _artifact_archive_digest(artifact.get("digest")),
        "created_at": artifact.get("created_at"),
        "producer_run_id": _positive_int(
            producer.get("id"), "exact recovery artifact producer run id"
        ),
    }


def _exact_repository_artifact_exists(
    token: str, *, repository: str, name: str
) -> bool:
    return _exact_repository_artifact(token, repository=repository, name=name) is not None


def _validate_ruleset_dispatch_artifact(
    *,
    request: Mapping[str, Any],
    receipt: Mapping[str, Any] | None,
    review_file: Mapping[str, Any],
    locator: Mapping[str, Any],
    repository: str,
) -> dict[str, Any]:
    if request.get("event_type") != "qikvrt_ruleset_reconcile":
        raise RulesetBlock("ruleset source artifact event type mismatch")
    payload = _mapping(request.get("client_payload"), "ruleset client payload")
    if (
        payload.get("schema") != "qikvrt_ruleset_reconcile_dispatch_v1"
        or payload.get("repository") != repository
    ):
        raise RulesetBlock("ruleset source artifact envelope mismatch")
    source = _mapping(payload.get("source"), "ruleset source binding")
    if (
        source.get("workflow_path") != CONTINUATION_PATH
        or source.get("run_id") != locator.get("source_run_id")
        or source.get("run_attempt") != locator.get("source_run_attempt")
        or not isinstance(source.get("workflow_id"), int)
        or source.get("workflow_id", 0) <= 0
    ):
        raise RulesetBlock("ruleset source artifact run binding mismatch")
    binding = _mapping(payload.get("binding"), "ruleset state binding")
    for key in (
        "main_head_sha",
        "main_tree_sha",
        "policy_blob_sha",
        "pre_state_sha256",
        "desired_state_sha256",
    ):
        value = binding.get(key)
        if key.endswith("sha256"):
            _sha256(value, f"ruleset {key}")
        else:
            _sha(value, f"ruleset {key}")
    if binding.get("ruleset_id") != 19344903:
        raise RulesetBlock("ruleset source artifact ruleset id mismatch")
    causal = _mapping(payload.get("causal"), "ruleset causal binding")
    if (
        causal.get("d0") != 2
        or causal.get("state")
        not in {"REOBSERVE_RULESET_DRIFT", "REOBSERVE_RULESET_CURRENT"}
        or causal.get("productive_effect") is not False
    ):
        raise RulesetBlock("ruleset source artifact causal binding mismatch")
    review = _validate_review_resume_binding(
        _mapping(payload.get("review"), "ruleset review binding")
    )
    if review != review_file:
        raise RulesetBlock("ruleset source artifact review files differ")
    gate = _mapping(review.get("gate"), "review gate binding")
    subject = _mapping(review.get("subject"), "review subject binding")
    if (
        gate.get("run_id") != locator.get("gate_run_id")
        or gate.get("run_attempt") != locator.get("gate_run_attempt")
        or subject.get("pull_request") != locator.get("pull_request")
        or subject.get("head_sha") != locator.get("head_sha")
        or review.get("fingerprint") != locator.get("review_fingerprint")
    ):
        raise RulesetBlock("ruleset run locator and source artifact differ")
    if receipt is not None:
        if (
            receipt.get("schema") != "qikvrt_ruleset_reconcile_dispatch_receipt_v1"
            or receipt.get("state") != "DISPATCHED"
            or receipt.get("transport_ack") is not True
            or receipt.get("effect_observed") is not False
            or receipt.get("productive_effect") is not False
            or receipt.get("main_head_sha") != binding.get("main_head_sha")
            or receipt.get("main_tree_sha") != binding.get("main_tree_sha")
            or receipt.get("pre_state_sha256") != binding.get("pre_state_sha256")
            or receipt.get("desired_state_sha256")
            != binding.get("desired_state_sha256")
            or receipt.get("review_resume") != review
        ):
            raise RulesetBlock("ruleset source dispatch receipt mismatch")
    return {
        "source": dict(source),
        "binding": dict(binding),
        "review": review,
    }


def reobserve_ruleset_dispatch_artifact(
    token: str,
    *,
    repository: str,
    run_id: int,
    run_attempt: int,
    expected_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_run_id = _positive_int(run_id, "ruleset source run id")
    source_attempt = _positive_int(run_attempt, "ruleset source run attempt")
    artifacts = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{source_run_id}/artifacts?per_page=100",
        token,
    )
    artifact = classify_exact_run_artifact(
        artifacts,
        run_id=source_run_id,
        expected_name=(
            f"qikvrt-ruleset-reconcile-intent-{source_run_id}-{source_attempt}"
        ),
    )
    archive = github_get_bytes(
        f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact['id']}/zip",
        token,
    )
    files = _json_files_from_zip(
        archive,
        expected_digest=artifact["digest"],
        required_names=("dispatch-request.json", "review-resume-binding.json"),
    )
    request = files["dispatch-request.json"]
    payload = _mapping(request.get("client_payload"), "ruleset client payload")
    if expected_payload is not None and dict(payload) != dict(expected_payload):
        raise RulesetBlock("repository dispatch differs from source bridge artifact")
    review = _mapping(payload.get("review"), "ruleset review binding")
    gate = _mapping(review.get("gate"), "review gate binding")
    subject = _mapping(review.get("subject"), "review subject binding")
    locator = {
        "source_run_id": source_run_id,
        "source_run_attempt": source_attempt,
        "gate_run_id": gate.get("run_id"),
        "gate_run_attempt": gate.get("run_attempt"),
        "pull_request": subject.get("pull_request"),
        "head_sha": subject.get("head_sha"),
        "review_fingerprint": review.get("fingerprint"),
    }
    binding = _validate_ruleset_dispatch_artifact(
        request=request,
        receipt=None,
        review_file=files["review-resume-binding.json"],
        locator=locator,
        repository=repository,
    )
    return {**binding, "artifact": artifact, "request": dict(request)}


def _validate_current_reconciler_receipt(
    *,
    execution: Mapping[str, Any],
    receipt: Mapping[str, Any],
    review_file: Mapping[str, Any],
    source_binding: Mapping[str, Any],
    source_artifact_proof: Mapping[str, Any],
    source_run_proof: Mapping[str, Any],
    source_job_proof: Mapping[str, Any],
    pre_effect_proof: Mapping[str, Any] | None = None,
) -> None:
    source = _mapping(source_binding.get("source"), "ruleset source")
    binding = _mapping(source_binding.get("binding"), "ruleset binding")
    review = _mapping(source_binding.get("review"), "ruleset review")
    if (
        execution.get("schema")
        != "qikvrt_ruleset_reconcile_execution_binding_v1"
        or execution.get("event") != "repository_dispatch"
        or execution.get("main_head_sha") != binding.get("main_head_sha")
        or execution.get("main_tree_sha") != binding.get("main_tree_sha")
        or execution.get("policy_blob_sha") != binding.get("policy_blob_sha")
        or execution.get("ruleset_id") != 19344903
        or execution.get("desired_state_sha256")
        != binding.get("desired_state_sha256")
        or execution.get("source") != source
        or execution.get("review_resume") != review
        or execution.get("candidate_bytes_consumed") is not False
        or review_file != review
    ):
        raise RulesetBlock("ruleset reconciler execution binding mismatch")
    if (
        source_artifact_proof.get("artifact") != source_binding.get("artifact")
        or source_artifact_proof.get("source") != source
        or source_artifact_proof.get("binding") != binding
        or source_artifact_proof.get("review") != review
        or source_artifact_proof.get("secret_boundary_crossed") is not False
        or source_run_proof.get("state")
        not in {SOURCE_RUN_DURABLE_INTENT, SOURCE_RUN_TERMINAL_SUCCESS}
        or source_run_proof.get("secret_boundary_crossed") is not False
        or source_job_proof.get("state") != SOURCE_RUN_DURABLE_INTENT
        or source_job_proof.get("intent_step_name") != SOURCE_INTENT_STEP_NAME
        or source_job_proof.get("intent_step_conclusion") != "success"
        or source_job_proof.get("secret_boundary_crossed") is not False
    ):
        raise RulesetBlock("ruleset reconciler durable intent proof mismatch")
    if (
        receipt.get("schema") != SCHEMA
        or receipt.get("repository") != "Goldkelch/qik-vrt"
        or receipt.get("ruleset_id") != 19344903
        or receipt.get("state") != "CURRENT"
        or receipt.get("desired_state_sha256")
        != binding.get("desired_state_sha256")
    ):
        raise RulesetBlock("ruleset reconciler did not prove CURRENT")
    mutation = receipt.get("mutation")
    if mutation == "NONE":
        if (
            receipt.get("pre_state_sha256") != binding.get("desired_state_sha256")
            or receipt.get("effect_observed") is not False
        ):
            raise RulesetBlock("ruleset CURRENT no-op receipt is not exact")
    elif mutation == "PUT":
        authority_environment = _mapping(
            receipt.get("authority_environment_readback"),
            "ruleset Authority environment readback",
        )
        if (
            receipt.get("effect_observed") is not True
            or receipt.get("post_update_readback") is not True
            or receipt.get("pre_effect_double_read") is not True
            or receipt.get("immediate_pre_effect_reobservation") is not True
            or receipt.get("pre_effect_source_reobservation") is not True
            or receipt.get("write_concurrency") != "LAST_WRITER_WINS"
            or receipt.get("conditional_update_used") is not False
            or receipt.get("get_put_race_eliminated") is not False
            or receipt.get("converged_before_mutation") is not False
            or authority_environment.get("schema")
            != "qikvrt_ruleset_authority_environment_readback_v1"
            or authority_environment.get("state")
            != "VERIFIED_FOR_THIS_EFFECT_ONLY"
            or authority_environment.get("environment")
            != "qikvrt-ruleset-authority"
            or authority_environment.get("credential_name")
            != "QIKVRT_ENV_RULESET_ADMIN_TOKEN"
            or authority_environment.get("deployment_branch") != "main"
            or authority_environment.get("environment_secret_name_present") is not True
            or authority_environment.get("repository_scope_fallback_names_absent")
            is not True
            or authority_environment.get("organization_scope_fallback_names_absent")
            is not True
            or authority_environment.get("repository_owner")
            != {"login": "Goldkelch", "id": 293941403, "type": "User"}
            or authority_environment.get("organization_scope_readback")
            != "NOT_APPLICABLE_USER_OWNER"
            or authority_environment.get("secret_values_observed") is not False
        ):
            raise RulesetBlock("ruleset PUT receipt lacks exact readback")
        if (
            pre_effect_proof is None
            or pre_effect_proof.get("dispatch_artifact")
            != source_binding.get("artifact")
            or pre_effect_proof.get("review_resume") != review
            or pre_effect_proof.get("run_id") != source.get("run_id")
            or pre_effect_proof.get("run_attempt") != source.get("run_attempt")
            or pre_effect_proof.get("intent_step_name") != SOURCE_INTENT_STEP_NAME
            or pre_effect_proof.get("secret_boundary_crossed") is not False
        ):
            raise RulesetBlock("ruleset PUT pre-effect intent proof mismatch")
    else:
        raise RulesetBlock("ruleset CURRENT receipt mutation is invalid")


def plan_ruleset_review_resume(
    token: str,
    *,
    repository: str,
    trigger_run_id: int,
    trigger_run_attempt: int,
    trigger_workflow_id: int,
    trigger_main_head: str,
    trigger_display_title: str,
) -> dict[str, Any]:
    """Reobserve one exact reconciler completion without performing an effect."""
    if repository != "Goldkelch/qik-vrt":
        raise RulesetBlock("ruleset resume repository mismatch")
    run_id = _positive_int(trigger_run_id, "reconciler run id")
    attempt = _positive_int(trigger_run_attempt, "reconciler run attempt")
    workflow_id = _positive_int(trigger_workflow_id, "reconciler workflow id")
    main_head = _sha(trigger_main_head, "reconciler main head")
    locator = parse_ruleset_reconciler_locator(trigger_display_title)

    workflow = github_get(
        f"https://api.github.com/repos/{repository}/actions/workflows/qikvrt_ruleset_reconcile.yml",
        token,
    )
    if workflow.get("id") != workflow_id or workflow.get("path") != RULESET_RECONCILER_PATH:
        raise RulesetBlock("ruleset reconciler stable workflow identity mismatch")
    run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}", token
    )
    observed_run = {
        "id": run.get("id"),
        "run_attempt": run.get("run_attempt"),
        "workflow_id": run.get("workflow_id"),
        "path": _workflow_path(run.get("path")),
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "repository": _mapping(run.get("repository"), "reconciler repository").get(
            "full_name"
        ),
        "status": run.get("status"),
        "display_title": run.get("display_title"),
    }
    expected_run = {
        "id": run_id,
        "run_attempt": attempt,
        "workflow_id": workflow_id,
        "path": RULESET_RECONCILER_PATH,
        "event": "repository_dispatch",
        "head_branch": "main",
        "head_sha": main_head,
        "repository": repository,
        "status": "completed",
        "display_title": trigger_display_title,
    }
    if observed_run != expected_run:
        raise RulesetBlock("ruleset reconciler completion identity mismatch")
    live_main = github_get(
        f"https://api.github.com/repos/{repository}/git/ref/heads/main", token
    )
    if _mapping(live_main.get("object"), "live main object").get("sha") != main_head:
        raise RulesetBlock("ruleset resume main head drifted")

    from tools.qikvrt_ruleset_outbox import (
        GitHubLedgerBackend,
        lookup as lookup_outbox,
        request_for_transport_attempt,
    )

    outbox_item = lookup_outbox(
        GitHubLedgerBackend(repository, token),
        lane="ruleset-dispatch",
        sequence=locator["sequence"],
        fingerprint=locator["intent_sha256"],
    )
    transport = _mapping(
        _mapping(outbox_item.get("transport"), "ruleset outbox transports").get(
            str(locator["transport_attempt"])
        ),
        "ruleset outbox transport",
    )
    witnesses = outbox_item.get("witnesses")
    if not isinstance(witnesses, list):
        raise RulesetBlock("ruleset outbox witnesses are missing")
    matches = [
        _mapping(item, "ruleset source witness")
        for item in witnesses
        if isinstance(item, Mapping)
        and item.get("witness_sha256") == transport.get("witness_sha256")
    ]
    if len(matches) != 1:
        raise RulesetBlock("ruleset transport witness is not unique")
    witness = matches[0]
    witness_payload = _mapping(witness.get("payload"), "ruleset witness payload")
    source = _mapping(witness_payload.get("producer"), "ruleset dispatch source")
    source_run_id = _positive_int(source.get("run_id"), "source run id")
    source_attempt = _positive_int(source.get("run_attempt"), "source attempt")
    source_binding = reobserve_ruleset_dispatch_artifact(
        token,
        repository=repository,
        run_id=source_run_id,
        run_attempt=source_attempt,
    )
    source_artifact = _mapping(source_binding.get("artifact"), "source artifact")
    if (
        source_binding.get("request") != witness_payload.get("request")
        or source_artifact.get("id")
        != _mapping(witness.get("artifact"), "witness artifact").get("id")
        or source_artifact.get("digest")
        != _mapping(witness.get("artifact"), "witness artifact").get(
            "archive_sha256"
        )
        or request_for_transport_attempt(
            _mapping(outbox_item.get("intent"), "ruleset intent"),
            locator["transport_attempt"],
            witness=witness,
        ).get("client_payload", {}).get("transport")
        != {
            "intent_sha256": locator["intent_sha256"],
            "sequence": locator["sequence"],
            "attempt": locator["transport_attempt"],
        }
    ):
        raise RulesetBlock("reconciler locator and durable outbox witness differ")
    source_chronology = reobserve_dispatch_source(
        token,
        repository=repository,
        head_sha=main_head,
        run_id=source_run_id,
        run_attempt=source_attempt,
        workflow_id=_positive_int(source.get("workflow_id"), "source workflow id"),
    )
    review = reobserve_review_resume_binding(
        token,
        repository=repository,
        main_head_sha=main_head,
        binding=_mapping(source_binding.get("review"), "review-resume binding"),
    )

    conclusion = run.get("conclusion")
    if conclusion != "success":
        if attempt == 1:
            return {
                "schema": "qikvrt_ruleset_review_resume_plan_v1",
                "state": "REOBSERVE",
                "d0": 2,
                "action": "RERUN_RECONCILER_ONCE",
                "reconciler_run_id": run_id,
                "reconciler_run_attempt": attempt,
                "source_artifact": source_artifact,
                "source_chronology": source_chronology,
                "review_resume": review,
                "productive_effect": False,
            }
        return {
            "schema": "qikvrt_ruleset_review_resume_plan_v1",
            "state": "REQUEST_AUTHORITY",
            "d0": 3,
            "action": "NONE",
            "first_blocker": f"RULESET_RECONCILER_{str(conclusion).upper()}",
            "reconciler_run_id": run_id,
            "reconciler_run_attempt": attempt,
            "source_artifact": source_artifact,
            "source_chronology": source_chronology,
            "review_resume": review,
            "productive_effect": False,
        }

    artifacts = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100",
        token,
    )
    receipt_artifact = classify_exact_run_artifact(
        artifacts,
        run_id=run_id,
        expected_name=f"qikvrt-main-ruleset-receipt-{run_id}-{attempt}",
    )
    archive = github_get_bytes(
        f"https://api.github.com/repos/{repository}/actions/artifacts/{receipt_artifact['id']}/zip",
        token,
    )
    files = _json_files_from_zip(
        archive,
        expected_digest=receipt_artifact["digest"],
        required_names=(
            "execution-binding.json",
            "review-resume-binding.json",
            "reconcile-receipt.json",
            "source-dispatch-artifact-binding.json",
            "source-run-classification.json",
            "source-jobs-classification.json",
        ),
    )
    pre_effect: Mapping[str, Any] | None = None
    if files["reconcile-receipt.json"].get("mutation") == "PUT":
        pre_effect = _json_files_from_zip(
            archive,
            expected_digest=receipt_artifact["digest"],
            required_names=("pre-effect-source-binding.json",),
        )["pre-effect-source-binding.json"]
    _validate_current_reconciler_receipt(
        execution=files["execution-binding.json"],
        receipt=files["reconcile-receipt.json"],
        review_file=files["review-resume-binding.json"],
        source_binding=source_binding,
        source_artifact_proof=files["source-dispatch-artifact-binding.json"],
        source_run_proof=files["source-run-classification.json"],
        source_job_proof=files["source-jobs-classification.json"],
        pre_effect_proof=pre_effect,
    )
    target = github_get(
        f"https://api.github.com/repos/{repository}/actions/workflows/qikvrt_requested_review_executor.yml",
        token,
    )
    target_workflow_id = _positive_int(target.get("id"), "requested-review workflow id")
    if target.get("path") != REQUESTED_REVIEW_EXECUTOR_PATH:
        raise RulesetBlock("requested-review workflow path mismatch")
    subject = _mapping(review.get("subject"), "review-resume subject")
    resume_preimage = {
        "schema": "qikvrt_ruleset_review_resume_v1",
        "repository": repository,
        "reconciler": {
            "workflow_id": workflow_id,
            "run_id": run_id,
            "run_attempt": attempt,
            "artifact": receipt_artifact,
        },
        "source_artifact": source_artifact,
        "source_chronology": source_chronology,
        "review_resume": review,
        "target_workflow_id": target_workflow_id,
        "evaluator_sha": main_head,
    }
    return {
        "schema": "qikvrt_ruleset_review_resume_plan_v1",
        "state": "REOBSERVE",
        "d0": 2,
        "action": "DISPATCH_REQUESTED_REVIEW_EXECUTOR",
        "reconciler_run_id": run_id,
        "reconciler_run_attempt": attempt,
        "target_workflow_id": target_workflow_id,
        "evaluator_sha": main_head,
        "pull_request": subject["pull_request"],
        "head_sha": subject["head_sha"],
        "evidence_fingerprint": subject["evidence_fingerprint"],
        "resume_fingerprint": digest(resume_preimage),
        "source_artifact": source_artifact,
        "reconciler_artifact": receipt_artifact,
        "review_resume": review,
        "productive_effect": False,
    }


def classify_dispatch_source_run(
    value: Mapping[str, Any],
    *,
    repository: str,
    head_sha: str,
    run_attempt: int,
    workflow_id: int,
    allow_durable_intent: bool = False,
    allow_attempt_advance: bool = False,
) -> dict[str, Any]:
    if workflow_id <= 0:
        raise RulesetBlock("ruleset dispatch source workflow id must be positive")
    expected = {
        "path": CONTINUATION_PATH,
        "workflow_id": workflow_id,
        "event": "workflow_run",
        "head_branch": "main",
        "head_sha": head_sha,
        "repository": repository,
    }
    observed = {
        "path": _workflow_path(value.get("path")),
        "workflow_id": value.get("workflow_id"),
        "event": value.get("event"),
        "head_branch": value.get("head_branch"),
        "head_sha": value.get("head_sha"),
        "repository": _mapping(value.get("repository"), "source run repository").get(
            "full_name"
        ),
    }
    if observed != expected:
        raise RulesetBlock("ruleset dispatch source-run identity mismatch")
    observed_attempt = value.get("run_attempt")
    if (
        not isinstance(observed_attempt, int)
        or observed_attempt < run_attempt
        or (not allow_attempt_advance and observed_attempt != run_attempt)
    ):
        raise RulesetBlock("ruleset dispatch source run attempt mismatch")
    status = value.get("status")
    conclusion = value.get("conclusion")
    if status in ACTIVE_RUN_STATUSES:
        if allow_durable_intent:
            return {
                "state": SOURCE_RUN_DURABLE_INTENT,
                "status": status,
                "conclusion": conclusion,
            }
        return {
            "state": SOURCE_RUN_NONTERMINAL,
            "status": status,
            "conclusion": conclusion,
        }
    if status != "completed":
        raise RulesetBlock("ruleset dispatch source run has unknown status")
    if conclusion != "success":
        if allow_durable_intent and conclusion in {
            "failure",
            "cancelled",
            "timed_out",
            "action_required",
            "stale",
            "startup_failure",
        }:
            return {
                "state": SOURCE_RUN_DURABLE_INTENT,
                "status": status,
                "conclusion": conclusion,
            }
        raise RulesetBlock(
            f"ruleset dispatch source run completed without success: {conclusion}"
        )
    return {
        "state": SOURCE_RUN_TERMINAL_SUCCESS,
        "status": status,
        "conclusion": conclusion,
    }


def classify_dispatch_source_jobs(
    value: Mapping[str, Any], *, run_attempt: int, require_durable_intent: bool = False
) -> dict[str, Any]:
    if run_attempt <= 0:
        raise RulesetBlock("ruleset dispatch source run attempt must be positive")
    total_count = value.get("total_count")
    jobs = value.get("jobs")
    if not isinstance(total_count, int) or total_count < 0:
        raise RulesetBlock("ruleset dispatch source jobs total_count is invalid")
    if not isinstance(jobs, list):
        raise RulesetBlock("ruleset dispatch source jobs must be a list")
    if total_count > 100 or len(jobs) != total_count:
        raise RulesetBlock("ruleset dispatch source jobs observation is incomplete")
    observed_jobs = [_mapping(job, "source workflow job") for job in jobs]
    named_matches = [
        job for job in observed_jobs if job.get("name") == SOURCE_BRIDGE_JOB_NAME
    ]
    matches = [job for job in named_matches if job.get("run_attempt") == run_attempt]
    if named_matches and not matches:
        raise RulesetBlock("ruleset dispatch source bridge job attempt mismatch")
    if len(matches) != 1:
        raise RulesetBlock("ruleset dispatch source bridge job is not unique")
    job = matches[0]
    job_id = job.get("id")
    if not isinstance(job_id, int) or job_id <= 0:
        raise RulesetBlock("ruleset dispatch source bridge job id is invalid")
    if require_durable_intent:
        steps = job.get("steps")
        if not isinstance(steps, list):
            raise RulesetBlock("ruleset dispatch source bridge steps are missing")
        intent_steps = [
            _mapping(step, "source workflow step")
            for step in steps
            if isinstance(step, Mapping) and step.get("name") == SOURCE_INTENT_STEP_NAME
        ]
        if len(intent_steps) != 1:
            raise RulesetBlock("ruleset dispatch intent step is not unique")
        intent = intent_steps[0]
        intent_number = _positive_int(
            intent.get("number"), "ruleset dispatch intent step number"
        )
        if intent.get("status") != "completed" or intent.get("conclusion") != "success":
            raise RulesetBlock("ruleset dispatch intent was not durably preserved")
        transports = [
            _mapping(step, "source transport step")
            for step in steps
            if isinstance(step, Mapping)
            and step.get("name") == SOURCE_TRANSPORT_STEP_NAME
        ]
        if len(transports) != 1:
            raise RulesetBlock("ruleset dispatch transport step is not unique")
        transport = transports[0]
        if not isinstance(transport.get("number"), int) or transport["number"] <= intent_number:
            raise RulesetBlock("ruleset dispatch transport precedes durable intent")
        return {
            "state": SOURCE_RUN_DURABLE_INTENT,
            "job_id": job_id,
            "job_name": SOURCE_BRIDGE_JOB_NAME,
            "run_attempt": run_attempt,
            "intent_step_name": SOURCE_INTENT_STEP_NAME,
            "intent_step_number": intent_number,
            "intent_step_status": "completed",
            "intent_step_conclusion": "success",
            "transport_step_name": SOURCE_TRANSPORT_STEP_NAME,
            "transport_step_status": transport.get("status"),
            "transport_step_conclusion": transport.get("conclusion"),
        }
    if job.get("status") != "completed" or job.get("conclusion") != "success":
        raise RulesetBlock(
            "ruleset dispatch source bridge job did not complete successfully"
        )
    return {
        "state": SOURCE_RUN_TERMINAL_SUCCESS,
        "job_id": job_id,
        "job_name": SOURCE_BRIDGE_JOB_NAME,
        "run_attempt": run_attempt,
        "status": "completed",
        "conclusion": "success",
    }


def reobserve_dispatch_source(
    token: str,
    *,
    repository: str,
    head_sha: str,
    run_id: int,
    run_attempt: int,
    workflow_id: int,
) -> dict[str, Any]:
    if repository != "Goldkelch/qik-vrt":
        raise RulesetBlock("ruleset dispatch source repository mismatch")
    if run_id <= 0:
        raise RulesetBlock("ruleset dispatch source run id must be positive")
    run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}"
        f"/attempts/{run_attempt}",
        token,
    )
    run_result = classify_dispatch_source_run(
        run,
        repository=repository,
        head_sha=head_sha,
        run_attempt=run_attempt,
        workflow_id=workflow_id,
        allow_durable_intent=True,
    )
    jobs = github_get(
        "https://api.github.com/"
        f"repos/{repository}/actions/runs/{run_id}/jobs?filter=all&per_page=100",
        token,
    )
    job_result = classify_dispatch_source_jobs(
        jobs, run_attempt=run_attempt, require_durable_intent=True
    )
    live_main = github_get(
        f"https://api.github.com/repos/{repository}/git/ref/heads/main", token
    )
    if _mapping(live_main.get("object"), "live main object").get("sha") != head_sha:
        raise RulesetBlock("ruleset dispatch main head drifted before effect")
    return {
        "state": SOURCE_RUN_DURABLE_INTENT,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "workflow_id": workflow_id,
        "job_id": job_result["job_id"],
        "intent_step_name": SOURCE_INTENT_STEP_NAME,
        "transport_step_name": SOURCE_TRANSPORT_STEP_NAME,
        "source_run_state": run_result["state"],
        "intent_step_status": job_result["intent_step_status"],
        "intent_step_conclusion": job_result["intent_step_conclusion"],
        "head_sha": head_sha,
    }


def reobserve_dispatch_source_attempt_for_recovery(
    token: str,
    *,
    repository: str,
    head_sha: str,
    run_id: int,
    run_attempt: int,
    workflow_id: int,
) -> dict[str, Any]:
    """Bind one exact durable bridge intent before any transport effect."""
    attempt_run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}"
        f"/attempts/{run_attempt}",
        token,
    )
    attempt_result = classify_dispatch_source_run(
        attempt_run,
        repository=repository,
        head_sha=head_sha,
        run_attempt=run_attempt,
        workflow_id=workflow_id,
        allow_durable_intent=True,
    )
    latest_run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}", token
    )
    classify_dispatch_source_run(
        latest_run,
        repository=repository,
        head_sha=head_sha,
        run_attempt=run_attempt,
        workflow_id=workflow_id,
        allow_durable_intent=True,
    )
    jobs = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}"
        "/jobs?filter=all&per_page=100",
        token,
    )
    job_result = classify_dispatch_source_jobs(
        jobs, run_attempt=run_attempt, require_durable_intent=True
    )
    live_main = github_get(
        f"https://api.github.com/repos/{repository}/git/ref/heads/main", token
    )
    if _mapping(live_main.get("object"), "live main object").get("sha") != head_sha:
        raise RulesetBlock("ruleset dispatch main head drifted before recovery")
    return {
        "state": SOURCE_RUN_DURABLE_INTENT,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "workflow_id": workflow_id,
        "created_at": attempt_run.get("created_at"),
        "attempt_state": attempt_result["state"],
        "job_id": job_result["job_id"],
        "intent_step_status": job_result["intent_step_status"],
        "intent_step_conclusion": job_result["intent_step_conclusion"],
        "head_sha": head_sha,
    }


def classify_review_resume_source_run(
    value: Mapping[str, Any],
    *,
    repository: str,
    head_sha: str,
    run_attempt: int,
    workflow_id: int,
    allowed_events: frozenset[str] = frozenset({"workflow_run"}),
) -> dict[str, Any]:
    observed = {
        "path": _workflow_path(value.get("path")),
        "workflow_id": value.get("workflow_id"),
        "event": value.get("event"),
        "head_branch": value.get("head_branch"),
        "head_sha": value.get("head_sha"),
        "repository": _mapping(value.get("repository"), "resume source repository").get(
            "full_name"
        ),
        "run_attempt": value.get("run_attempt"),
    }
    expected = {
        "path": CONTINUATION_PATH,
        "workflow_id": _positive_int(workflow_id, "resume source workflow id"),
        "event": value.get("event"),
        "head_branch": "main",
        "head_sha": _sha(head_sha, "resume source main head"),
        "repository": repository,
        "run_attempt": _positive_int(run_attempt, "resume source attempt"),
    }
    if observed != expected:
        raise RulesetBlock("review-resume source-run identity mismatch")
    if observed["event"] not in allowed_events:
        raise RulesetBlock("review-resume source-run event mismatch")
    status = value.get("status")
    conclusion = value.get("conclusion")
    if status not in ACTIVE_RUN_STATUSES and status != "completed":
        raise RulesetBlock("review-resume source run has unknown status")
    return {"state": SOURCE_RUN_DURABLE_INTENT, "status": status, "conclusion": conclusion}


def classify_review_resume_source_jobs(
    value: Mapping[str, Any],
    *,
    run_attempt: int,
    intent_step_name: str = RULESET_REVIEW_RESUME_INTENT_STEP_NAME,
    transport_step_name: str = RULESET_REVIEW_RESUME_TRANSPORT_STEP_NAME,
    allowed_job_names: frozenset[str] = frozenset({RULESET_REVIEW_RESUME_JOB_NAME}),
) -> dict[str, Any]:
    total = value.get("total_count")
    jobs = value.get("jobs")
    if (
        not isinstance(total, int)
        or total < 0
        or total > 100
        or not isinstance(jobs, list)
        or len(jobs) != total
    ):
        raise RulesetBlock("review-resume source jobs observation is incomplete")
    matches = [
        _mapping(raw, "review-resume source job")
        for raw in jobs
        if isinstance(raw, Mapping)
        and raw.get("name") in allowed_job_names
        and raw.get("run_attempt") == run_attempt
    ]
    if len(matches) != 1:
        raise RulesetBlock("review-resume source job is not unique")
    job = matches[0]
    steps = job.get("steps")
    if not isinstance(steps, list):
        raise RulesetBlock("review-resume source steps are missing")

    def exact_step(name: str) -> Mapping[str, Any]:
        found = [
            _mapping(raw, "review-resume source step")
            for raw in steps
            if isinstance(raw, Mapping) and raw.get("name") == name
        ]
        if len(found) != 1:
            raise RulesetBlock(f"review-resume source step is not unique: {name}")
        return found[0]

    intent = exact_step(intent_step_name)
    transport = exact_step(transport_step_name)
    intent_number = _positive_int(intent.get("number"), "review-resume intent step")
    transport_number = _positive_int(
        transport.get("number"), "review-resume transport step"
    )
    if intent.get("status") != "completed" or intent.get("conclusion") != "success":
        raise RulesetBlock("review-resume intent was not durably preserved")
    if transport_number <= intent_number:
        raise RulesetBlock("review-resume transport precedes durable intent")
    return {
        "state": SOURCE_RUN_DURABLE_INTENT,
        "job_id": _positive_int(job.get("id"), "review-resume source job id"),
        "intent_step_name": intent_step_name,
        "intent_step_conclusion": "success",
        "transport_step_name": transport_step_name,
        "transport_step_status": transport.get("status"),
        "transport_step_conclusion": transport.get("conclusion"),
    }


def reobserve_ruleset_review_resume_intent(
    token: str,
    *,
    repository: str,
    run_id: int,
    run_attempt: int,
    artifact_name: str | None = None,
) -> dict[str, Any]:
    source_run_id = _positive_int(run_id, "review-resume source run id")
    source_attempt = _positive_int(run_attempt, "review-resume source attempt")
    expected_name = artifact_name or (
        f"qikvrt-ruleset-review-resume-intent-{source_run_id}-{source_attempt}"
    )
    name_match = RULESET_REVIEW_INTENT_PATTERN.fullmatch(expected_name)
    if (
        name_match is None
        or int(name_match.group(1)) != source_run_id
        or int(name_match.group(2)) != source_attempt
    ):
        raise RulesetBlock("review-resume intent artifact name is invalid")
    recovery_target = (
        (int(name_match.group(3)), int(name_match.group(4)))
        if name_match.group(3) is not None and name_match.group(4) is not None
        else None
    )
    artifacts = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{source_run_id}"
        "/artifacts?per_page=100",
        token,
    )
    artifact = classify_exact_run_artifact(
        artifacts,
        run_id=source_run_id,
        expected_name=expected_name,
    )
    archive = github_get_bytes(
        f"https://api.github.com/repos/{repository}/actions/artifacts/"
        f"{artifact['id']}/zip",
        token,
    )
    files = _json_files_from_zip(
        archive,
        expected_digest=artifact["digest"],
        required_names=(
            "resume-plan.json",
            "pre-dispatch-plan.json",
            "executor-dispatch-request.json",
        ),
    )
    plan = _mapping(files["resume-plan.json"], "review-resume plan")
    if plan != files["pre-dispatch-plan.json"]:
        raise RulesetBlock("review-resume intent plans differ")
    requested_review_executor_title(plan)
    request = _mapping(
        files["executor-dispatch-request.json"], "requested-review dispatch request"
    )
    expected_request = {
        "ref": "main",
        "return_run_details": True,
        "inputs": {
            "pr": str(plan["pull_request"]),
            "head": plan["head_sha"],
            "fingerprint": plan["evidence_fingerprint"],
            "evaluator_sha": plan["evaluator_sha"],
        },
    }
    if dict(request) != expected_request:
        raise RulesetBlock("requested-review dispatch request differs from exact plan")

    reconciler_run_id = _positive_int(
        plan.get("reconciler_run_id"), "resume reconciler run id"
    )
    reconciler_attempt = _positive_int(
        plan.get("reconciler_run_attempt"), "resume reconciler attempt"
    )
    if recovery_target is not None and recovery_target != (
        reconciler_run_id,
        reconciler_attempt,
    ):
        raise RulesetBlock("review-resume recovery artifact target differs from plan")
    reconciler_run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{reconciler_run_id}",
        token,
    )
    reconciler_head = _sha(
        reconciler_run.get("head_sha"), "resume reconciler main head"
    )
    source_workflow = github_get(
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        "qikvrt_autonomous_pr_head_continuation.yml",
        token,
    )
    source_workflow_id = _positive_int(
        source_workflow.get("id"), "review-resume source workflow id"
    )
    if source_workflow.get("path") != CONTINUATION_PATH:
        raise RulesetBlock("review-resume source workflow path mismatch")
    attempt_run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{source_run_id}"
        f"/attempts/{source_attempt}",
        token,
    )
    classify_review_resume_source_run(
        attempt_run,
        repository=repository,
        head_sha=reconciler_head,
        run_attempt=source_attempt,
        workflow_id=source_workflow_id,
        allowed_events=(
            frozenset({"schedule"})
            if recovery_target is not None
            else frozenset({"workflow_run"})
        ),
    )
    jobs = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{source_run_id}"
        "/jobs?filter=all&per_page=100",
        token,
    )
    job = classify_review_resume_source_jobs(
        jobs,
        run_attempt=source_attempt,
        allowed_job_names=(
            frozenset(
                {
                    RULESET_TRANSPORT_RECOVERY_JOB_NAME,
                    RULESET_RERUN_RECOVERY_JOB_NAME,
                }
            )
            if recovery_target is not None
            else frozenset({RULESET_REVIEW_RESUME_JOB_NAME})
        ),
    )
    current_plan = plan_ruleset_review_resume(
        token,
        repository=repository,
        trigger_run_id=reconciler_run_id,
        trigger_run_attempt=reconciler_attempt,
        trigger_workflow_id=_positive_int(
            reconciler_run.get("workflow_id"), "resume reconciler workflow id"
        ),
        trigger_main_head=reconciler_head,
        trigger_display_title=str(reconciler_run.get("display_title")),
    )
    if review_resume_transport_projection(current_plan) != review_resume_transport_projection(plan):
        raise RulesetBlock("review-resume live plan differs from durable intent")
    return {
        "artifact": artifact,
        "source_run_id": source_run_id,
        "source_run_attempt": source_attempt,
        "source_workflow_id": source_workflow_id,
        "source_created_at": attempt_run.get("created_at"),
        "source_job": job,
        "reconciler_run_id": reconciler_run_id,
        "reconciler_run_attempt": reconciler_attempt,
        "main_head_sha": reconciler_head,
        "plan": dict(plan),
        "dispatch_request": dict(request),
    }


def reobserve_ruleset_reconciler_rerun_intent(
    token: str,
    *,
    repository: str,
    run_id: int,
    run_attempt: int,
    artifact_name: str | None = None,
) -> dict[str, Any]:
    source_run_id = _positive_int(run_id, "rerun source run id")
    source_attempt = _positive_int(run_attempt, "rerun source attempt")
    expected_name = artifact_name or (
        f"qikvrt-ruleset-reconciler-rerun-intent-{source_run_id}-{source_attempt}"
    )
    name_match = RULESET_RERUN_INTENT_PATTERN.fullmatch(expected_name)
    if (
        name_match is None
        or int(name_match.group(1)) != source_run_id
        or int(name_match.group(2)) != source_attempt
    ):
        raise RulesetBlock("ruleset rerun intent artifact name is invalid")
    recovery_target = (
        int(name_match.group(3)) if name_match.group(3) is not None else None
    )
    artifacts = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{source_run_id}"
        "/artifacts?per_page=100",
        token,
    )
    artifact = classify_exact_run_artifact(
        artifacts,
        run_id=source_run_id,
        expected_name=expected_name,
    )
    archive = github_get_bytes(
        f"https://api.github.com/repos/{repository}/actions/artifacts/"
        f"{artifact['id']}/zip",
        token,
    )
    files = _json_files_from_zip(
        archive,
        expected_digest=artifact["digest"],
        required_names=("resume-plan.json", "reconciler-rerun-request.json"),
    )
    plan = _mapping(files["resume-plan.json"], "ruleset rerun plan")
    reconciler_rerun_transport_projection(plan)
    target_run_id = _positive_int(
        plan.get("reconciler_run_id"), "rerun target run id"
    )
    if recovery_target is not None and recovery_target != target_run_id:
        raise RulesetBlock("ruleset rerun recovery artifact target differs from plan")
    target_attempt = _positive_int(
        plan.get("reconciler_run_attempt"), "rerun target attempt"
    )
    request = _mapping(files["reconciler-rerun-request.json"], "rerun request")
    expected_request = {
        "schema": "qikvrt_ruleset_reconciler_rerun_request_v1",
        "repository": repository,
        "reconciler_run_id": target_run_id,
        "reconciler_run_attempt": target_attempt,
        "method": "POST",
        "endpoint": f"repos/{repository}/actions/runs/{target_run_id}/rerun",
        "target_attempt": 2,
        "productive_effect": False,
    }
    if dict(request) != expected_request:
        raise RulesetBlock("ruleset rerun request differs from exact plan")
    target_run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{target_run_id}",
        token,
    )
    target_current_attempt = _positive_int(
        target_run.get("run_attempt"), "rerun target current attempt"
    )
    if target_current_attempt > 2:
        raise RulesetBlock("ruleset rerun target advanced beyond bounded attempt 2")
    target_head = _sha(target_run.get("head_sha"), "rerun target main head")
    target_attempt_one = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{target_run_id}"
        "/attempts/1",
        token,
    )
    reconciler_workflow = github_get(
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        "qikvrt_ruleset_reconcile.yml",
        token,
    )
    reconciler_workflow_id = _positive_int(
        reconciler_workflow.get("id"), "rerun target workflow id"
    )
    if reconciler_workflow.get("path") != RULESET_RECONCILER_PATH:
        raise RulesetBlock("ruleset rerun target workflow path mismatch")
    observed_target = {
        "id": target_attempt_one.get("id"),
        "run_attempt": target_attempt_one.get("run_attempt"),
        "workflow_id": target_attempt_one.get("workflow_id"),
        "path": _workflow_path(target_attempt_one.get("path")),
        "event": target_attempt_one.get("event"),
        "head_branch": target_attempt_one.get("head_branch"),
        "head_sha": target_attempt_one.get("head_sha"),
        "repository": _mapping(
            target_attempt_one.get("repository"), "rerun target repository"
        ).get("full_name"),
        "status": target_attempt_one.get("status"),
    }
    expected_target = {
        "id": target_run_id,
        "run_attempt": 1,
        "workflow_id": reconciler_workflow_id,
        "path": RULESET_RECONCILER_PATH,
        "event": "repository_dispatch",
        "head_branch": "main",
        "head_sha": target_head,
        "repository": repository,
        "status": "completed",
    }
    if observed_target != expected_target or target_attempt_one.get("conclusion") == "success":
        raise RulesetBlock("ruleset rerun target attempt 1 is not exact adverse evidence")
    locator = parse_ruleset_reconciler_locator(target_attempt_one.get("display_title"))
    review = _mapping(plan.get("review_resume"), "rerun review binding")
    gate = _mapping(review.get("gate"), "rerun review gate")
    subject = _mapping(review.get("subject"), "rerun review subject")
    if (
        locator["gate_run_id"] != gate.get("run_id")
        or locator["gate_run_attempt"] != gate.get("run_attempt")
        or locator["pull_request"] != subject.get("pull_request")
        or locator["head_sha"] != subject.get("head_sha")
        or locator["review_fingerprint"] != review.get("fingerprint")
    ):
        raise RulesetBlock("ruleset rerun locator and review binding differ")
    source_binding = reobserve_ruleset_dispatch_artifact(
        token,
        repository=repository,
        run_id=locator["source_run_id"],
        run_attempt=locator["source_run_attempt"],
    )
    if source_binding.get("artifact") != plan.get("source_artifact"):
        raise RulesetBlock("ruleset rerun source artifact differs from plan")
    source_workflow = github_get(
        f"https://api.github.com/repos/{repository}/actions/workflows/"
        "qikvrt_autonomous_pr_head_continuation.yml",
        token,
    )
    source_workflow_id = _positive_int(
        source_workflow.get("id"), "rerun source workflow id"
    )
    if source_workflow.get("path") != CONTINUATION_PATH:
        raise RulesetBlock("ruleset rerun source workflow path mismatch")
    attempt_run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{source_run_id}"
        f"/attempts/{source_attempt}",
        token,
    )
    classify_review_resume_source_run(
        attempt_run,
        repository=repository,
        head_sha=target_head,
        run_attempt=source_attempt,
        workflow_id=source_workflow_id,
        allowed_events=(
            frozenset({"schedule"})
            if recovery_target is not None
            else frozenset({"workflow_run"})
        ),
    )
    jobs = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{source_run_id}"
        "/jobs?filter=all&per_page=100",
        token,
    )
    source_job = classify_review_resume_source_jobs(
        jobs,
        run_attempt=source_attempt,
        intent_step_name=RULESET_RECONCILER_RERUN_INTENT_STEP_NAME,
        transport_step_name=RULESET_RECONCILER_RERUN_TRANSPORT_STEP_NAME,
        allowed_job_names=(
            frozenset({RULESET_TRANSPORT_RECOVERY_JOB_NAME})
            if recovery_target is not None
            else frozenset({RULESET_REVIEW_RESUME_JOB_NAME})
        ),
    )
    if target_current_attempt == 1:
        current_plan = plan_ruleset_review_resume(
            token,
            repository=repository,
            trigger_run_id=target_run_id,
            trigger_run_attempt=1,
            trigger_workflow_id=_positive_int(
                target_run.get("workflow_id"), "rerun target workflow id"
            ),
            trigger_main_head=target_head,
            trigger_display_title=str(target_run.get("display_title")),
        )
        if reconciler_rerun_transport_projection(
            current_plan
        ) != reconciler_rerun_transport_projection(plan):
            raise RulesetBlock("ruleset rerun live plan differs from durable intent")
    return {
        "artifact": artifact,
        "source_run_id": source_run_id,
        "source_run_attempt": source_attempt,
        "source_created_at": attempt_run.get("created_at"),
        "source_job": source_job,
        "target_run_id": target_run_id,
        "target_bound_attempt": 1,
        "target_current_attempt": target_current_attempt,
        "target_status": target_run.get("status"),
        "target_conclusion": target_run.get("conclusion"),
        "target_workflow_id": _positive_int(
            target_run.get("workflow_id"), "rerun target workflow id"
        ),
        "target_display_title": target_run.get("display_title"),
        "target_main_head": target_head,
        "plan": dict(plan),
        "rerun_request": dict(request),
    }


def _unique_recovery_review_intent_for_target(
    token: str,
    *,
    repository: str,
    reconciler_run_id: int,
    reconciler_run_attempt: int,
) -> dict[str, Any] | None:
    target_run = _positive_int(reconciler_run_id, "review recovery target run")
    target_attempt = _positive_int(
        reconciler_run_attempt, "review recovery target attempt"
    )
    pattern = re.compile(
        r"qikvrt-ruleset-review-resume-intent-[1-9][0-9]*-[1-9][0-9]*-"
        rf"reconciler-{target_run}-{target_attempt}"
    )
    matches, complete = _bounded_repository_artifacts(
        token, repository=repository, name_pattern=pattern
    )
    live = [item for item in matches if item.get("expired") is False]
    if not complete:
        raise RulesetBlock("review recovery intent scan is incomplete")
    if len(live) > 1:
        raise RulesetBlock("review recovery intent is not unique")
    return live[0] if live else None


def _unique_recovery_rerun_intent_for_target(
    token: str, *, repository: str, reconciler_run_id: int
) -> dict[str, Any] | None:
    target_run = _positive_int(reconciler_run_id, "rerun recovery target run")
    pattern = re.compile(
        r"qikvrt-ruleset-reconciler-rerun-intent-[1-9][0-9]*-[1-9][0-9]*-"
        rf"target-{target_run}"
    )
    matches, complete = _bounded_repository_artifacts(
        token, repository=repository, name_pattern=pattern
    )
    live = [item for item in matches if item.get("expired") is False]
    if not complete:
        raise RulesetBlock("rerun recovery intent scan is incomplete")
    if len(live) > 1:
        raise RulesetBlock("rerun recovery intent is not unique")
    return live[0] if live else None


def _requested_review_dispatch_request(plan: Mapping[str, Any]) -> dict[str, Any]:
    requested_review_executor_title(plan)
    return {
        "ref": "main",
        "return_run_details": True,
        "inputs": {
            "pr": str(plan["pull_request"]),
            "head": plan["head_sha"],
            "fingerprint": plan["evidence_fingerprint"],
            "evaluator_sha": plan["evaluator_sha"],
        },
    }


def _reconciler_rerun_request(
    plan: Mapping[str, Any], *, repository: str
) -> dict[str, Any]:
    reconciler_rerun_transport_projection(plan)
    run_id = _positive_int(plan.get("reconciler_run_id"), "rerun target run id")
    return {
        "schema": "qikvrt_ruleset_reconciler_rerun_request_v1",
        "repository": repository,
        "reconciler_run_id": run_id,
        "reconciler_run_attempt": 1,
        "method": "POST",
        "endpoint": f"repos/{repository}/actions/runs/{run_id}/rerun",
        "target_attempt": 2,
        "productive_effect": False,
    }


def _plan_completed_reconciler_for_scheduled_recovery(
    token: str,
    *,
    repository: str,
    main_head_sha: str,
    workflow_id: int,
    title: str,
    successor: Mapping[str, Any],
    source_artifact: Mapping[str, Any],
    allow_new_outbox_effect: bool,
) -> dict[str, Any] | None:
    match = _mapping(successor.get("match"), "completed reconciler successor")
    plan = plan_ruleset_review_resume(
        token,
        repository=repository,
        trigger_run_id=_positive_int(match.get("id"), "reconciler successor run id"),
        trigger_run_attempt=_positive_int(
            match.get("run_attempt"), "reconciler successor attempt"
        ),
        trigger_workflow_id=_positive_int(workflow_id, "reconciler workflow id"),
        trigger_main_head=main_head_sha,
        trigger_display_title=title,
    )
    if plan.get("action") == "DISPATCH_REQUESTED_REVIEW_EXECUTOR":
        existing = _unique_recovery_review_intent_for_target(
            token,
            repository=repository,
            reconciler_run_id=plan["reconciler_run_id"],
            reconciler_run_attempt=plan["reconciler_run_attempt"],
        )
        if existing is not None and not allow_new_outbox_effect:
            return None
        return {
            "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
            "state": "REOBSERVE",
            "d0": 2,
            "action": "DISPATCH_REQUESTED_REVIEW_EXECUTOR",
            "target_workflow_id": plan["target_workflow_id"],
            "reconciler_run_id": plan["reconciler_run_id"],
            "reconciler_run_attempt": plan["reconciler_run_attempt"],
            "review_intent_suffix": (
                f"reconciler-{plan['reconciler_run_id']}-"
                f"{plan['reconciler_run_attempt']}"
            ),
            "dispatch_request": _requested_review_dispatch_request(plan),
            "resume_plan": plan,
            "source_artifact": dict(source_artifact),
            "productive_effect": False,
        }
    if plan.get("action") == "RERUN_RECONCILER_ONCE":
        existing = _unique_recovery_rerun_intent_for_target(
            token,
            repository=repository,
            reconciler_run_id=plan["reconciler_run_id"],
        )
        if existing is not None and not allow_new_outbox_effect:
            return None
        return {
            "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
            "state": "REOBSERVE",
            "d0": 2,
            "action": "RERUN_RECONCILER_ONCE",
            "reconciler_run_id": plan["reconciler_run_id"],
            "reconciler_run_attempt": plan["reconciler_run_attempt"],
            "rerun_intent_suffix": f"target-{plan['reconciler_run_id']}",
            "rerun_request": _reconciler_rerun_request(plan, repository=repository),
            "resume_plan": plan,
            "source_artifact": dict(source_artifact),
            "productive_effect": False,
        }
    if plan.get("action") == "NONE" and plan.get("d0") == 3:
        return {
            "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
            "state": "REQUEST_AUTHORITY",
            "d0": 3,
            "action": "NONE",
            "first_blocker": plan.get("first_blocker"),
            "reconciler_run_id": plan.get("reconciler_run_id"),
            "reconciler_run_attempt": plan.get("reconciler_run_attempt"),
            "resume_plan": plan,
            "source_artifact": dict(source_artifact),
            "productive_effect": False,
        }
    raise RulesetBlock("completed reconciler produced an invalid continuation plan")


def select_ruleset_reconcile_transport_recovery(
    token: str,
    *,
    repository: str,
    main_head_sha: str,
    expected_source_run_id: int | None = None,
    expected_source_run_attempt: int | None = None,
    allow_recovery_attempt_2: bool = False,
) -> dict[str, Any]:
    """Select at most one exact orphaned ruleset repository_dispatch outbox."""
    if repository != "Goldkelch/qik-vrt":
        raise RulesetBlock("ruleset transport recovery repository mismatch")
    main_head = _sha(main_head_sha, "ruleset recovery main head")
    outbox_item, candidate = _current_ruleset_outbox_intent(
        token,
        repository=repository,
        lane="ruleset-dispatch",
        main_head_sha=main_head,
    )
    candidates = [] if candidate is None else [candidate]
    scan_complete = True
    for candidate in candidates:
        if candidate.get("expired") is not False:
            continue
        match = re.fullmatch(
            r"qikvrt-ruleset-reconcile-intent-([1-9][0-9]*)-([1-9][0-9]*)",
            str(candidate["name"]),
        )
        if match is None:
            continue
        source_run_id = int(match.group(1))
        source_attempt = int(match.group(2))
        if expected_source_run_id is not None and (
            source_run_id != expected_source_run_id
            or source_attempt != expected_source_run_attempt
        ):
            continue
        recovery_name = (
            "qikvrt-ruleset-reconcile-transport-recovery-"
            f"{source_run_id}-{source_attempt}-attempt-2"
        )
        authority_name = (
            "qikvrt-ruleset-reconcile-transport-authority-"
            f"{source_run_id}-{source_attempt}"
        )
        try:
            if _exact_repository_artifact_exists(
                token, repository=repository, name=authority_name
            ):
                continue
            if candidate["producer_run_id"] != source_run_id:
                raise RulesetBlock("ruleset intent name and producer differ")
            source_binding = reobserve_ruleset_dispatch_artifact(
                token,
                repository=repository,
                run_id=source_run_id,
                run_attempt=source_attempt,
            )
            source = _mapping(source_binding.get("source"), "ruleset source")
            binding = _mapping(source_binding.get("binding"), "ruleset binding")
            if outbox_item is None:
                raise RulesetBlock("ruleset outbox item disappeared")
            outbox_intent = _mapping(
                outbox_item.get("intent"), "ruleset outbox intent"
            )
            sealed_request = _mapping(
                _mapping(outbox_intent.get("payload"), "ruleset outbox payload").get(
                    "request"
                ),
                "ruleset outbox request",
            )
            if source_binding.get("request") != sealed_request:
                raise RulesetBlock("ruleset artifact and ledger request differ")
            if binding.get("main_head_sha") != main_head:
                raise RulesetBlock("ruleset recovery source main has drifted")
            source_workflow = github_get(
                f"https://api.github.com/repos/{repository}/actions/workflows/"
                "qikvrt_autonomous_pr_head_continuation.yml",
                token,
            )
            if (
                source_workflow.get("id") != source.get("workflow_id")
                or source_workflow.get("path") != CONTINUATION_PATH
            ):
                raise RulesetBlock("ruleset recovery source workflow mismatch")
            source_proof = reobserve_dispatch_source_attempt_for_recovery(
                token,
                repository=repository,
                head_sha=main_head,
                run_id=source_run_id,
                run_attempt=source_attempt,
                workflow_id=_positive_int(
                    source.get("workflow_id"), "ruleset source workflow id"
                ),
            )
            review = reobserve_review_resume_binding(
                token,
                repository=repository,
                main_head_sha=main_head,
                binding=_mapping(source_binding.get("review"), "ruleset review"),
            )
            not_before = source_proof.get("created_at")
            _timestamp(not_before, "ruleset source creation time")
            transports = _mapping(
                outbox_item.get("transport"), "ruleset outbox transports"
            )
            recovery_artifact = (
                {"created_at": not_before}
                if "2" in transports
                else None
            )
            scan_not_before = (
                recovery_artifact.get("created_at")
                if recovery_artifact is not None
                else not_before
            )
            _timestamp(scan_not_before, "ruleset transport ordinal creation time")
            reconciler_workflow = github_get(
                f"https://api.github.com/repos/{repository}/actions/workflows/"
                "qikvrt_ruleset_reconcile.yml",
                token,
            )
            reconciler_workflow_id = _positive_int(
                reconciler_workflow.get("id"), "ruleset reconciler workflow id"
            )
            if reconciler_workflow.get("path") != RULESET_RECONCILER_PATH:
                raise RulesetBlock("ruleset recovery reconciler path mismatch")
            runs, runs_complete = _bounded_workflow_runs_since(
                token,
                repository=repository,
                workflow="qikvrt_ruleset_reconcile.yml",
                event="repository_dispatch",
                not_before=str(scan_not_before),
            )
            transport_attempts = sorted(int(key) for key in transports)
            locator_attempt = transport_attempts[-1] if transport_attempts else 1
            locator_title = ruleset_reconciler_title(
                intent_sha256=outbox_item["fingerprint"],
                sequence=outbox_item["sequence"],
                transport_attempt=locator_attempt,
            )
            successor = classify_bound_successor_scan(
                runs,
                scan_complete=runs_complete,
                title=locator_title,
                workflow_id=reconciler_workflow_id,
                workflow_path=RULESET_RECONCILER_PATH,
                event="repository_dispatch",
                repository=repository,
                main_head_sha=main_head,
                not_before=str(scan_not_before),
            )
            if successor["state"] == "TRANSPORT_PENDING":
                continue
            if successor["state"] == "TRANSPORT_COMPLETED":
                terminal = _plan_completed_reconciler_for_scheduled_recovery(
                    token,
                    repository=repository,
                    main_head_sha=main_head,
                    workflow_id=reconciler_workflow_id,
                    title=locator_title,
                    successor=successor,
                    source_artifact=candidate,
                    allow_new_outbox_effect=allow_recovery_attempt_2,
                )
                if terminal is None:
                    continue
                return {
                    **terminal,
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "main_head_sha": main_head,
                    "authority_artifact_name": authority_name,
                    "outbox": {
                        "lane": "ruleset-dispatch",
                        "sequence": outbox_item["sequence"],
                        "fingerprint": outbox_item["fingerprint"],
                        "transport_attempts": sorted(int(key) for key in transports),
                    },
                }
            if successor["state"] in {
                "AMBIGUOUS_ACCEPTED_RUNS",
                "SCAN_INCOMPLETE",
            }:
                return {
                    "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
                    "state": "REQUEST_AUTHORITY",
                    "d0": 3,
                    "action": "NONE",
                    "first_blocker": f"RULESET_RECONCILER_{successor['state']}",
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "source_artifact": candidate,
                    "successor": successor,
                    "authority_artifact_name": authority_name,
                    "productive_effect": False,
                    "outbox": {
                        "lane": "ruleset-dispatch",
                        "sequence": outbox_item["sequence"],
                        "fingerprint": outbox_item["fingerprint"],
                        "transport_attempts": sorted(int(key) for key in transports),
                    },
                }
            if transport_attempts == [1, 2]:
                return {
                    "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
                    "state": "REQUEST_AUTHORITY",
                    "d0": 3,
                    "action": "NONE",
                    "first_blocker": "RULESET_RECONCILE_ATTEMPT_2_ORPHAN",
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "source_artifact": candidate,
                    "review_resume": review,
                    "authority_artifact_name": authority_name,
                    "productive_effect": False,
                    "outbox": {
                        "lane": "ruleset-dispatch",
                        "sequence": outbox_item["sequence"],
                        "fingerprint": outbox_item["fingerprint"],
                        "transport_attempts": transport_attempts,
                    },
                }
            if transport_attempts not in ([], [1]):
                raise RulesetBlock("ruleset outbox transport ordinal is invalid")
            transport_attempt = 1 if not transport_attempts else 2
            retry_evidence = (
                None
                if transport_attempt == 1
                else {
                    "schema": "qikvrt_ruleset_outbox_retry_evidence_v1",
                    "lane": "ruleset-dispatch",
                    "sequence": outbox_item["sequence"],
                    "fingerprint": outbox_item["fingerprint"],
                    "attempt": 1,
                    "classification": "ORPHAN_NO_BOUND_SUCCESSOR",
                    "first_blocker": "NO_BOUND_RULESET_RECONCILER_AFTER_ATTEMPT_1",
                    "successor": None,
                    "d0": 2,
                    "verified": True,
                    "productive_effect": False,
                }
            )
            return {
                "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
                "state": "REOBSERVE",
                "d0": 2,
                "action": "REPLAY_REPOSITORY_DISPATCH_ONCE",
                "source_run_id": source_run_id,
                "source_run_attempt": source_attempt,
                "source_workflow_id": source.get("workflow_id"),
                "main_head_sha": main_head,
                "recovery_artifact_name": recovery_name,
                "dispatch_request": source_binding["request"],
                "transport_attempt": transport_attempt,
                "retry_evidence": retry_evidence,
                "source_artifact": candidate,
                "review_resume": review,
                "productive_effect": False,
                "outbox": {
                    "lane": "ruleset-dispatch",
                    "sequence": outbox_item["sequence"],
                    "fingerprint": outbox_item["fingerprint"],
                    "transport_attempts": sorted(int(key) for key in transports),
                },
            }
        except (OSError, ValueError, RulesetBlock) as exc:
            return {
                "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
                "state": "REQUEST_AUTHORITY",
                "d0": 3,
                "action": "NONE",
                "first_blocker": str(exc),
                "source_run_id": source_run_id,
                "source_run_attempt": source_attempt,
                "source_artifact": candidate,
                "authority_artifact_name": authority_name,
                "productive_effect": False,
            }
    if expected_source_run_id is not None:
        raise RulesetBlock("exact ruleset recovery source intent is unavailable")
    return {
        "schema": "qikvrt_ruleset_transport_recovery_plan_v1",
        "state": "HOLD" if scan_complete else "REQUEST_AUTHORITY",
        "d0": 1 if scan_complete else 3,
        "action": "NONE",
        "first_blocker": (
            "NO_ORPHAN_RULESET_RECONCILE_TRANSPORT"
            if scan_complete
            else "RULESET_RECONCILE_INTENT_SCAN_INCOMPLETE"
        ),
        "productive_effect": False,
    }


def select_ruleset_review_resume_transport_recovery(
    token: str,
    *,
    repository: str,
    main_head_sha: str,
    expected_source_run_id: int | None = None,
    expected_source_run_attempt: int | None = None,
    allow_recovery_attempt_2: bool = False,
) -> dict[str, Any]:
    """Select at most one exact orphaned requested-review successor outbox."""
    if repository != "Goldkelch/qik-vrt":
        raise RulesetBlock("review-resume recovery repository mismatch")
    main_head = _sha(main_head_sha, "review-resume recovery main head")
    candidates, scan_complete = _bounded_repository_artifacts(
        token,
        repository=repository,
        name_pattern=RULESET_REVIEW_INTENT_PATTERN,
    )
    for candidate in candidates:
        if candidate.get("expired") is not False:
            continue
        match = RULESET_REVIEW_INTENT_PATTERN.fullmatch(str(candidate["name"]))
        if match is None:
            continue
        # Groups 3/4 are an optional exact reconciler target.  Legacy intent
        # names intentionally leave both unset, so parse the producer tuple
        # independently and let the artifact reobserver bind any target tuple
        # to the sealed plan.
        source_run_id = int(match.group(1))
        source_attempt = int(match.group(2))
        if (match.group(3) is None) != (match.group(4) is None):
            raise RulesetBlock("review-resume recovery target tuple is incomplete")
        if expected_source_run_id is not None and (
            source_run_id != expected_source_run_id
            or source_attempt != expected_source_run_attempt
        ):
            continue
        recovery_name = (
            "qikvrt-ruleset-review-resume-transport-recovery-"
            f"{source_run_id}-{source_attempt}-attempt-2"
        )
        authority_name = (
            "qikvrt-ruleset-review-resume-transport-authority-"
            f"{source_run_id}-{source_attempt}"
        )
        try:
            if _exact_repository_artifact_exists(
                token, repository=repository, name=authority_name
            ):
                continue
            if candidate["producer_run_id"] != source_run_id:
                raise RulesetBlock("review-resume intent name and producer differ")
            intent = reobserve_ruleset_review_resume_intent(
                token,
                repository=repository,
                run_id=source_run_id,
                run_attempt=source_attempt,
                artifact_name=str(candidate["name"]),
            )
            if intent.get("main_head_sha") != main_head:
                raise RulesetBlock("review-resume recovery main has drifted")
            plan = _mapping(intent.get("plan"), "review-resume recovery plan")
            workflow_id = _positive_int(
                plan.get("target_workflow_id"), "requested-review workflow id"
            )
            workflow = github_get(
                f"https://api.github.com/repos/{repository}/actions/workflows/"
                "qikvrt_requested_review_executor.yml",
                token,
            )
            if (
                workflow.get("id") != workflow_id
                or workflow.get("path") != REQUESTED_REVIEW_EXECUTOR_PATH
            ):
                raise RulesetBlock("requested-review successor workflow mismatch")
            not_before = intent.get("source_created_at")
            _timestamp(not_before, "review-resume source creation time")
            recovery_artifact = _exact_repository_artifact(
                token, repository=repository, name=recovery_name
            )
            scan_not_before = (
                recovery_artifact.get("created_at")
                if recovery_artifact is not None
                else not_before
            )
            _timestamp(scan_not_before, "requested-review transport ordinal time")
            runs, runs_complete = _bounded_workflow_runs_since(
                token,
                repository=repository,
                workflow="qikvrt_requested_review_executor.yml",
                event="workflow_dispatch",
                not_before=str(scan_not_before),
            )
            successor = classify_bound_successor_scan(
                runs,
                scan_complete=runs_complete,
                title=requested_review_executor_title(plan),
                workflow_id=workflow_id,
                workflow_path=REQUESTED_REVIEW_EXECUTOR_PATH,
                event="workflow_dispatch",
                repository=repository,
                main_head_sha=main_head,
                not_before=str(scan_not_before),
            )
            if successor["state"] == "TRANSPORT_PENDING":
                continue
            terminal_blocker: str | None = None
            if successor["state"] == "TRANSPORT_COMPLETED":
                successor_match = _mapping(
                    successor.get("match"), "requested-review completed successor"
                )
                try:
                    validate_completed_requested_review_successor(
                        token,
                        repository=repository,
                        main_head_sha=main_head,
                        workflow_id=workflow_id,
                        run_id=_positive_int(
                            successor_match.get("id"),
                            "requested-review completed run id",
                        ),
                        run_attempt=_positive_int(
                            successor_match.get("run_attempt"),
                            "requested-review completed run attempt",
                        ),
                        plan=plan,
                    )
                except (OSError, ValueError, RulesetBlock) as exc:
                    terminal_blocker = str(exc)
                else:
                    continue
            if successor["state"] in {
                "AMBIGUOUS_ACCEPTED_RUNS",
                "SCAN_INCOMPLETE",
            }:
                return {
                    "schema": "qikvrt_ruleset_review_transport_recovery_plan_v1",
                    "state": "REQUEST_AUTHORITY",
                    "d0": 3,
                    "action": "NONE",
                    "first_blocker": f"REQUESTED_REVIEW_{successor['state']}",
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "source_artifact": candidate,
                    "successor": successor,
                    "authority_artifact_name": authority_name,
                    "productive_effect": False,
                }
            recovery_exists = recovery_artifact is not None
            source_job = _mapping(intent.get("source_job"), "review source job")
            if terminal_blocker is not None and (
                recovery_exists
                or _mapping(successor.get("match"), "adverse requested-review run").get(
                    "run_attempt"
                )
                != 1
            ):
                return {
                    "schema": "qikvrt_ruleset_review_transport_recovery_plan_v1",
                    "state": "REQUEST_AUTHORITY",
                    "d0": 3,
                    "action": "NONE",
                    "first_blocker": (
                        "REQUESTED_REVIEW_ATTEMPT_2_TERMINAL_ADVERSE: "
                        f"{terminal_blocker}"
                    ),
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "source_artifact": candidate,
                    "successor": successor,
                    "authority_artifact_name": authority_name,
                    "productive_effect": False,
                }
            if (
                recovery_exists and not allow_recovery_attempt_2
            ) or (
                terminal_blocker is None
                and source_job.get("transport_step_conclusion") == "success"
            ):
                blocker = (
                    "REQUESTED_REVIEW_RECOVERY_ATTEMPT_2_ORPHAN"
                    if recovery_exists
                    else "REQUESTED_REVIEW_TRANSPORT_ACK_WITHOUT_BOUND_RUN"
                )
                return {
                    "schema": "qikvrt_ruleset_review_transport_recovery_plan_v1",
                    "state": "REQUEST_AUTHORITY",
                    "d0": 3,
                    "action": "NONE",
                    "first_blocker": blocker,
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "source_artifact": candidate,
                    "authority_artifact_name": authority_name,
                    "productive_effect": False,
                }
            return {
                "schema": "qikvrt_ruleset_review_transport_recovery_plan_v1",
                "state": "REOBSERVE",
                "d0": 2,
                "action": "REPLAY_REQUESTED_REVIEW_ONCE",
                "source_run_id": source_run_id,
                "source_run_attempt": source_attempt,
                "main_head_sha": main_head,
                "target_workflow_id": workflow_id,
                "recovery_artifact_name": recovery_name,
                "dispatch_request": intent["dispatch_request"],
                "resume_plan": dict(plan),
                "source_artifact": candidate,
                "adverse_successor": successor if terminal_blocker is not None else None,
                "first_blocker": terminal_blocker,
                "productive_effect": False,
            }
        except (OSError, ValueError, RulesetBlock) as exc:
            return {
                "schema": "qikvrt_ruleset_review_transport_recovery_plan_v1",
                "state": "REQUEST_AUTHORITY",
                "d0": 3,
                "action": "NONE",
                "first_blocker": str(exc),
                "source_run_id": source_run_id,
                "source_run_attempt": source_attempt,
                "source_artifact": candidate,
                "authority_artifact_name": authority_name,
                "productive_effect": False,
            }
    if expected_source_run_id is not None:
        raise RulesetBlock("exact review-resume recovery source intent is unavailable")
    return {
        "schema": "qikvrt_ruleset_review_transport_recovery_plan_v1",
        "state": "HOLD" if scan_complete else "REQUEST_AUTHORITY",
        "d0": 1 if scan_complete else 3,
        "action": "NONE",
        "first_blocker": (
            "NO_ORPHAN_RULESET_REVIEW_RESUME_TRANSPORT"
            if scan_complete
            else "RULESET_REVIEW_RESUME_INTENT_SCAN_INCOMPLETE"
        ),
        "productive_effect": False,
    }


def select_ruleset_reconciler_rerun_transport_recovery(
    token: str,
    *,
    repository: str,
    main_head_sha: str,
    expected_source_run_id: int | None = None,
    expected_source_run_attempt: int | None = None,
    allow_recovery_attempt_2: bool = False,
) -> dict[str, Any]:
    """Select at most one durable orphaned reconciler-rerun request."""
    if repository != "Goldkelch/qik-vrt":
        raise RulesetBlock("reconciler-rerun recovery repository mismatch")
    main_head = _sha(main_head_sha, "reconciler-rerun recovery main head")
    candidates, scan_complete = _bounded_repository_artifacts(
        token,
        repository=repository,
        name_pattern=RULESET_RERUN_INTENT_PATTERN,
    )
    for candidate in candidates:
        if candidate.get("expired") is not False:
            continue
        match = RULESET_RERUN_INTENT_PATTERN.fullmatch(str(candidate["name"]))
        if match is None:
            continue
        source_run_id, source_attempt = (int(value) for value in match.groups())
        if expected_source_run_id is not None and (
            source_run_id != expected_source_run_id
            or source_attempt != expected_source_run_attempt
        ):
            continue
        recovery_name = (
            "qikvrt-ruleset-reconciler-rerun-transport-recovery-"
            f"{source_run_id}-{source_attempt}-attempt-2"
        )
        authority_name = (
            "qikvrt-ruleset-reconciler-rerun-transport-authority-"
            f"{source_run_id}-{source_attempt}"
        )
        try:
            if _exact_repository_artifact_exists(
                token, repository=repository, name=authority_name
            ):
                continue
            if candidate["producer_run_id"] != source_run_id:
                raise RulesetBlock("rerun intent name and producer differ")
            intent = reobserve_ruleset_reconciler_rerun_intent(
                token,
                repository=repository,
                run_id=source_run_id,
                run_attempt=source_attempt,
                artifact_name=str(candidate["name"]),
            )
            if intent.get("target_main_head") != main_head:
                raise RulesetBlock("reconciler-rerun recovery main has drifted")
            target_attempt = intent.get("target_current_attempt")
            if target_attempt == 2:
                target_status = intent.get("target_status")
                if target_status in ACTIVE_RUN_STATUSES:
                    continue
                if target_status != "completed":
                    raise RulesetBlock("reconciler attempt 2 has unknown status")
                successor = {
                    "state": "TRANSPORT_COMPLETED",
                    "match": {
                        "id": intent["target_run_id"],
                        "run_attempt": 2,
                        "status": "completed",
                        "conclusion": intent.get("target_conclusion"),
                    },
                }
                terminal = _plan_completed_reconciler_for_scheduled_recovery(
                    token,
                    repository=repository,
                    main_head_sha=main_head,
                    workflow_id=_positive_int(
                        intent.get("target_workflow_id"),
                        "reconciler attempt-2 workflow id",
                    ),
                    title=str(intent.get("target_display_title")),
                    successor=successor,
                    source_artifact=candidate,
                    allow_new_outbox_effect=allow_recovery_attempt_2,
                )
                if terminal is None:
                    continue
                return {
                    **terminal,
                    "schema": "qikvrt_ruleset_rerun_transport_recovery_plan_v1",
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "target_run_id": intent["target_run_id"],
                    "main_head_sha": main_head,
                    "authority_artifact_name": authority_name,
                }
            if target_attempt != 1:
                raise RulesetBlock("reconciler-rerun target attempt is not bounded")
            recovery_exists = _exact_repository_artifact_exists(
                token, repository=repository, name=recovery_name
            )
            source_job = _mapping(intent.get("source_job"), "rerun source job")
            if (
                recovery_exists and not allow_recovery_attempt_2
            ) or source_job.get("transport_step_conclusion") == "success":
                blocker = (
                    "RULESET_RERUN_RECOVERY_ATTEMPT_2_ORPHAN"
                    if recovery_exists
                    else "RULESET_RERUN_TRANSPORT_ACK_WITHOUT_ATTEMPT_ADVANCE"
                )
                return {
                    "schema": "qikvrt_ruleset_rerun_transport_recovery_plan_v1",
                    "state": "REQUEST_AUTHORITY",
                    "d0": 3,
                    "action": "NONE",
                    "first_blocker": blocker,
                    "source_run_id": source_run_id,
                    "source_run_attempt": source_attempt,
                    "target_run_id": intent["target_run_id"],
                    "source_artifact": candidate,
                    "authority_artifact_name": authority_name,
                    "productive_effect": False,
                }
            return {
                "schema": "qikvrt_ruleset_rerun_transport_recovery_plan_v1",
                "state": "REOBSERVE",
                "d0": 2,
                "action": "REPLAY_RECONCILER_RERUN_ONCE",
                "source_run_id": source_run_id,
                "source_run_attempt": source_attempt,
                "target_run_id": intent["target_run_id"],
                "target_bound_attempt": 1,
                "target_attempt": 2,
                "main_head_sha": main_head,
                "recovery_artifact_name": recovery_name,
                "rerun_request": intent["rerun_request"],
                "resume_plan": intent["plan"],
                "source_artifact": candidate,
                "productive_effect": False,
            }
        except (OSError, ValueError, RulesetBlock) as exc:
            return {
                "schema": "qikvrt_ruleset_rerun_transport_recovery_plan_v1",
                "state": "REQUEST_AUTHORITY",
                "d0": 3,
                "action": "NONE",
                "first_blocker": str(exc),
                "source_run_id": source_run_id,
                "source_run_attempt": source_attempt,
                "source_artifact": candidate,
                "authority_artifact_name": authority_name,
                "productive_effect": False,
            }
    if expected_source_run_id is not None:
        raise RulesetBlock("exact reconciler-rerun recovery intent is unavailable")
    return {
        "schema": "qikvrt_ruleset_rerun_transport_recovery_plan_v1",
        "state": "HOLD" if scan_complete else "REQUEST_AUTHORITY",
        "d0": 1 if scan_complete else 3,
        "action": "NONE",
        "first_blocker": (
            "NO_ORPHAN_RULESET_RECONCILER_RERUN_TRANSPORT"
            if scan_complete
            else "RULESET_RECONCILER_RERUN_INTENT_SCAN_INCOMPLETE"
        ),
        "productive_effect": False,
    }


def reobserve_durable_source_intent_after_effect(
    token: str,
    *,
    repository: str,
    head_sha: str,
    run_id: int,
    run_attempt: int,
    workflow_id: int,
) -> dict[str, Any]:
    """Keep immutable attempt evidence valid after a later source rerun.

    The original attempt's uploaded intent and successful upload step remain the
    authority.  A newer attempt is observed only as chronology and contributes
    no evidence to the already-completed reconciler effect.
    """
    run = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}", token
    )
    run_result = classify_dispatch_source_run(
        run,
        repository=repository,
        head_sha=head_sha,
        run_attempt=run_attempt,
        workflow_id=workflow_id,
        allow_durable_intent=True,
        allow_attempt_advance=True,
    )
    jobs = github_get(
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/jobs?filter=all&per_page=100",
        token,
    )
    job_result = classify_dispatch_source_jobs(
        jobs, run_attempt=run_attempt, require_durable_intent=True
    )
    return {
        "state": SOURCE_RUN_DURABLE_INTENT,
        "run_id": run_id,
        "bound_run_attempt": run_attempt,
        "observed_run_attempt": run.get("run_attempt"),
        "attempt_advance_is_chronology_only": run.get("run_attempt") != run_attempt,
        "run_state": run_result["state"],
        "job_id": job_result["job_id"],
        "intent_step_name": SOURCE_INTENT_STEP_NAME,
    }


def reobserve_dispatch_source_from_environment() -> dict[str, Any]:
    try:
        run_id = int(os.environ.get("REQUEST_SOURCE_RUN_ID", ""))
        run_attempt = int(os.environ.get("REQUEST_SOURCE_RUN_ATTEMPT", ""))
        workflow_id = int(os.environ.get("REQUEST_SOURCE_WORKFLOW_ID", ""))
    except ValueError as exc:
        raise RulesetBlock("ruleset dispatch source numeric binding is invalid") from exc
    result = reobserve_dispatch_source(
        os.environ.get("GH_TOKEN", ""),
        repository=os.environ.get("GITHUB_REPOSITORY", ""),
        head_sha=os.environ.get("REQUEST_MAIN_HEAD", ""),
        run_id=run_id,
        run_attempt=run_attempt,
        workflow_id=workflow_id,
    )
    try:
        expected_payload = json.loads(os.environ.get("REQUEST_PAYLOAD_JSON", ""))
    except json.JSONDecodeError as exc:
        raise RulesetBlock("repository dispatch payload is invalid") from exc
    source_artifact = reobserve_ruleset_dispatch_artifact(
        os.environ.get("GH_TOKEN", ""),
        repository=os.environ.get("GITHUB_REPOSITORY", ""),
        run_id=run_id,
        run_attempt=run_attempt,
        expected_payload=_mapping(expected_payload, "repository dispatch payload"),
    )
    review = reobserve_review_resume_binding_from_environment()
    return {
        **result,
        "dispatch_artifact": source_artifact["artifact"],
        "review_resume": review,
    }


def _complete_github_named_collection(
    token: str, *, url: str, key: str, label: str
) -> list[dict[str, Any]]:
    """Read one stable complete bounded GitHub inventory or fail closed.

    Offset pagination cannot prove secret-name absence while concurrent
    insert/delete operations shift page boundaries.  The protected manual
    effect therefore admits only an inventory that fits one 100-item page and
    is returned identically by two immediate reads.
    """

    def one_read() -> list[dict[str, Any]]:
        separator = "&" if "?" in url else "?"
        response = github_get(f"{url}{separator}per_page=100&page=1", token)
        total = response.get("total_count")
        items = response.get(key)
        if (
            isinstance(total, bool)
            or not isinstance(total, int)
            or not (0 <= total <= 100)
            or not isinstance(items, list)
            or len(items) != total
        ):
            raise RulesetBlock(
                f"{label} inventory is not one complete bounded page"
            )
        values: list[dict[str, Any]] = []
        for raw in items:
            item = dict(_mapping(raw, f"{label} inventory item"))
            if not isinstance(item.get("name"), str) or not item["name"]:
                raise RulesetBlock(f"{label} inventory item name is invalid")
            values.append(item)
        names = [item["name"] for item in values]
        ids = [item.get("id") for item in values if "id" in item]
        if len(set(names)) != len(names) or (
            ids
            and (
                len(ids) != len(values)
                or any(
                    isinstance(identifier, bool)
                    or not isinstance(identifier, int)
                    or identifier < 1
                    for identifier in ids
                )
                or len(set(ids)) != len(ids)
            )
        ):
            raise RulesetBlock(f"{label} inventory is incomplete or ambiguous")
        return values

    first = one_read()
    values = one_read()
    if digest(first) != digest(values):
        raise RulesetBlock(f"{label} inventory changed during readback")
    return values


def reobserve_ruleset_authority_environment(
    token: str, policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Prove the admin credential resolved from the protected environment.

    GitHub's secret expression can fall back to repository or organization
    scope when an environment secret is absent.  The fixed admin process must
    therefore inventory every applicable scope before any ruleset mutation.
    A User-owned repository has no organization fallback scope; an
    Organization-owned repository requires the complete organization
    inventory.  Unknown owner identity or missing endpoint authority is an
    explicit HOLD, never permission to continue.
    """
    repository = policy.get("repository")
    authority = _mapping(policy.get("authority"), "ruleset authority")
    if repository != "Goldkelch/qik-vrt":
        raise RulesetBlock("AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: repository")
    environment_name = authority.get("environment")
    credential_name = authority.get("credential")
    if (
        environment_name != "qikvrt-ruleset-authority"
        or credential_name != "QIKVRT_ENV_RULESET_ADMIN_TOKEN"
    ):
        raise RulesetBlock("AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: contract")
    encoded_environment = urllib.parse.quote(environment_name, safe="")
    base = f"https://api.github.com/repos/{repository}"
    try:
        repository_document = github_get(base, token)
        repository_owner = _mapping(
            repository_document.get("owner"), "Authority repository owner"
        )
        expected_owner = _mapping(
            _mapping(
                authority.get("required_external_readback"),
                "Authority required external readback",
            ).get("repository_owner"),
            "Authority expected repository owner",
        )
        owner = {
            "login": repository_owner.get("login"),
            "id": repository_owner.get("id"),
            "type": repository_owner.get("type"),
        }
        if (
            owner != expected_owner
            or owner["type"] not in {"User", "Organization"}
            or isinstance(owner["id"], bool)
            or not isinstance(owner["id"], int)
            or owner["id"] < 1
        ):
            raise RulesetBlock("repository owner identity/type is not exact")
        environment = github_get(
            f"{base}/environments/{encoded_environment}", token
        )
        deployment = _mapping(
            environment.get("deployment_branch_policy"),
            "Authority environment deployment policy",
        )
        protection_rules = environment.get("protection_rules")
        if (
            environment.get("name") != environment_name
            or deployment.get("protected_branches") is not False
            or deployment.get("custom_branch_policies") is not True
            or not isinstance(protection_rules, list)
            or not protection_rules
        ):
            raise RulesetBlock("environment is not protected selected-main-only")
        branch_policies = _complete_github_named_collection(
            token,
            url=(
                f"{base}/environments/{encoded_environment}/"
                "deployment-branch-policies"
            ),
            key="branch_policies",
            label="Authority environment branch-policy",
        )
        if len(branch_policies) != 1 or branch_policies[0].get("name") != "main":
            raise RulesetBlock("environment deployment branch is not exactly main")
        policy_type = branch_policies[0].get("type")
        if policy_type not in {None, "branch"}:
            raise RulesetBlock("environment main deployment policy is not a branch")

        environment_secrets = _complete_github_named_collection(
            token,
            url=f"{base}/environments/{encoded_environment}/secrets",
            key="secrets",
            label="Authority environment secret",
        )
        repository_secrets = _complete_github_named_collection(
            token,
            url=f"{base}/actions/secrets",
            key="secrets",
            label="repository Actions secret",
        )
        if owner["type"] == "Organization":
            organization_secrets = _complete_github_named_collection(
                token,
                url=(
                    "https://api.github.com/orgs/"
                    f"{urllib.parse.quote(str(owner['login']), safe='')}/"
                    "actions/secrets"
                ),
                key="secrets",
                label="organization Actions secret",
            )
            organization_scope_readback = "COMPLETE_ORGANIZATION_INVENTORY"
        else:
            organization_secrets = []
            organization_scope_readback = "NOT_APPLICABLE_USER_OWNER"
        environment_names = {item["name"] for item in environment_secrets}
        repository_names = {item["name"] for item in repository_secrets}
        organization_names = {item["name"] for item in organization_secrets}
        forbidden = {
            "QIKVRT_ENV_RULESET_ADMIN_TOKEN",
            "QIKVRT_RULESET_ADMIN_TOKEN",
        }
        if credential_name not in environment_names:
            raise RulesetBlock("environment admin secret name is absent")
        if "QIKVRT_RULESET_ADMIN_TOKEN" in environment_names:
            raise RulesetBlock("legacy environment admin secret name is present")
        if repository_names & forbidden:
            raise RulesetBlock("repository-scope admin secret fallback is present")
        if organization_names & forbidden:
            raise RulesetBlock("organization-scope admin secret fallback is present")
    except (OSError, ValueError, RulesetBlock) as exc:
        detail = str(exc)
        if detail.startswith("AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED"):
            raise
        raise RulesetBlock(
            f"AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: {detail}"
        ) from exc
    return {
        "schema": "qikvrt_ruleset_authority_environment_readback_v1",
        "state": "VERIFIED_FOR_THIS_EFFECT_ONLY",
        "repository": repository,
        "repository_owner": owner,
        "environment": environment_name,
        "credential_name": credential_name,
        "deployment_branch": "main",
        "environment_protection_rule_count": len(protection_rules),
        "environment_secret_name_present": True,
        "repository_scope_fallback_names_absent": True,
        "organization_scope_fallback_names_absent": True,
        "organization_scope_readback": organization_scope_readback,
        "secret_values_observed": False,
    }


def reconcile(
    token: str,
    policy: Mapping[str, Any],
    *,
    pre_effect_check: Callable[[], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    repository = policy["repository"]
    ruleset_id = policy["ruleset_id"]
    url = f"https://api.github.com/repos/{repository}/rulesets/{ruleset_id}"
    initial = _request("GET", url, token)
    plan = evaluate(initial, policy)
    if plan["state"] == INCOMPLETE_VISIBILITY:
        raise RulesetBlock(
            "admin ruleset observation omitted bypass_actors; refusing CURRENT or PUT"
        )
    if plan["state"] == "CURRENT":
        return plan

    reobserved = _request("GET", url, token)
    reobserved_plan = evaluate(reobserved, policy)
    if (
        reobserved_plan["state"] != "DRIFT"
        or reobserved_plan["pre_state_sha256"] != plan["pre_state_sha256"]
    ):
        raise RulesetBlock("ruleset drifted after planning; refusing mutation")
    planned_payload = desired_payload(policy)
    authority_environment = reobserve_ruleset_authority_environment(token, policy)
    if pre_effect_check is not None:
        pre_effect_check()

    # GitHub does not document conditional/CAS semantics for this unsafe endpoint.
    # Reobserve after every potentially long authority/source inventory, then
    # issue the PUT as the immediately following network effect.  This narrows
    # but cannot eliminate the final GET-to-PUT race; post-readback drives
    # honest last-writer convergence.
    immediate = _request("GET", url, token)
    immediate_plan = evaluate(immediate, policy)
    if immediate_plan["state"] == INCOMPLETE_VISIBILITY:
        raise RulesetBlock(
            "immediate pre-effect observation omitted bypass_actors; "
            "refusing mutation"
        )
    if immediate_plan["state"] == "CURRENT":
        return {
            **immediate_plan,
            "planned_pre_state_sha256": plan["pre_state_sha256"],
            "mutation": "NONE",
            "pre_effect_double_read": True,
            "immediate_pre_effect_reobservation": True,
            "pre_effect_source_reobservation": pre_effect_check is not None,
            "authority_environment_readback": authority_environment,
            "write_concurrency": "LAST_WRITER_WINS",
            "conditional_update_used": False,
            "get_put_race_eliminated": False,
            "converged_before_mutation": True,
            "post_update_readback": False,
            "effect_observed": False,
        }
    if (
        immediate_plan["state"] != "DRIFT"
        or immediate_plan["pre_state_sha256"] != plan["pre_state_sha256"]
    ):
        raise RulesetBlock(
            "ruleset drifted during authority/source readback; refusing mutation"
        )
    _request(
        "PUT",
        url,
        token,
        payload=planned_payload,
    )
    observed = _request("GET", url, token)
    final = evaluate(observed, policy)
    if final["state"] != "CURRENT":
        raise RulesetBlock(
            "ruleset update was not confirmed by exact post-readback; "
            "last-writer convergence remains pending"
        )
    return {
        **final,
        "pre_state_sha256": plan["pre_state_sha256"],
        "mutation": "PUT",
        "pre_effect_double_read": True,
        "immediate_pre_effect_reobservation": True,
        "pre_effect_source_reobservation": pre_effect_check is not None,
        "authority_environment_readback": authority_environment,
        "write_concurrency": "LAST_WRITER_WINS",
        "conditional_update_used": False,
        "get_put_race_eliminated": False,
        "converged_before_mutation": False,
        "post_update_readback": True,
        "effect_observed": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=pathlib.Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--revalidate-dispatch-source", action="store_true")
    parser.add_argument("--receipt", type=pathlib.Path)
    args = parser.parse_args(argv)
    policy = load_policy()
    try:
        if args.revalidate_dispatch_source and not args.apply:
            raise RulesetBlock("--revalidate-dispatch-source requires --apply")
        if args.apply:
            token = os.environ.get("QIKVRT_ENV_RULESET_ADMIN_TOKEN", "")
            if not token:
                raise RulesetBlock("QIKVRT_ENV_RULESET_ADMIN_TOKEN is unavailable")
            pre_effect_check = (
                reobserve_dispatch_source_from_environment
                if args.revalidate_dispatch_source
                else None
            )
            result = reconcile(token, policy, pre_effect_check=pre_effect_check)
        else:
            if args.snapshot is None:
                raise RulesetBlock("--snapshot is required without --apply")
            current = json.loads(args.snapshot.read_text(encoding="utf-8"))
            result = evaluate(_mapping(current, "ruleset snapshot"), policy)
    except (OSError, ValueError, json.JSONDecodeError, RulesetBlock) as exc:
        result = {
            "schema": SCHEMA,
            "repository": policy["repository"],
            "ruleset_id": policy["ruleset_id"],
            "state": "HOLD",
            "first_blocker": str(exc),
            "mutation": "NONE",
            "effect_observed": False,
        }
        exit_code = 2
    else:
        exit_code = 0 if result["state"] == "CURRENT" else 10
    raw = canonical_bytes(result)
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_bytes(raw)
    sys.stdout.buffer.write(raw)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
