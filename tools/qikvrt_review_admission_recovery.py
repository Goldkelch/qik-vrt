#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed recovery for trusted review workflows rejected before job 1.

The workflow supplies complete GitHub run/job/artifact observations.  This
module is pure: it selects and seals at most one same-run attempt-2 rerun and
verifies the pre-effect and post-effect bindings.  It never fabricates a new
webhook or authorizes a native account review.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from tools.qikvrt_ruleset_outbox import (
    compact_canonical_bytes as _shared_compact_canonical_bytes,
    compact_digest as _shared_compact_digest,
)


class AdmissionRecoveryError(ValueError):
    """Recovery evidence is malformed or no longer exact."""


COMPLETION_CLAIMS = {
    "PASS": False,
    "FINAL_PASS": False,
    "EFFECT_ACK_DONE": False,
    "MERGE": False,
}

TERMINAL_RECOVERY_BLOCKERS = {
    "ACTION_REQUIRED_D0_3": frozenset(
        {"SOURCE_ATTEMPT_1_ACTION_REQUIRED"}
    ),
    "RETRY_EXHAUSTED_D0_3": frozenset(
        {
            "ZERO_JOB_INGRESS_ATTEMPT_BOUND_EXHAUSTED",
            "SHARED_CORE_PARENT_TERMINAL_WITHOUT_A2_ACCEPTANCE",
        }
    ),
    "RERUN_TRANSPORT_UNACKNOWLEDGED_D0_3": frozenset(
        {"RERUN_TRANSPORT_UNACKNOWLEDGED"}
    ),
    "LIVE_SUBJECT_DRIFT_D0_3": frozenset(
        {"ZERO_JOB_INGRESS_LIVE_SUBJECT_DRIFT"}
    ),
    "SUPERSEDED_EVALUATOR_D0_3": frozenset(
        {"ZERO_JOB_RECOVERY_EVALUATOR_SUPERSEDED"}
    ),
    "SIGNER_RECEIPT_RECOVERY_EXHAUSTED_D0_3": frozenset(
        {"DELEGATED_SIGNER_RECEIPT_ATTEMPT_2_ADVERSE"}
    ),
}

TERMINAL_RECOVERY_DEFAULT_BLOCKER = {
    state: sorted(blockers)[0]
    for state, blockers in TERMINAL_RECOVERY_BLOCKERS.items()
}


