#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Evaluate the exact dual-repository human-DoD idle predicate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "qikvrt_mesh_dual_repository_idle_gate_v1"

def _load(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: object required")
    return value

def evaluate(authority: dict[str, Any], mirror: dict[str, Any],
             authority_open_issues: int, mirror_open_issues: int) -> dict[str, Any]:
    for name,value in (("authority_open_issues",authority_open_issues),
                       ("mirror_open_issues",mirror_open_issues)):
        if isinstance(value,bool) or not isinstance(value,int) or value < 0:
            raise ValueError(name + " must be a non-negative integer")
    def repo_state(label: str, census: dict[str, Any], issues: int) -> dict[str, Any]:
        counts=census.get("counts")
        if not isinstance(counts,dict):
            raise ValueError(label + " census counts missing")
        prs=counts.get("open_pull_requests")
        if isinstance(prs,bool) or not isinstance(prs,int) or prs < 0:
            raise ValueError(label + " open_pull_requests unavailable")
        complete=census.get("inventory_complete") is True
        merged=census.get("all_productive_branches_merged") is True
        return {
            "repository": census.get("repository"),
            "main_head": census.get("main_head"),
            "subject": census.get("subject"),
            "inventory_complete": complete,
            "all_productive_branches_merged": merged,
            "open_pull_requests": prs,
            "open_issues": issues,
            "idle": complete and merged and prs == 0 and issues == 0,
        }
    a=repo_state("authority",authority,authority_open_issues)
    m=repo_state("mirror",mirror,mirror_open_issues)
    ready=a["idle"] and m["idle"]
    return {
        "schema": SCHEMA,
        "authority": a,
        "mirror": m,
        "human_dod_idle": ready,
        "state": "IDLE_READY" if ready else "BUSY",
        "main_tree_equality_required": False,
        "predecessor_evidence_transfer": False,
        "repository_effect_ack_done": False,
    }

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--authority-census",type=Path,required=True)
    p.add_argument("--mirror-census",type=Path,required=True)
    p.add_argument("--authority-open-issues",type=int,required=True)
    p.add_argument("--mirror-open-issues",type=int,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    report=evaluate(_load(args.authority_census),_load(args.mirror_census),
                    args.authority_open_issues,args.mirror_open_issues)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))
    return 0 if report["human_dod_idle"] else 3

if __name__=="__main__":
    raise SystemExit(main())
