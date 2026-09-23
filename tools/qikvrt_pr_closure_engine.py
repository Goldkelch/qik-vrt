#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Repository-native pull-request closure engine.

The engine turns observed open PR work into one bounded repository mutation per
run. It never fabricates review, never bypasses required native rules, and never
crosses an external-effect boundary. Authority merges use GitHub's native PR
merge endpoint only after the configured strict ruleset, exact-head gates and an
exact-head independent approval have all been reobserved. Mirror promotion uses
an unforced fast-forward ref update, which acts as an exact-base CAS: if main
moves to a non-ancestor before the write, GitHub rejects the update.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

AUTO_READY_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
TECHNICAL_REVIEW_CONTEXT = "QIKVRT requested review execution"


class ClosureBlock(ValueError):
    """Raised for invalid policy or repository observations."""


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ClosureBlock(f"{label} is not a lowercase Git SHA-1")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ClosureBlock(f"{label} must be a non-empty string")
    return value


def validate_policy(policy: Mapping[str, Any], repository: str) -> dict[str, Any]:
    if policy.get("schema") != "qikvrt_autonomous_pr_closure_policy_v1":
        raise ClosureBlock("closure policy schema mismatch")
    if policy.get("status") != "ACTIVE":
        raise ClosureBlock("closure policy is not active")
    repos = policy.get("repositories")
    if not isinstance(repos, Mapping) or repository not in repos:
        raise ClosureBlock("repository is not authorized by closure policy")
    repo_policy = repos[repository]
    if not isinstance(repo_policy, Mapping):
        raise ClosureBlock("repository policy must be an object")
    reviewer = _string(policy.get("required_independent_reviewer"), "required_independent_reviewer")
    max_scan = policy.get("max_scan_per_run")
    max_mutations = policy.get("max_mutations_per_run")
    if isinstance(max_scan, bool) or not isinstance(max_scan, int) or not 1 <= max_scan <= 32:
        raise ClosureBlock("max_scan_per_run must be in [1, 32]")
    if max_mutations != 1:
        raise ClosureBlock("max_mutations_per_run must be exactly 1")
    check = policy.get("required_check")
    if not isinstance(check, Mapping):
        raise ClosureBlock("required_check must be an object")
    _string(check.get("name"), "required_check.name")
    app_id = check.get("integration_id")
    if isinstance(app_id, bool) or not isinstance(app_id, int) or app_id < 1:
        raise ClosureBlock("required_check.integration_id must be positive")
    mode = repo_policy.get("promotion_mode")
    if mode not in {"NATIVE_PR_MERGE", "FAST_FORWARD_CAS"}:
        raise ClosureBlock("unsupported promotion_mode")
    if repo_policy.get("base_branch") != "main":
        raise ClosureBlock("only main-base closure is authorized")
    if repo_policy.get("role_local_head_required") is not True:
        raise ClosureBlock("role-local head requirement may not be disabled")
    return {
        "reviewer": reviewer,
        "max_scan": max_scan,
        "required_check": dict(check),
        "repo": dict(repo_policy),
    }


def exact_head_approval(reviews: Iterable[Mapping[str, Any]], reviewer: str, head_sha: str, author: str) -> bool:
    latest: Mapping[str, Any] | None = None
    for review in reviews:
        if not isinstance(review, Mapping):
            continue
        user = review.get("user")
        login = user.get("login") if isinstance(user, Mapping) else None
        if login != reviewer or login == author or review.get("commit_id") != head_sha:
            continue
        if latest is None or (review.get("submitted_at") or "") > (latest.get("submitted_at") or ""):
            latest = review
    return bool(latest and latest.get("state") == "APPROVED")


def required_check_green(check_runs: Iterable[Mapping[str, Any]], name: str, integration_id: int) -> bool:
    matches = []
    for run in check_runs:
        if not isinstance(run, Mapping) or run.get("name") != name:
            continue
        app = run.get("app")
        app_id = app.get("id") if isinstance(app, Mapping) else None
        if app_id == integration_id:
            matches.append(run)
    if not matches:
        return False
    latest = max(matches, key=lambda x: (x.get("completed_at") or x.get("started_at") or "", x.get("id") or 0))
    return latest.get("status") == "completed" and latest.get("conclusion") == "success"


