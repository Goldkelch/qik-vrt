#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed autonomous operator for repository-executable ontology work."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import urllib.error
import urllib.request

POLICY = Path("policy/AUTONOMOUS_ONTOLOGY_CLOSURE_V1.json")
QUEUE = Path("state/ontology-autonomy/QUEUE.json")
STATUS = Path("state/ontology-autonomy/STATUS.json")
INDEX_JSON = Path("docs/publications/index.json")
INDEX_HTML = Path("docs/publications/index.html")


class OperatorError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OperatorError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OperatorError(f"expected object in {path}")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_contract(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    policy = load_json(root / POLICY)
    queue = load_json(root / QUEUE)
    status = load_json(root / STATUS)
    if policy.get("schema") != "qikvrt_autonomous_ontology_closure_policy_v1":
        raise OperatorError("wrong policy schema")
    if queue.get("schema") != "qikvrt_autonomous_ontology_closure_queue_v1":
        raise OperatorError("wrong queue schema")
    if status.get("schema") != "qikvrt_autonomous_ontology_closure_status_v1":
        raise OperatorError("wrong status schema")
    claims = {"EFFECT_ACK_DONE": False, "FINAL_PASS": False, "PASS": False}
    if queue.get("release_claims") != claims:
        raise OperatorError("queue contains a false release claim")
    if status.get("release_claims") != claims or policy.get("release_claims") != claims:
        raise OperatorError("release claim projections disagree")
    units = queue.get("work_units")
    if not isinstance(units, list) or not units:
        raise OperatorError("work unit queue is empty")
    ids: set[str] = set()
    orders: list[int] = []
    non_auto = {"EXTERNAL_SCIENCE", "INDEPENDENT_REPLICATION", "IRREVERSIBLE_EXTERNAL_EFFECT"}
    for unit in units:
        if not isinstance(unit, dict):
            raise OperatorError("work unit is not an object")
        uid = unit.get("id")
        if not isinstance(uid, str) or not uid or uid in ids:
            raise OperatorError("work unit IDs must be unique non-empty strings")
        ids.add(uid)
        order = unit.get("order")
        if not isinstance(order, int):
            raise OperatorError(f"{uid}: order is not an integer")
        orders.append(order)
        if unit.get("action_class") in non_auto and unit.get("automatic") is not False:
            raise OperatorError(f"{uid}: external truth gate marked automatic")
        if unit.get("automatic") is True and not unit.get("handler"):
            raise OperatorError(f"{uid}: automatic unit lacks a handler")
    if orders != sorted(orders) or len(orders) != len(set(orders)):
        raise OperatorError("work unit order must be strictly increasing")
    if queue.get("effect_state") != "EFFECT_ACK_CONTINUE":
        raise OperatorError("effect state is not fail-closed")
    return policy, queue, status


def publication_indexed(root: Path, target: str) -> bool:
    return (
        target in (root / INDEX_JSON).read_text(encoding="utf-8")
        and target in (root / INDEX_HTML).read_text(encoding="utf-8")
    )


def find_publication_generator(root: Path) -> Path:
    candidates: list[Path] = []
    for path in sorted((root / "tools").rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if (
            "docs/publications/index.json" in text
            and "docs/publications/index.html" in text
            and "write" in text
        ):
            candidates.append(path)
    if len(candidates) != 1:
        names = [str(path.relative_to(root)) for path in candidates]
        raise OperatorError(f"expected one publication-index generator, found {names}")
    return candidates[0]


def run_capture(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        tail = "\n".join(result.stdout.splitlines()[-120:])
        raise OperatorError(
            f"command failed ({result.returncode}): {' '.join(args)}\n{tail}"
        )
    return result.stdout


def api(
    token: str,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, bytes]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    request.add_header("User-Agent", "qikvrt-autonomous-ontology-closure/1.0")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        if exc.code in {404, 409, 422}:
            return exc.code, body
        raise OperatorError(
            f"GitHub API {method} {url} failed with {exc.code}: {body[:1000]!r}"
        ) from exc


def api_json(
    token: str,
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status, body = api(token, method, url, payload)
    if status < 200 or status >= 300:
        raise OperatorError(
            f"GitHub API {method} {url} returned {status}: {body[:1000]!r}"
        )
    value = json.loads(body.decode("utf-8")) if body else {}
    if not isinstance(value, dict):
        raise OperatorError("GitHub API response is not an object")
    return value


def create_qce_successor(
    root: Path,
    unit: dict[str, Any],
    repository: str,
    token: str,
) -> dict[str, Any]:
    owner, name = repository.split("/", 1)
    base_url = f"https://api.github.com/repos/{owner}/{name}"
    pr = api_json(token, "GET", f"{base_url}/pulls/{int(unit['source_pr'])}")
    if pr.get("state") != "open":
        raise OperatorError("source QCE PR is not open")
    if pr.get("head", {}).get("repo", {}).get("full_name") != repository:
        raise OperatorError("source QCE PR is not a same-repository candidate")
    source_head = pr["head"]["sha"]
    with tempfile.TemporaryDirectory(prefix="qikvrt-qce-successor-") as temp:
        work = Path(temp) / "work"
        run_capture(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                f"https://github.com/{repository}.git",
                str(work),
            ],
            root,
        )
        run_capture(["git", "fetch", "origin", source_head], work)
        run_capture(["git", "checkout", "--detach", source_head], work)
        target = str(unit["required_target"])
        if not publication_indexed(work, target):
            generator = find_publication_generator(work)
            run_capture([sys.executable, "-B", str(generator.relative_to(work))], work)
        if not publication_indexed(work, target):
            raise OperatorError("publication generator did not index the QCE README")
        integrity = work / "tools/qikvrt_integrity.py"
        if integrity.exists():
            run_capture(
                [sys.executable, "-B", str(integrity.relative_to(work)), "generate"],
                work,
            )
        run_capture(
            [
                sys.executable,
                "-B",
                "-m",
                "unittest",
                "-v",
                "tests.test_qikvrt_self_disclosure",
            ],
            work,
        )
        changed = [
            line
            for line in run_capture(
                ["git", "diff", "--name-only", source_head, "--"], work
            ).splitlines()
            if line.strip()
        ]
        allowed = {
            "docs/publications/index.json",
            "docs/publications/index.html",
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        }
        unexpected = sorted(set(changed) - allowed)
        if unexpected:
            raise OperatorError(f"QCE successor changed unexpected paths: {unexpected}")
        if not changed:
            return {
                "state": "NOOP_ALREADY_SATISFIED",
                "source_pr": unit["source_pr"],
                "source_head": source_head,
            }
        source_commit = api_json(
            token, "GET", f"{base_url}/git/commits/{source_head}"
        )
        entries: list[dict[str, Any]] = []
        for rel in changed:
            raw = (work / rel).read_bytes()
            blob = api_json(
                token,
                "POST",
                f"{base_url}/git/blobs",
                {
                    "content": base64.b64encode(raw).decode("ascii"),
                    "encoding": "base64",
                },
            )
            entries.append(
                {"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]}
            )
        tree = api_json(
            token,
            "POST",
            f"{base_url}/git/trees",
            {"base_tree": source_commit["tree"]["sha"], "tree": entries},
        )
        commit = api_json(
            token,
            "POST",
            f"{base_url}/git/commits",
            {
                "message": (
                    "Repair QCE publication discovery on the exact candidate head\n\n"
                    "History-preserving deterministic successor. No scientific claim, "
                    "Zenodo effect, PASS, FINAL_PASS, or EFFECT_ACK_DONE is created."
                ),
                "tree": tree["sha"],
                "parents": [source_head],
            },
        )
        branch = str(unit["successor_branch"])
        status, body = api(token, "GET", f"{base_url}/git/ref/heads/{branch}")
        if status == 200:
            existing = json.loads(body.decode("utf-8"))["object"]["sha"]
            if existing == commit["sha"]:
                return {
                    "state": "SUCCESSOR_ALREADY_EXISTS",
                    "source_pr": unit["source_pr"],
                    "source_head": source_head,
                    "successor_branch": branch,
                    "successor_head": commit["sha"],
                }
            branch = f"{branch}-{commit['sha'][:8]}"
        api_json(
            token,
            "POST",
            f"{base_url}/git/refs",
            {"ref": f"refs/heads/{branch}", "sha": commit["sha"]},
        )
        body_text = (
            f"History-preserving successor of Authority PR #411 exact head `{source_head}`.\n\n"
            "The repository-owned publication generator adds the QCE bundle to the "
            "canonical discovery index, regenerates only repository-native integrity "
            "outputs, and leaves every QCE scientific and effect boundary unchanged.\n\n"
            "No merge, Mirror promotion, Zenodo/IETF mutation, release, `PASS`, "
            "`FINAL_PASS`, or `EFFECT_ACK_DONE` is claimed or authorized."
        )
        new_pr = api_json(
            token,
            "POST",
            f"{base_url}/pulls",
            {
                "title": "QCE: repair publication discovery on exact candidate successor",
                "head": branch,
                "base": "main",
                "body": body_text,
                "draft": True,
            },
        )
        return {
            "state": "SUCCESSOR_CREATED",
            "source_pr": unit["source_pr"],
            "source_head": source_head,
            "successor_branch": branch,
            "successor_head": commit["sha"],
            "successor_tree": tree["sha"],
            "successor_pr": new_pr["number"],
            "changed_paths": changed,
        }


def write_status(
    root: Path,
    status: dict[str, Any],
    *,
    result: str,
    action: str | None,
    blockers: list[str],
    details: dict[str, Any] | None = None,
) -> None:
    updated = dict(status)
    updated["observed_at"] = (
        dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    )
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    updated["last_run_id"] = int(run_id) if run_id.isdigit() else None
    updated["last_action"] = action
    updated["last_result"] = result
    updated["blockers"] = blockers
    if details is not None:
        updated["details"] = details
    (root / STATUS).write_text(canonical_json(updated), encoding="utf-8")


def plan(root: Path) -> dict[str, Any]:
    _policy, queue, _status = validate_contract(root)
    for unit in queue["work_units"]:
        if unit["state"] == "READY" and unit["automatic"] is True:
            return {"state": "ELIGIBLE", "work_unit": unit}
    return {"state": "NO_AUTOMATIC_WORK", "work_unit": None}


def apply(root: Path, repository: str, token: str) -> dict[str, Any]:
    _policy, _queue, status = validate_contract(root)
    selected = plan(root)
    unit = selected.get("work_unit")
    if not unit:
        write_status(
            root,
            status,
            result="NOOP",
            action=None,
            blockers=["NO_ELIGIBLE_AUTOMATIC_WORK_UNIT"],
        )
        return {"state": "NOOP"}
    try:
        if unit["handler"] == "qce_publication_discovery_successor":
            details = create_qce_successor(root, unit, repository, token)
        else:
            raise OperatorError(
                f"handler declared but not implemented in v1: {unit['handler']}"
            )
    except OperatorError as exc:
        write_status(
            root,
            status,
            result="BLOCK",
            action=unit["id"],
            blockers=[str(exc)],
        )
        raise
    write_status(
        root,
        status,
        result=details["state"],
        action=unit["id"],
        blockers=[],
        details=details,
    )
    return details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "plan", "apply"])
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--repository",
        default=os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    try:
        if args.command == "verify":
            validate_contract(root)
            result = {"state": "VERIFIED"}
        elif args.command == "plan":
            result = plan(root)
        else:
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                raise OperatorError("GITHUB_TOKEN is required for apply")
            result = apply(root, args.repository, token)
    except OperatorError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    print(canonical_json(result) if args.json else result["state"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
