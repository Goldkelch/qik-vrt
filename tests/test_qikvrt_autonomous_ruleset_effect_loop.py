# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_ruleset_effect_loop.yml"


class AutonomousRulesetEffectLoopContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_event_driven_and_not_polled(self):
        self.assertIn('workflows:\n      - "QIKVRT required code-owner review"', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertNotIn("schedule:", self.text)

    def test_routes_only_exact_ruleset_blocker(self):
        self.assertIn("CODE_OWNER_RULE_NOT_ENFORCED", self.text)
        self.assertIn("RULESET_REPAIR_NOT_REQUIRED", self.text)
        self.assertIn("EXACT_SUBJECT_DRIFT", self.text)

    def test_reuses_existing_reconciler_and_readback_contract(self):
        self.assertIn("tools/qikvrt_ruleset_reconcile.py", self.text)
        self.assertIn("--apply", self.text)
        self.assertIn("--receipt /tmp/qikvrt-autonomous-ruleset-receipt.json", self.text)
        self.assertIn("QIKVRT_RULESET_ADMIN_TOKEN", self.text)

    def test_closes_loop_with_one_fresh_gate_dispatch(self):
        self.assertIn("qikvrt_required_review_gate.yml/dispatches", self.text)
        self.assertIn("Dispatch exactly one fresh same-head gate reobservation", self.text)
        self.assertIn('test "$current_head" = "$EXPECTED_HEAD"', self.text)

    def test_authority_boundary_is_explicit(self):
        self.assertIn("Publish authority HOLD when administrator capability is unavailable", self.text)
        self.assertIn("REQUEST_AUTHORITY:", self.text)
        self.assertIn("state=pending", self.text)

    def test_effect_and_reobservation_are_separate(self):
        self.assertIn("QIKVRT autonomous ruleset repair", self.text)
        self.assertIn("ruleset reconciled; exact-head gate reobservation dispatched", self.text)
        self.assertNotIn("gh pr merge", self.text)
        self.assertNotIn("event=APPROVE", self.text)


if __name__ == "__main__":
    unittest.main()
