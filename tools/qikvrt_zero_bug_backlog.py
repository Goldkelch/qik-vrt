#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Deterministic backlog dispatcher for the QIK-VRT Zero Bug Policy.

The dispatcher treats every open issue as active work. It never closes issues and
never infers completion. An issue with an open issue-agent PR is already owned by
that transaction and is therefore not redispatched. Every other open issue is
submitted to the existing trusted-main Autonomous issue processing workflow.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Issue:
    number: int
    title: str


def _gh_json(args: list[str]) -> Any:
    return json.loads(subprocess.check_output(["gh", "api", *args], text=True))


def _pages(path: str) -> list[Any]:
    value = json.loads(
        subprocess.check_output(
            ["gh", "api", "--paginate", "--slurp", path], text=True
        )
    )
    out: list[Any] = []
    for page in value:
        out.extend(page if isinstance(page, list) else [page])
    return out


def open_issues(repository: str) -> list[Issue]:
    rows = _pages(f"repos/{repository}/issues?state=open&per_page=100")
    issues = [
        Issue(number=int(row["number"]), title=str(row.get("title") or ""))
        for row in rows
        if "pull_request" not in row
    ]
    return sorted(issues, key=lambda item: item.number)


def has_active_issue_pr(repository: str, issue_number: int) -> bool:
    owner = repository.split("/", 1)[0]
    prs = _gh_json(
        [
            f"repos/{repository}/pulls?state=open&head={owner}:issue-agent/{issue_number}&per_page=1"
        ]
    )
    return bool(prs)


def plan(repository: str, issues: Iterable[Issue]) -> dict[str, Any]:
    active: list[int] = []
    dispatch: list[int] = []
    for issue in issues:
        if has_active_issue_pr(repository, issue.number):
            active.append(issue.number)
        else:
            dispatch.append(issue.number)
    return {
        "schema": "qikvrt_zero_bug_backlog_plan_v1",
        "repository": repository,
        "open_issue_count": len(active) + len(dispatch),
        "active_issue_prs": active,
        "dispatch_issue_numbers": dispatch,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def dispatch(repository: str, issue_numbers: Iterable[int]) -> None:
    for number in issue_numbers:
        subprocess.check_call(
            [
                "gh",
                "api",
                "--method",
                "POST",
                f"repos/{repository}/actions/workflows/issue-autonomous-processing.yml/dispatches",
                "-f",
                "ref=main",
                "-f",
                f"inputs[issue_number]={number}",
            ]
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "dispatch"))
    parser.add_argument("--repository", required=True)
    args = parser.parse_args()

    result = plan(args.repository, open_issues(args.repository))
    print(json.dumps(result, sort_keys=True, indent=2))
    if args.command == "dispatch":
        dispatch(args.repository, result["dispatch_issue_numbers"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
