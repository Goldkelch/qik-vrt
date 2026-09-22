# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded execution bridge to existing trusted-main QIK-VRT carriers.

A completed bridge iteration is not repository or product completion. Native
carriers retain their own allowlists, approval requirements and writer locks.
This module never checks out PR code, mutates refs, cancels runs or retries a
terminal exact-head carrier. It does not implement a new general-purpose solver.
"""
from __future__ import annotations

import datetime as dt
import json
import hashlib
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

CARRIERS = (
    "qikvrt_reflexive_repository_watchdog.yml",
    "qikvrt_autonomous_self_heal.yml",
    "qikvrt_autonomous_pr_head_continuation.yml",
    "qikvrt_autonomous_pr_continuation.yml",
)
READ_ONLY = frozenset({CARRIERS[0]})
# Reused from the native executor/mesh contract, augmented by the existing
# requested-review executor's materializer writer classification.
WRITERS = frozenset({
    "QIK-VRT autonomous bounded self-heal",
    "QIK-VRT autonomous draft-PR continuation",
    "QIK-VRT expected-head promotion executor",
    "QIKVRT requested review executor",
    "QIKVRT repository evidence materialization",
    "QIKVRT Cloud Transputer integrity objects v1",
})
WRITER_PATHS = frozenset({
    ".github/workflows/qikvrt_autonomous_self_heal.yml",
    ".github/workflows/qikvrt_autonomous_pr_continuation.yml",
    ".github/workflows/qikvrt_expected_head_promotion.yml",
    ".github/workflows/qikvrt_requested_review_executor.yml",
    ".github/workflows/qikvrt_batch04_integrity.yml",
    ".github/workflows/qikvrt_cloud_transputer_integrity_objects_v1.yml",
})
ACTIVE = frozenset({"queued", "in_progress", "waiting", "pending", "requested"})
OPT_IN = "<!-- qikvrt-autonomous-self-heal:enabled -->"
SHA = re.compile(r"^[0-9a-f]{40}$")


class BoundaryError(RuntimeError):
    """Execution or provenance is not established; never coerce this to DONE."""


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def carrier_path(name):
    if name not in CARRIERS:
        raise BoundaryError("NON_ALLOWLISTED_CARRIER")
    return ".github/workflows/" + name


def bind_subject(repository, head, tree):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise BoundaryError("INVALID_REPOSITORY")
    if not SHA.fullmatch(head or "") or not SHA.fullmatch(tree or ""):
        raise BoundaryError("INVALID_EXACT_SUBJECT")
    return {"repository": repository, "head": head, "tree": tree}


def classify_run(run, jobs, workflow, subject):
    if (run.get("head_sha") != subject["head"]
            or run.get("head_branch") != "main"
            or run.get("path", "").split("@", 1)[0] != carrier_path(workflow)):
        raise BoundaryError("CHILD_SUBJECT_OR_WORKFLOW_MISMATCH")
    if run.get("status") in ACTIVE:
        return "ADMITTED_EXECUTION" if jobs else "ADMISSION_NOT_OBSERVED"
    if run.get("status") != "completed":
        raise BoundaryError("UNKNOWN_RUN_STATUS")
    if not jobs:
        return "TERMINAL_WITHOUT_ADMITTED_JOBS"
    if run.get("conclusion") != "success":
        return "NATIVE_CARRIER_FAILURE"
    if not any(j.get("conclusion") == "success" for j in jobs):
        return "NO_SUCCESSFUL_JOB"
    return "NATIVE_CARRIER_COMPLETED_NOT_EFFECT_ACK"


def eligible_carriers(prs, repository):
    same_repo = [pr for pr in prs
                 if ((pr.get("head") or {}).get("repo") or {}).get("full_name") == repository]
    selected = [CARRIERS[0], CARRIERS[1]]
    if same_repo:
        selected.append(CARRIERS[2])
    if any(pr.get("draft") is True and OPT_IN in (pr.get("body") or "")
           for pr in same_repo):
        selected.append(CARRIERS[3])
    return selected


def choose_carrier(eligible, runs, head, active_runs):
    """Reuse active/terminal executions; no wake-up retry of the same subject."""
    writer_active = any(
        run.get("status") in ACTIVE
        and (run.get("name") in WRITERS
             or run.get("path", "").split("@", 1)[0] in WRITER_PATHS)
        for run in active_runs
    )
    existing = []
    for workflow in eligible:
        matching = [run for run in runs if run.get("head_sha") == head
                    and run.get("head_branch") == "main"
                    and run.get("path", "").split("@", 1)[0] == carrier_path(workflow)]
        active = [run for run in matching if run.get("status") in ACTIVE]
        if active:
            existing.append((workflow, max(active, key=lambda run: run["id"])))
            continue
        if matching:  # A terminal failure is a new cause, not rerun permission.
            continue
        if workflow in READ_ONLY or not writer_active:
            return workflow, None, "DISPATCH"
    if existing:
        workflow, run = existing[0]
        return workflow, run, "OBSERVE_EXISTING"
    return None, None, "NO_NEW_AUTHORIZED_CARRIER"


class GitHubAPI:
    def __init__(self, repository, token):
        bind_subject(repository, "0" * 40, "0" * 40)
        if not token:
            raise BoundaryError("AUTHENTICATED_EXECUTION_TOKEN_MISSING")
        self.repository = repository
        self.token = token

    def __call__(self, path, body=None):
        if (not path.startswith(f"repos/{self.repository}/")
                or ".." in path or "%" in path or "#" in path):
            raise BoundaryError("OUT_OF_SCOPE_API_PATH")
        if body is not None:
            allowed = {f"repos/{self.repository}/actions/workflows/{name}/dispatches"
                       for name in CARRIERS}
            if path not in allowed or body != {"ref": "main", "return_run_details": True}:
                raise BoundaryError("NON_ALLOWLISTED_DISPATCH")
        request = urllib.request.Request(
            "https://api.github.com/" + path,
            data=None if body is None else json.dumps(body).encode(),
            method="GET" if body is None else "POST",
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json",
                     "User-Agent": "qikvrt-universal-roundtrip-controller",
                     "X-GitHub-Api-Version": "2026-03-10"},
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            # Do not echo authentication material or an untrusted response body.
            raise BoundaryError(f"API_HTTP_{error.code}: {path}") from None


def pages(api, prefix, key=None):
    result = []
    for page in range(1, 101):
        separator = "&" if "?" in prefix else "?"
        value = api(f"{prefix}{separator}per_page=100&page={page}")
        items = value.get(key) if key and isinstance(value, dict) else value
        if not isinstance(items, list):
            raise BoundaryError("INCOMPLETE_API_COLLECTION")
        result.extend(items)
        if len(items) < 100:
            if key and value.get("total_count", len(result)) > len(result):
                raise BoundaryError("TRUNCATED_API_COLLECTION")
            return result
    raise BoundaryError("PAGINATION_BOUND_EXCEEDED")


def execute(api, repository, receipt_path, budget_seconds=480,
            sleep=time.sleep, clock=time.monotonic):
    prefix = f"repos/{repository}/"
    deadline = clock() + budget_seconds
    receipt = {"schema": "qikvrt_universal_roundtrip_execution_v1",
               "started_at": timestamp(), "repository": repository,
               "state": "EFFECT_ACK_CONTINUE", "effect_ack_done": False,
               "predecessor_evidence_transfer": False,
               "controller_source_head": os.environ.get("QIKVRT_CONTROLLER_HEAD"),
               "controller_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "observations": [], "child_executions": [], "blockers": []}

    def persist():
        receipt["observed_at"] = timestamp()
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = receipt_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        temporary.replace(receipt_path)

    try:
        while clock() < deadline:
            head = api(prefix + "git/ref/heads/main")["object"]["sha"]
            tree = api(prefix + "git/commits/" + head)["tree"]["sha"]
            subject = bind_subject(repository, head, tree)
            prs = pages(api, prefix + "pulls?state=open")
            issues = [item for item in pages(api, prefix + "issues?state=open")
                      if "pull_request" not in item]
            branches = pages(api, prefix + "branches")
            workflows = pages(api, prefix + "actions/workflows", "workflows")
            runs = pages(api, prefix + "actions/runs?head_sha=" + head, "workflow_runs")
            active_runs = []
            for state in sorted(ACTIVE):
                active_runs.extend(pages(api, prefix + "actions/runs?status=" + state,
                                         "workflow_runs"))
            receipt["subject"] = subject
            receipt["workflow_inventory"] = [
                {key: workflow.get(key) for key in ("id", "name", "path", "state")}
                for workflow in workflows]
            receipt["observations"].append({
                "at": timestamp(), "subject": subject,
                "pull_requests": [{"number": pr["number"],
                                   "head": pr["head"]["sha"]} for pr in prs],
                "issues": [item["number"] for item in issues],
                "branches": [{"name": branch["name"],
                              "head": branch["commit"]["sha"]} for branch in branches],
            })
            eligible = eligible_carriers(prs, repository)
            known_paths = {workflow.get("path") for workflow in workflows
                           if workflow.get("state") == "active"}
            for workflow in eligible:
                if carrier_path(workflow) not in known_paths:
                    blocker = {"cause": "NATIVE_CARRIER_NOT_ACTIVE", "workflow": workflow}
                    if blocker not in receipt["blockers"]:
                        receipt["blockers"].append(blocker)
            eligible = [w for w in eligible if carrier_path(w) in known_paths]
            workflow, run, action = choose_carrier(eligible, runs, head, active_runs)
            if workflow is None:
                receipt["continuation"] = action
                # An empty object inventory never substitutes for an effect verifier.
                receipt["blockers"].append({"cause": "SCOPED_EFFECT_READBACK_NOT_ESTABLISHED"})
                persist()
                return receipt
            if api(prefix + "git/ref/heads/main")["object"]["sha"] != head:
                persist()
                continue
            if action == "DISPATCH":
                persist()  # Preserve the precondition before the effectful request.
                response = api(prefix + "actions/workflows/" + workflow + "/dispatches",
                               {"ref": "main", "return_run_details": True})
                if not isinstance(response, dict) or type(response.get("workflow_run_id")) is not int:
                    raise BoundaryError("DISPATCH_RUN_ID_NOT_RETURNED_NO_TIME_BASED_INFERENCE")
                run_id = response["workflow_run_id"]
            else:
                run_id = run["id"]
            execution = next((item for item in receipt["child_executions"]
                              if item["run_id"] == run_id), None)
            if execution is None:
                execution = {"workflow": workflow, "run_id": run_id, "subject": subject,
                             "action": action, "effect_ack_done": False}
                receipt["child_executions"].append(execution)
            persist()
            run = api(prefix + f"actions/runs/{run_id}")
            jobs = pages(api, prefix + f"actions/runs/{run_id}/jobs", "jobs")
            execution["classification"] = classify_run(run, jobs, workflow, subject)
            execution["conclusion"] = run.get("conclusion")
            execution["admitted_jobs"] = len(jobs)
            execution["readback_at"] = timestamp()
            persist()
            if run.get("status") == "completed":
                if execution["classification"] != "NATIVE_CARRIER_COMPLETED_NOT_EFFECT_ACK":
                    receipt["blockers"].append({"cause": execution["classification"],
                                                "run_id": run_id})
            else:
                sleep(min(15, max(0, deadline - clock())))
            # Reconcile after one readback: an active watchdog must not starve an
            # independently eligible repair, nor a writer starve observation.
        receipt["continuation"] = "RESUME_BOUND_EXECUTIONS_ON_EVENT_OR_SCHEDULE"
        persist()
        return receipt
    except Exception as error:
        receipt["state"] = "EFFECT_ACK_BLOCK"
        receipt["blockers"].append({"cause": str(error)[:500]})
        persist()
        raise


def main():
    repository = os.environ["GITHUB_REPOSITORY"]
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise BoundaryError("TRUSTED_MAIN_ONLY")
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        raise BoundaryError("PULL_REQUEST_IS_VALIDATION_ONLY")
    contract = json.loads(Path("state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json").read_text())
    declared = set(contract["dispatch_policy"]["writer_workflow_names"])
    if not declared <= WRITERS:
        raise BoundaryError("NATIVE_WRITER_CONTRACT_CHANGED")
    output = Path(os.environ["QIKVRT_ROUNDTRIP_RECEIPT"])
    result = execute(GitHubAPI(repository, os.environ.get("GH_TOKEN", "")),
                     repository, output)
    print(json.dumps({key: result.get(key) for key in
                      ("state", "effect_ack_done", "subject", "continuation", "blockers")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
