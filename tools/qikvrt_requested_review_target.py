#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Resolve safe, current pull-request targets for lifecycle triggers.

The privileged lifecycle executor never trusts a pull-request number, artifact,
or shell fragment produced by an untrusted workflow. Direct events are
re-read, status commits are resolved through a unique GitHub PR association,
and workflow runs are bound to GitHub's own run-to-PR association
before their PR is re-read.  A scheduler can list the current open PR numbers,
but each selected PR is still re-observed by the executor before a write.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any, Mapping, Sequence


class TargetResolutionError(RuntimeError):
    """Raised when an event cannot be resolved safely."""


class GitHubApi:
    """Minimal read-only GitHub CLI adapter used on Actions runners."""

    def json(self, path: str) -> Any:
        return json.loads(subprocess.check_output(["gh", "api", path], text=True))

    def pages(self, path: str) -> list[Any]:
        pages = json.loads(
            subprocess.check_output(["gh", "api", "--paginate", "--slurp", path], text=True)
        )
        if not isinstance(pages, list):
            raise TargetResolutionError(f"paginated GitHub response for {path} is not a list")
        values: list[Any] = []
        for page in pages:
            if isinstance(page, list):
                values.extend(page)
            else:
                values.append(page)
        return values


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TargetResolutionError(f"{label} is not an object")
    return value


