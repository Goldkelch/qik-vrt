#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AIHandoffContractTests(unittest.TestCase):
    def load_json(self, relative: str) -> dict[str, object]:
        value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def test_handoff_validator_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", "tools/ai_handoff.py"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("AI_HANDOFF_STATUS=VALID", completed.stdout)
        self.assertIn("PROGRESS_STATE=IDLE", completed.stdout)
        self.assertIn("RUNTIME_TOOLCHAIN_LOCK=runtime/toolchains/TOOLCHAIN.lock.tsv", completed.stdout)
        self.assertIn("RUNTIME_OPTIONAL_CAPABILITIES_AVAILABLE=", completed.stdout)

    def test_every_github_boundary_requires_a_complete_frame(self) -> None:
        policy = self.load_json("policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
        self.assertEqual(policy["schema"], "qikvrt-human-machine-progress-protocol/1.3")
        communication = policy["communication_rules"]
        self.assertIsInstance(communication, dict)
        for key in (
            "progress_frame_before_every_github_action",
            "progress_frame_after_every_github_action",
            "progress_frame_on_every_workflow_transition",
            "progress_frame_on_every_job_transition",
            "progress_frame_on_every_step_transition",
            "telemetry_observation_and_persistence_is_one_nonrecursive_atomic_cycle",
        ):
            self.assertIs(communication[key], True, key)
        self.assertIs(communication["allow_batched_github_actions_without_intermediate_frame"], False)
        self.assertIs(communication["later_summary_compensates_for_missing_frame"], False)

    def test_observation_cycles_are_serial_and_five_seconds_apart(self) -> None:
        policy = self.load_json("policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json")
        observation = policy["observation_contract"]
        self.assertIsInstance(observation, dict)
        self.assertIs(observation["serial_cycles"], True)
        self.assertIs(observation["overlapping_cycles_allowed"], False)
        self.assertIs(observation["persist_frame_before_next_cycle"], True)
        self.assertEqual(observation["poll_interval_seconds_after_completed_cycle"], 5)
        watcher = (ROOT / ".github/workflows/qikvrt_live_status_watch.yml").read_text(encoding="utf-8")
        self.assertIn("cancel-in-progress: false", watcher)
        self.assertIn("sleep 5", watcher)
        self.assertIn("state_signature", watcher)
        self.assertIn("GITHUB_STEP_SUMMARY", watcher)

    def test_tracked_progress_snapshot_is_not_stale_active_state(self) -> None:
        snapshot = self.load_json("AI_PROGRESS.json")
        self.assertEqual(snapshot["schema"], "qikvrt_human_machine_progress_v2")
        self.assertIn(snapshot["state"], {"IDLE", "PASS", "BLOCK", "FAIL", "TIMEOUT", "CANCELLED"})
        self.assertNotIn(snapshot["state"], {"RUNNING", "WAITING"})
        self.assertEqual(snapshot["percent"], 100)
        human = (ROOT / "AI_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("[██████████] 100%", human)
        self.assertIn(f"`{snapshot['state']}`", human)

    def test_repository_runtime_authority_and_cache_are_bound(self) -> None:
        context = self.load_json("AI_CONTEXT.json")
        runtime = context["runtime_authority"]
        self.assertIsInstance(runtime, dict)
        self.assertIs(runtime["repository_is_runtime_authority"], True)
        self.assertEqual(runtime["cache_root"], ".qikvrt/toolchains")
        for key in (
            "cache_policy",
            "toolchain_lock",
            "bootstrap_posix",
            "bootstrap_windows",
            "adaptive_runtime",
        ):
            self.assertTrue((ROOT / runtime[key]).is_file(), key)

        adaptive = (ROOT / runtime["adaptive_runtime"]).read_text(encoding="utf-8")
        self.assertIn("actions/cache/restore@", adaptive)
        self.assertIn("actions/cache/save@", adaptive)
        self.assertIn(".qikvrt/toolchains/gh", adaptive)

        optional = runtime["optional_capabilities"]
        self.assertIsInstance(optional, dict)
        self.assertIn("lean_cache_workflow", optional)
        lean_path = ROOT / optional["lean_cache_workflow"]
        if lean_path.is_file():
            lean = lean_path.read_text(encoding="utf-8")
            self.assertIn("Restore cumulative Lean runtime cache", lean)
            self.assertIn("~/.elan", lean)
            self.assertIn(".lake/packages", lean)
            self.assertIn(".lake/build", lean)
        else:
            self.assertNotIn(optional["lean_cache_workflow"], context["required_read_order"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
