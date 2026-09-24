#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded QIK-VRT real-mesh fan-out and lossless consolidation benchmark.

Measures software execution on four independent loopback TCP node processes.
Every timed message is independently reobserved from all node-local ledgers and
closed only by the existing bounded Effect-Acknowledgement evaluator. The
consolidator verifies cardinality, unique identity and SHA-256 preservation.

This does not establish FPGA/ASIC/silicon performance or patentability.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import pathlib
import platform
import statistics
import sys
import tempfile
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.qikvrt_real_mesh import (
    MeshHarness,
    build_message,
    canonical_sha256,
    finalize_effect_ack,
    reobserve_route,
)

FANOUTS = (1, 2, 4, 8, 16)
ROUTES = (
    ("pair-a-authority","pair-a-mirror","pair-b-mirror","pair-b-authority"),
    ("pair-b-authority","pair-b-mirror","pair-a-mirror","pair-a-authority"),
    ("pair-b-mirror","pair-a-mirror","pair-a-authority","pair-b-authority"),
    ("pair-a-mirror","pair-a-authority","pair-b-authority","pair-b-mirror"),
)

def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[int(round((len(ordered) - 1) * q))]

def cpu_model() -> str:
    path = pathlib.Path("/proc/cpuinfo")
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
    return platform.processor() or "UNAVAILABLE"