def technical_review_green(statuses: Iterable[Mapping[str, Any]], context: str = TECHNICAL_REVIEW_CONTEXT) -> bool:
    matches = [s for s in statuses if isinstance(s, Mapping) and s.get("context") == context]
    if not matches:
        return False
    latest = max(matches, key=lambda x: (x.get("updated_at") or x.get("created_at") or "", x.get("id") or 0))
    return latest.get("state") == "success"


def classify_pr(pr: Mapping[str, Any], observed: Mapping[str, Any], config: Mapping[str, Any], repository: str) -> dict[str, Any]:
    number = pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ClosureBlock("pull request number is invalid")
    if pr.get("state") != "open":
        return {"pr": number, "action": "SKIP_CLOSED"}
    base = pr.get("base")
    head = pr.get("head")
    if not isinstance(base, Mapping) or not isinstance(head, Mapping):
        raise ClosureBlock("pull request lacks Git bindings")
    if base.get("ref") != config["repo"]["base_branch"]:
        return {"pr": number, "action": "BLOCK_UNSUPPORTED_BASE"}
    head_repo = head.get("repo")
    if not isinstance(head_repo, Mapping) or head_repo.get("full_name") != repository:
        return {"pr": number, "action": "BLOCK_NON_ROLE_LOCAL_HEAD"}

    head_sha = _sha(head.get("sha"), "pull request head")
    current_main = _sha(observed.get("current_main_sha"), "current main")
    compare_status = observed.get("compare_status")
    changed_files = pr.get("changed_files")
    if changed_files == 0 or compare_status == "identical":
        return {"pr": number, "action": "CLOSE_ALREADY_CONTAINED", "head_sha": head_sha}

    if pr.get("draft") is True:
        author = ((pr.get("user") or {}).get("login") if isinstance(pr.get("user"), Mapping) else None)
        body = pr.get("body") or ""
        head_ref = head.get("ref") or ""
        if (
            author == "github-actions[bot]"
            and isinstance(body, str)
            and AUTO_READY_MARKER in body
            and isinstance(head_ref, str)
            and head_ref.startswith("automation/self-heal-")
        ):
            return {"pr": number, "action": "MARK_READY", "head_sha": head_sha, "node_id": pr.get("node_id")}
        return {"pr": number, "action": "BLOCK_DRAFT_REQUIRES_OWNER"}

    if compare_status != "ahead":
        mergeable_state = pr.get("mergeable_state")
        if pr.get("mergeable") is False or mergeable_state == "dirty":
            return {"pr": number, "action": "BLOCK_REPAIR_REQUIRED", "reason": "MERGE_CONFLICT"}
        return {"pr": number, "action": "UPDATE_BRANCH", "head_sha": head_sha}

    check = config["required_check"]
    if not required_check_green(observed.get("check_runs", []), check["name"], check["integration_id"]):
        return {"pr": number, "action": "WAIT_REQUIRED_CHECK", "head_sha": head_sha}

    author = ((pr.get("user") or {}).get("login") if isinstance(pr.get("user"), Mapping) else "") or ""
    reviewer = config["reviewer"]
    reviews = observed.get("reviews", [])
    approved = exact_head_approval(reviews, reviewer, head_sha, author)
    requested = set(observed.get("requested_reviewers", []))
    if not approved:
        if reviewer not in requested:
            return {"pr": number, "action": "REQUEST_REVIEW", "head_sha": head_sha, "reviewer": reviewer}
        return {"pr": number, "action": "WAIT_INDEPENDENT_REVIEW", "head_sha": head_sha}

    if not technical_review_green(observed.get("statuses", [])):
        return {"pr": number, "action": "WAIT_TECHNICAL_REVIEW", "head_sha": head_sha}

    if base.get("sha") != current_main:
        return {"pr": number, "action": "REOBSERVE_BASE_DRIFT", "head_sha": head_sha}

    return {
        "pr": number,
        "action": "MERGE",
        "head_sha": head_sha,
        "main_sha": current_main,
        "promotion_mode": config["repo"]["promotion_mode"],
    }


