# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import pathlib
import unittest

from tools import qikvrt_denk_mengenlehre as model


ROOT = pathlib.Path(__file__).resolve().parents[1]


class DenkMengenlehreContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = model._load_policy()

    def test_power_set_contains_exactly_all_64_subsets(self) -> None:
        document = model.build_power_set(self.policy)
        subsets = document["subsets"]
        observed = {
            tuple(entry["passed_gate_ids"])
            for entry in subsets
        }
        self.assertEqual(document["cardinality"], 64)
        self.assertEqual(len(subsets), 64)
        self.assertEqual(len(observed), 64)
        self.assertIn((), observed)
        self.assertIn(("G1", "G2", "G3", "G4", "G5", "G6"), observed)

    def test_batch_pass_is_conjunction_not_union(self) -> None:
        gates = [
            {"id": f"G{index}", "pass": True}
            for index in range(1, 7)
        ]
        self.assertTrue(model.conjunctive_batch_pass(gates))
        gates[2]["pass"] = False
        self.assertFalse(model.conjunctive_batch_pass(gates))
        self.assertFalse(model.conjunctive_batch_pass(gates[:5]))

    def test_empty_set_is_initial_state_not_mutated_container(self) -> None:
        set_model = self.policy["set_model"]
        self.assertEqual(set_model["initial_evidence"], [])
        self.assertEqual(
            set_model["evidence_transition"],
            "E_(i+1) = E_i union Evidence(G_(i+1))",
        )

    def test_self_reference_is_typed_and_not_self_membership(self) -> None:
        reference = self.policy["self_reference"]
        self.assertEqual(reference["relation"], "descriptor_references_scope")
        self.assertEqual(reference["referent_scope_id"], model.SCOPE_ID)
        self.assertIs(reference["system_member_of_itself"], False)
        bound, descriptor = model._context_descriptor(self.policy)
        self.assertTrue(bound)
        self.assertIsNotNone(descriptor)

    def test_relative_complement_has_explicit_finite_universe(self) -> None:
        universe = set(self.policy["candidate_input_universe"])
        allowed = set(self.policy["allowed_inputs"])
        excluded = set(self.policy["excluded_inputs"])
        loaded = set(self.policy["loaded_inputs"])
        self.assertEqual(excluded, universe - allowed)
        self.assertFalse(allowed & excluded)
        self.assertFalse(loaded & excluded)
        self.assertLessEqual(loaded, allowed)

    def test_scope_does_not_reuse_content_batch_or_artifact_identity(self) -> None:
        distinct = set(self.policy["distinct_from"])
        self.assertEqual(
            self.policy["qualified_batch_alias"],
            "DENK-MENGENLEHRE-BATCH-002",
        )
        self.assertIn("CONTENT-DISPOSITION-BATCH-002", distinct)
        self.assertIn("github-actions-artifact-8696689772", distinct)

    def test_json_loader_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(model.ContractError):
            json.loads(
                '{"scope_id":"a","scope_id":"b"}',
                object_pairs_hook=model._strict_object,
            )

    def test_all_declared_artifact_paths_are_normalized(self) -> None:
        for name, value in self.policy["artifacts"].items():
            relative = model._relative_path(value, name)
            self.assertFalse(relative.is_absolute())
            self.assertNotIn("..", relative.parts)
            if name != "power_set":
                self.assertTrue((ROOT / relative).is_file(), name)


if __name__ == "__main__":
    unittest.main()