def run_one(harness: MeshHarness, message: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter_ns()
    terminal = harness.route_message(message)
    observation = reobserve_route(harness, message, terminal)
    ack = finalize_effect_ack(message, observation)
    elapsed = time.perf_counter_ns() - start
    if terminal["message_id"] != message["message_id"]:
        raise RuntimeError("MESSAGE_ID_MISMATCH")
    if terminal["payload_sha256"] != message["payload_sha256"]:
        raise RuntimeError("PAYLOAD_HASH_MISMATCH")
    if not observation["complete_route_reobserved"]:
        raise RuntimeError("ROUTE_NOT_REOBSERVED")
    return {
        "message_id": message["message_id"],
        "route_id": message["route_id"],
        "payload_sha256": message["payload_sha256"],
        "terminal_receipt_sha256": canonical_sha256(terminal),
        "route_observation_sha256": canonical_sha256(observation),
        "effect_ack_sha256": canonical_sha256(ack),
        "latency_ns": elapsed,
    }

def consolidate(expected_ids: set[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.perf_counter_ns()
    observed_ids = [row["message_id"] for row in rows]
    unique_ids = set(observed_ids)
    missing = sorted(expected_ids - unique_ids)
    unexpected = sorted(unique_ids - expected_ids)
    duplicates = len(observed_ids) - len(unique_ids)
    projection = [
        {
            "message_id": row["message_id"],
            "route_id": row["route_id"],
            "payload_sha256": row["payload_sha256"],
            "terminal_receipt_sha256": row["terminal_receipt_sha256"],
            "route_observation_sha256": row["route_observation_sha256"],
            "effect_ack_sha256": row["effect_ack_sha256"],
        }
        for row in sorted(rows, key=lambda row: row["message_id"])
    ]
    digest = canonical_sha256(projection)
    elapsed = time.perf_counter_ns() - start
    if missing or unexpected or duplicates:
        raise RuntimeError(
            f"LOSSLESS_CONSOLIDATION_FAILED missing={missing} "
            f"unexpected={unexpected} duplicates={duplicates}"
        )
    return {
        "expected_results": len(expected_ids),
        "observed_results": len(rows),
        "unique_results": len(unique_ids),
        "missing_results": 0,
        "unexpected_results": 0,
        "duplicate_results": 0,
        "hash_mismatch_results": 0,
        "lossless": True,
        "consolidation_ns": elapsed,
        "consolidated_sha256": digest,
    }

def timed_trial(harness: MeshHarness, *, fanout: int, messages: int, trial: int,
                source_head: str, source_tree: str) -> dict[str, Any]:
    batch = []
    for index in range(messages):
        route = ROUTES[index % len(ROUTES)]
        ident = f"f{fanout}-t{trial}-m{index:04d}"
        batch.append(build_message(
            harness.topology, route,
            message_id=f"mesh-bench-{ident}",
            nonce=f"mesh-bench-nonce-{ident}",
            source_head=source_head, source_tree=source_tree,
        ))
    expected = {item["message_id"] for item in batch}
    started = time.perf_counter_ns()
    with concurrent.futures.ThreadPoolExecutor(max_workers=fanout) as executor:
        rows = list(executor.map(lambda message: run_one(harness, message), batch))
    workload_ns = time.perf_counter_ns() - started
    consolidation = consolidate(expected, rows)
    total_ns = workload_ns + consolidation["consolidation_ns"]
    latencies_ms = [row["latency_ns"] / 1_000_000.0 for row in rows]
    return {
        "fanout": fanout,
        "trial": trial,
        "messages": messages,
        "workload_ns": workload_ns,
        "total_verified_ns": total_ns,
        "verified_messages_per_second": messages / (total_ns / 1_000_000_000.0),
        "latency_ms": {
            "min": min(latencies_ms),
            "median": statistics.median(latencies_ms),
            "p95": percentile(latencies_ms, 0.95),
            "max": max(latencies_ms),
        },
        "consolidation": consolidation,
    }

def benchmark(*, source_head: str, source_tree: str, messages: int, repeats: int) -> dict[str, Any]:
    results = []
    for fanout in FANOUTS:
        with tempfile.TemporaryDirectory(prefix=f"qikvrt-fanout-{fanout}-") as temp:
            with MeshHarness(pathlib.Path(temp), source_tree) as harness:
                assert harness.topology is not None
                warm = build_message(
                    harness.topology, ROUTES[0],
                    message_id=f"mesh-bench-warmup-f{fanout}",
                    nonce=f"mesh-bench-warmup-nonce-f{fanout}",
                    source_head=source_head, source_tree=source_tree,
                )
                run_one(harness, warm)
                for trial in range(repeats):
                    results.append(timed_trial(
                        harness, fanout=fanout, messages=messages, trial=trial,
                        source_head=source_head, source_tree=source_tree,
                    ))
    grouped = {}
    for row in results:
        grouped.setdefault(row["fanout"], []).append(row)
    baseline = statistics.median(
        row["verified_messages_per_second"] for row in grouped[1]
    )
    summary = []
    for fanout in FANOUTS:
        rows = grouped[fanout]
        throughput = [row["verified_messages_per_second"] for row in rows]
        median_throughput = statistics.median(throughput)
        summary.append({
            "fanout": fanout,
            "repeats": repeats,
            "messages_per_trial": messages,
            "median_verified_messages_per_second": median_throughput,
            "min_verified_messages_per_second": min(throughput),
            "max_verified_messages_per_second": max(throughput),
            "throughput_ratio_vs_fanout_1": median_throughput / baseline,
            "median_message_latency_ms": statistics.median(
                row["latency_ms"]["median"] for row in rows
            ),
            "median_p95_latency_ms": statistics.median(
                row["latency_ms"]["p95"] for row in rows
            ),
            "median_consolidation_ms": statistics.median(
                row["consolidation"]["consolidation_ns"] / 1_000_000.0
                for row in rows
            ),
            "all_trials_lossless": all(
                row["consolidation"]["lossless"] for row in rows
            ),
        })
    return {
        "schema": "qikvrt_mesh_fanout_consolidation_benchmark_v1",
        "source_head": source_head,
        "source_tree": source_tree,
        "workload": {
            "runtime": "tools/qikvrt_real_mesh.py",
            "transport": "LOOPBACK_TCP",
            "node_processes": 4,
            "authority_mirror_pairs": 2,
            "routes": [list(route) for route in ROUTES],
            "fanouts": list(FANOUTS),
            "messages_per_trial": messages,
            "repeats": repeats,
            "timed_scope": "TCP route + durable ledgers + full route readback + bounded Effect-Ack + consolidation",
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "logical_cpu_count": os.cpu_count(),
            "cpu_model": cpu_model(),
            "github_runner_name": os.environ.get("RUNNER_NAME"),
            "github_runner_os": os.environ.get("RUNNER_OS"),
            "github_runner_arch": os.environ.get("RUNNER_ARCH"),
        },
        "summary": summary,
        "trials": results,
        "lossless_acceptance": {
            "all_trials_lossless": all(
                row["consolidation"]["lossless"] for row in results
            ),
            "predecessor_evidence_transfer": False,
            "transport_ack_is_effect_ack": False,
            "repository_effect_ack_done": False,
        },
        "evidence_boundary": {
            "software_loopback_benchmark": True,
            "multi_host_network_benchmark": False,
            "physical_m68000_benchmark": False,
            "fpga_or_asic_benchmark": False,
            "silicon_speedup_established": False,
            "patentability_established": False,
            "suitable_as_bounded_software_performance_evidence": True,
            "physical_semiconductor_projection_requires_additional_evidence": True,
        },
    }

def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# QIK-VRT Mesh Fan-Out / Lossless Consolidation Benchmark",
        "",
        "Source HEAD: " + report["source_head"],
        "Source TREE: " + report["source_tree"],
        "",
        "| Fan-out | Median verified msg/s | Ratio vs 1 | Median latency ms | Median p95 ms | Consolidation ms | Lossless |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for row in report["summary"]:
        lines.append(
            "| {fanout} | {t:.3f} | {r:.3f}x | {l:.3f} | {p:.3f} | {c:.3f} | {ok} |".format(
                fanout=row["fanout"],
                t=row["median_verified_messages_per_second"],
                r=row["throughput_ratio_vs_fanout_1"],
                l=row["median_message_latency_ms"],
                p=row["median_p95_latency_ms"],
                c=row["median_consolidation_ms"],
                ok="YES" if row["all_trials_lossless"] else "NO",
            )
        )
    lines += [
        "",
        "Every timed result was reobserved from all node-local ledgers before bounded Effect-Ack closure.",
        "The consolidation gate requires exact cardinality, unique message IDs and preserved SHA-256 bindings.",
        "",
        "Evidence boundary: hosted-runner loopback-TCP software benchmark only; no physical MC68000, FPGA, ASIC or silicon speedup and no patentability conclusion.",
        "",
    ]
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--messages", type=int, default=20)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--json", type=pathlib.Path, required=True)
    parser.add_argument("--markdown", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if not 4 <= args.messages <= 256:
        parser.error("--messages must be 4..256")
    if not 1 <= args.repeats <= 10:
        parser.error("--repeats must be 1..10")
    report = benchmark(
        source_head=args.source_head, source_tree=args.source_tree,
        messages=args.messages, repeats=args.repeats,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
