#!/usr/bin/env python3
"""Create a deterministic, bounded virtual QIK-VRT mesh child for a blocked work unit."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "qikvrt_recursive_virtual_mesh_instance_v1"
REQUIRED_REOBSERVATION = (
    "COMMITS", "TREES", "BRANCHES", "PULL_REQUESTS", "ISSUES",
    "REVIEWS_AND_REVIEW_THREADS", "WORKFLOW_RUNS_JOBS_STEPS_CHECKS_AND_ARTIFACTS",
    "REGISTRY_AND_ACTIVE_NODE_SET", "NODE_REQUEST_QUEUE", "LEDGERS_AND_RECEIPTS",
    "MANIFESTS_AND_INTEGRITY_PROJECTIONS", "UNEXPECTED_SIDE_EFFECTS",
)

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def create_virtual_mesh(parent: dict[str, Any]) -> dict[str, Any]:
    required = ("authority_repository", "authority_head", "authority_tree", "blocker")
    missing = [field for field in required if not isinstance(parent.get(field), str) or not parent[field]]
    if missing:
        raise ValueError("blocked work unit is missing: " + ", ".join(missing))
    identity = {
        "schema": SCHEMA,
        "parent_repository": parent["authority_repository"],
        "parent_head": parent["authority_head"],
        "parent_tree": parent["authority_tree"],
        "blocker": parent["blocker"],
    }
    instance_id = sha256(identity)
    return {
        "schema": SCHEMA,
        "instance_id": instance_id,
        "parent": identity,
        "role": "VIRTUAL_AUTHORITY",
        "state": "ACTIVE_UNTIL_BLOCKER_IS_RESOLVED_OR_ESCALATED",
        "authority_rules": {
            "deduplicated_dispatch": True,
            "predecessor_evidence_transfer": "FORBIDDEN",
            "direct_main_mutation": "FORBIDDEN",
            "post_dispatch_deep_reobservation": "REQUIRED",
            "missing_or_ambiguous_receipt": "HOLD_UNVERIFIED",
        },
        "work_queue": [{
            "work_id": sha256({"instance_id": instance_id, "kind": "UNBLOCK"}),
            "kind": "UNBLOCK_PARENT_BLOCKER",
            "blocker": parent["blocker"],
            "state": "PENDING",
        }],
        "required_deep_reobservation": list(REQUIRED_REOBSERVATION),
        "completion": {
            "parent_blocker_resolved": False,
            "child_receipts_complete": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parent = json.loads(args.parent.read_text(encoding="utf-8"))
    instance = create_virtual_mesh(parent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(instance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(instance, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
