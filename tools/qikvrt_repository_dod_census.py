#!/usr/bin/env python3
"""Read-only exact-subject census for QIK-VRT repository DoD carriers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

PR_ALLOWED = {"MERGE", "SUPERSEDE", "CLOSE_AS_REDUNDANT", "REJECT_WITH_EVIDENCE"}
BRANCH_ALLOWED = {
    "MERGED",
    "SUPERSEDED",
    "REDUNDANT",
    "HISTORICAL/RETAINED_BY_POLICY",
    "PRODUCTIVE_CURRENT_CANDIDATE",
}
MARKER = "<!-- qikvrt-dod-pr-disposition:"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def ancestor(commit: str, subject: str) -> bool | None:
    probe = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, subject],
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode == 0:
        return True
    if probe.returncode == 1:
        return False
    return None


def explicit_pr_disposition(body: Any) -> str | None:
    if not isinstance(body, str):
        return None
    for value in PR_ALLOWED:
        if f"{MARKER}{value} -->" in body:
            return value
    return None


def classify_pr(pr: Mapping[str, Any], subject: str, current_pr: int) -> dict[str, Any]:
    number = pr.get("number")
    head = ((pr.get("head") or {}).get("sha")) if isinstance(pr, Mapping) else None
    row = {"number": number, "head": head, "state": pr.get("state")}
    if not isinstance(number, int) or not isinstance(head, str) or len(head) != 40:
        return {**row, "regarded": False, "disposition": "UNREGARDED", "reason": "INVALID_PR_IDENTITY"}
    if number == current_pr and head == subject:
        return {**row, "regarded": True, "disposition": "MERGE", "reason": "CURRENT_FINAL_CANDIDATE"}
    rel = ancestor(head, subject)
    if rel is True:
        return {**row, "regarded": True, "disposition": "SUPERSEDE", "reason": "HEAD_ANCESTOR_OF_CANDIDATE"}
    explicit = explicit_pr_disposition(pr.get("body"))
    if explicit is not None:
        return {**row, "regarded": True, "disposition": explicit, "reason": "EXPLICIT_EVIDENCE_BOUND_DISPOSITION"}
    return {
        **row,
        "regarded": False,
        "disposition": "UNREGARDED",
        "reason": "HEAD_NOT_PROVED_ABSORBED_OR_DISPOSED",
        "ancestor_probe": rel,
    }


def classify_branch(name: str, tip: str, subject: str, main_head: str) -> dict[str, Any]:
    row = {"name": name, "tip": tip}
    if name == "main":
        return {**row, "regarded": True, "disposition": "MERGED", "reason": "DEFAULT_BRANCH"}
    if tip == subject and subject != main_head:
        return {
            **row,
            "regarded": True,
            "disposition": "PRODUCTIVE_CURRENT_CANDIDATE",
            "reason": "EXACT_FINAL_CANDIDATE",
        }
    rel = ancestor(tip, subject)
    if rel is True:
        return {**row, "regarded": True, "disposition": "SUPERSEDED", "reason": "TIP_ANCESTOR_OF_CANDIDATE"}
    return {
        **row,
        "regarded": False,
        "disposition": "UNREGARDED",
        "reason": "TIP_NOT_PROVED_ABSORBED_OR_DISPOSED",
        "ancestor_probe": rel,
    }


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("open PR snapshot must be a JSON list")
    if value and all(isinstance(page, list) for page in value):
        rows = [row for page in value for row in page]
    else:
        rows = value
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("open PR snapshot contains a non-object")
    return rows


def branch_rows() -> list[tuple[str, str]]:
    raw = git("for-each-ref", "--format=%(refname:short)\t%(objectname)", "refs/remotes/origin/")
    rows: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        name, tip = line.split("\t", 1)
        if name == "origin/HEAD":
            continue
        if not name.startswith("origin/"):
            continue
        rows.append((name[len("origin/"):], tip))
    return rows


def build(repository: str, subject: str, tree: str, current_pr: int, open_prs: Path) -> dict[str, Any]:
    actual_head = git("rev-parse", "HEAD")
    actual_tree = git("rev-parse", "HEAD^{tree}")
    if (actual_head, actual_tree) != (subject, tree):
        raise ValueError("EXACT_SUBJECT_DRIFT")
    main_head = git("rev-parse", "refs/remotes/origin/main")
    prs = flatten_pages(json.loads(open_prs.read_text(encoding="utf-8")))
    pr_rows = [classify_pr(pr, subject, current_pr) for pr in prs]
    branches = [classify_branch(name, tip, subject, main_head) for name, tip in branch_rows()]
    unregarded_prs = [row["number"] for row in pr_rows if not row["regarded"]]
    unregarded_branches = [row["name"] for row in branches if not row["regarded"]]
    candidate_on_main = subject == main_head
    return {
        "schema": "qikvrt_repository_dod_census_v1",
        "repository": repository,
        "subject": {"head": subject, "tree": tree},
        "main_head": main_head,
        "inventory_complete": True,
        "counts": {
            "open_pull_requests": len(pr_rows),
            "branch_refs": len(branches),
            "unregarded_pull_requests": len(unregarded_prs),
            "unregarded_branches": len(unregarded_branches),
        },
        "all_pull_requests_regarded": not unregarded_prs,
        "all_branches_regarded": not unregarded_branches,
        "all_productive_branches_merged": (
            candidate_on_main and not unregarded_prs and not unregarded_branches
        ),
        "pull_requests": pr_rows,
        "branches": branches,
        "unregarded_pull_requests": unregarded_prs,
        "unregarded_branches": unregarded_branches,
        "predecessor_evidence_transfer": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository", required=True)
    p.add_argument("--subject-head", required=True)
    p.add_argument("--subject-tree", required=True)
    p.add_argument("--current-pr", required=True, type=int)
    p.add_argument("--open-prs", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    try:
        report = build(
            args.repository,
            args.subject_head,
            args.subject_tree,
            args.current_pr,
            args.open_prs,
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("HOLD_UNVERIFIED " + str(exc))
        return 2
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
