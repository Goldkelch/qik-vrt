# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


class PullRequestHeadMutationBoundaryTests(unittest.TestCase):
    def test_dynamic_pr_head_writers_are_guarded_from_pull_request_events(self) -> None:
        offenders: list[str] = []
        for path in sorted(WORKFLOWS.glob("*.yml")):
            text = path.read_text(encoding="utf-8")
            if "pull_request:" not in text:
                continue
            derives_pr_target = (
                "github.event_name == 'pull_request' && github.head_ref" in text
                or "github.event_name == \"pull_request\" && github.head_ref" in text
            )
            if not derives_pr_target:
                continue
            blocks = text.split("\n      - name: ")
            for block in blocks:
                mutates_target = (
                    'git push origin "HEAD:$TARGET_REF"' in block
                    or "git push origin 'HEAD:$TARGET_REF'" in block
                    or "git push origin HEAD:$TARGET_REF" in block
                )
                if not mutates_target:
                    continue
                guarded = (
                    "if: github.event_name != 'pull_request'" in block
                    or 'if: github.event_name != "pull_request"' in block
                    or "if: github.event_name == 'push'" in block
                    or 'if: github.event_name == "push"' in block
                )
                if not guarded:
                    offenders.append(path.as_posix())
        self.assertEqual(
            offenders,
            [],
            "PR workflows must never push to their own github.head_ref via TARGET_REF; "
            "materialize/read back without mutating the active PR head: "
            + ", ".join(offenders),
        )

    def test_primary_materializer_keeps_pr_persistence_read_only(self) -> None:
        path = WORKFLOWS / "qikvrt_batch04_integrity.yml"
        text = path.read_text(encoding="utf-8")
        marker = "- name: Commit materialized repository evidence"
        self.assertIn(marker, text)
        block = text[text.index(marker):]
        self.assertIn("if: github.event_name != 'pull_request'", block)
        self.assertIn('git push origin "HEAD:$TARGET_REF"', block)


    def test_primary_materializer_admits_publication_branch_push(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        push = text.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
        self.assertIn("      - docs/information-effect-axis-v1\n", push)
        self.assertIn("github.actor != 'github-actions[bot]'", text)
        self.assertNotIn("pull_request_target:", text)

    def test_primary_materializer_pins_checkout_to_event_head(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        self.assertIn(
            "EXPECTED_HEAD: ${{ github.event_name == 'pull_request' && "
            "github.event.pull_request.head.sha || github.sha }}",
            text,
        )
        self.assertIn("ref: ${{ env.EXPECTED_HEAD }}", text)
        self.assertNotIn("ref: ${{ env.TARGET_REF }}", text)

    def test_primary_materializer_retains_gate_and_drift_guards(self) -> None:
        text = (WORKFLOWS / "qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
        marker = "- name: Commit materialized repository evidence"
        before, persist = text.split(marker, 1)
        self.assertIn("make test", before)
        self.assertIn("python3 tools/qikvrt_integrity.py verify", before)
        self.assertIn('if [ "$remote_head" != "$source_head" ]; then', persist)
        self.assertIn('if [ "$remote_head_after_commit" != "$source_head" ]; then', persist)
        self.assertIn('git push origin "HEAD:$TARGET_REF"', persist)
        self.assertNotIn("--force", persist)
        self.assertIn("if: github.event_name != 'pull_request'", persist)
        self.assertIn("permissions:\n  contents: write\n", text)
        self.assertIn("cancel-in-progress: false", text)


if __name__ == "__main__":
    unittest.main()
