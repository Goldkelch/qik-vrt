# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/issue-agent-autofinish.yml"


class IssueAgentAutofinishWorkflowSyntaxTests(unittest.TestCase):
    def test_run_block_never_escapes_yaml_scalar(self):
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        start = lines.index("        run: |")
        body = lines[start + 1 :]
        self.assertTrue(body)
        for number, line in enumerate(body, start=start + 2):
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            self.assertGreaterEqual(
                indent,
                10,
                f"workflow shell line {number} escaped run block: {line!r}",
            )

    def test_deindented_run_block_is_valid_bash(self):
        lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
        start = lines.index("        run: |")
        shell = "\n".join(
            line[10:] if len(line) >= 10 else line
            for line in lines[start + 1 :]
        ) + "\n"
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
