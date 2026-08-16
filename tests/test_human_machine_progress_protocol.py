#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression contract for the repository delivery-closure standard."""
from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json"
ORDERED_GATES = [
    "SCOPE_AND_IMPLEMENTATION_BOUND",
    "TARGETED_REGRESSION",
    "DOCUMENTATION_DISPOSITION",
    "REPOSITORY_INTEGRITY_MATERIALIZED",
    "EXACT_HEAD_TEST_GATE",
    "REMOTE_REF_REOBSERVED",
]


class HumanMachineProgressProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.closure = self.policy["delivery_closure"]

    def test_delivery_closure_is_ordered_and_fail_closed(self) -> None:
        self.assertEqual(self.closure["applies_to"], "AUTHORIZED_REPOSITORY_MUTATION")
        self.assertEqual(self.closure["completion_state"], "REPOSITORY_DELIVERY_VERIFIED")
        self.assertTrue(self.closure["all_applicable_gates_required"])
        self.assertEqual(self.closure["ordered_gates"], ORDERED_GATES)
        self.assertTrue(self.closure["documentation"]["updated_or_explicitly_not_applicable"])
        self.assertTrue(self.closure["documentation"]["not_applicable_requires_reason"])
        self.assertEqual(
            self.closure["remote_evidence_required"],
            ["repository", "target_ref", "head_sha", "root_tree", "observed_at"],
        )
        for claim in (
            "local_commit_alone_is_delivery",
            "push_without_reobservation_is_delivery",
            "merge_without_current_ref_evidence_is_delivery",
            "missing_gate_may_be_claimed_complete",
        ):
            with self.subTest(claim=claim):
                self.assertFalse(self.closure["forbidden_inferences"][claim])

    def test_foundation_and_test_first_loop_remain_explicit(self) -> None:
        foundation = self.closure["foundational_model"]
        self.assertEqual(foundation["additive_identity"], "0")
        self.assertEqual(foundation["multiplicative_identity"], "1")
        self.assertEqual(foundation["operational_start"], "DISTINGUISHABILITY")
        self.assertIn("TEST", foundation["information_flow"])
        self.assertTrue(foundation["formal_empirical_and_normative_claims_remain_separately_bound"])
        self.assertTrue(self.closure["test_first"]["required_for_behavior_changes"])
        self.assertEqual(self.closure["test_first"]["loop"], ["RED", "GREEN", "REFACTOR"])

    def test_browser_delivery_boundary_is_explicit(self) -> None:
        browser = self.closure["browser_interface_when_applicable"]
        self.assertIn("STATIC_SOURCE_AND_SECURITY_CONTRACT", browser["required_checks"])
        self.assertIn("DECLARED_CORS_AND_SAME_ORIGIN_READS", browser["required_checks"])
        self.assertIn("OPT_IN_VOICE_OR_DEVICE_BEHAVIOR", browser["required_checks"])
        self.assertTrue(browser["microphone_must_not_start_automatically"])
        self.assertEqual(browser["denied_or_unavailable_device_capability_state"], ["CONTINUE", "BLOCK"])
        self.assertFalse(browser["visual_readback_state_proves_audibility"])
        self.assertFalse(browser["one_browser_observation_proves_cross_browser_or_cross_device_behavior"])

    def test_human_and_review_contracts_reference_the_same_closure(self) -> None:
        expected = "REPOSITORY_DELIVERY_VERIFIED"
        paths = (
            ROOT / "AGENTS.md",
            ROOT / "docs/HUMAN_MACHINE_PROGRESS_PROTOCOL.md",
            ROOT / "docs/HUMAN_MACHINE_PROGRESS_STANDARD.md",
            ROOT / ".github/PULL_REQUEST_TEMPLATE.md",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertIn(expected, path.read_text(encoding="utf-8"))

    def test_release_claims_remain_false(self) -> None:
        self.assertEqual(
            self.closure["release_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
