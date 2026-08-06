#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Progressing V2 operator with persistent work-unit completion state."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import urllib.request
import zipfile

import qikvrt_autonomous_ontology_closure as v1

QUEUE = Path("state/ontology-autonomy/QUEUE_V2.json")
STATUS = Path("state/ontology-autonomy/STATUS_V2.json")
AUDIO_REVIEW = Path("state/ontology-autonomy/A08_A09_ACOUSTIC_REVIEW_REQUEST.json")
UNIFIED_WORK = Path("state/work_units/UNIFIED_ONTOLOGY_KERNEL_PROGRAM_V1.json")
RECEIPT_NAME = "QCE_KERNEL_RECEIPT.json"
SUCCESS_STATES = {
    "SUCCESSOR_CREATED",
    "SUCCESSOR_ALREADY_EXISTS",
    "NOOP_ALREADY_SATISFIED",
    "RECEIPT_ALREADY_PRESENT",
    "RECEIPT_SUCCESSOR_CREATED",
    "AUDIO_REVIEW_REQUEST_CREATED",
    "AUDIO_REVIEW_REQUEST_ALREADY_EXISTS",
    "UNIFIED_WORK_UNITS_CREATED",
    "UNIFIED_WORK_UNITS_ALREADY_EXIST",
}


def load_contract(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    policy = v1.load_json(root / v1.POLICY)
    queue = v1.load_json(root / QUEUE)
    status = v1.load_json(root / STATUS)
    if policy.get("schema") != "qikvrt_autonomous_ontology_closure_policy_v1":
        raise v1.OperatorError("wrong policy schema")
    if queue.get("schema") != "qikvrt_autonomous_ontology_closure_queue_v2":
        raise v1.OperatorError("wrong V2 queue schema")
    if status.get("schema") != "qikvrt_autonomous_ontology_closure_status_v2":
        raise v1.OperatorError("wrong V2 status schema")
    claims = {"EFFECT_ACK_DONE": False, "FINAL_PASS": False, "PASS": False}
    if policy.get("release_claims") != claims or queue.get("release_claims") != claims or status.get("release_claims") != claims:
        raise v1.OperatorError("false or divergent release claim projection")
    units = queue.get("work_units")
    if not isinstance(units, list) or not units:
        raise v1.OperatorError("V2 queue is empty")
    seen: set[str] = set()
    orders: list[int] = []
    non_auto = {"EXTERNAL_SCIENCE", "INDEPENDENT_REPLICATION", "IRREVERSIBLE_EXTERNAL_EFFECT"}
    for unit in units:
        uid = unit.get("id")
        if not isinstance(uid, str) or not uid or uid in seen:
            raise v1.OperatorError("work-unit IDs are not unique")
        seen.add(uid)
        order = unit.get("order")
        if not isinstance(order, int):
            raise v1.OperatorError(f"{uid}: invalid order")
        orders.append(order)
        if unit.get("action_class") in non_auto and unit.get("automatic") is not False:
            raise v1.OperatorError(f"{uid}: external truth gate marked automatic")
        if unit.get("automatic") is True and not unit.get("handler"):
            raise v1.OperatorError(f"{uid}: automatic unit lacks handler")
    if orders != sorted(orders) or len(orders) != len(set(orders)):
        raise v1.OperatorError("work-unit order is not strictly increasing")
    completed = status.get("completed_work_units")
    if not isinstance(completed, list) or len(completed) != len(set(completed)) or not set(completed).issubset(seen):
        raise v1.OperatorError("invalid completed-work-unit projection")
    if not isinstance(status.get("predecessor_results"), dict):
        raise v1.OperatorError("predecessor_results is not an object")
    return policy, queue, status


def api_value(token: str, method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    status, body = v1.api(token, method, url, payload)
    if status < 200 or status >= 300:
        raise v1.OperatorError(f"GitHub API {method} {url} returned {status}: {body[:1000]!r}")
    return json.loads(body.decode("utf-8")) if body else None


def open_prs(token: str, repository: str) -> list[dict[str, Any]]:
    value = api_value(token, "GET", f"https://api.github.com/repos/{repository}/pulls?state=open&per_page=100")
    if not isinstance(value, list):
        raise v1.OperatorError("open PR response is not a list")
    return [item for item in value if isinstance(item, dict)]


def find_open_pr(token: str, repository: str, branch_prefix: str) -> dict[str, Any] | None:
    for pr in open_prs(token, repository):
        if str(pr.get("head", {}).get("ref", "")).startswith(branch_prefix):
            return pr
    return None


def exact_head_gates(token: str, repository: str, head_sha: str) -> dict[str, Any]:
    value = api_value(
        token,
        "GET",
        f"https://api.github.com/repos/{repository}/actions/runs?head_sha={head_sha}&event=pull_request&per_page=100",
    )
    runs = value.get("workflow_runs", []) if isinstance(value, dict) else []
    required = {
        "QIK-VRT QCE candidate verification",
        "QIKVRT CI",
        "QIKVRT Collective Proposal Review",
        "QIK-VRT global claim completion",
        "QIKVRT repository evidence materialization",
    }
    observed: dict[str, list[dict[str, Any]]] = {name: [] for name in required}
    for run in runs:
        name = run.get("name")
        if name in observed:
            observed[name].append(
                {
                    "id": run.get("id"),
                    "status": run.get("status"),
                    "conclusion": run.get("conclusion"),
                    "run_attempt": run.get("run_attempt"),
                }
            )
    latest: dict[str, dict[str, Any] | None] = {}
    for name, entries in observed.items():
        latest[name] = max(entries, key=lambda x: int(x.get("id") or 0)) if entries else None
    ready = all(
        item is not None
        and item.get("status") == "completed"
        and item.get("conclusion") in {"success", "skipped"}
        for item in latest.values()
    )
    return {"ready": ready, "required": latest}


def create_commit_pr(
    token: str,
    repository: str,
    parent_sha: str,
    files: dict[str, bytes],
    branch: str,
    title: str,
    body: str,
    commit_message: str,
) -> dict[str, Any]:
    existing = find_open_pr(token, repository, branch)
    if existing is not None and existing.get("head", {}).get("ref") == branch:
        return {
            "state": "SUCCESSOR_ALREADY_EXISTS",
            "successor_pr": existing["number"],
            "successor_branch": branch,
            "successor_head": existing["head"]["sha"],
        }
    base_url = f"https://api.github.com/repos/{repository}"
    parent = v1.api_json(token, "GET", f"{base_url}/git/commits/{parent_sha}")
    entries: list[dict[str, Any]] = []
    for path, raw in sorted(files.items()):
        blob = v1.api_json(
            token,
            "POST",
            f"{base_url}/git/blobs",
            {"content": base64.b64encode(raw).decode("ascii"), "encoding": "base64"},
        )
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = v1.api_json(
        token,
        "POST",
        f"{base_url}/git/trees",
        {"base_tree": parent["tree"]["sha"], "tree": entries},
    )
    commit = v1.api_json(
        token,
        "POST",
        f"{base_url}/git/commits",
        {"message": commit_message, "tree": tree["sha"], "parents": [parent_sha]},
    )
    ref_status, ref_body = v1.api(token, "GET", f"{base_url}/git/ref/heads/{branch}")
    if ref_status == 200:
        current = json.loads(ref_body.decode("utf-8"))["object"]["sha"]
        if current != commit["sha"]:
            branch = f"{branch}-{commit['sha'][:8]}"
    v1.api_json(
        token,
        "POST",
        f"{base_url}/git/refs",
        {"ref": f"refs/heads/{branch}", "sha": commit["sha"]},
    )
    pr = v1.api_json(
        token,
        "POST",
        f"{base_url}/pulls",
        {"title": title, "head": branch, "base": "main", "body": body, "draft": True},
    )
    return {
        "state": "SUCCESSOR_CREATED",
        "successor_pr": pr["number"],
        "successor_branch": branch,
        "successor_head": commit["sha"],
        "successor_tree": tree["sha"],
        "changed_paths": sorted(files),
    }


def clone_head(repository: str, head_sha: str, parent: Path) -> Path:
    work = parent / "work"
    v1.run_capture(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            f"https://github.com/{repository}.git",
            str(work),
        ],
        parent,
    )
    v1.run_capture(["git", "fetch", "origin", head_sha], work)
    v1.run_capture(["git", "checkout", "--detach", head_sha], work)
    return work


def qce_candidate_pr(token: str, repository: str, status: dict[str, Any]) -> dict[str, Any]:
    first = status.get("predecessor_results", {}).get("QCE-DISCOVERY-INDEX-CURRENT-V1", {})
    number = first.get("successor_pr") if isinstance(first, dict) else None
    if isinstance(number, int):
        pr = v1.api_json(token, "GET", f"https://api.github.com/repos/{repository}/pulls/{number}")
        if pr.get("state") == "open":
            return pr
    existing = find_open_pr(token, repository, "automation/qce-publication-discovery-current-v1")
    if existing is not None:
        return existing
    return v1.api_json(token, "GET", f"https://api.github.com/repos/{repository}/pulls/411")


def handler_qce_discovery(root: Path, unit: dict[str, Any], repository: str, token: str) -> dict[str, Any]:
    existing = find_open_pr(token, repository, str(unit["successor_branch"]))
    if existing is not None:
        return {
            "state": "SUCCESSOR_ALREADY_EXISTS",
            "source_pr": unit["source_pr"],
            "successor_pr": existing["number"],
            "successor_branch": existing["head"]["ref"],
            "successor_head": existing["head"]["sha"],
        }
    return v1.create_qce_successor(root, unit, repository, token)


def download_artifact(token: str, repository: str, artifact_id: int) -> bytes:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/actions/artifacts/{artifact_id}/zip",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qikvrt-autonomous-ontology-closure/2.0",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def handler_qce_receipt(
    root: Path,
    unit: dict[str, Any],
    repository: str,
    token: str,
    status: dict[str, Any],
) -> dict[str, Any]:
    pr = qce_candidate_pr(token, repository, status)
    head_sha = pr["head"]["sha"]
    gates = exact_head_gates(token, repository, head_sha)
    if not gates["ready"]:
        return {
            "state": "WAITING_ON_QCE_EXACT_HEAD_GATES",
            "source_pr": pr["number"],
            "source_head": head_sha,
            "gates": gates["required"],
        }
    run_id = int(unit["known_successful_run"])
    run = v1.api_json(token, "GET", f"https://api.github.com/repos/{repository}/actions/runs/{run_id}")
    run_head = str(run.get("head_sha", ""))
    with tempfile.TemporaryDirectory(prefix="qikvrt-qce-receipt-") as temp:
        work = clone_head(repository, head_sha, Path(temp))
        qce_root = work / "docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence"
        for path in sorted(qce_root.glob("*RECEIPT*.json")):
            if "TEMPLATE" in path.name.upper():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if str(run_id) in text and run_head and run_head in text:
                return {
                    "state": "RECEIPT_ALREADY_PRESENT",
                    "source_pr": pr["number"],
                    "source_head": head_sha,
                    "receipt_path": str(path.relative_to(work)),
                    "run_id": run_id,
                    "run_head": run_head,
                }
        artifacts = v1.api_json(
            token,
            "GET",
            f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100",
        ).get("artifacts", [])
        candidates = [
            item
            for item in artifacts
            if not item.get("expired")
            and "qce" in str(item.get("name", "")).lower()
            and (
                "receipt" in str(item.get("name", "")).lower()
                or "formal" in str(item.get("name", "")).lower()
            )
        ]
        if len(candidates) != 1:
            return {
                "state": "WAITING_ON_UNIQUE_QCE_RECEIPT_ARTIFACT",
                "run_id": run_id,
                "candidate_artifacts": [
                    {"id": x.get("id"), "name": x.get("name"), "expired": x.get("expired")}
                    for x in candidates
                ],
            }
        archive = download_artifact(token, repository, int(candidates[0]["id"]))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            matches: list[tuple[str, bytes]] = []
            for name in zf.namelist():
                if not name.lower().endswith(".json"):
                    continue
                raw = zf.read(name)
                text = raw.decode("utf-8", errors="replace")
                if str(run_id) in text and run_head in text and "kernel" in text.lower():
                    matches.append((name, raw))
        preferred = [item for item in matches if "receipt" in item[0].lower()]
        selected = preferred[0] if len(preferred) == 1 else (matches[0] if len(matches) == 1 else None)
        if selected is None:
            return {
                "state": "WAITING_ON_UNIQUE_QCE_RECEIPT_JSON",
                "run_id": run_id,
                "matches": [name for name, _raw in matches],
            }
        destination = qce_root / RECEIPT_NAME
        destination.write_bytes(selected[1])
        regenerate = qce_root / "regenerate_qce_integrity.py"
        if regenerate.exists():
            v1.run_capture([sys.executable, "-B", str(regenerate.relative_to(work))], work)
        integrity = work / "tools/qikvrt_integrity.py"
        if integrity.exists():
            v1.run_capture([sys.executable, "-B", str(integrity.relative_to(work)), "generate"], work)
        changed = [
            line
            for line in v1.run_capture(["git", "diff", "--name-only", head_sha, "--"], work).splitlines()
            if line.strip()
        ]
        allowed_roots = {
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        }
        unexpected = [
            path
            for path in changed
            if path not in allowed_roots
            and not path.startswith("docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/")
        ]
        if unexpected:
            raise v1.OperatorError(f"QCE receipt successor changed unexpected paths: {unexpected}")
        files = {path: (work / path).read_bytes() for path in changed}
        details = create_commit_pr(
            token,
            repository,
            head_sha,
            files,
            str(unit["successor_branch"]),
            "QCE: persist exact kernel receipt on current successor",
            (
                f"Persist the bounded QCE kernel receipt from run `{run_id}` after terminal exact-head gates. "
                "No physical correspondence, Zenodo publication, PASS, FINAL_PASS, or EFFECT_ACK_DONE is inferred."
            ),
            "Persist exact QCE kernel receipt and regenerate bounded integrity",
        )
        details["state"] = "RECEIPT_SUCCESSOR_CREATED" if details["state"] == "SUCCESSOR_CREATED" else details["state"]
        details["run_id"] = run_id
        details["run_head"] = run_head
        return details


def current_main(token: str, repository: str) -> str:
    value = api_value(token, "GET", f"https://api.github.com/repos/{repository}/git/ref/heads/main")
    return str(value["object"]["sha"])


def handler_audio_review(unit: dict[str, Any], repository: str, token: str) -> dict[str, Any]:
    existing = find_open_pr(token, repository, str(unit["successor_branch"]))
    if existing is not None:
        return {
            "state": "AUDIO_REVIEW_REQUEST_ALREADY_EXISTS",
            "successor_pr": existing["number"],
            "successor_branch": existing["head"]["ref"],
            "successor_head": existing["head"]["sha"],
        }
    run_id = int(unit["known_transport_run"])
    run = v1.api_json(token, "GET", f"https://api.github.com/repos/{repository}/actions/runs/{run_id}")
    if run.get("status") != "completed" or run.get("conclusion") != "success":
        return {
            "state": "WAITING_ON_SUCCESSFUL_AUDIO_TRANSPORT_RUN",
            "run_id": run_id,
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
        }
    artifacts = v1.api_json(
        token,
        "GET",
        f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100",
    ).get("artifacts", [])
    bounded = [
        item
        for item in artifacts
        if not item.get("expired")
        and any(key in str(item.get("name", "")).lower() for key in ("a08", "a09", "audio"))
    ]
    if not bounded:
        return {
            "state": "WAITING_ON_BOUNDED_AUDIO_ARTIFACTS",
            "run_id": run_id,
            "artifact_count": len(artifacts),
        }
    payload = {
        "_license": {
            "classification": "machine_readable_review_request",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_audio_human_review_request_v1",
        "repository": repository,
        "source_pr": int(unit["source_pr"]),
        "run_id": run_id,
        "run_head": run.get("head_sha"),
        "artifacts": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "size_in_bytes": item.get("size_in_bytes"),
                "digest": item.get("digest"),
                "created_at": item.get("created_at"),
                "expires_at": item.get("expires_at"),
            }
            for item in bounded
        ],
        "automatic_asr": "EVIDENCE_AVAILABLE",
        "human_acoustic_review": "REQUIRED",
        "verbatim_verified": False,
        "scientific_validation": "NOT_INFERRED",
        "publication_authorized": False,
        "release_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        "effect_state": "EFFECT_ACK_CONTINUE",
    }
    details = create_commit_pr(
        token,
        repository,
        current_main(token, repository),
        {str(AUDIO_REVIEW): v1.canonical_json(payload).encode("utf-8")},
        str(unit["successor_branch"]),
        "Audio: materialize A08/A09 human acoustic-review request",
        (
            f"Bind the bounded ASR artifacts from run `{run_id}` for human acoustic review. "
            "No transcript is promoted to verbatim certification and no scientific or publication claim is created."
        ),
        "Materialize digest-bound A08/A09 acoustic-review request",
    )
    details["state"] = "AUDIO_REVIEW_REQUEST_CREATED" if details["state"] == "SUCCESSOR_CREATED" else details["state"]
    details["run_id"] = run_id
    return details


