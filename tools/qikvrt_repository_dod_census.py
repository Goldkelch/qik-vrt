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
    "PRODUCTIVE_UNMERGED",
}
MARKER = "<!-- qikvrt-dod-pr-disposition:"
OBSERVED_SCHEMA = "qikvrt_open_pr_snapshot_v1"
UNAVAILABLE_SCHEMA = "qikvrt_open_pr_snapshot_unavailable_v1"


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


def same_tree(left: str, right: str) -> bool | None:
    try:
        return git("rev-parse", left + "^{tree}") == git("rev-parse", right + "^{tree}")
    except subprocess.CalledProcessError:
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
    head_obj = pr.get("head") or {}
    head = head_obj.get("sha") if isinstance(head_obj, Mapping) else None
    head_ref = head_obj.get("ref") if isinstance(head_obj, Mapping) else None
    row = {
        "number": number,
        "head": head,
        "head_ref": head_ref,
        "state": pr.get("state"),
    }
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


def _linked_branch_disposition(pr: Mapping[str, Any]) -> tuple[str, str] | None:
    if pr.get("regarded") is not True:
        return None
    disposition = pr.get("disposition")
    if disposition == "SUPERSEDE":
        return "SUPERSEDED", "OPEN_PR_PROVES_SUPERSESSION"
    if disposition == "CLOSE_AS_REDUNDANT":
        return "REDUNDANT", "OPEN_PR_PROVES_REDUNDANCY"
    if disposition == "REJECT_WITH_EVIDENCE":
        return "HISTORICAL/RETAINED_BY_POLICY", "OPEN_PR_EVIDENCE_BOUND_REJECTION"
    if disposition == "MERGE":
        return "PRODUCTIVE_UNMERGED", "REGARDED_OPEN_PR_REMAINS_PRODUCTIVE"
    return None


def classify_branch(
    name: str,
    tip: str,
    subject: str,
    main_head: str,
    pr_by_ref: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    row = {"name": name, "tip": tip}
    if name == "main":
        return {**row, "regarded": True, "disposition": "MERGED", "reason": "DEFAULT_BRANCH"}
    if tip == subject:
        if subject == main_head:
            return {**row, "regarded": True, "disposition": "REDUNDANT", "reason": "TIP_EQUALS_EXACT_MAIN"}
        return {
            **row,
            "regarded": True,
            "disposition": "PRODUCTIVE_CURRENT_CANDIDATE",
            "reason": "EXACT_FINAL_CANDIDATE",
        }

    rel = ancestor(tip, subject)
    if rel is True:
        return {**row, "regarded": True, "disposition": "SUPERSEDED", "reason": "TIP_ANCESTOR_OF_CANDIDATE"}

    equal = same_tree(tip, subject)
    if equal is True:
        return {**row, "regarded": True, "disposition": "REDUNDANT", "reason": "TREE_IDENTICAL_TO_CANDIDATE"}

    linked = (pr_by_ref or {}).get(name)
    if isinstance(linked, Mapping) and linked.get("head") == tip:
        derived = _linked_branch_disposition(linked)
        if derived is not None:
            disposition, reason = derived
            return {
                **row,
                "regarded": True,
                "disposition": disposition,
                "reason": reason,
                "pull_request": linked.get("number"),
            }

    return {
        **row,
        "regarded": False,
        "disposition": "UNREGARDED",
        "reason": "TIP_NOT_PROVED_ABSORBED_OR_DISPOSED",
        "ancestor_probe": rel,
        "tree_equal_probe": equal,
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


def load_pr_snapshot(path: Path) -> tuple[list[dict[str, Any]], bool, str | None, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, Mapping) and value.get("schema") == UNAVAILABLE_SCHEMA:
        if value.get("state") != "HOLD_UNVERIFIED":
            raise ValueError("unavailable PR snapshot must be HOLD_UNVERIFIED")
        reason = value.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError("unavailable PR snapshot requires reason")
        return [], False, reason, "UNAVAILABLE"

    if isinstance(value, Mapping) and value.get("schema") == OBSERVED_SCHEMA:
        if value.get("state") != "OBSERVED":
            raise ValueError("observed PR snapshot must be OBSERVED")
        source = value.get("source")
        if source not in {"REST", "GRAPHQL"}:
            raise ValueError("observed PR snapshot requires REST or GRAPHQL source")
        return flatten_pages(value.get("pull_requests")), True, None, source

    return flatten_pages(value), True, None, "LEGACY_LIST"


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
    prs, pr_snapshot_complete, pr_snapshot_reason, pr_snapshot_source = load_pr_snapshot(open_prs)
    pr_rows = [classify_pr(pr, subject, current_pr) for pr in prs]
    pr_by_ref = {
        row["head_ref"]: row
        for row in pr_rows
        if isinstance(row.get("head_ref"), str) and row["head_ref"]
    }
    branches = [
        classify_branch(name, tip, subject, main_head, pr_by_ref)
        for name, tip in branch_rows()
    ]

    unregarded_prs = [row["number"] for row in pr_rows if not row["regarded"]]
    unregarded_branches = [row["name"] for row in branches if not row["regarded"]]
    productive_unmerged = [
        row["name"]
        for row in branches
        if row.get("disposition") in {"PRODUCTIVE_CURRENT_CANDIDATE", "PRODUCTIVE_UNMERGED"}
    ]
    candidate_on_main = subject == main_head
    inventory_complete = pr_snapshot_complete

    all_prs_regarded = pr_snapshot_complete and not unregarded_prs
    all_branches_regarded = not unregarded_branches
    all_productive_merged = (
        inventory_complete
        and candidate_on_main
        and all_prs_regarded
        and all_branches_regarded
        and not productive_unmerged
    )

    reasons: list[str] = []
    if not pr_snapshot_complete:
        reasons.append("OPEN_PR_SNAPSHOT_UNAVAILABLE:" + str(pr_snapshot_reason))

    return {
        "schema": "qikvrt_repository_dod_census_v1",
        "repository": repository,
        "subject": {"head": subject, "tree": tree},
        "main_head": main_head,
        "state": "OBSERVED" if inventory_complete else "HOLD_UNVERIFIED",
        "inventory_complete": inventory_complete,
        "inventory_reasons": reasons,
        "pr_snapshot": {
            "complete": pr_snapshot_complete,
            "reason": pr_snapshot_reason,
            "source": pr_snapshot_source,
            "fabricated_fallback": False,
        },
        "branch_snapshot": {
            "complete": True,
            "source": "FETCHED_GIT_REFS",
        },
        "counts": {
            "open_pull_requests": len(pr_rows) if pr_snapshot_complete else None,
            "branch_refs": len(branches),
            "unregarded_pull_requests": len(unregarded_prs) if pr_snapshot_complete else None,
            "unregarded_branches": len(unregarded_branches),
            "productive_unmerged_branches": len(productive_unmerged),
        },
        "all_pull_requests_regarded": all_prs_regarded,
        "all_branches_regarded": all_branches_regarded,
        "all_productive_branches_merged": all_productive_merged,
        "pull_requests": pr_rows,
        "branches": branches,
        "unregarded_pull_requests": unregarded_prs if pr_snapshot_complete else [],
        "unregarded_branches": unregarded_branches,
        "productive_unmerged_branches": productive_unmerged,
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
    print(json.dumps({
        "state": report["state"],
        "inventory_complete": report["inventory_complete"],
        "counts": report["counts"],
        "inventory_reasons": report["inventory_reasons"],
        "pr_snapshot_source": report["pr_snapshot"]["source"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