def _sha(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AdmissionRecoveryError(f"{label} is not a Git SHA-1")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise AdmissionRecoveryError(f"{label} is not a SHA-256")
    return value


def _positive(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AdmissionRecoveryError(f"{label} must be positive")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return _shared_compact_canonical_bytes(value)


def _canonical_sha256(value: Any) -> str:
    return _shared_compact_digest(value)


def _workflow_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise AdmissionRecoveryError("workflow path is missing")
    return value.split("@", 1)[0]


def _live_subject(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("live recovery subject is missing")
    result = {
        "pr_number": _positive(value.get("pr_number"), "live PR number"),
        "head_sha": _sha(value.get("head_sha"), "live head SHA"),
        "head_tree_sha": _sha(
            value.get("head_tree_sha"), "live head tree SHA"
        ),
        "head_repository": value.get("head_repository"),
        "head_ref": value.get("head_ref"),
        "base_sha": _sha(value.get("base_sha"), "live base SHA"),
        "base_tree_sha": _sha(
            value.get("base_tree_sha"), "live base tree SHA"
        ),
        "base_repository": value.get("base_repository"),
        "base_ref": value.get("base_ref"),
    }
    if (
        not isinstance(result["head_repository"], str)
        or result["head_repository"].count("/") != 1
        or not isinstance(result["head_ref"], str)
        or not result["head_ref"]
        or result["base_repository"] != result["head_repository"]
        or result["base_ref"] != "main"
    ):
        raise AdmissionRecoveryError("live recovery subject provenance differs")
    return result


def _projection(run: Mapping[str, Any]) -> dict[str, Any]:
    repository = run.get("repository")
    if not isinstance(repository, Mapping):
        raise AdmissionRecoveryError("source run repository is missing")
    pull_requests = run.get("pull_requests", [])
    if not isinstance(pull_requests, list):
        raise AdmissionRecoveryError("source run pull_requests is malformed")
    return {
        "run_id": _positive(run.get("id"), "source run id"),
        "run_attempt": _positive(
            run.get("run_attempt", 1), "source run attempt"
        ),
        "workflow_id": _positive(run.get("workflow_id"), "source workflow id"),
        "workflow_path": _workflow_path(run.get("path")),
        "repository": repository.get("full_name"),
        "repository_id": repository.get("id"),
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "head_sha": _sha(run.get("head_sha"), "source run head SHA"),
        "display_title": run.get("display_title"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "created_at": run.get("created_at"),
        "jobs_total": run.get("jobs_total"),
        "artifacts_total": run.get("artifacts_total"),
        "pull_requests": pull_requests,
    }


def classify_zero_job_admission(
    run: Mapping[str, Any],
    *,
    repository: str,
    repository_id: int | None = None,
    current_main_sha: str,
    trusted_workflow_id: int,
    trusted_workflow_path: str,
    activation_locator: str,
    allowed_events: set[str],
    allow_bound_requested_child: bool = False,
) -> dict[str, Any]:
    """Classify one source without inferring why GitHub cancelled it."""
    if not isinstance(run, Mapping):
        raise AdmissionRecoveryError("source run must be an object")
    main_sha = _sha(current_main_sha, "current main SHA")
    trusted_id = _positive(trusted_workflow_id, "trusted workflow id")
    trusted_repository_id = (
        None
        if repository_id is None
        else _positive(repository_id, "trusted repository id")
    )
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise AdmissionRecoveryError("repository is invalid")
    if (
        not isinstance(trusted_workflow_path, str)
        or not trusted_workflow_path.startswith(".github/workflows/")
        or activation_locator not in {
            "qikvrt-rr-v3",
            "QIKVRT required code-owner review admission-v2",
        }
        or not isinstance(allowed_events, set)
        or not allowed_events
        or "schedule" in allowed_events
        or not isinstance(allow_bound_requested_child, bool)
        or (
            allow_bound_requested_child
            and activation_locator != "qikvrt-rr-v3"
        )
    ):
        raise AdmissionRecoveryError("recovery trust configuration is invalid")
    value = _projection(run)
    title = value["display_title"]
    if activation_locator == "qikvrt-rr-v3":
        evaluator_pattern = (
            r"^qikvrt-rr-v3 e=([0-9a-f]{40}) "
            r"p=(?:[1-9][0-9]*|event) "
            r"h=(?:[0-9a-f]{40}|event) "
            r"f=(?:[0-9a-f]{64}|event) "
            r"i=(?:[0-9a-f]{64}|event) a=(?:1|2|event)$"
        )
    else:
        evaluator_pattern = (
            rf"^{re.escape(activation_locator)} "
            r"evaluator-([0-9a-f]{40})(?: |$)"
        )
    evaluator_match = (
        re.match(evaluator_pattern, title) if isinstance(title, str) else None
    )
    evaluator_sha = evaluator_match.group(1) if evaluator_match else None
    local_admission_locator = (
        activation_locator != "qikvrt-rr-v3"
        or allow_bound_requested_child
        or (
            isinstance(title, str)
            and re.fullmatch(
                r"qikvrt-rr-v3 e=[0-9a-f]{40} p=event h=event "
                r"f=event i=event a=event",
                title,
            )
            is not None
        )
    )
    pull_requests = value["pull_requests"]
    if value["event"] == "pull_request_target":
        event_pr = pull_requests[0] if len(pull_requests) == 1 else None
        event_head = (
            event_pr.get("head") if isinstance(event_pr, Mapping) else None
        )
        event_base = (
            event_pr.get("base") if isinstance(event_pr, Mapping) else None
        )
        event_head_repo = (
            event_head.get("repo") if isinstance(event_head, Mapping) else None
        )
        event_base_repo = (
            event_base.get("repo") if isinstance(event_base, Mapping) else None
        )
        embedded_repository_ids_match = (
            trusted_repository_id is not None
            and isinstance(event_head_repo, Mapping)
            and isinstance(event_base_repo, Mapping)
            and event_head_repo.get("id") == trusted_repository_id
            and event_base_repo.get("id") == trusted_repository_id
        )
        embedded_repository_names_match = (
            isinstance(event_head_repo, Mapping)
            and isinstance(event_base_repo, Mapping)
            and event_head_repo.get("full_name") in {None, repository}
            and event_base_repo.get("full_name") in {None, repository}
        )
        event_provenance = (
            isinstance(event_pr, Mapping)
            and _positive(event_pr.get("number"), "event PR number") > 0
            and isinstance(event_head, Mapping)
            and isinstance(event_head.get("sha"), str)
            and _sha(event_head.get("sha"), "event PR head SHA")
                == event_head.get("sha")
            and value["head_sha"] == evaluator_sha
            and value["head_branch"] == "main"
            and embedded_repository_ids_match
            and embedded_repository_names_match
            and isinstance(event_base, Mapping)
            and event_base.get("ref") == "main"
            and event_base.get("sha") == evaluator_sha
        )
    else:
        event_provenance = (
            value["head_branch"] == "main"
            and evaluator_sha is not None
            and value["head_sha"] == evaluator_sha
        )
    checks = {
        "workflow_id": value["workflow_id"] == trusted_id,
        "workflow_path": value["workflow_path"] == trusted_workflow_path,
        "repository": value["repository"] == repository,
        "repository_id": (
            trusted_repository_id is not None
            and value["repository_id"] == trusted_repository_id
        ),
        "event": value["event"] in allowed_events,
        "event_provenance": event_provenance,
        "activation_locator": (
            evaluator_sha is not None and local_admission_locator
        ),
        "evaluator_workflow_sha_current": evaluator_sha == main_sha,
        "terminal_result": (
            value["status"] == "completed"
            and isinstance(value["conclusion"], str)
            and bool(value["conclusion"])
        ),
        "zero_jobs": value["jobs_total"] == 0,
        "zero_artifacts": value["artifacts_total"] == 0,
    }
    if not isinstance(value["created_at"], str) or not value["created_at"]:
        raise AdmissionRecoveryError("source run creation time is missing")
    structural_checks = {
        key: result
        for key, result in checks.items()
        if key != "evaluator_workflow_sha_current"
    }
    if not all(structural_checks.values()):
        return {
            "schema": "qikvrt_review_admission_classification_v1",
            "state": "INELIGIBLE",
            "eligible": False,
            "source": value,
            "checks": checks,
            "rerun_required": False,
            "d0": 3,
            "completion_claims": dict(COMPLETION_CLAIMS),
        }
    if checks["evaluator_workflow_sha_current"] is not True:
        state = "SUPERSEDED_EVALUATOR_D0_3"
        rerun_required = False
        d0 = 3
    elif value["conclusion"] == "action_required":
        state = "ACTION_REQUIRED_D0_3"
        rerun_required = False
        d0 = 3
    elif value["run_attempt"] == 1:
        state = "RERUN_ATTEMPT_2"
        rerun_required = True
        d0 = 2
    else:
        state = "RETRY_EXHAUSTED_D0_3"
        rerun_required = False
        d0 = 3
    result = {
        "schema": "qikvrt_review_admission_classification_v1",
        "state": state,
        "eligible": True,
        "source": value,
        "checks": checks,
        "rerun_required": rerun_required,
        "d0": d0,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    if state == "ACTION_REQUIRED_D0_3":
        result["first_blocker"] = "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
    elif state == "SUPERSEDED_EVALUATOR_D0_3":
        result["first_blocker"] = "ZERO_JOB_RECOVERY_EVALUATOR_SUPERSEDED"
    return result


def select_recovery(
    runs: Sequence[Mapping[str, Any]],
    *,
    target_configs: Mapping[int, Mapping[str, Any]],
    repository: str,
    repository_id: int,
    current_main_sha: str,
    current_run_id: int,
    consumed_sources: set[str] | None = None,
    bound_requested_run_ids: set[int] | None = None,
) -> dict[str, Any]:
    """Select exactly one oldest eligible source; attempt 2 is terminal."""
    current = _positive(current_run_id, "current recovery run id")
    consumed = set() if consumed_sources is None else consumed_sources
    bound_requested = (
        set() if bound_requested_run_ids is None else bound_requested_run_ids
    )
    if not isinstance(consumed, set) or any(
        not isinstance(item, str) or not item for item in consumed
    ):
        raise AdmissionRecoveryError("consumed recovery sources are malformed")
    if not isinstance(bound_requested, set) or any(
        isinstance(item, bool) or not isinstance(item, int) or item < 1
        for item in bound_requested
    ):
        raise AdmissionRecoveryError("bound requested-review sources are malformed")
    if not isinstance(runs, Sequence) or isinstance(runs, (str, bytes)):
        raise AdmissionRecoveryError("source runs must be a list")
    candidates: list[dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, Mapping):
            raise AdmissionRecoveryError("source run must be an object")
        if run.get("id") == current:
            continue
        workflow_id = run.get("workflow_id")
        config = target_configs.get(workflow_id) if isinstance(workflow_id, int) else None
        if not isinstance(config, Mapping):
            continue
        classified = classify_zero_job_admission(
            run,
            repository=repository,
            repository_id=repository_id,
            current_main_sha=current_main_sha,
            trusted_workflow_id=workflow_id,
            trusted_workflow_path=config.get("path"),
            activation_locator=config.get("activation_locator"),
            allowed_events=set(config.get("allowed_events", [])),
            allow_bound_requested_child=run.get("id") in bound_requested,
        )
        if classified["eligible"]:
            source = classified["source"]
            key = (
                f"{source['workflow_id']}:{source['run_id']}:"
                f"{source['run_attempt']}"
            )
            if key in consumed:
                continue
            candidates.append(classified)
    candidates.sort(
        key=lambda item: (
            item["source"]["created_at"], item["source"]["run_id"]
        )
    )
    if not candidates:
        return {
            "schema": "qikvrt_review_admission_recovery_selection_v1",
            "state": "EMPTY",
            "selected": None,
            "rerun_required": False,
            "d0": 0,
            "completion_claims": dict(COMPLETION_CLAIMS),
        }
    selected = candidates[0]
    result = {
        "schema": "qikvrt_review_admission_recovery_selection_v1",
        "state": selected["state"],
        "selected": selected["source"],
        "checks": selected["checks"],
        "rerun_required": selected["rerun_required"],
        "d0": selected["d0"],
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    if selected.get("first_blocker") is not None:
        result["first_blocker"] = selected["first_blocker"]
    return result


ADMISSION_INBOX_REF = "qikvrt/review-admission-inbox-v1"


RECOVERY_LEDGER_REFS = {
    "admission-source-rerun": ADMISSION_INBOX_REF,
    "review-wakeup": "qikvrt/review-wakeup-ledger-v1",
}

RECOVERY_LEDGER_AUTHORITY_ENVIRONMENT = "qikvrt-outbox-ledger-authority"
RECOVERY_LEDGER_WRITER_SECRET = "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN"
RECOVERY_LEDGER_AUDITOR_SECRET = "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN"
RECOVERY_LEDGER_WRITER_ACTOR_VARIABLE = (
    "QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID"
)
RECOVERY_LEDGER_FORBIDDEN_FALLBACK_SECRETS = frozenset(
    {
        RECOVERY_LEDGER_WRITER_SECRET,
        RECOVERY_LEDGER_AUDITOR_SECRET,
        "QIKVRT_OUTBOX_LEDGER_WRITER_TOKEN",
        "QIKVRT_OUTBOX_LEDGER_AUDITOR_TOKEN",
    }
)


def recovery_ledger_genesis_path(lane: str) -> str:
    if lane not in RECOVERY_LEDGER_REFS:
        raise AdmissionRecoveryError("recovery ledger lane is invalid")
    return f".qikvrt/recovery/{lane}/genesis.json"


def build_recovery_ledger_genesis(
    *, lane: str, repository: str, repository_id: int, initialized_at: str
) -> dict[str, Any]:
    if lane not in RECOVERY_LEDGER_REFS:
        raise AdmissionRecoveryError("recovery ledger lane is invalid")
    record_schema_epoch = {
        "admission-source-rerun": "qikvrt_review_admission_inbox_source_v1",
        "review-wakeup": "qikvrt_human_review_transition_fact_v2",
    }[lane]
    value = {
        "schema": "qikvrt_recovery_ledger_genesis_v1",
        "lane": lane,
        "repository": _repository(repository, "recovery genesis repository"),
        "repository_id": _positive(
            repository_id, "recovery genesis repository id"
        ),
        "ref": RECOVERY_LEDGER_REFS[lane],
        "initialized_at": _timestamp(
            initialized_at, "recovery genesis timestamp"
        ),
        "no_silent_reinitialization": True,
        "deletion_protection_required": True,
        "update_protection_required": True,
        "non_fast_forward_protection_required": True,
        "writer_environment": RECOVERY_LEDGER_AUTHORITY_ENVIRONMENT,
        "writer_secret": RECOVERY_LEDGER_WRITER_SECRET,
        "writer_actor_variable": RECOVERY_LEDGER_WRITER_ACTOR_VARIABLE,
        "sole_integration_bypass_required": True,
        "record_schema_epoch": record_schema_epoch,
        "migration_policy": "EXTERNAL_EMPTY_GENESIS_NO_IN_PLACE_MIGRATION",
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["genesis_sha256"] = _canonical_sha256(value)
    return value


def validate_recovery_ledger_genesis(
    value: Mapping[str, Any],
    *, lane: str,
    repository: str,
    repository_id: int,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("recovery ledger genesis is malformed")
    observed = dict(value)
    claimed = observed.pop("genesis_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("recovery ledger genesis digest differs")
    if (
        lane not in RECOVERY_LEDGER_REFS
        or observed.get("schema") != "qikvrt_recovery_ledger_genesis_v1"
        or observed.get("lane") != lane
        or observed.get("repository") != repository
        or observed.get("repository_id") != repository_id
        or observed.get("ref") != RECOVERY_LEDGER_REFS[lane]
        or observed.get("no_silent_reinitialization") is not True
        or observed.get("deletion_protection_required") is not True
        or observed.get("update_protection_required") is not True
        or observed.get("non_fast_forward_protection_required") is not True
        or observed.get("writer_environment")
            != RECOVERY_LEDGER_AUTHORITY_ENVIRONMENT
        or observed.get("writer_secret") != RECOVERY_LEDGER_WRITER_SECRET
        or observed.get("writer_actor_variable")
            != RECOVERY_LEDGER_WRITER_ACTOR_VARIABLE
        or observed.get("sole_integration_bypass_required") is not True
        or observed.get("record_schema_epoch") != {
            "admission-source-rerun": "qikvrt_review_admission_inbox_source_v1",
            "review-wakeup": "qikvrt_human_review_transition_fact_v2",
        }.get(lane)
        or observed.get("migration_policy")
            != "EXTERNAL_EMPTY_GENESIS_NO_IN_PLACE_MIGRATION"
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("recovery ledger genesis boundary differs")
    initialized_at = _timestamp(
        observed.get("initialized_at"), "recovery genesis timestamp"
    )
    _positive(observed.get("repository_id"), "recovery genesis repository id")
    expected = build_recovery_ledger_genesis(
        lane=lane,
        repository=repository,
        repository_id=repository_id,
        initialized_at=initialized_at,
    )
    if dict(value) != expected:
        raise AdmissionRecoveryError("recovery ledger genesis shape differs")
    return dict(value)


def validate_recovery_ledger_rulesets(
    rulesets: Sequence[Mapping[str, Any]], *, lane: str, writer_actor_id: int
) -> dict[str, Any]:
    """Require one exact active protected-ref ruleset and sole App bypass."""
    if lane not in RECOVERY_LEDGER_REFS:
        raise AdmissionRecoveryError("recovery ledger lane is invalid")
    if not isinstance(rulesets, Sequence) or isinstance(rulesets, (str, bytes)):
        raise AdmissionRecoveryError("recovery ledger rulesets are malformed")
    exact_ref = f"refs/heads/{RECOVERY_LEDGER_REFS[lane]}"
    actor_id = _positive(writer_actor_id, "ledger writer actor id")
    matches: list[dict[str, Any]] = []
    for raw in rulesets:
        if not isinstance(raw, Mapping):
            raise AdmissionRecoveryError("recovery ledger ruleset is malformed")
        conditions = raw.get("conditions")
        ref_name = conditions.get("ref_name") if isinstance(conditions, Mapping) else None
        if (
            not isinstance(ref_name, Mapping)
            or ref_name.get("include") != [exact_ref]
            or ref_name.get("exclude") != []
        ):
            continue
        rules = raw.get("rules")
        bypass = raw.get("bypass_actors")
        if (
            raw.get("enforcement") != "active"
            or raw.get("target") != "branch"
            or raw.get("source_type") != "Repository"
            or not isinstance(rules, list)
            or {item.get("type") for item in rules if isinstance(item, Mapping)}
                != {"update", "deletion", "non_fast_forward"}
            or not isinstance(bypass, list)
            or len(bypass) != 1
            or not isinstance(bypass[0], Mapping)
            or bypass[0].get("actor_id") != actor_id
            or bypass[0].get("actor_type") != "Integration"
            or bypass[0].get("bypass_mode") != "always"
        ):
            raise AdmissionRecoveryError(
                "recovery ledger protected-ref authority differs"
            )
        matches.append(dict(raw))
    if len(matches) != 1:
        raise AdmissionRecoveryError(
            "exact recovery ledger protected-ref ruleset is absent or ambiguous"
        )
    return matches[0]


def recovery_ledger_ruleset_id(
    branch_rules: Sequence[Mapping[str, Any]], *, lane: str
) -> int:
    if lane not in RECOVERY_LEDGER_REFS:
        raise AdmissionRecoveryError("recovery ledger lane is invalid")
    if not isinstance(branch_rules, Sequence) or isinstance(
        branch_rules, (str, bytes)
    ):
        raise AdmissionRecoveryError("recovery ledger branch rules are malformed")
    required = {"update", "deletion", "non_fast_forward"}
    authoritative = [
        item for item in branch_rules
        if isinstance(item, Mapping) and item.get("type") in required
    ]
    ids = {
        item.get("ruleset_id") for item in authoritative
        if isinstance(item.get("ruleset_id"), int)
        and not isinstance(item.get("ruleset_id"), bool)
    }
    if (
        {item.get("type") for item in authoritative} != required
        or len(ids) != 1
    ):
        raise AdmissionRecoveryError(
            "recovery ledger update/deletion/non-fast-forward protection differs"
        )
    return _positive(next(iter(ids)), "recovery ledger ruleset id")


def verify_recovery_ledger_authority(
    *,
    lane: str,
    repository: str,
    writer_actor_id: int,
    writer_group: str,
    api: Callable[[str], Any],
) -> dict[str, Any]:
    """Read back the exact App, ref, environment and secret-scope boundary."""
    if lane not in RECOVERY_LEDGER_REFS:
        raise AdmissionRecoveryError("recovery ledger lane is invalid")
    repo = _repository(repository, "recovery ledger repository")
    actor_id = _positive(writer_actor_id, "recovery ledger writer actor id")
    expected_group = f"qikvrt-outbox-ledger-v2-{lane}"
    if writer_group != expected_group:
        raise AdmissionRecoveryError("recovery ledger writer group differs")
    installation = api("installation")
    if (
        not isinstance(installation, Mapping)
        or installation.get("app_id") != actor_id
    ):
        raise AdmissionRecoveryError("recovery ledger writer App differs")
    branch = RECOVERY_LEDGER_REFS[lane]
    encoded_branch = urllib.parse.quote(branch, safe="")
    rules: list[Mapping[str, Any]] = []
    for page in range(1, 101):
        batch = api(
            f"repos/{repo}/rules/branches/{encoded_branch}?per_page=100&page={page}"
        )
        if not isinstance(batch, list) or any(
            not isinstance(item, Mapping) for item in batch
        ):
            raise AdmissionRecoveryError(
                "recovery ledger branch-rule readback is malformed"
            )
        rules.extend(batch)
        if len(batch) < 100:
            break
    else:
        raise AdmissionRecoveryError(
            "recovery ledger branch-rule pagination exceeded"
        )
    ruleset_id = recovery_ledger_ruleset_id(rules, lane=lane)
    ruleset = api(f"repos/{repo}/rulesets/{ruleset_id}")
    exact = validate_recovery_ledger_rulesets(
        [ruleset], lane=lane, writer_actor_id=actor_id
    )
    if exact.get("id") != ruleset_id or exact.get("source") != repo:
        raise AdmissionRecoveryError("recovery ledger ruleset source differs")

    environment_name = urllib.parse.quote(
        RECOVERY_LEDGER_AUTHORITY_ENVIRONMENT, safe=""
    )
    environment = api(f"repos/{repo}/environments/{environment_name}")
    if not isinstance(environment, Mapping):
        raise AdmissionRecoveryError(
            "recovery ledger Authority environment readback is malformed"
        )
    deployment = environment.get("deployment_branch_policy")
    protection_rules = environment.get("protection_rules")
    if (
        environment.get("name") != RECOVERY_LEDGER_AUTHORITY_ENVIRONMENT
        or not isinstance(deployment, Mapping)
        or deployment.get("protected_branches") is not False
        or deployment.get("custom_branch_policies") is not True
        or not isinstance(protection_rules, list)
        or not protection_rules
    ):
        raise AdmissionRecoveryError(
            "recovery ledger Authority environment is not protected main-only"
        )

    def named_inventory(path: str, key: str) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        declared_total: int | None = None
        for page in range(1, 11):
            separator = "&" if "?" in path else "?"
            response = api(f"{path}{separator}per_page=100&page={page}")
            if not isinstance(response, Mapping):
                raise AdmissionRecoveryError(
                    "recovery ledger Authority inventory is malformed"
                )
            total = response.get("total_count")
            items = response.get(key)
            if (
                isinstance(total, bool)
                or not isinstance(total, int)
                or total < 0
                or total > 1000
                or not isinstance(items, list)
                or len(items) > 100
                or any(not isinstance(item, Mapping) for item in items)
            ):
                raise AdmissionRecoveryError(
                    "recovery ledger Authority inventory page is malformed"
                )
            if declared_total is None:
                declared_total = total
            elif declared_total != total:
                raise AdmissionRecoveryError(
                    "recovery ledger Authority inventory changed during readback"
                )
            values.extend(dict(item) for item in items)
            if len(items) < 100:
                break
        else:
            raise AdmissionRecoveryError(
                "recovery ledger Authority inventory exceeds bound"
            )
        names = [item.get("name") for item in values]
        if (
            declared_total != len(values)
            or any(not isinstance(name, str) or not name for name in names)
            or len(set(names)) != len(names)
        ):
            raise AdmissionRecoveryError(
                "recovery ledger Authority inventory is incomplete"
            )
        return values

    branch_policies = named_inventory(
        f"repos/{repo}/environments/{environment_name}/"
        "deployment-branch-policies",
        "branch_policies",
    )
    environment_secrets = named_inventory(
        f"repos/{repo}/environments/{environment_name}/secrets", "secrets"
    )
    repository_secrets = named_inventory(
        f"repos/{repo}/actions/secrets", "secrets"
    )
    repository_metadata = api(f"repos/{repo}")
    owner = (
        repository_metadata.get("owner")
        if isinstance(repository_metadata, Mapping)
        else None
    )
    if not isinstance(owner, Mapping):
        raise AdmissionRecoveryError(
            "recovery ledger repository owner readback is malformed"
        )
    expected_owner = repo.split("/", 1)[0]
    owner_login = owner.get("login")
    owner_type = owner.get("type")
    owner_id = owner.get("id")
    if (
        owner_login != expected_owner
        or owner_type not in {"User", "Organization"}
        or isinstance(owner_id, bool)
        or not isinstance(owner_id, int)
        or owner_id < 1
    ):
        raise AdmissionRecoveryError(
            "recovery ledger repository owner identity is invalid"
        )
    if owner_type == "Organization":
        organization_secrets = named_inventory(
            "orgs/"
            + urllib.parse.quote(str(owner_login), safe="")
            + "/actions/secrets",
            "secrets",
        )
        organization_scope = "VERIFIED_ORGANIZATION_SECRET_INVENTORY"
    else:
        # A user account has no organization-secret namespace.  Skipping that
        # endpoint is structural evidence, not an interpretation of a 404 as
        # an empty inventory.
        organization_secrets = []
        organization_scope = "NOT_APPLICABLE_USER_OWNER"
    environment_names = {item["name"] for item in environment_secrets}
    repository_names = {item["name"] for item in repository_secrets}
    organization_names = {item["name"] for item in organization_secrets}
    if (
        [
            {"name": item.get("name"), "type": item.get("type")}
            for item in branch_policies
        ]
        != [{"name": "main", "type": "branch"}]
        or not {
            RECOVERY_LEDGER_WRITER_SECRET,
            RECOVERY_LEDGER_AUDITOR_SECRET,
        }.issubset(environment_names)
        or RECOVERY_LEDGER_FORBIDDEN_FALLBACK_SECRETS & repository_names
        or RECOVERY_LEDGER_FORBIDDEN_FALLBACK_SECRETS & organization_names
    ):
        raise AdmissionRecoveryError(
            "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED"
        )
    ref = api(f"repos/{repo}/git/ref/heads/{branch}")
    obj = ref.get("object") if isinstance(ref, Mapping) else None
    head_sha = _sha(
        obj.get("sha") if isinstance(obj, Mapping) else None,
        "recovery ledger protected ref head",
    )
    return {
        "schema": "qikvrt_recovery_ledger_authority_readback_v1",
        "lane": lane,
        "repository": repo,
        "ref": f"refs/heads/{branch}",
        "head_sha": head_sha,
        "ruleset_id": ruleset_id,
        "writer_actor_id": actor_id,
        "writer_group": expected_group,
        "repository_owner": {
            "login": owner_login,
            "type": owner_type,
            "id": owner_id,
        },
        "environment": RECOVERY_LEDGER_AUTHORITY_ENVIRONMENT,
        "deployment_branch": "main",
        "protection_rules_present": True,
        "environment_secret_names_present": [
            RECOVERY_LEDGER_AUDITOR_SECRET,
            RECOVERY_LEDGER_WRITER_SECRET,
        ],
        "repository_scope_fallback_names_absent": True,
        "organization_scope_fallback_names_absent": True,
        "organization_scope_readback": organization_scope,
        "secret_values_observed": False,
        "external_configuration_verified": True,
        "verified": True,
        "authority_boundary": "RECOVERY_ONLY",
    }


def build_recovery_ledger_effect_authority_readback(
    authority: Mapping[str, Any],
    *,
    lane: str,
    evaluator_sha: str,
    effect_run_id: int,
    effect_run_attempt: int,
    effect_run_started_at: str,
) -> dict[str, Any]:
    """Seal one live external-configuration proof into the same ledger CAS."""
    if not isinstance(authority, Mapping):
        raise AdmissionRecoveryError("recovery ledger Authority proof is malformed")
    exact = dict(authority)
    repository = exact.get("repository")
    owner = exact.get("repository_owner")
    expected_owner = (
        repository.split("/", 1)[0]
        if isinstance(repository, str) and "/" in repository
        else None
    )
    owner_type = owner.get("type") if isinstance(owner, Mapping) else None
    owner_scope = exact.get("organization_scope_readback")
    if (
        exact.get("schema") != "qikvrt_recovery_ledger_authority_readback_v1"
        or exact.get("lane") != lane
        or exact.get("verified") is not True
        or exact.get("external_configuration_verified") is not True
        or exact.get("deployment_branch") != "main"
        or exact.get("environment") != RECOVERY_LEDGER_AUTHORITY_ENVIRONMENT
        or exact.get("environment_secret_names_present")
        != [RECOVERY_LEDGER_AUDITOR_SECRET, RECOVERY_LEDGER_WRITER_SECRET]
        or exact.get("repository_scope_fallback_names_absent") is not True
        or exact.get("organization_scope_fallback_names_absent") is not True
        or not isinstance(owner, Mapping)
        or owner.get("login") != expected_owner
        or owner_type not in {"User", "Organization"}
        or isinstance(owner.get("id"), bool)
        or not isinstance(owner.get("id"), int)
        or owner.get("id") < 1
        or owner_scope
        != (
            "VERIFIED_ORGANIZATION_SECRET_INVENTORY"
            if owner_type == "Organization"
            else "NOT_APPLICABLE_USER_OWNER"
        )
        or exact.get("secret_values_observed") is not False
        or exact.get("authority_boundary") != "RECOVERY_ONLY"
    ):
        raise AdmissionRecoveryError(
            "recovery ledger external configuration is not verified"
        )
    value = {
        "schema": "qikvrt_recovery_ledger_effect_authority_readback_v1",
        "lane": lane,
        "authority": exact,
        "intent_evaluator_sha": _sha(
            evaluator_sha, "recovery Authority evaluator"
        ),
        "effect_run_id": _positive(
            effect_run_id, "recovery Authority effect run"
        ),
        "effect_run_attempt": _positive(
            effect_run_attempt, "recovery Authority effect run attempt"
        ),
        "effect_run_started_at": _timestamp(
            effect_run_started_at, "recovery Authority effect run start"
        ),
        "external_configuration_verified": True,
        "persisted_with_effect": True,
        "authority_boundary": "RECOVERY_ONLY",
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["readback_sha256"] = _canonical_sha256(value)
    return value


def validate_recovery_ledger_effect_authority_readback(
    value: Mapping[str, Any], *, lane: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError(
            "recovery ledger effect Authority readback is malformed"
        )
    observed = dict(value)
    claimed = observed.pop("readback_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError(
            "recovery ledger effect Authority digest differs"
        )
    rebuilt = build_recovery_ledger_effect_authority_readback(
        observed.get("authority"),
        lane=lane,
        evaluator_sha=observed.get("intent_evaluator_sha"),
        effect_run_id=observed.get("effect_run_id"),
        effect_run_attempt=observed.get("effect_run_attempt"),
        effect_run_started_at=observed.get("effect_run_started_at"),
    )
    if rebuilt != dict(value):
        raise AdmissionRecoveryError(
            "recovery ledger effect Authority readback differs"
        )
    return dict(value)


def recovery_ledger_effect_authority_readback_path(
    value: Mapping[str, Any], *, lane: str
) -> str:
    exact = validate_recovery_ledger_effect_authority_readback(value, lane=lane)
    return (
        f".qikvrt/recovery/{lane}/authority-readbacks/"
        f"{exact['effect_run_id']:020d}/"
        f"{exact['effect_run_attempt']:04d}-{exact['readback_sha256']}.json"
    )


def admission_inbox_meta_path() -> str:
    return ".qikvrt/recovery/admission-source-rerun/meta.json"


def admission_inbox_scan_path() -> str:
    return ".qikvrt/recovery/admission-source-rerun/scan.json"


def admission_inbox_slot_path(sequence: int) -> str:
    return (
        ".qikvrt/recovery/admission-source-rerun/slots/"
        f"{_positive(sequence, 'admission inbox sequence'):020d}.json"
    )


def admission_inbox_locator_path(fingerprint: str) -> str:
    if not isinstance(fingerprint, str) or re.fullmatch(
        r"[0-9a-f]{64}", fingerprint
    ) is None:
        raise AdmissionRecoveryError("admission inbox fingerprint is malformed")
    return (
        ".qikvrt/recovery/admission-source-rerun/fingerprints/"
        f"{fingerprint[:2]}/{fingerprint}.json"
    )


def admission_inbox_rerun_path(sequence: int) -> str:
    return (
        ".qikvrt/recovery/admission-source-rerun/child-rerun/"
        f"{_positive(sequence, 'admission inbox sequence'):020d}.json"
    )


def admission_inbox_acceptance_path(sequence: int) -> str:
    return (
        ".qikvrt/recovery/admission-source-rerun/acceptance/"
        f"{_positive(sequence, 'admission inbox sequence'):020d}.json"
    )


def admission_inbox_attempt_chain_path(run_id: int, run_attempt: int = 2) -> str:
    source_run = _positive(run_id, "admission attempt-chain run id")
    attempt = _positive(run_attempt, "admission attempt-chain run attempt")
    if attempt != 2:
        raise AdmissionRecoveryError("admission attempt-chain target is not two")
    return (
        ".qikvrt/recovery/admission-source-rerun/attempt-authority/"
        f"{source_run}/attempt-{attempt}.json"
    )


def admission_inbox_terminal_path(sequence: int) -> str:
    return (
        ".qikvrt/recovery/admission-source-rerun/terminal/"
        f"{_positive(sequence, 'admission inbox sequence'):020d}.json"
    )


def empty_admission_inbox_meta() -> dict[str, Any]:
    return {
        "schema": "qikvrt_review_admission_inbox_meta_v1",
        "next_sequence": 1,
        "drain_sequence": 1,
        "authority_boundary": "RECOVERY_ONLY",
    }


def validate_admission_inbox_meta(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission inbox metadata is malformed")
    if (
        value.get("schema") != "qikvrt_review_admission_inbox_meta_v1"
        or value.get("authority_boundary") != "RECOVERY_ONLY"
    ):
        raise AdmissionRecoveryError("admission inbox metadata boundary differs")
    next_sequence = _positive(value.get("next_sequence"), "inbox next sequence")
    drain_sequence = _positive(
        value.get("drain_sequence"), "inbox drain sequence"
    )
    if drain_sequence > next_sequence:
        raise AdmissionRecoveryError("admission inbox drain exceeds next")
    return dict(value)


def empty_admission_scan_cursor() -> dict[str, Any]:
    return {
        "schema": "qikvrt_review_admission_scan_cursor_v3",
        "target_index": 0,
        "page": 1,
        "generation": 1,
        "window_upper_created_at": None,
        "window_lower_created_at": None,
        "repository_created_at": None,
        "deferred_windows": [],
        "quarantined_windows": [],
        "quarantined_window_count": 0,
        "quarantine_chain_sha256": _canonical_sha256([]),
        "target_declared_total": None,
        "target_run_ids": [],
        "target_run_ids_sha256": _canonical_sha256([]),
        "inventory_restart_count": 0,
        "last_completed_inventory": None,
        "default_window_seconds": 30 * 24 * 60 * 60,
        "filtered_result_cap": 1000,
        "page_size": 20,
        "authority_boundary": "RECOVERY_ONLY",
    }


def validate_admission_scan_cursor(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission scan cursor is malformed")
    if (
        value.get("schema") != "qikvrt_review_admission_scan_cursor_v3"
        or value.get("target_index") not in {0, 1}
        or value.get("page_size") != 20
        or value.get("default_window_seconds") != 30 * 24 * 60 * 60
        or value.get("filtered_result_cap") != 1000
        or value.get("authority_boundary") != "RECOVERY_ONLY"
    ):
        raise AdmissionRecoveryError("admission scan cursor boundary differs")
    _positive(value.get("page"), "admission scan page")
    _positive(value.get("generation"), "admission scan generation")
    upper = value.get("window_upper_created_at")
    lower = value.get("window_lower_created_at")
    floor = value.get("repository_created_at")
    if (upper is None) != (lower is None) or (upper is None) != (floor is None):
        raise AdmissionRecoveryError("admission scan window is partial")
    if upper is not None:
        upper = _timestamp(upper, "admission scan upper creation bound")
        lower = _timestamp(lower, "admission scan lower creation bound")
        floor = _timestamp(floor, "admission scan repository creation bound")
        if not floor <= lower < upper:
            raise AdmissionRecoveryError("admission scan window order differs")
    deferred = value.get("deferred_windows")
    if not isinstance(deferred, list) or len(deferred) > 64:
        raise AdmissionRecoveryError("admission scan deferred windows differ")
    for window in deferred:
        if not isinstance(window, Mapping):
            raise AdmissionRecoveryError("admission scan deferred window is malformed")
        deferred_lower = _timestamp(
            window.get("lower_created_at"), "deferred scan lower bound"
        )
        deferred_upper = _timestamp(
            window.get("upper_created_at"), "deferred scan upper bound"
        )
        if not deferred_lower < deferred_upper:
            raise AdmissionRecoveryError("admission scan deferred window order differs")
    quarantined = value.get("quarantined_windows")
    quarantine_count = value.get("quarantined_window_count")
    if (
        not isinstance(quarantined, list)
        or len(quarantined) > 64
        or isinstance(quarantine_count, bool)
        or not isinstance(quarantine_count, int)
        or quarantine_count < len(quarantined)
    ):
        raise AdmissionRecoveryError("admission scan quarantine boundary differs")
    _digest(
        value.get("quarantine_chain_sha256"),
        "admission scan quarantine chain",
    )
    declared_total = value.get("target_declared_total")
    run_ids = value.get("target_run_ids")
    restart_count = value.get("inventory_restart_count")
    if (
        not isinstance(run_ids, list)
        or len(run_ids) >= value["filtered_result_cap"]
        or any(
            isinstance(run_id, bool)
            or not isinstance(run_id, int)
            or run_id < 1
            for run_id in run_ids
        )
        or len(set(run_ids)) != len(run_ids)
        or run_ids != sorted(run_ids, reverse=True)
        or value.get("target_run_ids_sha256") != _canonical_sha256(run_ids)
        or isinstance(restart_count, bool)
        or not isinstance(restart_count, int)
        or restart_count < 0
    ):
        raise AdmissionRecoveryError("admission scan target inventory differs")
    if declared_total is None:
        if run_ids or value.get("page") != 1:
            raise AdmissionRecoveryError(
                "admission scan unsealed inventory has page state"
            )
    elif (
        isinstance(declared_total, bool)
        or not isinstance(declared_total, int)
        or declared_total < 0
        or declared_total >= value["filtered_result_cap"]
        or len(run_ids) >= declared_total
        or len(run_ids) != (value["page"] - 1) * value["page_size"]
    ):
        raise AdmissionRecoveryError("admission scan declared inventory differs")
    completed = value.get("last_completed_inventory")
    if completed is not None:
        if not isinstance(completed, Mapping):
            raise AdmissionRecoveryError(
                "admission scan completed inventory is malformed"
            )
        completed_total = completed.get("declared_total")
        if (
            set(completed)
            != {
                "target_index",
                "generation",
                "lower_created_at",
                "upper_created_at",
                "declared_total",
                "ordered_run_ids_sha256",
            }
            or completed.get("target_index") not in {0, 1}
            or isinstance(completed.get("generation"), bool)
            or not isinstance(completed.get("generation"), int)
            or completed["generation"] < 1
            or isinstance(completed_total, bool)
            or not isinstance(completed_total, int)
            or not (0 <= completed_total < value["filtered_result_cap"])
        ):
            raise AdmissionRecoveryError(
                "admission scan completed inventory differs"
            )
        completed_lower = _timestamp(
            completed.get("lower_created_at"),
            "completed scan lower bound",
        )
        completed_upper = _timestamp(
            completed.get("upper_created_at"),
            "completed scan upper bound",
        )
        if completed_lower >= completed_upper:
            raise AdmissionRecoveryError(
                "admission scan completed inventory order differs"
            )
        _digest(
            completed.get("ordered_run_ids_sha256"),
            "completed scan ordered run inventory",
        )
    for evidence in quarantined:
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("target_index") not in {0, 1}
            or isinstance(evidence.get("declared_total"), bool)
            or not isinstance(evidence.get("declared_total"), int)
            or evidence["declared_total"] < value["filtered_result_cap"]
            or evidence.get("result") != "INCOMPLETE_NOT_ABSENCE"
            or evidence.get("authority_state") != "HOLD"
            or evidence.get("continuation_strategy")
                != "EXACT_SOURCE_RUN_ID_EVENT_OR_AUTHORITY_SUPPLIED_ID"
            or evidence.get("absence_authorized") is not False
        ):
            raise AdmissionRecoveryError("admission scan quarantine differs")
        lower = _timestamp(
            evidence.get("lower_created_at"), "quarantine lower bound"
        )
        upper = _timestamp(
            evidence.get("upper_created_at"), "quarantine upper bound"
        )
        if not lower < upper:
            raise AdmissionRecoveryError("admission scan quarantine order differs")
    return dict(value)


def migrate_admission_scan_cursor(value: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade the pre-inventory cursor by conservatively rescanning its target.

    Version two did not persist the endpoint's declared total or the ordered
    run IDs already traversed.  Those bytes cannot authorize continuing at a
    later page.  Migration therefore retains the immutable time shard and all
    quarantine/fairness state, but returns the current target to page one and
    records one inventory restart.  Existing source locators make this replay
    idempotent; no source absence is inferred from the discarded page offset.
    """
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission scan cursor is malformed")
    if value.get("schema") == "qikvrt_review_admission_scan_cursor_v3":
        return validate_admission_scan_cursor(value)
    legacy_keys = {
        "schema",
        "target_index",
        "page",
        "generation",
        "window_upper_created_at",
        "window_lower_created_at",
        "repository_created_at",
        "deferred_windows",
        "quarantined_windows",
        "quarantined_window_count",
        "quarantine_chain_sha256",
        "default_window_seconds",
        "filtered_result_cap",
        "page_size",
        "authority_boundary",
    }
    if value.get("schema") != "qikvrt_review_admission_scan_cursor_v2" or set(
        value
    ) != legacy_keys:
        raise AdmissionRecoveryError("admission scan cursor schema differs")
    upgraded = dict(value)
    upgraded.update(
        {
            "schema": "qikvrt_review_admission_scan_cursor_v3",
            "page": 1,
            "target_declared_total": None,
            "target_run_ids": [],
            "target_run_ids_sha256": _canonical_sha256([]),
            "inventory_restart_count": 1,
            "last_completed_inventory": None,
        }
    )
    return validate_admission_scan_cursor(upgraded)


def bind_admission_scan_window(
    cursor: Mapping[str, Any], *, upper_created_at: str,
    repository_created_at: str,
) -> dict[str, Any]:
    current = validate_admission_scan_cursor(cursor)
    upper = _timestamp(upper_created_at, "admission scan upper creation bound")
    floor = _timestamp(
        repository_created_at, "admission scan repository creation bound"
    )
    if current["window_upper_created_at"] is not None:
        if current["repository_created_at"] != floor:
            raise AdmissionRecoveryError("admission scan repository bound differs")
        if current["window_upper_created_at"] != upper:
            raise AdmissionRecoveryError("admission scan upper bound is immutable")
        return current
    upper_dt = datetime.fromisoformat(upper.replace("Z", "+00:00"))
    floor_dt = datetime.fromisoformat(floor.replace("Z", "+00:00"))
    if floor_dt >= upper_dt:
        raise AdmissionRecoveryError("admission scan repository bound is not older")
    lower_dt = max(
        floor_dt,
        upper_dt - timedelta(seconds=current["default_window_seconds"]),
    )
    result = dict(current)
    result["window_upper_created_at"] = upper
    result["window_lower_created_at"] = lower_dt.isoformat().replace(
        "+00:00", "Z"
    )
    result["repository_created_at"] = floor
    return result


def shrink_admission_scan_window(
    cursor: Mapping[str, Any], *, declared_total: int
) -> dict[str, Any]:
    """Bisect a capped immutable time shard without inferring absence."""
    current = validate_admission_scan_cursor(cursor)
    if (
        isinstance(declared_total, bool)
        or not isinstance(declared_total, int)
        or declared_total < current["filtered_result_cap"]
    ):
        raise AdmissionRecoveryError("admission scan cap observation differs")
    if (
        current["page"] != 1
        or current["target_index"] not in {0, 1}
        or current["target_declared_total"] is not None
        or current["target_run_ids"]
    ):
        raise AdmissionRecoveryError("admission scan capped page is not first")
    lower = datetime.fromisoformat(
        current["window_lower_created_at"].replace("Z", "+00:00")
    )
    upper = datetime.fromisoformat(
        current["window_upper_created_at"].replace("Z", "+00:00")
    )
    seconds = int((upper - lower).total_seconds())
    if seconds <= 1:
        evidence = {
            "target_index": current["target_index"],
            "lower_created_at": current["window_lower_created_at"],
            "upper_created_at": current["window_upper_created_at"],
            "declared_total": declared_total,
            "filtered_result_cap": current["filtered_result_cap"],
            "generation": current["generation"],
            "result": "INCOMPLETE_NOT_ABSENCE",
            "authority_state": "HOLD",
            "continuation_strategy": (
                "EXACT_SOURCE_RUN_ID_EVENT_OR_AUTHORITY_SUPPLIED_ID"
            ),
            "absence_authorized": False,
        }
        result = dict(current)
        result["quarantined_window_count"] += 1
        result["quarantine_chain_sha256"] = _canonical_sha256({
            "prior": current["quarantine_chain_sha256"],
            "evidence": evidence,
        })
        result["quarantined_windows"] = (
            list(current["quarantined_windows"])[-63:] + [evidence]
        )
        result["page"] = 1
        if result["target_index"] == 0:
            result["target_index"] = 1
        else:
            result["target_index"] = 0
            deferred = list(result["deferred_windows"])
            if deferred:
                window = deferred.pop()
                result["window_lower_created_at"] = window["lower_created_at"]
                result["window_upper_created_at"] = window["upper_created_at"]
                result["deferred_windows"] = deferred
            elif result["window_lower_created_at"] == result["repository_created_at"]:
                # Rebind to the next immutable high-watermark on the next
                # schedule; the quarantined second remains explicit evidence.
                result["generation"] += 1
                result["window_lower_created_at"] = None
                result["window_upper_created_at"] = None
                result["repository_created_at"] = None
            else:
                upper_text = result["window_lower_created_at"]
                upper_dt = datetime.fromisoformat(
                    upper_text.replace("Z", "+00:00")
                )
                floor_dt = datetime.fromisoformat(
                    result["repository_created_at"].replace("Z", "+00:00")
                )
                lower_dt = max(
                    floor_dt,
                    upper_dt - timedelta(
                        seconds=result["default_window_seconds"]
                    ),
                )
                result["window_upper_created_at"] = upper_text
                result["window_lower_created_at"] = lower_dt.isoformat().replace(
                    "+00:00", "Z"
                )
        return validate_admission_scan_cursor(result)
    midpoint = lower + timedelta(seconds=seconds // 2)
    midpoint_text = midpoint.isoformat().replace("+00:00", "Z")
    deferred = list(current["deferred_windows"])
    deferred.append({
        "lower_created_at": current["window_lower_created_at"],
        "upper_created_at": midpoint_text,
    })
    result = dict(current)
    result["window_lower_created_at"] = midpoint_text
    result["deferred_windows"] = deferred
    result["page"] = 1
    return validate_admission_scan_cursor(result)


def restart_admission_scan_inventory(
    cursor: Mapping[str, Any],
) -> dict[str, Any]:
    """Forget one inconsistent page inventory without advancing its shard.

    This transition is used when the endpoint's declared total crosses the
    filtered-result cap after page one.  The already sealed time bounds remain
    immutable and the next tick re-reads page one, where the ordinary shard
    split/quarantine logic can make bounded progress.  It never authorizes an
    absence or skips a source ID from the abandoned inventory.
    """
    current = validate_admission_scan_cursor(cursor)
    if (
        current["page"] == 1
        or current["target_declared_total"] is None
        or not current["target_run_ids"]
    ):
        raise AdmissionRecoveryError(
            "admission scan inventory restart has no sealed prior page"
        )
    result = dict(current)
    result["page"] = 1
    result["target_declared_total"] = None
    result["target_run_ids"] = []
    result["target_run_ids_sha256"] = _canonical_sha256([])
    result["inventory_restart_count"] += 1
    return validate_admission_scan_cursor(result)


def build_admission_scan_quarantine_record(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> dict[str, Any]:
    prior = validate_admission_scan_cursor(before)
    current = validate_admission_scan_cursor(after)
    if (
        current["quarantined_window_count"]
        != prior["quarantined_window_count"] + 1
        or current["quarantine_chain_sha256"]
        == prior["quarantine_chain_sha256"]
        or not current["quarantined_windows"]
    ):
        raise AdmissionRecoveryError("admission quarantine transition differs")
    evidence = current["quarantined_windows"][-1]
    value = {
        "schema": "qikvrt_review_admission_scan_quarantine_v1",
        "evidence": evidence,
        "prior_chain_sha256": prior["quarantine_chain_sha256"],
        "quarantine_chain_sha256": current["quarantine_chain_sha256"],
        "quarantined_window_count": current["quarantined_window_count"],
        "authority_state": "HOLD",
        "continuation_strategy": (
            "EXACT_SOURCE_RUN_ID_EVENT_OR_AUTHORITY_SUPPLIED_ID"
        ),
        "absence_authorized": False,
        "authority_boundary": "RECOVERY_ONLY",
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["record_sha256"] = _canonical_sha256(value)
    return value


def validate_admission_scan_quarantine_record(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission quarantine record is malformed")
    raw = dict(value)
    claimed = raw.pop("record_sha256", None)
    if claimed != _canonical_sha256(raw):
        raise AdmissionRecoveryError("admission quarantine digest differs")
    evidence = raw.get("evidence")
    if (
        raw.get("schema") != "qikvrt_review_admission_scan_quarantine_v1"
        or not isinstance(evidence, Mapping)
        or evidence.get("result") != "INCOMPLETE_NOT_ABSENCE"
        or raw.get("authority_state") != "HOLD"
        or raw.get("continuation_strategy")
            != "EXACT_SOURCE_RUN_ID_EVENT_OR_AUTHORITY_SUPPLIED_ID"
        or raw.get("absence_authorized") is not False
        or raw.get("authority_boundary") != "RECOVERY_ONLY"
        or raw.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("admission quarantine boundary differs")
    _digest(raw.get("prior_chain_sha256"), "admission quarantine prior chain")
    chain = _digest(
        raw.get("quarantine_chain_sha256"), "admission quarantine chain"
    )
    _positive(raw.get("quarantined_window_count"), "quarantine count")
    if chain != _canonical_sha256({
        "prior": raw["prior_chain_sha256"], "evidence": dict(evidence)
    }):
        raise AdmissionRecoveryError("admission quarantine chain differs")
    return dict(value)


def admission_scan_quarantine_path(record: Mapping[str, Any]) -> str:
    exact = validate_admission_scan_quarantine_record(record)
    digest = exact["record_sha256"]
    return (
        ".qikvrt/recovery/admission-source-rerun/quarantine/"
        f"{digest[:2]}/{digest}.json"
    )


def advance_admission_scan_cursor(
    cursor: Mapping[str, Any], *, declared_total: int,
    observed_run_ids: Sequence[int],
    next_upper_created_at: str | None = None,
) -> dict[str, Any]:
    """Advance one immutable, count-consistent workflow-run inventory page.

    GitHub's filtered runs endpoint supplies a declared total for the sealed
    creation window.  A short/shifted page, total drift, or a duplicate ID is
    not evidence that the remainder is absent: reset this target inventory to
    page one and retry it in a later recovery tick.  The cursor advances to a
    different target/window only after the ordered unique inventory count is
    exactly the declared total.
    """
    current = validate_admission_scan_cursor(cursor)
    ids = list(observed_run_ids) if isinstance(observed_run_ids, Sequence) else []
    if (
        isinstance(observed_run_ids, (str, bytes, bytearray))
        or len(ids) > current["page_size"]
        or any(
            isinstance(run_id, bool)
            or not isinstance(run_id, int)
            or run_id < 1
            for run_id in ids
        )
        or isinstance(declared_total, bool)
        or not isinstance(declared_total, int)
        or declared_total < 0
        or declared_total >= current["filtered_result_cap"]
    ):
        raise AdmissionRecoveryError("admission scan page inventory is malformed")
    if current["window_upper_created_at"] is None:
        raise AdmissionRecoveryError("admission scan window is not sealed")

    prior_total = current["target_declared_total"]
    prior_ids = list(current["target_run_ids"])
    expected_before = (current["page"] - 1) * current["page_size"]
    expected_page_count = min(
        current["page_size"], max(0, declared_total - expected_before)
    )
    drifted = (
        (prior_total is not None and prior_total != declared_total)
        or len(prior_ids) != expected_before
        or len(ids) != expected_page_count
        or len(set(ids)) != len(ids)
        or bool(set(prior_ids).intersection(ids))
        or ids != sorted(ids, reverse=True)
        or (bool(prior_ids) and bool(ids) and prior_ids[-1] <= ids[0])
    )
    if drifted:
        # This is a durable restart, never a negative observation.  It also
        # prevents processing bytes from a page that was not part of one
        # count-consistent ordered inventory.
        result = dict(current)
        result["page"] = 1
        result["target_declared_total"] = None
        result["target_run_ids"] = []
        result["target_run_ids_sha256"] = _canonical_sha256([])
        result["inventory_restart_count"] += 1
        return validate_admission_scan_cursor(result)

    inventory = prior_ids + ids
    if len(inventory) > declared_total:
        raise AdmissionRecoveryError("admission scan inventory exceeds declared total")
    result = dict(current)
    result["target_declared_total"] = declared_total
    result["target_run_ids"] = inventory
    result["target_run_ids_sha256"] = _canonical_sha256(inventory)
    if len(inventory) < declared_total:
        result["page"] += 1
    else:
        result["last_completed_inventory"] = {
            "target_index": current["target_index"],
            "generation": current["generation"],
            "lower_created_at": current["window_lower_created_at"],
            "upper_created_at": current["window_upper_created_at"],
            "declared_total": declared_total,
            "ordered_run_ids_sha256": _canonical_sha256(inventory),
        }
        result["page"] = 1
        result["target_declared_total"] = None
        result["target_run_ids"] = []
        result["target_run_ids_sha256"] = _canonical_sha256([])
        if result["target_index"] == 0:
            result["target_index"] = 1
        else:
            result["target_index"] = 0
            deferred = list(result["deferred_windows"])
            if deferred:
                window = deferred.pop()
                result["window_lower_created_at"] = window["lower_created_at"]
                result["window_upper_created_at"] = window["upper_created_at"]
                result["deferred_windows"] = deferred
            elif result["window_lower_created_at"] == result["repository_created_at"]:
                upper = _timestamp(
                    next_upper_created_at,
                    "next admission scan upper creation bound",
                )
                rebound = empty_admission_scan_cursor()
                rebound["generation"] = result["generation"] + 1
                return bind_admission_scan_window(
                    rebound,
                    upper_created_at=upper,
                    repository_created_at=result["repository_created_at"],
                )
            else:
                upper_text = result["window_lower_created_at"]
                upper_dt = datetime.fromisoformat(
                    upper_text.replace("Z", "+00:00")
                )
                floor_dt = datetime.fromisoformat(
                    result["repository_created_at"].replace("Z", "+00:00")
                )
                lower_dt = max(
                    floor_dt,
                    upper_dt - timedelta(
                        seconds=result["default_window_seconds"]
                    ),
                )
                result["window_upper_created_at"] = upper_text
                result["window_lower_created_at"] = lower_dt.isoformat().replace(
                    "+00:00", "Z"
                )
    return validate_admission_scan_cursor(result)


def _admission_wakeup_origin_from_projection(
    record: Mapping[str, Any], source: Mapping[str, Any], *, ledger_head: str
) -> dict[str, Any]:
    """Bind one requested child to its immutable human-review wake-up ACK.

    The ACK is the transport authority for attempt 1.  A later technical
    same-run rerun may use this record only to recover that exact child; it
    never carries review authority or successor evidence.
    """
    exact_record = validate_review_wakeup_record(record)
    exact_head = _sha(ledger_head, "review wake-up ledger head")
    ack = exact_record.get("ack")
    if ack is None or exact_record.get("terminal") is not None:
        raise AdmissionRecoveryError(
            "admission requested child has no exact wake-up ACK"
        )
    proof = ack.get("child_proof") if isinstance(ack, Mapping) else None
    child = proof.get("child") if isinstance(proof, Mapping) else None
    if not isinstance(child, Mapping):
        raise AdmissionRecoveryError(
            "admission requested child wake-up proof is malformed"
        )
    immutable = {
        "run_id": "run_id",
        "run_attempt": "run_attempt",
        "workflow_id": "workflow_id",
        "workflow_path": "workflow_path",
        "repository": "repository",
        "repository_id": "repository_id",
        "event": "event",
        "head_branch": "head_branch",
        "head_sha": "head_sha",
        "display_title": "display_title",
    }
    if (
        source.get("run_attempt") != 1
        or source.get("event") != "workflow_dispatch"
        or any(source.get(field) != child.get(child_field)
               for field, child_field in immutable.items())
        or source.get("display_title")
        != review_wakeup_child_title(
            exact_record["intent"],
            transport_attempt=ack["transport_attempt"],
        )
        or proof.get("transport_ack_observed") is not True
    ):
        raise AdmissionRecoveryError(
            "admission requested child differs from wake-up ACK"
        )
    value = {
        "schema": "qikvrt_review_admission_wakeup_origin_v1",
        "kind": "HUMAN_REVIEW_WAKEUP_ACK",
        "ledger_ref": "refs/heads/qikvrt/review-wakeup-ledger-v1",
        "ledger_head": exact_head,
        "record_path": exact_record["record_path"],
        "record_sha256": exact_record["record_sha256"],
        "ack_sha256": ack["ack_sha256"],
        "intent_sha256": exact_record["intent"]["intent_sha256"],
        "fact_fingerprint": exact_record["fact_fingerprint"],
        "transport_attempt": ack["transport_attempt"],
        "child_run_id": child["run_id"],
        "child_run_attempt": child["run_attempt"],
        "record": exact_record,
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["origin_sha256"] = _canonical_sha256(value)
    return value


def build_admission_wakeup_origin(
    record: Mapping[str, Any], run: Mapping[str, Any], *, ledger_head: str
) -> dict[str, Any]:
    candidate = dict(run)
    candidate.setdefault("jobs_total", 0)
    candidate.setdefault("artifacts_total", 0)
    source = _projection(candidate)
    source.pop("jobs_total", None)
    source.pop("artifacts_total", None)
    return _admission_wakeup_origin_from_projection(
        record, source, ledger_head=ledger_head
    )


def validate_admission_wakeup_origin(
    value: Mapping[str, Any], *, source: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission wake-up origin is malformed")
    expected = _admission_wakeup_origin_from_projection(
        value.get("record"), source, ledger_head=value.get("ledger_head")
    )
    if dict(value) != expected:
        raise AdmissionRecoveryError("admission wake-up origin differs")
    return dict(value)


def _requested_v3_locator(title: Any) -> dict[str, Any] | None:
    if not isinstance(title, str):
        return None
    match = re.fullmatch(
        r"qikvrt-rr-v3 e=([0-9a-f]{40}) p=([1-9][0-9]*) "
        r"h=([0-9a-f]{40}) f=([0-9a-f]{64}) "
        r"i=([0-9a-f]{64}) a=(1)",
        title,
    )
    if match is None:
        return None
    evaluator, pr, head, semantic, intent, attempt = match.groups()
    return {
        "evaluator_sha": evaluator,
        "pr_number": int(pr),
        "head_sha": head,
        "semantic_fingerprint": semantic,
        "intent_fingerprint": intent,
        "transport_attempt": int(attempt),
    }


def build_exact_review_core_origin(
    core_lookup: Mapping[str, Any],
    run: Mapping[str, Any],
    *,
    jobs_total: int,
    artifacts_total: int,
) -> dict[str, Any]:
    """Bind one zero-job child to its already accepted shared-Core sequence."""
    value = build_shared_review_core_origin(
        core_lookup, run, jobs_total=jobs_total, artifacts_total=artifacts_total
    )
    if value["lane"] != "exact-review-dispatch":
        raise AdmissionRecoveryError("exact-review Core lane differs")
    return value


def build_shared_review_core_origin(
    core_lookup: Mapping[str, Any],
    run: Mapping[str, Any],
    *,
    jobs_total: int,
    artifacts_total: int,
) -> dict[str, Any]:
    """Bind a zero-job Requested child to one accepted review-Core sequence."""
    from tools.qikvrt_ruleset_outbox import (
        _validate_intent_record,
        digest as core_digest,
        validate_acceptance_record,
        validate_transport_record,
    )

    if not isinstance(core_lookup, Mapping):
        raise AdmissionRecoveryError("exact-review Core lookup is malformed")
    lookup = dict(core_lookup)
    lane = lookup.get("lane")
    if (
        lookup.get("schema") != "qikvrt_ruleset_outbox_next_v1"
        or lane not in {
            "exact-review-dispatch",
            "mesh-review-successor-dispatch",
        }
        or lookup.get("state") != "PENDING"
        or lookup.get("lookup_state") not in {None, "PENDING"}
    ):
        raise AdmissionRecoveryError("shared review Core item is not pending")
    sequence = _positive(lookup.get("sequence"), "shared review Core sequence")
    fingerprint = _digest(
        lookup.get("fingerprint"), "shared review Core fingerprint"
    )
    intent = _validate_intent_record(
        lookup.get("intent"), lane=lane
    )
    if (
        intent.get("sequence") != sequence
        or intent.get("fingerprint") != fingerprint
    ):
        raise AdmissionRecoveryError("shared review Core intent differs")
    locator = _requested_v3_locator(run.get("display_title"))
    if locator is None or locator["intent_fingerprint"] != fingerprint:
        raise AdmissionRecoveryError("source run lacks shared review Core locator")
    attempt = locator["transport_attempt"]
    transports = lookup.get("transport")
    acceptances = lookup.get("acceptance")
    witnesses = lookup.get("witnesses")
    if (
        not isinstance(transports, Mapping)
        or not isinstance(acceptances, Mapping)
        or not isinstance(witnesses, Sequence)
        or isinstance(witnesses, (str, bytes))
    ):
        raise AdmissionRecoveryError("exact-review Core transport is malformed")
    retry_scan_cursors = lookup.get("retry_scan_cursor")
    if not isinstance(retry_scan_cursors, Mapping):
        raise AdmissionRecoveryError(
            "shared review Core retry-scan cursor map is malformed"
        )
    attempt_one_transport = validate_transport_record(
        transports.get("1"),
        intent=intent,
        attempt=1,
        witnesses=witnesses,
    )
    if attempt != 1:
        raise AdmissionRecoveryError(
            "shared review Core new-run transport is not attempt one"
        )
    transport_chain = {"1": attempt_one_transport}
    retry_scan_cursor_chain: dict[str, Any] = {}
    transport = attempt_one_transport
    acceptance = validate_acceptance_record(
        acceptances.get(str(attempt)),
        intent=intent,
        transport=transport,
        attempt=attempt,
    )
    source_input = dict(run)
    source_input["jobs_total"] = jobs_total
    source_input["artifacts_total"] = artifacts_total
    source = _projection(source_input)
    child = acceptance["child"]
    current_child = {
        "run_id": source["run_id"],
        "run_attempt": source["run_attempt"],
        "workflow_id": source["workflow_id"],
        "workflow_path": source["workflow_path"],
        "event": source["event"],
        "repository": source["repository"],
        "head_sha": source["head_sha"],
        "status": source["status"],
        "conclusion": source["conclusion"],
        "display_title": source["display_title"],
    }
    immutable_child_fields = (
        "run_id",
        "run_attempt",
        "workflow_id",
        "workflow_path",
        "event",
        "repository",
        "head_sha",
        "display_title",
    )
    accepted_child_identity = {
        field: child.get(field) for field in immutable_child_fields
    }
    current_child_identity = {
        field: current_child.get(field) for field in immutable_child_fields
    }
    meta = lookup.get("meta")
    request = intent.get("payload", {}).get("request", {})
    inputs = request.get("inputs") if isinstance(request, Mapping) else None
    if (
        current_child_identity != accepted_child_identity
        or child.get("status")
        not in {"queued", "in_progress", "waiting", "pending"}
        or child.get("conclusion") is not None
        or source["run_attempt"] != 1
        or source["status"] != "completed"
        or source["conclusion"] not in {"cancelled", "action_required"}
        or jobs_total != 0
        or artifacts_total != 0
        or acceptance.get("child_sha256") != core_digest(child)
        or not isinstance(meta, Mapping)
        or meta.get("drain_seq") != sequence
        or not isinstance(inputs, Mapping)
        or inputs.get("transport_intent_sha256") != fingerprint
        or inputs.get("transport_attempt") != "1"
        or inputs.get("evaluator_sha") != locator["evaluator_sha"]
        or inputs.get("head") != locator["head_sha"]
        or inputs.get("pr") != str(locator["pr_number"])
        or inputs.get("fingerprint") != locator["semantic_fingerprint"]
    ):
        raise AdmissionRecoveryError(
            "zero-job source differs from accepted shared review Core child"
        )
    recovery = lookup.get("child_recovery")
    completions = lookup.get("completion")
    if (
        isinstance(recovery, Mapping)
        and recovery.get(str(attempt)) is not None
    ) or (
        isinstance(completions, Mapping)
        and completions.get(str(attempt)) is not None
    ):
        raise AdmissionRecoveryError(
            "shared review Core child already has recovery or completion evidence"
        )
    sealed_source = dict(source)
    sealed_source.pop("jobs_total", None)
    sealed_source.pop("artifacts_total", None)
    value = {
        "schema": "qikvrt_review_admission_shared_review_core_origin_v1",
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "transport_attempt": attempt,
        "ledger_ref": lookup.get("ledger_ref"),
        "ledger_head": lookup.get("ledger_head"),
        "intent": intent,
        "intent_sha256": core_digest(intent),
        "witnesses": [dict(item) for item in witnesses],
        "transport": transport,
        "transport_sha256": core_digest(transport),
        "transport_chain": transport_chain,
        "retry_scan_cursor_chain": retry_scan_cursor_chain,
        "acceptance": acceptance,
        "acceptance_sha256": core_digest(acceptance),
        "accepted_child_sha256": acceptance["child_sha256"],
        "source": sealed_source,
        "same_run_recovery_required": source["conclusion"] == "cancelled",
        "terminal_hold_required": source["conclusion"] == "action_required",
        "terminal_first_blocker": (
            "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
            if source["conclusion"] == "action_required"
            else None
        ),
        "competing_recovery_authority": False,
        "authority_boundary": "SHARED_CORE_REVIEW_ONLY",
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    if (
        value["ledger_ref"]
        != f"refs/heads/qikvrt/outbox-ledger-v2/{lane}"
    ):
        raise AdmissionRecoveryError("shared review Core ref differs")
    _sha(value["ledger_head"], "shared review Core ledger head")
    value["origin_sha256"] = _canonical_sha256(value)
    return value


def validate_exact_review_core_origin(
    value: Mapping[str, Any], *, source: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    exact = validate_shared_review_core_origin(value, source=source)
    if exact["lane"] != "exact-review-dispatch":
        raise AdmissionRecoveryError("exact-review Core lane differs")
    return exact


def validate_shared_review_core_origin(
    value: Mapping[str, Any], *, source: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("exact-review Core origin is malformed")
    observed = dict(value)
    claimed = observed.pop("origin_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("exact-review Core origin digest differs")
    run = observed.get("source")
    if not isinstance(run, Mapping):
        raise AdmissionRecoveryError("exact-review Core source is malformed")
    raw_run = {
        "id": run.get("run_id"),
        "run_attempt": run.get("run_attempt"),
        "workflow_id": run.get("workflow_id"),
        "path": run.get("workflow_path"),
        "repository": {
            "id": run.get("repository_id"),
            "full_name": run.get("repository"),
        },
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "display_title": run.get("display_title"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "created_at": run.get("created_at"),
        "pull_requests": run.get("pull_requests"),
    }
    rebuilt = build_shared_review_core_origin(
        {
            "schema": "qikvrt_ruleset_outbox_next_v1",
            "state": "PENDING",
            "lookup_state": "PENDING",
            "lane": observed.get("lane"),
            "sequence": observed.get("sequence"),
            "fingerprint": observed.get("fingerprint"),
            "intent": observed.get("intent"),
            "witnesses": observed.get("witnesses"),
            "transport": observed.get("transport_chain"),
            "acceptance": {
                str(observed.get("transport_attempt")): observed.get("acceptance")
            },
            "meta": {
                "drain_seq": observed.get("sequence"),
            },
            "ledger_ref": observed.get("ledger_ref"),
            "ledger_head": observed.get("ledger_head"),
            "child_recovery": {},
            "completion": {},
            "retry_scan_cursor": observed.get("retry_scan_cursor_chain"),
        },
        raw_run,
        jobs_total=0,
        artifacts_total=0,
    )
    compared_source = None
    if source is not None:
        compared_source = dict(source)
        compared_source.pop("jobs_total", None)
        compared_source.pop("artifacts_total", None)
    if dict(value) != rebuilt or (
        compared_source is not None and compared_source != run
    ):
        raise AdmissionRecoveryError("exact-review Core origin differs")
    return dict(value)


def build_exact_review_core_retry_evidence(
    origin: Mapping[str, Any], *, source: Mapping[str, Any]
) -> dict[str, Any]:
    exact = validate_exact_review_core_origin(origin, source=source)
    return build_shared_review_core_retry_evidence(exact, source=source)


def build_shared_review_core_retry_evidence(
    origin: Mapping[str, Any], *, source: Mapping[str, Any]
) -> dict[str, Any]:
    exact = validate_shared_review_core_origin(origin, source=source)
    if (
        exact.get("same_run_recovery_required") is not True
        or exact.get("terminal_hold_required") is not False
        or exact["source"].get("conclusion") != "cancelled"
    ):
        raise AdmissionRecoveryError(
            "shared review Core result does not authorize a same-run rerun"
        )
    run = exact["source"]
    observed_terminal_child = {
        "run_id": run["run_id"],
        "run_attempt": run["run_attempt"],
        "workflow_id": run["workflow_id"],
        "workflow_path": run["workflow_path"],
        "event": run["event"],
        "repository": run["repository"],
        "head_sha": run["head_sha"],
        "status": run["status"],
        "conclusion": run["conclusion"],
        "display_title": run["display_title"],
    }
    from tools.qikvrt_ruleset_outbox import digest as core_digest

    return {
        "schema": "qikvrt_ruleset_outbox_child_retry_evidence_v3",
        "lane": exact["lane"],
        "sequence": exact["sequence"],
        "fingerprint": exact["fingerprint"],
        "transport_attempt": 1,
        "classification": "ZERO_JOB_CONCURRENCY_CANCELLED",
        "first_blocker": "ATTEMPT_1_ZERO_JOB_CONCURRENCY_CANCELLED",
        "accepted_child_sha256": exact["accepted_child_sha256"],
        "observed_terminal_child": observed_terminal_child,
        "observed_terminal_child_sha256": core_digest(observed_terminal_child),
        "jobs_total_count": 0,
        "verified": True,
        "productive_effect": False,
    }


def build_shared_review_core_child_rerun_absence_observation(
    origin: Mapping[str, Any],
    preparation: Mapping[str, Any],
    *,
    target_run: Mapping[str, Any],
    target_jobs_total: int,
    target_artifacts_total: int,
    preparation_actor_run: Mapping[str, Any],
    observation_started_at: str,
    observation_completed_at: str,
) -> dict[str, Any]:
    """Seal a post-actor exact observation that same-run attempt two is absent."""
    from tools.qikvrt_ruleset_outbox import (
        CHILD_RERUN_OBSERVATION_SCHEMA,
        TERMINAL_RUN_CONCLUSIONS,
        digest as core_digest,
    )

    exact = validate_shared_review_core_origin(origin)
    prepared = validate_shared_review_core_rerun_preparation(
        preparation, origin=exact
    )
    if prepared.get("transport_attempt") != 1:
        raise AdmissionRecoveryError(
            "shared review Core child-rerun preparation attempt differs"
        )
    source_input = dict(target_run)
    source_input["jobs_total"] = target_jobs_total
    source_input["artifacts_total"] = target_artifacts_total
    observed = _projection(source_input)
    target = {
        "run_id": observed["run_id"],
        "run_attempt": observed["run_attempt"],
        "workflow_id": observed["workflow_id"],
        "workflow_path": observed["workflow_path"],
        "event": observed["event"],
        "repository": observed["repository"],
        "head_sha": observed["head_sha"],
        "status": observed["status"],
        "conclusion": observed["conclusion"],
        "display_title": observed["display_title"],
    }
    retry = prepared.get("retry_evidence")
    stored_target = (
        retry.get("observed_terminal_child")
        if isinstance(retry, Mapping)
        else None
    )
    actor_repository = preparation_actor_run.get("repository")
    actor = {
        "run_id": preparation_actor_run.get(
            "id", preparation_actor_run.get("run_id")
        ),
        "run_attempt": preparation_actor_run.get("run_attempt"),
        "status": preparation_actor_run.get("status"),
        "conclusion": preparation_actor_run.get("conclusion"),
        "created_at": preparation_actor_run.get("created_at"),
        "updated_at": preparation_actor_run.get("updated_at"),
    }
    actor_started = _timestamp(
        actor["created_at"], "child-rerun preparation actor creation"
    )
    actor_terminal = _timestamp(
        actor["updated_at"], "child-rerun preparation actor terminal time"
    )
    observation_start = _timestamp(
        observation_started_at, "child-rerun absence observation start"
    )
    observation_end = _timestamp(
        observation_completed_at, "child-rerun absence observation end"
    )
    if (
        target != stored_target
        or target_jobs_total != 0
        or target_artifacts_total != 0
        or target["run_attempt"] != 1
        or target["status"] != "completed"
        or target["conclusion"] != "cancelled"
        or actor["run_id"] != prepared.get("actor_run_id")
        or actor["run_attempt"] != prepared.get("actor_run_attempt")
        or actor["status"] != "completed"
        or actor["conclusion"] not in TERMINAL_RUN_CONCLUSIONS
        or actor_started > actor_terminal
        or observation_start <= actor_terminal
        or observation_start > observation_end
        or (
            isinstance(actor_repository, Mapping)
            and actor_repository.get("full_name") not in {None, target["repository"]}
        )
    ):
        raise AdmissionRecoveryError(
            "shared review Core child-rerun absence observation differs"
        )
    value = {
        "schema": CHILD_RERUN_OBSERVATION_SCHEMA,
        "blocker": "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
        "lane": exact["lane"],
        "sequence": exact["sequence"],
        "fingerprint": exact["fingerprint"],
        "transport_attempt": 1,
        "target_run_id": target["run_id"],
        "target_run_attempt": 2,
        "target_attempt_one_child": target,
        "target_attempt_one_child_sha256": core_digest(target),
        "preparation_actor": actor,
        "preparation_actor_sha256": core_digest(actor),
        "query_window_start": actor_started,
        "query_window_end": observation_start,
        "observation_started_at": observation_start,
        "observation_completed_at": observation_end,
        "observed_run_attempt": 1,
        "scan_complete": True,
        "successor_present": False,
        "verified": True,
        "productive_effect": False,
    }
    return value


def build_shared_review_core_action_required_observation(
    origin: Mapping[str, Any],
    *,
    target_run: Mapping[str, Any],
    target_jobs_total: int,
    target_artifacts_total: int,
    admission_receipt: Mapping[str, Any],
    current_main_sha: str,
    live_subject: Mapping[str, Any],
    observation_started_at: str,
    observation_completed_at: str,
) -> dict[str, Any]:
    """Bind exact accepted attempt-one ``action_required`` as a Core HOLD.

    ``action_required`` is a terminal first result, not a concurrency retry
    signal.  The observation therefore authorizes no same-run attempt two.  It
    reopens the accepted child, the local Admission D0=3 receipt, the current
    main/PR subject, and a complete zero-job/zero-artifact inventory before the
    Shared-Core sequence may be terminalized.
    """
    from tools.qikvrt_ruleset_outbox import (
        AUTHORITY_OBSERVATION_SCHEMA,
        digest as core_digest,
    )

    exact = validate_shared_review_core_origin(origin)
    if (
        exact.get("same_run_recovery_required") is not False
        or exact.get("terminal_hold_required") is not True
        or exact.get("terminal_first_blocker")
        != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
    ):
        raise AdmissionRecoveryError(
            "shared review Core source is not an action-required HOLD"
        )
    if any(
        isinstance(total, bool) or not isinstance(total, int) or total != 0
        for total in (target_jobs_total, target_artifacts_total)
    ):
        raise AdmissionRecoveryError(
            "shared review Core action-required inventory differs"
        )
    candidate = dict(target_run)
    candidate["jobs_total"] = target_jobs_total
    candidate["artifacts_total"] = target_artifacts_total
    observed_source = _projection(candidate)
    if observed_source != {
        **exact["source"],
        "jobs_total": 0,
        "artifacts_total": 0,
    }:
        raise AdmissionRecoveryError(
            "shared review Core action-required source differs"
        )
    receipt = validate_terminal_receipt(admission_receipt)
    if (
        receipt.get("state") != "ACTION_REQUIRED_D0_3"
        or receipt.get("first_blocker")
        != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
        or receipt.get("source") != observed_source
    ):
        raise AdmissionRecoveryError(
            "shared review Core action-required Admission receipt differs"
        )
    main_sha = _sha(current_main_sha, "action-required observed main")
    payload = exact.get("intent", {}).get("payload")
    request = payload.get("request") if isinstance(payload, Mapping) else None
    inputs = request.get("inputs") if isinstance(request, Mapping) else None
    sealed_subject = (
        payload.get("subject") if isinstance(payload, Mapping) else None
    )
    subject = _live_subject(live_subject)
    locator = _requested_v3_locator(observed_source.get("display_title"))
    if (
        not isinstance(inputs, Mapping)
        or not isinstance(sealed_subject, Mapping)
        or locator is None
        or inputs.get("pr") != str(subject["pr_number"])
        or inputs.get("head") != subject["head_sha"]
        or inputs.get("evaluator_sha") != main_sha
        or locator["pr_number"] != subject["pr_number"]
        or locator["head_sha"] != subject["head_sha"]
        or subject["base_sha"] != main_sha
        or subject["base_repository"] != observed_source["repository"]
        or subject["head_repository"] != observed_source["repository"]
        or exact["intent"].get("payload", {}).get("main_head_sha")
        != main_sha
        or observed_source["head_sha"] != main_sha
    ):
        raise AdmissionRecoveryError(
            "shared review Core action-required live subject differs"
        )
    if exact["lane"] == "exact-review-dispatch":
        observed_subject = {
            "pull_request": subject["pr_number"],
            "head_repository": subject["head_repository"],
            "head_ref": subject["head_ref"],
            "head_sha": subject["head_sha"],
            "head_tree_sha": subject["head_tree_sha"],
            "base_ref": subject["base_ref"],
            "base_sha": subject["base_sha"],
        }
        if observed_subject != dict(sealed_subject):
            raise AdmissionRecoveryError(
                "exact-review Core action-required subject projection differs"
            )
    else:
        queue = sealed_subject.get("queue_intent")
        if (
            sealed_subject.get("schema")
            != "qikvrt_mesh_review_successor_subject_v1"
            or not isinstance(queue, Mapping)
            or queue.get("pr_number") != subject["pr_number"]
            or queue.get("head_sha") != subject["head_sha"]
            or queue.get("tree_sha") != subject["head_tree_sha"]
            or queue.get("base_sha") != subject["base_sha"]
            or sealed_subject.get("productive_effect") is not False
        ):
            raise AdmissionRecoveryError(
                "mesh review Core action-required subject projection differs"
            )
        # The queue subject is itself content-addressed by Core.  Its complete
        # bytes are carried after all PR/head/tree/base locators above have
        # been independently reobserved from the API.
        observed_subject = dict(sealed_subject)
    started = _timestamp(
        observation_started_at, "action-required observation start"
    )
    completed = _timestamp(
        observation_completed_at, "action-required observation end"
    )
    created = _timestamp(
        observed_source.get("created_at"), "action-required child creation"
    )
    updated = _timestamp(
        target_run.get("updated_at"), "action-required child update"
    )
    if created > updated or started > completed or updated > completed:
        raise AdmissionRecoveryError(
            "shared review Core action-required observation time differs"
        )
    observed_child = {
        "run_id": observed_source["run_id"],
        "run_attempt": observed_source["run_attempt"],
        "workflow_id": observed_source["workflow_id"],
        "workflow_path": observed_source["workflow_path"],
        "event": observed_source["event"],
        "repository": observed_source["repository"],
        "head_sha": observed_source["head_sha"],
        "status": observed_source["status"],
        "conclusion": observed_source["conclusion"],
        "display_title": observed_source["display_title"],
    }
    value = {
        "schema": AUTHORITY_OBSERVATION_SCHEMA,
        "blocker": "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
        "lane": exact["lane"],
        "sequence": exact["sequence"],
        "fingerprint": exact["fingerprint"],
        "transport_attempt": 1,
        "intent_sha256": exact["intent_sha256"],
        "acceptance_sha256": exact["acceptance_sha256"],
        "accepted_child_sha256": exact["accepted_child_sha256"],
        "observed_child": observed_child,
        "observed_child_sha256": core_digest(observed_child),
        "jobs_total_count": 0,
        "jobs_set_sha256": core_digest([]),
        "jobs_pages_scanned": 1,
        "jobs_page_cap": 100,
        "jobs_scan_complete": True,
        "admission_receipt": receipt,
        "admission_receipt_sha256": core_digest(receipt),
        "sealed_main_head_sha": main_sha,
        "observed_main_head_sha": main_sha,
        "sealed_subject_sha256": core_digest(dict(sealed_subject)),
        "observed_subject": observed_subject,
        "observed_subject_sha256": core_digest(observed_subject),
        "observation_started_at": started,
        "observation_completed_at": completed,
        "verified": True,
        "productive_effect": False,
    }
    return value


def build_shared_review_core_action_required_terminal_evidence(
    origin: Mapping[str, Any],
    observation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the persisted action-required observation to Core D0=3."""
    from tools.qikvrt_ruleset_outbox import (
        AUTHORITY_OBSERVATION_RECEIPT_SCHEMA,
        EXHAUSTION_SCHEMA,
        TERMINAL_EVIDENCE_SCHEMA,
        authority_observation_path,
        digest as core_digest,
        empty_completion_claims,
        validate_authority_observation_record,
    )

    exact = validate_shared_review_core_origin(origin)
    if not isinstance(observation_receipt, Mapping):
        raise AdmissionRecoveryError(
            "shared review Core action-required observation receipt is malformed"
        )
    receipt = dict(observation_receipt)
    record = validate_authority_observation_record(
        receipt.get("record"), intent=exact["intent"]
    )
    record_sha = core_digest(record)
    observation = record["observation"]
    ledger_head = receipt.get("ledger_head")
    if (
        set(receipt)
        != {
            "schema", "state", "record", "record_sha256", "record_path",
            "ledger_ref", "ledger_head", "cas", "productive_effect",
        }
        or receipt.get("schema") != AUTHORITY_OBSERVATION_RECEIPT_SCHEMA
        or receipt.get("state") != "IMMUTABLE_API_OBSERVATION_PERSISTED"
        or receipt.get("record_sha256") != record_sha
        or receipt.get("record_path") != authority_observation_path(
            exact["lane"], exact["sequence"], record_sha
        )
        or receipt.get("ledger_ref") != exact["ledger_ref"]
        or receipt.get("productive_effect") is not False
        or record.get("blocker") != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
        or observation.get("observed_child", {}).get("run_id")
        != exact["source"]["run_id"]
        or observation.get("transport_attempt") != 1
    ):
        raise AdmissionRecoveryError(
            "shared review Core action-required observation receipt differs"
        )
    _validate_shared_core_cas(receipt.get("cas"), ledger_head=ledger_head)
    return {
        "schema": TERMINAL_EVIDENCE_SCHEMA,
        "completion_claims": empty_completion_claims(),
        "d0": 3,
        "state": "REQUEST_AUTHORITY",
        "reason": "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
        "exhaustion": {
            "schema": EXHAUSTION_SCHEMA,
            "lane": exact["lane"],
            "sequence": exact["sequence"],
            "fingerprint": exact["fingerprint"],
            "mode": "AMBIGUOUS_OR_DRIFT",
            "attempts": [1],
            "first_blocker": "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
            "authority_observation_sha256": record_sha,
            "observation_sha256": core_digest(observation),
            "verified": True,
            "productive_effect": False,
        },
        "productive_effect": False,
    }


def validate_shared_review_core_action_required_terminal_readback(
    origin: Mapping[str, Any],
    admission_receipt: Mapping[str, Any],
    terminal_evidence: Mapping[str, Any],
    terminal_receipt: Mapping[str, Any],
    core_lookup: Mapping[str, Any],
) -> dict[str, Any]:
    """Require an Auditor-reopened action-required Core terminal fixed point."""
    from tools.qikvrt_ruleset_outbox import (
        TERMINAL_EVIDENCE_SCHEMA,
        TERMINAL_SCHEMA,
        digest as core_digest,
        validate_authority_observation_record,
    )

    exact = validate_shared_review_core_origin(origin)
    local_receipt = validate_terminal_receipt(admission_receipt)
    evidence = dict(terminal_evidence) if isinstance(
        terminal_evidence, Mapping
    ) else {}
    receipt = dict(terminal_receipt) if isinstance(
        terminal_receipt, Mapping
    ) else {}
    lookup = dict(core_lookup) if isinstance(core_lookup, Mapping) else {}
    stored = dict(lookup.get("terminal")) if isinstance(
        lookup.get("terminal"), Mapping
    ) else {}
    observation_record = validate_authority_observation_record(
        lookup.get("authority_observation"), intent=exact["intent"]
    )
    observation = observation_record["observation"]
    expected_terminal_keys = {
        "schema", "lane", "sequence", "fingerprint", "state", "d0",
        "evidence_sha256", "evidence", "productive_effect",
    }
    receipt_terminal = {
        key: receipt.get(key) for key in expected_terminal_keys
    }
    if (
        local_receipt.get("state") != "ACTION_REQUIRED_D0_3"
        or local_receipt.get("first_blocker")
        != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
        or evidence.get("schema") != TERMINAL_EVIDENCE_SCHEMA
        or evidence.get("d0") != 3
        or evidence.get("reason") != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
        or evidence.get("productive_effect") is not False
        or set(receipt)
        != expected_terminal_keys | {"ledger_ref", "ledger_head", "cas"}
        or receipt_terminal != stored
        or receipt.get("ledger_ref") != exact["ledger_ref"]
        or lookup.get("schema") != "qikvrt_ruleset_outbox_next_v1"
        or lookup.get("state") != "TERMINAL"
        or lookup.get("lookup_state") != "TERMINAL"
        or lookup.get("lane") != exact["lane"]
        or lookup.get("sequence") != exact["sequence"]
        or lookup.get("fingerprint") != exact["fingerprint"]
        or lookup.get("intent") != exact["intent"]
        or lookup.get("ledger_ref") != exact["ledger_ref"]
        or lookup.get("ledger_head") != receipt.get("ledger_head")
        or not isinstance(lookup.get("meta"), Mapping)
        or lookup["meta"].get("drain_seq", 0) <= exact["sequence"]
        or lookup.get("terminal_supersession") is not None
        or set(stored) != expected_terminal_keys
        or stored.get("schema") != TERMINAL_SCHEMA
        or stored.get("lane") != exact["lane"]
        or stored.get("sequence") != exact["sequence"]
        or stored.get("fingerprint") != exact["fingerprint"]
        or stored.get("state") != "TERMINAL"
        or stored.get("d0") != 3
        or stored.get("evidence") != evidence
        or stored.get("evidence_sha256") != core_digest(evidence)
        or stored.get("productive_effect") is not False
        or lookup.get("effective_d0") != 3
        or observation_record.get("blocker")
        != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
        or evidence.get("exhaustion", {}).get(
            "authority_observation_sha256"
        ) != core_digest(observation_record)
        or evidence.get("exhaustion", {}).get("observation_sha256")
        != core_digest(observation)
        or observation.get("admission_receipt") != local_receipt
        or observation.get("admission_receipt_sha256")
        != core_digest(local_receipt)
    ):
        raise AdmissionRecoveryError(
            "shared review Core action-required terminal readback differs"
        )
    _validate_shared_core_cas(
        receipt.get("cas"), ledger_head=receipt.get("ledger_head")
    )
    value = {
        "schema": (
            "qikvrt_review_admission_core_action_required_terminal_readback_v1"
        ),
        "lane": exact["lane"],
        "sequence": exact["sequence"],
        "fingerprint": exact["fingerprint"],
        "ledger_ref": exact["ledger_ref"],
        "ledger_head": lookup["ledger_head"],
        "terminal": stored,
        "terminal_sha256": core_digest(stored),
        "terminal_receipt_sha256": core_digest(receipt),
        "state": "TERMINAL_D0_3_DURABLY_REOBSERVED",
        "effect_ack": "ACTION_REQUIRED_HOLD_TERMINAL_REOBSERVED",
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "approval_authorized": False,
        "required_gate_success_authorized": False,
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["readback_sha256"] = _canonical_sha256(value)
    return value


def build_shared_review_core_child_rerun_terminal_evidence(
    origin: Mapping[str, Any],
    observation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one persisted no-A2 observation to the Core D0=3 terminal CAS."""
    from tools.qikvrt_ruleset_outbox import (
        AUTHORITY_OBSERVATION_RECEIPT_SCHEMA,
        EXHAUSTION_SCHEMA,
        TERMINAL_EVIDENCE_SCHEMA,
        authority_observation_path,
        digest as core_digest,
        empty_completion_claims,
        validate_authority_observation_record,
    )

    exact = validate_shared_review_core_origin(origin)
    if not isinstance(observation_receipt, Mapping):
        raise AdmissionRecoveryError(
            "shared review Core Authority observation receipt is malformed"
        )
    receipt = dict(observation_receipt)
    record = validate_authority_observation_record(
        receipt.get("record"), intent=exact["intent"]
    )
    record_sha = core_digest(record)
    observation = record["observation"]
    ledger_head = receipt.get("ledger_head")
    if (
        set(receipt)
        != {
            "schema", "state", "record", "record_sha256", "record_path",
            "ledger_ref", "ledger_head", "cas", "productive_effect",
        }
        or receipt.get("schema") != AUTHORITY_OBSERVATION_RECEIPT_SCHEMA
        or receipt.get("state") != "IMMUTABLE_API_OBSERVATION_PERSISTED"
        or receipt.get("record_sha256") != record_sha
        or receipt.get("record_path") != authority_observation_path(
            exact["lane"], exact["sequence"], record_sha
        )
        or receipt.get("ledger_ref") != exact["ledger_ref"]
        or receipt.get("productive_effect") is not False
        or record.get("blocker") != "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED"
        or observation.get("target_run_id") != exact["source"]["run_id"]
        or observation.get("target_run_attempt") != 2
    ):
        raise AdmissionRecoveryError(
            "shared review Core Authority observation receipt differs"
        )
    _validate_shared_core_cas(receipt.get("cas"), ledger_head=ledger_head)
    return {
        "schema": TERMINAL_EVIDENCE_SCHEMA,
        "completion_claims": empty_completion_claims(),
        "d0": 3,
        "state": "REQUEST_AUTHORITY",
        "reason": "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
        "exhaustion": {
            "schema": EXHAUSTION_SCHEMA,
            "lane": exact["lane"],
            "sequence": exact["sequence"],
            "fingerprint": exact["fingerprint"],
            "mode": "CHILD_RERUN_EXHAUSTED",
            "attempts": [1],
            "first_blocker": "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
            "transport_attempt": 1,
            "target_run_id": exact["source"]["run_id"],
            "target_run_attempt": 2,
            "successor": None,
            "successor_sha256": None,
            "authority_observation_sha256": record_sha,
            "observation_sha256": core_digest(observation),
            "verified": True,
            "productive_effect": False,
        },
        "productive_effect": False,
    }


def validate_shared_review_core_child_rerun_terminal_readback(
    origin: Mapping[str, Any],
    terminal_evidence: Mapping[str, Any],
    terminal_receipt: Mapping[str, Any],
    core_lookup: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the Core D0=3 CAS through an exact Auditor lookup.

    A writer command receipt alone is not durable evidence.  This validator
    requires the subsequently read historical terminal, its advanced FIFO
    cursor, and the exact evidence bytes that selected the immutable
    post-actor no-attempt-two observation.
    """
    from tools.qikvrt_ruleset_outbox import (
        TERMINAL_EVIDENCE_SCHEMA,
        TERMINAL_SCHEMA,
        digest as core_digest,
    )

    exact = validate_shared_review_core_origin(origin)
    evidence = dict(terminal_evidence) if isinstance(
        terminal_evidence, Mapping
    ) else {}
    receipt = dict(terminal_receipt) if isinstance(
        terminal_receipt, Mapping
    ) else {}
    lookup = dict(core_lookup) if isinstance(core_lookup, Mapping) else {}
    evidence_sha = core_digest(evidence)
    stored_terminal = lookup.get("terminal")
    stored = dict(stored_terminal) if isinstance(
        stored_terminal, Mapping
    ) else {}
    receipt_terminal = {
        key: receipt.get(key)
        for key in (
            "schema", "lane", "sequence", "fingerprint", "state", "d0",
            "evidence_sha256", "evidence", "productive_effect",
        )
    }
    expected_terminal_keys = {
        "schema", "lane", "sequence", "fingerprint", "state", "d0",
        "evidence_sha256", "evidence", "productive_effect",
    }
    if (
        evidence.get("schema") != TERMINAL_EVIDENCE_SCHEMA
        or evidence.get("d0") != 3
        or evidence.get("reason")
            != "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED"
        or evidence.get("productive_effect") is not False
        or set(receipt)
            != expected_terminal_keys | {"ledger_ref", "ledger_head", "cas"}
        or receipt_terminal != stored
        or receipt.get("ledger_ref") != exact["ledger_ref"]
        or lookup.get("schema") != "qikvrt_ruleset_outbox_next_v1"
        or lookup.get("state") != "TERMINAL"
        or lookup.get("lookup_state") != "TERMINAL"
        or lookup.get("lane") != exact["lane"]
        or lookup.get("sequence") != exact["sequence"]
        or lookup.get("fingerprint") != exact["fingerprint"]
        or lookup.get("intent") != exact["intent"]
        or lookup.get("ledger_ref") != exact["ledger_ref"]
        or lookup.get("ledger_head") != receipt.get("ledger_head")
        or not isinstance(lookup.get("meta"), Mapping)
        or lookup["meta"].get("drain_seq", 0) <= exact["sequence"]
        or set(stored) != expected_terminal_keys
        or stored.get("schema") != TERMINAL_SCHEMA
        or stored.get("lane") != exact["lane"]
        or stored.get("sequence") != exact["sequence"]
        or stored.get("fingerprint") != exact["fingerprint"]
        or stored.get("state") != "TERMINAL"
        or stored.get("d0") != 3
        or stored.get("evidence") != evidence
        or stored.get("evidence_sha256") != evidence_sha
        or stored.get("productive_effect") is not False
        or lookup.get("effective_d0") != 3
    ):
        raise AdmissionRecoveryError(
            "shared review Core child-rerun terminal readback differs"
        )
    _validate_shared_core_cas(
        receipt.get("cas"), ledger_head=receipt.get("ledger_head")
    )
    # Reopen and validate the immutable A1 acceptance plus child-rerun
    # preparation from the same terminal snapshot.  No local cache is a
    # substitute for the Shared-Core historical readback.
    recovery = reobserve_shared_review_core_child_recovery(
        lookup, origin=exact
    )
    if (
        recovery.get("state") != "PREPARED"
        or recovery.get("parent_state") != "TERMINAL"
        or recovery.get("acceptance") is not None
    ):
        raise AdmissionRecoveryError(
            "shared review Core terminal recovery chain differs"
        )
    value = {
        "schema": (
            "qikvrt_review_admission_core_child_rerun_terminal_readback_v1"
        ),
        "lane": exact["lane"],
        "sequence": exact["sequence"],
        "fingerprint": exact["fingerprint"],
        "ledger_ref": exact["ledger_ref"],
        "ledger_head": lookup["ledger_head"],
        "terminal": stored,
        "terminal_sha256": core_digest(stored),
        "terminal_receipt_sha256": core_digest(receipt),
        "state": "TERMINAL_D0_3_DURABLY_REOBSERVED",
        "effect_ack": "TRANSPORT_UNACKNOWLEDGED_TERMINAL_REOBSERVED",
        "authority_boundary": "RECOVERY_ONLY",
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["readback_sha256"] = _canonical_sha256(value)
    return value


def reobserve_shared_review_core_child_recovery(
    core_lookup: Mapping[str, Any], *, origin: Mapping[str, Any]
) -> dict[str, Any]:
    """Recover exact persisted Core rerun records without replaying a mutation."""
    exact = validate_shared_review_core_origin(origin)
    if not isinstance(core_lookup, Mapping):
        raise AdmissionRecoveryError("shared review Core recovery lookup is malformed")
    lookup = dict(core_lookup)
    if (
        lookup.get("schema") != "qikvrt_ruleset_outbox_next_v1"
        or lookup.get("state") not in {"PENDING", "TERMINAL"}
        or lookup.get("lane") != exact["lane"]
        or lookup.get("sequence") != exact["sequence"]
        or lookup.get("fingerprint") != exact["fingerprint"]
        or lookup.get("intent") != exact["intent"]
        or lookup.get("ledger_ref") != exact["ledger_ref"]
        or not isinstance(lookup.get("ledger_head"), str)
        or not isinstance(lookup.get("meta"), Mapping)
        or (
            lookup.get("state") == "PENDING"
            and lookup["meta"].get("drain_seq") != exact["sequence"]
        )
        or (
            lookup.get("state") == "TERMINAL"
            and lookup["meta"].get("drain_seq", 0) <= exact["sequence"]
        )
    ):
        raise AdmissionRecoveryError("shared review Core recovery lookup differs")
    _sha(lookup["ledger_head"], "shared review Core recovery lookup head")
    acceptances = lookup.get("acceptance")
    recovery = lookup.get("child_recovery")
    attempt = str(exact["transport_attempt"])
    if (
        not isinstance(acceptances, Mapping)
        or acceptances.get(attempt) != exact["acceptance"]
        or not isinstance(recovery, Mapping)
    ):
        raise AdmissionRecoveryError("shared review Core original acceptance differs")
    state = recovery.get(attempt)
    if state is None:
        return {
            "schema": "qikvrt_review_admission_core_recovery_readback_v1",
            "state": "NOT_PREPARED",
            "lane": exact["lane"],
            "sequence": exact["sequence"],
            "fingerprint": exact["fingerprint"],
            "transport_attempt": exact["transport_attempt"],
            "ledger_ref": exact["ledger_ref"],
            "ledger_head": lookup["ledger_head"],
            "parent_state": lookup["state"],
            "preparation": None,
            "acceptance": None,
            "productive_effect": False,
        }
    if not isinstance(state, Mapping) or not isinstance(state.get("rerun"), Mapping):
        raise AdmissionRecoveryError("shared review Core recovery state is malformed")

    def durable(raw: Mapping[str, Any], kind: str) -> dict[str, Any]:
        record = dict(raw)
        record["ledger_ref"] = exact["ledger_ref"]
        record["ledger_head"] = lookup["ledger_head"]
        record["durable_readback"] = {
            "schema": "qikvrt_review_admission_core_durable_readback_v1",
            "kind": kind,
            "lane": exact["lane"],
            "sequence": exact["sequence"],
            "fingerprint": exact["fingerprint"],
            "transport_attempt": exact["transport_attempt"],
            "ledger_ref": exact["ledger_ref"],
            "ledger_head": lookup["ledger_head"],
            "record_sha256": _canonical_sha256(raw),
            "verified": True,
            "productive_effect": False,
        }
        return record

    preparation = durable(state["rerun"], "CHILD_RERUN_PREPARATION")
    validate_shared_review_core_rerun_preparation(preparation, origin=exact)
    accepted = state.get("acceptance")
    acceptance = (
        durable(accepted, "CHILD_RERUN_ACCEPTANCE")
        if isinstance(accepted, Mapping) else None
    )
    if acceptance is not None:
        child = acceptance.get("child")
        # Convert the sealed normalized Core child back to the minimal REST
        # shape accepted by the local validator.
        validate_shared_review_core_rerun_acceptance(
            acceptance,
            origin=exact,
            child_run={
                "id": child.get("run_id") if isinstance(child, Mapping) else None,
                "run_attempt": child.get("run_attempt") if isinstance(child, Mapping) else None,
                "workflow_id": child.get("workflow_id") if isinstance(child, Mapping) else None,
                "path": child.get("workflow_path") if isinstance(child, Mapping) else None,
                "event": child.get("event") if isinstance(child, Mapping) else None,
                "repository": {
                    "full_name": child.get("repository")
                    if isinstance(child, Mapping) else None
                },
                "head_sha": child.get("head_sha") if isinstance(child, Mapping) else None,
                "status": child.get("status") if isinstance(child, Mapping) else None,
                "conclusion": child.get("conclusion") if isinstance(child, Mapping) else None,
                "display_title": child.get("display_title")
                if isinstance(child, Mapping) else None,
            },
        )
    return {
        "schema": "qikvrt_review_admission_core_recovery_readback_v1",
        "state": "ACCEPTED" if acceptance is not None else "PREPARED",
        "lane": exact["lane"],
        "sequence": exact["sequence"],
        "fingerprint": exact["fingerprint"],
        "transport_attempt": exact["transport_attempt"],
        "ledger_ref": exact["ledger_ref"],
        "ledger_head": lookup["ledger_head"],
        "parent_state": lookup["state"],
        "preparation": preparation,
        "acceptance": acceptance,
        "productive_effect": False,
    }


def build_delegated_signer_receipt_recovery_evidence(
    *,
    plan: Mapping[str, Any],
    run: Mapping[str, Any],
    repository: str,
    current_main_sha: str,
    pr: Mapping[str, Any],
    head_commit: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    jobs_total: int,
    artifacts_total: int,
    signer_receipt_blocker: str,
    artifact_inventory_sha256: str,
) -> dict[str, Any]:
    """Prove the technical COMMENT POST->crash state for one same-run rerun.

    ``TECHNICAL_CONTINUE`` is deliberately a non-approving COMMENT.  A marked
    historical APPROVED review is predecessor evidence only and can never
    authorize this recovery path.
    """
    from tools.qikvrt_native_account_review import (
        parse_delegated_review_locator,
        validate_plan,
    )

    exact_plan = validate_plan(plan)
    repo = _repository(repository, "signer recovery repository")
    evaluator = _sha(current_main_sha, "signer recovery evaluator")
    projection_input = dict(run)
    projection_input["jobs_total"] = jobs_total
    projection_input["artifacts_total"] = artifacts_total
    source = _projection(projection_input)
    if (
        source["workflow_path"]
        != ".github/workflows/qikvrt_required_review_gate.yml"
        or source["run_id"] != exact_plan.get("signer_run_id")
        or source["run_attempt"] != 1
        or exact_plan.get("signer_run_attempt") != 1
        or exact_plan.get("signer_evaluator_sha") != evaluator
        or source["head_sha"] != evaluator
        or source["head_branch"] != "main"
        or source["status"] != "completed"
        or not isinstance(source["conclusion"], str)
        or not source["conclusion"]
        or isinstance(jobs_total, bool)
        or not isinstance(jobs_total, int)
        or jobs_total < 1
        or isinstance(artifacts_total, bool)
        or not isinstance(artifacts_total, int)
        or artifacts_total < 1
        or exact_plan.get("event") != "TECHNICAL_CONTINUE"
    ):
        raise AdmissionRecoveryError("signer recovery source run is ineligible")
    if not isinstance(reviews, Sequence) or isinstance(reviews, (str, bytes)):
        raise AdmissionRecoveryError("signer recovery reviews are malformed")
    target_reviews: list[Mapping[str, Any]] = []
    exact_candidates: list[Mapping[str, Any]] = []
    reviewer = exact_plan.get("reviewer")
    for raw_review in reviews:
        if not isinstance(raw_review, Mapping):
            raise AdmissionRecoveryError("signer recovery review is malformed")
        account = raw_review.get("user")
        if (
            not isinstance(account, Mapping)
            or not isinstance(account.get("login"), str)
            or not isinstance(reviewer, str)
            or account["login"].casefold() != reviewer.casefold()
            or raw_review.get("commit_id") != exact_plan.get("head_sha")
        ):
            continue
        target_reviews.append(raw_review)
        if (
            account.get("type") == "User"
            and str(raw_review.get("state") or "").upper() == "COMMENTED"
            and raw_review.get("body") == exact_plan.get("review_body")
            and parse_delegated_review_locator(raw_review.get("body"))
            == parse_delegated_review_locator(exact_plan.get("review_body"))
        ):
            exact_candidates.append(raw_review)
    # A technical COMMENT is not a review-approval state.  Keep the adoption
    # lane narrower than native review ordering: exactly one canonical comment
    # and no companion target-account review of any state may be transferred.
    if len(exact_candidates) != 1 or len(target_reviews) != 1:
        raise AdmissionRecoveryError(
            "signer recovery review is manual, conflicting, dismissed, or absent"
        )
    candidate = exact_candidates[0]
    locator = parse_delegated_review_locator(candidate.get("body"))
    user = candidate.get("user")
    head = pr.get("head") if isinstance(pr, Mapping) else None
    base = pr.get("base") if isinstance(pr, Mapping) else None
    tree = head_commit.get("tree") if isinstance(head_commit, Mapping) else None
    if (
        locator is None
        or locator.get("event") != "TECHNICAL_CONTINUE"
        or locator["signer_run_id"] != source["run_id"]
        or locator["signer_run_attempt"] != 1
        or locator["signer_evaluator_sha"] != evaluator
        or not isinstance(user, Mapping)
        or user.get("login") != exact_plan.get("reviewer")
        or user.get("type") != "User"
        or candidate.get("commit_id") != exact_plan.get("head_sha")
        or str(candidate.get("state") or "").upper() != "COMMENTED"
        or not isinstance(candidate.get("id"), int)
        or isinstance(candidate.get("id"), bool)
        or candidate["id"] < 1
        or not isinstance(candidate.get("submitted_at"), str)
        or not candidate["submitted_at"]
        or not isinstance(pr, Mapping)
        or pr.get("number") != exact_plan.get("pr_number")
        or pr.get("state") != "open"
        or not isinstance(head, Mapping)
        or head.get("sha") != exact_plan.get("head_sha")
        or not isinstance(base, Mapping)
        or base.get("ref") != "main"
        or base.get("sha") != evaluator
        or not isinstance(tree, Mapping)
        or tree.get("sha") != exact_plan.get("tree_sha")
        or exact_plan.get("base_sha") != evaluator
        or not isinstance(signer_receipt_blocker, str)
        or not signer_receipt_blocker.startswith("SIGNER_RECEIPT_")
    ):
        raise AdmissionRecoveryError("signer recovery subject differs")
    artifact_digest = _digest(
        artifact_inventory_sha256, "signer recovery artifact inventory"
    )
    review_projection = {
        "id": candidate["id"],
        "user_id": user.get("id"),
        "user_login": user.get("login"),
        "user_type": user.get("type"),
        "state": str(candidate.get("state") or "").upper(),
        "submitted_at": candidate["submitted_at"],
        "commit_id": candidate.get("commit_id"),
        "body_sha256": hashlib.sha256(
            candidate["body"].encode("utf-8")
        ).hexdigest(),
    }
    if (
        isinstance(review_projection["user_id"], bool)
        or not isinstance(review_projection["user_id"], int)
        or review_projection["user_id"] < 1
    ):
        raise AdmissionRecoveryError("signer recovery reviewer id is invalid")
    value = {
        "schema": "qikvrt_delegated_signer_receipt_recovery_evidence_v1",
        "repository": repo,
        "evaluator_sha": evaluator,
        "origin_run_id": source["run_id"],
        "origin_run_attempt": 1,
        "authorized_run_attempt": 2,
        "plan": exact_plan,
        "plan_sha256": exact_plan["plan_sha256"],
        "review": review_projection,
        "review_locator": locator,
        "reviews_sha256": _canonical_sha256(list(reviews)),
        "review_ids": sorted(
            item.get("id") for item in reviews
            if isinstance(item, Mapping)
            and isinstance(item.get("id"), int)
            and not isinstance(item.get("id"), bool)
        ),
        "subject": {
            "pr_number": pr["number"],
            "base_sha": base["sha"],
            "base_ref": base["ref"],
            "head_sha": head["sha"],
            "head_tree_sha": tree["sha"],
        },
        "source_jobs_total": jobs_total,
        "source_artifacts_total": artifacts_total,
        "artifact_inventory_sha256": artifact_digest,
        "signer_receipt_observation": {
            "state": "NO_VALID_EXACT_RECEIPT",
            "first_blocker": signer_receipt_blocker,
            "verified_review_id": None,
        },
        "recovery_effect": (
            "RERUN_SAME_GATE_RUN_FOR_TECHNICAL_RECEIPT_REOBSERVATION"
        ),
        "new_review_post_authorized": False,
        "technical_reobservation_only": True,
        "approval_authorized": False,
        "required_gate_success_authorized": False,
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["evidence_sha256"] = _canonical_sha256(value)
    return value


def validate_delegated_signer_receipt_recovery_evidence(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    from tools.qikvrt_native_account_review import (
        parse_delegated_review_locator,
        validate_plan,
    )

    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("signer recovery evidence is malformed")
    observed = dict(value)
    claimed = observed.pop("evidence_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("signer recovery evidence digest differs")
    plan = validate_plan(observed.get("plan"))
    review = observed.get("review")
    locator = observed.get("review_locator")
    receipt = observed.get("signer_receipt_observation")
    subject = observed.get("subject")
    if (
        observed.get("schema")
        != "qikvrt_delegated_signer_receipt_recovery_evidence_v1"
        or observed.get("plan_sha256") != plan["plan_sha256"]
        or observed.get("origin_run_id") != plan.get("signer_run_id")
        or observed.get("origin_run_attempt") != 1
        or observed.get("authorized_run_attempt") != 2
        or plan.get("signer_run_attempt") != 1
        or plan.get("event") != "TECHNICAL_CONTINUE"
        or observed.get("evaluator_sha") != plan.get("signer_evaluator_sha")
        or not isinstance(review, Mapping)
        or not isinstance(locator, Mapping)
        or locator
        != parse_delegated_review_locator(plan.get("review_body"))
        or review.get("body_sha256")
        != hashlib.sha256(plan["review_body"].encode("utf-8")).hexdigest()
        or review.get("user_login") != plan.get("reviewer")
        or review.get("state") != "COMMENTED"
        or review.get("commit_id") != plan.get("head_sha")
        or locator.get("event") != "TECHNICAL_CONTINUE"
        or not isinstance(subject, Mapping)
        or subject.get("pr_number") != plan.get("pr_number")
        or subject.get("base_sha") != plan.get("base_sha")
        or subject.get("head_sha") != plan.get("head_sha")
        or subject.get("head_tree_sha") != plan.get("tree_sha")
        or not isinstance(receipt, Mapping)
        or receipt.get("state") != "NO_VALID_EXACT_RECEIPT"
        or not isinstance(receipt.get("first_blocker"), str)
        or not receipt["first_blocker"].startswith("SIGNER_RECEIPT_")
        or receipt.get("verified_review_id") is not None
        or observed.get("recovery_effect")
        != "RERUN_SAME_GATE_RUN_FOR_TECHNICAL_RECEIPT_REOBSERVATION"
        or observed.get("new_review_post_authorized") is not False
        or observed.get("technical_reobservation_only") is not True
        or observed.get("approval_authorized") is not False
        or observed.get("required_gate_success_authorized") is not False
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("signer recovery evidence boundary differs")
    _repository(observed.get("repository"), "signer recovery repository")
    _sha(observed.get("evaluator_sha"), "signer recovery evaluator")
    _digest(
        observed.get("artifact_inventory_sha256"),
        "signer recovery artifact inventory",
    )
    return dict(value)


def build_admission_inbox_source(
    run: Mapping[str, Any], *,
    repository: str,
    repository_id: int,
    current_main_sha: str,
    target_configs: Mapping[int, Mapping[str, Any]],
    review_wakeup_record: Mapping[str, Any] | None = None,
    review_wakeup_ledger_head: str | None = None,
    exact_review_core_lookup: Mapping[str, Any] | None = None,
    mesh_review_core_lookup: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(run, Mapping):
        raise AdmissionRecoveryError("admission inbox source is malformed")
    workflow_id = run.get("workflow_id")
    config = (
        target_configs.get(workflow_id)
        if isinstance(workflow_id, int) else None
    )
    if not isinstance(config, Mapping):
        raise AdmissionRecoveryError("admission inbox source workflow is untrusted")
    candidate = dict(run)
    candidate["jobs_total"] = 0
    candidate["artifacts_total"] = 0
    title = candidate.get("display_title")
    locator = config.get("activation_locator")
    shared_requested_child = (
        locator == "qikvrt-rr-v3"
        and isinstance(title, str)
        and re.search(r" i=event a=event$", title) is None
    )
    classified = classify_zero_job_admission(
        candidate,
        repository=repository,
        repository_id=repository_id,
        current_main_sha=current_main_sha,
        trusted_workflow_id=workflow_id,
        trusted_workflow_path=config.get("path"),
        activation_locator=config.get("activation_locator"),
        allowed_events=set(config.get("allowed_events", [])),
        allow_bound_requested_child=shared_requested_child,
    )
    if not classified["eligible"]:
        raise AdmissionRecoveryError("admission inbox source provenance differs")
    source = dict(classified["source"])
    source.pop("jobs_total", None)
    source.pop("artifacts_total", None)
    if shared_requested_child:
        provided_core = [
            item
            for item in (exact_review_core_lookup, mesh_review_core_lookup)
            if item is not None
        ]
        if len(provided_core) != 1:
            raise AdmissionRecoveryError(
                "requested child lacks one shared review Core authority"
            )
        origin = build_shared_review_core_origin(
            provided_core[0],
            candidate,
            jobs_total=0,
            artifacts_total=0,
        )
        source_kind = (
            "CORE_EXACT_REVIEW_CHILD_ZERO_JOB"
            if origin["lane"] == "exact-review-dispatch"
            else "CORE_MESH_REVIEW_CHILD_ZERO_JOB"
        )
        if review_wakeup_record is not None or review_wakeup_ledger_head is not None:
            raise AdmissionRecoveryError(
                "requested child carries competing wake-up recovery authority"
            )
    else:
        if (
            review_wakeup_record is not None
            or review_wakeup_ledger_head is not None
            or exact_review_core_lookup is not None
            or mesh_review_core_lookup is not None
        ):
            raise AdmissionRecoveryError(
                "direct admission source unexpectedly carries wake-up authority"
            )
        origin = None
        source_kind = "DIRECT_EVENT_ZERO_JOB"
    identity = {
        "repository": repository,
        "repository_id": repository_id,
        "workflow_id": source["workflow_id"],
        "run_id": source["run_id"],
        "source_kind": source_kind,
        "origin_sha256": origin.get("origin_sha256") if origin else None,
    }
    fingerprint = _canonical_sha256(identity)
    value = {
        "schema": "qikvrt_review_admission_inbox_source_v1",
        "source_fingerprint": fingerprint,
        "source": source,
        "source_kind": source_kind,
        "origin_authority": origin,
        "trusted_config": {
            "path": config["path"],
            "activation_locator": config["activation_locator"],
            "allowed_events": sorted(set(config["allowed_events"])),
        },
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["source_sha256"] = _canonical_sha256(value)
    return value


def build_admission_signer_recovery_source(
    run: Mapping[str, Any], *,
    repository: str,
    repository_id: int,
    current_main_sha: str,
    target_configs: Mapping[int, Mapping[str, Any]],
    recovery_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Enqueue one exact Gate attempt-1 post-effect receipt-loss source."""
    if not isinstance(run, Mapping):
        raise AdmissionRecoveryError("signer recovery inbox run is malformed")
    workflow_id = run.get("workflow_id")
    config = (
        target_configs.get(workflow_id)
        if isinstance(workflow_id, int) else None
    )
    if (
        not isinstance(config, Mapping)
        or config.get("path")
        != ".github/workflows/qikvrt_required_review_gate.yml"
        or config.get("activation_locator")
        != "QIKVRT required code-owner review admission-v2"
    ):
        raise AdmissionRecoveryError("signer recovery workflow is untrusted")
    candidate = dict(run)
    candidate["jobs_total"] = 0
    candidate["artifacts_total"] = 0
    classified = classify_zero_job_admission(
        candidate,
        repository=repository,
        repository_id=repository_id,
        current_main_sha=current_main_sha,
        trusted_workflow_id=workflow_id,
        trusted_workflow_path=config.get("path"),
        activation_locator=config.get("activation_locator"),
        allowed_events=set(config.get("allowed_events", [])),
    )
    if not classified["eligible"]:
        raise AdmissionRecoveryError("signer recovery source provenance differs")
    evidence = validate_delegated_signer_receipt_recovery_evidence(
        recovery_evidence
    )
    source = dict(classified["source"])
    source.pop("jobs_total", None)
    source.pop("artifacts_total", None)
    if (
        source["run_id"] != evidence["origin_run_id"]
        or source["run_attempt"] != evidence["origin_run_attempt"]
        or source["repository"] != evidence["repository"]
        or source["head_sha"] != evidence["evaluator_sha"]
    ):
        raise AdmissionRecoveryError("signer recovery evidence source differs")
    source_kind = "DELEGATED_SIGNER_RECEIPT_RECOVERY"
    identity = {
        "repository": repository,
        "repository_id": repository_id,
        "workflow_id": source["workflow_id"],
        "run_id": source["run_id"],
        "source_kind": source_kind,
        "origin_sha256": evidence["evidence_sha256"],
    }
    value = {
        "schema": "qikvrt_review_admission_inbox_source_v1",
        "source_fingerprint": _canonical_sha256(identity),
        "source": source,
        "source_kind": source_kind,
        "origin_authority": evidence,
        "trusted_config": {
            "path": config["path"],
            "activation_locator": config["activation_locator"],
            "allowed_events": sorted(set(config["allowed_events"])),
        },
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["source_sha256"] = _canonical_sha256(value)
    return value


def validate_admission_inbox_source(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission inbox source record is malformed")
    observed = dict(value)
    claimed = observed.pop("source_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("admission inbox source digest differs")
    source = observed.get("source")
    config = observed.get("trusted_config")
    if (
        observed.get("schema") != "qikvrt_review_admission_inbox_source_v1"
        or not isinstance(source, Mapping)
        or not isinstance(config, Mapping)
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("admission inbox source boundary differs")
    projection_input = {
        "id": source.get("run_id") if isinstance(source, Mapping) else None,
        "run_attempt": source.get("run_attempt")
        if isinstance(source, Mapping) else None,
        "workflow_id": source.get("workflow_id")
        if isinstance(source, Mapping) else None,
        "path": source.get("workflow_path")
        if isinstance(source, Mapping) else None,
        "repository": {
            "full_name": source.get("repository")
            if isinstance(source, Mapping) else None,
            "id": source.get("repository_id")
            if isinstance(source, Mapping) else None,
        },
        "event": source.get("event") if isinstance(source, Mapping) else None,
        "head_branch": source.get("head_branch")
        if isinstance(source, Mapping) else None,
        "head_sha": source.get("head_sha")
        if isinstance(source, Mapping) else None,
        "display_title": source.get("display_title")
        if isinstance(source, Mapping) else None,
        "status": source.get("status")
        if isinstance(source, Mapping) else None,
        "conclusion": source.get("conclusion")
        if isinstance(source, Mapping) else None,
        "created_at": source.get("created_at")
        if isinstance(source, Mapping) else None,
        "pull_requests": source.get("pull_requests")
        if isinstance(source, Mapping) else None,
        "jobs_total": 0,
        "artifacts_total": 0,
    }
    projection = _projection(projection_input)
    projection.pop("jobs_total", None)
    projection.pop("artifacts_total", None)
    identity = {
        "repository": projection["repository"],
        "repository_id": projection["repository_id"],
        "workflow_id": projection["workflow_id"],
        "run_id": projection["run_id"],
        "source_kind": observed.get("source_kind"),
        "origin_sha256": (
            (
                observed.get("origin_authority", {}).get("evidence_sha256")
                if observed.get("source_kind")
                    == "DELEGATED_SIGNER_RECEIPT_RECOVERY"
                else observed.get("origin_authority", {}).get("origin_sha256")
            )
            if isinstance(observed.get("origin_authority"), Mapping)
            else None
        ),
    }
    source_kind = observed.get("source_kind")
    origin = observed.get("origin_authority")
    if source_kind in {
        "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
        "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
    }:
        exact_origin = validate_shared_review_core_origin(
            origin, source=projection
        )
        expected_kind = (
            "CORE_EXACT_REVIEW_CHILD_ZERO_JOB"
            if exact_origin["lane"] == "exact-review-dispatch"
            else "CORE_MESH_REVIEW_CHILD_ZERO_JOB"
        )
        if source_kind != expected_kind:
            raise AdmissionRecoveryError("shared review Core source kind differs")
    elif source_kind == "DELEGATED_SIGNER_RECEIPT_RECOVERY":
        evidence = validate_delegated_signer_receipt_recovery_evidence(origin)
        if (
            projection["run_id"] != evidence["origin_run_id"]
            or projection["run_attempt"] != evidence["origin_run_attempt"]
            or projection["repository"] != evidence["repository"]
            or projection["head_sha"] != evidence["evaluator_sha"]
        ):
            raise AdmissionRecoveryError(
                "signer recovery inbox evidence differs"
            )
    elif source_kind == "DIRECT_EVENT_ZERO_JOB":
        if origin is not None:
            raise AdmissionRecoveryError(
                "direct admission source carries wake-up authority"
            )
    else:
        raise AdmissionRecoveryError("admission inbox source kind differs")
    if (
        projection != dict(source)
        or observed.get("source_fingerprint") != _canonical_sha256(identity)
        or config.get("path") != projection["workflow_path"]
        or config.get("activation_locator") not in {
            "qikvrt-rr-v3",
            "QIKVRT required code-owner review admission-v2",
        }
        or not isinstance(config.get("allowed_events"), list)
        or (
            config.get("activation_locator") == "qikvrt-rr-v3"
            and source_kind == "DIRECT_EVENT_ZERO_JOB"
            and not (
                isinstance(projection.get("display_title"), str)
                and re.search(
                    r" i=event a=event$", projection["display_title"]
                ) is not None
            )
        )
    ):
        raise AdmissionRecoveryError("admission inbox source identity differs")
    return dict(value)


def build_admission_inbox_slot(
    source_record: Mapping[str, Any], *, sequence: int
) -> dict[str, Any]:
    exact = validate_admission_inbox_source(source_record)
    seq = _positive(sequence, "admission inbox sequence")
    value = {
        "schema": "qikvrt_review_admission_inbox_slot_v1",
        "sequence": seq,
        "source_fingerprint": exact["source_fingerprint"],
        "source_sha256": exact["source_sha256"],
        "source": exact,
        "authority_boundary": "RECOVERY_ONLY",
    }
    value["slot_sha256"] = _canonical_sha256(value)
    return value


def validate_admission_inbox_slot(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission inbox slot is malformed")
    observed = dict(value)
    claimed = observed.pop("slot_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("admission inbox slot digest differs")
    source = validate_admission_inbox_source(observed.get("source"))
    if (
        observed.get("schema") != "qikvrt_review_admission_inbox_slot_v1"
        or observed.get("sequence") != _positive(
            observed.get("sequence"), "admission inbox sequence"
        )
        or observed.get("source_fingerprint") != source["source_fingerprint"]
        or observed.get("source_sha256") != source["source_sha256"]
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
    ):
        raise AdmissionRecoveryError("admission inbox slot boundary differs")
    return dict(value)


def build_admission_inbox_continuation(
    slot: Mapping[str, Any],
    run: Mapping[str, Any],
    *,
    jobs_total: int,
    artifacts_total: int,
) -> dict[str, Any]:
    """Seal the first exact technical continuation for one FIFO source.

    This is deliberately not a business PASS.  It only proves that the exact
    accepted run is no longer a zero-job/zero-artifact ingress result, allowing
    the recovery cursor to advance without transferring any successor result.
    """
    exact_slot = validate_admission_inbox_slot(slot)
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (jobs_total, artifacts_total)
    ):
        raise AdmissionRecoveryError("admission continuation totals are invalid")
    if jobs_total == 0 and artifacts_total == 0:
        raise AdmissionRecoveryError("admission continuation is not materialized")
    candidate = dict(run)
    candidate["jobs_total"] = jobs_total
    candidate["artifacts_total"] = artifacts_total
    observed = _projection(candidate)
    source = exact_slot["source"]["source"]
    immutable_fields = (
        "run_id", "workflow_id", "workflow_path", "repository",
        "repository_id", "event", "head_branch", "head_sha",
        "display_title", "created_at", "pull_requests",
    )
    if any(observed[field] != source[field] for field in immutable_fields):
        raise AdmissionRecoveryError("admission continuation source differs")
    if observed["run_attempt"] not in {1, 2}:
        raise AdmissionRecoveryError("admission continuation attempt differs")
    value = {
        "schema": "qikvrt_review_admission_inbox_continuation_v1",
        "sequence": exact_slot["sequence"],
        "source_fingerprint": exact_slot["source_fingerprint"],
        "source_sha256": exact_slot["source_sha256"],
        "source": source,
        "observed": observed,
        "first_causal_continuation": (
            "EXACT_SOURCE_JOB_OR_ARTIFACT_MATERIALIZED"
        ),
        "d0": 2,
        "effect_ack": "TECHNICAL_CONTINUATION_PENDING_REOBSERVATION",
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["receipt_sha256"] = _canonical_sha256(value)
    return value


def validate_admission_inbox_continuation(
    value: Mapping[str, Any], slot: Mapping[str, Any]
) -> dict[str, Any]:
    exact_slot = validate_admission_inbox_slot(slot)
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission continuation is malformed")
    observed = dict(value)
    claimed = observed.pop("receipt_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("admission continuation digest differs")
    run = observed.get("observed")
    source = exact_slot["source"]["source"]
    totals = (
        run.get("jobs_total") if isinstance(run, Mapping) else None,
        run.get("artifacts_total") if isinstance(run, Mapping) else None,
    )
    totals_valid = all(
        not isinstance(total, bool) and isinstance(total, int) and total >= 0
        for total in totals
    )
    if (
        observed.get("schema")
            != "qikvrt_review_admission_inbox_continuation_v1"
        or observed.get("sequence") != exact_slot["sequence"]
        or observed.get("source_fingerprint")
            != exact_slot["source_fingerprint"]
        or observed.get("source_sha256") != exact_slot["source_sha256"]
        or observed.get("source") != source
        or not isinstance(run, Mapping)
        or not totals_valid
        or sum(totals) < 1
        or observed.get("first_causal_continuation")
            != "EXACT_SOURCE_JOB_OR_ARTIFACT_MATERIALIZED"
        or observed.get("d0") != 2
        or observed.get("effect_ack")
            != "TECHNICAL_CONTINUATION_PENDING_REOBSERVATION"
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("productive_effect") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("admission continuation boundary differs")
    immutable_fields = (
        "run_id", "workflow_id", "workflow_path", "repository",
        "repository_id", "event", "head_branch", "head_sha",
        "display_title", "created_at", "pull_requests",
    )
    if any(run.get(field) != source[field] for field in immutable_fields):
        raise AdmissionRecoveryError("admission continuation identity differs")
    if run.get("run_attempt") not in {1, 2}:
        raise AdmissionRecoveryError("admission continuation attempt differs")
    return dict(value)


def build_admission_signer_receipt_continuation(
    slot: Mapping[str, Any], run: Mapping[str, Any], *,
    jobs_total: int, artifacts_total: int,
    signer_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal attempt-2 technical receipt reobservation without review Authority."""
    from tools.qikvrt_native_account_review import validate_signer_receipt

    # The full receipt was already validated from exact API/artifact bytes by
    # observe_automated_signer_receipts.  Re-bind every recovery-relevant
    # locator here; do not reinterpret the native-review policy.
    exact_slot = validate_admission_inbox_slot(slot)
    if exact_slot["source"].get("source_kind") != (
        "DELEGATED_SIGNER_RECEIPT_RECOVERY"
    ):
        raise AdmissionRecoveryError("signer continuation slot kind differs")
    evidence = validate_delegated_signer_receipt_recovery_evidence(
        exact_slot["source"]["origin_authority"]
    )
    candidate = dict(run)
    candidate["jobs_total"] = jobs_total
    candidate["artifacts_total"] = artifacts_total
    observed = _projection(candidate)
    source = exact_slot["source"]["source"]
    immutable = (
        "run_id", "workflow_id", "workflow_path", "repository",
        "repository_id", "event", "head_branch", "head_sha",
        "display_title", "created_at", "pull_requests",
    )
    receipt = dict(signer_receipt) if isinstance(signer_receipt, Mapping) else {}
    review = receipt.get("review")
    effect_readback = receipt.get("effect_readback")
    if (
        any(observed[field] != source[field] for field in immutable)
        or observed["run_attempt"] != 2
        or observed["status"] != "completed"
        or observed["conclusion"] != "success"
        or receipt.get("schema")
        != "qikvrt_native_account_review_signer_receipt_v1"
        or receipt.get("repository") != evidence["repository"]
        or receipt.get("evaluator_sha") != evidence["evaluator_sha"]
        or receipt.get("run_id") != evidence["origin_run_id"]
        or receipt.get("run_attempt") != 2
        or receipt.get("origin_run_id") != evidence["origin_run_id"]
        or receipt.get("origin_run_attempt") != 1
        or not isinstance(receipt.get("plan_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", receipt["plan_sha256"]) is None
        or receipt.get("evidence_fingerprint")
            != evidence["review_locator"]["evidence_fingerprint"]
        or receipt.get("pr_number") != evidence["subject"]["pr_number"]
        or receipt.get("head_sha") != evidence["subject"]["head_sha"]
        or receipt.get("tree_sha") != evidence["subject"]["head_tree_sha"]
        or not isinstance(review, Mapping)
        or review.get("id") != evidence["review"]["id"]
        or review.get("state") != "COMMENTED"
        or review.get("body_sha256") != evidence["review"]["body_sha256"]
        or not isinstance(effect_readback, Mapping)
        or effect_readback.get("effect_mode")
            != "ADOPT_UNRECEIPTED"
        or effect_readback.get("state") != "COMMENTED"
        or receipt.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("signer continuation receipt differs")
    # Keep this reference so static callers cannot silently pass a similarly
    # shaped, non-native schema without the authoritative validator existing.
    if not callable(validate_signer_receipt):
        raise AdmissionRecoveryError("native signer receipt validator is absent")
    value = {
        "schema": "qikvrt_review_admission_signer_continuation_v1",
        "sequence": exact_slot["sequence"],
        "source_fingerprint": exact_slot["source_fingerprint"],
        "source_sha256": exact_slot["source_sha256"],
        "observed": observed,
        "signer_receipt": receipt,
        "signer_receipt_sha256": _digest(
            receipt.get("receipt_sha256"), "signer continuation receipt"
        ),
        "first_causal_continuation": (
            "EXACT_ATTEMPT_2_TECHNICAL_RECEIPT_REOBSERVED"
        ),
        "d0": 2,
        "effect_ack": "TECHNICAL_CONTINUATION_PENDING_REOBSERVATION",
        "authority_boundary": "RECOVERY_ONLY",
        "technical_reobservation_only": True,
        "approval_authorized": False,
        "required_gate_success_authorized": False,
        "native_account_review_authorized": False,
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["receipt_sha256"] = _canonical_sha256(value)
    return value


def validate_admission_signer_receipt_continuation(
    value: Mapping[str, Any], slot: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("signer continuation is malformed")
    observed = dict(value)
    claimed = observed.pop("receipt_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("signer continuation digest differs")
    run = value.get("observed")
    if not isinstance(run, Mapping):
        raise AdmissionRecoveryError("signer continuation run is malformed")
    raw_run = {
        "id": run.get("run_id"),
        "run_attempt": run.get("run_attempt"),
        "workflow_id": run.get("workflow_id"),
        "path": run.get("workflow_path"),
        "repository": {
            "full_name": run.get("repository"),
            "id": run.get("repository_id"),
        },
        "event": run.get("event"),
        "head_branch": run.get("head_branch"),
        "head_sha": run.get("head_sha"),
        "display_title": run.get("display_title"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "created_at": run.get("created_at"),
        "pull_requests": run.get("pull_requests"),
    }
    expected = build_admission_signer_receipt_continuation(
        slot,
        raw_run,
        jobs_total=run.get("jobs_total"),
        artifacts_total=run.get("artifacts_total"),
        signer_receipt=value.get("signer_receipt"),
    )
    if dict(value) != expected:
        raise AdmissionRecoveryError("signer continuation differs")
    return dict(value)


def build_recovery_intent(
    selection: Mapping[str, Any],
    *,
    recovery_repository: str,
    recovery_workflow_id: int,
    recovery_workflow_path: str,
    recovery_head_sha: str,
) -> dict[str, Any]:
    if selection.get("state") != "RERUN_ATTEMPT_2" or selection.get(
        "rerun_required"
    ) is not True:
        raise AdmissionRecoveryError("selection does not authorize attempt 2")
    selected = selection.get("selected")
    if not isinstance(selected, Mapping) or selected.get("run_attempt") != 1:
        raise AdmissionRecoveryError("selection source is not attempt 1")
    value = {
        "schema": "qikvrt_review_admission_rerun_intent_v1",
        "recovery_repository": recovery_repository,
        "recovery_workflow_id": _positive(
            recovery_workflow_id, "recovery workflow id"
        ),
        "recovery_workflow_path": _workflow_path(recovery_workflow_path),
        "recovery_head_sha": _sha(recovery_head_sha, "recovery head SHA"),
        "source": dict(selected),
        "source_kind": "DIRECT_EVENT_ZERO_JOB",
        "origin_authority": None,
        "authorized_rerun_attempt": 2,
        "authority_boundary": "TECHNICAL_REOBSERVATION_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    origin = selection.get("origin_authority")
    if origin is not None:
        if selection.get("source_kind") == "DELEGATED_SIGNER_RECEIPT_RECOVERY":
            exact_origin = validate_delegated_signer_receipt_recovery_evidence(
                origin
            )
            if (
                selected.get("run_id") != exact_origin["origin_run_id"]
                or selected.get("run_attempt")
                    != exact_origin["origin_run_attempt"]
            ):
                raise AdmissionRecoveryError(
                    "signer recovery intent source differs"
                )
            value["source_kind"] = "DELEGATED_SIGNER_RECEIPT_RECOVERY"
        elif selection.get("source_kind") in {
            "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
            "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
        }:
            exact_origin = validate_shared_review_core_origin(
                origin, source=selected
            )
            expected_kind = (
                "CORE_EXACT_REVIEW_CHILD_ZERO_JOB"
                if exact_origin["lane"] == "exact-review-dispatch"
                else "CORE_MESH_REVIEW_CHILD_ZERO_JOB"
            )
            if selection.get("source_kind") != expected_kind:
                raise AdmissionRecoveryError("shared review Core source kind differs")
            value["source_kind"] = expected_kind
        else:
            raise AdmissionRecoveryError(
                "recovery origin is not a recognized sole authority"
            )
        value["origin_authority"] = exact_origin
    if selected.get("event") == "pull_request_target":
        value["live_subject"] = _live_subject(selection.get("live_subject"))
    elif value["source_kind"] in {
        "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
        "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
    }:
        live = _live_subject(selection.get("live_subject"))
        payload = exact_origin.get("intent", {}).get("payload", {})
        if exact_origin["lane"] == "exact-review-dispatch":
            core_subject = payload.get("subject")
            differs = not isinstance(core_subject, Mapping) or any(
                live[live_key] != core_subject[core_key]
                for live_key, core_key in (
                    ("pr_number", "pull_request"),
                    ("head_repository", "head_repository"),
                    ("head_ref", "head_ref"),
                    ("head_sha", "head_sha"),
                    ("head_tree_sha", "head_tree_sha"),
                    ("base_ref", "base_ref"),
                    ("base_sha", "base_sha"),
                )
            )
        else:
            request = payload.get("request")
            inputs = request.get("inputs") if isinstance(request, Mapping) else None
            differs = (
                not isinstance(inputs, Mapping)
                or str(live["pr_number"]) != inputs.get("pr")
                or live["head_sha"] != inputs.get("head")
                or live["head_repository"] != recovery_repository
                or live["base_repository"] != recovery_repository
                or live["base_ref"] != "main"
                or live["base_sha"] != payload.get("main_head_sha")
                or inputs.get("evaluator_sha") != payload.get("main_head_sha")
            )
        if differs:
            raise AdmissionRecoveryError(
                "live subject differs from shared review Core intent"
            )
        value["live_subject"] = live
    value["intent_sha256"] = _canonical_sha256(value)
    return value


def build_recovery_producer_binding(
    intent: Mapping[str, Any],
    *,
    recovery_run_id: int,
    recovery_run_attempt: int,
) -> dict[str, Any]:
    value = validate_recovery_intent(intent)
    result = {
        "schema": "qikvrt_review_admission_rerun_producer_binding_v1",
        "intent_sha256": value["intent_sha256"],
        "recovery_run_id": _positive(recovery_run_id, "recovery run id"),
        "recovery_run_attempt": _positive(
            recovery_run_attempt, "recovery run attempt"
        ),
    }
    result["binding_sha256"] = _canonical_sha256(result)
    return result


def validate_recovery_producer_binding(
    intent: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    value = validate_recovery_intent(intent)
    if not isinstance(binding, Mapping):
        raise AdmissionRecoveryError("producer binding must be an object")
    observed = dict(binding)
    claimed = observed.pop("binding_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("producer binding digest differs")
    if (
        observed.get("schema")
        != "qikvrt_review_admission_rerun_producer_binding_v1"
        or observed.get("intent_sha256") != value["intent_sha256"]
    ):
        raise AdmissionRecoveryError("producer binding differs from intent")
    _positive(observed.get("recovery_run_id"), "binding recovery run id")
    _positive(
        observed.get("recovery_run_attempt"),
        "binding recovery run attempt",
    )
    return dict(binding)


def build_terminal_receipt(selection: Mapping[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(selection, Mapping)
        or selection.get("state") not in TERMINAL_RECOVERY_BLOCKERS
        or selection.get("rerun_required") is not False
        or selection.get("d0") != 3
    ):
        raise AdmissionRecoveryError("selection is not a terminal recovery hold")
    source = selection.get("selected")
    if not isinstance(source, Mapping):
        raise AdmissionRecoveryError("terminal source attempt is invalid")
    state = selection["state"]
    first_blocker = selection.get("first_blocker") or (
        TERMINAL_RECOVERY_DEFAULT_BLOCKER[state]
    )
    if first_blocker not in TERMINAL_RECOVERY_BLOCKERS[state]:
        raise AdmissionRecoveryError("terminal recovery blocker is not authorized")
    result = {
        "schema": "qikvrt_review_admission_terminal_receipt_v1",
        "source": dict(source),
        "source_key": (
            f"{source['workflow_id']}:{source['run_id']}:{source['run_attempt']}"
        ),
        "state": state,
        "first_blocker": first_blocker,
        "d0": 3,
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    result["receipt_sha256"] = _canonical_sha256(result)
    return result


def validate_terminal_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise AdmissionRecoveryError("terminal receipt must be an object")
    value = dict(receipt)
    claimed = value.pop("receipt_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("terminal receipt digest differs")
    if (
        value.get("schema") != "qikvrt_review_admission_terminal_receipt_v1"
        or value.get("state") not in TERMINAL_RECOVERY_BLOCKERS
        or value.get("first_blocker")
            not in TERMINAL_RECOVERY_BLOCKERS.get(value.get("state"), ())
        or value.get("d0") != 3
        or value.get("native_account_review_authorized") is not False
        or value.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("terminal receipt boundary differs")
    return dict(receipt)


def validate_recovery_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(intent, Mapping):
        raise AdmissionRecoveryError("recovery intent must be an object")
    value = dict(intent)
    claimed = value.pop("intent_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("recovery intent digest differs")
    if (
        value.get("schema") != "qikvrt_review_admission_rerun_intent_v1"
        or value.get("authorized_rerun_attempt") != 2
        or value.get("native_account_review_authorized") is not False
        or value.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("recovery intent authority boundary differs")
    source = value.get("source")
    if not isinstance(source, Mapping):
        raise AdmissionRecoveryError("recovery intent source is malformed")
    source_kind = value.get("source_kind")
    if source_kind in {
        "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
        "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
    }:
        exact_origin = validate_shared_review_core_origin(
            value.get("origin_authority"), source=source
        )
        expected_kind = (
            "CORE_EXACT_REVIEW_CHILD_ZERO_JOB"
            if exact_origin["lane"] == "exact-review-dispatch"
            else "CORE_MESH_REVIEW_CHILD_ZERO_JOB"
        )
        if source_kind != expected_kind:
            raise AdmissionRecoveryError("shared review Core intent kind differs")
    elif source_kind == "DELEGATED_SIGNER_RECEIPT_RECOVERY":
        evidence = validate_delegated_signer_receipt_recovery_evidence(
            value.get("origin_authority")
        )
        if (
            source.get("run_id") != evidence["origin_run_id"]
            or source.get("run_attempt") != evidence["origin_run_attempt"]
        ):
            raise AdmissionRecoveryError(
                "signer recovery intent source differs"
            )
    elif source_kind == "DIRECT_EVENT_ZERO_JOB":
        if value.get("origin_authority") is not None:
            raise AdmissionRecoveryError(
                "direct recovery intent carries wake-up authority"
            )
    else:
        raise AdmissionRecoveryError("recovery intent source kind differs")
    return dict(intent)


def plan_recovery_effect(
    intent: Mapping[str, Any],
    *,
    source_run: Mapping[str, Any],
    source_jobs_total: int,
    source_artifacts_total: int,
    current_main_sha: str,
    live_subject: Mapping[str, Any] | None = None,
    current_wakeup_record: Mapping[str, Any] | None = None,
    current_review_subject: Mapping[str, Any] | None = None,
    current_signer_recovery_evidence: Mapping[str, Any] | None = None,
    current_exact_review_core_origin: Mapping[str, Any] | None = None,
    current_shared_review_core_preparation: Mapping[str, Any] | None = None,
    current_recovery_producer_binding: Mapping[str, Any] | None = None,
    current_recovery_run_id: int | None = None,
    current_recovery_run_attempt: int | None = None,
) -> dict[str, Any]:
    value = validate_recovery_intent(intent)
    source = dict(source_run)
    source["jobs_total"] = source_jobs_total
    source["artifacts_total"] = source_artifacts_total
    observed = _projection(source)
    if observed != value["source"]:
        raise AdmissionRecoveryError("source run drifted before rerun effect")
    if value["recovery_head_sha"] != _sha(
        current_main_sha, "effect current main SHA"
    ):
        raise AdmissionRecoveryError("recovery main drifted before rerun effect")
    if "live_subject" in value:
        if _live_subject(live_subject) != value["live_subject"]:
            raise AdmissionRecoveryError(
                "live recovery subject drifted before rerun effect"
            )
    producer = validate_recovery_producer_binding(
        value, current_recovery_producer_binding
    )
    actor_run_id = _positive(
        current_recovery_run_id, "current recovery run id"
    )
    actor_run_attempt = _positive(
        current_recovery_run_attempt, "current recovery run attempt"
    )
    post_authorized = (
        producer["recovery_run_id"] == actor_run_id
        and producer["recovery_run_attempt"] == actor_run_attempt
    )
    if value["source_kind"] in {
        "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
        "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
    }:
        origin = validate_shared_review_core_origin(
            value["origin_authority"], source=value["source"]
        )
        if current_exact_review_core_origin is not None:
            raise AdmissionRecoveryError(
                "stale shared review Core origin cannot authorize the rerun effect"
            )
        preparation = validate_shared_review_core_rerun_preparation(
            current_shared_review_core_preparation, origin=origin
        )
        post_authorized = post_authorized and (
            preparation["actor_run_id"] == actor_run_id
            and preparation["actor_run_attempt"] == actor_run_attempt
        )
    elif value["source_kind"] == "DELEGATED_SIGNER_RECEIPT_RECOVERY":
        exact_signer = validate_delegated_signer_receipt_recovery_evidence(
            value["origin_authority"]
        )
        observed_signer = validate_delegated_signer_receipt_recovery_evidence(
            current_signer_recovery_evidence
        )
        immutable = (
            "repository", "evaluator_sha", "origin_run_id",
            "origin_run_attempt", "authorized_run_attempt", "plan_sha256",
            "review", "review_locator", "subject",
        )
        if any(observed_signer[field] != exact_signer[field] for field in immutable):
            raise AdmissionRecoveryError(
                "signer recovery authority drifted before rerun effect"
            )
    elif (
        current_wakeup_record is not None
        or current_review_subject is not None
        or current_signer_recovery_evidence is not None
        or current_exact_review_core_origin is not None
        or current_shared_review_core_preparation is not None
    ):
        raise AdmissionRecoveryError(
            "direct recovery effect carries wake-up observation"
        )
    zero_job_mode = value["source_kind"] in {
        "DIRECT_EVENT_ZERO_JOB", "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
        "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
    }
    if (
        observed["run_attempt"] != 1
        or observed["status"] != "completed"
        or not isinstance(observed["conclusion"], str)
        or not observed["conclusion"]
        or (
            zero_job_mode
            and (
                observed["jobs_total"] != 0
                or observed["artifacts_total"] != 0
            )
        )
        or (
            not zero_job_mode
            and (
                observed["jobs_total"]
                    != value["origin_authority"]["source_jobs_total"]
                or observed["artifacts_total"]
                    != value["origin_authority"]["source_artifacts_total"]
            )
        )
    ):
        raise AdmissionRecoveryError("source no longer authorizes attempt 2")
    return {
        "schema": "qikvrt_review_admission_rerun_effect_v1",
        "effect": (
            "RERUN_SAME_SOURCE_RUN_ATTEMPT_2"
            if post_authorized
            else "POLL_ONLY_CONSUMED_SAME_RUN_ATTEMPT_2"
        ),
        "source_run_id": observed["run_id"],
        "source_attempt": 1,
        "authorized_attempt": 2,
        "intent_sha256": value["intent_sha256"],
        "source_kind": value["source_kind"],
        "origin_authority_sha256": (
            value["origin_authority"].get("origin_sha256")
            or value["origin_authority"].get("evidence_sha256")
            if value["origin_authority"] is not None else None
        ),
        "new_rerun_post_authorized": post_authorized,
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }


def verify_rerun_readback(
    intent: Mapping[str, Any], rerun: Mapping[str, Any]
) -> dict[str, Any]:
    value = validate_recovery_intent(intent)
    observed = _projection(rerun)
    source = value["source"]
    checks = {
        field: observed[field] == source[field]
        for field in (
            "run_id", "workflow_id", "workflow_path", "repository", "event",
            "head_branch", "head_sha", "display_title",
        )
    }
    checks["run_attempt"] = observed["run_attempt"] == 2
    result = {
        "schema": "qikvrt_review_admission_rerun_readback_v1",
        "source_run_id": source["run_id"],
        "rerun_attempt": observed["run_attempt"],
        "checks": checks,
        "transport_ack_observed": all(checks.values()),
        "d0": 2,
        "effect_ack": "PENDING_ATTEMPT_2_RESULT",
        "source_kind": value["source_kind"],
        "origin_authority_sha256": (
            value["origin_authority"].get("origin_sha256")
            or value["origin_authority"].get("evidence_sha256")
            if value["origin_authority"] is not None else None
        ),
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    if not result["transport_ack_observed"]:
        raise AdmissionRecoveryError("attempt-2 readback differs from source")
    return result


def _stable_rerun_child_locator(run: Mapping[str, Any]) -> dict[str, Any]:
    observed = _projection(run)
    return {
        "id": observed["run_id"],
        "run_attempt": observed["run_attempt"],
        "workflow_id": observed["workflow_id"],
        "path": observed["workflow_path"],
        "repository": {
            "id": observed["repository_id"],
            "full_name": observed["repository"],
        },
        "event": observed["event"],
        "head_branch": observed["head_branch"],
        "head_sha": observed["head_sha"],
        "display_title": observed["display_title"],
        "pull_requests": observed["pull_requests"],
    }


def plan_shared_review_core_attempt_two_adoption(
    intent: Mapping[str, Any], *, child_run: Mapping[str, Any],
    current_main_sha: str, live_subject: Mapping[str, Any],
    core_preparation: Mapping[str, Any],
    core_acceptance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Adopt an exact A2 created before the recovery receipt was persisted."""
    exact = validate_recovery_intent(intent)
    if exact["source_kind"] not in {
        "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
        "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
    }:
        raise AdmissionRecoveryError("attempt-two adoption lacks Shared-Core origin")
    if exact["recovery_head_sha"] != _sha(
        current_main_sha, "adoption current main SHA"
    ):
        raise AdmissionRecoveryError("adoption main drifted")
    if _live_subject(live_subject) != exact.get("live_subject"):
        raise AdmissionRecoveryError("adoption live subject drifted")
    origin = validate_shared_review_core_origin(
        exact["origin_authority"], source=exact["source"]
    )
    preparation = validate_shared_review_core_rerun_preparation(
        core_preparation, origin=origin
    )
    readback = verify_rerun_readback(exact, child_run)
    acceptance = None
    if core_acceptance is not None:
        acceptance = validate_shared_review_core_rerun_acceptance(
            core_acceptance, origin=origin, child_run=child_run
        )
    return {
        "schema": "qikvrt_review_admission_core_attempt_two_adoption_v1",
        "effect": "ADOPT_EXISTING_SAME_RUN_ATTEMPT_2",
        "source_run_id": exact["source"]["run_id"],
        "source_attempt": 1,
        "authorized_attempt": 2,
        "intent_sha256": exact["intent_sha256"],
        "core_lane": origin["lane"],
        "core_sequence": origin["sequence"],
        "core_transport_attempt": origin["transport_attempt"],
        "core_preparation_sha256": _canonical_sha256(preparation),
        "core_acceptance_sha256": (
            _canonical_sha256(acceptance) if acceptance is not None else None
        ),
        "readback": readback,
        "new_rerun_post_authorized": False,
        "native_account_review_authorized": False,
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }


def build_admission_rerun_acceptance(
    *,
    slot: Mapping[str, Any],
    rerun_record: Mapping[str, Any],
    child_run: Mapping[str, Any],
    readback: Mapping[str, Any],
) -> dict[str, Any]:
    exact_slot = validate_admission_inbox_slot(slot)
    if not isinstance(rerun_record, Mapping):
        raise AdmissionRecoveryError("admission rerun record is malformed")
    intent = validate_recovery_intent(rerun_record.get("intent"))
    producer = validate_recovery_producer_binding(
        intent, rerun_record.get("producer_binding")
    )
    intent_source = dict(intent["source"])
    intent_source.pop("jobs_total", None)
    intent_source.pop("artifacts_total", None)
    if (
        rerun_record.get("schema")
        != "qikvrt_review_admission_inbox_child_rerun_v1"
        or rerun_record.get("sequence") != exact_slot["sequence"]
        or rerun_record.get("source_fingerprint")
        != exact_slot["source_fingerprint"]
        or rerun_record.get("source_sha256") != exact_slot["source_sha256"]
        or rerun_record.get("state") != "PRE_EFFECT_REOBSERVED"
        or rerun_record.get("authority_boundary") != "RECOVERY_ONLY"
        or rerun_record.get("productive_effect") is not False
        or intent_source != exact_slot["source"]["source"]
    ):
        raise AdmissionRecoveryError("admission rerun record differs from slot")
    exact_readback = verify_rerun_readback(intent, child_run)
    if not isinstance(readback, Mapping) or dict(readback) != exact_readback:
        raise AdmissionRecoveryError("admission rerun readback differs")
    stable_child = _stable_rerun_child_locator(child_run)
    value = {
        "schema": "qikvrt_review_admission_inbox_child_acceptance_v2",
        "sequence": exact_slot["sequence"],
        "source_fingerprint": exact_slot["source_fingerprint"],
        "source_sha256": exact_slot["source_sha256"],
        "intent_sha256": intent["intent_sha256"],
        "producer_binding_sha256": producer["binding_sha256"],
        "child_run_id": intent["source"]["run_id"],
        "child_run_attempt": 2,
        "child": stable_child,
        "readback": exact_readback,
        "effect_ack": "TRANSPORT_ACCEPTED_PENDING_REOBSERVATION",
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["acceptance_sha256"] = _canonical_sha256(value)
    return value


def validate_admission_rerun_acceptance(
    value: Mapping[str, Any], *, slot: Mapping[str, Any],
    rerun_record: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission rerun acceptance is malformed")
    expected = build_admission_rerun_acceptance(
        slot=slot,
        rerun_record=rerun_record,
        child_run=value.get("child"),
        readback=value.get("readback"),
    )
    if dict(value) != expected:
        raise AdmissionRecoveryError("admission rerun acceptance differs")
    return dict(value)


def validate_exact_review_core_rerun_preparation(
    value: Mapping[str, Any], *, origin: Mapping[str, Any]
) -> dict[str, Any]:
    exact = validate_shared_review_core_rerun_preparation(value, origin=origin)
    if exact["lane"] != "exact-review-dispatch":
        raise AdmissionRecoveryError("exact-review Core preparation lane differs")
    return exact


def validate_shared_review_core_rerun_preparation(
    value: Mapping[str, Any], *, origin: Mapping[str, Any]
) -> dict[str, Any]:
    exact = validate_shared_review_core_origin(origin)
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("shared-Core rerun preparation is malformed")
    retry = build_shared_review_core_retry_evidence(
        exact, source=exact["source"]
    )
    if (
        value.get("schema") != "qikvrt_ruleset_outbox_child_rerun_v1"
        or value.get("lane") != exact["lane"]
        or value.get("sequence") != exact["sequence"]
        or value.get("fingerprint") != exact["fingerprint"]
        or value.get("transport_attempt") != exact["transport_attempt"]
        or value.get("target_run_id") != exact["source"]["run_id"]
        or value.get("target_run_attempt") != 2
        or value.get("endpoint")
        != (
            f"repos/{exact['source']['repository']}/actions/runs/"
            f"{exact['source']['run_id']}/rerun"
        )
        or value.get("retry_evidence") != retry
        or value.get("state") != "PRE_EFFECT_REOBSERVED"
        or value.get("productive_effect") is not False
        or value.get("ledger_ref") != exact["ledger_ref"]
    ):
        raise AdmissionRecoveryError("shared-Core rerun preparation differs")
    _positive(value.get("actor_run_id"), "shared-Core rerun actor run id")
    _positive(
        value.get("actor_run_attempt"),
        "shared-Core rerun actor run attempt",
    )
    _sha(value.get("ledger_head"), "shared-Core rerun ledger head")
    cas = value.get("cas")
    durable = value.get("durable_readback")
    if isinstance(cas, Mapping) == isinstance(durable, Mapping):
        raise AdmissionRecoveryError(
            "shared-Core rerun requires exactly one mutation or durable readback"
        )
    if isinstance(cas, Mapping):
        _validate_shared_core_cas(cas, ledger_head=value.get("ledger_head"))
    if isinstance(durable, Mapping) and (
        durable.get("schema")
        != "qikvrt_review_admission_core_durable_readback_v1"
        or durable.get("kind") != "CHILD_RERUN_PREPARATION"
        or durable.get("lane") != exact["lane"]
        or durable.get("sequence") != exact["sequence"]
        or durable.get("fingerprint") != exact["fingerprint"]
        or durable.get("transport_attempt") != exact["transport_attempt"]
        or durable.get("ledger_ref") != value.get("ledger_ref")
        or durable.get("ledger_head") != value.get("ledger_head")
        or durable.get("record_sha256")
        != _canonical_sha256({
            key:item for key,item in value.items()
            if key not in {"ledger_ref", "ledger_head", "durable_readback"}
        })
        or durable.get("verified") is not True
        or durable.get("productive_effect") is not False
    ):
        raise AdmissionRecoveryError("shared-Core preparation readback differs")
    return dict(value)


def validate_exact_review_core_rerun_acceptance(
    value: Mapping[str, Any], *, origin: Mapping[str, Any],
    child_run: Mapping[str, Any],
) -> dict[str, Any]:
    exact = validate_shared_review_core_rerun_acceptance(
        value, origin=origin, child_run=child_run
    )
    if exact["lane"] != "exact-review-dispatch":
        raise AdmissionRecoveryError("exact-review Core acceptance lane differs")
    return exact


def validate_shared_review_core_rerun_acceptance(
    value: Mapping[str, Any], *, origin: Mapping[str, Any],
    child_run: Mapping[str, Any],
) -> dict[str, Any]:
    from tools.qikvrt_ruleset_outbox import (
        digest as core_digest,
        normalize_child_for_intent,
    )

    exact = validate_shared_review_core_origin(origin)
    if not isinstance(value, Mapping) or not isinstance(child_run, Mapping):
        raise AdmissionRecoveryError("shared-Core rerun acceptance is malformed")
    repository = child_run.get("repository")
    candidate = {
        "run_id": child_run.get("id", child_run.get("run_id")),
        "run_attempt": child_run.get("run_attempt"),
        "workflow_id": child_run.get("workflow_id"),
        "workflow_path": _workflow_path(
            child_run.get("path", child_run.get("workflow_path"))
        ),
        "event": child_run.get("event"),
        "repository": (
            repository.get("full_name") if isinstance(repository, Mapping)
            else repository
        ),
        "head_sha": child_run.get("head_sha"),
        "status": child_run.get("status"),
        "conclusion": child_run.get("conclusion"),
        "display_title": child_run.get("display_title"),
    }
    sealed_normalized = normalize_child_for_intent(
        value.get("child"),
        intent=exact["intent"],
        attempt=exact["transport_attempt"],
        same_run_recovery=True,
    )
    immutable_fields = (
        "run_id", "run_attempt", "workflow_id", "workflow_path", "event",
        "repository", "head_sha", "display_title",
    )
    live_identity = {
        field: candidate.get(field) for field in immutable_fields
    }
    if (
        _positive(candidate.get("run_id"), "live shared-Core child run id")
            != candidate.get("run_id")
        or _positive(
            candidate.get("run_attempt"),
            "live shared-Core child run attempt",
        ) != 2
        or _positive(
            candidate.get("workflow_id"), "live shared-Core child workflow id"
        ) != candidate.get("workflow_id")
        or _sha(candidate.get("head_sha"), "live shared-Core child head")
            != candidate.get("head_sha")
    ):
        raise AdmissionRecoveryError("shared-Core live child identity differs")
    if (
        value.get("schema")
        != "qikvrt_ruleset_outbox_child_rerun_acceptance_v1"
        or value.get("lane") != exact["lane"]
        or value.get("sequence") != exact["sequence"]
        or value.get("fingerprint") != exact["fingerprint"]
        or value.get("transport_attempt") != exact["transport_attempt"]
        or value.get("child") != sealed_normalized
        or value.get("child_sha256") != core_digest(sealed_normalized)
        or any(
            live_identity.get(field) != sealed_normalized.get(field)
            for field in immutable_fields
        )
        or value.get("state") != "CHILD_RERUN_ACCEPTED_LOCATOR"
        or value.get("productive_effect") is not False
        or value.get("ledger_ref") != exact["ledger_ref"]
    ):
        raise AdmissionRecoveryError("shared-Core rerun acceptance differs")
    _sha(value.get("ledger_head"), "shared-Core acceptance ledger head")
    cas = value.get("cas")
    durable = value.get("durable_readback")
    if isinstance(cas, Mapping) == isinstance(durable, Mapping):
        raise AdmissionRecoveryError(
            "shared-Core acceptance requires exactly one mutation or durable readback"
        )
    if isinstance(cas, Mapping):
        _validate_shared_core_cas(cas, ledger_head=value.get("ledger_head"))
    if isinstance(durable, Mapping) and (
        durable.get("schema")
        != "qikvrt_review_admission_core_durable_readback_v1"
        or durable.get("kind") != "CHILD_RERUN_ACCEPTANCE"
        or durable.get("lane") != exact["lane"]
        or durable.get("sequence") != exact["sequence"]
        or durable.get("fingerprint") != exact["fingerprint"]
        or durable.get("transport_attempt") != exact["transport_attempt"]
        or durable.get("ledger_ref") != value.get("ledger_ref")
        or durable.get("ledger_head") != value.get("ledger_head")
        or durable.get("record_sha256")
        != _canonical_sha256({
            key:item for key,item in value.items()
            if key not in {"ledger_ref", "ledger_head", "durable_readback"}
        })
        or durable.get("verified") is not True
        or durable.get("productive_effect") is not False
    ):
        raise AdmissionRecoveryError("shared-Core acceptance readback differs")
    return dict(value)


def _validate_shared_core_cas(
    value: Mapping[str, Any], *, ledger_head: Any
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("shared-Core CAS receipt is malformed")
    exact = dict(value)
    attempts = exact.get("attempts")
    if (
        set(exact)
        != {"schema", "persisted", "appended", "head", "attempts", "force"}
        or exact.get("schema") != "qikvrt_ruleset_outbox_cas_v1"
        or exact.get("persisted") is not True
        or not isinstance(exact.get("appended"), bool)
        or exact.get("head") != ledger_head
        or isinstance(attempts, bool)
        or not isinstance(attempts, int)
        or not (1 <= attempts <= 32)
        or exact.get("force") is not False
    ):
        raise AdmissionRecoveryError("shared-Core CAS receipt differs")
    _sha(ledger_head, "shared-Core CAS ledger head")
    return exact


def build_admission_attempt_authority_chain(
    *,
    slot: Mapping[str, Any],
    rerun_record: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    core_preparation: Mapping[str, Any],
    core_acceptance: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal one shared-Core A1 acceptance -> same-run A2 authority chain."""
    exact_slot = validate_admission_inbox_slot(slot)
    exact_acceptance = validate_admission_rerun_acceptance(
        acceptance, slot=exact_slot, rerun_record=rerun_record
    )
    intent = validate_recovery_intent(rerun_record.get("intent"))
    if intent["source_kind"] not in {
        "CORE_EXACT_REVIEW_CHILD_ZERO_JOB",
        "CORE_MESH_REVIEW_CHILD_ZERO_JOB",
    }:
        raise AdmissionRecoveryError(
            "admission attempt chain has no shared review Core origin"
        )
    origin = validate_shared_review_core_origin(
        intent["origin_authority"], source=intent["source"]
    )
    child = exact_acceptance["child"]
    exact_preparation = validate_shared_review_core_rerun_preparation(
        core_preparation, origin=origin
    )
    exact_core_acceptance = validate_shared_review_core_rerun_acceptance(
        core_acceptance, origin=origin, child_run=child
    )
    if (
        not isinstance(exact_preparation.get("durable_readback"), Mapping)
        or not isinstance(exact_core_acceptance.get("durable_readback"), Mapping)
    ):
        raise AdmissionRecoveryError(
            "admission attempt chain requires durable Shared-Core readback"
        )
    subject = _live_subject(intent.get("live_subject"))
    value = {
        "schema": "qikvrt_review_admission_same_run_authority_v1",
        "path": admission_inbox_attempt_chain_path(child["id"], 2),
        "repository": intent["source"]["repository"],
        "repository_id": intent["source"]["repository_id"],
        "source_run_id": child["id"],
        "origin_run_attempt": 1,
        "authorized_run_attempt": 2,
        "workflow_id": child["workflow_id"],
        "workflow_path": _workflow_path(child["path"]),
        "evaluator_sha": child["head_sha"],
        "pr_number": subject["pr_number"],
        "head_sha": subject["head_sha"],
        "head_tree_sha": subject["head_tree_sha"],
        "base_sha": subject["base_sha"],
        "core_authority": {
            "lane": origin["lane"],
            "sequence": origin["sequence"],
            "fingerprint": origin["fingerprint"],
            "transport_attempt": origin["transport_attempt"],
            "ledger_ref": origin["ledger_ref"],
            "origin_ledger_head": origin["ledger_head"],
            "origin_sha256": origin["origin_sha256"],
            "accepted_attempt_1_child_sha256": origin[
                "accepted_child_sha256"
            ],
            "rerun_preparation": exact_preparation,
            "rerun_preparation_sha256": _canonical_sha256(
                exact_preparation
            ),
            "same_run_acceptance": exact_core_acceptance,
            "same_run_acceptance_sha256": _canonical_sha256(
                exact_core_acceptance
            ),
            "same_run_recovery": True,
        },
        "admission_authority": {
            "sequence": exact_slot["sequence"],
            "slot_path": admission_inbox_slot_path(exact_slot["sequence"]),
            "slot_sha256": exact_slot["slot_sha256"],
            "rerun_path": admission_inbox_rerun_path(exact_slot["sequence"]),
            "rerun_sha256": _canonical_sha256(rerun_record),
            "rerun_intent_sha256": intent["intent_sha256"],
            "acceptance_path": admission_inbox_acceptance_path(
                exact_slot["sequence"]
            ),
            "acceptance_sha256": exact_acceptance["acceptance_sha256"],
            "readback_sha256": _canonical_sha256(
                exact_acceptance["readback"]
            ),
        },
        "slot": exact_slot,
        "rerun_record": dict(rerun_record),
        "acceptance": exact_acceptance,
        "state": "SHARED_CORE_SAME_RUN_ATTEMPT_2_ACCEPTED",
        "effect_ack": "TRANSPORT_ACCEPTED_PENDING_REOBSERVATION",
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["chain_sha256"] = _canonical_sha256(value)
    return value


def validate_admission_attempt_authority_chain(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("admission attempt chain is malformed")
    expected = build_admission_attempt_authority_chain(
        slot=value.get("slot"),
        rerun_record=value.get("rerun_record"),
        acceptance=value.get("acceptance"),
        core_preparation=value.get("core_authority", {}).get(
            "rerun_preparation"
        ),
        core_acceptance=value.get("core_authority", {}).get(
            "same_run_acceptance"
        ),
    )
    if dict(value) != expected:
        raise AdmissionRecoveryError("admission attempt chain differs")
    return dict(value)


def build_terminal_producer_binding(
    receipt: Mapping[str, Any],
    *,
    recovery_repository: str,
    recovery_workflow_id: int,
    recovery_workflow_path: str,
    recovery_head_sha: str,
    recovery_run_id: int,
    recovery_run_attempt: int,
) -> dict[str, Any]:
    """Bind a terminal receipt to its historical trusted-main producer.

    The recovery head is deliberately historical.  Consumers must compare it
    with the producing run, not with today's ``main``; otherwise an old D0=3
    receipt becomes invisible after every ordinary main advance.
    """
    exact = validate_terminal_receipt(receipt)
    if not isinstance(recovery_repository, str) or recovery_repository.count("/") != 1:
        raise AdmissionRecoveryError("terminal producer repository is invalid")
    value = {
        "schema": "qikvrt_review_admission_terminal_producer_binding_v1",
        "receipt_sha256": exact["receipt_sha256"],
        "recovery_repository": recovery_repository,
        "recovery_workflow_id": _positive(
            recovery_workflow_id, "terminal producer workflow id"
        ),
        "recovery_workflow_path": _workflow_path(recovery_workflow_path),
        "recovery_head_sha": _sha(
            recovery_head_sha, "terminal producer head SHA"
        ),
        "recovery_run_id": _positive(
            recovery_run_id, "terminal producer run id"
        ),
        "recovery_run_attempt": _positive(
            recovery_run_attempt, "terminal producer run attempt"
        ),
    }
    value["binding_sha256"] = _canonical_sha256(value)
    return value


def validate_terminal_producer_binding(
    receipt: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    exact = validate_terminal_receipt(receipt)
    if not isinstance(binding, Mapping):
        raise AdmissionRecoveryError("terminal producer binding must be an object")
    value = dict(binding)
    claimed = value.pop("binding_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("terminal producer binding digest differs")
    if (
        value.get("schema")
        != "qikvrt_review_admission_terminal_producer_binding_v1"
        or value.get("receipt_sha256") != exact["receipt_sha256"]
        or not isinstance(value.get("recovery_repository"), str)
        or value["recovery_repository"].count("/") != 1
    ):
        raise AdmissionRecoveryError("terminal producer binding differs")
    _positive(value.get("recovery_workflow_id"), "terminal producer workflow id")
    _workflow_path(value.get("recovery_workflow_path"))
    _sha(value.get("recovery_head_sha"), "terminal producer head SHA")
    _positive(value.get("recovery_run_id"), "terminal producer run id")
    _positive(
        value.get("recovery_run_attempt"), "terminal producer run attempt"
    )
    return dict(binding)


TECHNICAL_REVIEW_MARKER = "qikvrt-mesh-review:v1"


def _repository(value: Any, label: str) -> str:
    if not isinstance(value, str) or value.count("/") != 1:
        raise AdmissionRecoveryError(f"{label} is invalid")
    return value


def _timestamp(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
            value,
        )
    ):
        raise AdmissionRecoveryError(f"{label} is not an exact UTC timestamp")
    return value


def _repo_identity(value: Any, repository: str, label: str) -> None:
    if not isinstance(value, Mapping) or value.get("full_name") != repository:
        raise AdmissionRecoveryError(f"{label} repository differs")


def _review_subject(
    pull_request: Mapping[str, Any],
    commits: Sequence[Mapping[str, Any]],
    *,
    repository: str,
    current_main_sha: str,
    current_main_tree_sha: str,
    commit_observation_mode: str = "COMPLETE_PR_COMMITS",
) -> dict[str, Any]:
    if not isinstance(pull_request, Mapping):
        raise AdmissionRecoveryError("pull request observation is malformed")
    number = _positive(pull_request.get("number"), "pull request number")
    head = pull_request.get("head")
    base = pull_request.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        raise AdmissionRecoveryError("pull request refs are malformed")
    _repo_identity(head.get("repo"), repository, "pull request head")
    _repo_identity(base.get("repo"), repository, "pull request base")
    head_sha = _sha(head.get("sha"), "pull request head SHA")
    base_sha = _sha(base.get("sha"), "pull request base SHA")
    if (
        pull_request.get("state") != "open"
        or base.get("ref") != "main"
        or base_sha != _sha(current_main_sha, "current main SHA")
        or not isinstance(head.get("ref"), str)
        or not head["ref"]
    ):
        raise AdmissionRecoveryError("pull request is not an exact open main subject")
    if not isinstance(commits, Sequence) or isinstance(commits, (str, bytes)):
        raise AdmissionRecoveryError("pull request commits are malformed")
    commit_values = list(commits)
    if not commit_values:
        raise AdmissionRecoveryError("pull request commit list is empty")
    declared_commits = pull_request.get("commits")
    if commit_observation_mode == "COMPLETE_PR_COMMITS":
        if (
            isinstance(declared_commits, bool)
            or not isinstance(declared_commits, int)
            or declared_commits != len(commit_values)
        ):
            raise AdmissionRecoveryError(
                "pull request commit pagination is incomplete"
            )
    elif commit_observation_mode == "EXACT_HEAD_SINGLETON":
        # The pulls/{number}/commits endpoint is capped at 250 and therefore
        # cannot prove completeness for every open PR.  Wake-up recovery only
        # needs the live head/tree binding, so its trusted pre-effect path uses
        # one direct commits/{head} response and makes no history-completeness
        # claim.  The PR's declared commit count is deliberately not compared.
        if len(commit_values) != 1:
            raise AdmissionRecoveryError(
                "exact-head singleton observation has extra commits"
            )
    else:
        raise AdmissionRecoveryError("commit observation mode is invalid")
    commit_shas: list[str] = []
    for commit in commit_values:
        if not isinstance(commit, Mapping):
            raise AdmissionRecoveryError("pull request commit is malformed")
        commit_shas.append(_sha(commit.get("sha"), "pull request commit SHA"))
    if len(set(commit_shas)) != len(commit_shas) or commit_shas[-1] != head_sha:
        raise AdmissionRecoveryError("pull request commit pagination differs from head")
    last_commit = commit_values[-1].get("commit")
    tree = last_commit.get("tree") if isinstance(last_commit, Mapping) else None
    head_tree_sha = _sha(
        tree.get("sha") if isinstance(tree, Mapping) else None,
        "pull request head tree SHA",
    )
    return {
        "repository": repository,
        "pr_number": number,
        "head_sha": head_sha,
        "head_tree_sha": head_tree_sha,
        "head_ref": head["ref"],
        "base_sha": base_sha,
        "base_tree_sha": _sha(
            current_main_tree_sha, "current main tree SHA"
        ),
        "base_ref": "main",
        "commit_observation_mode": commit_observation_mode,
    }


def _review_fact_payload(
    subject: Mapping[str, Any],
    review: Mapping[str, Any],
    *,
    transition_kind: str,
    review_state: str,
    prior_state: str | None = None,
) -> dict[str, Any]:
    user = review.get("user")
    if not isinstance(user, Mapping):
        raise AdmissionRecoveryError("review user is missing")
    value = {
        "schema": "qikvrt_human_review_transition_fact_v2",
        "transition_kind": transition_kind,
        "repository": _repository(subject.get("repository"), "fact repository"),
        "pr_number": _positive(subject.get("pr_number"), "fact PR number"),
        "head_sha": _sha(subject.get("head_sha"), "fact head SHA"),
        "head_tree_sha": _sha(
            subject.get("head_tree_sha"), "fact head tree SHA"
        ),
        "head_ref": subject.get("head_ref"),
        "base_sha": _sha(subject.get("base_sha"), "fact base SHA"),
        "base_tree_sha": _sha(
            subject.get("base_tree_sha"), "fact base tree SHA"
        ),
        "base_ref": subject.get("base_ref"),
        "review_id": _positive(review.get("id"), "review id"),
        "reviewer_id": _positive(user.get("id"), "reviewer id"),
        "reviewer_login": user.get("login"),
        "review_state": review_state,
        "submitted_at": _timestamp(review.get("submitted_at"), "review submission"),
        "commit_id": _sha(review.get("commit_id"), "review commit id"),
        "authority_boundary": "WAKEUP_RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    if (
        value["base_ref"] != "main"
        or not isinstance(value["head_ref"], str)
        or not value["head_ref"]
        or not isinstance(value["reviewer_login"], str)
        or not value["reviewer_login"]
        or not isinstance(review_state, str)
        or not review_state
    ):
        raise AdmissionRecoveryError("review fact identity is malformed")
    if prior_state is not None:
        if not isinstance(prior_state, str) or not prior_state:
            raise AdmissionRecoveryError("prior review state is malformed")
        value["prior_review_state"] = prior_state
    value["fact_fingerprint"] = _canonical_sha256(value)
    return value


def validate_human_review_fact(fact: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(fact, Mapping):
        raise AdmissionRecoveryError("human review fact must be an object")
    value = dict(fact)
    claimed = value.pop("fact_fingerprint", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("human review fact digest differs")
    if (
        value.get("schema") != "qikvrt_human_review_transition_fact_v2"
        or value.get("transition_kind") not in {"REVIEW_STATE", "REVIEW_ABSENT"}
        or value.get("base_ref") != "main"
        or value.get("authority_boundary") != "WAKEUP_RECOVERY_ONLY"
        or value.get("native_account_review_authorized") is not False
        or value.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("human review fact boundary differs")
    _repository(value.get("repository"), "fact repository")
    _positive(value.get("pr_number"), "fact PR number")
    if not isinstance(value.get("head_ref"), str) or not value["head_ref"]:
        raise AdmissionRecoveryError("fact head ref is malformed")
    for field in ("head_sha", "head_tree_sha", "base_sha", "base_tree_sha", "commit_id"):
        _sha(value.get(field), f"fact {field}")
    _positive(value.get("review_id"), "fact review id")
    _positive(value.get("reviewer_id"), "fact reviewer id")
    if not isinstance(value.get("reviewer_login"), str) or not value["reviewer_login"]:
        raise AdmissionRecoveryError("fact reviewer login is malformed")
    _timestamp(value.get("submitted_at"), "fact submission")
    state = value.get("review_state")
    if not isinstance(state, str) or not state:
        raise AdmissionRecoveryError("fact review state is malformed")
    if value["transition_kind"] == "REVIEW_ABSENT":
        if state != "ABSENT" or not isinstance(value.get("prior_review_state"), str):
            raise AdmissionRecoveryError("absent review fact is malformed")
    elif "prior_review_state" in value:
        raise AdmissionRecoveryError("state review fact has prior state")
    return dict(fact)


def build_direct_review_observation(
    *, review_id: int, review: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Seal one exact review-ID GET without retaining untrusted review body."""
    exact_id = _positive(review_id, "direct review observation id")
    value: dict[str, Any] = {
        "schema": "qikvrt_direct_review_observation_v1",
        "review_id": exact_id,
        "exact_get_complete": True,
        "authority_boundary": "WAKEUP_RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    if review is None:
        value.update({"state": "NOT_FOUND", "review": None})
    else:
        if not isinstance(review, Mapping) or review.get("id") != exact_id:
            raise AdmissionRecoveryError("direct review observation identity differs")
        user = review.get("user")
        if not isinstance(user, Mapping):
            raise AdmissionRecoveryError("direct review observation user is missing")
        state = review.get("state")
        if not isinstance(state, str) or not state:
            raise AdmissionRecoveryError("direct review observation state is missing")
        value.update({
            "state": "FOUND",
            "review": {
                "id": exact_id,
                "user": {
                    "id": _positive(
                        user.get("id"), "direct review observation user id"
                    ),
                    "login": user.get("login"),
                    "type": user.get("type"),
                },
                "state": state.upper(),
                "submitted_at": _timestamp(
                    review.get("submitted_at"),
                    "direct review observation submission",
                ),
                "commit_id": _sha(
                    review.get("commit_id"),
                    "direct review observation commit id",
                ),
            },
        })
        projected_user = value["review"]["user"]
        if (
            not isinstance(projected_user["login"], str)
            or not projected_user["login"]
            or not isinstance(projected_user["type"], str)
            or not projected_user["type"]
        ):
            raise AdmissionRecoveryError(
                "direct review observation user identity is malformed"
            )
    value["observation_sha256"] = _canonical_sha256(value)
    return value


def validate_direct_review_observation(
    value: Mapping[str, Any], *, review_id: int
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("direct review observation is malformed")
    observed = dict(value)
    claimed = observed.pop("observation_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("direct review observation digest differs")
    exact_id = _positive(review_id, "direct review observation id")
    if (
        observed.get("schema") != "qikvrt_direct_review_observation_v1"
        or observed.get("review_id") != exact_id
        or observed.get("exact_get_complete") is not True
        or observed.get("authority_boundary") != "WAKEUP_RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("direct review observation boundary differs")
    state = observed.get("state")
    review = observed.get("review")
    if state == "NOT_FOUND":
        if review is not None:
            raise AdmissionRecoveryError("missing review observation contains review")
    elif state == "FOUND":
        if not isinstance(review, Mapping) or review.get("id") != exact_id:
            raise AdmissionRecoveryError("found review observation identity differs")
        user = review.get("user")
        if not isinstance(user, Mapping):
            raise AdmissionRecoveryError("found review observation user is missing")
        _positive(user.get("id"), "found review observation user id")
        if (
            not isinstance(user.get("login"), str)
            or not user["login"]
            or not isinstance(user.get("type"), str)
            or not user["type"]
            or not isinstance(review.get("state"), str)
            or not review["state"]
        ):
            raise AdmissionRecoveryError("found review observation differs")
        _timestamp(review.get("submitted_at"), "found review submission")
        _sha(review.get("commit_id"), "found review commit id")
        if "body" in review:
            raise AdmissionRecoveryError("direct review body must not be sealed")
    else:
        raise AdmissionRecoveryError("direct review observation state differs")
    return dict(value)


def review_observation_scan_path() -> str:
    return ".qikvrt/recovery/review-wakeup/observation-scan.json"


def review_observation_queue_meta_path() -> str:
    return ".qikvrt/recovery/review-wakeup/observation-queue-meta.json"


def review_observation_slot_path(sequence: int) -> str:
    return (
        ".qikvrt/recovery/review-wakeup/observation-slots/"
        f"{_positive(sequence, 'review observation sequence'):020d}.json"
    )


def review_observation_locator_path(fingerprint: str) -> str:
    if not isinstance(fingerprint, str) or re.fullmatch(
        r"[0-9a-f]{64}", fingerprint
    ) is None:
        raise AdmissionRecoveryError("review observation fingerprint is invalid")
    return (
        ".qikvrt/recovery/review-wakeup/observation-fingerprints/"
        f"{fingerprint[:2]}/{fingerprint}.json"
    )


def review_observation_subject_cursor_path(pr_number: int) -> str:
    return (
        ".qikvrt/recovery/review-wakeup/observation-subjects/"
        f"pr-{_positive(pr_number, 'review observation PR number')}.json"
    )


def build_review_observation_subject_cursor(
    pull_request: Mapping[str, Any],
    commits: Sequence[Mapping[str, Any]],
    *,
    repository: str,
    current_main_sha: str,
    current_main_tree_sha: str,
    next_review_page: int,
    generation: int,
    commit_observation_mode: str = "COMPLETE_PR_COMMITS",
    last_ack_review_id: int | None = None,
    last_ack_fact_fingerprint: str | None = None,
) -> dict[str, Any]:
    subject = _review_subject(
        pull_request,
        commits,
        repository=repository,
        current_main_sha=current_main_sha,
        current_main_tree_sha=current_main_tree_sha,
        commit_observation_mode=commit_observation_mode,
    )
    page = _positive(next_review_page, "review observation resume page")
    if page < 1:
        raise AdmissionRecoveryError("review observation resume page differs")
    if (last_ack_review_id is None) != (last_ack_fact_fingerprint is None):
        raise AdmissionRecoveryError("review observation ACK cursor is partial")
    ack_cursor = None
    if last_ack_review_id is not None:
        ack_cursor = {
            "review_id": _positive(
                last_ack_review_id, "review observation ACK review id"
            ),
            "fact_fingerprint": _digest(
                last_ack_fact_fingerprint,
                "review observation ACK fact fingerprint",
            ),
        }
    minimal_pull = {
        "number": subject["pr_number"],
        "commits": pull_request.get("commits"),
        "state": "open",
        "head": {
            "sha": subject["head_sha"], "ref": subject["head_ref"],
            "repo": {"full_name": subject["repository"]},
        },
        "base": {
            "sha": subject["base_sha"], "ref": "main",
            "repo": {"full_name": subject["repository"]},
        },
    }
    minimal_commits: list[dict[str, Any]] = []
    for item in commits:
        if not isinstance(item, Mapping):
            raise AdmissionRecoveryError("review observation resume commit differs")
        detail = item.get("commit")
        tree = detail.get("tree") if isinstance(detail, Mapping) else None
        minimal_commits.append({
            "sha": _sha(
                item.get("sha"), "review observation resume commit SHA"
            ),
            "commit": {"tree": {"sha": _sha(
                tree.get("sha") if isinstance(tree, Mapping) else None,
                "review observation resume commit tree SHA",
            )}},
        })
    value = {
        "schema": "qikvrt_human_review_observation_subject_cursor_v1",
        "subject": subject,
        "pull": minimal_pull,
        "commits": minimal_commits,
        "next_review_page": page,
        "generation": _positive(generation, "review observation generation"),
        "quantum_pages": 1,
        "ack_recheck_quantum": 1,
        "last_ack_cursor": ack_cursor,
        "authority_boundary": "RECOVERY_ONLY",
    }
    value["cursor_sha256"] = _canonical_sha256(value)
    return value


def validate_review_observation_subject_cursor(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review observation subject cursor is malformed")
    observed = dict(value)
    claimed = observed.pop("cursor_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("review observation subject cursor digest differs")
    commits = observed.get("commits")
    pull = observed.get("pull")
    subject = observed.get("subject")
    if (
        observed.get("schema")
            != "qikvrt_human_review_observation_subject_cursor_v1"
        or not isinstance(subject, Mapping)
        or not isinstance(pull, Mapping)
        or not isinstance(commits, list)
        or len(commits) > 250
        or observed.get("quantum_pages") != 1
        or observed.get("ack_recheck_quantum") != 1
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
    ):
        raise AdmissionRecoveryError("review observation subject cursor differs")
    rebuilt = _review_subject(
        pull,
        commits,
        repository=subject.get("repository"),
        current_main_sha=subject.get("base_sha"),
        current_main_tree_sha=subject.get("base_tree_sha"),
        commit_observation_mode=subject.get("commit_observation_mode"),
    )
    if rebuilt != subject:
        raise AdmissionRecoveryError("review observation resume subject differs")
    _positive(observed.get("next_review_page"), "review observation resume page")
    _positive(observed.get("generation"), "review observation resume generation")
    ack_cursor = observed.get("last_ack_cursor")
    if ack_cursor is not None:
        if not isinstance(ack_cursor, Mapping):
            raise AdmissionRecoveryError("review observation ACK cursor is malformed")
        _positive(ack_cursor.get("review_id"), "review observation ACK review id")
        _digest(
            ack_cursor.get("fact_fingerprint"),
            "review observation ACK fact fingerprint",
        )
    return dict(value)


def empty_review_observation_queue_meta() -> dict[str, Any]:
    return {
        "schema": "qikvrt_human_review_observation_queue_meta_v1",
        "next_sequence": 1,
        "drain_sequence": 1,
        "authority_boundary": "RECOVERY_ONLY",
    }


def validate_review_observation_queue_meta(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review observation queue metadata is malformed")
    if (
        value.get("schema")
            != "qikvrt_human_review_observation_queue_meta_v1"
        or value.get("authority_boundary") != "RECOVERY_ONLY"
    ):
        raise AdmissionRecoveryError("review observation queue boundary differs")
    next_sequence = _positive(
        value.get("next_sequence"), "review observation next sequence"
    )
    drain_sequence = _positive(
        value.get("drain_sequence"), "review observation drain sequence"
    )
    if drain_sequence > next_sequence:
        raise AdmissionRecoveryError("review observation drain exceeds next")
    return dict(value)


def empty_review_observation_scan() -> dict[str, Any]:
    return {
        "schema": "qikvrt_human_review_observation_scan_v1",
        "generation": 1,
        "pull_page": 1,
        "active": None,
        "pull_page_size": 1,
        "item_page_size": 100,
        "authority_boundary": "RECOVERY_ONLY",
    }


def validate_review_observation_scan(
    value: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review observation scan is malformed")
    if (
        value.get("schema") != "qikvrt_human_review_observation_scan_v1"
        or value.get("pull_page_size") != 1
        or value.get("item_page_size") != 100
        or value.get("authority_boundary") != "RECOVERY_ONLY"
    ):
        raise AdmissionRecoveryError("review observation scan boundary differs")
    _positive(value.get("generation"), "review scan generation")
    _positive(value.get("pull_page"), "review scan pull page")
    active = value.get("active")
    if active is not None:
        if not isinstance(active, Mapping):
            raise AdmissionRecoveryError("review scan active subject is malformed")
        if active.get("stage") not in {
            "COMMITS", "REVIEWS", "ACK_RECHECK"
        }:
            raise AdmissionRecoveryError("review scan active stage differs")
        _positive(active.get("page"), "review scan active page")
        pull = active.get("pull")
        commits = active.get("commits")
        facts = active.get("facts")
        if (
            not isinstance(pull, Mapping)
            or not isinstance(commits, list)
            or not isinstance(facts, list)
            or any(not isinstance(item, Mapping) for item in commits)
        ):
            raise AdmissionRecoveryError("review scan active payload differs")
        fingerprints: set[str] = set()
        for fact in facts:
            exact = validate_human_review_fact(fact)
            if exact["fact_fingerprint"] in fingerprints:
                raise AdmissionRecoveryError("review scan active fact is duplicated")
            fingerprints.add(exact["fact_fingerprint"])
        seen_ids = active.get("seen_review_ids")
        if (
            not isinstance(seen_ids, list)
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item < 1
                for item in seen_ids
            )
            or len(set(seen_ids)) != len(seen_ids)
        ):
            raise AdmissionRecoveryError("review scan seen IDs differ")
        acknowledged = active.get("acknowledged_facts", [])
        if not isinstance(acknowledged, list):
            raise AdmissionRecoveryError("review scan ACK cursor is malformed")
        for fact in acknowledged:
            validate_human_review_fact(fact)
        ack_index = active.get("ack_index", 0)
        if (
            isinstance(ack_index, bool)
            or not isinstance(ack_index, int)
            or ack_index < 0
            or ack_index > len(acknowledged)
            or (active.get("stage") == "ACK_RECHECK" and not acknowledged)
        ):
            raise AdmissionRecoveryError("review scan ACK index differs")
        ack_cursor = active.get("last_ack_cursor")
        if ack_cursor is not None:
            if not isinstance(ack_cursor, Mapping):
                raise AdmissionRecoveryError("review scan ACK cursor differs")
            _positive(ack_cursor.get("review_id"), "review scan ACK review id")
            _digest(
                ack_cursor.get("fact_fingerprint"),
                "review scan ACK fact fingerprint",
            )
        for field in ("base_sha", "base_tree_sha"):
            _sha(active.get(field), f"review scan {field}")
    return dict(value)


def build_review_observation_slot(
    fact: Mapping[str, Any], *, sequence: int, generation: int,
    covered_facts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    exact = validate_human_review_fact(fact)
    raw_covered = [exact] if covered_facts is None else list(covered_facts)
    covered = [validate_human_review_fact(item) for item in raw_covered]
    covered.sort(key=lambda item: (
        item["submitted_at"], item["review_id"], item["fact_fingerprint"]
    ))
    subject_key = review_wakeup_subject_key(exact)
    if (
        not covered or len(covered) > 100 or covered[0] != exact
        or len({item["fact_fingerprint"] for item in covered}) != len(covered)
        or any(review_wakeup_subject_key(item) != subject_key for item in covered)
    ):
        raise AdmissionRecoveryError("review observation covered facts differ")
    value = {
        "schema": "qikvrt_human_review_observation_slot_v1",
        "sequence": _positive(sequence, "review observation sequence"),
        "generation": _positive(generation, "review observation generation"),
        "fact_fingerprint": exact["fact_fingerprint"],
        "fact": exact,
        "covered_facts": covered,
        "covered_fact_fingerprints": [
            item["fact_fingerprint"] for item in covered
        ],
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["slot_sha256"] = _canonical_sha256(value)
    return value


def validate_review_observation_slot(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review observation slot is malformed")
    observed = dict(value)
    claimed = observed.pop("slot_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("review observation slot digest differs")
    fact = validate_human_review_fact(observed.get("fact"))
    covered_raw = observed.get("covered_facts")
    if not isinstance(covered_raw, list):
        raise AdmissionRecoveryError("review observation covered facts are malformed")
    covered = [validate_human_review_fact(item) for item in covered_raw]
    if (
        observed.get("schema") != "qikvrt_human_review_observation_slot_v1"
        or observed.get("sequence") != _positive(
            observed.get("sequence"), "review observation sequence"
        )
        or observed.get("generation") != _positive(
            observed.get("generation"), "review observation generation"
        )
        or observed.get("fact_fingerprint") != fact["fact_fingerprint"]
        or not covered or len(covered) > 100 or covered[0] != fact
        or observed.get("covered_fact_fingerprints") != [
            item["fact_fingerprint"] for item in covered
        ]
        or len(set(observed["covered_fact_fingerprints"])) != len(covered)
        or any(
            review_wakeup_subject_key(item) != review_wakeup_subject_key(fact)
            for item in covered
        )
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("review observation slot boundary differs")
    return dict(value)


def observe_human_review_facts(
    pull_requests: Sequence[Mapping[str, Any]],
    *,
    reviews_by_pr: Mapping[int, Sequence[Mapping[str, Any]]],
    commits_by_pr: Mapping[int, Sequence[Mapping[str, Any]]],
    repository: str,
    current_main_sha: str,
    current_main_tree_sha: str,
    technical_marker: str = TECHNICAL_REVIEW_MARKER,
    commit_observation_mode: str = "COMPLETE_PR_COMMITS",
) -> dict[str, Any]:
    """Build exact current-head human-review facts from complete observations."""
    repo = _repository(repository, "review observation repository")
    if not isinstance(pull_requests, Sequence) or isinstance(
        pull_requests, (str, bytes)
    ):
        raise AdmissionRecoveryError("pull request observations are malformed")
    if not isinstance(reviews_by_pr, Mapping) or not isinstance(commits_by_pr, Mapping):
        raise AdmissionRecoveryError("review observation pages are malformed")
    if not isinstance(technical_marker, str) or not technical_marker:
        raise AdmissionRecoveryError("technical review marker is missing")
    subjects: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    seen_prs: set[int] = set()
    for pull_request in pull_requests:
        if not isinstance(pull_request, Mapping):
            raise AdmissionRecoveryError("pull request observation is malformed")
        number = _positive(pull_request.get("number"), "pull request number")
        if number in seen_prs:
            raise AdmissionRecoveryError("duplicate pull request observation")
        seen_prs.add(number)
        reviews = reviews_by_pr.get(number)
        commits = commits_by_pr.get(number)
        if (
            not isinstance(reviews, Sequence)
            or isinstance(reviews, (str, bytes))
            or not isinstance(commits, Sequence)
            or isinstance(commits, (str, bytes))
        ):
            raise AdmissionRecoveryError("pull request review/commit pages are missing")
        subject = _review_subject(
            pull_request,
            commits,
            repository=repo,
            current_main_sha=current_main_sha,
            current_main_tree_sha=current_main_tree_sha,
            commit_observation_mode=commit_observation_mode,
        )
        review_ids: list[int] = []
        excluded_ids: list[int] = []
        for review in reviews:
            if not isinstance(review, Mapping):
                raise AdmissionRecoveryError("review observation is malformed")
            review_id = _positive(review.get("id"), "review id")
            if review_id in review_ids:
                raise AdmissionRecoveryError("duplicate review observation")
            review_ids.append(review_id)
            user = review.get("user")
            if not isinstance(user, Mapping):
                raise AdmissionRecoveryError("review user is missing")
            login = user.get("login")
            is_bot = (
                str(user.get("type", "")).casefold() == "bot"
                or (isinstance(login, str) and login.casefold().endswith("[bot]"))
            )
            # Public marker text is untrusted and can be quoted by any human.
            # The repository-owned technical projection uses the exact
            # github-actions[bot] identity, already excluded above.
            if is_bot:
                excluded_ids.append(review_id)
                continue
            state = review.get("state")
            if not isinstance(state, str) or not state:
                raise AdmissionRecoveryError("review state is missing")
            state = state.upper()
            if state == "PENDING" or review.get("submitted_at") is None:
                continue
            if review.get("commit_id") != subject["head_sha"]:
                continue
            facts.append(
                _review_fact_payload(
                    subject,
                    review,
                    transition_kind="REVIEW_STATE",
                    review_state=state,
                )
            )
        subjects.append(
            {
                **subject,
                "observed_review_ids": sorted(review_ids),
                "excluded_review_ids": sorted(excluded_ids),
            }
        )
    facts.sort(
        key=lambda item: (
            item["submitted_at"], item["pr_number"], item["review_id"],
            item["review_state"], item["fact_fingerprint"],
        )
    )
    return {
        "schema": "qikvrt_human_review_observation_v1",
        "repository": repo,
        "current_main_sha": _sha(current_main_sha, "current main SHA"),
        "current_main_tree_sha": _sha(
            current_main_tree_sha, "current main tree SHA"
        ),
        "subjects": subjects,
        "facts": facts,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }


def build_review_absence_facts(
    observation: Mapping[str, Any],
    acknowledged_facts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Turn an ACKed exact-head review's later absence into a tombstone fact."""
    if not isinstance(observation, Mapping) or observation.get("schema") != (
        "qikvrt_human_review_observation_v1"
    ):
        raise AdmissionRecoveryError("human review observation is malformed")
    if not isinstance(acknowledged_facts, Sequence) or isinstance(
        acknowledged_facts, (str, bytes)
    ):
        raise AdmissionRecoveryError("acknowledged review facts are malformed")
    subjects = {
        (subject["repository"], subject["pr_number"]): subject
        for subject in observation.get("subjects", [])
        if isinstance(subject, Mapping)
    }
    result: dict[str, dict[str, Any]] = {}
    for raw in acknowledged_facts:
        previous = validate_human_review_fact(raw)
        if previous["transition_kind"] != "REVIEW_STATE":
            continue
        subject = subjects.get((previous["repository"], previous["pr_number"]))
        if not isinstance(subject, Mapping):
            continue
        exact_subject = all(
            previous[field] == subject[field]
            for field in (
                "head_sha", "head_tree_sha", "head_ref", "base_sha", "base_tree_sha",
                "base_ref",
            )
        )
        if not exact_subject or previous["review_id"] in subject["observed_review_ids"]:
            continue
        review = {
            "id": previous["review_id"],
            "user": {
                "id": previous["reviewer_id"],
                "login": previous["reviewer_login"],
            },
            "submitted_at": previous["submitted_at"],
            "commit_id": previous["commit_id"],
        }
        absence = _review_fact_payload(
            subject,
            review,
            transition_kind="REVIEW_ABSENT",
            review_state="ABSENT",
            prior_state=previous["review_state"],
        )
        result[absence["fact_fingerprint"]] = absence
    return sorted(
        result.values(),
        key=lambda item: (
            item["submitted_at"], item["pr_number"], item["review_id"],
            item["fact_fingerprint"],
        ),
    )


def build_review_wakeup_intent(
    fact: Mapping[str, Any],
    *,
    head_ref: str,
    recovery_repository: str,
    recovery_repository_id: int,
    recovery_workflow_id: int,
    recovery_workflow_path: str,
    recovery_head_sha: str,
    requested_workflow_id: int,
    requested_workflow_path: str,
    requested_workflow_sha: str,
) -> dict[str, Any]:
    exact_fact = validate_human_review_fact(fact)
    recovery_sha = _sha(recovery_head_sha, "review wake-up recovery head SHA")
    evaluator_sha = _sha(
        requested_workflow_sha, "requested-review evaluator SHA"
    )
    if evaluator_sha != recovery_sha:
        raise AdmissionRecoveryError("requested-review evaluator is not current main")
    if not isinstance(head_ref, str) or not head_ref:
        raise AdmissionRecoveryError("review wake-up head ref is missing")
    if head_ref != exact_fact["head_ref"]:
        raise AdmissionRecoveryError("review wake-up head ref differs from fact")
    if recovery_repository != exact_fact["repository"]:
        raise AdmissionRecoveryError("review wake-up repository differs from fact")
    fingerprint = exact_fact["fact_fingerprint"]
    core_subject = {
        "pull_request": exact_fact["pr_number"],
        "head_repository": exact_fact["repository"],
        "head_ref": head_ref,
        "head_sha": exact_fact["head_sha"],
        "head_tree_sha": exact_fact["head_tree_sha"],
        "base_ref": exact_fact["base_ref"],
        "base_sha": exact_fact["base_sha"],
    }
    value = {
        "schema": "qikvrt_human_review_wakeup_intent_v2",
        "fact": exact_fact,
        "fact_fingerprint": fingerprint,
        "head_ref": head_ref,
        "core_lane": "exact-review-dispatch",
        "core_subject": core_subject,
        "recovery_repository": _repository(
            recovery_repository, "review wake-up repository"
        ),
        "recovery_repository_id": _positive(
            recovery_repository_id, "review wake-up repository id"
        ),
        "recovery_workflow_id": _positive(
            recovery_workflow_id, "review wake-up workflow id"
        ),
        "recovery_workflow_path": _workflow_path(recovery_workflow_path),
        "recovery_head_sha": recovery_sha,
        "requested_workflow_id": _positive(
            requested_workflow_id, "requested-review workflow id"
        ),
        "requested_workflow_path": _workflow_path(requested_workflow_path),
        "requested_workflow_sha": evaluator_sha,
        "max_transport_attempts": 1,
        "authority_boundary": "WAKEUP_RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["intent_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(intent, Mapping):
        raise AdmissionRecoveryError("review wake-up intent must be an object")
    value = dict(intent)
    claimed = value.pop("intent_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("review wake-up intent digest differs")
    if (
        value.get("schema") != "qikvrt_human_review_wakeup_intent_v2"
        or value.get("max_transport_attempts") != 1
        or value.get("authority_boundary") != "WAKEUP_RECOVERY_ONLY"
        or value.get("native_account_review_authorized") is not False
        or value.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("review wake-up intent boundary differs")
    fact = validate_human_review_fact(value.get("fact"))
    if fact["fact_fingerprint"] != value.get("fact_fingerprint"):
        raise AdmissionRecoveryError("review wake-up fact binding differs")
    if not isinstance(value.get("head_ref"), str) or not value["head_ref"]:
        raise AdmissionRecoveryError("review wake-up head ref is missing")
    expected_subject = {
        "pull_request": fact["pr_number"],
        "head_repository": fact["repository"],
        "head_ref": value["head_ref"],
        "head_sha": fact["head_sha"],
        "head_tree_sha": fact["head_tree_sha"],
        "base_ref": fact["base_ref"],
        "base_sha": fact["base_sha"],
    }
    if (
        value.get("core_lane") != "exact-review-dispatch"
        or value.get("core_subject") != expected_subject
    ):
        raise AdmissionRecoveryError("review wake-up Core subject differs")
    _repository(value.get("recovery_repository"), "review wake-up repository")
    _positive(value.get("recovery_repository_id"), "review wake-up repository id")
    _positive(value.get("recovery_workflow_id"), "review wake-up workflow id")
    _workflow_path(value.get("recovery_workflow_path"))
    recovery_sha = _sha(value.get("recovery_head_sha"), "review wake-up head SHA")
    _positive(value.get("requested_workflow_id"), "requested-review workflow id")
    _workflow_path(value.get("requested_workflow_path"))
    if _sha(value.get("requested_workflow_sha"), "requested-review SHA") != recovery_sha:
        raise AdmissionRecoveryError("review wake-up evaluator differs from main")
    expected = build_review_wakeup_intent(
        fact,
        head_ref=value["head_ref"],
        recovery_repository=value["recovery_repository"],
        recovery_repository_id=value["recovery_repository_id"],
        recovery_workflow_id=value["recovery_workflow_id"],
        recovery_workflow_path=value["recovery_workflow_path"],
        recovery_head_sha=recovery_sha,
        requested_workflow_id=value["requested_workflow_id"],
        requested_workflow_path=value["requested_workflow_path"],
        requested_workflow_sha=value["requested_workflow_sha"],
    )
    if expected != dict(intent):
        raise AdmissionRecoveryError("review wake-up intent projection differs")
    return dict(intent)


def build_review_wakeup_core_payload(
    intent: Mapping[str, Any],
    *,
    producer_run_id: int,
    producer_run_attempt: int,
    producer_event: str,
    producer_workflow_sha: str | None = None,
) -> dict[str, Any]:
    """Materialize the sole Shared-Core exact-review work unit for a wake-up.

    The custom wake-up ledger seals only the human fact and its recovery
    lifecycle.  This payload moves transport authority to the existing
    ``exact-review-dispatch`` FIFO.  Producer bytes may change when a later
    schedule adds an idempotent witness, while Core's semantic work-unit hash
    remains stable because subject, evaluator, target and request are exact.
    """
    from tools.qikvrt_ruleset_outbox import seal_review_transport_payload

    exact = validate_review_wakeup_intent(intent)
    actual_producer_sha = _sha(
        producer_workflow_sha or exact["recovery_head_sha"],
        "review wake-up Core producer workflow SHA",
    )
    if producer_event not in {"schedule", "workflow_dispatch"}:
        raise AdmissionRecoveryError("review wake-up Core producer event differs")
    fact = exact["fact"]
    draft = {
        "schema": "qikvrt_ruleset_outbox_payload_v1",
        "repository": exact["recovery_repository"],
        "lane": "exact-review-dispatch",
        "main_head_sha": exact["requested_workflow_sha"],
        "producer": {
            "workflow_path": exact["recovery_workflow_path"],
            "workflow_sha": actual_producer_sha,
            "workflow_id": exact["recovery_workflow_id"],
            "run_id": _positive(producer_run_id, "review wake-up Core producer run"),
            "run_attempt": _positive(
                producer_run_attempt, "review wake-up Core producer attempt"
            ),
            "event": producer_event,
        },
        "subject": exact["core_subject"],
        "target": {
            "workflow_id": exact["requested_workflow_id"],
            "workflow_path": exact["requested_workflow_path"],
            "event": "workflow_dispatch",
        },
        "request": {
            "ref": "main",
            "return_run_details": True,
            "inputs": {
                "pr": str(fact["pr_number"]),
                "head": fact["head_sha"],
                "fingerprint": fact["fact_fingerprint"],
                "evaluator_sha": exact["requested_workflow_sha"],
                "transport_intent_sha256": "0" * 64,
                "transport_attempt": "1",
            },
        },
        "causal": {
            "d0": 2,
            "state": "HUMAN_REVIEW_WAKEUP",
            "productive_effect": False,
        },
    }
    return seal_review_transport_payload(draft, attempt=1)


def validate_review_wakeup_core_payload(
    value: Mapping[str, Any], intent: Mapping[str, Any]
) -> dict[str, Any]:
    from tools.qikvrt_ruleset_outbox import validate_payload

    exact = validate_review_wakeup_intent(intent)
    payload = validate_payload(value, lane="exact-review-dispatch")
    if not isinstance(value, Mapping) or dict(value) != payload:
        raise AdmissionRecoveryError("review wake-up Core payload is not canonical")
    fact = exact["fact"]
    subject = payload["subject"]
    inputs = payload["request"]["inputs"]
    if (
        payload["repository"] != exact["recovery_repository"]
        or payload["main_head_sha"] != exact["requested_workflow_sha"]
        or payload["producer"]["workflow_path"]
        != exact["recovery_workflow_path"]
        or not re.fullmatch(
            r"[0-9a-f]{40}", str(payload["producer"]["workflow_sha"])
        )
        or payload["producer"]["workflow_id"] != exact["recovery_workflow_id"]
        or payload["producer"]["event"] not in {"schedule", "workflow_dispatch"}
        or subject != exact["core_subject"]
        or payload["target"]
        != {
            "workflow_id": exact["requested_workflow_id"],
            "workflow_path": exact["requested_workflow_path"],
            "event": "workflow_dispatch",
        }
        or inputs["pr"] != str(fact["pr_number"])
        or inputs["head"] != fact["head_sha"]
        or inputs["fingerprint"] != fact["fact_fingerprint"]
        or inputs["evaluator_sha"] != exact["requested_workflow_sha"]
        or inputs["transport_attempt"] != "1"
        or payload["causal"]
        != {"d0": 2, "state": "HUMAN_REVIEW_WAKEUP", "productive_effect": False}
    ):
        raise AdmissionRecoveryError("review wake-up Core payload differs")
    from tools.qikvrt_ruleset_outbox import digest as core_digest, semantic_work_unit

    if inputs["transport_intent_sha256"] != core_digest(
        semantic_work_unit(payload)
    ):
        raise AdmissionRecoveryError("review wake-up Core fingerprint differs")
    return payload


def review_wakeup_core_fingerprint(
    intent: Mapping[str, Any], payload: Mapping[str, Any]
) -> str:
    from tools.qikvrt_ruleset_outbox import digest as core_digest, semantic_work_unit

    exact = validate_review_wakeup_core_payload(payload, intent)
    return core_digest(semantic_work_unit(exact))


def review_wakeup_child_title(
    intent: Mapping[str, Any], *, transport_attempt: int,
    core_payload: Mapping[str, Any],
) -> str:
    """Return the complete, API-observable requested-child locator.

    The locator is derived only after the durable intent has its content hash,
    avoiding a self-referential digest while making the sole transport
    independently adoptable after a producer crash.
    """
    exact = validate_review_wakeup_intent(intent)
    attempt = _positive(transport_attempt, "review wake-up transport attempt")
    if attempt != 1:
        raise AdmissionRecoveryError("review wake-up transport attempt exceeds bound")
    fact = exact["fact"]
    core_fingerprint = review_wakeup_core_fingerprint(exact, core_payload)
    title = (
        f"qikvrt-rr-v3 e={exact['requested_workflow_sha']} "
        f"p={fact['pr_number']} h={fact['head_sha']} "
        f"f={fact['fact_fingerprint']} i={core_fingerprint} a={attempt}"
    )
    if len(title.encode("utf-8")) >= 255:
        raise AdmissionRecoveryError("review wake-up child locator is too long")
    return title


def review_wakeup_dispatch_request(
    intent: Mapping[str, Any], *, transport_attempt: int,
    core_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive the secret-free dispatch body from one durable intent attempt."""
    exact = validate_review_wakeup_intent(intent)
    attempt = _positive(transport_attempt, "review wake-up transport attempt")
    if attempt != 1:
        raise AdmissionRecoveryError("review wake-up transport attempt exceeds bound")
    from tools.qikvrt_ruleset_outbox import request_for_transport_attempt

    payload = validate_review_wakeup_core_payload(core_payload, exact)
    core_fingerprint = review_wakeup_core_fingerprint(exact, payload)
    core_intent = {
        "lane": "exact-review-dispatch",
        "fingerprint": core_fingerprint,
        "payload": payload,
    }
    return request_for_transport_attempt(core_intent, attempt)


def build_review_wakeup_orphan_observation(
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    observed_to: str,
    filtered_run_ids: Sequence[int],
) -> dict[str, Any]:
    """Seal a complete sub-1,000 window proving no exact bound child."""
    exact = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(exact, binding)
    upper = _timestamp(observed_to, "review wake-up lookup upper bound")
    lower = producer["orphan_lookup_created_from"]
    if not lower < upper:
        raise AdmissionRecoveryError("review wake-up lookup window order differs")
    if not isinstance(filtered_run_ids, Sequence) or isinstance(
        filtered_run_ids, (str, bytes)
    ):
        raise AdmissionRecoveryError("review wake-up lookup run IDs are malformed")
    ids = [
        _positive(item, "review wake-up lookup run id")
        for item in filtered_run_ids
    ]
    if len(ids) >= 1000 or len(set(ids)) != len(ids):
        raise AdmissionRecoveryError("review wake-up lookup exceeds safe cap")
    value = {
        "schema": "qikvrt_human_review_wakeup_orphan_observation_v1",
        "intent_sha256": exact["intent_sha256"],
        "fact_fingerprint": exact["fact_fingerprint"],
        "producer_binding_sha256": producer["binding_sha256"],
        "transport_attempt": producer["transport_attempt"],
        "created_from": lower,
        "created_to": upper,
        "filtered_total_count": len(ids),
        "filtered_run_ids_sha256": _canonical_sha256(ids),
        "exact_matching_child_run_ids": [],
        "complete": True,
        "filtered_result_cap_not_reached": True,
        "result": "ORPHAN_NO_BOUND_SUCCESSOR",
        "authority_boundary": "RECOVERY_ONLY",
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["observation_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_orphan_observation(
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(exact, binding)
    if not isinstance(observation, Mapping):
        raise AdmissionRecoveryError("review wake-up orphan observation is malformed")
    value = dict(observation)
    claimed = value.pop("observation_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("review wake-up orphan observation digest differs")
    if (
        value.get("schema")
            != "qikvrt_human_review_wakeup_orphan_observation_v1"
        or value.get("intent_sha256") != exact["intent_sha256"]
        or value.get("fact_fingerprint") != exact["fact_fingerprint"]
        or value.get("producer_binding_sha256") != producer["binding_sha256"]
        or value.get("transport_attempt") != producer["transport_attempt"]
        or value.get("created_from") != producer["orphan_lookup_created_from"]
        or value.get("exact_matching_child_run_ids") != []
        or value.get("complete") is not True
        or value.get("filtered_result_cap_not_reached") is not True
        or value.get("result") != "ORPHAN_NO_BOUND_SUCCESSOR"
        or value.get("authority_boundary") != "RECOVERY_ONLY"
        or value.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("review wake-up orphan observation differs")
    _timestamp(value.get("created_to"), "review wake-up lookup upper bound")
    total = value.get("filtered_total_count")
    frontier_sha = value.get("frontier_sha256")
    if (
        isinstance(total, bool)
        or not isinstance(total, int)
        or total < 0
        or (frontier_sha is None and total >= 1000)
    ):
        raise AdmissionRecoveryError("review wake-up lookup total differs")
    if frontier_sha is not None:
        _digest(frontier_sha, "review wake-up orphan frontier digest")
    _digest(
        value.get("filtered_run_ids_sha256"),
        "review wake-up lookup run IDs digest",
    )
    return dict(observation)


def review_wakeup_orphan_frontier_path(
    intent: Mapping[str, Any], binding: Mapping[str, Any]
) -> str:
    """Return the O(1) shard for one exact transport-attempt lookup."""
    exact = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(exact, binding)
    fingerprint = exact["fact_fingerprint"]
    return (
        ".qikvrt/recovery/review-wakeup/orphan-frontiers/"
        f"{fingerprint[:2]}/{fingerprint}/attempt-"
        f"{producer['transport_attempt']}.json"
    )


def _frontier_child(
    intent: Mapping[str, Any], child_run: Mapping[str, Any], *, attempt: int
) -> dict[str, Any]:
    proof = validate_requested_review_child(
        intent,
        child_run,
        current_main_sha=validate_review_wakeup_intent(intent)[
            "requested_workflow_sha"
        ],
        transport_attempt=attempt,
    )
    child = proof["child"]
    # Retain only the exact stable REST fields consumed by the child validator.
    return {
        "id": child["run_id"],
        "run_attempt": child["run_attempt"],
        "workflow_id": child["workflow_id"],
        "path": child["workflow_path"],
        "repository": {
            "id": child["repository_id"],
            "full_name": child["repository"],
        },
        "event": child["event"],
        "head_branch": child["head_branch"],
        "head_sha": child["head_sha"],
        "display_title": child["display_title"],
        "status": child["status"],
    }


def build_review_wakeup_orphan_frontier(
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    observed_to: str,
) -> dict[str, Any]:
    """Seal a finite lookup root that can be split across recovery ticks."""
    exact = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(exact, binding)
    lower = producer["orphan_lookup_created_from"]
    upper = _timestamp(observed_to, "review wake-up frontier upper bound")
    if not lower < upper:
        raise AdmissionRecoveryError("review wake-up frontier order differs")
    value = {
        "schema": "qikvrt_human_review_wakeup_orphan_frontier_v1",
        "path": review_wakeup_orphan_frontier_path(exact, producer),
        "intent_sha256": exact["intent_sha256"],
        "fact_fingerprint": exact["fact_fingerprint"],
        "producer_binding_sha256": producer["binding_sha256"],
        "transport_attempt": producer["transport_attempt"],
        "root_created_from": lower,
        "root_created_to": upper,
        "pending_windows": [{"created_from": lower, "created_to": upper}],
        "completed_window_count": 0,
        "filtered_run_count": 0,
        "observation_chain_sha256": _canonical_sha256([]),
        "matching_children": [],
        "state": "PENDING",
        "authority_boundary": "RECOVERY_ONLY",
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["frontier_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_orphan_frontier(
    frontier: Mapping[str, Any],
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(exact, binding)
    if not isinstance(frontier, Mapping):
        raise AdmissionRecoveryError("review wake-up frontier is malformed")
    value = dict(frontier)
    claimed = value.pop("frontier_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("review wake-up frontier digest differs")
    pending = value.get("pending_windows")
    children = value.get("matching_children")
    if (
        value.get("schema")
        != "qikvrt_human_review_wakeup_orphan_frontier_v1"
        or value.get("path")
        != review_wakeup_orphan_frontier_path(exact, producer)
        or value.get("intent_sha256") != exact["intent_sha256"]
        or value.get("fact_fingerprint") != exact["fact_fingerprint"]
        or value.get("producer_binding_sha256")
        != producer["binding_sha256"]
        or value.get("transport_attempt") != producer["transport_attempt"]
        or value.get("root_created_from")
        != producer["orphan_lookup_created_from"]
        or not isinstance(pending, list)
        or len(pending) > 64
        or not isinstance(children, list)
        or len(children) > 2
        or value.get("state") not in {
            "PENDING", "COMPLETE", "QUARANTINED_CAP_HOLD"
        }
        or value.get("authority_boundary") != "RECOVERY_ONLY"
        or value.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("review wake-up frontier boundary differs")
    root_from = _timestamp(
        value.get("root_created_from"), "review wake-up frontier root lower"
    )
    root_to = _timestamp(
        value.get("root_created_to"), "review wake-up frontier root upper"
    )
    if not root_from < root_to:
        raise AdmissionRecoveryError("review wake-up frontier root order differs")
    for window in pending:
        if not isinstance(window, Mapping):
            raise AdmissionRecoveryError("review wake-up frontier window differs")
        lower = _timestamp(
            window.get("created_from"), "review wake-up frontier lower"
        )
        upper = _timestamp(
            window.get("created_to"), "review wake-up frontier upper"
        )
        if not root_from <= lower < upper <= root_to:
            raise AdmissionRecoveryError("review wake-up frontier window order differs")
    completed = value.get("completed_window_count")
    count = value.get("filtered_run_count")
    if any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in (completed, count)
    ):
        raise AdmissionRecoveryError("review wake-up frontier counts differ")
    _digest(
        value.get("observation_chain_sha256"),
        "review wake-up frontier observation chain",
    )
    seen: dict[int, dict[str, Any]] = {}
    for item in children:
        if not isinstance(item, Mapping):
            raise AdmissionRecoveryError("review wake-up frontier child differs")
        child = _frontier_child(exact, item.get("child"), attempt=producer["transport_attempt"])
        child_sha = _canonical_sha256(child)
        if item.get("child") != child or item.get("child_sha256") != child_sha:
            raise AdmissionRecoveryError("review wake-up frontier child digest differs")
        if child["id"] in seen:
            raise AdmissionRecoveryError("review wake-up frontier child duplicates")
        seen[child["id"]] = child
    if value["state"] == "PENDING" and not pending:
        raise AdmissionRecoveryError("pending review wake-up frontier is empty")
    if value["state"] != "PENDING" and pending:
        raise AdmissionRecoveryError("terminal review wake-up frontier still has work")
    return dict(frontier)


def advance_review_wakeup_orphan_frontier(
    frontier: Mapping[str, Any],
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    declared_total: int,
    filtered_run_ids: Sequence[int],
    exact_matching_children: Sequence[Mapping[str, Any]],
    filtered_result_cap: int = 1000,
) -> dict[str, Any]:
    """Consume or split exactly one immutable lookup shard.

    A capped shard is never negative evidence.  It is bisected durably.  If
    GitHub's second-granularity timestamp cannot be split further, the item is
    quarantined as an explicit authority hold so later FIFO facts can run.
    """
    current = validate_review_wakeup_orphan_frontier(frontier, intent, binding)
    if current["state"] != "PENDING":
        raise AdmissionRecoveryError("review wake-up frontier is already terminal")
    if (
        isinstance(declared_total, bool)
        or not isinstance(declared_total, int)
        or declared_total < 0
        or filtered_result_cap != 1000
    ):
        raise AdmissionRecoveryError("review wake-up frontier total differs")
    result = dict(current)
    result.pop("frontier_sha256", None)
    pending = [dict(item) for item in result["pending_windows"]]
    window = pending.pop()
    lower_dt = datetime.fromisoformat(
        window["created_from"].replace("Z", "+00:00")
    )
    upper_dt = datetime.fromisoformat(
        window["created_to"].replace("Z", "+00:00")
    )
    if declared_total >= filtered_result_cap:
        seconds = int((upper_dt - lower_dt).total_seconds())
        if seconds <= 1:
            result["pending_windows"] = []
            result["state"] = "QUARANTINED_CAP_HOLD"
            cap_evidence = {
                "created_from": window["created_from"],
                "created_to": window["created_to"],
                "declared_total": declared_total,
                "filtered_result_cap": filtered_result_cap,
                "result": "INCOMPLETE_NOT_ABSENCE",
            }
            result["observation_chain_sha256"] = _canonical_sha256({
                "prior": result["observation_chain_sha256"],
                "observation": cap_evidence,
            })
        else:
            midpoint = lower_dt + timedelta(seconds=seconds // 2)
            midpoint_text = midpoint.isoformat().replace("+00:00", "Z")
            # LIFO: inspect the newer half first, then the older half.  The
            # root bounds remain immutable and no mutable history tail exists.
            pending.extend([
                {
                    "created_from": window["created_from"],
                    "created_to": midpoint_text,
                },
                {
                    "created_from": midpoint_text,
                    "created_to": window["created_to"],
                },
            ])
            if len(pending) > 64:
                raise AdmissionRecoveryError(
                    "review wake-up frontier split depth exceeds bound"
                )
            result["pending_windows"] = pending
    else:
        if not isinstance(filtered_run_ids, Sequence) or isinstance(
            filtered_run_ids, (str, bytes)
        ):
            raise AdmissionRecoveryError("review wake-up frontier IDs differ")
        ids = [
            _positive(item, "review wake-up frontier run id")
            for item in filtered_run_ids
        ]
        if len(ids) != declared_total or len(set(ids)) != len(ids):
            raise AdmissionRecoveryError("review wake-up frontier page incomplete")
        if not isinstance(exact_matching_children, Sequence) or isinstance(
            exact_matching_children, (str, bytes)
        ):
            raise AdmissionRecoveryError("review wake-up frontier matches differ")
        attempt = current["transport_attempt"]
        existing = {
            item["child"]["id"]: dict(item)
            for item in result["matching_children"]
        }
        for raw in exact_matching_children:
            child = _frontier_child(intent, raw, attempt=attempt)
            if child["id"] not in ids:
                raise AdmissionRecoveryError(
                    "review wake-up frontier match was not enumerated"
                )
            item = {"child": child, "child_sha256": _canonical_sha256(child)}
            prior = existing.get(child["id"])
            if prior is not None and prior != item:
                raise AdmissionRecoveryError(
                    "review wake-up frontier child collision"
                )
            existing[child["id"]] = item
        if len(existing) > 2:
            # Two already proves ambiguity; never let adversarial duplicate
            # transport results make the durable shard unbounded.
            ordered = sorted(existing.values(), key=lambda item:item["child"]["id"])
            existing = {item["child"]["id"]:item for item in ordered[:2]}
        observation = {
            "created_from": window["created_from"],
            "created_to": window["created_to"],
            "declared_total": declared_total,
            "filtered_run_ids_sha256": _canonical_sha256(ids),
            "matching_child_sha256": sorted(
                item["child_sha256"] for item in existing.values()
            ),
        }
        result["observation_chain_sha256"] = _canonical_sha256({
            "prior": result["observation_chain_sha256"],
            "observation": observation,
        })
        result["completed_window_count"] += 1
        result["filtered_run_count"] += declared_total
        result["matching_children"] = sorted(
            existing.values(), key=lambda item:item["child"]["id"]
        )
        result["pending_windows"] = pending
        if not pending:
            result["state"] = "COMPLETE"
    result["frontier_sha256"] = _canonical_sha256(result)
    return validate_review_wakeup_orphan_frontier(result, intent, binding)


def build_review_wakeup_orphan_observation_from_frontier(
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
    frontier: Mapping[str, Any],
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(exact, binding)
    observed = validate_review_wakeup_orphan_frontier(
        frontier, exact, producer
    )
    if observed["state"] != "COMPLETE" or observed["matching_children"]:
        raise AdmissionRecoveryError(
            "review wake-up frontier does not prove orphan absence"
        )
    value = {
        "schema": "qikvrt_human_review_wakeup_orphan_observation_v1",
        "intent_sha256": exact["intent_sha256"],
        "fact_fingerprint": exact["fact_fingerprint"],
        "producer_binding_sha256": producer["binding_sha256"],
        "transport_attempt": producer["transport_attempt"],
        "created_from": observed["root_created_from"],
        "created_to": observed["root_created_to"],
        "filtered_total_count": observed["filtered_run_count"],
        "filtered_run_ids_sha256": observed["observation_chain_sha256"],
        "exact_matching_child_run_ids": [],
        "complete": True,
        "filtered_result_cap_not_reached": True,
        "result": "ORPHAN_NO_BOUND_SUCCESSOR",
        "frontier_sha256": observed["frontier_sha256"],
        "authority_boundary": "RECOVERY_ONLY",
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["observation_sha256"] = _canonical_sha256(value)
    return value


def build_review_wakeup_producer_binding(
    intent: Mapping[str, Any],
    *,
    recovery_run_id: int,
    recovery_run_attempt: int,
    recovery_run_started_at: str,
    transport_attempt: int,
    prior_orphan_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    attempt = _positive(transport_attempt, "review wake-up transport attempt")
    if attempt != 1:
        raise AdmissionRecoveryError("review wake-up transport attempt exceeds bound")
    started_at = _timestamp(
        recovery_run_started_at, "review wake-up recovery start"
    )
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    if started.tzinfo is None or started.utcoffset() != timedelta(0):
        raise AdmissionRecoveryError("review wake-up recovery start is not UTC")
    # GitHub run creation timestamps are second-granular and the REST filter
    # is strict `created:>`.  Seal a one-second-earlier lower bound so a child
    # accepted in the recovery run's start second remains adoptable.
    lookup_from = (started - timedelta(seconds=1)).isoformat().replace(
        "+00:00", "Z"
    )
    value = {
        "schema": "qikvrt_human_review_wakeup_producer_binding_v1",
        "intent_sha256": exact["intent_sha256"],
        "fact_fingerprint": exact["fact_fingerprint"],
        "recovery_run_id": _positive(recovery_run_id, "recovery run id"),
        "recovery_run_attempt": _positive(
            recovery_run_attempt, "recovery run attempt"
        ),
        "recovery_run_started_at": started_at,
        "orphan_lookup_created_from": lookup_from,
        "transport_attempt": attempt,
        "prior_orphan_observation": None,
    }
    if prior_orphan_observation is not None:
        raise AdmissionRecoveryError(
            "review wake-up first attempt has prior orphan observation"
        )
    value["binding_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_producer_binding(
    intent: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    if not isinstance(binding, Mapping):
        raise AdmissionRecoveryError("review wake-up producer binding is malformed")
    value = dict(binding)
    claimed = value.pop("binding_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("review wake-up producer digest differs")
    if (
        value.get("schema")
        != "qikvrt_human_review_wakeup_producer_binding_v1"
        or value.get("intent_sha256") != exact["intent_sha256"]
        or value.get("fact_fingerprint") != exact["fact_fingerprint"]
    ):
        raise AdmissionRecoveryError("review wake-up producer differs from intent")
    _positive(value.get("recovery_run_id"), "recovery run id")
    _positive(value.get("recovery_run_attempt"), "recovery run attempt")
    started_at = _timestamp(
        value.get("recovery_run_started_at"), "review wake-up recovery start"
    )
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    expected_lookup = (started - timedelta(seconds=1)).isoformat().replace(
        "+00:00", "Z"
    )
    if value.get("orphan_lookup_created_from") != expected_lookup:
        raise AdmissionRecoveryError("review wake-up lookup start differs")
    if value.get("transport_attempt") != 1:
        raise AdmissionRecoveryError("review wake-up producer attempt differs")
    prior = value.get("prior_orphan_observation")
    if prior is not None:
        raise AdmissionRecoveryError(
            "review wake-up first attempt prior observation differs"
        )
    return dict(binding)


def select_review_wakeup_transition(
    facts: Sequence[Mapping[str, Any]],
    *,
    acknowledged_fingerprints: set[str],
    terminal_fingerprints: set[str],
    reusable_intents: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Choose the deterministic oldest unseen transition without a cursor."""
    if not isinstance(facts, Sequence) or isinstance(facts, (str, bytes)):
        raise AdmissionRecoveryError("review wake-up facts are malformed")
    for values, label in (
        (acknowledged_fingerprints, "acknowledged"),
        (terminal_fingerprints, "terminal"),
    ):
        if not isinstance(values, set) or any(
            not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item)
            for item in values
        ):
            raise AdmissionRecoveryError(f"{label} fingerprints are malformed")
    if not isinstance(reusable_intents, Mapping):
        raise AdmissionRecoveryError("reusable review wake-up intents are malformed")
    exact: dict[str, dict[str, Any]] = {}
    for raw in facts:
        fact = validate_human_review_fact(raw)
        fingerprint = fact["fact_fingerprint"]
        previous = exact.get(fingerprint)
        if previous is not None and previous != fact:
            raise AdmissionRecoveryError("review fact fingerprint collision")
        exact[fingerprint] = fact
    ordered = sorted(
        exact.values(),
        key=lambda item: (
            item["submitted_at"], item["pr_number"], item["review_id"],
            item["transition_kind"], item["fact_fingerprint"],
        ),
    )
    for fact in ordered:
        fingerprint = fact["fact_fingerprint"]
        if fingerprint in acknowledged_fingerprints or fingerprint in terminal_fingerprints:
            continue
        reusable = reusable_intents.get(fingerprint)
        if reusable is None:
            return {
                "schema": "qikvrt_human_review_wakeup_selection_v1",
                "state": "DISPATCH_ATTEMPT_1",
                "fact": fact,
                "intent": None,
                "transport_attempt": 1,
                "d0": 2,
                "completion_claims": dict(COMPLETION_CLAIMS),
            }
        if not isinstance(reusable, Mapping):
            raise AdmissionRecoveryError("reusable review wake-up intent is malformed")
        intent = validate_review_wakeup_intent(reusable.get("intent"))
        if intent["fact_fingerprint"] != fingerprint:
            raise AdmissionRecoveryError("reusable intent fact differs")
        attempts_raw = reusable.get("transport_attempts")
        if not isinstance(attempts_raw, (set, list, tuple)):
            raise AdmissionRecoveryError("review wake-up attempts are malformed")
        attempts = set(attempts_raw)
        if attempts != {1}:
            raise AdmissionRecoveryError("review wake-up attempt sequence differs")
        return {
            "schema": "qikvrt_human_review_wakeup_selection_v1",
            "state": "CORE_TRANSPORT_PENDING",
            "fact": fact,
            "intent": intent,
            "transport_attempt": 1,
            "d0": 2,
            "first_blocker": "SHARED_CORE_EXACT_REVIEW_NOT_YET_ACCEPTED",
            "completion_claims": dict(COMPLETION_CLAIMS),
        }
    return {
        "schema": "qikvrt_human_review_wakeup_selection_v1",
        "state": "EMPTY",
        "fact": None,
        "intent": None,
        "transport_attempt": None,
        "d0": 0,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }


def validate_review_wakeup_preeffect(
    intent: Mapping[str, Any], observation: Mapping[str, Any], *,
    transport_attempt: int,
    core_payload: Mapping[str, Any],
    direct_review_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    fact = exact["fact"]
    if not isinstance(observation, Mapping) or observation.get("schema") != (
        "qikvrt_human_review_observation_v1"
    ):
        raise AdmissionRecoveryError("pre-effect review observation is malformed")
    if (
        observation.get("repository") != fact["repository"]
        or observation.get("current_main_sha") != exact["recovery_head_sha"]
    ):
        raise AdmissionRecoveryError("pre-effect review main differs")
    subjects = [
        subject for subject in observation.get("subjects", [])
        if isinstance(subject, Mapping)
        and subject.get("repository") == fact["repository"]
        and subject.get("pr_number") == fact["pr_number"]
    ]
    if len(subjects) != 1:
        raise AdmissionRecoveryError("pre-effect review subject is absent or ambiguous")
    subject = subjects[0]
    if not all(
        subject.get(field) == fact[field]
        for field in (
            "head_sha", "head_tree_sha", "head_ref", "base_sha",
            "base_tree_sha", "base_ref",
        )
    ):
        raise AdmissionRecoveryError("pre-effect review subject drifted")
    direct: dict[str, Any] | None = None
    if (
        fact["transition_kind"] == "REVIEW_ABSENT"
        or fact["review_state"] == "DISMISSED"
    ):
        if direct_review_observation is None:
            raise AdmissionRecoveryError(
                "direct review-ID observation is required for removal or dismissal"
            )
        direct = validate_direct_review_observation(
            direct_review_observation, review_id=fact["review_id"]
        )
    if fact["transition_kind"] == "REVIEW_STATE":
        current = {
            value["fact_fingerprint"]: value
            for value in observation.get("facts", [])
            if isinstance(value, Mapping)
        }
        if (
            fact["review_state"] != "DISMISSED"
            and current.get(fact["fact_fingerprint"]) != fact
        ):
            raise AdmissionRecoveryError("pre-effect review state drifted")
        if fact["review_state"] == "DISMISSED":
            assert direct is not None
            review = direct.get("review")
            if (
                direct.get("state") != "FOUND"
                or not isinstance(review, Mapping)
                or review.get("id") != fact["review_id"]
                or review.get("state") != "DISMISSED"
                or review.get("submitted_at") != fact["submitted_at"]
                or review.get("commit_id") != fact["commit_id"]
                or not isinstance(review.get("user"), Mapping)
                or review["user"].get("id") != fact["reviewer_id"]
                or review["user"].get("login") != fact["reviewer_login"]
            ):
                raise AdmissionRecoveryError(
                    "direct dismissed review identity differs"
                )
    else:
        assert direct is not None
        if direct.get("state") != "NOT_FOUND":
            raise AdmissionRecoveryError("direct absent review still exists")
    return {
        "schema": "qikvrt_human_review_wakeup_effect_plan_v1",
        "effect": "DISPATCH_SECRET_FREE_REQUESTED_REVIEW_EVALUATOR",
        "fact_fingerprint": fact["fact_fingerprint"],
        "dispatch_request": review_wakeup_dispatch_request(
            exact, transport_attempt=transport_attempt,
            core_payload=core_payload,
        ),
        "expected_child_title": review_wakeup_child_title(
            exact, transport_attempt=transport_attempt,
            core_payload=core_payload,
        ),
        "core_fingerprint": review_wakeup_core_fingerprint(
            exact, core_payload
        ),
        "transport_attempt": transport_attempt,
        "direct_review_observation_sha256": (
            direct.get("observation_sha256") if direct is not None else None
        ),
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }


def validate_requested_review_child(
    intent: Mapping[str, Any],
    child_run: Mapping[str, Any],
    *,
    current_main_sha: str,
    transport_attempt: int,
    core_payload: Mapping[str, Any],
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    if not isinstance(child_run, Mapping):
        raise AdmissionRecoveryError("requested-review child is malformed")
    repository = child_run.get("repository")
    if not isinstance(repository, Mapping):
        raise AdmissionRecoveryError("requested-review child repository is missing")
    child = {
        "run_id": _positive(child_run.get("id"), "requested-review child id"),
        "run_attempt": _positive(
            child_run.get("run_attempt", 1), "requested-review child attempt"
        ),
        "workflow_id": _positive(
            child_run.get("workflow_id"), "requested-review child workflow id"
        ),
        "workflow_path": _workflow_path(child_run.get("path")),
        "repository": repository.get("full_name"),
        "repository_id": repository.get("id"),
        "event": child_run.get("event"),
        "head_branch": child_run.get("head_branch"),
        "head_sha": _sha(child_run.get("head_sha"), "requested-review child SHA"),
        "display_title": child_run.get("display_title"),
        "status": child_run.get("status"),
    }
    checks = {
        "current_main": exact["requested_workflow_sha"]
        == _sha(current_main_sha, "child proof current main SHA"),
        "workflow_id": child["workflow_id"] == exact["requested_workflow_id"],
        "workflow_path": child["workflow_path"] == exact["requested_workflow_path"],
        "repository": child["repository"] == exact["recovery_repository"],
        "repository_id": child["repository_id"]
        == exact["recovery_repository_id"],
        "event": child["event"] == "workflow_dispatch",
        "head_branch": child["head_branch"] == "main",
        "head_sha": child["head_sha"] == exact["requested_workflow_sha"],
        "display_title": child["display_title"] == review_wakeup_child_title(
            exact, transport_attempt=transport_attempt,
            core_payload=core_payload,
        ),
        "status": child["status"] in {"queued", "in_progress", "completed"},
    }
    if not all(checks.values()):
        raise AdmissionRecoveryError("requested-review child proof differs")
    return {
        "schema": "qikvrt_human_review_wakeup_child_proof_v1",
        "child": child,
        "transport_intent_sha256": review_wakeup_core_fingerprint(
            exact, core_payload
        ),
        "transport_attempt": transport_attempt,
        "checks": checks,
        "transport_ack_observed": True,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }


def build_review_wakeup_core_acceptance_proof(
    intent: Mapping[str, Any],
    core_payload: Mapping[str, Any],
    core_lookup: Mapping[str, Any],
    *,
    current_main_sha: str,
) -> dict[str, Any]:
    """Bind a wake-up ACK to one exact accepted Shared-Core A1 child."""
    from tools.qikvrt_ruleset_outbox import (
        _validate_intent_record,
        acceptance_path,
        digest as core_digest,
        intent_path,
        semantic_work_unit,
        transport_path,
        validate_acceptance_record,
        validate_transport_record,
    )

    exact = validate_review_wakeup_intent(intent)
    payload = validate_review_wakeup_core_payload(core_payload, exact)
    fingerprint = core_digest(semantic_work_unit(payload))
    _sha(current_main_sha, "review wake-up Core observed main")
    if not isinstance(core_lookup, Mapping):
        raise AdmissionRecoveryError("review wake-up Core lookup is malformed")
    lookup = dict(core_lookup)
    sequence = _positive(lookup.get("sequence"), "review wake-up Core sequence")
    core_intent = _validate_intent_record(
        lookup.get("intent"), lane="exact-review-dispatch"
    )
    witnesses = lookup.get("witnesses")
    transports = lookup.get("transport")
    acceptances = lookup.get("acceptance")
    if (
        lookup.get("schema") != "qikvrt_ruleset_outbox_next_v1"
        or lookup.get("state") not in {"PENDING", "TERMINAL"}
        or lookup.get("lookup_state") != lookup.get("state")
        or lookup.get("lane") != "exact-review-dispatch"
        or lookup.get("fingerprint") != fingerprint
        or core_intent["sequence"] != sequence
        or core_intent["fingerprint"] != fingerprint
        or semantic_work_unit(core_intent["payload"])
        != semantic_work_unit(payload)
        or lookup.get("ledger_ref")
        != "refs/heads/qikvrt/outbox-ledger-v2/exact-review-dispatch"
        or not isinstance(witnesses, Sequence)
        or isinstance(witnesses, (str, bytes))
        or not isinstance(transports, Mapping)
        or set(transports) != {"1"}
        or not isinstance(acceptances, Mapping)
        or set(acceptances) != {"1"}
    ):
        raise AdmissionRecoveryError("review wake-up Core locator differs")
    transport = validate_transport_record(
        transports.get("1"), intent=core_intent, attempt=1,
        witnesses=witnesses,
    )
    acceptance = validate_acceptance_record(
        acceptances.get("1"), intent=core_intent,
        transport=transport, attempt=1,
    )
    child = acceptance["child"]
    fact = exact["fact"]
    if (
        child.get("run_attempt") != 1
        or child.get("workflow_id") != exact["requested_workflow_id"]
        or child.get("workflow_path") != exact["requested_workflow_path"]
        or child.get("event") != "workflow_dispatch"
        or child.get("repository") != exact["recovery_repository"]
        or child.get("head_sha") != exact["requested_workflow_sha"]
        or core_intent["payload"]["request"]["inputs"]["pr"]
        != str(fact["pr_number"])
        or core_intent["payload"]["request"]["inputs"]["head"]
        != fact["head_sha"]
        or core_intent["payload"]["request"]["inputs"]["fingerprint"]
        != fact["fact_fingerprint"]
        or acceptance.get("child_sha256") != core_digest(child)
    ):
        raise AdmissionRecoveryError("review wake-up Core accepted child differs")
    authority = {
        "schema": "qikvrt_human_review_wakeup_core_acceptance_locator_v1",
        "lane": "exact-review-dispatch",
        "sequence": sequence,
        "fingerprint": fingerprint,
        "transport_attempt": 1,
        "ledger_ref": lookup["ledger_ref"],
        "ledger_head": _sha(
            lookup.get("ledger_head"), "review wake-up Core ledger head"
        ),
        "intent_path": intent_path(
            "exact-review-dispatch", sequence, fingerprint
        ),
        "intent_sha256": core_digest(core_intent),
        "transport_path": transport_path(
            "exact-review-dispatch", sequence, 1
        ),
        "transport_sha256": core_digest(transport),
        "acceptance_path": acceptance_path(
            "exact-review-dispatch", sequence, 1
        ),
        "acceptance_sha256": core_digest(acceptance),
        "child": child,
        "accepted_child_sha256": acceptance["child_sha256"],
        "wakeup_intent_sha256": exact["intent_sha256"],
        "fact_fingerprint": exact["fact_fingerprint"],
        "state": "CORE_ATTEMPT_1_ACCEPTED_LOCATOR",
        "same_run_recovery_authority": "SHARED_CORE_ONLY",
        "productive_effect": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    authority["authority_sha256"] = _canonical_sha256(authority)
    return authority


def validate_review_wakeup_core_acceptance_proof(
    value: Mapping[str, Any], intent: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review wake-up Core authority is malformed")
    from tools.qikvrt_ruleset_outbox import (
        acceptance_path,
        digest as core_digest,
        intent_path,
        transport_path,
    )

    exact = validate_review_wakeup_intent(intent)
    authority = dict(value)
    claimed = authority.pop("authority_sha256", None)
    if claimed != _canonical_sha256(authority):
        raise AdmissionRecoveryError("review wake-up Core authority digest differs")
    sequence = _positive(
        authority.get("sequence"), "review wake-up Core locator sequence"
    )
    fingerprint = _digest(
        authority.get("fingerprint"), "review wake-up Core locator fingerprint"
    )
    expected_payload = build_review_wakeup_core_payload(
        exact,
        producer_run_id=1,
        producer_run_attempt=1,
        producer_event="schedule",
        producer_workflow_sha=exact["recovery_head_sha"],
    )
    expected_fingerprint = review_wakeup_core_fingerprint(
        exact, expected_payload
    )
    child = authority.get("child")
    expected_child_title = review_wakeup_child_title(
        exact, transport_attempt=1, core_payload=expected_payload
    )
    if (
        set(authority)
        != {
            "schema", "lane", "sequence", "fingerprint",
            "transport_attempt", "ledger_ref", "ledger_head",
            "intent_path", "intent_sha256", "transport_path",
            "transport_sha256", "acceptance_path", "acceptance_sha256",
            "child", "accepted_child_sha256", "wakeup_intent_sha256",
            "fact_fingerprint", "state", "same_run_recovery_authority",
            "productive_effect", "completion_claims",
        }
        or authority.get("schema")
        != "qikvrt_human_review_wakeup_core_acceptance_locator_v1"
        or authority.get("lane") != "exact-review-dispatch"
        or fingerprint != expected_fingerprint
        or authority.get("transport_attempt") != 1
        or authority.get("ledger_ref")
        != "refs/heads/qikvrt/outbox-ledger-v2/exact-review-dispatch"
        or authority.get("intent_path")
        != intent_path("exact-review-dispatch", sequence, fingerprint)
        or authority.get("transport_path")
        != transport_path("exact-review-dispatch", sequence, 1)
        or authority.get("acceptance_path")
        != acceptance_path("exact-review-dispatch", sequence, 1)
        or authority.get("wakeup_intent_sha256") != exact["intent_sha256"]
        or authority.get("fact_fingerprint") != exact["fact_fingerprint"]
        or authority.get("state") != "CORE_ATTEMPT_1_ACCEPTED_LOCATOR"
        or authority.get("same_run_recovery_authority") != "SHARED_CORE_ONLY"
        or authority.get("productive_effect") is not False
        or authority.get("completion_claims") != COMPLETION_CLAIMS
        or not isinstance(child, Mapping)
        or set(child) != {
            "run_id", "run_attempt", "workflow_id", "workflow_path",
            "event", "repository", "head_sha", "status", "conclusion",
            "display_title",
        }
        or isinstance(child.get("run_id"), bool)
        or not isinstance(child.get("run_id"), int)
        or child.get("run_id", 0) < 1
        or child.get("run_attempt") != 1
        or child.get("workflow_id") != exact["requested_workflow_id"]
        or child.get("workflow_path") != exact["requested_workflow_path"]
        or child.get("event") != "workflow_dispatch"
        or child.get("repository") != exact["recovery_repository"]
        or child.get("head_sha") != exact["requested_workflow_sha"]
        or child.get("display_title") != expected_child_title
        or child.get("status") not in {
            "queued", "in_progress", "waiting", "pending", "completed"
        }
        or (
            child.get("status") == "completed"
            and (
                not isinstance(child.get("conclusion"), str)
                or not child["conclusion"]
            )
        )
        or (
            child.get("status") != "completed"
            and child.get("conclusion") is not None
        )
        or authority.get("accepted_child_sha256") != core_digest(child)
    ):
        raise AdmissionRecoveryError("review wake-up Core authority differs")
    _sha(authority.get("ledger_head"), "review wake-up Core locator head")
    for field in (
        "intent_sha256", "transport_sha256", "acceptance_sha256"
    ):
        _digest(authority.get(field), f"review wake-up Core locator {field}")
    return dict(value)


def build_review_wakeup_ack(
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
    core_payload: Mapping[str, Any],
    core_lookup: Mapping[str, Any],
    *,
    current_main_sha: str,
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(exact, binding)
    core_authority = build_review_wakeup_core_acceptance_proof(
        exact, core_payload, core_lookup,
        current_main_sha=current_main_sha,
    )
    child = core_authority["child"]
    proof = {
        "schema": "qikvrt_human_review_wakeup_child_proof_v2",
        "child": child,
        "transport_intent_sha256": core_authority["fingerprint"],
        "transport_attempt": producer["transport_attempt"],
        "core_authority": core_authority,
        "transport_ack_observed": True,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value = {
        "schema": "qikvrt_human_review_wakeup_ack_v1",
        "intent_sha256": exact["intent_sha256"],
        "fact": exact["fact"],
        "fact_fingerprint": exact["fact_fingerprint"],
        "producer_binding_sha256": producer["binding_sha256"],
        "transport_attempt": producer["transport_attempt"],
        "child_proof": proof,
        "d0": 2,
        "effect_ack": "TRANSPORT_ACCEPTED_PENDING_REOBSERVATION",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["ack_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_ack(
    ack: Mapping[str, Any],
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
    core_payload: Mapping[str, Any],
    core_lookup: Mapping[str, Any],
    *,
    current_main_sha: str,
) -> dict[str, Any]:
    expected = build_review_wakeup_ack(
        intent, binding, core_payload, core_lookup,
        current_main_sha=current_main_sha
    )
    if not isinstance(ack, Mapping) or dict(ack) != expected:
        raise AdmissionRecoveryError("review wake-up ACK differs")
    return dict(ack)


def build_review_wakeup_core_resolution(
    intent: Mapping[str, Any],
    core_payload: Mapping[str, Any],
    core_lookup: Mapping[str, Any],
    *,
    observed_main_sha: str,
) -> dict[str, Any]:
    """Seal the exact Core terminal/absence fact used to drain a local HOLD."""
    from tools.qikvrt_ruleset_outbox import (
        TERMINAL_SCHEMA,
        _validate_intent_record,
        digest as core_digest,
        semantic_work_unit,
        terminal_path,
        validate_terminal_evidence,
    )

    exact = validate_review_wakeup_intent(intent)
    payload = validate_review_wakeup_core_payload(core_payload, exact)
    fingerprint = review_wakeup_core_fingerprint(exact, payload)
    main = _sha(observed_main_sha, "review wake-up Core resolution main")
    if core_lookup == {"lookup_state": "NOT_FOUND"}:
        if main == exact["requested_workflow_sha"]:
            raise AdmissionRecoveryError(
                "current wake-up cannot resolve an absent Core record"
            )
        value = {
            "schema": "qikvrt_human_review_wakeup_core_resolution_v1",
            "state": "SUPERSEDED_NO_CORE_RECORD",
            "lane": "exact-review-dispatch",
            "fingerprint": fingerprint,
            "sequence": None,
            "ledger_ref": None,
            "ledger_head": None,
            "terminal_path": None,
            "terminal_sha256": None,
            "observed_main_sha": main,
            "wakeup_intent_sha256": exact["intent_sha256"],
            "fact_fingerprint": exact["fact_fingerprint"],
            "verified": True,
            "productive_effect": False,
            "completion_claims": dict(COMPLETION_CLAIMS),
        }
    else:
        if not isinstance(core_lookup, Mapping):
            raise AdmissionRecoveryError("review wake-up Core resolution is malformed")
        lookup = dict(core_lookup)
        sequence = _positive(
            lookup.get("sequence"), "review wake-up Core resolution sequence"
        )
        core_intent = _validate_intent_record(
            lookup.get("intent"), lane="exact-review-dispatch"
        )
        acceptances = lookup.get("acceptance")
        terminal = lookup.get("terminal")
        terminal_evidence = (
            validate_terminal_evidence(terminal.get("evidence"), next_item=lookup)
            if isinstance(terminal, Mapping) else None
        )
        if (
            lookup.get("state") != "TERMINAL"
            or lookup.get("lookup_state") != "TERMINAL"
            or lookup.get("lane") != "exact-review-dispatch"
            or lookup.get("fingerprint") != fingerprint
            or core_intent.get("sequence") != sequence
            or core_intent.get("fingerprint") != fingerprint
            or semantic_work_unit(core_intent["payload"])
            != semantic_work_unit(payload)
            or lookup.get("ledger_ref")
            != "refs/heads/qikvrt/outbox-ledger-v2/exact-review-dispatch"
            or not isinstance(acceptances, Mapping)
            or dict(acceptances) != {}
            or not isinstance(terminal, Mapping)
            or set(terminal) != {
                "schema", "lane", "sequence", "fingerprint", "state", "d0",
                "evidence_sha256", "evidence", "productive_effect",
            }
            or terminal.get("schema") != TERMINAL_SCHEMA
            or terminal.get("lane") != "exact-review-dispatch"
            or terminal.get("sequence") != sequence
            or terminal.get("fingerprint") != fingerprint
            or terminal.get("state") != "TERMINAL"
            or terminal.get("d0") != terminal_evidence.get("d0")
            or terminal.get("evidence_sha256") != core_digest(terminal_evidence)
            or terminal.get("productive_effect") is not False
        ):
            raise AdmissionRecoveryError(
                "review wake-up Core terminal resolution differs"
            )
        value = {
            "schema": "qikvrt_human_review_wakeup_core_resolution_v1",
            "state": "CORE_TERMINAL_NO_ACCEPTANCE",
            "lane": "exact-review-dispatch",
            "fingerprint": fingerprint,
            "sequence": sequence,
            "ledger_ref": lookup["ledger_ref"],
            "ledger_head": _sha(
                lookup.get("ledger_head"), "review wake-up Core resolution head"
            ),
            "terminal_path": terminal_path("exact-review-dispatch", sequence),
            "terminal_sha256": core_digest(terminal),
            "observed_main_sha": main,
            "wakeup_intent_sha256": exact["intent_sha256"],
            "fact_fingerprint": exact["fact_fingerprint"],
            "verified": True,
            "productive_effect": False,
            "completion_claims": dict(COMPLETION_CLAIMS),
        }
    value["resolution_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_core_resolution(
    value: Mapping[str, Any],
    intent: Mapping[str, Any],
    core_payload: Mapping[str, Any],
    core_lookup: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review wake-up Core resolution is malformed")
    expected = build_review_wakeup_core_resolution(
        intent, core_payload, core_lookup,
        observed_main_sha=value.get("observed_main_sha"),
    )
    if dict(value) != expected:
        raise AdmissionRecoveryError("review wake-up Core resolution differs")
    return dict(value)


def _validate_review_wakeup_core_resolution_locator(
    value: Mapping[str, Any], intent: Mapping[str, Any]
) -> dict[str, Any]:
    from tools.qikvrt_ruleset_outbox import terminal_path

    exact = validate_review_wakeup_intent(intent)
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review wake-up Core resolution is malformed")
    if set(value) != {
        "schema", "state", "lane", "fingerprint", "sequence",
        "ledger_ref", "ledger_head", "terminal_path", "terminal_sha256",
        "observed_main_sha", "wakeup_intent_sha256", "fact_fingerprint",
        "verified", "productive_effect", "completion_claims",
        "resolution_sha256",
    }:
        raise AdmissionRecoveryError("review wake-up Core resolution shape differs")
    resolution = dict(value)
    claimed = resolution.pop("resolution_sha256", None)
    if claimed != _canonical_sha256(resolution):
        raise AdmissionRecoveryError("review wake-up Core resolution digest differs")
    expected_payload = build_review_wakeup_core_payload(
        exact, producer_run_id=1, producer_run_attempt=1,
        producer_event="schedule",
        producer_workflow_sha=exact["recovery_head_sha"],
    )
    fingerprint = review_wakeup_core_fingerprint(exact, expected_payload)
    state = resolution.get("state")
    if (
        resolution.get("schema")
        != "qikvrt_human_review_wakeup_core_resolution_v1"
        or resolution.get("lane") != "exact-review-dispatch"
        or resolution.get("fingerprint") != fingerprint
        or resolution.get("wakeup_intent_sha256") != exact["intent_sha256"]
        or resolution.get("fact_fingerprint") != exact["fact_fingerprint"]
        or resolution.get("verified") is not True
        or resolution.get("productive_effect") is not False
        or resolution.get("completion_claims") != COMPLETION_CLAIMS
        or state not in {
            "SUPERSEDED_NO_CORE_RECORD", "CORE_TERMINAL_NO_ACCEPTANCE"
        }
    ):
        raise AdmissionRecoveryError("review wake-up Core resolution differs")
    observed_main = _sha(
        resolution.get("observed_main_sha"), "review wake-up Core resolution main"
    )
    if state == "SUPERSEDED_NO_CORE_RECORD":
        if (
            observed_main == exact["requested_workflow_sha"]
            or any(
                resolution.get(field) is not None
                for field in (
                    "sequence", "ledger_ref", "ledger_head",
                    "terminal_path", "terminal_sha256",
                )
            )
        ):
            raise AdmissionRecoveryError("review wake-up supersession differs")
    else:
        sequence = _positive(
            resolution.get("sequence"), "review wake-up Core resolution sequence"
        )
        if (
            resolution.get("ledger_ref")
            != "refs/heads/qikvrt/outbox-ledger-v2/exact-review-dispatch"
            or resolution.get("terminal_path")
            != terminal_path("exact-review-dispatch", sequence)
        ):
            raise AdmissionRecoveryError("review wake-up Core terminal locator differs")
        _sha(resolution.get("ledger_head"), "review wake-up Core resolution head")
        _digest(
            resolution.get("terminal_sha256"),
            "review wake-up Core terminal digest",
        )
    return dict(value)


def build_review_wakeup_terminal(
    intent: Mapping[str, Any], *, transport_attempts: set[int],
    first_blocker: str = "REQUESTED_REVIEW_WAKEUP_TRANSPORT_ACK_MISSING",
    core_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    if transport_attempts != {1}:
        raise AdmissionRecoveryError("review wake-up terminal attempt set differs")
    if first_blocker not in {
        "REQUESTED_REVIEW_WAKEUP_TRANSPORT_ACK_MISSING",
        "REQUESTED_REVIEW_WAKEUP_CHILD_LOOKUP_AMBIGUOUS",
        "REQUESTED_REVIEW_WAKEUP_CHILD_LOOKUP_INCOMPLETE",
        "REQUESTED_REVIEW_WAKEUP_TRANSITION_SUPERSEDED",
        "SHARED_CORE_EXACT_REVIEW_TERMINAL_WITHOUT_ACCEPTANCE",
    }:
        raise AdmissionRecoveryError("review wake-up terminal blocker differs")
    exact_resolution = (
        _validate_review_wakeup_core_resolution_locator(core_resolution, exact)
        if core_resolution is not None else None
    )
    if first_blocker == "REQUESTED_REVIEW_WAKEUP_TRANSITION_SUPERSEDED" and (
        exact_resolution is None
        or exact_resolution["state"] != "SUPERSEDED_NO_CORE_RECORD"
    ):
        raise AdmissionRecoveryError("review wake-up supersession proof is missing")
    if (
        first_blocker == "SHARED_CORE_EXACT_REVIEW_TERMINAL_WITHOUT_ACCEPTANCE"
        and (
            exact_resolution is None
            or exact_resolution["state"] != "CORE_TERMINAL_NO_ACCEPTANCE"
        )
    ):
        raise AdmissionRecoveryError("review wake-up Core terminal proof is missing")
    value = {
        "schema": "qikvrt_human_review_wakeup_terminal_v2",
        "intent_sha256": exact["intent_sha256"],
        "fact": exact["fact"],
        "fact_fingerprint": exact["fact_fingerprint"],
        "transport_attempts": sorted(transport_attempts),
        "state": (
            "SUPERSEDED_D0_3"
            if first_blocker == "REQUESTED_REVIEW_WAKEUP_TRANSITION_SUPERSEDED"
            else "RETRY_EXHAUSTED_D0_3"
        ),
        "first_blocker": first_blocker,
        "core_resolution": (
            exact_resolution
        ),
        "d0": 3,
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["receipt_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_terminal(
    receipt: Mapping[str, Any], intent: Mapping[str, Any]
) -> dict[str, Any]:
    semantic = validate_review_wakeup_intent(intent)
    if not isinstance(receipt, Mapping):
        raise AdmissionRecoveryError("review wake-up terminal receipt differs")
    blocker = receipt.get("first_blocker")
    core_resolution = receipt.get("core_resolution")
    attempts = receipt.get("transport_attempts")
    if (
        not isinstance(attempts, list)
        or attempts != [1]
    ):
        raise AdmissionRecoveryError("review wake-up terminal attempts differ")
    expected = build_review_wakeup_terminal(
        semantic, transport_attempts=set(attempts), first_blocker=blocker,
        core_resolution=(
            core_resolution if isinstance(core_resolution, Mapping) else None
        ),
    )
    if dict(receipt) != expected:
        raise AdmissionRecoveryError("review wake-up terminal receipt differs")
    return dict(receipt)


def build_review_wakeup_terminal_binding(
    receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    *,
    recovery_run_id: int,
    recovery_run_attempt: int,
    terminalizer_workflow_sha: str,
) -> dict[str, Any]:
    exact = validate_review_wakeup_terminal(receipt, intent)
    semantic = validate_review_wakeup_intent(intent)
    value = {
        "schema": "qikvrt_human_review_wakeup_terminal_binding_v1",
        "receipt_sha256": exact["receipt_sha256"],
        "intent_sha256": semantic["intent_sha256"],
        "recovery_run_id": _positive(recovery_run_id, "recovery run id"),
        "recovery_run_attempt": _positive(
            recovery_run_attempt, "recovery run attempt"
        ),
        "recovery_repository": semantic["recovery_repository"],
        "recovery_workflow_id": semantic["recovery_workflow_id"],
        "recovery_workflow_path": semantic["recovery_workflow_path"],
        "terminalizer_workflow_sha": _sha(
            terminalizer_workflow_sha, "terminalizer workflow SHA"
        ),
        "intent_evaluator_sha": semantic["recovery_head_sha"],
    }
    value["binding_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_terminal_binding(
    receipt: Mapping[str, Any],
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    exact = validate_review_wakeup_terminal(receipt, intent)
    semantic = validate_review_wakeup_intent(intent)
    if not isinstance(binding, Mapping):
        raise AdmissionRecoveryError("review wake-up terminal binding is malformed")
    value = dict(binding)
    claimed = value.pop("binding_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("review wake-up terminal binding digest differs")
    expected = {
        "schema": "qikvrt_human_review_wakeup_terminal_binding_v1",
        "receipt_sha256": exact["receipt_sha256"],
        "intent_sha256": semantic["intent_sha256"],
        "recovery_run_id": value.get("recovery_run_id"),
        "recovery_run_attempt": value.get("recovery_run_attempt"),
        "recovery_repository": semantic["recovery_repository"],
        "recovery_workflow_id": semantic["recovery_workflow_id"],
        "recovery_workflow_path": semantic["recovery_workflow_path"],
        "terminalizer_workflow_sha": value.get("terminalizer_workflow_sha"),
        "intent_evaluator_sha": semantic["recovery_head_sha"],
    }
    _positive(value.get("recovery_run_id"), "recovery run id")
    _positive(value.get("recovery_run_attempt"), "recovery run attempt")
    _sha(value.get("terminalizer_workflow_sha"), "terminalizer workflow SHA")
    if value != expected:
        raise AdmissionRecoveryError("review wake-up terminal binding differs")
    return dict(binding)


def _seal_review_wakeup_record(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["record_sha256"] = _canonical_sha256(result)
    return result


def review_wakeup_record_path(fingerprint: str) -> str:
    if not isinstance(fingerprint, str) or not re.fullmatch(
        r"[0-9a-f]{64}", fingerprint
    ):
        raise AdmissionRecoveryError("review wake-up record fingerprint is invalid")
    return (
        ".qikvrt/recovery/review-wakeup/records/"
        f"{fingerprint[:2]}/{fingerprint}.json"
    )


def review_wakeup_active_path() -> str:
    """Return the bounded pointer to the sole nonterminal wake-up record."""
    return ".qikvrt/recovery/review-wakeup/active.json"


def build_review_wakeup_active(intent: Mapping[str, Any]) -> dict[str, Any]:
    exact = validate_review_wakeup_intent(intent)
    value = {
        "schema": "qikvrt_human_review_wakeup_active_v1",
        "fact_fingerprint": exact["fact_fingerprint"],
        "intent_sha256": exact["intent_sha256"],
        "record_path": review_wakeup_record_path(exact["fact_fingerprint"]),
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    value["active_sha256"] = _canonical_sha256(value)
    return value


def validate_review_wakeup_active(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review wake-up active pointer is malformed")
    observed = dict(value)
    claimed = observed.pop("active_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("review wake-up active digest differs")
    fingerprint = observed.get("fact_fingerprint")
    if (
        observed.get("schema") != "qikvrt_human_review_wakeup_active_v1"
        or observed.get("record_path") != review_wakeup_record_path(fingerprint)
        or not isinstance(observed.get("intent_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", observed["intent_sha256"]) is None
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("review wake-up active boundary differs")
    return dict(value)


def bind_review_wakeup_active_record(
    active: Mapping[str, Any], record: Mapping[str, Any]
) -> dict[str, Any]:
    pointer = validate_review_wakeup_active(active)
    exact = validate_review_wakeup_record(record)
    if (
        pointer["fact_fingerprint"] != exact["fact_fingerprint"]
        or pointer["intent_sha256"] != exact["intent"]["intent_sha256"]
        or pointer["record_path"] != exact["record_path"]
        or exact.get("ack") is not None
        or exact.get("terminal") is not None
    ):
        raise AdmissionRecoveryError("review wake-up active record differs")
    return exact


def review_wakeup_subject_key(subject: Mapping[str, Any]) -> str:
    if not isinstance(subject, Mapping):
        raise AdmissionRecoveryError("review wake-up subject is malformed")
    value = {
        "repository": _repository(
            subject.get("repository"), "review wake-up subject repository"
        ),
        "pr_number": _positive(
            subject.get("pr_number"), "review wake-up subject PR"
        ),
        "head_sha": _sha(subject.get("head_sha"), "review wake-up subject head"),
        "head_tree_sha": _sha(
            subject.get("head_tree_sha"), "review wake-up subject head tree"
        ),
        "head_ref": subject.get("head_ref"),
        "base_sha": _sha(subject.get("base_sha"), "review wake-up subject base"),
        "base_tree_sha": _sha(
            subject.get("base_tree_sha"), "review wake-up subject base tree"
        ),
        "base_ref": subject.get("base_ref"),
    }
    if (
        value["base_ref"] != "main"
        or not isinstance(value["head_ref"], str)
        or not value["head_ref"]
    ):
        raise AdmissionRecoveryError("review wake-up subject base differs")
    return _canonical_sha256(value)


def review_wakeup_subject_path(subject: Mapping[str, Any]) -> str:
    key = review_wakeup_subject_key(subject)
    return (
        ".qikvrt/recovery/review-wakeup/subjects/"
        f"{key[:2]}/{key}.json"
    )


def review_wakeup_subject_ack_slot_path(
    subject: Mapping[str, Any], sequence: int
) -> str:
    key = review_wakeup_subject_key(subject)
    return (
        ".qikvrt/recovery/review-wakeup/subject-acks/"
        f"{key[:2]}/{key}/{_positive(sequence, 'subject ACK sequence'):020d}.json"
    )


def empty_review_wakeup_subject(*, subject: Mapping[str, Any]) -> dict[str, Any]:
    key = review_wakeup_subject_key(subject)
    value = {
        field: subject[field]
        for field in (
            "repository", "pr_number", "head_sha", "head_tree_sha", "head_ref",
            "base_sha", "base_tree_sha", "base_ref",
        )
    }
    result = {
        "schema": "qikvrt_human_review_wakeup_subject_v2",
        "subject_key": key,
        "subject": value,
        "next_ack_sequence": 1,
        "recheck_sequence": 1,
        "acknowledged_review_count": 0,
        "authority_boundary": "RECOVERY_ONLY",
        "native_account_review_authorized": False,
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    result["subject_sha256"] = _canonical_sha256(result)
    return result


def _validate_review_wakeup_ack_record(
    ack: Mapping[str, Any],
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    semantic = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(semantic, binding)
    if not isinstance(ack, Mapping):
        raise AdmissionRecoveryError("review wake-up ACK is malformed")
    value = dict(ack)
    claimed = value.pop("ack_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("review wake-up ACK digest differs")
    proof = value.get("child_proof")
    child = proof.get("child") if isinstance(proof, Mapping) else None
    core_authority = (
        validate_review_wakeup_core_acceptance_proof(
            proof.get("core_authority"), semantic
        ) if isinstance(proof, Mapping) else None
    )
    if (
        value.get("schema") != "qikvrt_human_review_wakeup_ack_v1"
        or value.get("intent_sha256") != semantic["intent_sha256"]
        or value.get("fact") != semantic["fact"]
        or value.get("fact_fingerprint") != semantic["fact_fingerprint"]
        or value.get("producer_binding_sha256") != producer["binding_sha256"]
        or value.get("transport_attempt") != producer["transport_attempt"]
        or value.get("d0") != 2
        or value.get("effect_ack") != "TRANSPORT_ACCEPTED_PENDING_REOBSERVATION"
        or value.get("native_account_review_authorized") is not False
        or value.get("completion_claims") != COMPLETION_CLAIMS
        or not isinstance(proof, Mapping)
        or proof.get("schema")
            != "qikvrt_human_review_wakeup_child_proof_v2"
        or proof.get("transport_ack_observed") is not True
        or proof.get("completion_claims") != COMPLETION_CLAIMS
        or not isinstance(child, Mapping)
        or child.get("run_id") is None
        or child != core_authority["child"]
        or proof.get("transport_intent_sha256")
        != core_authority["fingerprint"]
        or proof.get("transport_attempt") != 1
    ):
        raise AdmissionRecoveryError("review wake-up ACK boundary differs")
    return dict(ack)


def validate_review_wakeup_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise AdmissionRecoveryError("review wake-up record must be an object")
    value = dict(record)
    claimed = value.pop("record_sha256", None)
    if claimed != _canonical_sha256(value):
        raise AdmissionRecoveryError("review wake-up record digest differs")
    if (
        value.get("schema") != "qikvrt_human_review_wakeup_record_v1"
        or value.get("authority_boundary") != "RECOVERY_ONLY"
        or value.get("native_account_review_authorized") is not False
        or value.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("review wake-up record boundary differs")
    fact = validate_human_review_fact(value.get("fact"))
    intent = validate_review_wakeup_intent(value.get("intent"))
    if (
        value.get("fact_fingerprint") != fact["fact_fingerprint"]
        or intent["fact"] != fact
        or value.get("record_path")
            != review_wakeup_record_path(fact["fact_fingerprint"])
    ):
        raise AdmissionRecoveryError("review wake-up record identity differs")
    attempts = value.get("attempts")
    if not isinstance(attempts, list) or len(attempts) != 1:
        raise AdmissionRecoveryError("review wake-up record attempts are malformed")
    exact_attempts = [
        validate_review_wakeup_producer_binding(intent, attempt)
        for attempt in attempts
    ]
    numbers = [attempt["transport_attempt"] for attempt in exact_attempts]
    if numbers != [1]:
        raise AdmissionRecoveryError("review wake-up record attempt order differs")
    ack = value.get("ack")
    terminal = value.get("terminal")
    if ack is not None and terminal is not None:
        raise AdmissionRecoveryError("review wake-up record has two terminal states")
    if ack is not None:
        bound = next(
            (attempt for attempt in exact_attempts
             if attempt["binding_sha256"]
             == ack.get("producer_binding_sha256")),
            None,
        ) if isinstance(ack, Mapping) else None
        if bound is None:
            raise AdmissionRecoveryError("review wake-up record ACK attempt differs")
        _validate_review_wakeup_ack_record(ack, intent, bound)
    if terminal is not None:
        if not isinstance(terminal, Mapping):
            raise AdmissionRecoveryError("review wake-up record terminal is premature")
        receipt = validate_review_wakeup_terminal(terminal.get("receipt"), intent)
        if receipt["transport_attempts"] != numbers:
            raise AdmissionRecoveryError("review wake-up terminal attempts differ")
        validate_review_wakeup_terminal_binding(
            receipt, intent, terminal.get("binding")
        )
    return dict(record)


def record_review_wakeup_intent(
    record: Mapping[str, Any] | None,
    intent: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    semantic = validate_review_wakeup_intent(intent)
    producer = validate_review_wakeup_producer_binding(semantic, binding)
    if record is None:
        if producer["transport_attempt"] != 1:
            raise AdmissionRecoveryError("review wake-up first attempt is not one")
        value = {
            "schema": "qikvrt_human_review_wakeup_record_v1",
            "record_path": review_wakeup_record_path(
                semantic["fact_fingerprint"]
            ),
            "fact_fingerprint": semantic["fact_fingerprint"],
            "fact": semantic["fact"],
            "intent": semantic,
            "attempts": [producer],
            "ack": None,
            "terminal": None,
            "authority_boundary": "RECOVERY_ONLY",
            "native_account_review_authorized": False,
            "completion_claims": dict(COMPLETION_CLAIMS),
        }
        return _seal_review_wakeup_record(value)
    current = validate_review_wakeup_record(record)
    if current["intent"] != semantic or current["fact"] != semantic["fact"]:
        raise AdmissionRecoveryError("review wake-up durable intent differs")
    if current.get("ack") is not None or current.get("terminal") is not None:
        raise AdmissionRecoveryError("review wake-up transition is already terminal")
    raise AdmissionRecoveryError("review wake-up transport is already consumed")


def record_review_wakeup_ack(
    record: Mapping[str, Any], ack: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_review_wakeup_record(record)
    if current.get("terminal") is not None:
        raise AdmissionRecoveryError("review wake-up ACK follows terminal")
    bound = next(
        (attempt for attempt in current["attempts"]
         if attempt["binding_sha256"]
         == (ack.get("producer_binding_sha256") if isinstance(ack, Mapping) else None)),
        None,
    )
    if bound is None:
        raise AdmissionRecoveryError("review wake-up ACK producer is not durable")
    exact = _validate_review_wakeup_ack_record(ack, current["intent"], bound)
    if current.get("ack") is not None and current["ack"] != exact:
        raise AdmissionRecoveryError("review wake-up ACK identity differs")
    value = dict(current)
    value.pop("record_sha256", None)
    value["ack"] = exact
    return _seal_review_wakeup_record(value)


def record_review_wakeup_terminal(
    record: Mapping[str, Any],
    receipt: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    current = validate_review_wakeup_record(record)
    if current.get("ack") is not None:
        raise AdmissionRecoveryError("review wake-up terminal follows ACK")
    exact = validate_review_wakeup_terminal(receipt, current["intent"])
    exact_binding = validate_review_wakeup_terminal_binding(
        exact, current["intent"], binding
    )
    if exact["transport_attempts"] != [
        item["transport_attempt"] for item in current["attempts"]
    ]:
        raise AdmissionRecoveryError("review wake-up terminal attempts differ")
    terminal = {"receipt": exact, "binding": exact_binding}
    if current.get("terminal") is not None and current["terminal"] != terminal:
        raise AdmissionRecoveryError("review wake-up terminal identity differs")
    value = dict(current)
    value.pop("record_sha256", None)
    value["terminal"] = terminal
    return _seal_review_wakeup_record(value)


def validate_review_wakeup_subject(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review wake-up subject record is malformed")
    observed = dict(value)
    claimed = observed.pop("subject_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("review wake-up subject digest differs")
    if (
        observed.get("schema") != "qikvrt_human_review_wakeup_subject_v2"
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("native_account_review_authorized") is not False
        or observed.get("completion_claims") != COMPLETION_CLAIMS
        or observed.get("subject_key")
            != review_wakeup_subject_key(observed.get("subject"))
    ):
        raise AdmissionRecoveryError("review wake-up subject boundary differs")
    next_sequence = _positive(
        observed.get("next_ack_sequence"), "subject next ACK sequence"
    )
    recheck_sequence = _positive(
        observed.get("recheck_sequence"), "subject ACK recheck sequence"
    )
    count = observed.get("acknowledged_review_count")
    if (
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        or next_sequence != count + 1
        or (count == 0 and recheck_sequence != 1)
        or (count > 0 and recheck_sequence > count)
    ):
        raise AdmissionRecoveryError("review wake-up subject ACK frontier differs")
    return dict(value)


def validate_review_wakeup_subject_ack_slot(
    value: Mapping[str, Any], *, subject: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AdmissionRecoveryError("review wake-up subject ACK slot is malformed")
    observed = dict(value)
    claimed = observed.pop("slot_sha256", None)
    if claimed != _canonical_sha256(observed):
        raise AdmissionRecoveryError("review wake-up subject ACK slot digest differs")
    fact = validate_human_review_fact(observed.get("fact"))
    sequence = _positive(observed.get("sequence"), "subject ACK slot sequence")
    key = review_wakeup_subject_key(subject)
    if (
        observed.get("schema") != "qikvrt_human_review_wakeup_subject_ack_slot_v1"
        or observed.get("subject_key") != key
        or observed.get("path") != review_wakeup_subject_ack_slot_path(
            subject, sequence
        )
        or fact.get("transition_kind") != "REVIEW_STATE"
        or review_wakeup_subject_key(fact) != key
        or observed.get("authority_boundary") != "RECOVERY_ONLY"
        or observed.get("completion_claims") != COMPLETION_CLAIMS
    ):
        raise AdmissionRecoveryError("review wake-up subject ACK slot differs")
    return dict(value)


def build_review_wakeup_subject_ack_transition(
    subject_record: Mapping[str, Any] | None,
    ack: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(ack, Mapping):
        raise AdmissionRecoveryError("review wake-up subject ACK is malformed")
    fact = validate_human_review_fact(ack.get("fact"))
    if fact["transition_kind"] != "REVIEW_STATE":
        if subject_record is None:
            raise AdmissionRecoveryError("absence ACK cannot initialize a subject")
        current = validate_review_wakeup_subject(subject_record)
        return {
            "subject_after": current,
            "slot_path": None,
            "slot": None,
        }
    current = (
        empty_review_wakeup_subject(subject=fact)
        if subject_record is None
        else validate_review_wakeup_subject(subject_record)
    )
    if review_wakeup_subject_key(fact) != current["subject_key"]:
        raise AdmissionRecoveryError("review wake-up subject ACK differs")
    sequence = current["next_ack_sequence"]
    slot_path = review_wakeup_subject_ack_slot_path(fact, sequence)
    slot = {
        "schema": "qikvrt_human_review_wakeup_subject_ack_slot_v1",
        "subject_key": current["subject_key"],
        "sequence": sequence,
        "path": slot_path,
        "fact": fact,
        "authority_boundary": "RECOVERY_ONLY",
        "completion_claims": dict(COMPLETION_CLAIMS),
    }
    slot["slot_sha256"] = _canonical_sha256(slot)
    validate_review_wakeup_subject_ack_slot(slot, subject=fact)
    value = dict(current)
    value.pop("subject_sha256", None)
    value["next_ack_sequence"] = sequence + 1
    value["acknowledged_review_count"] = sequence
    value["subject_sha256"] = _canonical_sha256(value)
    return {"subject_after": value, "slot_path": slot_path, "slot": slot}


def advance_review_wakeup_subject_recheck(
    subject_record: Mapping[str, Any]
) -> dict[str, Any]:
    current = validate_review_wakeup_subject(subject_record)
    if current["acknowledged_review_count"] < 1:
        raise AdmissionRecoveryError("review wake-up subject has no ACK to recheck")
    value = dict(current)
    value.pop("subject_sha256", None)
    current_sequence = value["recheck_sequence"]
    value["recheck_sequence"] = (
        current_sequence + 1
        if current_sequence < value["acknowledged_review_count"] else 1
    )
    value["subject_sha256"] = _canonical_sha256(value)
    return value


def record_review_wakeup_subject_ack(
    subject_record: Mapping[str, Any] | None,
    ack: Mapping[str, Any],
) -> dict[str, Any]:
    return build_review_wakeup_subject_ack_transition(
        subject_record, ack
    )["subject_after"]
