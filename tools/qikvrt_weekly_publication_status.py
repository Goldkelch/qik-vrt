#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Emit one fail-closed weekly publication-path status into a tracking issue."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

TRACKED_PRS = (1120, 1140, 1138, 1141)
DEFAULT_ISSUE = 1186
MARKER = "qikvrt-weekly-publication-status:v1"
API = "https://api.github.com"
PUBLIC_HOSTS = {"zenodo.org", "doi.org", "datatracker.ietf.org", "www.ietf.org"}
PUBLIC_URL_RE = re.compile(
    r"https://(?:zenodo\\.org/records/\\d+|doi\\.org/10\\.5281/zenodo\\.\\d+|"
    r"datatracker\\.ietf\\.org/doc/[A-Za-z0-9._~!$&'()*+,;=:@%/-]+|"
    r"www\\.ietf\\.org/archive/id/[A-Za-z0-9._~!$&'()*+,;=:@%/-]+)"
)
EVIDENCE_NAME_RE = re.compile(
    r"(zenodo|publication|public[_-]?(?:readback|evidence|status)|doi)",
    re.IGNORECASE,
)


class TrackerError(RuntimeError):
    pass


class GitHub:
    def __init__(self, repository: str, token: str):
        if "/" not in repository:
            raise TrackerError("repository must be owner/name")
        if not token:
            raise TrackerError("GITHUB_TOKEN is missing")
        self.repository = repository
        self.token = token

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, str]]:
        body = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + self.token,
            "User-Agent": "qikvrt-weekly-publication-status/1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if payload is not None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            API + path, data=body, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                value = json.loads(raw) if raw else None
                return value, dict(response.headers.items())
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
            raise TrackerError(f"GitHub API {method} {path} failed: {exc}") from exc

    def get(self, path: str) -> Any:
        return self._request("GET", path)[0]

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", path, payload)[0]

    def paged(self, path: str) -> list[Any]:
        separator = "&" if "?" in path else "?"
        page = 1
        result: list[Any] = []
        while True:
            value = self.get(f"{path}{separator}per_page=100&page={page}")
            if not isinstance(value, list):
                raise TrackerError(f"expected list from {path}")
            result.extend(value)
            if len(value) < 100:
                return result
            page += 1

    def repo_get(self, suffix: str) -> Any:
        return self.get(f"/repos/{self.repository}{suffix}")

    def repo_paged(self, suffix: str) -> list[Any]:
        return self.paged(f"/repos/{self.repository}{suffix}")

    def repo_post(self, suffix: str, payload: dict[str, Any]) -> Any:
        return self.post(f"/repos/{self.repository}{suffix}", payload)


def utc_week(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.timezone.utc)
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def encode_snapshot(snapshot: dict[str, Any]) -> str:
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_snapshot(encoded: str) -> dict[str, Any]:
    try:
        value = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")))
    except (ValueError, json.JSONDecodeError) as exc:
        raise TrackerError("invalid tracker snapshot marker") from exc
    if not isinstance(value, dict):
        raise TrackerError("tracker snapshot must be an object")
    return value


def marker_line(week: str, snapshot: dict[str, Any]) -> str:
    return f"<!-- {MARKER} week={week} snapshot={encode_snapshot(snapshot)} -->"


def parse_marker(body: str) -> tuple[str, dict[str, Any]] | None:
    pattern = re.compile(
        rf"<!-- {re.escape(MARKER)} week=([0-9]{{4}}-W[0-9]{{2}}) snapshot=([A-Za-z0-9_=-]+) -->"
    )
    match = pattern.search(body or "")
    if not match:
        return None
    return match.group(1), decode_snapshot(match.group(2))


def effective_exact_head_approvals(reviews: list[dict[str, Any]], head: str) -> list[str]:
    latest: dict[str, str] = {}
    for review in reviews:
        user = review.get("user") or {}
        login = user.get("login")
        commit_id = review.get("commit_id")
        state = str(review.get("state") or "").upper()
        if not isinstance(login, str) or commit_id != head:
            continue
        if state in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest[login] = state
    return sorted(login for login, state in latest.items() if state == "APPROVED")


