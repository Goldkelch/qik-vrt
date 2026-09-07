#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fresh read-only observation of the QIK-VRT Authority/Mirror pair."""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

AUTHORITY = "Goldkelch/qik-vrt"
MIRROR = "ingolf-lohmann/qik-vrt"
API = "https://api.github.com/repos/{repository}/branches/main"


def read_branch(repository: str) -> dict[str, str]:
    request = urllib.request.Request(
        API.format(repository=repository),
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qikvrt-cloud-mirror-observer/1.0",
        },
    )
    token = os.environ.get("QIKVRT_GITHUB_READ_TOKEN", "")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(request, timeout=20) as response:
        value: dict[str, Any] = json.load(response)
    commit = value.get("commit", {})
    head = commit.get("sha")
    tree = commit.get("commit", {}).get("tree", {}).get("sha")
    if not isinstance(head, str) or len(head) != 40:
        raise ValueError(f"{repository}: invalid main head")
    if not isinstance(tree, str) or len(tree) != 40:
        raise ValueError(f"{repository}: invalid main tree")
    return {"repository": repository, "ref_name": "main", "head_sha": head, "root_tree_sha": tree}


def observe(path: Path) -> dict[str, Any]:
    authority = read_branch(AUTHORITY)
    mirror = read_branch(MIRROR)
    same_head = authority["head_sha"] == mirror["head_sha"]
    same_tree = authority["root_tree_sha"] == mirror["root_tree_sha"]
    relationship = (
        "HEAD_AND_TREE_EQUAL"
        if same_head and same_tree
        else "TREE_EQUAL_HEAD_DISTINCT"
        if same_tree
        else "DIVERGED"
    )
    result = {
        "schema": "qikvrt_cloud_authority_mirror_observation_v1",
        "observed_at_unix": int(time.time()),
        "authority": authority,
        "mirror": mirror,
        "relationship": relationship,
        "same_head_observed": same_head,
        "same_root_tree_observed": same_tree,
        "effect_class": "OBSERVE_ONLY",
        "synchronization_claimed": False,
        "merge_claimed": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/var/lib/qikvrt/state/repository-mirror.json"),
    )
    parser.add_argument("--interval", type=int, default=900)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        try:
            value = observe(args.output)
            print(json.dumps(value, sort_keys=True), flush=True)
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            error = {
                "schema": "qikvrt_cloud_authority_mirror_observation_v1",
                "observed_at_unix": int(time.time()),
                "state": "REOBSERVE",
                "reason": str(exc),
                "effect_class": "OBSERVE_ONLY",
                "synchronization_claimed": False,
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(error, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(error, sort_keys=True), flush=True)
            if args.once:
                return 2
        if args.once:
            return 0
        time.sleep(max(60, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
