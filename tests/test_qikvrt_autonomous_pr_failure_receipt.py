# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tempfile
import unittest

from tools.qikvrt_autonomous_pr_failure_receipt import (
    FailureReceiptError,
    build_receipt,
    main,
    normalize_conflict_paths,
    render_annotation,
    render_pr_comment,
    render_summary,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml"


class AutonomousPRFailureReceiptTests(unittest.TestCase):
    def _receipt(self) -> dict[str, object]:
        return build_receipt(
            repository="Goldkelch/qik-vrt",
            run_id=33047686781,
            run_attempt=1,
            job="continue-one-opted-in-draft",
            pr_number=890,
            head_ref="automation/self-heal-7e0abdf711dd4792d18d14b7",
            expected_head_sha="e93db12aa33ef334df327bad9282bd2ec1562b58",
            observed_base_sha="fb744e5b5925d61c6b473e27aab3606f237f7e6d",
            current_main_sha="1fe7b0cc033ab53369248478e6f14b6d6babbead",
            classification="NON_ALLOWLISTED_MERGE_CONFLICTS",
            exit_code=2,
            failing_phase="INTEGRATE_CURRENT_MAIN",
            failing_line=83,
            failing_command="git merge --no-ff --no-edit 1fe7b0c",
            branch_push_state="NOT_ATTEMPTED",
            conflict_paths=(
                "tools/qikvrt_requested_review_executor.py",
                ".github/workflows/qikvrt_requested_review_executor.yml",
            ),
        )

    def test_receipt_binds_subject_cause_and_effect_boundary(self) -> None:
        receipt = self._receipt()
        self.assertEqual(
            receipt["schema"],
            "qikvrt.autonomous-pr-continuation.failure-receipt.v1",
        )
        self.assertEqual(receipt["state"], "BLOCK")
        self.assertEqual(
            receipt["classification"], "NON_ALLOWLISTED_MERGE_CONFLICTS"
        )
        self.assertEqual(receipt["binding"]["pull_request"], 890)
        self.assertEqual(
            receipt["binding"]["expected_head_sha"],
            "e93db12aa33ef334df327bad9282bd2ec1562b58",
        )
        self.assertEqual(receipt["causal_detail"]["conflict_count"], 2)
        self.assertEqual(receipt["effects"]["branch_push_state"], "NOT_ATTEMPTED")
        self.assertEqual(receipt["effects"]["external_effect"], "NONE")
        self.assertFalse(receipt["effects"]["productive_effect"])

    def test_all_human_surfaces_include_reason_and_exact_binding(self) -> None:
        receipt = self._receipt()
        annotation = render_annotation(receipt)
        summary = render_summary(receipt)
        comment = render_pr_comment(
            receipt,
            current_head_sha="e93db12aa33ef334df327bad9282bd2ec1562b58",
        )
        for rendered in (annotation, summary, comment):
            self.assertIn("NON_ALLOWLISTED_MERGE_CONFLICTS", rendered)
            self.assertIn("890", rendered)
            self.assertIn("e93db12", rendered)
        self.assertIn("tools/qikvrt_requested_review_executor.py", summary)
        self.assertIn("binding drift after the failed run: `false`", comment)
        self.assertIn("Smallest next evidence", summary)

    def test_comment_marks_head_drift_without_transferring_evidence(self) -> None:
        comment = render_pr_comment(
            self._receipt(),
            current_head_sha="a" * 40,
        )
        self.assertIn("binding drift after the failed run: `true`", comment)
        self.assertIn("exact observed head", comment)
        self.assertIn("current live PR head at notification", comment)

    def test_conflict_paths_are_sorted_deduplicated_and_safe(self) -> None:
        self.assertEqual(
            normalize_conflict_paths(("z/path", "a/path", "z/path", "")),
            ["a/path", "z/path"],
        )
        with self.assertRaises(FailureReceiptError):
            normalize_conflict_paths(("../escape",))
        with self.assertRaises(FailureReceiptError):
            normalize_conflict_paths(("/absolute",))

    def test_merge_conflict_classification_requires_actual_paths(self) -> None:
        values = self._receipt()
        binding = values["binding"]
        execution = values["execution"]
        with self.assertRaises(FailureReceiptError):
            build_receipt(
                repository=binding["repository"],
                run_id=execution["run_id"],
                run_attempt=execution["run_attempt"],
                job=execution["job"],
                pr_number=binding["pull_request"],
                head_ref=binding["head_ref"],
                expected_head_sha=binding["expected_head_sha"],
                observed_base_sha=binding["observed_base_sha"],
                current_main_sha=binding["current_main_sha"],
                classification="NON_ALLOWLISTED_MERGE_CONFLICTS",
                exit_code=2,
                failing_phase="INTEGRATE_CURRENT_MAIN",
                failing_line=1,
                failing_command="git merge",
                branch_push_state="NOT_ATTEMPTED",
                conflict_paths=(),
            )

    def test_cli_materializes_json_summary_annotation_and_comment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            conflicts = root / "conflicts.txt"
            receipt = root / "receipt.json"
            summary = root / "summary.md"
            annotation = root / "annotation.txt"
            conflicts.write_text("z/path\na/path\nz/path\n", encoding="utf-8")
            rc = main(
                [
                    "write",
                    "--output",
                    str(receipt),
                    "--summary-output",
                    str(summary),
                    "--annotation-output",
                    str(annotation),
                    "--repository",
                    "Goldkelch/qik-vrt",
                    "--run-id",
                    "33047686781",
                    "--run-attempt",
                    "1",
                    "--job",
                    "continue-one-opted-in-draft",
                    "--pr-number",
                    "890",
                    "--head-ref",
                    "automation/self-heal-7e0abdf711dd4792d18d14b7",
                    "--expected-head",
                    "e93db12aa33ef334df327bad9282bd2ec1562b58",
                    "--observed-base",
                    "fb744e5b5925d61c6b473e27aab3606f237f7e6d",
                    "--current-main",
                    "1fe7b0cc033ab53369248478e6f14b6d6babbead",
                    "--classification",
                    "NON_ALLOWLISTED_MERGE_CONFLICTS",
                    "--exit-code",
                    "2",
                    "--failing-phase",
                    "INTEGRATE_CURRENT_MAIN",
                    "--failing-line",
                    "83",
                    "--failing-command",
                    "git merge --no-ff --no-edit 1fe7b0c",
                    "--branch-push-state",
                    "NOT_ATTEMPTED",
                    "--conflicts-file",
                    str(conflicts),
                ]
            )
            self.assertEqual(rc, 0)
            value = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(value["causal_detail"]["conflict_paths"], ["a/path", "z/path"])
            self.assertIn("NON_ALLOWLISTED_MERGE_CONFLICTS", summary.read_text())
            self.assertIn("causal receipt preserved", annotation.read_text())

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                rc = main(
                    [
                        "render-comment",
                        "--input",
                        str(receipt),
                        "--current-head",
                        "e93db12aa33ef334df327bad9282bd2ec1562b58",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn(
                "qikvrt-autonomous-pr-continuation-failure",
                output.getvalue(),
            )

    def test_workflow_forbids_a_bare_failure_disposition(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        required_surfaces = (
            "failure-receipt.json",
            "failure-summary.md",
            "failure-annotation.txt",
            "GITHUB_STEP_SUMMARY",
            "::error title=%s::%s",
            "NON_ALLOWLISTED_MERGE_CONFLICTS",
            "qikvrt-autonomous-pr-continuation-failure",
            "Publish exact causal failure disposition",
            "Preserve causal continuation diagnostics",
            "actions/upload-artifact@",
        )
        for surface in required_surfaces:
            self.assertIn(surface, source)
        self.assertLess(
            source.index("cp tools/qikvrt_autonomous_pr_failure_receipt.py"),
            source.index('git switch -C "$HEAD_REF" "$EXPECTED_HEAD"'),
        )
        self.assertIn("branch_push_state=NOT_ATTEMPTED", source)
        self.assertIn("branch_push_state=IN_PROGRESS", source)
        self.assertIn("branch_push_state=OBSERVED", source)
        self.assertIn("continue-on-error: true", source)


if __name__ == "__main__":
    unittest.main()