def check_summary(checks: list[dict[str, Any]]) -> dict[str, int]:
    result = {"success": 0, "failure": 0, "pending": 0, "neutral": 0}
    for check in checks:
        status = check.get("status")
        conclusion = check.get("conclusion")
        if status != "completed":
            result["pending"] += 1
        elif conclusion in {"success", "skipped"}:
            result["success"] += 1
        elif conclusion in {"neutral"}:
            result["neutral"] += 1
        else:
            result["failure"] += 1
    return result


def is_allowed_public_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in PUBLIC_HOSTS


def read_public_url(url: str) -> dict[str, Any]:
    if not is_allowed_public_url(url):
        return {"state": "NOT_ESTABLISHED", "url": url, "reason": "HOST_NOT_ALLOWED"}
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "qikvrt-weekly-publication-status/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = int(response.status)
            final_url = response.geturl()
            response.read(4096)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {
            "state": "NOT_ESTABLISHED",
            "url": url,
            "reason": type(exc).__name__,
        }
    if 200 <= status < 400 and is_allowed_public_url(final_url):
        return {
            "state": "FRESH_PUBLIC_READBACK",
            "url": url,
            "final_url": final_url,
            "http_status": status,
        }
    return {
        "state": "NOT_ESTABLISHED",
        "url": url,
        "final_url": final_url,
        "http_status": status,
    }


def evidence_urls(gh: GitHub, pr: int, head: str) -> list[tuple[str, str]]:
    files = gh.repo_paged(f"/pulls/{pr}/files")
    urls: set[tuple[str, str]] = set()
    for item in files:
        filename = item.get("filename")
        if not isinstance(filename, str) or not EVIDENCE_NAME_RE.search(filename):
            continue
        if not filename.lower().endswith((".json", ".md", ".txt", ".yml", ".yaml")):
            continue
        quoted = urllib.parse.quote(filename, safe="/")
        try:
            value = gh.repo_get(f"/contents/{quoted}?ref={urllib.parse.quote(head)}")
        except TrackerError:
            continue
        if not isinstance(value, dict):
            continue
        content = value.get("content")
        encoding = value.get("encoding")
        if not isinstance(content, str):
            continue
        try:
            raw = base64.b64decode(content) if encoding == "base64" else content.encode()
            text = raw.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            continue
        for match in PUBLIC_URL_RE.findall(text):
            urls.add((filename, match.rstrip(".,);]")))
    return sorted(urls)


def public_readback(gh: GitHub, pr: int, head: str) -> dict[str, Any]:
    candidates = evidence_urls(gh, pr, head)
    if not candidates:
        return {"state": "NOT_ESTABLISHED", "evidence_source": None, "url": None}
    failures: list[dict[str, Any]] = []
    for source, url in candidates:
        result = read_public_url(url)
        result["evidence_source"] = source
        if result["state"] == "FRESH_PUBLIC_READBACK":
            return result
        failures.append(result)
    first = failures[0]
    return {
        "state": "NOT_ESTABLISHED",
        "evidence_source": first.get("evidence_source"),
        "url": first.get("url"),
        "reason": first.get("reason") or "READBACK_FAILED",
    }


def observe_pr(gh: GitHub, number: int) -> dict[str, Any]:
    pr = gh.repo_get(f"/pulls/{number}")
    if not isinstance(pr, dict):
        raise TrackerError(f"PR #{number} payload is not an object")
    head = ((pr.get("head") or {}).get("sha"))
    if not isinstance(head, str) or len(head) != 40:
        raise TrackerError(f"PR #{number} has no exact head")
    reviews = gh.repo_paged(f"/pulls/{number}/reviews")
    checks_payload = gh.repo_get(f"/commits/{head}/check-runs?per_page=100")
    checks = checks_payload.get("check_runs", []) if isinstance(checks_payload, dict) else []
    if not isinstance(checks, list):
        checks = []
    requested = sorted(
        user.get("login")
        for user in pr.get("requested_reviewers", [])
        if isinstance(user, dict) and isinstance(user.get("login"), str)
    )
    return {
        "number": number,
        "head": head,
        "state": pr.get("state"),
        "draft": bool(pr.get("draft")),
        "merged": pr.get("merged_at") is not None,
        "requested_reviewers": requested,
        "exact_head_approvals": effective_exact_head_approvals(reviews, head),
        "checks": check_summary(checks),
        "public_readback": public_readback(gh, number, head),
    }


