# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_self_heal_terminal_monitor",
    ROOT / "tools/qikvrt_self_heal_terminal_monitor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SelfHealTerminalMonitorTests(unittest.TestCase):
    def test_remote_mismatch_is_fail_closed_and_a_real_integration_defect(self) -> None:
        result = MODULE.classify(
            {"conclusion": "failure"},
            {
                "state": "HOLD",
                "failure_class": "AUTONOMOUS_PRE_EFFECT_BLOCKED",
                "detail": "canonical source remote URL mismatch",
            },
        )
        self.assertTrue(result["expected_fail_closed_hold"])
        self.assertTrue(result["actual_defect"])
        self.assertEqual(
            result["smallest_action"],
            "MATERIALIZE_POLICY_BOUND_CANONICAL_UPSTREAM_REMOTE",
        )
        self.assertFalse(result["administrator_action_required"])

    def test_other_hold_remains_expected_fail_closed(self) -> None:
        result = MODULE.classify(
            {"conclusion": "failure"},
            {"state": "HOLD", "detail": "NO_COMPETING_WRITER not established"},
        )
        self.assertEqual(result["kind"], "EXPECTED_FAIL_CLOSED_HOLD")
        self.assertTrue(result["expected_fail_closed_hold"])
        self.assertFalse(result["actual_defect"])

    def test_snapshot_preserves_writer_lease_and_no_completion_claim(self) -> None:
        snapshot = MODULE.build_snapshot(
            repository="Goldkelch/qik-vrt",
            observed_at="2026-08-16T20:04:29Z",
            head="88dde0ba2394e941f11b8e848fcd4899bbc5d29c",
            tree="c56cefb1464ec934d4b34b705618d5de2b40292c",
            self_heal_runs={"workflow_runs": [{"id": 1, "run_number": 1, "conclusion": "failure"}]},
            self_heal_jobs={"jobs": [{"id": 2, "name": "observe-repair-propose", "steps": [{"number": 5, "name": "Execute bounded repository-native repairs before external effects", "conclusion": "failure"}]}]},
            self_heal_receipt={"state": "HOLD", "detail": "canonical source remote URL mismatch"},
            watchdog_runs={"workflow_runs": [{"id": 3, "run_number": 3, "conclusion": "success"}]},
            watchdog_receipt={
                "state": "QUIESCENT_OBSERVATION",
                "disposition": "OBSERVE",
                "observations": {
                    "active_productive_runs": [],
                    "active_writers": [],
                    "stale_writers": [],
                    "waiting_productive_runs": [],
                    "untrusted_terminal_runs": [],
                },
                "leases": {
                    "writer_lease_seconds": 1200,
                    "queue_lease_seconds": 600,
                    "progress_lease_seconds": 900,
                },
                "resource_graph": {"cycle_detected": False},
            },
        )
        self.assertEqual(snapshot["writer_lease"]["active_writers"], [])
        self.assertEqual(snapshot["writer_lease"]["leases"]["writer_lease_seconds"], 1200)
        self.assertFalse(snapshot["completion_claims"]["PASS"])
        self.assertFalse(snapshot["completion_claims"]["EFFECT_ACK_DONE"])

    def test_repository_monitor_workflow_is_permanent_event_driven_and_read_only(self) -> None:
        workflow = (ROOT / ".github/workflows/qikvrt_self_heal_terminal_monitor.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn('- "QIK-VRT autonomous bounded self-heal"', workflow)
        self.assertIn('- "QIKVRT reflexive repository watchdog"', workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("git push", workflow)
        self.assertNotIn("gh pr", workflow)

    def test_terminal_pattern_and_firefox_adapter_preserve_passive_boundary(self) -> None:
        pattern = json.loads((ROOT / "docs/terminal/TERMINAL_PATTERN_V1.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "docs/terminal/firefox/manifest.json").read_text(encoding="utf-8"))
        popup = (ROOT / "docs/terminal/firefox/popup.js").read_text(encoding="utf-8")
        self.assertEqual(pattern["pattern_id"], "QIKVRT_TERMINAL_PATTERN_V1")
        self.assertEqual(pattern["adapters"]["firefox_webextension"]["state"], "REFERENCE_IMPLEMENTED")
        self.assertFalse(pattern["client_contract"]["repository_writes"])
        self.assertFalse(pattern["client_contract"]["effect_execution"])
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertEqual(manifest.get("permissions", []), [])
        self.assertEqual(manifest["host_permissions"], ["https://api.github.com/repos/Goldkelch/qik-vrt/*"])
        self.assertIn('credentials: "omit"', popup)
        self.assertNotIn("POST", popup)
        self.assertNotIn("PUT", popup)
        self.assertNotIn("PATCH", popup)
        self.assertNotIn("DELETE", popup)


if __name__ == "__main__":
    unittest.main()
