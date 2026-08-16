#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Collect a complete, read-only exact-binding pull-request review snapshot."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import subprocess
from typing import Any, Mapping, Sequence
from urllib.parse import quote


class SnapshotError(RuntimeError):
    """Raised when a required GitHub observation is incomplete or malformed."""


class GitHubApi:
    """Small, shell-free adapter around the GitHub CLI available in Actions."""

    def json(self, path: str) -> Any:
        return json.loads(subprocess.check_output(["gh", "api", path], text=True))

    def pages(self, path: str) -> list[Any]:
        pages = json.loads(
            subprocess.check_output(["gh", "api", "--paginate", "--slurp", path], text=True)
        )
        if not isinstance(pages, list):
            raise SnapshotError(f"paginated GitHub response for {path} is not a list")
        values: list[Any] = []
        for page in pages:
            if isinstance(page, list):
                values.extend(page)
            else:
                values.append(page)
        return values

    def raw(self, path: str, accept: str) -> bytes:
        return subprocess.check_output(["gh", "api", "-H", f"Accept: {accept}", path])

    def graphql(self, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        command = ["gh", "api", "graphql", "-f", f"query={query}"]
        for key, value in variables.items():
            flag = "-F" if isinstance(value, int) else "-f"
            command.extend([flag, f"{key}={value}"])
        result = json.loads(subprocess.check_output(command, text=True))
        if not isinstance(result, Mapping):
            raise SnapshotError("GraphQL response is not an object")
        return result


THREAD_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $after) {
        nodes { isResolved }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

# GitHub's pull-request files endpoint is documented to return at most 3,000
# files. The rendered diff endpoint has lower display limits. A lifecycle
# snapshot must never label an API-truncated scope as an exact reviewed scope.
MAX_PULL_REQUEST_FILES_API = 3000
MAX_RENDERED_DIFF_FILES = 300
MAX_RENDERED_DIFF_LINES = 20000
# GitHub can limit a single rendered raw-diff file at 500 KiB. A total below
# this stricter bound also keeps every individual file below that boundary.
MAX_RENDERED_DIFF_BYTES = 500 * 1024


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SnapshotError(f"{label} is not an object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SnapshotError(f"{label} is not a non-empty string")
    return value


def _sha(value: Any, label: str) -> str:
    value = _text(value, label)
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise SnapshotError(f"{label} is not a lowercase Git SHA-1")
    return value


def _optional_sha(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _sha(value, label)


def _timestamp(value: Any, label: str) -> tuple[str, datetime]:
    value = _text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise SnapshotError(f"{label} must include a timezone")
    return value, parsed


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SnapshotError(f"{label} is not a non-negative integer")
    return value


def _commit_tree(api: GitHubApi, repository: str, commit: str) -> str:
    value = _object(api.json(f"repos/{repository}/commits/{commit}"), "commit")
    nested = _object(value.get("commit"), "commit.commit")
    tree = _object(nested.get("tree"), "commit.commit.tree")
    return _sha(tree.get("sha"), "commit tree sha")


def _review_threads(api: GitHubApi, owner: str, name: str, number: int) -> list[Mapping[str, Any]]:
    after: str | None = None
    threads: list[Mapping[str, Any]] = []
    while True:
        variables: dict[str, Any] = {"owner": owner, "name": name, "number": number}
        if after is not None:
            variables["after"] = after
        response = _object(api.graphql(THREAD_QUERY, variables), "GraphQL response")
        data = _object(response.get("data"), "GraphQL data")
        repository = _object(data.get("repository"), "GraphQL repository")
        pull_request = _object(repository.get("pullRequest"), "GraphQL pull request")
        connection = _object(pull_request.get("reviewThreads"), "GraphQL review threads")
        nodes = connection.get("nodes")
        if not isinstance(nodes, list) or not all(isinstance(node, Mapping) for node in nodes):
            raise SnapshotError("GraphQL review thread nodes are malformed")
        threads.extend(nodes)
        page_info = _object(connection.get("pageInfo"), "GraphQL review thread page info")
        has_next = page_info.get("hasNextPage")
        if not isinstance(has_next, bool):
            raise SnapshotError("GraphQL review thread pagination is malformed")
        if not has_next:
            return threads
        after = _text(page_info.get("endCursor"), "GraphQL review thread end cursor")


def _check_runs(api: GitHubApi, repository: str, commit: str) -> list[Mapping[str, Any]]:
    pages = api.pages(f"repos/{repository}/commits/{commit}/check-runs?per_page=100&filter=latest")
    runs: list[Mapping[str, Any]] = []
    for page in pages:
        value = _object(page, "check-runs page")
        page_runs = value.get("check_runs")
        if not isinstance(page_runs, list) or not all(isinstance(run, Mapping) for run in page_runs):
            raise SnapshotError("check-runs page is malformed")
        runs.extend(page_runs)
    return runs


def _legacy_statuses(api: GitHubApi, repository: str, commit: str) -> list[Mapping[str, Any]]:
    values = api.pages(f"repos/{repository}/commits/{commit}/statuses?per_page=100")
    if not all(isinstance(value, Mapping) for value in values):
        raise SnapshotError("legacy commit statuses are malformed")
    # The endpoint is historical: a failed context that was later retried can
    # remain in its response.  Collapse it deterministically to the newest
    # status for each context instead of treating an old retry as perpetual
    # gate failure.
    latest: dict[str, tuple[tuple[str, int], Mapping[str, Any]]] = {}
    for value in values:
        context = _text(value.get("context"), "legacy commit status context")
        timestamp = value.get("updated_at") or value.get("created_at")
        timestamp = _text(timestamp, "legacy commit status timestamp")
        status_id = value.get("id")
        if isinstance(status_id, bool) or not isinstance(status_id, int):
            raise SnapshotError("legacy commit status id is malformed")
        order = (timestamp, status_id)
        key = context.casefold()
        if key not in latest or order > latest[key][0]:
            latest[key] = (order, value)
    return [latest[key][1] for key in sorted(latest)]


def _gate_observations(
    api: GitHubApi,
    repository: str,
    *,
    head: str,
    test_merge: str | None,
) -> list[dict[str, Any]]:
    """Return every current check/status on head and GitHub's test merge.

    Required checks can be attached to the synthetic PR merge context rather
    than the branch head.  Both contexts are bound and every observed gate is
    retained with its exact source SHA for evidence-bound blocker reporting.
    """
    contexts: list[tuple[str, str]] = [("head", head)]
    if test_merge is not None and test_merge != head:
        contexts.append(("test_merge", test_merge))
    observations: list[dict[str, Any]] = []
    for context, commit in contexts:
        for check in _check_runs(api, repository, commit):
            name = _text(check.get("name"), "check-run name")
            status = _text(check.get("status"), "check-run status")
            conclusion = check.get("conclusion")
            if conclusion is not None and not isinstance(conclusion, str):
                raise SnapshotError("check-run conclusion is malformed")
            check_id = check.get("id")
            if check_id is not None and (isinstance(check_id, bool) or not isinstance(check_id, int)):
                raise SnapshotError("check-run id is malformed")
            details_url = check.get("details_url") or check.get("html_url")
            if details_url is not None and not isinstance(details_url, str):
                raise SnapshotError("check-run details URL is malformed")
            observations.append(
                {
                    "kind": "check_run",
                    "context": context,
                    "sha": commit,
                    "name": name,
                    "status": status,
                    "conclusion": conclusion,
                    "id": check_id,
                    "details_url": details_url,
                }
            )
        for status in _legacy_statuses(api, repository, commit):
            name = _text(status.get("context"), "legacy status context")
            state = _text(status.get("state"), "legacy status state")
            status_id = status.get("id")
            if isinstance(status_id, bool) or not isinstance(status_id, int):
                raise SnapshotError("legacy status id is malformed")
            target_url = status.get("target_url")
            if target_url is not None and not isinstance(target_url, str):
                raise SnapshotError("legacy status target URL is malformed")
            observations.append(
                {
                    "kind": "legacy_status",
                    "context": context,
                    "sha": commit,
                    "name": name,
                    "state": state,
                    "id": status_id,
                    "target_url": target_url,
                }
            )
    return sorted(
        observations,
        key=lambda item: (
            item["context"],
            item["kind"],
            item["name"].casefold(),
            str(item.get("id", "")),
        ),
    )


def _gate_is_green(observation: Mapping[str, Any]) -> bool:
    if observation["kind"] == "check_run":
        return observation["status"] == "completed" and observation["conclusion"] in {
            "success",
            "skipped",
        }
    return observation["state"] == "success"


def _team_label(team: Mapping[str, Any], label: str) -> str:
    slug = team.get("slug")
    if isinstance(slug, str) and slug:
        return slug
    name = team.get("name")
    if isinstance(name, str) and name:
        return name
    raise SnapshotError(f"{label} has no slug or name")


def _requested_reviewer_label(event: Mapping[str, Any], label: str) -> str | None:
    reviewer = event.get("requested_reviewer")
    if reviewer is None:
        return None
    reviewer_object = _object(reviewer, label)
    return _text(reviewer_object.get("login"), f"{label} login")


def _requested_team_label(event: Mapping[str, Any], label: str) -> str | None:
    team = event.get("requested_team")
    if team is None:
        return None
    return _team_label(_object(team, label), label)


def _request_history(
    events: Sequence[Any],
    *,
    actor_label: str,
    actor_from_event,
) -> tuple[list[str], dict[str, str], dict[str, int]]:
    """Reduce request/remove events in their explicit GitHub sequence.

    GitHub's REST ordering is not a semantic guarantee.  A removed reviewer is
    excluded unless a later request reactivates it; a reviewer consumed by a
    submitted review remains eligible only when GitHub has emitted no explicit
    removal event.
    """
    ordered: list[tuple[tuple[datetime, int], Mapping[str, Any]]] = []
    for value in events:
        if not isinstance(value, Mapping):
            raise SnapshotError("requested-review event is malformed")
        event_name = value.get("event")
        if event_name not in {"review_requested", "review_request_removed"}:
            continue
        actor = actor_from_event(value, f"{actor_label} event")
        if actor is None:
            # This is the other actor kind (team versus user), not malformed.
            continue
        timestamp_text, timestamp = _timestamp(value.get("created_at"), f"{actor_label} event created_at")
        event_id = value.get("id")
        if isinstance(event_id, bool) or not isinstance(event_id, int):
            raise SnapshotError(f"{actor_label} event id is malformed")
        ordered.append(((timestamp, event_id), value))
    state: dict[str, tuple[str, str, int]] = {}
    for _, event in sorted(ordered, key=lambda entry: entry[0]):
        actor = actor_from_event(event, f"{actor_label} event")
        assert actor is not None
        key = actor.casefold()
        if event["event"] == "review_requested":
            timestamp, _ = _timestamp(event.get("created_at"), f"{actor_label} event created_at")
            event_id = event["id"]
            assert isinstance(event_id, int) and not isinstance(event_id, bool)
            state[key] = (actor, timestamp, event_id)
        else:
            state.pop(key, None)
    names = sorted((value[0] for value in state.values()), key=str.casefold)
    requested_at = {
        value[0]: value[1] for _, value in sorted(state.items(), key=lambda entry: entry[0])
    }
    event_ids = {
        value[0]: value[2] for _, value in sorted(state.items(), key=lambda entry: entry[0])
    }
    return names, requested_at, event_ids


def _validate_request_event_actors(events: Sequence[Any]) -> None:
    for value in events:
        if not isinstance(value, Mapping):
            raise SnapshotError("requested-review event is malformed")
        if value.get("event") not in {"review_requested", "review_request_removed"}:
            continue
        if value.get("requested_reviewer") is None and value.get("requested_team") is None:
            raise SnapshotError("requested-review event has no reviewer or team actor")


def _active_reviewer_logins(pull_request: Mapping[str, Any]) -> list[str]:
    active = pull_request.get("requested_reviewers")
    if not isinstance(active, list) or not all(
        isinstance(reviewer, Mapping) and isinstance(reviewer.get("login"), str) and reviewer["login"]
        for reviewer in active
    ):
        raise SnapshotError("active requested-reviewer observation is malformed")
    return sorted({reviewer["login"] for reviewer in active}, key=str.casefold)


def _active_team_labels(pull_request: Mapping[str, Any]) -> list[str]:
    active = pull_request.get("requested_teams")
    if not isinstance(active, list):
        raise SnapshotError("active requested-team observation is malformed")
    teams: dict[str, str] = {}
    for team in active:
        name = _team_label(_object(team, "active requested review team"), "active requested review team")
        teams.setdefault(name.casefold(), name)
    return sorted(teams.values(), key=str.casefold)


def _competing_writers(
    api: GitHubApi,
    repository: str,
    number: int,
    pull_request: Mapping[str, Any],
) -> tuple[bool, str]:
    """Detect another open pull request sharing this mutable head ref."""
    state = _text(pull_request.get("state"), "pull request state")
    if state != "open":
        return True, f"pull request state is {state!r}, not open"
    head = _object(pull_request.get("head"), "pull request head")
    head_ref = _text(head.get("ref"), "pull request head ref")
    head_repository = _object(head.get("repo"), "pull request head repository")
    head_owner = _object(head_repository.get("owner"), "pull request head repository owner")
    owner_login = _text(head_owner.get("login"), "pull request head repository owner login")
    encoded_selector = quote(f"{owner_login}:{head_ref}", safe="")
    candidates = api.pages(
        f"repos/{repository}/pulls?state=open&head={encoded_selector}&per_page=100"
    )
    other_numbers: list[int] = []
    for candidate in candidates:
        value = _object(candidate, "competing pull request")
        candidate_number = value.get("number")
        if isinstance(candidate_number, bool) or not isinstance(candidate_number, int):
            raise SnapshotError("competing pull request number is malformed")
        candidate_head = _object(value.get("head"), "competing pull request head")
        if candidate_number != number and candidate_head.get("ref") == head_ref:
            other_numbers.append(candidate_number)
    if other_numbers:
        return (
            True,
            "open pull request(s) share mutable candidate head ref: "
            + ", ".join(f"#{candidate}" for candidate in sorted(set(other_numbers))),
        )
    return False, "no open pull request shares the mutable candidate head ref"


def observe_pull_request(api: GitHubApi, repository: str, number: int) -> dict[str, Any]:
    """Return all exact observations needed by the fail-closed decision core."""
    if "/" not in repository:
        raise SnapshotError("repository must be owner/name")
    owner, name = repository.split("/", 1)
    initial = _object(api.json(f"repos/{repository}/pulls/{number}"), "pull request")
    initial_head = _object(initial.get("head"), "pull request head")
    initial_base = _object(initial.get("base"), "pull request base")
    initial_state = _text(initial.get("state"), "pull request state")
    changed_file_count = _nonnegative_int(initial.get("changed_files"), "pull request changed_files")
    if changed_file_count > MAX_PULL_REQUEST_FILES_API:
        raise SnapshotError(
            "pull request changed_files exceeds GitHub files API completeness bound "
            f"({changed_file_count} > {MAX_PULL_REQUEST_FILES_API})"
        )
    head = _sha(initial_head.get("sha"), "pull request head sha")
    base = _sha(initial_base.get("sha"), "pull request base sha")
    base_ref = _text(initial_base.get("ref"), "pull request base ref")
    merge_commit = _optional_sha(initial.get("merge_commit_sha"), "pull request test-merge sha")
    updated_at, _ = _timestamp(initial.get("updated_at"), "pull request updated_at")
    tree = _commit_tree(api, repository, head)

    files = api.pages(f"repos/{repository}/pulls/{number}/files?per_page=100")
    if not all(
        isinstance(item, Mapping)
        and isinstance(item.get("filename"), str)
        and (
            item.get("previous_filename") is None
            or isinstance(item.get("previous_filename"), str)
        )
        for item in files
    ):
        raise SnapshotError("changed-path observation is malformed")
    if len(files) != changed_file_count:
        raise SnapshotError(
            "changed-path observation count does not match pull request changed_files "
            f"({len(files)} != {changed_file_count})"
        )
    changed_paths = sorted(
        {
            path
            for item in files
            for path in (item["filename"], item.get("previous_filename"))
            if isinstance(path, str) and path
        }
    ) or ["<no-paths>"]
    diff = api.raw(f"repos/{repository}/pulls/{number}", "application/vnd.github.diff")
    # Count only actual diff headers, never an identical string in changed
    # source text (for example an added line beginning `+diff --git`).
    diff_file_count = sum(line.startswith(b"diff --git ") for line in diff.splitlines())
    diff_line_count = diff.count(b"\n")
    if changed_file_count > MAX_RENDERED_DIFF_FILES:
        raise SnapshotError(
            "pull request changed_files exceeds bounded rendered-diff coverage "
            f"({changed_file_count} > {MAX_RENDERED_DIFF_FILES})"
        )
    if len(diff) >= MAX_RENDERED_DIFF_BYTES or diff_line_count >= MAX_RENDERED_DIFF_LINES:
        raise SnapshotError(
            "rendered diff reaches GitHub completeness boundary "
            f"(bytes={len(diff)}, lines={diff_line_count})"
        )
    if diff_file_count != changed_file_count:
        raise SnapshotError(
            "rendered diff file headers do not match pull request changed_files "
            f"({diff_file_count} != {changed_file_count})"
        )
    comments = api.pages(f"repos/{repository}/issues/{number}/comments?per_page=100")
    reviews = api.pages(f"repos/{repository}/pulls/{number}/reviews?per_page=100")
    events = api.pages(f"repos/{repository}/issues/{number}/events?per_page=100")
    if not all(isinstance(item, Mapping) for item in comments):
        raise SnapshotError("comment observation is malformed")
    if not all(isinstance(item, Mapping) for item in reviews):
        raise SnapshotError("review observation is malformed")

    _validate_request_event_actors(events)
    history, requested_at, requested_event_ids = _request_history(
        events,
        actor_label="requested reviewer",
        actor_from_event=_requested_reviewer_label,
    )
    team_history, team_requested_at, team_requested_event_ids = _request_history(
        events,
        actor_label="requested team",
        actor_from_event=_requested_team_label,
    )
    threads = _review_threads(api, owner, name, number)
    if not all(isinstance(thread.get("isResolved"), bool) for thread in threads):
        raise SnapshotError("review thread resolution state is malformed")
    gate_observations = _gate_observations(
        api, repository, head=head, test_merge=merge_commit
    )
    gates_green = bool(gate_observations) and all(
        _gate_is_green(gate) for gate in gate_observations
    )

    # This final identity reobservation prevents the decision core from mixing
    # a candidate binding sampled at the start with a head/base/tree that moved
    # while diff, review, and gate observations were in flight.
    current = _object(api.json(f"repos/{repository}/pulls/{number}"), "final pull request")
    current_head_object = _object(current.get("head"), "final pull request head")
    current_base_object = _object(current.get("base"), "final pull request base")
    current_state = _text(current.get("state"), "final pull request state")
    current_head = _sha(current_head_object.get("sha"), "final pull request head sha")
    current_base = _sha(current_base_object.get("sha"), "final pull request base sha")
    current_tree = _commit_tree(api, repository, current_head)
    current_base_ref = _text(current_base_object.get("ref"), "final pull request base ref")
    current_merge_commit = _optional_sha(
        current.get("merge_commit_sha"), "final pull request test-merge sha"
    )
    current_updated_at, _ = _timestamp(current.get("updated_at"), "final pull request updated_at")
    observed_base = _object(api.json(f"repos/{repository}/commits/{current_base_ref}"), "final base ref")
    active_logins = _active_reviewer_logins(current)
    active_teams = _active_team_labels(current)
    if current_head == head and current_base == base and current_base_ref == base_ref:
        competing_writer_or_supersession, competing_writer_detail = _competing_writers(
            api, repository, number, current
        )
    else:
        competing_writer_or_supersession = False
        competing_writer_detail = "not evaluated because final exact candidate identity drifted"

    return {
        "repository": repository,
        "pull_request": number,
        "state": initial_state,
        "current_state": current_state,
        "base_ref": base_ref,
        "current_base_ref": current_base_ref,
        "base_sha": base,
        "current_pull_request_base_sha": current_base,
        "current_base_sha": _sha(observed_base.get("sha"), "observed current base sha"),
        "head_sha": head,
        "current_head_sha": current_head,
        "tree_sha": tree,
        "current_tree_sha": current_tree,
        "merge_commit_sha": merge_commit,
        "current_merge_commit_sha": current_merge_commit,
        "updated_at": updated_at,
        "current_updated_at": current_updated_at,
        "active_requested_reviewers": active_logins,
        "requested_reviewer_history": history,
        "requested_reviewer_requested_at": requested_at,
        "requested_reviewer_request_event_ids": requested_event_ids,
        "active_requested_teams": active_teams,
        "requested_team_history": team_history,
        "requested_team_requested_at": team_requested_at,
        "requested_team_request_event_ids": team_requested_event_ids,
        "changed_paths": changed_paths,
        "diff_sha256": hashlib.sha256(diff).hexdigest(),
        "diff_bytes": len(diff),
        "comments": comments,
        "reviews": reviews,
        "unresolved_threads": sum(not thread["isResolved"] for thread in threads),
        "gate_coverage": "OBSERVED_ACTIONS_AND_LEGACY_ONLY",
        "all_observed_candidate_gates_terminal_green": gates_green,
        "check_run_count": sum(gate["kind"] == "check_run" for gate in gate_observations),
        "legacy_status_count": sum(gate["kind"] == "legacy_status" for gate in gate_observations),
        "gate_observations": gate_observations,
        "competing_writer_or_supersession": competing_writer_or_supersession,
        "competing_writer_detail": competing_writer_detail,
        "existing_lifecycle_reviews": reviews,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="owner/name")
    parser.add_argument("--pull-request", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        value = observe_pull_request(GitHubApi(), args.repository, args.pull_request)
    except (OSError, ValueError, json.JSONDecodeError, SnapshotError) as exc:
        print(json.dumps({"error": "INVALID_REVIEW_SNAPSHOT", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