def handler_unified_work(unit: dict[str, Any], repository: str, token: str) -> dict[str, Any]:
    existing = find_open_pr(token, repository, str(unit["successor_branch"]))
    if existing is not None:
        return {
            "state": "UNIFIED_WORK_UNITS_ALREADY_EXIST",
            "successor_pr": existing["number"],
            "successor_branch": existing["head"]["ref"],
            "successor_head": existing["head"]["sha"],
        }
    payload = {
        "_license": {
            "classification": "machine_readable_work_unit_program",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_unified_ontology_kernel_program_v1",
        "program_id": "UNIFIED-ONTOLOGY-KERNEL-PROGRAM-V1",
        "formal_chain": [
            "DIFFERENCE",
            "INFORMATION",
            "RELATION",
            "CAUSALITY",
            "SPACETIME",
            "MATTER",
            "LIFE",
            "COGNITION",
            "RESPONSIBILITY",
            "FUTURE",
        ],
        "required_claim_kinds": [
            "DEFINITION",
            "ASSUMPTION",
            "FORMAL_THEOREM",
            "CORRESPONDENCE_POSTULATE",
            "EMPIRICAL_CLAIM",
            "INTERPRETATION",
            "NORMATIVE_RULE",
        ],
        "finite_work_units": [
            {
                "id": f"UOK-{index:02d}",
                "from": left,
                "to": right,
                "state": "OPEN_FORMALIZATION",
                "requirements": [
                    "explicit typed signature",
                    "declared assumptions",
                    "non-circular construction",
                    "model witness or inconsistency result",
                    "complete axiom audit",
                    "no empirical correspondence inferred from kernel acceptance",
                ],
            }
            for index, (left, right) in enumerate(
                zip(
                    [
                        "DIFFERENCE",
                        "INFORMATION",
                        "RELATION",
                        "CAUSALITY",
                        "SPACETIME",
                        "MATTER",
                        "LIFE",
                        "COGNITION",
                        "RESPONSIBILITY",
                    ],
                    [
                        "INFORMATION",
                        "RELATION",
                        "CAUSALITY",
                        "SPACETIME",
                        "MATTER",
                        "LIFE",
                        "COGNITION",
                        "RESPONSIBILITY",
                        "FUTURE",
                    ],
                ),
                start=1,
            )
        ],
        "physical_obligations": [f"QCE-O0{index}" for index in range(1, 8)],
        "formal_completion": "OPEN",
        "physical_correspondence": "OPEN_CANDIDATE",
        "empirical_confirmation": "OPEN",
        "independent_reproduction": "OPEN",
        "release_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        "effect_state": "EFFECT_ACK_CONTINUE",
    }
    details = create_commit_pr(
        token,
        repository,
        current_main(token, repository),
        {str(UNIFIED_WORK): v1.canonical_json(payload).encode("utf-8")},
        str(unit["successor_branch"]),
        "Formalization: materialize unified ontology kernel work units",
        (
            "Add a finite typed formalization program for the complete ontology chain while keeping physical correspondence, empirical confirmation and independent reproduction explicitly open."
        ),
        "Materialize finite unified ontology kernel program",
    )
    details["state"] = "UNIFIED_WORK_UNITS_CREATED" if details["state"] == "SUCCESSOR_CREATED" else details["state"]
    return details


def plan(root: Path) -> dict[str, Any]:
    _policy, queue, status = load_contract(root)
    completed = set(status["completed_work_units"])
    automatic = [unit for unit in queue["work_units"] if unit.get("automatic") is True]
    for unit in automatic:
        if unit["id"] in completed:
            continue
        predecessors = [prior["id"] for prior in automatic if prior["order"] < unit["order"]]
        if all(uid in completed for uid in predecessors):
            return {"state": "ELIGIBLE", "work_unit": unit}
        return {
            "state": "WAITING_ON_PREDECESSOR",
            "work_unit": unit,
            "missing_predecessors": [uid for uid in predecessors if uid not in completed],
        }
    return {"state": "NO_AUTOMATIC_WORK", "work_unit": None}


def write_status(
    root: Path,
    status: dict[str, Any],
    unit: dict[str, Any] | None,
    details: dict[str, Any],
    blocker: str | None = None,
) -> None:
    updated = dict(status)
    updated["observed_at"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    updated["last_run_id"] = int(run_id) if run_id.isdigit() else None
    updated["last_action"] = unit.get("id") if unit else None
    updated["last_result"] = details.get("state", "BLOCK")
    updated["blockers"] = [blocker] if blocker else []
    completed = list(updated.get("completed_work_units", []))
    results = dict(updated.get("predecessor_results", {}))
    if unit is not None:
        results[unit["id"]] = details
        if details.get("state") in SUCCESS_STATES and unit["id"] not in completed:
            completed.append(unit["id"])
    updated["completed_work_units"] = completed
    updated["predecessor_results"] = results
    (root / STATUS).write_text(v1.canonical_json(updated), encoding="utf-8")


def apply(root: Path, repository: str, token: str) -> dict[str, Any]:
    _policy, _queue, status = load_contract(root)
    selected = plan(root)
    unit = selected.get("work_unit")
    if selected["state"] != "ELIGIBLE" or unit is None:
        details = {"state": selected["state"], **{k: v for k, v in selected.items() if k != "work_unit"}}
        write_status(root, status, unit, details)
        return details
    try:
        handler = unit["handler"]
        if handler == "qce_publication_discovery_successor":
            details = handler_qce_discovery(root, unit, repository, token)
        elif handler == "qce_kernel_receipt_persistence":
            details = handler_qce_receipt(root, unit, repository, token, status)
        elif handler == "audio_artifact_review_request":
            details = handler_audio_review(unit, repository, token)
        elif handler == "materialize_unified_ontology_work_units":
            details = handler_unified_work(unit, repository, token)
        else:
            raise v1.OperatorError(f"unknown V2 handler: {handler}")
    except v1.OperatorError as exc:
        details = {"state": "BLOCK", "error": str(exc)}
        write_status(root, status, unit, details, str(exc))
        raise
    write_status(root, status, unit, details)
    return details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "plan", "apply"])
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    try:
        if args.command == "verify":
            load_contract(root)
            result = {"state": "VERIFIED"}
        elif args.command == "plan":
            result = plan(root)
        else:
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                raise v1.OperatorError("GITHUB_TOKEN is required for apply")
            result = apply(root, args.repository, token)
    except v1.OperatorError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    print(v1.canonical_json(result) if args.json else result["state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
