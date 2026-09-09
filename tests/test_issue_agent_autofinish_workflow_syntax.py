# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/issue-agent-autofinish.yml"
PROCESSOR = ROOT / ".github/workflows/issue-autonomous-processing.yml"


class IssueAgentAutofinishWorkflowSyntaxTests(unittest.TestCase):
    @staticmethod
    def shell_for_step(path: Path, step_name: str) -> str:
        lines = path.read_text(encoding="utf-8").splitlines()
        start = lines.index(step_name)
        run = next(index for index in range(start + 1, len(lines)) if lines[index] == "        run: |")
        body: list[str] = []
        for line in lines[run + 1 :]:
            if line.strip() and len(line) - len(line.lstrip(" ")) < 10:
                break
            body.append(line[10:] if len(line) >= 10 else line)
        return "\n".join(body) + "\n"

    def test_run_block_never_escapes_yaml_scalar(self):
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        for step_name in (
            "      - name: Bind one safe issue identifier for observer serialization",
            "      - name: Bind exact open issue-agent candidates and request merge authority",
        ):
            start = lines.index(step_name)
            run = next(index for index in range(start + 1, len(lines)) if lines[index] == "        run: |")
            body = lines[run + 1 :]
            self.assertTrue(body)
            for number, line in enumerate(body, start=run + 2):
                if line.strip() and len(line) - len(line.lstrip(" ")) < 10:
                    break
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip(" "))
                self.assertGreaterEqual(
                    indent,
                    10,
                    f"workflow shell line {number} escaped run block: {line!r}",
                )

    def test_deindented_run_block_is_valid_bash(self):
        for step_name in (
            "      - name: Bind one safe issue identifier for observer serialization",
            "      - name: Bind exact open issue-agent candidates and request merge authority",
        ):
            result = subprocess.run(
                ["bash", "-n"],
                input=self.shell_for_step(WORKFLOW, step_name),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_observer_receipt_and_concurrency_are_bound_per_exact_issue_run(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "group: issue-agent-completion-authority-observer-${{ needs.bind_issue.outputs.issue_number }}",
            workflow,
        )
        self.assertIn("Bind one safe issue identifier for observer serialization", workflow)
        self.assertIn("never directly from an unvalidated dispatch input", workflow)
        self.assertIn("[[ \"$REQUESTED_ISSUE\" =~ ^[1-9][0-9]*$ ]]", workflow)
        self.assertIn("- exact head: $head_sha", workflow)
        self.assertIn("- observer workflow run: $GITHUB_RUN_ID", workflow)

    def test_exact_handoff_is_bounded_and_valid_bash(self):
        workflow = PROCESSOR.read_text(encoding="utf-8")
        self.assertIn("actions: write", workflow)
        self.assertIn("gh workflow run issue-agent-autofinish.yml", workflow)
        self.assertIn("expected_head=$EXPECTED_HEAD", workflow)
        self.assertIn("actions/runs/$candidate", workflow)
        self.assertIn('--arg run "$run_id"', workflow)
        self.assertIn('contains("- observer workflow run: " + $run)', workflow)
        self.assertIn('pr_after="$(gh api "repos/$REPOSITORY/pulls/$EXPECTED_PR")"', workflow)
        self.assertIn('jq -r .head.sha <<<"$pr_after"', workflow)
        self.assertIn(".head.repo.full_name // empty", workflow)
        shell = self.shell_for_step(
            PROCESSOR,
            "      - name: Dispatch and reobserve the exact issue completion authority receipt",
        )
        result = subprocess.run(
            ["bash", "-n"],
            input=shell,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
