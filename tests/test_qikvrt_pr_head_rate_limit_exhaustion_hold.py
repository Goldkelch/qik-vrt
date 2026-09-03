# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_pr_head_continuation.yml"


class PrHeadRateLimitExhaustionHoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_bounded_backoff_is_preserved(self) -> None:
        self.assertIn("for delay in 0 15 45", self.text)
        self.assertIn("API rate limit exceeded for installation.", self.text)
        self.assertNotIn("until gh api", self.text)

    def test_exhaustion_is_persisted_as_hold_not_selector_failure(self) -> None:
        self.assertIn('rate_limit_marker="$root/rate-limit-exhausted.json"', self.text)
        self.assertIn("emit_rate_limit_hold()", self.text)
        self.assertIn('reason:"GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED"', self.text)
        self.assertIn('first_causal_blocker:"GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED"', self.text)
        self.assertIn('next_action:"REOBSERVE_ON_NEXT_REPOSITORY_INTERRUPT"', self.text)
        self.assertIn('{d0:1,state:"HOLD"', self.text)
        self.assertIn('echo "selected=false" >> "$GITHUB_OUTPUT"', self.text)

    def test_exhausted_reads_return_only_type_safe_fail_closed_placeholders(self) -> None:
        self.assertIn('*"/pulls?"*) printf \'[]\\n\'', self.text)
        self.assertIn('*"/actions/runs?"*) printf \'{"workflow_runs":[]}\\n\'', self.text)
        self.assertIn('*"/jobs?"*) printf \'0\\n\'', self.text)
        self.assertIn('*"/status") printf \'missing\\n\'', self.text)
        self.assertGreaterEqual(self.text.count('if [ -f "$rate_limit_marker" ]'), 5)

    def test_non_quota_api_failure_remains_hard_failure(self) -> None:
        needle = 'if ! grep -Fq "API rate limit exceeded for installation." "$error"; then'
        self.assertIn(needle, self.text)
        start = self.text.index(needle)
        hard_failure_slice = self.text[start : start + 300]
        self.assertIn("return 1", hard_failure_slice)

    def test_hold_path_cannot_dispatch(self) -> None:
        hold = self.text.index("emit_rate_limit_hold()")
        dispatch = self.text.index("- name: Dispatch exact-head REOBSERVE continuation")
        self.assertLess(hold, dispatch)
        self.assertIn("if: steps.select.outputs.selected == 'true'", self.text[dispatch : dispatch + 250])


if __name__ == "__main__":
    unittest.main()
