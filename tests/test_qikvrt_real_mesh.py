#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import json
import pathlib
import socket
import tempfile
import unittest

from tools import qikvrt_real_mesh as mesh

SOURCE_HEAD = "a" * 40
SOURCE_TREE = "b" * 40


def unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class RealMeshPureContractTests(unittest.TestCase):
    def synthetic_topology(self) -> dict[str, object]:
        nodes = []
        for index, (pair_id, role, repository) in enumerate(
            (
                ("pair-a", "AUTHORITY", "Goldkelch/qik-vrt"),
                ("pair-a", "MIRROR", "ingolf-lohmann/qik-vrt"),
                ("pair-b", "AUTHORITY", "Goldkelch/qik-vrt"),
                ("pair-b", "MIRROR", "ingolf-lohmann/qik-vrt"),
            ),
            start=1,
        ):
            nodes.append(
                {
                    "node_id": f"node-{index}",
                    "pair_id": pair_id,
                    "role": role,
                    "repository": repository,
                    "instance_id": f"instance-{index}",
                    "root_tree_sha": ("a" if role == "AUTHORITY" else "b") * 40,
                    "host": "127.0.0.1",
                    "port": 20000 + index,
                }
            )
        return {
            "schema": mesh.TOPOLOGY_SCHEMA,
            "mesh_id": mesh.MESH_ID,
            "network_scope": mesh.NETWORK_SCOPE,
            "nodes": nodes,
            "links": [
                ["node-1", "node-2"],
                ["node-1", "node-3"],
                ["node-2", "node-3"],
                ["node-2", "node-4"],
                ["node-3", "node-4"],
            ],
        }

    def test_real_mesh_requires_two_complete_authority_mirror_pairs(self) -> None:
        topology = self.synthetic_topology()
        for node in topology["nodes"]:
            node["pair_id"] = "only-pair"
        with self.assertRaisesRegex(
            mesh.MeshRuntimeError,
            "REAL_MESH_REQUIRES_AT_LEAST_TWO_AUTHORITY_MIRROR_PAIRS",
        ):
            mesh.normalize_topology(topology)

    def test_real_mesh_requires_connected_cyclic_peer_graph(self) -> None:
        topology = self.synthetic_topology()
        topology["links"] = [
            ["node-1", "node-2"],
            ["node-2", "node-3"],
            ["node-3", "node-4"],
            ["node-1", "node-2"],
        ]
        with self.assertRaises(mesh.MeshRuntimeError):
            mesh.normalize_topology(topology)

    def test_route_must_cross_pairs_and_follow_declared_links(self) -> None:
        topology = mesh.normalize_topology(self.synthetic_topology())
        with self.assertRaises(mesh.MeshRuntimeError):
            mesh.build_message(
                topology,
                ["node-1", "node-2", "node-1", "node-2"],
                message_id="bad-route",
                nonce="BAD-ROUTE",
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
            )

    def test_explicit_ambiguity_is_a_deterministic_hold_not_an_admission(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qikvrt-real-mesh-hold-") as directory:
            with mesh.MeshHarness(pathlib.Path(directory), SOURCE_TREE) as harness:
                assert harness.topology is not None
                route = ["pair-a-authority", "pair-a-mirror", "pair-b-mirror", "pair-b-authority"]
                message = mesh.build_message(
                    harness.topology, route, message_id="explicit-hold-0001",
                    nonce="EXPLICIT-HOLD-NONCE", source_head=SOURCE_HEAD,
                    source_tree=SOURCE_TREE, ambiguity_present=True,
                )
                first = mesh.node_by_id(harness.topology, route[0])
                response = mesh.send_message(first["host"], first["port"], message)
                self.assertEqual(response["effect_state"], "EFFECT_ACK_CONTINUE")
                self.assertEqual(response["reason"], "EXPLICIT_AMBIGUITY_HOLD")
                self.assertFalse(response["ordinary_release"])


class RealMeshNetworkTests(unittest.TestCase):
    def test_four_process_two_pair_mesh_executes_two_routes_and_restart_replay(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qikvrt-real-mesh-test-") as directory:
            receipt = mesh.run_demo(
                pathlib.Path(directory),
                source_head=SOURCE_HEAD,
                source_tree=SOURCE_TREE,
            )
        self.assertEqual(receipt["schema"], mesh.EXECUTION_RECEIPT_SCHEMA)
        self.assertEqual(receipt["pair_count"], 2)
        self.assertEqual(receipt["node_process_count"], 4)
        self.assertEqual(receipt["transport"], "TCP")
        self.assertEqual(receipt["network_scope"], mesh.NETWORK_SCOPE)
        self.assertTrue(receipt["redundant_path_observed"])
        self.assertTrue(receipt["restart_replay"]["observed"])
        self.assertTrue(receipt["restart_replay"]["same_terminal_receipt"])
        self.assertTrue(receipt["restart_replay"]["ledger_record_count_unchanged"])
        self.assertEqual(len(receipt["routes"]), 2)
        for route in receipt["routes"]:
            with self.subTest(path=route["observation"]["path"]):
                self.assertTrue(route["observation"]["complete_route_reobserved"])
                self.assertEqual(len(route["observation"]["node_observations"]), 4)
                self.assertEqual(route["bounded_effect_ack"]["state"], "EFFECT_ACK_DONE")
                self.assertTrue(route["bounded_effect_ack"]["ordinary_release"])
        claims = receipt["completion_claims"]
        self.assertTrue(claims["real_multi_pair_mesh_runtime_executed"])
        self.assertTrue(claims["independent_tcp_node_processes_observed"])
        self.assertTrue(claims["bounded_loopback_effect_ack_done"])
        for false_claim in (
            "general_effect_ack_done",
            "general_internet_reachability",
            "production_deployment",
            "physical_hardware_execution",
            "authority_mirror_synchronization",
            "authority_mirror_equality_claimed",
            "merge",
            "PASS",
            "FINAL_PASS",
        ):
            self.assertFalse(claims[false_claim])
        self.assertEqual(receipt["effect_ack_scope"], mesh.EFFECT_ACK_SCOPE)
        self.assertEqual(receipt["external_effect"], "NONE")
        self.assertTrue(all(pair["state"] == "DIVERGED" for pair in receipt["pair_states"]))
        projection = dict(receipt)
        stored_hash = projection.pop("receipt_sha256")
        self.assertEqual(stored_hash, mesh.canonical_sha256(projection))

    def test_tamper_rebinding_and_partition_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="qikvrt-real-mesh-negative-") as directory:
            with mesh.MeshHarness(pathlib.Path(directory), SOURCE_TREE) as harness:
                assert harness.topology is not None
                route = [
                    "pair-a-authority",
                    "pair-a-mirror",
                    "pair-b-mirror",
                    "pair-b-authority",
                ]
                message = mesh.build_message(
                    harness.topology,
                    route,
                    message_id="negative-route-0001",
                    nonce="NEGATIVE-NONCE-0001",
                    source_head=SOURCE_HEAD,
                    source_tree=SOURCE_TREE,
                )
                first = mesh.node_by_id(harness.topology, route[0])

                tampered = copy.deepcopy(message)
                tampered["payload"]["nonce"] = "TAMPERED"
                tamper_response = mesh.send_message(first["host"], first["port"], tampered)
                self.assertEqual(tamper_response["effect_state"], "EFFECT_ACK_BLOCK")
                self.assertIn("payload_sha256 mismatch", tamper_response["reason"])

                terminal = harness.route_message(message)
                self.assertEqual(terminal["schema"], mesh.TERMINAL_RECEIPT_SCHEMA)
                rebound = mesh.build_message(
                    harness.topology,
                    route,
                    message_id=message["message_id"],
                    nonce="DIFFERENT-BYTES",
                    source_head=SOURCE_HEAD,
                    source_tree=SOURCE_TREE,
                )
                rebound_response = mesh.send_message(first["host"], first["port"], rebound)
                self.assertEqual(rebound_response["effect_state"], "EFFECT_ACK_BLOCK")
                self.assertEqual(
                    rebound_response["reason"],
                    "MESSAGE_ID_REBOUND_TO_DIFFERENT_BYTES",
                )

                partitioned_topology = copy.deepcopy(harness.topology)
                for node in partitioned_topology["nodes"]:
                    if node["node_id"] == route[1]:
                        node["port"] = unused_loopback_port()
                partitioned_topology = mesh.normalize_topology(partitioned_topology)
                partitioned = mesh.build_message(
                    partitioned_topology,
                    route,
                    message_id="partition-route-0001",
                    nonce="PARTITION-NONCE-0001",
                    source_head=SOURCE_HEAD,
                    source_tree=SOURCE_TREE,
                )
                partition_response = mesh.send_message(first["host"], first["port"], partitioned)
                self.assertEqual(partition_response["effect_state"], "EFFECT_ACK_CONTINUE")
                self.assertFalse(partition_response["ordinary_release"])
                self.assertTrue(partition_response["retryable"])
                self.assertIn("NEXT_HOP_UNREACHABLE", partition_response["reason"])


class RealMeshRepositoryContractTests(unittest.TestCase):
    def test_committed_contract_and_workflow_preserve_runtime_boundaries(self) -> None:
        root = pathlib.Path(__file__).resolve().parents[1]
        contract = json.loads(
            (root / "state" / "mesh" / "QIKVRT_REAL_MESH_V1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["mesh_id"], mesh.MESH_ID)
        self.assertEqual(contract["minimum_topology"]["pair_count"], 2)
        self.assertEqual(contract["minimum_topology"]["node_process_count"], 4)
        self.assertEqual(contract["transport"]["network_scope"], mesh.NETWORK_SCOPE)
        self.assertFalse(contract["effect_boundary"]["general_effect_ack_done"])
        self.assertFalse(contract["effect_boundary"]["authority_mirror_synchronization"])
        self.assertEqual(contract["deterministic_admission"]["message_field"], "ambiguity_present")
        self.assertFalse(contract["deterministic_admission"]["sampling"])
        workflow = (
            root / ".github" / "workflows" / "qikvrt_real_mesh.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertIn("QIKVRT real multi-pair Mesh runtime", workflow)
        self.assertIn("tools/qikvrt_real_mesh.py demo", workflow)
        self.assertIn("127.0.0.1", (root / "docs" / "architecture" / "QIKVRT_REAL_MESH_V1.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
