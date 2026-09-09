# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression contract for the single-writer ruleset effect topology."""

from __future__ import annotations

import pathlib
import re
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"
EFFECT_PATH = WORKFLOW_ROOT / "qikvrt_autonomous_ruleset_effect_loop.yml"
BRIDGE_PATH = WORKFLOW_ROOT / "qikvrt_ruleset_effect_dispatch_bridge.yml"
WATCHDOG_PATH = WORKFLOW_ROOT / "qikvrt_reflexive_repository_watchdog.yml"
RETIRED_WRITER_PATH = WORKFLOW_ROOT / "qikvrt_ruleset_reconcile.yml"
APP_MINT = "actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349"


def workflow_document(path: pathlib.Path) -> dict[str, object]:
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    if not isinstance(value, dict):
        raise AssertionError(f"workflow is not a mapping: {path}")
    return value


def workflow_run_sources(document: dict[str, object]) -> list[str]:
    triggers = document.get("on")
    if not isinstance(triggers, dict):
        return []
    workflow_run = triggers.get("workflow_run")
    if not isinstance(workflow_run, dict):
        return []
    sources = workflow_run.get("workflows", [])
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
        raise AssertionError("workflow_run sources are malformed")
    return list(sources)


class RulesetTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.texts = {
            path.name: path.read_text(encoding="utf-8")
            for path in sorted((*WORKFLOW_ROOT.glob("*.yml"), *WORKFLOW_ROOT.glob("*.yaml")))
        }
        cls.effect = EFFECT_PATH.read_text(encoding="utf-8")
        cls.bridge = BRIDGE_PATH.read_text(encoding="utf-8")
        cls.watchdog = WATCHDOG_PATH.read_text(encoding="utf-8")

    def test_only_effect_loop_can_mint_app_authority_and_invoke_apply(self) -> None:
        apply_callers = [
            name
            for name, text in self.texts.items()
            if "tools/qikvrt_ruleset_reconcile.py" in text
            and re.search(r"(^|\s)--apply(?:\s|$)", text)
        ]
        app_mint_holders = [
            name for name, text in self.texts.items() if APP_MINT in text
        ]
        self.assertFalse(RETIRED_WRITER_PATH.exists())
        self.assertEqual(apply_callers, [EFFECT_PATH.name])
        self.assertEqual(app_mint_holders, [EFFECT_PATH.name])
        self.assertIn("QIKVRT_RULESET_ADMIN_TOKEN: ${{ steps.app-token.outputs.token }}", self.effect)
        self.assertIn("permission-administration: write", self.effect)
        self.assertNotIn("secrets.QIKVRT_RULESET_ADMIN_TOKEN", self.effect)
        self.assertNotIn("QIKVRT_RULESET_ADMIN_TOKEN", self.bridge)

    def test_bridge_is_sole_workflow_run_ingress_and_effect_loop_is_dispatch_only(self) -> None:
        effect_document = workflow_document(EFFECT_PATH)
        bridge_document = workflow_document(BRIDGE_PATH)
        effect_triggers = effect_document.get("on")
        self.assertEqual(set(effect_triggers or {}), {"workflow_dispatch"})
        self.assertEqual(
            workflow_run_sources(bridge_document),
            ["QIKVRT required code-owner review"],
        )
        dispatch_sources = [
            name
            for name, text in self.texts.items()
            if re.search(
                r"actions/workflows/(?:qikvrt_autonomous_ruleset_effect_loop\.yml|\$\{EFFECT_WORKFLOW\})/dispatches",
                text,
            )
        ]
        self.assertEqual(dispatch_sources, sorted([BRIDGE_PATH.name, WATCHDOG_PATH.name]))
        self.assertIn('mode:"PR"', self.bridge)
        self.assertIn('mode: "MAIN"', self.watchdog)

    def test_every_pr_candidate_reconciles_before_durable_receipt(self) -> None:
        self.assertIn("qikvrt_ruleset_single_apply_receipt_v1", self.effect)
        self.assertIn("qikvrt-ruleset-apply:", self.effect)
        self.assertNotIn("APPLY_REQUIRED", self.effect)
        self.assertNotIn("ALREADY_APPLIED", self.effect)
        self.assertNotIn("steps.apply_receipt", self.effect)
        self.assertIn("Policy SHA-256", self.effect)
        self.assertIn("Current reconciliation receipt SHA-256", self.effect)
        self.assertIn("Exact trusted Main: ${EXPECTED_MAIN}", self.effect)
        self.assertIn('jq -r .user.login <<<"$readback"', self.effect)
        self.assertIn("Record and read back completed exact-subject reconciliation receipt", self.effect)
        self.assertLess(
            self.effect.index("python3 -B tools/qikvrt_ruleset_reconcile.py"),
            self.effect.index("Record and read back completed exact-subject reconciliation receipt"),
        )
        pre_apply, _record = self.effect.split(
            "      - name: Record and read back completed exact-subject reconciliation receipt",
            1,
        )
        self.assertNotIn(
            'gh api --method POST "repos/${REPOSITORY}/issues/${PR_NUMBER}/comments"',
            pre_apply,
        )

    def test_main_dispatch_is_schedule_only_and_bounded_without_app_authority(self) -> None:
        dispatch_job = self.watchdog.split(
            "  dispatch-main-ruleset-reconciliation:", 1
        )[1]
        self.assertIn("github.event_name == 'schedule'", dispatch_job)
        self.assertIn("actions: write", dispatch_job)
        self.assertIn("expected_policy_sha", dispatch_job)
        self.assertIn("ACTIVE_OR_QUEUED_EXACT_MAIN_EFFECT_EXISTS", dispatch_job)
        self.assertIn("ACTIVE_OR_QUEUED_EFFECT_EXISTS", dispatch_job)
        self.assertIn("qikvrt_ruleset_main_dispatch_receipt_v1", dispatch_job)
        self.assertIn("qikvrt-ruleset-main-dispatch-", dispatch_job)
        self.assertNotIn("QIKVRT_RULESET_ADMIN_TOKEN", dispatch_job)
        self.assertNotIn("create-github-app-token", dispatch_job)
        self.assertNotIn("qikvrt_ruleset_reconcile.py", dispatch_job)
        self.assertNotIn("--apply", dispatch_job)

    def test_ruleset_flow_has_no_required_review_feedback_edge(self) -> None:
        self.assertNotIn("qikvrt_required_review_gate.yml/dispatches", self.effect)
        self.assertNotIn("Dispatch one fresh same-head review-gate reobservation", self.effect)
        self.assertNotIn("workflow_run:", self.effect)


if __name__ == "__main__":
    unittest.main()
