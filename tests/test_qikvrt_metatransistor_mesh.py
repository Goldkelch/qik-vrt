# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import copy
import unittest

from tools.qikvrt_metatransistor_mesh import (
    FANOUT,
    GATE_NAMES,
    RETIREMENT_DEPTH,
    classify_gate_set,
    derealize,
    fixed_point_alu,
    logical_node_count,
    manifest_children,
    materialize_mesh,
    retirement_prepare_receipt,
    root_node,
)


class MetatransistorMeshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.subject = {
            "repository": "Goldkelch/qik-vrt",
            "kind": "pull_request",
            "number": 992,
            "head_sha": "c" * 40,
        }
        self.payload = {"kind": "DATA", "value": "universell gebunden"}

    def test_every_authority_manifests_exactly_eight_children(self) -> None:
        root = root_node(self.subject)
        children = manifest_children(root, self.payload)
        self.assertEqual(FANOUT, len(children))
        self.assertEqual(list(range(FANOUT)), [child["slot"] for child in children])
        self.assertTrue(all(child["authority_node_id"] == root["node_id"] for child in children))
        self.assertTrue(all(child["role"] == "MIRROR_AUTHORITY" for child in children))
        self.assertTrue(all(child["child_authority_contract"]["child_count"] == FANOUT for child in children))
        self.assertEqual([0, 7], [child["slot"] for child in children if child["terminal"]])
        self.assertTrue(all(child["monitor"] for child in children))

    def test_mirror_node_becomes_authority_for_its_own_eight_children(self) -> None:
        root = root_node(self.subject)
        first = manifest_children(root, self.payload)[3]
        second = manifest_children(first, self.payload)
        self.assertEqual(FANOUT, len(second))
        self.assertTrue(all(child["authority_node_id"] == first["node_id"] for child in second))
        self.assertTrue(all(child["depth"] == 2 for child in second))
        self.assertEqual([3, 0], second[0]["path"])
        self.assertEqual([3, 7], second[-1]["path"])

    def test_lossless_manifestation_and_derealization(self) -> None:
        root = root_node(self.subject)
        children = manifest_children(root, self.payload)
        receipt = derealize(root, children)
        self.assertTrue(receipt["lossless"])
        self.assertEqual(self.payload, receipt["payload"])
        self.assertEqual(children[0]["payload_sha256"], receipt["payload_sha256"])
        self.assertEqual(FANOUT, len(receipt["child_state_sha256"]))

    def test_tampered_child_cannot_derealize(self) -> None:
        root = root_node(self.subject)
        children = manifest_children(root, self.payload)
        tampered = copy.deepcopy(children)
        tampered[4]["payload"]["value"] = "changed"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            derealize(root, tampered)

    def test_materialized_depth_two_has_seventy_three_nodes(self) -> None:
        projection = materialize_mesh(self.subject, self.payload, materialized_depth=2)
        self.assertEqual(73, projection["materialized_node_count"])
        self.assertEqual(
            153_391_689,
            projection["logical_node_count_at_retirement_depth"],
        )
        self.assertEqual(73, logical_node_count(2))
        self.assertFalse(projection["polling"])
        self.assertEqual("KubiKAva", projection["framework"])

    def test_fixed_point_addition_is_exact(self) -> None:
        # Q8.8: 1.5 + 0.5 = 2.0
        receipt = fixed_point_alu("ADD", 384, 128, bits=16, fractional_bits=8)
        self.assertEqual("CONTINUE", receipt["state"])
        self.assertEqual(512, receipt["result_raw"])
        self.assertEqual("2", receipt["result_decimal"])
        self.assertEqual(0, receipt["discarded_product_remainder_raw"])

    def test_fixed_point_mac_preserves_explicit_rounding_receipt(self) -> None:
        # Q8.8: 1.5 * 0.5 + 0.25 = 1.0
        receipt = fixed_point_alu(
            "MAC",
            384,
            128,
            accumulator_raw=64,
            bits=16,
            fractional_bits=8,
        )
        self.assertEqual(256, receipt["result_raw"])
        self.assertEqual("1", receipt["result_decimal"])
        self.assertEqual("TOWARD_ZERO", receipt["rounding"])
        self.assertTrue(receipt["transport_lossless"])

    def test_fixed_point_overflow_is_local_hold_not_false_result(self) -> None:
        receipt = fixed_point_alu("ADD", 127, 1, bits=8, fractional_bits=0)
        self.assertEqual("HOLD", receipt["state"])
        self.assertEqual("FIXED_POINT_OVERFLOW", receipt["first_blocker"])
        self.assertIsNone(receipt["result_raw"])

    def test_depth_nine_all_hold_is_retirement_action_while_carrier_exists(self) -> None:
        classification = classify_gate_set(
            {name: "HOLD" for name in GATE_NAMES},
            causal_depth=RETIREMENT_DEPTH,
            carrier_exists=True,
        )
        self.assertEqual("RETIRE_CANDIDATE", classification["state"])
        self.assertEqual("PREPARE_EXACT_CARRIER_RETIREMENT", classification["action"])
        self.assertFalse(classification["hold_admissible"])
        self.assertTrue(classification["all_holds"])

    def test_hold_is_only_admissible_after_the_carrier_is_gone(self) -> None:
        classification = classify_gate_set(
            {name: "HOLD" for name in GATE_NAMES},
            causal_depth=RETIREMENT_DEPTH,
            carrier_exists=False,
        )
        self.assertEqual("HOLD", classification["state"])
        self.assertEqual("NO_REPOSITORY_CARRIER_REMAINS", classification["action"])
        self.assertTrue(classification["hold_admissible"])

    def test_incomplete_gate_set_reobserves_instead_of_holding(self) -> None:
        classification = classify_gate_set(
            {GATE_NAMES[0]: "HOLD"},
            causal_depth=RETIREMENT_DEPTH,
            carrier_exists=True,
        )
        self.assertEqual("REOBSERVE", classification["state"])
        self.assertFalse(classification["all_observed"])
        self.assertFalse(classification["hold_admissible"])

    def test_retirement_prepare_receipt_is_effect_free(self) -> None:
        classification = classify_gate_set(
            {name: "HOLD" for name in GATE_NAMES},
            causal_depth=RETIREMENT_DEPTH,
            carrier_exists=True,
        )
        receipt = retirement_prepare_receipt(
            subject=self.subject,
            classification=classification,
        )
        self.assertEqual("ALL_EIGHT_GATES_HOLD_AT_DEPTH_NINE", receipt["reason"])
        self.assertFalse(receipt["effect_performed"])
        self.assertFalse(receipt["predecessor_evidence_transfer"])


if __name__ == "__main__":
    unittest.main()
