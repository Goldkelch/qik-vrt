# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/ADAPTIVE_LIVE_REOBSERVATION_V1.json"


class AdaptiveLiveReobservationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_latest_head_is_live_relation_not_pinned_constant(self) -> None:
        selection = self.contract["selection"]
        self.assertTrue(selection["head_is_relation_not_constant"])
        self.assertTrue(selection["restart_on_head_drift"])
        self.assertTrue(selection["never_transfer_gate_success_between_heads"])

    def test_materialization_and_trusted_carrier_are_distinguished(self) -> None:
        detection = self.contract["selection"]["materialization_detection"]
        self.assertTrue(detection["github_actions_bot_commit_requires_parent_lineage_check"])
        self.assertTrue(detection["projection_only_changes_are_repository_native_materialization"])
        self.assertTrue(detection["tree_identical_trusted_carrier_is_same_materialized_state"])
        self.assertTrue(detection["scope_or_provenance_drift_blocks"])

    def test_terminal_render_and_inward_reflexivity_are_mandatory(self) -> None:
        required = set(self.contract["adaptive_terminal_render"]["required_sections"])
        self.assertIn("INWARD_REFLEXIVITY", required)
        self.assertIn("OUTWARD_REFLECTION", required)
        self.assertIn("FIRST_DETERMINISTIC_BLOCKER", required)
        self.assertTrue(self.contract["observation"]["observer_remains_live_during_hold"])
        self.assertTrue(self.contract["observation"]["productive_writer_requires_fresh_clear_inward_projection"])

    def test_untrusted_or_nonterminal_state_cannot_autopromote(self) -> None:
        stops = set(self.contract["automatic_continuation"]["stop_conditions"])
        self.assertIn("NONTERMINAL_APPLICABLE_GATE", stops)
        self.assertIn("UNTRUSTED_ACTION_REQUIRED_OR_ZERO_JOB", stops)
        self.assertIn("HUMAN_IDENTITY_DEPENDENT_REVIEW_REQUIRED", stops)
        self.assertFalse(self.contract["completion_claims"]["PASS"])
        self.assertFalse(self.contract["completion_claims"]["EFFECT_ACK_DONE"])


if __name__ == "__main__":
    unittest.main()
