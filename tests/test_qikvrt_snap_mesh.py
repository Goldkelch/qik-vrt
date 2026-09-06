# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Adapter tests; native tests explicitly require a real SNAP-built executable."""
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_snap_mesh as snap

HEAD = "a" * 40
TREE = "b" * 40


def fixture():
    topology = {"schema": "qikvrt_real_mesh_topology_v1",
                "mesh_id": "QIKVRT_REAL_MULTI_PAIR_MESH_V1",
                "network_scope": "LOOPBACK_TCP_ONLY",
                "nodes": [{"node_id": name, "root_tree_sha": str(i) * 40}
                          for i, name in enumerate(["a", "b", "c", "d"])],
                "links": [["a", "b"], ["b", "c"], ["c", "d"], ["d", "a"]]}
    value = {"schema": "qikvrt_real_mesh_execution_receipt_v1",
             "source_head": HEAD, "source_tree": TREE,
             "network_scope": "LOOPBACK_TCP_ONLY", "external_effect": "NONE",
             "topology": topology, "routes": [{"observation": {"path": ["a", "b", "c", "d"]}}]}
    return seal(value)


def seal(value):
    value["topology_sha256"] = snap.digest(snap.canonical(value["topology"]))
    value.pop("receipt_sha256", None)
    value["receipt_sha256"] = snap.digest(snap.canonical(value))
    return value


