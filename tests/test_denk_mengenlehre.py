# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import unittest
from unittest import mock

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

    def test_exact_checkout_accepts_detached_head_but_not_dirty_bytes(self) -> None:
        commit = "1" * 40
        self.assertTrue(model.exact_checkout_bound(commit, ""))
        self.assertFalse(model.exact_checkout_bound(commit, " M file"))
        self.assertFalse(model.exact_checkout_bound("HEAD", ""))

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

    def test_poster_is_exact_visual_evidence_and_not_proof(self) -> None:
        poster = self.policy["visual_evidence"]["poster"]
        path = ROOT / poster["path"]
        data = path.read_bytes()
        self.assertEqual(len(data), poster["bytes"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), poster["sha256"])
        self.assertEqual(model.git_blob_sha1(data), poster["git_blob_sha1"])
        self.assertEqual(
            model.jpeg_dimensions(data),
            (poster["pixel_width"], poster["pixel_height"]),
        )
        self.assertEqual(poster["media_type"], "image/jpeg")
        self.assertEqual(poster["role"], "EXPLANATORY_VISUALIZATION")
        self.assertEqual(
            poster["generation_method"],
            "NOT_ESTABLISHED_BY_REPOSITORY_EVIDENCE",
        )
        self.assertEqual(
            poster["third_party_material_status"],
            "NOT_ESTABLISHED_BY_REPOSITORY_EVIDENCE",
        )
        self.assertIs(poster["embedded_rights_metadata_present"], False)
        self.assertIs(poster["source_bytes_preserved"], True)
        self.assertIs(poster["formal_proof"], False)
        context = model._load_json(model.CONTEXT_PATH)
        descriptor = context["reasoning_models"][model.SCOPE_ID]
        self.assertEqual(descriptor["visual_evidence"], [poster["path"]])
        self.assertIn(poster["path"], context["required_read_order"])

    def test_poster_contract_rejects_digest_drift(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["visual_evidence"]["poster"]["sha256"] = "0" * 64
        poster_path = model._relative_path(
            policy["artifacts"]["poster"],
            "poster",
        )
        record = model._file_record(poster_path)
        bound, _ = model._poster_contract(policy, policy["artifacts"], record)
        self.assertFalse(bound)

    def test_context_descriptor_rejects_visual_reference_drift(self) -> None:
        context = model._load_json(model.CONTEXT_PATH)
        drifted = copy.deepcopy(context)
        drifted["reasoning_models"][model.SCOPE_ID]["visual_evidence"] = [
            "docs/axiome/not-the-canonical-poster.jpg"
        ]
        with mock.patch.object(model, "_load_json", return_value=drifted):
            bound, _ = model._context_descriptor(self.policy)
        self.assertFalse(bound)

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
