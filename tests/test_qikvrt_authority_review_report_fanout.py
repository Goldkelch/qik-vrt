# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Static contract checks for the finite Authority review-report fan-out."""
from __future__ import annotations

import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_authority_review_report_fanout.yml"
CODEC_POLICY = ROOT / "state/mesh/QIKVRT_MESH_NONPOLLING_QUADRATIC_CODEC_V1.json"
DOCUMENTATION = ROOT / "docs/architecture/QIKVRT_AUTHORITY_REVIEW_REPORT_FANOUT_EPOCH_V1.md"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class AuthorityReviewReportFanoutEpochTests(unittest.TestCase):
    def test_fanout_freezes_a_finite_quadratic_epoch_before_dispatch(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        policy = json.loads(CODEC_POLICY.read_text(encoding="utf-8"))

        self.assertEqual(policy["schema"], "qikvrt_mesh_nonpolling_quadratic_codec_v1")
        self.assertEqual(policy["quadratic_scaling"]["lane_count"], "N*N")
        self.assertTrue(policy["quadratic_scaling"]["finite_generic_required"])
        self.assertEqual(policy["canonical_mapping"]["lane_index"], "row*N+column")
        self.assertIn("MESH_EPOCH_POLICY_PATH: state/mesh/QIKVRT_MESH_NONPOLLING_QUADRATIC_CODEC_V1.json", workflow)
        self.assertIn('MAX_ACTIVE_MESH_NODES: "64"', workflow)
        self.assertIn("Materialize frozen active Registry Mesh epoch", workflow)
        self.assertIn("qikvrt_authority_review_mesh_epoch_v1", workflow)
        self.assertIn('"registry_node_count"', workflow)
        self.assertIn('"node_count"', workflow)
        self.assertIn('"maximum_node_count"', workflow)
        self.assertIn('"row_major_lane_ids"', workflow)
        self.assertIn('"lane_index_rule": "row*N+column"', workflow)
        self.assertIn("Registry node_count exceeds the reviewed finite bound", workflow)
        self.assertIn("active Registry node count is outside the reviewed finite bound", workflow)
        self.assertIn("Registry has duplicate active node repositories", workflow)
        self.assertIn("Registry has duplicate active node GUIDs", workflow)
        self.assertNotIn("sort -u > /tmp/active-registry-nodes.txt", workflow)

        reobserve = workflow.index("Reobserve frozen Mesh epoch immediately before dispatch")
        dispatch = workflow.index("Dispatch exact report to every frozen Registry node")
        self.assertLess(reobserve, dispatch)
        self.assertIn("repos/$REPOSITORY/commits/main", workflow)
        self.assertIn("contents/registry/NODEMESH_INDEX.json?ref=main", workflow)
        self.assertIn("Registry drift or Authority main drift observed before dispatch", workflow)
        self.assertIn("EPOCH_FROZEN_FOR_FINITE_DISPATCH", workflow)

    def test_per_target_idempotency_is_bound_to_epoch_source_and_target(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("qikvrt_authority_review_report_delivery_idempotency_v1", workflow)
        self.assertIn('"epoch_sha256": epoch_sha256', workflow)
        self.assertIn('"source_head_sha": source_head', workflow)
        self.assertIn('"target_repository": repository', workflow)
        self.assertIn('"target_guid": guid', workflow)
        self.assertIn('"target_index": index', workflow)
        self.assertIn('"target_self_lane_id": self_lane_id', workflow)
        self.assertIn('binding["idempotency_key"] = hashlib.sha256(canonical(binding)).hexdigest()', workflow)
        self.assertIn("per-target delivery idempotency binding is ambiguous", workflow)
        self.assertIn("qikvrt_authority_review_report_fanout_delivery_v2", workflow)
        self.assertIn("/tmp/authority-review-delivery-plan.jsonl", workflow)
        self.assertNotIn("sleep ", workflow)
        self.assertNotIn("while :", workflow)
        self.assertNotIn("schedule:", workflow)

    def test_canonical_epoch_and_delivery_binding_are_stable(self) -> None:
        nodes = [
            {"guid": "22222222-2222-2222-2222-222222222222", "repository": "z/node"},
            {"guid": "11111111-1111-1111-1111-111111111111", "repository": "a/node"},
        ]
        ordered = sorted(nodes, key=lambda item: (item["repository"], item["guid"]))
        for index, node in enumerate(ordered):
            node["index"] = index
        count = len(ordered)
        lanes = [
            f"qikvrt-mesh-lane-v1/{row:04d}/{column:04d}/{source['guid']}/{target['guid']}"
            for row, source in enumerate(ordered)
            for column, target in enumerate(ordered)
        ]
        self.assertEqual(count, 2)
        self.assertEqual(len(lanes), count * count)
        self.assertEqual(lanes[0], "qikvrt-mesh-lane-v1/0000/0000/11111111-1111-1111-1111-111111111111/11111111-1111-1111-1111-111111111111")
        self.assertEqual(lanes[1], "qikvrt-mesh-lane-v1/0000/0001/11111111-1111-1111-1111-111111111111/22222222-2222-2222-2222-222222222222")

        epoch = {
            "schema": "qikvrt_authority_review_mesh_epoch_v1",
            "node_count": count,
            "lane_count": len(lanes),
            "ordered_active_nodes": ordered,
            "row_major_lane_ids": lanes,
        }
        epoch_hash = hashlib.sha256(canonical(epoch)).hexdigest()
        target = ordered[1]
        binding = {
            "schema": "qikvrt_authority_review_report_delivery_idempotency_v1",
            "epoch_sha256": epoch_hash,
            "source_head_sha": "a" * 40,
            "target_repository": target["repository"],
            "target_guid": target["guid"],
            "target_index": target["index"],
            "target_self_lane_id": lanes[target["index"] * count + target["index"]],
            "event_type": "qikvrt_authority_review_report_v1",
        }
        first = hashlib.sha256(canonical(binding)).hexdigest()
        self.assertEqual(first, hashlib.sha256(canonical(dict(binding))).hexdigest())
        changed_target = dict(binding)
        changed_target["target_repository"] = "other/node"
        self.assertNotEqual(first, hashlib.sha256(canonical(changed_target)).hexdigest())
        changed_head = dict(binding)
        changed_head["source_head_sha"] = "b" * 40
        self.assertNotEqual(first, hashlib.sha256(canonical(changed_head)).hexdigest())
        changed_epoch = dict(binding)
        changed_epoch["epoch_sha256"] = "c" * 64
        self.assertNotEqual(first, hashlib.sha256(canonical(changed_epoch)).hexdigest())

    def test_documentation_keeps_the_transport_and_effect_boundaries(self) -> None:
        documentation = DOCUMENTATION.read_text(encoding="utf-8")
        self.assertIn("`N*N`", documentation)
        self.assertIn("`row*N+column`", documentation)
        self.assertIn("`MAX_ACTIVE_MESH_NODES=64`", documentation)
        self.assertIn("Registry drift", documentation)
        self.assertIn("idempotency", documentation.casefold())
        self.assertIn("not a target receipt", documentation)
        self.assertIn("`EFFECT_ACK_DONE`", documentation)
        self.assertIn("no polling", documentation.casefold())


if __name__ == "__main__":
    unittest.main()
