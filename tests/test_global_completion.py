#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCOPE = ROOT / "GLOBAL_COMPLETION_SCOPE.json"
INVENTORY = ROOT / "GLOBAL_CLAIM_INVENTORY.json"
TRACEABILITY = ROOT / "GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json"
KERNEL = ROOT / "GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json"
FINAL_INPUT = ROOT / "GLOBAL_COMPLETION_FINALIZATION_INPUT.json"
FINAL_RECEIPT = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"
FORMAL_STATUS = ROOT / "formalization" / "QIKVRT_Formalization_v2.0" / "GLOBAL_COMPLETION_STATUS.json"
AI_PROGRESS = ROOT / "AI_PROGRESS.json"
GENERATOR = ROOT / "tools/qikvrt_global_completion.py"
spec = importlib.util.spec_from_file_location("global_completion", GENERATOR)
generator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(generator)

ALLOWED = {
    "KERNEL_PROVED",
    "KERNEL_PROVED_CONDITIONAL",
    "EMPIRICAL_EVIDENCE_BOUND",
    "INTERPRETIVE",
    "NORMATIVE",
    "OPEN",
    "OUT_OF_SCOPE",
}


def load(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} is not an object")
    return value


class GlobalCompletionTests(unittest.TestCase):
    def test_alpha2_historical_status_freeze_is_byte_current(self) -> None:
        subprocess.run(
            [sys.executable, "-B", "tools/qikvrt_freeze_alpha2_status.py", "check"],
            cwd=ROOT,
            check=True,
        )

    def test_generator_is_byte_current(self) -> None:
        subprocess.run(
            [sys.executable, "-B", "tools/qikvrt_global_completion.py", "check"],
            cwd=ROOT,
            check=True,
        )

    def test_scope_is_exact_and_finite(self) -> None:
        scope = load(SCOPE)
        self.assertEqual(scope["scope_id"], "qikvrt-global-claim-scope-v1")
        self.assertEqual(
            [item["expected"] for item in scope["included_registries"]],
            [43, 34, 15],
        )
        self.assertEqual(set(scope["terminal_dispositions"]), ALLOWED)
        self.assertTrue(scope["excluded_classes"])
        tag = scope["exact_tag_binding"]
        self.assertEqual(
            tag["tag"],
            "v2026.07.28-authority-mirror-zenodo-equality-1.0.0",
        )
        self.assertEqual(tag["zenodo_doi"], "10.5281/zenodo.21633411")

    def test_inventory_is_complete_unique_and_terminal(self) -> None:
        inventory = load(INVENTORY)
        claims = inventory["claims"]
        self.assertEqual(len(claims), 92)
        identifiers = [item["inventory_id"] for item in claims]
        self.assertEqual(len(set(identifiers)), len(identifiers))
        self.assertEqual(
            {item["namespace"] for item in claims},
            {"MANUSCRIPT", "APPENDIX", "EFFECT_ACK"},
        )
        self.assertTrue(
            all(item["terminal_disposition"] in ALLOWED for item in claims)
        )
        self.assertTrue(all(item["source_refs"] for item in claims))
        self.assertEqual(inventory["counts"]["total"], 92)
        self.assertEqual(
            inventory["counts"]["kernel_eligible_primary_claims"], 54
        )

    def test_kernel_receipts_cover_every_primary_kernel_claim(self) -> None:
        inventory = load(INVENTORY)
        kernel = load(KERNEL)
        eligible = {
            item["inventory_id"]
            for item in inventory["claims"]
            if item["namespace"] in {"MANUSCRIPT", "EFFECT_ACK"}
            and item["terminal_disposition"]
            in {"KERNEL_PROVED", "KERNEL_PROVED_CONDITIONAL"}
        }
        receipts = {
            item["inventory_id"] for item in kernel["primary_receipts"]
        }
        self.assertEqual(eligible, receipts)
        self.assertEqual(len(receipts), 54)
        self.assertTrue(
            all(item["exact_tag_required"] for item in kernel["primary_receipts"])
        )
        self.assertTrue(kernel["tag_protected_paths"])

    def test_traceability_is_total_without_proof_inflation(self) -> None:
        inventory = load(INVENTORY)
        trace = load(TRACEABILITY)
        self.assertEqual(trace["counts"]["records"], 92)
        self.assertEqual(trace["counts"]["source_bound"], 92)
        self.assertEqual(
            {item["inventory_id"] for item in trace["records"]},
            {item["inventory_id"] for item in inventory["claims"]},
        )
        self.assertTrue(
            trace["completeness"]["every_primary_kernel_claim_has_native_receipt"]
        )
        self.assertTrue(
            trace["completeness"][
                "non_kernel_claims_are_not_misrepresented_as_lean_theorems"
            ]
        )
        for item in trace["records"]:
            requirement = item["proof_or_disposition"]["requirement"]
            if item["terminal_disposition"] in {
                "EMPIRICAL_EVIDENCE_BOUND",
                "INTERPRETIVE",
                "NORMATIVE",
                "OPEN",
                "OUT_OF_SCOPE",
            }:
                self.assertNotEqual(requirement, "NATIVE_LEAN_KERNEL_RECEIPT")

    def test_final_receipt_is_fail_closed_until_authorized(self) -> None:
        status = load(FORMAL_STATUS)
        if FINAL_INPUT.exists():
            receipt = load(FINAL_RECEIPT)
            self.assertEqual(receipt["state"], "FINAL_PASS")
            self.assertTrue(all(receipt["claims"].values()))
            self.assertTrue(receipt["claim_semantics"]["scope_qualified"])
            self.assertTrue(
                receipt["claim_semantics"]["open_claims_are_not_claimed_proved"]
            )
            self.assertEqual(status["state"], "FINAL_PASS")
        else:
            self.assertFalse(FINAL_RECEIPT.exists())
            self.assertEqual(status["state"], "CANDIDATE_MATERIALIZED")

    def test_root_projection_owner_is_explicit_and_supersedable(self) -> None:
        receipt = generator.terminal_batch_002_receipt()
        self.assertIsNotNone(receipt)
        progress = load(AI_PROGRESS)
        global_receipt = load(FINAL_RECEIPT)
        generator.validate_root_progress_owner(progress, global_receipt)
        future = copy.deepcopy(progress)
        future["operation_id"] = "future-content-disposition-owner"
        future["projection_owner"] = {
            "tool": "tools/qikvrt_global_completion.py",
            "check_command": "python3 -B tools/qikvrt_global_completion.py --check",
        }
        generator.validate_root_progress_owner(future, global_receipt)
        lost_scope = copy.deepcopy(future)
        del lost_scope["scopes"][receipt["union_id"]]
        with self.assertRaises(ValueError):
            generator.validate_root_progress_owner(
                lost_scope,
                global_receipt,
                receipt,
            )
        del future["projection_owner"]
        with self.assertRaises(ValueError):
            generator.validate_root_progress_owner(future, global_receipt)
        false_terminal = copy.deepcopy(receipt)
        false_terminal["completion_claims"]["pass"] = True
        with self.assertRaises(ValueError):
            generator.validate_terminal_batch_002_receipt(false_terminal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
