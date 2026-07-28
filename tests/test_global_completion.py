#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import json
import pathlib
import unittest

from tools import qikvrt_global_completion as completion

ROOT = pathlib.Path(__file__).resolve().parents[1]


class GlobalCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scope = json.loads(completion.SCOPE_PATH.read_text(encoding="utf-8"))
        cls.inventory = json.loads(completion.INVENTORY_PATH.read_text(encoding="utf-8"))
        cls.traceability = json.loads(completion.TRACEABILITY_PATH.read_text(encoding="utf-8"))
        cls.kernel = json.loads(completion.KERNEL_RECEIPTS_PATH.read_text(encoding="utf-8"))
        cls.receipt = json.loads(completion.COMPLETION_RECEIPT_PATH.read_text(encoding="utf-8"))

    def test_materialization_is_byte_current(self) -> None:
        inventory, traceability, kernel, receipt, _paths = completion._build()
        expected = (inventory, traceability, kernel, receipt)
        for path, value in zip(completion.OUTPUTS, expected, strict=True):
            self.assertEqual(path.read_bytes(), completion._json_bytes(value), path.as_posix())

    def test_global_claim_universe_is_exact_and_unique(self) -> None:
        expected = sum(item["expected_entries"] for item in self.scope["claim_sources"])
        expected += len(self.scope["operational_claims"])
        claims = self.inventory["claims"]
        ids = [item["id"] for item in claims]
        self.assertEqual(len(claims), expected)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.inventory["counts"]["claims"], expected)
        self.assertEqual(
            set(self.scope["allowed_terminal_dispositions"]),
            completion.TERMINAL_DISPOSITIONS,
        )
        self.assertFalse(
            set(item["terminal_disposition"] for item in claims)
            - completion.TERMINAL_DISPOSITIONS
        )

    def test_source_claim_disposition_traceability_is_total(self) -> None:
        claims = {item["id"] for item in self.inventory["claims"]}
        traced = {item["claim_id"] for item in self.traceability["entries"]}
        self.assertEqual(claims, traced)
        self.assertEqual(self.traceability["counts"]["claims"], len(claims))
        self.assertEqual(self.traceability["counts"]["source_bound"], len(claims))
        self.assertEqual(self.traceability["counts"]["terminally_classified"], len(claims))
        for entry in self.traceability["entries"]:
            self.assertIsInstance(entry["source"].get("path"), str)
            self.assertIn(entry["terminal_disposition"], completion.TERMINAL_DISPOSITIONS)
            self.assertTrue(entry["disposition_evidence"])

    def test_every_direct_kernel_eligible_claim_has_exact_tag_receipt(self) -> None:
        eligible = {
            item["id"]
            for item in self.inventory["claims"]
            if item["kernel_eligible"] is True
        }
        receipts = {item["claim_id"] for item in self.kernel["receipts"]}
        self.assertEqual(eligible, receipts)
        self.assertEqual(self.kernel["counts"]["coverage_gap"], 0)
        self.assertEqual(self.kernel["exact_tag"], self.scope["baseline"]["tag"])
        for receipt in self.kernel["receipts"]:
            self.assertIn(receipt["terminal_disposition"], completion.KERNEL_DISPOSITIONS)
            self.assertTrue(receipt["proof_constants"])
            self.assertRegex(receipt["source_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(receipt["source_git_blob_sha1"], r"^[0-9a-f]{40}$")
            self.assertEqual(
                receipt["verification_contract"],
                ".github/workflows/qikvrt_manuscript_proof.yml",
            )

    def test_open_boundaries_are_explicit_and_block_global_final_pass(self) -> None:
        open_ids = {
            item["id"]
            for item in self.inventory["claims"]
            if item["terminal_disposition"] == "OPEN"
        }
        self.assertEqual(open_ids, set(self.receipt["open_claim_ids"]))
        for required in (
            "EFFECT_ACK::EA-OPEN-001",
            "EFFECT_ACK::EA-OPEN-002",
            "EFFECT_ACK::EA-OPEN-003",
        ):
            self.assertIn(required, open_ids)
        claims = self.receipt["claims"]
        self.assertTrue(claims["complete_claim_inventory"])
        self.assertTrue(claims["complete_source_claim_disposition_traceability"])
        self.assertTrue(
            claims["complete_exact_tag_kernel_receipt_coverage_for_kernel_eligible_claims"]
        )
        for key in (
            "green_global_gates_on_exact_candidate",
            "authority_mirror_equality_for_exact_candidate",
            "pass",
            "final_pass",
            "effect_ack_done",
            "fully_kernel_verified_overall_completion",
        ):
            self.assertFalse(claims[key], key)

    def test_status_projections_are_not_stale_or_semantically_promoted(self) -> None:
        completion._validate_status_projections()
        readme = completion.FORMALIZATION_README_PATH.read_text(encoding="utf-8")
        plan = completion.COMPLETION_PLAN_PATH.read_text(encoding="utf-8")
        self.assertNotIn("(work in progress)", readme)
        self.assertNotIn("12 kernel-checked atomic bindings", readme)
        self.assertNotIn("Status: ACTIVE", plan)
        self.assertIn("An explicit `OPEN` disposition", readme)
        self.assertIn("`OPEN` is an explicit terminal inventory disposition", plan)


if __name__ == "__main__":
    unittest.main(verbosity=2)
