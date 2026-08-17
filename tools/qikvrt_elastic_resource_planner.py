#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import argparse
import json
from pathlib import Path

POLICY_PATH = Path("state/autonomy/BOUNDED_ELASTIC_RESOURCE_DELEGATION_V1.json")
DEFAULT_WORK = ["repository", "workflows", "integrity", "terminal", "effect-ack", "mesh", "cache", "reviews"]


def load_policy(path: Path = POLICY_PATH):
    return json.loads(path.read_text(encoding="utf-8"))


def build_plan(requested: int | None = None, work_items=None):
    policy = load_policy()
    work = list(work_items or DEFAULT_WORK)
    ceiling = int(policy["elasticity"]["max_observer_lanes"])
    default = int(policy["elasticity"]["default_observer_lanes"])
    lanes = min(len(work), ceiling, max(1, requested if requested is not None else default))
    shards = [{"lane": i, "work": work[i::lanes]} for i in range(lanes)]
    return {
        "schema": "qikvrt_elastic_resource_plan_v1",
        "state": "PLAN",
        "observer_lanes": lanes,
        "productive_writer_limit": int(policy["serialization"]["productive_writer_limit"]),
        "shards": shards,
        "constraints": {
            "read_only_parallel_lanes": True,
            "deterministic_reduction_required": True,
            "credential_escalation_forbidden": True,
            "failed_gate_may_not_be_masked": True,
            "external_effect_authorization_implied": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lanes", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    plan = build_plan(args.lanes)
    print(json.dumps(plan, sort_keys=True, separators=(",", ":")) if args.json else json.dumps(plan, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
