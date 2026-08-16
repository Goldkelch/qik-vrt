#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def gh_json(*args: str) -> object:
    out = subprocess.check_output(["gh", "api", *args], text=True)
    return json.loads(out)


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", "api", *args], text=True).strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository", required=True)
    p.add_argument("--pr", required=True, type=int)
    p.add_argument("--expected-head", required=True)
    ns = p.parse_args()

    pr = gh_json(f"repos/{ns.repository}/pulls/{ns.pr}")
    if not isinstance(pr, dict) or pr.get("state") != "open":
        raise SystemExit("HOLD: pull request is not open")
    head = pr.get("head", {})
    base = pr.get("base", {})
    if head.get("repo", {}).get("full_name") != ns.repository:
        raise SystemExit("HOLD: cross-repository head is forbidden")
    if head.get("sha") != ns.expected_head:
        raise SystemExit("HOLD: exact head moved")
    branch = head.get("ref")
    if not isinstance(branch, str) or not branch or branch == base.get("ref"):
        raise SystemExit("HOLD: default/base branch carrier is forbidden")

    commit = gh_json(f"repos/{ns.repository}/git/commits/{ns.expected_head}")
    if not isinstance(commit, dict):
        raise SystemExit("HOLD: exact commit unavailable")
    tree = commit.get("tree", {}).get("sha")
    if not isinstance(tree, str) or len(tree) != 40:
        raise SystemExit("HOLD: exact tree unavailable")

    runs = gh_json(f"repos/{ns.repository}/actions/runs?head_sha={ns.expected_head}&per_page=100")
    observed = [] if not isinstance(runs, dict) else runs.get("workflow_runs", [])
    if not any(isinstance(r, dict) and r.get("conclusion") == "action_required" for r in observed):
        raise SystemExit("HOLD: action_required is not established on exact head")

    payload = json.dumps({
        "message": "chore(actions): trusted tree-identical verification carrier",
        "tree": tree,
        "parents": [ns.expected_head],
    })
    created = subprocess.check_output(
        ["gh", "api", "-X", "POST", f"repos/{ns.repository}/git/commits", "--input", "-"],
        input=payload,
        text=True,
    )
    new_commit = json.loads(created)
    new_sha = new_commit.get("sha")
    if not isinstance(new_sha, str) or len(new_sha) != 40:
        raise SystemExit("BLOCK: carrier commit creation returned no SHA")

    ref_payload = json.dumps({"sha": new_sha, "force": False})
    subprocess.check_output(
        ["gh", "api", "-X", "PATCH", f"repos/{ns.repository}/git/refs/heads/{branch}", "--input", "-"],
        input=ref_payload,
        text=True,
    )

    readback = gh_json(f"repos/{ns.repository}/git/commits/{new_sha}")
    if not isinstance(readback, dict) or readback.get("tree", {}).get("sha") != tree:
        raise SystemExit("BLOCK: carrier tree changed")
    print(json.dumps({
        "state": "TRUSTED_TREE_IDENTICAL_CARRIER_CREATED",
        "previous_head": ns.expected_head,
        "new_head": new_sha,
        "tree": tree,
        "branch": branch,
        "force_push": False,
        "fresh_exact_head_gates_required": True,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