class AdapterTests(unittest.TestCase):
    def project(self, value):
        return snap.project(snap.canonical(value), HEAD, TREE)

    def rejects(self, value, reason):
        with self.assertRaisesRegex(snap.AnalysisError, reason):
            self.project(seal(value))

    def test_exact_binding_and_graph(self):
        p = self.project(fixture())
        self.assertEqual(p["graph"], {"node_ids": ["a", "b", "c", "d"],
                                      "edges": [[0, 1], [0, 3], [1, 2], [2, 3]]})
        self.assertEqual(p["source_head"], HEAD)
        self.assertIn("NOT_CAUSAL_PROOF", p["edge_semantics"])
        self.assertEqual(len({n["root_tree_sha"] for n in p["node_metadata"]}), 4)

    def test_projection_deterministic_not_raw_hash(self):
        first = fixture()
        second = copy.deepcopy(first)
        second["topology"]["nodes"].reverse()
        second["topology"]["links"].reverse()
        a, b = self.project(first), self.project(seal(second))
        self.assertEqual(a["graph_sha256"], b["graph_sha256"])
        self.assertNotEqual(a["input_bytes_sha256"], b["input_bytes_sha256"])

    def test_raw_bytes_not_only_json_bound(self):
        a = snap.project(json.dumps(fixture(), indent=2).encode(), HEAD, TREE)
        b = self.project(fixture())
        self.assertNotEqual(a["input_bytes_sha256"], b["input_bytes_sha256"])
        self.assertEqual(a["input_receipt_sha256"], b["input_receipt_sha256"])

    def test_stale_head(self):
        value = fixture(); value["source_head"] = "c" * 40
        self.rejects(value, "STALE_SUBJECT")

    def test_stale_tree(self):
        value = fixture(); value["source_tree"] = "c" * 40
        self.rejects(value, "STALE_SUBJECT")

    def test_digest_tampering(self):
        value = fixture(); value["receipt_sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(snap.AnalysisError, "RECEIPT_DIGEST_MISMATCH"):
            self.project(value)

    def test_topology_digest(self):
        value = fixture(); value["topology_sha256"] = "sha256:" + "0" * 64
        value.pop("receipt_sha256")
        value["receipt_sha256"] = snap.digest(snap.canonical(value))
        with self.assertRaisesRegex(snap.AnalysisError, "TOPOLOGY_DIGEST_MISMATCH"):
            self.project(value)

    def test_duplicate_nodes(self):
        value = fixture(); value["topology"]["nodes"][1]["node_id"] = "a"
        self.rejects(value, "DUPLICATE_NODE")

    def test_unknown_node(self):
        value = fixture(); value["topology"]["links"][0][0] = "absent"
        self.rejects(value, "INVALID_LINK_ENDPOINT")

    def test_self_link(self):
        value = fixture(); value["topology"]["links"][0] = ["a", "a"]
        self.rejects(value, "SELF_LINK")

    def test_reversed_duplicate_link(self):
        value = fixture(); value["topology"]["links"].append(["b", "a"])
        self.rejects(value, "DUPLICATE_LINK")

    def test_bool_node_id(self):
        value = fixture(); value["topology"]["nodes"][0]["node_id"] = True
        self.rejects(value, "INVALID_NODE_ID")

    def test_route_missing_edge(self):
        value = fixture(); value["routes"][0]["observation"]["path"] = ["a", "c"]
        self.rejects(value, "ROUTE_OUTSIDE_TOPOLOGY")

    def test_route_repeats(self):
        value = fixture(); value["routes"][0]["observation"]["path"] = ["a", "b", "a"]
        self.rejects(value, "REPEATED_ROUTE_NODE")

    def test_transport_and_effect_are_separate(self):
        value = fixture(); value["external_effect"] = "EFFECT_ACK_DONE"
        self.rejects(value, "EXTERNAL_EFFECT_BOUNDARY")

    def test_unsupported_schema(self):
        value = fixture(); value["schema"] = "unknown"
        self.rejects(value, "UNSUPPORTED_RECEIPT_SCHEMA")

    def test_duplicate_json_keys(self):
        with self.assertRaisesRegex(snap.AnalysisError, "DUPLICATE_JSON_KEY"):
            snap.load_json(b'{"x": 1, "x": 2}')

    def test_float_nan_infinity(self):
        for raw in (b'{"x":1.5}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(snap.AnalysisError):
                snap.load_json(raw)

    def test_input_size(self):
        with self.assertRaisesRegex(snap.AnalysisError, "INPUT_TOO_LARGE"):
            snap.load_json(b" " * (snap.MAX_BYTES + 1))

    def test_no_silent_backend_fallback(self):
        with self.assertRaisesRegex(snap.AnalysisError, "SNAP_BACKEND_UNAVAILABLE"):
            snap.native_metrics(pathlib.Path("/nonexistent/qikvrt-snap"),
                                self.project(fixture())["graph"])

    def test_cli_hold_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            receipt = root / "receipt.json"; receipt.write_bytes(snap.canonical(fixture()))
            output = root / "report.json"; output.write_text("previous evidence\n")
            run = subprocess.run([sys.executable, str(snap.ROOT / "tools/qikvrt_snap_mesh.py"),
                                  "--receipt", str(receipt), "--expected-head", HEAD,
                                  "--expected-tree", TREE, "--backend", str(root / "missing"),
                                  "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, "")
            self.assertEqual(json.loads(run.stderr)["state"], "HOLD")
            self.assertEqual(output.read_text(), "previous evidence\n")

    def test_wrong_dependency_pin_never_invokes_compiler(self):
        from tools import qikvrt_build_snap as builder
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(builder, "git", return_value="0" * 40), \
                 mock.patch.object(builder.shutil, "which") as compiler:
                with self.assertRaisesRegex(snap.AnalysisError, "SNAP_SOURCE_NOT_EXACT_CLEAN_PIN"):
                    builder.build(pathlib.Path(tmp) / "source", pathlib.Path(tmp) / "output")
                compiler.assert_not_called()

    def test_existing_workflow_requires_native_backend(self):
        workflow = (snap.ROOT / ".github/workflows/qikvrt_real_mesh.yml").read_text()
        self.assertIn("contents: read", workflow)
        self.assertIn("QIKVRT_SNAP_BACKEND=", workflow)
        self.assertIn("test -x .qikvrt/real-mesh/snap/qikvrt-snap", workflow)
        self.assertIn("qikvrt_real_mesh_system_verification.py verify", workflow)
        self.assertIn("tools/qikvrt_integrity.py verify", workflow)
        self.assertNotIn("continue-on-error", workflow)
        self.assertNotIn("schedule:", workflow)

    def test_mocked_output_is_only_a_protocol_test(self):
        graph = self.project(fixture())["graph"]
        response = {"nodes": 4, "edges": 4, "components": 1,
                    "max_component_diameter": 2, "unreachable_ordered_pairs": 0,
                    "degrees": [2, 2, 2, 2]}
        with mock.patch.object(snap.subprocess, "run", return_value=
                               subprocess.CompletedProcess([], 0, json.dumps(response), "")):
            self.assertEqual(snap.native_metrics(pathlib.Path("protocol-test-double"), graph), response)
        response["degrees"] = [True, 2, 2, 2]
        with mock.patch.object(snap.subprocess, "run", return_value=
                               subprocess.CompletedProcess([], 0, json.dumps(response), "")):
            with self.assertRaisesRegex(snap.AnalysisError, "BACKEND_DEGREE_MISMATCH"):
                snap.native_metrics(pathlib.Path("protocol-test-double"), graph)


@unittest.skipUnless(os.environ.get("QIKVRT_SNAP_BACKEND"),
                     "native SNAP backend not provisioned; NOT execution evidence")
class NativeTests(unittest.TestCase):
    def test_real_snap_cycle(self):
        binary = pathlib.Path(os.environ["QIKVRT_SNAP_BACKEND"])
        report = snap.analyze(snap.canonical(fixture()), HEAD, TREE, binary)
        self.assertTrue(report["backend_executed"])
        self.assertEqual(report["metrics"]["components"], 1)
        self.assertEqual(report["metrics"]["max_component_diameter"], 2)
        self.assertFalse(any(report["claims"].values()))

    def test_real_snap_isolates(self):
        graph = {"node_ids": ["a", "b", "isolated"], "edges": [[0, 1]]}
        metrics = snap.native_metrics(pathlib.Path(os.environ["QIKVRT_SNAP_BACKEND"]), graph)
        self.assertEqual(metrics["components"], 2)
        self.assertEqual(metrics["unreachable_ordered_pairs"], 4)
        self.assertEqual(metrics["degrees"], [1, 1, 0])


if __name__ == "__main__":
    unittest.main()