def changed_fields(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    if previous is None:
        return ["BASELINE_CAPTURE"]
    fields = (
        "head",
        "state",
        "draft",
        "merged",
        "requested_reviewers",
        "exact_head_approvals",
        "checks",
        "public_readback",
    )
    changes: list[str] = []
    for key in fields:
        if previous.get(key) != current.get(key):
            changes.append(f"{key}: {previous.get(key)!r} -> {current.get(key)!r}")
    return changes


def blockers(item: dict[str, Any]) -> list[str]:
    result: list[str] = []
    if item["draft"]:
        result.append("DRAFT")
    if item["state"] == "open" and not item["merged"]:
        result.append("UNMERGED")
    if item["requested_reviewers"] and not item["exact_head_approvals"]:
        result.append("NATIVE_REVIEW_PENDING")
    checks = item["checks"]
    if checks["failure"]:
        result.append(f"CHECK_FAILURES={checks['failure']}")
    if checks["pending"]:
        result.append(f"CHECKS_PENDING={checks['pending']}")
    return result


def next_step(item: dict[str, Any]) -> str:
    if item["checks"]["failure"]:
        return "Inspect and repair the first failing exact-head check."
    if item["checks"]["pending"]:
        return "Wait for the already-admitted exact-head checks to reach a terminal state; do not infer success."
    if item["draft"]:
        return "Resolve the candidate-specific draft blocker on this exact head, then use the native review path."
    if item["requested_reviewers"] and not item["exact_head_approvals"]:
        reviewers = ", ".join(item["requested_reviewers"])
        return f"Obtain a native exact-head review from the already requested reviewer(s): {reviewers}."
    if item["state"] == "open" and not item["merged"]:
        return "Use the protected native merge path only after all required exact-head gates are satisfied."
    if item["public_readback"]["state"] != "FRESH_PUBLIC_READBACK":
        return "Bind the actual public publication URL in repository evidence and perform a fresh anonymous readback."
    return "No further step is derived by this observer; EFFECT_ACK_DONE remains a separate gate."


def render_comment(
    week: str,
    previous: dict[str, Any] | None,
    snapshot: dict[str, Any],
) -> str:
    lines = [
        f"## QIK-VRT Publikationspfad — {week}",
        "",
        f"Beobachtet: `{snapshot['observed_at']}`",
        "",
        "### Frisch belegte Änderungen",
    ]
    any_change = False
    previous_prs = (previous or {}).get("prs", {})
    for number in TRACKED_PRS:
        key = str(number)
        changes = changed_fields(previous_prs.get(key), snapshot["prs"][key])
        if changes:
            any_change = True
            lines.append(f"- #{number} `{snapshot['prs'][key]['head']}`: " + "; ".join(changes))
    if not any_change:
        lines.append("- `NO_FRESH_CHANGE`")
    lines.extend(["", "### Offene Freigaben / Blocker"])
    any_blocker = False
    for number in TRACKED_PRS:
        item = snapshot["prs"][str(number)]
        bs = blockers(item)
        if bs:
            any_blocker = True
            lines.append(f"- #{number} `{item['head']}`: " + ", ".join(bs))
    if not any_blocker:
        lines.append("- keine durch diesen Beobachter belegten Repository-Blocker")
    lines.extend(["", "### Öffentliche Veröffentlichung / frischer Readback"])
    for number in TRACKED_PRS:
        item = snapshot["prs"][str(number)]
        readback = item["public_readback"]
        if readback["state"] == "FRESH_PUBLIC_READBACK":
            lines.append(
                f"- #{number}: `FRESH_PUBLIC_READBACK` — {readback['url']} "
                f"(HTTP {readback['http_status']}, Quelle `{readback['evidence_source']}`)"
            )
        else:
            lines.append(f"- #{number}: `NOT_ESTABLISHED`")
    lines.extend(["", "### Kleinster nächster Schritt"])
    ranked = [snapshot["prs"][str(number)] for number in TRACKED_PRS]
    chosen = next((item for item in ranked if item["checks"]["failure"]), None)
    chosen = chosen or next((item for item in ranked if item["checks"]["pending"]), None)
    chosen = chosen or next(
        (
            item
            for item in ranked
            if (
                not item["draft"]
                and item["requested_reviewers"]
                and not item["exact_head_approvals"]
            )
        ),
        None,
    )
    chosen = chosen or next((item for item in ranked if item["draft"]), None)
    chosen = chosen or next(
        (item for item in ranked if item["state"] == "open" and not item["merged"]),
        None,
    )
    chosen = chosen or next(
        (
            item
            for item in ranked
            if item["public_readback"]["state"] != "FRESH_PUBLIC_READBACK"
        ),
        ranked[0],
    )
    lines.append(f"- #{chosen['number']} `{chosen['head']}`: {next_step(chosen)}")
    lines.extend(
        [
            "",
            "> `REPOSITORY_SUCCESS != EFFECT_ACK_DONE`  ",
            "> `WORKFLOW_GREEN != PUBLICATION`  ",
            "> `PREDECESSOR_EVIDENCE_TRANSFER = false`",
            "",
            marker_line(week, snapshot),
        ]
    )
    return "\n".join(lines)


def previous_snapshot(
    comments: list[dict[str, Any]], current_week: str
) -> tuple[bool, dict[str, Any] | None]:
    previous: dict[str, Any] | None = None
    already_emitted = False
    for comment in comments:
        body = comment.get("body")
        if not isinstance(body, str):
            continue
        parsed = parse_marker(body)
        if parsed is None:
            continue
        week, snapshot = parsed
        if week == current_week:
            already_emitted = True
        previous = snapshot
    return already_emitted, previous


def run(repository: str, issue: int, token: str) -> dict[str, Any]:
    gh = GitHub(repository, token)
    week = utc_week()
    comments = gh.repo_paged(f"/issues/{issue}/comments")
    already_emitted, previous = previous_snapshot(comments, week)
    if already_emitted:
        return {"state": "NOOP", "week": week, "reason": "WEEK_ALREADY_EMITTED"}

    observed_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    prs = {str(number): observe_pr(gh, number) for number in TRACKED_PRS}
    snapshot = {
        "schema": "qikvrt-weekly-publication-status/1",
        "week": week,
        "observed_at": observed_at,
        "repository": repository,
        "tracking_issue": issue,
        "prs": prs,
        "completion_claims": {
            "repository_success_is_effect_ack_done": False,
            "effect_ack_done": False,
        },
    }
    body = render_comment(week, previous, snapshot)
    created = gh.repo_post(f"/issues/{issue}/comments", {"body": body})
    comment_id = created.get("id") if isinstance(created, dict) else None
    if not isinstance(comment_id, int):
        raise TrackerError("created comment has no numeric id")
    readback = gh.repo_get(f"/issues/comments/{comment_id}")
    if not isinstance(readback, dict) or readback.get("body") != body:
        raise TrackerError("tracking comment readback mismatch")
    return {
        "state": "COMMENT_PERSISTED_AND_READ_BACK",
        "week": week,
        "comment_id": comment_id,
        "snapshot": snapshot,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--issue", type=int, default=DEFAULT_ISSUE)
    args = parser.parse_args()
    try:
        result = run(args.repository, args.issue, os.environ.get("GITHUB_TOKEN", ""))
    except TrackerError as exc:
        print(json.dumps({"state": "BLOCK", "detail": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
