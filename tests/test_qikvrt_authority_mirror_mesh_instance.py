#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "qikvrt_authority_mirror_mesh_instance.py"
CONTRACT = ROOT / "state" / "mesh" / "QIKVRT_AUTHORITY_MIRROR_MESH_INSTANCE_V1.json"
MONITOR = ROOT / "docs" / "monitor" / "index.html"

SPEC = importlib.util.spec_from_file_location("qikvrt_authority_mirror_mesh_instance", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


AUTHORITY_HEAD = "3cb6273924f3de310e3bd1cd5b827e8e3529220a"
AUTHORITY_TREE = "864b7728c1c52687e4a11668bf0a2ee3fec08365"
MIRROR_HEAD = "25c4df4caf063d0545621f9958941c3cd0dfd5fa"
MIRROR_TREE = "bd421a2624d20804c74eef77647fc52fcdb1feec"
HASH_A = "a" * 64
HASH_B = "b" * 64


def observation(
    *,
    authority_tree: str = AUTHORITY_TREE,
    mirror_tree: str = MIRROR_TREE,
    authority_integrity: dict[str, str] | None = None,
    mirror_integrity: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "schema": MODULE.INPUT_SCHEMA,
        "observation_id": "authority-mirror-observation-2026-08-24T1216Z",
        "observed_at": "2026-08-24T12:16:00Z",
        "authority": {
            "repository": "Goldkelch/qik-vrt",
            "role": "AUTHORITY",
            "ref_name": "main",
            "head_sha": AUTHORITY_HEAD,
            "root_tree_sha": authority_tree,
            "inventory": {"open_issues": 19, "open_pull_requests": 177, "branches": 930},
            "integrity": authority_integrity,
        },
        "mirror": {
            "repository": "ingolf-lohmann/qik-vrt",
            "role": "MIRROR",
            "ref_name": "main",
            "head_sha": MIRROR_HEAD,
            "root_tree_sha": mirror_tree,
            "inventory": {"open_issues": 2, "open_pull_requests": 25, "branches": 433},
            "integrity": mirror_integrity,
        },
    }


class AuthorityMirrorMeshInstanceTests(unittest.TestCase):
    def test_diverged_pair_is_a_mesh_instance_without_a_synthetic_main(self) -> None:
        instance = MODULE.build_mesh_instance(observation())
        relation = instance["relationship"]
        self.assertEqual(instance["mesh_instance_id"], MODULE.MESH_INSTANCE_ID)
        self.assertEqual(relation["state"], "DIVERGED")
        self.assertFalse(relation["same_root_tree_observed"])
        self.assertEqual(relation["canonical_content"]["state"], "NOT_DERIVED")
        self.assertIsNone(relation["canonical_content"]["mesh_main_ref"])
        self.assertEqual(relation["first_deterministic_blocker"], "AUTHORITY_MIRROR_ROOT_TREE_DIFFER")
        self.assertEqual(instance["effect_class"], "OBSERVE_ONLY")
        self.assertFalse(instance["completion_claims"]["authority_mirror_equality_claimed"])
        self.assertFalse(instance["completion_claims"]["merge"])

    def test_mesh_inventory_is_arithmetic_only_and_keeps_gc_boundary(self) -> None:
        instance = MODULE.build_mesh_instance(observation())
        inventory = instance["inventory_aggregation"]
        self.assertEqual(inventory["open_issues"], 21)
        self.assertEqual(inventory["open_pull_requests"], 202)
        self.assertEqual(inventory["branches"], 1363)
        self.assertEqual(inventory["non_main_branch_refs"], 1361)
        self.assertEqual(
            inventory["semantics"],
            "ARITHMETIC_SUM_ONLY_NO_EQUALITY_OR_LIFECYCLE_INFERENCE",
        )
        self.assertFalse(inventory["non_main_ref_is_lifecycle_or_gc_authority"])

    def test_equal_tree_without_pair_integrity_remains_unverified(self) -> None:
        instance = MODULE.build_mesh_instance(
            observation(authority_tree=AUTHORITY_TREE, mirror_tree=AUTHORITY_TREE)
        )
        self.assertEqual(
            instance["relationship"]["state"],
            "TREE_EQUALITY_UNVERIFIED_INTEGRITY",
        )
        self.assertFalse(instance["relationship"]["matching_integrity_pair_observed"])
        self.assertIsNone(instance["relationship"]["canonical_content"]["mesh_main_ref"])

    def test_matching_integrity_still_needs_reciprocal_receipt(self) -> None:
        integrity = {
            "repository_file_manifest_sha256": HASH_A,
            "sha256sums_sha256": HASH_B,
        }
        instance = MODULE.build_mesh_instance(
            observation(
                authority_tree=AUTHORITY_TREE,
                mirror_tree=AUTHORITY_TREE,
                authority_integrity=integrity,
                mirror_integrity=integrity,
            )
        )
        relation = instance["relationship"]
        self.assertEqual(relation["state"], "CONTENT_EQUIVALENT_NOT_RECIPROCAL_RECEIPT_BOUND")
        self.assertTrue(relation["same_root_tree_observed"])
        self.assertTrue(relation["matching_integrity_pair_observed"])
        self.assertEqual(relation["first_deterministic_blocker"], "RECIPROCAL_WHOLE_TREE_RECEIPT_NOT_BOUND")
        self.assertFalse(instance["completion_claims"]["authority_mirror_equality_claimed"])

    def test_full_terminal_view_is_lossless_and_short_view_remains_bound(self) -> None:
        instance = MODULE.build_mesh_instance(observation())
        full = MODULE.terminal_projection(instance, "FULL")
        executive = MODULE.terminal_projection(instance, "EXECUTIVE")
        self.assertEqual(full["full"], instance)
        self.assertEqual(full["canonical_envelope_sha256"], executive["canonical_envelope_sha256"])
        self.assertEqual(executive["executive"]["state"], "DIVERGED")
        self.assertNotIn("nodes", executive)

    def test_rejects_a_non_main_or_wrong_role_node(self) -> None:
        value = observation()
        value["authority"]["ref_name"] = "candidate"
        with self.assertRaisesRegex(MODULE.MeshInstanceError, "ref_name must be main"):
            MODULE.build_mesh_instance(value)
        value = observation()
        value["mirror"]["role"] = "AUTHORITY"
        with self.assertRaisesRegex(MODULE.MeshInstanceError, "MIRROR.role"):
            MODULE.build_mesh_instance(value)

    def test_contract_and_live_monitor_keep_the_same_non_claims(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["instance_id"], MODULE.MESH_INSTANCE_ID)
        self.assertFalse(contract["effect_boundary"]["cross_repository_sync"])
        self.assertFalse(contract["aggregation"]["non_main_ref_is_safe_to_delete"])
        self.assertFalse(contract["completion_claims"]["mesh_canonical_main_derived"])
        monitor = MONITOR.read_text(encoding="utf-8")
        for marker in (
            "QIK-VRT Mesh Authority/Mirror-Instanz",
            "TREE_EQUALITY_UNVERIFIED_INTEGRITY",
            "NICHT_ABGELEITET",
            "NON_MAIN_REF != STALE_REF != ORPHAN_REF != SAFE_TO_DELETE",
            "method: \"GET\"",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, monitor)


if __name__ == "__main__":
    unittest.main(verbosity=2)
