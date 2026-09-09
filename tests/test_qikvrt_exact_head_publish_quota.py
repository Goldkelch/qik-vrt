# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_exact_head_verify.yml"


class ExactHeadPublishQuotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_dispatch_envelope_uses_git_refs_not_rest_budget(self) -> None:
        self.assertIn("Validate dispatch envelope without REST quota", self.text)
        self.assertIn('refs/pull/${TARGET_PR}/head', self.text)
        self.assertIn('refs/heads/${TARGET_REF}', self.text)
        self.assertNotIn('gh api "repos/${GITHUB_REPOSITORY}/pulls/${TARGET_PR}"', self.text)

    def test_primary_installation_quota_waits_for_observed_reset(self) -> None:
        self.assertIn("API rate limit exceeded for installation.", self.text)
        self.assertIn("gh api rate_limit --jq '.resources.core.reset'", self.text)
        self.assertIn("QIKVRT_GITHUB_INSTALLATION_RATE_LIMIT_RESET_WAIT_SECONDS", self.text)
        self.assertIn("sleep \"$delay\"", self.text)
        self.assertIn("delay -gt 3700", self.text)
        self.assertNotIn("for delay in 0 15 45", self.text)

    def test_verified_head_is_not_reclassified_by_publish_transport_failure(self) -> None:
        self.assertIn("id: verified", self.text)
        self.assertIn('echo "passed=true" >> "$GITHUB_OUTPUT"', self.text)
        self.assertIn("steps.verified.outputs.passed == 'true'", self.text)
        self.assertIn("steps.verified.outputs.passed != 'true'", self.text)
        self.assertIn("steps.envelope.outputs.validated == 'true'", self.text)
        self.assertNotIn("if: failure()", self.text)

    def test_success_path_has_only_required_mutative_api_edges(self) -> None:
        self.assertNotIn("gh pr comment", self.text)
        self.assertIn('"repos/${GITHUB_REPOSITORY}/statuses/${TARGET_SHA}"', self.text)
        self.assertIn("qikvrt_requested_review_executor.yml/dispatches", self.text)
        self.assertIn("sleep 1", self.text)
        self.assertNotIn("pull-requests: write", self.text)

    def test_timeout_covers_one_primary_reset_window(self) -> None:
        self.assertIn("timeout-minutes: 90", self.text)


if __name__ == "__main__":
    unittest.main()
