#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only SNAP analysis of exact-bound real-Mesh receipt topology.

This consumes declared topology, not a causal graph. Neither a hash nor a graph
metric authenticates a receipt, reobserves a node, or authorizes an effect.
The existing real-Mesh verifier remains a separate prerequisite in the workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = ROOT / "runtime/toolchains/SNAP.lock.json"
SCHEMA = "qikvrt_snap_mesh_analysis_v1"
MAX_BYTES = 4 * 1024 * 1024
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
NODE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


class AnalysisError(ValueError):
    """Invalid input, stale subject, or unavailable/unbound native backend."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AnalysisError("DUPLICATE_JSON_KEY: " + key)
        result[key] = value
    return result


def _no_number(value: str) -> Any:
    raise AnalysisError("NON_INTEGER_JSON_NUMBER: " + value)


def load_json(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_BYTES:
        raise AnalysisError("INPUT_TOO_LARGE")
    try:
        value = json.loads(raw, object_pairs_hook=_object,
                           parse_float=_no_number, parse_constant=_no_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise AnalysisError("INVALID_JSON") from exc
    if not isinstance(value, dict):
        raise AnalysisError("JSON_OBJECT_REQUIRED")
    return value


def read_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        return load_json(stream.read(MAX_BYTES + 1))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisError(message)


def project(raw: bytes, expected_head: str, expected_tree: str) -> dict[str, Any]:
    """Bind exact receipt bytes and project only declared undirected links."""
    _require(bool(SHA1.fullmatch(expected_head)), "INVALID_EXPECTED_HEAD")
    _require(bool(SHA1.fullmatch(expected_tree)), "INVALID_EXPECTED_TREE")
    receipt = load_json(raw)
    _require(receipt.get("schema") == "qikvrt_real_mesh_execution_receipt_v1",
             "UNSUPPORTED_RECEIPT_SCHEMA")
    _require(receipt.get("source_head") == expected_head and
             receipt.get("source_tree") == expected_tree, "STALE_SUBJECT")
    _require(receipt.get("external_effect") == "NONE", "EXTERNAL_EFFECT_BOUNDARY")
    _require(receipt.get("network_scope") == "LOOPBACK_TCP_ONLY", "NETWORK_SCOPE")
    body = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    _require(receipt.get("receipt_sha256") == digest(canonical(body)),
             "RECEIPT_DIGEST_MISMATCH")
    topology = receipt.get("topology")
    _require(isinstance(topology, dict), "TOPOLOGY_REQUIRED")
    _require(topology.get("schema") == "qikvrt_real_mesh_topology_v1",
             "UNSUPPORTED_TOPOLOGY_SCHEMA")
    _require(receipt.get("topology_sha256") == digest(canonical(topology)),
             "TOPOLOGY_DIGEST_MISMATCH")
    nodes = topology.get("nodes")
    links = topology.get("links")
    _require(isinstance(nodes, list) and 4 <= len(nodes) <= 16, "NODE_LIMIT")
    _require(isinstance(links, list) and len(links) <= 120, "LINK_LIMIT")
    identifiers: list[str] = []
    for node in nodes:
        _require(isinstance(node, dict), "INVALID_NODE")
        name = node.get("node_id")
        _require(isinstance(name, str) and bool(NODE_ID.fullmatch(name)),
                 "INVALID_NODE_ID")
        identifiers.append(name)
    _require(len(set(identifiers)) == len(identifiers), "DUPLICATE_NODE")
    identifiers.sort()
    index = {name: i for i, name in enumerate(identifiers)}
    edges: set[tuple[int, int]] = set()
    for link in links:
        _require(isinstance(link, list) and len(link) == 2 and
                 all(isinstance(name, str) and name in index for name in link),
                 "INVALID_LINK_ENDPOINT")
        edge = tuple(sorted((index[link[0]], index[link[1]])))
        _require(edge[0] != edge[1], "SELF_LINK")
        _require(edge not in edges, "DUPLICATE_LINK")
        edges.add(edge)
    routes = receipt.get("routes")
    _require(isinstance(routes, list) and len(routes) <= 64, "INVALID_ROUTES")
    for route in routes:
        _require(isinstance(route, dict) and
                 isinstance(route.get("observation"), dict), "INVALID_ROUTE")
        obs = route["observation"]
        path = obs.get("path")
        _require(isinstance(path, list) and 2 <= len(path) <= len(nodes) and
                 all(isinstance(n, str) and n in index for n in path),
                 "INVALID_ROUTE_PATH")
        _require(len(set(path)) == len(path), "REPEATED_ROUTE_NODE")
        for left, right in zip(path, path[1:]):
            _require(tuple(sorted((index[left], index[right]))) in edges,
                     "ROUTE_OUTSIDE_TOPOLOGY")
    graph = {"node_ids": identifiers, "edges": [list(e) for e in sorted(edges)]}
    return {
        "source_head": expected_head, "source_tree": expected_tree,
        "input_bytes_sha256": digest(raw),
        "input_receipt_sha256": receipt["receipt_sha256"],
        "topology_sha256": receipt["topology_sha256"],
        "graph_sha256": digest(canonical(graph)), "graph": graph,
        "node_metadata": sorted(nodes, key=lambda n: n["node_id"]),
        "route_count": len(routes),
        "edge_semantics": "DECLARED_UNDIRECTED_TOPOLOGY_LINK_NOT_CAUSAL_PROOF",
        "route_semantics": "DECLARED_PATH_NOT_FRESH_DELIVERY_READBACK",
    }


def encode_graph(graph: dict[str, Any]) -> str:
    return "{} {}\n{}".format(
        len(graph["node_ids"]), len(graph["edges"]),
        "".join(f"{a} {b}\n" for a, b in graph["edges"]))


def native_metrics(binary: pathlib.Path, graph: dict[str, Any]) -> dict[str, Any]:
    try:
        proc = subprocess.run([str(binary.resolve())], input=encode_graph(graph),
                              text=True, capture_output=True, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise AnalysisError("SNAP_BACKEND_UNAVAILABLE_OR_FAILED") from exc
    metrics = load_json(proc.stdout.encode("utf-8"))
    keys = {"nodes", "edges", "components", "max_component_diameter",
            "unreachable_ordered_pairs", "degrees"}
    _require(set(metrics) == keys, "INVALID_BACKEND_FIELDS")
    _require(all(type(metrics[k]) is int for k in keys - {"degrees"}),
             "INVALID_BACKEND_INTEGER")
    n, m = len(graph["node_ids"]), len(graph["edges"])
    _require(metrics["nodes"] == n and metrics["edges"] == m, "BACKEND_GRAPH_MISMATCH")
    degrees = [0] * n
    for a, b in graph["edges"]:
        degrees[a] += 1
        degrees[b] += 1
    _require(isinstance(metrics["degrees"], list) and
             all(type(x) is int for x in metrics["degrees"]) and
             metrics["degrees"] == degrees, "BACKEND_DEGREE_MISMATCH")
    _require(1 <= metrics["components"] <= n and
             0 <= metrics["max_component_diameter"] < n and
             0 <= metrics["unreachable_ordered_pairs"] <= n * (n - 1),
             "INVALID_BACKEND_METRIC_RANGE")
    return metrics


def bound_backend(binary: pathlib.Path) -> dict[str, Any]:
    lock = read_json(LOCK)
    build = read_json(binary.with_suffix(".build.json"))
    _require(build.get("source_commit") == lock["commit"] and
             build.get("source_tree") == lock["tree"], "BACKEND_SOURCE_MISMATCH")
    _require(build.get("binary_sha256") == digest(binary.read_bytes()),
             "BACKEND_BINARY_MISMATCH")
    _require(build.get("bridge_sha256") == digest(
        (ROOT / "tools/qikvrt_snap_mesh.cpp").read_bytes()), "BACKEND_BRIDGE_MISMATCH")
    _require(build.get("lock_sha256") == digest(LOCK.read_bytes()),
             "BACKEND_LOCK_MISMATCH")
    notice = binary.with_suffix(".LICENSE.txt").read_bytes()
    license_blob = hashlib.sha1(b"blob " + str(len(notice)).encode() + b"\0" + notice).hexdigest()
    _require(license_blob == lock["license_blob"], "BACKEND_LICENSE_MISMATCH")
    return build


def analyze(raw: bytes, head: str, tree: str, binary: pathlib.Path) -> dict[str, Any]:
    projection = project(raw, head, tree)
    build = bound_backend(binary)
    # The native binary is mandatory; there is no NetworkX/Python fallback.
    metrics = native_metrics(binary, projection["graph"])
    _require(digest(binary.read_bytes()) == build["binary_sha256"],
             "BACKEND_CHANGED_DURING_ANALYSIS")
    report = {
        "schema": SCHEMA, "state": "ANALYSIS_COMPLETE", "backend_executed": True,
        "backend": "Stanford Network Analysis Platform (C++)",
        "binding": projection, "build": build, "metrics": metrics,
        "adapter_sha256": digest(pathlib.Path(__file__).read_bytes()),
        "external_effect": "NONE", "ordinary_release": False,
        "claims": {"causal_proof": False, "fresh_node_readback": False,
                   "authority_mirror_synchronization": False, "merge": False,
                   "publication": False, "PASS": False, "FINAL_PASS": False,
                   "EFFECT_ACK_DONE": False},
    }
    report["report_sha256"] = digest(canonical(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--backend", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        with args.receipt.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        report = analyze(raw, args.expected_head, args.expected_tree, args.backend)
    except (AnalysisError, OSError, KeyError, TypeError) as exc:
        # stderr only: never overwrite a prior successful report on a failed run.
        print(json.dumps({"schema": SCHEMA, "state": "HOLD",
                          "reason": str(exc), "analysis_complete": False,
                          "external_effect": "NONE", "ordinary_release": False}),
              file=sys.stderr)
        return 2
    encoded = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        # Create-only prevents stale evidence from being silently replaced.
        with args.output.open("x", encoding="utf-8") as out:
            out.write(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
