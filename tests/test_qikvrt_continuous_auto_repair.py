# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github/workflows/qikvrt_autonomous_self_heal.yml"


class ContinuousAutoRepairContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    def test_every_instance_has_event_driven_and_five_minute_opportunities(self) -> None:
        workflow = self.workflow
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn("push:\n    branches: [main]", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn('- "QIKVRT CI"', workflow)
        self.assertIn('- "QIKVRT repository evidence materialization"', workflow)
        self.assertIn("types: [completed]", workflow)
        self.assertIn(
            "github.event.workflow_run.head_branch == 'main'",
            workflow,
        )

    def test_pull_request_validation_is_read_only_and_exact_head_bound(self) -> None:
        workflow = self.workflow
        self.assertIn("pull_request:", workflow)
        self.assertIn(
            '"tests/test_qikvrt_continuous_auto_repair.py"',
            workflow,
        )
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn(
            "ref: ${{ github.event.pull_request.head.sha }}",
            workflow,
        )
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("github.event_name != 'pull_request'", workflow)

    def test_operational_runs_remain_single_writer_and_non_preemptive(self) -> None:
        workflow = self.workflow
        self.assertIn(
            "group: qikvrt-autonomous-self-heal-${{ github.repository }}-",
            workflow,
        )
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertNotIn("Goldkelch/qik-vrt", workflow)
        self.assertNotIn("ingolf-lohmann/qik-vrt", workflow)

    def test_no_recursive_watchdog_or_self_trigger_is_admitted(self) -> None:
        workflow = self.workflow
        self.assertNotIn(
            '- "QIKVRT reflexive repository watchdog"',
            workflow,
        )
        self.assertNotIn(
            '- "QIK-VRT autonomous bounded self-heal"',
            workflow,
        )

    def test_receipt_is_preserved_even_when_the_controller_blocks(self) -> None:
        workflow = self.workflow
        self.assertIn("set +e", workflow)
        self.assertIn("rc=$?", workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn(
            "qikvrt-self-heal-receipt-${{ github.run_id }}-${{ github.run_attempt }}",
            workflow,
        )
        self.assertIn('exit "$rc"', workflow)

    def test_workflow_cannot_directly_promote_or_cross_external_effects(self) -> None:
        workflow = self.workflow
        self.assertNotIn("gh pr merge", workflow)
        self.assertNotIn("gh release", workflow)
        self.assertNotIn("git push origin main", workflow)
        self.assertNotIn("/dispatches", workflow)


if __name__ == "__main__":
    unittest.main()