@dataclass
class GitHubAPI:
    repository: str
    token: str
    api_url: str = "https://api.github.com"

    def request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Any:
        url = path if path.startswith("http") else self.api_url.rstrip("/") + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ClosureBlock(f"GitHub API {method} {path} failed: HTTP {exc.code}: {body[:500]}") from exc
        return json.loads(raw.decode("utf-8")) if raw else None

    def repo_path(self, suffix: str) -> str:
        return f"/repos/{self.repository}{suffix}"

    def open_prs(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for page in range(1, 6):
            batch = self.request("GET", self.repo_path(f"/pulls?state=open&per_page=100&page={page}"))
            if not isinstance(batch, list):
                raise ClosureBlock("open pull-request response is not a list")
            rows.extend(batch)
            if len(batch) < 100:
                break
        rows.sort(key=lambda pr: (pr.get("created_at") or "", pr.get("number") or 0))
        return rows

    def current_main(self) -> str:
        value = self.request("GET", self.repo_path("/branches/main"))
        return _sha(((value or {}).get("commit") or {}).get("sha"), "current main")

    def inspect(self, pr: Mapping[str, Any], current_main: str) -> dict[str, Any]:
        number = pr["number"]
        head_sha = pr["head"]["sha"]
        compare = self.request("GET", self.repo_path(f"/compare/{current_main}...{head_sha}"))
        check_runs = self.request("GET", self.repo_path(f"/commits/{head_sha}/check-runs?per_page=100"))
        statuses = self.request("GET", self.repo_path(f"/commits/{head_sha}/status"))
        reviews = self.request("GET", self.repo_path(f"/pulls/{number}/reviews?per_page=100"))
        requested = self.request("GET", self.repo_path(f"/pulls/{number}/requested_reviewers"))
        return {
            "current_main_sha": current_main,
            "compare_status": (compare or {}).get("status"),
            "check_runs": (check_runs or {}).get("check_runs", []),
            "statuses": (statuses or {}).get("statuses", []),
            "reviews": reviews if isinstance(reviews, list) else [],
            "requested_reviewers": [u.get("login") for u in (requested or {}).get("users", []) if isinstance(u, Mapping)],
        }

    def assert_authority_ruleset(self, config: Mapping[str, Any]) -> None:
        ruleset_id = config["repo"].get("ruleset_id")
        if not isinstance(ruleset_id, int):
            raise ClosureBlock("authority promotion requires ruleset_id")
        ruleset = self.request("GET", self.repo_path(f"/rulesets/{ruleset_id}"))
        if not isinstance(ruleset, Mapping) or ruleset.get("enforcement") != "active":
            raise ClosureBlock("authority ruleset is not active")
        strict = False
        required_check = config["required_check"]
        has_pull_request_rule = False
        for rule in ruleset.get("rules", []):
            if not isinstance(rule, Mapping):
                continue
            if rule.get("type") == "pull_request":
                has_pull_request_rule = True
            if rule.get("type") == "required_status_checks":
                params = rule.get("parameters") or {}
                if params.get("strict_required_status_checks_policy") is True:
                    for check in params.get("required_status_checks", []):
                        if (
                            isinstance(check, Mapping)
                            and check.get("context") == required_check["name"]
                            and check.get("integration_id") == required_check["integration_id"]
                        ):
                            strict = True
        if not has_pull_request_rule or not strict:
            raise ClosureBlock("authority ruleset lacks strict required PR/check protection")

    def apply(self, action: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
        number = action["pr"]
        kind = action["action"]
        if kind == "CLOSE_ALREADY_CONTAINED":
            marker = "<!-- qikvrt-pr-closure-engine:v1 disposition=ALREADY_CONTAINED -->"
            self.request("POST", self.repo_path(f"/issues/{number}/comments"), {"body": marker + "\n\nCurrent main already contains the PR diff. Closing without merge; no predecessor evidence is transferred."})
            self.request("PATCH", self.repo_path(f"/pulls/{number}"), {"state": "closed"})
        elif kind == "MARK_READY":
            node_id = _string(action.get("node_id"), "pull request node_id")
            query = "mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id}){pullRequest{number isDraft}}}"
            self.request("POST", "/graphql", {"query": query, "variables": {"id": node_id}})
        elif kind == "UPDATE_BRANCH":
            self.request("PUT", self.repo_path(f"/pulls/{number}/update-branch"), {"expected_head_sha": action["head_sha"]})
        elif kind == "REQUEST_REVIEW":
            self.request("POST", self.repo_path(f"/pulls/{number}/requested_reviewers"), {"reviewers": [action["reviewer"]]})
        elif kind == "MERGE":
            pr = self.request("GET", self.repo_path(f"/pulls/{number}"))
            current_main = self.current_main()
            observed = self.inspect(pr, current_main)
            fresh = classify_pr(pr, observed, config, self.repository)
            if fresh.get("action") != "MERGE" or fresh.get("head_sha") != action.get("head_sha"):
                raise ClosureBlock(f"final closure fence changed: {fresh}")
            mode = fresh["promotion_mode"]
            if mode == "NATIVE_PR_MERGE":
                self.assert_authority_ruleset(config)
                result = self.request("PUT", self.repo_path(f"/pulls/{number}/merge"), {"merge_method": "merge", "sha": fresh["head_sha"]})
                if not isinstance(result, Mapping) or result.get("merged") is not True:
                    raise ClosureBlock(f"native merge was not confirmed: {result}")
            elif mode == "FAST_FORWARD_CAS":
                self.request("PATCH", self.repo_path("/git/refs/heads/main"), {"sha": fresh["head_sha"], "force": False})
            else:
                raise ClosureBlock("unsupported promotion mode at apply fence")
        else:
            raise ClosureBlock(f"action {kind!r} is not mutable")
        return {"applied": True, "action": dict(action)}


def scan_window(
    prs: Sequence[Mapping[str, Any]],
    max_scan: int,
    run_number: Any,
) -> tuple[list[Mapping[str, Any]], int]:
    """Return a deterministic bounded rotating window over the open PR queue."""
    if not prs:
        return [], 0
    try:
        serial = int(run_number or 1)
    except (TypeError, ValueError):
        serial = 1
    serial = max(serial, 1)
    offset = ((serial - 1) * max_scan) % len(prs)
    ordered = list(prs[offset:]) + list(prs[:offset])
    return ordered[:max_scan], offset


def execute(api: GitHubAPI, policy: Mapping[str, Any], *, apply: bool) -> dict[str, Any]:
    config = validate_policy(policy, api.repository)
    current_main = api.current_main()
    prs = api.open_prs()
    window, scan_offset = scan_window(
        prs,
        config["max_scan"],
        os.environ.get("GITHUB_RUN_NUMBER"),
    )
    receipt: dict[str, Any] = {
        "schema": "qikvrt_pr_closure_run_receipt_v1",
        "repository": api.repository,
        "current_main_sha": current_main,
        "open_pr_count": len(prs),
        "scan_offset": scan_offset,
        "scanned": [],
        "selected_action": None,
        "mutation_applied": False,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }
    for summary in window:
        pr = api.request("GET", api.repo_path(f"/pulls/{summary['number']}"))
        if not isinstance(pr, Mapping):
            raise ClosureBlock("pull-request detail response is not an object")
        observed = api.inspect(pr, current_main)
        decision = classify_pr(pr, observed, config, api.repository)
        receipt["scanned"].append(decision)
        if decision["action"] in {"CLOSE_ALREADY_CONTAINED", "MARK_READY", "UPDATE_BRANCH", "REQUEST_REVIEW", "MERGE"}:
            receipt["selected_action"] = decision
            if apply:
                api.apply(decision, config)
                receipt["mutation_applied"] = True
            break
    return receipt


def _load_json(path: str) -> Any:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate-policy", "run"))
    parser.add_argument("--policy", default="state/autonomy/AUTONOMOUS_PR_CLOSURE_POLICY_V1.json")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN", ""))
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        policy = _load_json(args.policy)
        if args.command == "validate-policy":
            if args.repository:
                result = validate_policy(policy, args.repository)
            else:
                for repository in policy.get("repositories", {}):
                    validate_policy(policy, repository)
                result = {"state": "VALID"}
        else:
            repository = _string(args.repository, "repository")
            token = _string(args.token, "token")
            result = execute(GitHubAPI(repository, token, args.api_url), policy, apply=args.apply)
    except (OSError, json.JSONDecodeError, ClosureBlock) as exc:
        result = {
            "schema": "qikvrt_pr_closure_run_receipt_v1",
            "state": "BLOCK",
            "first_blocker": str(exc),
            "mutation_applied": False,
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        }
        code = 2
    else:
        code = 0
    rendered = json.dumps(result, sort_keys=True, indent=2)
    print(rendered)
    if args.output:
        pathlib.Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
