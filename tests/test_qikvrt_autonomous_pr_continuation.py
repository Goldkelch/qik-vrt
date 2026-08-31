# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations


import json
import pathlib
import subprocess
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
CONTINUATION = ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml"
VERIFIER = ROOT / ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"




class AutonomousPRContinuationTests(unittest.TestCase):
    def test_contract_is_opt_in_same_repo_draft_and_one_at_a_time(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        value = contract["pull_request_continuation"]
        self.assertEqual(
            value["opt_in_marker"],
            "<!-- qikvrt-autonomous-self-heal:enabled -->",
        )
        self.assertTrue(value["same_repository_only"])
        self.assertTrue(value["draft_only"])
        self.assertEqual(value["maximum_pull_requests_per_run"], 1)
        self.assertEqual(value["history_rewrite"], "FORBIDDEN")
        self.assertEqual(
            value["automatic_promotion"],
            "TWO_PHASE_EXPECTED_HEAD_BOUND_ONLY",
        )


    def test_continuation_preserves_history_and_never_merges_or_force_pushes(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("git merge --no-ff --no-edit", source)
        self.assertIn("live_head_before_push", source)
        self.assertIn("refs/heads/${HEAD_REF}", source)
        self.assertNotIn("git push --force", source)
        self.assertNotIn("git push -f", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("refs/heads/main\"", source)
        self.assertIn("make test", source)
        self.assertIn("qikvrt_autonomous_exact_head_verify", source)


    def test_only_handler_owned_generated_conflicts_are_auto_resolved(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        self.assertIn("git diff --name-only --diff-filter=U", source)
        self.assertIn(".allowlisted_handlers[].mutable_paths[]", source)
        self.assertIn("HOLD: non-allowlisted merge conflicts", source)
        self.assertIn("git checkout --ours", source)
        self.assertIn("generated-output reset", source)
        self.assertIn("HOLD conflict fingerprint", source)
        self.assertIn("QIKVRT autonomous draft continuation", source)
        self.assertIn("commits/" + "$" + "{EXPECTED_HEAD}/statuses", source)
        self.assertNotIn("git checkout --theirs", source)
        self.assertNotIn("git merge --abort || true", source)


    def test_continuation_shell_block_is_syntax_valid(self) -> None:
        source = CONTINUATION.read_text(encoding="utf-8")
        marker = "      - name: Continue exact draft head through deterministic repairs\n"