def _number(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise TargetResolutionError(f"{label} is not a positive integer")
    return value


def _repository(value: Any) -> str:
    if not isinstance(value, str) or value.count("/") != 1 or len(value) > 201:
        raise TargetResolutionError("repository must be owner/name")
    owner, name = value.split("/", 1)
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    if not owner or not name or any(character not in allowed for character in owner + name):
        raise TargetResolutionError("repository contains an invalid component")
    return value


def _expected_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise TargetResolutionError(f"{label} must be a non-empty string")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise TargetResolutionError(f"{label} contains a control character")
    return value


def _expected_workflow_path(value: Any) -> str:
    path = _expected_text(value, "expected workflow path")
    if not path.startswith(".github/workflows/") or not path.endswith((".yml", ".yaml")):
        raise TargetResolutionError("expected workflow path is not a repository workflow file")
    if "@" in path or ".." in path or "/" in path[len(".github/workflows/") :]:
        raise TargetResolutionError("expected workflow path is malformed")
    return path


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise TargetResolutionError(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise TargetResolutionError(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def resolve_direct_open_pull_request(api: GitHubApi, repository: str, number: int) -> int | None:
    """Return a direct event target only when it remains open."""
    repo = _repository(repository)
    pull_request_number = _number(number, "pull request number")
    value = _object(api.json(f"repos/{repo}/pulls/{pull_request_number}"), "pull request")
    if value.get("state") != "open":
        return None
    observed_number = _number(value.get("number", pull_request_number), "pull request number")
    if observed_number != pull_request_number:
        raise TargetResolutionError("direct pull request observation returned a different number")
    return pull_request_number


def resolve_unique_open_pull_request_for_head(
    api: GitHubApi, repository: str, head_sha: str
) -> int | None:
    """Return the one open PR currently bound to ``head_sha``.

    Zero candidates is an expected safe no-op for a stale signal.  Multiple
    candidates is a deterministic ambiguity that must not select one silently.
    """
    repo = _repository(repository)
    head = _sha(head_sha, "event head sha")
    candidates = api.pages(f"repos/{repo}/commits/{head}/pulls?per_page=100")
    matching: list[int] = []
    for candidate in candidates:
        value = _object(candidate, "commit-associated pull request")
        if value.get("state") != "open":
            continue
        candidate_head = _object(value.get("head"), "commit-associated pull request head")
        if candidate_head.get("sha") != head:
            continue
        matching.append(_number(value.get("number"), "commit-associated pull request number"))
    numbers = sorted(set(matching))
    if not numbers:
        return None
    if len(numbers) != 1:
        raise TargetResolutionError(
            "event head resolves to multiple open pull requests: "
            + ", ".join(f"#{number}" for number in numbers)
        )
    return numbers[0]


def resolve_unique_open_pull_request_for_commit(
    api: GitHubApi, repository: str, commit_sha: str
) -> int | None:
    """Resolve a unique open PR associated with a head *or* test-merge SHA.

    Legacy status events can be attached to GitHub's synthetic test-merge
    commit rather than ``pull_request.head.sha``. The API association is only a
    safe selector: the returned PR is immediately re-fetched and the executor
    later performs its full current exact-binding snapshot before any write.
    """
    repo = _repository(repository)
    commit = _sha(commit_sha, "event commit sha")
    candidates = api.pages(f"repos/{repo}/commits/{commit}/pulls?per_page=100")
    numbers: list[int] = []
    for candidate in candidates:
        value = _object(candidate, "commit-associated pull request")
        if value.get("state") == "open":
            numbers.append(_number(value.get("number"), "commit-associated pull request number"))
    unique = sorted(set(numbers))
    if not unique:
        return None
    if len(unique) != 1:
        raise TargetResolutionError(
            "event commit resolves to multiple open pull requests: "
            + ", ".join(f"#{number}" for number in unique)
        )
    return resolve_direct_open_pull_request(api, repo, unique[0])


def resolve_unique_open_pull_request_for_workflow_run(
    api: GitHubApi,
    repository: str,
    workflow_run_id: int,
    *,
    expected_workflow_name: str | None = None,
    expected_event: str | None = None,
    expected_workflow_path: str | None = None,
) -> int | None:
    """Return the one still-open PR authoritatively associated with one run.

    This is deliberately independent of ``workflow_run.head_sha``: for a
    ``pull_request_review`` workflow, GitHub may expose a generated merge SHA
    rather than the pull request branch head.  The REST run record's
    ``pull_requests`` association is the trusted selector; the selected PR is
    immediately re-fetched before it is returned.
    """
    repo = _repository(repository)
    run_id = _number(workflow_run_id, "workflow run id")
    run = _object(api.json(f"repos/{repo}/actions/runs/{run_id}"), "workflow run")
    observed_run_id = _number(run.get("id"), "workflow run id")
    if observed_run_id != run_id:
        raise TargetResolutionError("workflow run observation returned a different id")
    run_repository = _object(run.get("repository"), "workflow run repository")
    if run_repository.get("full_name") != repo:
        raise TargetResolutionError("workflow run is not bound to the expected repository")
    if expected_workflow_name is not None:
        expected_name = _expected_text(expected_workflow_name, "expected workflow name")
        if run.get("name") != expected_name:
            raise TargetResolutionError("workflow run name does not match the expected workflow")
    if expected_event is not None:
        expected_run_event = _expected_text(expected_event, "expected workflow event")
        if run.get("event") != expected_run_event:
            raise TargetResolutionError("workflow run event does not match the expected event")
    if expected_workflow_path is not None:
        expected_path = _expected_workflow_path(expected_workflow_path)
        observed_path = run.get("path")
        if not isinstance(observed_path, str) or not observed_path.startswith(expected_path + "@"):
            raise TargetResolutionError("workflow run path does not match the expected workflow path")
        _number(run.get("workflow_id"), "workflow run workflow_id")

    associations = run.get("pull_requests")
    if not isinstance(associations, list):
        raise TargetResolutionError("workflow run pull_requests is not a list")
    if len(associations) != 1:
        raise TargetResolutionError(
            "workflow run must be associated with exactly one pull request"
        )
    association = _object(associations[0], "workflow run pull request association")
    pull_request_number = _number(
        association.get("number"), "workflow run pull request number"
    )
    return resolve_direct_open_pull_request(api, repo, pull_request_number)


def resolve_unique_open_pull_request_for_run(
    api: GitHubApi,
    repository: str,
    workflow_run_id: int,
    *,
    expected_workflow_name: str | None = None,
    expected_event: str | None = None,
    expected_workflow_path: str | None = None,
) -> int | None:
    """Compatibility name for the trusted workflow-run resolver."""
    return resolve_unique_open_pull_request_for_workflow_run(
        api,
        repository,
        workflow_run_id,
        expected_workflow_name=expected_workflow_name,
        expected_event=expected_event,
        expected_workflow_path=expected_workflow_path,
    )


def resolve_all_current_open_pull_requests(api: GitHubApi, repository: str) -> list[int]:
    """List distinct current open PR numbers from GitHub's paginated endpoint.

    A response that is malformed, reports a non-open item despite the open
    filter, or repeats a number is rejected rather than silently scheduling a
    partial or ambiguous set.
    """
    repo = _repository(repository)
    candidates = api.pages(f"repos/{repo}/pulls?state=open&per_page=100")
    numbers: list[int] = []
    for candidate in candidates:
        value = _object(candidate, "open pull request")
        if value.get("state") != "open":
            raise TargetResolutionError("open pull request listing contains a non-open item")
        numbers.append(_number(value.get("number"), "open pull request number"))
    if len(set(numbers)) != len(numbers):
        raise TargetResolutionError("open pull request listing contains duplicate numbers")
    return sorted(numbers)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="owner/name")
    parser.add_argument("--expected-workflow-name")
    parser.add_argument("--expected-event")
    parser.add_argument("--expected-workflow-path")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--direct-pull-request", type=int)
    group.add_argument("--head-sha")
    group.add_argument("--commit-sha")
    group.add_argument("--workflow-run-id", type=int)
    group.add_argument("--all-open", action="store_true")
    args = parser.parse_args(argv)
    try:
        repository = _repository(args.repository)
        if (
            (
                args.expected_workflow_name is not None
                or args.expected_event is not None
                or args.expected_workflow_path is not None
            )
            and args.workflow_run_id is None
        ):
            raise TargetResolutionError(
                "workflow run expectations require --workflow-run-id"
            )
        if args.direct_pull_request is not None:
            pull_request = resolve_direct_open_pull_request(
                GitHubApi(), repository, args.direct_pull_request
            )
            result: dict[str, Any] = {"pull_request": pull_request}
        elif args.head_sha is not None:
            pull_request = resolve_unique_open_pull_request_for_head(
                GitHubApi(), repository, args.head_sha
            )
            result = {"pull_request": pull_request}
        elif args.commit_sha is not None:
            pull_request = resolve_unique_open_pull_request_for_commit(
                GitHubApi(), repository, args.commit_sha
            )
            result = {"pull_request": pull_request}
        elif args.workflow_run_id is not None:
            pull_request = resolve_unique_open_pull_request_for_workflow_run(
                GitHubApi(),
                repository,
                args.workflow_run_id,
                expected_workflow_name=args.expected_workflow_name,
                expected_event=args.expected_event,
                expected_workflow_path=args.expected_workflow_path,
            )
            result = {"pull_request": pull_request}
        else:
            result = {"pull_requests": resolve_all_current_open_pull_requests(GitHubApi(), repository)}
    except (OSError, ValueError, json.JSONDecodeError, TargetResolutionError) as exc:
        print(json.dumps({"error": "INVALID_LIFECYCLE_TRIGGER", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
