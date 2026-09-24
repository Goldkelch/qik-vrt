#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""QIK-VRT Mesh scenario benchmark built on the canonical fan-out harness."""
from __future__ import annotations
import argparse
import json
import pathlib
import statistics
import tempfile
import time
from typing import Any

from tools.qikvrt_mesh_fanout_benchmark import (
    FANOUTS,
    ROUTES,
    consolidate,
    percentile,
    run_one,
    timed_trial,
)
from tools.qikvrt_real_mesh import MeshHarness, build_message

def transition(harness: MeshHarness, scenario: str, fanout: int, trial: int,
               source_head: str, source_tree: str) -> dict[str, Any]:
    if scenario == "STEADY_CONCURRENT":
        return {"scenario": scenario, "transition_ns": 0, "fail_closed_observed": None}
    node_id="pair-b-mirror"
    if scenario == "RESTART_RECOVERY":
        started=time.perf_counter_ns()
        harness.restart(node_id)
        elapsed=time.perf_counter_ns()-started
        return {
            "scenario": scenario,
            "node_id": node_id,
            "restart_rebind_ns": elapsed,
            "transition_ns": elapsed,
            "fail_closed_observed": None,
        }
    if scenario == "PARTITION_RECOVERY":
        node=harness.nodes[node_id]
        node.stop()
        route=ROUTES[0]
        probe=build_message(
            harness.topology,route,
            message_id=f"partition-probe-f{fanout}-t{trial}",
            nonce=f"PARTITION-PROBE-f{fanout}-t{trial}",
            source_head=source_head,source_tree=source_tree,
        )
        started=time.perf_counter_ns()
        response=harness.route_message(probe)
        detection=time.perf_counter_ns()-started
        fail_closed=(
            response.get("schema") == "qikvrt_real_mesh_hold_v1"
            and response.get("ordinary_release") is False
            and response.get("retryable") is True
            and "NEXT_HOP_UNREACHABLE" in str(response.get("reason"))
        )
        if not fail_closed:
            raise RuntimeError("PARTITION_DID_NOT_FAIL_CLOSED")
        restore_started=time.perf_counter_ns()
        harness.restart(node_id)
        restore=time.perf_counter_ns()-restore_started
        return {
            "scenario": scenario,
            "node_id": node_id,
            "partition_detection_ns": detection,
            "restart_rebind_ns": restore,
            "transition_ns": detection + restore,
            "fail_closed_observed": True,
        }
    raise ValueError("unsupported scenario")

def benchmark_scenario(*,scenario: str,source_head: str,source_tree: str,
                       messages: int,repeats: int,
                       repository_state: dict[str,Any]) -> dict[str,Any]:
    results=[]
    for fanout in FANOUTS:
        with tempfile.TemporaryDirectory(prefix=f"qikvrt-{scenario.lower()}-{fanout}-") as temp:
            with MeshHarness(pathlib.Path(temp),source_tree) as harness:
                assert harness.topology is not None
                warm=build_message(
                    harness.topology,ROUTES[0],
                    message_id=f"scenario-warmup-{scenario.lower()}-f{fanout}",
                    nonce=f"SCENARIO-WARMUP-{scenario}-f{fanout}",
                    source_head=source_head,source_tree=source_tree,
                )
                warm_result=run_one(harness,warm)
                if not warm_result["ok"]:
                    raise RuntimeError("WARMUP_FAILED:"+str(warm_result))
                for trial in range(repeats):
                    state=transition(
                        harness,scenario,fanout,trial,source_head,source_tree
                    )
                    row=timed_trial(
                        harness,fanout=fanout,messages=messages,trial=trial,
                        source_head=source_head,source_tree=source_tree,
                    )
                    row["scenario_transition"]=state
                    results.append(row)
    grouped={}
    for row in results:
        grouped.setdefault(row["fanout"],[]).append(row)
    baseline=statistics.median(
        row["verified_messages_per_second"] for row in grouped[1]
    )
    summary=[]
    for fanout in FANOUTS:
        rows=grouped[fanout]
        throughput=[row["verified_messages_per_second"] for row in rows]
        latency=[
            row["latency_ms"]["median"] for row in rows
            if row["latency_ms"] is not None
        ]
        p95=[
            row["latency_ms"]["p95"] for row in rows
            if row["latency_ms"] is not None
        ]
        transitions=[row["scenario_transition"]["transition_ns"]/1_000_000.0 for row in rows]
        summary.append({
            "fanout":fanout,
            "median_verified_messages_per_second":statistics.median(throughput),
            "throughput_ratio_vs_fanout_1":(
                statistics.median(throughput)/baseline if baseline else None
            ),
            "median_successful_messages":statistics.median(
                row["successful_messages"] for row in rows
            ),
            "median_failed_messages":statistics.median(
                row["failed_messages"] for row in rows
            ),
            "median_message_latency_ms":statistics.median(latency) if latency else None,
            "median_p95_latency_ms":statistics.median(p95) if p95 else None,
            "median_transition_ms":statistics.median(transitions),
            "all_trials_lossless":all(row["consolidation"]["lossless"] for row in rows),
            "fail_closed_observed_when_required":all(
                row["scenario_transition"]["fail_closed_observed"] is True
                for row in rows
            ) if scenario=="PARTITION_RECOVERY" else None,
        })
    return {
        "schema":"qikvrt_mesh_scenario_benchmark_v1",
        "scenario":scenario,
        "source_head":source_head,
        "source_tree":source_tree,
        "repository_state":repository_state,
        "messages_per_trial":messages,
        "repeats":repeats,
        "fanouts":list(FANOUTS),
        "summary":summary,
        "trials":results,
        "acceptance":{
            "all_trials_lossless":all(row["consolidation"]["lossless"] for row in results),
            "partition_fail_closed":(
                all(row["scenario_transition"]["fail_closed_observed"] is True for row in results)
                if scenario=="PARTITION_RECOVERY" else None
            ),
            "predecessor_evidence_transfer":False,
            "repository_effect_ack_done":False,
        },
        "evidence_boundary":{
            "loopback_tcp_software_only":True,
            "physical_m68000_speedup_established":False,
            "fpga_asic_silicon_speedup_established":False,
            "patentability_established":False,
        },
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--scenario",choices=["STEADY_CONCURRENT","RESTART_RECOVERY","PARTITION_RECOVERY"],required=True)
    p.add_argument("--source-head",required=True)
    p.add_argument("--source-tree",required=True)
    p.add_argument("--messages",type=int,default=20)
    p.add_argument("--repeats",type=int,default=3)
    p.add_argument("--repository-state",type=pathlib.Path,required=True)
    p.add_argument("--output",type=pathlib.Path,required=True)
    a=p.parse_args()
    state=json.loads(a.repository_state.read_text(encoding="utf-8"))
    report=benchmark_scenario(
        scenario=a.scenario,source_head=a.source_head,source_tree=a.source_tree,
        messages=a.messages,repeats=a.repeats,repository_state=state
    )
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report["summary"],sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
